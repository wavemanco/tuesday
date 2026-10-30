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
- a statement about a set of map rows names every row of it, exactly, and an
  exclusive quantifier fails whatever it names — job-underwriter
  references/evidence-model.md, "The row is the unit" (its quoted lists are the
  rule's words; INCLUSIVE, EXCLUSIVE and AFTER_LEDGER_ONLY hold exactly them, list by
  list, as rule_quantifier_scopes() reads them, and CI checks that they do); how
  prose is read for it (years, map words that are also ordinary English, row names,
  articles, parentheses) is stated once, above MAP_WORDS, and how a claim is judged
  against the map's rows, above Claim (set_claims);
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
from dataclasses import dataclass

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
# requirements, a fit, the rows below `direct` as "gaps", a gap type, the candidate's
# constraints (CONSTRAINT_WORDS says when), or the candidate claims the rows hold. How the prose is read, stated once here for every
# check that reads it:
#
# - Some map words are also ordinary English: important, preferred, direct, absent
#   and singular gate and gap. Each is a map word wherever it stands, except before
#   one of its ordinary heads, a closed list (_ORDINARY_HEADS): "a gap analysis", "a
#   gap year", "two direct reports", "one direct conversation", "two important
#   unknowns", and "absent" before a determiner, where it is a preposition ("absent a
#   reference"); or as the first word of a "-to-" compound ("direct-to-consumer").
#   Because the list is closed, a word not on it leaves the map word a map word:
#   "every gate checks out", "neither gate applies", "two direct hits", "five
#   important skills" all count. A token in backticks (`important`) is a map word
#   before anything. The words that are never ordinary English — must-have, hard
#   gate, requirement, row, adjacent, unclear, hard_gate_fail, and the plurals gates
#   and gaps — are map words wherever they stand ("two gates fail outright").
# - "N of M" and a fraction ("4/7", "four out of seven") are a count over the map in
#   three cases. A map word follows in reach (MAP_COUNT: "4/7 direct", "five of seven
#   material requirements"). A requirement or fit noun follows, which it counts whatever
#   stands before it ("5 of 7 skills", "a 5/7 fit"; _RATIO_NOUN). Or the ratio ends its
#   clause (_RATIO_ENDS) — end of text or punctuation ("Fit: 4 of 7.", "6 of 7, with R4
#   open"), a linking or auxiliary verb ("Six of nine look solid"), a verb a fit or a
#   gate takes ("5 of 7 hold"), or a past participle or listed predicate adjective with
#   no noun after it for it to modify ("5 of 7 covered", "4 of 7 met by the CV", "5/7
#   strong."; not "one of seven bundled functions"), an adverb in -ly allowed before any
#   of these ("5 of 7 solidly evidenced") — and the words before it do not mark it as a
#   figure (_RATIO_FIGURE): a possessive ("her 3 of 5"), a ranking verb ("ranked 1 of
#   40", "scored 4/5"), or, written with a slash, a date word ("Start date 3/15 is
#   fixed", "from 3/15"). An article marks nothing ("Fit is a 5 of 7." counts). Followed
#   by anything else — another noun ("one of two openings", "3 of 5 years", "3 of 5
#   launches"), a preposition or an article ("ranked 1 of 40 in the cohort", "2 of 3 on
#   the panel") — it is a figure, which the rule leaves alone; so is one whose first
#   number exceeds its second ("24/7", "2024/25"). That is RATIO, read through map_claim
#   with everything else here. In the one sentence after the ledger every ratio RATIO
#   reads, first number no larger than its second, is read as a count of rows wherever
#   it stands and whatever it counts (after_ledger_claim), and judged as one; a date
#   and "24/7" are not ratios there either.
# - A year is not a count: "February 2027" never counts rows (_COUNT).
# - A count does not reach a singular map noun named by a row ID: "round 2 of the
#   interviews, and the R8 gate" names R8's gate and counts nothing (MAP_COUNT only; a
#   quantifier such as "only the R4 gap" still picks rows out).
# - "a"/"an" opens a new noun phrase, so a count or quantifier does not reach past it
#   to a map word ("the one question a hard gate may ask") unless only a row ID or a
#   linking verb stands between ("two have a gap", "only R4 has a gap" still count).
# - A count inside a parenthesis does not reach a map word outside it: "(mentor two
#   juniors) is `unclear`" counts juniors (_hits).
_ORDINARY_HEADS = {
    "compound": r"analys[ie]s|years?|agents?|fees?",
    "adjective": (r"reports?|mentees?|conversations?|contacts?|messages?|lines?|managers?|quotes?|questions?|"
                  r"unknowns?|caveats?|evidence|experience|"
                  # the register's, the upgrade menu's and the candidate's own nouns: a
                  # count of these counts entries, actions or facts, never map rows
                  r"risks?|concerns?|signals?|red\s+flags?|flags?|points?|emails?|calls?|hires?|roles?|"
                  r"locations?|sales|competitors?"),
    "preposition": r"an?|the|any|such|further|more|other|some|his|her|their|its",
}


def _map_word(word: str, heads: str) -> str:
    """`word` read as a map word: as a token in backticks, or anywhere but before one
    of its ordinary heads or as the first word of a "-to-" compound."""
    return (r"(?:(?<=`)" + word + r"\b|" + word + r"\b(?!-to-)(?!(?:\s+|-)(?:"
            + _ORDINARY_HEADS[heads] + r")\b))")


TIER_WORDS = (r"(?:hard[_ -]?gates?|must[_ -]?haves?|requirements?|rows?|gates|"
              + _map_word(r"(?:important|preferred)", "adjective") + r"|" + _map_word("gate", "compound") + r")")
