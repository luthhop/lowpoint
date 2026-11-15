"""Exporta do Neon, numa transação READ ONLY, só o que a análise usa.

Grava parquet local em analysis/output/data/. Só os 20 produtos do
pré-registro e só até o corte (08/12 00:00 BRT). Sem seller_id.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from analysis import prereg

_PRICE_SQL = """
select p.catalog_product_id, h.price, h.original_price, h.available, h.collected_at
from price_history h join products p on p.id = h.product_id
where p.catalog_product_id = any(:ids) and h.collected_at < :cutoff
order by p.catalog_product_id, h.collected_at
"""
_OFFERS_SQL = """
select p.catalog_product_id, s.item_id, s.price, s.original_price, s.collected_at,
       s.deal_ids, s.tags
from offer_snapshots s join products p on p.id = s.product_id
where p.catalog_product_id = any(:ids) and s.collected_at < :cutoff
order by p.catalog_product_id, s.collected_at
"""


def export(out_dir: Path) -> dict:
    from lowpoint.db import engine  # importa só aqui: testes não tocam no banco

    out_dir.mkdir(parents=True, exist_ok=True)
    params = {"ids": [p.catalog_id for p in prereg.PRODUCTS], "cutoff": prereg.CUTOFF}
    with engine.connect() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        read_only = conn.execute(text("SHOW transaction_read_only")).scalar()
        if read_only != "on":
            raise RuntimeError("transação não está READ ONLY; exportação abortada")
        prices = pd.read_sql(text(_PRICE_SQL), conn, params=params)
        offers = pd.read_sql(text(_OFFERS_SQL), conn, params=params)
        conn.rollback()

    prices.to_parquet(out_dir / "price_history.parquet", index=False)
    offers.to_parquet(out_dir / "offers.parquet", index=False)
    meta = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "read_only": read_only,
        "price_history_rows": len(prices),
        "offer_rows": len(offers),
        "cutoff": prereg.CUTOFF.isoformat(),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return meta
