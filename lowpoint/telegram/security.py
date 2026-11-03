import hmac
import os


def validate_secret_token(header_value: str | None) -> bool:
    expected = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    if not expected or not header_value:
        return False
    return hmac.compare_digest(header_value, expected)


def is_chat_allowed(chat_id: int) -> bool:
    raw = os.environ.get("ALLOWED_CHAT_IDS", "")
    if not raw:
        return False
    allowed = set()
    for part in raw.split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            allowed.add(int(part))
    return chat_id in allowed


UNAUTHORIZED_MESSAGE = "Esse bot é pessoal e está em fase de testes."
