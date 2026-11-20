#!/usr/bin/env python3
"""Task B: recount core screens from the grade files only (no scorer used).

A run passes a screen only if BOTH grade files (<stem>.grade-1.json and
<stem>.grade-2.json, at the top level of the part dir) give PASS on every
named outcome. A missing grade file, or a named outcome that is missing or
appears more than once in a file's "verdicts", is reported and counts as not
passing. Nothing under killed/ is read.
"""
import json
import os

ROOT = '/var/tmp/tuesday-measure/1a3/runs'
MODELS = ['haiku', 'sonnet']
INSTALLS = ['alone', 'tuesday']

SCREENS = [
    ('job-underwriter 7 canned', 'part-4', 'job-underwriter-7.canned.run{r}', [1, 2, 3]),
    ('job-underwriter 8 canned', 'part-4', 'job-underwriter-8.canned.run{r}', [2, 3, 4]),
    ('mock-interview 9 canned', 'part-5', 'mock-interview-9.canned.run{r}', [1, 2, 3]),
    ('mock-interview 10', 'part-5', 'mock-interview-10.run{r}', [1, 2, 3, 5]),
    ('mock-interview 11', 'part-5', 'mock-interview-11.run{r}', [1, 2, 3, 5]),
    ('mock-interview 12', 'part-5', 'mock-interview-12.run{r}', [1, 2, 3, 5]),
    ('mock-interview 13', 'part-5', 'mock-interview-13.run{r}', [2, 3, 4]),
]


def check_run(part_dir, stem, outcomes):
    """Return (passed, problems, fails) for one run."""
    problems = []
    fails = []
    ok = True
    for g in (1, 2):
        p = os.path.join(part_dir, '%s.grade-%d.json' % (stem, g))
        if 'killed' in p.split(os.sep):
            continue
        if not os.path.isfile(p):
            problems.append('grade-%d missing' % g)
            ok = False
            continue
        with open(p, encoding='utf-8') as f:
            d = json.load(f)
        verdicts = d.get('verdicts') or []
        for fld in ('missing', 'duplicates', 'incomplete', 'invalid', 'regraded'):
            if d.get(fld):
                problems.append('grade-%d self-reports %s=%s' % (g, fld, d.get(fld)))
        odd = sorted({str(v.get('verdict')) for v in verdicts} - {'PASS', 'FAIL'})
        if odd:
            problems.append('grade-%d has non-PASS/FAIL verdict strings %s' % (g, odd))
        for n in outcomes:
            hits = [v for v in verdicts if str(v.get('n')) == str(n)]
            if not hits:
                problems.append('grade-%d #%d missing' % (g, n))
                ok = False
            elif len(hits) > 1:
                problems.append('grade-%d #%d duplicated (%d)' % (g, n, len(hits)))
                ok = False
            else:
                verdict = str(hits[0].get('verdict', '')).strip().upper()
                if verdict != 'PASS':
                    fails.append('g%d#%d=%s' % (g, n, verdict))
                    ok = False
    return ok, problems, fails


def main():
    rows = []
    problems_all = []
    detail = []
    for model in MODELS:
        for name, part, pat, outcomes in SCREENS:
            per = {}
            for inst in INSTALLS:
                part_dir = os.path.join(ROOT, model, inst, part)
                n_pass = 0
                for r in range(5):
                    stem = pat.format(r=r)
                    ok, probs, fails = check_run(part_dir, stem, outcomes)
                    n_pass += ok
                    detail.append('%s %s %s %s: %s%s' % (
                        model, inst, part, stem, 'PASS' if ok else 'fail',
                        (' [' + ', '.join(fails) + ']') if fails else ''))
                    for pr in probs:
                        problems_all.append('%s/%s/%s %s: %s' % (model, inst, part, stem, pr))
                per[inst] = n_pass
            rows.append((model, name, ','.join(map(str, outcomes)), per['alone'], per['tuesday'],
                         per['alone'] + per['tuesday']))

    print('| model | screen | outcomes | alone /5 | tuesday /5 | pooled /10 |')
    print('|---|---|---|---|---|---|')
    for r in rows:
        print('| %s | %s | %s | %d | %d | %d |' % r)
    print()
    print('Problems (missing grade file / outcome missing or duplicated):')
    print('\n'.join(problems_all) if problems_all else 'none')
    print()
    print('Per-run detail:')
    print('\n'.join(detail))


if __name__ == '__main__':
    main()
