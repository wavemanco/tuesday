import json, os, re, sys, collections

M = '/var/tmp/tuesday-measure/1a'
MODELS = ['haiku', 'sonnet']
INSTALLS = ['alone', 'tuesday']
PART = {'job-underwriter': 'part-4', 'mock-interview': 'part-5'}
# (label, skill, case id, canned_only, expectations)
SCREENS = [
    ('JU7', 'job-underwriter', 7, True, [1, 2, 3]),
    ('JU8', 'job-underwriter', 8, True, [2, 3, 4]),
    ('MI9', 'mock-interview', 9, True, [1, 2, 3]),
    ('MI10', 'mock-interview', 10, False, [1, 2, 3, 5]),
    ('MI11', 'mock-interview', 11, False, [1, 2, 3, 5]),
    ('MI12', 'mock-interview', 12, False, [1, 2, 3, 5]),
    ('MI13', 'mock-interview', 13, False, [2, 3, 4]),
]
BAR = {'haiku': (6, 2), 'sonnet': (7, 3)}
STEM_RE = re.compile(r'^(job-underwriter|mock-interview)-(\d+)(?:\.(canned|denied))?\.run(\d+)$')

odd = []

def load_json(p):
    with open(p) as f:
        return json.load(f)

# ---- overrides
overrides = {}  # (model, install, stem, grader, expectation) -> record id
adj = []
with open(os.path.join(M, 'adjudications.jsonl')) as f:
    for ln, line in enumerate(f, 1):
        if line.strip():
            adj.append(json.loads(line))
for r in adj:
    if r.get('gate') == 'quote/core quote' and str(r.get('adjudication', '')).startswith('overturned'):
        k = (r['model'], r['install'], r['stem'], int(r['grader']), int(r['expectation']))
        if k in overrides:
            odd.append('duplicate override key %s (%s, %s)' % (k, overrides[k], r['id']))
        overrides[k] = r['id']

# ---- load grades
def grade_map(path, stem, gi):
    d = load_json(path)
    vs = d.get('verdicts')
    if not isinstance(vs, list):
        odd.append('%s: verdicts not a list' % path)
        return {}
    m = {}
    for v in vs:
        n = v.get('n')
        val = v.get('verdict')
        if val not in ('PASS', 'FAIL'):
            odd.append('%s: n=%r verdict value %r' % (path, n, val))
        if n in m:
            odd.append('%s: duplicate n=%r (%r then %r)' % (path, n, m[n], val))
        m[n] = val
    if d.get('grader') not in (None, gi):
        odd.append('%s: grader field %r != file index %d' % (path, d.get('grader'), gi))
    return m

