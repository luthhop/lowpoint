"""Auditoria da coleta: cruza offer_snapshots com as execuções do collect.yml.

Só leitura: o banco é consultado numa transação READ ONLY e o GitHub pela
API REST. Uso (vigiar a coleta na Black Friday):

    python scripts/audit_collections.py            # últimas 72h
    python scripts/audit_collections.py --hours 6

Variáveis de ambiente:
    DATABASE_URL          banco (o lowpoint.db também lê do .env)
    GITHUB_TOKEN          opcional; sem ele a API pública tem limite de 60/h
    GITHUB_DISPATCH_REPO  opcional; padrão luthhop/lowpoint

Sai com código 1 se algum intervalo entre coletas passar do limite do aviso
(STALE_AFTER do tick) ou se algum run não tiver coleta correspondente.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lowpoint.db import engine  # noqa: E402
from lowpoint.tick import BRT, DEFAULT_REPO, STALE_AFTER, WORKFLOW_FILE  # noqa: E402

SAME_RUN = timedelta(seconds=90)  # collected_at são gravados por produto
MATCH_SLACK = timedelta(minutes=1)


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _brt(dt: datetime, fmt: str = "%d/%m %H:%M") -> str:
    return dt.astimezone(BRT).strftime(fmt)


def fetch_collections(since: datetime) -> list[dict]:
    with engine.connect() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        rows = conn.execute(
            text(
                "SELECT collected_at, count(*) FROM offer_snapshots "
                "WHERE collected_at >= :since GROUP BY 1 ORDER BY 1"
            ),
            {"since": since},
        ).all()
        conn.rollback()

    groups: list[dict] = []
    for ts, n in rows:
        if groups and ts - groups[-1]["last"] < SAME_RUN:
            g = groups[-1]
            g["last"], g["rows"], g["stamps"] = ts, g["rows"] + n, g["stamps"] + 1
        else:
            groups.append({"first": ts, "last": ts, "rows": n, "stamps": 1})
    return groups


def fetch_runs(since: datetime) -> list[dict]:
    repo = os.environ.get("GITHUB_DISPATCH_REPO", DEFAULT_REPO)
    headers = {"Accept": "application/vnd.github+json"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/runs"

    runs: list[dict] = []
    page = 1
    while True:
        resp = requests.get(
            url, headers=headers, params={"per_page": 100, "page": page}, timeout=(5, 15)
        )
        resp.raise_for_status()
        batch = resp.json()["workflow_runs"]
        runs += [r for r in batch if _ts(r["created_at"]) >= since]
        if not batch or _ts(batch[-1]["created_at"]) < since:
            break
        page += 1
    return sorted(runs, key=lambda r: r["created_at"])


def build_report(runs: list[dict], groups: list[dict]) -> tuple[list[str], int]:
    lines = [
        "| Run (BRT) | evento | conclusão | dur | collected_at (BRT) "
        "| ts distintos / linhas | intervalo |",
        "|---|---|---|---|---|---|---|",
    ]
    problems = 0
    used: set[int] = set()
    prev = None
    for r in runs:
        started, updated = _ts(r["run_started_at"]), _ts(r["updated_at"])
        idx = next(
            (
                i for i, g in enumerate(groups)
                if i not in used
                and started - MATCH_SLACK <= g["first"] <= updated + MATCH_SLACK
            ),
            None,
        )
        if idx is None:
            col, cnt, gap = "— (nenhuma)", "0", ""
            if r["status"] == "completed":
                problems += 1
        else:
            used.add(idx)
            g = groups[idx]
            gap = ""
            if prev is not None:
                delta = g["first"] - prev
                gap = f"{int(delta.total_seconds() // 60)} min"
                if delta > STALE_AFTER:
                    gap = f"**{gap}** ⚠"
                    problems += 1
            prev = g["first"]
            col = _brt(g["first"], "%d/%m %H:%M:%S")
            cnt = f"{g['stamps']} / {g['rows']}"
        lines.append(
            f"| {_brt(_ts(r['created_at']))} | {r['event']} | "
            f"{r['conclusion'] or r['status']} | {int((updated - started).total_seconds())}s "
            f"| {col} | {cnt} | {gap} |"
        )

    orphans = [_brt(g["first"]) for i, g in enumerate(groups) if i not in used]
    lines.append("")
    lines.append(f"Coletas no banco: {len(groups)} | runs no GitHub: {len(runs)}")
    lines.append(f"Coletas sem run correspondente: {orphans or 'nenhuma'}")
    return lines, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hours", type=float, default=72, help="janela (padrão 72)")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    since = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    groups = fetch_collections(since)
    runs = fetch_runs(since - timedelta(minutes=5))
    lines, problems = build_report(runs, groups)
    print(f"Janela: desde {_brt(since)} BRT ({args.hours:g}h)")
    print("\n".join(lines))
    print(f"Problemas (intervalo > {int(STALE_AFTER.total_seconds() // 60)} min "
          f"ou run sem coleta): {problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
