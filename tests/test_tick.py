"""[TESTE] /api/tick com dependências falsas: sem GitHub, Telegram ou banco."""
from datetime import datetime, timedelta, timezone

import pytest

from lowpoint.tick import TickDeps, handle_tick, in_bf_window

SECRET = "s3cret-tick"
UTC = timezone.utc


class Fake:
    def __init__(self, last_collected, dispatch_ok=True):
        self.last_collected = last_collected
        self.dispatch_ok = dispatch_ok
        self.warning_at = None
        self.dispatches = 0
        self.messages: list[str] = []

    def deps(self) -> TickDeps:
        def dispatch():
            self.dispatches += 1
            return self.dispatch_ok

        def send(text):
            self.messages.append(text)
            return True

        def record(at):
            self.warning_at = at

        return TickDeps(
            last_collected_at=lambda: self.last_collected,
            last_warning_at=lambda: self.warning_at,
            record_warning=record,
            dispatch=dispatch,
            send_warning=send,
        )


@pytest.fixture(autouse=True)
def _secret(monkeypatch):
    monkeypatch.setenv("TICK_SECRET", SECRET)


# 10/11 15:00 BRT, fora da janela da Black Friday
OFF_PEAK = datetime(2026, 11, 10, 18, 0, tzinfo=UTC)


class TestAuth:
    @pytest.mark.parametrize("method, secret", [
        ("POST", "errado"),
        ("POST", None),
        ("POST", ""),
        ("POST", SECRET + "x"),
        ("GET", SECRET),
        ("PUT", SECRET),
    ])
    def test_rejects_with_401_and_no_side_effects(self, method, secret):
        fake = Fake(OFF_PEAK - timedelta(hours=5))
        result = handle_tick(method, secret, OFF_PEAK, fake.deps())
        assert result == {"statusCode": 401}
        assert fake.dispatches == 0 and fake.messages == []

    def test_rejects_when_env_secret_missing(self, monkeypatch):
        monkeypatch.delenv("TICK_SECRET")
        fake = Fake(OFF_PEAK)
        assert handle_tick("POST", "", OFF_PEAK, fake.deps()) == {"statusCode": 401}

    def test_internal_error_has_no_details(self):
        def boom():
            raise RuntimeError("DATABASE_URL=postgres://segredo")
        deps = Fake(None).deps()
        deps.last_collected_at = boom
        assert handle_tick("POST", SECRET, OFF_PEAK, deps) == {"statusCode": 500}


class TestStaleWarning:
    def test_delay_over_90_min_sends_warning(self):
        fake = Fake(OFF_PEAK - timedelta(minutes=95))
        result = handle_tick("POST", SECRET, OFF_PEAK, fake.deps())
        assert result["warned"] is True
        assert fake.messages == [
            "Coleta atrasada: a última foi há 1h35 (10/11 13:25). "
            "Disparei uma nova coleta."
        ]

    def test_delay_of_exactly_90_min_does_not_warn(self):
        fake = Fake(OFF_PEAK - timedelta(minutes=90))
        handle_tick("POST", SECRET, OFF_PEAK, fake.deps())
        assert fake.messages == []

    def test_two_ticks_in_a_row_send_one_warning(self):
        fake = Fake(OFF_PEAK - timedelta(minutes=100))
        handle_tick("POST", SECRET, OFF_PEAK, fake.deps())
        handle_tick("POST", SECRET, OFF_PEAK + timedelta(minutes=15), fake.deps())
        assert len(fake.messages) == 1

    def test_warns_again_after_one_hour(self):
        fake = Fake(OFF_PEAK - timedelta(minutes=100))
        for minutes in (0, 15, 30, 45, 60):
            handle_tick("POST", SECRET, OFF_PEAK + timedelta(minutes=minutes), fake.deps())
        assert len(fake.messages) == 2

    def test_failed_dispatch_is_reported(self):
        fake = Fake(OFF_PEAK - timedelta(hours=3), dispatch_ok=False)
        result = handle_tick("POST", SECRET, OFF_PEAK, fake.deps())
        assert result["statusCode"] == 502
        assert "Não disparei coleta" in fake.messages[0]


class TestDispatchRhythm:
    def test_off_peak_skips_when_recent(self):
        fake = Fake(OFF_PEAK - timedelta(minutes=50))
        result = handle_tick("POST", SECRET, OFF_PEAK, fake.deps())
        assert result == {"statusCode": 200, "dispatched": False, "warned": False}
        assert fake.dispatches == 0

    def test_off_peak_dispatches_after_55_min(self):
        fake = Fake(OFF_PEAK - timedelta(minutes=56))
        handle_tick("POST", SECRET, OFF_PEAK, fake.deps())
        assert fake.dispatches == 1

    def test_dispatches_when_no_collection_ever(self):
        fake = Fake(None)
        handle_tick("POST", SECRET, OFF_PEAK, fake.deps())
        assert fake.dispatches == 1 and fake.messages == []

    @pytest.mark.parametrize("now", [
        datetime(2026, 11, 23, 3, 0, tzinfo=UTC),    # 23/11 00:00 BRT
        datetime(2026, 11, 25, 15, 0, tzinfo=UTC),
        datetime(2026, 11, 28, 2, 59, tzinfo=UTC),   # 27/11 23:59 BRT
    ])
    def test_bf_window_always_dispatches(self, now):
        fake = Fake(now - timedelta(minutes=1))
        for i in range(3):
            handle_tick("POST", SECRET, now + timedelta(seconds=i), fake.deps())
        assert fake.dispatches == 3

    @pytest.mark.parametrize("now, expected", [
        (datetime(2026, 11, 23, 2, 59, tzinfo=UTC), False),  # 22/11 23:59 BRT
        (datetime(2026, 11, 23, 3, 0, tzinfo=UTC), True),
        (datetime(2026, 11, 28, 2, 59, tzinfo=UTC), True),
        (datetime(2026, 11, 28, 3, 0, tzinfo=UTC), False),   # 28/11 00:00 BRT
    ])
    def test_bf_window_edges_in_brasilia_time(self, now, expected):
        assert in_bf_window(now) is expected


class TestHttpHandler:
    """[TESTE] Handler real de api/tick.py num servidor local (127.0.0.1)."""

    @pytest.fixture
    def server(self):
        import threading
        from http.server import HTTPServer
        from api.tick import handler
        srv = HTTPServer(("127.0.0.1", 0), handler)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        yield f"http://127.0.0.1:{srv.server_port}/api/tick"
        srv.shutdown()

    @pytest.mark.parametrize("method, headers", [
        ("GET", {"X-Tick-Secret": SECRET}),
        ("POST", {"X-Tick-Secret": "errado"}),
        ("POST", {}),
        ("DELETE", {"X-Tick-Secret": SECRET}),
    ])
    def test_401_without_details(self, server, method, headers):
        import requests
        resp = requests.request(method, server, headers=headers, timeout=5)
        assert resp.status_code == 401
        assert resp.content == b"{}"