results = {}  # (model, install, label) -> dict
changed = []
all_rows = []
for model in MODELS:
    for inst in INSTALLS:
        for label, skill, cid, canned_only, exps in SCREENS:
            d = os.path.join(M, 'runs', model, inst, PART[skill])
            stems = set()
            for fn in os.listdir(d):
                mm = re.match(r'^(.*?)\.(meta\.json|grade-\d+\.json|md|checks\.json)$', fn)
                if not mm:
                    continue
                s = mm.group(1)
                sm = STEM_RE.match(s)
                if not sm:
                    continue
                if sm.group(1) != skill or int(sm.group(2)) != cid:
                    continue
                if canned_only and sm.group(3) != 'canned':
                    continue
                stems.add(s)
            res = {'stems': sorted(stems), 'setaside': [], 'unresolved': [],
                   'pass_g': [], 'fail_g': [], 'pass_o': [], 'fail_o': []}
            for s in sorted(stems, key=lambda x: (x.split('.run')[0], int(x.split('.run')[1]))):
                mp = os.path.join(d, s + '.meta.json')
                if not os.path.exists(mp):
                    res['unresolved'].append((s, 'no meta.json'))
                    odd.append('%s/%s/%s: no meta.json' % (model, inst, s))
                    continue
                meta = load_json(mp)
                if meta.get('stem') not in (None, s):
                    odd.append('%s/%s/%s: meta stem field %r' % (model, inst, s, meta.get('stem')))
                mdl = str(meta.get('model', ''))
                if model not in mdl:
                    odd.append('%s/%s/%s: meta model %r' % (model, inst, s, mdl))
                st = (meta.get('harness') or {}).get('status')
                if st != 'ok':
                    res['setaside'].append((s, st, (meta.get('harness') or {}).get('reasons')))
                    for gi in (1, 2):
                        if os.path.exists(os.path.join(d, '%s.grade-%d.json' % (s, gi))):
                            odd.append('%s/%s/%s: set-aside run has grade-%d file' % (model, inst, s, gi))
                    continue
                gm = {}
                missing = []
                for gi in (1, 2):
                    gp = os.path.join(d, '%s.grade-%d.json' % (s, gi))
                    if not os.path.exists(gp):
                        missing.append('grade-%d.json missing' % gi)
                        continue
                    gm[gi] = grade_map(gp, s, gi)
                    for n in exps:
                        if n not in gm[gi]:
                            missing.append('grader %d #%d missing' % (gi, n))
                if missing:
                    res['unresolved'].append((s, '; '.join(missing)))
                    continue
                cells_g = {(gi, n): gm[gi][n] for gi in (1, 2) for n in exps}
                cells_o = dict(cells_g)
                applied = []
                for (gi, n) in cells_o:
                    k = (model, inst, s, gi, n)
                    if k in overrides:
                        applied.append((overrides[k], gi, n, cells_o[(gi, n)]))
                        cells_o[(gi, n)] = 'PASS'
                pg = all(v == 'PASS' for v in cells_g.values())
                po = all(v == 'PASS' for v in cells_o.values())
                res['pass_g' if pg else 'fail_g'].append(s)
                res['pass_o' if po else 'fail_o'].append(s)
                fails = ['g%d#%d' % (gi, n) for (gi, n), v in sorted(cells_g.items()) if v != 'PASS']
                all_rows.append((model, inst, label, s, 'PASS' if pg else 'FAIL', 'PASS' if po else 'FAIL', ','.join(fails), applied))
                if applied:
                    changed.append((model, inst, label, s, pg, po, applied, fails))
            results[(model, inst, label)] = res

# ---- unused overrides
used = set()
for c in changed:
    for a in c[6]:
        used.add(a[0])
for k, rid in overrides.items():
    if rid not in used:
        odd.append('override %s %s not applied to any core-screen cell' % (rid, k))

# ---- report
def fmt(model, label, key):
    out = {}
    for inst in INSTALLS:
        r = results[(model, inst, label)]
        p = len(r['pass_' + key]); dec = p + len(r['fail_' + key])
        out[inst] = (p, dec, len(r['setaside']), len(r['unresolved']))
    return out

for key, title in (('g', 'AS GRADED'), ('o', 'WITH OVERRIDES')):
    print('=' * 20, title)
    for model in MODELS:
        need_pool, need_each = BAR[model]
        print('-- %s (bar: >=%d pooled, >=%d each install)' % (model, need_pool, need_each))
        print('%-5s %-9s %-9s %-9s %-8s %-8s %s' % ('scr', 'pooled', 'alone', 'tuesday', 'setaside', 'unres', 'bar'))
        met = 0
        for label, *_ in SCREENS:
            o = fmt(model, label, key)
            P = o['alone'][0] + o['tuesday'][0]; D = o['alone'][1] + o['tuesday'][1]
            sa = '%d/%d' % (o['alone'][2], o['tuesday'][2]); un = '%d/%d' % (o['alone'][3], o['tuesday'][3])
            ok = P >= need_pool and o['alone'][0] >= need_each and o['tuesday'][0] >= need_each
            met += ok
            print('%-5s %-9s %-9s %-9s %-8s %-8s %s' % (label, '%d/%d' % (P, D), '%d/%d' % o['alone'][:2], '%d/%d' % o['tuesday'][:2], sa, un, 'MEETS' if ok else 'no'))
        print('screens meeting bar: %d/7' % met)

print('=' * 20, 'SET-ASIDES')
for (model, inst, label), r in sorted(results.items()):
    for s in r['setaside']:
        print(model, inst, label, s)
print('=' * 20, 'UNRESOLVED')
for (model, inst, label), r in sorted(results.items()):
    for s in r['unresolved']:
        print(model, inst, label, s)
print('=' * 20, 'CHANGED BY OVERRIDES')
for c in changed:
    print(c)
print('=' * 20, 'STEM COUNTS')
for (model, inst, label), r in sorted(results.items()):
    print(model, inst, label, len(r['stems']))
print('=' * 20, 'ODD')
for o in odd:
    print(o)

with open(sys.argv[1], 'w') as f:
    for row in all_rows:
        f.write(json.dumps(row) + '\n')
