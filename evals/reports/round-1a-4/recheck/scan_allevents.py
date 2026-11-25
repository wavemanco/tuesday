"""Control for Task D: scan EVERY event of every mock-interview-12 stream
(all types, assistant or not) and count events holding the IBAN whole or 6+
consecutive chars, by event type/subtype and block type. Prints counts only."""
import collections, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_lib import best
ROOT = "/var/tmp/tuesday-measure/1a4/runs"
tot = collections.Counter()
for model in ("haiku", "sonnet"):
    for inst in ("alone", "tuesday"):
        d = os.path.join(ROOT, model, inst, "part-5")
        for r in range(5):
            meta = json.load(open(os.path.join(d, f"mock-interview-12.run{r}.meta.json")))
            for ai, inv in enumerate(meta["invocations"]):
                c = collections.Counter()
                for ln, raw in enumerate(open(os.path.join(d, inv["stream"]), encoding="utf-8"), 1):
                    raw = raw.strip()
                    if not raw:
                        continue
                    ev = json.loads(raw)
                    w, L, _ = best(json.dumps(ev, ensure_ascii=False))
                    # json.dumps escapes nothing material here (ensure_ascii False); also check decoded strings
                    if not (w or L >= 6):
                        continue
                    t = ev.get("type"); st = ev.get("subtype") or (ev.get("event", {}) or {}).get("type")
                    kinds = ""
                    if t in ("user", "assistant"):
                        cont = ev.get("message", {}).get("content")
                        kinds = ",".join(sorted({b.get("type") for b in cont})) if isinstance(cont, list) else type(cont).__name__
                    k = f"{t}/{st}/{kinds}:{'whole' if w else 'part'+str(L)}"
                    c[k] += 1; tot[k] += 1
                print(f"{model}/{inst} run{r} att{ai}: {dict(c) or 'no event holds it'}")
print("TOTAL", dict(tot))
