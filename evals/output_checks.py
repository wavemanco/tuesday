"""Deterministic checks on a saved response: what can be read exactly, without a grader.

Three things in this suite were graded by a model reading prose and got wrong in
ways a parser would not have. A grader passed `yes` rows for targets no search was
aimed at, because nothing told it which searches ran. A grader failed a research
count that was right, for the same reason. And graders passed fit snapshots whose
"five of seven `direct`" disagreed with the map beneath them, because comparing a
sentence with a table two screens away is exactly the comparison CONTRIBUTING.md
says prose cannot hold. Each of those now has a fixed form in the skill — an
accounting table with one bare label per numbered row and a tally line above it,
a fit ledger projected from the evidence map by row ID, a verbatim column for
quoted evidence — and a fixed form can be checked.

Every function here is pure: it takes the response text, the fixture and the
harness's own record of the run, and returns findings. Nothing reads a file or
calls a model, so every decline path is testable in CI.

Each check reports PASS or FAIL with its reason, and is either `judgement` (the
skill decided something wrong) or `format` (the form was broken, so the judgement
could not be read). They are counted separately: a qualifier in a status cell and
a `yes` with no search behind it are different defects with different fixes, and
folding one into the other is how a formatting slip gets reported as wrong
accounting. A check that needs the harness's record of research calls is not run
on a response that has none — it is listed as unchecked, never passed.
"""

from __future__ import annotations

import re

VOCAB = ("yes", "skipped", "n/a", "unavailable")
SEARCH_KIND = {"WebSearch": "search", "mcp__web__search": "search",
               "WebFetch": "fetch", "mcp__web__fetch": "fetch"}
FILE_MARKER = re.compile(r"^----- file the response produced: (.+?) -----[ \t]*$", re.M)
LOG_CHECKS = ("yes_has_call", "skip_has_no_call", "unavailable_has_refusal",
              "zero_calls", "tally_searches", "tally_fetches")


def finding(check: str, target, ok: bool, why: str, kind: str = "judgement") -> dict:
    return {"check": check, "target": str(target), "verdict": "PASS" if ok else "FAIL",
            "why": why, "kind": kind}


# --- Reading the response ---------------------------------------------------

def split_response(text: str) -> list[tuple[str, str]]:
    """The chat text and each file the run produced, as (source, text) pairs.

    The harness appends delivered files below the chat under a marker line. A
    table that appears in both must be read in both: a response whose chat and
    file disagree has told the reader two different things.
    """
    marks = list(FILE_MARKER.finditer(text))
    if not marks:
        return [("chat", text)]
    sources = [("chat", text[:marks[0].start()])]
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        sources.append((mark.group(1), text[mark.end():end]))
    return sources


def split_cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    return [c.replace("\\|", "|").strip() for c in re.split(r"(?<!\\)\|", body)]


