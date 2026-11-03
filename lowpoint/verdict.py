from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from statistics import median

from lowpoint.config import (
    HIKE_THRESHOLD,
    INFLATED_ORIGINAL_THRESHOLD,
    MEDIAN_WINDOW_DAYS,
    MIN_MONITORING_DAYS,
    PRICE_HIKE_WINDOW_DAYS,
    REAL_DISCOUNT_THRESHOLD,
)


@dataclass(frozen=True)
class PricePoint:
    price: Decimal
    original_price: Decimal | None
    collected_at: datetime


@dataclass(frozen=True)
class VerdictResult:
    verdict: str  # "real", "maquiado", "neutro"
    current_price: Decimal
    lowest_price: Decimal | None
    median_30d: Decimal | None
    monitoring_days: int
    reason: str
    pre_hike_price: Decimal | None = None


def compute_verdict(
    current_price: Decimal,
    original_price: Decimal | None,
    history: list[PricePoint],
    now: datetime | None = None,
    *,
    min_monitoring_days: int = MIN_MONITORING_DAYS,
    median_window_days: int = MEDIAN_WINDOW_DAYS,
    hike_window_days: int = PRICE_HIKE_WINDOW_DAYS,
    real_discount_threshold: Decimal = REAL_DISCOUNT_THRESHOLD,
    hike_threshold: Decimal = HIKE_THRESHOLD,
    inflated_original_threshold: Decimal = INFLATED_ORIGINAL_THRESHOLD,
) -> VerdictResult:
    if now is None:
        now = datetime.now(timezone.utc)

    available = [p for p in history if p.price > 0]

    if not available:
        return VerdictResult(
            verdict="neutro",
            current_price=current_price,
            lowest_price=None,
            median_30d=None,
            monitoring_days=0,
            reason="sem histórico de preço",
        )

    earliest = min(p.collected_at for p in available)
    monitoring_days = max((now - earliest).days, 0)

    if monitoring_days < min_monitoring_days:
        lowest = min(p.price for p in available)
        return VerdictResult(
            verdict="neutro",
            current_price=current_price,
            lowest_price=lowest,
            median_30d=None,
            monitoring_days=monitoring_days,
            reason=f"menor preço em {'1 dia' if monitoring_days == 1 else f'{monitoring_days} dias'} de monitoramento",
        )

    lowest_price = min(p.price for p in available)

    cutoff_30d = now - timedelta(days=median_window_days)
    prices_30d = [p.price for p in available if p.collected_at >= cutoff_30d]
    median_30d = median(prices_30d) if prices_30d else median([p.price for p in available])

    period_label = (
        ("1 dia" if monitoring_days == 1 else f"{monitoring_days} dias")
        if monitoring_days < 90
        else "90 dias"
    )

    hike_result = _detect_hike(
        available, now, hike_window_days, hike_threshold
    )

    if hike_result is not None:
        return VerdictResult(
            verdict="maquiado",
            current_price=current_price,
            lowest_price=lowest_price,
            median_30d=median_30d,
            monitoring_days=monitoring_days,
            reason=(
                f"preço subiu {hike_result.pct_increase:.0%} nos últimos "
                f"{hike_window_days} dias antes da queda atual "
                f"(era R$ {hike_result.pre_hike_price:.2f})"
            ),
            pre_hike_price=hike_result.pre_hike_price,
        )

    if original_price is not None and median_30d > 0:
        if original_price > median_30d * inflated_original_threshold:
            return VerdictResult(
                verdict="maquiado",
                current_price=current_price,
                lowest_price=lowest_price,
                median_30d=median_30d,
                monitoring_days=monitoring_days,
                reason=(
                    f"preço 'de' R$ {original_price:.2f} está inflado — "
                    f"mediana dos últimos {median_window_days} dias é "
                    f"R$ {median_30d:.2f} (período: {period_label})"
                ),
            )

    if median_30d > 0:
        real_discount = (median_30d - current_price) / median_30d
        if (
            real_discount >= real_discount_threshold
            and current_price <= lowest_price
        ):
            return VerdictResult(
                verdict="real",
                current_price=current_price,
                lowest_price=lowest_price,
                median_30d=median_30d,
                monitoring_days=monitoring_days,
                reason=(
                    f"desconto real de {real_discount:.0%} vs. mediana — "
                    f"menor preço em {period_label}"
                ),
            )

    return VerdictResult(
        verdict="neutro",
        current_price=current_price,
        lowest_price=lowest_price,
        median_30d=median_30d,
        monitoring_days=monitoring_days,
        reason=f"preço dentro da faixa normal ({period_label} de dados)",
    )


@dataclass(frozen=True)
class _HikeDetection:
    pre_hike_price: Decimal
    pct_increase: Decimal


def _detect_hike(
    history: list[PricePoint],
    now: datetime,
    hike_window_days: int,
    hike_threshold: Decimal,
) -> _HikeDetection | None:
    hike_start = now - timedelta(days=hike_window_days)
    before_window = [p for p in history if p.collected_at < hike_start]
    in_window = [p for p in history if p.collected_at >= hike_start]

    if not before_window or not in_window:
        return None

    pre_hike_price = median([p.price for p in before_window])
    peak_in_window = max(p.price for p in in_window)

    if pre_hike_price > 0:
        pct_increase = (peak_in_window - pre_hike_price) / pre_hike_price
        if pct_increase > hike_threshold:
            return _HikeDetection(
                pre_hike_price=pre_hike_price,
                pct_increase=pct_increase,
            )

    return None
