"""Show chat_id of users who messaged the bot. Safe: never prints the token."""

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("TELEGRAM_BOT_TOKEN não encontrado no .env")
        sys.exit(1)

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if not data.get("ok"):
        print(f"Erro da API: {data}")
        sys.exit(1)

    results = data.get("result", [])
    if not results:
        print(
            "Nenhuma mensagem encontrada.\n"
            "Mande uma mensagem ao bot no Telegram e rode de novo."
        )
        return

    seen: dict[int, str] = {}
    for update in results:
        msg = update.get("message") or update.get("edited_message") or {}
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        if chat_id and chat_id not in seen:
            name = chat.get("first_name", "")
            username = chat.get("username", "")
            label = f"{name} (@{username})" if username else name
            seen[chat_id] = label

    if not seen:
        print("Nenhum chat_id encontrado nos updates.")
        return

    print("Chat IDs que mandaram mensagem ao bot:\n")
    for chat_id, label in seen.items():
        print(f"  {chat_id}  {label}")


if __name__ == "__main__":
    main()
