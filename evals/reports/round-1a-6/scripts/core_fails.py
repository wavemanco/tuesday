"""core_fails.py M MODEL [SCREEN_SUBSTR]: for each core screen, every failing named outcome per run and grader, with
the grader's finding cut short. Report aid only; reads the grade files."""
import json
import sys
from pathlib import Path

M = Path(sys.argv[1]); model = sys.argv[2]; only = sys.argv[3] if len(sys.argv) > 3 else ""
SCREENS = [("JU 7 canned", 4, "job-underwriter-7.canned", (1, 2, 3)), ("JU 8 canned", 4, "job-underwriter-8.canned", (2, 3, 4)),
           ("MI 9 canned", 5, "mock-interview-9.canned", (1, 2, 3)), ("MI 10", 5, "mock-interview-10", (1, 2, 3, 5)),
           ("MI 11", 5, "mock-interview-11", (1, 2, 3, 5)), ("MI 12", 5, "mock-interview-12", (1, 2, 3, 5)),
           ("MI 13", 5, "mock-interview-13", (2, 3, 4))]
for label, part, base, ns in SCREENS:
    if only and only not in label:
        continue
    print(f"=== {label}")
    for arm in ("alone", "tuesday"):
        for i in range(5):
            stem = f"{base}.run{i}"
            d = M / "runs" / model / arm / f"part-{part}"
            for g in (1, 2):
                for x in json.loads((d / f"{stem}.grade-{g}.json").read_text())["verdicts"]:
                    if x["n"] in ns and x["verdict"] != "PASS":
                        ev = x.get("why") or ""
                        print(f"  {arm:7} run{i} #{x['n']} g{g}: {ev[:260]}")
