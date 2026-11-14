"""Cadastra os produtos de análise da BF (memoria/analise-bf.md) como watches.

    python scripts/add_watches.py              # dry-run (padrão): não grava nada
    python scripts/add_watches.py --apply      # grava watch + 1º ponto do histórico

Regras:
- Usa register_product (a mesma função do /adicionar) e o mesmo limite de 20
  watches ativos por chat do webhook. Apelido vem da lista.
- Alvo provisório = 50% da melhor oferta (select_best_offer, como o coletor),
  arredondado para baixo para reais inteiros.
- Chamadas ao ML sequenciais, 1 s entre elas, 1 tentativa só. 429 → para e
  reporta. 401 → para (no dry-run não renova token, porque isso grava no banco).
- Não roda entre :40 e :50 para não competir com a coleta das :45; a janela
  é checada antes de cada chamada.
- --apply é tudo-ou-nada na checagem do limite e pula IDs já cadastrados
  (register_product sobrescreveria o alvo deles).
"""

import argparse
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_FLOOR, Decimal
from pathlib import Path
from statistics import median as _median

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lowpoint.best_offer import select_best_offer  # noqa: E402
from lowpoint.db import SessionLocal  # noqa: E402
from lowpoint.models import PriceHistory, Product, Watch  # noqa: E402
from lowpoint.register import register_product  # noqa: E402
from lowpoint.sources.base import CatalogSnapshot  # noqa: E402
from lowpoint.sources.ml_catalog import REQUEST_TIMEOUT, MLCatalogSource  # noqa: E402
from lowpoint.telegram.webhook import _MAX_WATCHES_PER_CHAT  # noqa: E402

LIST_FILE = Path(__file__).resolve().parent.parent / "memoria" / "analise-bf.md"
CALL_INTERVAL_SECONDS = 1.0
BLOCKED_MINUTES = range(40, 51)  # :40 a :50, coleta às :45
TARGET_RATIO = Decimal("0.50")


class StopRun(Exception):
    """Interrompe o lote inteiro (429, 401, janela da coleta)."""


def check_window(now: datetime | None = None) -> None:
    now = now or datetime.now()
    if now.minute in BLOCKED_MINUTES:
        raise StopRun(
            f"{now:%H:%M}: janela :40–:50 (coleta das :45). Rode depois das :50."
        )


class GentleMLSource(MLCatalogSource):
    """MLCatalogSource com 1 tentativa, 1 s entre chamadas e parada em 429/401."""

    def __init__(self, allow_refresh: bool):
        super().__init__()
        self._allow_refresh = allow_refresh
        self._last_call = 0.0

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        check_window()
        wait = CALL_INTERVAL_SECONDS - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self.call_count += 1
        try:
            resp = requests.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
        finally:
            self._last_call = time.monotonic()
        if resp.status_code == 429:
            raise StopRun(
                f"HTTP 429 em {url} (Retry-After={resp.headers.get('Retry-After', '-')}). "
                f"Parei após {self.call_count} chamadas."
            )
        return resp

    def _refresh_token(self) -> str:
        if not self._allow_refresh:
            raise StopRun(
                "HTTP 401: token ML expirado. No dry-run não renovo (gravaria no banco); "
                "a coleta das :45 renova. Rode de novo depois."
            )
        return super()._refresh_token()


@dataclass
class Entry:
    catalog_id: str
    nickname: str
    group: str


@dataclass
class Row:
    entry: Entry
    title: str = ""
    best_price: Decimal | None = None
    target: Decimal | None = None
    offers: int = 0
    new_offers: int = 0
    sellers: int = 0
    registered: str = "não"
    error: str = ""
    warnings: list[str] = field(default_factory=list)
    snapshot: CatalogSnapshot | None = None
    hist_median: Decimal | None = None


def load_entries(path: Path = LIST_FILE) -> list[Entry]:
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 3 and parts[0].startswith("MLB") and parts[0][3:].isdigit():
            entries.append(Entry(*parts))
    return entries


def default_chat_id() -> int:
    for part in os.environ.get("ALLOWED_CHAT_IDS", "").split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            return int(part)
    raise SystemExit("ALLOWED_CHAT_IDS vazio; informe --chat-id")


def floor_target(best_price: Decimal) -> Decimal:
    return (best_price * TARGET_RATIO).to_integral_value(rounding=ROUND_FLOOR)


def db_state(session, chat_id: int, catalog_id: str) -> tuple[str, Decimal | None]:
    """(situação do cadastro, mediana histórica) — só leitura."""
    product = session.query(Product).filter(Product.catalog_product_id == catalog_id).first()
    if not product:
        return "não", None
    watch = (
        session.query(Watch)
        .filter(Watch.chat_id == chat_id, Watch.product_id == product.id)
        .first()
    )
    prices = [
        Decimal(str(p))
        for (p,) in session.query(PriceHistory.price).filter(
            PriceHistory.product_id == product.id, PriceHistory.available.is_(True)
        )
    ]
    hist = _median(prices) if prices else None
    if not watch:
        return "produto sim, watch não", hist
    return ("sim (ativo)" if watch.active else "sim (inativo)"), hist


