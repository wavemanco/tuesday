"""Count runs in the new rooms (parts 4 and 5) whose graded attempt needed the runner's nudge, per install and room.
Usage: nudges.py MEASURE_DIR MODEL"""
import json, sys, re
from pathlib import Path
from collections import Counter
M, model = Path(sys.argv[1]), sys.argv[2]
for arm in ("alone", "tuesday"):
    tot, nud, rooms = 0, 0, Counter()
    for p in (4, 5):
        for f in sorted((M / "runs" / model / arm / f"part-{p}").glob("*.meta.json")):
            m = json.loads(f.read_text())
            tot += 1
            if any(inv.get("nudged") for inv in m.get("invocations") or []):
                nud += 1
                rooms[re.sub(r"\.run\d+\.meta\.json$", "", f.name)] += 1
    print(f"{model} {arm}: nudged {nud}/{tot}", dict(sorted(rooms.items())))
