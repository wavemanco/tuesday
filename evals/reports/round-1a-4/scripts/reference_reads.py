"""reference_reads.py M MODEL: per install and part, how many graded attempts read each reference file (Read calls
on skills/<module>/references/*.md in the sealed streams). Context for the report, no model calls."""
import ast, json, sys
from collections import Counter, defaultdict
from pathlib import Path

M, model = Path(sys.argv[1]), sys.argv[2]
seals = sorted(M.glob(f"sealed/{model}-quality-*"))
assert seals, "no sealed step"
SE = seals[-1] / model
tot = defaultdict(Counter); runs = Counter(); anyref = Counter()
for arm in ("alone", "tuesday"):
    for part in (1, 2, 4, 5):
        for mf in sorted((M / "runs" / model / arm / f"part-{part}").glob("*.meta.json")):
            meta = json.loads(mf.read_text())
            inv = meta["invocations"]; inv = ast.literal_eval(inv) if isinstance(inv, str) else inv
            g = meta.get("graded_invocation", 0)
            if g is None or g >= len(inv):
                continue
            room = Path(inv[g]["room"]).name
            s = SE / arm / f"part-{part}" / "streams" / f"{room}.jsonl"
            if not s.exists():
                continue
            seen = set()
            for l in s.read_text(errors="replace").splitlines():
                if '"Read"' not in l:
                    continue
                e = json.loads(l)
                if e.get("type") != "assistant":
                    continue
                for b in (e.get("message") or {}).get("content") or []:
                    if b.get("type") == "tool_use" and b.get("name") == "Read":
                        p = (b.get("input") or {}).get("file_path", "")
                        if "/references/" in p:
                            seen.add(p.rsplit("/", 1)[-1])
            key = (arm, part)
            runs[key] += 1
            anyref[key] += bool(seen)
            for f in seen:
                tot[key][f] += 1
for key in sorted(runs):
    print(f"{key[0]:8} part-{key[1]}: {anyref[key]}/{runs[key]} graded attempts read a reference; "
          + ", ".join(f"{f} {n}" for f, n in tot[key].most_common()))
