"""notify.py: watches silenciosos, anti-spam ligado ao banco e replay de um dia de BF."""

from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lowpoint.antispam import alert_kind
from lowpoint.best_offer import BestOfferResult
from lowpoint.models import Alert, Base, PriceHistory, Product, Watch
from lowpoint.sources.base import OfferData
from lowpoint.telegram import notify
from lowpoint.verdict import VerdictResult

NOW = datetime(2026, 11, 27, 15, 0, tzinfo=timezone.utc)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    # notify fecha a sessão a cada chamada; aqui a mesma sessão em memória é
    # reaproveitada entre coletas, então o close vira no-op durante o teste.
    with patch.object(session, "close"):
        yield session
    session.close()


@pytest.fixture(autouse=True)
def _token(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")


def _offer(price: str) -> OfferData:
    return OfferData(
        item_id="MLB999", seller_id=1, price=Decimal(price), original_price=None,
        condition="new", official_store_id=1, free_shipping=True, warranty="12 meses",
    )


def _best(price: str) -> BestOfferResult:
    return BestOfferResult(offer=_offer(price), available=True, warnings=[], suspect_offers=[])


def _seed(session, catalog_id="MLB1", *, target="1000", silent=False, chat_id=100):
    product = Product(catalog_product_id=catalog_id, title=f"Produto {catalog_id}",
                      url=f"https://www.mercadolivre.com.br/p/{catalog_id}")
    session.add(product)
    session.flush()
    watch = Watch(chat_id=chat_id, product_id=product.id,
                  target_price=Decimal(target), silent=silent)
    session.add(watch)
    session.commit()
    return product, watch


def _verdict(kind: str, price: str) -> VerdictResult:
    p = Decimal(price)
    return VerdictResult(
        verdict=kind, current_price=p, lowest_price=p, median_30d=Decimal("1000"),
        monitoring_days=30, reason="teste", baseline_price=Decimal("1000"),
    )


class TestSilentWatch:
    @pytest.mark.parametrize("verdict,price", [
        ("real", "900"),       # verdict_real (alvo 500 não bate)
        ("real", "400"),       # target_hit com real
        ("maquiado", "1200"),  # verdict_maquiado
        ("maquiado", "400"),   # target_hit_maquiado
        ("neutro", "400"),     # target_hit com neutro
    ])
    def test_silent_never_alerts(self, db_session, verdict, price):
        product, watch = _seed(db_session, target="500", silent=True)
        with (
            patch.object(notify, "SessionLocal", return_value=db_session),
            patch.object(notify, "compute_verdict", return_value=_verdict(verdict, price)),
            patch.object(notify, "_send_message", return_value=True) as send,
        ):
            notify.send_alerts_after_collect(_best(price), product, now=NOW)
        send.assert_not_called()
        assert db_session.query(Alert).count() == 0

    @pytest.mark.parametrize("verdict,price", [
        ("real", "900"), ("real", "400"), ("maquiado", "1200"),
        ("maquiado", "400"), ("neutro", "400"),
    ])
    def test_same_cases_alert_when_not_silent(self, db_session, verdict, price):
        product, _ = _seed(db_session, target="500", silent=False)
        with (
            patch.object(notify, "SessionLocal", return_value=db_session),
            patch.object(notify, "compute_verdict", return_value=_verdict(verdict, price)),
            patch.object(notify, "_send_message", return_value=True) as send,
        ):
            notify.send_alerts_after_collect(_best(price), product, now=NOW)
        send.assert_called_once()

    def test_silent_and_normal_on_same_product(self, db_session):
        product, silent = _seed(db_session, target="500", silent=True, chat_id=100)
        normal = Watch(chat_id=200, product_id=product.id, target_price=Decimal("500"))
        db_session.add(normal)
        db_session.commit()
        normal_id = normal.id
        with (
            patch.object(notify, "SessionLocal", return_value=db_session),
            patch.object(notify, "compute_verdict", return_value=_verdict("real", "400")),
            patch.object(notify, "_send_message", return_value=True) as send,
        ):
            notify.send_alerts_after_collect(_best("400"), product, now=NOW)
        assert send.call_count == 1
        assert send.call_args.args[1] == 200
        assert [a.watch_id for a in db_session.query(Alert)] == [normal_id]

    def test_silent_watch_still_collected(self, db_session):
        """Coleta e histórico continuam iguais para watch silencioso."""
        from datetime import datetime as dt

        from lowpoint.collect import collect_once
        from lowpoint.sources.base import CatalogSnapshot
        from lowpoint.sources.mock import MockSource

        product, _ = _seed(db_session, "MLB_SILENT", target="1", silent=True)
        src = MockSource()
        src.set_response("MLB_SILENT", CatalogSnapshot(
            catalog_product_id="MLB_SILENT", title="X", image_url=None,
            offers=[_offer("100")], collected_at=dt(2026, 11, 20, tzinfo=timezone.utc),
        ))
        with (
            patch("lowpoint.collect.SessionLocal", return_value=db_session),
            patch.object(notify, "SessionLocal", return_value=db_session),
            patch.object(notify, "_send_message", return_value=True) as send,
        ):
            collect_once(src)
        assert db_session.query(PriceHistory).filter_by(product_id=product.id).count() == 1
        send.assert_not_called()


class TestAntiSpamWiring:
    def _run(self, db_session, product, verdict, price, now):
        with (
            patch.object(notify, "SessionLocal", return_value=db_session),
            patch.object(notify, "compute_verdict", return_value=_verdict(verdict, price)),
            patch.object(notify, "_send_message", return_value=True) as send,
        ):
            notify.send_alerts_after_collect(_best(price), product, now=now)
        return send.call_count

    def test_records_sent_at_from_now(self, db_session):
        product, _ = _seed(db_session, target="500")
        assert self._run(db_session, product, "real", "900", NOW) == 1
        alert = db_session.query(Alert).one()
        assert alert.sent_at.replace(tzinfo=timezone.utc) == NOW

    def test_hourly_cap_across_types(self, db_session):
        product, _ = _seed(db_session, target="500")
        assert self._run(db_session, product, "maquiado", "1200", NOW) == 1
        assert self._run(db_session, product, "real", "900", NOW + timedelta(minutes=45)) == 0
        assert self._run(db_session, product, "real", "900", NOW + timedelta(hours=1)) == 1

    def test_maquiado_once_per_24h(self, db_session):
        product, _ = _seed(db_session, target="500")
        assert self._run(db_session, product, "maquiado", "1200", NOW) == 1
        assert self._run(db_session, product, "maquiado", "1100", NOW + timedelta(hours=5)) == 0
        assert self._run(db_session, product, "maquiado", "1100", NOW + timedelta(hours=24)) == 1

    def test_failed_send_is_not_recorded(self, db_session):
        product, _ = _seed(db_session, target="500")
        with (
            patch.object(notify, "SessionLocal", return_value=db_session),
            patch.object(notify, "compute_verdict", return_value=_verdict("real", "900")),
            patch.object(notify, "_send_message", return_value=False),
        ):
            notify.send_alerts_after_collect(_best("900"), product, now=NOW)
        assert db_session.query(Alert).count() == 0


# ---------------------------------------------------------------- replay BF

# Brasília = UTC-3. Dia da BF: 27/11 00:00–23:45 BRT, coleta a cada 15 min.
BF_START = datetime(2026, 11, 27, 3, 0, tzinfo=timezone.utc)
NORMAL = ["1000", "1010", "995", "1005", "990"]      # ±1% em torno de 1000
PICO = ["1300", "1313", "1295", "1305", "1287"]      # +30%, ±1%
QUEDA = ["900", "909", "895", "905", "891"]          # -10% do normal, ±1%
REPLAY_WATCHES = {"A": "950", "B": "500", "C": "1005"}  # alvos


def _bf_prices() -> list[tuple[datetime, Decimal]]:
    out = []
    for step in range(96):
        ts = BF_START + timedelta(minutes=15 * step)
        if step < 24:      # 00:00–05:45
            seq = NORMAL
        elif step < 48:    # 06:00–11:45 pico
            seq = PICO
        else:              # 12:00–23:45 queda real
            seq = QUEDA
        out.append((ts, Decimal(seq[step % 5])))
    return out


def _legacy_should_alert(session, watch_id, alert_type, current_price, now):
    """Regra antiga: mesmo alert_type só reenvia se o preço cair abaixo do último."""
    last = (
        session.query(Alert)
        .filter(Alert.watch_id == watch_id, Alert.alert_type == alert_type)
        .order_by(Alert.sent_at.desc())
        .first()
    )
    send = last is None or current_price < Decimal(str(last.price_at_alert))
    return notify.Decision(send, "regra antiga")


def _replay(db_session, *, legacy: bool) -> dict[str, list[tuple[datetime, str]]]:
    products = {}
    for name, target in REPLAY_WATCHES.items():
        product, watch = _seed(db_session, f"MLB_{name}", target=target)
        products[name] = (product, watch.id)
        # 30 dias de histórico horário em ~1000 (±1%) antes da BF
        ts = BF_START - timedelta(days=30)
        i = 0
        while ts < BF_START:
            db_session.add(PriceHistory(
                product_id=product.id, price=Decimal(NORMAL[i % 5]), original_price=None,
                item_id="MLB999", seller_id=1, available=True, collected_at=ts,
            ))
            ts += timedelta(hours=1)
            i += 1
    # um watch silencioso no mesmo produto A, para provar que fica quieto no replay
    silent = Watch(chat_id=300, product_id=products["A"][0].id,
                   target_price=Decimal("5000"), silent=True)
    db_session.add(silent)
    db_session.commit()
    silent_id = silent.id

    patches = [
        patch.object(notify, "SessionLocal", return_value=db_session),
        patch.object(notify, "_send_message", return_value=True),
    ]
    if legacy:
        patches.append(patch.object(notify, "_should_alert", side_effect=_legacy_should_alert))
    for p in patches:
        p.start()
    try:
        for ts, price in _bf_prices():
            for product, _ in products.values():
                db_session.add(PriceHistory(
                    product_id=product.id, price=price, original_price=None,
                    item_id="MLB999", seller_id=1, available=True, collected_at=ts,
                ))
                db_session.commit()
                notify.send_alerts_after_collect(_best(str(price)), product, now=ts)
    finally:
        for p in patches:
            p.stop()

    by_watch: dict[str, list[tuple[datetime, str]]] = {}
    id_to_name = {wid: name for name, (_, wid) in products.items()}
    id_to_name[silent_id] = "silencioso"
    for a in db_session.query(Alert).order_by(Alert.sent_at):
        by_watch.setdefault(id_to_name[a.watch_id], []).append(
            (a.sent_at.replace(tzinfo=timezone.utc), a.alert_type)
        )
    return by_watch


def _print_replay(label, result):
    total = sum(len(v) for v in result.values())
    print(f"\n[TESTE] replay BF — regra {label}: {total} alertas")
    for name in [*REPLAY_WATCHES, "silencioso"]:
        alerts = result.get(name, [])
        kinds = Counter(t for _, t in alerts)
        brt = [f"{(ts - timedelta(hours=3)):%H:%M} {t}" for ts, t in alerts]
        print(f"  watch {name}: {len(alerts):>3}  {dict(kinds)}")
        for line in brt:
            print(f"      {line}")
    return total


class TestReplayBlackFriday:
    def test_replay_old_vs_new(self, db_session):
        old = _replay(db_session, legacy=True)
        db_session.query(Alert).delete()
        db_session.query(PriceHistory).delete()
        db_session.query(Watch).delete()
        db_session.query(Product).delete()
        db_session.commit()
        new = _replay(db_session, legacy=False)

        old_total = _print_replay("antiga", old)
        new_total = _print_replay("nova", new)

        assert "silencioso" not in old and "silencioso" not in new
        assert new_total < old_total
        for alerts in new.values():
            for (t1, _), (t2, _) in zip(alerts, alerts[1:]):
                assert t2 - t1 >= timedelta(hours=1)
            maq = [ts for ts, t in alerts if alert_kind(t) == "maquiado"]
            assert len(maq) <= 1  # um dia só: no máximo 1 maquiado
