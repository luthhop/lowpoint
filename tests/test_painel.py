"""[TESTE] /api/painel com dados falsos: sem banco, sem rede.

Os dados de entrada trazem de propósito campos que nunca podem vazar
(alvo, chat_id, seller_id, item_id, silent, apelido, grupo) para provar que o
contrato é montado campo a campo.
"""
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from analysis import metrics, prereg
from lowpoint import painel
from lowpoint.painel import PainelData, PriceRow

BRT = prereg.BRT
UTC = timezone.utc
NOW = datetime(2026, 11, 15, 10, 30, tzinfo=BRT)

SECRET_VALUES = ["987654321", "MLB9999999999", "1234.56", "-1001234567890", "meu ps5"]
FORBIDDEN_KEYS = ["target", "alvo", "chat_id", "seller_id", "item_id", "silent", "nickname",
                  "apelido", "watch", "pessoal", "group", "grupo", "token"]


@dataclass(frozen=True)
class LeakyRow(PriceRow):
    """Linha com campos sensíveis pendurados (como um ORM traria): o payload não pode usar."""
    seller_id: int = 987654321
    item_id: str = "MLB9999999999"
    target_price: str = "1234.56"
    chat_id: int = -1001234567890
    nickname: str = "meu ps5"
    silent: bool = True


def _rows(start, end, price, step=timedelta(hours=1), available=True):
    out, t = [], start
    while t < end:
        out.append(LeakyRow(at=t.astimezone(UTC), price=Decimal(price), available=available))
        t += step
    return out


def _data(now=NOW, price="100.00", last=None, counts=None, extra=None):
    rows = {p.catalog_id: _rows(prereg.W["B0"].start, now, price) for p in prereg.PRODUCTS}
    if extra:
        rows.update(extra)
    # produto fora da allowlist (watch 1, LG 32"): nunca aparece
    rows["MLB24061510"] = _rows(prereg.W["B0"].start, now, "999.00")
    return PainelData(
        rows=rows,
        last_collection=last or (now - timedelta(minutes=45)),
        offer_counts=counts or {p.catalog_id: 10 for p in prereg.PRODUCTS},
    )


def _payload(**kw):
    return painel.build_payload(_data(**kw), now=kw.get("now", NOW))


# --- Contrato -----------------------------------------------------------------

def test_contract_keys_are_exactly_the_approved_ones():
    p = _payload()
    assert set(p) == {"versao", "gerado_em", "ultima_coleta", "coleta_atrasada", "amostragem",
                      "referencia", "produtos"}
    assert set(p["referencia"]) == {"definicao", "inicio", "fim", "parcial"}
    for prod in p["produtos"]:
        assert set(prod) == {"id", "nome", "categoria", "url", "preco_atual", "preco_atual_em",
                             "disponivel", "poucas_ofertas", "referencia", "vs_referencia_pct", "serie"}


def test_exactly_the_20_preregistered_products_in_fixed_order():
    ids = [x["id"] for x in _payload()["produtos"]]
    assert len(ids) == 20
    assert set(ids) == {p.catalog_id for p in prereg.PRODUCTS}
    assert "MLB24061510" not in ids  # watch 1 fora da allowlist


def test_categories_hide_which_products_are_personal():
    cats = {x["id"]: x["categoria"] for x in _payload()["produtos"]}
    assert set(cats.values()) == {"TV e áudio", "Celular e computador", "Casa", "Games", "Controle"}
    assert cats["MLB57081243"] == "Games"                 # PS5
    assert cats["MLB79391475"] == "Celular e computador"  # LG 27"
    assert cats["MLB59323822"] == "Celular e computador"  # AOC 27"
    assert cats["MLB26967981"] == cats["MLB19400333"] == "Controle"
    order = [x["categoria"] for x in _payload()["produtos"]]
    assert order == sorted(order, key=painel.CATEGORY_ORDER.index)


