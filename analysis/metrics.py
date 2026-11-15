"""Métricas P1a, P1b, P2, P3, P4, P5 e cobertura, como no pré-registro v1.

Funções puras sobre listas de Obs (uma coleta de um produto). Sem pandas,
sem banco: os testes rodam com dados sintéticos. Regras e números vêm de
analysis.prereg; nada de limiar escrito aqui.
"""
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
from statistics import median

from analysis import prereg
from analysis.prereg import W, Window
from lowpoint.verdict import PricePoint, compute_verdict


@dataclass(frozen=True)
class Obs:
    """Linha de price_history: melhor oferta de uma coleta."""
    at: datetime
    price: Decimal
    original_price: Decimal | None
    available: bool


@dataclass(frozen=True)
class OfferObs:
    """Linha de offer_snapshots (P3 secundária e exploratório)."""
    at: datetime
    item_id: str
    price: Decimal
    original_price: Decimal | None
    deal_ids: tuple | None = None
    tags: tuple | None = None


@dataclass
class Dataset:
    obs: dict[str, list[Obs]]
    offers: dict[str, list[OfferObs]] = field(default_factory=dict)


# --- Básicos -----------------------------------------------------------------

def _valid(obs, window: Window) -> list[Obs]:
    """Coletas disponíveis na janela ("available = false é descartada")."""
    return sorted((o for o in obs if o.available and window.contains(o.at)), key=lambda o: o.at)


def has_streak(flags: list[bool], k: int = prereg.STREAK) -> bool:
    run = 0
    for f in flags:
        run = run + 1 if f else 0
        if run >= k:
            return True
    return False


@dataclass(frozen=True)
class Coverage:
    n: int
    expected: Decimal
    ratio: Decimal | None
    ok: bool
    partial: bool


def coverage(obs, window: Window, now: datetime) -> Coverage:
    """"Cobertura mínima": coletas disponíveis / esperadas, só no trecho já decorrido."""
    end = min(now, window.end)
    partial = now < window.end
    if end <= window.start:
        return Coverage(0, Decimal(0), None, False, partial)
    hours = Decimal(int((end - window.start).total_seconds())) / Decimal(3600)
    expected = hours * window.rate
    n = sum(1 for o in obs if o.available and window.start <= o.at < end)
    ratio = min(Decimal(1), Decimal(n) / expected)
    return Coverage(n, expected, ratio, ratio >= prereg.MIN_COVERAGE, partial)


def reference(obs) -> Decimal | None:
    """"Referência": mediana da melhor oferta na B0."""
    prices = [o.price for o in _valid(obs, W["B0"])]
    return median(prices) if prices else None


def _median_before(obs, end: datetime) -> Decimal | None:
    prices = [o.price for o in obs if o.available and o.at < end]
    return median(prices) if prices else None


def _pct_below(ref: Decimal, price: Decimal) -> Decimal:
    return (ref - price) / ref


# --- P1a: o que o Lowpoint teria dito -----------------------------------------

@dataclass(frozen=True)
class P1aResult:
    verdicts: list[str]
    real_collections: int
    counts: bool
    any_one: bool
    max_discount: Decimal | None  # vs. baseline_price


def p1a_product(obs) -> P1aResult:
    """Replay de compute_verdict em cada coleta da BF, com o histórico até ela.

    Igual ao notify.py: histórico = price_history disponível até o instante
    (inclui a coleta atual, gravada antes do alerta), preço e riscado da melhor
    oferta, now = horário da coleta. Nada do futuro entra.
    """
    avail = sorted((o for o in obs if o.available), key=lambda o: o.at)
    points = [PricePoint(o.price, o.original_price, o.at) for o in avail]
    times = [o.at for o in avail]
    verdicts, discounts = [], []
    for o in avail:
        if not W["BF"].contains(o.at):
            continue
        history = points[: bisect_right(times, o.at)]
        v = compute_verdict(o.price, o.original_price, history, o.at)
        verdicts.append(v.verdict)
        if v.baseline_price:
            discounts.append(_pct_below(v.baseline_price, o.price))
    flags = [v == "real" for v in verdicts]
    return P1aResult(verdicts, sum(flags), has_streak(flags), any(flags),
                     max(discounts) if discounts else None)


