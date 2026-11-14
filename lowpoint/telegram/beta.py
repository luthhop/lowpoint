"""Pedido de convite pro beta fechado (chats fora de ALLOWED_CHAT_IDS).

- /start (inclusive /start beta, do link t.me/...?start=beta) → resposta fixa
  e um aviso pro dono (1º ALLOWED_CHAT_IDS) com nome, @username e chat_id.
- Anti-abuso: no máximo 1 aviso por chat a cada 24h.
- Nada sobre quem pediu vai pro banco: o aviso é só uma mensagem do Telegram.
  Para o limite de 24h guardamos em system_state apenas o horário do último
  aviso, numa chave HMAC do chat_id (com TELEGRAM_WEBHOOK_SECRET) que não
  revela o chat_id nem o nome.
"""

import hashlib
import hmac
import logging
import os
from datetime import datetime, timedelta, timezone

import requests

from lowpoint.db import SessionLocal
from lowpoint.models import SystemState
from lowpoint.telegram.security import UNAUTHORIZED_MESSAGE

log = logging.getLogger("lowpoint.beta")

INVITE_REPLY = "O Lowpoint tá em beta fechado. Teu pedido chegou, te aviso se abrir vaga."
POINT_TO_START = UNAUTHORIZED_MESSAGE
NOTICE_INTERVAL = timedelta(hours=24)
HTTP_TIMEOUT = (5, 10)
_KEY_PREFIX = "beta_notice:"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def is_start(text: str) -> bool:
    command = text.split(maxsplit=1)[0] if text else ""
    return command == "/start" or command.startswith("/start@")


def _state_key(chat_id: int) -> str:
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").encode()
    digest = hmac.new(secret, str(chat_id).encode(), hashlib.sha256).hexdigest()
    return _KEY_PREFIX + digest[:32]


def _owner_chat_id() -> int | None:
    for part in os.environ.get("ALLOWED_CHAT_IDS", "").split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            return int(part)
    return None


def _notice_text(chat_id: int, sender: dict) -> str:
    name = " ".join(
        p for p in (sender.get("first_name"), sender.get("last_name")) if p
    ).strip() or "(sem nome)"
    lines = ["Pedido de convite pro beta", f"Nome: {name}"]
    if sender.get("username"):
        lines.append(f"Usuário: @{sender['username']}")
    lines.append(f"chat_id: {chat_id}")
    return "\n".join(lines)


def _send_notice(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    owner = _owner_chat_id()
    if not token or owner is None:
        log.error("TELEGRAM_BOT_TOKEN ou ALLOWED_CHAT_IDS ausente; pedido de convite sem aviso.")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": owner, "text": text},  # texto puro: nome vem do usuário
            timeout=HTTP_TIMEOUT,
        )
    except requests.RequestException:
        log.exception("Falha de rede ao avisar pedido de convite.")
        return False
    if not resp.ok:
        log.error("Aviso de pedido de convite falhou (HTTP %s).", getattr(resp, "status_code", "?"))
    return bool(resp.ok)


def handle_outsider(chat_id: int, text: str, sender: dict) -> str:
    """Texto da resposta para um chat fora da allowlist (e avisa o dono se for /start)."""
    if not is_start(text):
        return POINT_TO_START

    now = _now()
    key = _state_key(chat_id)
    session = SessionLocal()
    try:
        row = session.get(SystemState, key)
        last = row.value_at if row else None
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if last is not None and now - last < NOTICE_INTERVAL:
            return INVITE_REPLY
        if _send_notice(_notice_text(chat_id, sender)):
            session.merge(SystemState(key=key, value_at=now))
            session.commit()
    except Exception:
        session.rollback()
        log.exception("Erro ao registrar pedido de convite.")
    finally:
        session.close()
    return INVITE_REPLY