def test_body_never_contains_forbidden_fields_or_values():
    status, headers, body = painel.handle_painel("GET", "/api/painel", now=NOW, fetch=lambda: _data())
    assert status == 200
    text = body.decode("utf-8").lower()
    for key in FORBIDDEN_KEYS:
        assert f'"{key}' not in text, key
    for value in SECRET_VALUES:
        assert value.lower() not in text, value


def test_url_is_the_public_catalog_link_and_money_is_string():
    prod = _payload()["produtos"][0]
    assert prod["url"] == f"https://www.mercadolivre.com.br/p/{prod['id']}"
    assert prod["preco_atual"] == "100.00" and prod["referencia"] == "100.00"
    assert all(isinstance(pt[1], str) for pt in prod["serie"])


# --- Referência -------------------------------------------------------------------

def test_reference_is_partial_until_b0_ends_and_matches_analysis():
    p = _payload()
    assert p["referencia"]["parcial"] is True
    assert p["referencia"]["inicio"] == "2026-11-14T17:50:00Z"
    assert p["referencia"]["fim"] == "2026-11-17T17:50:00Z"
    after = datetime(2026, 11, 17, 14, 50, tzinfo=BRT)
    assert _payload(now=after)["referencia"]["parcial"] is False

    data = _data()
    ps5 = prereg.PRODUCTS[0].catalog_id
    obs = [metrics.Obs(r.at, r.price, None, r.available) for r in data.rows[ps5]]
    prod = next(x for x in painel.build_payload(data, now=NOW)["produtos"] if x["id"] == ps5)
    assert Decimal(prod["referencia"]) == metrics.reference(obs)


@pytest.mark.parametrize("price, pct", [
    ("92.79", "-7.2"),   # −7,21% → trunca para −7,2 (nunca exagera)
    ("92.71", "-7.2"),   # −7,29% → −7,2
    ("107.29", "7.2"),
    ("100.00", "0.0"),
    ("99.99", "0.0"),    # −0,01% → 0,0
])
def test_pct_vs_reference_truncates_toward_zero(price, pct):
    ps5 = prereg.PRODUCTS[0].catalog_id
    rows = _rows(prereg.W["B0"].start, NOW - timedelta(hours=1), "100.00")
    rows.append(PriceRow(at=(NOW - timedelta(minutes=30)).astimezone(UTC), price=Decimal(price), available=True))
    prod = next(x for x in _payload(extra={ps5: rows})["produtos"] if x["id"] == ps5)
    assert prod["vs_referencia_pct"] == pct


# --- Série --------------------------------------------------------------------------

def test_series_is_last_available_price_per_3h_block_from_b0():
    ps5 = prereg.PRODUCTS[0].catalog_id
    b0 = prereg.W["B0"].start  # 14/11 14:50 BRT
    rows = [
        PriceRow(datetime(2026, 11, 14, 14, 0, tzinfo=BRT).astimezone(UTC), Decimal("1"), True),   # antes da B0
        PriceRow(b0.astimezone(UTC), Decimal("10"), True),                                           # bloco 12–15h
        PriceRow(datetime(2026, 11, 14, 15, 10, tzinfo=BRT).astimezone(UTC), Decimal("20"), True),  # bloco 15–18h
        PriceRow(datetime(2026, 11, 14, 16, 10, tzinfo=BRT).astimezone(UTC), Decimal("21"), True),
        PriceRow(datetime(2026, 11, 14, 17, 10, tzinfo=BRT).astimezone(UTC), Decimal("0"), False),  # indisponível no meio
        PriceRow(datetime(2026, 11, 14, 18, 10, tzinfo=BRT).astimezone(UTC), Decimal("30"), True),  # bloco 18–21h
    ]
    prod = next(x for x in _payload(extra={ps5: rows})["produtos"] if x["id"] == ps5)
    assert prod["serie"] == [["2026-11-14T17:50:00Z", "10.00"], ["2026-11-14T18:00:00Z", "21.00"],
                             ["2026-11-14T21:00:00Z", "30.00"]]


