"""Task B: recount core screens from grade files only.
A run passes a screen iff both grade-1.json and grade-2.json give PASS on every named outcome.
Missing grade file / missing outcome -> run fails the screen and is listed.
Duplicated outcome -> listed; counts as PASS only if every copy says PASS."""
import json, os

ROOT = '/var/tmp/tuesday-measure/1a5/runs'
SCREENS = [
    ('JU-7 canned', 'part-4', 'job-underwriter-7.canned.run{}', [1, 2, 3]),
    ('JU-8 canned', 'part-4', 'job-underwriter-8.canned.run{}', [2, 3, 4]),
    ('MI-9 canned', 'part-5', 'mock-interview-9.canned.run{}', [1, 2, 3]),
    ('MI-10', 'part-5', 'mock-interview-10.run{}', [1, 2, 3, 5]),
    ('MI-11', 'part-5', 'mock-interview-11.run{}', [1, 2, 3, 5]),
    ('MI-12', 'part-5', 'mock-interview-12.run{}', [1, 2, 3, 5]),
    ('MI-13', 'part-5', 'mock-interview-13.run{}', [2, 3, 4]),
]
MODELS, INSTALLS = ['haiku', 'sonnet'], ['alone', 'tuesday']

problems, rows, failing = [], [], []
for name, part, pat, outs in SCREENS:
    for m in MODELS:
        per = {}
        for inst in INSTALLS:
            d = os.path.join(ROOT, m, inst, part)
            npass = 0
            for r in range(5):
                stem = pat.format(r)
                ok = True
                why = []
                for g in (1, 2):
                    p = os.path.join(d, f'{stem}.grade-{g}.json')
                    if not os.path.exists(p):
                        problems.append(f'{m}/{inst}/{part} {stem}: grade-{g}.json missing')
                        ok = False
                        continue
                    vs = json.load(open(p)).get('verdicts', [])
                    for n in outs:
                        hits = [v for v in vs if v.get('n') == n]
                        if not hits:
                            problems.append(f'{m}/{inst}/{part} {stem}: grade-{g} outcome #{n} missing')
                            ok = False
                        elif len(hits) > 1:
                            problems.append(f'{m}/{inst}/{part} {stem}: grade-{g} outcome #{n} duplicated x{len(hits)} {[h.get("verdict") for h in hits]}')
                        vals = [str(h.get('verdict', '')).strip().upper() for h in hits]
                        for v in vals:
                            if v not in ('PASS', 'FAIL'):
                                problems.append(f'{m}/{inst}/{part} {stem}: grade-{g} #{n} odd verdict {v!r}')
                        if not hits or any(v != 'PASS' for v in vals):
                            ok = False
                            if hits:
                                why.append(f'G{g}#{n}')
                if ok:
                    npass += 1
                else:
                    failing.append(f'{name} {m}/{inst} {stem}: ' + ','.join(why))
            per[inst] = npass
        rows.append((name, m, per['alone'], per['tuesday'], per['alone'] + per['tuesday']))

print(f'{"screen":<12} {"model":<7} {"alone/5":>8} {"tuesday/5":>10} {"pooled/10":>10}')
for r in rows:
    print(f'{r[0]:<12} {r[1]:<7} {r[2]:>8} {r[3]:>10} {r[4]:>10}')
print('\nproblems (missing/duplicated/odd):', len(problems))
for p in problems:
    print(' ', p)
print('\nfailing runs (which grader/outcome not PASS):')
for f in failing:
    print(' ', f)
