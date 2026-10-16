"""The fit-ledger and decision-snapshot rules, stated once for every check that reads them.

job-underwriter's snapshot rules were checked twice: by ci/check_skills.py on the
worked dossier, and by evals/output_checks.py on the output of real runs. Each kept
its own copy of the patterns, and the copies drifted — the harness lacked "both",
"neither" and "each of" after CI had them, exempted "RR2 (`high`)" while CI failed
it, and read the first "hard gates" anywhere in the snapshot while CI read the slot.
The same output passed one check of a rule and failed the other. So the patterns and
the rule functions live here, and both checkers call them: a rule changed here is
changed for both, and a rule cannot be checked one way in CI and another in the
harness.

What is a rule here, and where it is written:
- no count, fraction or quantifier over the map — job-underwriter
  references/evidence-model.md, "The row is the unit" (its quoted list is the rule;
  QUANTIFIERS and AFTER_LEDGER_ONLY hold exactly it, scope by scope, as
  rule_quantifier_scopes() reads it, and CI checks that they do);
  how prose is read for it (years, map words that are also ordinary English, row
  names, articles, parentheses) is stated once, above MAP_WORDS;
- naming a row in its Requirement's own words — the fit ledger's rule 2, which
  the hard-gates line's failed and unconfirmed rows use too (names_requirement);
- which fits a gate row may take — references/evidence-model.md, "A gate is met, not
  established, or failed" (gate_fit_problems, run with the hard-gates line);
- the sentence after the ledger, the bands, the hard-gates line and the severe red
  flags — references/risk-and-decision.md, "The decision snapshot", items 2, 4, 5.

Every function is pure: text in, problems out. Problems are plain sentences; the
callers prefix them (CI with the dossier's path, the harness with nothing).
No third-party imports, like the rest of ci/.
"""

from __future__ import annotations

import re

PRIORITY_ORDER = ["hard_gate", "must_have", "important", "preferred"]
FIT_ORDER = ["direct", "adjacent", "unclear", "absent", "hard_gate_fail"]
BANDS = ("high", "medium", "low", "none")
ROW_ID = r"R\d+[a-z]?"
RISK_ID = r"RR\d+"

COUNT_WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve".split())}
_NUMBER = r"(?:\d+|" + "|".join(COUNT_WORDS) + r")"

# "N of M": "five of seven", "4 of 7".
COUNTED = re.compile(r"\b" + _NUMBER + r"\s+of\s+" + _NUMBER + r"\b", re.I)
# "4/7", "four out of".
FRACTION = re.compile(r"\b\d+\s*/\s*\d+\b|\b" + _NUMBER + r"\s+out\s+of\b", re.I)

# What a count or a quantifier is about when it is about the map: a tier, rows or
# requirements, a fit, or the rows below `direct` as "gaps". How the prose is read,
# stated once here for every check that reads it:
#
# - Some map words are also ordinary English: "two important unknowns", "one direct
#   conversation", "two direct reports", "absent a reference", "a gap analysis". Each
#   of these — important, preferred, direct, absent and singular gate and gap — is a
#   map word only as a token (in backticks, `important`), where it ends its noun
#   phrase ("only two direct.", "five important", "the one gap"), or where a word in
#   _NP_END follows it: a linking verb or preposition ("both gate rows are met"), a
#   requirement noun ("two direct rows", "the one preferred item"), a fit noun ("five
#   direct fits", "two direct matches") or a verb a gate, gap or fit takes as its
#   predicate ("every gate passes", "neither gate fails", "4 of 7 met"). Followed by
#   any other word it is that word's adjective, and the count is about that word. A
#   hyphen that joins a word ("direct-to-consumer", "on-call") does not end a noun
#   phrase. The words that are never ordinary English — must-have, hard gate,
#   requirement, row, adjacent, unclear, hard_gate_fail, and the plurals gates and
#   gaps — are map words wherever they stand ("two gates fail outright").
# - "N of M" and a fraction ("4/7", "four out of seven") are a count over the map when
#   they end their noun phrase ("Fit: 4 of 7.", "4 of 7 met") or a map word follows in
#   reach ("4/7 direct", "five of seven material requirements"). Followed by any other
#   noun they count that noun ("one of two openings", "24/7 on-call", "3 of 5 years").
#   One whose first number exceeds its second ("24/7", "2024/25") counts no rows.
#   That is RATIO, read through map_claim with everything else here.
# - A year is not a count: "February 2027" never counts rows (_COUNT).
# - A count does not reach a singular map noun named by a row ID: "round 2 of the
#   interviews, and the R8 gate" names R8's gate and counts nothing (MAP_COUNT only; a
#   quantifier such as "only the R4 gap" still picks rows out).
# - "a"/"an" opens a new noun phrase, so a count or quantifier does not reach past it
#   to a map word ("the one question a hard gate may ask") unless only a row ID or a
#   linking verb stands between ("two have a gap", "only R4 has a gap" still count).
# - A count inside a parenthesis does not reach a map word outside it: "(mentor two
#   juniors) is `unclear`" counts juniors (_search).
_NP_END = (r"(?=\s*(?:-(?!\w)|[^\w\s-]|\Z|(?:and|or|but|nor|is|are|was|were|be|been|sit|sits|remain|remains|read|reads|"
           r"stand|stands|has|have|had|would|will|can|may|might|must|should|in|on|at|to|for|of|with|from|under|"
           r"below|above|across|among|against|than|a|an|the|that|which|this|left|remaining|open|outstanding|"
           r"here|there|now|ones?|" + ROW_ID + r"|rows?|requirements?|tiers?|items?|skills?|qualifications?|"
           r"criteri(?:on|a)|dut(?:y|ies)|responsibilit(?:y|ies)|asks?|terms?|conditions?|"
           # the fit nouns, and the verbs a gate, gap or fit takes as its predicate
           r"fits?|match(?:es)?|met|meets?|fail(?:s|ed)?|pass(?:es|ed)?|holds?|held|blocks?|blocked|"
           r"clears?|cleared|matters?|closes?|closed|stays?)\b(?!-\w)))")


