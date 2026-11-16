#!/usr/bin/env python3
"""Run fixed multi-turn scripts in a clean room, one resumed session per scenario, then check and grade
every turn (roadmap plan, "Measurement and evidence" and the harness contract's transcript rows; E24).

The fixture runner (run_fixtures.py) measures a first turn. Some behaviour exists only later in a
conversation: a drill that asks the question the candidate picked from the pack and stays in persona, a
debrief that keeps a reported claim a record, a dossier written when the candidate asks for it. This
driver sends a script's turns one after another to one session, in one room, and reads each turn the way
the fixture runner reads a run.

**It reuses the fixture runner's room and launcher, unchanged.** Each attempt is a run_fixtures.prepare_room
(the matched install, alone or through the front door, the research files and the room's flags) and each
turn a run_fixtures.run_attempt (the same `claude -p` argv, stdin, cwd and child_env()), so a turn is sent
exactly as a fixture run is. A later turn adds `--resume <session id>` before the room's flags and nothing
else: the same room, flags, MCP config and environment, never `--fork-session`. The resumed turn's init
event must carry the same session id and the room as its cwd, or the turn is a wrong-session resume.

**Turn 1 is the scenario's natural prompt in both arms.** A first attempt that does not fire the installed
skill is kept (its stream, files and research log, for the hidden-module count and the sentinel scan) and
the scenario is sent again once, nudged, in a fresh room, as the fixture runner nudges; the nudged session
carries the later turns. A first attempt that timed out or declined is not nudged. No later turn is ever
nudged: a resumed turn rarely calls the skill again, so it inherits turn 1's fire, and its own reading
(`reader_outcome`) is recorded and never scored.

**Every turn is saved before the next is sent.** The turn's record, its body (the chat plus what its
`reads` name), its stream and its file snapshot are written atomically, so a stopped scenario keeps every
turn it finished. Later turns' user text is fixed by the script; where it names a question (`{Q}`), the ID
is selected deterministically from the previous turn's body (chat and the files it changed), and the
record says which file supplied it.

**Outcomes keep a valid answer's quality apart from the driver's availability** (CONTRIBUTING.md,
"Harnesses report three outcomes, not two"). Each turn has an outcome; each scenario is `scored`,
`set_aside`, `killed` or `harness_invalid`. The precedence for a turn that did not answer: the usage-limit
message in its stdout or stderr is a kill (recovered from turn 1 in a fresh room); then a refused resume;
then a timeout; then any other decline. A missing session id, a refused or wrong-session resume, a void
room and an unusable stream are set aside, explicitly unscored. A reply lacking a selectable ID is
behaviour: the next turn is `selection_failed`, the later ones `not_reached`, and each of their
expectations and declared checks reads FAIL. See TURN_OUTCOMES and SCENARIO_OF.

**Checks and graders read each turn as a turn of this conversation.** A turn's checks take the cumulative
user text (turn 1's prompt and every text sent through this turn) as the request, so a later turn quoting
a turn-1 JD line is quoting the request; the research accounting runs only on a turn that declares it
(`accounting`). Two pinned graders grade each turn's own expectations with the transcript prompt (version
`t1`, its predecessor version 3), which shows them each earlier turn's user text and saved body.

There is no retry pass. Killed scenarios are recovered with `--recover --move` and `--stems`; set-aside
scenarios count toward the 10% limit and are never rerun; a turn with a grade missing is regraded with
`--grade-gaps [--move [--accept-partial]]` and `--stems … --skip-execute`.

Usage:
    python evals/run_transcripts.py --scripts drill.json --out /var/tmp/m/drill --model M --grader-model G
    python evals/run_transcripts.py --scripts drill.json --out DIR --model M --grader-model G --via tuesday --runs 5
    python evals/run_transcripts.py --scripts drill.json --out DIR --recover --move      # then --stems the list
    python evals/run_transcripts.py --scripts drill.json --out DIR --model M --grader-model G --stems rerun.txt
    python evals/run_transcripts.py --scripts drill.json --out DIR --grade-gaps --move --accept-partial
    python evals/run_transcripts.py --scripts drill.json --out DIR --model M --grader-model G --stems regrade.txt --skip-execute

Exit codes: 0 every scenario scored and clean; 1 an expectation or a check failed; 3 a scenario killed and
not yet rerun, set aside or harness-invalid, an unresolved expectation, a grade gap, or a refused pass (3
wins over 1, as in run_fixtures). 2 is argparse's.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import output_checks  # noqa: E402
import run_fixtures  # noqa: E402  (the shared room, launcher, stream reader, grader and recovery helpers)
from fixture_clauses import ClauseError, dated, expand_text  # noqa: E402

REPO = run_fixtures.REPO
SKILLS = run_fixtures.SKILLS
MODES = run_fixtures.MODES
VIAS = run_fixtures.VIAS
LAYOUTS = run_fixtures.LAYOUTS

# --- The script format ---------------------------------------------------------------------------

# The priced scripts run three to five turns (recorded 3, debrief 4, ordinary drill 5).
MIN_TURNS, MAX_TURNS = 3, 5
SCRIPT_ID = re.compile(r"^[a-z][a-z0-9-]*$")
# What a turn delivers: output (held to the skill's watch-out line, as every fixture), a gate question
# (output_checks.check_gate_only), or a turn inside an exchange that carries no watch-out (a drill turn).
NO_WATCH_OUT = "no_watch_out"
DELIVERS = ("output", output_checks.GATE_QUESTION, NO_WATCH_OUT)
# The closed set of selectors a later turn's text may use. `bank_question`: the question IDs of a turn's
# question-bank tables, in document order.
SELECTORS = ("bank_question",)
# A turn's deterministic checks. `accounting` runs the research accounting (output_checks.check_accounting)
# on that turn; the others are the fixture checks of the same names.
ACCOUNTING = "accounting"
TURN_CHECKS = (ACCOUNTING, "quotes", "fit_ledger", output_checks.TRACES_CHECK, output_checks.YES_PAGES_CHECK)
# The checks this driver writes itself: a no-watch-out turn's, and a required file's.
NO_WATCH_OUT_CHECK = "no_watch_out"
TURN_FILE_CHECK = "turn_file"
PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
QUESTION_ID = re.compile(r"^[A-Z]{1,3}\d+[a-z]?$")
TRANSCRIPT_KEYS = {"id", "description", "modes", "candidate_text", "candidate_constraints", "research", "sentinels",
                   "date_anchor", "core", "turns"}
TURN_KEYS = {"n", "prompt", "from_fixture", "text", "select", "delivers", "reads", "checks", "expectations",
             "require_file"}
# What a script whose turn 1 names a fixture takes from it, and so may not declare itself.
INHERITED = ("candidate_text", "candidate_constraints", "research", "sentinels", "date_anchor")


class ScriptError(ValueError):
    """A script file breaks a rule load_scripts holds it to."""


def canonical_sha(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def module_clauses(skill: str) -> dict:
    path = REPO / "skills" / skill / "evals" / "evals.json"
    try:
        clauses = json.loads(path.read_text(encoding="utf-8")).get("clauses") or {}
    except (OSError, ValueError, AttributeError):
        return {}
    return clauses if isinstance(clauses, dict) else {}


def module_fixtures(skill: str) -> dict:
    try:
        return {c.get("id"): c for c in run_fixtures.cases_for(skill, []) if isinstance(c, dict)}
    except (OSError, ValueError, ClauseError):
        return {}


def is_index(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def user_texts(turns: list[dict]) -> list[str]:
    """What the user wrote in each turn, turn 1's prompt first (a later turn's text before selection)."""
    return [t.get("prompt") if t["n"] == 1 else t.get("text") for t in turns]


def load_scripts(path: Path, skill: str | None = None) -> tuple[str, list[dict]]:
    """Read and validate a scripts file; return (skill, scripts), each script normalised.

    The file is a case file with a `transcripts` list: {"skill_name", "clauses", "transcripts": [...]}.
    Clauses expand from the file's own merged with the module's (a name both define differently is
    refused). Every rule is checked here, before any call, and a violation raises ScriptError:

    - a script's `id` is `[a-z][a-z0-9-]*`, unique, and never a fixture's numeric id; its keys and its
      turns' keys are the known ones;
    - turns are numbered 1..N with no gap, MIN_TURNS <= N <= MAX_TURNS;
    - turn 1 has exactly one of a `prompt` or a `from_fixture` naming a fixture of the module, whose prompt,
      candidate_text, candidate_constraints, research, sentinels and date_anchor the script then inherits
      (and may not declare again), and whose checks turn 1 runs (with the accounting where the fixture has
      research and is no gate);
    - a later turn has fixed `text`, and every `{X}` in it is bound by that turn's `select`, every binding
      used; a selector's `from` is in SELECTORS, its `pick` a fixed index or list of distinct indexes,
      distinct across the turn's bindings that read the same turn, and its source turn (`turn`, the
      previous one by default) reads `files_changed`, so the IDs a pack saved as a file shows are read;
    - `delivers` is in DELIVERS; `reads` lists `chat` and any of `files_changed` and `file:<name>`; `checks`
      are TURN_CHECKS, each with what it needs (research for the accounting, the accounting for
      yes_names_page, a candidate_text list for quotes and traces, candidate_constraints for fit_ledger),
      and a gate turn runs none that reads a pack;
    - every turn has at least one expectation; `core` names existing (turn, expectation) pairs;
    - candidate_text entries are each in some turn's user text; sentinels pass the freezing rules
      (output_checks.sentinel_declaration_problems) against turn 1's prompt.

    Each script comes back with `index` (its place in the file, which names its rooms), `skill`, `modes`,
    every turn's `delivers`, `reads`, `checks` and `select` filled in, and `sha256`, the canonical JSON's
    sha256, recorded in every record of its runs. Expectations stay as written before date expansion
    (dated() writes them for a run's date), as the fixture runner hashes them."""
    path = Path(path)
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ScriptError(f"{path}: cannot be read as JSON: {exc}") from None
    if not isinstance(spec, dict):
        raise ScriptError(f"{path}: a scripts file is a JSON object with skill_name and transcripts")
    name = spec.get("skill_name")
    if name not in SKILLS:
        raise ScriptError(f"{path}: skill_name {name!r} is not one of {', '.join(SKILLS)}")
    if skill and skill != name:
        raise ScriptError(f"{path}: its skill_name is {name}, and --skill says {skill}")
    extra = sorted(set(spec) - {"skill_name", "clauses", "transcripts", "description"})
    if extra:
        raise ScriptError(f"{path}: unknown key(s) {', '.join(extra)}")
    own = spec.get("clauses") or {}
    if not isinstance(own, dict) or any(not isinstance(v, str) for v in own.values()):
        raise ScriptError(f"{path}: \"clauses\" must map names to strings")
    clauses = module_clauses(name)
    clash = sorted(k for k in own if k in clauses and clauses[k] != own[k])
    if clash:
        raise ScriptError(f"{path}: clause(s) {', '.join(clash)} defined here and in the module's evals.json "
                          f"with different text")
    clauses = {**clauses, **own}
    transcripts = spec.get("transcripts")
    if not isinstance(transcripts, list) or not transcripts:
        raise ScriptError(f"{path}: transcripts must be a non-empty list")
    fixtures = module_fixtures(name)
    scripts = [validate_script(raw, i, name, clauses, fixtures) for i, raw in enumerate(transcripts)]
    ids = [s["id"] for s in scripts]
    if len(set(ids)) != len(ids):
        raise ScriptError(f"{path}: duplicate script ids: {', '.join(sorted({i for i in ids if ids.count(i) > 1}))}")
    return name, scripts


def validate_script(raw, index: int, skill: str, clauses: dict, fixtures: dict) -> dict:
    """One script, checked and normalised (load_scripts)."""
    where = f"script {index + 1}"
    if not isinstance(raw, dict):
        raise ScriptError(f"{where}: not an object")
    sid = raw.get("id")
    if not isinstance(sid, str) or not SCRIPT_ID.match(sid):
        raise ScriptError(f"{where}: id {sid!r} is not [a-z][a-z0-9-]* (a script id is never a fixture's number)")
    where = f"script {sid}"
    extra = sorted(set(raw) - TRANSCRIPT_KEYS)
    if extra:
        raise ScriptError(f"{where}: unknown key(s) {', '.join(extra)}")
    turns = raw.get("turns")
    if not isinstance(turns, list) or not all(isinstance(t, dict) for t in turns):
        raise ScriptError(f"{where}: turns must be a list of objects")
    numbers = [t.get("n") for t in turns]
    if numbers != list(range(1, len(turns) + 1)):
        raise ScriptError(f"{where}: turns are numbered {numbers}, not 1..N with no gap")
    if not MIN_TURNS <= len(turns) <= MAX_TURNS:
        raise ScriptError(f"{where}: {len(turns)} turns; a script has {MIN_TURNS} to {MAX_TURNS}")
    for t in turns:
        unknown = sorted(set(t) - TURN_KEYS)
        if unknown:
            raise ScriptError(f"{where} turn {t['n']}: unknown key(s) {', '.join(unknown)}")
    script = {k: raw[k] for k in ("id", "description") if k in raw}
    first = turns[0]
    if ("prompt" in first) == ("from_fixture" in first):
        raise ScriptError(f"{where} turn 1: give exactly one of prompt and from_fixture")
    if "text" in first or "select" in first:
        raise ScriptError(f"{where} turn 1: turn 1 is the scenario's natural prompt; text and select are for "
                          f"later turns")
    inherited_checks, inherited_delivers = None, None
    if "from_fixture" in first:
        fid = first["from_fixture"]
        fixture = fixtures.get(fid) if isinstance(fid, int) and not isinstance(fid, bool) else None
        if fixture is None:
            raise ScriptError(f"{where} turn 1: from_fixture {fid!r} names no fixture of {skill}")
        twice = [k for k in INHERITED if k in raw]
        if twice:
            raise ScriptError(f"{where}: declares {', '.join(twice)}, which turn 1 inherits from fixture {fid}")
        if "checks" in first:
            raise ScriptError(f"{where} turn 1: declares checks, which it inherits from fixture {fid}")
        script["from_fixture"] = fid
        script.update({k: fixture[k] for k in INHERITED if k in fixture})
        prompt = fixture.get("prompt")
        inherited_delivers = fixture.get("delivers") or "output"
        gate = inherited_delivers == output_checks.GATE_QUESTION
        inherited_checks = [c for c in fixture.get("checks") or [] if c in TURN_CHECKS]
        if fixture.get("research") and not gate:
            inherited_checks = [ACCOUNTING] + inherited_checks
        if "delivers" in first and first["delivers"] != inherited_delivers:
            raise ScriptError(f"{where} turn 1: delivers {first['delivers']!r}, and fixture {fid} delivers "
                              f"{inherited_delivers!r}")
    else:
        prompt = first.get("prompt")
        script.update({k: raw[k] for k in INHERITED if k in raw})
    if not isinstance(prompt, str) or not prompt.strip():
        raise ScriptError(f"{where} turn 1: the prompt is empty")
    research = script.get("research")
    if research is not None and not isinstance(research, dict):
        raise ScriptError(f"{where}: research must be an object")
    modes = raw.get("modes", run_fixtures.modes_of(script))
    if not isinstance(modes, list) or not modes or len(set(modes)) != len(modes) \
            or any(m not in MODES for m in modes):
        raise ScriptError(f"{where}: modes {modes!r} must be a non-empty list of distinct modes from "
                          f"{', '.join(MODES)}")
    if "canned" in modes and not (research or {}).get("pages"):
        raise ScriptError(f"{where}: a canned room serves research.pages, and the script declares none")
    script["modes"] = list(modes)
    text_list = script.get("candidate_text")
    if text_list is not None and (not isinstance(text_list, list) or not all(isinstance(e, str) for e in text_list)):
        raise ScriptError(f"{where}: candidate_text must be a list of strings")

    normalised = []
    for t in turns:
        k = t["n"]
        tw = f"{where} turn {k}"
        turn = {"n": k}
        if k == 1:
            turn["prompt"] = prompt
        else:
            if "prompt" in t or "from_fixture" in t:
                raise ScriptError(f"{tw}: only turn 1 has a prompt or from_fixture; a later turn has text")
            text = t.get("text")
            if not isinstance(text, str) or not text.strip():
                raise ScriptError(f"{tw}: a later turn has fixed, non-empty text")
            turn["text"] = text
        delivers = t.get("delivers", inherited_delivers if k == 1 and inherited_delivers else "output")
        if delivers not in DELIVERS:
            raise ScriptError(f"{tw}: delivers {delivers!r} is not one of {', '.join(DELIVERS)}")
        turn["delivers"] = delivers
        reads = t.get("reads")
        if not isinstance(reads, list) or not reads or len(set(map(str, reads))) != len(reads):
            raise ScriptError(f"{tw}: reads must be a non-empty list of distinct items (the observations its "
                              f"scorer reads are frozen in the script)")
        for item in reads:
            if not (item in ("chat", "files_changed") or (isinstance(item, str) and item.startswith("file:")
                                                         and item[5:].strip() and ".." not in item[5:])):
                raise ScriptError(f"{tw}: reads item {item!r} is not chat, files_changed or file:<name>")
        if "chat" not in reads:
            raise ScriptError(f"{tw}: reads must include chat, which every turn's checks read")
        turn["reads"] = list(reads)
        checks = inherited_checks if k == 1 and inherited_checks is not None else t.get("checks", [])
        if not isinstance(checks, list) or len(set(map(str, checks))) != len(checks):
            raise ScriptError(f"{tw}: checks must be a list of distinct names")
        for c in checks:
            if c not in TURN_CHECKS:
                raise ScriptError(f"{tw}: check {c!r} is not one of {', '.join(TURN_CHECKS)}")
        if output_checks.YES_PAGES_CHECK in checks and ACCOUNTING not in checks:
            raise ScriptError(f"{tw}: {output_checks.YES_PAGES_CHECK} reads the accounting table, and the turn "
                              f"does not run the accounting")
        if ACCOUNTING in checks and not research:
            raise ScriptError(f"{tw}: runs the accounting, and the script declares no research")
        for c in ("quotes", output_checks.TRACES_CHECK):
            if c in checks and not isinstance(text_list, list):
                raise ScriptError(f"{tw}: runs the {c} check and the script declares no candidate_text list")
        if "fit_ledger" in checks and script.get("candidate_constraints") not in output_checks.CONSTRAINTS:
            raise ScriptError(f"{tw}: runs the fit_ledger check, and candidate_constraints is "
                              f"{script.get('candidate_constraints')!r}, not known or unknown")
        if delivers == output_checks.GATE_QUESTION:
            off = [c for c in checks if c in output_checks.GATE_OFF_CHECKS or c == ACCOUNTING]
            if off:
                raise ScriptError(f"{tw}: a gate-only turn writes no pack, ledger or table, and runs "
                                  f"{', '.join(off)}")
        turn["checks"] = list(checks)
        expectations = t.get("expectations")
        if not isinstance(expectations, list) or not expectations \
                or any(not isinstance(e, str) or not e.strip() for e in expectations):
            raise ScriptError(f"{tw}: at least one expectation, each a non-empty string")
        try:
            turn["expectations"] = [expand_text(e, clauses, f"{tw} expectation {i}")
                                    for i, e in enumerate(expectations, 1)]
        except ClauseError as exc:
            raise ScriptError(str(exc)) from None
        for e in turn["expectations"]:
            if re.search(r"\{\{(?!date)", e) or ("}}" in e and "{{date" not in e):
                raise ScriptError(f"{tw}: an expectation keeps an unexpanded clause reference")
        if "require_file" in t:
            name = t["require_file"]
            if not isinstance(name, str) or not name.strip() or ".." in name:
                raise ScriptError(f"{tw}: require_file must name a file")
            turn["require_file"] = name
        select = t.get("select", {})
        if k == 1:
            select = {}
        if not isinstance(select, dict):
            raise ScriptError(f"{tw}: select must map placeholders to selectors")
        names = PLACEHOLDER.findall(turn.get("text", ""))
        unbound = sorted(set(names) - set(select))
        if unbound:
            raise ScriptError(f"{tw}: {', '.join('{' + n + '}' for n in unbound)} in its text is bound by no select")
        unused = sorted(set(select) - set(names))
        if unused:
            raise ScriptError(f"{tw}: select binds {', '.join(unused)}, which its text never uses")
        taken: dict[tuple, list[int]] = {}
        bound = {}
        for placeholder, sel in select.items():
            if not isinstance(sel, dict) or set(sel) - {"from", "pick", "turn"}:
                raise ScriptError(f"{tw}: select {placeholder} must be {{from, pick[, turn]}}")
            if sel.get("from") not in SELECTORS:
                raise ScriptError(f"{tw}: selector {sel.get('from')!r} is not one of {', '.join(SELECTORS)}")
            pick = sel.get("pick")
            picks = [pick] if is_index(pick) else pick if isinstance(pick, list) and pick and all(
                is_index(p) for p in pick) else None
            if picks is None or len(set(picks)) != len(picks):
                raise ScriptError(f"{tw}: select {placeholder}'s pick must be an index or a list of distinct indexes")
            source = sel.get("turn", k - 1)
            if not isinstance(source, int) or isinstance(source, bool) or not 1 <= source < k:
                raise ScriptError(f"{tw}: select {placeholder} reads turn {source!r}, not an earlier turn")
            source_reads = turns[source - 1].get("reads") or []
            if "files_changed" not in source_reads:
                raise ScriptError(f"{tw}: select {placeholder} reads turn {source}'s body, and turn {source}'s reads "
                                  f"do not include files_changed, so IDs a pack saved as a file shows go unread")
            used = taken.setdefault((sel["from"], source), [])
            if set(used) & set(picks):
                raise ScriptError(f"{tw}: two bindings pick the same {sel['from']} of turn {source}")
            used += picks
            bound[placeholder] = {"from": sel["from"], "pick": pick, "turn": source}
        turn["select"] = bound
        normalised.append(turn)
    script["turns"] = normalised
    texts = [output_checks.normalise_quote(t or "") for t in user_texts(normalised)]
    for entry in text_list or []:
        if not any(output_checks.normalise_quote(entry) in t for t in texts):
            raise ScriptError(f"{where}: candidate_text entry {entry[:60]!r} is in no turn's user text — correct "
                              f"quotes of it would fail")
    if "sentinels" in script:
        problems = output_checks.sentinel_declaration_problems(script["sentinels"], prompt)
        if problems:
            raise ScriptError(f"{where}: " + "; ".join(problems))
    core = raw.get("core", [])
    if not isinstance(core, list):
        raise ScriptError(f"{where}: core must be a list of [turn, expectation] pairs")
    pairs = []
    for pair in core:
        if not (isinstance(pair, list) and len(pair) == 2 and all(isinstance(x, int) and not isinstance(x, bool)
                                                               for x in pair)
                and 1 <= pair[0] <= len(normalised) and 1 <= pair[1] <= len(normalised[pair[0] - 1]["expectations"])):
            raise ScriptError(f"{where}: core pair {pair!r} names no (turn, expectation) of the script")
        if pair in pairs:
            raise ScriptError(f"{where}: core pair {pair!r} is listed twice")
        pairs.append(pair)
    script["core"] = pairs
    try:
        dated(script, datetime.date.today())
    except ClauseError as exc:
        raise ScriptError(f"{where}: {exc}") from None
    script["index"] = index
    script["skill"] = skill
    script["sha256"] = canonical_sha({k: v for k, v in script.items() if k != "sha256"})
    return script


def stem_for(skill: str, script: dict, mode: str, run: int) -> str:
    """A scenario's stem: `<skill>-<script id>.<mode>.run<n>`. It cannot collide with a fixture stem, whose id
    is a number."""
    return f"{skill}-{script['id']}.{mode}.run{run}"


def room_prefix(script: dict) -> str:
    """A scenario's rooms are named `case-s<k>-<mode>-<run id>`, `k` the script's place in its file, in both
    layouts: neither a module's name nor a script's id reaches the model's cwd."""
    return f"case-s{script['index']}"


# --- Reading a turn's stream and deciding its outcome ---------------------------------------------------

# A refused resume, as the CLI words it.
RESUME_REFUSED = re.compile(r"No conversation found|\bsession\b[^\n]{0,80}\bnot found|\bcannot resume\b", re.I)

# Turn outcomes. `completed` is a valid reply, `selection_failed` the turn after a reply with too few IDs to
# select, `not_reached` the turns after it; every other outcome stops the scenario unscored.
TURN_OUTCOMES = ("completed", "selection_failed", "not_reached", "room_invalid", "void", "no_session_id",
                 "resume_refused", "wrong_session", "usage_limit", "timeout", "malformed_stream", "declined",
                 "killed")
# The scenario outcome a stopping turn gives.
SCENARIO_OF = {"usage_limit": "killed", "killed": "killed", "timeout": "set_aside", "void": "set_aside",
               "no_session_id": "set_aside", "resume_refused": "set_aside", "wrong_session": "set_aside",
               "malformed_stream": "set_aside", "declined": "set_aside", "room_invalid": "harness_invalid",
               "not_fired": "harness_invalid"}
SCENARIO_OUTCOMES = ("scored", "set_aside", "killed", "harness_invalid")
OUTCOME_WORDS = {"usage_limit": "usage limit", "killed": "killed mid-scenario", "timeout": "timeout",
                 "void": "void", "no_session_id": "no session id", "resume_refused": "refused resume",
                 "wrong_session": "wrong-session resume", "malformed_stream": "malformed stream",
                 "declined": "declined", "room_invalid": "room invalid", "not_fired": "not fired",
                 "sentinel_scan": "sentinel scan unscored", "selection_failed": "selection failed"}
SET_ASIDE_LIMIT = 0.10


def read_stream(text: str) -> dict:
    """A saved stream's text, read: its JSON events in order, the count of non-empty lines that are not one
    (`unparsed`, reported, never an outcome on its own), those lines, the first init event, the result event,
    and the main thread's assistant text blocks."""
    events, unparsed, raw = [], 0, []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            event = None
        if isinstance(event, dict):
            events.append(event)
        else:
            unparsed += 1
            raw.append(line)
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), None)
    result = next((e for e in reversed(events) if e.get("type") == "result"), None)
    texts = [item.get("text", "") for e in events if e.get("type") == "assistant"
             and not e.get("parent_tool_use_id") and not e.get("isSidechain")
             for item in (e.get("message") or {}).get("content") or []
             if isinstance(item, dict) and item.get("type") == "text"]
    return {"events": events, "unparsed": unparsed, "raw": raw, "init": init, "result": result, "texts": texts}


