"""Locate every line/field holding the whole eval-12 IBAN in given streams (prints paths/metadata only)."""
import json, os, sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))  # helpers sit beside this script
from scan import runs, walk, ROOT
for stem in sys.argv[1:]:
    rd = os.path.join(ROOT, 'haiku', 'tuesday', 'part-5')
    meta = json.load(open(os.path.join(rd, stem + '.meta.json')))
    for ai, inv in enumerate(meta['invocations']):
        for ln, line in enumerate(open(os.path.join(rd, inv['stream'])), 1):
            if 22 not in runs(line):
                continue
            try:
                ev = json.loads(line)
            except Exception:
                print(stem, ai, ln, 'non-JSON line'); continue
            paths = [p for p, v in walk(ev) if 22 in runs(v)]
            extra = ''
            if ev.get('type') == 'user':
                c = ev['message'].get('content')
                if isinstance(c, list):
                    extra = ' first-text-start=' + repr([b.get('text', '')[:40] for b in c if b.get('type') == 'text'][:1])
            print(stem, f'a{ai}', f'L{ln}', ev.get('type'), ev.get('subtype'), paths, extra)
