#!/usr/bin/env python3
"""Dump helper for the recheck: prints text/JSON with ID-like values masked.

Masks: IBAN-shaped strings, runs of 6+ digits (spaces/dashes allowed between),
and email addresses whose domain does not end in .example.

Usage:
  dump.py text <file>                       print a text file, masked, with line numbers
  dump.py eval <evals.json> <id>            print one eval (prompt, files, expectations)
  dump.py clause <evals.json> <name>        print one clause
  dump.py clauses <evals.json>              list clause names
  dump.py json <file>                       pretty-print JSON, masked
  dump.py stream <stream.jsonl> [maxlen]    print assistant text, tool_use inputs, tool results (truncated), user text
"""
import json
import re
import sys

# spaces/dashes allowed anywhere after the country code (e.g. grouped "XX 00 ABCD 1234 ...")
IBAN_RE = re.compile(r'\b[A-Za-z]{2}[ \-]?\d{2}(?:[ \-]?[A-Za-z0-9]){8,30}\b')
DIGITS_RE = re.compile(r'\d(?:[ \-]?\d){5,}')
EMAIL_RE = re.compile(r'[A-Za-z0-9._%+\-]+@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})')


EVALS = ['/var/tmp/tuesday-measure/1a3/frozen/cases/candidate/mock-interview.evals.json',
         '/var/tmp/tuesday-measure/1a3/frozen/cases/candidate/job-underwriter.evals.json']


def _planted():
    """Normalized planted IBAN(s) from the eval sentinels (kept in memory, never printed)."""
    out = set()
    for path in EVALS:
        try:
            with open(path, encoding='utf-8') as f:
                d = json.load(f)
            for ev in d['evals']:
                for s in ev.get('sentinels', []) or []:
                    for sp in s.get('spellings', []):
                        out.add(re.sub(r'[\s\-]', '', sp).upper())
        except Exception:
            pass
    return sorted(out)


PLANTED = _planted()


def _mask_planted(s):
    """Mask any run of 6+ consecutive planted-IBAN characters (spaces/dashes/case ignored)."""
    norm = re.sub(r'[\s\-]', '', s).upper()
    for p in PLANTED:
        if not any(p[i:i + 6] in norm for i in range(len(p) - 5)):
            continue
        for L in range(len(p), 5, -1):
            for i in range(0, len(p) - L + 1):
                frag = p[i:i + L]
                pat = r'[\s\-]*'.join(re.escape(c) for c in frag)
                s, n = re.subn(pat, '[planted-IBAN fragment %d chars]' % L, s, flags=re.I)
    return s


def mask(s):
    if not isinstance(s, str):
        s = json.dumps(s, ensure_ascii=False)
    s = _mask_planted(s)

    def iban(m):
        v = m.group(0)
        compact = re.sub(r'[ \-]', '', v)
        # require at least some digits beyond the check digits to look like an account number
        if sum(c.isdigit() for c in compact) >= 8:
            return '[IBAN-like %d chars, starts %s...]' % (len(compact), compact[:2])
        return v

    s = IBAN_RE.sub(iban, s)
    s = DIGITS_RE.sub(lambda m: '[%d-digit run]' % sum(c.isdigit() for c in m.group(0)), s)

    def email(m):
        dom = m.group(1).lower()
        if dom.endswith('.example') or dom == 'example':
            return m.group(0)
        return '[email masked]'

    s = EMAIL_RE.sub(email, s)
    return s


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def main():
    cmd = sys.argv[1]
    if cmd == 'text':
        with open(sys.argv[2], encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                print('%4d| %s' % (i, mask(line.rstrip('\n'))))
    elif cmd == 'json':
        print(mask(json.dumps(load(sys.argv[2]), indent=1, ensure_ascii=False)))
    elif cmd == 'clauses':
        d = load(sys.argv[2])
        for k in d.get('clauses', {}):
            print(k)
    elif cmd == 'clause':
        d = load(sys.argv[2])
        print(mask(d['clauses'][sys.argv[3]]))
    elif cmd == 'eval':
        d = load(sys.argv[2])
        want = sys.argv[3]
        for ev in d['evals']:
            if str(ev.get('id')) == want:
                for k, v in ev.items():
                    if k == 'expectations':
                        print('== expectations')
                        for i, e in enumerate(v, 1):
                            print('  #%d: %s' % (i, mask(e)))
                    elif k == 'files':
                        print('== files')
                        print(mask(json.dumps(v, indent=1, ensure_ascii=False)))
                    else:
                        print('== %s' % k)
                        print(mask(v))
                break
        else:
            print('no eval', want)
    elif cmd == 'stream':
        maxlen = int(sys.argv[3]) if len(sys.argv) > 3 else 600
        with open(sys.argv[2], encoding='utf-8') as f:
            for ln, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    print('%d: [unparseable]' % ln)
                    continue
                t = ev.get('type')
                if t in ('stream_event', 'rate_limit_event', 'active_goal', 'autocompact_state'):
                    continue
                if t == 'system' and ev.get('subtype') in ('status', 'thinking_tokens'):
                    continue
                msg = ev.get('message')
                if not isinstance(msg, dict):
                    msg = {}
                content = msg.get('content')
                if t in ('assistant', 'user') and content is not None:
                    if isinstance(content, str):
                        print('%d %s text: %s' % (ln, t, mask(content[:maxlen])))
                        continue
                    for b in content:
                        bt = b.get('type')
                        if bt == 'text':
                            txt = b.get('text', '')
                            lim = None if t == 'assistant' else maxlen
                            print('%d %s text: %s' % (ln, t, mask(txt if lim is None else txt[:lim])))
                        elif bt == 'tool_use':
                            print('%d %s tool_use %s: %s' % (ln, t, b.get('name'), mask(json.dumps(b.get('input'), ensure_ascii=False))))
                        elif bt == 'tool_result':
                            c = b.get('content')
                            if isinstance(c, list):
                                c = ' '.join(x.get('text', '') for x in c if isinstance(x, dict))
                            print('%d %s tool_result: %s' % (ln, t, mask(str(c)[:maxlen])))
                        elif bt == 'thinking':
                            print('%d %s thinking: %s' % (ln, t, mask(b.get('thinking', '')[:maxlen])))
                        else:
                            print('%d %s %s' % (ln, t, bt))
                else:
                    print('%d %s %s' % (ln, t, mask(json.dumps(ev, ensure_ascii=False)[:200])))
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