# The candidate's hard constraints and non-negotiables. They are an input
# (candidate_constraints), not a tier: each one the role's terms touch is carried by
# a `hard_gate` row, but the JD's own gate terms are gate rows too, so a set of them
# is a set of gate rows and not the gate tier — one this module cannot resolve
# (class_of), like a gap type. And saying they were not given ("no constraints were
# stated", "none of your non-negotiables was named") says nothing about the map's
# rows. So they are map words except in a clause that says they were not given
# (_NOT_GIVEN: a negation and a verb of giving), and never in "no <tier>".
CONSTRAINT_WORDS = r"(?:hard[_ -]?constraints?|constraints?|non[_ -]?negotiables?)"
_NOT_GIVEN = (re.compile(r"\b(?:no|none|not|never|without)\b|n't\b", re.I),
              re.compile(r"\b(?:stat(?:e|es|ed|ing)|gave|give|gives|given|giving|nam(?:e|es|ed)|provid\w*|mention\w*|"
                         r"list(?:s|ed)?|specif\w*|shar(?:e|es|ed)|offer(?:s|ed)?|volunteer\w*|rais(?:e|es|ed))\b", re.I))
FIT_WORDS = (r"(?:adjacent|unclear|hard[_ -]?gate[_ -]?fails?|" + _map_word("direct", "adjective") + r"|"
             + _map_word("absent", "preposition") + r")")
# A gap type the map's Gap column carries, and the candidate claims its rows hold: a
# set of either is a set of rows, though not one this module can resolve (class_of).
GAP_TYPES = r"(?:capability|transferability|(?<=`)(?:presentation|discovery)\b)"
MAP_WORDS = (r"(?:" + TIER_WORDS + r"|" + FIT_WORDS + r"|gaps|" + _map_word("gap", "compound") + r"|" + GAP_TYPES
             + r"|" + CONSTRAINT_WORDS + r"|candidate(?:'s|’s)?\s+claims)")
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
    r"(?P<q>" + _COUNT + r"(?:\s+of)?(?:\s+(?:the|my|its|these|those|our|your|their))?(?:\s+" + _NUMBER + r"\b)?"
    + r"|" + FRACTION.pattern + r")" + r"(?:" + _REACH + r")?(?P<w>" + _COUNTED_MAP_WORDS + r")\b", re.I)

# The quantifiers of the rule, in evidence-model.md's own lists ("The row is the
# unit"), which state them once, in three scopes. INCLUSIVE may stand over a set of
# rows the sentence names, and then it is judged against the map (set_claims);
# EXCLUSIVE fails whatever it names, because it speaks for the rows it does not
# name; AFTER_LEDGER_ONLY, a bare "none", is exclusive in the one sentence after the
# fit ledger only, because the slots elsewhere require "none failed" and "none
# found", and the token `none` in backticks is a band or a gap type, never a
# quantifier. ci/check_skills.py holds each scope to the lists as
# rule_quantifier_scopes() reads them, so a word added to any of them there fails CI
# until it is added here.
INCLUSIVE = ("N of M", "every", "all", "each of", "none of", "both", "neither", "no `must_have` row")
EXCLUSIVE = ("only", "the one", "the rest", "no other", "any other", "none of the others", "all but")
AFTER_LEDGER_ONLY = ("none",)
QUANTIFIERS = INCLUSIVE + EXCLUSIVE + AFTER_LEDGER_ONLY


def _phrase(phrase: str) -> str:
    """One word of the lists as a pattern, in any sense: what the sentence after the
    ledger may hold only as the rule allows."""
    if phrase == "N of M":
        # The list's "N of M" as words; the slash and "out of" forms are read through
        # RATIO, which knows a date and "24/7" are not ratios.
        return COUNTED.pattern
    if phrase == "no `must_have` row":
        # Any tier or rows, in any spelling: "no must-have", "no `hard_gate` row".
        return r"\bno\s+[`*_]*" + TIER_WORDS + r"\b"
    if phrase == "none":
        return r"(?<!`)\bnone\b(?!`)(?!\s+of\b)"
    if phrase == "none of":
        return r"\bnone\s+of\b(?!\s+the\s+others?\b)"
    if phrase == "all":
        return r"\ball\b(?!\s+(?:but|except)\b)"
    if phrase == "all but":
        # "all but R4", "all except", and "every must-have but R4": an exception
        # speaks for every row of the set it leaves unnamed.
        return (r"\ball\s+(?:but|except)\b|\bevery\s+(?:[\w`'-]+\s+){0,5}?(?:but|except)(?=\s+(?:for\s+)?"
                + ROW_ID + r"\b)")
    return r"\b" + r"\s+".join(map(re.escape, phrase.split())) + r"\b"


def rule_quantifiers(evidence_model: str) -> list[str]:
    """Every quoted quantifier in evidence-model.md's "The row is the unit" bullet,
    in all three scopes. For a drift check. Returns [] when the bullet or its lists
    cannot be found, which a caller should treat as a failure."""
    return [q for scope in rule_quantifier_scopes(evidence_model) for q in scope]


# Where evidence-model.md's exclusive list turns from the whole map to the one
# sentence after the ledger: "— and in the one sentence after the snapshot's fit
# ledger, … a bare "none" too."
SCOPE_TURN = re.compile(r"\bin the one sentence after\b[^\"]*")


def rule_quantifier_scopes(evidence_model: str) -> tuple[list[str], list[str], list[str]]:
    """evidence-model.md's lists in their three scopes: (the inclusive quantifiers,
    the exclusive ones, the further ones it makes exclusive in the sentence after
    the fit ledger only). For the drift check that holds them to INCLUSIVE,
    EXCLUSIVE and AFTER_LEDGER_ONLY. All empty when the bullet or a list cannot be
    found."""
    bullet = next((line for line in evidence_model.splitlines()
                   if line.lstrip("- ").startswith("**The row is the unit")), "")
    inclusive = re.search(r"\binclusive quantifiers\b[^:]*:\s*(.*?)\.(?:\s|$)", bullet)
    exclusive = re.search(r"\bexclusive quantifiers\b[^:]*:\s*(.*?)\.(?:\s|$)", bullet)
    if not inclusive or not exclusive:
        return [], [], []
    turn = SCOPE_TURN.search(exclusive.group(1))
    cut = turn.start() if turn else len(exclusive.group(1))
    return (re.findall(r'"([^"]+)"', inclusive.group(1)),
            re.findall(r'"([^"]+)"', exclusive.group(1)[:cut]),
            re.findall(r'"([^"]+)"', exclusive.group(1)[cut:]))


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


