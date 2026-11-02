from dataclasses import dataclass
from decimal import Decimal

from lowpoint.sources.base import OfferData


@dataclass(frozen=True)
class BestOfferResult:
    offer: OfferData
    available: bool
    warnings: list[str]


def select_best_offer(
    offers: list[OfferData],
    *,
    require_warranty: bool = False,
    prefer_official_store: bool = True,
) -> BestOfferResult | None:
    new_offers = [o for o in offers if o.condition == "new"]
    if not new_offers:
        return None

    if require_warranty:
        with_warranty = [o for o in new_offers if o.warranty]
        if with_warranty:
            new_offers = with_warranty

    if prefer_official_store:
        official = [o for o in new_offers if o.official_store_id is not None]
        if official:
            new_offers = official

    best = min(new_offers, key=lambda o: o.price)

    warnings: list[str] = []
    if not best.warranty:
        warnings.append("oferta sem garantia informada")

    return BestOfferResult(
        offer=best,
        available=True,
        warnings=warnings,
    )
