#!/usr/bin/env python3
"""Run each skill's own eval fixtures in a clean room, then grade them.

The problem this solves is authoring context. A fixture graded in the session
that wrote the skill is graded by a reader who already knows what the skill
meant — who supplies the charitable reading, and scores the intent rather than
the output. This runner puts the fixture in front of a session that has only
the skill installed and nothing else: no repository, no spec, no conversation
about what the skill was supposed to do.

Two phases, separable so a long execute pass is graded without re-running it:

    execute   one throwaway project per run, containing only that skill;
              each fixture prompt is sent raw and the full response saved,
              with the harness's own record of what the run did.
    grade     each response is checked deterministically where its form can be
              read exactly, and scored against its own expectations by graders
              that never see the skill, only the response and the expectations.

Graders are deliberately adversarial and deliberately more than one. Every
defect worth fixing in this suite so far was found by the grader that disagreed,
and two of them were found in responses another grader had passed outright.

**Rooms are isolated and pinned.** "Only the skill installed" was not true: a
default room loaded the host's own skills, 46 of them, one named mock-interview.
Every historical room fired the installed skill, so no past number is
contaminated, but nothing stopped the next one from firing the wrong skill and
being graded as this skill's output. Rooms now run with `--setting-sources
project`, a fire counts only when the Skill call names the installed skill, and
any other loaded skill sharing its name is recorded. `--model` pins the room's
model and the stream's own init event records what actually ran — the host
default moved from the model every measured room used to a newer one between
sets, and an unpinned comparison would have measured the move.

**Graders run with no tools and a pinned model.** A grader used to be a default
session with web search, a shell and every host skill loaded, able to go and
check a research claim itself, with no record of which model graded. Graders now
run with `--tools ""`, no MCP servers, no skills and no settings, and each grade
file records the model that answered, the CLI version, the flags, the hash of
every expectation it graded and the grader prompt's version. `--grader-model`
pins them; it defaults to `--model`.

**Research runs in one of two rooms, and the room is checked, not assumed.** A
fixture declares its modes. `denied` is the historical condition — web search
present and every call refused — pinned with `--strict-mcp-config` so a host
setting cannot quietly make it live. `canned` serves the fixture's own pages
through `research_server.py`, a stub search engine whose corpus, config and call
log live under `<out>/research/`, one set per invocation, never in the room or
its scratchpad (anything there would be collected and graded as the response).
Every run's init event and tool calls are checked against its mode; a room that
did not match is harness-invalid, never a skill result. A canned room that
connected and offered search but saw zero calls is a valid room: not searching
is something the skill did.

**A nudge is a new room.** A run that does not fire the installed skill is
re-run with the skill named — in a fresh room, because the first attempt's
files and searches would otherwise be credited to the response being graded. A
run that never fires it is harness-invalid: it is not this skill's output.

**What the graders are told.** The response sits between two marker lines the
prompt names, and nothing outside them is the response's text, so the record
after it is never read as its closing lines. The prompt states the room's actual
research mode and carries a "What the harness observed" block: the calls the run actually
sent, or that it sent none, or — for a run saved before this record existed —
that nothing was recorded and research counts must not be graded. Graders had
been failing true claims of refused searches because nothing told them the
searches happened. The block is ground truth for checking the response's claims
about research, never a source of content the response lacks.

**Deterministic checks.** The accounting table, the tally line, the fit ledger
and the verbatim quotation cells have fixed forms, so `output_checks.py` reads
them exactly and writes `{stem}.checks.json` beside each response. A check
failure is a failure like a grader's, keyed `chk:<check>:<target>` and
classified the same way; a check that needs the research record is not run on a
response that has none.

Runs are adaptive. Every fixture runs once; a fixture that fails something —
a grader verdict or a check — runs again, and each failure is then reported as
deterministic (it failed every valid run) or intermittent (at least one fully
graded run passed it). That distinction is the whole point. One fixture in this
suite has scored 12/12, 13/13, 13/13 and 9/13 on the same skill, and a single run
cannot tell that from a defect. A run where some grader returned nothing for an
expectation, and no grader failed it, is partially graded and does not pass it.
The expectation is then intermittent if another run failed it and a fully graded
run passed it, and otherwise unresolved, never clean (classify).

Exit codes:
    0   clean: every expectation and check passed in every valid run
    1   skill failures: a grader or a check failed something
    3   incomplete: a harness-invalid run or an unresolved expectation exists
        (this wins over 1 — a set with holes in it is not a measurement yet).
        Not 2, which argparse and recurring.py already use.

Regrading. Grade files are never overwritten: `--skip-execute` refuses an --out
that already holds them. `--regrade-from SRC --out NEW` copies SRC's responses
and meta into a fresh directory, reconstructs the research record of runs saved
before it existed (`backfill_tools.py`), and grades and checks them there.
`--stems FILE` re-runs the runs a file names, each under its own run number, in an --out
that holds none of their files; with --skip-execute it grades, for each of them that holds a
response, every grader with no grade file, and reads the others' files, never overwritten.

What a run keeps. Each attempt's stream is written as it arrives (`streams/<room>.inflight.jsonl`,
then `.jsonl`, or `.partial.jsonl` for a timeout or a decline, whose stream is kept too); its init
event once under `init/`; every file it left in its room and scratchpad under `files/<room>/`, with
an inventory in the meta (a cut attempt's marked `partial_evidence`); its session id, and through
the front door the hidden modules it reached (E16, read from the whole stream). The meta records the
watch-out line the installed payload declares, which the checks hold the run to in any checkout.
A fixture declaring `sentinels` has every attempt scanned from that evidence (output_checks.
scan_sentinels), and a run whose list breaks the freezing rules or whose evidence is incomplete is
harness-invalid. The runtime account email is masked in every record and printed line (masked). Moves and snapshots never
overwrite: a name already taken gets `~<pass id>`.

Passes. Every invocation that runs or grades writes `passes/<pass id>.json` (argv, host, CLI, the
harness's code, the payload's digests, the settings), and every meta and grade names its pass. A pass
whose code, payload or settings differ from the folder's earlier passes, or from `--expect FILE` (a
frozen pass record), is refused before any call; `--expect` also refuses any `--retry-runs` but 0.

Recovery. The summary lists each finished run's grade file that is missing or misses a verdict, and
`grade-gaps.json` holds them; `--grade-gaps [--move [--accept-partial]]` moves them for `--stems …
--skip-execute`. `--killed [--move]` classifies the unfinished runs per stem (usage-limit kills and
runs a restart cut mid-attempt are kept under killed/ and listed for `--stems`; timeouts, declines
and invalid rooms are set aside, never rerun).

Usage:
    python evals/run_fixtures.py --out /tmp/clean-room --model claude-sonnet-5
    python evals/run_fixtures.py --skill job-underwriter --eval 3 --out /tmp/cr
    python evals/run_fixtures.py --out /tmp/cr --retry-runs 0   # one run, no retries
    python evals/run_fixtures.py --out /tmp/cr --skip-execute   # grade saved, ungraded runs
    python evals/run_fixtures.py --regrade-from /tmp/cr --out /tmp/cr-regrade --expectation 14
    python evals/run_fixtures.py --skill job-underwriter --cases probe.json --out /tmp/p
    python evals/run_fixtures.py --stems killed.txt --out /tmp/cr                # re-run named runs in place
    python evals/run_fixtures.py --via tuesday --out /tmp/fd     # each fixture through the front door
    python evals/run_fixtures.py --layout plugin --out /tmp/alone # each module alone, installed as the front door is
    python evals/run_fixtures.py --out /tmp/cr --retry-runs 0 --expect frozen-pass.json  # refuse any drift
    python evals/run_fixtures.py --out /tmp/cr --grade-gaps --move --accept-partial   # then --stems … --skip-execute
    python evals/run_fixtures.py --out /tmp/cr --runs 5 --killed --move               # then --stems the list

`--via tuesday` runs each module's fixtures with the front door installed as the
Claude Code plugin ships it; `--layout plugin` installs a module alone the same way, the
control a comparison through Tuesday uses (evals/README.md, "Through Tuesday").
"""

from __future__ import annotations

import argparse
import datetime
import fnmatch
import functools
import hashlib
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import uuid
import zipfile
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

import output_checks  # noqa: E402
import run_routing  # noqa: E402  (the front door's plugin install and routing reader, for --via tuesday)
from child_env import child_env  # noqa: E402
from fixture_clauses import dated, load_cases  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SKILLS = ["job-underwriter", "mock-interview", "resume-tailor"]
SERVER = Path(__file__).resolve().parent / "research_server.py"
MODES = ("denied", "canned")
# How a fixture's module reaches the room: installed alone (`skill`), or through the front door.
VIAS = ("skill", "tuesday")
# Where a run's skills sit (evals/README.md, "Through Tuesday"): the room's own `.claude/skills/`
# (`project`: the module alone, as every ledger baseline before the arms shared an install), or a
# plugin of the room's own beside it (`plugin`: the front door as it ships, or the module alone
# installed the same way, so the two arms differ only in what the plugin holds).
LAYOUTS = ("project", "plugin")
# The tools a refused save is a refusal of (`refusals`).
SAVE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
SEARCH_KIND = output_checks.SEARCH_KIND
# A run's files share its stem: `<stem>.meta.json`, `<stem>.grade-2.json`, `<stem>.turn3.json`.
STEM_FILE = re.compile(r"^(.+?\.run\d+)(\..*)?$")
PERMISSION_TEXT = re.compile(r"requested permissions|haven't granted|permission to use|"
                             r"not allowed|was denied|denied by", re.I)

GRADER_PROMPT_VERSION = "3"
# The two lines the grader prompt fences the response between, and names (version 3). Version 2
# put the harness's record straight after the response, unmarked, and graders read the record
# as the response's own closing text (evals/README.md, "What the graders see").
RESPONSE_BEGINS = "===== RESPONSE BEGINS ====="
RESPONSE_ENDS = "===== RESPONSE ENDS ====="

GRADER_PROMPT = """You are grading one response against a fixed list of expectations.

Grade adversarially. Your job is to find where the response falls short, not to
give it the benefit of the doubt. A partial satisfaction is a FAIL. An
expectation the response gestures at but does not actually do is a FAIL. Do not
reward length, confidence, or good intentions. You are not being asked whether
the response is good; you are being asked whether each specific expectation is
met by text actually present in the response.

You have not seen the skill that produced this and you do not need to. Judge the
response by its own text, never by what some other document might say. The one
record you are given beside it is the harness's account of the research the run
actually did, and it has one use, stated where it appears.

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

## The request that was made

{prompt}

## The response to grade

This is everything the response produced, between the line `{begins}` and the line `{ends}`. Nothing outside those two lines is text the response wrote. Where it delivered by writing a file, that file's full contents appear below the chat text under a `----- file the response produced -----` marker, and it counts exactly as if it had been written inline.

{begins}
{response}
{ends}

## What the harness observed

{observed}

This record is ground truth for checking the response's claims about its own research: whether a search was sent, how many were, and whether each target's label matches what happened. It must never be used to supply content the response lacks — a page, a figure or a fact that appears only here does not count as the response having said it.

## The expectations

{expectations}

Return ONLY a JSON object, no prose around it:

{{"verdicts": [{{"n": 1, "why": "one sentence, quoting the response where it matters", "verdict": "PASS" or "FAIL"}}, ...]}}

{sites}One entry per expectation, under the number it is given above. The reason comes before the verdict in every entry.
"""

RESEARCH_MODE = {
    "denied": "This response was produced in a room where web search and fetch were\n"
              "  present but every call to them was refused: research could be attempted\n"
              "  and could never return anything. Declining to research, saying so plainly,\n"
              "  and carrying the consequence into the analysis is correct behaviour and\n"
              "  passes, unless the expectation specifically demands research.",
    "canned": "This response was produced in a room with a working search tool over a\n"
              "  fixed set of pages: research could be attempted and could return results.\n"
              "  Whether it was attempted, and what each call returned, is in the harness's\n"
              "  record below.",
}

SITES_INSTRUCTION = """An expectation marked [enumerate every site] covers many places in the response, and its entry also carries a "sites" list, before "why":

{"n": 14, "sites": [{"where": "section / row / column", "clause": "the words at that site", "rests_on": "the quoted sentence it rests on, or none", "status": "traced" or "slot" or "untraced"}], "why": "...", "verdict": "PASS" or "FAIL"}

List every site the expectation covers, not a sample. A site is "traced" when it rests on a sentence you can quote, a "slot" when it asserts nothing and leaves a place for the answer, and "untraced" when it rests on nothing you can quote. The verdict is FAIL if and only if any site is untraced.

"""


# The sha256 of version 3's text (the template, its research-mode lines and the sites instruction),
# recorded in every grade beside its version.
GRADER_PROMPT_SHA256 = hashlib.sha256(json.dumps([GRADER_PROMPT, RESEARCH_MODE, SITES_INSTRUCTION], sort_keys=True,
                                                 ensure_ascii=False).encode("utf-8")).hexdigest()


def install_one(root: Path, skill: str, run_id: str) -> str:
    """Install a single skill into an otherwise empty project; return its name.

    Only one skill goes in. A clean room with both siblings present would be
    testing routing as well as output, and routing already has its own eval.
    """
    name = f"{skill}-{run_id}"
    dest = root / ".claude" / "skills" / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(REPO / "skills" / skill, dest,
                    ignore=shutil.ignore_patterns("evals", "__pycache__", "*.pyc", ".DS_Store"))
    skill_md = dest / "SKILL.md"
    text = skill_md.read_text()
    renamed = re.sub(rf"^name:\s*{re.escape(skill)}\s*$", f"name: {name}", text,
                     count=1, flags=re.MULTILINE)
    if renamed == text:
        raise SystemExit(f"{skill}: frontmatter name not found to rename")
    skill_md.write_text(renamed)
    return name


def install_in_plugin(room: Path, run_id: str, module: str | None = None) -> tuple[Path, dict[str, str]]:
    """Install a fixture run's skills as the routing arm's plugin layout installs them, in a
    plugin folder beside the room, never in it (`run_routing.install_plugin`): the front door,
    the hub and the three hidden modules; or, given `module`, that module alone, visible, the
    module-alone arm's plugin install. Return the plugin folder and name -> installed name."""
    plugin = run_routing.home(room, "plugin")
    return plugin, run_routing.install_plugin(plugin, run_id, module)


def save_rules(room: Path) -> list[str]:
    """The permission rules that let a run save inside its own room, as a user who answers the save
    prompt with "allow edits in this folder" would (the owner's decision 4; evals/README.md,
    "Through Tuesday"): `Edit` on every file under the room, which covers the edit tools, and,
    when the room is reached through a symlink, the same rule on its resolved path. Nothing
    else is writable: the plugin folder beside the room, which holds the skills, stays refused."""
    rules = [f"Edit(/{room.absolute().as_posix()}/**)"]
    resolved = f"Edit(/{room.resolve().as_posix()}/**)"
    return rules + ([resolved] if resolved not in rules else [])


def plugin_flags(flags: list[str], room: Path) -> list[str]:
    """A room's flags with its plugin added, the plugin's skills folder readable and the room
    writable: `--plugin-dir`, and the routing arm's read rule (`run_routing.read_rule`) and the
    room's save rules (`save_rules`) joined to the room's one `--allowedTools` list, or given
    their own when the room has none. Both arms' plugin installs run under exactly these; the
    project layout and the graders get no save rule."""
    flags, rules = list(flags), [run_routing.read_rule(room, "plugin"), *save_rules(room)]
    if "--allowedTools" in flags:
        at = flags.index("--allowedTools") + 1
        flags[at:at] = rules
    else:
        flags += ["--allowedTools", *rules]
    return flags + ["--plugin-dir", str(run_routing.home(room, "plugin"))]


def room_writable(flags: list[str], room: Path) -> bool:
    """Whether a run's flags let it save inside its room (`save_rules`), recorded on every
    invocation and run (`room_writable`)."""
    return all(rule in flags for rule in save_rules(room))


def tuesday_fire(lines, names: dict[str, str], skill: str, room: Path) -> str:
    """`fired` when a run through the front door read `skill`'s playbook through the hub and
    reached no hidden module; otherwise the routing reader's label for what the run did
    instead (`run_routing.RunReader`, front-door arm: another module, `hidden-<module>`,
    `tuesday-unrouted`, `neither`, `void`, `error`). The same reader scores the routing arm,
    so a fire here is a route there."""
    reader = run_routing.RunReader(names, "tuesday", None, "plugin", room)
    outcome = None
    for line in lines:
        event = line
        if not isinstance(line, dict):
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
        if isinstance(event, dict):
            outcome = reader.feed(event)
            if outcome:
                break
    outcome = outcome or reader.exited()
    return "fired" if outcome == skill else outcome


