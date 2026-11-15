"""[TESTE] Métricas do pré-registro com dados sintéticos (sem banco, sem rede)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from analysis import metrics, prereg
from analysis.metrics import Obs

BRT = prereg.BRT
D = Decimal


def _hourly(start, end, price, step=timedelta(hours=1), original=None):
    out, t = [], start
    while t < end:
        out.append(Obs(at=t.astimezone(timezone.utc), price=D(price), original_price=original, available=True))
        t += step
    return out


B0, PRE, BF, POS = prereg.WINDOWS
QUARTER = timedelta(minutes=15)


def _series(b0="1000", pre="1000", bf="1000", pos="1000"):
    return (
        _hourly(B0.start, B0.end, b0)
        + _hourly(PRE.start, PRE.end, pre)
        + _hourly(BF.start, BF.end, bf, step=QUARTER)
        + _hourly(POS.start, POS.end, pos)
    )


def _replace_bf(series, prices):
    """Troca os preços das primeiras coletas da BF, na ordem."""
    bf_idx = [i for i, o in enumerate(series) if BF.contains(o.at)]
    out = list(series)
    for i, p in zip(bf_idx, prices):
        o = out[i]
        out[i] = Obs(at=o.at, price=D(p), original_price=o.original_price, available=True)
    return out


AFTER = prereg.CUTOFF + timedelta(days=1)


# --- História da landing (adaptada às janelas do pré-registro) -------------

def test_landing_story_is_maquiagem_in_p2():
    """Mesmos preços da landing (3.450 → 6.000 → 3.600), datas nas janelas v1."""
    s = _series(b0="3450.00", pre="6000.00", bf="3600.00", pos="3600.00")
    ref = metrics.reference(s)
    assert ref == D("3450.00")
    r = metrics.p2_product(s, ref)
    assert r.hike and r.retreat and r.fachada
    assert r.classification == "maquiagem"


def test_hike_and_real_drop_is_reported_apart():
    s = _series(b0="3450.00", pre="6000.00", bf="3200.00")
    assert metrics.p2_product(s, D("3450.00")).classification == "subiu_mas_real"


def test_p2_borders_are_inclusive():
    # máx PRE = Ref×1,10; min BF = máx×0,95 = 1045; 1045 ≥ Ref×0,97 = 970 → maquiagem
    s = _series(b0="1000", pre="1100", bf="1045")
    assert metrics.p2_product(s, D("1000")).classification == "maquiagem"
    s = _series(b0="1000", pre="1099.99", bf="1000")
    assert metrics.p2_product(s, D("1000")).classification == "sem_padrao"


# --- Desconto real ---------------------------------------------------------

def test_real_discount_case_p1b_yes_and_p1a_real():
    s = _replace_bf(_series(), ["900"] * 8)
    ref = metrics.reference(s)
    assert metrics.p1b_product(s, ref).counts
    a = metrics.p1a_product(s)
    assert a.counts and a.real_collections >= 2


def test_p1b_border_is_inclusive_at_5_percent():
    s = _replace_bf(_series(), ["950", "950"])
    assert metrics.p1b_product(s, D("1000")).counts
    s = _replace_bf(_series(), ["950.01", "950.01"])
    assert not metrics.p1b_product(s, D("1000")).counts


# --- 2 coletas seguidas vs. 1 isolada ---------------------------------------

def test_one_isolated_collection_does_not_count():
    s = _replace_bf(_series(), ["900"])
    r = metrics.p1b_product(s, D("1000"))
    assert not r.counts and r.any_one


def test_two_non_consecutive_do_not_count():
    s = _replace_bf(_series(), ["900", "1000", "900"])
    r = metrics.p1b_product(s, D("1000"))
    assert not r.counts and r.any_one


def test_two_consecutive_count():
    s = _replace_bf(_series(), ["1000", "900", "900"])
    assert metrics.p1b_product(s, D("1000")).counts


def test_unavailable_collection_is_discarded_not_a_break():
    s = _replace_bf(_series(), ["900"])
    bf_idx = [i for i, o in enumerate(s) if BF.contains(o.at)]
    gap = s[bf_idx[1]]
    s[bf_idx[1]] = Obs(at=gap.at, price=D("0"), original_price=None, available=False)
    o = s[bf_idx[2]]
    s[bf_idx[2]] = Obs(at=o.at, price=D("900"), original_price=None, available=True)
    assert metrics.p1b_product(s, D("1000")).counts


def test_streak_helper():
    assert metrics.has_streak([False, True, True], 2)
    assert not metrics.has_streak([True, False, True], 2)
    assert metrics.has_streak([True], 1)
    assert not metrics.has_streak([], 1)


# --- P1a sem olhar o futuro -------------------------------------------------

def test_p1a_uses_only_history_until_each_collection(monkeypatch):
    import analysis.metrics as m
    seen = []
    real_cv = m.compute_verdict

    def spy(price, original, history, now=None, **kw):
        assert all(p.collected_at <= now for p in history)
        seen.append((now, max(p.collected_at for p in history)))
        return real_cv(price, original, history, now, **kw)

    monkeypatch.setattr(m, "compute_verdict", spy)
    s = _replace_bf(_series(), ["900"] * 4)
    m.p1a_product(s)
    assert seen and all(now == last for now, last in seen)


def test_p1a_results_do_not_change_with_future_data():
    s = _replace_bf(_series(), ["900"] * 4)
    full = metrics.p1a_product(s)
    # Corta tudo depois da 6ª coleta da BF: as 6 primeiras decisões não podem mudar.
    bf_times = [o.at for o in s if BF.contains(o.at)]
    cut = [o for o in s if o.at <= bf_times[5]]
    partial = metrics.p1a_product(cut)
    assert full.verdicts[:6] == partial.verdicts


# --- Cobertura 69% vs. 70% ---------------------------------------------------

def _window(hours, rate=1):
    start = datetime(2026, 11, 14, 14, 50, tzinfo=BRT)
    return prereg.Window("X", start, start + timedelta(hours=hours), rate)


@pytest.mark.parametrize("n, ok", [(69, False), (70, True)])
def test_coverage_69_vs_70(n, ok):
    w = _window(100)
    obs = _hourly(w.start, w.start + timedelta(hours=n), "10")
    c = metrics.coverage(obs, w, now=AFTER)
    assert c.expected == 100 and c.n == n
    assert c.ok is ok


def test_coverage_ignores_unavailable_and_counts_partial_window():
    w = _window(100)
    obs = _hourly(w.start, w.start + timedelta(hours=10), "10")
    obs[0] = Obs(at=obs[0].at, price=D("0"), original_price=None, available=False)
    c = metrics.coverage(obs, w, now=w.start + timedelta(hours=10))
    assert c.partial and c.expected == 10 and c.n == 9


# --- P4: empate de 1% -------------------------------------------------------

def test_p4_exactly_1_percent_wins():
    assert metrics.p4_winner({"antes": D("100"), "BF": D("99"), "POS": D("100")}) == "BF"


def test_p4_below_1_percent_is_tie():
    assert metrics.p4_winner({"antes": D("100"), "BF": D("99.01"), "POS": D("100")}) == "empate"


def test_p4_product_uses_three_periods():
    s = _series(b0="1000", pre="1000", bf="950", pos="900")
    r = metrics.p4_product(s)
    assert r.mins == {"antes": D("1000"), "BF": D("950"), "POS": D("900")}
    assert r.winner == "POS"


# --- P3 --------------------------------------------------------------------

def test_p3_inflated_strike_price():
    s = _series()
    s = [Obs(o.at, o.price, D("1200") if BF.contains(o.at) else None, True) for o in s]
    assert metrics.p3_product(s, D("1000")).classification == "inflado"
    s = [Obs(o.at, o.price, D("1100") if BF.contains(o.at) else None, True) for o in s]
    assert metrics.p3_product(s, D("1000")).classification == "honesto"
    assert metrics.p3_product(_series(), D("1000")).classification == "sem_riscado"


# --- Manchetes ---------------------------------------------------------------

def test_headlines():
    # Emenda 2: cortes viram proporção dos produtos com cobertura (10/18, 4/18, 5/18).
    assert metrics.p1_headline(10, 18) == "a maioria teve"
    assert metrics.p1_headline(4, 18) == "não teve"
    assert metrics.p1_headline(5, 18) == "uma minoria teve"
    assert metrics.p1_headline(9, 16) == "a maioria teve"     # 56,25% ≥ 10/18
    assert metrics.p1_headline(5, 17) == "uma minoria teve"   # 29,4%
    assert metrics.p1_headline(4, 17) == "uma minoria teve"   # 23,5% > 4/18
    assert metrics.p1_headline(2, 12) == "não teve"           # 16,7%
    assert metrics.p2_headline(0, 0, 18) == "não houve maquiagem"
    assert metrics.p2_headline(1, 1, 18) == "sim, houve maquiagem"
    assert metrics.p2_headline(5, 5, 18) == "sim, houve maquiagem; foi comum"
    assert metrics.p2_headline(4, 4, 14) == "sim, houve maquiagem; foi comum"  # 28,6% ≥ 5/18
    assert metrics.p2_headline(4, 4, 18) == "sim, houve maquiagem"
    assert metrics.p3_headline(5, 10) == "não é honesto"
    assert metrics.p3_headline(2, 10) == "é honesto"
    assert metrics.p3_headline(3, 10) == "depende do produto"
    assert metrics.p3_headline(0, 0) is None
    assert metrics.p4_headline(["BF"] * 9 + ["POS"] * 9) == "sim, a BF foi o melhor momento"
    assert metrics.p4_headline(["POS"] * 9 + ["empate"] * 9) == "não, valeu esperar"
    assert metrics.p4_headline(["BF"] * 8 + ["POS"] * 8 + ["empate"] * 2) == "sem padrão"
    assert metrics.p5_answer([True, True], D("0.05")) == "sim"
    assert metrics.p5_answer([True, True], D("0.049")) == "não"
    assert metrics.p5_answer([True, False], D("0.10")) == "misto"
    assert metrics.p5_answer([False, False], D("0.10")) == "não"


# --- Janelas incompletas -------------------------------------------------------

def _dataset(series_by_catalog):
    return metrics.Dataset(
        obs={p.catalog_id: series_by_catalog.get(p.catalog_id, []) for p in prereg.PRODUCTS},
        offers={},
    )


def test_today_only_coverage_and_partial_b0():
    now = datetime(2026, 11, 15, 10, 0, tzinfo=BRT)
    s = [o for o in _series() if o.at < now]
    res = metrics.run_all(_dataset({p.catalog_id: s for p in prereg.PRODUCTS}), now)
    assert res.window_status == {"B0": "em andamento", "PRE": "futura", "BF": "futura", "POS": "futura"}
    for q in ("P1a", "P1b", "P2", "P3", "P4", "P5"):
        assert res.questions[q].status == "incompleto"
        assert res.questions[q].headline is None
        assert res.questions[q].rows == []
    assert all(r.partial for r in res.b0_partial.values())


def _thin_bf(series, keep_of_5):
    """Mantém keep_of_5 de cada 5 coletas da BF (3 → 60% de cobertura)."""
    out, i = [], 0
    for o in series:
        if BF.contains(o.at):
            i += 1
            if (i - 1) % 5 >= keep_of_5:
                continue
        out.append(o)
    return out


def test_product_at_60pct_is_excluded_and_headline_still_computed():
    """Emenda 2: <70% numa janela usada exclui o produto daquela pergunta, só isso."""
    full = _series()
    data = {p.catalog_id: full for p in prereg.PRODUCTS}
    lame = prereg.PRODUCTS[5]
    data[lame.catalog_id] = _thin_bf(full, 3)
    res = metrics.run_all(_dataset(data), AFTER)
    assert res.coverage[lame.catalog_id]["BF"].ratio == D("0.6")
    for q in ("P1a", "P1b", "P2", "P3", "P4", "P5"):
        Q = res.questions[q]
        assert Q.status == "ok", q
        # P3 sem nenhum riscado na série sintética: sem manchete por definição.
        assert Q.headline is not None or (q == "P3" and Q.extra["com riscado"] == 0), q
        assert [e[0] for e in Q.excluded] == [lame.label], q
        assert "BF" in Q.excluded[0][1]
        assert lame.catalog_id not in {r.catalog_id for r in Q.rows if r.result != "excluído"}
    assert res.questions["P1b"].headline == "não teve"
    assert res.questions["P1b"].extra["de 18 com cobertura"] == 17


def test_fewer_than_12_of_18_covered_is_incompleto():
    full = _series()
    data = {p.catalog_id: full for p in prereg.PRODUCTS}
    for p in prereg.NON_CONTROL[:7]:
        data[p.catalog_id] = _thin_bf(full, 3)
    res = metrics.run_all(_dataset(data), AFTER)
    q = res.questions["P1b"]
    assert q.status == "incompleto" and q.headline is None
    assert "11 de 18" in q.reason
    assert len(q.excluded) == 7


def test_exactly_12_of_18_covered_gets_headline():
    full = _series()
    data = {p.catalog_id: full for p in prereg.PRODUCTS}
    for p in prereg.NON_CONTROL[:6]:
        data[p.catalog_id] = _thin_bf(full, 3)
    res = metrics.run_all(_dataset(data), AFTER)
    assert res.questions["P1b"].status == "ok"


def test_p3_base_is_the_18_non_control():
    full = _series()
    res = metrics.run_all(_dataset({p.catalog_id: full for p in prereg.PRODUCTS}), AFTER)
    ids = {r.catalog_id for r in res.questions["P3"].rows}
    assert ids == {p.catalog_id for p in prereg.NON_CONTROL}


def test_p5_needs_both_controls_covered():
    full = _series()
    data = {p.catalog_id: full for p in prereg.PRODUCTS}
    data[prereg.CONTROLS[0].catalog_id] = _thin_bf(full, 3)
    q = metrics.run_all(_dataset(data), AFTER).questions["P5"]
    assert q.status == "incompleto" and q.headline is None
    assert "controle" in q.reason


def test_complete_run_all_flat_gives_headlines():
    full = _series()
    res = metrics.run_all(_dataset({p.catalog_id: full for p in prereg.PRODUCTS}), AFTER)
    assert res.questions["P1b"].headline == "não teve"
    assert res.questions["P2"].headline == "não houve maquiagem"
    assert res.questions["P4"].headline == "sem padrão"  # tudo empate
    assert res.questions["P5"].headline == "não"        # os 18 ficaram parados
