"""collect.yml: na BF o ritmo de 15 min vem do tick; o GitHub só tem a reserva :17."""

import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "collect.yml"


def _text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_only_hourly_reserve_cron():
    crons = re.findall(r'^\s*-\s*cron:\s*"([^"]+)"', _text(), flags=re.M)
    assert crons == ["17 * * * *"]


def test_bf_reserve_lines_removed():
    assert "2,32,47" not in _text()


def test_manual_dispatch_kept():
    assert re.search(r"^\s*workflow_dispatch:", _text(), flags=re.M)