# "N of M", "N out of M" and "4/7" (not a date's "10/16/2026", not a decimal). They
# count the map only as the comment above MAP_WORDS says: ending their clause
# (_RATIO_ENDS) and not marked as a figure (_RATIO_FIGURE), or with a map word in
# reach, which MAP_COUNT reads.
RATIO = re.compile(r"\b(" + _NUMBER + r")\s+(?:out\s+)?of\s+(" + _NUMBER + r")\b|(?<![\d/.,])\b(\d+)\s*/\s*(\d+)\b"
                   r"(?!\s*/\s*\d|[.,]\d)", re.I)
# What may follow a ratio that ends its clause. A participle or a predicate adjective
# ends it only where the clause goes on after it with no noun for it to modify: "5
# of 7 covered, R4 open", "4 of 7 met by the CV", but not "one of seven bundled
# functions" or "0 of 5 budgeted searches", where it is the noun's adjective.
_PUNCT_END = r"\s*(?:-(?!\w)|[^\w\s-]|\Z)"
_CLAUSE_GOES_ON = (r"(?:" + _PUNCT_END + r"|\s+(?:\w+ly|by|in|on|at|to|for|from|with|under|against|across|through|"
                   r"per|via|as|than|and|or|but|nor|while|since|because|if|unless|though|although|yet|so|a|an|the|"
                   r"now|already|still|outright|overall|too|here|there|today|again|enough|" + ROW_ID + r")\b)")
_RATIO_ENDS = re.compile(
    _PUNCT_END + r"|\s+(?:\w+ly\s+)?(?:"
    # a linking or auxiliary verb, or a conjunction that ends the clause
    r"(?:is|are|was|were|be|been|being|look|looks|seem|seems|remain|remains|stand|stands|stay|stays|sit|sits|"
    r"read|reads|have|has|had|would|will|can|could|may|might|must|should|do|does|did|and|or|but|nor|"
    # a verb a fit or a gate takes
    r"meets?|fail|fails|pass|passes|holds?|blocks?|clears?|matters?|closes?|carry|carries|survives?|lacks?|"
    r"needs?|check|apply|applies|land|lands)\b(?!-\w)"
    # a past participle or a predicate adjective, with the clause going on after it
    # (a listed set: an arbitrary past tense — "4 of 5 renewed", "3 of 4 shipped" — is
    # the candidate's own figure, which the rule leaves alone)
    r"|(?:met|unmet|covered|confirmed|satisfied|evidenced|cleared|established|supported|demonstrated|"
    r"addressed|matched|verified|held|shown|proven|known|seen|left|done|given|open|outstanding|remaining|strong|solid|"
    r"clear|weak|thin|sound|firm|fine|good)\b(?!-\w)" + _CLAUSE_GOES_ON + r")", re.I)
# A requirement or fit noun after a ratio is what it counts ("5 of 7 skills", "a 5/7
# fit"), whatever stands before it.
_RATIO_NOUN = re.compile(r"\s+(?:ones?|rows?|requirements?|tiers?|items?|skills?|qualifications?|criteri(?:on|a)|"
                         r"dut(?:y|ies)|responsibilit(?:y|ies)|asks?|terms?|conditions?|fits?|match(?:es)?)\b(?!-\w)",
                         re.I)
_RATIO_FIGURE = re.compile(
    r"\b(?:his|her|their|my|its|ranked|ranks|ranking|placed|finished|came|scored|scores|rated|graded)\s+$", re.I)
_DATE_WORD = re.compile(
    r"\b(?:date|dated|on|by|from|until|till|through|before|after|since|starts?|starting|started|begins?|"
    r"beginning|began|due|deadline|closes?|closing|closed|ends?|ending|ended|effective)\s+$", re.I)


def _number(word: str) -> int:
    return int(word) if word.isdigit() else COUNT_WORDS[word.lower()]


def _ratios(text: str) -> list[re.Match]:
    """Every RATIO that counts rows by itself: its first number no larger than its
    second, ending its clause, and not marked as a figure by the words before it."""
    out = []
    for hit in RATIO.finditer(text):
        slashed = hit.group(3) is not None
        n, m = (hit.group(3), hit.group(4)) if slashed else (hit.group(1), hit.group(2))
        before = text[max(0, hit.start() - 40):hit.start()]
        if _number(n) > _number(m):
            continue
        if _RATIO_NOUN.match(text, hit.end()) or (
                _RATIO_ENDS.match(text, hit.end()) and not _RATIO_FIGURE.search(before)
                and not (slashed and _DATE_WORD.search(before))):
            out.append(hit)
    return out


def _all_ratios(text: str) -> list[re.Match]:
    """Every ratio RATIO reads, its first number no larger than its second, wherever it
    stands and whatever it counts: how the sentence after the ledger reads a ratio,
    as a count of rows. A date ("10/16/2026") and "24/7" are not ratios here either."""
    return [h for h in RATIO.finditer(text)
            if _number(h.group(3) or h.group(1)) <= _number(h.group(4) or h.group(2))]