def inspect(source: GentleMLSource, session, chat_id: int, entry: Entry) -> Row:
    row = Row(entry)
    row.registered, row.hist_median = db_state(session, chat_id, entry.catalog_id)
    try:
        snap = source.fetch_catalog(entry.catalog_id)
    except requests.HTTPError as exc:
        row.error = f"HTTP {exc.response.status_code}"
        return row
    row.snapshot = snap
    row.title = snap.title
    row.offers = len(snap.offers)
    row.new_offers = sum(1 for o in snap.offers if o.condition == "new")
    row.sellers = len({o.seller_id for o in snap.offers})
    best = select_best_offer(snap.offers, historical_median=row.hist_median)
    if best:
        row.best_price = best.offer.price
        row.target = floor_target(best.offer.price)
        row.warnings = best.warnings
    return row


def flags(row: Row) -> str:
    out = []
    if row.error:
        out.append(row.error)
    elif row.offers == 0:
        out.append("⚠ 0 OFERTAS")
    elif row.best_price is None:
        out.append("⚠ sem oferta new válida")
    if not row.error and row.sellers == 1:
        out.append("⚠ 1 VENDEDOR")
    return ", ".join(out)


def brl(v: Decimal | None) -> str:
    return "-" if v is None else f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def print_table(rows: list[Row]) -> None:
    print(f"{'ID':<14} {'Apelido':<24} {'Nome (ML)':<44} {'Melhor':>13} "
          f"{'Alvo 50%':>12} {'Of.':>4} {'Vend.':>5}  {'Cadastrado':<22} Marcas")
    for r in rows:
        print(f"{r.entry.catalog_id:<14} {r.entry.nickname[:24]:<24} {r.title[:44]:<44} "
              f"{brl(r.best_price):>13} {brl(r.target):>12} {r.offers:>4} {r.sellers:>5}  "
              f"{r.registered:<22} {flags(r)}")


def apply_row(row: Row, chat_id: int) -> str:
    """Mesma sequência do /adicionar: register_product → apelido → 1º ponto."""
    product, watch = register_product(row.entry.catalog_id, row.target, chat_id)
    session = SessionLocal()
    try:
        w = session.get(Watch, watch.id)
        w.nickname = row.entry.nickname
        p = session.get(Product, product.id)
        snap = row.snapshot
        if snap.title and p.title.startswith("(pendente"):
            p.title = snap.title
            if snap.image_url:
                p.image_url = snap.image_url
        best = select_best_offer(snap.offers, historical_median=row.hist_median)
        session.add(PriceHistory(
            product_id=p.id,
            price=best.offer.price,
            original_price=best.offer.original_price,
            item_id=best.offer.item_id,
            seller_id=best.offer.seller_id,
            available=True,
            collected_at=snap.collected_at,
        ))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return f"watch {watch.id}, alvo {brl(row.target)}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True)
    mode.add_argument("--apply", action="store_true")
    ap.add_argument("--chat-id", type=int)
    args = ap.parse_args()

    chat_id = args.chat_id if args.chat_id is not None else default_chat_id()
    entries = load_entries()
    print(f"{'APPLY' if args.apply else 'DRY-RUN'} — {len(entries)} produtos de {LIST_FILE.name}")

    try:
        check_window()
    except StopRun as exc:
        print(f"PARADO: {exc}")
        return 2

    session = SessionLocal()
    try:
        session.connection().exec_driver_sql("SET TRANSACTION READ ONLY")
        active = (
            session.query(Watch)
            .filter(Watch.chat_id == chat_id, Watch.active.is_(True))
            .count()
        )
        source = GentleMLSource(allow_refresh=args.apply)
        rows: list[Row] = []
        stopped = None
        for e in entries:
            try:
                rows.append(inspect(source, session, chat_id, e))
            except StopRun as exc:
                stopped = str(exc)
                break
    finally:
        session.rollback()
        session.close()

    print_table(rows)
    print(f"\nChamadas ao ML: {source.call_count}")

    new_rows = [r for r in rows if r.registered in ("não", "produto sim, watch não")]
    total_after = active + len(new_rows)
    print(f"Limite: {active} watches ativos + {len(new_rows)} novos = {total_after} "
          f"(máx. {_MAX_WATCHES_PER_CHAT})")
    if stopped:
        print(f"\nPARADO: {stopped}")
        return 2
    if total_after > _MAX_WATCHES_PER_CHAT:
        print("ESTOURA O LIMITE: nada será gravado.")
        return 1

    if not args.apply:
        print("\nDry-run: nada foi gravado.")
        return 0

    bad = [r for r in new_rows if r.error or r.target is None]
    if bad:
        print("Sem melhor oferta válida, nada gravado: "
              + ", ".join(r.entry.catalog_id for r in bad))
        return 1
    for r in rows:
        if r not in new_rows:
            print(f"{r.entry.catalog_id}: já cadastrado ({r.registered}), pulado")
            continue
        print(f"{r.entry.catalog_id}: {apply_row(r, chat_id)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