CLI_FAILURE_MARKERS = (
    "session limit", "usage limit", "rate limit", "credit balance",
    "invalid api key", "overloaded", "quota",
)
# The usage-limit message, as the fix round's grade_gaps.py read it: a run, an attempt or a grade cut by the
# limit is killed and recovered (evals/README.md, "Regrading a saved set"), never set aside. It is read only
# where the CLI writes the message (limit_line), never in a reply's prose: a pack that discusses an API's
# usage limit is no kill.
LIMIT = re.compile(r"hit your (?:weekly |session |usage )?limit|\busage limit\b|\bsession limit\b", re.I)
# The limit message as a whole reply: what the CLI prints in place of an answer ("You've hit your session
# limit · resets 7am (UTC)", "Claude AI usage limit reached|…"), anchored, so a reply that only mentions a
# usage limit is not one.
LIMIT_MESSAGE = re.compile(r"\s*(?:you(?:'|’)ve|you\s+have)\s+(?:hit|reached)\s+your\s+"
                           r"(?:weekly\s+|session\s+|usage\s+|daily\s+|\d+-hour\s+)?limit\b[^\n]{0,80}"
                           r"|\s*(?:claude(?:\s+ai)?\s+)?(?:usage|session|weekly|\d+-hour)\s+limit\s+reached\b[^\n]{0,80}",
                           re.I)
# How long a killed CLI's pipes are drained before the runner stops reading them and only reaps it: a child
# the CLI started (an MCP server) can hold a pipe open after the CLI itself is gone.
REAP_SECONDS = 30
# A reply this short that carries a decline marker is a decline, when the stream gives no clean result.
SHORT_REPLY = 200
# How much of a declined run's stderr its invocation keeps (`stderr_head`).
STDERR_KEPT = 1000


def cli_failed(text: str, returncode: int) -> bool:
    """Did the CLI decline to answer rather than answering?

    A refusal from the harness is not a result from the skill. Left undetected,
    "You've hit your session limit" is saved as a 48-character response and
    graded as a fixture that produced almost nothing — the third variant in this
    suite of a non-result being recorded as a result, after the routing runner's
    errored runs and the truncated grader reply.

    The marker test is for a reply the CLI gave no clean result for (`stream_declined`):
    a short in-persona question that mentions a quota or a rate limit is an answer.
    """
    if returncode != 0:
        return True
    head = text.strip()[:400].lower()
    return len(text.strip()) < SHORT_REPLY and any(m in head for m in CLI_FAILURE_MARKERS)


def stream_declined(text: str, returncode: int | None, result: dict) -> bool:
    """Whether a stream-mode run declined to answer, by its exit code, its result event and its text.

    A run that exits 0 with a result event that is not an error answered: its text is the reply, however
    short and whatever it mentions (a drill question about a missed quota, a rate-limit problem, an API's
    usage limit). The decline markers (cli_failed) are read only when no result event arrived or the result
    is an error. One reply is never an answer whatever its result event says: the usage-limit message as
    the whole reply (LIMIT_MESSAGE, anchored), so the 48-character limit message is never graded."""
    if returncode != 0:
        return True
    answered = not result.get("incomplete") and not result.get("is_error")
    if not answered and cli_failed(text, 0):
        return True
    return bool(LIMIT_MESSAGE.fullmatch(text.strip()))


def limit_line(raw: list[str], texts: list[str], result: dict | None, stderr: str) -> str | None:
    """The line that carries the usage-limit message (LIMIT), read only where the CLI writes it: its stderr,
    stdout lines that are not JSON, the result event's `result` text when the result is an error or the
    text is short (under SHORT_REPLY), and the last main-thread assistant text block when it is short. A
    reply's prose is never read: a long pack, or a partial one cut by a timeout, that names an API's usage
    limit is no kill. None when no such line carries it."""
    result = result if isinstance(result, dict) else {}
    said = str(result.get("result") or "") if isinstance(result.get("result"), str) else ""
    places = [stderr or "", *raw]
    if said and (result.get("is_error") or len(said.strip()) < SHORT_REPLY):
        places.append(said)
    if texts and len(texts[-1].strip()) < SHORT_REPLY:
        places.append(texts[-1])
    for place in places:
        for line in place.splitlines():
            if LIMIT.search(line):
                return line.strip()[:200]
    return None


def stream_limit(stdout: str, stderr: str) -> str | None:
    """limit_line over a run's stdout and stderr: its JSON events, the lines that are not one, the last
    result event and the main thread's assistant text blocks."""
    raw, texts, result = [], [], None
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            event = None
        if not isinstance(event, dict):
            raw.append(line)
        elif event.get("type") == "result":
            result = event
        elif event.get("type") == "assistant" and not event.get("parent_tool_use_id") \
                and not event.get("isSidechain"):
            texts += [item.get("text", "") for item in (event.get("message") or {}).get("content") or []
                      if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str)]
    return limit_line(raw, texts, result, stderr)


def masked(value):
    """A value with the runtime account email masked (output_checks._redacted, the runtime sentinels read
    from the environment); the value itself when none is set. Every record, reason and printed line the
    drivers write passes through it, so the address never reaches a file or a log."""
    secrets = [s for entry in output_checks.runtime_sentinels(os.environ) for s in entry["spellings"]]
    return output_checks._redacted(value, secrets) if secrets else value


class CLITimeout(RuntimeError):
    """The CLI ran out of time. Carries whatever it had streamed by then.

    An uncaught TimeoutExpired used to abort the whole worker pool and lose the
    partial stream with it; one slow canned room — tool searches, then up to
    eight calls — would have taken every other run down. The process is killed
    and reaped before this is raised, so a timed-out CLI spends nothing more and
    writes nothing more.
    """

    def __init__(self, message: str, partial: str = ""):
        super().__init__(message)
        self.partial = partial


class CLIDeclined(RuntimeError):
    """The CLI declined to answer in stream mode: a non-zero exit, a run that ended in error or without a
    result event, or a decline message for a reply. The message is the text the RuntimeError carried
    before ("CLI declined: …"), so readers that match it keep matching. It carries what the run streamed
    (`partial`, kept as the attempt's partial stream), its exit code, the head of its stderr, and `limit`:
    whether the usage-limit message is where the CLI writes it (stream_limit), a kill to recover rather than
    a decline to set aside. The message and the stderr head have the runtime account email masked."""

    def __init__(self, message: str, partial: str = "", returncode: int | None = None,
                 stderr_head: str = "", limit: bool = False):
        super().__init__(message)
        self.partial = partial
        self.returncode = returncode
        self.stderr_head = stderr_head
        self.limit = limit


def decode(raw) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return str(raw)


def read_back(path: Path) -> str:
    """A stream file the CLI wrote, as text (UTF-8, undecodable bytes replaced)."""
    try:
        return Path(path).read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return ""


