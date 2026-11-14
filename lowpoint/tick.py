"""Batida externa (/api/tick): dispara a coleta e avisa se ela atrasar.

Um cron externo chama POST /api/tick: de hora em hora fora da BF e a cada
15 min de 23 a 27/11 (poupa o compute do Neon, que acorda a cada batida).
Quem decide se coleta é este módulo:
- 23–27/11 (horário de Brasília): dispara a coleta em toda batida.
- Fora disso: só dispara se a última coleta tiver mais de 25 min.
Independente do disparo, se a última coleta tiver mais de 90 min, manda
aviso no Telegram, no máximo 1 por hora de atraso.

Regra dos 25 min: pular uma batida não pode fazer a seguinte passar do
limite do aviso. Precisa valer OFF_PEAK_MIN_GAP + OFF_PEAK_TICK_PERIOD +
folga (5 min de atraso do cron/coleta) <= STALE_AFTER, ou seja,
25 + 60 + 5 <= 90. Com 55 min (valor pensado para batida de 15 min), a
coleta de reserva do GitHub caindo 5–29 min depois de um dispatch fazia a
batida seguinte pular e a outra avisar com ~1h45 de atraso (11–13/11).
"""

import hmac
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Callable

log = logging.getLogger("lowpoint.tick")

TICK_SECRET_HEADER = "X-Tick-Secret"
BRT = timezone(timedelta(hours=-3))  # Brasil sem horário de verão desde 2019
BF_START = date(2026, 11, 23)
BF_END = date(2026, 11, 27)
OFF_PEAK_MIN_GAP = timedelta(minutes=25)
OFF_PEAK_TICK_PERIOD = timedelta(hours=1)  # cadência do cron externo fora da BF
STALE_AFTER = timedelta(minutes=90)
WARNING_REPEAT = timedelta(hours=1)
STALE_WARNING_KEY = "stale_collect_warning"
DEFAULT_REPO = "luthhop/lowpoint"
WORKFLOW_FILE = "collect.yml"
HTTP_TIMEOUT = (5, 10)


@dataclass
class TickDeps:
    last_collected_at: Callable[[], datetime | None]
    last_warning_at: Callable[[], datetime | None]
    record_warning: Callable[[datetime], None]
    dispatch: Callable[[], bool]
    send_warning: Callable[[str], bool]


def is_valid_tick_secret(header_value: str | None) -> bool:
    expected = os.environ.get("TICK_SECRET", "")
    if not expected or not header_value:
        return False
    return hmac.compare_digest(header_value.encode(), expected.encode())


def in_bf_window(now: datetime) -> bool:
    return BF_START <= now.astimezone(BRT).date() <= BF_END


def should_dispatch(now: datetime, last_collected: datetime | None) -> bool:
    if in_bf_window(now) or last_collected is None:
        return True
    return now - last_collected > OFF_PEAK_MIN_GAP


def _warning_text(now: datetime, last: datetime, dispatched: bool) -> str:
    minutes = int((now - last).total_seconds() // 60)
    hora = last.astimezone(BRT).strftime("%d/%m %H:%M")
    acao = (
        "Disparei uma nova coleta."
        if dispatched
        else "Não disparei coleta nesta batida. Confere o GitHub Actions."
    )
    return (
        f"Coleta atrasada: a última foi há {minutes // 60}h{minutes % 60:02d} "
        f"({hora}). {acao}"
    )


def run_tick(now: datetime, deps: TickDeps) -> dict:
    last = deps.last_collected_at()
    wants_dispatch = should_dispatch(now, last)
    dispatched = deps.dispatch() if wants_dispatch else False

    warned = False
    if last is not None and now - last > STALE_AFTER:
        last_warning = deps.last_warning_at()
        if last_warning is None or now - last_warning >= WARNING_REPEAT:
            if deps.send_warning(_warning_text(now, last, dispatched)):
                deps.record_warning(now)
                warned = True

    log.info(
        "tick: última coleta=%s, disparo=%s/%s, aviso=%s",
        last, wants_dispatch, dispatched, warned,
    )
    status = 502 if wants_dispatch and not dispatched else 200
    return {"statusCode": status, "dispatched": dispatched, "warned": warned}


def handle_tick(
    method: str,
    secret_header: str | None,
    now: datetime | None = None,
    deps: TickDeps | None = None,
) -> dict:
    if method != "POST" or not is_valid_tick_secret(secret_header):
        return {"statusCode": 401}
    if now is None:
        now = datetime.now(timezone.utc)
    try:
        return run_tick(now, deps or default_deps())
    except Exception:
        log.exception("tick falhou")
        return {"statusCode": 500}


# ─── Dependências reais (banco, GitHub, Telegram) ──────────────────────


def default_deps() -> TickDeps:
    import requests
    from sqlalchemy import func

    from lowpoint.db import SessionLocal
    from lowpoint.models import OfferSnapshot, SystemState

    def last_collected_at() -> datetime | None:
        # offer_snapshots só é gravado pelo coletor (o /adicionar grava só price_history).
        with SessionLocal() as s:
            return s.query(func.max(OfferSnapshot.collected_at)).scalar()

    def last_warning_at() -> datetime | None:
        with SessionLocal() as s:
            row = s.get(SystemState, STALE_WARNING_KEY)
            return row.value_at if row else None

    def record_warning(at: datetime) -> None:
        with SessionLocal() as s:
            s.merge(SystemState(key=STALE_WARNING_KEY, value_at=at))
            s.commit()

    def dispatch() -> bool:
        token = os.environ.get("GITHUB_DISPATCH_TOKEN", "")
        if not token:
            log.error("GITHUB_DISPATCH_TOKEN ausente.")
            return False
        repo = os.environ.get("GITHUB_DISPATCH_REPO", DEFAULT_REPO)
        try:
            resp = requests.post(
                f"https://api.github.com/repos/{repo}/actions/workflows/"
                f"{WORKFLOW_FILE}/dispatches",
                json={"ref": "main"},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException:
            log.exception("Falha de rede ao disparar o workflow.")
            return False
        if not resp.ok:
            log.error("workflow_dispatch respondeu HTTP %d.", resp.status_code)
        return resp.ok

    def send_warning(text: str) -> bool:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_ids = os.environ.get("ALLOWED_CHAT_IDS", "")
        if not bot_token or not chat_ids:
            log.error("TELEGRAM_BOT_TOKEN ou ALLOWED_CHAT_IDS ausente.")
            return False
        chat_id = int(chat_ids.split(",")[0].strip())
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
                timeout=HTTP_TIMEOUT,
            )
        except requests.RequestException:
            log.exception("Falha de rede ao avisar no Telegram.")
            return False
        return resp.ok

    return TickDeps(
        last_collected_at=last_collected_at,
        last_warning_at=last_warning_at,
        record_warning=record_warning,
        dispatch=dispatch,
        send_warning=send_warning,
    )
