"""Control for Task D: for the given streams, locate each event holding 6+
IBAN chars and say which decoded string field holds it (path, length of run,
offset in IBAN). Prints no characters of the IBAN.
usage: python3 -I scan_locate.py STREAM..."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_lib import best

def walk(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, f"{p}.{k}" if p else k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{p}[{i}]")
    elif isinstance(o, str):
        yield p, o

for sp in sys.argv[1:]:
    for ln, raw in enumerate(open(sp, encoding="utf-8"), 1):
        raw = raw.strip()
        if not raw:
            continue
        ev = json.loads(raw)
        for p, v in walk(ev):
            w, L, off = best(v)
            if w or L >= 6:
                extra = ""
                if p.endswith(".text") and ev.get("type") == "user":
                    extra = f" starts-with-Base-directory={v.startswith('Base directory for this skill')}"
                print(f"{os.path.basename(sp)} L{ln} type={ev.get('type')} field={p} {'WHOLE' if w else f'run {L} at IBAN offset {off}'} (field len {len(v)}){extra}")
