import json
import logging
import re
from decimal import Decimal, InvalidOperation

from lowpoint.db import SessionLocal
from lowpoint.models import PriceHistory, Product, Watch
from lowpoint.register import extract_catalog_id, register_product
from lowpoint.telegram.formatter import fmt_brl
from lowpoint.telegram.security import (
    UNAUTHORIZED_MESSAGE,
    is_chat_allowed,
    validate_secret_token,
)

log = logging.getLogger("lowpoint.webhook")

_MAX_WATCHES_PER_CHAT = 20


def handle_update(update: dict, secret_header: str | None) -> dict:
    if not validate_secret_token(secret_header):
        return {"statusCode": 403}

    message = update.get("message")
    callback = update.get("callback_query")

    if callback:
        return _handle_callback(callback)
    if not message:
        return {"statusCode": 200}

    chat_id = message.get("chat", {}).get("id")
    text = (message.get("text") or "").strip()

    if not chat_id or not text:
        return {"statusCode": 200}

    if not is_chat_allowed(chat_id):
        return _reply(chat_id, UNAUTHORIZED_MESSAGE)

    if text.startswith("/adicionar"):
        return _cmd_adicionar(chat_id, text)
    if text.startswith("/lista"):
        return _cmd_lista(chat_id)
    if text.startswith("/remover"):
        return _cmd_remover(chat_id)
    if text.startswith("/start"):
        return _reply(chat_id, "Lowpoint. Manda /lista pra ver teus produtos.")

    return {"statusCode": 200}


def _reply(chat_id: int, text: str, **extra) -> dict:
    body: dict = {
        "method": "sendMessage",
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    body.update(extra)
    return body


def _cmd_adicionar(chat_id: int, text: str) -> dict:
    parts = text.split(maxsplit=3)
    if len(parts) < 3:
        return _reply(
            chat_id,
            "Uso: /adicionar <link> <alvo> [apelido]\n\n"
            "Exemplo:\n"
            "/adicionar mercadolivre.com.br/p/MLB57081243 3500 PS5",
        )

    url_arg = parts[1]
    if not url_arg.startswith("http"):
        url_arg = "https://" + url_arg

    catalog_id = extract_catalog_id(url_arg)
    if not catalog_id:
        return _reply(
            chat_id,
            "Esse link não é de produto de catálogo do Mercado Livre.\n\n"
            "Preciso de um link assim:\n"
            "mercadolivre.com.br/p/MLB12345678",
        )

    try:
        target = Decimal(parts[2].replace(",", "."))
        if target <= 0:
            raise InvalidOperation
    except (InvalidOperation, ArithmeticError):
        return _reply(chat_id, f"Preço-alvo inválido: {parts[2]}")

    nickname = parts[3].strip() if len(parts) > 3 else None

    session = SessionLocal()
    try:
        count = (
            session.query(Watch)
            .filter(Watch.chat_id == chat_id, Watch.active.is_(True))
            .count()
        )
        if count >= _MAX_WATCHES_PER_CHAT:
            return _reply(chat_id, f"Limite de {_MAX_WATCHES_PER_CHAT} produtos atingido.")
    finally:
        session.close()

    product, watch = register_product(catalog_id, target, chat_id)

    if nickname:
        session = SessionLocal()
        try:
            w = session.query(Watch).get(watch.id)
            w.nickname = nickname
            session.commit()
        finally:
            session.close()

    display_name = nickname or product.title
    if display_name.startswith("(pendente"):
        display_name = catalog_id

    return _reply(
        chat_id,
        f"Pronto. Monitorando:\n\n"
        f"<b>{display_name}</b>\n"
        f"Alvo: {fmt_brl(target)}\n"
        f"Coleta a cada hora. Te aviso quando chegar lá.",
    )


def _cmd_lista(chat_id: int) -> dict:
    session = SessionLocal()
    try:
        watches = (
            session.query(Watch)
            .join(Product)
            .filter(Watch.chat_id == chat_id, Watch.active.is_(True))
            .order_by(Watch.created_at)
            .all()
        )
        if not watches:
            return _reply(chat_id, "Nenhum produto monitorado. Usa /adicionar pra começar.")

        lines = ["Teus produtos:\n"]
        for i, w in enumerate(watches, 1):
            name = w.nickname or w.product.title
            target = fmt_brl(Decimal(str(w.target_price)))

            last = (
                session.query(PriceHistory)
                .filter(
                    PriceHistory.product_id == w.product_id,
                    PriceHistory.available.is_(True),
                )
                .order_by(PriceHistory.collected_at.desc())
                .first()
            )
            price_str = fmt_brl(Decimal(str(last.price))) if last else "—"

            days = (
                (last.collected_at - w.created_at).days
                if last
                else 0
            )
            lines.append(
                f"{i}. <b>{name}</b>\n"
                f"   Agora: {price_str} · Alvo: {target}\n"
                f"   Monitorando há {days} dias"
            )

        return _reply(chat_id, "\n".join(lines))
    finally:
        session.close()


def _cmd_remover(chat_id: int) -> dict:
    session = SessionLocal()
    try:
        watches = (
            session.query(Watch)
            .join(Product)
            .filter(Watch.chat_id == chat_id, Watch.active.is_(True))
            .order_by(Watch.created_at)
            .all()
        )
        if not watches:
            return _reply(chat_id, "Nenhum produto pra remover.")

        buttons = []
        for i, w in enumerate(watches, 1):
            name = w.nickname or w.product.title
            buttons.append(
                [{"text": f"{i}. {name}", "callback_data": f"rm:{w.id}"}]
            )

        return _reply(
            chat_id,
            "Qual produto quer remover?",
            reply_markup={"inline_keyboard": buttons},
        )
    finally:
        session.close()


def _handle_callback(callback: dict) -> dict:
    data = callback.get("data", "")
    chat_id = callback.get("message", {}).get("chat", {}).get("id")
    callback_id = callback.get("id")

    if not chat_id or not is_chat_allowed(chat_id):
        return {"method": "answerCallbackQuery", "callback_query_id": callback_id}

    if data.startswith("rm:"):
        return _do_remove(chat_id, callback_id, data)

    return {"method": "answerCallbackQuery", "callback_query_id": callback_id}


def _do_remove(chat_id: int, callback_id: str, data: str) -> dict:
    try:
        watch_id = int(data.split(":")[1])
    except (IndexError, ValueError):
        return {"method": "answerCallbackQuery", "callback_query_id": callback_id}

    session = SessionLocal()
    try:
        watch = (
            session.query(Watch)
            .filter(
                Watch.id == watch_id,
                Watch.chat_id == chat_id,
                Watch.active.is_(True),
            )
            .first()
        )
        if not watch:
            return _reply(chat_id, "Produto já removido ou não encontrado.")

        name = watch.nickname or watch.product.title
        watch.active = False
        session.commit()

        return _reply(chat_id, f"Removido: <b>{name}</b>")
    except Exception:
        session.rollback()
        return _reply(chat_id, "Erro ao remover. Tenta de novo.")
    finally:
        session.close()
