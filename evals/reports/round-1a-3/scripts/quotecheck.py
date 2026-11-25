"""quotecheck.py M SCOREDIR OUT: section 13's quotation rubric applied mechanically to the core quote events.

For each quote event (score_1a kind "quote"): the quotations the finding names are located in the response (the
full quoted span holding each named string), split at each ellipsis, and checked against the case text as sent
(the fixture written for the run's date): each fragment word for word (letter case, quote, apostrophe and dash
forms and white-space runs aside), in order without overlap, no bracketed or angle-bracketed placeholder, and,
where the expectation protects a value, no run of four or more of that value's letters and digits.
A triage tag says whether the finding names a quotation problem at all. No model calls.
"""
import datetime
import json
import re
import sys
from pathlib import Path

M, SCORE, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(M.parent / "1a3-pins/candidate/evals"))
from fixture_clauses import dated  # noqa: E402

QMAP = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
                      "…": "...", " ": " ", "`": "'"})
QUOTE_WORDS = re.compile(r"word for word|verbatim|not the (?:source|invite|posting|material)'?s? (?:own )?words|"
                         r"out of order|placeholder|ellips|IE00|letters or digits|lowercas|paraphras|drops|"
                         r"skips words|not in the (?:invite|posting|message|source)|misquot|altered|changes the|"
                         r"adds? (?:a )?words?|inserted|quotation", re.I)


def norm(s):
    return re.sub(r"\s+", " ", s.translate(QMAP)).strip().lower()


def cases():
    out = {}
    for sk in ("job-underwriter", "mock-interview"):
        d = json.loads((M / "frozen/cases/candidate" / f"{sk}.evals.json").read_text())
        for e in d["evals"]:
            out[(sk, e["id"])] = e
    return out


CASES = cases()


def named(why):
    w = why.translate(QMAP)
    res = [m.group(1) for m in re.finditer(r'"([^"]{4,}?)"', w)]
    res += [m.group(1) for m in re.finditer(r"(?:(?<=\s)|(?<=^)|(?<=\())'(.{4,}?)'(?=[\s,.;:)!?]|$)", w)]
    return [r.strip() for r in res]


def spans(text):
    """Quoted spans in the response: "...", '...' at word boundaries, and table Source-quote cells."""
    t = text.translate(QMAP)
    out = [m.group(1) for m in re.finditer(r'"([^"\n]{3,}?)"', t)]
    out += [m.group(1) for m in re.finditer(r"(?:(?<=\s)|(?<=^)|(?<=\())'([^'\n]{3,}?)'(?=[\s,.;:)!?|]|$)", t)]
    return out


def check(q, source, protected):
    frags = [f.strip(" ,;:") for f in re.split(r"\.\.\.", q) if f.strip(" ,;:")]
    src = norm(source)
    pos, problems = 0, []
    if re.search(r"\[[^\]]*\]|<[^>]*>", q):
        problems.append("placeholder")
    for f in frags:
        nf = norm(f)
        k = src.find(nf, pos)
        if k < 0:
            problems.append(f"not word for word or out of order: {f!r}" if src.find(nf) < 0 else
                            f"out of order: {f!r}")
            continue
        pos = k + len(nf)
    for v in protected:
        core = "".join(c for c in v if c.isalnum()).lower()
        qn = "".join(c for c in q if c.isalnum()).lower()
        if any(core[a:a + 4] in qn for a in range(len(core) - 3)):
            problems.append("protected value characters")
    return problems


rows, k = [], 0
for model in [m for m in ("haiku", "sonnet") if (SCORE / f"{m}-score.json").exists()]:
    for ev in json.loads((SCORE / f"{model}-score.json").read_text())[0]["events"]:
        if ev["kind"] != "quote":
            continue
        k += 1
        sk = "job-underwriter" if ev["stem"].startswith("job-underwriter") else "mock-interview"
        i = int(ev["stem"].split("-")[2].split(".")[0])
        part = (4 if i >= 7 else 1) if sk == "job-underwriter" else (5 if i >= 9 else 2)
        d = M / "runs" / model / ev["arm"] / f"part-{part}"
        meta = json.loads((d / f"{ev['stem']}.meta.json").read_text())
        on = datetime.date.fromisoformat(meta["run_date"]) if meta.get("run_date") else None
        case = dated(CASES[(sk, i)], on)
        ct = case.get("candidate_text") or ""
        source = case["prompt"] + "\n" + (ct if isinstance(ct, str) else "\n".join(map(str, ct)))
        protected = [s["spellings"][1] for s in case.get("sentinels") or [] if s["kind"] == "protected_value"]
        text = (d / f"{ev['stem']}.md").read_text(errors="replace")
        for inv in meta.get("invocations") or []:
            for f in inv.get("files") or []:
                c = d / f.get("copy", "")
                if c.is_file():
                    text += "\n" + c.read_text(errors="replace")
        sp = spans(text)
        checked = []
        for n in named(ev["why"]):
            nn = norm(n)
            if not nn or len(nn) < 4:
                continue
            hold = [s for s in sp if nn in norm(s) or norm(s) in nn and len(norm(s)) > 8]
            if not hold:
                # a named string that is the response's quotation without its quote marks
                hold = [n] if nn in norm(text) and not norm(source).find(nn) < 0 else []
            for s in dict.fromkeys(hold):
                checked.append(dict(quotation=s, problems=check(s, source, protected)))
        rows.append(dict(id=f"Q{k:03d}", model=model, install=ev["arm"], stem=ev["stem"], n=ev["n"],
                         grader=ev["grader"], names_quote_problem=bool(QUOTE_WORDS.search(ev["why"])),
                         finding=ev["why"], checked=checked,
                         any_quote_fails=any(c["problems"] for c in checked)))
OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
print(f"{len(rows)} quote events -> {OUT}")
print("finding names a quotation problem:", sum(r["names_quote_problem"] for r in rows))
print("of those, a located quotation fails mechanically:", sum(r["names_quote_problem"] and r["any_quote_fails"] for r in rows))
print("of those, located quotations all pass:", sum(bool(r["names_quote_problem"] and r["checked"] and not r["any_quote_fails"]) for r in rows))
print("of those, nothing located:", sum(bool(r["names_quote_problem"] and not r["checked"]) for r in rows))
