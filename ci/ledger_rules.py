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
- a statement about a set of map rows agrees with the map, and in the snapshot and
  decision.summary names every row of it, and a complement fails there whatever it
  names — job-underwriter references/evidence-model.md, "The row is the unit" (its
  quoted lists are the rule's words; NAMED_SET, COMPLEMENT and AFTER_LEDGER_ONLY hold
  exactly them, list by list, as rule_quantifier_scopes() reads them, and CI checks
  that they do); how
  prose is read for it (years, map words that are also ordinary English, row names,
  articles, parentheses) is stated once, above MAP_WORDS, and what the check reads
  of the rule and what it leaves to the grader, above Claim (set_claims);
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
# requirements, a fit, or the rows below `direct` as "gaps". How the prose is read,
# stated once here for every check that reads it:
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
#   reads, first number no larger than its second, is a set claim wherever it stands
#   and whatever it counts (after_ledger_claim); a date and "24/7" are not ratios there
#   either.
# - A year is not a count: "February 2027" never counts rows (_COUNT).
# - A count does not reach a singular map noun named by a row ID: "round 2 of the
#   interviews, and the R8 gate" names R8's gate and counts nothing (MAP_COUNT only; a
#   quantifier such as "only the R4 gap" still picks rows out).
# - "a"/"an" opens a new noun phrase, so a count or quantifier does not reach past it
#   to a map word ("the one question a hard gate may ask") unless only a row ID or a
#   linking verb stands between ("two have a gap", "only R4 has a gap" still count).
# - A count inside a parenthesis does not reach a map word outside it: "(mentor two
#   juniors) is `unclear`" counts juniors (_finds).
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
FIT_WORDS = (r"(?:adjacent|unclear|hard[_ -]?gate[_ -]?fails?|" + _map_word("direct", "adjective") + r"|"
             + _map_word("absent", "preposition") + r")")
# The plural map nouns: a set of rows, never one.
_PLURAL_MAP_NOUNS = r"(?:hard[_ -]?gates|must[_ -]?haves|requirements|rows|gates|gaps)"
MAP_WORDS = r"(?:" + TIER_WORDS + r"|" + FIT_WORDS + r"|gaps|" + _map_word("gap", "compound") + r")"
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

# The words of the rule, in evidence-model.md's own lists ("The row is the unit"),
# which state them once, in three scopes. NAMED_SET, the named-set words, may stand
# over a set of rows the sentence names; COMPLEMENT, the complements, fail whatever
# they name, because they describe a set by the rows they leave out; AFTER_LEDGER_ONLY,
# a bare "none", is a complement in the one sentence after the fit ledger only,
# because the slots elsewhere require "none failed" and "none found", and the token
# `none` in backticks is a band or a gap type, never a quantifier. ci/check_skills.py
# holds each scope to the lists as rule_quantifier_scopes() reads them, so a word
# added to any of them there fails CI until it is added here.
NAMED_SET = ("N of M", "every", "all", "each of", "none of", "both", "neither", "no `must_have` row", "only",
             "the one")
COMPLEMENT = ("the rest", "the others", "everything else", "nothing else", "no other", "any other",
              "none of the others", "all but", "all except")
AFTER_LEDGER_ONLY = ("none",)
QUANTIFIERS = NAMED_SET + COMPLEMENT + AFTER_LEDGER_ONLY
# Where each list starts, in evidence-model.md's bullet and in a grader clause that
# speaks of them: the first "named-set words" and the first plural "complements".
NAMED_SET_MARK = re.compile(r"\bnamed-set words\b", re.I)
COMPLEMENT_MARK = re.compile(r"\bcomplements\b", re.I)


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
    if phrase == "none of the others":
        # "none of the other must-haves" too: it speaks for the rows it does not name.
        return r"\bnone\s+of\s+the\s+others?\b"
    if phrase == "the others":
        # "the other must-haves" too, before a plural map noun; the singular "the other
        # hard gate, R9" names one row and is not read.
        return r"\bthe\s+other(?:s\b|(?=(?:\s+[\w`*-]+){0,2}?\s+[`*_]*" + _PLURAL_MAP_NOUNS + r"\b))"
    if phrase == "all":
        return r"\ball\b(?!\s+(?:but|except)\b)"
    if phrase in ("all but", "all except"):
        return r"\ball\s+" + phrase.split()[1] + r"\b"
    return r"\b" + r"\s+".join(map(re.escape, phrase.split())) + r"\b"


