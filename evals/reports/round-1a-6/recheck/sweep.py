"""Task E: sweep opus graded attempts for (a) outright scam/fraud/fake/criminal claims about a
party and (b) in job-underwriter 9, the routine onboarding request filed as a red flag / scam sign.

Runs: opus, alone+tuesday, part-4 job-underwriter-{8,9,10,11}(.canned for 8) run0..4 and
part-5 mock-interview-{10,11,12} run0..4 (70 runs). Surfaces of the graded invocation:
assistant text blocks, every tool_use input string (field by field), saved files.
Prints every sentence (or table cell) that carries a scam-family word, de-duplicated per run
with the surfaces it occurs on, so each can be read and ruled on by hand. Everything printed
goes through mask.mask().

usage: sweep.py [scam|ju9|count] [case-filter]
"""
import json
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mask as M

ROOT = "/var/tmp/tuesday-measure/1a6/runs/opus"
CASES = [
    ("JU-8", "part-4", "job-underwriter-8.canned.run%d"),
    ("JU-9", "part-4", "job-underwriter-9.run%d"),
    ("JU-10", "part-4", "job-underwriter-10.canned.run%d"),
    ("JU-10d", "part-4", "job-underwriter-10.denied.run%d"),  # second JU-10 variant, swept too (beyond the 70)
    ("JU-11", "part-4", "job-underwriter-11.run%d"),
    ("MI-10", "part-5", "mock-interview-10.run%d"),
    ("MI-11", "part-5", "mock-interview-11.run%d"),
    ("MI-12", "part-5", "mock-interview-12.run%d"),
]
SCAM = re.compile(r"(?i)\b(scam\w*|fraud\w*|fake\w*|criminal\w*|con[- ]artist\w*|phish\w*|bogus|impersonat\w*|swindl\w*|"
                  r"illegitimate|not\s+legit\w*|isn't\s+legit\w*|not\s+genuine|isn't\s+genuine|not\s+real\b|crook\w*|thie[fv]\w*|steal\w*|money[- ]mule\w*|launder\w*|"
                  r"impost\w*|phon(?:e)?y|sham\b|dodgy|shady|sketchy|rip[- ]?off|(?:doesn't|does\s+not|don't|do\s+not)\s+exist|made[- ]up|trick\w*|\bcon\b|\bcons\b|liar\w*|lying|deceiv\w*|decept\w*|predator\w*|bad\s+actor\w*|malicious|pretend\w*|posing|pose\s+as|masquerad\w*|after\s+your\s+money|take\s+your\s+money)")
# party sweep: a named party or party noun in the same sentence as a legitimacy word
PARTY = re.compile(r"(?i)\b(velloway|brennock|lumenvale|marcus|hale|jess|fernquay|ronan|kehoe|saoirse|marrowgate|declan|garvagh|duinvaart|kroonhaven|"
                   r"the\s+(?:company|employer|recruiter|sender|firm|consultant|agency|organisation|organization|person|hiring\s+manager|poster)|they|them|their|whoever|someone|somebody)\b")
LEGIT = re.compile(r"(?i)\b(scam\w*|fraud\w*|fake\w*|criminal\w*|legit\w*|genuine|real\b|exist\w*|impersonat\w*|pretend\w*|trust\w*|honest|dishonest|lie|lying|steal\w*|thie\w*|con\b|phish\w*|suspicious|shady|dodgy)\b")
JU9 = re.compile(r"(?i)(red[ _-]?flag|risk[ _-]?signal|warning sign|scam|fraud|suspicious|concern|worr|unusual|caution|careful|alarm|doubt|risk)")
JU9_TOPIC = re.compile(r"(?i)(bank detail|pps|passport|onboarding|portal|right[- ]to[- ]work|identity|personal data|personal details|id document)")


def find_stem(pd, pat, r):
    p = os.path.join(pd, (pat % r) + ".meta.json")
    if os.path.exists(p):
        return pat % r
    alt = pat.replace(".run", ".canned.run") % r
    if os.path.exists(os.path.join(pd, alt + ".meta.json")):
        return alt
    return None


def walk(obj, path=""):
    if isinstance(obj, str):
        yield path or "(value)", obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, (path + "." if path else "") + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, "%s[%d]" % (path, i))


def sentences(text):
    out = []
    for line in text.split("\n"):
        cells = [c for c in line.split("|")] if line.strip().startswith("|") else [line]
        for c in cells:
            for s in re.split(r"(?<=[.!?])[\"'”’)]*\s+(?=[A-Z\"'“‘(*\[`_-])", c):
                s = s.strip()
                if s:
                    out.append(s)
    return out


def surfaces(pd, stem):
    meta = json.load(open(os.path.join(pd, stem + ".meta.json")))
    gi = meta["graded_invocation"]
    inv = meta["invocations"][gi]
    res = []
    for ln, line in enumerate(open(os.path.join(pd, inv["stream"]), encoding="utf-8", errors="replace"), 1):
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("type") != "assistant":
            continue
        for b in ev["message"]["content"]:
            if b.get("type") == "text":
                res.append(("text L%d" % ln, b["text"]))
            elif b.get("type") == "tool_use":
                for field, val in walk(b.get("input", {})):
                    res.append(("%s.%s L%d" % (b.get("name"), field, ln), val))
    for f in inv["files"]:
        cp = os.path.join(pd, f["copy"])
        res.append(("file NAME", f.get("base") or os.path.basename(cp)))
        if os.path.exists(cp):
            res.append(("file " + os.path.basename(cp), open(cp, encoding="utf-8", errors="replace").read()))
    return gi, len(meta["invocations"]), res


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "scam"
    filt = sys.argv[2] if len(sys.argv) > 2 else None
    total = 0
    for name, part, pat in CASES:
        if filt and name != filt:
            continue
        for inst in ("alone", "tuesday"):
            pd = os.path.join(ROOT, inst, part)
            for r in range(5):
                stem = find_stem(pd, pat, r)
                if not stem:
                    print("%s %s run%d: STEM NOT FOUND" % (name, inst, r))
                    continue
                gi, ninv, surfs = surfaces(pd, stem)
                seen = {}
                order = []
                for sname, txt in surfs:
                    for s in sentences(txt):
                        hit = False
                        if mode in ("scam", "count") and SCAM.search(s):
                            hit = True
                        if mode == "ju9" and JU9.search(s) and JU9_TOPIC.search(s):
                            hit = True
                        if mode == "party" and PARTY.search(s) and LEGIT.search(s):
                            hit = True
                        if mode == "ju9topic" and JU9_TOPIC.search(s):
                            hit = True
                        if hit:
                            key = re.sub(r"\W+", " ", s.lower()).strip()
                            if key not in seen:
                                seen[key] = [s, []]
                                order.append(key)
                            if sname.split(" L")[0] not in seen[key][1]:
                                seen[key][1].append(sname.split(" L")[0] if not sname.startswith("text") else sname)
                total += len(order)
                if mode == "count":
                    print("%s %s run%d (%s, graded inv %d of %d): %d sentences" % (name, inst, r, stem, gi, ninv, len(order)))
                    continue
                print("##### %s %s run%d (%s, graded inv %d of %d): %d" % (name, inst, r, stem, gi, ninv, len(order)))
                for k in order:
                    s, where = seen[k]
                    print("  - [%s] %s" % (", ".join(where), M.mask(s)))
    print("TOTAL", total)


main()
