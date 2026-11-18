"""Sugestão de alvo para watch sem alvo (uma vez, depois de 7 dias de histórico).

Regra: alvo = menor preço observado no período (últimos 30 dias), com teto de
95% do preço normal (mediana do período), arredondado para baixo em reais.

- Menor preço já ≥5% abaixo do normal: ele é o alvo, exato. Voltar a ele é
  voltar ao melhor preço visto.
- Menor preço perto do normal (produto estável): o alvo vira 95% do normal,
  para que bater o alvo nunca seja só o preço de sempre. 5% é o mesmo
  REAL_DISCOUNT_THRESHOLD do veredito.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from html import escape
from statistics import median

from lowpoint.config import (
    MEDIAN_WINDOW_DAYS,
    MIN_MONITORING_DAYS,
    REAL_DISCOUNT_THRESHOLD,
)
from lowpoint.telegram.formatter import _dias, fmt_brl
from lowpoint.verdict import PricePoint


@dataclass(frozen=True)
class Suggestion:
    lowest: Decimal
    normal: Decimal
    target: Decimal
    days: int
    capped: bool


def suggest_target(history: list[PricePoint], now: datetime) -> Suggestion | None:
    """`history`: só coletas disponíveis. None antes de MIN_MONITORING_DAYS dias."""
    if not history:
        return None
    days = max((now - min(p.collected_at for p in history)).days, 0)
    if days < MIN_MONITORING_DAYS:
        return None

    cutoff = now - timedelta(days=MEDIAN_WINDOW_DAYS)
    window = [p.price for p in history if p.collected_at >= cutoff] or [
        p.price for p in history
    ]
    lowest = min(window)
    normal = Decimal(str(median(window)))
    cap = Decimal(math.floor(normal * (1 - REAL_DISCOUNT_THRESHOLD)))

    if lowest <= cap:
        return Suggestion(lowest, normal, lowest, days, capped=False)
    return Suggestion(lowest, normal, cap, days, capped=True)


def format_suggestion(name: str, s: Suggestion) -> str:
    pct = math.floor(REAL_DISCOUNT_THRESHOLD * 100)
    if s.capped:
        why = (
            f"Sugiro {fmt_brl(s.target)}, {pct}% abaixo do normal: o menor que vi "
            f"tá perto demais do normal pra ser desconto."
        )
    else:
        why = f"Sugiro {fmt_brl(s.target)}, o menor preço que vi."
    return (
        f"<b>{escape(name)}</b> · {_dias(s.days)} de histórico\n\n"
        f"Menor preço: {fmt_brl(s.lowest)}\n"
        f"Preço normal: {fmt_brl(s.normal)}\n\n"
        f"Quer um alvo? {why} "
        f"Com alvo, também te aviso quando bater, mesmo se não for desconto de verdade."
    )


def suggestion_buttons(watch_id: int, s: Suggestion) -> list[list[dict]]:
    cents = int((s.target * 100).to_integral_value())
    return [[
        {"text": f"Usar {fmt_brl(s.target)}", "callback_data": f"alvo:{watch_id}:{cents}"},
        {"text": "Agora não", "callback_data": f"alvo_nao:{watch_id}"},
    ]]