def _map_word(words: str) -> str:
    """`words` read as map words, the ordinary-English ones only as a token or where
    they end their noun phrase."""
    return r"(?:(?<=`)" + words + r"\b|" + words + r"\b" + _NP_END + r")"


TIER_WORDS = (r"(?:hard[_ -]?gates?|must[_ -]?haves?|requirements?|rows?|gates|"
              + _map_word(r"(?:important|preferred|gate)") + r")")
FIT_WORDS = r"(?:adjacent|unclear|hard[_ -]?gate[_ -]?fails?|" + _map_word(r"(?:direct|absent)") + r")"
MAP_WORDS = r"(?:" + TIER_WORDS + r"|" + FIT_WORDS + r"|gaps|" + _map_word(r"gap") + r")"
# A singular map noun right after a row ID is that row's name, not a counted word.
_NAMED = "".join(rf"(?<!R{d}{x} )(?<!R{d}{x}` )" for d in (r"\d", r"\d\d") for x in ("", "[a-z]"))
_COUNTED_MAP_WORDS = r"(?:" + _NAMED + r"|(?!(?:gate|gap|requirement|row)\b))" + MAP_WORDS
# Up to four words between, inside one clause: a full stop, semicolon, colon or
# question mark ends the reach, so a number in one sentence is never tied to a map
# word in the next. An article ends it too, unless only row IDs and linking words
# came before it.
_SEP = r"[^\w.!?;:]+"
_LINK = r"(?:" + ROW_ID + r"|of|them|they|which|is|are|was|were|has|have|had|carry|carries|show|shows|need|needs)"
_REACH = (r"(?:(?:" + _SEP + _LINK + r"\b){0,3}?" + _SEP + r"an?\b)?(?:" + _SEP + r"(?!an?\b)\w+){0,4}?" + _SEP)
# A number that is a count: not an enumerator "(2)", not a price "£95k", not part
# of a decimal, a range ("3–7") or a row ID ("R4" has no word boundary before its
# digit), not quoted ("a team of one"), not a year ("2027"), and not a figure with
# its unit — "8+ years", "an 8-year bar", "9 years", "three squads" are the
# candidate's or the posting's numbers, which the rule leaves alone — and not the
# pronoun in "this one" or "that one".
_UNIT = (r"(?:years?|yrs?|months?|weeks?|days?|hours?|minutes?|people|persons?|employees|staff|"
         r"reports?|squads?|teams?|engineers?|times?|percent)")
_COUNT = (r"(?<![(£$€#.\d–—-])(?<!\bthis )(?<!\bthat )\b(?!(?:19|20)\d\d\b)" + _NUMBER
          + r"\b(?!\s*\)|[.,]\d|%|\+|[-–—]\s*\d|-|[\"”’']|\s+" + _UNIT + r"\b)")
# "Four rows", "four direct", "four of the seven material requirements",
# "5/7 must-haves": a count, then within reach a map word.
MAP_COUNT = re.compile(
    r"(?:" + _COUNT + r"(?:\s+of)?(?:\s+(?:the|my|its|these|those|our|your|their))?(?:\s+" + _NUMBER + r"\b)?"
    + r"|" + FRACTION.pattern + r")" + r"(?:" + _REACH + r")?" + _COUNTED_MAP_WORDS + r"\b", re.I)

