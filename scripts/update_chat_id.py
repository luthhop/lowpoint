"""Update chat_id of existing watches (those registered via CLI with chat_id=0).

Usage:
    python scripts/update_chat_id.py <chat_id>
    python scripts/update_chat_id.py <chat_id> --dry-run
"""

import argparse
import sys

from dotenv import load_dotenv

load_dotenv()

from lowpoint.db import SessionLocal
from lowpoint.models import Watch


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Atualizar chat_id dos watches existentes"
    )
    parser.add_argument("chat_id", type=int, help="Novo chat_id (do Telegram)")
    parser.add_argument(
        "--from-id",
        type=int,
        default=0,
        help="chat_id atual a substituir (default: 0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar o que seria alterado sem salvar",
    )
    args = parser.parse_args()

    session = SessionLocal()
    try:
        watches = (
            session.query(Watch)
            .filter(Watch.chat_id == args.from_id, Watch.active.is_(True))
            .all()
        )

        if not watches:
            print(f"Nenhum watch ativo com chat_id={args.from_id}.")
            return

        for w in watches:
            label = w.nickname or f"product_id={w.product_id}"
            print(f"  Watch {w.id}: {label}  chat_id {w.chat_id} -> {args.chat_id}")
            if not args.dry_run:
                w.chat_id = args.chat_id

        if args.dry_run:
            print(f"\n(dry-run) {len(watches)} watch(es) seriam atualizados.")
        else:
            session.commit()
            print(f"\n{len(watches)} watch(es) atualizados.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
