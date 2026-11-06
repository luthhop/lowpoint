"""[TESTE] The landing's fictitious fixture must agree with the real verdict engine.

Reads local JSON only. No network, Telegram or database access.
"""
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from lowpoint.verdict import PricePoint, compute_verdict


@pytest.mark.parametrize("date, expected", [("2026-11-27", "maquiado"), ("2026-12-02", "real")])
def test_frontend_story_matches_verdict(date, expected):
    path = Path(__file__).resolve().parents[1] / "frontend/src/data/demo-history.json"
    story = json.loads(path.read_text(encoding="utf-8"))
    now = datetime.fromisoformat(date).replace(hour=12, tzinfo=timezone.utc)
    history = [
        PricePoint(
            price=Decimal(p["priceCents"]) / 100,
            original_price=None,
            collected_at=datetime.fromisoformat(p["date"]).replace(hour=12, tzinfo=timezone.utc),
        )
        for p in story["points"] if p["date"] <= date
    ]
    result = compute_verdict(
        history[-1].price, Decimal(story["crossedOutCents"]) / 100, history, now,
    )
    assert result.verdict == expected
    assert result.baseline_price == Decimal(story["baselineCents"]) / 100
