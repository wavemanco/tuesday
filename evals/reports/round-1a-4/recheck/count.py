"""Task B: recount core screens from the grade files (own script, no scorer).
A run passes a screen only if both grade-1.json and grade-2.json give PASS on
every named outcome (expectation number n). Reports passes per install and
pooled, and anomalies: missing grade file, named outcome missing or duplicated,
non-PASS/FAIL verdict values, and the grade file's own missing/duplicates/invalid
fields when they touch a named outcome."""
import json, os

ROOT = "/var/tmp/tuesday-measure/1a4/runs"
SCREENS = [
    ("job-underwriter 7 canned", "part-4", "job-underwriter-7.canned.run{r}", [1, 2, 3]),
    ("job-underwriter 8 canned", "part-4", "job-underwriter-8.canned.run{r}", [2, 3, 4]),
    ("mock-interview 9 canned", "part-5", "mock-interview-9.canned.run{r}", [1, 2, 3]),
    ("mock-interview 10", "part-5", "mock-interview-10.run{r}", [1, 2, 3, 5]),
    ("mock-interview 11", "part-5", "mock-interview-11.run{r}", [1, 2, 3, 5]),
    ("mock-interview 12", "part-5", "mock-interview-12.run{r}", [1, 2, 3, 5]),
    ("mock-interview 13", "part-5", "mock-interview-13.run{r}", [2, 3, 4]),
]
MODELS = ["haiku", "sonnet"]
INSTALLS = ["alone", "tuesday"]

anomalies = []
table = []
detail = []
for name, part, pat, outs in SCREENS:
    for model in MODELS:
        row = {"screen": name, "model": model}
        pooled = 0
        for inst in INSTALLS:
            d = os.path.join(ROOT, model, inst, part)
            passes = 0
            for r in range(5):
                stem = pat.format(r=r)
                ok = True
                per = []
                for g in (1, 2):
                    p = os.path.join(d, f"{stem}.grade-{g}.json")
                    if not os.path.exists(p):
                        anomalies.append(f"{model}/{inst}/{part} {stem}: grade-{g}.json missing")
                        ok = False
                        per.append(f"g{g}:missing")
                        continue
                    gj = json.load(open(p))
                    vs = gj.get("verdicts", [])
                    got = []
                    for n in outs:
                        hits = [v for v in vs if v.get("n") == n]
                        if len(hits) == 0:
                            anomalies.append(f"{model}/{inst}/{part} {stem} grade-{g}: outcome {n} missing")
                            ok = False
                            got.append(f"{n}:none")
                        elif len(hits) > 1:
                            anomalies.append(f"{model}/{inst}/{part} {stem} grade-{g}: outcome {n} duplicated ({len(hits)})")
                            ok = False
                            got.append(f"{n}:dup")
                        else:
                            vv = hits[0].get("verdict")
                            if vv not in ("PASS", "FAIL"):
                                anomalies.append(f"{model}/{inst}/{part} {stem} grade-{g}: outcome {n} verdict {vv!r}")
                            if vv != "PASS":
                                ok = False
                            got.append(f"{n}:{'P' if vv == 'PASS' else vv}")
                    for fld in ("missing", "duplicates", "invalid", "incomplete"):
                        lst = gj.get(fld) or []
                        touched = [x for x in lst if (x.get("n") if isinstance(x, dict) else x) in outs]
                        if touched:
                            anomalies.append(f"{model}/{inst}/{part} {stem} grade-{g}: grade file '{fld}' lists {touched}")
                    per.append(f"g{g}[" + " ".join(got) + "]")
                passes += ok
                detail.append(f"{name:26s} {model:6s} {inst:7s} {stem:36s} {'PASS' if ok else 'fail'}  " + " ".join(per))
            row[inst] = passes
            pooled += passes
        row["pooled"] = pooled
        table.append(row)

print(f"{'screen':26s} {'model':6s} {'alone':>5s} {'tuesday':>7s} {'pooled':>7s}")
for row in table:
    print(f"{row['screen']:26s} {row['model']:6s} {row['alone']:>3d}/5 {row['tuesday']:>5d}/5 {row['pooled']:>4d}/10")
print("\nAnomalies:")
print("\n".join(anomalies) if anomalies else "none")
print("\nPer-run detail:")
print("\n".join(detail))
