"""Marca como silenciosos os watches dos produtos de análise (memoria/analise-bf.md).

    python scripts/mark_silent.py            # dry-run (padrão): só confere
    python scripts/mark_silent.py --apply    # grava silent=true

Confere pelos IDs MLB da lista, não pelo número do watch: cada ID precisa ter
exatamente 1 watch ativo no chat, e o conjunto precisa bater com
--expect-watch-ids (padrão 6–22). Qualquer divergência → nada é gravado.
Respeita o teto MAX_SILENT_WATCHES_PER_CHAT e a janela :40–:50 da coleta.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import update  # noqa: E402

from lowpoint.config import MAX_SILENT_WATCHES_PER_CHAT  # noqa: E402
from lowpoint.db import SessionLocal  # noqa: E402
from lowpoint.models import Product, Watch  # noqa: E402

from add_watches import StopRun, check_window, default_chat_id, load_entries  # noqa: E402

DEFAULT_EXPECTED = set(range(6, 23))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--chat-id", type=int)
    args = ap.parse_args()

    try:
        check_window()
    except StopRun as exc:
        print(f"PARADO: {exc}")
        return 2

    chat_id = args.chat_id if args.chat_id is not None else default_chat_id()
    entries = load_entries()
    print(f"{'APPLY' if args.apply else 'DRY-RUN'} — {len(entries)} IDs de analise-bf.md")

    session = SessionLocal()
    try:
        if not args.apply:
            session.connection().exec_driver_sql("SET TRANSACTION READ ONLY")
        problems: list[str] = []
        watch_ids: list[int] = []
        for e in entries:
            rows = (
                session.query(Watch, Product)
                .join(Product)
                .filter(
                    Product.catalog_product_id == e.catalog_id,
                    Watch.chat_id == chat_id,
                    Watch.active.is_(True),
                )
                .all()
            )
            if len(rows) != 1:
                problems.append(f"{e.catalog_id}: {len(rows)} watches ativos (esperado 1)")
                continue
            w, p = rows[0]
            watch_ids.append(w.id)
            print(f"  watch {w.id:>3} · {e.catalog_id:<14} · {w.nickname or p.title} "
                  f"· silent={w.silent}")

        if set(watch_ids) != DEFAULT_EXPECTED:
            problems.append(f"watches {sorted(watch_ids)} ≠ esperados {sorted(DEFAULT_EXPECTED)}")

        others_silent = (
            session.query(Watch)
            .filter(Watch.chat_id == chat_id, Watch.active.is_(True),
                    Watch.silent.is_(True), Watch.id.notin_(watch_ids))
            .count()
        )
        total_silent = others_silent + len(watch_ids)
        print(f"Teto de silenciosos: {total_silent} (máx. {MAX_SILENT_WATCHES_PER_CHAT})")
        if total_silent > MAX_SILENT_WATCHES_PER_CHAT:
            problems.append("estoura o teto de silenciosos")

        if problems:
            print("DIVERGÊNCIA, nada gravado:\n  " + "\n  ".join(problems))
            session.rollback()
            return 1

        if not args.apply:
            print("Dry-run: nada foi gravado.")
            session.rollback()
            return 0

        result = session.execute(
            update(Watch)
            .where(Watch.id.in_(watch_ids), Watch.chat_id == chat_id)
            .values(silent=True)
        )
        if result.rowcount != len(entries):
            session.rollback()
            print(f"UPDATE afetaria {result.rowcount} linhas (esperado {len(entries)}): desfeito")
            return 1
        session.commit()
        print(f"silent=true gravado em {result.rowcount} watches: {sorted(watch_ids)}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
