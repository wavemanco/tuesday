"""Dump helper: print a file (optionally a line range) through mask().
usage: python3 -I dump.py FILE [START END]
       python3 -I dump.py --json FILE KEYPATH   (dot-separated keys / list indexes)
       python3 -I dump.py --eval SKILL ID       (print one eval and the clauses it uses)
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mask import mask

args = sys.argv[1:]
if args[0] == "--json":
    obj = json.load(open(args[1]))
    if len(args) > 2 and args[2]:
        for k in args[2].split("."):
            obj = obj[int(k)] if isinstance(obj, list) else obj[k]
    print(mask(json.dumps(obj, indent=1, ensure_ascii=False)))
elif args[0] == "--eval":
    path = f"/var/tmp/tuesday-measure/1a4/frozen/cases/candidate/{args[1]}.evals.json"
    data = json.load(open(path))
    ev = [e for e in data["evals"] if str(e["id"]) == args[2]][0]
    print(mask(json.dumps(ev, indent=1, ensure_ascii=False)))
    used = set()
    for x in ev.get("expectations", []):
        used.update(re.findall(r"\{\{(\w+)\}\}", json.dumps(x)))
    want = args[3].split(",") if len(args) > 3 else sorted(used)
    for k in want:
        print(f"\n=== clause {k} ===")
        print(mask(data["clauses"].get(k, "<missing>") if isinstance(data["clauses"].get(k), str) else json.dumps(data["clauses"].get(k), indent=1, ensure_ascii=False)))
else:
    lines = open(args[0], encoding="utf-8", errors="replace").read().split("\n")
    s = int(args[1]) if len(args) > 1 else 1
    e = int(args[2]) if len(args) > 2 else len(lines)
    for i in range(s - 1, min(e, len(lines))):
        print(f"{i+1:5d}| {mask(lines[i])}")