# --- P1b: o que a régua fixa diz ----------------------------------------------

@dataclass(frozen=True)
class P1bResult:
    real_collections: int
    counts: bool
    any_one: bool
    max_discount: Decimal | None  # vs. Referência
    real_times: tuple = ()


def p1b_product(obs, ref: Decimal) -> P1bResult:
    bf = _valid(obs, W["BF"])
    limit = ref * (1 - prereg.REAL)
    flags = [o.price <= limit for o in bf]
    disc = max((_pct_below(ref, o.price) for o in bf), default=None)
    times = tuple(o.at for o, f in zip(bf, flags) if f)
    return P1bResult(sum(flags), has_streak(flags), any(flags), disc, times)


# --- P2: maquiagem --------------------------------------------------------------

@dataclass(frozen=True)
class P2Result:
    max_pre: Decimal | None
    min_bf: Decimal | None
    hike: bool
    retreat: bool
    fachada: bool
    classification: str  # maquiagem | subiu_mas_real | subiu_sem_recuo | sem_padrao | sem dados
    min_bf_at: datetime | None = None


def p2_product(obs, ref: Decimal) -> P2Result:
    pre, bf = _valid(obs, W["PRE"]), _valid(obs, W["BF"])
    if not pre or not bf:
        return P2Result(None, None, False, False, False, "sem dados")
    max_pre = max(o.price for o in pre)
    low = min(bf, key=lambda o: (o.price, o.at))
    min_bf = low.price
    hike = max_pre >= ref * (1 + prereg.HIKE)
    retreat = min_bf <= max_pre * (1 - prereg.RETREAT)
    fachada = min_bf >= ref * (1 - prereg.FACHADA)
    if hike and retreat:
        cls = "maquiagem" if fachada else "subiu_mas_real"
    elif hike:
        cls = "subiu_sem_recuo"
    else:
        cls = "sem_padrao"
    return P2Result(max_pre, min_bf, hike, retreat, fachada, cls, low.at)


# --- P3: preço riscado ---------------------------------------------------------

@dataclass(frozen=True)
class P3Result:
    with_strike: int
    inflated: int
    classification: str  # inflado | honesto | sem_riscado


def p3_product(obs, ref: Decimal) -> P3Result:
    bf = [o for o in _valid(obs, W["BF"]) if o.original_price is not None]
    inflated = sum(1 for o in bf if o.original_price / ref > prereg.INFLATED)
    if not bf:
        return P3Result(0, 0, "sem_riscado")
    cls = "inflado" if Decimal(inflated) / len(bf) > Decimal("0.5") else "honesto"
    return P3Result(len(bf), inflated, cls)


def p3_secondary(offers) -> tuple[int, int]:
    """Por anúncio: riscado na BF / mediana do próprio item na B0. (n, n > 1,10)."""
    b0 = {}
    for o in offers:
        if W["B0"].contains(o.at):
            b0.setdefault(o.item_id, []).append(o.price)
    n = inflated = 0
    for o in offers:
        if W["BF"].contains(o.at) and o.original_price is not None and o.item_id in b0:
            n += 1
            inflated += o.original_price / median(b0[o.item_id]) > prereg.INFLATED
    return n, inflated


# --- P4: quando foi o menor preço ---------------------------------------------

@dataclass(frozen=True)
class P4Result:
    mins: dict[str, Decimal]
    winner: str  # antes | BF | POS | empate | sem dados


def p4_winner(mins: dict[str, Decimal]) -> str:
    ranked = sorted(mins.items(), key=lambda kv: kv[1])
    (best, low), (_, second) = ranked[0], ranked[1]
    if second > 0 and (second - low) / second >= prereg.P4_TIE:
        return best
    return "empate"


def p4_product(obs) -> P4Result:
    periods = {"antes": prereg.ANTES, "BF": W["BF"], "POS": W["POS"]}
    mins = {}
    for name, w in periods.items():
        v = _valid(obs, w)
        if v:
            mins[name] = min(o.price for o in v)
    if len(mins) < 3:
        return P4Result(mins, "sem dados")
    return P4Result(mins, p4_winner(mins))


