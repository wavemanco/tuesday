"""Task B: recount core screens from the grade files (own logic, no existing scorer).

A run passes a screen only if both grade-1.json and grade-2.json give PASS on every
named outcome. Problems listed: missing grade file, named outcome missing, named
outcome duplicated (appearing more than once in a grade file's verdicts list),
unreadable file, or a verdict other than PASS/FAIL.
"""
import json
import os
from collections import Counter

ROOT = "/var/tmp/tuesday-measure/1a6/runs"
SCREENS = [
    ("JU-7 canned", "part-4", "job-underwriter-7.canned.run%d", [1, 2, 3]),
    ("JU-8 canned", "part-4", "job-underwriter-8.canned.run%d", [2, 3, 4]),
    ("MI-9 canned", "part-5", "mock-interview-9.canned.run%d", [1, 2, 3]),
    ("MI-10", "part-5", "mock-interview-10.run%d", [1, 2, 3, 5]),
    ("MI-11", "part-5", "mock-interview-11.run%d", [1, 2, 3, 5]),
    ("MI-12", "part-5", "mock-interview-12.run%d", [1, 2, 3, 5]),
    ("MI-13", "part-5", "mock-interview-13.run%d", [2, 3, 4]),
]
MODELS = ["sonnet", "opus"]
INSTALLS = ["alone", "tuesday"]

problems = []
table = {}
detail = {}
for name, part, pat, outs in SCREENS:
    for model in MODELS:
        for inst in INSTALLS:
            npass = 0
            fails = []
            for r in range(5):
                stem = pat % r
                ok = True
                why = []
                for g in (1, 2):
                    p = os.path.join(ROOT, model, inst, part, "%s.grade-%d.json" % (stem, g))
                    if not os.path.exists(p):
                        problems.append("%s %s/%s %s: grade-%d MISSING" % (name, model, inst, stem, g))
                        ok = False
                        why.append("g%d missing" % g)
                        continue
                    try:
                        j = json.load(open(p))
                    except Exception as e:
                        problems.append("%s %s/%s %s: grade-%d unreadable (%s)" % (name, model, inst, stem, g, type(e).__name__))
                        ok = False
                        continue
                    vs = j.get("verdicts", [])
                    cnt = Counter(v.get("n") for v in vs)
                    for n in outs:
                        if cnt[n] == 0:
                            problems.append("%s %s/%s %s: grade-%d outcome #%d MISSING" % (name, model, inst, stem, g, n))
                            ok = False
                            why.append("g%d #%d missing" % (g, n))
                        elif cnt[n] > 1:
                            problems.append("%s %s/%s %s: grade-%d outcome #%d DUPLICATED x%d" % (name, model, inst, stem, g, n, cnt[n]))
                            ok = False
                            why.append("g%d #%d dup" % (g, n))
                        else:
                            v = [x for x in vs if x.get("n") == n][0].get("verdict")
                            if v not in ("PASS", "FAIL"):
                                problems.append("%s %s/%s %s: grade-%d outcome #%d verdict=%r" % (name, model, inst, stem, g, n, v))
                            if v != "PASS":
                                ok = False
                                why.append("g%d #%d %s" % (g, n, v))
                if ok:
                    npass += 1
                else:
                    fails.append("run%d[%s]" % (r, ",".join(why)))
            table[(name, model, inst)] = npass
            detail[(name, model, inst)] = fails

print("%-12s %-7s %6s %8s %7s" % ("screen", "model", "alone", "tuesday", "pooled"))
for name, _, _, outs in SCREENS:
    for model in MODELS:
        a = table[(name, model, "alone")]
        t = table[(name, model, "tuesday")]
        print("%-12s %-7s %4d/5 %6d/5 %4d/10   outcomes %s" % (name, model, a, t, a + t, outs))
print()
print("non-passing runs (which grade/outcome blocked them):")
for k, v in detail.items():
    if v:
        print("  %s %s/%s: %s" % (k[0], k[1], k[2], "; ".join(v)))
print()
print("problems (missing/duplicated/odd):", len(problems))
for p in problems:
    print("  " + p)

# sanity: grade files' own skill/id/run/mode fields and their own missing/duplicates/invalid/incomplete lists
print()
print("grade-file self-report check:")
odd = 0
for name, part, pat, outs in SCREENS:
    for model in MODELS:
        for inst in INSTALLS:
            for r in range(5):
                stem = pat % r
                for g in (1, 2):
                    p = os.path.join(ROOT, model, inst, part, "%s.grade-%d.json" % (stem, g))
                    if not os.path.exists(p):
                        continue
                    j = json.load(open(p))
                    flags = {k: j.get(k) for k in ("missing", "duplicates", "invalid", "incomplete") if j.get(k)}
                    sid = "%s-%s" % (j.get("skill"), j.get("id"))
                    if not stem.startswith(sid + ".") or str(j.get("run")) not in (str(r), "run%d" % r):
                        flags["stem_mismatch"] = (j.get("skill"), j.get("id"), j.get("run"), j.get("mode"))
                    if flags:
                        odd += 1
                        print("  %s/%s %s g%d: %s" % (model, inst, stem, g, flags))
print("  files with self-reported issues or id mismatch:", odd)
