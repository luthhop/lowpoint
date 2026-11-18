"""[TESTE] /adicionar <link> [alvo] [apelido], watches sem alvo e sugestão de alvo.

Tudo em SQLite em memória; Telegram e fonte de preço mockados. Nada grava na
tabela alerts de produção nem envia mensagem real.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lowpoint.best_offer import BestOfferResult
from lowpoint.models import Alert, Base, PriceHistory, Product, Watch
from lowpoint.sources.base import OfferData
from lowpoint.telegram import notify
from lowpoint.telegram.adicionar import parse_adicionar, parse_price
from lowpoint.telegram.webhook import handle_update
from lowpoint.verdict import VerdictResult

NOW = datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc)
LINK = (
    "https://www.mercadolivre.com.br/console-playstation-5-slim-digital/p/MLB57081243"
    "?matt_tool=12345&pdp_filters=item_id:MLB111#reco_item_pos=1"
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    with patch.object(session, "close"):
        yield session
    session.close()


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "100")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")


def _update(text: str, chat_id: int = 100) -> dict:
    return {"message": {"chat": {"id": chat_id}, "text": text}}


def _callback(data: str, chat_id: int = 100) -> dict:
    return {"callback_query": {"id": "cb-1", "data": data, "message": {"chat": {"id": chat_id}}}}


# ------------------------------------------------------------------ parser

class TestParsePrice:
    @pytest.mark.parametrize("token,expected", [
        ("3500", "3500"),
        ("3.500", "3500"),
        ("3500,00", "3500.00"),
        ("3.500,00", "3500.00"),
        ("R$3.500", "3500"),
        ("r$3500,90", "3500.90"),
        ("3500.50", "3500.50"),   # formato antigo (ponto decimal) continua valendo
        ("1.250.000", "1250000"),
        ("99,9", "99.9"),
    ])
    def test_valid(self, token, expected):
        assert parse_price(token) == Decimal(expected)

    @pytest.mark.parametrize("token", [
        "Tab", "S10", "0", "0,00", "-10", "3,500.00", "35.00.0", "3.5000", "R$", "1e3", "",
        "3500,001",
    ])
    def test_invalid(self, token):
        assert parse_price(token) is None


class TestParseAdicionar:
    def test_only_link(self):
        p = parse_adicionar(f"/adicionar {LINK}")
        assert p.url == LINK and p.target is None and p.nickname is None

    def test_link_target(self):
        p = parse_adicionar(f"/adicionar {LINK} 3500")
        assert p.target == Decimal("3500") and p.nickname is None

    def test_link_target_nickname(self):
        p = parse_adicionar(f"/adicionar {LINK} 3.500,00 PS5 Slim")
        assert p.target == Decimal("3500.00") and p.nickname == "PS5 Slim"

    def test_r_dollar_as_separate_token(self):
        p = parse_adicionar(f"/adicionar {LINK} R$ 3.500 PS5")
        assert p.target == Decimal("3500") and p.nickname == "PS5"

    def test_bug_tab_s10_lite_is_nickname(self):
        """Antes: 'Preço-alvo inválido: Tab'."""
        p = parse_adicionar(f"/adicionar {LINK} Tab S10 Lite")
        assert p.target is None and p.nickname == "Tab S10 Lite"

    def test_number_after_nickname_word_stays_in_nickname(self):
        p = parse_adicionar(f"/adicionar {LINK} RTX 5070")
        assert p.target is None and p.nickname == "RTX 5070"

    def test_lone_r_dollar_without_number_is_nickname(self):
        p = parse_adicionar(f"/adicionar {LINK} R$ barato")
        assert p.target is None and p.nickname == "R$ barato"

    def test_no_link(self):
        assert parse_adicionar("/adicionar").url is None

    def test_extra_spaces(self):
        p = parse_adicionar(f"/adicionar   {LINK}   3500   PS5   Slim ")
        assert p.target == Decimal("3500") and p.nickname == "PS5   Slim"


# ------------------------------------------------------------------ /adicionar

def _live(price="3200.00", title="Console PlayStation 5 Slim Digital Edition"):
    return {"title": title, "price": Decimal(price), "offers": 7}


def _adicionar(db_session, text, live=None, history_days=0):
    with (
        patch("lowpoint.telegram.webhook.SessionLocal", return_value=db_session),
        patch("lowpoint.register.SessionLocal", return_value=db_session),
        patch("lowpoint.telegram.webhook._fetch_live_price",
              return_value=live if live is not None else _live()),
        patch("lowpoint.telegram.webhook._history_days", return_value=history_days),
    ):
        return handle_update(_update(text), "test-secret")["text"]


class TestAdicionarSemAlvo:
    def test_link_with_params_only(self, db_session):
        text = _adicionar(db_session, f"/adicionar {LINK}")
        w = db_session.query(Watch).one()
        assert w.target_price is None and w.nickname is None and w.silent is False
        assert db_session.get(Product, w.product_id).catalog_product_id == "MLB57081243"
        assert text == (
            "<b>Console PlayStation 5 Slim Digital Edition</b> adicionado. "
            "Preço atual: R$ 3.200,00.\n\n"
            "Sem alvo: te aviso quando o desconto for de verdade. "
            "Começo a dar veredito em 7 dias."
        )

    def test_nickname_without_target(self, db_session):
        text = _adicionar(db_session, f"/adicionar {LINK} Tab S10 Lite",
                          live=_live(title="Tablet Samsung Galaxy Tab S10 Lite"))
        w = db_session.query(Watch).one()
        assert w.target_price is None and w.nickname == "Tab S10 Lite"
        assert "inválido" not in text
        assert text.startswith("<b>Tab S10 Lite</b> adicionado.")

    def test_existing_history_shortens_wait(self, db_session):
        text = _adicionar(db_session, f"/adicionar {LINK}", history_days=4)
        assert text.endswith("Começo a dar veredito em 3 dias.")

    def test_one_day_left_singular(self, db_session):
        text = _adicionar(db_session, f"/adicionar {LINK}", history_days=6)
        assert text.endswith("Começo a dar veredito em 1 dia.")

    def test_enough_history_already(self, db_session):
        text = _adicionar(db_session, f"/adicionar {LINK}", history_days=12)
        assert text.endswith("Já tenho 12 dias de histórico, então o veredito já vale.")

    def test_price_unknown(self, db_session):
        text = _adicionar(db_session, f"/adicionar {LINK}", live={})
        assert "Preço chega na próxima coleta." in text
        assert "<b>MLB57081243</b> adicionado." in text

    def test_html_escaped_nickname(self, db_session):
        text = _adicionar(db_session, f"/adicionar {LINK} <Fone>")
        assert "<b>&lt;Fone&gt;</b>" in text

    def test_silent_watch_readded_without_target_drops_provisional_target(self, db_session):
        p = Product(catalog_product_id="MLB57081243", title="PS5", url="u")
        db_session.add(p)
        db_session.flush()
        db_session.add(Watch(chat_id=100, product_id=p.id, target_price=Decimal("1600"), silent=True))
        db_session.commit()
        _adicionar(db_session, f"/adicionar {LINK}")
        w = db_session.query(Watch).one()
        assert w.silent is False and w.target_price is None

    def test_active_watch_with_target_readded_without_target_keeps_target(self, db_session):
        p = Product(catalog_product_id="MLB57081243", title="PS5", url="u")
        db_session.add(p)
        db_session.flush()
        db_session.add(Watch(chat_id=100, product_id=p.id, target_price=Decimal("3500")))
        db_session.commit()
        text = _adicionar(db_session, f"/adicionar {LINK} PS5")
        w = db_session.query(Watch).one()
        assert w.target_price == Decimal("3500")
        assert "Alvo: R$ 3.500,00" in text


class TestAdicionarComAlvoRegressao:
    """Formato com alvo: mesma mensagem e mesmo efeito de antes."""

    def test_target_message_unchanged(self, db_session):
        text = _adicionar(db_session, f"/adicionar {LINK} 3500")
        assert text == (
            "Pronto. Monitorando:\n\n"
            "<b>Console PlayStation 5 Slim Digital Edition</b>\n"
            "Alvo: R$ 3.500,00\n"
            "Agora: R$ 3.200,00\n"
            "7 ofertas disponíveis\n"
            "\nTe aviso quando chegar lá."
        )
        assert db_session.query(Watch).one().target_price == Decimal("3500")

    def test_target_and_nickname_message_unchanged(self, db_session):
        text = _adicionar(db_session, f"/adicionar {LINK} R$ 3.500,00 PS5")
        assert text == (
            "Pronto. Monitorando:\n\n"
            "<b>PS5</b>\n"
            "Console PlayStation 5 Slim Digital Edition\n"
            "Alvo: R$ 3.500,00\n"
            "Agora: R$ 3.200,00\n"
            "7 ofertas disponíveis\n"
            "\nTe aviso quando chegar lá."
        )

    def test_usage_message_without_link(self, db_session):
        with patch("lowpoint.telegram.webhook.SessionLocal", return_value=db_session):
            text = handle_update(_update("/adicionar"), "test-secret")["text"]
        assert text.startswith("Uso: /adicionar <link> [alvo] [apelido]")


# ------------------------------------------------------------------ /lista

class TestListaSemAlvo:
    def test_shows_sem_alvo(self, db_session):
        p = Product(catalog_product_id="MLB1", title="PS5 Slim Digital", url="u")
        q = Product(catalog_product_id="MLB2", title="Monitor LG 27", url="u")
        db_session.add_all([p, q])
        db_session.flush()
        created = datetime.now(timezone.utc) - timedelta(days=2, hours=1)
        db_session.add_all([
            Watch(chat_id=100, product_id=p.id, target_price=None, created_at=created),
            Watch(chat_id=100, product_id=q.id, target_price=Decimal("1200"),
                  created_at=created + timedelta(seconds=1)),
            PriceHistory(product_id=p.id, price=Decimal("3599"), item_id="MLB9", seller_id=1,
                         available=True, collected_at=created),  # primeira coleta
            PriceHistory(product_id=q.id, price=Decimal("1299"), item_id="MLB8", seller_id=1,
                         available=True, collected_at=created),
            PriceHistory(product_id=p.id, price=Decimal("3599"), item_id="MLB9", seller_id=1,
                         available=True, collected_at=datetime.now(timezone.utc)),
            PriceHistory(product_id=q.id, price=Decimal("1299"), item_id="MLB8", seller_id=1,
                         available=True, collected_at=datetime.now(timezone.utc)),
        ])
        db_session.commit()
        with patch("lowpoint.telegram.webhook.SessionLocal", return_value=db_session):
            text = handle_update(_update("/lista"), "test-secret")["text"]
        assert text == (
            "Teus produtos:\n\n"
            "1. <b>PS5 Slim Digital</b>\n"
            "   Agora: R$ 3.599,00 · sem alvo\n"
            "   Monitorando há 2 dias\n"
            "2. <b>Monitor LG 27</b>\n"
            "   Agora: R$ 1.299,00 · Alvo: R$ 1.200,00\n"
            "   Monitorando há 2 dias"
        )


class TestListaDiasNuncaNegativos:
    """Antes: watch criado depois do histórico (live fetch falhou) dava "há -5 dias"."""

    def _lista(self, db_session):
        with patch("lowpoint.telegram.webhook.SessionLocal", return_value=db_session):
            return handle_update(_update("/lista"), "test-secret")["text"]

    def _product(self, db_session, collected):
        p = Product(catalog_product_id="MLB5", title="Monitor LG 27", url="u")
        db_session.add(p)
        db_session.flush()
        for t in collected:
            db_session.add(PriceHistory(product_id=p.id, price=Decimal("1299"), item_id="MLB9",
                                        seller_id=1, available=True, collected_at=t))
        db_session.add(Watch(chat_id=100, product_id=p.id, target_price=None,
                             created_at=datetime.now(timezone.utc)))
        db_session.commit()

    def test_history_older_than_watch_counts_from_first_collection(self, db_session):
        now = datetime.now(timezone.utc)
        self._product(db_session, [now - timedelta(days=9, hours=1), now - timedelta(days=4, hours=2)])
        text = self._lista(db_session)
        assert "há -" not in text
        assert "Monitorando há 9 dias" in text

    def test_only_old_collection_never_negative(self, db_session):
        now = datetime.now(timezone.utc)
        self._product(db_session, [now - timedelta(days=4, hours=2)])
        text = self._lista(db_session)
        assert "Monitorando há 4 dias" in text
        assert "há -" not in text

    def test_future_timestamp_clamped_to_zero(self, db_session):
        now = datetime.now(timezone.utc)
        self._product(db_session, [now + timedelta(days=2)])
        assert "Monitorando desde hoje" in self._lista(db_session)

    def test_reactivated_silent_keeps_full_history(self, db_session):
        now = datetime.now(timezone.utc)
        self._product(db_session, [now - timedelta(days=9, hours=1), now])
        assert "Monitorando há 9 dias" in self._lista(db_session)


# ------------------------------------------------------------------ alertas

def _offer(price: str) -> OfferData:
    return OfferData(item_id="MLB999", seller_id=1, price=Decimal(price), original_price=None,
                     condition="new", official_store_id=1, free_shipping=True, warranty="12 meses")


def _best(price: str) -> BestOfferResult:
    return BestOfferResult(offer=_offer(price), available=True, warnings=[], suspect_offers=[])


def _verdict(kind: str, price: str, days: int = 30) -> VerdictResult:
    p = Decimal(price)
    return VerdictResult(verdict=kind, current_price=p, lowest_price=p, median_30d=Decimal("1000"),
                         monitoring_days=days, reason="teste", baseline_price=Decimal("1000"))


def _seed_watch(session, target, *, silent=False, chat_id=100, catalog="MLB1"):
    product = Product(catalog_product_id=catalog, title=f"Produto {catalog}", url="u")
    session.add(product)
    session.flush()
    watch = Watch(chat_id=chat_id, product_id=product.id,
                  target_price=Decimal(target) if target is not None else None, silent=silent)
    session.add(watch)
    session.commit()
    return product, watch


def _run_alerts(session, product, verdict, price, now=NOW):
    with (
        patch.object(notify, "SessionLocal", return_value=session),
        patch.object(notify, "compute_verdict", return_value=_verdict(verdict, price)),
        patch.object(notify, "_send_message", return_value=True) as send,
        patch.object(notify, "_send_suggestion", return_value=True) as suggest,
    ):
        notify.send_alerts_after_collect(_best(price), product, now=now)
    return send, suggest


class TestAlertasSemAlvo:
    def test_real_sends_pode_ir(self, db_session):
        product, _ = _seed_watch(db_session, None)
        send, _ = _run_alerts(db_session, product, "real", "900")
        send.assert_called_once()
        msg = send.call_args.args[2]
        assert msg.alert_type == "verdict_real"
        assert "PODE IR" in msg.text and "alvo" not in msg.text.lower()
        assert db_session.query(Alert).one().alert_type == "verdict_real"

    @pytest.mark.parametrize("price", ["1200", "1", "999999"])
    def test_maquiado_sends_segura_never_target_hit(self, db_session, price):
        product, _ = _seed_watch(db_session, None)
        send, _ = _run_alerts(db_session, product, "maquiado", price)
        msg = send.call_args.args[2]
        assert msg.alert_type == "verdict_maquiado"
        assert "SEGURA" in msg.text and "alvo" not in msg.text.lower()

    @pytest.mark.parametrize("price", ["1", "500", "999999"])
    def test_neutro_never_sends(self, db_session, price):
        product, _ = _seed_watch(db_session, None)
        send, _ = _run_alerts(db_session, product, "neutro", price)
        send.assert_not_called()
        assert db_session.query(Alert).count() == 0

    def test_real_at_any_price_is_never_target_hit(self, db_session):
        product, _ = _seed_watch(db_session, None)
        send, _ = _run_alerts(db_session, product, "real", "1")
        assert send.call_args.args[2].alert_type == "verdict_real"

    def test_antispam_still_applies(self, db_session):
        product, _ = _seed_watch(db_session, None)
        assert _run_alerts(db_session, product, "maquiado", "1200")[0].call_count == 1
        later = NOW + timedelta(hours=5)
        assert _run_alerts(db_session, product, "maquiado", "1100", later)[0].call_count == 0
        later = NOW + timedelta(hours=24)
        assert _run_alerts(db_session, product, "maquiado", "1100", later)[0].call_count == 1

    def test_mixed_product_target_watch_unaffected(self, db_session):
        product, with_target = _seed_watch(db_session, "500", chat_id=200)
        db_session.add(Watch(chat_id=100, product_id=product.id, target_price=None))
        db_session.commit()
        send, _ = _run_alerts(db_session, product, "neutro", "400")
        assert send.call_count == 1
        assert send.call_args.args[1] == 200
        assert send.call_args.args[2].alert_type == "target_hit"


class TestRegressaoComAlvoESilenciosos:
    """Mesmos cenários de antes: tipo do alerta e texto idênticos ao formatter atual."""

    CASES = [("real", "900"), ("real", "400"), ("maquiado", "1200"),
             ("maquiado", "400"), ("neutro", "400"), ("neutro", "900")]
    EXPECTED_TYPE = {("real", "900"): "verdict_real", ("real", "400"): "target_hit",
                     ("maquiado", "1200"): "verdict_maquiado", ("maquiado", "400"): "target_hit_maquiado",
                     ("neutro", "400"): "target_hit", ("neutro", "900"): None}

    @pytest.mark.parametrize("verdict,price", CASES)
    def test_target_watch_same_alert(self, db_session, verdict, price):
        product, _ = _seed_watch(db_session, "500")
        send, suggest = _run_alerts(db_session, product, verdict, price)
        expected = self.EXPECTED_TYPE[(verdict, price)]
        if expected is None:
            send.assert_not_called()
        else:
            assert send.call_args.args[2].alert_type == expected
        suggest.assert_not_called()

    @pytest.mark.parametrize("verdict,price", CASES)
    @pytest.mark.parametrize("target", ["500", None])
    def test_silent_never_alerts_nor_suggests(self, db_session, verdict, price, target):
        product, _ = _seed_watch(db_session, target, silent=True)
        send, suggest = _run_alerts(db_session, product, verdict, price)
        send.assert_not_called()
        suggest.assert_not_called()
        assert db_session.query(Alert).count() == 0


# ------------------------------------------------------------------ sugestão de alvo

from lowpoint.target_suggestion import suggest_target  # noqa: E402
from lowpoint.verdict import PricePoint  # noqa: E402


def _points(prices, start=NOW - timedelta(days=8), step=timedelta(hours=12)):
    return [PricePoint(price=Decimal(p), original_price=None, collected_at=start + i * step)
            for i, p in enumerate(prices)]


class TestSuggestTargetRule:
    def test_none_before_7_days(self):
        pts = _points(["1000", "900"], start=NOW - timedelta(days=6, hours=23))
        assert suggest_target(pts, NOW) is None

    def test_none_without_history(self):
        assert suggest_target([], NOW) is None

    def test_lowest_when_it_is_a_real_discount(self):
        # mediana 1000, menor 880 (12% abaixo) → alvo = menor
        pts = _points(["1000"] * 10 + ["880"] + ["1000"] * 6)
        s = suggest_target(pts, NOW)
        assert s.lowest == Decimal("880") and s.normal == Decimal("1000")
        assert s.target == Decimal("880") and s.days == 8

    def test_capped_at_95pct_of_normal_when_price_is_flat(self):
        # menor 990 (só 1% abaixo do normal) → teto 95% da mediana = 950
        pts = _points(["1000", "995", "990", "1000", "1005", "1000", "1000"] * 2 + ["1000"])
        s = suggest_target(pts, NOW)
        assert s.lowest == Decimal("990") and s.target == Decimal("950")
        assert s.capped is True

    def test_lowest_kept_exact(self):
        pts = _points(["3599.90"] * 10 + ["3399.99"] + ["3599.90"] * 6)
        assert suggest_target(pts, NOW).target == Decimal("3399.99")
        assert suggest_target(pts, NOW).capped is False

    def test_cap_rounds_down(self):
        pts = _points(["3599.90"] * 17)  # 95% de 3599,90 = 3419,905
        assert suggest_target(pts, NOW).target == Decimal("3419")

    def test_normal_uses_last_30_days(self):
        old = _points(["5000"] * 20, start=NOW - timedelta(days=60), step=timedelta(days=1))
        recent = _points(["1000"] * 17)
        s = suggest_target(old + recent, NOW)
        assert s.normal == Decimal("1000")
        assert s.lowest == Decimal("1000")  # menor do período de 30 dias
        assert s.target == Decimal("950")


def _history(session, product_id, prices, start=NOW - timedelta(days=8)):
    for i, p in enumerate(prices):
        session.add(PriceHistory(product_id=product_id, price=Decimal(p), item_id="MLB9",
                                 seller_id=1, available=True,
                                 collected_at=start + i * timedelta(hours=12)))
    session.commit()


def _run_real(session, product, price, now=NOW, sent=True):
    """Sem mock do veredito nem do formatter da sugestão: só Telegram mockado."""
    with (
        patch.object(notify, "SessionLocal", return_value=session),
        patch.object(notify, "_send_message", return_value=True) as send,
        patch.object(notify, "_send_suggestion", return_value=sent) as suggest,
    ):
        notify.send_alerts_after_collect(_best(price), product, now=now)
    return send, suggest


class TestSugestaoNoColetor:
    def test_suggests_once_after_7_days(self, db_session):
        product, watch = _seed_watch(db_session, None)
        _history(db_session, product.id, ["1000"] * 10 + ["880"] + ["1000"] * 6)
        _, suggest = _run_real(db_session, product, "1000")
        suggest.assert_called_once()
        chat_id, text, buttons = suggest.call_args.args[1:4]
        assert chat_id == 100
        assert buttons == [[
            {"text": "Usar R$ 880,00", "callback_data": f"alvo:{watch.id}:88000"},
            {"text": "Agora não", "callback_data": f"alvo_nao:{watch.id}"},
        ]]
        assert db_session.get(Watch, watch.id).target_suggested_at is not None
        assert db_session.query(Alert).count() == 0  # sugestão não é alerta

        _, again = _run_real(db_session, product, "1000", now=NOW + timedelta(days=3))
        again.assert_not_called()

    def test_not_before_7_days(self, db_session):
        product, watch = _seed_watch(db_session, None)
        _history(db_session, product.id, ["1000"] * 5, start=NOW - timedelta(days=3))
        _, suggest = _run_real(db_session, product, "1000")
        suggest.assert_not_called()
        assert db_session.get(Watch, watch.id).target_suggested_at is None

    def test_failed_send_retries_next_collection(self, db_session):
        product, watch = _seed_watch(db_session, None)
        _history(db_session, product.id, ["1000"] * 17)
        _run_real(db_session, product, "1000", sent=False)
        assert db_session.get(Watch, watch.id).target_suggested_at is None
        _, suggest = _run_real(db_session, product, "1000", now=NOW + timedelta(hours=1))
        suggest.assert_called_once()

    def test_watch_with_target_never_gets_suggestion(self, db_session):
        product, _ = _seed_watch(db_session, "500")
        _history(db_session, product.id, ["1000"] * 17)
        _, suggest = _run_real(db_session, product, "1000")
        suggest.assert_not_called()

    def test_suggestion_and_alert_in_same_collection(self, db_session):
        product, _ = _seed_watch(db_session, None)
        _history(db_session, product.id, ["1000"] * 17)
        db_session.add(PriceHistory(product_id=product.id, price=Decimal("850"), item_id="MLB9",
                                    seller_id=1, available=True, collected_at=NOW))
        db_session.commit()
        send, suggest = _run_real(db_session, product, "850")
        assert send.call_args.args[2].alert_type == "verdict_real"
        suggest.assert_called_once()


class TestSugestaoTexto:
    def test_render_lowest(self):
        from lowpoint.target_suggestion import Suggestion, format_suggestion
        s = Suggestion(lowest=Decimal("3399.90"), normal=Decimal("3799.00"),
                       target=Decimal("3399.90"), days=8, capped=False)
        assert format_suggestion("PS5 Slim Digital", s) == (
            "<b>PS5 Slim Digital</b> · 8 dias de histórico\n\n"
            "Menor preço: R$ 3.399,90\n"
            "Preço normal: R$ 3.799,00\n\n"
            "Quer um alvo? Sugiro R$ 3.399,90, o menor preço que vi. "
            "Com alvo, também te aviso quando bater, mesmo se não for desconto de verdade."
        )

    def test_render_capped(self):
        from lowpoint.target_suggestion import Suggestion, format_suggestion
        s = Suggestion(lowest=Decimal("990"), normal=Decimal("1000"),
                       target=Decimal("950"), days=12, capped=True)
        assert format_suggestion("Monitor <LG>", s) == (
            "<b>Monitor &lt;LG&gt;</b> · 12 dias de histórico\n\n"
            "Menor preço: R$ 990,00\n"
            "Preço normal: R$ 1.000,00\n\n"
            "Quer um alvo? Sugiro R$ 950,00, 5% abaixo do normal: o menor que vi "
            "tá perto demais do normal pra ser desconto. "
            "Com alvo, também te aviso quando bater, mesmo se não for desconto de verdade."
        )


class TestSugestaoCallbacks:
    def _cb(self, db_session, data, chat_id=100):
        with patch("lowpoint.telegram.webhook.SessionLocal", return_value=db_session):
            return handle_update(_callback(data, chat_id), "test-secret")

    def test_accept_sets_target(self, db_session):
        _, watch = _seed_watch(db_session, None)
        result = self._cb(db_session, f"alvo:{watch.id}:88000")
        assert db_session.get(Watch, watch.id).target_price == Decimal("880.00")
        assert result["text"] == "Alvo definido: <b>R$ 880,00</b>. Te aviso quando bater."

    def test_decline_keeps_no_target(self, db_session):
        _, watch = _seed_watch(db_session, None)
        result = self._cb(db_session, f"alvo_nao:{watch.id}")
        assert db_session.get(Watch, watch.id).target_price is None
        assert result["text"] == (
            "Beleza, sigo sem alvo. Te aviso só quando o desconto for de verdade."
        )

    def test_accept_other_chat_is_ignored(self, db_session):
        _, watch = _seed_watch(db_session, None, chat_id=200)
        result = self._cb(db_session, f"alvo:{watch.id}:88000", chat_id=100)
        assert db_session.get(Watch, watch.id).target_price is None
        assert "não encontrado" in result["text"].lower()

    @pytest.mark.parametrize("data", ["alvo:x:1", "alvo:1", "alvo:1:0", "alvo:1:-5"])
    def test_malformed(self, db_session, data):
        _seed_watch(db_session, None)
        result = self._cb(db_session, data)
        assert result["method"] == "answerCallbackQuery"
        assert db_session.query(Watch).one().target_price is None
