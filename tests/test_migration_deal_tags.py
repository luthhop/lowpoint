"""[TESTE] Migração deal_ids/tags em SQLite em memória, sem env.py nem banco real."""

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

MIGRATION = next(Path(__file__).parent.parent.glob("alembic/versions/*_add_offer_deal_ids_tags.py"), None)


def _load():
    assert MIGRATION is not None, "migração *_add_offer_deal_ids_tags.py não existe"
    spec = importlib.util.spec_from_file_location("mig_deal_tags", MIGRATION)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def conn():
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as c:
        c.execute(text(
            "create table offer_snapshots (id integer primary key, item_id varchar not null)"
        ))
        c.execute(text("insert into offer_snapshots (item_id) values ('MLB_ANTIGA')"))
        yield c


def _cols(conn):
    return {c["name"]: c for c in inspect(conn).get_columns("offer_snapshots")}


def test_revision_chain():
    mod = _load()
    assert mod.down_revision == "f4a5b6c7d8e9"


def test_upgrade_adds_nullable_columns_and_old_rows_stay_null(conn):
    mod = _load()
    with Operations.context(MigrationContext.configure(conn)):
        mod.upgrade()
    cols = _cols(conn)
    assert cols["deal_ids"]["nullable"] and cols["tags"]["nullable"]
    assert cols["deal_ids"]["default"] is None and cols["tags"]["default"] is None
    row = conn.execute(text(
        "select deal_ids is null, tags is null from offer_snapshots where item_id='MLB_ANTIGA'"
    )).one()
    assert tuple(row) == (1, 1)


def test_downgrade_removes_columns(conn):
    mod = _load()
    with Operations.context(MigrationContext.configure(conn)):
        mod.upgrade()
        mod.downgrade()
    cols = _cols(conn)
    assert "deal_ids" not in cols and "tags" not in cols