# --- P5: controles ------------------------------------------------------------

@dataclass(frozen=True)
class P5Result:
    var_bf: Decimal | None
    amplitude: Decimal | None


def p5_product(obs, ref: Decimal) -> P5Result:
    bf = _valid(obs, W["BF"])
    all_ = _valid(obs, prereg.PERIODO)
    var = (median([o.price for o in bf]) - ref) / ref if bf else None
    amp = (max(o.price for o in all_) - min(o.price for o in all_)) / ref if all_ else None
    return P5Result(var, amp)


# --- Manchetes (seção de cada pergunta) ----------------------------------------

def p1_headline(n_yes: int, n_covered: int) -> str:
    """Emenda 2: proporção dos 18 com cobertura (≥ 10/18, ≤ 4/18)."""
    share = Fraction(n_yes, n_covered)
    if share >= prereg.P1_MAJORITY:
        return "a maioria teve"
    if share <= prereg.P1_NONE:
        return "não teve"
    return "uma minoria teve"


def p2_headline(n20: int, n18: int, n18_covered: int) -> str:
    """"Sim" com ≥ 1 produto; "foi comum" com ≥ 5/18 dos cobertos (Emenda 2)."""
    if n20 < 1:
        return "não houve maquiagem"
    common = Fraction(n18, n18_covered) >= prereg.P2_COMMON
    return "sim, houve maquiagem" + ("; foi comum" if common else "")


def p3_headline(inflated: int, with_strike: int) -> str | None:
    if with_strike == 0:
        return None
    share = Decimal(inflated) / with_strike
    if share >= Decimal("0.5"):
        return "não é honesto"
    if share <= Decimal("0.2"):
        return "é honesto"
    return "depende do produto"


def p4_headline(winners18: list[str]) -> str:
    n = len(winners18)
    if winners18.count("BF") * 2 >= n:
        return "sim, a BF foi o melhor momento"
    if winners18.count("POS") * 2 >= n:
        return "não, valeu esperar"
    return "sem padrão"


def p5_answer(controls_ok: list[bool], median_abs_var18: Decimal) -> str:
    # Leitura do texto: "os 18 parados" já responde "não"; senão, 2 controles
    # no esperado = "sim", só um = "misto", nenhum = "não".
    if median_abs_var18 < prereg.P5_FLAT:
        return "não"
    ok = sum(controls_ok)
    return {2: "sim", 1: "misto"}.get(ok, "não")


# --- Execução completa ---------------------------------------------------------

QUESTION_WINDOWS = {
    "P1a": ("BF",),
    "P1b": ("B0", "BF"),
    "P2": ("B0", "PRE", "BF"),
    "P3": ("B0", "BF"),
    "P4": ("B0", "PRE", "BF", "POS"),
    "P5": ("B0", "PRE", "BF", "POS"),
}


@dataclass
class Row:
    catalog_id: str
    label: str
    group: str
    result: str
    detail: dict = field(default_factory=dict)


@dataclass
class Question:
    status: str  # ok | incompleto
    reason: str
    rows: list[Row] = field(default_factory=list)
    headline: str | None = None
    extra: dict = field(default_factory=dict)
    excluded: list[tuple[str, str]] = field(default_factory=list)  # (produto, motivo)


@dataclass(frozen=True)
class RefInfo:
    n: int
    ref: Decimal | None
    partial: bool


@dataclass
class Results:
    now: datetime
    window_status: dict[str, str]
    coverage: dict[str, dict[str, Coverage]]
    b0_partial: dict[str, RefInfo]
    questions: dict[str, Question]
    exploratory: dict


def _fmt_end(w: Window) -> str:
    return w.end.astimezone(prereg.BRT).strftime("%d/%m %H:%M")


