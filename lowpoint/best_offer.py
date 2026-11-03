from dataclasses import dataclass
from decimal import Decimal
from statistics import median as _median

from lowpoint.sources.base import OfferData


def _has_warranty(warranty: str | None) -> bool:
    return bool(warranty) and warranty.lower() != "sem garantia"


@dataclass(frozen=True)
class BestOfferResult:
    offer: OfferData
    available: bool
    warnings: list[str]
    suspect_offers: list[OfferData]


def select_best_offer(
    offers: list[OfferData],
    *,
    require_warranty: bool = False,
    suspect_threshold: Decimal = Decimal("0.60"),
) -> BestOfferResult | None:
    new_offers = [o for o in offers if o.condition == "new"]
    if not new_offers:
        return None

    # >= 3 ofertas para mediana ter significado estatístico
    suspect_offers: list[OfferData] = []
    if len(new_offers) >= 3:
        med = _median([o.price for o in new_offers])
        cutoff = med * suspect_threshold
        suspect_offers = [o for o in new_offers if o.price < cutoff]

    eligible = [o for o in new_offers if o not in suspect_offers]
    if not eligible:
        return None

    if require_warranty:
        with_warranty = [o for o in eligible if _has_warranty(o.warranty)]
        if with_warranty:
            eligible = with_warranty

    best = min(
        eligible,
        key=lambda o: (
            o.price,
            0 if _has_warranty(o.warranty) else 1,
            0 if o.official_store_id is not None else 1,
        ),
    )

    warnings: list[str] = []
    if best.official_store_id is None:
        warnings.append("oferta de vendedor não-oficial")
    if not _has_warranty(best.warranty):
        warnings.append("oferta sem garantia informada")
    if suspect_offers:
        warnings.append(
            f"{len(suspect_offers)} oferta(s) suspeita(s) descartada(s) "
            f"(preço muito abaixo da mediana)"
        )

    return BestOfferResult(
        offer=best,
        available=True,
        warnings=warnings,
        suspect_offers=suspect_offers,
    )