# --- Set claims ----------------------------------------------------------------------
#
# The rule (evidence-model.md, "The row is the unit"): a statement about a set of map
# rows names every row of the set by ID, in the same sentence; named, it may count or
# quantify, and the rows it names and any number it gives are exactly the map's rows
# for the set it describes, and what it says of them is true of each; unnamed, it
# fails even when accurate; and an exclusive quantifier fails whatever it names. How
# a sentence is read for it, and in what order it is judged:
#
# - A claim is a word of the lists or a count over the map, read as the comment above
#   MAP_WORDS says: an inclusive word or a count with a map word in reach, an
#   exclusive word with a map word in reach or standing directly over a row ID ("only
#   R1–R5", "only the R4 and R5 rows" — not "only the employer can change R1", where
#   "only" restricts something that is not a row), "all but" and "every … but R4"
#   anywhere, and a ratio that counts rows (_ratios). In the one sentence after the
#   fit ledger, which is about the map by construction, every word of the lists and
#   every ratio is a claim wherever it stands (after_ledger=True), a bare "none" an
#   exclusive one.
# - 1. Every claim, with or without the map's rows: an exclusive word fails; a claim
#   whose sentence names no row ID fails; a count that gives more rows than the
#   sentence names fails. That is all the functions check without the map, which no
#   CI or harness caller does.
# - 2. With the map's rows ({id: (priority, fit)}): a row ID the map lacks fails (a
#   split row's parent ID, "R4" for R4a and R4b, names neither row). Then the set the
#   claim describes follows its subject, the one reading evidence-model.md states:
#   - Over row IDs — the quantifier stands right after the IDs, a linking or
#     auxiliary verb allowed between ("R1 and R2 both fail", "R3 and R4 are both
#     `direct`", "R1 and R2, both hard gates, fail"), or the IDs right after it ("both
#     R4 and R5", "none of R4, R5"): its set is those rows and no others. "both" and
#     "neither" stand over exactly two; and what the words after the quantifier say of
#     them, where those words are the map's (_said: a tier, a fit, "below `direct`",
#     "fail"), is true of each ("neither", "none of": of none).
#   - Over a noun ("every must-have", "two hard gates", "four of the seven
#     requirements"): its set is everything its noun says, read from the quantifier
#     through the noun (_NOUN_TAIL) — a map word before the noun narrows it ("both
#     failed hard gates" is the gate rows at hard_gate_fail), two tiers joined are both
#     ("every hard gate and must-have"). Every row of that class is named in the
#     sentence, and "both"/"neither" say its size is two. What the clause then says of
#     it (_said, after the noun) is true of each named row — "every must-have — R1,
#     R2, R3, R4 — is `direct`" fails where R4 is `unclear`, as the count "four
#     must-haves are `direct`" does. A count counts the rows its predicate is true of:
#     "two hard gates fail" is the gate rows at hard_gate_fail, its number their
#     number. In "N of M <noun>" the noun is the set M is drawn from ("two of the five
#     gaps"), and N the rows of it the predicate is true of; with no noun after the
#     fit ("4/7 direct", "four of seven `direct`"), M is every row and the fit is what
#     N says.
#   - Over neither — a quantifier or count with no noun and no IDs ("both fail",
#     "two are `direct`"): a quantifier refers back to rows the sentence names, and is
#     the grader's; a count's set is what its clause says of it ("two have a gap" is
#     the rows below `direct`).
# - 3. Where the set does not resolve — a gap type, the candidate's claims or
#   constraints, a fit or tier the clause says in other words ("two must-haves look
#   strong", "every gap that matters"), a noun narrowed by a word that is not the
#   map's ("every open must-have") or by a relative clause ("hard gates you fail"),
#   two fits — step 1 still applies, and the IDs that name it stand in its own clause
#   (_clause: an ID in another clause of the sentence is about something else);
#   whether it is exact is the grader's. A count over such a set still names at least
#   as many rows of the noun's class as it gives. Whatever the sentence says of its
#   rows in words that are not the map's ("has evidence", "is met") is the grader's to
#   judge true.

@dataclass
class Claim:
    """A count or quantifier over the map, as read in one sentence. `why` is the
    problem when it breaks the rule, "" when it holds; `kind` is "inclusive",
    "exclusive", "count" or, from after_ledger_claim alone, "sentence"."""
    text: str
    kind: str
    sentence: str
    why: str = ""


_ROW_NAMED = re.compile(r"(?<![A-Za-z])(" + ROW_ID + r")\b")
_ID_LIST = ROW_ID + r"(?:\s*(?:,|and|&|or|nor)\s*(?:and\s+|or\s+)?" + ROW_ID + r")*"
_FLOATS = ("both", "all", "each of", "neither")
# IDs right before a quantifier, a linking or auxiliary verb allowed between.
_FLOATING = re.compile(r"(?<![A-Za-z])" + _ID_LIST + r",?\s*(?:(?:are|were|is|was|do|did|have|had|will|would|can|"
                       r"could|must|should|may|might)\s+)?$")
# IDs right after one: "both R4 and R5", "none of R4, R5", "neither R1 nor R2".
_IDS_AFTER = re.compile(r"\s*(?:of\s+)?(?:the\s+)?(?:rows?\s+)?(?<![A-Za-z])(" + _ID_LIST + r")\b")
_NEGATIVE = ("none of", "neither", "no `must_have` row")
_LINK_VERB = re.compile(r"\b(?:is|are|was|were|has|have|had|carry|carries|show|shows|need|needs|sits?)\b", re.I)
# The rest of a claim's noun: more map words or a neutral head ("rows", "fits", "hits"),
# "below `direct`", "at `adjacent`", and a second tier joined to the first.
_NOUN_TAIL = re.compile(r"(?:[\s`*_-]+(?:(?:at|below)\s+`?\w+`?|ones?\b|fits?\b|match(?:es)?\b|items?\b|hits?\b|"
                        r"(?:and|or)\b(?=[\s`*_]+" + TIER_WORDS + r")|" + MAP_WORDS + r"))*", re.I)
# A run of row IDs set off inside a clause — "every must-have — R1, R2 — is direct",
# "two must-haves, R4 and R5, sit below" — is the naming, not the predicate.
_ID_RUN = re.compile(r"\s*[—–(,]?\s*(?<![A-Za-z])" + ROW_ID + r"(?:\s*(?:,|and|&)\s*(?:and\s+)?" + ROW_ID
                     + r")*\s*[—–),]?", re.I)
