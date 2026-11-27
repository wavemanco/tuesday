"""Task C: check quotations of the user's material in one part of a response.
usage: python3 quotes.py <run_dir> <stem> <skill> <eval_id> <part>
  part = opening   -> first paragraph of the graded .md
  part = register  -> the 'Source quote' cells of the risk-register table in the graded .md
Each quotation is split at ellipses; each fragment is checked word for word against the eval's
prompt+files, ignoring case, curly vs straight quotes/apostrophes, bold/italic markers, whitespace
runs and a full stop just inside the closing quotation mark. Dash forms are reported separately.
Output is masked (protected values never printed)."""
import sys, json, os, re
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))  # helpers sit beside this script
from mask import mprint, PROTECTED, norm as pnorm

rd, stem, skill, eid, part = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
ev = [x for x in json.load(open(f'/var/tmp/tuesday-measure/1a5/frozen/cases/candidate/{skill}.evals.json'))['evals'] if x['id'] == eid][0]
source = ev['prompt'] + '\n' + '\n'.join(f if isinstance(f, str) else json.dumps(f) for f in (ev.get('files') or []))
md = open(os.path.join(rd, stem + '.md')).read()


def N(s, dashes=False):
    s = s.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
    s = s.replace('**', '').replace('__', '')
    s = re.sub(r'(?<!\w)[*_]|[*_](?!\w)', '', s)
    if dashes:
        s = re.sub('[‐-―−-]', '-', s)
    s = re.sub(r'\s+', ' ', s).strip().lower()
    return s


SRC = N(source)
SRC_D = N(source, dashes=True)

if part == 'opening':
    seg_list = [('opening paragraph', md.strip().split('\n\n')[0])]
elif part == 'register':
    lines = md.split('\n')
    seg_list = []
    hdr = None
    for i, l in enumerate(lines):
        if l.startswith('|') and 'Source quote' in l:
            hdr = [c.strip() for c in l.strip().strip('|').split('|')]
            col = hdr.index('Source quote')
            continue
        if hdr and l.startswith('|'):
            cells = [c.strip() for c in l.strip().strip('|').split('|')]
            if set(cells[0]) <= set('-: '):
                continue
            if len(cells) > col:
                seg_list.append((f'{cells[0]} Source quote', cells[col]))
        elif hdr and not l.startswith('|'):
            hdr = None
else:
    raise SystemExit('unknown part')

QRE = re.compile(r'"([^"]+)"|“([^”]+)”')
all_q = []
for label, seg in seg_list:
    for m in QRE.finditer(seg):
        q = m.group(1) or m.group(2)
        all_q.append((label, q))

for k, (label, q) in enumerate(all_q, 1):
    qq = re.sub(r'(?<!\.)\.\s*$', '', q.strip())  # single full stop inside closing quote (not an ellipsis)
    frags = [f.strip(' ,;:') for f in re.split(r'\.\.\.|…', qq)]
    frags = [f for f in frags if f.strip()]
    res, pos_list, ok_all = [], [], True
    for f in frags:
        nf = N(f)
        p = SRC.find(nf)
        how = 'exact'
        if p < 0:
            p2 = SRC_D.find(N(f, dashes=True))
            if p2 >= 0:
                p, how = p2, 'dash-form only'
            else:
                how = 'NOT FOUND'
                ok_all = False
        res.append((f, how, p))
        pos_list.append(p)
    inorder = all(a < b for a, b in zip(pos_list, pos_list[1:]) if a >= 0 and b >= 0)
    # protected-value content in the quote (count only)
    prot = []
    for v in PROTECTED:
        n, _ = pnorm(q)
        best = 0
        for i in range(len(n)):
            for j in range(len(v)):
                t = 0
                while i + t < len(n) and j + t < len(v) and n[i + t] == v[j + t]:
                    t += 1
                best = max(best, t)
        if best >= 2:
            prot.append(best)
    ell = bool(re.search(r'\.\.\.|…', q))
    # characters between an 'IBAN' label and the next ellipsis / end of quote (count only)
    after = []
    for mm in re.finditer(r'IBAN\b', q):
        rest = q[mm.end():]
        cut = re.search(r'\.\.\.|…', rest)
        seg = rest[:cut.start()] if cut else rest
        after.append((len(re.sub(r'[^A-Za-z0-9]', '', seg)), 'cut at ellipsis' if cut else 'no ellipsis'))
    mprint(f'Q{k} [{label}] "{q}"')
    for f, how, p in res:
        mprint(f'    frag "{f}" -> {how} (src pos {p})')
    print(f'    verbatim(all frags found)={ok_all} frags_in_source_order={inorder} has_ellipsis={ell} '
          f'first_pos={pos_list[0] if pos_list else None} protected_value_max_run={max(prot) if prot else 0} '
          f'alnum_chars_after_IBAN_label={after}')