def test_unavailable_latest_collection_hides_last_price():
    """[TESTE] Termos ML 5.2: sem oferta disponível, o JSON público não traz o último preço."""
    ps5 = prereg.PRODUCTS[0].catalog_id
    rows = _rows(prereg.W["B0"].start, NOW - timedelta(hours=1), "100.00")
    rows.append(PriceRow(at=(NOW - timedelta(minutes=30)).astimezone(UTC), price=Decimal("0"), available=False))
    prod = next(x for x in _payload(extra={ps5: rows})["produtos"] if x["id"] == ps5)
    assert prod["disponivel"] is False
    assert prod["preco_atual"] is None
    assert prod["preco_atual_em"] is None
    assert prod["vs_referencia_pct"] is None
    assert prod["referencia"] == "100.00"  # a Referência é da B0, não é preço atual
    assert prod["serie"] == []  # o último ponto da série seria o último preço


def test_unavailable_body_has_no_price_besides_reference():
    """[TESTE] Termos ML 5.2: nenhum valor de preço do produto indisponível no JSON além da Referência."""
    ps5 = prereg.PRODUCTS[0].catalog_id
    rows = _rows(prereg.W["B0"].start, NOW - timedelta(hours=1), "123.45")
    rows[-1] = PriceRow(at=rows[-1].at, price=Decimal("111.11"), available=True)
    rows.append(PriceRow(at=(NOW - timedelta(minutes=30)).astimezone(UTC), price=Decimal("0"), available=False))
    prod = next(x for x in _payload(extra={ps5: rows})["produtos"] if x["id"] == ps5)
    assert "111.11" not in json.dumps(prod)


def test_available_again_shows_price():
    ps5 = prereg.PRODUCTS[0].catalog_id
    rows = _rows(prereg.W["B0"].start, NOW - timedelta(hours=2), "100.00")
    rows.append(PriceRow(at=(NOW - timedelta(minutes=90)).astimezone(UTC), price=Decimal("0"), available=False))
    rows.append(PriceRow(at=(NOW - timedelta(minutes=30)).astimezone(UTC), price=Decimal("95.00"), available=True))
    prod = next(x for x in _payload(extra={ps5: rows})["produtos"] if x["id"] == ps5)
    assert prod["disponivel"] is True and prod["preco_atual"] == "95.00"
    assert prod["vs_referencia_pct"] is not None


def test_product_without_any_data_is_listed_with_nulls():
    ps5 = prereg.PRODUCTS[0].catalog_id
    prod = next(x for x in _payload(extra={ps5: []})["produtos"] if x["id"] == ps5)
    assert prod["preco_atual"] is None and prod["referencia"] is None
    assert prod["vs_referencia_pct"] is None and prod["serie"] == [] and prod["disponivel"] is False


def test_few_offers_flag_below_3():
    counts = {p.catalog_id: 10 for p in prereg.PRODUCTS}
    counts["MLB48808732"] = 2  # TV TCL
    counts["MLB1055309009"] = 3  # iPhone: 3 não é "poucas"
    prods = {x["id"]: x for x in _payload(counts=counts)["produtos"]}
    assert prods["MLB48808732"]["poucas_ofertas"] is True
    assert prods["MLB1055309009"]["poucas_ofertas"] is False


@pytest.mark.parametrize("minutes, late", [(90, False), (91, True)])
def test_collection_late_after_90_minutes(minutes, late):
    p = _payload(last=NOW - timedelta(minutes=minutes))
    assert p["coleta_atrasada"] is late


# --- HTTP ------------------------------------------------------------------------------

class CountingFetch:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return _data()


@pytest.fixture(autouse=True)
def _clear_memo():
    painel.clear_memo()
    yield
    painel.clear_memo()


@pytest.fixture(autouse=True)
def _painel_on(monkeypatch):
    """Os testes de contrato rodam com o interruptor ligado; os de desligado limpam a env."""
    monkeypatch.setenv("PAINEL_ENABLED", "true")