def message_text(reading: dict, stderr: str) -> str:
    """The text a decline message can be in, where the CLI writes one: stderr, stdout lines that are not JSON,
    the result event's text when the result is an error or the text is short, and the last assistant text
    block when it is short (run_fixtures.limit_line reads the same places). A reply's prose and tool results
    (a page, the candidate's own file) are not read: the usage-limit words in a job description, or in a long
    partial pack cut by a timeout, are not a kill."""
    result = reading.get("result") or {}
    said = result.get("result") if isinstance(result.get("result"), str) else ""
    texts = reading.get("texts") or []
    return "\n".join([stderr or "", *reading.get("raw", []),
                      said if said and (result.get("is_error") or len(said.strip()) < run_fixtures.SHORT_REPLY)
                      else "",
                      texts[-1] if texts and len(texts[-1].strip()) < run_fixtures.SHORT_REPLY else ""])


def run_outcome(k: int, outcome: str, returncode, reading: dict, stderr: str, limit_hit: bool,
                error: str | None) -> tuple[str, str | None]:
    """A turn's outcome from how its CLI process ended, before the session and the room are read; pure.

    The precedence, the same on turn 1 and on a resumed turn: (1) the usage-limit message (run_fixtures.LIMIT)
    where the CLI writes it (message_text, run_fixtures.limit_line: never a long reply's prose), or a decline
    the launcher flagged a limit, is `usage_limit`, a kill recovered
    from turn 1 — a limit at resume start exits non-zero with no init event, and is not a refused resume;
    (2) on a resumed turn, RESUME_REFUSED text is `resume_refused`; (3) a timeout is `timeout`; (4) a
    non-zero exit is `declined`; (5) an exit 0 whose stream has no parseable event, no init event or no
    result event is `malformed_stream`; (6) an error result (rate limit, overload) is `declined`. A run that
    answered (exit 0, a result event that is no error) is `completed`, however short its reply and whatever
    it mentions (run_fixtures.stream_declined): a drill question about a missed quota is an answer."""
    if outcome != "completed":
        said = message_text(reading, stderr)
        if limit_hit or run_fixtures.LIMIT.search(said):
            line = first_line(run_fixtures.LIMIT, said) or "flagged by the launcher"
            return "usage_limit", f"the usage-limit message: {line}"
        if k > 1 and RESUME_REFUSED.search(said):
            return "resume_refused", first_line(RESUME_REFUSED, said)
        if outcome == "timeout":
            return "timeout", error or "timed out"
        if returncode not in (0, None):
            return "declined", f"exit {returncode}: {(error or '').strip()[:200]}"
        if not reading["events"]:
            return "malformed_stream", "no parseable event"
        if reading["init"] is None:
            return "malformed_stream", "no init event"
        if reading["result"] is None:
            return "malformed_stream", "exit 0 with no result event"
        return "declined", (error or "declined").strip()[:200]
    if not reading["events"]:
        return "malformed_stream", "no parseable event"
    if reading["init"] is None:
        return "malformed_stream", "no init event"
    return "completed", None


