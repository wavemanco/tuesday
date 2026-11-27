"""Dump helper: every printed string goes through mask.mask().

usage:
  dump.py eval <skill> <id> [prompt|files|exp|all] [n]
  dump.py clause <skill> <name>
  dump.py text <path> [from_line] [to_line]
  dump.py grades <part_dir> <stem> [n ...]
  dump.py meta <part_dir> <stem>
  dump.py grep <path> <regex> [context_chars]
"""
import json
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mask as M


def P(*a):
    print(M.mask(" ".join(str(x) for x in a)))


def load_eval(skill, i):
    d = json.load(open(M.EVAL_DIR + skill + ".evals.json"))
    for e in d["evals"]:
        if e["id"] == int(i):
            return d, e
    raise SystemExit("no eval")


def expand(d, s):
    def rep(m):
        return d["clauses"][m.group(1)]
    return re.sub(r"\{\{(\w+)\}\}", rep, s)


def main():
    cmd = sys.argv[1]
    if cmd == "eval":
        skill, i = sys.argv[2], sys.argv[3]
        what = sys.argv[4] if len(sys.argv) > 4 else "all"
        d, e = load_eval(skill, i)
        if what in ("prompt", "all"):
            P("=== PROMPT ===\n" + e["prompt"])
        if what in ("files", "all"):
            for f in e.get("files", []):
                P("=== FILE ===\n" + (f if isinstance(f, str) else json.dumps(f, indent=1, ensure_ascii=False)))
        if what in ("exp", "all"):
            ns = [int(x) for x in sys.argv[5:]]
            for n, x in enumerate(e["expectations"], 1):
                if ns and n not in ns:
                    continue
                P("=== EXP #%d ===\n%s" % (n, expand(d, x) if isinstance(x, str) else json.dumps(x, ensure_ascii=False)))
        if what == "other":
            for k in sys.argv[5:]:
                P("=== %s ===\n%s" % (k, json.dumps(e.get(k), indent=1, ensure_ascii=False)))
    elif cmd == "clause":
        d = json.load(open(M.EVAL_DIR + sys.argv[2] + ".evals.json"))
        P(d["clauses"][sys.argv[3]])
    elif cmd == "text":
        lines = open(sys.argv[2], encoding="utf-8", errors="replace").read().split("\n")
        a = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        b = int(sys.argv[4]) if len(sys.argv) > 4 else len(lines)
        for k in range(a - 1, min(b, len(lines))):
            print("%5d| %s" % (k + 1, M.mask(lines[k])))
    elif cmd == "grades":
        pd, stem = sys.argv[2], sys.argv[3]
        ns = [int(x) for x in sys.argv[4:]]
        for g in (1, 2):
            p = os.path.join(pd, "%s.grade-%d.json" % (stem, g))
            if not os.path.exists(p):
                print("grade-%d MISSING" % g)
                continue
            j = json.load(open(p))
            for v in j.get("verdicts", []):
                if ns and v.get("n") not in ns:
                    continue
                P("grade-%d #%s %s :: %s" % (g, v.get("n"), v.get("verdict"), v.get("why")))
    elif cmd == "meta":
        pd, stem = sys.argv[2], sys.argv[3]
        j = json.load(open(os.path.join(pd, stem + ".meta.json")))
        P("keys:", list(j.keys()))
        P("graded_invocation:", j.get("graded_invocation"))
        for k, inv in enumerate(j.get("invocations", [])):
            P("inv", k, "keys", list(inv.keys()))
            P("  stream:", inv.get("stream"))
            for f in inv.get("files", []):
                P("  file:", json.dumps(f, ensure_ascii=False))
            for t in inv.get("tool_calls", []):
                s = json.dumps(t, ensure_ascii=False)
                P("  tool:", s[:300])
    elif cmd == "blocks":
        # blocks <part_dir> <stem> [maxchars] : assistant text/tool_use blocks of the graded invocation, in order
        pd, stem = sys.argv[2], sys.argv[3]
        mx = int(sys.argv[4]) if len(sys.argv) > 4 else 400
        j = json.load(open(os.path.join(pd, stem + ".meta.json")))
        gi = j.get("graded_invocation", 0)
        for k, inv in enumerate(j["invocations"]):
            print("=== invocation %d%s nudged=%s" % (k, " (GRADED)" if k == gi else "", inv.get("nudged")))
            sp = os.path.join(pd, inv["stream"])
            for ln, line in enumerate(open(sp, encoding="utf-8", errors="replace"), 1):
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                t = ev.get("type")
                if t == "assistant":
                    for b in ev.get("message", {}).get("content", []):
                        if b.get("type") == "text":
                            print("L%d text: %s" % (ln, M.mask(repr(b["text"][:mx]))))
                        elif b.get("type") == "tool_use":
                            print("L%d tool_use %s: %s" % (ln, b.get("name"), M.mask(json.dumps(b.get("input"), ensure_ascii=False)[:mx])))
                elif t == "user":
                    c = ev.get("message", {}).get("content")
                    if isinstance(c, list):
                        for b in c:
                            if b.get("type") == "text" and b["text"].startswith("Base directory for this skill"):
                                print("L%d user: [skill text loads] %s" % (ln, M.mask(b["text"][:120])))
                    elif isinstance(c, str) and c.startswith("Base directory for this skill"):
                        print("L%d user: [skill text loads] %s" % (ln, M.mask(c[:120])))
    elif cmd == "grep":
        txt = open(sys.argv[2], encoding="utf-8", errors="replace").read()
        c = int(sys.argv[4]) if len(sys.argv) > 4 else 150
        for m in re.finditer(sys.argv[3], txt):
            ln = txt.count("\n", 0, m.start()) + 1
            print("L%d: " % ln + M.mask("...%s..." % txt[max(0, m.start() - c): m.end() + c]))


main()