# The quantifiers the rule forbids over the map or a tier of it: evidence-model.md's
# list, verbatim ("The row is the unit"), which states it once. Every word of it is a
# quantifier over the map wherever a map word follows it within reach (MAP_UNIVERSAL),
# and any of them fails in the one sentence after the fit ledger wherever it stands
# (AFTER_LEDGER_UNIVERSAL). The list scopes one more to that sentence only —
# AFTER_LEDGER_ONLY, a bare "none" — because the slots elsewhere require "none
# failed" and "none found"; the token `none` in backticks is a band or a gap type and
# never a quantifier. ci/check_skills.py holds both scopes to the list as
# rule_quantifier_scopes() reads it, so a word added to either side there fails CI
# until it is added here.
AFTER_LEDGER_ONLY = ("none",)
QUANTIFIERS = ("N of M", "every", "all", "each of", "only", "the one", "none of", "both",
               "neither", "the rest", "no other", "any other", "no `must_have` row") + AFTER_LEDGER_ONLY


def _phrase(phrase: str) -> str:
    if phrase == "N of M":
        return COUNTED.pattern
    if phrase == "no `must_have` row":
        # Any tier or rows, in any spelling: "no must-have", "no `hard_gate` row".
        return r"\bno\s+[`*_]*" + TIER_WORDS + r"\b"
    if phrase == "none":
        return r"(?<!`)\bnone\b(?!`)"
    return r"\b" + r"\s+".join(map(re.escape, phrase.split())) + r"\b"


# The sentence after the ledger is about the map by construction, so any of these
# in it is a quantifier over the map, wherever it stands.
AFTER_LEDGER_UNIVERSAL = re.compile("|".join(f"(?:{_phrase(p)})" for p in QUANTIFIERS), re.I)

# Elsewhere — decision.summary and the rest of the snapshot — a word of the list is a
# quantifier over the map when a map word follows it within reach: "every must-have",
# "both rows", "the rest are `direct`", "the only gap". The words are the list's own,
# built from QUANTIFIERS so the two cannot drift. Three are read in their quantifier
# sense only, because the prose needs the plain ones: "only" when it picks rows out
# ("the only", "only R4", "only two") rather than qualifying one ("only adjacent"),
# "all" also as "all but" with no map word after it, and bare "none" not at all —
# the slots require "none failed" and "none found", and the list exempts it.
_PROSE_WORDS = [p for p in QUANTIFIERS if p not in ("N of M", "no `must_have` row", "none", "only")]
_ONLY = r"\bthe\s+only\b|\bonly(?=\s+(?:R\d|the\b|" + _NUMBER + r"\b))"
MAP_UNIVERSAL = re.compile(
    r"(?:" + "|".join(_phrase(p) for p in _PROSE_WORDS) + r"|" + _ONLY + r")(?:" + _REACH + r")?"
    + MAP_WORDS + r"\b|" + _phrase("no `must_have` row") + r"|\ball\s+(?:but|except)\b", re.I)


def rule_quantifiers(evidence_model: str) -> list[str]:
    """The quoted quantifiers in evidence-model.md's "The row is the unit" bullet,
    the ones it scopes to the sentence after the ledger included.

    For a drift check. Returns [] when the bullet or its list cannot be found,
    which a caller should treat as a failure.
    """
    general, after = rule_quantifier_scopes(evidence_model)
    return general + after


# Where evidence-model.md's list turns from the whole map to the one sentence after
# the ledger: "— and in the one sentence after the snapshot's fit ledger, … no …".
SCOPE_TURN = re.compile(r"\bin the one sentence after\b[^\"]*")


def rule_quantifier_scopes(evidence_model: str) -> tuple[list[str], list[str]]:
    """evidence-model.md's list in its two scopes: (the quantifiers over the map
    anywhere, the further ones it scopes to the sentence after the fit ledger).
    For the drift check that holds them to QUANTIFIERS and AFTER_LEDGER_ONLY.
    Both empty when the bullet or its list cannot be found."""
    bullet = next((line for line in evidence_model.splitlines()
                   if line.lstrip("- ").startswith("**The row is the unit")), "")
    lead = re.search(r"quantifier over the map or a tier of it:\s*(.*?)\.\s", bullet)
    if not lead:
        return [], []
    turn = SCOPE_TURN.search(lead.group(1))
    cut = turn.start() if turn else len(lead.group(1))
    return (re.findall(r'"([^"]+)"', lead.group(1)[:cut]),
            re.findall(r'"([^"]+)"', lead.group(1)[cut:]))


# --- Sentences ---------------------------------------------------------------------

_ABBREVIATIONS = re.compile(r"\b(?:e\.g|i\.e|etc|vs|approx|cf|No|St|Mr|Ms|Mrs|Dr)\.", re.I)
SENTENCE_BREAK = re.compile(r"(?<=[.!?])[\"”’')\]*_]*\s+(?=[\"“‘(`*_\[]*[A-Z0-9])")


def sentences(text: str) -> list[str]:
    """The sentences of a passage: a full stop, question or exclamation mark, then
    a capital. A code span, a decimal and an abbreviation's full stop are not breaks."""
    masked = re.sub(r"`[^`\n]*`", lambda m: "`" + "x" * (len(m.group(0)) - 2) + "`", text)
    masked = re.sub(r"(?<=\d)\.(?=\d)", "x", masked)
    masked = _ABBREVIATIONS.sub(lambda m: m.group(0)[:-1] + "x", masked)
    cuts = [0] + [m.end() for m in SENTENCE_BREAK.finditer(masked)] + [len(text)]
    return [text[a:b].strip() for a, b in zip(cuts, cuts[1:]) if text[a:b].strip()]


