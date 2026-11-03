"""Price collector: fetches offers from ML catalog and stores in the database.

Usage:
    python -m lowpoint.collect --once          # single cycle
    python -m lowpoint.collect --interval 3600 # every hour (default)
"""

import argparse
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal

from lowpoint.best_offer import select_best_offer
from lowpoint.db import SessionLocal
from lowpoint.models import OfferSnapshot, PriceHistory, Product, Watch
from lowpoint.sources.base import PriceSource
from lowpoint.sources.ml_catalog import MLCatalogSource
from lowpoint.telegram.notify import send_alerts_after_collect

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("lowpoint.collect")


def collect_once(source: PriceSource) -> None:
    session = SessionLocal()
    try:
        products = (
            session.query(Product)
            .join(Watch)
            .filter(Watch.active.is_(True))
            .distinct()
            .all()
        )

        if not products:
            log.info("Nenhum produto com watch ativo.")
            return

        log.info("Coletando %d produto(s)...", len(products))

        for product in products:
            try:
                _collect_product(session, source, product)
            except Exception:
                log.exception("Erro ao coletar %s", product.catalog_product_id)
                session.rollback()

    finally:
        session.close()


def _collect_product(
    session, source: PriceSource, product: Product
) -> None:
    snapshot = source.fetch_catalog(product.catalog_product_id)

    if snapshot.title and product.title.startswith("(pendente"):
        product.title = snapshot.title
    if snapshot.image_url and not product.image_url:
        product.image_url = snapshot.image_url
    product.updated_at = datetime.now(timezone.utc)

    now = snapshot.collected_at

    for offer in snapshot.offers:
        session.add(
            OfferSnapshot(
                product_id=product.id,
                item_id=offer.item_id,
                seller_id=offer.seller_id,
                price=offer.price,
                original_price=offer.original_price,
                condition=offer.condition,
                official_store_id=offer.official_store_id,
                free_shipping=offer.free_shipping,
                warranty=offer.warranty,
                collected_at=now,
            )
        )

    best = select_best_offer(snapshot.offers)

    if best:
        session.add(
            PriceHistory(
                product_id=product.id,
                price=best.offer.price,
                original_price=best.offer.original_price,
                item_id=best.offer.item_id,
                seller_id=best.offer.seller_id,
                available=True,
                collected_at=now,
            )
        )
        log.info(
            "%s | %d ofertas | melhor: R$ %.2f (seller %d, item %s)%s",
            product.catalog_product_id,
            len(snapshot.offers),
            best.offer.price,
            best.offer.seller_id,
            best.offer.item_id,
            " -> " + ", ".join(best.warnings) if best.warnings else "",
        )
    else:
        session.add(
            PriceHistory(
                product_id=product.id,
                price=Decimal("0"),
                original_price=None,
                item_id="",
                seller_id=0,
                available=False,
                collected_at=now,
            )
        )
        log.warning(
            "%s | %d ofertas | nenhuma oferta nova válida",
            product.catalog_product_id,
            len(snapshot.offers),
        )

    session.commit()

    if best:
        try:
            send_alerts_after_collect(best, product)
        except Exception:
            log.exception("Erro ao enviar alertas para %s", product.catalog_product_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Coletor de preços Lowpoint")
    parser.add_argument("--once", action="store_true", help="Rodar um único ciclo")
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Intervalo entre ciclos em segundos (padrão: 3600)",
    )
    args = parser.parse_args()

    source = MLCatalogSource()

    if args.once:
        log.info("Modo --once: um ciclo de coleta.")
        collect_once(source)
        log.info("Coleta finalizada.")
    else:
        log.info("Modo agendado: a cada %ds.", args.interval)
        while True:
            try:
                collect_once(source)
            except Exception:
                log.exception("Erro no ciclo de coleta")
            log.info("Próxima coleta em %ds...", args.interval)
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
