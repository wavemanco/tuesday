"""grepsurf.py <part_dir> <stem> <regex> [width]: grep md transcript and the graded invocation's saved files, masked."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mask as M
pd, stem, rx = sys.argv[1], sys.argv[2], sys.argv[3]
w = int(sys.argv[4]) if len(sys.argv) > 4 else 220
j = json.load(open(os.path.join(pd, stem + ".meta.json")))
inv = j["invocations"][j["graded_invocation"]]
surfs = [("md", os.path.join(pd, stem + ".md"))] + [("file:" + os.path.basename(f["copy"]), os.path.join(pd, f["copy"])) for f in inv["files"]]
for name, p in surfs:
    lines = open(p, encoding="utf-8", errors="replace").read().split("\n")
    for k, l in enumerate(lines, 1):
        for m in re.finditer(rx, l, re.I):
            a = max(0, m.start() - w); b = min(len(l), m.end() + w)
            print("%s L%d: %s" % (name, k, M.mask(("…" if a else "") + l[a:b] + ("…" if b < len(l) else ""))))
            break