def _search(pattern: re.Pattern, text: str) -> re.Match | None:
    """The first match of a count-or-quantifier pattern that does not reach out of a
    parenthesis: in "(mentor two juniors) is `unclear`" the count is inside one and
    the map word outside, so the count is the candidate's, not the map's."""
    at = 0
    while (hit := pattern.search(text, at)) is not None:
        if hit.group(0).count(")") <= hit.group(0).count("("):
            return hit
        at = hit.start() + 1
    return None


# "N of M", "N out of M" and "4/7" (not a date's "10/16/2026", not a decimal). They
# count the map only as the comment above MAP_WORDS says: ending their noun phrase, or
# with a map word in reach, which MAP_COUNT reads.
RATIO = re.compile(r"(?:\b(" + _NUMBER + r")\s+(?:out\s+)?of\s+(" + _NUMBER + r")\b|(?<![\d/.,])\b(\d+)\s*/\s*(\d+)\b"
                   r"(?!\s*/\s*\d|[.,]\d))" + _NP_END, re.I)


def _number(word: str) -> int:
    return int(word) if word.isdigit() else COUNT_WORDS[word.lower()]


def _ratio(text: str) -> re.Match | None:
    """The first RATIO that could count rows: its first number no larger than its
    second."""
    for hit in RATIO.finditer(text):
        n, m = (hit.group(1), hit.group(2)) if hit.group(1) else (hit.group(3), hit.group(4))
        if _number(n) <= _number(m):
            return hit
    return None


def map_claim(text: str) -> re.Match | None:
    """A count, fraction or quantifier over the map, in any prose that reads it: the
    snapshot's prose, decision.summary, and the counts in the sentence after the
    ledger. The one reader every check of the rule calls, in CI and in the harness: a
    ratio that counts rows (RATIO), a count with a map word in reach (MAP_COUNT), or a
    word of the list with a map word in reach (MAP_UNIVERSAL). Counts that are not
    about map rows — the candidate's own figures, "two of three squads", "24/7
    on-call", the Research tier line — are outside the rule, and bare "none" stays out
    because the slots require "none failed" and "none found". How the words are read
    is stated once, above MAP_WORDS."""
    return _ratio(text) or _search(MAP_COUNT, text) or _search(MAP_UNIVERSAL, text)


SECOND_SENTENCE = re.compile(r"(?s)(?<=\S)\s.*")


def after_ledger_claim(text: str) -> re.Match | None:
    """What rule 2 forbids after the ledger: a count or fraction over the map, read as
    map_claim reads it everywhere; any word of the list, "N of M" included, wherever
    it stands ("at most one sentence … says nothing about the rows it does not
    name"); or a second sentence. For a second sentence the match is that sentence."""
    hit = map_claim(text) or AFTER_LEDGER_UNIVERSAL.search(text)
    if hit:
        return hit
    parts = sentences(text)
    if len(parts) > 1:
        at = text.index(parts[1])
        return re.compile(re.escape(text[at:])).search(text, at)
    return None


def is_second_sentence(text: str, hit: re.Match | None) -> bool:
    """Whether after_ledger_claim's hit is the extra-sentence case rather than a
    count or quantifier, so both checkers word the failure the same way."""
    return bool(hit) and len(sentences(text)) > 1 and hit.group(0) == text[hit.start():]


LEDGER_MARK = re.compile(r"^\s*[*_]*\s*fit ledger\b", re.I)


def ledger_lines_span(lines: list[str]) -> tuple[int, int] | None:
    """(first, end) line indexes of the ledger's "- " lines under its mark."""
    mark = next((i for i, line in enumerate(lines) if LEDGER_MARK.match(line)), None)
    if mark is None:
        return None
    i = mark + 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    first = i
    while i < len(lines) and lines[i].lstrip().startswith("- "):
        i += 1
    return first, i


# Where the after-ledger region stops: the next slot, bold-led or bulleted, a heading,
# a table, a fence, or a slot label written plain.
NEXT_SLOT = re.compile(r"^\s*(?:[-*+]\s|\*\*|__|#|\||```|(?:opportunity ledger|hard gates|severe red flags|"
                       r"conditions for go|what would change)\b)", re.I)


def ledger_sentence(snapshot: str) -> str:
    """Everything between the ledger's lines and the next slot — every paragraph of
    it, not only the first, since a second paragraph is a second sentence."""
    lines = snapshot.splitlines()
    span = ledger_lines_span(lines)
    if span is None:
        return ""
    i = span[1]
    para = []
    while i < len(lines) and not NEXT_SLOT.match(lines[i]):
        if lines[i].strip():
            para.append(lines[i].strip())
        i += 1
    return " ".join(para)


