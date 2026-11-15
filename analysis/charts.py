"""Gráficos da análise com a identidade do Lowpoint.

Ink/Paper fazem o trabalho; Forest só para desconto real, Ochre só para
"segura" (maquiagem); Muted para apoio. Nada de vermelho.
"""
import os
import time
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

from analysis import metrics, prereg  # noqa: E402

INK = "#0A0A0A"
PAPER = "#F5F5F0"
FOREST = "#1B6B3A"
OCHRE = "#7A5A10"
MUTED = "#999999"
PALETTE = (INK, PAPER, FOREST, OCHRE, MUTED)

_FALLBACKS = ("DejaVu Sans Mono", "Consolas", "Courier New", "monospace")
# TTF oficiais da IBM (github.com/IBM/plex, v2.005), licença OFL em fonts/LICENSE.txt.
FONT_DIR = Path(__file__).resolve().parent / "fonts"


def _register_bundled_fonts() -> None:
    known = {f.fname for f in font_manager.fontManager.ttflist}
    for ttf in sorted(FONT_DIR.glob("*.ttf")):
        if str(ttf) not in known:
            font_manager.fontManager.addfont(str(ttf))


def pick_mono_font() -> tuple[str, str | None]:
    _register_bundled_fonts()
    names = {f.name for f in font_manager.fontManager.ttflist}
    if "IBM Plex Mono" in names:
        return "IBM Plex Mono", None
    for f in _FALLBACKS:
        if f in names or f == "monospace":
            return f, (f"IBM Plex Mono não encontrada em {FONT_DIR}; gráficos usam {f}.")
    raise AssertionError("unreachable")


def _style(font: str) -> None:
    plt.rcParams.update({
        "font.family": font, "font.size": 9, "font.weight": 500,  # marca: Plex Mono 500/700
        "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER,
        "axes.edgecolor": INK, "axes.labelcolor": INK, "text.color": INK,
        "xtick.color": INK, "ytick.color": INK,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.prop_cycle": matplotlib.cycler(color=[INK]),
    })


def _save(fig, path: Path, attempts: int = 3) -> None:
    """Grava em temporário e troca. No Windows, um PNG recém-lido (antivírus,
    pré-visualização) pode ficar travado por um instante: tenta de novo."""
    tmp = path.with_name(path.stem + ".tmp" + path.suffix)
    fig.savefig(tmp, dpi=130)
    for i in range(attempts):
        try:
            os.replace(tmp, path)
            return
        except OSError:
            if i == attempts - 1:
                raise
            time.sleep(1.0)


def _brl(x, _pos=None) -> str:
    """R$ no padrão brasileiro; centavos abaixo de R$ 100 (eixo de pilha/livro)."""
    txt = f"{x:,.2f}" if abs(x) < 100 else f"{x:,.0f}"
    return "R$ " + txt.replace(",", "X").replace(".", ",").replace("X", ".")


# Versão de publicação: só apresentação, nenhuma métrica depende disto.
WINDOW_LABELS = {"B0": "B0", "PRE": "PRÉ-BF", "BF": "BF", "POS": "PÓS-BF"}
WINDOW_ALPHA = {"B0": 0.06, "PRE": 0.06, "BF": 0.30, "POS": 0.06}


def window_ticks() -> list[tuple[datetime, str]]:
    """Ticks nas fronteiras das janelas. O fim é exclusivo (08/12 00:00), então
    a última fronteira leva o rótulo do último dia incluído: 07/12."""
    ticks = [(w.start, w.start.astimezone(prereg.BRT).strftime("%d/%m")) for w in prereg.WINDOWS]
    last = prereg.CUTOFF - timedelta(days=1)
    return ticks + [(prereg.CUTOFF, last.astimezone(prereg.BRT).strftime("%d/%m"))]


