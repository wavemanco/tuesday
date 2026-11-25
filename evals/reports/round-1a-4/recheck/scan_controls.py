"""Controls for scan.py (Task D): per stream of every mock-interview-12 attempt,
(a) positive control: does the user prompt event hold the IBAN whole (it should);
(b) total characters of thinking text available (redacted thinking = 0);
(c) whether non-assistant system events (task_summary, post_turn_summary,
    permission_denied, result) hold the IBAN whole or 6+ chars.
Prints counts and booleans only."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_lib import best

ROOT = "/var/tmp/tuesday-measure/1a4/runs"
for model in ("haiku", "sonnet"):
    for inst in ("alone", "tuesday"):
        d = os.path.join(ROOT, model, inst, "part-5")
        for r in range(5):
            stem = f"mock-interview-12.run{r}"
            meta = json.load(open(os.path.join(d, stem + ".meta.json")))
            for ai, inv in enumerate(meta["invocations"]):
                first_user_whole = None
                think = 0
                sys_hits = []
                for ln, raw in enumerate(open(os.path.join(d, inv["stream"]), encoding="utf-8"), 1):
                    raw = raw.strip()
                    if not raw:
                        continue
                    ev = json.loads(raw)
                    t = ev.get("type")
                    if t == "user" and first_user_whole is None:
                        first_user_whole = best(json.dumps(ev.get("message", {}), ensure_ascii=False))[0]
                    if t == "assistant":
                        for b in ev.get("message", {}).get("content", []):
                            if b.get("type") == "thinking":
                                think += len(b.get("thinking", ""))
                    if t in ("system", "result"):
                        st = ev.get("subtype")
                        if st == "init":
                            continue
                        w, L, _ = best(json.dumps(ev, ensure_ascii=False))
                        if w or L >= 6:
                            sys_hits.append(f"L{ln} {t}/{st}: {'whole' if w else L}")
                print(f"{model}/{inst} {stem} att{ai}: first user event holds IBAN whole={first_user_whole}; thinking chars={think}; system/result hits={sys_hits or 'none'}")