def snapshot_prose(snapshot: str) -> str:
    """The snapshot without the ledger's own lines and without table rows."""
    lines = snapshot.splitlines()
    span = ledger_lines_span(lines)
    drop = set(range(*span)) if span else set()
    return "\n".join(line for i, line in enumerate(lines)
                     if i not in drop and not line.lstrip().startswith(("|", "Research tier")))


SLOT_LINE = re.compile(r"^\s*[-*+]\s+(?:\*\*|__)?[A-Z][^:\n]{0,40}:")


def slot_extent(snapshot: str) -> str:
    """The snapshot through its last bulleted slot ("- **Conditions for go:** …") and
    that slot's continuation lines. A worked template explains its snapshot in a
    paragraph after the slots; that commentary is about the rules, not a reading of
    the map, and is not the snapshot. With no bulleted slot, the whole text."""
    lines = snapshot.splitlines()
    last = max((i for i, line in enumerate(lines) if SLOT_LINE.match(line)), default=None)
    if last is None:
        return snapshot
    end = last + 1
    while end < len(lines) and lines[end].strip():
        end += 1
    return "\n".join(lines[:end])


# --- Bands -------------------------------------------------------------------------

BAND_TOKEN = re.compile(r"`(" + "|".join(BANDS) + r")`")
BAND_ATTACHED = re.compile(r"(?<![A-Za-z])(" + ROW_ID + r")\s*\(\s*`(" + "|".join(BANDS) + r")`\s*\)")
# The same band written without backticks: "R3 (high)", "RR2 (high)", "(high)".
BAND_PLAIN = re.compile(r"(?<![A-Za-z])(?:(" + ROW_ID + r"|" + RISK_ID + r")\s*)?\(\s*(high|medium|low|none)\s*\)", re.I)


def _token(cell: str) -> str:
    return re.sub(r"[`*]", "", cell or "").strip().lower()


def band_problems(snapshot: str, confidence: dict[str, str]) -> list[str]:
    """Every band in the snapshot sits as "R4 (`medium`)" and is R4's Confidence.

    `confidence` maps each evidence-map row ID to its Confidence cell. A bare
    `high`, `medium`, `low` or `none` is always a confidence band (rule 5); a
    register entry's severity is written `severity: high`, which this never reads.
    A band in parentheses without backticks — "R3 (high)" — is read the same way:
    beside a row it is that row's and is checked against it, beside a register
    entry it is a severity written like a band, and alone it is attached to
    nothing. A plain "(none)" with no ID before it is not read, since prose uses it.
    """
    attached = {m.start(2) - 1: m for m in BAND_ATTACHED.finditer(snapshot)}
    problems = []
    for token in BAND_TOKEN.finditer(snapshot):
        band = token.group(1)
        hit = attached.get(token.start())
        if hit is None:
            why = f"snapshot states `{band}` without attaching it to one row"
            if re.search(r"(?<![A-Za-z])" + RISK_ID + r"\s*\(\s*$", snapshot[:token.start()]):
                why += f" (a severity written like a band; write `severity: {band}`)"
            problems.append(why)
            continue
        problems += _band_against_map(hit.group(1), band, confidence)
    for plain in BAND_PLAIN.finditer(snapshot):
        rid, band = plain.group(1), plain.group(2).lower()
        if rid is None:
            if band != "none":
                problems.append(f"snapshot states ({band}) without attaching it to one row")
        elif re.fullmatch(RISK_ID, rid):
            problems.append(f"snapshot gives {rid} ({band}), a severity written like a band; "
                            f"write {rid} (`severity: {band}`)")
        else:
            problems += _band_against_map(rid, band, confidence)
    return problems


def _band_against_map(rid: str, band: str, confidence: dict[str, str]) -> list[str]:
    if rid not in confidence:
        return [f"snapshot gives {rid} `{band}`; {rid} is not a row of the evidence map"]
    if _token(confidence[rid]) != band:
        return [f"snapshot gives {rid} `{band}`; the map says {_token(confidence[rid]) or 'nothing'}"]
    return []


# --- Slots -------------------------------------------------------------------------

def slot_lines(snapshot: str, label: str) -> list[re.Match]:
    """Every line that is the snapshot's `label` slot: the label opens the line (after
    an optional bullet), bold optional, colon required inside or outside the bold.
    Prose that mentions the label mid-sentence is never the slot."""
    words = r"[ _-]".join(map(re.escape, label.split()))
    pattern = re.compile(
        r"^[ \t]*(?:[-*+][ \t]+)?(?:\*\*|__)?[ \t]*" + words +
        r"[ \t]*(?::[ \t]*(?:\*\*|__)|(?:\*\*|__)?[ \t]*:)[ \t]*(.*?)[ \t]*$", re.I | re.M)
    return list(pattern.finditer(snapshot))


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


NAME_STOP = {"a", "an", "the", "and", "or", "of", "for", "with", "in", "on", "to", "at", "by"}


