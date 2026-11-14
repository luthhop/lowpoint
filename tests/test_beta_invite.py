"""[TESTE] Pedido de convite pro beta: /start de chat fora da allowlist.

Nada é enviado de verdade: requests.post do módulo é substituído por mock.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lowpoint.models import Base, Product, SystemState, Watch
from lowpoint.telegram import beta
from lowpoint.telegram.webhook import handle_update

OWNER = 100
OUTSIDER = 555777
NOW = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)

INVITE_REPLY = "O Lowpoint tá em beta fechado. Teu pedido chegou, te aviso se abrir vaga."
POINT_TO_START = "O Lowpoint tá em beta fechado. Manda /start pra pedir convite."


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
    monkeypatch.setenv("ALLOWED_CHAT_IDS", f"{OWNER},200")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")


@pytest.fixture()
def post():
    ok = MagicMock(ok=True)
    with patch.object(beta.requests, "post", return_value=ok) as m:
        yield m


def _msg(text, chat_id=OUTSIDER, first="Ana", last="Souza", username="ana_s"):
    sender = {"id": chat_id, "first_name": first}
    if last:
        sender["last_name"] = last
    if username:
        sender["username"] = username
    return {"message": {"chat": {"id": chat_id}, "from": sender, "text": text}}


def _send(db_session, update, now=NOW):
    with (
        patch.object(beta, "SessionLocal", return_value=db_session),
        patch.object(beta, "_now", return_value=now),
    ):
        return handle_update(update, "test-secret")


class TestPedidoNovo:
    @pytest.mark.parametrize("text", ["/start", "/start beta", "/start@LowpointBot beta"])
    def test_reply_and_notice(self, db_session, post, text):
        result = _send(db_session, _msg(text))
        assert result["chat_id"] == OUTSIDER
        assert result["text"] == INVITE_REPLY

        post.assert_called_once()
        url = post.call_args.args[0]
        payload = post.call_args.kwargs["json"]
        assert url == "https://api.telegram.org/bottest-token/sendMessage"
        assert payload["chat_id"] == OWNER
        assert "Ana Souza" in payload["text"]
        assert "@ana_s" in payload["text"]
        assert str(OUTSIDER) in payload["text"]
        assert "parse_mode" not in payload  # nome vem do usuário: texto puro

    def test_without_username(self, db_session, post):
        _send(db_session, _msg("/start beta", username=None, last=None))
        text = post.call_args.kwargs["json"]["text"]
        assert "Ana" in text and "@" not in text
        assert str(OUTSIDER) in text

    def test_nothing_about_requester_in_db(self, db_session, post):
        _send(db_session, _msg("/start beta"))
        assert db_session.query(Watch).count() == 0
        assert db_session.query(Product).count() == 0
        rows = db_session.query(SystemState).all()
        assert len(rows) == 1  # só o horário do aviso, chave sem o chat_id
        assert str(OUTSIDER) not in rows[0].key
        assert "ana" not in rows[0].key.lower()


class TestPedidoRepetido:
    def test_second_request_within_24h_does_not_notify(self, db_session, post):
        _send(db_session, _msg("/start beta"))
        result = _send(db_session, _msg("/start"), now=NOW + timedelta(hours=23, minutes=59))
        assert result["text"] == INVITE_REPLY
        assert post.call_count == 1

    def test_exactly_24h_notifies_again(self, db_session, post):
        _send(db_session, _msg("/start beta"))
        _send(db_session, _msg("/start beta"), now=NOW + timedelta(hours=24))
        assert post.call_count == 2

    def test_other_chat_is_independent(self, db_session, post):
        _send(db_session, _msg("/start beta"))
        _send(db_session, _msg("/start beta", chat_id=888999), now=NOW + timedelta(minutes=5))
        assert post.call_count == 2

    def test_failed_notice_is_not_recorded(self, db_session):
        with patch.object(beta.requests, "post", return_value=MagicMock(ok=False)) as p:
            _send(db_session, _msg("/start beta"))
            _send(db_session, _msg("/start beta"), now=NOW + timedelta(minutes=1))
        assert p.call_count == 2  # sem registro, tenta avisar de novo
        assert db_session.query(SystemState).count() == 0


class TestOutrasMensagensDeFora:
    @pytest.mark.parametrize("text", ["oi", "/lista", "/adicionar mercadolivre.com.br/p/MLB1 10"])
    def test_points_to_start_without_notice(self, db_session, post, text):
        result = _send(db_session, _msg(text))
        assert result["text"] == POINT_TO_START
        post.assert_not_called()
        assert db_session.query(SystemState).count() == 0


class TestAllowlistNormal:
    @pytest.mark.parametrize("text", ["/start", "/start beta"])
    def test_allowed_start_is_normal_flow(self, db_session, post, text):
        result = _send(db_session, _msg(text, chat_id=OWNER))
        assert result["text"] == "Lowpoint. Manda /lista pra ver teus produtos."
        post.assert_not_called()
        assert db_session.query(SystemState).count() == 0
