"""Relatório da análise BF: python -m analysis.report

1. Guarda: limiares do config.py e lowpoint/verdict.py iguais ao pré-registro
   (commit 65ed7ef). Se não, recusa e sai com código 2, sem gerar nada.
2. Exporta do Neon em READ ONLY para analysis/output/data/ (--no-export reaproveita).
3. Calcula P1–P5 (só janelas completas e cobertura ≥ 70%) e o exploratório.
4. Escreve analysis/output/relatorio.md e os gráficos em analysis/output/charts/.
"""
import argparse
import json
import math
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

import lowpoint.config
from analysis import metrics, prereg
from analysis.metrics import Dataset, Obs, OfferObs

OUT = Path(__file__).resolve().parent / "output"

TITLES = {
    "P1a": "P1a — O que o Lowpoint teria dito (compute_verdict coleta a coleta)",
    "P1b": "P1b — O que a régua fixa diz (≥ 5% abaixo da Referência, ≥ 2 coletas seguidas)",
    "P2": "P2 — Maquiagem (subida antes da BF e \"queda\" na BF)",
    "P3": "P3 — O preço riscado é honesto?",
    "P4": "P4 — O menor preço caiu na BF ou depois (até 07/12)?",
    "P5": "P5 — Os controles (pilha, livro) se comportaram diferente?",
}


# --- Leitura do parquet --------------------------------------------------------