_CLAUSE_END = re.compile(r"[;:.!?(—–·]|,\s*(?:and|but|or|so|while|though|although|because|with|which|since)\b", re.I)
# Where one clause of a sentence gives way to the next, for which IDs stand with a
# claim: a semicolon, or a comma and a conjunction. A colon, a dash or a parenthesis
# sets the naming off inside the clause, and does not end it.
_CLAUSE_BREAK = re.compile(r";|,\s*(?:and|but|or|so|yet|while|though|although|because|since|whereas)\b", re.I)
# The words a claim's set or predicate may hold and still be the map's: map words,
# neutral heads and "at"; in a noun, determiners, possessives, numbers, "of" and
# "material" (the v0.1 measurement's word for the map's rows); in a predicate,
# linking verbs, articles and relative pronouns. Any other word is one the map cannot
# read, and leaves the set or the predicate to the grader.
_MAP_TOKEN = (r"hard|gates?|must|haves?|important|preferred|requirements?|rows?|ones?|fits?|match(?:es)?|items?|hits?|"
              r"direct|directly|adjacent|unclear|absent|hard_gate_fail|hard_gate|must_have|below|gaps?|"
              r"fail|fails|failed|failing|at")
_NOUN_TOKEN = re.compile(r"(?:" + _MAP_TOKEN + r"|the|a|an|of|my|your|his|her|their|its|our|these|those|material|"
                         r"and|or|" + _NUMBER + r")", re.I)
_SAID_TOKEN = re.compile(r"(?:" + _MAP_TOKEN + r"|is|are|was|were|be|been|sit|sits|stand|stands|read|reads|remain|"
                         r"remains|land|lands|rate|rated|rates|has|had|carry|carries|a|an|the|that|which|who|both|all|"
                         r"each|outright)", re.I)
# A relative clause right after a noun narrows it: "every gap that matters", "both
# hard gates you fail".
_RELATIVE = re.compile(r"\s*(?:that|which|who|whom|whose|you|he|she|they|we|I)\b")
# A range writes two IDs and names only them.
_RANGE = re.compile(r"(?<![A-Za-z])" + ROW_ID + r"\s*(?:[–-]|\s(?:through|to)\s)\s*(?:" + ROW_ID + r"|[a-z]\b)")

# What a claim's words resolve to (class_of): the tier, the fit, or the rows below
# `direct`. Read in this order, each match removed, so "hard_gate_fail" is a fit
# and not a tier, and "below `direct`" is not `direct`.
_BELOW = re.compile(r"\bbelow\s+`?direct`?|\bgaps?\b", re.I)
_FAILED = re.compile(r"\bhard[_ -]?gate[_ -]?fails?\b|\bfail(?:s|ed|ing)?\b", re.I)
_FITS = {fit: re.compile(r"\b" + fit + r"(?:ly)?\b(?!-to-)", re.I) for fit in ("direct", "adjacent", "unclear", "absent")}
_TIERS = (("hard_gate", re.compile(r"\bhard[_ -]?gates?\b|\bgates?\b", re.I)),
          ("must_have", re.compile(r"\bmust[_ -]?haves?\b", re.I)),
          ("important", re.compile(r"\bimportant\b", re.I)),
          ("preferred", re.compile(r"\bpreferred\b", re.I)),
          ("*", re.compile(r"\brequirements?\b|\brows?\b", re.I)))
_UNRESOLVED = re.compile(r"\b(?:capability|transferability|presentation|discovery)\b|\bcandidate(?:'s|’s)?\s+claims\b|"
                         r"\b" + CONSTRAINT_WORDS + r"\b", re.I)

def class_of(words: str) -> tuple[str | None, str | None] | None:
    """(tier, fit) the words give, "*" for every tier, two tiers joined as "a+b",
    and "below" for every fit but `direct`; None when they give no class, or one
    this module cannot resolve."""
    text = words.replace("`", " ")
    if _UNRESOLVED.search(text):
        return None
    fits = set()
    if _BELOW.search(text):
        fits.add("below")
        text = _BELOW.sub(" ", text)
    if _FAILED.search(text):
        fits.add("hard_gate_fail")
        text = _FAILED.sub(" ", text)
    fits |= {fit for fit, pattern in _FITS.items() if pattern.search(text)}
    tiers = [tier for tier, pattern in _TIERS if pattern.search(text)]
    if len(tiers) > 1 and "*" in tiers:
        tiers.remove("*")
    specific = fits - {"below"}
    if len(specific) > 1 or (not tiers and not fits):
        return None
    fit = next(iter(specific)) if specific else ("below" if fits else None)
    if fit == "direct" and "below" in fits:
        return None
    return ("+".join(tiers) if tiers else None), fit


def class_rows(cls: tuple[str | None, str | None], rows: dict[str, tuple[str, str]]) -> set[str]:
    tier, fit = cls
    return {rid for rid, (priority, row_fit) in rows.items()
            if (tier in (None, "*") or priority in tier.split("+"))
            and (fit is None or row_fit == fit or (fit == "below" and row_fit != "direct"))}


def _merge(a, b):
    """One class that is both a and b, or None when they cannot both hold."""
    if a is None or b is None:
        return a or b
    (ta, fa), (tb, fb) = a, b
    if ta in (None, "*") or ta == tb:
        tier = tb if tb is not None else ta
    elif tb in (None, "*"):
        tier = ta
    else:
        return None
    if fa is None or fa == fb:
        fit = fb
    elif fb is None:
        fit = fa
    elif fa == "below" and fb != "direct":
        fit = fb
    elif fb == "below" and fa != "direct":
        fit = fa
    else:
        return None
    return tier, fit


def _describe(cls: tuple[str | None, str | None]) -> str:
    tier, fit = cls
    words = [] if tier in (None, "*") else [tier.replace("+", " and ")]
    words += [] if fit is None else ["below `direct`" if fit == "below" else f"`{fit}`"]
    return " ".join(words) or "every"


def _rows_of(rows) -> dict[str, tuple[str, str]] | None:
    """The map's rows as {id: (priority, fit)}, from that or from {id: {"priority",
    "fit", …}}, the shape both checkers already hold."""
    if rows is None:
        return None
    out = {}
    for rid, row in rows.items():
        priority, fit = (row.get("priority", ""), row.get("fit", "")) if isinstance(row, dict) else row
        out[rid] = (_token(priority), _token(fit))
    return out


def _numbers(text: str) -> list[int]:
    return [_number(w) for w in re.findall(r"(?<![\w/.-])" + _NUMBER + r"(?![\w/.-])|\d+", text, re.I)
            if re.fullmatch(_NUMBER, w, re.I)]


