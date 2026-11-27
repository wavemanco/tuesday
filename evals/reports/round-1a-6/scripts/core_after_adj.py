"""core_after_adj.py M MODEL...: core screens with every adjudication applied.

A run passes a screen when, on every named outcome, both graders PASS, or a grader's FAIL is a core quote event whose
ruling, or whose owner review, is 'overturned' in $M/adjudications.jsonl. Reads the grade files and the rulings only; no model calls.
"""
import json
import sys
from pathlib import Path

M = Path(sys.argv[1])
SCREENS = [("JU 7 canned", 4, "job-underwriter-7.canned", (1, 2, 3)), ("JU 8 canned", 4, "job-underwriter-8.canned", (2, 3, 4)),
           ("MI 9 canned", 5, "mock-interview-9.canned", (1, 2, 3)), ("MI 10", 5, "mock-interview-10", (1, 2, 3, 5)),
           ("MI 11", 5, "mock-interview-11", (1, 2, 3, 5)), ("MI 12", 5, "mock-interview-12", (1, 2, 3, 5)),
           ("MI 13", 5, "mock-interview-13", (2, 3, 4))]
adj = [json.loads(l) for l in (M / "adjudications.jsonl").read_text().splitlines()]
# A finding counts as overturned when the adjudication overturns it, or when the owner's review does (from round 1a-6:
# an owner_review that starts "overturned").
over = {(r["model"], r["install"], r["stem"], int(r["grader"]), int(r["expectation"]))
        for r in adj if r["id"].startswith("Q") and (r["adjudication"].startswith("overturned")
                                                    or str(r.get("owner_review", "")).startswith("overturned"))}
for model in sys.argv[2:]:
    print(f"=== {model}")
    for label, part, base, ns in SCREENS:
        per, changed = {}, []
        for arm in ("alone", "tuesday"):
            k = 0
            for i in range(5):
                stem = f"{base}.run{i}"
                d = M / "runs" / model / arm / f"part-{part}"
                ok = ok_raw = True
                for g in (1, 2):
                    v = {x["n"]: x["verdict"] for x in json.loads((d / f"{stem}.grade-{g}.json").read_text())["verdicts"]}
                    for n in ns:
                        if v.get(n) != "PASS":
                            ok_raw = False
                            if (model, arm, stem, g, n) not in over:
                                ok = False
                k += ok
                if ok != ok_raw:
                    changed.append(f"{arm} {stem}")
            per[arm] = k
        print(f"  {label:12} {per['alone'] + per['tuesday']}/10 (alone {per['alone']}, tuesday {per['tuesday']})"
              + (f"  changed by a ruling: {changed}" if changed else ""))