SEPARATOR = re.compile(r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?\s*$")


def md_tables(text: str) -> list[dict]:
    """Every pipe table in the text: {header, rows, line}."""
    lines = text.splitlines()
    tables, i = [], 0
    while i + 1 < len(lines):
        if lines[i].lstrip().startswith("|") and SEPARATOR.match(lines[i + 1]) \
                and "-" in lines[i + 1]:
            header = split_cells(lines[i])
            rows, j = [], i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                rows.append(split_cells(lines[j]))
                j += 1
            tables.append({"header": header, "rows": rows, "line": i + 1})
            i = j
        else:
            i += 1
    return tables


def bare(cell: str) -> str:
    """A cell with emphasis and code marks removed, lowercased (underscores kept:
    `must_have` is a token, not emphasis)."""
    return cell.replace("`", "").replace("*", "").strip().lower()


def header_names(table: dict) -> list[str]:
    return [cell.replace("`", "").replace("*", "").strip().lower() for cell in table["header"]]


# --- 6a. Research accounting ---------------------------------------------------

ROW_NUMBER = re.compile(r"^\s*[*_`]*\s*(\d+)\s*[.)]?")


def parse_accounting(text: str) -> dict:
    """Read the evidence-status accounting table: absent, unparseable or checked.

    Rows are keyed strictly by the number the row starts with. Saved runs show
    every other key varying — a target named three ways across five runs of one
    fixture, rows in a different order, two targets merged into one row — so
    mapping by order or by name would mis-file rows as often as it found them.
    A status cell must hold exactly one label; a qualifier beside it is recorded
    as a format violation and the leading label is still read, so the summary
    does not report a formatting slip as wrong accounting.
    """
    candidates, parsed, problems = 0, [], []
    for source, body in split_response(text):
        for table in md_tables(body):
            names = header_names(table)
            status_col = next((i for i, h in enumerate(names) if h in ("status", "ran")), None)
            numbered = bool(names) and names[0] in ("#", "no", "no.", "n") and len(names) > 1 \
                and "target" in names[1]
            if not names or ("target" not in names[0] and not numbered):
                # A table with the target further along — "Status | Target", say — is
                # still read, and its layout reported. A number in its own first column
                # ("# | Target | Status | Reason") is the same table drawn another way:
                # a probe run wrote it, and failing it would fail a correct accounting
                # on its drawing, so it is read without comment.
                if status_col is None or not any("target" in h for h in names[1:status_col]):
                    continue
                problems.append((None, f"{source}: the target is not the first column "
                                       f"(header: {' | '.join(table['header'])})"))
            candidates += 1
            if status_col is None:
                problems.append((None, f"{source}: the target table has no Status column "
                                       f"(header: {' | '.join(table['header'])})"))
                continue
            rows: dict[int, dict] = {}
            for cells in table["rows"]:
                first = cells[0] if cells else ""
                number = ROW_NUMBER.match(first)
                if not number:
                    problems.append((None, f"{source}: a row does not start with a target "
                                           f"number: {first[:80]!r}"))
                    continue
                n = int(number.group(1))
                raw = cells[status_col].strip() if status_col < len(cells) else ""
                status = raw.replace("`", "").replace("*", "").strip().lower()
                label = status
                if status not in VOCAB:
                    problems.append((n, f"{source}: row {n}'s status is {raw[:80]!r}, "
                                        f"not one bare label"))
                    lead = re.match(r"[a-z/]+", status)
                    if lead and lead.group(0) in VOCAB:
                        label = lead.group(0)
                if n in rows:
                    problems.append((n, f"{source}: target {n} has two rows"))
                    continue
                rows[n] = {"label": label, "raw": raw, "target": first,
                           "why": cells[2].strip() if len(cells) > 2 else ""}
            if rows:
                parsed.append((source, rows))
                break                                   # the first readable table per source
            problems.append((None, f"{source}: the target table has no numbered rows"))
    if not candidates:
        return {"outcome": "absent", "rows": {}, "format": [], "sources": []}
    if not parsed:
        return {"outcome": "unparseable", "rows": {}, "format": problems, "sources": []}
    first_source, rows = parsed[0]
    for source, other in parsed[1:]:
        if {n: r["label"] for n, r in other.items()} != {n: r["label"] for n, r in rows.items()}:
            problems.append((None, f"{first_source} and {source} carry accounting tables "
                                   f"that disagree"))
    return {"outcome": "checked", "rows": rows, "format": problems,
            "sources": [s for s, _ in parsed]}


TALLY = re.compile(
    r"research tier\s*:\s*(l\d)\s*[-–—]\s*(?:searches\s+(\d+)\s+of\s+(\d+)\s*,\s*"
    r"fetches\s+(\d+)\s+of\s+(\d+)|(no searches))\s*\.?\s*$", re.I)
TALLY_CANDIDATE = re.compile(r"research tier\s*:", re.I)


def parse_tally(text: str) -> dict:
    """Read the one fixed tally line: absent, unparseable or checked.

    The count a grader got wrong in set 3 was stated in free prose ("Searches
    attempted: 3. Completed: 0.") with nothing fixing which calls it counted.
    """
    found, loose = [], []
    for source, body in split_response(text):
        for line in body.splitlines():
            plain = line.replace("*", "").replace("`", "").strip()
            if not TALLY_CANDIDATE.search(plain):
                continue
            match = TALLY.search(plain)
            if not match:
                loose.append(f"{source}: {plain[:120]}")
                continue
            tier = match.group(1).upper()
            if match.group(6):
                found.append((source, {"tier": tier, "no_searches": True}))
            else:
                found.append((source, {"tier": tier, "no_searches": False,
                                       "searches": int(match.group(2)),
                                       "searches_budget": int(match.group(3)),
                                       "fetches": int(match.group(4)),
                                       "fetches_budget": int(match.group(5))}))
    if not found:
        return {"outcome": "unparseable" if loose else "absent", "lines": loose}
    tally = dict(found[0][1])
    tally["outcome"] = "checked"
    tally["disagree"] = [f"{found[0][0]} and {s}" for s, t in found[1:] if t != found[0][1]]
    return tally


def term_in(term: str, text: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])",
                     text.lower()) is not None


def same_url(a: str, b: str) -> bool:
    return str(a).strip().rstrip("/") == str(b).strip().rstrip("/")