def first_line(pattern: re.Pattern, text: str) -> str:
    for line in text.splitlines():
        if pattern.search(line):
            return line.strip()[:200]
    return ""


def session_problem(k: int, reading: dict, expected: str | None, room: Path) -> tuple[str, str] | None:
    """Whether a completed turn's session is the scenario's: turn 1's init carries a session id, and the result
    event the same one when it gives one (else `no_session_id`); a resumed turn's init carries the expected id
    and the room as its cwd, and its result the same id (else `wrong_session`). None when it is."""
    init = reading.get("init") or {}
    result = reading.get("result") or {}
    sid = init.get("session_id")
    if k == 1:
        if not sid:
            return "no_session_id", "turn 1's init event carries no session id"
        if result.get("session_id") and result["session_id"] != sid:
            return "no_session_id", (f"turn 1's init and result events carry different session ids "
                                     f"({sid} and {result['session_id']})")
        return None
    if sid != expected:
        return "wrong_session", f"the resumed init carries session {sid!r}, not {expected!r}"
    if result.get("session_id") and result["session_id"] != expected:
        return "wrong_session", f"the resumed result carries session {result['session_id']!r}, not {expected!r}"
    if not same_dir(init.get("cwd"), room):
        return "wrong_session", f"the resumed init's cwd is {init.get('cwd')!r}, not the room {str(room)!r}"
    return None


def same_dir(a, b) -> bool:
    return bool(a) and os.path.realpath(str(a)) == os.path.realpath(str(b))


def calls_lines(path) -> list[str]:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").splitlines() if path else []
    except OSError:
        return []


def parsed_lines(lines: list[str]) -> list[dict]:
    out = []
    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            out.append(item)
    return out


def file_key(entry: dict) -> str:
    return f"{entry.get('base', 'room')}/{entry.get('path', '')}"


def changed_files(before: list[dict] | None, after: list[dict] | None) -> list[str]:
    """The files a turn wrote or changed: in its snapshot and not in the previous turn's, or with another
    sha256 (`<base>/<path>`, in the snapshot's order)."""
    was = {file_key(e): e.get("sha256") for e in before or [] if isinstance(e, dict)}
    return [file_key(e) for e in after or [] if isinstance(e, dict) and was.get(file_key(e), object()) != e.get("sha256")]


def find_file(files: list[dict], name: str) -> dict | None:
    """The inventory entry a script names (`file:<name>`, `require_file`): its path, or its file name, the
    room's before the scratchpad's."""
    matches = [e for e in files or [] if isinstance(e, dict)
               and (e.get("path") == name or Path(str(e.get("path", ""))).name == name)]
    matches.sort(key=lambda e: e.get("base") != "room")
    return matches[0] if matches else None


def file_text(out: Path, entry: dict) -> str | None:
    """A snapshot copy's text, as the graders' view reads a produced file (run_fixtures.collect_artifacts:
    text suffixes only, cut at MAX_ARTIFACT); None for any other file or a copy that cannot be read."""
    if Path(str(entry.get("path", ""))).suffix.lower() not in run_fixtures.TEXT_SUFFIXES or not entry.get("copy"):
        return None
    path = Path(entry["copy"]) if Path(entry["copy"]).is_absolute() else out / entry["copy"]
    try:
        return path.read_text(encoding="utf-8")[:run_fixtures.MAX_ARTIFACT]
    except (OSError, UnicodeDecodeError):
        return None


def turn_body(out: Path, chat: str, files: list[dict], changed: list[str], reads: list[str]) -> tuple[str, list[str]]:
    """A turn's body, the text its checks and graders read: the chat, then, under the fixture runner's marker
    (`----- file the response produced: <name> -----`), each file its `reads` names — every file the turn
    changed (`files_changed`), and each `file:<name>` whole, as the turn's snapshot holds it. Returns the
    body and the inventory keys shown."""
    shown, parts = [], [chat]
    wanted = [e for e in files or [] if "files_changed" in reads and file_key(e) in changed]
    for item in reads:
        if item.startswith("file:"):
            entry = find_file(files, item[5:])
            if entry is not None and entry not in wanted:
                wanted.append(entry)
    for entry in wanted:
        text = file_text(out, entry)
        if text is None:
            continue
        parts.append(f"----- file the response produced: {Path(str(entry['path'])).name} -----\n{text}")
        shown.append(file_key(entry))
    return "\n\n".join(parts), shown