def launch(cmd: list[str], prompt: str, cwd: Path, env: dict, timeout: int,
           stream_to: Path | None = None) -> tuple[int, str, str]:
    """Start one CLI process with the prompt on stdin and wait for it; return (exit code, stdout, stderr).

    `Popen(stdin, stdout, stderr)` with `communicate(input=…, timeout=…)`, which feeds stdin and drains
    both pipes together, so a CLI writing more than a pipe's buffer to stderr cannot block on it. Given
    `stream_to`, stdout goes straight to that file as the CLI writes it, so a runner killed mid-run leaves
    the stream on disk, and the text returned is read back from it. On a timeout the process is killed
    and reaped, then CLITimeout carries what it streamed. The child stays in the runner's process group
    (no new session), so a guard that stops the group stops it too."""
    sink = open(stream_to, "wb") if stream_to is not None else None
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=sink if sink else subprocess.PIPE,
                                stderr=subprocess.PIPE, cwd=str(cwd), env=env, text=True)
        try:
            stdout, stderr = proc.communicate(input=prompt, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            proc.kill()
            try:
                stdout, _ = proc.communicate(timeout=REAP_SECONDS)
            except subprocess.TimeoutExpired as again:
                # A child of the CLI holds a pipe open: stop reading, keep what was read, reap the CLI.
                stdout = decode(again.stdout or exc.stdout)
                for pipe in (proc.stdout, proc.stderr):
                    if pipe:
                        pipe.close()
                proc.wait()
            partial = read_back(stream_to) if sink else decode(stdout)
            raise CLITimeout(f"timed out after {timeout}s", partial) from None
    finally:
        if sink:
            sink.close()
    if sink:
        stdout = read_back(stream_to)
    return proc.returncode, stdout or "", stderr or ""


def claude(prompt: str, cwd: Path, timeout: int, extra_args=(), output: str = "stream",
           installed: str = "", stream_to: Path | None = None) -> dict:
    """Run one `claude -p` with the prompt on stdin; return what it produced.

    `output="stream"` returns parse_stream()'s record plus the raw stdout;
    `output="json"` returns the CLI's JSON result object, whose "result" field
    carries the reply. The prompt always goes on stdin: --mcp-config, --tools,
    --allowedTools and --disallowedTools are variadic and would swallow a
    positional prompt. The caller's flags are passed as given and nothing is
    added to them, so a room's research flags can never leak into a grader.
    `stream_to` (stream mode) writes the stream to that file as it arrives
    (launch); argv, stdin, cwd and environment are the same either way.

    Raises CLITimeout on a timeout, CLIDeclined (stream mode) when the CLI
    declined to answer (stream_declined), and RuntimeError when a grader's JSON
    reply was a decline, so a limit message can never be mistaken for a short
    response.
    """
    fmt = {"stream": ["--output-format", "stream-json", "--verbose"],
           "json": ["--output-format", "json"]}[output]
    cmd = ["claude", "-p", *fmt, *extra_args]
    # Only the room's own skills: no synced account skills, no parent session (child_env).
    env = child_env()
    returncode, stdout, stderr = launch(cmd, prompt, cwd, env, timeout, stream_to if output == "stream" else None)

    if output == "json":
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            raise RuntimeError(masked(f"CLI declined: no JSON result "
                                      f"({(stdout or stderr).strip()[:200]})")) from None
        reply = str(data.get("result") or "")
        if returncode != 0 or data.get("is_error") or cli_failed(reply, returncode):
            raise RuntimeError(masked(f"CLI declined: {reply.strip()[:200] or stderr.strip()[:200]}"))
        return data

    parsed = parse_stream(stdout.splitlines(), installed)
    parsed["stdout"] = stdout
    result = parsed["result"]

    def declined(message: str) -> CLIDeclined:
        return CLIDeclined(masked(message), stdout, returncode, masked(stderr.strip()[:2000]),
                           stream_limit(stdout, stderr) is not None)
    if stream_declined(parsed["text"], returncode, result):
        raise declined(f"CLI declined: {parsed['text'].strip()[:200] or stderr.strip()[:200]}")
    if result["incomplete"] or result.get("is_error"):
        raise declined(f"CLI declined: the run ended "
                       f"{'without a result' if result['incomplete'] else 'in error'}"
                       f" ({result.get('subtype')})")
    return parsed


# --- Reading the stream --------------------------------------------------------

def excerpt(content, limit: int = 1500) -> str:
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "\n".join(c.get("text", "") if isinstance(c, dict) and c.get("type") == "text"
                         else json.dumps(c) for c in content)
    elif content is None:
        text = ""
    else:
        text = json.dumps(content)
    return text[:limit]


def clipped(value, limit: int = 2000):
    """A tool input with its long strings cut: a Write call carries the whole pack."""
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + f"... [{len(value)} chars]"
    if isinstance(value, dict):
        return {k: clipped(v, limit) for k, v in value.items()}
    if isinstance(value, list):
        return [clipped(v, limit) for v in value]
    return value


def parse_stream(lines, installed_name: str) -> dict:
    """Read a stream-json run (or a session transcript) into the harness's record.

    Extracted from claude() so it can be tested: the old loop kept only the text
    and whether *any* Skill fired, which could not tell the installed skill from
    a host skill of the same name, threw away every tool call, and could not say
    whether the stream had finished. Returns:

      text        assistant text from the main thread only — a subagent's notes
                  are not the response;
      fire        "fired" (the installed skill), "wrong_skill" (another skill),
                  or "not_fired";
      init        version, model, permission mode, tools, MCP servers, how many
                  skills loaded and which of them compete with the installed one;
      result      subtype, is_error, turns, modelUsage, permission denials, the
                  session id, and incomplete=True when no result event arrived (a
                  timeout);
      tool_calls  every tool_use joined to its tool_result by id;
      init_event  the first init event whole, or None (run_attempt keeps it under
                  init/, init_evidence).
    """
    # A plugin's skill is listed and called by its plugin-qualified id, `<plugin>:<name>`, a call
    # may give the name alone, and either may follow one `/`: every name is read as the routing
    # reader reads it, by the part after the colon (run_routing.local_name).
    local = run_routing.local_name(installed_name or "")
    base = re.sub(r"-[0-9a-f]{8}$", "", local)
    text, calls, order, fired_skills, denied_events = [], {}, [], [], []
    init, result, init_event = {}, None, None
    for line in lines:
        event = line
        if not isinstance(line, dict):
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
        if not isinstance(event, dict):
            continue
        kind = event.get("type")
        parent = event.get("parent_tool_use_id")
        side = bool(parent) or bool(event.get("isSidechain"))
        if kind == "system" and event.get("subtype") == "init":
            if init_event is None:
                init_event = event
            skills = [s for s in event.get("skills") or [] if isinstance(s, str)]
            init = {"claude_code_version": event.get("claude_code_version"),
                    "model": event.get("model"),
                    "permissionMode": event.get("permissionMode"),
                    "tools": event.get("tools") or [],
                    "mcp_servers": event.get("mcp_servers") or [],
                    "skills": len(skills),
                    "installed_loaded": bool(local) and any(run_routing.local_name(s) == local for s in skills),
                    "competing_skills": [s for s in skills if base and base in run_routing.local_name(s)
                                         and run_routing.local_name(s) != local],
                    "session_id": event.get("session_id"),
                    "cwd": event.get("cwd")}
        elif kind == "system" and event.get("subtype") == "permission_denied":
            denied_events.append({"tool_name": event.get("tool_name"),
                                  "tool_use_id": event.get("tool_use_id")})
        elif kind == "assistant":
            for item in (event.get("message") or {}).get("content") or []:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "text" and not side:
                    text.append(item.get("text", ""))
                elif item.get("type") == "tool_use":
                    tid = item.get("id")
                    calls[tid] = {"id": tid, "name": item.get("name"),
                                  "input": clipped(item.get("input")),
                                  "is_error": None, "result_excerpt": None,
                                  "parent_tool_use_id": parent}
                    order.append(tid)
                    if item.get("name") == "Skill":
                        fired_skills.append(str((item.get("input") or {}).get("skill", "")))
        elif kind == "user":
            content = (event.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for item in content:
                if isinstance(item, dict) and item.get("type") == "tool_result" \
                        and item.get("tool_use_id") in calls:
                    call = calls[item["tool_use_id"]]
                    call["is_error"] = bool(item.get("is_error"))
                    call["result_excerpt"] = excerpt(item.get("content"))
        elif kind == "result":
            result = {"subtype": event.get("subtype"), "is_error": event.get("is_error"),
                      "num_turns": event.get("num_turns"), "modelUsage": event.get("modelUsage"),
                      "permission_denials": event.get("permission_denials") or [],
                      "session_id": event.get("session_id"), "incomplete": False}
    if result is None:
        result = {"subtype": None, "is_error": None, "num_turns": None, "modelUsage": None,
                  "permission_denials": denied_events, "session_id": None, "incomplete": True}
    names = [run_routing.local_name(s) for s in fired_skills]
    fire = "fired" if local and local in names else \
        ("wrong_skill" if fired_skills else "not_fired")
    return {"text": "\n".join(text), "fire": fire, "skills_fired": fired_skills,
            "init": init, "result": result, "tool_calls": [calls[t] for t in order],
            "init_event": init_event}


def refused(call: dict, denied_ids: set) -> bool:
    return call.get("id") in denied_ids or bool(
        call.get("is_error") and PERMISSION_TEXT.search(call.get("result_excerpt") or ""))


def build_research_log(tool_calls: list[dict], permission_denials: list | None,
                       calls_log: list[dict] | None) -> list[dict]:
    """Every search or fetch the run attempted, refused ones included.

    The old runner dropped the tool stream entirely, so nothing could say whether
    a `yes` row had a search behind it or a `skipped` row had one it hid. In a
    canned room each MCP call is joined, in order, to the server's own log line —
    the URLs it returned and the targets those pages are tagged with — so the
    record does not depend on the model's account of what it did.
    """
    denied_ids = {d.get("tool_use_id") for d in permission_denials or [] if isinstance(d, dict)}
    server = [c for c in calls_log or [] if "tool" in c]
    used = [False] * len(server)
    log, seen = [], set()
    for call in tool_calls:
        kind = SEARCH_KIND.get(call.get("name"))
        if not kind:
            continue
        seen.add(call.get("id"))
        given = call.get("input") or {}
        asked = given.get("query") if kind == "search" else given.get("url")
        if refused(call, denied_ids):
            outcome = "refused"
        elif call.get("is_error") or call.get("is_error") is None:
            outcome = "error"
        else:
            outcome = "returned"
        urls, targets = [], []
        if call["name"].startswith("mcp__web__"):
            tool = call["name"].rsplit("__", 1)[-1]
            for i, line in enumerate(server):
                if not used[i] and line.get("tool") == tool and \
                        (line.get("args") or {}).get("query" if kind == "search" else "url") == asked:
                    used[i] = True
                    urls, targets = line.get("returned_urls") or [], line.get("targets") or []
                    break
        elif outcome == "returned":
            urls = [asked] if kind == "fetch" else \
                re.findall(r"https?://[^\s\"')\]>]+", call.get("result_excerpt") or "")
        log.append({"id": call.get("id"), "tool": call.get("name"), "kind": kind,
                    "query_or_url": asked, "outcome": outcome,
                    "urls_returned": urls, "targets": targets})
    for denial in permission_denials or []:
        if not isinstance(denial, dict):
            continue
        kind = SEARCH_KIND.get(denial.get("tool_name"))
        if not kind or denial.get("tool_use_id") in seen:
            continue
        given = denial.get("tool_input") or {}
        log.append({"id": denial.get("tool_use_id"), "tool": denial.get("tool_name"), "kind": kind,
                    "query_or_url": given.get("query") if kind == "search" else given.get("url"),
                    "outcome": "refused", "urls_returned": [], "targets": []})
    for i, line in enumerate(server):
        if not used[i]:          # the server saw a call the stream never showed
            kind = "search" if line.get("tool") == "search" else "fetch"
            log.append({"id": None, "tool": f"mcp__web__{line.get('tool')}", "kind": kind,
                        "query_or_url": (line.get("args") or {}).get("query" if kind == "search" else "url"),
                        "outcome": "returned", "urls_returned": line.get("returned_urls") or [],
                        "targets": line.get("targets") or [], "server_only": True})
    return log


def classify_room(mode: str, invocation: dict, calls_log: list[dict] | None) -> tuple[str, list[str]]:
    """Did this room give the skill the conditions its mode promises?

    Decided only from evidence about the room — never from what the skill did
    with it. An earlier draft called a canned run with zero calls harness-invalid,
    which would have moved the worst accounting failure, `yes` rows with no
    search behind them, out of scoring altogether. A room that connected and
    offered search was a valid room whatever the skill then chose.
    """
    reasons = []
    if invocation.get("fire") != "fired":
        reasons.append(f"the installed skill never fired ({invocation.get('fire')})"
                       if invocation.get("via", "skill") == "skill" else
                       f"the module's playbook was not read through the front door ({invocation.get('fire')})")
    init = invocation.get("init") or {}
    calls = invocation.get("tool_calls") or []
    denied_ids = {d.get("tool_use_id") for d in
                  (invocation.get("result") or {}).get("permission_denials") or []
                  if isinstance(d, dict)}
    if not init:
        reasons.append("no init event, so the room's tools and servers are unknown")
        return ("harness-invalid", reasons)
    servers = {s.get("name"): s.get("status") for s in init.get("mcp_servers") or []
               if isinstance(s, dict)}
    tools = set(init.get("tools") or [])
    if mode == "canned":
        if "web" not in servers:
            reasons.append("the research server is not among the room's MCP servers")
        elif servers["web"] != "connected":
            reasons.append(f"the research server's status is {servers['web']!r}, not connected")
        missing = [t for t in ("mcp__web__search", "mcp__web__fetch") if t not in tools]
        if missing:
            reasons.append(f"the room does not offer {', '.join(missing)}")
        present = [t for t in ("WebSearch", "WebFetch") if t in tools]
        if present:
            reasons.append(f"{', '.join(present)} present in a canned room")
        if not any(line.get("rpc") == "initialize" for line in calls_log or []):
            reasons.append("the server's log has no initialize line")
        for call in calls:
            if str(call.get("name", "")).startswith("mcp__web__") and call.get("is_error") \
                    and not refused(call, denied_ids):
                reasons.append(f"the research server returned an error: "
                               f"{(call.get('result_excerpt') or '')[:120]!r}")
    elif mode == "denied":
        if servers:
            reasons.append(f"MCP server(s) in a denied room: {', '.join(map(str, servers))}")
        for call in calls:
            if call.get("name") in SEARCH_KIND and call.get("is_error") is False:
                reasons.append(f"{call['name']} returned a result in a denied room")
    else:
        reasons.append(f"unknown research mode {mode!r}")
    return ("harness-invalid", reasons) if reasons else ("ok", [])


# --- Rooms, modes and where their files live --------------------------------------

def modes_of(case: dict) -> list[str]:
    return list((case.get("research") or {}).get("modes") or ["denied"])


def stem_for(skill: str, case: dict, mode: str, run: int) -> str:
    """The one name every file of a run shares.

    A fixture run in two rooms needs the mode in its name or the rooms overwrite
    each other's responses and grades. A denied-only fixture keeps the old
    name, so sets saved before modes existed are still found.
    """
    if modes_of(case) == ["denied"]:
        return f"{skill}-{case['id']}.run{run}"
    return f"{skill}-{case['id']}.{mode}.run{run}"


def runs_on_disk(out: Path, skill: str, case: dict, mode: str) -> list[int]:
    prefix = stem_for(skill, case, mode, 0)[:-len(".run0")]
    pattern = re.compile(rf"^{re.escape(prefix)}\.run(\d+)\.md$")
    return sorted(int(m.group(1)) for p in out.glob("*.md") if (m := pattern.match(p.name)))


def sidecar_dirs(room: Path) -> list[Path]:
    """Scratchpads a nested session may write to instead of its own directory.

    A `claude -p` subprocess is given its own scratchpad outside its working
    directory, and a skill told to save a file will reasonably use it. Scanning
    only the room found nothing and made a skill that had delivered look like a
    skill that had claimed to — the harness reporting a false negative about a
    false positive. The room's directory name carries this run's unique id, so
    the sidecar can be found by that rather than by reconstructing the host's
    path-mangling scheme.
    """
    parent = Path("/tmp/claude-0")
    if not parent.is_dir():
        return []
    return [child for child in parent.iterdir()
            if child.is_dir() and room.name in child.name]


class RoomLeak(Exception):
    """A research file would land where the response's files are collected."""


def research_paths(out: Path, room: Path, which: str) -> dict[str, Path]:
    """Config, corpus and call log for one invocation, outside the room.

    Everything in the room or its scratchpad is collected and graded as the
    response, so a corpus there would be graded as research the skill did. One
    set per invocation, because workers run concurrently and a nudged re-run's
    calls must never be read as the first attempt's.
    """
    base = out.resolve() / "research"
    paths = {kind: base / f"{room.name}.{which}.{ext}"
             for kind, ext in (("mcp", "mcp.json"), ("corpus", "corpus.json"),
                               ("calls", "calls.jsonl"))}
    forbidden = [room.resolve(), *(d.resolve() for d in sidecar_dirs(room))]
    for path in paths.values():
        if not path.is_absolute() or any(path == f or f in path.parents for f in forbidden):
            raise RoomLeak(f"{path} lies inside {room} or its scratchpad")
    return paths


def room_flags(mode: str, paths: dict | None = None) -> list[str]:
    """The flags that make a room the mode it claims to be.

    Both modes drop user settings, which could otherwise allow a search tool and
    turn a denied room live without a trace. Denied keeps WebSearch and WebFetch
    present and refused — never --disallowedTools — because that is the
    condition every historical `unavailable` was measured under. Canned removes
    them, so the only search the skill can reach is the fixture's.
    """
    if mode == "denied":
        return ["--setting-sources", "project", "--strict-mcp-config"]
    if mode == "canned":
        if not paths:
            raise ValueError("a canned room needs its research paths")
        return ["--setting-sources", "project", "--mcp-config", str(paths["mcp"]),
                "--strict-mcp-config", "--allowedTools", "mcp__web__search", "mcp__web__fetch",
                "--disallowedTools", "WebSearch", "WebFetch"]
    raise ValueError(f"unknown research mode {mode!r}")


def write_research_files(case: dict, paths: dict) -> None:
    research = case.get("research") or {}
    paths["corpus"].parent.mkdir(parents=True, exist_ok=True)
    paths["corpus"].write_text(json.dumps({"entity_tokens": research.get("entity_tokens", []),
                                           "pages": research.get("pages", []),
                                           "user_pages": research.get("user_pages", [])}, indent=1))
    paths["mcp"].write_text(json.dumps({"mcpServers": {"web": {
        "type": "stdio", "command": "python3",
        "args": ["-I", str(SERVER), str(paths["corpus"]), str(paths["calls"])]}}}, indent=1))


def read_calls(path: Path | None) -> list[dict]:
    if not path or not Path(path).exists():
        return []
    lines = []
    for line in Path(path).read_text().splitlines():
        try:
            lines.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return lines


TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".csv"}
MAX_ARTIFACT = 200_000


def collect_artifacts(room: Path, skill_dir: Path) -> list[tuple[str, str]]:
    """Return (name, content) for every text file the run produced.

    A skill that delivers by writing a file — mock-interview saves its pack as
    markdown and presents it — leaves only a cover note in the chat stream.
    Grading that note against expectations about the pack's contents scores the
    wrong artifact, and scores it badly.
    """
    found = []
    for base in [room, *sidecar_dirs(room)]:
        for path in sorted(base.rglob("*")):
            if not path.is_file() or skill_dir == path or skill_dir in path.parents:
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                found.append((path.name, path.read_text()[:MAX_ARTIFACT]))
            except (OSError, UnicodeDecodeError):
                continue
    return found


# --- Rooms and attempts: what both drivers share (run_transcripts.py imports these) --------------

# A generated file larger than this is listed in the inventory but not copied (`truncated`), which leaves
# the sentinel scan's evidence incomplete for that attempt (output_checks.scan_sentinels).
MAX_COPY = 20_000_000


class Room(NamedTuple):
    """One prepared clean room: its folder, run id, the installed command a nudge names, the installed
    names (plugin layout; None in the project layout), the install's folder, the research paths
    (canned; None in a denied room) and the room's flags (room_flags, plus the model and the plugin's)."""
    room: Path
    run_id: str
    name: str
    names: dict | None
    skill_dir: Path
    paths: dict | None
    flags: list


def prepare_room(skill: str, case: dict, out: Path, mode: str, via: str = "skill", layout: str = "project",
                 nudged: bool = False, which: str | None = None, model: str | None = None,
                 prefix: str | None = None) -> Room:
    """A fresh room for one attempt, exactly as execute() has always built one: a new run id, the room's
    folder, the install (the module alone, or the front door in a plugin beside the room), a canned room's
    research files (`which` names them, `first` or `nudged` by default) and the flags. `prefix` names the
    room in place of the layout's default (`<skill>-<id>` in the project layout, `case-<id>` in a plugin),
    for a driver whose rooms are named otherwise."""
    run_id = uuid.uuid4().hex[:8]
    if prefix is None:
        prefix = f"{skill}-{case['id']}" if layout == "project" else f"case-{case['id']}"
    room = out / "rooms" / f"{prefix}-{mode}-{run_id}"
    room.mkdir(parents=True, exist_ok=True)
    if layout == "plugin":
        skill_dir, names = install_in_plugin(room, run_id, None if via == "tuesday" else skill)
        listed = run_routing.HUB if via == "tuesday" else skill
        name = run_routing.installed_command(names[listed], run_routing.plugin_prefix(names, "plugin"))
    else:
        name = install_one(room, skill, run_id)
        skill_dir, names = room / ".claude" / "skills" / name, None
    paths = research_paths(out, room, which or ("nudged" if nudged else "first")) \
        if mode == "canned" else None
    if paths:
        write_research_files(case, paths)
    flags = room_flags(mode, paths) + (["--model", model] if model else [])
    if layout == "plugin":
        flags = plugin_flags(flags, room)
    return Room(room, run_id, name, names, skill_dir, paths, flags)


def installed_watch_out(skill: str, room: Room, via: str) -> dict:
    """The watch-out line the payload installed in `room` declares for `skill` (output_checks.
    declared_watch_out), its sha256, and where in the install it was read: the module's SKILL.md alone,
    or the hub's copy of its playbook through the front door. Recorded in each meta, so a re-check in
    another checkout holds a run to the line its own revision shipped (check_run)."""
    if via == "tuesday" and room.names:
        path = room.skill_dir / "skills" / room.names[run_routing.HUB] / "references" / f"{skill}.md"
    elif room.names:
        path = room.skill_dir / "skills" / room.names[skill] / "SKILL.md"
    else:
        path = room.skill_dir / "SKILL.md"
    line = output_checks.declared_watch_out(path.read_text()) if path.exists() else None
    base = room.skill_dir if room.names else room.skill_dir.parent
    return {"line": line, "sha256": hashlib.sha256(line.encode("utf-8")).hexdigest() if line else None,
            "read_from": path.relative_to(base).as_posix() if base in path.parents else str(path)}


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, data) -> None:
    """Write JSON atomically: a temporary file beside it, then a rename, so a reader never sees half. The
    runtime account email is masked (masked): no record the drivers write keeps it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(masked(data), indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def suffixed(name: str, tag: str) -> str:
    """A file or folder name with `~<tag>` after its stem: `<stem>~<tag>.meta.json` for a run's file,
    `<room>~<tag>.partial.jsonl` for a room's, so readers that glob by suffix still find it."""
    match = STEM_FILE.match(name)
    if match:
        return f"{match.group(1)}~{tag}{match.group(2) or ''}"
    head, dot, tail = name.partition(".")
    return f"{head}~{tag}{dot}{tail}"


def unclaimed(path: Path, tag: str | None) -> Path:
    """`path` when nothing is there; otherwise the same name suffixed with `tag` (the pass id), then a
    count: a snapshot or a move into killed/ never overwrites what is already kept."""
    if not path.exists():
        return path
    tag = tag or new_pass_id()
    candidate, n = path.with_name(suffixed(path.name, tag)), 2
    while candidate.exists():
        candidate, n = path.with_name(suffixed(path.name, f"{tag}-{n}")), n + 1
    return candidate


def inflight_marker(out: Path, base: str) -> Path:
    """The record of one attempt kept while its run is unfinished: `inflight/<room>[.<label>].json`.
    A runner that dies mid-run (a restart, the owner's guard) leaves it, and recovery reads it
    (killed_survey); the runner removes it once the run's meta is written."""
    return out / "inflight" / f"{base}.json"


def take_inflight(meta: dict) -> list[str]:
    """The in-flight records of a run's attempts, taken off its invocations before its meta is written."""
    return [m for inv in meta.get("invocations") or [] if (m := inv.pop("inflight", None))]


def clear_inflight(out: Path, markers: list[str]) -> None:
    """Remove the in-flight records of a run whose meta is now written."""
    for marker in markers:
        (out / marker).unlink(missing_ok=True)


def save_init(out: Path, event: dict | None) -> str | None:
    """Keep a run's init event once under `init/<init_sha256>.json` (run_routing.init_evidence: the event
    without the keys that differ on every run, so runs that started alike share one file; the stream
    holds the whole event). Return the sha, or None for a run with no init event."""
    if not isinstance(event, dict):
        return None
    sha, kept = run_routing.init_evidence(event)
    path = out / "init" / f"{sha}.json"
    if not path.exists():
        write_json(path, kept)
    return sha


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def snapshot_files(room: Path, skill_dir: Path, dest: Path, out: Path | None = None) -> list[dict]:
    """Copy every file a run left in its room and its scratchpad (sidecar_dirs), of any suffix, to
    `dest/<base>/<relative path>`, `<base>` being `room` or `scratchpad`; return the inventory. Only the
    install (`skill_dir`) is skipped, and symbolic links are not followed. Each entry is {"base", "path",
    "bytes", "sha256", "copy" (relative to `out` when given), "truncated"}: a file over MAX_COPY is listed
    and not copied, `truncated`, which leaves the sentinel scan's evidence incomplete. collect_artifacts,
    the graders' view, is separate and unchanged."""
    entries = []
    sidecars = sidecar_dirs(room)
    bases = [("room", room)] + [("scratchpad" if i == 0 else f"scratchpad-{i + 1}", d)
                                for i, d in enumerate(sidecars)]
    for base_name, base in bases:
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_symlink() or not path.is_file() or skill_dir == path or skill_dir in path.parents:
                continue
            rel = path.relative_to(base).as_posix()
            size = path.stat().st_size
            entry = {"base": base_name, "path": rel, "bytes": size, "sha256": file_sha256(path),
                     "copy": None, "truncated": size > MAX_COPY}
            if not entry["truncated"]:
                target = dest / base_name / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                entry["copy"] = target.relative_to(out).as_posix() if out and out in target.parents \
                    else str(target)
            entries.append(entry)
    return entries


def hidden_reach_labels(events, names: dict | None, room: Path) -> list[str]:
    """The hidden modules a run through the front door reached (E16): a routing reader of the front-door
    arm fed every event of the stream, whatever it decided on the way. tuesday_fire stops at the first
    outcome, and the reader settles `void` at the init event, so a reach after either was never read."""
    if not names:
        return []
    reader = run_routing.RunReader(names, "tuesday", None, "plugin", room)
    for line in events:
        event = line
        if not isinstance(line, dict):
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
        if not isinstance(event, dict):
            continue
        try:
            reader.feed(event)
        except (AttributeError, TypeError, KeyError):
            continue        # a malformed event is not a reach, and does not stop the reading
    return [label for label in reader.reached if label.startswith("hidden-")]


