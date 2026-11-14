"""Anti-spam por watch: decide se um alerta pode sair, dado o último enviado.

Ordem das regras:
1. Teto geral: no máximo 1 alerta por ALERT_MIN_INTERVAL (1h), qualquer tipo.
2. Sem alerta anterior → envia.
3. Tipo mudou em relação ao último alerta → envia.
4. Mesmo tipo maquiado → só depois de MAQUIADO_REPEAT_INTERVAL (24h).
5. Mesmo tipo real/target_hit (e neutro) → só se o preço estiver pelo menos
   REPEAT_ALERT_MIN_DROP (3%) abaixo do último alerta.

Bordas inclusivas: exatamente 1h, 24h ou 3% liberam o envio.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from lowpoint.config import (
    ALERT_MIN_INTERVAL,
    MAQUIADO_REPEAT_INTERVAL,
    REPEAT_ALERT_MIN_DROP,
)

_KIND_BY_ALERT_TYPE = {
    "verdict_real": "real",
    "target_hit": "target_hit",
    "verdict_maquiado": "maquiado",
    "target_hit_maquiado": "maquiado",
    "neutro": "neutro",
}


@dataclass(frozen=True)
class Decision:
    send: bool
    reason: str


def alert_kind(alert_type: str) -> str:
    """Tipo do alerta para o anti-spam (as duas variantes de maquiado são um tipo só)."""
    return _KIND_BY_ALERT_TYPE.get(alert_type, alert_type)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def should_send(alert_type: str, price: Decimal, now: datetime, last) -> Decision:
    """`last`: último alerta enviado para o watch (alert_type, price_at_alert, sent_at) ou None."""
    if last is None:
        return Decision(True, "primeiro alerta")

    elapsed = _aware(now) - _aware(last.sent_at)
    if elapsed < ALERT_MIN_INTERVAL:
        return Decision(False, "teto de 1 por hora")

    kind = alert_kind(alert_type)
    if kind != alert_kind(last.alert_type):
        return Decision(True, f"tipo mudou ({alert_kind(last.alert_type)} → {kind})")

    if kind == "maquiado":
        if elapsed >= MAQUIADO_REPEAT_INTERVAL:
            return Decision(True, "maquiado de novo após 24h")
        return Decision(False, "maquiado repetido antes de 24h")

    limit = Decimal(str(last.price_at_alert)) * (1 - REPEAT_ALERT_MIN_DROP)
    if price <= limit:
        return Decision(True, "caiu ≥3% desde o último alerta")
    return Decision(False, "não caiu 3% desde o último alerta")