def _predicate(sentence: str, at: int) -> str:
    """What the clause says of a claim's set: from `at` to the clause's end, with a
    run of row IDs set off inside it dropped."""
    rest = _ID_RUN.sub(" ", sentence[at:at + 160])
    end = _CLAUSE_END.search(rest)
    return rest[:end.start()] if end else rest


def _said(words: str):
    """What `words` say of rows, read in the map's terms: a class, None when they
    say nothing the map holds, or "unresolved" when they say it in other words."""
    tokens = re.findall(r"[A-Za-z_]+", words)
    if any(not _SAID_TOKEN.fullmatch(t) for t in tokens):
        return "unresolved"
    return class_of(words) if tokens else None


def _clause(sentence: str, at: int) -> str:
    """The clause of `sentence` that holds position `at` (_CLAUSE_BREAK)."""
    start, end = 0, len(sentence)
    for brk in _CLAUSE_BREAK.finditer(sentence):
        if brk.end() <= at:
            start = brk.end()
        elif brk.start() >= at:
            end = brk.start()
            break
    return sentence[start:end]


def _prose_patterns() -> list[tuple[str, str, re.Pattern]]:
    """(phrase, kind, pattern) for the words of the lists read in prose, where a map
    word must be in reach — or, for an exclusive word, a row ID it stands directly
    over. Built from the lists themselves, so the two cannot drift."""
    out = []
    for phrase in INCLUSIVE:
        if phrase in ("N of M",):
            continue
        if phrase == "no `must_have` row":
            out.append((phrase, "inclusive", re.compile(r"(?P<q>\bno)\s+[`*_]*(?P<w>" + TIER_WORDS + r")\b", re.I)))
            continue
        out.append((phrase, "inclusive",
                    re.compile(r"(?P<q>" + _phrase(phrase) + r")(?:" + _REACH + r")?(?P<w>" + MAP_WORDS + r")\b", re.I)))
    for phrase in EXCLUSIVE:
        if phrase == "all but":
            out.append((phrase, "exclusive", re.compile(r"(?P<q>" + _phrase(phrase) + r")(?P<w>)", re.I)))
            continue
        # "only" picks rows out ("the only", "only R4", "only two"); qualifying one
        # row ("only adjacent") it is not a quantifier outside the sentence after the
        # ledger. A row ID counts only right after the word ("only R4", "only the R4
        # and R5 rows"); across other words, only a map word does.
        q = (r"\bthe\s+only\b|\bonly(?=\s+(?:R\d|the\b|" + _NUMBER + r"\b))") if phrase == "only" else _phrase(phrase)
        out.append((phrase, "exclusive", re.compile(r"(?P<q>" + q + r")" + _SEP + r"(?:the\s+)?(?:rows?\s+)?"
                                                     r"(?P<w>(?<![A-Za-z])" + ROW_ID + r")\b", re.I)))
        out.append((phrase, "exclusive", re.compile(r"(?P<q>" + q + r")(?:" + _REACH + r")?(?P<w>" + MAP_WORDS
                                                     + r")\b", re.I)))
    return out


PROSE_QUANTIFIERS = _prose_patterns()
# The sentence after the ledger: every word of the lists, in any sense.
AFTER_LEDGER_WORDS = [(phrase, "inclusive" if phrase in INCLUSIVE else "exclusive", re.compile(_phrase(phrase), re.I))
                      for phrase in QUANTIFIERS if phrase != "N of M"]


def _constraints_only(sentence: str, w_start: int, end: int) -> bool:
    """A claim whose map word is the candidate's constraints, in a clause that says
    they were not given ("no constraints were stated"): not about the map
    (CONSTRAINT_WORDS)."""
    clause = _clause(sentence, w_start)
    return (re.fullmatch(r"[`*_]*" + CONSTRAINT_WORDS + r"[`*_]*", sentence[w_start:end], re.I) is not None
            and all(pattern.search(clause) for pattern in _NOT_GIVEN))


def _hits(sentence: str, after_ledger: bool) -> list[tuple[str, str, int, int, int, int]]:
    """(phrase, kind, start, quantifier end, map-word start, end) per claim in one
    sentence. A count's phrase is "count"; a map-word start equal to the end means no
    map word was read."""
    found: dict[tuple[int, str], tuple] = {}

    def add(phrase, kind, start, q_end, w_start, end):
        key = (start, kind)
        if key not in found or end > found[key][5]:
            found[key] = (phrase, kind, start, q_end, w_start, end)

    for phrase, kind, pattern in PROSE_QUANTIFIERS:
        for hit in pattern.finditer(sentence):
            if hit.group(0).count(")") > hit.group(0).count("("):
                continue                  # a quantifier inside a parenthesis, a map word outside it
            if not _constraints_only(sentence, hit.start("w"), hit.end()):
                add(phrase, kind, hit.start(), hit.end("q"), hit.start("w"), hit.end())
    for hit in MAP_COUNT.finditer(sentence):
        if (hit.group(0).count(")") <= hit.group(0).count("(")
                and not _constraints_only(sentence, hit.start("w"), hit.end())):
            add("count", "count", hit.start(), hit.end("q"), hit.start("w"), hit.end())
    for hit in (_all_ratios(sentence) if after_ledger else _ratios(sentence)):
        add("count", "count", hit.start(), hit.end(), hit.end(), hit.end())
    if after_ledger:
        for phrase, kind, pattern in AFTER_LEDGER_WORDS:
            for hit in pattern.finditer(sentence):
                prose = next((p for ph, k, p in PROSE_QUANTIFIERS if ph == phrase), None)
                full = prose.match(sentence, hit.start()) if prose else None
                if full and full.group(0).count(")") <= full.group(0).count("("):
                    add(phrase, kind, full.start(), full.end("q"), full.start("w"), full.end())
                else:
                    add(phrase, kind, hit.start(), hit.end(), hit.end(), hit.end())
    # An exclusive reading of a span overrides an inclusive one at the same place:
    # "every must-have but R4" is "all but", whatever else "every" is.
    out = sorted(found.values(), key=lambda h: (h[2], h[1] != "exclusive"))
    return out