def run_attempt(prompt: str, room: Room, out: Path, timeout: int, skill: str, via: str = "skill",
                layout: str = "project", mode: str = "denied", nudged: bool = False, label: str | None = None,
                extra_args=(), pass_id: str | None = None, stem: str | None = None) -> tuple[dict, dict]:
    """Send one prompt in a prepared room and record the attempt; return (invocation, parsed stream).

    The CLI gets `extra_args` before the room's flags (a resumed turn's `--resume <id>`; nothing for a
    fixture run), the room's cwd and child_env(): a fixture run sends exactly what it always has. The
    stream is written as it arrives to `streams/<room>[.<label>].inflight.jsonl` and renamed to `.jsonl`
    when the run answered, or to `.partial.jsonl` on a timeout or a decline, whose stream is kept too.
    While the attempt runs, `inflight/<room>[.<label>].json` records it for recovery.

    The invocation holds today's keys (room, nudged, installed, flags, via, layout, room_writable,
    skill_dir, calls_log, outcome, fire, init, result, tool_calls, research_log, and error for a run that
    did not answer) and the evidence: `stream` (relative to `out`), `stream_sha256`, `init_sha256`
    (save_init), `session_id`, `limit_hit`, `files` (snapshot_files, under `files/<room>[.<label>]/`),
    `partial_evidence` (the attempt was cut mid-run: its stream and files are as far as it got),
    `pass_id`, `names`, and through the front door `hidden_reached` (hidden_reach_labels). A declined
    attempt also keeps its exit code (`returncode`) and the head of its stderr (`stderr_head`)."""
    flags = [*extra_args, *room.flags]
    invocation = {"room": str(room.room), "nudged": nudged, "installed": room.name, "flags": flags,
                  "via": via, "layout": layout, "room_writable": room_writable(flags, room.room),
                  "skill_dir": str(room.skill_dir),
                  "calls_log": str(room.paths["calls"]) if room.paths else None}
    base = room.room.name + (f".{label}" if label else "")
    streams = out / "streams"
    streams.mkdir(parents=True, exist_ok=True)
    inflight = streams / f"{base}.inflight.jsonl"
    marker = inflight_marker(out, base)
    record = {"stem": stem, "label": label, "pass_id": pass_id, "started": utc_now(), "state": "running",
              "stream": inflight.relative_to(out).as_posix(), "invocation": invocation}
    write_json(marker, record)
    error = None
    try:
        parsed = claude(prompt, room.room, timeout, flags, "stream", room.name, stream_to=inflight)
        stdout = parsed.pop("stdout", "")
    except RuntimeError as exc:
        # A timeout or a decline keeps what it streamed, so the record says how far the run got.
        error, stdout, parsed = exc, decode(getattr(exc, "partial", "")), None
    if not inflight.exists():           # a stand-in for the CLI that returned its stdout unwritten
        inflight.write_bytes(stdout.encode("utf-8"))
    final = unclaimed(streams / f"{base}{'.partial' if error else ''}.jsonl", pass_id)
    os.replace(inflight, final)
    lines = stdout.splitlines()
    if parsed is None:
        parsed = parse_stream(lines, room.name)
    if via == "tuesday":
        parsed["fire"] = tuesday_fire(lines, room.names, skill, room.room)
    calls = read_calls(room.paths["calls"]) if room.paths else []
    research = build_research_log(parsed["tool_calls"], parsed["result"]["permission_denials"], calls)
    if error is None:
        invocation.update(outcome="completed", fire=parsed["fire"], skills_fired=parsed["skills_fired"],
                          init=parsed["init"], result=parsed["result"], tool_calls=parsed["tool_calls"],
                          research_log=research)
    else:
        invocation.update(outcome="timeout" if isinstance(error, CLITimeout) else "declined",
                          error=masked(str(error)), fire=parsed["fire"], init=parsed["init"],
                          result=parsed["result"], tool_calls=parsed["tool_calls"], research_log=research)
        if isinstance(error, CLIDeclined):
            # How the CLI declined, which a reader of the outcome needs and the message does not carry whole:
            # its exit code and the head of its stderr (a refused resume or a limit at start prints there),
            # the runtime account email masked (output_checks.runtime_sentinels: never written).
            invocation.update(returncode=error.returncode, stderr_head=masked((error.stderr_head or "")[:STDERR_KEPT]))
    init_event = parsed.get("init_event")
    invocation.update(
        stream=final.relative_to(out).as_posix(), stream_sha256=file_sha256(final),
        init_sha256=save_init(out, init_event),
        session_id=(init_event or {}).get("session_id") or parsed["result"].get("session_id"),
        limit_hit=bool(getattr(error, "limit", False)),
        files=snapshot_files(room.room, room.skill_dir, unclaimed(out / "files" / base, pass_id), out),
        partial_evidence=error is not None, pass_id=pass_id, inflight=marker.relative_to(out).as_posix())
    if room.names:
        invocation["names"] = dict(room.names)
    if via == "tuesday":
        invocation["hidden_reached"] = hidden_reach_labels(lines, room.names, room.room)
    write_json(marker, {**record, "state": "ended", "stream": invocation["stream"], "invocation": invocation})
    return invocation, parsed


# --- The sentinel scan's evidence, read back from a run's saved files ------------------------------------

def run_folder(out: Path, inv: dict) -> list[Path]:
    """Where an invocation's saved files may be: the folder it is read from, then the folder it was run
    in (its room's grandparent), for a run copied elsewhere (--regrade-from)."""
    folders = [out]
    room = inv.get("room")
    if room and Path(room).parent.name == "rooms" and Path(room).parent.parent not in folders:
        folders.append(Path(room).parent.parent)
    return folders


def saved_stream(out: Path, inv: dict) -> Path | None:
    """An invocation's saved stream: the one it records, or for a run saved before invocations recorded
    one, its room's `streams/<room>.jsonl` or `.partial.jsonl`; None when there is none."""
    for folder in run_folder(out, inv):
        if inv.get("stream"):
            candidates = [folder / inv["stream"]]
        else:
            room = Path(inv.get("room") or "").name
            candidates = [folder / "streams" / f"{room}.jsonl", folder / "streams" / f"{room}.partial.jsonl"] \
                if room else []
        found = next((p for p in candidates if p.is_file()), None)
        if found:
            return found
    return None


def read_events(path: Path) -> list[dict]:
    """Every JSON object of a saved stream, in order; lines that are not one are skipped."""
    events = []
    for line in read_back(path).splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def zip_members(data: bytes) -> list[tuple[str, str]]:
    """(name, text) for each member of a zip-format file (docx, xlsx, odt); [] for any other file."""
    return file_parts(data)[0] if data.startswith(b"PK") else []


PDF_STREAM = re.compile(rb"stream\r?\n(.*?)\r?\n?endstream", re.S)


def file_parts(data: bytes) -> tuple[list[tuple[str, str]], str | None]:
    """What the scan reads inside a generated file beyond its text, and why part of it could not be read:
    each member of a zip-format file (docx, xlsx, odt); each content stream of a PDF, inflated where it is
    FlateDecode-compressed (a compressed text layer is otherwise unread bytes). The reason is set for a zip
    that cannot be opened or holds a member over MAX_COPY, a PDF stream that cannot be inflated, and a file
    that is neither UTF-8 text, a zip nor a PDF: what the scan cannot read is never scored clean."""
    if data.startswith(b"PK"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                infos = [info for info in z.infolist() if not info.is_dir()]
                members = [(info.filename, z.read(info).decode("utf-8", errors="replace"))
                           for info in infos if info.file_size <= MAX_COPY]
        except (zipfile.BadZipFile, OSError, RuntimeError, ValueError, EOFError, zlib.error):
            return [], "a zip that cannot be opened"
        over = [info.filename for info in infos if info.file_size > MAX_COPY]
        return members, f"a member over {MAX_COPY} bytes ({over[0]})" if over else None
    if data.startswith(b"%PDF"):
        members, reason = [], None
        for n, m in enumerate(PDF_STREAM.finditer(data), 1):
            body = m.group(1)
            dictionary = data[:m.start()].rsplit(b"obj", 1)[-1]
            if b"FlateDecode" in dictionary:
                try:
                    body = zlib.decompressobj().decompress(body)
                except zlib.error:
                    reason = reason or f"PDF stream {n} cannot be inflated"
                    continue
            members.append((f"pdf stream {n}", body.decode("latin-1")))
        return members, reason
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return [], "neither UTF-8 text, a zip nor a PDF"
    return [], None


def inventory_texts(out: Path, inv: dict) -> list[dict] | None:
    """An invocation's generated files as the scan reads them: {"path": "<base>/<path>", "text",
    "members", "truncated"}, read from their copies (file_parts: zip members, a PDF's streams). None when
    the invocation kept no inventory; a copy that cannot be read, or a part of one (file_parts' reason,
    kept as `unreadable`), counts as truncated, so the evidence is incomplete rather than clean."""
    files = inv.get("files")
    if not isinstance(files, list):
        return None
    texts = []
    for entry in files:
        if not isinstance(entry, dict):
            continue
        data, truncated = None, bool(entry.get("truncated"))
        if not truncated and entry.get("copy"):
            for folder in run_folder(out, inv):
                path = Path(entry["copy"]) if Path(entry["copy"]).is_absolute() else folder / entry["copy"]
                if path.is_file():
                    data = path.read_bytes()
                    break
        if data is None:
            truncated = True
        members, unreadable = file_parts(data or b"")
        texts.append({"path": f"{entry.get('base', 'room')}/{entry.get('path', '')}",
                      "text": (data or b"").decode("utf-8", errors="replace"),
                      "members": members, "truncated": truncated or unreadable is not None,
                      **({"unreadable": unreadable} if unreadable else {})})
    return texts


def attempt_evidence(out: Path, meta: dict) -> list[dict]:
    """Every attempt of a saved run as the sentinel scan reads it (output_checks.scan_sentinels): the
    first attempt and the nudged one, completed, timed out, declined or killed alike, each labelled
    (`first`, `nudged`), with every event of its saved stream, whether a result event arrived, a canned
    room's server call log, and its generated files read from their copies. Pure reading of saved files."""
    attempts = []
    canned = meta.get("mode") == "canned"
    for inv in meta.get("invocations") or []:
        stream = saved_stream(out, inv)
        events = read_events(stream) if stream else None
        calls = None
        if inv.get("calls_log"):
            log = Path(inv["calls_log"])
            found = next((p for p in (log, out / "research" / log.name) if p.is_file()), None)
            calls = read_calls(found) if found else None
        attempts.append({"label": inv.get("label") or ("nudged" if inv.get("nudged") else "first"),
                         "outcome": inv.get("outcome"), "events": events,
                         "complete": any(e.get("type") == "result" for e in events or []),
                         "calls_log": calls, "canned": canned, "files": inventory_texts(out, inv)})
    return attempts


def evidence_problems(meta: dict, out: Path, case: dict) -> list[str]:
    """What a run declaring `sentinels` lacks for its scan to be scored (output_checks.scan_sentinels'
    `missing`): an attempt with no stream or no parsed event, a canned attempt with no call log, no
    file inventory or a truncated file. [] for a fixture that declares none. A declared list that breaks
    the freezing rules is not read here: sentinel_reasons gives it as its own reason."""
    if not case.get("sentinels"):
        return []
    return list(output_checks.scan_sentinels(case["sentinels"], attempt_evidence(out, meta))["scan"]["missing"])


def sentinel_reasons(meta: dict, out: Path, case: dict) -> list[str]:
    """Why a run's sentinel scan cannot be scored, as harness reasons: each problem of the fixture's declared
    list ("sentinel declaration: …", output_checks.sentinel_declaration_reasons), so a mistyped or
    one-spelling list never scores clean; else each piece of missing evidence ("sentinel scan: …")."""
    declared = output_checks.sentinel_declaration_reasons(case)
    return declared or [f"sentinel scan: {m}" for m in evidence_problems(meta, out, case)]


# --- Execute ---------------------------------------------------------------------------

def harness_status(meta: dict) -> tuple[str, list[str]]:
    """ok, or harness-invalid with reasons — for runs saved before and after this record."""
    if not meta:
        return "harness-invalid", ["no record of this run"]
    if meta.get("harness"):
        return meta["harness"].get("status", "ok"), list(meta["harness"].get("reasons", []))
    if meta.get("error"):
        return "harness-invalid", [f"skipped: {meta['error']}"]
    if meta.get("skill_fired") is False:
        return "harness-invalid", ["the installed skill never fired"]
    return "ok", []


def write_meta(out: Path, stem: str, meta: dict) -> None:
    """Write a run's meta atomically (a temporary file, then a rename), the runtime account email masked."""
    path = out / f"{stem}.meta.json"
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(masked(meta), indent=2) + "\n")
    os.replace(tmp, path)


def refusals(invocation: dict) -> tuple[dict[str, int] | None, bool | None]:
    """The tool calls the CLI refused an invocation for want of permission, counted by tool, and
    whether a save (SAVE_TOOLS) was among them, from its result event's `permission_denials`.
    (None, None) for a run that ended before its result event: its list was never read, so it is
    not counted as none. Recorded on every run and reported, never scored."""
    result = invocation.get("result") or {}
    if not result or result.get("incomplete"):
        return None, None
    counts: dict[str, int] = {}
    for denial in result.get("permission_denials") or []:
        if isinstance(denial, dict):
            tool = str(denial.get("tool_name"))
            counts[tool] = counts.get(tool, 0) + 1
    return dict(sorted(counts.items())), any(tool in counts for tool in SAVE_TOOLS)


def run_date(meta: dict) -> datetime.date | None:
    """The date a run recorded as `run_date`, which its fixture's relative dates were written
    for; None for a run saved before runs recorded one, whose fixture is then written at its
    `date_anchor` (fixture_clauses.dated), the text such a run was sent."""
    try:
        return datetime.date.fromisoformat(meta.get("run_date") or "")
    except (TypeError, ValueError):
        return None


def execute(skill: str, case: dict, out: Path, run: int, timeout: int,
            model: str | None, mode: str | None = None, via: str = "skill",
            layout: str | None = None, on: datetime.date | None = None, *, pass_id: str | None = None) -> dict:
    """Run one fixture in a clean room and save the response plus the room's record.

    In a plugin (`layout="plugin"`, which the front door always is) the room is named for the
    case alone, since the plugin's folder path reaches the model and a module's name in it would
    point the route. The fixture's relative dates are written for the run's date, `on` (today
    unless given), which the meta records as `run_date`. Each attempt is a prepare_room and a
    run_attempt, the same sequence and the same prompts as before they were split out, so a run
    sends exactly what it always has. The meta also records the pass (`pass_id`) and the watch-out
    line the installed payload declares (`declared_watch_out`), and a fixture declaring `sentinels`
    whose list breaks the freezing rules or whose scan evidence is incomplete is harness-invalid
    (sentinel_reasons). The account email is masked in the meta and every printed line (masked).
    """
    layout = layout or ("plugin" if via == "tuesday" else "project")
    if via == "tuesday" and layout != "plugin":
        raise ValueError("the front door is installed as the plugin it ships as: layout plugin")
    on = on or datetime.date.today()
    case = dated(case, on)
    mode = mode or modes_of(case)[0]
    stem = stem_for(skill, case, mode, run)
    meta = {"skill": skill, "id": case["id"], "run": run, "mode": mode, "stem": stem,
            "model": model, "via": via, "layout": layout, "run_date": on.isoformat(), "pass_id": pass_id,
            "invocations": []}
    parsed = None
    for nudged in (False, True):
        room = prepare_room(skill, case, out, mode, via, layout, nudged, model=model)
        if "declared_watch_out" not in meta:
            meta["declared_watch_out"] = installed_watch_out(skill, room, via)
        prompt = case["prompt"] if not nudged else \
            f"Use the {room.name} skill for this.\n\n{case['prompt']}"
        invocation, parsed = run_attempt(prompt, room, out, timeout, skill, via, layout, mode, nudged,
                                         pass_id=pass_id, stem=stem)
        meta["invocations"].append(invocation)
        if invocation["outcome"] != "completed":
            # A timeout or a decline keeps what it streamed and the files it left, so the record says
            # how far the run got. Neither is nudged — a second attempt at a run the CLI would not
            # finish is not a fix.
            refused, save_refused = refusals(invocation)
            meta.update(error=invocation["error"], outcome=invocation["outcome"],
                        graded_invocation=None, research_log=None,
                        refused=refused, save_refused=save_refused, room_writable=invocation["room_writable"],
                        harness={"status": "harness-invalid", "reasons": [f"skipped: {invocation['error']}"]})
            markers = take_inflight(meta)
            write_meta(out, stem, meta)
            clear_inflight(out, markers)
            print(masked(f"  SKIPPED {skill} eval {case['id']} [{mode}] (run {run}): {invocation['error']}"),
                  flush=True)
            return meta
        if invocation["fire"] == "fired":
            break
        # The skill not firing is the routing eval's finding, not this one's.
        # Here it would leave the expectations ungraded, so the fixture is re-run
        # with the skill named — in a new room, so nothing the first attempt
        # wrote or searched is credited to the response that gets graded.

    graded = meta["invocations"][-1]
    status, reasons = classify_room(mode, graded, read_calls(graded.get("calls_log")))
    room = Path(graded["room"])
    artifacts = collect_artifacts(room, Path(graded["skill_dir"]))
    text = parsed["text"]
    if artifacts:
        text += "\n\n" + "\n\n".join(
            f"----- file the response produced: {name_} -----\n{content}"
            for name_, content in artifacts)
    body = out / f"{stem}.md"
    body.write_text(text)
    meta.update(graded_invocation=len(meta["invocations"]) - 1,
                triggered_unprompted=not graded["nudged"],
                skill_fired=graded["fire"] == "fired", fire=graded["fire"],
                chars=len(text), response_file=body.name, artifacts=[a[0] for a in artifacts],
                research_log=graded["research_log"],
                harness={"status": status, "reasons": reasons})
    meta["refused"], meta["save_refused"] = refusals(graded)
    meta["room_writable"] = graded["room_writable"]
    missing = sentinel_reasons(meta, out, case)
    if missing:
        # The scan cannot read what it must, or reads a list that may look for the wrong value: the run is
        # not graded and is out of every denominator.
        meta["harness"] = {"status": "harness-invalid", "reasons": reasons + missing}
        status, reasons = "harness-invalid", meta["harness"]["reasons"]
    markers = take_inflight(meta)
    write_meta(out, stem, meta)
    clear_inflight(out, markers)
    init = graded.get("init") or {}
    read, unread = output_checks.user_link_reads(graded["research_log"], case.get("research"))
    links = sum(len(fetches) for fetches in [*read.values(), *unread.values()])
    where = " via the front door" if via == "tuesday" else " alone, in a plugin" if layout == "plugin" else ""
    refused = ", ".join(f"{tool} {n}" for tool, n in (meta["refused"] or {}).items())
    print(masked(f"  ran {skill} eval {case['id']} [{mode}]{where} "
          f"(run {run}): {len(text)} chars"
          f"{f', {len(artifacts)} file(s)' if artifacts else ''}"
          f"{'' if not graded['nudged'] else ' (needed a nudge to fire)'}"
          f", {len(graded['research_log']) - links} research call(s)"
          f"{f', {len(read)} user link(s) read' if read else ''}"
          f"{f', {len(unread)} user link(s) not opened' if unread else ''}"
          f"{f', refused {refused}' + (' (a save among them)' if meta['save_refused'] else '') if refused else ''}"
          f", model {init.get('model')}"
          f"{'' if status == 'ok' else ' — HARNESS-INVALID: ' + '; '.join(reasons)}"), flush=True)
    return meta


