import json, os, re

M = '/var/tmp/tuesday-measure/1a'
PART = {'job-underwriter': 'part-4', 'mock-interview': 'part-5'}

def norm(s):
    s = s.lower()
    s = re.sub(r'[*`|]', '', s)
    s = s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    s = s.replace('—', '-').replace('–', '-')
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def norm_strict(s):
    # only what the brief asks: case, whitespace, * ` |
    s = s.lower()
    s = re.sub(r'[*`|]', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

recs = [json.loads(l) for l in open(os.path.join(M, 'adjudications.jsonl')) if l.strip()]
sel = [r for r in recs if str(r.get('gate', '')).startswith('zero/') and r.get('adjudication') == 'confirmed']
print('confirmed zero-gate records:', len(sel))
nf = 0
for r in sel:
    skill = 'job-underwriter' if r['stem'].startswith('job-underwriter') else 'mock-interview'
    p = os.path.join(M, 'runs', r['model'], r['install'], PART[skill], r['stem'] + '.md')
    if not os.path.exists(p):
        print('MISSING MD', r['id'], p)
        nf += 1
        continue
    raw = open(p).read()
    md_s = norm_strict(raw)
    md_l = norm(raw)
    passage = r.get('passage', '')
    parts = [x for x in re.split(r';|\.\.\.|…', passage)]
    parts = [x.strip() for x in parts]
    parts = [x for x in parts if norm(x).strip(' .,()"\'') != '']
    res = []
    for x in parts:
        xs = norm_strict(x)
        xl = norm(x)
        xt = xl.strip(' .,:()"\'')
        if xs and xs in md_s:
            res.append(('exact', x))
        elif xl and xl in md_l:
            res.append(('quote/dash-normalised', x))
        elif xt and xt in md_l:
            res.append(('after trimming edge punctuation', x))
        else:
            res.append(('NOT FOUND', x))
    bad = [x for t, x in res if t == 'NOT FOUND']
    tag = 'FAIL' if bad else 'ok'
    if bad:
        nf += 1
    print('%s %s %s/%s/%s g%s #%s %s surface=%s' % (tag, r['id'], r['model'], r['install'], r['stem'], r['grader'], r['expectation'], r['gate'], r.get('surface')))
    for t, x in res:
        print('     [%s] %r' % (t, x))
print('records with an excerpt not found:', nf)