def aimed_at(entry: dict, target: dict, pages: list[dict], mode: str) -> bool:
    """Was this call aimed at this target?

    By what it asked, never by what the response says it was for: its query (or
    URL) carries one of the target's terms, it fetched a page tagged with the
    target, or — where the server is ours — it returned one.
    """
    asked = str(entry.get("query_or_url") or "")
    if any(term_in(term, asked) for term in target.get("terms", [])):
        return True
    if entry.get("kind") == "fetch" and any(
            same_url(p.get("url", ""), asked) and p.get("target") == target.get("n")
            for p in pages):
        return True
    return mode == "canned" and target.get("n") in (entry.get("targets") or [])


def accepted(target: dict, mode: str) -> list[str]:
    accept = target.get("accept", [])
    if isinstance(accept, dict):
        return list(accept.get(mode, []))
    return list(accept)


def normalise_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def canary_in(spelling: str, text: str) -> bool:
    """A canary as a whole token run: "143" is not found inside "1430"."""
    return bool(spelling) and re.search(r"(?<![\w])" + re.escape(spelling) + r"(?![\w])", text) is not None


def check_accounting(response: str, research: dict, mode: str,
                     research_log: list | None) -> dict:
    """Judge the accounting against what the harness recorded. Returns findings.

    Attribution is per target, because a run-level check passed the failure the
    prototype actually produced: a `yes` on a target no call was aimed at, in a
    run that had made other calls. A refused call counts as a call — the budget
    is spent on what was sent, and a target searched and refused was not skipped.
    """
    checks, info, unchecked = [], [], []
    table = parse_accounting(response)
    tally = parse_tally(response)
    targets = research.get("targets", [])
    pages = research.get("pages", [])
    have_log = research_log is not None
    log = research_log or []

    for n, problem in table["format"]:
        checks.append(finding("format", n if n is not None else "all", False, problem, "format"))
    info.append(f"accounting table: {table['outcome']}")

    aimed = {t["n"]: [e for e in log if aimed_at(e, t, pages, mode)] for t in targets}
    if have_log:
        for entry in log:
            if not any(aimed_at(entry, t, pages, mode) for t in targets):
                info.append(f"unattributed call: {entry.get('tool')} "
                            f"{str(entry.get('query_or_url'))[:100]!r} ({entry.get('outcome')})")
    else:
        unchecked = list(LOG_CHECKS)
        info.append("no research log recorded for this run: the checks that need one "
                    f"({', '.join(LOG_CHECKS)}) were not run")

    for target in targets:
        n = target["n"]
        row = table["rows"].get(n)
        if row is None:
            why = {"absent": "the response has no accounting table",
                   "unparseable": "the accounting table could not be read"}.get(
                table["outcome"], f"no row starts with {n}")
            checks.append(finding("row", n, False, why))
            continue
        label = row["label"]
        checks.append(finding("row", n, True, f"row {n} reads {row['raw']!r}"))
        in_vocab = label in VOCAB
        checks.append(finding("vocabulary", n, in_vocab,
                              f"{label!r} is {'' if in_vocab else 'not '}one of {', '.join(VOCAB)}"))
        allowed = accepted(target, mode)
        if allowed:
            checks.append(finding("accept", n, label in allowed,
                                  f"{label!r} in a {mode} room; this fixture accepts "
                                  f"{' or '.join(allowed)}"))
        if not have_log:
            continue
        calls = aimed[n]
        sent = [e for e in calls if e.get("outcome") != "refused"]
        refused = [e for e in calls if e.get("outcome") in ("refused", "error")]
        listing = "; ".join(f"{e.get('tool')} {str(e.get('query_or_url'))[:60]!r} "
                            f"{e.get('outcome')}" for e in calls) or "none"
        if label == "yes":
            checks.append(finding("yes_has_call", n, bool(sent),
                                  f"`yes` needs a call aimed at target {n} that was not "
                                  f"refused; calls aimed at it: {listing}"))
        elif label in ("skipped", "n/a"):
            checks.append(finding("skip_has_no_call", n, not calls,
                                  f"`{label}` needs no call aimed at target {n}, refused "
                                  f"ones included; calls aimed at it: {listing}"))
        elif label == "unavailable" and mode == "canned":
            checks.append(finding("unavailable_has_refusal", n, bool(refused),
                                  f"search was offered in this room, so `unavailable` needs a "
                                  f"refused or errored call aimed at target {n}; calls aimed "
                                  f"at it: {listing}"))

    searches = sum(1 for e in log if e.get("kind") == "search")
    fetches = sum(1 for e in log if e.get("kind") == "fetch")
    if research.get("zero_calls") and have_log:
        checks.append(finding("zero_calls", "all", not log,
                              f"the inputs answer every target, so no call should be sent; "
                              f"{searches} search and {fetches} fetch attempt(s) recorded"))

    if tally["outcome"] != "checked":
        why = ("no `Research tier:` tally line" if tally["outcome"] == "absent" else
               "a `Research tier:` line that is not the fixed form: " + "; ".join(tally["lines"][:2]))
        checks.append(finding("tally", "all", False, why))
    else:
        checks.append(finding("tally", "all", True, "the tally line is present and readable"))
        for pair in tally.get("disagree", []):
            checks.append(finding("format", "all", False,
                                  f"{pair} carry tally lines that disagree", "format"))
        if tally["no_searches"]:
            if have_log:
                checks.append(finding("tally_searches", "all", searches == 0 and fetches == 0,
                                      f"`{tally['tier']} — no searches` with {searches} search "
                                      f"and {fetches} fetch attempt(s) recorded"))
        else:
            if have_log:
                checks.append(finding("tally_searches", "all", tally["searches"] == searches,
                                      f"the tally says {tally['searches']} search(es); "
                                      f"{searches} attempt(s) recorded, refused ones included"))
                checks.append(finding("tally_fetches", "all", tally["fetches"] == fetches,
                                      f"the tally says {tally['fetches']} fetch(es); "
                                      f"{fetches} attempt(s) recorded, refused ones included"))
            budget = research.get("budget") or {}
            problems = []
            if "searches" in budget and tally["searches_budget"] != budget["searches"]:
                problems.append(f"search budget stated as {tally['searches_budget']}, "
                                f"the tier's is {budget['searches']}")
            if "fetches" in budget and tally["fetches_budget"] != budget["fetches"]:
                problems.append(f"fetch budget stated as {tally['fetches_budget']}, "
                                f"the tier's is {budget['fetches']}")
            if tally["searches"] > tally["searches_budget"]:
                problems.append(f"{tally['searches']} searches over a budget of "
                                f"{tally['searches_budget']}")
            if tally["fetches"] > tally["fetches_budget"]:
                problems.append(f"{tally['fetches']} fetches over a budget of "
                                f"{tally['fetches_budget']}")
            checks.append(finding("tally_budget", "all", not problems,
                                  "; ".join(problems) or "within the stated and declared budget"))

    said = normalise_ws(response)
    for canary in research.get("canaries", []):
        n = canary.get("target")
        spellings = canary.get("text", "")
        spellings = [spellings] if isinstance(spellings, str) else list(spellings)
        # One fact may be written several ways — "143 employees", "143 staff" — and
        # a probe run rounded a survey's "$147,300" to "~$147K". A canary lists the
        # spellings that still prove the page was read; any one of them counts.
        present = any(canary_in(normalise_ws(s), said) for s in spellings if s.strip())
        if mode == "denied":
            checks.append(finding("canary_absent", n, not present,
                                  f"no search can return in this room, so the canary for "
                                  f"target {n} must not appear; it "
                                  f"{'does' if present else 'does not'}"))
        elif mode == "canned":
            row = table["rows"].get(n)
            if row and row["label"] == "yes":
                checks.append(finding("canary", n, present,
                                      f"row {n} reads `yes`, so what its page alone says "
                                      f"should reach the response; the canary "
                                      f"{'appears' if present else 'does not appear'}"))
    info.append(f"recorded attempts: {searches} search, {fetches} fetch" if have_log
                else "recorded attempts: not recorded")
    return {"checks": checks, "info": info, "unchecked": unchecked,
            "accounting": table["outcome"], "tally": tally["outcome"]}


