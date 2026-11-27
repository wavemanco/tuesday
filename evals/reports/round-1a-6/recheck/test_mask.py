"""Test the masker on the evals' own text. Prints only counts and booleans."""
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mask as M

print("protected values loaded:", len(M.PROTECTED))
ib = M.ibans()
print("iban cases:", sorted(ib.keys()), "distinct normalized per case:", {k: len(v) for k, v in ib.items()})
print("iban lengths:", {k: [len(x) for x in v] for k, v in ib.items()})
allib = set().union(*ib.values())
print("two different numbers:", len(allib) == 2)

for f in ("job-underwriter.evals.json", "mock-interview.evals.json"):
    raw = open(M.EVAL_DIR + f).read()
    before = len(M.protected_spans(raw))
    out = M.mask(raw)  # raises on leak
    print(f, "raw protected hits:", before, "-> after mask:", len(M.protected_spans(out)), "masks:", out.count("[#]"))
    # also per-string over json content (decoded unicode)
    d = json.load(open(M.EVAL_DIR + f))
    n = 0
    def walk(x):
        global n
        if isinstance(x, str):
            M.mask(x); n += 1
        elif isinstance(x, dict):
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    walk(d)
    print("  strings masked cleanly:", n)

# synthetic variants built from the IBANs themselves (never printed)
for v in sorted(allib):
    up = v.upper()
    spaced = " ".join(up[i:i+4] for i in range(0, len(up), 4))
    dashed = "-".join(up[i:i+4] for i in range(0, len(up), 4))
    cut6 = up[:6] + "..."
    cut3 = up[:3] + "…"
    tail6 = "ending " + up[-6:]
    mid = "x " + up[8:14] + " y"
    tests = [up, spaced, dashed, v, cut6, cut3, tail6, mid, "acct: " + spaced.lower()]
    res = []
    for t in tests:
        o = M.mask("Pay to " + t + " today.")
        res.append(o.count("[#]") >= 1 and M.check_clean(o))
    print("synthetic variants masked:", res)
print("plain sentence unchanged:", M.mask("The interview is on 12 March 2026 at 10am.") )
print("email test:", M.mask("write to a.b@firm.example or c@real.com"))
