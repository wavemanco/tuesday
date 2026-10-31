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

import json
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ci"))
import ledger_rules  # noqa: E402  (the fit-ledger rules, shared with ci/check_skills.py)

VOCAB = ("yes", "skipped", "n/a", "unavailable")
SEARCH_KIND = {"WebSearch": "search", "mcp__web__search": "search",
               "WebFetch": "fetch", "mcp__web__fetch": "fetch"}
FILE_MARKER = re.compile(r"^----- file the response produced: (.+?) -----[ \t]*$", re.M)
LOG_CHECKS = ("yes_has_call", "skip_has_no_call", "unavailable_has_refusal",
              "zero_calls", "tally_searches", "tally_fetches", "tally_user_links",
              "off_target_shown", "off_target_has_call")


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
    does not report a formatting slip as wrong accounting. The one un-numbered
    row the rule allows — an off-target call's, bare `yes`, after every numbered
    row — is returned under `extra` and never keyed to a target.
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
            extras: list[dict] = []
            for cells in table["rows"]:
                first = cells[0] if cells else ""
                number = ROW_NUMBER.match(first)
                raw = cells[status_col].strip() if status_col < len(cells) else ""
                status = raw.replace("`", "").replace("*", "").strip().lower()
                if not number:
                    # A call sent outside every declared target is shown as an
                    # un-numbered row after the numbered ones, labeled `yes`
                    # (interaction-grammar §4). Only that exact form is read as one:
                    # before the numbered rows, or under any other label, an
                    # un-numbered row could stand in for a declared target's own.
                    if rows and status == "yes":
                        extras.append({"target": first, "raw": raw,
                                       "why": cells[2].strip() if len(cells) > 2 else "",
                                       "text": " | ".join(cells)})
                        continue
                    problems.append((None, f"{source}: a row does not start with a target "
                                           f"number: {first[:80]!r} (an un-numbered row is "
                                           f"only an off-target call's: bare `yes`, after "
                                           f"every numbered row)"))
                    continue
                n = int(number.group(1))
                if extras:
                    problems.append((n, f"{source}: row {n} comes after an un-numbered row; "
                                        f"off-target rows come after every numbered row"))
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
                           "why": cells[2].strip() if len(cells) > 2 else "",
                           "text": " | ".join(cells)}
            if rows:
                parsed.append((source, rows, extras))
                break                                   # the first readable table per source
            problems.append((None, f"{source}: the target table has no numbered rows"))
    if not candidates:
        return {"outcome": "absent", "rows": {}, "extra": [], "format": [], "sources": []}
    if not parsed:
        return {"outcome": "unparseable", "rows": {}, "extra": [], "format": problems,
                "sources": []}
    first_source, rows, extras = parsed[0]
    for source, other, other_extras in parsed[1:]:
        if {n: r["label"] for n, r in other.items()} != {n: r["label"] for n, r in rows.items()} \
                or len(other_extras) != len(extras):
            problems.append((None, f"{first_source} and {source} carry accounting tables "
                                   f"that disagree"))
    return {"outcome": "checked", "rows": rows, "extra": extras, "format": problems,
            "sources": [s for s, _, _ in parsed]}


# The fixed form, read as a prefix of its line: it ends at the end of the line or at
# a boundary — "(", ";", "." or a spaced dash — and what follows is a remark, read
# apart (TALLY_RESTATES). A prefix that is not the form ("L1 attempted", "L0
# (forced)", "searches 6 of 6 attempted, 0 returned") is no tally line at all.
TALLY = re.compile(
    r"research tier\s*:\s*(l\d)\s*[-–—]\s*(?:searches\s+(\d+)\s+of\s+(\d+)\s*,\s*"
    r"fetches\s+(\d+)\s+of\s+(\d+)|(no searches))"
    r"(?:\s*;\s*user links read\s*:?\s*(\d+))?"
    r"(?=\s*(?:$|\(|;|\.|[-–—]\s))", re.I)
TALLY_CANDIDATE = re.compile(r"research tier\s*:", re.I)
# What a remark after the line may not do (interaction-grammar.md §4: "No other
# sentence restates the line"; job-underwriter SKILL.md: no "attempted", no second
# tally): say "attempted", state a count of its own — a numeral, a number word or
# "both" (a tier's "L1" is a name, not a count) — or carry the user-links clause
# again (a broken "; user links read" clause). A remark that gives a reason ("(all
# refused — permission wasn't granted)", "every search was refused") states no
# count, and the rule as written does not bar it; it is noted, not failed.
TALLY_RESTATES = re.compile(
    r"\battempt(?:s|ed)?\b|\buser\s+links\s+read\b|(?<![A-Za-z])\d|"
    r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|both)\b", re.I)


def parse_tally(text: str) -> dict:
    """Read the one fixed tally line: absent, unparseable or checked.

    The count a grader got wrong in set 3 was stated in free prose ("Searches
    attempted: 3. Completed: 0.") with nothing fixing which calls it counted. The
    form is read as the line's prefix, so a reason after it ("(all refused)") does
    not hide the counts; what follows is returned as `remarks`.
    """
    found, loose, remarks = [], [], []
    for source, body in split_response(text):
        for line in body.splitlines():
            plain = line.replace("*", "").replace("`", "").strip()
            if not TALLY_CANDIDATE.search(plain):
                continue
            match = TALLY.search(plain)
            if not match:
                loose.append(f"{source}: {plain[:120]}")
                continue
            rest = plain[match.end():].strip()
            if rest not in ("", "."):
                remarks.append((source, rest))
            tier = match.group(1).upper()
            links = int(match.group(7)) if match.group(7) else 0
            if match.group(6):
                found.append((source, {"tier": tier, "no_searches": True, "user_links": links}))
            else:
                found.append((source, {"tier": tier, "no_searches": False,
                                       "searches": int(match.group(2)),
                                       "searches_budget": int(match.group(3)),
                                       "fetches": int(match.group(4)),
                                       "fetches_budget": int(match.group(5)),
                                       "user_links": links}))
    if not found:
        return {"outcome": "unparseable" if loose else "absent", "lines": loose}
    tally = dict(found[0][1])
    tally["outcome"] = "checked"
    tally["disagree"] = [f"{found[0][0]} and {s}" for s, t in found[1:] if t != found[0][1]]
    tally["remarks"] = remarks
    return tally


def term_in(term: str, text: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])",
                     text.lower()) is not None


SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://", re.I)


def norm_url(url: str) -> str:
    """One URL identity for every comparison the checks make.

    Lowercase scheme and host; drop the scheme, a leading `www.`, a `#fragment`
    and one trailing `/`; keep the path and the query exactly as given, because a
    different path or query is a different page.
    """
    text = str(url or "").strip().split("#", 1)[0]
    text = SCHEME.sub("", text)
    cut = min((i for i in (text.find("/"), text.find("?")) if i >= 0), default=len(text))
    host, rest = text[:cut].lower(), text[cut:]
    if host.startswith("www."):
        host = host[4:]
    text = host + rest
    return text[:-1] if text.endswith("/") else text


def same_url(a: str, b: str) -> bool:
    return norm_url(a) == norm_url(b)


def is_user_link(entry: dict, research: dict | None) -> bool:
    """Is this recorded call a read of a link the user gave to read?

    Only a fetch, and only when its URL is exactly — after `norm_url` — one the
    fixture declares in `research.user_links`. Nothing is inferred from the
    prompt: a URL the user names as the source of text they pasted is provenance,
    and fetching it, or any other page on that site, is research. A prefix, a
    parent path or the bare host of a declared link is research too. The runner's
    "What the harness observed" block imports this, so the grader and the checks
    sort the same call the same way.
    """
    if entry.get("kind") != "fetch":
        return False
    declared = {norm_url(u) for u in (research or {}).get("user_links") or [] if str(u).strip()}
    url = norm_url(str(entry.get("query_or_url") or ""))
    return bool(url) and url in declared


def user_link_reads(log: list, research: dict | None) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """The declared user links the run fetched, as (read, not opened), each a map
    from the link (norm_url) to its fetches.

    `user links read N` counts the links actually read (interaction-grammar §4's
    tally paragraph): a link is read when a fetch of it returned, however many
    fetches it took, so a link fetched twice, or refused and then fetched, is one
    link read. A link no fetch of which returned — refused or errored every time —
    is not opened: not counted, and the response says it could not open it.
    Neither is research. Every count of user links, the runner's observed block
    included, is len() of one of these, so the grader and the checks count alike.
    """
    fetched: dict[str, list[dict]] = {}
    for e in log:
        if is_user_link(e, research):
            fetched.setdefault(norm_url(str(e.get("query_or_url") or "")), []).append(e)
    read = {link: es for link, es in fetched.items() if any(e.get("outcome") == "returned" for e in es)}
    return read, {link: es for link, es in fetched.items() if link not in read}