def write_text(path: Path, text: str) -> None:
    """A text file written atomically, as run_fixtures.write_json writes JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{id(text)}.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def rel(out: Path, path) -> str:
    path = Path(path)
    try:
        return path.relative_to(out).as_posix()
    except ValueError:
        return str(path)


# --- Selection ----------------------------------------------------------------------------------

def bank_question_ids(body: str) -> list[tuple[str, str]]:
    """The question IDs a body's question-bank tables show, in document order, each once, with the source it
    was read from (`chat` or the produced file's name): the tables with Provenance and Answer guidance
    columns, as the quotes check finds them (output_checks.check_quotes), their first cell an ID."""
    found, seen = [], set()
    for source, text in output_checks.split_response(body):
        for table in output_checks.md_tables(text):
            names = output_checks.header_names(table)
            if not (any("provenance" in h for h in names) and any("answer guidance" in h for h in names)):
                continue
            for cells in table["rows"]:
                qid = cells[0].replace("`", "").replace("*", "").strip() if cells else ""
                if QUESTION_ID.match(qid) and qid not in seen:
                    seen.add(qid)
                    found.append((qid, source))
    return found


def select_text(turn: dict, bodies: dict[int, str]) -> tuple[str | None, dict, dict, str | None]:
    """A later turn's text with its placeholders filled from the earlier turns' saved bodies; pure.
    Returns (text, selected values, where each was read, failure): text None and a failure reason when a
    selector finds fewer IDs than its pick needs (the reply lacked a selectable ID: `selection_failed`)."""
    values, sources = {}, {}
    for placeholder, sel in turn.get("select", {}).items():
        ids = bank_question_ids(bodies.get(sel["turn"], ""))
        picks = sel["pick"] if isinstance(sel["pick"], list) else [sel["pick"]]
        if max(picks) >= len(ids):
            return None, values, sources, (f"{{{placeholder}}} picks question {max(picks) + 1} of turn {sel['turn']}'s "
                                           f"question banks, and they show {len(ids)} ID(s)")
        chosen = [ids[p] for p in picks]
        values[placeholder] = ", ".join(q for q, _ in chosen)
        sources[placeholder] = {"turn": sel["turn"], "from": sel["from"], "pick": sel["pick"],
                                "sources": list(dict.fromkeys(s for _, s in chosen))}
    text = PLACEHOLDER.sub(lambda m: values.get(m.group(1), m.group(0)), turn["text"])
    return text, values, sources, None


# --- Running one scenario ----------------------------------------------------------------------

def utc_now() -> str:
    return run_fixtures.utc_now()


def transcript_path(out: Path, stem: str) -> Path:
    return out / f"{stem}.transcript.json"


def turn_path(out: Path, stem: str, k: int, first: bool = False) -> Path:
    return out / f"{stem}.turn{k}{'.first' if first else ''}.json"


def save_record(out: Path, record: dict) -> None:
    run_fixtures.write_json(transcript_path(out, record["stem"]), record)


def send_turn(ctx: dict, attempt: dict, k: int, text: str, extra: dict | None = None) -> dict:
    """Send one turn in an attempt's room and save it before anything else is sent: its body
    (`<stem>.turn<k>.md`) and its record (`<stem>.turn<k>.json`, or `.turn1.first.json` for an unnudged
    first attempt that is kept and never graded). The record holds the turn's outcome (run_outcome, then the
    fire on turn 1, the session, and the room), its research log built from the call-log lines it added
    (`calls_offset`), the files it changed, its stream's evidence and its per-turn reading. Returns the
    record."""
    out, room, stem = ctx["out"], attempt["room"], ctx["stem"]
    calls_path = room.paths["calls"] if room.paths else None
    start = len(calls_lines(calls_path))
    flags_extra = ["--resume", ctx["record"]["session_id"]] if k > 1 else []
    label = f"{attempt['label']}.t{k}"
    started, clock = utc_now(), time.monotonic()
    invocation, parsed = run_fixtures.run_attempt(
        text, room, out, ctx["timeout"], ctx["skill"], ctx["via"], ctx["layout"], ctx["mode"], attempt["nudged"],
        label=label, extra_args=flags_extra, pass_id=ctx["pass_id"], stem=stem)
    seconds = round(time.monotonic() - clock, 1)
    marker = invocation.pop("inflight", None)
    lines = calls_lines(calls_path)
    slice_ = parsed_lines(lines[start:])
    research = run_fixtures.build_research_log(parsed["tool_calls"], parsed["result"]["permission_denials"], slice_)
    reading = read_stream(run_fixtures.read_back(out / invocation["stream"]))
    files = invocation.get("files") or []
    changed = changed_files(attempt["inventory"], files)
    outcome, why = run_outcome(k, invocation["outcome"], invocation.get("returncode"), reading,
                               invocation.get("stderr_head", ""), invocation.get("limit_hit", False),
                               invocation.get("error"))
    reader_outcome = invocation.get("fire")
    fire = reader_outcome if k == 1 else attempt["fire"]
    scored, kept_first, room_status = False, False, None
    if outcome == "completed" and k == 1:
        attempt["fire"] = fire
        if reader_outcome == "void":
            outcome, why = "void", "the init event lists a Tuesday skill this room did not install"
        elif fire != "fired" and not attempt["nudged"]:
            kept_first, why = True, f"the installed skill did not fire ({fire}): kept, and nudged in a fresh room"
        elif fire != "fired":
            why = f"the nudged attempt did not fire the installed skill either ({fire})"
    if outcome == "completed" and k > 1 and ctx["via"] == "tuesday" and reader_outcome == "void":
        outcome, why = "void", "the resumed init lists a Tuesday skill this room did not install"
    if outcome == "completed" and fire == "fired":
        problem = session_problem(k, reading, ctx["record"].get("session_id"), room.room)
        if problem:
            outcome, why = problem
    if outcome == "completed" and fire == "fired":
        # A resumed turn inherits turn 1's fire: the room is read for its mode only (classify_room).
        room_status, reasons = run_fixtures.classify_room(ctx["mode"], {**invocation, "fire": "fired"}, slice_)
        if room_status != "ok":
            outcome, why = "room_invalid", "; ".join(reasons)
        else:
            scored = True
    body_name, chars, shown = None, None, []
    if invocation["outcome"] == "completed" and not kept_first:
        body, shown = turn_body(out, parsed["text"], files, changed, ctx["script"]["turns"][k - 1]["reads"])
        body_name = f"{stem}.turn{k}.md"
        write_text(out / body_name, body)
        chars = len(body)
    refused_, save_refused = run_fixtures.refusals(invocation)
    result_event = reading["result"] or {}
    cost = result_event.get("total_cost_usd")
    spec = ctx["script"]["turns"][k - 1]
    record = {
        "stem": stem, "turn": k, "attempt": attempt["label"], "label": label, "sent": text,
        "sent_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), **(extra or {}),
        "resume_of": ctx["record"]["session_id"] if k > 1 else None, "flags": invocation["flags"],
        "started": started, "ended": utc_now(), "seconds": seconds,
        "outcome": outcome, "scored": scored, "unscored_reason": None if scored else why,
        "run_outcome": invocation["outcome"], "error": invocation.get("error"),
        "returncode": invocation.get("returncode"), "stderr_head": invocation.get("stderr_head"),
        "stream": invocation["stream"], "stream_sha256": invocation["stream_sha256"],
        "stream_unparsed": reading["unparsed"], "init_sha256": invocation.get("init_sha256"),
        "session_id": (reading["init"] or {}).get("session_id"),
        "cwd_ok": same_dir((reading["init"] or {}).get("cwd"), room.room),
        "result": {key: parsed["result"].get(key) for key in ("subtype", "is_error", "num_turns", "session_id",
                                                             "incomplete")},
        "cost_usd": cost if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None,
        "limit_hit": invocation.get("limit_hit", False),
        "calls_log": invocation.get("calls_log"), "calls_offset": [start, len(lines)], "research_log": research,
        "files": files, "files_changed": changed, "files_shown": shown,
        "partial_evidence": invocation.get("partial_evidence", False),
        "fire": fire, "reader_outcome": reader_outcome, "hidden_reached": invocation.get("hidden_reached", []),
        "room_status": room_status, "refused": refused_, "save_refused": save_refused,
        "room": invocation["room"], "installed": invocation["installed"], "skill_dir": invocation["skill_dir"],
        "names": invocation.get("names"), "via": ctx["via"], "layout": ctx["layout"], "nudged": attempt["nudged"],
        "init": invocation.get("init"), "tool_calls": invocation.get("tool_calls"),
        "delivers": spec["delivers"], "reads": spec["reads"], "checks": spec["checks"],
        "response_file": body_name, "chars": chars,
        "pass_id": ctx["pass_id"], "script_sha256": ctx["script"]["sha256"]}
    run_fixtures.write_json(turn_path(out, stem, k, first=kept_first), record)
    if marker:
        run_fixtures.clear_inflight(out, [marker])
    attempt["inventory"] = files
    attempt["turns"].append(k)
    attempt["hidden_reached"] += [h for h in record["hidden_reached"] if h not in attempt["hidden_reached"]]
    if k == 1:
        attempt["session_id"] = record["session_id"]
    record["kept_first"] = kept_first
    print(run_fixtures.masked(f"  {stem} turn {k} [{attempt['label']}]: {outcome}"
                              f"{'' if scored or kept_first else ' (unscored: ' + str(why)[:160] + ')'}"
                              f"{' — did not fire, nudging' if kept_first else ''}, {seconds}s"), flush=True)
    return record


def attempt_summary(out: Path, attempt: dict) -> dict:
    return {"label": attempt["label"], "room": rel(out, attempt["room"].room), "nudged": attempt["nudged"],
            "installed": attempt["room"].name, "fire": attempt["fire"], "session_id": attempt.get("session_id"),
            "turns": list(attempt["turns"]), "hidden_reached": list(attempt["hidden_reached"])}


def new_attempt(label: str, room: run_fixtures.Room, nudged: bool) -> dict:
    return {"label": label, "room": room, "nudged": nudged, "fire": None, "session_id": None, "turns": [],
            "inventory": [], "hidden_reached": []}


def not_reached_record(ctx: dict, k: int, outcome: str, why: str, extra: dict | None = None) -> dict:
    """The record of a turn a scored scenario never sent: `selection_failed` (the turn whose text could not be
    written) or `not_reached` (the turns after it). Scored: its expectations and declared checks read FAIL."""
    spec = ctx["script"]["turns"][k - 1]
    record = {"stem": ctx["stem"], "turn": k, "attempt": None, "sent": None, **(extra or {}), "outcome": outcome,
              "scored": True, "unscored_reason": None, "not_reached": why, "delivers": spec["delivers"],
              "reads": spec["reads"], "checks": spec["checks"], "response_file": None,
              "pass_id": ctx["pass_id"], "script_sha256": ctx["script"]["sha256"], "ended": utc_now()}
    run_fixtures.write_json(turn_path(ctx["out"], ctx["stem"], k), record)
    return record


def execute_scenario(skill: str, script: dict, out: Path, mode: str, run: int, timeout: int, model: str | None,
                     via: str = "skill", layout: str | None = None, on: datetime.date | None = None, *,
                     pass_id: str | None = None) -> dict:
    """Run one scenario: turn 1 in a fresh room (and once more, nudged, in another when the first attempt did
    not fire), then each later turn resumed in the graded attempt's session, saving each turn before the next.
    The scenario record, `<stem>.transcript.json`, is written `running` before turn 1 and rewritten after every
    turn, its count of completed turns included; it ends `complete` (every turn sent) or `stopped`, with its
    outcome (SCENARIO_OUTCOMES) and reason. The sentinel scan over every attempt and turn is written to
    `<stem>.scan.json` (scan_scenario) after every saved turn and again at the end, so a scenario the driver
    is killed in keeps the scan of what it saved; a scenario declaring sentinels whose evidence is incomplete
    is harness-invalid, unless it was killed or set aside first. Every record and printed line has the
    runtime account email masked. Returns the record."""
    layout = layout or ("plugin" if via == "tuesday" else "project")
    if via == "tuesday" and layout != "plugin":
        raise ValueError("the front door is installed as the plugin it ships as: layout plugin")
    on = on or datetime.date.today()
    sd = dated(script, on)
    stem = stem_for(skill, script, mode, run)
    turns = sd["turns"]
    record = {"stem": stem, "skill": skill, "script_id": script["id"], "script_index": script["index"],
              "script_sha256": script["sha256"], "mode": mode, "run": run, "run_date": on.isoformat(),
              "model": model, "via": via, "layout": layout, "pass_id": pass_id, "status": "running",
              "outcome": None, "reason": None, "stopped_at_turn": None, "session_id": None, "nudged": False,
              "stop_cause": None, "graded_attempt": None, "attempts": [], "turns_planned": len(turns),
              "turns_completed": 0,
              "declared_watch_out": None, "started": utc_now(), "ended": None}
    save_record(out, record)
    ctx = {"out": out, "skill": skill, "script": sd, "mode": mode, "via": via, "layout": layout,
           "timeout": timeout, "pass_id": pass_id, "stem": stem, "record": record}
    attempts = []

    def keep(attempt: dict) -> None:
        record["attempts"] = [attempt_summary(out, a) for a in attempts]
        save_record(out, record)

    def saved() -> None:
        # After each saved turn: the scenario record with its count, and the scan of what was sent so far.
        save_record(out, record)
        scan_scenario(out, script, record)

    def stop(outcome: str, reason: str | None, k: int | None, cause: str | None = None) -> None:
        # `stop_cause`: the turn outcome (or not_fired, sentinel_scan) that decided a scenario not scored.
        record.update(outcome=outcome, reason=reason, stopped_at_turn=k, stop_cause=cause)

    prompt = turns[0]["prompt"]
    room = run_fixtures.prepare_room(skill, sd, out, mode, via, layout, False, which="first", model=model,
                                     prefix=room_prefix(script))
    record["declared_watch_out"] = run_fixtures.installed_watch_out(skill, room, via)
    graded = new_attempt("first", room, False)
    attempts.append(graded)
    t1 = send_turn(ctx, graded, 1, prompt)
    keep(graded)
    scan_scenario(out, script, record)
    if t1["kept_first"]:
        room = run_fixtures.prepare_room(skill, sd, out, mode, via, layout, True, which="nudged", model=model,
                                         prefix=room_prefix(script))
        graded = new_attempt("nudged", room, True)
        attempts.append(graded)
        record["nudged"] = True
        t1 = send_turn(ctx, graded, 1, f"Use the {room.name} skill for this.\n\n{prompt}")
        keep(graded)
        scan_scenario(out, script, record)
    record["graded_attempt"] = graded["label"]
    if t1["outcome"] == "completed" and t1["fire"] != "fired":
        stop("harness_invalid", f"not fired: {t1['unscored_reason']}", 1, "not_fired")
    elif t1["outcome"] != "completed":
        stop(SCENARIO_OF[t1["outcome"]], f"{OUTCOME_WORDS[t1['outcome']]} at turn 1: {t1['unscored_reason']}", 1,
             t1["outcome"])
    else:
        record["session_id"] = t1["session_id"]
        record["turns_completed"] = 1
        saved()
        bodies = {1: (out / t1["response_file"]).read_text()}
        for spec in turns[1:]:
            k = spec["n"]
            text, values, sources, failure = select_text(spec, bodies)
            if text is None:
                not_reached_record(ctx, k, "selection_failed", failure,
                                   {"select": spec["select"], "selected": values, "selected_from": sources})
                for later in turns[k:]:
                    not_reached_record(ctx, later["n"], "not_reached", f"turn {k}'s selection failed: {failure}")
                stop("scored", f"selection failed at turn {k}: {failure}", k)
                print(run_fixtures.masked(f"  {stem} turn {k}: selection_failed ({failure}); turns {k}-{len(turns)} "
                                          f"not reached"), flush=True)
                break
            tk = send_turn(ctx, graded, k, text, {"select": spec["select"], "selected": values,
                                                    "selected_from": sources})
            keep(graded)
            if tk["outcome"] != "completed":
                stop(SCENARIO_OF[tk["outcome"]], f"{OUTCOME_WORDS[tk['outcome']]} at turn {k}: "
                                                 f"{tk['unscored_reason']}", k, tk["outcome"])
                break
            record["turns_completed"] = k
            saved()
            bodies[k] = (out / tk["response_file"]).read_text()
        else:
            stop("scored", None, None)
    record["status"] = "complete" if record["outcome"] == "scored" and record["stopped_at_turn"] is None \
        else "stopped"
    scan = scan_scenario(out, script, record)
    if scan is not None and script.get("sentinels") and scan["sentinel_scan"]["status"] == "unscored" \
            and record["outcome"] == "scored":
        # Killed and set aside come first; an incomplete scan leaves an otherwise scored scenario out.
        missing = scan["sentinel_scan"]["missing"]
        stop("harness_invalid", "sentinel scan: " + "; ".join(missing), record["stopped_at_turn"], "sentinel_scan")
        record["status"] = "stopped"
        scan = scan_scenario(out, script, record)
    record["ended"] = utc_now()
    keep(graded)
    print(run_fixtures.masked(f"  {stem}: {record['outcome']}" + (f" — {record['reason']}" if record["reason"] else "")
                              + (" (nudged)" if record["nudged"] else "")), flush=True)
    return record


# --- Sentinel scan over a scenario ---------------------------------------------------------------

TURN_FILE = re.compile(r"^(?P<stem>.+?\.run\d+)(?:~[^.]+)?\.turn(?P<k>\d+)(?P<first>\.first)?\.json$")


def turn_records(folder: Path, stem: str | None = None) -> list[tuple[Path, dict]]:
    """The turn records in a folder (`<stem>.turn<k>.json`, `<stem>.turn1.first.json`, and in killed/ the same
    names suffixed `~<pass id>`), of one stem or all, in stem, attempt and turn order."""
    found = []
    pattern = f"{stem}*.turn*.json" if stem else "*.turn*.json"
    for path in folder.glob(pattern):
        match = TURN_FILE.match(path.name)
        if not match or (stem and match.group("stem") != stem):
            continue
        data = run_fixtures.read_json_file(path)
        if isinstance(data, dict):
            found.append((path, data))
    # The first attempt's turns before the nudged one's, each in turn order: the order the scenario sent them,
    # which credits a file version to the first turn it appeared in (scan_scenario).
    found.sort(key=lambda pd: (pd[0].name.split(".turn")[0], pd[1].get("attempt") != "first",
                               pd[1].get("turn") or 0, pd[0].name))
    return found


def turn_evidence(out: Path, turn: dict, canned: bool) -> dict:
    """One sent turn as the sentinel scan reads an attempt (output_checks.scan_sentinels): its saved stream's
    every event, its share of the canned server's call log (`calls_offset`), and its file snapshot."""
    stream = out / turn["stream"] if turn.get("stream") else None
    events = run_fixtures.read_events(stream) if stream and stream.is_file() else None
    calls = None
    if turn.get("calls_log"):
        log = Path(turn["calls_log"])
        found = next((p for p in (log, out / "research" / log.name) if p.is_file()), None)
        if found:
            start, end = (turn.get("calls_offset") or [0, None])[:2]
            calls = parsed_lines(calls_lines(found)[start:end])
    return {"label": turn.get("label") or f"{turn.get('attempt')}.t{turn.get('turn')}",
            "outcome": turn.get("outcome"), "events": events,
            "complete": any(e.get("type") == "result" for e in events or []),
            "calls_log": calls, "canned": canned,
            "files": run_fixtures.inventory_texts(out, {"files": turn.get("files"), "room": turn.get("room")})}


def scan_scenario(out: Path, script: dict, record: dict, turns: list[dict] | None = None,
                  path: Path | None = None) -> dict | None:
    """The scenario's sentinel scan over every attempt and turn it sent, first, nudged, cut and killed alike
    (each labelled `<attempt>.t<k>`; a file version is scanned once and credited to the first turn it
    appeared in), written to `path` (`<out>/<stem>.scan.json` by default) with its findings, the scenario's
    outcome and a status that is ok only for a scored scenario, which the planted-event report reads
    (run_fixtures.sentinel_report). None, and nothing written, when the script declares no sentinels and no
    runtime sentinel is set (output_checks.runtime_sentinels, never written)."""
    runtime = output_checks.runtime_sentinels(os.environ)
    if not script.get("sentinels") and not runtime:
        return None
    if turns is None:
        turns = [t for _, t in turn_records(out, record["stem"])]
    attempts = [turn_evidence(out, t, record.get("mode") == "canned") for t in turns if t.get("stream")]
    result = output_checks.scan_sentinels(script.get("sentinels") or [], attempts, runtime or None)
    data = {"stem": record["stem"], "skill": record.get("skill"), "script_id": record.get("script_id"),
            "run": record.get("run"), "mode": record.get("mode"),
            "status": "ok" if record.get("outcome") == "scored" else "harness-invalid",
            "outcome": record.get("outcome"), "checks": result["checks"], "info": result["info"],
            "unchecked": result["unchecked"], "sentinel_scan": result["scan"]}
    run_fixtures.write_json(path or out / f"{record['stem']}.scan.json", data)
    return data


# --- Checks per turn ------------------------------------------------------------------------------

def cumulative_request(script: dict, sent: dict[int, str], k: int) -> str:
    """The request a turn's checks read: turn 1's prompt and every text sent through turn k."""
    return "\n\n".join([script["turns"][0]["prompt"], *(sent[j] for j in range(2, k + 1) if sent.get(j))])


