"""Self-test for mask.py: builds spellings of the IBAN in memory and checks
that mask() leaves no 3+ char piece of it. Prints only booleans."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mask as M
I = M.IBAN
grp = " ".join(I[i:i+4] for i in range(0, len(I), 4))
tests = [I, I.lower(), grp, grp.replace(" ", "-"), "IBAN " + grp + ", and", "IBAN " + I[:6] + "...", I[:4] + "…" + I[-2:], "x " + I[-4:-2] + " " + I[-2:] + " y", "pay " + grp[:-3] + "…"]
def leak(s, k):
    n = re.sub(r"[^A-Za-z0-9]", "", s).upper()
    return any(I[i:i+k] in n for i in range(len(I)-k+1))
for t in tests:
    out = M.mask(t)
    print("leak4:", leak(out, 4), "leak3:", leak(out, 3))