# --- 6b. Fit ledger ------------------------------------------------------------

PRIORITIES = ("hard_gate", "must_have", "important", "preferred")
FITS = ("direct", "adjacent", "unclear", "absent", "hard_gate_fail")
BANDS = ("high", "medium", "low", "none")
LEDGER_MARK = re.compile(r"^\s*[*_]*\s*fit ledger\b", re.I)
LEDGER_LINE = re.compile(r"^-\s+`?([a-z_]+)`?\s*(?:—|–|-|:)\s*(.+?)\s*$")
ITEM = re.compile(r"^(R\d+[a-z]?)(?:\s+\((.+)\))?$")
GROUP = re.compile(r"^`?([a-z_]+)`?\s*:\s*(.+)$")
QUANTIFIER = re.compile(r"\b(every|all|only|none|both)\b", re.I)
ID_RE = re.compile(r"\bR\d+[a-z]?\b")
# A risk severity shares the band words — "all `low` severity" in the opportunity
# ledger — and is not a confidence band, so that one exact form is set aside.
BAND_TOKEN = re.compile(r"`(high|medium|low|none)`(?!\s+severity\b)")
BAND_ATTACHED = re.compile(r"\b(R\d+[a-z]?)\s*\(\s*`(high|medium|low|none)`\s*\)")


