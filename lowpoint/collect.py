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

from sqlalchemy import func
from statistics import median as _median

from lowpoint.best_offer import select_best_offer
from lowpoint.db import SessionLocal
from lowpoint.models import OfferSnapshot, PriceHistory, Product, Watch
from lowpoint.sources.base import PriceSource
from lowpoint.sources.ml_catalog import MLCatalogSource
from lowpoint.telegram.notify import send_alerts_after_collect

ANOMALY_THRESHOLD = Decimal("0.30")
ANOMALY_MIN_COLLECTIONS = 3

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
        if hasattr(source, "call_count"):
            source.call_count = 0

        for product in products:
            try:
                _collect_product(session, source, product)
            except Exception:
                log.exception("Erro ao coletar %s", product.catalog_product_id)
                session.rollback()

        calls = getattr(source, "call_count", None)
        if calls is not None:
            log.info(
                "Chamadas HTTP ao ML nesta execução: %d (%d produto(s)).",
                calls, len(products),
            )

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

    hist_prices = [
        Decimal(str(r.price))
        for r in session.query(PriceHistory.price).filter(
            PriceHistory.product_id == product.id,
            PriceHistory.available.is_(True),
        ).all()
    ]
    hist_median = _median(hist_prices) if hist_prices else None

    best = select_best_offer(snapshot.offers, historical_median=hist_median)

    current_count = len(snapshot.offers)
    anomalous = _is_anomalous_collection(session, product.id, current_count)

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
            current_count,
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
            current_count,
        )

    session.commit()

    if anomalous:
        log.warning(
            "Coleta anômala para %s: %d ofertas (muito abaixo do normal). "
            "Dados gravados, alertas suprimidos.",
            product.catalog_product_id, current_count,
        )
    elif best:
        try:
            send_alerts_after_collect(best, product, offer_count=current_count)
        except Exception:
            log.exception("Erro ao enviar alertas para %s", product.catalog_product_id)


def _is_anomalous_collection(
    session, product_id: int, current_count: int
) -> bool:
    recent = (
        session.query(func.count(OfferSnapshot.id))
        .filter(OfferSnapshot.product_id == product_id)
        .group_by(OfferSnapshot.collected_at)
        .order_by(OfferSnapshot.collected_at.desc())
        .limit(10)
        .all()
    )
    counts = [row[0] for row in recent]
    if len(counts) < ANOMALY_MIN_COLLECTIONS:
        return False
    avg = _median(counts)
    if avg <= 0:
        return False
    return Decimal(str(current_count)) < Decimal(str(avg)) * ANOMALY_THRESHOLD


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
