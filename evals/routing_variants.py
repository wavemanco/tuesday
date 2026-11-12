#!/usr/bin/env python3
"""Generate the routing diagnostic's variant case files from suite-routing.json.

The diagnostic (evals/README.md, "The attachment diagnostic") asks whether a
routing decision is made from the message text before any file is opened. It
runs four arms, one model, five runs per case. Arms A and D are suite cases as
they stand; arms B and C are variants of them, written here and nowhere else:

- **B** (`routing-arm-b.json`): the six cases that claim attached files, with
  each attached document's text also pasted into the message. The files stay
  attached.
- **C** (`routing-arm-c.json`): the nine self-contained positive cases, with
  their domain content moved into an attached file and the message reduced to
  its intent.

The files are output, never edited: change the suite or this script, then run

    python evals/routing_variants.py           # rewrite both files
    python evals/routing_variants.py --check   # exit 1 if either is stale

`ci/check_skills.py --only evals` fails a committed file that differs from what
this script generates from the committed suite.

A variant's `id` is its arm's offset plus the suite id it derives from (case 3
becomes 203 in B; case 1 becomes 301 in C), so it can never collide with a
suite id, and `derived_from` records the suite id. Its `expected` route is the
suite case's.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EVALS = Path(__file__).resolve().parent
SUITE = EVALS / "suite-routing.json"

ARM_B_CASES = (3, 9, 15, 17, 18, 21)
ARM_C_CASES = (1, 2, 4, 5, 6, 7, 8, 10, 16)
OFFSET = {"B": 200, "C": 300}
OUTPUTS = {"B": "routing-arm-b.json", "C": "routing-arm-c.json"}

# --- Arm B: paste each attachment into the message ---------------------------
#
# Mechanical: the message, a blank line, then each attachment in the case's own
# order as its file name, a colon, a newline and its text verbatim, blank lines
# between. No other word is added, and `attachments` is kept, so the files are
# still written into the run's project.


def arm_b(case: dict) -> dict:
    files = case.get("attachments") or {}
    if not files:
        raise SystemExit(f"arm B: suite case {case['id']} carries no attachments")
    pasted = "\n\n".join(f"{name}:\n{text}" for name, text in files.items())
    return {"prompt": f"{case['prompt']}\n\n{pasted}", "attachments": dict(files)}


# --- Arm C: move the domain content into an attached file ---------------------
#
# The rule. INTENT below lists, for each case, the spans of its message that
# carry its intent: what the user asks to have decided or done, and how they feel
# about it, without the specifics (the role, the company, the requirements, the
# user's own background, the people, the dates). Parity with arm A: every arm-A
# message names what the ask is about (a posting, a CV, an interview), so every
# reduced message keeps at least one of TOPIC_NOUNS, taken from a span of its
# own, and only the specifics move (evals/test_harness.py holds both arms to it).
# Each span is copied verbatim from the suite and must occur in the message
# exactly once; the script fails
# otherwise, so a suite edit that breaks a span is caught here, not shipped.
#
# The transform is then fixed: every character of the message outside the
# INTENT spans moves, in order, into one attached file, ATTACHED_FILE, with runs
# of whitespace collapsed; the reduced message is ATTACHED_SENTENCE followed by
# the spans, in order, joined by one space. Nothing is dropped: the spans plus
# the file are the original message, and ATTACHED_SENTENCE is the only text
# added, there because every arm-A message claims its files (evals/README.md,
# "The attachment diagnostic", discloses it and what it confounds). The choice of span
# is the one judgment in this file, and it is made here, in the open, per case.
#
# A case whose content cannot be separated this way is written by hand in
# HAND_WRITTEN, with its reason. A case with nothing to move is in UNCHANGED,
# with its reason, and is carried into arm C as it stands.

ATTACHED_FILE = "details.txt"
ATTACHED_SENTENCE = "Details are in the attached file."

# What an ask is about, an event or a document: the parity rule's vocabulary,
# matched as whole words, case-insensitively (`topic_nouns`).
TOPIC_NOUNS = ("job", "role", "posting", "listing", "apply", "applying", "application", "applications",
               "interview", "interviewing", "interviewer", "round", "resume", "cv", "jd", "bullets",
               "portfolio", "case study", "ats")


def topic_nouns(text: str) -> list[str]:
    """The TOPIC_NOUNS a message names."""
    return [w for w in TOPIC_NOUNS if re.search(rf"(?<![\w']){re.escape(w)}(?![\w])", text, re.I)]


INTENT: dict[int, tuple[str, ...]] = {
    # The posting's stack and the user's years move; the framing and the ask stay.
    1: ("found this posting on a job board last night and i keep going back and forth on it.",
        "worth applying or am i kidding myself"),
    # The quoted posting and the recruiter's address move.
    2: ("Something about this listing feels off and I can't put my finger on it.",
        "Am I being paranoid?"),
    # The role, its source and the pasted posting move; the question names only
    # the case study the posting asks for, which is the user's cost, not the role.
    4: ("before I spend a saturday on the portfolio case study they want, is this actually a real "
        "opportunity worth that time?",),
    # The company, role, interviewer and day move; the round stays, as what the
    # ask is about, and so does the quoted question, as what the user wants help with.
    5: ("first real round after the recruiter screen.",
        "can you get me ready — i always freeze on the 'walk me through a time you disagreed with an "
        "engineer' type stuff",),
    # The interviewer, her stance and the user's role move; that it is an interview stays.
    6: ("I'm interviewing", "How do I tailor what I say for her specifically?",),
    # The round's shape and the session's name move; that it is a final round stays.
    7: ("final round", "no idea what that means or how to not sound rehearsed.", "help"),
    # The interview day, the scope and the comp band move; that it is an interview stays.
    10: ("I have an interview", "Not sure whether to prep properly or cancel.",),
    # The resume's shape, the pasted posting and the bullets move; "[pasted]"
    # stays, as the suite wrote it.
    16: ("quick one — for this posting [pasted], which of my bullets should I lead with?",),
}

HAND_WRITTEN: dict[int, tuple[str, str]] = {}  # id -> (message, attached text); none needed yet

UNCHANGED: dict[int, str] = {
    8: "Its whole message is the ask: no role, company, posting or resume text is in it, so there "
       "is no domain content to move, and attaching an empty file would claim a document the suite "
       "never wrote. It runs in arm C as it stands, identical to arm D.",
}


def arm_c(case: dict) -> dict:
    n = case["id"]
    if n in UNCHANGED:
        return {"prompt": case["prompt"], "unchanged": UNCHANGED[n]}
    if n in HAND_WRITTEN:
        message, moved = HAND_WRITTEN[n]
        return {"prompt": message, "attachments": {ATTACHED_FILE: moved}, "hand_written": True}
    spans = INTENT.get(n)
    if not spans:
        raise SystemExit(f"arm C: suite case {n} has no INTENT, HAND_WRITTEN or UNCHANGED entry")
    prompt, rest = case["prompt"], case["prompt"]
    for span in spans:
        if prompt.count(span) != 1:
            raise SystemExit(f"arm C: case {n}'s intent span occurs {prompt.count(span)} times in its "
                             f"message, not once: {span!r}")
        rest = rest.replace(span, " ", 1)
    moved = re.sub(r"\s+", " ", rest).strip()
    if not moved:
        raise SystemExit(f"arm C: case {n}'s intent spans are its whole message — list it in UNCHANGED")
    return {"prompt": " ".join((ATTACHED_SENTENCE, *spans)), "attachments": {ATTACHED_FILE: moved}}


ARMS = {
    "B": (ARM_B_CASES, arm_b,
          "Routing diagnostic arm B: the six attachment-claiming suite cases with each attached "
          "document's text also pasted into the message, the files still attached."),
    "C": (ARM_C_CASES, arm_c,
          "Routing diagnostic arm C: the self-contained positive suite cases with their domain "
          "content moved into an attached file and the message reduced to its intent."),
}


def build(suite: dict) -> dict[str, str]:
    """Each output file's name -> its exact text, from the suite as given."""
    by_id = {c["id"]: c for c in suite["cases"]}
    out = {}
    for arm, (ids, transform, purpose) in ARMS.items():
        cases = []
        for n in ids:
            if n not in by_id:
                raise SystemExit(f"arm {arm}: suite case {n} does not exist")
            source = by_id[n]
            variant = {"id": OFFSET[arm] + n, "derived_from": n, "arm": arm, "expected": source["expected"]}
            if "siblings" in source:
                variant["siblings"] = source["siblings"]
            variant.update(transform(source))
            cases.append(variant)
        doc = {"suite": suite.get("suite"), "purpose": purpose,
               "generated_by": "evals/routing_variants.py from evals/suite-routing.json — regenerate, never edit",
               "routes": suite["routes"], "cases": cases}
        out[OUTPUTS[arm]] = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if a committed file is stale; write nothing")
    args = ap.parse_args()
    stale = []
    for name, text in build(json.loads(SUITE.read_text(encoding="utf-8"))).items():
        path = EVALS / name
        if path.exists() and path.read_text(encoding="utf-8") == text:
            continue
        stale.append(name)
        if not args.check:
            path.write_text(text, encoding="utf-8")
    if args.check:
        print("stale: " + ", ".join(stale) if stale else "routing variants are current")
        return 1 if stale else 0
    print("wrote: " + ", ".join(stale) if stale else "routing variants already current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
