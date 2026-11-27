import json, os, re, collections

M = '/var/tmp/tuesday-measure/1a'
STEM_RE = re.compile(r'^(job-underwriter|mock-interview)-(\d+)(?:\.(canned|denied))?\.run(\d+)$')
vals = collections.Counter()
issues = []
metastems = collections.defaultdict(list)
gradeinfo = {}
for model in ('haiku', 'sonnet'):
    for inst in ('alone', 'tuesday'):
        for part in ('part-4', 'part-5'):
            d = os.path.join(M, 'runs', model, inst, part)
            for fn in sorted(os.listdir(d)):
                p = os.path.join(d, fn)
                if fn.endswith('.meta.json'):
                    s = fn[:-len('.meta.json')]
                    m = json.load(open(p))
                    metastems[(model, inst, m.get('stem'))].append(part + '/' + fn)
                    sm = STEM_RE.match(s)
                    if not sm:
                        issues.append('unparsed stem %s/%s/%s/%s' % (model, inst, part, s))
                        continue
                    if m.get('skill') != sm.group(1) or m.get('id') != int(sm.group(2)) or m.get('run') != int(sm.group(4)):
                        issues.append('meta skill/id/run mismatch %s/%s/%s: %r %r %r' % (model, inst, s, m.get('skill'), m.get('id'), m.get('run')))
                    if sm.group(3) and m.get('mode') != sm.group(3):
                        issues.append('meta mode %r vs stem %s/%s/%s' % (m.get('mode'), model, inst, s))
                    if m.get('response_file') not in (None, s + '.md'):
                        issues.append('response_file %r for %s/%s/%s' % (m.get('response_file'), model, inst, s))
                    if not os.path.exists(os.path.join(d, s + '.md')):
                        issues.append('no .md for %s/%s/%s' % (model, inst, s))
                    if model not in str(m.get('model')):
                        issues.append('model %r in %s/%s/%s' % (m.get('model'), model, inst, s))
                    gi_ = m.get('graded_invocation')
                    if gi_ not in (0, None):
                        issues.append('graded_invocation=%r ninvocations=%d %s/%s/%s' % (gi_, len(m.get('invocations', [])), model, inst, s))
                mm = re.match(r'^(.*)\.grade-(\d+)\.json$', fn)
                if mm:
                    s, gi = mm.group(1), int(mm.group(2))
                    if gi not in (1, 2):
                        issues.append('grader index %d file %s' % (gi, p))
                    g = json.load(open(p))
                    sm = STEM_RE.match(s)
                    if g.get('grader') != gi:
                        issues.append('grader field %r in %s' % (g.get('grader'), p))
                    if sm and (g.get('skill') != sm.group(1) or g.get('id') != int(sm.group(2)) or g.get('run') != int(sm.group(4))):
                        issues.append('grade skill/id/run mismatch %s: %r %r %r' % (p, g.get('skill'), g.get('id'), g.get('run')))
                    if sm and sm.group(3) and g.get('mode') != sm.group(3):
                        issues.append('grade mode %r vs %s' % (g.get('mode'), p))
                    ns = collections.Counter()
                    gmap = {}
                    for v in g.get('verdicts', []):
                        vals[repr(v.get('verdict'))] += 1
                        ns[v.get('n')] += 1
                        gmap[v.get('n')] = v.get('verdict')
                        if not isinstance(v.get('n'), int):
                            issues.append('non-int n %r in %s' % (v.get('n'), p))
                    for n, c in ns.items():
                        if c > 1:
                            issues.append('dup n=%r x%d in %s' % (n, c, p))
                    gradeinfo[(model, inst, s, gi)] = gmap
                    if not os.path.exists(os.path.join(d, s + '.meta.json')):
                        issues.append('grade without meta %s' % p)
for k, v in metastems.items():
    if len(v) > 1:
        issues.append('duplicate meta stem %s: %s' % (k, v))
print('verdict values over all grade files:', dict(vals))
# n coverage per skill/case
cov = collections.defaultdict(set)
for (model, inst, s, gi), gm in gradeinfo.items():
    cov[s.split('.')[0]].add(tuple(sorted(n for n in gm if isinstance(n, int))))
for k in sorted(cov):
    print('n-sets', k, sorted(cov[k]))
# adjudication vs grade files
adj = [json.loads(l) for l in open(os.path.join(M, 'adjudications.jsonl')) if l.strip()]
for r in adj:
    k = (r['model'], r['install'], r['stem'], int(r['grader']))
    if k not in gradeinfo:
        issues.append('adj %s refers to missing grade file %s' % (r['id'], k))
        continue
    actual = gradeinfo[k].get(int(r['expectation']))
    if actual != r.get('grader_verdict'):
        issues.append('adj %s grader_verdict %r but grade file says %r (%s #%s)' % (r['id'], r.get('grader_verdict'), actual, k, r['expectation']))
dupkeys = collections.Counter((r['model'], r['install'], r['stem'], r['grader'], r['expectation'], r['gate']) for r in adj)
for k, c in dupkeys.items():
    if c > 1:
        issues.append('duplicate adjudication key %s x%d' % (k, c))
print('ISSUES (%d):' % len(issues))
for i in issues:
    print(' ', i)
