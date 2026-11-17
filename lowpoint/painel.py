"""Painel ao vivo da vitrine: GET /api/painel (memoria/design/painel-ao-vivo.md).

Só leitura e público. O JSON é montado campo a campo a partir de uma
allowlist fixa (os 20 produtos do pré-registro): nada de alvo, chat_id,
seller_id, item_id, silent, apelido ou de quais produtos são pessoais.
Sem veredito: só preço, Referência (mediana da B0) e % vs Referência.
"""
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import ROUND_DOWN, Decimal
from typing import Callable

from analysis import metrics, prereg
from lowpoint.tick import STALE_AFTER

log = logging.getLogger("lowpoint.painel")

VERSION = 1
BLOCK = timedelta(hours=3)
MEMO_TTL = timedelta(minutes=5)
FEW_OFFERS = 3  # mesma regra do rodapé "poucos vendedores" dos alertas
CACHE_OK = "public, max-age=300, s-maxage=3600, stale-while-revalidate=3600"
DEFAULT_ORIGIN = "https://lowpoint-web.vercel.app"
ML_CATALOG_URL = "https://www.mercadolivre.com.br/p/{}"

# Categorias de memoria/analise-bf.md. Os 3 pessoais entram numa categoria
# comum para nada no JSON separar "os meus".
CATEGORY_ORDER = ["TV e áudio", "Celular e computador", "Casa", "Games", "Controle"]
CATEGORY = {
    "MLB57081243": "Games",                 # PS5
    "MLB79391475": "Celular e computador",  # LG 27"
    "MLB59323822": "Celular e computador",  # AOC 27"
    "MLB75001430": "TV e áudio", "MLB48808732": "TV e áudio", "MLB67919726": "TV e áudio",
    "MLB69393461": "TV e áudio", "MLB68445612": "TV e áudio",
    "MLB47111905": "Celular e computador", "MLB64222225": "Celular e computador",
    "MLB1055309009": "Celular e computador", "MLB70040749": "Celular e computador",
    "MLB19672271": "Casa", "MLB62963466": "Casa", "MLB17484025": "Casa", "MLB15261607": "Casa",
    "MLB28083897": "Games", "MLB49200061": "Games",
    "MLB26967981": "Controle", "MLB19400333": "Controle",
}
_ORDERED = sorted(prereg.PRODUCTS, key=lambda p: CATEGORY_ORDER.index(CATEGORY[p.catalog_id]))


@dataclass(frozen=True)
class PriceRow:
    at: datetime  # UTC
    price: Decimal
    available: bool


@dataclass
class PainelData:
    rows: dict[str, list[PriceRow]]
    last_collection: datetime | None
    offer_counts: dict[str, int]


# --- Montagem do JSON ---------------------------------------------------------

def _iso(t: datetime | None) -> str | None:
    return None if t is None else t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _money(x: Decimal | None) -> str | None:
    return None if x is None else f"{x:.2f}"


def _pct(current: Decimal, ref: Decimal) -> str:
    v = ((current - ref) / ref * 100).quantize(Decimal("0.1"), rounding=ROUND_DOWN)  # nunca exagera
    return "0.0" if v == 0 else f"{v:.1f}"


def _block_start(t: datetime) -> datetime:
    local = t.astimezone(prereg.BRT)
    return local.replace(hour=local.hour - local.hour % 3, minute=0, second=0, microsecond=0)


def _series(rows: list[PriceRow]) -> list[list[str]]:
    """Último preço disponível de cada bloco de 3h (BRT), a partir da B0."""
    b0 = prereg.W["B0"].start
    last: dict[datetime, PriceRow] = {}
    for r in sorted(rows, key=lambda r: r.at):
        if r.available and r.at >= b0:
            last[_block_start(r.at)] = r
    return [[_iso(max(block, b0)), _money(r.price)] for block, r in sorted(last.items())]


def _product(p: prereg.Product, rows: list[PriceRow], offer_count: int | None) -> dict:
    rows = sorted(rows, key=lambda r: r.at)
    available = [r for r in rows if r.available]
    current = available[-1] if available else None
    disponivel = bool(rows) and rows[-1].available
    ref = metrics.reference([metrics.Obs(r.at, r.price, None, r.available) for r in rows])
    pct = _pct(current.price, ref) if (disponivel and current and ref) else None
    return {
        "id": p.catalog_id,
        "nome": p.label,
        "categoria": CATEGORY[p.catalog_id],
        "url": ML_CATALOG_URL.format(p.catalog_id),
        # Termos ML 5.2: sem oferta disponível agora, não publica o último preço.
        "preco_atual": _money(current.price) if (disponivel and current) else None,
        "preco_atual_em": _iso(current.at) if (disponivel and current) else None,
        "disponivel": disponivel,
        "poucas_ofertas": offer_count is not None and offer_count < FEW_OFFERS,
        "referencia": _money(ref),
        "vs_referencia_pct": pct,
        "serie": _series(rows),
    }


