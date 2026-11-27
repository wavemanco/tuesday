"""Positive control for scan.py: per stream, count parsed events and assistant blocks scanned,
and count non-assistant events (user prompt, tool results) that DO hold the case's IBAN whole.
Also runs the matcher over haiku runs (outside Task D scope) as a check on real data."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mask as M
ROOT = "/var/tmp/tuesday-measure/1a6/runs"
IB = M.ibans()
CASES = [("mock-interview-12", "part-5", "mock-interview-12.run%d", list(IB[("mock-interview", 12)])[0]),
         ("job-underwriter-8", "part-4", "job-underwriter-8.canned.run%d", list(IB[("job-underwriter", 8)])[0])]
for case, part, pat, iban in CASES:
    for model in ("sonnet", "opus", "haiku"):
        for inst in ("alone", "tuesday"):
            row = []
            for r in range(5):
                pd = os.path.join(ROOT, model, inst, part)
                meta = json.load(open(os.path.join(pd, (pat % r) + ".meta.json")))
                for ai, inv in enumerate(meta["invocations"]):
                    nev = nab = ntu = user_hits = asst_hits = 0
                    for line in open(os.path.join(pd, inv["stream"]), encoding="utf-8", errors="replace"):
                        try:
                            ev = json.loads(line)
                        except Exception:
                            continue
                        nev += 1
                        s = json.dumps(ev, ensure_ascii=False)
                        if ev.get("type") == "assistant":
                            for b in ev["message"]["content"]:
                                nab += 1
                                ntu += b.get("type") == "tool_use"
                            # raw-json check of the whole assistant event (covers any field)
                            if iban in M.norm(json.loads(json.dumps(s))):
                                asst_hits += 1
                        elif iban in M.norm(s):
                            user_hits += 1
                    row.append("r%d.a%d ev=%d blocks=%d tool_use=%d nonasst_with_iban=%d asst_events_with_iban(raw)=%d" % (r, ai, nev, nab, ntu, user_hits, asst_hits))
            print(M.mask("%s %s %s" % (case, model, inst)))
            for x in row:
                print("    " + M.mask(x))
