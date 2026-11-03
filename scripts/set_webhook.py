"""Register or query the Telegram webhook. Safe: no token on the command line."""

import argparse
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

_API = "https://api.telegram.org"


def _get_env(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        print(f"{name} não encontrado no .env")
        sys.exit(1)
    return val


def set_webhook(token: str, url: str, secret: str) -> None:
    resp = requests.post(
        f"{_API}/bot{token}/setWebhook",
        json={
            "url": url,
            "secret_token": secret,
            "allowed_updates": ["message", "callback_query"],
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("ok"):
        print(f"Webhook registrado: {url}")
    else:
        print(f"Erro: {data}")
        sys.exit(1)


def get_info(token: str) -> None:
    resp = requests.get(
        f"{_API}/bot{token}/getWebhookInfo",
        timeout=10,
    )
    resp.raise_for_status()
    info = resp.json().get("result", {})

    print("Webhook info:")
    print(f"  URL:              {info.get('url') or '(não configurado)'}")
    print(f"  Pending updates:  {info.get('pending_update_count', 0)}")
    if info.get("last_error_date"):
        print(f"  Last error:       {info.get('last_error_message', '?')}")
    if info.get("has_custom_certificate"):
        print("  Custom cert:      sim")
    allowed = info.get("allowed_updates", [])
    if allowed:
        print(f"  Allowed updates:  {', '.join(allowed)}")


def delete_webhook(token: str) -> None:
    resp = requests.post(
        f"{_API}/bot{token}/deleteWebhook",
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("ok"):
        print("Webhook removido.")
    else:
        print(f"Erro: {data}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gerenciar webhook do Telegram")
    sub = parser.add_subparsers(dest="command")

    set_cmd = sub.add_parser("set", help="Registrar webhook")
    set_cmd.add_argument(
        "--url",
        help="URL do webhook (default: TELEGRAM_WEBHOOK_URL do .env)",
    )

    sub.add_parser("info", help="Consultar status do webhook")
    sub.add_parser("delete", help="Remover webhook")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    token = _get_env("TELEGRAM_BOT_TOKEN")

    if args.command == "set":
        url = args.url or os.environ.get("TELEGRAM_WEBHOOK_URL", "")
        if not url:
            print("Informe --url ou defina TELEGRAM_WEBHOOK_URL no .env")
            sys.exit(1)
        secret = _get_env("TELEGRAM_WEBHOOK_SECRET")
        set_webhook(token, url, secret)
    elif args.command == "info":
        get_info(token)
    elif args.command == "delete":
        delete_webhook(token)


if __name__ == "__main__":
    main()