def build_payload(data: PainelData, now: datetime) -> dict:
    b0 = prereg.W["B0"]
    last = data.last_collection
    return {
        "versao": VERSION,
        "gerado_em": _iso(now),
        "ultima_coleta": _iso(last),
        "coleta_atrasada": last is None or now - last > STALE_AFTER,
        "amostragem": "último preço de cada bloco de 3h (horário de Brasília)",
        "referencia": {
            "definicao": "mediana da melhor oferta de 14/11 14:50 a 17/11 14:50",
            "inicio": _iso(b0.start),
            "fim": _iso(b0.end),
            "parcial": now < b0.end,
        },
        "produtos": [
            _product(p, data.rows.get(p.catalog_id, []), data.offer_counts.get(p.catalog_id))
            for p in _ORDERED
        ],
    }


# --- Leitura do Neon (READ ONLY) ---------------------------------------------------

_PRICES_SQL = """
select p.catalog_product_id, h.price, h.available, h.collected_at
from price_history h join products p on p.id = h.product_id
where p.catalog_product_id = any(:ids) and h.collected_at >= :since
order by p.catalog_product_id, h.collected_at
"""
_LAST_SQL = "select max(collected_at) from offer_snapshots"
_COUNTS_SQL = """
select p.catalog_product_id, s.collected_at, count(*)
from offer_snapshots s join products p on p.id = s.product_id
where p.catalog_product_id = any(:ids) and s.collected_at >= :recent
group by 1, 2
"""


def fetch_from_db() -> PainelData:
    from sqlalchemy import text

    from lowpoint.db import engine

    ids = [p.catalog_id for p in prereg.PRODUCTS]
    recent = datetime.now(timezone.utc) - timedelta(hours=6)
    with engine.connect() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        rows: dict[str, list[PriceRow]] = {}
        for cid, price, available, at in conn.execute(
            text(_PRICES_SQL), {"ids": ids, "since": prereg.W["B0"].start}
        ):
            rows.setdefault(cid, []).append(PriceRow(at, Decimal(str(price)), bool(available)))
        last = conn.execute(text(_LAST_SQL)).scalar()
        latest: dict[str, tuple[datetime, int]] = {}
        for cid, at, n in conn.execute(text(_COUNTS_SQL), {"ids": ids, "recent": recent}):
            if cid not in latest or at > latest[cid][0]:
                latest[cid] = (at, n)
        conn.rollback()
    return PainelData(rows, last, {cid: n for cid, (_, n) in latest.items()})


# --- HTTP --------------------------------------------------------------------------

_memo: dict = {}


def clear_memo() -> None:
    _memo.clear()


def _json(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def handle_painel(method: str, path: str, *, now: datetime | None = None,
                  fetch: Callable[[], PainelData] = fetch_from_db) -> tuple[int, dict, bytes]:
    now = now or datetime.now(timezone.utc)
    base = {"Content-Type": "application/json; charset=utf-8"}
    if method not in ("GET", "HEAD"):
        return 405, {**base, "Allow": "GET, HEAD", "Cache-Control": "no-store"}, _json({"erro": "método"})
    if "?" in path:
        # Query string furaria o cache da CDN (cada ?x= vira uma chave nova) e
        # acertaria o Neon: recusada antes de qualquer consulta.
        return 400, {**base, "Cache-Control": "no-store"}, _json({"erro": "sem parâmetros"})

    if _memo and now - _memo["at"] < MEMO_TTL:
        body = _memo["body"]
    else:
        try:
            body = _json(build_payload(fetch(), now))
        except Exception:
            log.exception("painel: falha ao montar o payload")
            return 503, {**base, "Cache-Control": "no-store"}, _json({"erro": "indisponível"})
        _memo.update(at=now, body=body)

    headers = {
        **base,
        "Cache-Control": CACHE_OK,
        "Access-Control-Allow-Origin": os.environ.get("PAINEL_ALLOWED_ORIGIN", DEFAULT_ORIGIN),
    }
    return 200, headers, b"" if method == "HEAD" else body