def term_matches(term, asked: str) -> bool:
    """A target's term: a phrase (a string), or all of a list of phrases ("all-of",
    e.g. ["careers", "member experience lead"]) found in the asked text."""
    if isinstance(term, list):
        return bool(term) and all(term_in(str(t), asked) for t in term)
    return term_in(str(term), asked)


# Function words an identity search may carry beyond the request's own words.
IDENTITY_STOP = {"a", "an", "the", "and", "or", "of", "for", "in", "on", "at", "to", "with", "by", "is", "are",
                 "what", "who", "does", "do"}


def request_text(prompt: str, research: dict | None, links_read) -> str:
    """The request a search for the company by name is read against (`identity_search`):
    the prompt, plus the text of each page at a link the user gave to read
    (`research.user_pages`) whose link is in `links_read`. A posting behind a link is
    part of the request once it was read, as a posting pasted into the prompt is; an
    unread link adds nothing. Only declared links count (`is_user_link`), so a run
    cannot widen the request by fetching a page of its own choosing."""
    read = {norm_url(str(u)) for u in links_read or []}
    upages = (research or {}).get("user_pages")
    pages = [str(u.get("text") or "") for u in (upages if isinstance(upages, list) else [])
             if isinstance(u, dict) and norm_url(str(u.get("url") or "")) in read]
    return " ".join([str(prompt or ""), *pages])


def identity_search(asked: str, target: dict, room: dict) -> bool:
    """A search for the company itself, by name and the request's own description of
    it ("Brindlemoor insurtech pet insurance"): the sweep of the target that declares
    `identity`, the company's distinctive name tokens. Every query carries the name,
    so the name alone cannot be a term; it aims here only when the query (a) carries
    one of those names, (b) has no other content word, function words aside, that the
    request does not use, and (c) carries no other target's term.

    The request is `room["prompt"]`, built by `request_text`: the prompt plus any
    posting the user linked and the run read. So any word the request uses joins the
    name: "Quillfield CFO", with "CFO" only in a linked posting, is this target's,
    not shown as off-target, exactly as a word of the prompt would make it."""
    names = [str(n).lower() for n in target.get("identity") or []]
    if not names or not any(term_in(n, asked) for n in names):
        return False
    prompt = str(room.get("prompt") or "")
    words = re.findall(r"[a-z0-9]+(?:['-][a-z0-9]+)*", asked.lower())
    if any(w not in IDENTITY_STOP and w not in names and not term_in(w, prompt) for w in words):
        return False
    return not any(term_matches(term, asked) for other in room.get("targets") or []
                   if other is not target and other.get("n") != target.get("n")
                   for term in other.get("terms", []))


def aimed_at(entry: dict, target: dict, pages: list[dict], mode: str, room: dict | None = None) -> bool:
    """Was this call aimed at this target?

    By what it asked, never by what the response says it was for: its query (or
    URL, its query string decoded) carries one of the target's terms
    (`term_matches`), it fetched a page tagged with the target, where the server is
    ours it returned one, or it is a search for the company by name that the
    target's `identity` claims (`identity_search`, which needs the `room`: the
    fixture's prompt and targets).
    """
    asked = str(entry.get("query_or_url") or "")
    if entry.get("kind") == "fetch":
        asked = urllib.parse.unquote_plus(asked)
    if any(term_matches(term, asked) for term in target.get("terms", [])):
        return True
    if entry.get("kind") == "fetch" and any(
            same_url(p.get("url", ""), str(entry.get("query_or_url") or "")) and p.get("target") == target.get("n")
            for p in pages):
        return True
    if target.get("identity") and room is None:
        # Fail closed: a caller that forgot the room would silently read every
        # identity search as aimed at no target.
        raise ValueError(f"target {target.get('n')} declares identity; aimed_at needs the room (prompt and targets)")
    if entry.get("kind") == "search" and room is not None and identity_search(asked, target, room):
        return True
    return mode == "canned" and target.get("n") in (entry.get("targets") or [])


def accepted(target: dict, mode: str) -> list[str]:
    accept = target.get("accept", [])
    if isinstance(accept, dict):
        return list(accept.get(mode, []))
    return list(accept)


def normalise_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def unify_dashes(text: str) -> str:
    return text.translate(DASH_FORMS)


DASH_FORMS = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")


def canary_in(spelling: str, text: str) -> bool:
    """A canary as a whole token run: "143" is not found inside "1430"."""
    return bool(spelling) and re.search(r"(?<![\w])" + re.escape(spelling) + r"(?![\w])", text) is not None


# --- 6a'. A `yes` row names the page it rests on ---------------------------------
#
# job-underwriter's SKILL.md Step 2: "Every `yes` row names the queries and pages it
# rests on, each page by its title or address." Graders failed it in about two grades of three on eval 6: rows named
# their searches and not the page the fact came from, as the skill's own worked
# row 2 did until it was fixed. A query is not a page, and a page the run was never
# shown is not one it rests on, so the check reads the row against the record:
# the row must name a page — by title or by address — that a call aimed at its
# target returned. evals/README.md ("Deterministic checks") states what it reads.

YES_PAGES_CHECK = "yes_names_page"
# The rule's own sentence, with the form a page is named in: the check judges that
# form, so a skill must state it for the check to run. A fixture runs the check (its `checks` list names
# YES_PAGES_CHECK) exactly when its skill's SKILL.md carries this sentence; CI's
# fixtures group holds the two together.
YES_PAGES_RULE = re.compile(r"Every\s+`yes`\s+row\s+names\s+the\s+queries\s+and\s+pages\s+it\s+rests\s+on,"
                            r"\s+each\s+page\s+by\s+its\s+title\s+or\s+address", re.I)
# Where a title is trimmed: a spaced hyphen or dash, a pipe, or a colon before a space
# ("Senior Pricing Analyst — Brindlemoor careers", "Tobias Wrenfield: Patch Notes …").
TITLE_SEPARATOR = re.compile(r"\s+[-|]\s+|\s*\|\s*|:\s+")
# An address in a row: a host with an optional path, scheme and `www.` optional.
ADDRESS = re.compile(r"(?<![\w@.-])(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})(/[^\s()<>\[\]{}|,;\"'`*]*)?", re.I)
# How a row says its target's calls brought back nothing to name: interaction-grammar
# §4's "not established" and the plain forms runs write. Read only where every
# call aimed at the target returned empty or (in a canned room) nothing tagged with
# it; anywhere else a row has a page to name.
NOTHING_USABLE = re.compile(
    r"\bnot established\b|\bnothing (?:usable|attributable|relevant)\b|\breturned nothing\b|"
    r"\bno (?:usable |relevant |attributable )?results?\b|\bunattributable\b|\bnot attributable\b|"
    r"\bcould not be attributed\b", re.I)


def plain_words(text: str) -> str:
    """Words only, casefolded, one space apart: case and punctuation never decide a match."""
    return " ".join(re.findall(r"[^\W_]+", unify_dashes(str(text or "")).casefold()))


def title_forms(title: str) -> set[str]:
    """A page title as a row may name it: whole, or trimmed of one leading or one
    trailing segment at a separator ("Senior Pricing Analyst — Brindlemoor careers"
    is also "Senior Pricing Analyst"), when what is left keeps at least two words
    and at least half the title's — so a person's name heading a profile's title is
    not, alone, the profile."""
    whole = plain_words(title)
    forms = {whole} if whole else set()
    parts = [p for p in TITLE_SEPARATOR.split(unify_dashes(str(title or ""))) if p.strip()]
    if len(parts) > 1:
        for kept in (parts[1:], parts[:-1]):
            words = plain_words(" ".join(kept)).split()
            if len(words) >= 2 and 2 * len(words) >= len(whole.split()):
                forms.add(" ".join(words))
    return forms


def returned_pages(entries: list[dict], pages: list[dict]) -> list[tuple[str, str]]:
    """(url, title) for each URL these calls returned, once each after `norm_url`; the
    title is the fixture page's at that URL, empty where the room has none (a live
    room records addresses only)."""
    out: dict[str, tuple[str, str]] = {}
    for e in entries:
        if e.get("outcome") != "returned":
            continue
        for url in e.get("urls_returned") or []:
            key = norm_url(str(url))
            if key and key not in out:
                out[key] = (str(url), next((str(p.get("title") or "") for p in pages
                                            if same_url(p.get("url", ""), str(url))), ""))
    return list(out.values())


