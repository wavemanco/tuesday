"""Grep all assistant-authored surfaces of a run (all invocations) for a regex, masked output.
Surfaces: assistant text blocks and tool_use inputs in the raw stream, saved files, the .md.
usage: python3 grep_surfaces.py <run_dir> <stem> <regex> [context_chars]"""
import sys, json, os, re
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))  # helpers sit beside this script
from mask import mprint

rd, stem, rx = sys.argv[1], sys.argv[2], re.compile(sys.argv[3], re.I)
ctx = int(sys.argv[4]) if len(sys.argv) > 4 else 160
meta = json.load(open(os.path.join(rd, stem + '.meta.json')))
g = meta.get('graded_invocation')


def show(label, s):
    for m in rx.finditer(s):
        mprint(f'{label} @{m.start()}: ' + repr(s[max(0, m.start() - ctx):m.end() + ctx]))


for i, inv in enumerate(meta['invocations']):
    tag = f'inv{i}{"(graded)" if i == g else ""}'
    for f in inv.get('files', []) or []:
        c = f.get('copy')
        if c and os.path.exists(os.path.join(rd, c)):
            show(f'{tag} FILE {f.get("path")}', open(os.path.join(rd, c), errors='replace').read())
    for ln, line in enumerate(open(os.path.join(rd, inv['stream'])), 1):
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get('type') != 'assistant':
            continue
        for b in ev.get('message', {}).get('content', []):
            if b.get('type') == 'text':
                show(f'{tag} L{ln} text', b['text'])
            elif b.get('type') == 'tool_use':
                for k, v in (b.get('input') or {}).items():
                    show(f'{tag} L{ln} tool_use {b.get("name")}.{k}', v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))
