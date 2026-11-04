"""Recalcula price_history a partir de offer_snapshots com a regra atualizada de best_offer."""
import argparse
import sys

sys.path.insert(0, ".")

from decimal import Decimal
from statistics import median as _median

from lowpoint.best_offer import select_best_offer
from lowpoint.db import SessionLocal
from lowpoint.models import OfferSnapshot, PriceHistory
from lowpoint.sources.base import OfferData


def recalculate(dry_run: bool = False) -> None:
    session = SessionLocal()
    try:
        collections = (
            session.query(
                OfferSnapshot.product_id,
                OfferSnapshot.collected_at,
            )
            .distinct()
            .order_by(OfferSnapshot.product_id, OfferSnapshot.collected_at)
            .all()
        )

        prior_prices: dict[int, list[Decimal]] = {}
        updated = 0
        for product_id, collected_at in collections:
            snapshots = (
                session.query(OfferSnapshot)
                .filter_by(product_id=product_id, collected_at=collected_at)
                .all()
            )

            offers = [
                OfferData(
                    item_id=s.item_id,
                    seller_id=s.seller_id,
                    price=s.price,
                    original_price=s.original_price,
                    condition=s.condition,
                    official_store_id=s.official_store_id,
                    free_shipping=s.free_shipping,
                    warranty=s.warranty,
                )
                for s in snapshots
            ]

            prices_so_far = prior_prices.get(product_id, [])
            hist_median = _median(prices_so_far) if prices_so_far else None

            best = select_best_offer(offers, historical_median=hist_median)

            ph = (
                session.query(PriceHistory)
                .filter_by(product_id=product_id, collected_at=collected_at)
                .first()
            )

            if best and ph:
                if ph.price != best.offer.price or ph.item_id != best.offer.item_id:
                    old_price, old_item = ph.price, ph.item_id
                    if not dry_run:
                        ph.price = best.offer.price
                        ph.original_price = best.offer.original_price
                        ph.item_id = best.offer.item_id
                        ph.seller_id = best.offer.seller_id
                        ph.available = True
                    updated += 1
                    print(
                        f"  {product_id} @ {collected_at}: "
                        f"R$ {old_price} ({old_item}) -> "
                        f"R$ {best.offer.price} ({best.offer.item_id})"
                    )
                    if best.warnings:
                        print(f"    avisos: {', '.join(best.warnings)}")
                if ph.available:
                    prior_prices.setdefault(product_id, []).append(
                        Decimal(str(ph.price if dry_run else best.offer.price))
                    )
            elif best and not ph:
                if not dry_run:
                    session.add(
                        PriceHistory(
                            product_id=product_id,
                            price=best.offer.price,
                            original_price=best.offer.original_price,
                            item_id=best.offer.item_id,
                            seller_id=best.offer.seller_id,
                            available=True,
                            collected_at=collected_at,
                        )
                    )
                updated += 1
                print(f"  {product_id} @ {collected_at}: CRIADO R$ {best.offer.price}")
                prior_prices.setdefault(product_id, []).append(best.offer.price)
            elif not best and ph and ph.available:
                if not dry_run:
                    ph.price = Decimal("0")
                    ph.original_price = None
                    ph.item_id = ""
                    ph.seller_id = 0
                    ph.available = False
                updated += 1
                print(f"  {product_id} @ {collected_at}: -> indisponivel")
            else:
                if ph and ph.available:
                    prior_prices.setdefault(product_id, []).append(
                        Decimal(str(ph.price))
                    )

        if not dry_run:
            session.commit()

        mode = "DRY RUN" if dry_run else "APLICADO"
        print(
            f"\n[{mode}] {updated} registro(s) alterado(s) "
            f"de {len(collections)} coleta(s)."
        )

    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Recalcula price_history com a regra atualizada"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Mostra mudancas sem aplicar"
    )
    args = parser.parse_args()
    recalculate(dry_run=args.dry_run)
