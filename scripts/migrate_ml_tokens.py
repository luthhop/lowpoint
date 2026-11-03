"""Migra tokens do ML de ml_tokens.json para a tabela ml_tokens no banco."""
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from lowpoint.db import SessionLocal
from lowpoint.models import MLToken

TOKENS_PATH = Path(__file__).resolve().parent.parent / "ml_tokens.json"


def migrate() -> None:
    if not TOKENS_PATH.exists():
        print(f"Arquivo {TOKENS_PATH} nao encontrado.")
        return

    data = json.loads(TOKENS_PATH.read_text(encoding="utf-8"))
    session = SessionLocal()
    try:
        existing = session.query(MLToken).first()
        if existing:
            print("Token ja existe no banco. Atualizando...")
            existing.access_token = data["access_token"]
            existing.refresh_token = data.get("refresh_token")
            existing.expires_in = data.get("expires_in")
            existing.user_id = data.get("user_id")
        else:
            session.add(
                MLToken(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),
                    expires_in=data.get("expires_in"),
                    user_id=data.get("user_id"),
                )
            )
        session.commit()
        print("Token migrado para o banco com sucesso.")
    finally:
        session.close()


if __name__ == "__main__":
    migrate()