def rule_quantifiers(evidence_model: str) -> list[str]:
    """Every quoted quantifier in evidence-model.md's "The row is the unit" bullet,
    in all three scopes. For a drift check. Returns [] when the bullet or its lists
    cannot be found, which a caller should treat as a failure."""
    return [q for scope in rule_quantifier_scopes(evidence_model) for q in scope]


# Where evidence-model.md's complement list turns from the whole snapshot to the one
# sentence after the ledger: "— and in the one sentence after the snapshot's fit
# ledger, … a bare "none" too."
SCOPE_TURN = re.compile(r"\bin the one sentence after\b[^\"]*")


def rule_quantifier_scopes(evidence_model: str) -> tuple[list[str], list[str], list[str]]:
    """evidence-model.md's lists in their three scopes: (the named-set words, the
    complements, the further ones it makes a complement in the sentence after the
    fit ledger only). For the drift check that holds them to NAMED_SET, COMPLEMENT
    and AFTER_LEDGER_ONLY. All empty when the bullet or a list cannot be found."""
    bullet = next((line for line in evidence_model.splitlines()
                   if line.lstrip("- ").startswith("**The row is the unit")), "")
    named = re.search(NAMED_SET_MARK.pattern + r"[^:]*:\s*(.*?)\.(?:\s|$)", bullet, re.I)
    complement = re.search(COMPLEMENT_MARK.pattern + r"[^:]*:\s*(.*?)\.(?:\s|$)", bullet, re.I)
    if not named or not complement:
        return [], [], []
    turn = SCOPE_TURN.search(complement.group(1))
    cut = turn.start() if turn else len(complement.group(1))
    return (re.findall(r'"([^"]+)"', named.group(1)),
            re.findall(r'"([^"]+)"', complement.group(1)[:cut]),
            re.findall(r'"([^"]+)"', complement.group(1)[cut:]))


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
# The rule is evidence-model.md's "The row is the unit": anywhere in the response, a
# statement about a set of map rows agrees with the map; in the decision snapshot and
# decision.summary it also names every row of the set by ID, in the same sentence —
# unnamed there, it fails even when accurate — and a complement fails there whatever
# it names. The ledger_counts clause in job-underwriter's evals/evals.json states the
# whole rule to the grader. The functions below — set_claims, and map_claim and
# after_ledger_claim over it, the one reader CI and the harness call — enforce the
# part of it a pattern can decide, and leave the rest to the grader. This is the one
# statement of that boundary.
#
# Where it reads: the naming rule's scope only — the snapshot's prose, its status line
# included (map_claim over snapshot_prose), the one sentence after the fit ledger
# (after_ledger_claim), and decision.summary (map_claim).
#
# What the check reads there:
# - Which sentences make a set claim, in the map's own vocabulary: its tiers, fits,
#   rows, requirements, gaps and gates (MAP_WORDS), read as the comment above
#   MAP_WORDS says — a word of NAMED_SET with a map word in reach, "no" before a
#   tier, a count with a map word in reach (MAP_COUNT), or a ratio that counts rows
#   (_ratios). "only" and "the one" are named-set words: "the only" and "the one" are
#   read before any noun when a map word is in reach, so "the only path past the gate"
#   is a set claim, unnamed until it names its row ("the only path past R1"); bare
#   "only" is read only before a row ID, "the" or a number ("only R4", "only two
#   gaps"), never where it qualifies ("only adjacent evidence").
# - Presence: such a claim passes when its sentence names at least one row ID, any
#   row ID, and fails as an unnamed set claim when it names none. A sentence is one of
#   sentences() inside one paragraph, list item, heading or table row
#   (_claim_sentences).
# - Complements: a word of COMPLEMENT fails whether or not rows are named — with a
#   map word in reach ("the rest are `direct`", "no other row is open"), standing
#   directly over a row ID ("none of the others, R1 to R3"), and "all but" and "all
#   except" wherever they stand. "the others" and "none of the others" are read in
#   their noun form before a plural map noun too ("the other must-haves").
# - The one sentence after the fit ledger, which is about the map by construction:
#   every word of the lists, every ratio and a bare "none" are set claims there
#   wherever they stand and whatever they are about, and the verdict is the same — a
#   bare "none" and the complements fail; the named-set words and the ratios pass
#   when the sentence names a row. A second sentence there fails.
#
# What it leaves to the grader, which reads the rule in its own terms:
# - agreement, everywhere: whether what a set statement says is true of the map — the
#   rows it covers, N and M in a count or an "N of M", and what it says of them. That
#   is exactness, which the check does not read: in the snapshot a named claim passes
#   on its row IDs, true or false, so "R5b and R8 are the only rows below `direct`"
#   under a ledger listing a third passes the check and fails the grader;
# - which set a statement describes (it follows its subject), a row left out, an ID
#   the map lacks, a range or a split row's parent ID written for its rows;
# - an exception written in words other than "all but" and "all except" ("every
#   must-have but R4"), and a complement written in words not on the list ("every
#   other must-have", "all other rows", "the remaining gaps", a singular "the other
#   gate");
# - outside the sentence after the ledger, a word of the lists with no map word in
#   the reach the comment above MAP_WORDS gives ("R1 and R2 fail and nothing else in
#   the map can offset that" in the status line);
# - outside the sentence after the ledger, sets in the candidate's vocabulary rather
#   than the map's — "both of your hard constraints", "your non-negotiables", "your
#   claims" — and a set by gap type written without "gap" or "gaps" ("none of them is
#   a capability problem"), which the check does not read, named or not. Gap type is a
#   column of the map; written with "gap" or "gaps" it is a map word and is read, so
#   "none of them is a capability gap" fails unnamed;
# - every set statement outside the snapshot and decision.summary — the gap queue, the
#   application plan, evidence status, the upgrade menu — which the rule holds to
#   agreement alone.
# Each of these is read from English, which a pattern reads stricter than the rule
# in one sentence and looser in the next; so the check does not read them.