# --- Interruptor PAINEL_ENABLED ---------------------------------------------------------

@pytest.mark.parametrize("value", [None, "", "false", "0", "TRUE", "True", " true", "yes"])
@pytest.mark.parametrize("method", ["GET", "HEAD", "POST"])
def test_off_is_404_without_touching_the_db(monkeypatch, value, method):
    if value is None:
        monkeypatch.delenv("PAINEL_ENABLED", raising=False)
    else:
        monkeypatch.setenv("PAINEL_ENABLED", value)
    fetch = CountingFetch()
    status, headers, body = painel.handle_painel(method, "/api/painel", now=NOW, fetch=fetch)
    assert status == 404 and fetch.calls == 0
    # no-store: ao religar, a CDN não fica servindo o 404 por 1h.
    assert headers["Cache-Control"] == "no-store"
    # CORS no 404: o site precisa ler o status para mostrar "fora do ar".
    assert headers["Access-Control-Allow-Origin"] == "https://lowpoint-web.vercel.app"
    assert json.loads(body) == {"erro": "fora do ar"}


def test_off_never_serves_memoized_payload(monkeypatch):
    fetch = CountingFetch()
    assert painel.handle_painel("GET", "/api/painel", now=NOW, fetch=fetch)[0] == 200
    monkeypatch.setenv("PAINEL_ENABLED", "false")
    status, _, body = painel.handle_painel("GET", "/api/painel", now=NOW, fetch=fetch)
    assert status == 404 and b"produtos" not in body and fetch.calls == 1


def test_off_with_query_string_is_still_404(monkeypatch):
    monkeypatch.setenv("PAINEL_ENABLED", "false")
    assert painel.handle_painel("GET", "/api/painel?x=1", now=NOW, fetch=CountingFetch())[0] == 404


def test_on_is_200():
    fetch = CountingFetch()
    assert painel.handle_painel("GET", "/api/painel", now=NOW, fetch=fetch)[0] == 200
    assert fetch.calls == 1


@pytest.mark.parametrize("path", ["/api/painel?x=1", "/api/painel?", "/api/painel?_=123"])
def test_any_query_string_is_400_without_touching_the_db(path):
    fetch = CountingFetch()
    status, headers, body = painel.handle_painel("GET", path, now=NOW, fetch=fetch)
    assert status == 400 and fetch.calls == 0
    assert headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
def test_only_get_and_head(method):
    fetch = CountingFetch()
    status, headers, _ = painel.handle_painel(method, "/api/painel", now=NOW, fetch=fetch)
    assert status == 405 and fetch.calls == 0
    assert headers["Allow"] == "GET, HEAD"


def test_get_has_cache_and_cors_headers():
    status, headers, body = painel.handle_painel("GET", "/api/painel", now=NOW, fetch=CountingFetch())
    assert status == 200
    assert headers["Cache-Control"] == "public, max-age=300, s-maxage=3600, stale-while-revalidate=3600"
    assert headers["Access-Control-Allow-Origin"] == "https://lowpoint-web.vercel.app"
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    assert json.loads(body)["versao"] == 1


def test_head_has_no_body():
    status, headers, body = painel.handle_painel("HEAD", "/api/painel", now=NOW, fetch=CountingFetch())
    assert status == 200 and body == b""


def test_db_error_is_503_no_store_without_details():
    def boom():
        raise RuntimeError("connection to server at secret-host failed")
    status, headers, body = painel.handle_painel("GET", "/api/painel", now=NOW, fetch=boom)
    assert status == 503 and headers["Cache-Control"] == "no-store"
    assert b"secret-host" not in body


def test_db_error_503_has_cors_so_the_site_can_read_the_status():
    def boom():
        raise RuntimeError("x")
    _, headers, _ = painel.handle_painel("GET", "/api/painel", now=NOW, fetch=boom)
    assert headers["Access-Control-Allow-Origin"] == "https://lowpoint-web.vercel.app"