def _wrong_row(words: str, cls, rows, rid: str, negative: bool) -> str:
    priority, fit = rows[rid]
    return (f"\"{words}\" says {rid} is {'not ' if negative else ''}{_describe(cls)}; the map has {rid} at "
            f"{priority} `{fit}`")


def _leaves_out(words: str, cls, members, missing, sentence: str) -> str:
    why = (f"\"{words}\" describes the map's {_describe(cls)} rows, {sorted(members)}, and the sentence leaves out "
           f"{missing}")
    if _RANGE.search(sentence):
        why += " (a range names only its endpoints: write each row's ID)"
    return why


def _judge(sentence: str, hit: tuple, rows: dict[str, tuple[str, str]] | None) -> Claim:
    phrase, kind, start, q_end, w_start, end = hit
    if sentence[start:end].count("`") % 2 and sentence[end:end + 1] == "`":
        end += 1                          # the closing backtick of a token read as a map word
    words = sentence[start:end]
    claim = Claim(text=words, kind=kind, sentence=sentence)
    # 1. With or without the map.
    if kind == "exclusive":
        claim.why = f"\"{words}\" is an exclusive quantifier: it speaks for the rows it does not name"
        return claim
    named = set(_ROW_NAMED.findall(sentence))
    if not named:
        claim.why = f"\"{words}\" is a set claim over the map that names no row"
        return claim
    counted = _numbers(sentence[start:max(w_start, q_end)]) if kind == "count" else []
    if counted and len(named) < counted[0]:
        claim.why = f"\"{words}\" counts {counted[0]} rows, and the sentence names {len(named)}: {sorted(named)}"
        return claim
    if rows is None:
        return claim
    # 2. With the map.
    unknown = sorted(named - set(rows))
    if unknown:
        split = {u: sorted(r for r in rows if re.fullmatch(re.escape(u) + "[a-z]", r)) for u in unknown}
        parent = next((u for u in unknown if split[u]), None)
        claim.why = (f"\"{words}\" names {parent}, which the map splits into {split[parent]}: a split row is two rows"
                     if parent else f"\"{words}\" sits in a sentence naming {unknown}, which the map does not have")
        return claim
    has_noun = w_start < end
    tail = _NOUN_TAIL.match(sentence, end)
    noun_end = tail.end() if tail and has_noun else (end if has_noun else q_end)
    between = sentence[q_end:w_start] if has_noun else ""
    negative = phrase in _NEGATIVE

    # Over row IDs: the set is those rows.
    over = None
    if kind != "count":
        floating = _FLOATING.search(sentence[:start]) if phrase in _FLOATS else None
        after = None if floating else _IDS_AFTER.match(sentence, q_end)
        if floating:
            over, said_from = floating.group(0), q_end
        elif after:
            over, said_from = after.group(1), after.end()
    if over is not None:
        ids = _ROW_NAMED.findall(over)
        if phrase in ("both", "neither") and len(ids) != 2:
            claim.why = f"\"{words}\" says two, and it stands over {len(ids)} rows: {ids}"
            return claim
        said = [s for s in (_said(sentence[said_from:max(noun_end, said_from)]),
                            _said(_predicate(sentence, max(noun_end, said_from)))) if isinstance(s, tuple)]
        cls = _merge(*said) if len(said) == 2 else (said[0] if said else None)
        if cls is not None:
            members = class_rows(cls, rows)
            bad = [r for r in ids if (r in members) == negative]
            if bad:
                claim.why = _wrong_row(words, cls, rows, bad[0], negative)
        return claim
    if kind != "count" and (not has_noun or _ROW_NAMED.search(between) or _LINK_VERB.search(between)):
        return claim                      # over neither a noun nor IDs: it refers back, and is the grader's

    # Over a noun: the set is everything the noun says.
    pronoun = kind == "count" and _LINK_VERB.search(between)
    noun = "" if pronoun else sentence[q_end:noun_end]
    narrowed = (any(not _NOUN_TOKEN.fullmatch(t) for t in re.findall(r"[A-Za-z_]+", noun))
                or _RELATIVE.match(sentence, noun_end) is not None)
    broad = class_of(noun) if noun.strip() else None
    given = None if narrowed else broad
    said = _said((sentence[q_end:noun_end] + " " if pronoun else "") + _predicate(sentence, noun_end))
    said_cls = said if isinstance(said, tuple) else None
    n = m = None
    cls = m_cls = None
    if kind == "count":
        span = sentence[start:max(w_start, q_end)]
        numbers = _numbers(span) or _numbers(words)
        n = numbers[0] if numbers else None
        ratio = len(numbers) > 1 and re.search(r"\bof\b|/", span) is not None
        m = numbers[1] if ratio else None
        bare = (ratio and given is not None and given[0] is None
                and not re.search(TIER_WORDS + r"|\bgaps?\b", noun, re.I))
        if pronoun:
            cls = said_cls
        elif given is None:
            cls = None
        elif bare:
            # "4/7 direct", "four of seven `direct`": the fit is what N says, M is every row.
            m_cls = ("*", None)
            cls = _merge(given, said_cls) if said != "unresolved" else None
        elif ratio:
            # "two of the five gaps …": the noun is the set M is drawn from.
            m_cls = given
            cls = _merge(given, said_cls) if said_cls else None
        else:
            cls = _merge(given, said_cls) if said_cls else (given if said is None else None)
        drawn = broad or m_cls
        if n is not None and cls is None and drawn is not None and len(named & class_rows(drawn, rows)) < n:
            # The counted rows are rows of the noun's class, whatever is said of them.
            claim.why = (f"\"{words}\" counts {n} of the map's {_describe(drawn)} rows, and the sentence names "
                         f"{sorted(named & class_rows(drawn, rows)) or 'none of them'}")
            return claim
    else:
        cls = given
        n = 2 if phrase in ("both", "neither") else None
    if cls is None and m_cls is None:
        # 3. A set that does not resolve: the IDs that name it stand in its clause.
        if noun.strip() and not _ROW_NAMED.search(_clause(sentence, start)):
            claim.why = f"\"{words}\" is a set claim over the map that names no row in its own clause"
        return claim
    for which, set_cls, number in (("N", cls, n), ("M", m_cls, m)):
        if set_cls is None:
            continue
        members = class_rows(set_cls, rows)
        if which == "N":
            missing = sorted(members - named)
            if missing:
                claim.why = _leaves_out(words, set_cls, members, missing, sentence)
                return claim
        if number is not None and number != len(members):
            claim.why = (f"\"{words}\" gives {number}; the map's {_describe(set_cls)} rows number {len(members)}"
                         + (f": {sorted(members)}" if members else ""))
            return claim
    if kind != "count" and said_cls is not None:
        # What the clause says of the set is true of each row it names.
        members = class_rows(said_cls, rows)
        bad = [r for r in sorted(class_rows(cls, rows)) if (r in members) == negative]
        if bad:
            claim.why = _wrong_row(words, said_cls, rows, bad[0], negative)
    return claim