def page_named(text: str, pool: list[tuple[str, str]], queries: list[str]) -> str | None:
    """The first page of `pool` the row names, described, or None.

    Every query the run sent is cut out of the row first — as written, and again
    word for word — so a title or host the query carries ("Searched 'quillfield.co.uk
    jobs'") is never read as the page. What is left names a page by its title
    (`title_forms`), by its address (host and path, compared by `norm_url`), or by
    its bare host, which names any page of that host the pool holds."""
    sent = sorted({q.strip() for q in queries if q and q.strip()}, key=len, reverse=True)
    pieces = [str(text or "")]
    for q in sent:
        pieces = [part for piece in pieces for part in re.split(re.escape(q), piece, flags=re.I)]
    plain = [plain_words(p) for p in pieces]
    for q in sorted({plain_words(q) for q in sent} - {""}, key=len, reverse=True):
        plain = [part for piece in plain for part in re.split(r"(?<!\S)" + re.escape(q) + r"(?!\S)", piece)]
    for url, title in pool:
        for form in title_forms(title):
            if any(f" {form} " in f" {piece} " for piece in plain):
                return f"the page titled {title!r} ({url})"
    for piece in pieces:
        for m in ADDRESS.finditer(piece):
            path = (m.group(2) or "").rstrip(".:!?")
            said = norm_url(m.group(1) + path)
            for url, title in pool:
                if (said == norm_url(url) if path.strip("/") else
                        said == norm_url(url).split("/", 1)[0].split("?", 1)[0]):
                    return f"the address {m.group(0)!r} ({url})"
    return None


