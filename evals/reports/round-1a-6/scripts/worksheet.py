"""worksheet.py M SCOREDIR OUT: build the section-13 worksheet for zero-gate and backstop events (no model calls).

For each event in <model>-score.json (kind zero or backstop), print the grader's finding, locate every passage it
quotes in the assistant-authored surfaces (chat, saved files, outbound tool arguments) and in the user's input
(the frozen case prompt and files), and, for backstop events, search those surfaces for the planted value with
spaces, dashes and letter case ignored.
"""
import json
import re
import sys
from pathlib import Path

M, SCORE, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])

QMAP = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
                      "…": "...", " ": " "})


def norm(s):
    return re.sub(r"\s+", " ", s.translate(QMAP)).lower()


def fragments(why):
    w = why.translate(QMAP)
    out = []
    for m in re.finditer(r'"([^"]{5,}?)"', w):
        out.append(m.group(1))
    for m in re.finditer(r"(?:(?<=\s)|(?<=^)|(?<=\())'(.{5,}?)'(?=[\s,.;:)!?]|$)", w):
        out.append(m.group(1))
    seen, res = set(), []
    for f in out:
        f = f.strip(" .,")
        for piece in re.split(r"\.\.\.", f):
            piece = piece.strip(" .,")
            if len(piece) >= 5 and piece.lower() not in seen:
                seen.add(piece.lower())
                res.append(piece)
    return res


def cases():
    out = {}
    for sk in ("job-underwriter", "mock-interview"):
        d = json.loads((M / "frozen/cases/candidate" / f"{sk}.evals.json").read_text())
        evs = d["evals"] if isinstance(d, dict) and "evals" in d else d
        for e in evs:
            out[(sk, e["id"])] = e
    return out


CASES = cases()


def user_text(case):
    parts = [case.get("prompt", "")]
    for f in case.get("files") or []:
        if isinstance(f, dict):
            parts.append(f.get("content") or "")
            p = f.get("path") or f.get("src")
        else:
            p = f
        if isinstance(p, str):
            for base in (M / "frozen/cases/candidate", M / "frozen", M.parent / (M.name + "-pins") / "candidate"):
                q = base / p
                if q.is_file():
                    parts.append(q.read_text(errors="replace"))
                    break
    return "\n".join(parts)


def run_dir(model, arm, stem):
    sk = "job-underwriter" if stem.startswith("job-underwriter") else "mock-interview"
    i = int(stem.split("-")[2].split(".")[0])
    new = i >= 7 if sk == "job-underwriter" else i >= 9
    part = {("job-underwriter", False): 1, ("mock-interview", False): 2,
            ("job-underwriter", True): 4, ("mock-interview", True): 5}[(sk, new)]
    return M / "runs" / model / arm / f"part-{part}", sk, i


def surfaces(d, stem):
    meta = json.loads((d / f"{stem}.meta.json").read_text())
    s = {"chat": (d / f"{stem}.md").read_text(errors="replace") if (d / f"{stem}.md").exists() else ""}
    for inv in meta.get("invocations") or []:
        for f in inv.get("files") or []:
            c = d / f.get("copy", "")
            if c.is_file():
                s[f"file:{f.get('path')}"] = c.read_text(errors="replace")
        for t in inv.get("tool_calls") or []:
            if t.get("name") in ("Skill", "Read", "Glob", "Grep", "ToolSearch") or (
                    t.get("name") == "Bash" and "/skills/" in json.dumps(t.get("input"))):
                continue
            s[f"tool:{t.get('name')}:{t.get('id', '')[-6:]}"] = json.dumps(t.get("input"), ensure_ascii=False)
    return s, meta


def ctx(text, frag, width=260):
    nt, nf = norm(text), norm(frag)
    k = nt.find(nf)
    if k < 0:
        return None
    a, b = max(0, k - width), min(len(nt), k + len(nf) + width)
    return ("..." if a else "") + nt[a:b] + ("..." if b < len(nt) else "")


def flex(value):
    chars = [c for c in value if c.isalnum()]
    return re.compile(r"[\s\-]*".join(re.escape(c) for c in chars), re.I)


lines = []
k = 0
for model in [m for m in ("haiku", "sonnet", "opus") if (SCORE / f"{m}-score.json").exists()]:
    rows = json.loads((SCORE / f"{model}-score.json").read_text())[0]["events"]
    for ev in rows:
        if ev["kind"] not in ("zero", "backstop"):
            continue
        k += 1
        d, sk, i = run_dir(ev["model"], ev["arm"], ev["stem"])
        surf, meta = surfaces(d, ev["stem"])
        case = CASES[(sk, i)]
        ut = user_text(case)
        lines.append(f"\n### A{k:03d} {model} {ev['arm']} {ev['stem']} #{ev['n']} {ev['kind']}/{ev['gate']} grader {ev['grader']}"
                     f" valid={ev['valid']}")
        lines.append(f"FINDING: {ev['why']}")
        lines.append(f"SURFACES: {', '.join(surf)}")
        if ev["kind"] == "backstop":
            for sn in case.get("sentinels") or []:
                if sn["kind"] != ev["gate"]:
                    continue
                pat = flex(sn["spellings"][1] if len(sn["spellings"]) > 1 else sn["spellings"][0])
                full = [(name, m.group(0)) for name, t in surf.items() for m in pat.finditer(t)]
                lines.append(f"  PLANTED {sn['label']}: full matches in assistant surfaces: {full or 'none'}")
                core = "".join(c for c in sn["spellings"][1] if c.isalnum())
                parts = []
                for L in (8, 6):
                    for a in range(0, len(core) - L + 1):
                        p = flex(core[a:a + L])
                        for name, t in surf.items():
                            for m in p.finditer(t):
                                parts.append((name, m.group(0), t[max(0, m.start() - 60):m.end() + 60].replace("\n", " ")))
                    if parts:
                        break
                seen = set()
                for name, g, c in parts:
                    if (name, c) in seen:
                        continue
                    seen.add((name, c))
                    lines.append(f"  PARTIAL in {name}: {g!r} :: {c}")
                    if len(seen) >= 6:
                        break
        for f in fragments(ev["why"]):
            hit = [(name, ctx(t, f)) for name, t in surf.items() if ctx(t, f)]
            uin = ctx(ut, f, 80)
            if hit:
                name, c = hit[0]
                lines.append(f"  QUOTE {f!r} -> in {name}{' (+%d more)' % (len(hit) - 1) if len(hit) > 1 else ''}"
                             f"{' [also in user input]' if uin else ''}\n      {c}")
            else:
                lines.append(f"  QUOTE {f!r} -> NOT in assistant surfaces{' [in user input]' if uin else ''}")
OUT.write_text("\n".join(lines) + "\n")
print(f"{k} events written to {OUT}")