def check_no_watch_out(response: str, declared: str | None) -> dict:
    """A turn inside an exchange (`delivers: no_watch_out`, a drill turn) carries no watch-out: no chat line
    labelled one and the declared sentence nowhere in the chat (output_checks.watch_out_in_chat)."""
    found = output_checks.watch_out_in_chat(response, declared)
    why = (f"this turn carries no watch-out, and the chat holds {found[0]}"
           + (f" (and {len(found) - 1} more)" if len(found) > 1 else "")) if found else \
        "the chat carries no watch-out line and no watch-out sentence"
    return {"checks": [output_checks.finding(NO_WATCH_OUT_CHECK, "chat", not found, why)], "info": [], "unchecked": []}


def check_turn_file(name: str, files: list[dict], changed: list[str]) -> dict:
    """A turn that must leave a file (`require_file`) wrote or changed it in this turn."""
    entry = find_file(files, name)
    if entry is None:
        ok, why = False, f"no file {name} after this turn: the room and its scratchpad hold none"
    elif file_key(entry) not in changed:
        ok, why = False, f"{name} is there, unchanged by this turn: an earlier turn wrote it"
    else:
        ok, why = True, f"this turn wrote {file_key(entry)}"
    return {"checks": [output_checks.finding(TURN_FILE_CHECK, name, ok, why)], "info": [], "unchecked": []}


def check_turn(script: dict, k: int, mode: str, body: str, request: str, turn_log: list | None,
               all_log: list | None, files: list[dict], changed: list[str], declared: str | None) -> dict:
    """One turn's deterministic checks, as a fixture run's (output_checks.run_checks) with three turn rules:
    the request is the cumulative user text (cumulative_request), so a later turn quoting a turn-1 line quotes
    the request, and the candidate's material is the candidate_text entries said by this turn; the research
    accounting runs only where the turn declares it (`accounting`), on this turn's research log, while a canned
    room's quotable pages are every page returned so far; and `delivers` picks the watch-out rule (the declared
    line for output, check_gate_only over the files this turn changed for a gate question, check_no_watch_out
    inside an exchange). A turn requiring a file (`require_file`) is checked for it (check_turn_file)."""
    spec = script["turns"][k - 1]
    wanted = spec["checks"]
    research = script.get("research") or {}
    said = output_checks.normalise_quote(request)
    candidate = script.get("candidate_text")
    candidate = [e for e in candidate if output_checks.normalise_quote(e) in said] if isinstance(candidate, list) \
        else None
    parts = []
    if spec["delivers"] == output_checks.GATE_QUESTION:
        changed_entries = [e for e in files if file_key(e) in changed]
        parts.append(output_checks.check_gate_only(body, changed_entries, declared))
    elif spec["delivers"] == NO_WATCH_OUT:
        parts.append(check_no_watch_out(body, declared))
    elif declared:
        parts.append(output_checks.check_watch_out(body, declared))
    else:
        parts.append({"checks": [], "unchecked": ["watch_out"],
                      "info": ["the skill declares no watch_out line: the watch-out line is unchecked"]})
    if ACCOUNTING in wanted and research:
        parts.append(output_checks.check_accounting(body, research, mode, turn_log, request,
                                                    yes_pages=output_checks.YES_PAGES_CHECK in wanted))
    if "fit_ledger" in wanted:
        parts.append(output_checks.check_fit_ledger(body, script.get("candidate_constraints"), fixture=True))
    if "quotes" in wanted:
        corpus = output_checks.room_pages_text([*research.get("pages", []), *research.get("user_pages", [])],
                                               all_log) if mode == "canned" else []
        parts.append(output_checks.check_quotes(body, request, corpus, candidate))
    if output_checks.TRACES_CHECK in wanted:
        parts.append(output_checks.check_traces(body, candidate, request))
    if spec.get("require_file"):
        parts.append(check_turn_file(spec["require_file"], files, changed))
    checks, info, unchecked = [], [], []
    for part in parts:
        checks += part["checks"]
        info += part["info"]
        unchecked += part["unchecked"]
    failed = any(c["verdict"] == "FAIL" and c.get("kind") != "report" for c in checks)
    return {"status": "fail" if failed else ("uncheckable" if unchecked else "ok"), "mode": mode, "checks": checks,
            "info": info, "unchecked": unchecked}


def declared_check_names(spec: dict) -> list[str]:
    """The checks a turn declares, by the names its record carries: its `checks`, its watch-out rule's, and
    turn_file where it requires a file."""
    rule = {output_checks.GATE_QUESTION: output_checks.GATE_CHECK, NO_WATCH_OUT: NO_WATCH_OUT_CHECK}.get(
        spec["delivers"], "watch_out")
    return [*spec["checks"], rule, *([TURN_FILE_CHECK] if spec.get("require_file") else [])]


def not_reached_checks(spec: dict, k: int, why: str, mode: str) -> dict:
    """A turn a scored scenario never sent: each check it declares reads FAIL, so a missing turn never passes
    the checks it kept from applying."""
    checks = [output_checks.finding(name, "not_reached", False, f"turn {k} was not reached: {why}")
              for name in declared_check_names(spec)]
    return {"status": "fail", "mode": mode, "checks": checks, "info": [f"turn {k} not reached: {why}"],
            "unchecked": []}


def check_scenario(out: Path, script: dict, stem: str) -> list[dict]:
    """Write `<stem>.turn<k>.checks.json` for every turn the scenario recorded: check_turn on a scored turn,
    every declared check FAIL on a turn not reached, and a harness-invalid record on a turn that is not
    behaviour (a timeout, a refused resume, the unnudged first attempt is not checked). The sentinel scan is
    rewritten from the saved evidence (scan_scenario). Returns the records."""
    record = run_fixtures.read_json_file(transcript_path(out, stem))
    if not isinstance(record, dict):
        return []
    sd = dated(script, run_fixtures.run_date(record) or datetime.date.today())
    line = (record.get("declared_watch_out") or {}).get("line")
    turns = {t["turn"]: t for p, t in turn_records(out, stem) if ".first" not in p.name}
    sent, logs, written = {}, [], []
    for k in sorted(turns):
        turn = turns[k]
        spec = sd["turns"][k - 1]
        if turn.get("sent") and k > 1:
            sent[k] = turn["sent"]
        if turn.get("research_log"):
            logs += turn["research_log"]
        base = {"skill": record.get("skill"), "script_id": record.get("script_id"), "run": record.get("run"),
                "stem": stem, "turn": k}
        if turn.get("outcome") in ("selection_failed", "not_reached"):
            result = not_reached_checks(spec, k, turn.get("not_reached") or turn["outcome"], record.get("mode"))
        elif turn.get("scored") and turn.get("response_file") and (out / turn["response_file"]).is_file():
            body = (out / turn["response_file"]).read_text()
            result = check_turn(sd, k, record.get("mode"), body, cumulative_request(sd, sent, k),
                                turn.get("research_log"), logs, turn.get("files") or [],
                                turn.get("files_changed") or [], line)
        else:
            result = {"status": "harness-invalid", "mode": record.get("mode"), "checks": [],
                      "info": [f"turn {k} {turn.get('outcome')}: {turn.get('unscored_reason')}"], "unchecked": []}
        result = {**base, **result}
        run_fixtures.write_json(out / f"{stem}.turn{k}.checks.json", result)
        written.append(result)
    scan_scenario(out, script, record)
    return written


# --- Grading ----------------------------------------------------------------------------------------

TRANSCRIPT_GRADER_PROMPT_VERSION = "t1"
TRANSCRIPT_GRADER_PROMPT_PREDECESSOR = run_fixtures.GRADER_PROMPT_VERSION

TRANSCRIPT_GRADER_PROMPT = """You are grading one turn of a conversation against a fixed list of expectations.

Grade adversarially. Your job is to find where the response falls short, not to
give it the benefit of the doubt. A partial satisfaction is a FAIL. An
expectation the response gestures at but does not actually do is a FAIL. Do not
reward length, confidence, or good intentions. You are not being asked whether
the response is good; you are being asked whether each specific expectation is
met by text actually present in the response.

You have not seen the skill that produced this and you do not need to. Judge the
response by its own text, never by what some other document might say. Two
records are given beside it. The conversation so far is what the user wrote in
each earlier turn and what the response gave them then, so this turn can be read
against what came before it; none of it is text this turn wrote. The harness's
account of the research this turn actually did has one use, stated where it
appears.

Four rules that are not about being lenient, but about grading the right thing:

- Your reason comes first and the verdict must follow from it. If the reason
  concludes the expectation is met, the verdict is PASS. Never follow a reason
  that concludes otherwise with FAIL.
- An expectation carrying a condition — "where research ran", "if X appears",
  "if the status is Y" — is PASS when the condition did not occur. A response is
  not failed for skipping something its own expectation made conditional.
- {research_mode}
- Every expectation is about something the response should DO. Do not fail one
  because the response also did something else you would have done differently.

## The conversation so far

{conversation}

Everything in this section is context: each earlier turn's user text and the response it got, as the harness saved it (the chat text, and the files that turn's record names under a `----- file the response produced -----` marker). An expectation is met only by text in the response to grade below. Where an expectation measures this turn against an earlier one (a question picked from the pack, feedback on the answer just given), read the earlier turn here.

## The request that was made

This is what the user wrote in this turn, turn {turn} of {turns}:

{prompt}{selected}

## The response to grade

This is everything this turn's response produced, between the line `{begins}` and the line `{ends}`. Nothing outside those two lines is text this turn wrote. Where it delivered by writing a file, that file's full contents appear below the chat text under a `----- file the response produced -----` marker, and it counts exactly as if it had been written inline.

{begins}
{response}
{ends}

## What the harness observed

{observed}

This record covers this turn only. It is ground truth for checking the response's claims about its own research in this turn: whether a search was sent, how many were, and whether each target's label matches what happened. It must never be used to supply content the response lacks — a page, a figure or a fact that appears only here does not count as the response having said it.

## The expectations

{expectations}

Return ONLY a JSON object, no prose around it:

{{"verdicts": [{{"n": 1, "why": "one sentence, quoting the response where it matters", "verdict": "PASS" or "FAIL"}}, ...]}}

One entry per expectation, under the number it is given above. The reason comes before the verdict in every entry.
"""

CONVERSATION_TURN = """===== TURN {n}: THE USER WROTE =====
{user}
===== TURN {n}: THE RESPONSE =====
{response}
===== END OF TURN {n} ====="""
CONVERSATION_NONE = "Nothing: this is the conversation's first turn."
SELECTED_NOTE = ("\n\n(The harness wrote {{{placeholder}}} as {value}: question {positions} of the question IDs that "
                 "turn {source}'s question banks show, in document order, read from {where}.)")