class FlakyFetch(CountingFetch):
    """Funciona na 1ª chamada e falha nas seguintes (Neon caiu depois)."""
    def __call__(self):
        self.calls += 1
        if self.calls > 1:
            raise RuntimeError("connection to server at secret-host failed")
        return _data()


@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_db_error_serves_last_good_payload(method):
    fetch = FlakyFetch()
    _, _, good = painel.handle_painel("GET", "/api/painel", now=NOW, fetch=fetch)
    later = NOW + timedelta(minutes=30)  # memo vencido: tenta o banco e falha
    status, headers, body = painel.handle_painel(method, "/api/painel", now=later, fetch=fetch)
    assert status == 200 and fetch.calls == 2
    assert body == (b"" if method == "HEAD" else good)  # mesmo JSON, com o gerado_em antigo
    # cache curto: volta a tentar o banco logo, sem a CDN segurar o antigo por 1h
    assert headers["Cache-Control"] == painel.CACHE_STALE == "public, max-age=60, s-maxage=60"
    assert headers["Access-Control-Allow-Origin"] == "https://lowpoint-web.vercel.app"
    assert b"secret-host" not in body


def test_stale_fallback_does_not_refresh_memo_and_retries_db():
    fetch = FlakyFetch()
    painel.handle_painel("GET", "/api/painel", now=NOW, fetch=fetch)
    painel.handle_painel("GET", "/api/painel", now=NOW + timedelta(minutes=30), fetch=fetch)
    painel.handle_painel("GET", "/api/painel", now=NOW + timedelta(minutes=31), fetch=fetch)
    assert fetch.calls == 3  # cada pedido com memo vencido tenta o banco de novo


def test_stale_fallback_then_recovery_serves_fresh_payload():
    fetch = FlakyFetch()
    painel.handle_painel("GET", "/api/painel", now=NOW, fetch=fetch)
    painel.handle_painel("GET", "/api/painel", now=NOW + timedelta(minutes=30), fetch=fetch)
    fetch.calls = 0  # banco voltou
    recovered = NOW + timedelta(minutes=31)
    status, headers, body = painel.handle_painel("GET", "/api/painel", now=recovered, fetch=fetch)
    assert status == 200 and headers["Cache-Control"] == painel.CACHE_OK
    assert json.loads(body)["gerado_em"] == recovered.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_db_error_without_any_good_payload_is_still_503():
    def boom():
        raise RuntimeError("x")
    assert painel.handle_painel("GET", "/api/painel", now=NOW, fetch=boom)[0] == 503


def test_off_switch_wins_over_stale_payload(monkeypatch):
    fetch = FlakyFetch()
    painel.handle_painel("GET", "/api/painel", now=NOW, fetch=fetch)
    monkeypatch.setenv("PAINEL_ENABLED", "false")
    assert painel.handle_painel("GET", "/api/painel", now=NOW + timedelta(minutes=30), fetch=fetch)[0] == 404


def test_memo_avoids_second_db_hit_within_5_minutes():
    fetch = CountingFetch()
    painel.handle_painel("GET", "/api/painel", now=NOW, fetch=fetch)
    painel.handle_painel("GET", "/api/painel", now=NOW + timedelta(minutes=4), fetch=fetch)
    assert fetch.calls == 1
    painel.handle_painel("GET", "/api/painel", now=NOW + timedelta(minutes=6), fetch=fetch)
    assert fetch.calls == 2


def test_vercel_routes_painel():
    from pathlib import Path
    cfg = json.loads((Path(__file__).resolve().parent.parent / "vercel.json").read_text(encoding="utf-8"))
    assert {"src": "api/painel.py", "use": "@vercel/python"} in cfg["builds"]
    assert any(r["src"] == "/api/painel" and r["dest"] == "/api/painel.py" for r in cfg["routes"])
