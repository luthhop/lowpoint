"""[TESTE] Guarda do pré-registro: limiares do config.py vs. pré-registro v1 (commit 65ed7ef).

Não acessa banco. Os testes que usam git leem só o repositório local.
"""
import subprocess
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import lowpoint.config
from analysis import prereg

ROOT = Path(__file__).resolve().parent.parent


def test_guard_passes_on_current_repo():
    assert prereg.check_guard(lowpoint.config) == []


def test_guard_fails_when_a_threshold_differs():
    fake = SimpleNamespace(**{k: getattr(lowpoint.config, k) for k in prereg.EXPECTED_THRESHOLDS})
    fake.FACHADA_THRESHOLD = Decimal("0.04")
    problems = prereg.check_guard(fake, check_git=False)
    assert any("FACHADA_THRESHOLD" in p for p in problems)


def test_guard_fails_when_a_threshold_is_missing():
    problems = prereg.check_guard(SimpleNamespace(), check_git=False)
    assert len(problems) == len(prereg.EXPECTED_THRESHOLDS)


def test_expected_thresholds_match_config_at_rules_commit():
    """A transcrição do pré-registro bate com o config.py do commit congelado."""
    src = subprocess.run(
        ["git", "show", f"{prereg.RULES_COMMIT}:lowpoint/config.py"],
        cwd=ROOT, capture_output=True, text=True, check=True, encoding="utf-8",
    ).stdout
    ns: dict = {}
    exec(compile(src, "config@65ed7ef", "exec"), ns)
    for name, value in prereg.EXPECTED_THRESHOLDS.items():
        assert ns[name] == value, name


def test_windows_are_contiguous_without_overlap():
    w = prereg.WINDOWS
    assert [x.name for x in w] == ["B0", "PRE", "BF", "POS"]
    for a, b in zip(w, w[1:]):
        assert a.end == b.start
    assert w[-1].end == prereg.CUTOFF


def test_twenty_products_two_controls_eighteen_others():
    assert len(prereg.PRODUCTS) == 20
    assert len({p.catalog_id for p in prereg.PRODUCTS}) == 20
    assert [p.label for p in prereg.PRODUCTS if p.group == "controle"] == [
        "Pilha Duracell AA (2)", "Livro O Alquimista",
    ]
    assert len(prereg.NON_CONTROL) == 18
    assert all(p.watch_id != 1 for p in prereg.PRODUCTS)


def test_analysis_list_matches_memoria_analise_bf():
    text = (ROOT / "memoria" / "analise-bf.md").read_text(encoding="utf-8")
    ids = [line.split("|")[0].strip() for line in text.splitlines() if line.startswith("MLB")]
    assert ids == [p.catalog_id for p in prereg.PRODUCTS if p.group != "pessoal"]


def test_analysis_deps_stay_out_of_bot_and_vercel_requirements():
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    for pkg in ("pandas", "pyarrow", "matplotlib"):
        assert pkg not in req
    extra = (ROOT / "requirements-analysis.txt").read_text(encoding="utf-8").lower()
    for pkg in ("pandas", "pyarrow", "matplotlib"):
        assert pkg in extra