def set_claims(text: str, rows=None, after_ledger: bool = False) -> list[Claim]:
    """Every count or quantifier over the map in `text`, one sentence at a time, each
    judged by the rule (the comment above). `rows` is the map as {id: (priority,
    fit)} (or {id: {"priority", "fit", …}}); without it, only the comment's step 1 runs.
    `after_ledger` reads `text` as the sentence after the fit ledger."""
    table = _rows_of(rows)
    out = []
    for sentence in sentences(text):
        for hit in _hits(sentence, after_ledger):
            out.append(_judge(sentence, hit, table))
    return out


def map_claim(text: str, rows=None) -> Claim | None:
    """The first count or quantifier over the map that breaks the rule, in any prose
    that reads the map: the snapshot's prose and decision.summary. The one reader
    every check of the rule calls, in CI and in the harness. Counts that are not about
    map rows — the candidate's own figures, "two of three squads", "24/7 on-call",
    the Research tier line — are outside it, and bare "none" is read only after the
    ledger, because the slots require "none failed" and "none found". How the words
    are read is stated once, above MAP_WORDS and above Claim."""
    return next((c for c in set_claims(text, rows) if c.why), None)


def after_ledger_claim(text: str, rows=None) -> Claim | None:
    """What rule 2 forbids after the ledger: a set claim that breaks the rule, every
    word of the lists and every ratio read as about the map wherever it stands (the
    sentence is about the map by construction), a bare "none" exclusive there; or a
    second sentence ("at most one sentence"). For a second sentence the claim is
    that sentence, of kind "sentence"."""
    hit = next((c for c in set_claims(text, rows, after_ledger=True) if c.why), None)
    if hit:
        return hit
    parts = sentences(text)
    if len(parts) > 1:
        rest = text[text.index(parts[1]):]
        return Claim(text=rest, kind="sentence", sentence=rest, why="a second sentence after the ledger")
    return None


def is_second_sentence(text: str, hit: Claim | None) -> bool:
    """Whether after_ledger_claim's hit is the extra-sentence case rather than a
    count or quantifier, so both checkers word the failure the same way."""
    return bool(hit) and hit.kind == "sentence"


def quantifier_in(text: str) -> re.Match | None:
    """Any word of the lists, any ratio and any count over the map, in any sense and
    named or not: what the fit ledger's own lines may not hold, because the ledger is
    a projection and states no count at all (risk-and-decision.md, "The decision
    snapshot")."""
    for _, _, pattern in AFTER_LEDGER_WORDS:
        if (hit := pattern.search(text)):
            return hit
    return next(iter(_all_ratios(text)), None) or MAP_COUNT.search(text)


# The ledger's mark: its label, bold or plain, or a markdown heading that names it
# ("## Fit ledger").
LEDGER_MARK = re.compile(r"^\s*(?:#{1,6}\s+)?[*_]*\s*fit ledger\b", re.I)
# A heading that names one of the snapshot's own slots ("## Opportunity ledger") is
# inside the snapshot: it neither starts nor ends it (snapshot readers use this).
SLOT_HEADING = re.compile(r"^\s*#{1,6}\s+[*_]*\s*(?:fit ledger|opportunity ledger|hard gates|severe red flags|"
                          r"what would change|conditions)\b", re.I)


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
    """The snapshot without the ledger's own lines, table rows and the Research tier
    line (bold or plain), whose counts are the tally's, not the map's."""
    lines = snapshot.splitlines()
    span = ledger_lines_span(lines)
    drop = set(range(*span)) if span else set()
    return "\n".join(line for i, line in enumerate(lines)
                     if i not in drop and not line.lstrip().lstrip("*_").startswith(("|", "Research tier")))


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


# The abbreviations a Requirement's own words are written in, a closed table read on
# both sides of the comparison ("5+ yrs PM" names "5+ years of product management").
# Never initials matching: "(PR)" or "(BI)" names nothing it is not spelled as.
ABBREVIATIONS = {"pm": ("product", "management"), "yrs": ("years",), "yr": ("year",),
                 "mgmt": ("management",), "exp": ("experience",)}
# One spelling per word: partnering and partner, launches and launch, coordination
# and coordinate read alike. The stem keeps three letters or more; a figure ("5+",
# "150k") is kept whole.
_SUFFIXES = ("ations", "ation", "ates", "ate", "ings", "ing", "ions", "ion", "es", "ed", "e", "s")


def lemma(word: str) -> str:
    if re.fullmatch(r"\d+\+?|\d+k", word):
        return word
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def name_words(text: str) -> set[str]:
    """A parenthetical's words, for checking it names its row in the row's own words:
    compared by lemma, through the ABBREVIATIONS table, with "+" and "&" standing
    alone read as "and". Every other word must be the Requirement's, so a gloss or a
    conflict still fails."""
    out = set()
    for w in re.findall(r"[a-z0-9]+\+?|[+&]", text.replace("*", "").replace("`", "").lower()):
        if w in NAME_STOP or w in ("+", "&"):
            continue
        out.update(lemma(part) for part in ABBREVIATIONS.get(w, (w,)))
    return out


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