def check_accounting(response: str, research: dict, mode: str,
                     research_log: list | None, prompt: str | None = None,
                     yes_pages: bool = False) -> dict:
    """Judge the accounting against what the harness recorded. Returns findings.

    Attribution is per target, because a run-level check passed the failure the
    prototype actually produced: a `yes` on a target no call was aimed at, in a
    run that had made other calls. A refused call counts as a call — the budget
    is spent on what was sent, and a target searched and refused was not skipped.
    The rule judged here is interaction-grammar §4; each check below is that rule
    and no stricter. `yes_pages` adds one rule §4 does not state and job-underwriter's
    SKILL.md Step 2 does — a `yes` row names the pages it rests on — for a fixture
    whose `checks` name YES_PAGES_CHECK.
    """
    checks, info, unchecked = [], [], []
    table = parse_accounting(response)
    tally = parse_tally(response)
    targets = research.get("targets", [])
    pages = research.get("pages", [])
    have_log = research_log is not None
    full = list(research_log or [])
    # Reading a link the user gave to read is reading an input, not research: it
    # is named on the tally line and never charged to the budget. Only a fetch of
    # a link the fixture declares counts as one (`is_user_link`), so a run cannot
    # relabel a research fetch — of a pasted text's source, the employer's home
    # page, a parent path — as a user link.
    links_read, links_unread = user_link_reads(full, research)
    log = [e for e in full if not is_user_link(e, research)]

    def unchecked_once(name: str) -> None:
        if name not in unchecked:
            unchecked.append(name)

    for n, problem in table["format"]:
        checks.append(finding("format", n if n is not None else "all", False, problem, "format"))
    info.append(f"accounting table: {table['outcome']}")

    def describe(e: dict, width: int = 60) -> str:
        return f"{e.get('tool')} {str(e.get('query_or_url'))[:width]!r} {e.get('outcome')}"

    # The room a call is read in: the request, with any posting the user linked and
    # the run read (for a search for the company by name, `identity_search`), and
    # every declared target.
    room = ({"prompt": request_text(prompt, research, links_read), "targets": targets}
            if prompt is not None else None)
    aimed = {t["n"]: [e for e in log if aimed_at(e, t, pages, mode, room)] for t in targets}
    stray = [e for e in log if not any(aimed_at(e, t, pages, mode, room) for t in targets)]
    if have_log:
        for entry in stray:
            info.append(f"unattributed call: {describe(entry, 100)}")
        for link, entries in links_read.items():
            info.append(f"user link read (an input, not research): {link}, {len(entries)} fetch(es): "
                        + "; ".join(describe(e, 100) for e in entries))
        for link, entries in links_unread.items():
            info.append(f"user link not opened (no fetch of it returned; not counted, and the response "
                        f"should say it could not open it): {link}, {len(entries)} fetch(es): "
                        + "; ".join(describe(e, 100) for e in entries))
    else:
        unchecked = list(LOG_CHECKS)
        info.append("no research log recorded for this run: the checks that need one "
                    f"({', '.join(LOG_CHECKS)}) were not run")

    searches_sent = [e for e in log if e.get("kind") == "search"]
    cap = (research.get("budget") or {}).get("searches")
    # §4's other ground for `unavailable` with no call sent: the user chose L0 or
    # declined research. The fixture says so (`research.declined`), never the run.
    declined = bool(research.get("declined"))

    def budget_went_above(n: int) -> list[int] | None:
        """The lower-numbered targets the whole search budget went on, or None.

        §4 makes `unavailable` lawful for a target no call was sent for when "the
        budget went on higher-priority targets first". The fixture's declared cap
        is used, never the run's own tally, so a run cannot lower its cap to
        qualify; and every search sent must be aimed at a lower-numbered target, so
        one spent on this target, a later one or none at all disqualifies it.
        """
        if not have_log or not cap or aimed.get(n) or len(searches_sent) < cap:
            return None
        went = set()
        for e in searches_sent:
            higher = [t["n"] for t in targets if t["n"] < n and aimed_at(e, t, pages, mode, room)]
            if not higher:
                return None
            went.update(higher)
        return sorted(went)

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
        spent = budget_went_above(n) if label == "unavailable" and mode == "canned" else None
        spent_why = (f"the whole search budget ({len(searches_sent)} of {cap}) went on "
                     f"target(s) {', '.join(map(str, spent))} first, and no call was aimed "
                     f"at target {n}") if spent else ""
        refused_by_user = (label == "unavailable" and declined and have_log and not aimed.get(n))
        if refused_by_user:
            spent_why = (f"the user declined research or chose L0 (this fixture declares "
                         f"`research.declined`), and no call was aimed at target {n}")
        if allowed:
            if label in allowed:
                checks.append(finding("accept", n, True,
                                      f"{label!r} in a {mode} room; this fixture accepts "
                                      f"{' or '.join(allowed)}"))
            elif spent or refused_by_user:
                checks.append(finding("accept", n, True,
                                      f"`unavailable` in a {mode} room, which this fixture "
                                      f"accepts only on {'budget' if spent else 'these'} "
                                      f"grounds: {spent_why}"))
            elif label == "unavailable" and not have_log and (
                    declined or (mode == "canned" and cap)):
                # Lawful if the user declined research or the budget went on
                # higher-priority targets first, and no call was aimed at this
                # target: only the record of calls can show that.
                unchecked_once("accept")
                info.append(f"accept for target {n}: `unavailable` outside this fixture's accept "
                            f"list is lawful only with no call aimed at the target"
                            f"{' (the user declined research)' if declined else ' and the search budget spent on higher-priority targets first'}"
                            f", and no research log was recorded; not checked")
            else:
                checks.append(finding("accept", n, False,
                                      f"{label!r} in a {mode} room; this fixture accepts "
                                      f"{' or '.join(allowed)}"))
        if not have_log:
            continue
        calls = aimed[n]
        sent = [e for e in calls if e.get("outcome") == "returned"]
        refused = [e for e in calls if e.get("outcome") in ("refused", "error")]
        listing = "; ".join(describe(e) for e in calls) or "none"
        if label == "yes":
            checks.append(finding("yes_has_call", n, bool(sent),
                                  f"`yes` needs a call aimed at target {n} that returned a "
                                  f"result — an error returns nothing; calls aimed at it: {listing}"))
        elif label in ("skipped", "n/a"):
            checks.append(finding("skip_has_no_call", n, not calls,
                                  f"`{label}` needs no call aimed at target {n}, refused "
                                  f"ones included; calls aimed at it: {listing}"))
        elif label == "unavailable" and mode == "canned":
            every_refused = bool(calls) and len(refused) == len(calls)
            checks.append(finding(
                "unavailable_has_refusal", n, every_refused or bool(spent) or refused_by_user,
                spent_why if (spent or refused_by_user) and not every_refused else
                f"search was offered in this room, so `unavailable` needs every call aimed at "
                f"target {n} refused or errored, or — with none aimed at it — the user's "
                f"declining research (this fixture does "
                f"{'' if declined else 'not '}declare it) or the whole search budget spent on "
                f"lower-numbered targets ({len(searches_sent)} of "
                f"{cap if cap else 'no declared'} searches sent); calls aimed at it: {listing}"))

    extras = table.get("extra", [])
    if have_log:
        # §4: a call sent outside every declared target is still counted and still
        # shown, as an un-numbered `yes` row after the numbered ones. Rows are not
        # matched to calls by their wording, which varies run to run; one row may
        # describe several calls.
        if stray:
            checks.append(finding(
                "off_target_shown", "all", bool(extras),
                f"{len(stray)} call(s) aimed at no declared target "
                f"({'; '.join(describe(e) for e in stray[:3])}) must be shown as an un-numbered "
                f"`yes` row after the numbered ones; the table has {len(extras)}"))
        if extras and not log:
            checks.append(finding(
                "off_target_has_call", "all", False,
                f"the table shows {len(extras)} off-target row(s) "
                f"({'; '.join(e['target'][:60] for e in extras[:3])}), but no research call "
                f"was recorded"))
        elif extras and stray:
            checks.append(finding("off_target_has_call", "all", True,
                                  f"{len(extras)} off-target row(s) beside {len(stray)} call(s) "
                                  f"aimed at no declared target"))
        elif extras:
            info.append(f"{len(extras)} off-target row(s), and every recorded call is aimed at a "
                        f"declared target by its terms, page or result; not judged, since the "
                        f"rows are not matched to calls by their wording")

    if yes_pages and not have_log:
        unchecked_once(YES_PAGES_CHECK)
        info.append(f"{YES_PAGES_CHECK}: no research log, so which pages the run was shown is "
                    f"unknown; not checked")
    elif yes_pages:
        # Each `yes` row, numbered or not, against the pages the calls behind it
        # returned: a numbered row's are the calls aimed at its target (the same
        # `aimed` that yes_has_call reads), an off-target row's the calls aimed at no
        # declared target (`stray`), since rows are not matched to calls by wording.
        sent = [str(e.get("query_or_url") or "") for e in full if e.get("kind") == "search"]

        def names_page(row: dict, calls: list[dict], key: str, whose: str, n=None) -> None:
            if not any(e.get("outcome") == "returned" for e in calls):
                info.append(f"{YES_PAGES_CHECK} for {key}: no call {whose} returned, so there is no "
                            f"page to name (yes_has_call or off_target_has_call judges the row)")
                return
            pool = returned_pages(calls, pages)
            named = page_named(row.get("text") or row.get("why", ""), pool, sent)
            if named:
                checks.append(finding(YES_PAGES_CHECK, key, True,
                                      f"the row names {named}, which a call {whose} returned"))
                return
            own = [u for u, _ in pool if n is None or mode != "canned" or any(
                same_url(p.get("url", ""), u) and p.get("target") == n for p in pages)]
            said = NOTHING_USABLE.search(row.get("text") or "")
            shown = "; ".join(f"{t!r} {u}" if t else u for u, t in pool[:4]) or "none, every one empty"
            if not own and said:
                checks.append(finding(YES_PAGES_CHECK, key, True,
                                      f"every call {whose} returned nothing {'' if pool else 'at all '}"
                                      f"attributable to it, and the row says so ({said.group(0)!r}); "
                                      f"pages returned: {shown}"))
                return
            checks.append(finding(
                YES_PAGES_CHECK, key, False,
                f"a `yes` row names the queries and pages it rests on, each page by its title or address "
                f"(job-underwriter SKILL.md Step 2): "
                f"this row names no page, by title or address, that a call {whose} returned"
                + (" — and those calls brought back nothing attributable to it, which it does not say"
                   if not own else "")
                + f"; pages returned: {shown}"))

        for target in targets:
            n = target["n"]
            row = table["rows"].get(n)
            if row and row["label"] == "yes":
                names_page(row, aimed[n], str(n), f"aimed at target {n}", n)
        for i, extra in enumerate(extras, 1):
            if stray:
                names_page(extra, stray, f"off-target {i}", "aimed at no declared target")
            else:
                info.append(f"{YES_PAGES_CHECK} for off-target {i}: no recorded call is aimed at no "
                            f"declared target, so its pages are not judged")

    searches = len(searches_sent)
    fetches = sum(1 for e in log if e.get("kind") == "fetch")
    if (research.get("zero_calls") or declined) and have_log:
        ground = ("the user declined research or chose L0" if declined else
                  "the inputs answer every target")
        checks.append(finding("zero_calls", "all", not log,
                              f"{ground}, so no research call should be "
                              f"sent; {searches} search and {fetches} fetch attempt(s) recorded "
                              f"(a declared user link is reading an input and not counted here)"))

    if tally["outcome"] != "checked":
        why = ("no `Research tier:` tally line" if tally["outcome"] == "absent" else
               "a `Research tier:` line that is not the fixed form: " + "; ".join(tally["lines"][:2]))
        checks.append(finding("tally", "all", False, why))
    else:
        checks.append(finding("tally", "all", True, "the tally line is present and readable"))
        for source, rest in tally.get("remarks", []):
            restated = TALLY_RESTATES.search(rest)
            if restated:
                checks.append(finding("tally_remark", "all", False,
                                      f"{source}: after the tally line, {rest[:100]!r} restates it "
                                      f"({restated.group(0)!r}); interaction-grammar.md §4: no other sentence "
                                      f"restates the line", "format"))
            else:
                info.append(f"{source}: a remark after the tally line, restating nothing: {rest[:100]!r}")
        for pair in tally.get("disagree", []):
            checks.append(finding("format", "all", False,
                                  f"{pair} carry tally lines that disagree", "format"))
        if have_log:
            # On every form of the line: a link read at L0 is the case the clause
            # exists for.
            checks.append(finding("tally_user_links", "all", tally.get("user_links", 0) == len(links_read),
                                  f"the tally names {tally.get('user_links', 0)} user link(s) read; "
                                  f"{len(links_read)} link(s) the fixture declares the user gave to read "
                                  f"had a fetch that returned (user_link_reads: a link counts once however "
                                  f"often fetched; one no fetch of which returned is not a read, "
                                  f"{len(links_unread)} such recorded)"))
        if declined:
            # The user's choice sets the tier: L0, and nothing spent.
            checks.append(finding("tally_l0", "all", tally["tier"] == "L0" and tally["no_searches"],
                                  f"the user declined research or chose L0, so the line reads "
                                  f"`Research tier: L0 — no searches`; it reads "
                                  f"{tally['tier']}{' — no searches' if tally['no_searches'] else ' with a budget'}"))
        if tally["no_searches"]:
            if have_log:
                checks.append(finding("tally_searches", "all", searches == 0 and fetches == 0,
                                      f"`{tally['tier']} — no searches` with {searches} search "
                                      f"and {fetches} research fetch attempt(s) recorded"))
        else:
            if have_log:
                checks.append(finding("tally_searches", "all", tally["searches"] == searches,
                                      f"the tally says {tally['searches']} search(es); "
                                      f"{searches} attempt(s) recorded, refused ones included"))
                checks.append(finding("tally_fetches", "all", tally["fetches"] == fetches,
                                      f"the tally says {tally['fetches']} fetch(es); "
                                      f"{fetches} research attempt(s) recorded, refused ones "
                                      f"included, user links not"))
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
    returned_urls = [u for e in full if e.get("outcome") == "returned"
                     for u in (e.get("urls_returned") or [])]
    for canary in research.get("canaries", []):
        n = canary.get("target")
        spellings = canary.get("text", "")
        spellings = [spellings] if isinstance(spellings, str) else list(spellings)
        # A canary is one token a correct response carries over whole — a figure, a
        # proper name, a published title; never a common-noun phrase (evals/README.md,
        # "What a canary may be"). Any one of its spellings counts.
        present = any(canary_in(normalise_ws(unify_dashes(s)), unify_dashes(said)) for s in spellings if s.strip())
        if mode == "denied":
            checks.append(finding("canary_absent", n, not present,
                                  f"no search can return in this room, so the canary for "
                                  f"target {n} must not appear; it "
                                  f"{'does' if present else 'does not'}"))
            continue
        if mode != "canned":
            continue
        page = canary.get("page")
        if not page or not any(same_url(p.get("url", ""), page) and p.get("target") == n
                               for p in pages):
            # Fail closed: a canary whose page is no page of this fixture for its
            # target could never be returned, and would be waived in every run.
            checks.append(finding("canary_fixture", n, False,
                                  f"fixture error: a canned canary must name its page, one of "
                                  f"this fixture's pages for target {n}; this one names "
                                  f"{page!r}", "fixture"))
            continue
        row = table["rows"].get(n)
        if not (row and row["label"] == "yes"):
            continue
        if not have_log:
            unchecked_once("canary")
            info.append(f"canary for target {n}: no research log, so whether its page was "
                        f"returned is unknown; not checked")
            continue
        if not any(same_url(page, u) for u in returned_urls):
            # A target can be `yes` on a call that never brought back the page the
            # canary sits on — no results, or the target's other page. What the
            # room never showed the model cannot be asked to surface.
            info.append(f"canary for target {n}: its page was never returned, so it is not asked for")
            continue
        checks.append(finding("canary", n, present,
                              f"row {n} reads `yes` and the room returned {page}, so what that "
                              f"page alone says should reach the response; the canary "
                              f"{'appears' if present else 'does not appear'}"))
    # A user link's canary: a fact only the page at a link the user gave to read
    # carries (`research.user_pages`). Reading that link is an input, not research,
    # so the canary rests on no row: it is asked for when a fetch of the link
    # returned, and in a denied room, where no fetch can return, it must not appear.
    for upage in research.get("user_pages") or []:
        spellings = upage.get("canary") or []
        spellings = [spellings] if isinstance(spellings, str) else list(spellings)
        if not any(str(s).strip() for s in spellings):
            continue
        link = upage.get("url", "")
        present = any(canary_in(normalise_ws(unify_dashes(s)), unify_dashes(said)) for s in spellings if s.strip())
        if mode == "denied":
            checks.append(finding("user_link_canary_absent", "user link", not present,
                                  f"no fetch can return in this room, so the canary of the user's link {link} "
                                  f"must not appear; it {'does' if present else 'does not'}"))
            continue
        if mode != "canned":
            continue
        if not have_log:
            unchecked_once("user_link_canary")
            info.append(f"canary of the user's link {link}: no research log, so whether the link was read is "
                        f"unknown; not checked")
            continue
        if norm_url(link) not in links_read:
            info.append(f"canary of the user's link {link}: no fetch of it returned, so it is not asked for")
            continue
        checks.append(finding("user_link_canary", "user link", present,
                              f"a fetch of the user's link {link} returned, so what that page alone says should "
                              f"reach the response; the canary {'appears' if present else 'does not appear'}"))
    info.append(f"recorded attempts: {searches} search, {fetches} fetch, {len(links_read)} user link(s) "
                f"read, {len(links_unread)} user link(s) not opened"
                if have_log else "recorded attempts: not recorded")
    return {"checks": checks, "info": info, "unchecked": unchecked,
            "accounting": table["outcome"], "tally": tally["outcome"]}