# --- Grade -------------------------------------------------------------------------------

def parse_verdicts(text: str, n_expected) -> dict:
    """Recover verdicts from a grader reply, whole or truncated, in any key order.

    A long grade can be cut off mid-object. Read strictly, that yields zero
    verdicts, and a summary that counts missing verdicts as failures turns one
    truncated reply into a fixture where everything failed. The first salvage
    regex needed "n" first and "verdict" after it, and its lazy match could run on
    into the next object — so a why-first schema would have broken it, and an
    object missing its verdict would have borrowed the next one's. Each object is
    now decoded on its own at each "{". A reply that covers fewer expectations
    than it was given is recorded as incomplete, never scored as failures.

    `n_expected` is the number of expectations, or the list of numbers asked.
    """
    expected = list(range(1, n_expected + 1)) if isinstance(n_expected, int) \
        else sorted(set(n_expected))
    candidates, truncated = None, False
    stripped = (text or "").strip()
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    for blob in ([stripped, match.group(0)] if match else [stripped]):
        try:
            whole = json.loads(blob)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(whole, dict) and isinstance(whole.get("verdicts"), list):
            candidates = [v for v in whole["verdicts"] if isinstance(v, dict)]
            break
    if candidates is None:
        truncated, candidates, pos = True, [], 0
        decoder = json.JSONDecoder()
        while (start := stripped.find("{", pos)) != -1:
            try:
                obj, end = decoder.raw_decode(stripped, start)
            except json.JSONDecodeError:
                pos = start + 1
                continue
            if isinstance(obj, dict) and "n" in obj and "verdict" in obj:
                candidates.append(obj)
                pos = end
            else:
                pos = start + 1

    valid: dict[int, dict] = {}
    invalid, duplicates, conflicted = [], [], set()
    for v in candidates:
        n = v.get("n")
        if isinstance(n, bool) or not isinstance(n, int) or n not in expected:
            invalid.append({"n": n, "reason": "number out of range"})
            continue
        if v.get("verdict") not in ("PASS", "FAIL"):
            invalid.append({"n": n, "reason": f"verdict {v.get('verdict')!r} is not PASS or FAIL"})
            conflicted.add(n)
            continue
        if n in valid or n in conflicted:
            duplicates.append(n)
            if n in valid and valid[n]["verdict"] != v["verdict"]:
                invalid.append({"n": n, "reason": "two different verdicts"})
                conflicted.add(n)
                del valid[n]
            continue
        valid[n] = v
    for n in conflicted:
        valid.pop(n, None)
    verdicts = [valid[n] for n in sorted(valid)]
    incomplete = [n for n in expected if n not in valid]
    result = {"verdicts": verdicts, "expected": expected, "incomplete": incomplete,
              "missing": [n for n in incomplete if n not in conflicted],
              "duplicates": sorted(set(duplicates)), "invalid": invalid}
    if truncated:
        result["truncated"] = True
    if not verdicts:
        result["error"] = "grader returned no usable verdicts"
        result["raw"] = (text or "")[:2000]
    return result


def observed_block(meta: dict, research: dict | None = None) -> str:
    """The three states graders must be told apart: not recorded, none, and these.

    A search line names the URLs the room returned for it, so an expectation that
    turns on which pages a run was shown (mock-interview eval 7's cheat sheet) can
    be graded from the record rather than inferred from the response.

    A fetch of a link the fixture declares the user gave to read is sorted out by
    `output_checks.user_link_reads`, the classifier the deterministic checks use,
    and listed in its own group: it is reading an input, never in the fetch count,
    and `user links read N` counts the links with a fetch that returned, each once,
    so a grader comparing the tally with this record compares it with the same
    numbers the checks do.
    """
    if meta.get("research_log") is None:
        return ("Not recorded for this run: do not infer whether research was attempted, "
                "and do not grade research counts.")
    log = meta["research_log"]
    links, unopened = output_checks.user_link_reads(log, research)
    calls = [e for e in log if not output_checks.is_user_link(e, research)]

    def line(e: dict) -> str:
        asked = json.dumps(e.get("query_or_url"), ensure_ascii=False) \
            if e.get("kind") == "search" else str(e.get("query_or_url"))
        urls = [str(u) for u in e.get("urls_returned") or []]
        returned = (f", {len(urls)} result(s)" + (f": {', '.join(urls[:10])}" if urls else "")
                    + (f" and {len(urls) - 10} more" if len(urls) > 10 else "")) \
            if e.get("kind") == "search" and e.get("outcome") == "returned" else ""
        return f"- {e.get('kind')} via {e.get('tool')}: {asked} — {e.get('outcome')}{returned}"

    if not log:
        lines = ["Recorded: no search or fetch calls were made."]
    else:
        if not calls:
            lines = ["Recorded: no research search or fetch calls were made."]
        else:
            searches = sum(1 for e in calls if e.get("kind") == "search")
            lines = [f"Recorded: {len(calls)} research call(s) — {searches} search(es), "
                     f"{len(calls) - searches} fetch(es), refused ones included:"]
            lines += [line(e) for e in calls]
        if links:
            fetched = [e for es in links.values() for e in es]
            lines.append(f"User links read: {len(links)} link(s) the user gave to read, fetched and "
                         f"returned ({len(fetched)} fetch(es) listed below) — reading an input, not "
                         f"research, so named on the tally line as `user links read {len(links)}`, each "
                         f"link once however often fetched, and never in its fetch count:")
            lines += [line(e) for e in fetched]
        if unopened:
            fetched = [e for es in unopened.values() for e in es]
            lines.append(f"User links not opened: {len(unopened)} link(s) the user gave to read that no "
                         f"fetch returned — the host refused or errored ({len(fetched)} fetch(es) listed "
                         f"below); not reads, so not counted on the tally line or in its fetch count; the "
                         f"response should say it could not open the link:")
            lines += [line(e) for e in fetched]
    if meta.get("research_log_provenance"):
        lines.append("(Reconstructed from the run's session transcript.)")
    earlier = [inv for i, inv in enumerate(meta.get("invocations") or [])
               if i != meta.get("graded_invocation") and inv.get("research_log")]
    for inv in earlier:
        lines.append(f"An earlier attempt at this request, before the harness named the skill, "
                     f"made {len(inv['research_log'])} call(s). That response was discarded; "
                     f"its calls are not credited to this one.")
    return "\n".join(lines)


def expectation_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def grader_prompt(case: dict, body: str, mode: str, meta: dict, numbers: list[int]) -> str:
    enumerate_ns = set(case.get("enumerate") or [])
    expectations = "\n".join(
        f"{n}. {'[enumerate every site] ' if n in enumerate_ns else ''}{case['expectations'][n - 1]}"
        for n in numbers)
    return GRADER_PROMPT.format(
        research_mode=RESEARCH_MODE[mode], prompt=case["prompt"], response=body,
        begins=RESPONSE_BEGINS, ends=RESPONSE_ENDS,
        observed=observed_block(meta, case.get("research")), expectations=expectations,
        sites=SITES_INSTRUCTION if enumerate_ns & set(numbers) else "")


def grader_flags(model: str | None) -> list[str]:
    """No tools, no MCP, no skills, no settings: a grader reads and answers."""
    return ["--tools", "", "--strict-mcp-config", "--disable-slash-commands",
            "--setting-sources", "project", *(["--model", model] if model else [])]


@functools.lru_cache(maxsize=1)
def cli_version() -> str | None:
    """The JSON result carries no version, so graders' is asked for once."""
    try:
        proc = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=60)
        return proc.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def model_of(usage: dict | None) -> str | None:
    """The model that wrote the reply: the one with the most output tokens."""
    if not usage:
        return None
    return max(usage, key=lambda m: (usage[m] or {}).get("outputTokens", 0))


def untraced_sites(verdicts: list[dict], enumerate_ns) -> dict[str, int]:
    counts = {}
    for v in verdicts:
        if v.get("n") in set(enumerate_ns or []):
            sites = v.get("sites")
            counts[str(v["n"])] = sum(1 for s in sites if isinstance(s, dict)
                                      and s.get("status") == "untraced") \
                if isinstance(sites, list) else -1
    return counts


def grade(skill: str, case: dict, out: Path, run: int, grader: int, timeout: int,
          model: str | None, mode: str | None = None, only=None, *, pass_id: str | None = None) -> dict:
    """Score one saved response against its expectations (or the `only` subset), the fixture's
    relative dates written for the date the run recorded (`run_date`). The grade record names the
    pass that made it (`pass_id`) and the grader prompt's version and sha256."""
    mode = mode or modes_of(case)[0]
    stem = stem_for(skill, case, mode, run)
    base = {"skill": skill, "id": case["id"], "run": run, "mode": mode, "grader": grader}
    body_path = out / f"{stem}.md"
    meta_path = out / f"{stem}.meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    # An expectation is hashed as the fixture writes it, its relative dates unwritten: the
    # question asked is the same on every run date (recurring.py keys verdicts by the hash).
    template = case["expectations"]
    case = dated(case, run_date(meta))
    if not body_path.exists():
        # Silent here would drop the run out of the log entirely, leaving a reader
        # to infer from a gap in the grader numbering that anything happened.
        reason = "no response to grade — the execution was skipped"
        print(f"  no verdicts for {skill} eval {case['id']} [{mode}] (run {run}, grader {grader}): "
              f"{reason}", flush=True)
        return {**base, "error": reason, "verdicts": []}
    status, reasons = harness_status(meta)
    if status != "ok":
        reason = "harness-invalid: " + "; ".join(reasons)
        print(f"  not graded {skill} eval {case['id']} [{mode}] (run {run}, grader {grader}): "
              f"{reason}", flush=True)
        return {**base, "error": reason, "harness_invalid": True, "verdicts": []}

    total = len(case["expectations"])
    numbers = sorted(n for n in set(only or range(1, total + 1)) if 1 <= n <= total)
    body = body_path.read_text()
    flags = grader_flags(model)
    with_room = out / "grading"
    with_room.mkdir(parents=True, exist_ok=True)

    def ask(asked: list[int]) -> tuple[dict, dict | None, str | None]:
        try:
            data = claude(grader_prompt(case, body, mode, meta, asked), with_room, timeout,
                          flags, "json")
            return parse_verdicts(str(data.get("result") or ""), asked), data, None
        except RuntimeError as exc:
            print(masked(f"  SKIPPED grading {skill} eval {case['id']} [{mode}] (run {run}, "
                         f"grader {grader}): {exc}"), flush=True)
            return parse_verdicts("", asked), None, masked(str(exc))

    result, data, declined = ask(numbers)
    usage = dict((data or {}).get("modelUsage") or {})
    regraded = []
    if result["incomplete"] and not declined:
        # One targeted re-grade, same grader, asked only the gaps under their
        # original numbers. A second gap is recorded, not chased.
        retry, extra, _ = ask(result["incomplete"])
        regraded = list(result["incomplete"])
        for k, v in (extra or {}).get("modelUsage", {}).items():
            usage.setdefault(f"{k} (re-grade)", v)
        merged = {v["n"]: v for v in result["verdicts"]}
        merged.update({v["n"]: v for v in retry["verdicts"]})
        result.update(verdicts=[merged[n] for n in sorted(merged)],
                      incomplete=[n for n in numbers if n not in merged],
                      missing=[n for n in retry["missing"]],
                      duplicates=sorted(set(result["duplicates"]) | set(retry["duplicates"])),
                      invalid=result["invalid"] + retry["invalid"])
        if merged:
            result.pop("error", None)
            result.pop("raw", None)
    if declined:
        result["error"] = declined
    record = {**base, **result,
              "regraded": regraded,
              "grader_model": model_of({k: v for k, v in usage.items() if "(re-grade)" not in k}),
              "model_usage": {k: {f: (v or {}).get(f) for f in ("inputTokens", "outputTokens", "costUSD")}
                              for k, v in usage.items()},
              "requested_model": model, "cli_version": cli_version(), "flags": flags,
              "grader_prompt_version": GRADER_PROMPT_VERSION, "grader_prompt_sha256": GRADER_PROMPT_SHA256,
              **({"pass_id": pass_id} if pass_id else {}),
              "expectation_sha256": {str(n): expectation_sha(template[n - 1]) for n in numbers},
              "untraced_sites": untraced_sites(result["verdicts"], case.get("enumerate"))}
    record = masked(record)
    (out / f"{stem}.grade-{grader}.json").write_text(json.dumps(record, indent=2) + "\n")
    verdicts = record["verdicts"]
    # A grade that produced nothing is not a grade of zero. The SKIPPED line above
    # already said what happened; printing "0/12" beside it is the same mistake
    # this harness has now made five times, in the reporting rather than the data.
    if record.get("error") or not verdicts:
        print(masked(f"  no verdicts for {skill} eval {case['id']} [{mode}] (run {run}, grader {grader}): "
                     f"{record.get('error', 'grader returned nothing usable')}"), flush=True)
        return record
    passed = sum(1 for v in verdicts if v.get("verdict") == "PASS")
    gaps = f" (incomplete: {', '.join(map(str, record['incomplete']))})" if record["incomplete"] else ""
    print(f"  graded {skill} eval {case['id']} [{mode}] (run {run}, grader {grader}): "
          f"{passed}/{len(verdicts)} of {len(numbers)}{gaps}", flush=True)
    return record


def graded_files(meta: dict) -> list | None:
    """The graded attempt's generated-file inventory (its invocation's `files`), or None for a run
    that kept none: one saved before the driver listed the files a run wrote, or never graded."""
    graded = meta.get("graded_invocation")
    invocations = meta.get("invocations") or []
    if not isinstance(graded, int) or not 0 <= graded < len(invocations):
        return None
    files = invocations[graded].get("files")
    return files if isinstance(files, list) else None


def declared_line(skill: str, meta: dict) -> str | None:
    """The watch-out line a run is held to: the one its installed payload declared, which execute()
    records in the meta (`declared_watch_out`), so a run is checked against its own revision's line in
    any checkout; for a run saved before metas recorded it, the line this checkout's SKILL.md declares."""
    recorded = meta.get("declared_watch_out")
    if isinstance(recorded, dict) and "line" in recorded:
        return recorded["line"]
    skill_md = REPO / "skills" / skill / "SKILL.md"
    return output_checks.declared_watch_out(skill_md.read_text()) if skill_md.exists() else None


