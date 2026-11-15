"""[TESTE] Report e gráficos com dados sintéticos em parquet (sem banco)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("pyarrow")
pytest.importorskip("matplotlib")

import lowpoint.config  # noqa: E402
from analysis import charts, prereg, report  # noqa: E402

BRT = prereg.BRT


def _write_data(tmp_path, until):
    rows, offers = [], []
    for p in prereg.PRODUCTS:
        t = prereg.WINDOWS[0].start
        while t < until:
            at = t.astimezone(timezone.utc)
            rows.append(dict(catalog_product_id=p.catalog_id, price=Decimal("100.00"),
                             original_price=None, available=True, collected_at=at))
            offers.append(dict(catalog_product_id=p.catalog_id, item_id="MLBX1", price=Decimal("100.00"),
                               original_price=None, collected_at=at,
                               deal_ids=[] if at >= prereg.EMENDA1_START else None,
                               tags=["cart_eligible"] if at >= prereg.EMENDA1_START else None))
            t += timedelta(hours=1)
    d = tmp_path / "data"
    d.mkdir()
    pd.DataFrame(rows).to_parquet(d / "price_history.parquet")
    pd.DataFrame(offers).to_parquet(d / "offers.parquet")
    return d


def test_report_today_writes_text_and_charts(tmp_path, capsys):
    now = datetime(2026, 11, 15, 10, 0, tzinfo=BRT)
    data = _write_data(tmp_path, now)
    out = tmp_path / "out"
    code = report.main(["--no-export", "--data-dir", str(data), "--out", str(out)], now=now)
    assert code == 0
    text = (out / "relatorio.md").read_text(encoding="utf-8")
    assert "Confirmatório (P1–P5)" in text and "Exploratório" in text
    assert text.count("incompleto") >= 6
    assert "B0 parcial" in text
    assert "IBM Plex Mono não está instalada" not in text
    assert (out / "charts" / "resumo.png").exists()
    assert len(list((out / "charts").glob("w*.png"))) == 20
    assert "Confirmatório (P1–P5)" in capsys.readouterr().out


def test_report_refuses_when_guard_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(lowpoint.config, "REAL_DISCOUNT_THRESHOLD", Decimal("0.06"))
    out = tmp_path / "out"
    code = report.main(["--no-export", "--data-dir", str(tmp_path), "--out", str(out)])
    assert code == 2
    assert not out.exists()


def test_palette_has_brand_colors_and_no_red():
    assert charts.INK == "#0A0A0A" and charts.PAPER == "#F5F5F0"
    assert charts.FOREST == "#1B6B3A" and charts.OCHRE == "#7A5A10" and charts.MUTED == "#999999"
    for c in charts.PALETTE:
        r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
        assert not (r > 150 and g < 100 and b < 100), c


def test_plex_mono_is_bundled_and_registered():
    from pathlib import Path
    from matplotlib import font_manager as fm
    fonts = Path(charts.__file__).parent / "fonts"
    for f in ("IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf", "IBMPlexMono-Bold.ttf", "LICENSE.txt"):
        assert (fonts / f).exists(), f
    assert "SIL Open Font License" in (fonts / "LICENSE.txt").read_text(encoding="utf-8")
    family, warning = charts.pick_mono_font()
    assert family == "IBM Plex Mono" and warning is None
    medium = fm.findfont(fm.FontProperties(family="IBM Plex Mono", weight=500), fallback_to_default=False)
    assert medium.endswith("IBMPlexMono-Medium.ttf")


def test_report_after_cutoff_with_real_and_maquiagem(tmp_path, capsys):
    """Período completo: um produto com desconto real (Forest), um maquiado (Ochre)."""
    B0, PRE, BF, POS = prereg.WINDOWS
    real_id, mq_id = prereg.PRODUCTS[3].catalog_id, prereg.PRODUCTS[4].catalog_id
    lame = prereg.PRODUCTS[6]  # 60% de cobertura na BF: sai das perguntas, manchete segue
    rows = []
    for p in prereg.PRODUCTS:
        for w in prereg.WINDOWS:
            step = timedelta(minutes=15) if w.name == "BF" else timedelta(hours=1)
            t, i = w.start, 0
            while t < w.end:
                i += 1
                if p is lame and w.name == "BF" and (i - 1) % 5 >= 3:
                    t += step
                    continue
                price = Decimal("100.00")
                if p.catalog_id == real_id and w.name == "BF":
                    price = Decimal("80.00")
                if p.catalog_id == mq_id:
                    price = {"PRE": Decimal("150.00"), "BF": Decimal("100.00")}.get(w.name, price)
                rows.append(dict(catalog_product_id=p.catalog_id, price=price, original_price=None,
                                 available=True, collected_at=t.astimezone(timezone.utc)))
                t += step
    d = tmp_path / "data"
    d.mkdir()
    pd.DataFrame(rows).to_parquet(d / "price_history.parquet")
    out = tmp_path / "out"
    after = prereg.CUTOFF + timedelta(days=1)
    assert report.main(["--no-export", "--data-dir", str(d), "--out", str(out)], now=after) == 0
    text = (out / "relatorio.md").read_text(encoding="utf-8")
    assert "**Manchete:** não teve" in text           # P1a/P1b: 1 de 18
    assert "**Manchete:** sim, houve maquiagem" in text
    assert "incompleto" not in text
    assert f"Excluídos desta pergunta (1): {lame.label} (cobertura < 70%: BF 60,0%)" in text
    assert (out / "charts" / "resumo.png").stat().st_size > 0


def test_product_chart_publication_style(tmp_path, monkeypatch):
    """[TESTE] Versão de publicação: título só com o nome, rótulos PT, ticks nas fronteiras, BF marcada."""
    import matplotlib.colors as mcolors
    from matplotlib.patches import Rectangle
    captured = {}

    def fake_save(fig, path, attempts=3):
        ax = fig.axes[0]
        captured["title"] = ax.get_title(loc="left")
        captured["ticks"] = [t.get_text() for t in ax.get_xticklabels()]
        captured["texts"] = [t.get_text().strip() for t in ax.texts]
        spans = [p for p in ax.patches if isinstance(p, Rectangle)]
        captured["alphas"] = [mcolors.to_rgba(p.get_facecolor())[3] for p in spans]

    monkeypatch.setattr(charts, "_save", fake_save)
    family, _ = charts.pick_mono_font()
    charts._style(family)
    ps5 = prereg.PRODUCTS[0]
    charts.product_chart(tmp_path / "x.png", ps5, [], Decimal("4050"), True,
                         datetime(2026, 11, 15, 10, 0, tzinfo=BRT))
    assert captured["title"] == ps5.label
    assert captured["ticks"] == ["14/11", "17/11", "23/11", "28/11", "07/12"]
    for lab in ("B0", "PRÉ-BF", "BF", "PÓS-BF"):
        assert lab in captured["texts"]
    b0, pre, bf, pos = captured["alphas"]
    assert bf > 2 * max(b0, pre, pos)