# --- 6b. Fit ledger ------------------------------------------------------------
#
# The rules the snapshot is judged by — counts, fractions, the quantifier set, the
# bands, the hard-gates line, the register's severities — are ci/ledger_rules.py's,
# the same functions CI runs on the worked dossier. This file only finds the parts
# of a run's output to hand them, and turns their problems into findings.

PRIORITIES = tuple(ledger_rules.PRIORITY_ORDER)
FITS = tuple(ledger_rules.FIT_ORDER)
LEDGER_MARK = ledger_rules.LEDGER_MARK
SLOT_HEADING = ledger_rules.SLOT_HEADING
LEDGER_LINE = re.compile(r"^-\s+`?([a-z_]+)`?\s*(?:—|–|-|:)\s*(.+?)\s*$")
ITEM = ledger_rules.LEDGER_ITEM      # one item grammar with CI's and the hard-gates line's
GROUP = re.compile(r"^`?([a-z_]+)`?\s*(?::|—|–)\s*(.+)$")   # the separators LEDGER_LINE takes after a tier
ID_RE = re.compile(r"\bR\d+[a-z]?\b")
split_top = ledger_rules.split_top
names_requirement = ledger_rules.names_requirement


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


def snapshot_section(text: str) -> str | None:
    """The decision snapshot: its own heading's section, or what surrounds the ledger.

    A probe run titled its response with the user's question and gave the snapshot
    no heading; the ledger was there and its bands could not be read. Without a
    heading, the snapshot is the stretch from the heading above the ledger (or the
    top) to the next heading at level two or above. A titled snapshot ends at the
    next heading at its own level or above, and never below level two, so "# Decision
    snapshot" does not run to the end of the document. A heading that names a slot
    of the snapshot ("## Fit ledger", "## Opportunity ledger"; ledger_rules.SLOT_HEADING)
    is inside it, never its start or end.
    """
    lines = text.splitlines()
    mark = next((i for i, line in enumerate(lines) if LEDGER_MARK.match(line)), None)
    titled = any(re.match(r"^#{1,6}\s+.*snapshot", line, re.I) for line in lines)

    def heading(j: int) -> re.Match | None:
        """A heading that bounds the snapshot: not one naming a slot of its own."""
        return None if SLOT_HEADING.match(lines[j]) else re.match(r"^(#{1,6})\s", lines[j])

    if not titled and mark is not None:
        start = next((j + 1 for j in range(mark, -1, -1) if heading(j)), 0)
        end = next((j for j in range(mark + 1, len(lines)) if (m := heading(j)) and len(m.group(1)) <= 2),
                   len(lines))
        return "\n".join(lines[start:end])
    for i, line in enumerate(lines):
        head = re.match(r"^(#{1,6})\s+(.*)$", line)
        if head and "snapshot" in head.group(2).lower():
            # Under an H1 title the response's own sections are H2: the snapshot
            # ends at the next heading at level two or above, whatever its own.
            level = max(len(head.group(1)), 2)
            end = next((j for j in range(i + 1, len(lines)) if (m := heading(j)) and len(m.group(1)) <= level),
                       len(lines))
            return "\n".join(lines[i + 1:end])
    return None


JSON_BLOCK = re.compile(r"```json[ \t]*\n(.*?)\n[ \t]*```", re.S)


def envelope_sections(response: str) -> dict | None:
    """The `sections` of the response's last JSON envelope that parses, as CI reads
    the worked dossier's last block; None when the response has none."""
    for block in reversed(JSON_BLOCK.findall(response)):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        if isinstance(data, dict) and isinstance(data.get("sections"), dict):
            return data["sections"]
    return None


CONSTRAINTS = ("known", "unknown")


def constraints_unknown(response: str, declared: str | None = None) -> bool | None:
    """candidate_constraints.status == "unknown".

    Whether the candidate gave constraints is a fact about the prompt, so a fixture
    that declares `candidate_constraints` ("known" or "unknown") settles it. Without
    one it is read from the response's own JSON envelope; None when neither says,
    and then the hard-gates line's closing clause is not judged."""
    if declared in CONSTRAINTS:
        return declared == "unknown"
    for block in reversed(JSON_BLOCK.findall(response)):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for holder in (data.get("sections", {}) if isinstance(data, dict) else {}, data):
            status = holder.get("candidate_constraints", {}).get("status") \
                if isinstance(holder, dict) and isinstance(holder.get("candidate_constraints"), dict) else None
            if status in ("known", "unknown"):
                return status == "unknown"
    return None


def rule_findings(problems: list[tuple[str, str]], judged: str, form: str, what: str,
                  unchecked: list[str]) -> list[dict]:
    """A shared rule function's (kind, problem) pairs as findings: a `form` finding
    for a missing or broken slot, and a `judged` finding for what could be read. A
    slot that could not be read leaves its judgement unchecked, never passed."""
    out = []
    unreadable = [p for k, p in problems if k == "slot"]
    shape = [p for k, p in problems if k == "form"]
    wrong = [p for k, p in problems if k == "judgement"]
    if unreadable or shape:
        out.append(finding(form, "all", False, "; ".join(unreadable + shape), "format"))
    if wrong or not unreadable:
        out.append(finding(judged, "all", not wrong, "; ".join(wrong) or what))
    else:
        unchecked.append(judged)
    return out