def name_words(text: str) -> set[str]:
    """A parenthetical's words, for checking it names its row in the row's own words."""
    return {w.rstrip("s") for w in re.findall(r"[a-z0-9+]+", text.replace("*", "").replace("`", "").lower())
            if w not in NAME_STOP}


# A row named in its Requirement's own words, "R6 (Fully remote (UK))": the words in
# parentheses, which may hold one level of their own, since a Requirement's words do
# ("Remote (US) or our Denver office"). One grammar for the item wherever rule 2's
# naming rule applies — the fit ledger (LEDGER_ITEM, read by CI on the worked
# dossier and by the harness on runs) and the hard-gates line's failed and
# unconfirmed rows (GATE_ITEM) — so the two cannot accept different words.
ITEM_WORDS = r"\(((?:[^()]|\([^()]*\))+)\)"
LEDGER_ITEM = re.compile(r"^(" + ROW_ID + r")(?:\s+" + ITEM_WORDS + r")?$")


def names_requirement(note: str, requirement: str) -> bool:
    got = name_words(note)
    return bool(got) and got <= name_words(requirement)


# --- The hard-gates line (rule 4) ---------------------------------------------------

CONSTRAINTS_CLAUSE = re.compile(
    r"\s*;?\s*candidate constraints not given\s*[-—–]+\s*checks against them unknown\s*$", re.I)
GATE_ITEM = re.compile(r"^(" + ROW_ID + r")\s*(?:\(\s*`([a-z_]+)`\s*\)|`([a-z_]+)`|" + ITEM_WORDS + r")?$")
CLAUSE_ORDER = {"failed": 0, "none failed": 0, "none stated": 0, "unconfirmed": 1, "met": 2}


def _gate_items(text: str) -> list[tuple[str, str | None, str | None]] | None:
    """(id, fit, words) per item, or None when an item is not one."""
    items = []
    for piece in split_top(text, (",", " and ")):
        m = GATE_ITEM.match(piece.strip())
        if not m:
            return None
        items.append((m.group(1), m.group(2) or m.group(3), m.group(4)))
    return items


# A gate is binary (job-underwriter references/evidence-model.md, "A gate is met, not
# established, or failed"): a `hard_gate` row's fit is `direct`, `unclear` or
# `hard_gate_fail`, and `hard_gate_fail` is a gate row's fit only. Rule 4's line files
# every gate row that is neither failed nor unclear as met, so a gate row at `adjacent`
# or `absent` would read as met, and a failed non-gate row would not be on the line.
GATE_FITS = ("direct", "unclear", "hard_gate_fail")


def gate_fit_problems(rows: dict[str, dict]) -> list[tuple[str, str]]:
    """Every map row whose fit the gate rule forbids, as ("judgement", problem) pairs.

    `rows` maps each evidence-map row ID to {"priority", "fit", ...}."""
    problems = []
    for rid, row in rows.items():
        priority, fit = _token(row.get("priority", "")), _token(row.get("fit", ""))
        if priority == "hard_gate" and fit not in GATE_FITS:
            problems.append(("judgement", f"{rid} is a hard_gate row at `{fit or 'no fit'}`; a gate row's fit is "
                                          f"direct, unclear or hard_gate_fail (evidence-model.md, \"A gate is met, "
                                          f"not established, or failed\"), and the hard-gates line would file it "
                                          f"as met"))
        elif fit == "hard_gate_fail" and priority != "hard_gate":
            problems.append(("judgement", f"{rid} is a {priority or 'priority-less'} row at `hard_gate_fail`; only a "
                                          f"hard_gate row fails as a gate, and the hard-gates line does not read it"))
    return problems


def gates_line_problems(snapshot: str, rows: dict[str, dict],
                        constraints_unknown: bool | None = None) -> list[tuple[str, str]]:
    """The map's gate fits (gate_fit_problems), then the snapshot's hard-gates line."""
    return gate_fit_problems(rows) + _gates_line(snapshot, rows, constraints_unknown)