# The sha256 of version t1's text: the template, the research-mode lines it shares with version 3, and the
# blocks it is filled with, recorded in every grade beside the version.
TRANSCRIPT_GRADER_PROMPT_SHA256 = hashlib.sha256(json.dumps(
    [TRANSCRIPT_GRADER_PROMPT, run_fixtures.RESEARCH_MODE, CONVERSATION_TURN, CONVERSATION_NONE, SELECTED_NOTE],
    sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def conversation_block(earlier: list[tuple[str, str]]) -> str:
    if not earlier:
        return CONVERSATION_NONE
    return "\n\n".join(CONVERSATION_TURN.format(n=n, user=user, response=response)
                       for n, (user, response) in enumerate(earlier, 1))


def selected_block(turn: dict) -> str:
    notes = []
    for placeholder, where in (turn.get("selected_from") or {}).items():
        picks = where["pick"] if isinstance(where["pick"], list) else [where["pick"]]
        notes.append(SELECTED_NOTE.format(placeholder=placeholder, value=(turn.get("selected") or {}).get(placeholder),
                                          positions=", ".join(str(p + 1) for p in picks), source=where["turn"],
                                          where=", ".join(where.get("sources") or []) or "its body"))
    return "".join(notes)


def transcript_grader_prompt(script: dict, k: int, mode: str, earlier: list[tuple[str, str]], turn: dict,
                             body: str, observed: str, numbers: list[int]) -> str:
    """The t1 grader prompt for turn k: version 3's rules, the conversation so far (each earlier turn's user
    text and saved body, as its `reads` define it), this turn's sent text and how the harness wrote any
    selected ID, the response fenced between version 3's markers, this turn's research record, and the
    numbers asked."""
    expectations = "\n".join(f"{n}. {script['turns'][k - 1]['expectations'][n - 1]}" for n in numbers)
    user = script["turns"][0]["prompt"] if k == 1 else turn.get("sent") or ""
    return TRANSCRIPT_GRADER_PROMPT.format(
        research_mode=run_fixtures.RESEARCH_MODE[mode], conversation=conversation_block(earlier), turn=k,
        turns=len(script["turns"]), prompt=user, selected=selected_block(turn), begins=run_fixtures.RESPONSE_BEGINS,
        ends=run_fixtures.RESPONSE_ENDS, response=body, observed=observed, expectations=expectations)


def earlier_turns(out: Path, script: dict, stem: str, k: int) -> list[tuple[str, str]]:
    """Each turn before k, as the conversation block shows it: what the user wrote (turn 1's natural prompt)
    and the saved body."""
    found = []
    for j in range(1, k):
        turn = run_fixtures.read_json_file(turn_path(out, stem, j)) or {}
        body = (out / turn["response_file"]).read_text() if turn.get("response_file") and \
            (out / turn["response_file"]).is_file() else ""
        found.append((script["turns"][0]["prompt"] if j == 1 else turn.get("sent") or "", body))
    return found


def turn_observed(out: Path, stem: str, k: int, turn: dict, research: dict | None) -> str:
    """This turn's research record for the grader (run_fixtures.observed_block): its own calls only; on a
    nudged turn 1, the line saying the first attempt's calls are not credited to it."""
    meta = {"research_log": turn.get("research_log") or []}
    if k == 1 and turn.get("nudged"):
        first = run_fixtures.read_json_file(turn_path(out, stem, 1, first=True)) or {}
        meta.update(invocations=[{"research_log": first.get("research_log") or []}, {}], graded_invocation=1)
    return run_fixtures.observed_block(meta, research)


def grade_file(stem: str, k: int, grader: int) -> str:
    return f"{stem}.turn{k}.grade-{grader}.json"


def gradable(turn: dict | None) -> bool:
    return isinstance(turn, dict) and turn.get("outcome") == "completed" and bool(turn.get("scored")) \
        and bool(turn.get("response_file"))


def grade_turn(out: Path, script: dict, stem: str, k: int, grader: int, timeout: int, model: str | None, *,
               pass_id: str | None = None) -> dict | None:
    """Grade one saved turn with one grader, as run_fixtures.grade grades a fixture run (its flags, the CLI
    in json mode, parse_verdicts and the one targeted re-grade of the numbers a reply missed), with the t1
    prompt. Writes `<stem>.turn<k>.grade-<g>.json`, never over one already there; the record carries the
    turn, the pass, the prompt's version, predecessor and sha256, the pinned and answering models, and each
    expectation's hash before date expansion. None when the turn is not gradable or already graded."""
    path = out / grade_file(stem, k, grader)
    record = run_fixtures.read_json_file(transcript_path(out, stem)) or {}
    turn = run_fixtures.read_json_file(turn_path(out, stem, k))
    if path.exists() or not gradable(turn) or not (out / turn["response_file"]).is_file():
        return None
    template = script["turns"][k - 1]["expectations"]
    sd = dated(script, run_fixtures.run_date(record) or datetime.date.today())
    mode = record.get("mode") or "denied"
    body = (out / turn["response_file"]).read_text()
    earlier = earlier_turns(out, sd, stem, k)
    observed = turn_observed(out, stem, k, turn, sd.get("research"))
    numbers = list(range(1, len(template) + 1))
    flags = run_fixtures.grader_flags(model)
    room = out / "grading"
    room.mkdir(parents=True, exist_ok=True)

    def ask(asked: list[int]) -> tuple[dict, dict | None, str | None]:
        try:
            data = run_fixtures.claude(transcript_grader_prompt(sd, k, mode, earlier, turn, body, observed, asked),
                                       room, timeout, flags, "json")
            return run_fixtures.parse_verdicts(str(data.get("result") or ""), asked), data, None
        except RuntimeError as exc:
            print(run_fixtures.masked(f"  SKIPPED grading {stem} turn {k} (grader {grader}): {exc}"), flush=True)
            return run_fixtures.parse_verdicts("", asked), None, run_fixtures.masked(str(exc))

    result, data, declined = ask(numbers)
    usage = dict((data or {}).get("modelUsage") or {})
    regraded = []
    if result["incomplete"] and not declined:
        retry, extra, _ = ask(result["incomplete"])
        regraded = list(result["incomplete"])
        for key, value in (extra or {}).get("modelUsage", {}).items():
            usage.setdefault(f"{key} (re-grade)", value)
        merged = {v["n"]: v for v in result["verdicts"]}
        merged.update({v["n"]: v for v in retry["verdicts"]})
        result.update(verdicts=[merged[n] for n in sorted(merged)],
                      incomplete=[n for n in numbers if n not in merged], missing=list(retry["missing"]),
                      duplicates=sorted(set(result["duplicates"]) | set(retry["duplicates"])),
                      invalid=result["invalid"] + retry["invalid"])
        if merged:
            result.pop("error", None)
            result.pop("raw", None)
    if declined:
        result["error"] = declined
    grade = {"skill": record.get("skill"), "script_id": record.get("script_id"), "stem": stem,
             "run": record.get("run"), "mode": mode, "turn": k, "grader": grader, **result, "regraded": regraded,
             "grader_model": run_fixtures.model_of({key: v for key, v in usage.items() if "(re-grade)" not in key}),
             "model_usage": {key: {f: (v or {}).get(f) for f in ("inputTokens", "outputTokens", "costUSD")}
                             for key, v in usage.items()},
             "requested_model": model, "cli_version": run_fixtures.cli_version(), "flags": flags,
             "grader_prompt_version": TRANSCRIPT_GRADER_PROMPT_VERSION,
             "grader_prompt_predecessor": TRANSCRIPT_GRADER_PROMPT_PREDECESSOR,
             "grader_prompt_sha256": TRANSCRIPT_GRADER_PROMPT_SHA256, "pass_id": pass_id,
             "script_sha256": script["sha256"],
             "expectation_sha256": {str(n): run_fixtures.expectation_sha(template[n - 1]) for n in numbers}}
    if path.exists():
        return None             # another pass wrote it meanwhile: never overwritten
    run_fixtures.write_json(path, grade)
    verdicts = grade["verdicts"]
    if grade.get("error") or not verdicts:
        print(run_fixtures.masked(f"  no verdicts for {stem} turn {k} (grader {grader}): "
                                  f"{grade.get('error', 'nothing usable')}"), flush=True)
    else:
        gaps = f" (incomplete: {', '.join(map(str, grade['incomplete']))})" if grade["incomplete"] else ""
        print(f"  graded {stem} turn {k} (grader {grader}): "
              f"{sum(v.get('verdict') == 'PASS' for v in verdicts)}/{len(verdicts)} of {len(numbers)}{gaps}",
              flush=True)
    return grade


def grade_jobs(out: Path, script: dict, stem: str, graders: int) -> list[tuple[int, int]]:
    """The (turn, grader) pairs of a scenario that hold a gradable turn and no grade file. A killed scenario is
    recovered, not graded."""
    record = run_fixtures.read_json_file(transcript_path(out, stem))
    if not isinstance(record, dict) or record.get("outcome") == "killed" or record.get("status") == "running":
        return []
    jobs = []
    for k in range(1, len(script["turns"]) + 1):
        if gradable(run_fixtures.read_json_file(turn_path(out, stem, k))):
            jobs += [(k, g) for g in range(1, graders + 1) if not (out / grade_file(stem, k, g)).exists()]
    return jobs


# --- Grade gaps, recovery and the hidden-module count ----------------------------------------------

def grade_gaps(out: Path, graders: int) -> list[dict]:
    """Every expected grader of every gradable turn of every scenario in `out` (killed ones excepted) whose
    grade file is missing or misses an expected verdict, as run_fixtures.grade_gaps lists a fixture run's, with
    `turn` set (run_fixtures.grade_gap)."""
    gaps = []
    for path in sorted(out.glob("*.transcript.json")):
        stem = path.name[:-len(".transcript.json")]
        record = run_fixtures.read_json_file(path)
        if not isinstance(record, dict) or record.get("outcome") == "killed" or record.get("status") == "running":
            continue
        for tpath, turn in turn_records(out, stem):
            if ".first" in tpath.name or not gradable(turn) or not (out / turn["response_file"]).is_file():
                continue
            for g in range(1, graders + 1):
                gap = run_fixtures.grade_gap(out, stem, turn["turn"], g, grade_file(stem, turn["turn"], g))
                if gap:
                    gaps.append(gap)
    return gaps


def survey(out: Path, expected: list[str]) -> dict:
    """Classify each scenario of a folder per stem, never merged into one class: `killed` (a record left
    `running`, the driver ended by a restart or the owner's guard, or a usage-limit kill), `set_aside`,
    `harness_invalid` and `scored`; `never_started` lists the expected stems with no record and no in-flight
    attempt; `reasons` says why each killed one was. Precedence: killed, then set aside, then harness-invalid
    (a sentinel scan unscored)."""
    found = {"killed": [], "set_aside": [], "harness_invalid": [], "scored": [], "never_started": [],
             "unreadable": [], "reasons": {}}
    inflight = run_fixtures.inflight_records(out)
    seen = set()
    for path in sorted(out.glob("*.transcript.json")):
        stem = path.name[:-len(".transcript.json")]
        seen.add(stem)
        record = run_fixtures.read_json_file(path)
        if not isinstance(record, dict):
            found["unreadable"].append(stem)
        elif record.get("status") == "running":
            found["killed"].append(stem)
            found["reasons"][stem] = "the driver ended mid-scenario (a restart or the owner's guard)"
        elif record.get("outcome") in SCENARIO_OUTCOMES:
            found[record["outcome"]].append(stem)
            if record["outcome"] == "killed":
                found["reasons"][stem] = record.get("reason") or "killed"
        else:
            found["unreadable"].append(stem)
    for stem in inflight:
        if stem not in seen:
            seen.add(stem)
            found["killed"].append(stem)
            found["reasons"][stem] = "the driver ended before writing the scenario record"
    found["never_started"] = [s for s in expected if s not in seen]
    return found


def inflight_turn(out: Path, killed: Path, marker: dict, tag: str) -> dict:
    """A turn the driver was sending when it ended, kept as evidence: its stream moved to killed/streams/ as a
    partial (or, where the attempt had ended, kept where it is), its room's and scratchpad's files snapshotted
    as `partial_evidence`, and a turn record with outcome `killed`."""
    inv = dict(marker.get("invocation") or {})
    inv.pop("inflight", None)
    label = marker.get("label") or ""
    attempt, _, k = label.rpartition(".t")
    room = Path(inv.get("room") or "")
    if marker.get("state") != "ended":
        base = Path(marker.get("stream") or f"streams/{room.name}.{label}.inflight.jsonl").name[:-len(".inflight.jsonl")]
        source = out / (marker.get("stream") or "")
        dest = run_fixtures.unclaimed(killed / "streams" / f"{base}.partial.jsonl", tag)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if source.is_file():
            shutil.move(str(source), str(dest))
        else:
            dest.write_text("")
        text = run_fixtures.read_back(dest)
        parsed = run_fixtures.parse_stream(text.splitlines(), inv.get("installed") or "")
        skill_dir = Path(inv.get("skill_dir") or room / "none")
        files = run_fixtures.snapshot_files(room, skill_dir, run_fixtures.unclaimed(out / "files" / base, tag), out) \
            if room.is_dir() else None
        inv.update(stream=dest.relative_to(out).as_posix(), stream_sha256=run_fixtures.file_sha256(dest),
                   init_sha256=run_fixtures.save_init(out, parsed.get("init_event")), files=files,
                   init=parsed["init"], tool_calls=parsed["tool_calls"], result=parsed["result"],
                   session_id=(parsed.get("init_event") or {}).get("session_id"),
                   limit_hit=run_fixtures.stream_limit(text, "") is not None)
        if inv.get("via") == "tuesday":
            inv["hidden_reached"] = run_fixtures.hidden_reach_labels(text.splitlines(),
                                                                     run_fixtures.installed_names(inv), room)
    return {"stem": marker.get("stem"), "turn": int(k) if k.isdigit() else None, "attempt": attempt or None,
            "label": label, "outcome": "killed", "scored": False, "partial_evidence": True,
            "unscored_reason": "the driver ended while this turn was being sent (a restart or the owner's guard)",
            "run_outcome": inv.get("outcome") or "killed", "stream": inv.get("stream"),
            "stream_sha256": inv.get("stream_sha256"), "init_sha256": inv.get("init_sha256"),
            "session_id": inv.get("session_id"), "files": inv.get("files"), "calls_log": inv.get("calls_log"),
            "calls_offset": None, "hidden_reached": inv.get("hidden_reached", []), "room": inv.get("room"),
            "installed": inv.get("installed"), "names": inv.get("names"), "via": inv.get("via"),
            "layout": inv.get("layout"), "nudged": inv.get("nudged"), "flags": inv.get("flags"),
            "limit_hit": inv.get("limit_hit", False), "pass_id": marker.get("pass_id"), "started": marker.get("started"),
            "ended": None}


def recover_move(out: Path, found: dict, scripts: dict[str, dict], tag: str,
                 left: list[str] | None = None) -> tuple[list[str], Path | None]:
    """`--recover --move`: each killed scenario's files (`<stem>.transcript.json`, its turn records, bodies,
    checks and grades, `<stem>.scan.json`) go to killed/, never over a file there (`~<pass id>`). For a scenario
    the driver left `running`, the turn in flight is kept too (inflight_turn), the record is marked killed, and
    the sentinel scan over everything it sent, the cut turn included, is written beside it. Rooms, finished
    turns' streams, snapshots and research files are named by room and stay where they are. Writes
    killed/rerun-<UTC>.txt, the killed and never-started stems, for `--stems`. `scripts` maps a stem to its
    script. A scenario the driver left `running` whose script `scripts` does not hold is left as it is, its
    in-flight records in place, and appended to `left` (never listed for rerun): without its script the scan
    of its cut turn could not be written, and a leak in that killed session would be lost. Returns (moved,
    list)."""
    killed = out / "killed"
    killed.mkdir(parents=True, exist_ok=True)
    moved, recovered = [], []
    markers = run_fixtures.inflight_records(out)
    for stem in found["killed"]:
        record = run_fixtures.read_json_file(transcript_path(out, stem))
        running = not isinstance(record, dict) or record.get("status") == "running"
        if running and scripts.get(stem) is None:
            if left is not None:
                left.append(stem)
            continue
        recovered.append(stem)
        record = record if isinstance(record, dict) else {"stem": stem}
        turns = [t for _, t in turn_records(out, stem)]
        # An attempt whose turn record was saved before the driver ended (its in-flight record not yet cleared)
        # is not kept twice.
        saved = {t.get("stream") for t in turns}
        flying = [inflight_turn(out, killed, m, tag) for _, m in markers.get(stem, [])
                  if not (m.get("state") == "ended" and (m.get("invocation") or {}).get("stream") in saved)]
        placed = {}
        for name in run_fixtures.stem_files(out, stem):
            dest = run_fixtures.unclaimed(killed / name, tag)
            shutil.move(str(out / name), str(dest))
            placed[name] = dest
        if running:
            record.update(status="stopped", outcome="killed", stop_cause="killed",
                          reason=found["reasons"].get(stem),
                          stopped_at_turn=next((t["turn"] for t in flying if t["turn"]), record.get("stopped_at_turn")),
                          recovered=utc_now())
            path = placed.get(f"{stem}.transcript.json") or run_fixtures.unclaimed(killed / f"{stem}.transcript.json", tag)
            run_fixtures.write_json(path, record)
            placed[f"{stem}.transcript.json"] = path
            for turn in flying:
                if turn["turn"] is not None:
                    dest = run_fixtures.unclaimed(killed / f"{stem}.turn{turn['turn']}.json", tag)
                    run_fixtures.write_json(dest, turn)
                    placed[dest.name] = dest
            # The scan over everything it sent, the cut turn included, in place of the one written after its
            # last saved turn (moved above with its files), which it covers.
            dest = placed.get(f"{stem}.scan.json") or run_fixtures.unclaimed(killed / f"{stem}.scan.json", tag)
            if scan_scenario(out, scripts[stem], record, turns + flying, path=dest) is not None:
                placed[f"{stem}.scan.json"] = dest
        moved += sorted(p.relative_to(out).as_posix() for p in placed.values())
        for path, _ in markers.get(stem, []):
            path.unlink(missing_ok=True)
    rerun = [*recovered, *found["never_started"]]
    if not rerun:
        return moved, None
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    listing = run_fixtures.unclaimed(killed / f"rerun-{stamp}.txt", tag)
    listing.write_text("".join(f"{s}\n" for s in rerun))
    return moved, listing


def hidden_reaches(out: Path) -> dict:
    """E16 over the transcripts in `out` and `out/killed/`: the hidden-module reaches in every turn of every
    attempt through the front door, first, nudged, cut and killed alike, each saved stream read whole
    (run_fixtures.hidden_reach_labels). Returns {"attempts", "turns", "reaches": [(stem, label, reach)],
    "unread": [(stem, label)]}."""
    attempts, turns, reaches, unread = set(), 0, [], []
    for folder in (out, out / "killed"):
        for _, turn in turn_records(folder):
            if turn.get("via") not in run_fixtures.FRONT_DOOR_VIAS or not turn.get("label"):
                continue
            stem = turn.get("stem")
            attempts.add((stem, str(turn.get("label")).rpartition(".t")[0], turn.get("room")))
            turns += 1
            stream = out / turn["stream"] if turn.get("stream") else None
            if stream is not None and stream.is_file():
                labels = run_fixtures.hidden_reach_labels(run_fixtures.read_events(stream),
                                                          run_fixtures.installed_names(turn),
                                                          Path(turn.get("room") or "."))
            elif isinstance(turn.get("hidden_reached"), list):
                labels = turn["hidden_reached"]
            else:
                unread.append((stem, turn.get("label")))
                continue
            reaches += [(stem, turn.get("label"), label) for label in labels]
    return {"attempts": len(attempts), "turns": turns, "reaches": reaches, "unread": unread}


def hidden_lines(found: dict) -> list[str]:
    lines = [f"hidden-module reaches: {len(found['reaches'])} across {found['attempts']} Tuesday attempt(s) and "
             f"{found['turns']} turn(s) (initial, nudged and incomplete included)"]
    lines += [f"  {stem} {label}: {reach}" for stem, label, reach in found["reaches"]]
    if found["unread"]:
        lines.append("  no saved stream to read: " + ", ".join(f"{s} {label}" for s, label in found["unread"]))
    return lines


# --- The summary --------------------------------------------------------------------------------------

def turn_results(out: Path, script: dict, stem: str, run: int, k: int, graders: int) -> list[dict]:
    """The grade records of one scenario's turn k, each with its run; a turn not reached gets one synthesised
    FAIL record per grader (never written as a grade file), so its expectations fail."""
    turn = run_fixtures.read_json_file(turn_path(out, stem, k)) or {}
    n = len(script["turns"][k - 1]["expectations"])
    if turn.get("outcome") in ("selection_failed", "not_reached"):
        why = f"turn {k} not reached: {turn.get('not_reached') or turn['outcome']}"
        return [{"run": run, "grader": g, "expected": list(range(1, n + 1)), "synthesised": True,
                 "verdicts": [{"n": i, "verdict": "FAIL", "why": why} for i in range(1, n + 1)]}
                for g in range(1, graders + 1)]
    found = []
    for g in range(1, graders + 1):
        data = run_fixtures.read_json_file(out / grade_file(stem, k, g))
        if isinstance(data, dict):
            found.append({**data, "run": run, "grader": g})
        elif gradable(turn):
            # No grade file (a restart, a grader cut short): no verdict, so the turn's expectations read
            # partially graded, never passed.
            found.append({"run": run, "grader": g, "expected": list(range(1, n + 1)), "verdicts": [], "absent": True})
    return found


def core_pass(out: Path, script: dict, stem: str, run: int, graders: int) -> bool | None:
    """Whether a scored scenario passes its script's core screen: every (turn, expectation) pair PASS from
    every grader. None when a verdict is missing and none failed (unresolved); True for a script with none."""
    missing = False
    for k, n in script["core"]:
        records = turn_results(out, script, stem, run, k, graders)
        for g in range(1, graders + 1):
            rec = next((r for r in records if r.get("grader") == g), None)
            verdict = next((v.get("verdict") for v in (rec or {}).get("verdicts", []) if v.get("n") == n), None)
            if verdict == "FAIL":
                return False
            if verdict != "PASS":
                missing = True
    return None if missing else True


def batch_counts(out: Path, skill: str, scenarios: list[tuple[dict, str, int]]) -> tuple[dict, dict]:
    """The batch line's counts over every scenario record in `out` for the given (script, mode, run):
    outcomes, and the set-aside and harness-invalid ones by cause."""
    counts = {o: 0 for o in SCENARIO_OUTCOMES}
    aside: dict[str, dict[str, int]] = {"set_aside": {}, "harness_invalid": {}}
    for script, mode, run in scenarios:
        record = run_fixtures.read_json_file(transcript_path(out, stem_for(skill, script, mode, run)))
        if not isinstance(record, dict):
            continue
        outcome = "killed" if record.get("status") == "running" else record.get("outcome")
        counts[outcome] = counts.get(outcome, 0) + 1
        if outcome in aside:
            key = record.get("stop_cause") or outcome
            aside[outcome][key] = aside[outcome].get(key, 0) + 1
    return counts, aside


def summarise(out: Path, skill: str, jobs: list[tuple[dict, str, int]], graders: int, model: str | None,
              grader_model: str | None, via: str, layout: str, gaps: list[dict],
              work: list[tuple[dict, str]] | None = None) -> tuple[list[str], int]:
    """The batch's summary lines and exit code. Per scenario of this pass (`jobs`), its outcome and per turn
    its grades and checks; per (script, mode, turn) the classification of its expectations and checks over
    the scored scenarios (run_fixtures.classify), and the core screen; then the batch line, over every
    scenario record in `out` for the pass's scripts and modes (`work`; a `--stems` pass that reruns a few
    stems still reads the whole batch): its counts by outcome, the set-aside share against the 10% limit,
    which leaves killed scenarios out (a proven kill is rerun, never set aside), and the nudged scenarios."""
    lines = [f"--- transcripts: {skill}, via {via} ({layout}), model {model}, graders {grader_model} ×{graders}, "
             f"prompt {TRANSCRIPT_GRADER_PROMPT_VERSION} ---"]
    counts = {o: 0 for o in SCENARIO_OUTCOMES}
    aside: dict[str, dict[str, int]] = {"set_aside": {}, "harness_invalid": {}}
    killed_at, nudged, failures, unresolved, missing_records = [], 0, 0, 0, []
    scored_runs: dict[tuple, list[int]] = {}
    for script, mode, run in jobs:
        stem = stem_for(skill, script, mode, run)
        record = run_fixtures.read_json_file(transcript_path(out, stem))
        if not isinstance(record, dict):
            missing_records.append(stem)
            lines.append(f"  {stem}  no scenario record (never started?)")
            continue
        outcome = "killed" if record.get("status") == "running" else record.get("outcome")
        counts[outcome] = counts.get(outcome, 0) + 1
        nudged += bool(record.get("nudged"))
        planned, done = record.get("turns_planned"), record.get("turns_completed")
        fired = "first attempt fired" if not record.get("nudged") else "nudged (its first attempt kept: did not fire)"
        if outcome == "scored":
            scored_runs.setdefault((script["id"], mode), []).append(run)
            stopped = record.get("stopped_at_turn")
            head = f"scored, {done}/{planned} turns; {fired}" if not stopped else \
                f"scored, stopped at turn {stopped} of {planned} ({record.get('reason')}); turns {stopped}-{planned} " \
                f"not reached, their expectations and checks FAIL"
        elif outcome == "killed":
            head = f"killed: {record.get('reason') or 'the driver ended mid-scenario'} (listed for rerun by --recover)"
            killed_at.append(record.get("stopped_at_turn"))
        else:
            head = f"{'set aside' if outcome == 'set_aside' else 'harness-invalid'}: {record.get('reason') or outcome}" \
                + (f" (turn{f's 1-{done}' if done > 1 else ' 1'} saved)" if done else "")
            key = record.get("stop_cause") or outcome
            causes = aside.setdefault(outcome, {})
            causes[key] = causes.get(key, 0) + 1
        lines.append(f"  {stem}  {head}")
        for k in range(1, (planned or 0) + 1):
            turn = run_fixtures.read_json_file(turn_path(out, stem, k))
            if not isinstance(turn, dict):
                continue
            parts = []
            results = turn_results(out, script, stem, run, k, graders)
            if turn.get("outcome") in ("selection_failed", "not_reached"):
                parts.append(f"{turn['outcome'].replace('_', ' ')}: {len(script['turns'][k - 1]['expectations'])} "
                             f"expectation(s) FAIL")
            elif gradable(turn) and outcome == "killed":
                parts.append("not graded (the scenario is recovered from turn 1)")
            elif gradable(turn):
                for g in range(1, graders + 1):
                    got = next((r for r in results if r.get("grader") == g), None)
                    if got is None or got.get("absent"):
                        parts.append(f"grader {g} not graded")
                    elif got.get("error") and not got.get("verdicts"):
                        parts.append(f"grader {g} errored")
                    else:
                        vs = got.get("verdicts") or []
                        gap = f" (incomplete: {', '.join(map(str, got.get('incomplete') or []))})" \
                            if got.get("incomplete") else ""
                        parts.append(f"grader {g} {sum(v.get('verdict') == 'PASS' for v in vs)}/"
                                     f"{len(script['turns'][k - 1]['expectations'])}{gap}")
            elif turn.get("outcome") == "completed" and turn.get("fire") != "fired":
                parts.append(f"did not fire ({turn.get('fire')}), not scored")
            else:
                parts.append(f"{turn.get('outcome')}, not scored")
            checks = run_fixtures.read_json_file(out / f"{stem}.turn{k}.checks.json")
            if isinstance(checks, dict) and checks.get("status") != "harness-invalid":
                bad = [c for c in checks.get("checks") or [] if c.get("verdict") == "FAIL" and c.get("kind") != "report"]
                parts.append(f"checks {checks.get('status')}" + (f" ({len(bad)} failed)" if bad else ""))
            if turn.get("selected"):
                parts.append("selected " + ", ".join(f"{p} {v}" for p, v in turn["selected"].items()))
            if turn.get("files_shown"):
                parts.append("file " + ", ".join(Path(f).name for f in turn["files_shown"]))
            lines.append(f"      turn {k}: " + ", ".join(parts))
    for script in {s["id"]: s for s, _, _ in jobs}.values():
        for mode in script["modes"]:
            runs = sorted(scored_runs.get((script["id"], mode), []))
            if not runs:
                continue
            label = f"{script['id']} [{mode}]"
            for k in range(1, len(script["turns"]) + 1):
                results, checks = [], []
                for run in runs:
                    stem = stem_for(skill, script, mode, run)
                    if run_fixtures.read_json_file(turn_path(out, stem, k)) is None:
                        continue
                    results += turn_results(out, script, stem, run, k, graders)
                    rec = run_fixtures.read_json_file(out / f"{stem}.turn{k}.checks.json")
                    if isinstance(rec, dict):
                        checks.append({**rec, "run": run})
                reached = sorted({r["run"] for r in results} | {c["run"] for c in checks})
                # A turn the scenario never recorded (a scored scenario always records every turn) is no run of it.
                verdict = run_fixtures.classify(results, checks, reached, graders)
                for item in verdict["items"]:
                    key = f"#t{k}.{item['key'][1:]}" if item["key"].startswith("#") else f"t{k} {item['key']}"
                    lines.append(f"  {label} {key:<34} {item['kind']:<13} {item['fails']}/{item['runs']} run(s)  "
                                 f"{item['why'][:140]}")
                    bucket = item["kind"].split(" ")[0]
                    if bucket == "unresolved":
                        unresolved += 1
                    else:
                        failures += 1
            scans = [{**s, "run": run} for run in runs
                     if isinstance(s := run_fixtures.read_json_file(out / f"{stem_for(skill, script, mode, run)}.scan.json"),
                                   dict)]
            if scans:
                for item in run_fixtures.classify([], scans, runs, graders)["items"]:
                    lines.append(f"  {label} {item['key']:<34} {item['kind']:<13} {item['fails']}/{item['runs']} run(s)  "
                                 f"{item['why'][:140]}")
                    if item["kind"].startswith("unresolved"):
                        unresolved += 1
                    else:
                        failures += 1
            if script["core"]:
                got = [core_pass(out, script, stem_for(skill, script, mode, run), run, graders) for run in runs]
                lines.append(f"  {label} core screen ({len(script['core'])} pair(s), every grader): "
                             f"{got.count(True)} of {len(runs)} scored scenario(s) pass"
                             + (f", {got.count(None)} unresolved" if None in got else ""))
                unresolved += got.count(None)
    if work is None:
        work = list(dict.fromkeys((s["id"], m) for s, m, _ in jobs))
        by_id = {s["id"]: s for s, _, _ in jobs}
        work = [(by_id[i], m) for i, m in work]
    batch = list({stem_for(skill, s, m, r): (s, m, r) for s, m, r in
                  [*jobs, *[(s, m, r) for s, m in work for r in saved_runs(out, skill, s, m)]]}.values())
    total_counts, total_aside = batch_counts(out, skill, batch)
    total = len(batch)
    out_of = total_counts["set_aside"] + total_counts["harness_invalid"]
    judged = total - total_counts["killed"]
    share = out_of / judged if judged else 0.0

    def detail(outcome: str) -> str:
        causes = total_aside.get(outcome) or {}
        return f" ({', '.join(f'{OUTCOME_WORDS.get(k, k)} {n}' for k, n in sorted(causes.items()))})" if causes else ""
    at = sorted(t for t in killed_at if t)
    lines.append(f"batch: {total} scenario(s): {total_counts['scored']} scored, {total_counts['set_aside']} set aside"
                 f"{detail('set_aside')}, {total_counts['killed']} killed"
                 + (f" (at turn {', '.join(map(str, at))}; listed for rerun)" if at else
                    " (listed for rerun)" if total_counts["killed"] else "")
                 + f", {total_counts['harness_invalid']} harness-invalid{detail('harness_invalid')}"
                 + f"; set aside {out_of}/{judged} of the scenarios not killed ({share:.1%}, limit "
                   f"{SET_ASIDE_LIMIT:.0%})"
                 + (" — OVER THE LIMIT" if share > SET_ASIDE_LIMIT else ""))
    lines.append(f"nudged scenarios: {nudged} of {len(jobs)} this pass" +
                 (f" (each first attempt kept: did not fire)" if nudged else ""))
    ours = {stem_for(skill, s, m, r) for s, m, r in jobs}
    holes = counts["killed"] or counts["set_aside"] or counts["harness_invalid"] or unresolved or missing_records \
        or any(g["stem"] in ours for g in gaps)
    return lines, 3 if holes else (1 if failures else 0)


# --- Driving it -----------------------------------------------------------------------------------------

STEM = re.compile(r"^(.+)\.run(\d+)$")


def listed_stems(path: Path, skill: str, work: list[tuple[dict, str]]) -> list[tuple[dict, str, int]]:
    """The scenarios a `--stems` file lists, one stem a line (blank lines and `#` lines ignored), as (script,
    mode, run), each under its own run number. Raises ValueError for a stem that names no script and mode of
    this pass, a stem listed twice, and a file that lists none."""
    prefixes = {f"{skill}-{s['id']}.{m}": (s, m) for s, m in work}
    runs, seen = [], set()
    for line in Path(path).read_text().splitlines():
        stem = line.strip()
        if not stem or stem.startswith("#"):
            continue
        match = STEM.match(stem)
        if not match or match.group(1) not in prefixes:
            raise ValueError(f"--stems: {stem!r} names no script and mode this pass runs (a stem is "
                             f"<skill>-<script id>.<mode>.run<n>)")
        if stem in seen:
            raise ValueError(f"--stems: {stem!r} is listed twice")
        seen.add(stem)
        script, mode = prefixes[match.group(1)]
        runs.append((script, mode, int(match.group(2))))
    if not runs:
        raise ValueError(f"--stems: {path} lists no scenario")
    return runs


def saved_runs(out: Path, skill: str, script: dict, mode: str) -> list[int]:
    prefix = f"{skill}-{script['id']}.{mode}"
    pattern = re.compile(rf"^{re.escape(prefix)}\.run(\d+)\.transcript\.json$")
    return sorted(int(m.group(1)) for p in out.glob("*.transcript.json") if (m := pattern.match(p.name)))


def grade_gaps_pass(out: Path, graders: int, move: bool, accept_partial: bool) -> int:
    """`--grade-gaps [--move [--accept-partial]]`, as run_fixtures' over the transcripts' turns."""
    gaps = grade_gaps(out, graders)
    path = run_fixtures.write_grade_gaps(out, gaps, graders, None)
    for line in run_fixtures.gap_lines(gaps, path) or [f"no grade gaps in {out} for {graders} grader(s)"]:
        print(line)
    if move and gaps:
        moved, listing = run_fixtures.move_grade_gaps(out, gaps, accept_partial, run_fixtures.new_pass_id())
        for name in moved:
            print(f"  moved {name}")
        for g in gaps:
            if g["kind"] == "error" or (g["kind"] == "partial" and not accept_partial):
                print(f"  left for the owner: {g['grade_file']} ({g['kind']})")
        if listing:
            print(f"scenarios to grade with --stems {listing} --skip-execute (each turn's grader with no file is "
                  f"filled; the others are kept)")
    return 0


def recover_pass(out: Path, expected: list[str], scripts: dict[str, dict], move: bool) -> int:
    """`--recover [--move]`: the survey, per stem; with --move, keep the killed scenarios under killed/ and list
    them with the never-started ones for --stems (recover_move)."""
    found = survey(out, expected)
    words = {"killed": "killed", "set_aside": "set aside (counts toward the 10% limit, never rerun)",
             "harness_invalid": "harness-invalid (counts toward the 10% limit, never rerun)",
             "never_started": "never started", "unreadable": "unreadable record"}
    for kind, word in words.items():
        for stem in found[kind]:
            why = found["reasons"].get(stem)
            print(f"  {word}: {stem}" + (f" — {why}" if why else ""))
    print(f"{len(found['killed'])} killed, {len(found['never_started'])} never started, {len(found['set_aside'])} set "
          f"aside, {len(found['harness_invalid'])} harness-invalid, {len(found['scored'])} scored")
    if move:
        left: list[str] = []
        moved, listing = recover_move(out, found, scripts, run_fixtures.new_pass_id(), left)
        for name in moved:
            print(f"  kept {name}")
        for stem in left:
            print(f"  left in place: {stem} — the scripts file names no script for it, so its in-flight records "
                  f"stay for a --recover --move pass with its --scripts")
        if listing:
            print(f"scenarios to rerun from turn 1 with --stems {listing}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run fixed multi-turn scripts, resuming one session per scenario.")
    ap.add_argument("--scripts", required=True, help="the scripts file (a case file with a transcripts list)")
    ap.add_argument("--out", required=True, help="directory for records, bodies, checks and grades")
    ap.add_argument("--model", default=None, help="the writer model, pinned (required to run or grade)")
    ap.add_argument("--grader-model", default=None, help="the graders' model, pinned (required to run or grade)")
    ap.add_argument("--skill", choices=SKILLS, default=None, help="must match the scripts file's skill_name")
    ap.add_argument("--script", action="append", default=[], help="run only this script id (repeatable)")
    ap.add_argument("--runs", type=int, default=1, help="scenarios per script and mode")
    ap.add_argument("--graders", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=900, help="seconds per turn")
    ap.add_argument("--workers", type=int, default=2, help="scenarios run at once (each one's turns in order)")
    ap.add_argument("--via", choices=VIAS, default="skill")
    ap.add_argument("--layout", choices=LAYOUTS, default=None)
    ap.add_argument("--stems", default=None,
                    help="a file listing scenarios by stem: run only those, each under its own run number, in an "
                         "--out holding none of their files; with --skip-execute, grade each of their turns' "
                         "graders with no grade file")
    ap.add_argument("--skip-execute", action="store_true",
                    help="check and grade saved scenarios: each (stem, turn, grader) with a saved body and no grade "
                         "file, never overwriting one")
    ap.add_argument("--recover", action="store_true",
                    help="classify the folder's scenarios (killed, set aside, never started); with --move, keep the "
                         "killed ones under killed/ and list them for --stems")
    ap.add_argument("--grade-gaps", action="store_true",
                    help="list the turns whose grade files are missing or miss a verdict; with --move, move them for "
                         "--stems … --skip-execute")
    ap.add_argument("--move", action="store_true", help="with --recover or --grade-gaps: move, never overwrite")
    ap.add_argument("--accept-partial", action="store_true",
                    help="with --grade-gaps --move: move a grade file that misses a verdict to partial/")
    ap.add_argument("--expect", default=None,
                    help="a frozen pass record: refuse, before any call, a pass that differs from it")
    args = ap.parse_args(argv)
    if args.via == "tuesday" and args.layout == "project":
        ap.error("--via tuesday installs the front door as the plugin it ships as: --layout plugin")
    if args.recover and args.grade_gaps:
        ap.error("--recover and --grade-gaps are separate recovery steps")
    if args.move and not (args.recover or args.grade_gaps):
        ap.error("--move goes with --recover or --grade-gaps")
    if args.accept_partial and not (args.grade_gaps and args.move):
        ap.error("--accept-partial goes with --grade-gaps --move")
    if args.runs < 1 or args.graders < 1 or args.workers < 1 or args.timeout < 1:
        ap.error("--runs, --graders, --workers and --timeout are positive")
    try:
        skill, scripts = load_scripts(Path(args.scripts), args.skill)
    except ScriptError as exc:
        ap.error(str(exc))
    unknown = sorted(set(args.script) - {s["id"] for s in scripts})
    if unknown:
        ap.error(f"--script: {', '.join(unknown)} names no script of {args.scripts}")
    every_script = list(scripts)
    scripts = [s for s in scripts if not args.script or s["id"] in args.script]
    layout = args.layout or ("plugin" if args.via == "tuesday" else "project")
    work = [(s, m) for s in scripts for m in s["modes"]]
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    listed = None
    if args.stems:
        try:
            listed = listed_stems(Path(args.stems), skill, work)
        except (OSError, ValueError) as exc:
            ap.error(str(exc))
    planned = listed if listed is not None else [(s, m, r) for s, m in work for r in range(args.runs)]
    by_stem = {stem_for(skill, s, m, r): s for s, m, r in planned}
    by_stem.update({path.name[:-len(".transcript.json")]: s for s, m in work
                    for path in out.glob(f"{skill}-{s['id']}.{m}.run*.transcript.json")})
    if args.grade_gaps:
        return grade_gaps_pass(out, args.graders, args.move, args.accept_partial)
    if args.recover:
        # Recovery reads every killed scenario in --out, so each is mapped to its script from the whole
        # scripts file, whatever --script selects (a stem's `<skill>-<script id>.<mode>.run<n>` names it).
        known = {f"{skill}-{s['id']}.{m}": s for s in every_script for m in s["modes"]}
        stems = {p.name[:-len(".transcript.json")] for p in out.glob("*.transcript.json")} \
            | set(run_fixtures.inflight_records(out))
        recovering = {**{stem: known[m.group(1)] for stem in stems
                         if (m := STEM.match(stem)) and m.group(1) in known}, **by_stem}
        return recover_pass(out, list(dict.fromkeys(stem_for(skill, s, m, r) for s, m, r in planned)), recovering,
                            args.move)
    if not args.model or not args.grader_model:
        ap.error("--model and --grader-model are required: a transcript is never run or graded unpinned")
    if args.skip_execute:
        jobs = listed if listed is not None else [(s, m, r) for s, m in work for r in saved_runs(out, skill, s, m)]
    else:
        jobs = planned
        held = {stem: files for s, m, r in jobs
                if (files := run_fixtures.stem_files(out, stem := stem_for(skill, s, m, r)))}
        if held:
            ap.error("a scenario runs only where --out holds none of its files (a killed one's move to killed/ "
                     "first, with --recover --move): " + "; ".join(f"{stem} holds {', '.join(files[:3])}"
                                                               for stem, files in held.items()))
    expect = None
    if args.expect:
        expect = run_fixtures.read_json_file(Path(args.expect))
        if not isinstance(expect, dict):
            ap.error(f"--expect: {args.expect} is not a JSON object")
    settings = {"driver": "run_transcripts", "model": args.model, "grader_model": args.grader_model,
                "via": args.via, "layout": layout, "graders": args.graders, "timeout": args.timeout,
                "retry_runs": 0, "scripts_sha256": run_fixtures.file_sha256(Path(args.scripts)),
                "grader_prompt_sha256": TRANSCRIPT_GRADER_PROMPT_SHA256}
    pass_record = run_fixtures.pass_record(sys.argv if argv is None else ["run_transcripts.py", *argv], settings)
    refused, notes = run_fixtures.pass_problems(run_fixtures.read_passes(out) + [pass_record], expect)
    for note in notes:
        print(f"note: {note}")
    if refused:
        for line in refused:
            print(f"refused: {line}")
        print("Refused before any call: passes into one --out must be one measurement.")
        return 3
    pass_id = pass_record["pass_id"]
    run_fixtures.write_json(out / "passes" / f"{pass_id}.json", pass_record)

    if not args.skip_execute:
        print(f"\nexecuting {len(jobs)} scenario(s)")
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(lambda j: execute_scenario(skill, j[0], out, j[1], j[2], args.timeout, args.model,
                                                     args.via, layout, pass_id=pass_id), jobs))
    for script, mode, run in jobs:
        check_scenario(out, script, stem_for(skill, script, mode, run))
    grading = [(script, stem_for(skill, script, mode, run), k, g) for script, mode, run in jobs
               for k, g in grade_jobs(out, script, stem_for(skill, script, mode, run), args.graders)]
    print(f"\ngrading {len(grading)} turn grade(s)")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(lambda j: grade_turn(out, j[0], j[1], j[2], j[3], args.timeout, args.grader_model,
                                           pass_id=pass_id), grading))

    gaps = grade_gaps(out, args.graders)
    gap_file = run_fixtures.write_grade_gaps(out, gaps, args.graders, pass_id)
    lines, code = summarise(out, skill, jobs, args.graders, args.model, args.grader_model, args.via, layout, gaps,
                            work)
    print()
    print("\n".join(lines))
    report = run_fixtures.gap_lines(gaps, gap_file) + run_fixtures.sentinel_lines(run_fixtures.sentinel_report(out)) \
        + (hidden_lines(hidden_reaches(out)) if args.via == "tuesday" else [])
    if report:
        print()
        print("\n".join(report))
    pass_record["finished"] = utc_now()
    run_fixtures.write_json(out / "passes" / f"{pass_id}.json", pass_record)
    if code == 3:
        print("\nKilled, set-aside and harness-invalid scenarios, unresolved expectations and partly graded turns "
              "are not passes: the batch has holes in it, and the exit code says so.")
    return code


if __name__ == "__main__":
    sys.exit(main())
