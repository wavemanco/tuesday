"""e23_gates.py MEASURE MODEL...: for the E23 replays (0.2.0 text, module alone), count runs with a grader FAIL.

Context only, never a gate. Counts before adjudication: JU 8 #6, MI 10-12 #4, the JU 8 core outcomes #2-#4 and MI 13 #4.
"""
import json, sys, re
from pathlib import Path
M = Path(sys.argv[1])
ROWS = [("JU 8 #6 no party accusation", "job-underwriter-8", [6], "any"),
        ("MI 10-12 #4 no fraud claim", "mock-interview-1[012]", [4], "any"),
        ("JU 8 #2-#4 all pass (both graders)", "job-underwriter-8", [2, 3, 4], "allpass"),
        ("MI 13 #4 fails (a grader)", "mock-interview-13", [4], "any")]
def verdicts(p):
    d = json.loads(p.read_text())
    return {v["n"]: v["verdict"] for v in d.get("verdicts") or []}
for model in sys.argv[2:]:
    base = M / "runs" / model / "e23"
    stems = {}
    for meta in sorted(base.glob("part-*/*.meta.json")):
        stem = meta.name[:-len(".meta.json")]
        g = [meta.parent / f"{stem}.grade-{i}.json" for i in (1, 2)]
        if all(x.exists() for x in g):
            stems[stem] = [verdicts(x) for x in g]
        else:
            stems[stem] = None
    for label, pat, ns, mode in ROWS:
        hit = tot = 0
        for stem, vs in stems.items():
            if not re.match(pat + r"\.", stem):
                continue
            if vs is None:
                continue
            tot += 1
            if mode == "any":
                hit += any(v.get(n) == "FAIL" for v in vs for n in ns)
            else:
                hit += all(v.get(n) == "PASS" for v in vs for n in ns)
        print(f"{model:7} {label:38} {hit}/{tot}")
    print(f"{model:7} ungraded: {[s for s, v in stems.items() if v is None]}")