def _dec(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return x if isinstance(x, Decimal) else Decimal(str(x))


def _list(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else tuple(x)


def load_dataset(data_dir: Path) -> Dataset:
    obs: dict[str, list] = {}
    for r in pd.read_parquet(data_dir / "price_history.parquet").itertuples(index=False):
        obs.setdefault(r.catalog_product_id, []).append(Obs(
            at=r.collected_at.to_pydatetime(), price=_dec(r.price),
            original_price=_dec(r.original_price), available=bool(r.available)))
    offers: dict[str, list] = {}
    path = data_dir / "offers.parquet"
    if path.exists():
        for r in pd.read_parquet(path).itertuples(index=False):
            offers.setdefault(r.catalog_product_id, []).append(OfferObs(
                at=r.collected_at.to_pydatetime(), item_id=r.item_id, price=_dec(r.price),
                original_price=_dec(r.original_price), deal_ids=_list(r.deal_ids), tags=_list(r.tags)))
    return Dataset(obs, offers)


# --- Formatação ------------------------------------------------------------------

def _brl(x) -> str:
    return "—" if x is None else f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(x) -> str:
    return "—" if x is None else f"{x * 100:.1f}%".replace(".", ",")


def _dt(d) -> str:
    return "—" if d is None else d.astimezone(prereg.BRT).strftime("%d/%m %H:%M")


def _val(v) -> str:
    if isinstance(v, Decimal):
        return _pct(v) if abs(v) < 2 else _brl(v)
    if isinstance(v, bool):
        return "sim" if v else "não"
    return "—" if v is None else str(v)


def render(res: metrics.Results, meta: dict, font_warning: str | None) -> str:
    L = []
    L.append("# Análise BF — \"Os descontos da Black Friday eram reais?\"\n")
    L.append(f"- Gerado: {_dt(res.now)} BRT · pré-registro: `{prereg.DOC}` (tag `{prereg.TAG}`, + Emendas 1 e 2)")
    L.append(f"- Regras: commit `{prereg.RULES_COMMIT}` · guarda: OK "
             f"({len(prereg.EXPECTED_THRESHOLDS)} limiares iguais; {', '.join(prereg.FROZEN_FILES)} igual ao commit)")
    if meta:
        L.append(f"- Dados: exportados em {_dt(datetime.fromisoformat(meta['exported_at']))} "
                 f"(READ ONLY: {meta.get('read_only')}), {meta['price_history_rows']} coletas, "
                 f"{meta['offer_rows']} ofertas · corte {_dt(prereg.CUTOFF)}")
    if font_warning:
        L.append(f"- Aviso: {font_warning}")

    L.append("\n## Janelas\n")
    L.append("| Janela | Início | Fim (exclusivo) | Estado |\n|---|---|---|---|")
    for w in prereg.WINDOWS:
        L.append(f"| {w.name} | {_dt(w.start)} | {_dt(w.end)} | {res.window_status[w.name]} |")

    L.append("\n## Cobertura\n")
    L.append("Coletas disponíveis / esperadas no trecho já decorrido de cada janela (1/h; BF 4/h). Mínimo 70%.\n")
    L.append("| W | Produto | Grupo | " + " | ".join(w.name for w in prereg.WINDOWS) + " |")
    L.append("|---|---|---|" + "---|" * len(prereg.WINDOWS))
    for p in prereg.PRODUCTS:
        cells = []
        for w in prereg.WINDOWS:
            c = res.coverage[p.catalog_id][w.name]
            if c.ratio is None:
                cells.append("—")
            else:
                flag = "" if c.ok else " ⚠"
                cells.append(f"{c.n}/{c.expected:.0f} ({_pct(c.ratio)}){' parcial' if c.partial else ''}{flag}")
        L.append(f"| {p.watch_id} | {p.label} | {p.group} | " + " | ".join(cells) + " |")

    partial = res.window_status["B0"] != "completa"
    L.append("\n## " + ("B0 parcial (Referência provisória, ainda não vale)" if partial else "Referência (mediana da B0)") + "\n")
    L.append("| W | Produto | Coletas na B0 | Mediana |\n|---|---|---|---|")
    for p in prereg.PRODUCTS:
        b = res.b0_partial[p.catalog_id]
        L.append(f"| {p.watch_id} | {p.label} | {b.n} | {_brl(b.ref)} |")

    L.append("\n## Confirmatório (P1–P5)\n")
    L.append("Divergência entre P1a e P1b é resultado a reportar, não erro. Emenda 2: produto com "
             "cobertura < 70% numa janela usada sai só daquela pergunta; cortes de manchete são "
             "proporção dos 18 com cobertura e exigem ≥ 12 deles. P3 usa a base dos 18.\n")
    for q, title in TITLES.items():
        Q = res.questions[q]
        L.append(f"### {title}\n")
        if Q.status == "incompleto":
            L.append(f"**incompleto** — {Q.reason}. Manchete não calculada.\n")
        else:
            L.append(f"**Manchete:** {Q.headline or 'sem manchete (nenhum produto elegível)'}  ")
            L.append("Totais: " + ", ".join(f"{k}: {_val(v)}" for k, v in Q.extra.items()) + "\n")
        if Q.excluded:
            L.append(f"Excluídos desta pergunta ({len(Q.excluded)}): "
                     + "; ".join(f"{label} ({why})" for label, why in Q.excluded) + "\n")
        if Q.rows:
            keys = [k for k in Q.rows[0].detail if k not in ("result",) and not k.startswith("_")]
            keys = sorted({k for r in Q.rows for k in r.detail if k != "result" and not k.startswith("_")},
                          key=lambda k: (keys.index(k) if k in keys else 99, k))
            L.append("| Produto | Grupo | Resultado | " + " | ".join(keys) + " |")
            L.append("|---|---|---|" + "---|" * len(keys))
            for r in Q.rows:
                L.append(f"| {r.label} | {r.group} | {r.result} | "
                         + " | ".join(_val(r.detail.get(k)) for k in keys) + " |")
            L.append("")

    L.append("## Exploratório (não altera P1–P5)\n")
    L.append("### deal_ids e tags (gravados desde 15/11 09:45:29, Emenda 1)\n")
    deals = res.exploratory["deals_tags"]
    if not deals:
        L.append("Sem ofertas com os campos ainda.\n")
    for name, d in deals.items():
        L.append(f"- **{name}**{' (parcial)' if d['parcial'] else ''}: {d['ofertas']} ofertas, "
                 f"{d['com deal']} com deal ({_pct(Decimal(d['com deal']) / d['ofertas'])}); "
                 f"deal_ids: {d['deal_ids'] or '—'}")
        L.append(f"  - tags mais comuns: " + ", ".join(f"{t} ({n})" for t, n in d["tags"]))
    L.append("\n### Sensibilidade: referência longa (PS5 e monitores)\n")
    L.append("Ref longa = mediana de todo o histórico antes da Pré-BF. Definida depois do congelamento: exploratória.\n")
    L.append("| Produto | Desde | Ref longa | Ref B0 | P1b (Ref longa) | P2 (Ref longa) |\n|---|---|---|---|---|---|")
    for label, it in res.exploratory["ref_longa"].items():
        sfx = " (parcial)" if it["parcial"] else ""
        L.append(f"| {label} | {_dt(it['desde'])} | {_brl(it['Ref longa'])}{sfx} | {_brl(it['Ref B0'])}{sfx} | "
                 f"{_val(it.get('P1b (Ref longa)'))} | {_val(it.get('P2 (Ref longa)'))} |")
    return "\n".join(L) + "\n"


# --- Execução ---------------------------------------------------------------------

def main(argv=None, now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m analysis.report")
    ap.add_argument("--no-export", action="store_true", help="usa o parquet já exportado")
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    # Console do Windows (cp1252) não tem "≥", "→" etc.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    problems = prereg.check_guard(lowpoint.config)
    if problems:
        print("RECUSADO: as regras não batem com o pré-registro v1:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 2

    data_dir = args.data_dir or args.out / "data"
    meta = {}
    if not args.no_export:
        from analysis.export import export
        meta = export(data_dir)
    elif (data_dir / "meta.json").exists():
        meta = json.loads((data_dir / "meta.json").read_text(encoding="utf-8"))

    from analysis import charts

    now = now or datetime.now(prereg.BRT)
    data = load_dataset(data_dir)
    res = metrics.run_all(data, now)

    font, warning = charts.pick_mono_font()
    charts._style(font)
    chart_dir = args.out / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)
    p1b = {r.catalog_id: r for r in res.questions["P1b"].rows}
    p2 = {r.catalog_id: r for r in res.questions["P2"].rows}
    for p in prereg.PRODUCTS:
        s = data.obs.get(p.catalog_id, [])
        ref = res.b0_partial[p.catalog_id]
        real_times, mq_at = (), None
        if p.catalog_id in p1b and p1b[p.catalog_id].result != "excluído":
            real_times = metrics.p1b_product(s, ref.ref).real_times
        if p.catalog_id in p2 and p2[p.catalog_id].result == "maquiagem":
            mq_at = metrics.p2_product(s, ref.ref).min_bf_at
        charts.product_chart(chart_dir / f"w{p.watch_id:02d}_{p.catalog_id}.png", p, s,
                             ref.ref, ref.partial, now, real_times, mq_at)
    charts.summary_chart(chart_dir / "resumo.png", res)

    text = render(res, meta, warning)
    (args.out / "relatorio.md").write_text(text, encoding="utf-8")
    print(text)
    print("Arquivos gerados:")
    for f in sorted(args.out.rglob("*")):
        if f.is_file():
            print(f"  {f.relative_to(args.out.parent)}  ({f.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