def check_run(skill: str, case: dict, out: Path, run: int, mode: str) -> dict:
    """Run the deterministic checks on one saved response, the fixture's relative dates written
    for the date the run recorded (`run_date`); write {stem}.checks.json.

    A fixture declaring `sentinels`, or a runtime sentinel in the environment (output_checks.
    runtime_sentinels: the account email, read from TUESDAY_SCAN_ACCOUNT_EMAIL and never written), has
    its run's every attempt scanned from the saved evidence (attempt_evidence), first, nudged and cut
    alike; the record keeps the scan (`sentinel_scan`) whatever the harness status."""
    stem = stem_for(skill, case, mode, run)
    meta_path, body_path = out / f"{stem}.meta.json", out / f"{stem}.md"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    case = dated(case, run_date(meta))
    status, reasons = harness_status(meta)
    if status == "ok" and not body_path.exists():
        status, reasons = "harness-invalid", ["no response saved"]
    declared = output_checks.sentinel_declaration_reasons(case)
    if declared and not any(r in reasons for r in declared):
        # A list that breaks the freezing rules may look for the wrong value: such a run never scores clean.
        status, reasons = "harness-invalid", [*(reasons if status != "ok" else []), *declared]
    body = body_path.read_text() if body_path.exists() else ""
    # Every fixture's turn delivers output unless it declares "delivers": "gate_question", so every
    # run is held to the skill's watch-out line, the one its installed payload declared (declared_line);
    # a gate-only turn is held to carrying none, and to writing no file (output_checks.check_gate_only),
    # read from the graded attempt's generated-file inventory where the run kept one.
    line = declared_line(skill, meta)
    gate = case.get("delivers") == output_checks.GATE_QUESTION
    runtime = output_checks.runtime_sentinels(os.environ)
    attempts = attempt_evidence(out, meta) if (case.get("sentinels") or runtime) and meta.get("invocations") \
        else None
    record = output_checks.run_checks(case, mode, body, meta.get("research_log"), status, reasons,
                                      watch_out=line or "", generated_files=graded_files(meta) if gate else None,
                                      attempts=attempts, runtime_sentinels=runtime or None)
    record = masked({"skill": skill, "id": case["id"], "run": run, "stem": stem, **record})
    (out / f"{stem}.checks.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


# --- Classification --------------------------------------------------------------------------

def classify(results: list[dict], checks_results: list[dict], runs: list[int],
             graders: int) -> dict:
    """Classify every expectation and check across one fixture's runs.

    Pure, so it is tested: the old inline loop used every run as its denominator
    and counted only explicit FAILs, so an expectation one grader skipped in one
    run read as intermittent — a pass invented out of a gap. Here a run fails #n
    if any grader failed it, passes only when every grader returned a valid PASS,
    and is otherwise partially graded. Deterministic is FAIL in every valid run
    with none unresolved; intermittent needs a fully graded passing run; anything
    else is unresolved. Harness-invalid runs are left out of every denominator.
    """
    invalid = {}
    for r in results:
        if r.get("harness_invalid"):
            invalid[r.get("run")] = r.get("error", "harness-invalid")
    for c in checks_results:
        if c.get("status") == "harness-invalid":
            invalid[c.get("run")] = "; ".join(c.get("info") or []) or "harness-invalid"
    valid = [r for r in runs if r not in invalid]

    per_run: dict[str, dict[int, str]] = {}          # key -> run -> fail | pass | partial
    why: dict[str, str] = {}
    kinds: dict[str, str] = {}
    keys: set = set()
    for r in results:
        if r.get("run") in valid:
            keys |= {n for n in r.get("expected") or [v.get("n") for v in r.get("verdicts", [])]
                     if isinstance(n, int)}
    for n in sorted(keys):
        key = f"#{n}"
        kinds[key] = "grader"
        for run in valid:
            got = []
            for g in range(1, graders + 1):
                rec = next((x for x in results if x.get("run") == run and x.get("grader") == g), None)
                v = next((v for v in (rec or {}).get("verdicts", []) if v.get("n") == n), None)
                got.append(v.get("verdict") if v and v.get("verdict") in ("PASS", "FAIL") else None)
                if v and v.get("verdict") == "FAIL" and key not in why:
                    why[key] = " ".join(str(v.get("why", "")).split())
            per_run.setdefault(key, {})[run] = (
                "fail" if "FAIL" in got else "pass" if all(x == "PASS" for x in got) else "partial")

    check_keys: dict[str, dict] = {}
    for c in checks_results:
        if c.get("run") not in valid:
            continue
        for item in c.get("checks", []):
            if item.get("kind") == "report":   # never a defect (output_checks.REPORTED)
                continue
            key = f"chk:{item['check']}:{item['target']}"
            check_keys.setdefault(key, item)
    for key, sample in check_keys.items():
        kinds[key] = sample.get("kind", "judgement")
        check_name = key.split(":")[1]
        for run in valid:
            rec = next((c for c in checks_results if c.get("run") == run), None)
            items = [i for i in (rec or {}).get("checks", [])
                     if f"chk:{i['check']}:{i['target']}" == key]
            if any(i["verdict"] == "FAIL" for i in items):
                state = "fail"
                why.setdefault(key, next(i["why"] for i in items if i["verdict"] == "FAIL"))
            elif items:
                state = "pass"
            elif rec is None or check_name in (rec.get("unchecked") or []):
                state = "partial"           # the check could not run here
            else:
                state = "pass"              # it did not apply in this run
            per_run.setdefault(key, {})[run] = state

    items = []
    for key, states in per_run.items():
        fails = [r for r, s in states.items() if s == "fail"]
        passes = [r for r, s in states.items() if s == "pass"]
        partial = [r for r, s in states.items() if s == "partial"]
        if not fails and not partial:
            continue
        if fails and not passes and not partial:
            kind = "deterministic"
        elif fails and passes:
            kind = "intermittent"
        else:
            kind = f"unresolved ({len(partial)} partially graded)"
        items.append({"key": key, "kind": kind, "source": kinds.get(key),
                      "fails": len(fails), "runs": len(valid), "partial": len(partial),
                      "why": why.get(key, "")})
    items.sort(key=lambda i: (not i["key"].startswith("#"),
                              int(i["key"][1:]) if i["key"].startswith("#") else 0, i["key"]))
    return {"items": items, "valid_runs": valid, "invalid_runs": invalid}


# --- Recovery and reports: grade gaps, killed runs, passes, hidden reaches, planted events --------------

def read_json_file(path: Path):
    """A JSON file's value, or None when it is missing or cannot be read."""
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


GAP_KINDS = ("partial", "absent", "limit", "error")


def grade_gaps(out: Path, graders: int) -> list[dict]:
    """Every expected grader of every finished run in `out` whose grade file is missing or misses an
    expected verdict. Pure over saved files. A finished run holds its response and a meta whose harness
    status is ok (a harness-invalid run is never graded). Each entry: {"stem", "turn" (None for a fixture
    run), "grader", "grade_file", "kind", "expected", "missing", "invalid", "error"}, `kind` being
    `absent` (no grade file: a restart), `limit` (an error-only file whose error is the usage-limit
    message), `error` (an error-only file for another reason) or `partial` (verdicts that miss an expected
    number: missing, incomplete or conflicted). The fix round's gap check listed only files with no
    verdicts, so one missing verdict went unflagged; a partial file is listed here."""
    gaps = []
    for meta_path in sorted(out.glob("*.meta.json")):
        stem = meta_path.name[:-len(".meta.json")]
        meta = read_json_file(meta_path)
        if not isinstance(meta, dict) or not (out / f"{stem}.md").exists() or harness_status(meta)[0] != "ok":
            continue
        for g in range(1, graders + 1):
            entry = grade_gap(out, stem, None, g, f"{stem}.grade-{g}.json")
            if entry:
                gaps.append(entry)
    return gaps


def grade_gap(out: Path, stem: str, turn: int | None, grader: int, name: str) -> dict | None:
    """One expected grade file's gap (grade_gaps), or None when it holds every expected verdict or belongs to a
    harness-invalid run. Shared with the transcript driver, whose `turn` is the turn graded."""
    entry = {"stem": stem, "turn": turn, "grader": grader, "grade_file": name, "kind": None,
             "expected": [], "missing": [], "invalid": [], "error": None}
    data = read_json_file(out / name) if (out / name).exists() else None
    if not (out / name).exists():
        entry["kind"] = "absent"
    elif not isinstance(data, dict):
        entry.update(kind="error", error="the grade file cannot be read")
    elif data.get("harness_invalid"):
        return None
    elif not data.get("verdicts"):
        error = str(data.get("error") or "no verdicts")
        entry.update(kind="limit" if LIMIT.search(error) else "error", error=error,
                     expected=list(data.get("expected") or []))
    else:
        missing = sorted({n for n in [*(data.get("incomplete") or []), *(data.get("missing") or [])]
                          if isinstance(n, int)})
        if not missing:
            return None
        entry.update(kind="partial", expected=list(data.get("expected") or []), missing=missing,
                     invalid=list(data.get("invalid") or []), error=data.get("error"),
                     regraded=list(data.get("regraded") or []))
    return entry


def write_grade_gaps(out: Path, gaps: list[dict], graders: int, pass_id: str | None) -> Path:
    """`<out>/grade-gaps.json`, rewritten each pass: derived from the grade files, never a grade, and the
    form the recovery step (`--grade-gaps`) reads."""
    path = out / "grade-gaps.json"
    write_json(path, {"written": utc_now(), "pass_id": pass_id, "graders": graders, "files": gaps,
                      "stems": {kind: sorted({g["stem"] for g in gaps if g["kind"] == kind}) for kind in GAP_KINDS}})
    return path


def gap_lines(gaps: list[dict], path: Path) -> list[str]:
    """The summary's "partly graded" block, printed before the totals line."""
    if not gaps:
        return []
    lines = ["--- partly graded ---"]
    for g in gaps:
        turn = f" turn {g['turn']}" if g.get("turn") else ""
        head = f"  {g['stem']}{turn} grader {g['grader']}: "
        if g["kind"] == "partial":
            numbers = ", ".join(f"#{n}" for n in g["missing"])
            lines.append(head + f"no verdict for {numbers} of {len(g['expected'])}"
                         + (" (re-asked once)" if g.get("regraded") else ""))
        elif g["kind"] == "absent":
            lines.append(head + "no grade file (a restart?)")
        elif g["kind"] == "limit":
            lines.append(head + f"cut by the usage limit ({str(g['error'])[:100]})")
        else:
            lines.append(head + f"no verdicts ({str(g['error'])[:100]})")
    count = {kind: sum(1 for g in gaps if g["kind"] == kind) for kind in GAP_KINDS}
    lines.append(f"{count['partial']} grade file(s) miss an expected verdict, {count['absent']} missing, "
                 f"{count['limit']} cut by the usage limit and {count['error']} without verdicts: "
                 f"{path} lists them for recovery")
    return lines


def move_grade_gaps(out: Path, gaps: list[dict], accept_partial: bool, tag: str) -> tuple[list[str], Path | None]:
    """The tested missing-grader path's move (`--grade-gaps --move`): a grade file cut by the usage limit
    goes to killed/; a partial one goes to partial/ only with `accept_partial`, the owner's accepted
    recovery; an error-only file is left for the owner; an absent grader needs no move. Nothing is
    overwritten (unclaimed). Writes killed/regrade-<UTC>.txt listing the runs to grade with `--stems …
    --skip-execute`, which fills each grader with no file and keeps the others; return (moved, list)."""
    moved, stems = [], []
    for g in gaps:
        folder = {"limit": "killed", "partial": "partial" if accept_partial else None}.get(g["kind"])
        if folder:
            dest = unclaimed(out / folder / g["grade_file"], tag)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(out / g["grade_file"]), str(dest))
            moved.append(dest.relative_to(out).as_posix())
        if folder or g["kind"] == "absent":
            stems.append(g["stem"])
    if not stems:
        return moved, None
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    listing = unclaimed(out / "killed" / f"regrade-{stamp}.txt", tag)
    listing.parent.mkdir(parents=True, exist_ok=True)
    listing.write_text("".join(f"{s}\n" for s in dict.fromkeys(stems)))
    return moved, listing


def sentinel_report(out: Path) -> dict:
    """The planted-event report over every `sentinel_scan` in `out/*.checks.json` and `out/killed/`, and in
    a transcript scenario's `<stem>.scan.json` (run_transcripts.py), whose status is ok only for a scored
    scenario. Per kind: the eligible sessions (a valid run whose scan was scored), the events per surface in
    them and the sessions holding one; apart, the events seen in set-aside or killed sessions (a leak in a
    session later set aside still happened, Q10); and the unscored sessions."""
    report = {"kinds": {}, "apart": [], "unscored": [], "scans": 0}
    for folder, killed in ((out, False), (out / "killed", True)):
        for path in sorted([*folder.glob("*.checks.json"), *folder.glob("*.scan.json")]):
            data = read_json_file(path)
            scan = data.get("sentinel_scan") if isinstance(data, dict) else None
            if not isinstance(scan, dict):
                continue
            report["scans"] += 1
            stem = data.get("stem") or re.sub(r"\.(?:checks|scan)\.json$", "", path.name)
            scored = scan.get("status") == "scored"
            eligible = scored and not killed and data.get("status") != "harness-invalid"
            if not scored:
                report["unscored"].append(stem)
            hits = [h for a in (scan.get("attempts") or {}).values() if isinstance(a, dict)
                    for h in a.get("hits") or [] if isinstance(h, dict)]
            for declared in scan.get("sentinels") or []:
                kind = declared.get("kind")
                entry = report["kinds"].setdefault(kind, {"eligible": 0, "events": {}, "sessions": []})
                mine = [h for h in hits if h.get("kind") == kind]
                if eligible:
                    entry["eligible"] += 1
                    for h in mine:
                        entry["events"][h.get("surface")] = entry["events"].get(h.get("surface"), 0) + 1
                    if mine:
                        entry["sessions"].append(stem)
            if hits and not eligible:
                kinds: dict[str, int] = {}
                for h in hits:
                    kinds[h.get("kind")] = kinds.get(h.get("kind"), 0) + 1
                report["apart"].append({"stem": stem, "where": "killed" if killed else "set aside",
                                        "events": kinds})
    return report


def sentinel_lines(report: dict) -> list[str]:
    if not report["scans"]:
        return []
    parts = [f"{kind} {sum(e['events'].values())} in {e['eligible']} eligible session(s)"
             + (f" ({', '.join(f'{s} {n}' for s, n in sorted(e['events'].items()))})" if e["events"] else "")
             for kind, e in sorted(report["kinds"].items())]
    lines = ["planted events: " + ("; ".join(parts) or "no sentinel declared")]
    for a in report["apart"]:
        lines.append(f"  in a {a['where']} session, counted apart: {a['stem']}: "
                     + ", ".join(f"{k} {n}" for k, n in sorted(a["events"].items())))
    if report["unscored"]:
        lines.append(f"  unscored (evidence missing): {', '.join(report['unscored'])}")
    return lines


def installed_names(inv: dict) -> dict:
    """The names a front-door invocation installed: recorded since invocations kept them, else rebuilt from
    its room's run id, as install_tuesday names each skill `<skill>-<run id>`."""
    if isinstance(inv.get("names"), dict):
        return inv["names"]
    run_id = Path(inv.get("room") or "").name[-8:]
    return {**{m: f"{m}-{run_id}" for m in run_routing.SKILLS}, run_routing.HUB: f"{run_routing.HUB}-{run_id}"}


# A run through the front door, as its meta spells it: `frontdoor` before the code-name rename (E25).
FRONT_DOOR_VIAS = ("tuesday", "frontdoor")


def hidden_reaches(out: Path) -> dict:
    """E16: the hidden-module reaches in every invocation of every front-door run in `out` and
    `out/killed/`, first, nudged, timed out, declined, void and killed alike, before any run is left out
    as invalid. Each invocation's saved stream is read whole by hidden_reach_labels; one with no saved
    stream counts its recorded `hidden_reached`, or is listed unread. Returns {"attempts": n, "reaches":
    [(stem, invocation index, label)], "unread": [(stem, index)]}."""
    attempts, reaches, unread = 0, [], []
    for folder in (out, out / "killed"):
        for meta_path in sorted(folder.glob("*.meta.json")):
            meta = read_json_file(meta_path)
            if not isinstance(meta, dict) or meta.get("via") not in FRONT_DOOR_VIAS:
                continue
            stem = meta.get("stem") or meta_path.name[:-len(".meta.json")]
            for i, inv in enumerate(meta.get("invocations") or []):
                attempts += 1
                stream = saved_stream(out, inv)
                if stream is not None:
                    labels = hidden_reach_labels(read_events(stream), installed_names(inv),
                                                 Path(inv.get("room") or "."))
                elif isinstance(inv.get("hidden_reached"), list):
                    labels = inv["hidden_reached"]
                else:
                    unread.append((stem, i))
                    continue
                reaches += [(stem, i, label) for label in labels]
    return {"attempts": attempts, "reaches": reaches, "unread": unread}


def hidden_lines(found: dict) -> list[str]:
    line = (f"hidden-module reaches: {len(found['reaches'])} across {found['attempts']} Tuesday attempt(s) "
            f"(initial, nudged and incomplete included)")
    lines = [line] + [f"  {stem} attempt {i + 1}: {label}" for stem, i, label in found["reaches"]]
    if found["unread"]:
        lines.append(f"  no saved stream to read: {', '.join(f'{s} attempt {i + 1}' for s, i in found['unread'])}")
    return lines


SURVEY_KINDS = ("usage_limit", "restart", "timeout", "declined", "invalid", "unscored", "never_started")


def inflight_records(out: Path) -> dict[str, list[tuple[Path, dict]]]:
    """The in-flight records a runner left (inflight_marker), by stem."""
    found: dict[str, list[tuple[Path, dict]]] = {}
    for path in sorted((out / "inflight").glob("*.json")):
        record = read_json_file(path)
        if isinstance(record, dict) and record.get("stem"):
            found.setdefault(record["stem"], []).append((path, record))
    return found