def product_chart(path: Path, product: prereg.Product, obs, ref: Decimal | None,
                  ref_partial: bool, now: datetime, real_times=(), maquiagem_at=None) -> None:
    fig, ax = plt.subplots(figsize=(9, 3.6))
    for w in prereg.WINDOWS:
        ax.axvspan(w.start, w.end, color=MUTED, alpha=WINDOW_ALPHA[w.name], lw=0)
        ax.text(w.start, 0.97, f" {WINDOW_LABELS[w.name]}", transform=ax.get_xaxis_transform(),
                fontsize=8, color=INK, alpha=0.9 if w.name == "BF" else 0.6, va="top",
                fontweight="bold" if w.name == "BF" else None)
    # Fronteiras internas das janelas (17/11 14:50, 23/11 00:00, 28/11 00:00).
    for w in prereg.WINDOWS[1:]:
        ax.axvline(w.start, color=MUTED, lw=0.8, gid="fronteira")
    # "Agora" só enquanto a PÓS-BF não terminou (fim exclusivo: 08/12 00:00).
    if now < prereg.CUTOFF:
        ax.axvline(now, color=MUTED, lw=0.8, ls=":", gid="agora")
        ax.text(now, 1.0, "agora", transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                fontsize=7, color=MUTED, fontfamily=plt.rcParams["font.family"], gid="agora")
    pts = sorted((o for o in obs if o.available and o.at >= prereg.W["B0"].start), key=lambda o: o.at)
    if pts:
        ax.step([o.at for o in pts], [float(o.price) for o in pts], where="post", color=INK, lw=1.2)
    if ref is not None:
        label = f"Ref {'parcial ' if ref_partial else ''}{_brl(float(ref))}"
        ax.axhline(float(ref), color=INK, lw=0.8, ls="--")
        ax.text(prereg.CUTOFF, float(ref), f" {label}", fontsize=8, va="center", ha="left")
    if real_times:
        by_t = {o.at: o for o in pts}
        ax.scatter(list(real_times), [float(by_t[t].price) for t in real_times],
                   color=FOREST, s=14, zorder=3, label="desconto real (P1b)")
    if maquiagem_at is not None:
        o = next(o for o in pts if o.at == maquiagem_at)
        ax.scatter([o.at], [float(o.price)], color=OCHRE, s=40, zorder=4, marker="D", label="segura (P2)")
    ax.set_xlim(prereg.W["B0"].start, prereg.CUTOFF)
    ticks = window_ticks()
    ax.set_xticks([mdates.date2num(t) for t, _ in ticks], [lab for _, lab in ticks])
    ax.yaxis.set_major_formatter(_brl)
    ax.set_title(product.label, loc="left", fontsize=10, fontweight="bold", pad=14)  # espaço p/ "agora"
    if real_times or maquiagem_at is not None:
        ax.legend(frameon=False, fontsize=8, loc="lower left")
    fig.tight_layout()
    _save(fig, path)
    plt.close(fig)


def summary_chart(path: Path, res: "metrics.Results") -> None:
    labels = [f"w{p.watch_id} {p.label}" for p in prereg.PRODUCTS]
    p1b, p2 = res.questions["P1b"], res.questions["P2"]
    fig, ax = plt.subplots(figsize=(8, 6.5))
    if p1b.status == "ok" and p2.status == "ok":
        p1 = {r.catalog_id: r for r in p1b.rows}
        mq = {r.catalog_id: r.result for r in p2.rows}
        xs, ys, cs = [], [], []
        for i, p in enumerate(prereg.PRODUCTS):
            row = p1[p.catalog_id]
            if row.result == "excluído" or mq.get(p.catalog_id) == "excluído":
                labels[i] += " (excluído)"  # Emenda 2: fora da conta, sem ponto
                continue
            xs.append(-float(row.detail["maior desconto"] or 0) * 100)
            ys.append(i)
            cs.append(FOREST if row.result == "sim" else OCHRE if mq[p.catalog_id] == "maquiagem" else INK)
        ax.scatter(xs, ys, c=cs, s=30)
        ax.axvline(-float(prereg.REAL) * 100, color=MUTED, ls="--", lw=0.8)
        ax.set_xlabel("menor preço da BF vs. Referência (%)")
        title = "Resumo · BF vs. Referência (Forest = desconto real, Ochre = segura)"
    else:
        vals = [float(res.coverage[p.catalog_id]["B0"].ratio or 0) * 100 for p in prereg.PRODUCTS]
        ax.barh(range(len(vals)), vals, color=INK, height=0.6)
        ax.axvline(float(prereg.MIN_COVERAGE) * 100, color=MUTED, ls="--", lw=0.8)
        ax.set_xlim(0, 100)
        ax.set_xlabel("cobertura da B0 até agora (%) · mínimo 70%")
        title = "Resumo · confirmatório incompleto: só cobertura"
    ax.set_yticks(range(len(labels)), labels)
    ax.invert_yaxis()
    ax.set_title(title, loc="left", fontsize=10, fontweight="bold")
    fig.tight_layout()
    _save(fig, path)
    plt.close(fig)
