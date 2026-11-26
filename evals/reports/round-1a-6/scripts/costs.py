"""costs.py M MODEL...: API-price-equivalent cost of each model's quality step (runs and graders) and explicit panel.

Runs: every invocation's total_cost_usd in each *.meta.json, or else the sum of its result's modelUsage costUSD.
Graders: each *.grade-N.json's model_usage costUSD. killed/ folders are left out. Reads only; prints totals.
"""
import json
import sys
from pathlib import Path

M = Path(sys.argv[1])


def inv_cost(inv):
    c = inv.get("total_cost_usd")
    if isinstance(c, (int, float)):
        return float(c)
    mu = inv.get("modelUsage") or (inv.get("result") or {}).get("modelUsage") or {}
    return sum(float(v.get("costUSD", 0) or 0) for v in mu.values() if isinstance(v, dict))


def grade_cost(g):
    mu = g.get("model_usage") or {}
    if isinstance(mu, dict):
        if "costUSD" in mu:
            return float(mu["costUSD"] or 0)
        return sum(float(v.get("costUSD", 0) or 0) for v in mu.values() if isinstance(v, dict))
    return 0.0


for model in sys.argv[2:]:
    base = M / "runs" / model
    runs = grades = 0
    rc = gc = 0.0
    invs = 0
    for meta in base.rglob("*.meta.json"):
        if "killed" in meta.parts or "passes" in meta.parts:
            continue
        d = json.loads(meta.read_text())
        iv = d.get("invocations") or []
        runs += 1
        invs += len(iv)
        rc += sum(inv_cost(i) for i in iv)
    for g in base.rglob("*.grade-[12].json"):
        if "killed" in g.parts:
            continue
        grades += 1
        gc += grade_cost(json.loads(g.read_text()))
    print(f"{model}: {runs} runs ({invs} sessions), {grades} grades; runs ${rc:.2f}, graders ${gc:.2f}, total ${rc + gc:.2f}")