def split_top(text: str, separators: tuple[str, ...]) -> list[str]:
    """Split on any separator outside parentheses."""
    parts, depth, current, i = [], 0, "", 0
    while i < len(text):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if depth == 0:
            sep = next((s for s in separators if text.startswith(s, i)), None)
            if sep:
                parts.append(current)
                current, i = "", i + len(sep)
                continue
        current += ch
        i += 1
    parts.append(current)
    return [p.strip() for p in parts]


def parse_fit_ledger(text: str) -> dict:
    """The ledger's lines as [{priority, groups: [{fit, items: [{id, note}]}]}].

    Returns outcome absent / unparseable / checked. Unparseable names the line.
    """
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if LEDGER_MARK.match(line)), None)
    if start is None:
        return {"outcome": "absent", "lines": []}
    i = start + 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    raw = []
    while i < len(lines) and lines[i].lstrip().startswith("- "):
        raw.append(lines[i].strip())
        i += 1
    if not raw:
        return {"outcome": "unparseable", "lines": [],
                "why": f"no ledger lines under {lines[start].strip()[:100]!r}"}
    parsed, marked = [], []
    for line in raw:
        if "*" in line:
            # Bold or italic tokens are outside the grammar but not unreadable:
            # the projection is still judged, and the markup is reported apart.
            marked.append(line)
            line = line.replace("*", "")
        match = LEDGER_LINE.match(line)
        if not match or match.group(1) not in PRIORITIES:
            return {"outcome": "unparseable", "lines": [], "why": f"not a ledger line: {line[:100]!r}"}
        groups = []
        for chunk in split_top(match.group(2), (" · ", "·", ";")):
            group = GROUP.match(chunk)
            if not group or group.group(1) not in FITS:
                return {"outcome": "unparseable", "lines": [],
                        "why": f"not a fit group: {chunk[:80]!r} in {line[:100]!r}"}
            items = []
            for piece in split_top(group.group(2), (",",)):
                item = ITEM.match(piece)
                if not item:
                    return {"outcome": "unparseable", "lines": [],
                            "why": f"not a row ID: {piece[:60]!r} in {line[:100]!r}"}
                items.append({"id": item.group(1), "note": item.group(2)})
            groups.append({"fit": group.group(1), "items": items})
        parsed.append({"priority": match.group(1), "groups": groups, "line": line})
    return {"outcome": "checked", "lines": parsed, "marked": marked}


def evidence_map(text: str) -> dict | None:
    """The first table with #, Priority and Fit columns, rows keyed by #."""
    for table in md_tables(text):
        names = header_names(table)
        if not all(col in names for col in ("#", "priority", "fit")):
            continue
        col = {name: names.index(name) for name in ("#", "priority", "fit")}
        req = next((i for i, h in enumerate(names) if "requirement" in h), None)
        conf = next((i for i, h in enumerate(names) if "confidence" in h), None)
        rows = {}
        for cells in table["rows"]:
            def cell(i):
                return cells[i] if i is not None and i < len(cells) else ""
            rid = cell(col["#"]).replace("`", "").replace("*", "").strip()
            if rid:
                rows[rid] = {"priority": bare(cell(col["priority"])), "fit": bare(cell(col["fit"])),
                             "requirement": cell(req), "confidence": bare(cell(conf))}
        return rows
    return None


NAME_STOP = {"a", "an", "the", "and", "or", "of", "for", "with", "in", "on", "to", "at", "by"}


def names_requirement(note: str, requirement: str) -> bool:
    """The parenthetical is made of the Requirement's own words, in any order.

    The rule asks for a few of the Requirement's words so the reader can tell which
    row an ID is without scrolling to the map. A probe run wrote "R9 (Healthcare
    data / HIPAA experience)" for "Healthcare data experience (HIPAA)": the same
    words, reordered. A leading-fragment test failed it, and a check that fails a
    correct name teaches nothing but rewording. What it still refuses is a word the
    Requirement does not contain — a name that says something the map does not.
    """
    def words(s):
        return {w.rstrip("s") for w in re.findall(r"[a-z0-9+]+", s.replace("*", "").replace("`", "").lower())
                if w not in NAME_STOP}
    got = words(note)
    return bool(got) and got <= words(requirement)


def leading_fragment(note: str, requirement: str) -> bool:
    def norm(s):
        return normalise_ws(s.replace("`", "").replace("*", ""))
    frag, whole = norm(note), norm(requirement)
    if not frag or not re.search(r"[a-z0-9]", frag):
        return False
    return whole == frag or whole.startswith(frag + " ") or (
        whole.startswith(frag) and not whole[len(frag)].isalnum())


