"""Build the independent reader's event list for round 1a-5: one item per zero-gate run and expectation.

Reads the adjudication records only to find which (run, expectation) pairs carry a zero-gate grader event; it copies
the graders' verdicts verbatim from the grade files and drops every ruling field, so the reader sees no ruling.
Usage: build_events.py MEASURE_DIR > events.jsonl
"""
import json, sys, re
from pathlib import Path

M = Path(sys.argv[1])
PART = {"job-underwriter": {7: 4, 8: 4, 9: 4, 10: 4, 11: 4}, "mock-interview": {9: 5, 10: 5, 11: 5, 12: 5, 13: 5}}
IBAN = re.compile(r"IE\d\d(?:[ ]?[A-Z0-9]{2,4}){3,8}")

def part_of(stem):
    m = re.match(r"(job-underwriter|mock-interview)-(\d+)\.", stem)
    skill, n = m.group(1), int(m.group(2))
    return PART[skill].get(n) or (1 if skill == "job-underwriter" else 2)

seen, items = set(), []
for line in (M / "adjudications.jsonl").open():
    d = json.loads(line)
    if not d["id"].startswith("A") or not d["gate"].startswith("zero/"):
        continue
    key = (d["model"], d["install"], d["stem"], int(d["expectation"]))
    if key in seen:
        continue
    seen.add(key)
    model, install, stem, n = key
    run_dir = M / "runs" / model / install / f"part-{part_of(stem)}"
    findings = []
    for g in (1, 2):
        gf = run_dir / f"{stem}.grade-{g}.json"
        gd = json.loads(gf.read_text())
        for v in gd.get("verdicts") or gd.get("expectations") or []:
            if v.get("n") == n:
                findings.append({"grader": g, "verdict": v.get("verdict"), "why": IBAN.sub("[planted IBAN removed]", v.get("why") or "")})
    items.append({"model": model, "install": install, "stem": stem, "expectation": n,
                  "gate": d["gate"].split("/", 1)[1], "run_dir": str(run_dir), "findings": findings})

items.sort(key=lambda x: (x["model"] != "haiku", x["install"], x["stem"], x["expectation"]))
for i, it in enumerate(items, 1):
    it["item"] = f"E{i:02d}"
    print(json.dumps(it, ensure_ascii=False))