def check_fit_ledger(response: str, constraints: str | None = None, fixture: bool = False) -> dict:
    """The fit ledger is an exact projection of the evidence map, and counts nothing.

    The ledger replaced a sentence — "five of seven requirements are `direct`" —
    that the worked example taught with a wrong count from v0.1 and that measured
    runs copied and got wrong the same way. A projection can be compared with
    the map row by row; a sentence could only be argued with.

    `fixture` is set when the call comes from a fixture (run_checks): then the
    fixture's `candidate_constraints` is the only source of truth for the closing
    clause, and a value that is not "known" or "unknown" is a fixture error, never a
    fallback to the response's own envelope. A direct caller with no fixture (a
    unit test, the worked dossier) may leave it to the envelope.
    """
    checks, info, unchecked = [], [], []
    if fixture and constraints not in CONSTRAINTS:
        checks.append(finding("candidate_constraints", "all", False,
                              f"fixture error: a fit_ledger fixture declares top-level candidate_constraints "
                              f"as \"known\" or \"unknown\"; this one gives {constraints!r}", "fixture"))
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
            if note and names_requirement(note, requirement):
                copied_notes.add(note)
            if fit == "direct":
                continue
            if not note:
                bad_notes.append(f"{r} (`{fit}`) has no parenthetical")
            elif not names_requirement(note, requirement):
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
        word = ledger_rules.quantifier_in(text)
        if word:
            wording.append(f"{word.group(0)!r} in {line['line'][:80]!r}")
    checks.append(finding("ledger_wording", "all", not wording,
                          "; ".join(wording) or "no numeral or quantifier in the ledger"))

    # The one sentence the slot allows after the ledger is where the count came
    # back: a probe run wrote "R5b and R8 are the only rows below `direct`" under a
    # ledger that listed a third, and another "Every must-have is `direct`". It is
    # held to the rule the rest of the snapshot is (evidence-model.md, "The row is
    # the unit"), every word of the lists and every ratio in it read as a set claim
    # (ledger_rules.after_ledger_claim). Whether a named claim is true — the first
    # of those two — is the grader's: what the check reads and what it leaves to the
    # grader is stated above Claim in ci/ledger_rules.py.
    after = ledger_rules.ledger_sentence(source_text)
    word = ledger_rules.after_ledger_claim(after) if after else None
    if word and ledger_rules.is_second_sentence(after, word):
        said = f"more than one sentence after the ledger (rule 2 allows one): {word.text[:120]!r}"
    elif word:
        said = f"in the sentence after the ledger, {word.why}: {after[:120]!r}"
    else:
        said = "the sentence after the ledger names a row in every set claim it makes, and holds no complement"
    checks.append(finding("ledger_sentence", "all", word is None, said))

    # decision.summary is prose that reads the map, read with the one set-claim
    # reader (ledger_rules.map_claim) that CI and snapshot_count use.
    decision = (envelope_sections(response) or {}).get("decision")
    summary = decision.get("summary") if isinstance(decision, dict) else None
    if not isinstance(summary, str):
        unchecked.append("summary_count")
        info.append("no JSON envelope with sections.decision.summary: summary_count not checked")
    else:
        claim = ledger_rules.map_claim(summary)
        checks.append(finding("summary_count", "all", claim is None,
                              f"decision.summary: {claim.why}" if claim
                              else "decision.summary names a row in every set claim it makes over the map, "
                                   "and holds no complement"))

    section = snapshot_section(source_text)
    if section is None:
        checks.append(finding("snapshot_band", "all", False,
                              "no heading containing 'snapshot' to read the bands in",
                              "format"))
        unchecked += ["snapshot_count", "gates_line", "severity"]
        return {"checks": checks, "info": info, "unchecked": unchecked}

    band_problems = ledger_rules.band_problems(
        section, {rid: row.get("confidence", "") for rid, row in rows.items()})
    checks.append(finding("snapshot_band", "all", not band_problems,
                          "; ".join(band_problems) or "every band sits beside its row and "
                                                      "matches its Confidence"))
    count = ledger_rules.map_claim(ledger_rules.snapshot_prose(section))
    checks.append(finding("snapshot_count", "all", count is None,
                          f"the snapshot's prose: {count.why}" if count
                          else "the snapshot's prose names a row in every set claim it makes over the map, "
                               "and holds no complement"))
    unknown = (constraints == "unknown" if constraints in CONSTRAINTS else None) if fixture \
        else constraints_unknown(response, constraints)
    if unknown is None:
        info.append("hard-gates line: " + ("the fixture's candidate_constraints is not \"known\" or \"unknown\""
                                           if fixture else "neither the fixture nor the response declares "
                                           "candidate_constraints.status")
                    + ", so its closing \"candidate constraints not given\" clause is not judged")
    checks += rule_findings(ledger_rules.gates_line_problems(section, rows, unknown),
                            "gates_line", "gates_form",
                            "the hard-gates line agrees with the map's hard_gate rows", unchecked)

    register = ledger_rules.register_severities(source_text)
    if register is None:
        register = next((r for _, body in split_response(response)
                         if (r := ledger_rules.register_severities(body)) is not None), None)
    if register is None:
        info.append("no risk register with # and Severity columns: severities unchecked")
        unchecked.append("severity")
    else:
        checks += rule_findings(ledger_rules.severity_problems(section, register),
                                "severity", "severity_form",
                                "every severity matches the register, and the severe red flags line "
                                "names exactly its `severity: high` entries", unchecked)
    return {"checks": checks, "info": info, "unchecked": unchecked}


# --- 6c. Quotes -----------------------------------------------------------------

DQUOTES = dict.fromkeys(map(ord, "“”„‟″«»"), '"')
APOSTROPHES = dict.fromkeys(map(ord, "‘’‛′"), "'")
DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")
EDGE = " \t\"'.,;:!?()[]{}-"

# The evidence cell's grammar, closed, from mock-interview's output-template.md
# ("`Evidence, verbatim` holds the candidate's own words and nothing else"): the
# cell is `none given`, or one or more quoted sentences, each followed by a dash
# and where it came from — your CV, your message, the coach's notes, a dossier
# row. The cell is parsed whole, never pruned: deleting "a dash and up to sixty
# characters" before looking for leftovers is how "— your message, i.e. you set
# hiring strategy" passed as an origin. A dossier origin may name the row, or the
# field or section the quotation sits in — the template sends a dossier quote from
# `handoff_to_mock_interview.verified_candidate_evidence`, whose items carry no row
# ids — bare or alone in parentheses, from a closed set; nothing else may stand in
# those parentheses. "coach's notes" with or without its article is one origin.
DOSSIER_FIELD = (r"(?:handoff(?:_to_mock_interview)?(?:\.verified_candidate_evidence)?|verified_candidate_evidence|"
                 r"evidence_map)")
ORIGIN = (r"(?:your\s+cv|your\s+message|(?:the\s+)?coach's\s+notes|"
          r"(?:a\s+|the\s+)?dossier(?:'s)?(?:\s+row)?(?:,?\s+(?:row\s+)?r\d+[a-z]?)?"
          r"(?:\s+" + DOSSIER_FIELD + r"|\s*\(\s*" + DOSSIER_FIELD + r"\s*\))?)")
EVIDENCE_SEGMENT = r'"[^"\n]+"\s*-{1,2}\s*' + ORIGIN
# Segments are separated by what adds no words — a comma, semicolon, full stop,
# line break, "and" or a space, one punctuation mark optionally followed by "and"
# or a line break (", and"); each piece must still be a whole quote-and-origin
# segment, so nothing can be appended between them.
EVIDENCE_JOIN = r"(?:\s*(?:[;,.]\s*)?(?:<br\s*/?>|\band\b)\s*|\s*[;,.]\s*|\s+)"
EVIDENCE_CELL = re.compile(r"\s*" + EVIDENCE_SEGMENT + r"(?:" + EVIDENCE_JOIN + EVIDENCE_SEGMENT
                           + r")*\s*[.;]?\s*", re.I)
NONE_GIVEN = re.compile(r"\s*none given\s*[.;]?\s*", re.I)


def normalise_quote(text: str) -> str:
    text = text.translate(DQUOTES).translate(APOSTROPHES).translate(DASHES)
    text = text.replace("*", "").replace("`", "")
    return re.sub(r"\s+", " ", text.casefold()).strip()


def quoted_spans(cell: str) -> list[str]:
    return [span for span, _ in quoted_spans_with_origin(cell)]


# A Provenance quotation that is not the candidate's: a line from the JD, the
# recruiter, the company's published sources — the raising sources
# mock-interview's references/question-rubric.md defines — quoted with its origin
# beside it. Its origin is its own: "— X" or "(X)" right after it, "X:" or "X ("
# right before it, or, for a quoted title, the origin of the quotation it sits in
# ('"…" — Saltmarsh Games, "Announcing Project Larkspur"'). An origin that names the
# candidate's own material — their CV or message, the coach's notes, a fit-snapshot
# row, the dossier or one of its fields — is no other source.
CANDIDATE_ORIGIN = re.compile(
    r"(?<![a-z])(?:your\s+(?:cv|r[eé]sum[eé]|message|own|words)|(?:the\s+)?coach'?s?\s+notes?|cv|"
    r"r[eé]sum[eé]|candidate|dossier|verified[\s_]+(?:candidate[\s_]+)?evidence|fit\s+snapshot|f\d+[a-z]?|"
    # a dossier field is the dossier's material, named as rubric "A plain acknowledgment" says
    r"prohibited_claims?|acknowledge_gaps?|rejected_inferences?|handoff\w*|evidence_(?:state|map))"
    r"(?![a-z0-9])", re.I)
_DASH_ORIGIN = re.compile(r'\s*(?:-{1,2}|[–—])\s*([^;"\n()]*[^;"\n()\s,])')
_PAREN_ORIGIN = re.compile(r'\s*\(\s*([^()"\n]*[^()"\n\s])\s*\)')
_LEAD_ORIGIN = re.compile(r"([A-Za-z][\w'’ .-]{0,60}?)\s*(?::|\()\s*$")
_IN_ORIGIN = re.compile(r'^\s*(?:-{1,2}|[–—])\s*([^;"\n]*[^;"\n\s])\s*$')


def quoted_spans_with_origin(cell: str) -> list[tuple[str, str | None]]:
    """Each quotation in a cell with the origin written beside it, or None."""
    plain = cell.translate(DQUOTES).replace("`", "")
    hits = list(re.finditer(r'"([^"\n]+)"', plain))
    out = []
    for i, hit in enumerate(hits):
        after = plain[hit.end():hits[i + 1].start() if i + 1 < len(hits) else len(plain)]
        before = plain[hits[i - 1].end() if i else 0:hit.start()]
        before = before.rsplit(";", 1)[-1]
        origin = None
        if m := (_DASH_ORIGIN.match(after) or _PAREN_ORIGIN.match(after)):
            origin = m.group(1)
        elif m := _LEAD_ORIGIN.search(before):
            origin = m.group(1)
        elif i and (m := _IN_ORIGIN.match(plain[hits[i - 1].end():hit.start()])):
            origin = m.group(1)
        out.append((hit.group(1), origin.strip() if origin and origin.strip() else None))
    return out