def snapshot_section(text: str) -> str | None:
    """The decision snapshot: its own heading's section, or what surrounds the ledger.

    A probe run titled its response with the user's question and gave the snapshot
    no heading; the ledger was there and its bands could not be read. Without a
    heading, the snapshot is the stretch from the heading above the ledger (or the
    top) to the next heading at level two or above.
    """
    lines = text.splitlines()
    mark = next((i for i, line in enumerate(lines) if LEDGER_MARK.match(line)), None)
    titled = any(re.match(r"^#{1,6}\s+.*snapshot", line, re.I) for line in lines)
    if not titled and mark is not None:
        start = next((j + 1 for j in range(mark, -1, -1) if re.match(r"^#{1,6}\s", lines[j])), 0)
        end = next((j for j in range(mark + 1, len(lines)) if re.match(r"^#{1,2}\s", lines[j])), len(lines))
        return "\n".join(lines[start:end])
    for i, line in enumerate(lines):
        head = re.match(r"^(#{1,6})\s+(.*)$", line)
        if head and "snapshot" in head.group(2).lower():
            level = len(head.group(1))
            end = next((j for j in range(i + 1, len(lines))
                        if (m := re.match(r"^(#{1,6})\s", lines[j])) and len(m.group(1)) <= level),
                       len(lines))
            return "\n".join(lines[i + 1:end])
    return None


AFTER_UNIVERSAL = re.compile(
    r"\b(?:every|only|none|the one|the rest|no other|any other|"
    r"all(?=\s+(?:the\s+|of\s+the\s+|other\s+)?(?:\w+[- ])?(?:rows?|requirements?|must[- _]?haves?|gates?|items?)\b))\b",
    re.I)


def ledger_sentence(text: str) -> str | None:
    """The paragraph directly after the ledger's lines, unless it is the next slot."""
    lines = text.splitlines()
    mark = next((i for i, line in enumerate(lines) if LEDGER_MARK.match(line)), None)
    if mark is None:
        return None
    i = mark + 1
    while i < len(lines) and (not lines[i].strip() or lines[i].lstrip().startswith("- ")):
        i += 1
    para = []
    while i < len(lines) and lines[i].strip():
        para.append(lines[i].strip())
        i += 1
    text = " ".join(para)
    if not text or text.startswith("**") or text.startswith("#") or text.startswith("|"):
        return None
    return text


