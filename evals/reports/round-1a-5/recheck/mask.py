"""Masking helper. Loads the planted IBAN from mock-interview eval 12 (never prints it)
and masks it, any 6+ char run of it (spaces/dashes/case ignored), any IBAN-shaped string,
long digit runs, and non-.example emails."""
import json, re, sys

EVALS = '/var/tmp/tuesday-measure/1a5/frozen/cases/candidate/mock-interview.evals.json'
SPACED_IBAN_RE = re.compile(r'\b[A-Z]{2}[ \-]?\d{2}(?:[ \-]?[A-Z0-9]{4}){3,}')
IBAN_RE = re.compile(r'\b[A-Z]{2}\d{2}(?:[ \-]?[A-Z0-9]){10,30}\b', re.I)


def _eval12_text():
    d = json.load(open(EVALS))
    e = [x for x in d['evals'] if x['id'] == 12][0]
    return json.dumps(e, ensure_ascii=False)


def find_iban():
    t = _eval12_text()
    cands = set()
    for m in re.finditer(r'\bIE\d{2}(?:[ \-]?[A-Z0-9]){14,22}', t):
        cands.add(re.sub(r'[ \-]', '', m.group(0)).upper())
    return sorted(cands)


_c = find_iban()
IBAN = _c[0] if len(_c) == 1 else None


def _protected():
    vals = set()
    for f in ('job-underwriter', 'mock-interview'):
        d = json.load(open(f'/var/tmp/tuesday-measure/1a5/frozen/cases/candidate/{f}.evals.json'))
        for e in d['evals']:
            for st in e.get('sentinels', []) or []:
                for x in st.get('spellings', []):
                    vals.add(re.sub(r'[ \-]', '', x).upper())
    return sorted(vals)


PROTECTED = _protected()


def norm(s):
    """Normalise: drop spaces/dashes, uppercase; return (normalised, index map to original)."""
    out, idx = [], []
    for i, ch in enumerate(s):
        if ch in ' - ‐‑‒–':
            continue
        out.append(ch.upper())
        idx.append(i)
    return ''.join(out), idx


def runs_of_iban(s, minlen=6, value=None):
    """Return list of (orig_start, orig_end, length) spans in s that hold >=minlen consecutive
    chars of IBAN (normalised). Maximal runs."""
    IBAN = value or globals()['IBAN']
    if not IBAN:
        return []
    n, idx = norm(s)
    spans = []
    i = 0
    L = len(IBAN)
    while i < len(n):
        best = 0
        for j in range(L):
            k = 0
            while i + k < len(n) and j + k < L and n[i + k] == IBAN[j + k]:
                k += 1
            best = max(best, k)
        if best >= minlen:
            spans.append((idx[i], idx[i + best - 1] + 1, best))
            i += best
        else:
            i += 1
    return spans


EMAIL_RE = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
DIGITS_RE = re.compile(r'\d(?:[ \-]?\d){7,}')


def mask(s):
    if not isinstance(s, str):
        s = str(s)
    # IBAN runs first (spans on original string)
    spans = runs_of_iban(s)
    for a, b, k in reversed(spans):
        s = s[:a] + f'[IBAN-RUN:{k}ch]' + s[b:]
    for v in PROTECTED:
        if v == IBAN:
            continue
        sp = runs_of_iban(s, minlen=min(6, len(v)), value=v)
        for a, b, k in reversed(sp):
            s = s[:a] + f'[PROTECTED-RUN:{k}ch]' + s[b:]
    # protected prefixes of 4+ chars (country code + check digits onward), spaced or not
    for v in PROTECTED:
        if len(v) < 10:
            continue
        n, idx = norm(s)
        out = []
        i = 0
        while True:
            j = n.find(v[:4], i)
            if j < 0:
                break
            k = 4
            while j + k < len(n) and k < len(v) and n[j + k] == v[k]:
                k += 1
            out.append((idx[j], idx[j + k - 1] + 1, k))
            i = j + k
        for a, b, k in reversed(out):
            s = s[:a] + f'[PROTECTED-PREFIX:{k}ch]' + s[b:]
    s = SPACED_IBAN_RE.sub('[IBAN-SHAPED]', s)
    s = IBAN_RE.sub(lambda m: '[IBAN-SHAPED]', s)
    s = EMAIL_RE.sub(lambda m: m.group(0) if m.group(0).lower().rstrip('.').endswith('.example') else '[EMAIL]', s)
    s = DIGITS_RE.sub('[LONGNUM]', s)
    return s


def mprint(*a, **kw):
    print(*[mask(x) for x in a], **kw)


if __name__ == '__main__':
    # self-test on eval 12 text
    t = _eval12_text()
    print('iban candidates found:', len(_c), 'len', len(IBAN) if IBAN else None)
    m = mask(t)
    print('runs in raw eval text:', [(k) for a, b, k in runs_of_iban(t)])
    print('runs left after mask:', runs_of_iban(m))
    print('IBAN-shaped left after mask:', len(IBAN_RE.findall(m)))
    print('protected values loaded:', len(PROTECTED))
    for f, i in (('job-underwriter', 7), ('job-underwriter', 8), ('mock-interview', 9)):
        d = json.load(open(f'/var/tmp/tuesday-measure/1a5/frozen/cases/candidate/{f}.evals.json'))
        t2 = json.dumps([x for x in d['evals'] if x['id'] == i][0], ensure_ascii=False)
        m2 = mask(t2)
        left = sum(len(runs_of_iban(m2, minlen=min(6, len(v)), value=v)) for v in PROTECTED)
        print(f, i, 'markers', len(re.findall(r'\[(?:IBAN|PROTECTED)-RUN:\d+ch\]|\[IBAN-SHAPED\]|\[LONGNUM\]', m2)), 'runs left', left)
    print('masked markers:', re.findall(r'\[IBAN-RUN:\d+ch\]|\[IBAN-SHAPED\]|\[EMAIL\]|\[LONGNUM\]', m))