def other_source(origin: str | None) -> bool:
    """An origin naming a source other than the candidate's own material."""
    return bool(origin) and not CANDIDATE_ORIGIN.search(origin)


# A plain acknowledgment's source may be a dossier item, named by its field
# (mock-interview references/question-rubric.md, "A plain acknowledgment", which
# states the rule once): the cell that cites it names the field anywhere in it, and
# quotes the item, if at all, whole and exactly as the dossier gives it. So a
# Provenance quotation that equals one whole item of a field its cell names, in the
# request's own dossier, is that item; every other quotation is the candidate's
# words. A field the cell does not name never answers, and a field's name cannot
# carry text the dossier does not hold.
DOSSIER_FIELDS = ("prohibited_claims", "acknowledge_gap", "rejected_inferences")
FIELD_NAME = re.compile(r"(?<![A-Za-z_])(prohibited_claim|acknowledge_gap|rejected_inference)s?(?![A-Za-z_])", re.I)


def fields_named(cell: str) -> set[str]:
    """The dossier fields a cell names outside its quotations, singular or plural,
    with or without backticks."""
    plain = re.sub(r'"[^"\n]*"', " ", cell.translate(DQUOTES).replace("`", ""))
    return {next(f for f in DOSSIER_FIELDS if f.startswith(m.group(1).lower())) for m in FIELD_NAME.finditer(plain)}


def dossier_items(prompt: str) -> dict[str, set[str]] | None:
    """The items of each named dossier field in the request's dossier envelope,
    normalised as quotations are; None when the request carries no dossier."""
    for block in reversed(JSON_BLOCK.findall(prompt)):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        sections = data.get("sections") if isinstance(data, dict) else None
        if not isinstance(sections, dict) or "handoff_to_mock_interview" not in sections:
            continue
        handoff = sections.get("handoff_to_mock_interview")
        handoff = handoff if isinstance(handoff, dict) else {}
        state = sections.get("evidence_state")
        found = {
            "prohibited_claims": handoff.get("prohibited_claims") or [],
            "acknowledge_gap": [a.get("requirement", "") for a in handoff.get("uncertain_or_weak_areas") or []
                                if isinstance(a, dict) and a.get("allowed_interview_strategy") == "acknowledge_gap"],
            "rejected_inferences": state.get("rejected_inferences") or [] if isinstance(state, dict) else [],
        }
        return {field: {normalise_quote(str(item)).strip(EDGE) for item in items if isinstance(item, str)}
                for field, items in found.items()}
    return None


def evidence_cell_lawful(cell: str) -> bool:
    plain = cell.translate(DQUOTES).translate(APOSTROPHES).translate(DASHES)
    plain = plain.replace("*", "").replace("`", "")
    return bool(NONE_GIVEN.fullmatch(plain) or EVIDENCE_CELL.fullmatch(plain))


def contains_words(fragment: str, pool: str) -> bool:
    """The fragment is in the pool on word boundaries: "ran" is not inside "transferred"."""
    return re.search(r"(?<!\w)" + re.escape(fragment) + r"(?!\w)", pool) is not None


def check_quotes(response: str, prompt: str, corpus_texts: list[str] | tuple = (),
                 candidate_text: list[str] | None = None) -> dict:
    """Every quotation in the verbatim cells is a quotation of something.

    The fit snapshot's evidence column and the banks' Provenance cells exist so a
    claim about the candidate's past carries the words it rests on. A cell that
    paraphrases inside quotation marks defeats the column while looking like
    compliance — and graders passed exactly that, because the quote was close
    enough to read as the candidate's.

    The evidence column holds the candidate's words and nothing else, and a
    Provenance cell carries every candidate sentence its guidance rests on, so both
    are checked against what the candidate gave (the fixture's `candidate_text`), on
    any length of quotation: checked against the prompt, a quoted JD line, a
    dossier header or a prohibited claim passed as the candidate's own. A fixture
    that declares no `candidate_text` gets that check reported unchecked, never a
    fallback to the prompt; `[]` means the candidate gave nothing quotable. A
    Provenance quote must also stand in the fit snapshot's evidence column, because
    the template says it is quoted exactly as it appears there. Three Provenance
    quotations are not the candidate's: one whole item of a dossier field its cell
    names (fields_named); a raising source's line — not in what the candidate gave,
    with its own origin naming a source other than the candidate's material
    (quoted_spans_with_origin, other_source) — checked only for existence in the
    request or the room's pages; and the template's token "none given". The
    requirement column quotes the JD, so it is checked against the request and the
    pages, from three words up; a canned room's pages are their title, URL and text
    (room_pages_text).
    """
    haystack = normalise_quote(prompt + "\n" + "\n".join(corpus_texts))
    own = normalise_quote("\n".join(candidate_text)) if candidate_text is not None else None
    dossier = dossier_items(prompt)
    checks, info, unchecked = [], [], []
    counted = {"fit_snapshot": [0, 0], "banks": [0, 0], "requirements": [0, 0]}   # spans, failures
    seen = {"fit_snapshot": False, "banks": False, "requirements": False}
    found: list[tuple[str, str, str, str]] = []          # (section, source, row, cell)
    evidence_spans: list[str] = []
    for source, body in split_response(response):
        for table in md_tables(body):
            names = header_names(table)
            columns = []
            verbatim = next((i for i, h in enumerate(names) if "verbatim" in h), None)
            if verbatim is not None:
                columns.append(("fit_snapshot", verbatim))
            if any("provenance" in h for h in names) and any("answer guidance" in h for h in names):
                columns.append(("banks", next(i for i, h in enumerate(names) if "provenance" in h)))
            requirement = next((i for i, h in enumerate(names) if "requirement" in h), None)
            if verbatim is not None and requirement is not None:
                columns.append(("requirements", requirement))
            for section, col in columns:
                seen[section] = True
                for cells in table["rows"]:
                    if col >= len(cells):
                        continue
                    row_id = cells[0].replace("`", "").replace("*", "").strip()[:20]
                    found.append((section, source, row_id, cells[col]))
                    if section == "fit_snapshot":
                        evidence_spans += [normalise_quote(s).strip(EDGE) for s in quoted_spans(cells[col])]
    in_snapshot = "\n".join(evidence_spans)

    for section, source, row_id, cell in found:
        if section == "fit_snapshot" and not evidence_cell_lawful(cell):
            checks.append(finding(
                "evidence_form", section, False,
                f"{source} row {row_id}: an evidence cell is neither `none given` nor quoted words, "
                f"each followed by a dash and its origin (your CV, your message, the coach's notes, "
                f"a dossier row), with nothing else: {cell.strip()[:100]!r}", "format"))
        candidate_column = section in ("fit_snapshot", "banks")
        named = fields_named(cell) if section == "banks" else set()
        for span, origin in quoted_spans_with_origin(cell):
            whole = normalise_quote(span).strip(EDGE)
            if not whole or (not candidate_column and len(whole.split()) < 3):
                continue
            if section == "banks" and whole == "none given":
                # The template's own token for an empty evidence cell ("derived
                # from F2's \"none given\" row"), never anyone's sentence.
                continue
            frags = [f for f in (x.strip(EDGE) for x in re.split(r"\.\.\.|…", normalise_quote(span))) if f]
            if named and dossier is not None and any(whole in dossier[f] for f in named):
                # One whole item of a dossier field the cell names: that item.
                bad, where = [], ""
            elif section == "banks" and other_source(origin) and not (
                    own is not None and all(contains_words(f, own) for f in frags)):
                # A raising source's line, quoted with its own origin, which names
                # no material of the candidate's: checked for existence, as the
                # requirement column is, at any length. A quotation found in what
                # the candidate gave stays the candidate's, whatever it claims.
                bad = [f for f in frags if not contains_words(f, haystack)]
                where = f"the request{' or the pages' if corpus_texts else ''} (quoted as from {origin[:40]!r})"
            elif candidate_column:
                if own is None:
                    bad, where = [], ""
                else:
                    bad, where = [f for f in frags if not contains_words(f, own)], "what the candidate gave"
                if section == "banks" and not bad and seen["fit_snapshot"]:
                    # With no fit snapshot table there is no column to quote from;
                    # that is reported once, as format, not once per Provenance cell.
                    bad = [f for f in frags if not contains_words(f, in_snapshot)]
                    where = "the fit snapshot's evidence column"
                if own is None and section == "fit_snapshot":
                    continue
                if bad and named:
                    where += (f", nor one whole item of the dossier's {' or '.join(sorted(named))}"
                              if dossier is not None else
                              f", and the request carries no dossier to hold {' or '.join(sorted(named))}")
            else:
                bad = [f for f in frags if len(f.split()) >= 3 and f not in haystack]
                where = "the request" + (" or the pages" if corpus_texts else "")
            counted[section][0] += 1
            if bad:
                counted[section][1] += 1
                checks.append(finding(
                    "quotes", section, False,
                    f"{source} row {row_id}: \"{span.strip()[:120]}\" — \"{bad[0][:80]}\" is not in {where}"))
    if own is None:
        info.append("the fixture declares no candidate_text: the evidence column's quotations, and the "
                    "Provenance quotations' source, are unchecked (never checked against the prompt)")
        unchecked.append("quotes")
    for section, (spans, failures) in counted.items():
        label = {"fit_snapshot": "fit snapshot (a column named 'verbatim')",
                 "banks": "question banks (Provenance beside Answer guidance)",
                 "requirements": "requirement column beside the verbatim one"}[section]
        if not seen[section] and section == "requirements":
            continue
        if not seen[section]:
            checks.append(finding("quotes", section, False, f"no {label} table", "format"))
        elif section == "fit_snapshot" and own is None:
            continue
        elif not failures:
            what = "of three words or more, " if section == "requirements" else ""
            checks.append(finding("quotes", section, True,
                                  f"{spans} quotation(s) {what}all verbatim"
                                  + (" in what the candidate gave" if section != "requirements" and own is not None
                                     else "")))
        info.append(f"{section}: {spans} quotation(s) checked, {failures} not verbatim")
    return {"checks": checks, "info": info, "unchecked": unchecked}


