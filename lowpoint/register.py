"""Register a catalog product and create a watch without the bot.

Usage:
    python -m lowpoint.register --url "https://www.mercadolivre.com.br/.../p/MLB24061510" --target 1200.00
    python -m lowpoint.register --catalog-id MLB24061510 --target 1200.00
"""

import argparse
import re
import sys
from decimal import Decimal, InvalidOperation

from lowpoint.db import SessionLocal
from lowpoint.models import Product, Watch

DEFAULT_CHAT_ID = 0


def extract_catalog_id(url: str) -> str | None:
    match = re.search(r"/p/(MLB\d+)", url)
    return match.group(1) if match else None


def register_product(
    catalog_id: str,
    target_price: Decimal,
    chat_id: int = DEFAULT_CHAT_ID,
) -> tuple[Product, Watch]:
    session = SessionLocal()
    try:
        product = (
            session.query(Product)
            .filter(Product.catalog_product_id == catalog_id)
            .first()
        )
        if not product:
            product = Product(
                catalog_product_id=catalog_id,
                title=f"(pendente — {catalog_id})",
                url=f"https://www.mercadolivre.com.br/p/{catalog_id}",
            )
            session.add(product)
            session.flush()

        watch = (
            session.query(Watch)
            .filter(Watch.chat_id == chat_id, Watch.product_id == product.id)
            .first()
        )
        if watch:
            watch.target_price = target_price
            watch.active = True
        else:
            watch = Watch(
                chat_id=chat_id,
                product_id=product.id,
                target_price=target_price,
            )
            session.add(watch)

        session.commit()
        session.refresh(product)
        session.refresh(watch)
        return product, watch
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Cadastrar produto para monitorar")
    parser.add_argument("--url", help="URL do produto no Mercado Livre (/p/MLB...)")
    parser.add_argument("--catalog-id", help="ID de catálogo (ex: MLB24061510)")
    parser.add_argument("--target", required=True, help="Preço-alvo (ex: 1200.00)")
    parser.add_argument("--chat-id", type=int, default=DEFAULT_CHAT_ID)
    args = parser.parse_args()

    catalog_id = args.catalog_id
    if not catalog_id and args.url:
        catalog_id = extract_catalog_id(args.url)
    if not catalog_id:
        print("Erro: informe --url com link de catálogo (/p/MLB...) ou --catalog-id")
        sys.exit(1)

    try:
        target = Decimal(args.target)
    except InvalidOperation:
        print(f"Erro: preço-alvo inválido: {args.target}")
        sys.exit(1)

    product, watch = register_product(catalog_id, target, args.chat_id)
    print(f"Produto: {product.catalog_product_id} (id={product.id})")
    print(f"Watch:   id={watch.id}, target=R$ {watch.target_price:.2f}, active={watch.active}")


if __name__ == "__main__":
    main()