def _gates_line(snapshot: str, rows: dict[str, dict],
                constraints_unknown: bool | None = None) -> list[tuple[str, str]]:
    """The snapshot's `- **Hard gates:**` slot against the map's `hard_gate` rows.

    `rows` maps each evidence-map row ID to {"priority", "fit", "requirement"}.
    `constraints_unknown` is candidate_constraints.status == "unknown", or None when
    the caller cannot know it (then the closing clause is not judged).
    Returns (kind, problem) pairs; kind is "slot" (the slot is missing or doubled,
    so nothing could be read), "form" (the line's grammar) or "judgement".
    """
    gate = {rid: row for rid, row in rows.items() if _token(row.get("priority", "")) == "hard_gate"}
    found = slot_lines(snapshot, "hard gates")
    if not found:
        # Every snapshot carries the slot, gate rows or not (rule 4): with none it
        # reads "none stated", and it is where unknown constraints are flagged.
        return [("slot", "the snapshot has no **Hard gates:** line"
                         + (f"; the map's hard_gate rows are {sorted(gate)}" if gate else
                            "; with no hard_gate row it reads \"none stated\""))]
    if len(found) > 1:
        return [("slot", f"the snapshot has {len(found)} **Hard gates:** lines; the rule is one")]
    body = re.sub(r"(?:\*\*|__)\s*$", "", found[0].group(1)).strip()
    problems: list[tuple[str, str]] = []

    fits = {rid: _token(row.get("fit", "")) for rid, row in gate.items()}
    failed_rows = {r for r, f in fits.items() if f == "hard_gate_fail"}
    unclear_rows = {r for r, f in fits.items() if f == "unclear"}
    met_rows = set(gate) - failed_rows - unclear_rows

    named = set(re.findall(r"(?<![A-Za-z])(" + ROW_ID + r")\b", body))
    if named != set(gate):
        problems.append(("judgement", f"the hard-gates line names {sorted(named) or 'no row'}; "
                                      f"the map's hard_gate rows are {sorted(gate) or 'none'}"))
    for rid, fit in re.findall(r"(?<![A-Za-z])(" + ROW_ID + r")\s*\(?\s*`([a-z_]+)`", body):
        if rid in fits and fits[rid] != fit:
            problems.append(("judgement", f"the hard-gates line gives {rid} `{fit}`; the map says {fits[rid]}"))
    says_none_failed = re.search(r"\bnone failed\b", body, re.I) is not None
    if failed_rows and says_none_failed:
        problems.append(("judgement", f"the hard-gates line says \"none failed\"; the map's "
                                      f"hard_gate_fail rows are {sorted(failed_rows)}"))
    if gate and not failed_rows and not says_none_failed:
        problems.append(("judgement", "no gate row failed, and the hard-gates line does not say \"none failed\""))

    text = re.sub(r"[.\s]+$", "", re.sub(r"\*\*|__", "", body))
    flagged = CONSTRAINTS_CLAUSE.search(text)
    if flagged:
        text = text[:flagged.start()].strip()
    if constraints_unknown is True and not flagged:
        problems.append(("judgement", "the candidate's constraints were not given, and the hard-gates line "
                                      "does not end \"; candidate constraints not given — checks against them unknown\""))
    elif constraints_unknown is False and flagged:
        problems.append(("judgement", "the hard-gates line says the candidate's constraints were not given; "
                                      "candidate_constraints.status is known"))

    clauses: dict[str, list] = {}
    last = -1
    for clause in split_top(text, (";",)):
        if not clause:
            continue
        if re.fullmatch(r"none stated", clause, re.I):
            kind, items = "none stated", []
        elif (m := re.fullmatch(r"none failed(?:\s*\((.*)\))?", clause, re.I | re.S)):
            kind, items = "none failed", _gate_items(m.group(1)) if m.group(1) else []
        elif (m := re.fullmatch(r"(failed|unconfirmed|met)\s*:\s*(.+)", clause, re.I | re.S)):
            kind, items = m.group(1).lower(), _gate_items(m.group(2))
        else:
            problems.append(("form", f"the hard-gates line has a clause that is none of \"failed:\", "
                                     f"\"none failed\", \"unconfirmed:\", \"met:\" or \"none stated\": {clause[:80]!r}"))
            continue
        if items is None:
            problems.append(("form", f"the hard-gates line's {kind} clause is not a list of row IDs: {clause[:80]!r}"))
            items = []
        if kind in clauses or CLAUSE_ORDER[kind] < last or (CLAUSE_ORDER[kind] == 0 and last >= 0):
            problems.append(("form", f"the hard-gates line's \"{kind}\" clause is out of order or repeated "
                                     f"(failed or none failed, then unconfirmed, then met)"))
        last = max(last, CLAUSE_ORDER[kind])
        clauses[kind] = items

    def ids(kind: str) -> set[str]:
        return {i[0] for i in clauses.get(kind) or []}

    if not gate:
        if "none stated" not in clauses or len(clauses) > 1:
            problems.append(("judgement", "the map has no hard_gate row, and the hard-gates line does not read "
                                          "\"none stated\""))
        return problems
    if "none stated" in clauses:
        problems.append(("judgement", f"the hard-gates line says \"none stated\"; the map's hard_gate rows are "
                                      f"{sorted(gate)}"))
    if ids("failed") != failed_rows:
        problems.append(("judgement", f"the hard-gates line's failed clause names {sorted(ids('failed')) or 'no row'}; "
                                      f"the map's hard_gate_fail rows are {sorted(failed_rows) or 'none'}"))
    if ids("unconfirmed") != unclear_rows:
        problems.append(("judgement", f"the hard-gates line's unconfirmed clause names "
                                      f"{sorted(ids('unconfirmed')) or 'no row'}; the map's unclear gate rows are "
                                      f"{sorted(unclear_rows) or 'none'}"))
    met = ids("met") | ids("none failed")
    if met != met_rows:
        problems.append(("judgement", f"the hard-gates line gives {sorted(met) or 'no row'} as met; the map's "
                                      f"other gate rows are {sorted(met_rows) or 'none'}"))
    if "met" in clauses and "none failed" in clauses:
        problems.append(("form", "when none failed, the met rows sit in \"none failed (…)\", not a met: clause"))
    # Each failed and each unconfirmed row carries a few of its Requirement's own
    # words in parentheses, by the fit ledger's naming rule (names_requirement); the
    # conflict itself belongs in what would change this, not here.
    for kind in ("failed", "unconfirmed"):
        for rid, fit, words in clauses.get(kind) or []:
            requirement = gate.get(rid, {}).get("requirement", "")
            if words is None:
                problems.append(("form", f"the hard-gates line's {kind} {rid} carries no Requirement words "
                                         f"in parentheses"))
            elif not names_requirement(words, requirement):
                problems.append(("form", f"the hard-gates line names {kind} {rid} \"{words}\" in words its "
                                         f"Requirement cell does not use (the conflict goes in what would change "
                                         f"this)"))
    for kind in ("met", "none failed"):
        for rid, fit, words in clauses.get(kind) or []:
            if fit is None:
                problems.append(("form", f"the hard-gates line gives met {rid} without its fit in backticks"))
    return problems


