"""Control for Task D: scan every file under each part-5 files/ folder that
belongs to a mock-interview-12 attempt (by the attempt's stream name), and
compare with the files the meta lists. Prints counts and hit flags only."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_lib import best
ROOT = "/var/tmp/tuesday-measure/1a4/runs"
for model in ("haiku", "sonnet"):
    for inst in ("alone", "tuesday"):
        d = os.path.join(ROOT, model, inst, "part-5")
        for r in range(5):
            meta = json.load(open(os.path.join(d, f"mock-interview-12.run{r}.meta.json")))
            for ai, inv in enumerate(meta["invocations"]):
                case = os.path.basename(inv["stream"]).replace(".jsonl", "")
                fd = os.path.join(d, "files", case)
                listed = {f.get("copy") for f in inv.get("files", [])}
                found, hits = [], []
                if os.path.isdir(fd):
                    for root, _, fs in os.walk(fd):
                        for f in fs:
                            p = os.path.join(root, f)
                            relp = os.path.relpath(p, d)
                            found.append(relp)
                            w, L, _ = best(open(p, encoding="utf-8", errors="replace").read() + " " + relp)
                            if w or L >= 6:
                                hits.append((relp, w, L))
                unlisted = [x for x in found if x not in listed]
                print(f"{model}/{inst} run{r} att{ai}: files on disk={len(found)} listed in meta={len(listed)} unlisted={len(unlisted)} hits={hits or 'none'}")