def killed_survey(out: Path, expected: list[str]) -> dict:
    """Classify each stem of a fixture folder that is not a finished run, per stem, never merged into
    one class: `usage_limit` (an attempt cut by the usage-limit message: `limit_hit`, or, for a meta whose
    invocations predate `limit_hit`, its error matching LIMIT) and `restart` (no meta, and the runner's
    in-flight record left on disk: a restart or
    the owner's guard ended it mid-attempt) are killed, recovered under their own stems; `timeout`,
    `declined`, `invalid` (a room not its mode, a skill that never fired) and `unscored` (the sentinel
    scan's evidence missing) are set aside, count toward the 10% limit and are never rerun;
    `never_started` lists the `expected` stems with neither a meta nor an in-flight record. Precedence:
    killed, then set aside, then unscored. `stale` lists in-flight records of runs whose meta was written."""
    found: dict[str, list] = {kind: [] for kind in SURVEY_KINDS}
    records = inflight_records(out)
    metas = set()
    for meta_path in sorted(out.glob("*.meta.json")):
        stem = meta_path.name[:-len(".meta.json")]
        metas.add(stem)
        meta = read_json_file(meta_path)
        if not isinstance(meta, dict):
            found["invalid"].append(stem)
            continue
        status, reasons = harness_status(meta)
        if status == "ok":
            continue
        invocations = meta.get("invocations") or []
        # An invocation records `limit_hit` (stream_limit: the message where the CLI writes it); only a meta
        # saved before invocations recorded it is read by its error text, as the fix round read it.
        recorded = any("limit_hit" in inv for inv in invocations)
        if any(inv.get("limit_hit") for inv in invocations) or \
                (not recorded and LIMIT.search(str(meta.get("error") or ""))):
            found["usage_limit"].append(stem)
        elif meta.get("outcome") in ("timeout", "declined"):
            found[meta["outcome"]].append(stem)
        elif reasons and all(r.startswith("sentinel scan:") for r in reasons if r):
            found["unscored"].append(stem)
        else:
            found["invalid"].append(stem)
    found["restart"] = sorted(stem for stem in records if stem not in metas)
    found["stale"] = sorted(stem for stem in records if stem in metas)
    found["never_started"] = [stem for stem in expected if stem not in metas and stem not in records]
    return found


def recover_restart(out: Path, stem: str, records: list[tuple[Path, dict]], job: tuple | None,
                    tag: str) -> list[str]:
    """Keep what a run killed mid-attempt left, under killed/: snapshot each in-flight attempt's room and
    scratchpad (`partial_evidence`: as far as the run got), move its stream to killed/streams/ as a
    partial, and write the run's meta and checks there, the meta harness-invalid and outcome `killed`,
    the checks holding the sentinel scan over every attempt (a leak in a killed session is counted
    apart, never lost). `job` is the run's (skill, case, mode), when this pass's cases name it. Nothing is
    overwritten (unclaimed). Return the paths written."""
    skill, case, mode = job if job else (None, None, None)
    killed = out / "killed"
    (killed / "streams").mkdir(parents=True, exist_ok=True)
    invocations, written = [], []
    first = records[0][1]
    for _, record in records:
        inv = dict(record.get("invocation") or {})
        inv.pop("inflight", None)
        if record.get("state") != "ended":
            room = Path(inv.get("room") or "")
            base = Path(record.get("stream") or f"streams/{room.name}.inflight.jsonl").name[:-len(".inflight.jsonl")]
            source = out / (record.get("stream") or "")
            dest = unclaimed(killed / "streams" / f"{base}.partial.jsonl", tag)
            if source.is_file():
                shutil.move(str(source), str(dest))
            else:
                dest.write_text("")
            text = read_back(dest)
            parsed = parse_stream(text.splitlines(), inv.get("installed") or "")
            skill_dir = Path(inv.get("skill_dir") or room / "none")
            inv.update(outcome="killed", error="the runner ended mid-attempt (a restart or the owner's guard)",
                       fire=parsed["fire"], init=parsed["init"], result=parsed["result"],
                       tool_calls=parsed["tool_calls"], research_log=None,
                       stream=dest.relative_to(out).as_posix(), stream_sha256=file_sha256(dest),
                       init_sha256=save_init(out, parsed.get("init_event")),
                       session_id=(parsed.get("init_event") or {}).get("session_id"),
                       limit_hit=stream_limit(text, "") is not None,
                       files=snapshot_files(room, skill_dir, unclaimed(out / "files" / base, tag), out)
                       if room.is_dir() else None,
                       partial_evidence=True, pass_id=record.get("pass_id"))
            if inv.get("via") == "tuesday":
                inv["hidden_reached"] = hidden_reach_labels(text.splitlines(), installed_names(inv), room)
        invocations.append(inv)
    match = STEM.match(stem)
    reason = "killed: the runner ended mid-run (a restart or the owner's guard)"
    meta = {"skill": skill, "id": case.get("id") if case else None,
            "run": int(match.group(2)) if match else None, "stem": stem,
            "mode": mode, "via": (invocations[0] if invocations else {}).get("via"),
            "layout": (invocations[0] if invocations else {}).get("layout"), "pass_id": first.get("pass_id"),
            "invocations": invocations, "outcome": "killed", "error": reason, "graded_invocation": None,
            "research_log": None, "harness": {"status": "harness-invalid", "reasons": [reason]}}
    meta_path = unclaimed(killed / f"{stem}.meta.json", tag)
    write_json(meta_path, masked(meta))
    written.append(meta_path.relative_to(out).as_posix())
    if case is not None:
        runtime = output_checks.runtime_sentinels(os.environ)
        attempts = attempt_evidence(out, meta) if case.get("sentinels") or runtime else None
        record = output_checks.run_checks(case, mode or "denied", "", None, "harness-invalid", [reason],
                                          attempts=attempts, runtime_sentinels=runtime or None)
        checks_path = meta_path.with_name(meta_path.name[:-len(".meta.json")] + ".checks.json")
        write_json(checks_path, masked({"skill": meta["skill"], "id": meta["id"], "run": meta["run"], "stem": stem,
                                        **record}))
        written.append(checks_path.relative_to(out).as_posix())
    for path, _ in records:
        path.unlink(missing_ok=True)
    return written


def move_killed(out: Path, survey: dict, jobs: dict[str, tuple], tag: str,
                left: list[str] | None = None) -> tuple[list[str], Path | None]:
    """`--killed --move`: the usage-limit stems' files go to killed/ (rooms, streams, snapshots and
    research stay where they are, named by room); each restart stem's in-flight attempts are kept there
    (recover_restart); stale in-flight records are removed. Nothing is overwritten. A restart stem this
    pass's cases do not name (not in `jobs`) is left as it is, its in-flight records in place, and appended
    to `left`: without its case its sentinel scan could not be written, and a leak in that killed session
    would be lost; a pass naming its case recovers it. Writes killed/rerun-<UTC>.txt listing the killed
    and never-started stems, for `--stems`."""
    killed = out / "killed"
    killed.mkdir(parents=True, exist_ok=True)
    moved = []
    for stem in survey["usage_limit"]:
        for name in stem_files(out, stem):
            dest = unclaimed(killed / name, tag)
            shutil.move(str(out / name), str(dest))
            moved.append(dest.relative_to(out).as_posix())
    records = inflight_records(out)
    recovered = []
    for stem in survey["restart"]:
        if stem not in jobs:
            if left is not None:
                left.append(stem)
            continue
        moved += recover_restart(out, stem, records.get(stem, []), jobs[stem], tag)
        recovered.append(stem)
    for stem in survey.get("stale", []):
        for path, _ in records.get(stem, []):
            path.unlink(missing_ok=True)
    rerun = [*survey["usage_limit"], *recovered, *survey["never_started"]]
    if not rerun:
        return moved, None
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    listing = unclaimed(killed / f"rerun-{stamp}.txt", tag)
    listing.write_text("".join(f"{s}\n" for s in rerun))
    return moved, listing


# Passes: one record per invocation of the runner that runs or grades anything, under `<out>/passes/`.
# Every meta and grade carries its `pass_id`, so each grade names the invocation that made it.
INVENTORY_GLOBS = ("evals/*.py", "ci/ledger_rules.py", "ci/sync.py", "ci/package.py")
# The settings this runner records for a pass, every one of which every pass into one --out must share: a
# pass that differs is not the same measurement. pass_problems compares whatever settings a record holds, so
# a driver that records more (the transcript driver's scripts sha256) has those held too.
PASS_SETTINGS = ("model", "grader_model", "via", "layout", "graders", "timeout", "retry_runs", "cases_sha256")


_PASS_IDS: set[str] = set()


def new_pass_id() -> str:
    """`<UTC time>-<pid>`, with a count after it for a second id the same process makes in the same second."""
    stamp = f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{os.getpid()}"
    found, n = stamp, 2
    while found in _PASS_IDS:
        found, n = f"{stamp}-{n}", n + 1
    _PASS_IDS.add(found)
    return found


def inventory(repo: Path = REPO) -> dict[str, str]:
    """sha256 of the harness's own code: every evals/*.py, ci/ledger_rules.py, ci/sync.py, ci/package.py."""
    files = sorted({p for pattern in INVENTORY_GLOBS for p in repo.glob(pattern) if p.is_file()})
    return {p.relative_to(repo).as_posix(): file_sha256(p) for p in files}


def payload_digests(repo: Path = REPO) -> dict[str, str]:
    """The payload a pass installs: the hub's two digests (sync.digests) and each module's tree as
    install_one copies it (`module:<skill>`)."""
    digests = dict(run_routing.sync.digests(repo / "skills" / run_routing.HUB))
    for skill in run_routing.SKILLS:
        base = repo / "skills" / skill
        files = [(p.relative_to(base).as_posix(), p) for p in base.rglob("*")
                 if p.is_file() and not any(fnmatch.fnmatch(part, pattern) for part in p.relative_to(base).parts
                                            for pattern in run_routing.INSTALL_IGNORED)]
        digests[f"module:{skill}"] = run_routing.files_sha256(files)
    return digests


def git_state(repo: Path = REPO) -> dict:
    """The checkout's HEAD and how many files differ from it, best effort (None without git). Read-only:
    GIT_OPTIONAL_LOCKS=0 keeps `git status` from writing the index."""
    env = {**child_env(), "GIT_OPTIONAL_LOCKS": "0"}
    try:
        head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True,
                              timeout=30, env=env)
        status = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True,
                                text=True, timeout=60, env=env)
    except (OSError, subprocess.SubprocessError):
        return {"head": None, "dirty": None}
    return {"head": (head.stdout.strip() or None) if head.returncode == 0 else None,
            "dirty": len(status.stdout.splitlines()) if status.returncode == 0 else None}


def pass_record(argv: list[str], settings: dict, pass_id: str | None = None) -> dict:
    """A pass's record: who ran what where, the harness's code (inventory), the payload (digests), the
    settings every pass into the folder must share (PASS_SETTINGS), and when it started."""
    return {"pass_id": pass_id or new_pass_id(), "argv": list(argv), "hostname": socket.gethostname(),
            "uid": os.getuid() if hasattr(os, "getuid") else None, "cli_version": cli_version(),
            "python": sys.version.split()[0], "git": git_state(), "inventory": inventory(),
            "digests": payload_digests(), "settings": dict(settings), "started": utc_now(), "finished": None}


def read_passes(out: Path) -> list[dict]:
    return [p for p in (read_json_file(path) for path in sorted((out / "passes").glob("*.json")))
            if isinstance(p, dict)]


def differences(a: dict, b: dict) -> list[str]:
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


def pass_problems(passes: list[dict], expect: dict | None = None) -> tuple[list[str], list[str]]:
    """(refusals, notes) for the passes of one --out, the last being the one about to start. Passes that
    differ in the harness's code, the payload or a recorded setting (PASS_SETTINGS: models, via, layout,
    graders, timeout, retry runs, the case file's sha256; a driver's own, such as a scripts sha256) are not
    one measurement: refused. A different
    CLI version is recorded, never refused (E8), and noted "preflight required" unless `expect` names a
    preflight record for that version (its `preflight` list). `expect`, a frozen pass record or any JSON
    holding `digests`, `inventory` and `settings`, refuses the new pass on any difference from it, and
    on retry runs other than 0: a retry pass adds runs to fixed cells."""
    refusals, notes = [], []
    if not passes:
        return refusals, notes
    current = passes[-1]
    for earlier in passes[:-1]:
        for key, label in (("inventory", "the harness's code"), ("digests", "the installed payload")):
            changed = differences(earlier.get(key) or {}, current.get(key) or {})
            if changed:
                refusals.append(f"pass {current.get('pass_id')} differs from pass {earlier.get('pass_id')} in "
                                f"{label}: {', '.join(changed[:6])}{' …' if len(changed) > 6 else ''}")
        changed = differences(earlier.get("settings") or {}, current.get("settings") or {})
        if changed:
            refusals.append(f"pass {current.get('pass_id')} differs from pass {earlier.get('pass_id')} in "
                            + ", ".join(f"{k} ({(earlier.get('settings') or {}).get(k)!r} then "
                                        f"{(current.get('settings') or {}).get(k)!r})" for k in changed))
    preflight = (expect or {}).get("preflight") or []
    preflight = [preflight] if isinstance(preflight, str) else list(preflight)
    versions = list(dict.fromkeys(p.get("cli_version") for p in passes))
    reference = (expect or {}).get("cli_version") or (versions[0] if versions else None)
    if current.get("cli_version") != reference and reference is not None:
        notes.append(f"the CLI changed: {reference} then {current.get('cli_version')} (recorded, never refused)"
                     + ("" if current.get("cli_version") in preflight else "; preflight required"))
    if expect is not None:
        for key, label in (("digests", "the installed payload"), ("inventory", "the harness's code")):
            want = expect.get(key)
            if isinstance(want, dict):
                changed = differences(want, current.get(key) or {}) if key == "inventory" else \
                    [k for k, v in want.items() if (current.get(key) or {}).get(k) != v]
                if changed:
                    refusals.append(f"--expect: {label} differs from the frozen record: {', '.join(changed[:6])}")
        want = expect.get("settings")
        if isinstance(want, dict):
            changed = [k for k, v in want.items() if (current.get("settings") or {}).get(k) != v]
            if changed:
                refusals.append("--expect: " + ", ".join(f"{k} is {(current.get('settings') or {}).get(k)!r}, "
                                                        f"frozen {want[k]!r}" for k in changed))
        if (current.get("settings") or {}).get("retry_runs") != 0:
            refusals.append("--expect: retry runs must be 0 (a retry pass adds or replaces runs in fixed cells)")
    return refusals, notes


# --- Driving it ---------------------------------------------------------------------------

def cases_for(skill: str, only: list[int], cases_file: str | None = None) -> list[dict]:
    path = Path(cases_file) if cases_file else REPO / "skills" / skill / "evals" / "evals.json"
    cases = load_cases(path)
    return [c for c in cases if not only or c["id"] in only]


def copy_for_regrade(src: Path, out: Path) -> int:
    """Copy a saved set's responses and meta into a fresh directory to grade there.

    Regrading in place would overwrite the grades the ledger and the diagnosis
    cite. Checks are recomputed, never copied: they are cheap, and a copied one
    would describe the old checker.
    """
    copied = 0
    for path in sorted(src.glob("*.md")) + sorted(src.glob("*.meta.json")):
        shutil.copy2(path, out / path.name)
        copied += 1
    return copied


STEM = re.compile(r"^(.+)\.run(\d+)$")


def listed_runs(path: Path, work: list[tuple]) -> list[tuple]:
    """The runs a `--stems` file lists, one stem a line (blank lines and lines starting with `#`
    ignored), as (skill, case, mode, run) in the order listed, each under its own run number.
    Raises ValueError for a stem that names no fixture and room of this pass's `work`, a stem
    listed twice, and a file that lists none."""
    prefixes = {stem_for(s, c, m, 0)[:-len(".run0")]: (s, c, m) for s, c, m in work}
    runs, seen = [], set()
    for line in path.read_text().splitlines():
        stem = line.strip()
        if not stem or stem.startswith("#"):
            continue
        match = STEM.match(stem)
        if not match or match.group(1) not in prefixes:
            raise ValueError(f"--stems: {stem!r} names no fixture and room this pass runs "
                             f"(a stem is <skill>-<id>.run<n>, or <skill>-<id>.<mode>.run<n> for a fixture "
                             f"with more than the denied room)")
        if stem in seen:
            raise ValueError(f"--stems: {stem!r} is listed twice")
        seen.add(stem)
        skill, case, mode = prefixes[match.group(1)]
        runs.append((skill, case, mode, int(match.group(2))))
    if not runs:
        raise ValueError(f"--stems: {path} lists no run")
    return runs


def stem_files(out: Path, stem: str) -> list[str]:
    """The files of one run in a set's folder: its response, meta, checks and grade files."""
    return sorted(p.name for p in out.glob(f"{stem}.*") if p.is_file())


def cases_file(skill: str, cases: str | None) -> Path:
    return Path(cases) if cases else REPO / "skills" / skill / "evals" / "evals.json"


def grade_gaps_pass(out: Path, graders: int, move: bool, accept_partial: bool) -> int:
    """`--grade-gaps [--move [--accept-partial]]`: print the folder's grade gaps and rewrite grade-gaps.json;
    with --move, move them for the missing-grader path (move_grade_gaps)."""
    gaps = grade_gaps(out, graders)
    path = write_grade_gaps(out, gaps, graders, None)
    for line in gap_lines(gaps, path) or [f"no grade gaps in {out} for {graders} grader(s)"]:
        print(line)
    if move and gaps:
        moved, listing = move_grade_gaps(out, gaps, accept_partial, new_pass_id())
        for name in moved:
            print(f"  moved {name}")
        kept = [g for g in gaps if g["kind"] == "error" or (g["kind"] == "partial" and not accept_partial)]
        for g in kept:
            print(f"  left for the owner: {g['grade_file']} ({g['kind']})")
        if listing:
            print(f"runs to grade with --stems {listing} --skip-execute (each grader with no file is filled; "
                  f"the others are kept)")
    return 0


