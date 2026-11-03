"""Send one example of each alert type to your Telegram chat for visual review.

Uses fake data marked [TESTE]. Does NOT write to the alerts table.

Usage:
    python scripts/preview_alerts.py
"""

import os
import sys
import time
from decimal import Decimal

import requests
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, ".")

from lowpoint.telegram.formatter import AlertContext, AlertMessage, format_alert

_API = "https://api.telegram.org"


def _send(token: str, chat_id: int, msg: AlertMessage) -> None:
    payload = {
        "chat_id": chat_id,
        "text": msg.text,
        "parse_mode": msg.parse_mode,
        "reply_markup": {
            "inline_keyboard": [
                [{"text": msg.button_text, "url": msg.button_url}]
            ]
        },
    }
    resp = requests.post(
        f"{_API}/bot{token}/sendMessage",
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()


_SCENARIOS: list[tuple[str, dict]] = [
    (
        "Desconto real sem alvo (PODE IR)",
        dict(
            verdict="real",
            price=Decimal("3690.00"),
            original_price=Decimal("4499.00"),
            target_price=Decimal("3500.00"),
            lowest_price=Decimal("3780.00"),
            median_30d=Decimal("3890.00"),
            monitoring_days=47,
            pre_hike_price=None,
            has_warranty=True,
            is_official=True,
            suspect_count=0,
            cheapest_suspect_price=None,
        ),
    ),
    (
        "Alvo atingido + real",
        dict(
            verdict="real",
            price=Decimal("3400.00"),
            original_price=Decimal("4499.00"),
            target_price=Decimal("3500.00"),
            lowest_price=Decimal("3450.00"),
            median_30d=Decimal("3890.00"),
            monitoring_days=30,
            pre_hike_price=None,
            has_warranty=True,
            is_official=True,
            suspect_count=0,
            cheapest_suspect_price=None,
        ),
    ),
    (
        "Maquiado (SEGURA)",
        dict(
            verdict="maquiado",
            price=Decimal("3600.00"),
            original_price=Decimal("6000.00"),
            target_price=Decimal("3500.00"),
            lowest_price=Decimal("3400.00"),
            median_30d=Decimal("3450.00"),
            monitoring_days=45,
            pre_hike_price=Decimal("3300.00"),
            has_warranty=True,
            is_official=False,
            suspect_count=0,
            cheapest_suspect_price=None,
        ),
    ),
    (
        "Alvo atingido + maquiado",
        dict(
            verdict="maquiado",
            price=Decimal("3400.00"),
            original_price=Decimal("5600.00"),
            target_price=Decimal("3500.00"),
            lowest_price=Decimal("3350.00"),
            median_30d=Decimal("3450.00"),
            monitoring_days=38,
            pre_hike_price=None,
            has_warranty=False,
            is_official=True,
            suspect_count=2,
            cheapest_suspect_price=Decimal("1899.00"),
        ),
    ),
    (
        "Sem garantia + suspeitas",
        dict(
            verdict="real",
            price=Decimal("2990.00"),
            original_price=Decimal("4499.00"),
            target_price=Decimal("3500.00"),
            lowest_price=Decimal("3100.00"),
            median_30d=Decimal("3890.00"),
            monitoring_days=52,
            pre_hike_price=None,
            has_warranty=False,
            is_official=False,
            suspect_count=3,
            cheapest_suspect_price=Decimal("2399.00"),
        ),
    ),
]


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("TELEGRAM_BOT_TOKEN não encontrado no .env")
        sys.exit(1)

    raw = os.environ.get("ALLOWED_CHAT_IDS", "")
    if not raw:
        print("ALLOWED_CHAT_IDS não encontrado no .env")
        sys.exit(1)
    chat_id = int(raw.split(",")[0].strip())

    print(f"Enviando {len(_SCENARIOS)} alertas de teste para chat {chat_id}...\n")

    for label, overrides in _SCENARIOS:
        ctx = AlertContext(
            product_name="[TESTE] PS5 Slim Digital",
            item_id="MLB57081243",
            reason="dados fictícios para teste visual",
            **overrides,
        )
        msg = format_alert(ctx)
        _send(token, chat_id, msg)
        print(f"  Enviado: {label} ({msg.alert_type})")
        time.sleep(1)

    print("\nPronto. Confere no celular.")


if __name__ == "__main__":
    main()
