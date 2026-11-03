import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import requests

from lowpoint.best_offer import BestOfferResult, _has_warranty
from lowpoint.db import SessionLocal
from lowpoint.models import Alert, PriceHistory, Product, Watch
from lowpoint.telegram.formatter import AlertContext, AlertMessage, format_alert
from lowpoint.verdict import PricePoint, VerdictResult, compute_verdict

log = logging.getLogger("lowpoint.notify")

_API = "https://api.telegram.org"


def _send_message(
    bot_token: str,
    chat_id: int,
    msg: AlertMessage,
) -> bool:
    payload: dict = {
        "chat_id": chat_id,
        "text": msg.text,
        "parse_mode": msg.parse_mode,
        "reply_markup": {
            "inline_keyboard": [
                [{"text": msg.button_text, "url": msg.button_url}]
            ]
        },
    }
    try:
        resp = requests.post(
            f"{_API}/bot{bot_token}/sendMessage",
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception:
        log.exception("Falha ao enviar alerta para chat %d", chat_id)
        return False


def _should_alert(
    session, watch_id: int, alert_type: str, current_price: Decimal
) -> bool:
    last = (
        session.query(Alert)
        .filter(Alert.watch_id == watch_id, Alert.alert_type == alert_type)
        .order_by(Alert.sent_at.desc())
        .first()
    )
    if last is None:
        return True
    return current_price < last.price_at_alert


def _build_history(session, product_id: int) -> list[PricePoint]:
    rows = (
        session.query(PriceHistory)
        .filter(PriceHistory.product_id == product_id, PriceHistory.available.is_(True))
        .order_by(PriceHistory.collected_at)
        .all()
    )
    return [
        PricePoint(
            price=Decimal(str(r.price)),
            original_price=Decimal(str(r.original_price)) if r.original_price else None,
            collected_at=r.collected_at,
        )
        for r in rows
    ]


def send_alerts_after_collect(best: BestOfferResult, product: Product) -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        return

    session = SessionLocal()
    try:
        watches = (
            session.query(Watch)
            .filter(Watch.product_id == product.id, Watch.active.is_(True))
            .all()
        )
        if not watches:
            return

        history = _build_history(session, product.id)
        price = Decimal(str(best.offer.price))
        original_price = (
            Decimal(str(best.offer.original_price))
            if best.offer.original_price
            else None
        )

        verdict = compute_verdict(price, original_price, history)

        if verdict.verdict == "neutro":
            return

        for watch in watches:
            _process_watch(
                session, bot_token, watch, product, best, verdict, price, original_price,
            )

        session.commit()
    except Exception:
        session.rollback()
        log.exception("Erro ao enviar alertas para %s", product.catalog_product_id)
    finally:
        session.close()


def _process_watch(
    session,
    bot_token: str,
    watch: Watch,
    product: Product,
    best: BestOfferResult,
    verdict: VerdictResult,
    price: Decimal,
    original_price: Decimal | None,
) -> None:
    name = watch.nickname or product.title
    target = Decimal(str(watch.target_price))

    suspects = best.suspect_offers
    cheapest_suspect = (
        min(s.price for s in suspects) if suspects else None
    )

    ctx = AlertContext(
        product_name=name,
        item_id=best.offer.item_id,
        price=price,
        original_price=original_price,
        target_price=target,
        verdict=verdict.verdict,
        reason=verdict.reason,
        lowest_price=verdict.lowest_price,
        median_30d=verdict.median_30d,
        monitoring_days=verdict.monitoring_days,
        pre_hike_price=verdict.pre_hike_price,
        has_warranty=_has_warranty(best.offer.warranty),
        is_official=best.offer.official_store_id is not None,
        suspect_count=len(suspects),
        cheapest_suspect_price=cheapest_suspect,
    )

    msg = format_alert(ctx)

    if not _should_alert(session, watch.id, msg.alert_type, price):
        log.info(
            "Alerta %s suprimido para watch %d (preço não caiu)",
            msg.alert_type, watch.id,
        )
        return

    if _send_message(bot_token, watch.chat_id, msg):
        session.add(
            Alert(
                watch_id=watch.id,
                alert_type=msg.alert_type,
                verdict=verdict.verdict,
                price_at_alert=price,
            )
        )
        log.info(
            "Alerta %s enviado para chat %d (watch %d, R$ %s)",
            msg.alert_type, watch.chat_id, watch.id, price,
        )