def check_fit_ledger(response: str) -> dict:
    """The fit ledger is an exact projection of the evidence map, and counts nothing.

    The ledger replaced a sentence — "five of seven requirements are `direct`" —
    that the worked example taught with a wrong count from v0.1 and that measured
    runs copied and got wrong the same way. A projection can be compared with
    the map row by row; a sentence could only be argued with.
    """
    checks, info = [], []
    source_text = None
    for source, body in split_response(response):
        if parse_fit_ledger(body)["outcome"] != "absent":
            source_text = body
            info.append(f"fit ledger read from {source}")
            break
    ledger = parse_fit_ledger(source_text) if source_text is not None else {"outcome": "absent"}
    if ledger["outcome"] != "checked":
        absent = ledger["outcome"] == "absent"
        checks.append(finding("ledger_present", "all", False,
                              "no fit ledger" if absent else ledger.get("why", "unparseable"),
                              "judgement" if absent else "format"))
        return {"checks": checks, "info": info, "unchecked": []}
    checks.append(finding("ledger_present", "all", True, f"{len(ledger['lines'])} ledger line(s)"))
    if ledger.get("marked"):
        checks.append(finding("ledger_markup", "all", False,
                              f"emphasis in {len(ledger['marked'])} ledger line(s), e.g. "
                              f"{ledger['marked'][0][:80]!r}: tokens are bare or backticked",
                              "format"))

    rows = evidence_map(source_text)
    if rows is None:
        rows = next((m for _, body in split_response(response)
                     if (m := evidence_map(body)) is not None), None)
    if rows is None:
        checks.append(finding("evidence_map", "all", False,
                              "no table with #, Priority and Fit columns to project from"))
        return {"checks": checks, "info": info, "unchecked": []}

    placed: dict[str, list[tuple[str, str, str | None]]] = {}
    order_problems = []
    last_p = -1
    for line in ledger["lines"]:
        p = PRIORITIES.index(line["priority"])
        if p <= last_p:
            order_problems.append(f"`{line['priority']}` out of order or repeated")
        last_p = p
        last_f = -1
        for group in line["groups"]:
            f = FITS.index(group["fit"])
            if f <= last_f:
                order_problems.append(f"`{group['fit']}` out of order or repeated "
                                      f"under `{line['priority']}`")
            last_f = f
            for item in group["items"]:
                placed.setdefault(item["id"], []).append(
                    (line["priority"], group["fit"], item["note"]))
    checks.append(finding("ledger_order", "all", not order_problems,
                          "; ".join(order_problems) or "tiers and fits in enum order", "format"))

    missing = [r for r in rows if r not in placed]
    doubled = [r for r, where in placed.items() if len(where) > 1]
    stray = [r for r in placed if r not in rows]
    problems = ([f"missing: {', '.join(missing)}"] if missing else []) + \
               ([f"listed more than once: {', '.join(doubled)}"] if doubled else []) + \
               ([f"not in the map: {', '.join(stray)}"] if stray else [])
    checks.append(finding("ledger_coverage", "all", not problems,
                          "; ".join(problems) or f"all {len(rows)} map rows, once each"))

    wrong_tier = [f"{r} under `{w[0][0]}`, map says `{rows[r]['priority']}`"
                  for r, w in placed.items() if r in rows and w[0][0] != rows[r]["priority"]]
    wrong_fit = [f"{r} as `{w[0][1]}`, map says `{rows[r]['fit']}`"
                 for r, w in placed.items() if r in rows and w[0][1] != rows[r]["fit"]]
    checks.append(finding("ledger_tier", "all", not wrong_tier,
                          "; ".join(wrong_tier) or "every tier matches the map's Priority"))
    checks.append(finding("ledger_fit", "all", not wrong_fit,
                          "; ".join(wrong_fit) or "every fit matches the map's Fit"))

    copied_notes, bad_notes = set(), []
    for r, where in placed.items():
        for _, fit, note in where:
            requirement = rows.get(r, {}).get("requirement", "")
            if note and (leading_fragment(note, requirement) or names_requirement(note, requirement)):
                copied_notes.add(note)
            if fit == "direct":
                continue
            if not note:
                bad_notes.append(f"{r} (`{fit}`) has no parenthetical")
            elif not (leading_fragment(note, requirement) or names_requirement(note, requirement)):
                bad_notes.append(f"{r}'s ({note}) uses words its Requirement does not "
                                 f"({requirement[:60]!r})")
    checks.append(finding("ledger_parenthetical", "all", not bad_notes,
                          "; ".join(bad_notes) or "every row below `direct` is named in its "
                                                  "Requirement's own words", "format"))

    wording = []
    for line in ledger["lines"]:
        text = line["line"]
        # A parenthetical copied from the map's Requirement cell is the map's own
        # words — "5+ yrs PM" — not a count the ledger makes, so it is set aside.
        for note in copied_notes:
            text = text.replace(f"({note})", "()")
        text = ID_RE.sub("", text)
        if re.search(r"\d", text):
            wording.append(f"a numeral in {line['line'][:80]!r}")
        word = QUANTIFIER.search(text)
        if word:
            wording.append(f"{word.group(0)!r} in {line['line'][:80]!r}")
    checks.append(finding("ledger_wording", "all", not wording,
                          "; ".join(wording) or "no numeral or quantifier in the ledger"))

    # The one sentence the slot allows after the ledger is where the count came
    # back: a probe run wrote "R5b and R8 are the only rows below `direct`" under a
    # ledger that listed a third, and another "Every must-have is `direct`". The
    # rule forbids any universal over the map there, true or not, because the
    # true ones and the false ones read the same.
    after = ledger_sentence(source_text)
    word = AFTER_UNIVERSAL.search(after or "")
    checks.append(finding("ledger_sentence", "all", word is None,
                          f"{word.group(0)!r} in the sentence after the ledger: {after[:120]!r}"
                          if word else "the sentence after the ledger names rows and claims "
                                       "nothing about the rest"))

    section = snapshot_section(source_text)
    if section is None:
        checks.append(finding("snapshot_band", "all", False,
                              "no heading containing 'snapshot' to read the bands in",
                              "format"))
    else:
        attached = {m.start(2) - 1: m for m in BAND_ATTACHED.finditer(section)}
        band_problems = []
        for token in BAND_TOKEN.finditer(section):
            hit = attached.get(token.start())
            if hit is None:
                band_problems.append(f"`{token.group(1)}` is not attached to one row ID")
                continue
            rid, band = hit.group(1), hit.group(2)
            have = re.match(r"[a-z]+", rows.get(rid, {}).get("confidence", "") or "")
            if rid not in rows:
                band_problems.append(f"{rid} (`{band}`) is not a map row")
            elif not have or have.group(0) != band:
                band_problems.append(f"{rid} (`{band}`), map says "
                                     f"`{rows[rid].get('confidence', '')}`")
        checks.append(finding("snapshot_band", "all", not band_problems,
                              "; ".join(band_problems) or "every band sits beside its row and "
                                                          "matches its Confidence"))
    return {"checks": checks, "info": info, "unchecked": []}