def run_all(data: Dataset, now: datetime) -> Results:
    obs = {p.catalog_id: data.obs.get(p.catalog_id, []) for p in prereg.PRODUCTS}
    status = {w.name: w.status(now) for w in prereg.WINDOWS}
    cov = {cid: {w.name: coverage(s, w, now) for w in prereg.WINDOWS} for cid, s in obs.items()}
    b0 = {cid: RefInfo(len(_valid(s, W["B0"])), reference(s), status["B0"] != "completa")
          for cid, s in obs.items()}

    questions = {}
    for q, wins in QUESTION_WINDOWS.items():
        pending = [W[n] for n in wins if status[n] != "completa"]
        if pending:
            reason = "janela " + ", ".join(f"{w.name} termina em {_fmt_end(w)}" for w in pending)
            questions[q] = Question("incompleto", reason)
            continue
        questions[q] = _answer(q, wins, obs, cov, b0, data)

    return Results(now, status, cov, b0, questions, _exploratory(data, obs, status, now))


def _pct_txt(x) -> str:
    return f"{x * 100:.1f}%".replace(".", ",")


def _answer(q, wins, obs, cov, b0, data) -> Question:
    """Emenda 2: produto sem cobertura sai só desta pergunta; manchete exige
    ≥ MIN_COVERED dos 18 não-controle (e, no P5, os 2 controles)."""
    base = prereg.NON_CONTROL if q == "P3" else prereg.PRODUCTS  # P3: base dos 18
    rows, excluded, res = [], [], {}
    for p in base:
        c = cov[p.catalog_id]
        bad = [f"{n} {_pct_txt(c[n].ratio or 0)}" for n in wins if not c[n].ok]
        ref = b0[p.catalog_id].ref
        if bad or ref is None:
            reason = ("cobertura < 70%: " + ", ".join(bad)) if bad else "B0 sem coletas"
            excluded.append((p.label, reason))
            rows.append(Row(p.catalog_id, p.label, p.group, "excluído", {"motivo": reason}))
            continue
        r = _product_result(q, obs[p.catalog_id], ref, data.offers.get(p.catalog_id, []))
        res[p.catalog_id] = r
        rows.append(Row(p.catalog_id, p.label, p.group, r["result"], r))

    n18 = sum(1 for p in prereg.NON_CONTROL if p.catalog_id in res)
    if n18 < prereg.MIN_COVERED:
        reason = f"só {n18} de 18 com cobertura (mínimo {prereg.MIN_COVERED})"
        return Question("incompleto", reason, rows, excluded=excluded)
    missing_ctrl = [p.label for p in prereg.CONTROLS if p.catalog_id not in res]
    if q == "P5" and missing_ctrl:
        reason = "controle sem cobertura: " + ", ".join(missing_ctrl)
        return Question("incompleto", reason, rows, excluded=excluded)
    headline, extra = _headline(q, res)
    return Question("ok", "", rows, headline, extra, excluded)


def _product_result(q, s, ref, offers) -> dict:
    if q == "P1a":
        r = p1a_product(s)
        return {"result": "sim" if r.counts else "não", "coletas real": r.real_collections,
                "≥1 coleta": r.any_one, "maior desconto": r.max_discount}
    if q == "P1b":
        r = p1b_product(s, ref)
        return {"result": "sim" if r.counts else "não", "coletas ≤ Ref×0,95": r.real_collections,
                "≥1 coleta": r.any_one, "maior desconto": r.max_discount, "Ref": ref}
    if q == "P2":
        r = p2_product(s, ref)
        return {"result": r.classification, "Ref": ref, "máx Pré-BF": r.max_pre, "mín BF": r.min_bf}
    if q == "P3":
        r = p3_product(s, ref)
        n2, i2 = p3_secondary(offers)
        return {"result": r.classification, "coletas com riscado": r.with_strike,
                "infladas": r.inflated, "anúncios comparados": n2, "anúncios > 1,10": i2}
    if q == "P4":
        r = p4_product(s)
        d = {"result": r.winner, **{f"mín {k}": v for k, v in r.mins.items()}}
        if "BF" in r.mins and "POS" in r.mins:
            d["POS vs BF"] = (r.mins["POS"] - r.mins["BF"]) / r.mins["BF"]
        return d
    if q == "P5":
        r = p5_product(s, ref)
        a, b, c = p1a_product(s), p1b_product(s, ref), p2_product(s, ref)
        expected = (r.var_bf is not None and abs(r.var_bf) < prereg.P5_FLAT
                    and not a.counts and not b.counts and c.classification != "maquiagem")
        return {"result": "no esperado" if expected else "fora do esperado",
                "var BF vs Ref": r.var_bf, "amplitude": r.amplitude,
                "P1a": a.counts, "P1b": b.counts, "P2": c.classification, "_expected": expected}
    raise ValueError(q)