# --- The watch-out line (output-discipline.md rule 7) -----------------------------

WATCH_OUT_LABEL = "**Watch-out:**"
OUTPUT_DISCIPLINE = re.compile(r"^## Output discipline\s*$(.*?)(?=^## |\Z)", re.M | re.S)
WATCH_OUT_PARAM = re.compile(r"^[ \t]*watch_out[ \t]*:[ \t]*(.*?)[ \t]*$", re.M)
# A line labelled as a watch-out, in any spelling; and one labelled with the name it
# never takes, which counts only where the watch-out line should be.
WATCH_OUT_LABELLED = re.compile(r"^[\s>*_#-]*watch[- ]?outs?[*_\s]*:", re.I)
WARNING_LABELLED = re.compile(r"^[\s>*_#-]*warnings?[*_\s]*:", re.I)


def declared_watch_out(skill_md: str) -> str | None:
    """The sentence a SKILL.md declares as `watch_out:` under `## Output discipline`.

    One reader for the harness and for CI (ci/check_skills.py imports it), so the
    sentence the runs are held to and the one the copies are held to are the same
    string. None when the section or the parameter is missing or empty."""
    section = OUTPUT_DISCIPLINE.search(skill_md)
    found = WATCH_OUT_PARAM.search(section.group(1)) if section else None
    return found.group(1) if found and found.group(1) else None


def watch_out_line(sentence: str) -> str:
    """The line a delivered response ends with, exactly."""
    return f"{WATCH_OUT_LABEL} {sentence}"


def check_watch_out(response: str, sentence: str) -> dict:
    """The chat text ends with the skill's watch-out line, and no produced file holds it.

    Read exactly: the chat's last non-empty line must be `**Watch-out:** ` and the
    declared sentence, character for character once runs of whitespace are
    collapsed, and no other chat line may be labelled a watch-out. The chat is the
    text above the first file marker (split_response); a produced file fails if it
    holds the sentence or a line labelled a watch-out. A missing line, a line that is
    not last, a paraphrase, a line labelled a warning and a second labelled line are
    told apart in the reason, because each has a different fix. A warning elsewhere
    in the chat is not read: only the last line's label is."""
    checks = []
    want = " ".join(watch_out_line(sentence).split())
    sources = split_response(response)
    lines = [" ".join(line.split()) for line in sources[0][1].splitlines() if line.strip()]
    last = lines[-1] if lines else ""
    labelled = [i for i, line in enumerate(lines) if WATCH_OUT_LABELLED.match(line)]
    exact = [i for i, line in enumerate(lines) if line == want]
    if last == want and len(labelled) == 1:
        checks.append(finding("watch_out", "chat", True, "the chat's last line is the skill's watch-out, exactly"))
    elif last == want:
        others = [lines[i][:80] for i in labelled[:-1]]
        checks.append(finding("watch_out", "chat", False,
                              f"the watch-out line is last, but {len(others)} more line(s) are labelled as one, "
                              f"first {others[0]!r} — the line appears once"))
    elif exact:
        checks.append(finding("watch_out", "chat", False,
                              f"the watch-out line is present but not last: {len(lines) - 1 - exact[-1]} line(s) "
                              f"follow it, ending {last[:80]!r}"))
    elif WARNING_LABELLED.match(last):
        checks.append(finding("watch_out", "chat", False,
                              f"the last line is labelled a warning, which the watch-out is never called: "
                              f"{last[:120]!r}, wanted {want[:120]!r}"))
    elif labelled:
        got = lines[labelled[-1]]
        where = "the last line" if labelled[-1] == len(lines) - 1 else \
            f"a line {len(lines) - 1 - labelled[-1]} line(s) from the end"
        checks.append(finding("watch_out", "chat", False,
                              f"{where} is labelled a watch-out but is not the skill's sentence word for word: "
                              f"{got[:120]!r}, wanted {want[:120]!r}"))
    else:
        checks.append(finding("watch_out", "chat", False,
                              f"no watch-out line: the chat ends {(last or '(nothing)')[:80]!r}, wanted {want[:80]!r}"))
    flat = " ".join(sentence.split())
    for name, text in sources[1:]:
        inside = flat in " ".join(text.split()) or any(WATCH_OUT_LABELLED.match(line) for line in text.splitlines())
        checks.append(finding("watch_out", name, not inside,
                              f"{name} carries the watch-out — it closes the message that presents a file, never "
                              f"the file" if inside else f"{name} carries no watch-out line"))
    return {"checks": checks, "info": [], "unchecked": []}


# --- Assembly ----------------------------------------------------------------------

def room_pages_text(pages: list[dict], research_log: list | None) -> list[str]:
    """What a canned room showed the model, as quotable text: each page's title, URL
    and text, as research_server.py shows them in every result and fetch — and only
    the pages the run's research log shows returned. With no log, which pages
    returned is unknown, and every page of the fixture stands."""
    if research_log is not None:
        returned = [u for e in research_log if e.get("outcome") == "returned" for u in e.get("urls_returned") or []]
        pages = [p for p in pages if any(same_url(p.get("url", ""), u) for u in returned)]
    return [f"{p.get('title', '')}\n{p.get('url', '')}\n{p.get('text', '')}" for p in pages]


def run_checks(case: dict, mode: str, response: str, research_log: list | None,
               harness_status: str = "ok", harness_reasons: list | None = None,
               watch_out: str | None = None) -> dict:
    """Everything this fixture asks for, as one {stem}.checks.json record.

    `watch_out` is the skill's declared sentence. The runner passes it for every
    fixture of every skill, because every fixture's turn delivers output
    (run_fixtures.check_run); an empty string means the skill declares none, and
    the check is reported unchecked rather than passed. None leaves it out."""
    if harness_status != "ok":
        return {"status": "harness-invalid", "mode": mode, "checks": [],
                "info": list(harness_reasons or []), "unchecked": []}
    checks, info, unchecked = [], [], []
    research = case.get("research")
    wanted = case.get("checks", [])
    parts = []
    if research:
        parts.append(check_accounting(response, research, mode, research_log, case.get("prompt", ""),
                                      yes_pages=YES_PAGES_CHECK in wanted))
    if "fit_ledger" in wanted:
        parts.append(check_fit_ledger(response, case.get("candidate_constraints"), fixture=True))
    if "quotes" in wanted:
        corpus = room_pages_text([*(research or {}).get("pages", []), *(research or {}).get("user_pages", [])],
                                 research_log) if mode == "canned" else []
        parts.append(check_quotes(response, case.get("prompt", ""), corpus, case.get("candidate_text")))
    if watch_out:
        parts.append(check_watch_out(response, watch_out))
    elif watch_out is not None:
        parts.append({"checks": [], "unchecked": ["watch_out"],
                      "info": ["the skill declares no watch_out sentence: the watch-out line is unchecked"]})
    for part in parts:
        checks += part["checks"]
        info += part["info"]
        unchecked += part["unchecked"]
    failed = any(c["verdict"] == "FAIL" for c in checks)
    status = "fail" if failed else ("uncheckable" if unchecked else "ok")
    return {"status": status, "mode": mode, "checks": checks, "info": info,
            "unchecked": unchecked}