# --- 6c. Quotes -----------------------------------------------------------------

DQUOTES = dict.fromkeys(map(ord, "“”„‟″«»"), '"')
APOSTROPHES = dict.fromkeys(map(ord, "‘’‛′"), "'")
DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")
EDGE = " \t\"'.,;:!?()[]{}-"


def normalise_quote(text: str) -> str:
    text = text.translate(DQUOTES).translate(APOSTROPHES).translate(DASHES)
    text = text.replace("*", "").replace("`", "")
    return re.sub(r"\s+", " ", text.casefold()).strip()


def quoted_spans(cell: str) -> list[str]:
    plain = cell.translate(DQUOTES)
    return [m.group(1) for m in re.finditer(r'"([^"\n]+)"', plain)]


def check_quotes(response: str, prompt: str, corpus_texts: list[str] | tuple = ()) -> dict:
    """Every quotation in the verbatim cells is a quotation of something.

    The fit snapshot's evidence column and the banks' Provenance cells exist so a
    claim about the candidate's past carries the words it rests on. A cell that
    paraphrases inside quotation marks defeats the column while looking like
    compliance — and graders passed exactly that, because the quote was close
    enough to read as the candidate's.
    """
    haystack = normalise_quote(prompt + "\n" + "\n".join(corpus_texts))
    checks, info = [], []
    counted = {"fit_snapshot": [0, 0], "banks": [0, 0]}         # spans, failures
    seen = {"fit_snapshot": False, "banks": False}
    for source, body in split_response(response):
        for table in md_tables(body):
            names = header_names(table)
            columns = []
            verbatim = next((i for i, h in enumerate(names) if "verbatim" in h), None)
            if verbatim is not None:
                columns.append(("fit_snapshot", verbatim))
            if any("provenance" in h for h in names) and any("answer guidance" in h for h in names):
                columns.append(("banks", next(i for i, h in enumerate(names) if "provenance" in h)))
            for section, col in columns:
                seen[section] = True
                for cells in table["rows"]:
                    if col >= len(cells):
                        continue
                    row_id = cells[0].replace("`", "").replace("*", "").strip()[:20]
                    for span in quoted_spans(cells[col]):
                        whole = normalise_quote(span).strip(EDGE)
                        if len(whole.split()) < 3:
                            continue
                        counted[section][0] += 1
                        bad = [frag for frag in (f.strip(EDGE) for f in
                                                 re.split(r"\.\.\.|…", normalise_quote(span)))
                               if len(frag.split()) >= 3 and frag not in haystack]
                        if bad:
                            counted[section][1] += 1
                            checks.append(finding(
                                "quotes", section, False,
                                f"{source} row {row_id}: \"{span.strip()[:120]}\" — "
                                f"\"{bad[0][:80]}\" is not in the request"
                                f"{' or the pages' if corpus_texts else ''}"))
    for section, (spans, failures) in counted.items():
        label = "fit snapshot (a column named 'verbatim')" if section == "fit_snapshot" \
            else "question banks (Provenance beside Answer guidance)"
        if not seen[section]:
            checks.append(finding("quotes", section, False, f"no {label} table", "format"))
        elif not failures:
            checks.append(finding("quotes", section, True,
                                  f"{spans} quotation(s) of three words or more, all verbatim"))
        info.append(f"{section}: {spans} quotation(s) checked, {failures} not verbatim")
    return {"checks": checks, "info": info, "unchecked": []}


# --- Assembly ----------------------------------------------------------------------

def run_checks(case: dict, mode: str, response: str, research_log: list | None,
               harness_status: str = "ok", harness_reasons: list | None = None) -> dict:
    """Everything this fixture asks for, as one {stem}.checks.json record."""
    if harness_status != "ok":
        return {"status": "harness-invalid", "mode": mode, "checks": [],
                "info": list(harness_reasons or []), "unchecked": []}
    checks, info, unchecked = [], [], []
    research = case.get("research")
    wanted = case.get("checks", [])
    parts = []
    if research:
        parts.append(check_accounting(response, research, mode, research_log))
    if "fit_ledger" in wanted:
        parts.append(check_fit_ledger(response))
    if "quotes" in wanted:
        corpus = [p.get("text", "") for p in (research or {}).get("pages", [])] \
            if mode == "canned" else []
        parts.append(check_quotes(response, case.get("prompt", ""), corpus))
    for part in parts:
        checks += part["checks"]
        info += part["info"]
        unchecked += part["unchecked"]
    failed = any(c["verdict"] == "FAIL" for c in checks)
    status = "fail" if failed else ("uncheckable" if unchecked else "ok")
    return {"status": status, "mode": mode, "checks": checks, "info": info,
            "unchecked": unchecked}