@dataclass
class Claim:
    """A set claim over the map in one sentence. `kind` is "named_set", "complement",
    "count" or, from after_ledger_claim alone, "sentence"; `why` is the problem when
    it fails, "" when it passes."""
    text: str
    kind: str
    sentence: str
    why: str = ""


_ROW_NAMED = re.compile(r"(?<![A-Za-z])" + ROW_ID + r"\b")
# Where a sentence ends besides sentences()'s own breaks: a blank line, or a line that
# starts a list item, a heading, a table row or a quote.
_BLOCK_BREAK = re.compile(r"\n[ \t]*\n\s*|\n(?=[ \t]*(?:[-*+][ \t]|\d+[.)][ \t]|#|\||>))")


def _claim_sentences(text: str) -> list[str]:
    """The sentences a set claim and its row IDs must share."""
    return [s for block in _BLOCK_BREAK.split(text) for s in sentences(block)]


def _finds(pattern: re.Pattern, text: str):
    """Every match of a claim pattern that does not reach out of a parenthesis: in
    "(mentor two juniors) is `unclear`" the count is inside one and the map word
    outside, so the count is the candidate's, not the map's."""
    at = 0
    while (hit := pattern.search(text, at)) is not None:
        if hit.group(0).count(")") <= hit.group(0).count("("):
            yield hit
            at = max(hit.end(), hit.start() + 1)
        else:
            at = hit.start() + 1


_ONLY = r"\bthe\s+only\b|\bonly(?=\s+(?:R\d|the\b|" + _NUMBER + r"\b))"


def _prose_patterns() -> list[tuple[str, re.Pattern]]:
    """(kind, pattern) for the words of the lists read in prose, built from the lists
    themselves so the two cannot drift: a word with a map word in reach; "no" before
    a tier; "only", "the one" and a complement also directly over a row ID; and "all
    but" and "all except" anywhere.
    "only" is read where it picks rows out ("the only", "only R4", "only two"), not
    where it qualifies one ("only adjacent")."""
    out = []
    for kind, phrases in (("named_set", NAMED_SET), ("complement", COMPLEMENT)):
        for phrase in phrases:
            if phrase == "N of M":
                continue                      # a count: MAP_COUNT and _ratios read it
            if phrase in ("no `must_have` row", "all but", "all except"):
                out.append((kind, re.compile(_phrase(phrase), re.I)))
                continue
            q = _ONLY if phrase == "only" else _phrase(phrase)
            out.append((kind, re.compile(r"(?:" + q + r")(?:" + _REACH + r")?" + MAP_WORDS + r"\b", re.I)))
            if kind == "complement" or phrase in ("only", "the one"):
                out.append((kind, re.compile(r"(?:" + q + r")" + _SEP + r"(?:the\s+)?(?:rows?\s+)?(?<![A-Za-z])"
                                             + ROW_ID + r"\b", re.I)))
    return out