def _headline(q, res) -> tuple[str | None, dict]:
    ctrl = {p.catalog_id for p in prereg.CONTROLS}
    non = [cid for cid in res if cid not in ctrl]
    if q in ("P1a", "P1b"):
        n20 = sum(r["result"] == "sim" for r in res.values())
        n18 = sum(res[c]["result"] == "sim" for c in non)
        return p1_headline(n18, len(non)), {
            "sim (todos com cobertura)": n20, "todos com cobertura": len(res),
            "sim (18)": n18, "de 18 com cobertura": len(non)}
    if q == "P2":
        n20 = sum(r["result"] == "maquiagem" for r in res.values())
        n18 = sum(res[c]["result"] == "maquiagem" for c in non)
        real = sum(r["result"] == "subiu_mas_real" for r in res.values())
        return p2_headline(n20, n18, len(non)), {
            "maquiagem (todos com cobertura)": n20, "todos com cobertura": len(res),
            "maquiagem (18)": n18, "de 18 com cobertura": len(non), "subiu mas real": real}
    if q == "P3":
        with_s = [r for r in res.values() if r["result"] != "sem_riscado"]
        infl = sum(r["result"] == "inflado" for r in with_s)
        return p3_headline(infl, len(with_s)), {"com riscado": len(with_s), "inflados": infl}
    if q == "P4":
        winners = [res[c]["result"] for c in non]
        diffs = [res[c]["POS vs BF"] for c in non if "POS vs BF" in res[c]]
        return p4_headline(winners), {**Counter(winners),
                                      "mediana POS vs BF (18)": median(diffs) if diffs else None}
    if q == "P5":
        ok = [res[p.catalog_id]["_expected"] for p in prereg.CONTROLS]
        vars18 = [abs(res[c]["var BF vs Ref"]) for c in non if res[c]["var BF vs Ref"] is not None]
        med = median(vars18) if vars18 else Decimal(0)
        return p5_answer(ok, med), {"controles no esperado": sum(ok), "mediana |var| dos 18": med}
    raise ValueError(q)


# --- Exploratório (não altera P1–P5) ----------------------------------------------

def _exploratory(data, obs, status, now) -> dict:
    deals = {}
    for w in prereg.WINDOWS:
        if status[w.name] == "futura":
            continue
        offers = [o for cid in data.offers for o in data.offers[cid]
                  if w.contains(o.at) and o.at >= prereg.EMENDA1_START and o.tags is not None]
        if not offers:
            continue
        tags = Counter(t for o in offers for t in (o.tags or ()))
        deals[w.name] = {
            "ofertas": len(offers),
            "com deal": sum(1 for o in offers if o.deal_ids),
            "deal_ids": Counter(d for o in offers for d in (o.deal_ids or ())).most_common(5),
            "tags": tags.most_common(10),
            "parcial": status[w.name] != "completa",
        }

    long_ref = {}
    for p in prereg.PRODUCTS:
        if p.watch_id not in prereg.LONG_REF_WATCHES:
            continue
        s = obs[p.catalog_id]
        first = min((o.at for o in s if o.available), default=None)
        item = {"desde": first, "Ref longa": _median_before(s, W["PRE"].start),
                "Ref B0": reference(s), "parcial": status["B0"] != "completa"}
        if status["BF"] == "completa" and item["Ref longa"]:
            item["P1b (Ref longa)"] = p1b_product(s, item["Ref longa"]).counts
            item["P2 (Ref longa)"] = p2_product(s, item["Ref longa"]).classification
        long_ref[p.label] = item
    return {"deals_tags": deals, "ref_longa": long_ref}
