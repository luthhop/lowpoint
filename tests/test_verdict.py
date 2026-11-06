from datetime import datetime, timedelta, timezone
from decimal import Decimal

from lowpoint.verdict import PricePoint, compute_verdict


def _make_history(
    prices: list[float],
    start_days_ago: int = 60,
    interval_hours: int = 6,
) -> list[PricePoint]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=start_days_ago)
    return [
        PricePoint(
            price=Decimal(str(p)),
            original_price=None,
            collected_at=start + timedelta(hours=i * interval_hours),
        )
        for i, p in enumerate(prices)
    ]


class TestVerdictNeutroHistoricoInsuficiente:
    def test_sem_historico(self):
        result = compute_verdict(
            current_price=Decimal("1000"),
            original_price=None,
            history=[],
        )
        assert result.verdict == "neutro"
        assert "sem histórico" in result.reason

    def test_poucos_dias(self):
        now = datetime.now(timezone.utc)
        history = [
            PricePoint(
                price=Decimal("1200"),
                original_price=None,
                collected_at=now - timedelta(days=3),
            ),
        ]
        result = compute_verdict(
            current_price=Decimal("1100"),
            original_price=None,
            history=history,
            now=now,
            min_monitoring_days=7,
        )
        assert result.verdict == "neutro"
        assert "3 dias de monitoramento" in result.reason
        assert result.monitoring_days == 3


class TestVerdictReal:
    def test_desconto_real_abaixo_minimo_historico(self):
        prices = [1500.0] * 20 + [1480.0] * 20
        history = _make_history(prices, start_days_ago=60)

        result = compute_verdict(
            current_price=Decimal("1300"),
            original_price=None,
            history=history,
        )
        assert result.verdict == "real"
        assert "desconto real" in result.reason

    def test_desconto_real_precisa_estar_abaixo_minimo(self):
        prices = [1500.0] * 10 + [1400.0] * 10 + [1300.0] * 10
        history = _make_history(prices, start_days_ago=45)

        result = compute_verdict(
            current_price=Decimal("1350"),
            original_price=None,
            history=history,
        )
        assert result.verdict == "neutro"


class TestVerdictMaquiadoOriginalInflado:
    def test_preco_de_inflado(self):
        prices = [1400.0] * 40
        history = _make_history(prices, start_days_ago=60)

        result = compute_verdict(
            current_price=Decimal("1300"),
            original_price=Decimal("2500"),
            history=history,
        )
        assert result.verdict == "maquiado"
        assert "inflado" in result.reason

    def test_original_price_legitimo(self):
        prices = [1400.0] * 40
        history = _make_history(prices, start_days_ago=60)

        result = compute_verdict(
            current_price=Decimal("1200"),
            original_price=Decimal("1450"),
            history=history,
        )
        assert result.verdict != "maquiado" or "inflado" not in result.reason


class TestVerdictMaquiadoSubiramPraBaixar:
    def test_subiu_antes_da_queda(self):
        now = datetime.now(timezone.utc)
        history = []

        for i in range(40):
            history.append(
                PricePoint(
                    price=Decimal("1000"),
                    original_price=None,
                    collected_at=now - timedelta(days=60 - i),
                )
            )

        for i in range(10):
            history.append(
                PricePoint(
                    price=Decimal("1200"),
                    original_price=None,
                    collected_at=now - timedelta(days=12 - i),
                )
            )

        result = compute_verdict(
            current_price=Decimal("980"),
            original_price=Decimal("1200"),
            history=history,
            now=now,
        )
        assert result.verdict == "maquiado"
        assert "subiu" in result.reason
        assert result.pre_hike_price is not None

    def test_sem_alta_recente(self):
        now = datetime.now(timezone.utc)
        history = [
            PricePoint(
                price=Decimal("1000"),
                original_price=None,
                collected_at=now - timedelta(days=60 - i),
            )
            for i in range(50)
        ]

        result = compute_verdict(
            current_price=Decimal("900"),
            original_price=None,
            history=history,
            now=now,
        )
        assert result.verdict != "maquiado" or "subiu" not in result.reason


class TestVerdictNeutroFaixaNormal:
    def test_preco_estavel(self):
        prices = [1000.0] * 40
        history = _make_history(prices, start_days_ago=60)

        result = compute_verdict(
            current_price=Decimal("1000"),
            original_price=None,
            history=history,
        )
        assert result.verdict == "neutro"
        assert "faixa normal" in result.reason


class TestVerdictLimitesConfiguraveis:
    def test_threshold_customizado(self):
        prices = [1000.0] * 40
        history = _make_history(prices, start_days_ago=60)

        result_strict = compute_verdict(
            current_price=Decimal("970"),
            original_price=None,
            history=history,
            real_discount_threshold=Decimal("0.01"),
        )

        result_loose = compute_verdict(
            current_price=Decimal("970"),
            original_price=None,
            history=history,
            real_discount_threshold=Decimal("0.10"),
        )

        assert result_strict.verdict == "real"
        assert result_loose.verdict == "neutro"


class TestVerdictExcluiIndisponiveis:
    def test_preco_zero_ignorado(self):
        now = datetime.now(timezone.utc)
        history = [
            PricePoint(
                price=Decimal("0"),
                original_price=None,
                collected_at=now - timedelta(days=30),
            ),
            PricePoint(
                price=Decimal("1000"),
                original_price=None,
                collected_at=now - timedelta(days=20),
            ),
        ]

        result = compute_verdict(
            current_price=Decimal("900"),
            original_price=None,
            history=history,
            now=now,
        )
        assert result.lowest_price == Decimal("1000")


class TestVerdictPeriodoLabel:
    def test_periodo_real_menos_de_90(self):
        now = datetime.now(timezone.utc)
        history = [
            PricePoint(
                price=Decimal("1000"),
                original_price=None,
                collected_at=now - timedelta(days=21),
            )
            for _ in range(10)
        ]

        result = compute_verdict(
            current_price=Decimal("900"),
            original_price=None,
            history=history,
            now=now,
        )
        assert "21 dias" in result.reason