PROSE_QUANTIFIERS = _prose_patterns()
# The sentence after the ledger: every word of the lists, in any sense, a bare
# "none" a complement.
AFTER_LEDGER_WORDS = [("named_set" if phrase in NAMED_SET else "complement", re.compile(_phrase(phrase), re.I))
                      for phrase in QUANTIFIERS if phrase != "N of M"]


def _words(sentence: str, hit: re.Match) -> str:
    """A claim's words, with the closing backtick of a token read as a map word."""
    words = hit.group(0)
    return words + "`" if words.count("`") % 2 and sentence[hit.end():hit.end() + 1] == "`" else words


def _hits(sentence: str, after_ledger: bool) -> list[tuple[int, str, str]]:
    """(start, kind, words) for every set claim in one sentence, in order, a
    complement reading first where two start at one place."""
    found = [(h.start(), kind, _words(sentence, h)) for kind, pattern in PROSE_QUANTIFIERS
             for h in _finds(pattern, sentence)]
    found += [(h.start(), "count", _words(sentence, h)) for h in _finds(MAP_COUNT, sentence)]
    found += [(h.start(), "count", h.group(0)) for h in (_all_ratios if after_ledger else _ratios)(sentence)]
    if after_ledger:
        found += [(h.start(), kind, h.group(0)) for kind, pattern in AFTER_LEDGER_WORDS
                  for h in pattern.finditer(sentence)]
    return sorted(set(found), key=lambda h: (h[0], h[1] != "complement", -len(h[2])))


def set_claims(text: str, after_ledger: bool = False) -> list[Claim]:
    """Every set claim over the map in `text`, one sentence at a time, each judged as
    the comment above Claim says: a complement fails, and a named-set word or a count
    fails when its sentence names no row. `after_ledger` reads `text` as the sentence
    after the fit ledger."""
    out = []
    for sentence in _claim_sentences(text):
        named = _ROW_NAMED.search(sentence) is not None
        for _, kind, words in _hits(sentence, after_ledger):
            claim = Claim(text=words, kind=kind, sentence=sentence)
            if kind == "complement":
                claim.why = (f"\"{words}\" is a complement: it describes its set by the rows it leaves out, "
                             f"so it never names them")
            elif not named:
                claim.why = f"\"{words}\" is a set claim over the map that names no row"
            out.append(claim)
    return out


def map_claim(text: str) -> Claim | None:
    """The first set claim that fails, in the prose the naming rule covers: the
    snapshot's prose and decision.summary. Counts that are not about map rows — the candidate's
    own figures, "two of three squads", "24/7 on-call", the Research tier line — are
    outside it, and bare "none" is read only after the ledger, because the slots
    require "none failed" and "none found". What it reads and what it leaves to the
    grader: the comment above Claim."""
    return next((c for c in set_claims(text) if c.why), None)


def after_ledger_claim(text: str) -> Claim | None:
    """What rule 2 forbids after the ledger: a set claim that fails, every word of the
    lists and every ratio read as one wherever it stands, a bare "none" a complement
    there (the comment above Claim); or a second sentence ("at most one sentence").
    For a second sentence the claim is that sentence, of kind "sentence"."""
    hit = next((c for c in set_claims(text, after_ledger=True) if c.why), None)
    if hit:
        return hit
    parts = sentences(text)
    if len(parts) > 1:
        rest = text[text.index(parts[1]):]
        return Claim(text=rest, kind="sentence", sentence=rest, why="a second sentence after the ledger")
    return None


def is_second_sentence(text: str, hit: Claim | None) -> bool:
    """Whether after_ledger_claim's hit is the extra-sentence case rather than a set
    claim, so both checkers word the failure the same way."""
    return bool(hit) and hit.kind == "sentence"


def quantifier_in(text: str) -> re.Match | None:
    """Any word of the lists, any ratio and any count over the map, in any sense and
    named or not: what the fit ledger's own lines may not hold, because the ledger is
    a projection and states no count at all (risk-and-decision.md, "The decision
    snapshot")."""
    for _, pattern in AFTER_LEDGER_WORDS:
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