# --- Severity (rule 5) --------------------------------------------------------------

SEVERITY_ATTACHED = re.compile(r"(?<![A-Za-z])(" + RISK_ID + r")\s*\(\s*`severity:\s*([a-z]+)`\s*\)", re.I)


def _cells(line: str) -> list[str]:
    body = line.strip()
    body = body[1:] if body.startswith("|") else body
    body = body[:-1] if body.endswith("|") else body
    return [c.strip() for c in body.split("|")]


def register_severities(text: str) -> dict[str, str] | None:
    """The risk register's Severity cell per RR ID, from the first table with # and
    Severity columns whose rows are RR IDs; None when there is no such table."""
    lines = text.splitlines()
    for i in range(len(lines) - 1):
        if not lines[i].lstrip().startswith("|") or not re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]):
            continue
        header = [_token(c) for c in _cells(lines[i])]
        if "#" not in header or "severity" not in header:
            continue
        cid, csev = header.index("#"), header.index("severity")
        found: dict[str, str] = {}
        for line in lines[i + 2:]:
            if not line.lstrip().startswith("|"):
                break
            cells = _cells(line)
            rid = _token(cells[cid]).upper() if cid < len(cells) else ""
            if re.fullmatch(RISK_ID, rid):
                found[rid] = _token(cells[csev]) if csev < len(cells) else ""
        if found:
            return found
    return None


def severity_problems(snapshot: str, register: dict[str, str]) -> list[tuple[str, str]]:
    """Every `severity: x` the snapshot writes is its register entry's, and the severe
    red flags line names exactly the `severity: high` entries, or says "none found".

    Returns (kind, problem) pairs, kinds as gates_line_problems.
    """
    problems: list[tuple[str, str]] = []
    for hit in SEVERITY_ATTACHED.finditer(snapshot):
        rid, level = hit.group(1).upper(), hit.group(2).lower()
        if rid not in register:
            problems.append(("judgement", f"snapshot gives {rid} `severity: {level}`; {rid} is not in the risk register"))
        elif register[rid] != level:
            problems.append(("judgement", f"snapshot gives {rid} `severity: {level}`; the register says "
                                          f"{register[rid] or 'nothing'}"))
    high = {rid for rid, level in register.items() if level == "high"}
    found = slot_lines(snapshot, "severe red flags")
    if not found:
        return problems + [("slot", "the snapshot has no **Severe red flags:** line")]
    if len(found) > 1:
        return problems + [("slot", f"the snapshot has {len(found)} **Severe red flags:** lines; the rule is one")]
    body = found[0].group(1)
    named = {r.upper() for r in re.findall(r"(?<![A-Za-z])(" + RISK_ID + r")\b", body)}
    none_found = re.search(r"\bnone found\b", body, re.I) is not None
    if named != high:
        problems.append(("judgement", f"the severe-red-flags line names {sorted(named) or 'no entry'}; the "
                                      f"register's `severity: high` entries are {sorted(high) or 'none'}"))
    if none_found != (not high):
        problems.append(("judgement", "the severe-red-flags line says \"none found\" while the register has a "
                                      "`severity: high` entry" if none_found else
                                      "the register has no `severity: high` entry, and the severe-red-flags "
                                      "line does not say \"none found\""))
    tokened = {m.group(1).upper() for m in SEVERITY_ATTACHED.finditer(body)}
    for rid in sorted(named - tokened):
        problems.append(("form", f"the severe-red-flags line names {rid} without its full token, "
                                 f"{rid} (`severity: high`)"))
    return problems
