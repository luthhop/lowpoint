"""Notify via Telegram when the collect workflow fails.

Skips notification if the previous completed run also failed (avoids spam).
Called from GitHub Actions with `if: failure()`.

Env vars (set by the workflow):
    TELEGRAM_BOT_TOKEN, ALLOWED_CHAT_IDS, RUN_URL,
    GITHUB_REPOSITORY, GH_TOKEN
"""

import os
import sys

import requests


def _prev_run_also_failed() -> bool:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GH_TOKEN", "")
    if not repo or not token:
        return False

    try:
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/actions/workflows/collect.yml/runs",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            params={"per_page": 2, "status": "completed"},
            timeout=10,
        )
        resp.raise_for_status()
        runs = resp.json().get("workflow_runs", [])
        if runs:
            return runs[0].get("conclusion") == "failure"
    except Exception:
        pass
    return False


def main() -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_ids = os.environ.get("ALLOWED_CHAT_IDS", "")
    run_url = os.environ.get("RUN_URL", "")

    if not bot_token or not chat_ids:
        print("Variáveis de ambiente faltando, pulando notificação.")
        sys.exit(0)

    if _prev_run_also_failed():
        print("Run anterior também falhou, pulando notificação.")
        return

    chat_id = int(chat_ids.split(",")[0].strip())
    text = f"Coleta falhou.\n{run_url}"

    resp = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=10,
    )
    if resp.ok:
        print(f"Notificação enviada para chat {chat_id}.")
    else:
        print(f"Falha ao enviar: {resp.status_code} {resp.text}")


if __name__ == "__main__":
    main()