def killed_pass(out: Path, work: list[tuple], expected: list[str], move: bool) -> int:
    """`--killed [--move]`: classify the folder's unfinished stems (killed_survey); with --move, keep the
    killed ones under killed/ and list them with the never-started ones for --stems (move_killed)."""
    survey = killed_survey(out, expected)
    labels = {"usage_limit": "killed by the usage limit", "restart": "killed mid-run (a restart or the guard)",
              "timeout": "timed out (set aside)", "declined": "declined (set aside)",
              "invalid": "harness-invalid (set aside)", "unscored": "sentinel scan unscored (set aside)",
              "never_started": "never started"}
    for kind in SURVEY_KINDS:
        for stem in survey[kind]:
            print(f"  {labels[kind]}: {stem}")
    print(f"{len(survey['usage_limit']) + len(survey['restart'])} killed, {len(survey['never_started'])} never "
          f"started, {sum(len(survey[k]) for k in ('timeout', 'declined', 'invalid', 'unscored'))} set aside "
          f"(counted toward the 10% limit, never rerun)")
    if move:
        prefixes = {stem_for(s, c, m, 0)[:-len(".run0")]: (s, c, m) for s, c, m in work}
        jobs = {stem: prefixes[match.group(1)] for stem in survey["restart"]
                if (match := STEM.match(stem)) and match.group(1) in prefixes}
        left: list[str] = []
        moved, listing = move_killed(out, survey, jobs, new_pass_id(), left)
        for name in moved:
            print(f"  kept {name}")
        for stem in left:
            print(f"  left in place: {stem} — this pass's cases do not name it, so its in-flight records stay "
                  f"for a --killed --move pass with its --skill, --eval and --cases")
        if listing:
            print(f"runs to rerun with --stems {listing}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", action="append", choices=SKILLS, default=[])
    ap.add_argument("--eval", type=int, action="append", default=[])
    ap.add_argument("--out", required=True, help="directory for responses and grades")
    ap.add_argument("--graders", type=int, default=2)
    ap.add_argument("--runs", type=int, default=1, help="runs per fixture and mode in the first pass")
    ap.add_argument("--retry-runs", type=int, default=2,
                    help="extra runs for any fixture that failed something or had a "
                         "harness-invalid run (which also gets one replacement); 0 disables")
    ap.add_argument("--model", default=None, help="pin the rooms' model (recorded either way)")
    ap.add_argument("--grader-model", default=None, help="pin the graders' model; defaults to --model")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--skip-execute", action="store_true",
                    help="grade saved runs in an --out that holds no grades yet")
    ap.add_argument("--regrade-from", default=None,
                    help="copy a saved set's responses and meta into a fresh --out and grade there")
    ap.add_argument("--no-backfill", action="store_true",
                    help="with --regrade-from: do not reconstruct missing research records")
    ap.add_argument("--expectation", type=int, action="append", default=[],
                    help="grade only this expectation number (repeatable)")
    ap.add_argument("--cases", default=None,
                    help="load cases from this JSON instead of skills/<skill>/evals/evals.json")
    ap.add_argument("--via", choices=VIAS, default="skill",
                    help="skill: each module installed alone (the default); tuesday: the front door "
                         "installed as the plugin ships it, a fire counting only through the hub")
    ap.add_argument("--layout", choices=LAYOUTS, default=None,
                    help="where the skills sit: project, the room's .claude/skills/ (the default with --via "
                         "skill); plugin, a plugin beside the room, as the front door always is — with --via "
                         "skill, the module alone installed exactly as the front door is, the control a "
                         "comparison through Tuesday uses")
    ap.add_argument("--stems", default=None,
                    help="a file listing runs by stem, one a line: run only those, each under its own run "
                         "number, in --out, where none of their files may exist yet; with --skip-execute, grade "
                         "each grader of those that holds a response and no grade file of that grader, the "
                         "others kept. No retry pass follows")
    ap.add_argument("--expect", default=None,
                    help="a frozen pass record (or JSON with digests, inventory and settings): refuse, before "
                         "any call, a pass that differs from it, and any --retry-runs but 0")
    ap.add_argument("--grade-gaps", action="store_true",
                    help="list the folder's finished runs whose grade files are missing or miss a verdict, and "
                         "rewrite grade-gaps.json; with --move, move them for --stems … --skip-execute")
    ap.add_argument("--killed", action="store_true",
                    help="classify the folder's unfinished runs (killed, set aside, never started); with --move, "
                         "keep the killed ones under killed/ and list them for --stems")
    ap.add_argument("--move", action="store_true", help="with --grade-gaps or --killed: move, never overwrite")
    ap.add_argument("--accept-partial", action="store_true",
                    help="with --grade-gaps --move: move a grade file that misses a verdict to partial/, so its "
                         "grader is asked again (the owner's accepted recovery)")
    args = ap.parse_args()
    if args.via == "tuesday" and args.layout == "project":
        ap.error("--via tuesday installs the front door as the plugin it ships as: --layout plugin")

    if args.stems and args.regrade_from:
        ap.error("--stems re-runs or grades named runs in place, in --out; it does not combine with --regrade-from")
    if args.grade_gaps and args.killed:
        ap.error("--grade-gaps and --killed are separate recovery steps")
    if args.move and not (args.grade_gaps or args.killed):
        ap.error("--move goes with --grade-gaps or --killed")
    if args.accept_partial and not (args.grade_gaps and args.move):
        ap.error("--accept-partial goes with --grade-gaps --move")
    if args.cases and len(args.skill) != 1:
        ap.error("--cases needs exactly one --skill")

    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if args.grade_gaps:
        return grade_gaps_pass(out, args.graders, args.move, args.accept_partial)
    grader_model = args.grader_model or args.model
    skip_execute = args.skip_execute or bool(args.regrade_from)
    skills = args.skill or SKILLS
    work = [(s, c, m) for s in skills for c in cases_for(s, args.eval, args.cases)
            for m in modes_of(c)]
    listed = None
    if args.stems:
        try:
            listed = listed_runs(Path(args.stems), work)
        except (OSError, ValueError) as exc:
            ap.error(str(exc))
    if args.killed:
        expected = [stem_for(s, c, m, r) for s, c, m, r in listed] if listed is not None else \
            [stem_for(s, c, m, r) for s, c, m in work for r in range(args.runs)]
        return killed_pass(out, work, expected, args.move)
    if args.regrade_from:
        src = Path(args.regrade_from).resolve()
        if src == out:
            ap.error("--regrade-from must name a different directory from --out: never regrade in place")
        if any(out.glob("*.md")) or any(out.glob("*.grade-*.json")):
            ap.error(f"{out} is not fresh: --regrade-from copies into an empty --out")
    elif skip_execute and not args.stems and any(out.glob("*.grade-*.json")):
        ap.error(f"{out} already holds grade files; regrade into a fresh directory with "
                 f"--regrade-from {out} --out <new dir>")
    if listed is not None and not skip_execute:
        # Nothing is overwritten: a run is re-run only where the folder holds none of its files
        # (a killed run's files move to killed/ first, evals/README.md "Regrading a saved set").
        held = {stem: files for s, c, m, r in listed if (files := stem_files(out, stem := stem_for(s, c, m, r)))}
        if held:
            ap.error("--stems runs a listed run only where --out holds none of its files: "
                     + "; ".join(f"{stem} holds {', '.join(files)}" for stem, files in held.items()))
    expect = None
    if args.expect:
        expect = read_json_file(Path(args.expect))
        if not isinstance(expect, dict):
            ap.error(f"--expect: {args.expect} is not a JSON object")
        if args.retry_runs != 0:
            ap.error("--expect freezes a measurement, and a retry pass adds or replaces runs in its fixed cells: "
                     "--retry-runs 0")

    # One record per pass, written only once it is accepted: a pass that is not the same measurement as the
    # folder's earlier passes (or as --expect) is refused before any call, and leaves nothing behind.
    settings = {"model": args.model, "grader_model": grader_model, "via": args.via,
                "layout": args.layout or ("plugin" if args.via == "tuesday" else "project"),
                "graders": args.graders, "timeout": args.timeout, "retry_runs": args.retry_runs,
                "cases_sha256": {s: file_sha256(cases_file(s, args.cases)) for s in skills}}
    record = pass_record(sys.argv, settings)
    refused, notes = pass_problems(read_passes(out) + [record], expect)
    for note in notes:
        print(f"note: {note}")
    if refused:
        for line in refused:
            print(f"refused: {line}")
        print("Refused before any call: passes into one --out must be one measurement.")
        return 3
    pass_id = record["pass_id"]
    write_json(out / "passes" / f"{pass_id}.json", record)
    if args.regrade_from:
        print(f"copied {copy_for_regrade(src, out)} file(s) from {src}")
        if not args.no_backfill:
            import backfill_tools
            backfill_tools.backfill_dir(out)
    results: dict[tuple, list[dict]] = {(s, c["id"], m): [] for s, c, m in work}
    checks: dict[tuple, list[dict]] = {(s, c["id"], m): [] for s, c, m in work}
    runs_done: dict[tuple, list[int]] = {(s, c["id"], m): [] for s, c, m in work}
    all_graders = tuple(range(1, args.graders + 1))

    def pass_over(jobs: list[tuple], label: str) -> None:
        """Execute (unless skipping), check and grade one batch of (skill, case, mode, run[, graders]). A
        job naming its graders is graded by those only, and its other graders' saved files are read, so
        classify sees every grader of the run."""
        if not jobs:
            return
        jobs = [j if len(j) == 5 else (*j, all_graders) for j in jobs]
        if not skip_execute:
            print(f"\n{label}: executing {len(jobs)} fixture run(s)")
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                list(pool.map(lambda j: execute(j[0], j[1], out, j[3], args.timeout,
                                               args.model, j[2], args.via, args.layout, pass_id=pass_id), jobs))
        for skill, case, mode, run, _ in jobs:
            checks[(skill, case["id"], mode)].append(check_run(skill, case, out, run, mode))
        grade_jobs = [(s, c, m, r, g) for s, c, m, r, gs in jobs for g in gs]
        print(f"\n{label}: grading {len(jobs)} response(s), {len(grade_jobs)} grade(s)")
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            graded = list(pool.map(
                lambda j: grade(j[0], j[1], out, j[3], j[4], args.timeout, grader_model,
                                j[2], args.expectation or None, pass_id=pass_id), grade_jobs))
        for record_, (skill, case, mode, _, _) in zip(graded, grade_jobs):
            results[(skill, case["id"], mode)].append(record_)
        for skill, case, mode, run, gs in jobs:
            for g in all_graders:
                kept = None if g in gs else read_json_file(out / f"{stem_for(skill, case, mode, run)}.grade-{g}.json")
                if isinstance(kept, dict):
                    results[(skill, case["id"], mode)].append({**kept, "run": run, "grader": g})
            runs_done[(skill, case["id"], mode)].append(run)

    if listed is not None and skip_execute:
        # Grades are never overwritten: of the listed runs that hold a response, each grader with no grade
        # file is graded, and the others' files are kept and read (the tested missing-grader path).
        jobs = []
        for s, c, m, r in listed:
            stem = stem_for(s, c, m, r)
            missing = tuple(g for g in all_graders if not (out / f"{stem}.grade-{g}.json").exists())
            if not (out / f"{stem}.md").exists():
                print(f"  not graded {stem}: it holds no response")
            elif not missing:
                print(f"  not graded {stem}: it holds every grader's file, which is never overwritten")
            else:
                jobs.append((s, c, m, r, missing))
        pass_over(jobs, "listed runs")
    elif listed is not None:
        # No retry pass: its run numbers follow the listed runs' and could be ones the folder holds.
        pass_over(listed, "listed runs")
    elif skip_execute:
        pass_over([(s, c, m, r) for s, c, m in work for r in runs_on_disk(out, s, c, m)],
                  "saved runs")
    else:
        pass_over([(s, c, m, r) for s, c, m in work for r in range(args.runs)], "first pass")

        # Only fixtures that failed something, or lost a run to the harness, earn
        # more runs. A clean fixture is not evidence of reliability, but it is not
        # a lead either, and spending executions on it buys a number nobody acts on.
        retries = []
        for skill, case, mode in work:
            key = (skill, case["id"], mode)
            if not args.retry_runs:
                continue
            verdict = classify(results[key], checks[key], runs_done[key], args.graders)
            failed = any(i["fails"] for i in verdict["items"])
            # An invalid run is replaced once, not retried: it is a hole in the
            # set, not evidence about the skill.
            extra = (args.retry_runs if failed else 0) + len(verdict["invalid_runs"])
            start = max(runs_done[key], default=-1) + 1
            retries += [(skill, case, mode, start + i) for i in range(extra)]
        if retries:
            print(f"\n{len({(s, c['id'], m) for s, c, m, _ in retries})} fixture(s) failed "
                  f"something or lost a run; re-running to tell a defect from a draw")
        pass_over(retries, "retry pass")

    print("\n--- clean-room results ---")
    totals = {"deterministic": 0, "intermittent": 0, "unresolved": 0, "invalid": 0}
    for skill, case, mode in work:
        key = (skill, case["id"], mode)
        runs = sorted(runs_done[key])
        if not runs:
            continue                    # a saved set need not cover every fixture
        verdict = classify(results[key], checks[key], runs, args.graders)
        total = len([n for n in (args.expectation or range(1, len(case["expectations"]) + 1))
                     if 1 <= n <= len(case["expectations"])])
        print(f"  {skill} eval {case['id']} [{mode}]")
        for run in runs:
            if run in verdict["invalid_runs"]:
                print(f"      run {run}: harness-invalid — {verdict['invalid_runs'][run]}")
                continue
            per_grader = []
            for g in range(1, args.graders + 1):
                got = next((r for r in results[key] if r.get("run") == run and r.get("grader") == g), {})
                if got.get("error") and not got.get("verdicts"):
                    per_grader.append(f"grader {g} errored")
                    continue
                vs = got.get("verdicts", [])
                passed = sum(1 for v in vs if v.get("verdict") == "PASS")
                gaps = f" (incomplete: {', '.join(map(str, got.get('incomplete') or []))})" \
                    if got.get("incomplete") else ""
                per_grader.append(f"grader {g} {passed}/{len(vs)} of {total}{gaps}")
            rec = next((c for c in checks[key] if c.get("run") == run), None)
            if rec:
                failed = [c for c in rec["checks"] if c["verdict"] == "FAIL" and c.get("kind") != "report"]
                kinds = [c.get("kind", "judgement") for c in failed]
                fixture = (f", {kinds.count('fixture')} fixture error"
                           if "fixture" in kinds else "")
                per_grader.append(f"checks {rec['status']}"
                                  + (f" ({kinds.count('judgement')} judgement, "
                                     f"{kinds.count('format')} format{fixture})"
                                     if failed else ""))
            print(f"      run {run}: " + ", ".join(per_grader))
        for item in verdict["items"]:
            label = item["key"] if item["source"] == "grader" else f"{item['key']} [{item['source']}]"
            print(f"      {label:<34} {item['kind']:<13} {item['fails']}/{item['runs']} run(s)  "
                  f"{item['why'][:150]}")
            bucket = item["kind"].split(" ")[0]
            totals[bucket] = totals.get(bucket, 0) + 1
        for n in sorted(set(case.get("enumerate") or [])):
            if args.expectation and n not in args.expectation:
                continue
            cells = []
            for run in runs:
                if run in verdict["invalid_runs"]:
                    continue
                for g in range(1, args.graders + 1):
                    got = next((r for r in results[key] if r.get("run") == run
                                and r.get("grader") == g), {})
                    count = (got.get("untraced_sites") or {}).get(str(n))
                    cells.append(f"run {run} grader {g}: "
                                 + ("no sites listed" if count in (None, -1) else str(count)))
            if cells:
                print(f"      #{n} untraced sites — " + "; ".join(cells))
        totals["invalid"] += len(verdict["invalid_runs"])

    # The folder's grade gaps, in the summary and in grade-gaps.json, the form `--grade-gaps` reads; a gap in
    # one of this pass's runs leaves its expectations unresolved, so the exit code is 3.
    gaps = grade_gaps(out, args.graders)
    gap_file = write_grade_gaps(out, gaps, args.graders, pass_id)
    ours = {stem_for(s, c, m, r) for s, c, m in work for r in runs_done[(s, c["id"], m)]}
    lines = gap_lines(gaps, gap_file)
    if lines:
        print()
        print("\n".join(lines))
    report = [*sentinel_lines(sentinel_report(out)),
              *(hidden_lines(hidden_reaches(out)) if args.via == "tuesday" else [])]
    if report:
        print()
        print("\n".join(report))
    record["finished"] = utc_now()
    write_json(out / "passes" / f"{pass_id}.json", record)

    print(f"\n{totals['deterministic']} deterministic failure(s), {totals['intermittent']} "
          f"intermittent, {totals['unresolved']} unresolved, {totals['invalid']} "
          f"harness-invalid run(s)")
    if totals["intermittent"]:
        print("An intermittent failure is a reliability finding, not a defect to patch: "
              "the rule fired once and not another time, so rewriting it is as likely to "
              "move the number by luck as by fixing anything.")
    if totals["unresolved"] or totals["invalid"] or any(g["stem"] in ours for g in gaps):
        print("Unresolved expectations, partly graded runs and harness-invalid runs are not passes: the "
              "set has holes in it, and the exit code says so.")
        return 3
    return 1 if totals["deterministic"] or totals["intermittent"] else 0


if __name__ == "__main__":
    sys.exit(main())
