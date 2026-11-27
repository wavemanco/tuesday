"""Dump the assistant-authored surfaces of one run, masked.
usage: python3 dump_run.py <run_dir> <stem> [--all-inv] [--stream] [--md] [--files] [--tools] [--grades]
Default prints everything for the graded invocation."""
import sys, json, os
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))  # helpers sit beside this script
from mask import mprint, mask

rd, stem = sys.argv[1], sys.argv[2]
flags = set(sys.argv[3:])
everything = not (flags & {'--stream', '--md', '--files', '--tools', '--grades'})
meta = json.load(open(os.path.join(rd, stem + '.meta.json')))
g = meta.get('graded_invocation')
invs = list(enumerate(meta['invocations']))
if '--all-inv' not in flags:
    invs = [(i, v) for i, v in invs if i == g]
print('graded_invocation', g, 'n_invocations', len(meta['invocations']))

if everything or '--grades' in flags:
    for k in (1, 2):
        p = os.path.join(rd, f'{stem}.grade-{k}.json')
        if os.path.exists(p):
            gd = json.load(open(p))
            for v in gd.get('verdicts', []):
                mprint(f'G{k} #{v.get("n")} {v.get("verdict")}: {v.get("why")}')
if everything or '--md' in flags:
    mprint('==== MD ====\n' + open(os.path.join(rd, stem + '.md')).read())
for i, inv in invs:
    print(f'==== INVOCATION {i} nudged={inv.get("nudged")} outcome={inv.get("outcome")} stream={inv.get("stream")}')
    if everything or '--files' in flags:
        for f in inv.get('files', []) or []:
            mprint('-- FILE', json.dumps({k: v for k, v in f.items() if k != 'content'}))
            c = f.get('copy')
            if c and os.path.exists(os.path.join(rd, c)):
                mprint(open(os.path.join(rd, c), errors='replace').read())
    if everything or '--tools' in flags:
        for tc in inv.get('tool_calls', []) or []:
            mprint('-- TOOL', tc.get('name'), json.dumps(tc.get('input'), ensure_ascii=False))
    if '--stream' in flags:
        sp = os.path.join(rd, inv['stream'])
        for ln, line in enumerate(open(sp), 1):
            try:
                ev = json.loads(line)
            except Exception:
                continue
            t = ev.get('type')
            if t == 'assistant':
                for b in ev.get('message', {}).get('content', []):
                    if b.get('type') == 'text':
                        mprint(f'[L{ln} assistant text] ' + b['text'])
                    elif b.get('type') == 'tool_use':
                        mprint(f'[L{ln} tool_use {b.get("name")}] ' + json.dumps(b.get('input'), ensure_ascii=False)[:4000])
            elif t == 'user':
                c = ev.get('message', {}).get('content')
                if isinstance(c, list):
                    for b in c:
                        if b.get('type') == 'text' and b['text'].startswith('Base directory for this skill'):
                            mprint(f'[L{ln} user SKILL-LOAD] ' + b['text'][:200])
                        elif b.get('type') == 'tool_result':
                            cc = b.get('content')
                            s = json.dumps(cc, ensure_ascii=False) if not isinstance(cc, str) else cc
                            mprint(f'[L{ln} tool_result] ' + s[:300])
                elif isinstance(c, str):
                    mprint(f'[L{ln} user str] ' + c[:300])
