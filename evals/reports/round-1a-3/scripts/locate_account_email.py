"""locate_account_email.py M MODEL... > located-account-email.json

The scan records the runtime account email as counts only (E17), so a tool_input failure of kind account_email has
no `where`. This reads each such attempt's sealed stream ($M/sealed/<step>/<model>/<arm>/part-N/streams/<room>.jsonl),
gets the value from the kit's lib/account_email.py (captured, never printed), and lists, for every assistant
tool_use whose input holds it, the tool name and the key paths that hold it. The value is never written.
Used by score_1a.py to apply manifest section 23 option (a) to this kind as to the planted ones.
"""
import ast, json, re, subprocess, sys
from pathlib import Path

M, MODELS = Path(sys.argv[1]), sys.argv[2:]
v = subprocess.run([sys.executable, "-I", "-B", str(M / "frozen/kit/lib/account_email.py")],
                   capture_output=True, text=True).stdout
assert "@" in v
pat = re.compile(re.escape(v), re.I)


def paths(o, p=""):
    if isinstance(o, dict):
        for k, x in o.items():
            if pat.search(k):
                yield p + "." + "<key>"
            yield from paths(x, f"{p}.{k}")
    elif isinstance(o, list):
        for i, x in enumerate(o):
            yield from paths(x, f"{p}[{i}]")
    elif isinstance(o, str) and pat.search(o):
        yield p


out = []
for model in MODELS:
    for chk in sorted((M / "runs" / model).glob("*/part-*/*.checks.json")):
        c = json.loads(chk.read_text())
        if not any(x.get("check") == "sentinel" and x.get("target") == "account_email.tool_input"
                   and x.get("verdict") == "FAIL" for x in c.get("checks", [])):
            continue
        arm, part, stem = chk.parts[-3], chk.parts[-2], chk.name[:-len(".checks.json")]
        meta = json.loads(chk.with_name(stem + ".meta.json").read_text())
        inv = meta["invocations"]
        inv = ast.literal_eval(inv) if isinstance(inv, str) else inv
        hit_atts = [a for a, x in ((c.get("sentinel_scan") or {}).get("attempts") or {}).items()
                    if any(h.get("kind") == "account_email" and h.get("surface") == "tool_input"
                           for h in x.get("hits") or [])]
        for att in hit_atts:
            want_nudged = att == "nudged"
            rooms = [Path(i["room"]).name for i in inv if bool(i.get("nudged")) == want_nudged]
            found = []
            for room in rooms:
                for s in M.glob(f"sealed/*/{model}/{arm}/{part}/streams/{room}.jsonl"):
                    for n, line in enumerate(s.read_text(errors="replace").splitlines()):
                        if not line.strip() or not pat.search(line):
                            continue
                        e = json.loads(line)
                        if e.get("type") != "assistant":
                            continue
                        for b in (e.get("message") or {}).get("content") or []:
                            if b.get("type") == "tool_use":
                                ps = sorted(set(paths(b.get("input"))))
                                if ps:
                                    found.append(dict(event=n, tool=b.get("name"), paths=ps))
            out.append(dict(kind="account_email", model=model, arm=arm, part=part, stem=stem, attempt=att,
                            rooms=rooms, tool_uses=found,
                            skill_args_only=bool(found) and all(f["tool"] == "Skill" and f["paths"] == [".args"]
                                                                for f in found)))
json.dump(out, sys.stdout, indent=1)
print()
