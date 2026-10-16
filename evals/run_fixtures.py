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

**What the graders are told.** The prompt states the room's actual research mode
and carries a "What the harness observed" block: the calls the run actually
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
expectation does not pass it: the expectation is reported unresolved until
every grader has graded it, never clean.

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

Usage:
    python evals/run_fixtures.py --out /tmp/clean-room --model claude-sonnet-5
    python evals/run_fixtures.py --skill job-underwriter --eval 3 --out /tmp/cr
    python evals/run_fixtures.py --out /tmp/cr --retry-runs 0   # one run, no retries
    python evals/run_fixtures.py --out /tmp/cr --skip-execute   # grade saved, ungraded runs
    python evals/run_fixtures.py --regrade-from /tmp/cr --out /tmp/cr-regrade --expectation 14
    python evals/run_fixtures.py --skill job-underwriter --cases probe.json --out /tmp/p
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import output_checks  # noqa: E402
from fixture_clauses import load_cases  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SKILLS = ["job-underwriter", "mock-interview", "resume-tailor"]
SERVER = Path(__file__).resolve().parent / "research_server.py"
MODES = ("denied", "canned")
SEARCH_KIND = output_checks.SEARCH_KIND
PERMISSION_TEXT = re.compile(r"requested permissions|haven't granted|permission to use|"
                             r"not allowed|was denied|denied by", re.I)

GRADER_PROMPT_VERSION = "2"

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

This is everything the response produced. Where it delivered by writing a file, that file's full contents appear below the chat text under a `----- file the response produced -----` marker, and it counts exactly as if it had been written inline.

{response}

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


CLI_FAILURE_MARKERS = (
    "session limit", "usage limit", "rate limit", "credit balance",
    "invalid api key", "overloaded", "quota",
)


def cli_failed(text: str, returncode: int) -> bool:
    """Did the CLI decline to answer rather than answering?

    A refusal from the harness is not a result from the skill. Left undetected,
    "You've hit your session limit" is saved as a 48-character response and
    graded as a fixture that produced almost nothing — the third variant in this
    suite of a non-result being recorded as a result, after the routing runner's
    errored runs and the truncated grader reply.
    """
    if returncode != 0:
        return True
    head = text.strip()[:400].lower()
    return len(text.strip()) < 200 and any(m in head for m in CLI_FAILURE_MARKERS)


class CLITimeout(RuntimeError):
    """The CLI ran out of time. Carries whatever it had streamed by then.

    An uncaught TimeoutExpired used to abort the whole worker pool and lose the
    partial stream with it; one slow canned room — tool searches, then up to
    eight calls — would have taken every other run down.
    """

    def __init__(self, message: str, partial: str = ""):
        super().__init__(message)
        self.partial = partial


def decode(raw) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return str(raw)


def claude(prompt: str, cwd: Path, timeout: int, extra_args=(), output: str = "stream",
           installed: str = "") -> dict:
    """Run one `claude -p` with the prompt on stdin; return what it produced.

    `output="stream"` returns parse_stream()'s record plus the raw stdout;
    `output="json"` returns the CLI's JSON result object, whose "result" field
    carries the reply. The prompt always goes on stdin: --mcp-config, --tools,
    --allowedTools and --disallowedTools are variadic and would swallow a
    positional prompt. The caller's flags are passed as given and nothing is
    added to them, so a room's research flags can never leak into a grader.

    Raises CLITimeout on a timeout, and RuntimeError when the CLI declined to
    answer, so a limit message can never be mistaken for a short response.
    """
    fmt = {"stream": ["--output-format", "stream-json", "--verbose"],
           "json": ["--output-format", "json"]}[output]
    cmd = ["claude", "-p", *fmt, *extra_args]
    # CLAUDECODE guards interactive terminal nesting; a subprocess run is safe.
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    try:
        proc = subprocess.run(cmd, input=prompt, cwd=str(cwd), env=env,
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise CLITimeout(f"timed out after {timeout}s", decode(exc.stdout)) from None

    if output == "json":
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            raise RuntimeError(f"CLI declined: no JSON result "
                               f"({(proc.stdout or proc.stderr).strip()[:200]})") from None
        reply = str(data.get("result") or "")
        if proc.returncode != 0 or data.get("is_error") or cli_failed(reply, proc.returncode):
            raise RuntimeError(f"CLI declined: {reply.strip()[:200] or proc.stderr.strip()[:200]}")
        return data

    parsed = parse_stream(proc.stdout.splitlines(), installed)
    parsed["stdout"] = proc.stdout
    if cli_failed(parsed["text"], proc.returncode):
        raise RuntimeError(f"CLI declined: {parsed['text'].strip()[:200] or proc.stderr.strip()[:200]}")
    if parsed["result"]["incomplete"] or parsed["result"].get("is_error"):
        raise RuntimeError(f"CLI declined: the run ended "
                           f"{'without a result' if parsed['result']['incomplete'] else 'in error'}"
                           f" ({parsed['result'].get('subtype')})")
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
      result      subtype, is_error, turns, modelUsage, permission denials, and
                  incomplete=True when no result event arrived (a timeout);
      tool_calls  every tool_use joined to its tool_result by id.
    """
    base = re.sub(r"-[0-9a-f]{8}$", "", installed_name or "")
    text, calls, order, fired_skills, denied_events = [], {}, [], [], []
    init, result = {}, None
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
            skills = [s for s in event.get("skills") or [] if isinstance(s, str)]
            init = {"claude_code_version": event.get("claude_code_version"),
                    "model": event.get("model"),
                    "permissionMode": event.get("permissionMode"),
                    "tools": event.get("tools") or [],
                    "mcp_servers": event.get("mcp_servers") or [],
                    "skills": len(skills),
                    "installed_loaded": installed_name in skills,
                    "competing_skills": [s for s in skills
                                         if base and base in s and s != installed_name],
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
                      "incomplete": False}
    if result is None:
        result = {"subtype": None, "is_error": None, "num_turns": None, "modelUsage": None,
                  "permission_denials": denied_events, "incomplete": True}
    names = [s.split(":")[-1] for s in fired_skills]
    fire = "fired" if installed_name and installed_name in names else \
        ("wrong_skill" if fired_skills else "not_fired")
    return {"text": "\n".join(text), "fire": fire, "skills_fired": fired_skills,
            "init": init, "result": result, "tool_calls": [calls[t] for t in order]}


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
        reasons.append(f"the installed skill never fired ({invocation.get('fire')})")
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
                                           "pages": research.get("pages", [])}, indent=1))
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
    (out / f"{stem}.meta.json").write_text(json.dumps(meta, indent=2) + "\n")


def execute(skill: str, case: dict, out: Path, run: int, timeout: int,
            model: str | None, mode: str | None = None) -> dict:
    """Run one fixture in a clean room and save the response plus the room's record."""
    mode = mode or modes_of(case)[0]
    stem = stem_for(skill, case, mode, run)
    meta = {"skill": skill, "id": case["id"], "run": run, "mode": mode, "stem": stem,
            "model": model, "invocations": []}
    parsed = None
    for nudged in (False, True):
        run_id = uuid.uuid4().hex[:8]
        room = out / "rooms" / f"{skill}-{case['id']}-{mode}-{run_id}"
        room.mkdir(parents=True, exist_ok=True)
        name = install_one(room, skill, run_id)
        paths = research_paths(out, room, "nudged" if nudged else "first") \
            if mode == "canned" else None
        if paths:
            write_research_files(case, paths)
        flags = room_flags(mode, paths) + (["--model", model] if model else [])
        prompt = case["prompt"] if not nudged else \
            f"Use the {name} skill for this.\n\n{case['prompt']}"
        invocation = {"room": str(room), "nudged": nudged, "installed": name, "flags": flags,
                      "calls_log": str(paths["calls"]) if paths else None}
        meta["invocations"].append(invocation)
        try:
            parsed = claude(prompt, room, timeout, flags, "stream", name)
        except RuntimeError as exc:
            # A timeout keeps what it streamed, so the record says how far the
            # run got; a decline has nothing to keep. Neither is nudged — a
            # second attempt at a run the CLI would not finish is not a fix.
            stdout = getattr(exc, "partial", "")
            if stdout:
                (out / "streams").mkdir(exist_ok=True)
                (out / "streams" / f"{room.name}.partial.jsonl").write_text(stdout)
            partial = parse_stream(stdout.splitlines(), name)
            invocation.update(outcome="timeout" if isinstance(exc, CLITimeout) else "declined",
                              error=str(exc), fire=partial["fire"], init=partial["init"],
                              result=partial["result"], tool_calls=partial["tool_calls"],
                              research_log=build_research_log(
                                  partial["tool_calls"], partial["result"]["permission_denials"],
                                  read_calls(paths["calls"]) if paths else []))
            meta.update(error=str(exc), outcome=invocation["outcome"],
                        graded_invocation=None, research_log=None,
                        harness={"status": "harness-invalid", "reasons": [f"skipped: {exc}"]})
            write_meta(out, stem, meta)
            print(f"  SKIPPED {skill} eval {case['id']} [{mode}] (run {run}): {exc}", flush=True)
            return meta
        streams = out / "streams"
        streams.mkdir(exist_ok=True)
        (streams / f"{room.name}.jsonl").write_text(parsed.pop("stdout", ""))
        calls = read_calls(paths["calls"]) if paths else []
        invocation.update(outcome="completed", fire=parsed["fire"],
                          skills_fired=parsed["skills_fired"], init=parsed["init"],
                          result=parsed["result"], tool_calls=parsed["tool_calls"],
                          research_log=build_research_log(
                              parsed["tool_calls"], parsed["result"]["permission_denials"], calls))
        if parsed["fire"] == "fired":
            break
        # The skill not firing is the routing eval's finding, not this one's.
        # Here it would leave the expectations ungraded, so the fixture is re-run
        # with the skill named — in a new room, so nothing the first attempt
        # wrote or searched is credited to the response that gets graded.

    graded = meta["invocations"][-1]
    status, reasons = classify_room(mode, graded, read_calls(graded.get("calls_log")))
    room = Path(graded["room"])
    artifacts = collect_artifacts(room, room / ".claude" / "skills" / graded["installed"])
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
    write_meta(out, stem, meta)
    init = graded.get("init") or {}
    read, unread = output_checks.user_link_reads(graded["research_log"], case.get("research"))
    links = len(read) + len(unread)
    print(f"  ran {skill} eval {case['id']} [{mode}] (run {run}): {len(text)} chars"
          f"{f', {len(artifacts)} file(s)' if artifacts else ''}"
          f"{'' if not graded['nudged'] else ' (needed a nudge to fire)'}"
          f", {len(graded['research_log']) - links} research call(s)"
          f"{f', {len(read)} user link(s) read' if read else ''}"
          f"{f', {len(unread)} user link(s) not opened' if unread else ''}, model {init.get('model')}"
          f"{'' if status == 'ok' else ' — HARNESS-INVALID: ' + '; '.join(reasons)}", flush=True)
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
    and `user links read N` counts only the reads that returned, so a grader
    comparing the tally with this record compares it with the same numbers the
    checks do.
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
            lines.append(f"User links read: {len(links)} fetch(es) of a link the user gave to read "
                         f"that returned — reading an input, not research, so named on the tally "
                         f"line as `user links read {len(links)}` and never in its fetch count:")
            lines += [line(e) for e in links]
        if unopened:
            lines.append(f"User links not opened: {len(unopened)} fetch(es) of a link the user gave "
                         f"to read that the host refused or that errored — not reads, so not counted "
                         f"on the tally line or in its fetch count; the response should say it could "
                         f"not open the link:")
            lines += [line(e) for e in unopened]
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
          model: str | None, mode: str | None = None, only=None) -> dict:
    """Score one saved response against its expectations (or the `only` subset)."""
    mode = mode or modes_of(case)[0]
    stem = stem_for(skill, case, mode, run)
    base = {"skill": skill, "id": case["id"], "run": run, "mode": mode, "grader": grader}
    body_path = out / f"{stem}.md"
    meta_path = out / f"{stem}.meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
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
            print(f"  SKIPPED grading {skill} eval {case['id']} [{mode}] (run {run}, "
                  f"grader {grader}): {exc}", flush=True)
            return parse_verdicts("", asked), None, str(exc)

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
              "grader_prompt_version": GRADER_PROMPT_VERSION,
              "expectation_sha256": {str(n): expectation_sha(case["expectations"][n - 1])
                                     for n in numbers},
              "untraced_sites": untraced_sites(result["verdicts"], case.get("enumerate"))}
    (out / f"{stem}.grade-{grader}.json").write_text(json.dumps(record, indent=2) + "\n")
    verdicts = record["verdicts"]
    # A grade that produced nothing is not a grade of zero. The SKIPPED line above
    # already said what happened; printing "0/12" beside it is the same mistake
    # this harness has now made five times, in the reporting rather than the data.
    if record.get("error") or not verdicts:
        print(f"  no verdicts for {skill} eval {case['id']} [{mode}] (run {run}, grader {grader}): "
              f"{record.get('error', 'grader returned nothing usable')}", flush=True)
        return record
    passed = sum(1 for v in verdicts if v.get("verdict") == "PASS")
    gaps = f" (incomplete: {', '.join(map(str, record['incomplete']))})" if record["incomplete"] else ""
    print(f"  graded {skill} eval {case['id']} [{mode}] (run {run}, grader {grader}): "
          f"{passed}/{len(verdicts)} of {len(numbers)}{gaps}", flush=True)
    return record


def check_run(skill: str, case: dict, out: Path, run: int, mode: str) -> dict:
    """Run the deterministic checks on one saved response; write {stem}.checks.json."""
    stem = stem_for(skill, case, mode, run)
    meta_path, body_path = out / f"{stem}.meta.json", out / f"{stem}.md"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    status, reasons = harness_status(meta)
    if status == "ok" and not body_path.exists():
        status, reasons = "harness-invalid", ["no response saved"]
    body = body_path.read_text() if body_path.exists() else ""
    record = output_checks.run_checks(case, mode, body, meta.get("research_log"), status, reasons)
    record = {"skill": skill, "id": case["id"], "run": run, "stem": stem, **record}
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
    args = ap.parse_args()

    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    grader_model = args.grader_model or args.model
    skip_execute = args.skip_execute
    if args.regrade_from:
        src = Path(args.regrade_from).resolve()
        if src == out:
            ap.error("--regrade-from must name a different directory from --out: never regrade in place")
        if any(out.glob("*.md")) or any(out.glob("*.grade-*.json")):
            ap.error(f"{out} is not fresh: --regrade-from copies into an empty --out")
        print(f"copied {copy_for_regrade(src, out)} file(s) from {src}")
        if not args.no_backfill:
            import backfill_tools
            backfill_tools.backfill_dir(out)
        skip_execute = True
    elif skip_execute and any(out.glob("*.grade-*.json")):
        ap.error(f"{out} already holds grade files; regrade into a fresh directory with "
                 f"--regrade-from {out} --out <new dir>")
    if args.cases and len(args.skill) != 1:
        ap.error("--cases needs exactly one --skill")

    skills = args.skill or SKILLS
    work = [(s, c, m) for s in skills for c in cases_for(s, args.eval, args.cases)
            for m in modes_of(c)]
    results: dict[tuple, list[dict]] = {(s, c["id"], m): [] for s, c, m in work}
    checks: dict[tuple, list[dict]] = {(s, c["id"], m): [] for s, c, m in work}
    runs_done: dict[tuple, list[int]] = {(s, c["id"], m): [] for s, c, m in work}

    def pass_over(jobs: list[tuple], label: str) -> None:
        """Execute (unless skipping), check and grade one batch of (skill, case, mode, run)."""
        if not jobs:
            return
        if not skip_execute:
            print(f"\n{label}: executing {len(jobs)} fixture run(s)")
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                list(pool.map(lambda j: execute(j[0], j[1], out, j[3], args.timeout,
                                               args.model, j[2]), jobs))
        for skill, case, mode, run in jobs:
            checks[(skill, case["id"], mode)].append(check_run(skill, case, out, run, mode))
        print(f"\n{label}: grading {len(jobs)} response(s), {args.graders} grader(s) each")
        grade_jobs = [(s, c, m, r, g) for s, c, m, r in jobs for g in range(1, args.graders + 1)]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            graded = list(pool.map(
                lambda j: grade(j[0], j[1], out, j[3], j[4], args.timeout, grader_model,
                                j[2], args.expectation or None), grade_jobs))
        for record, (skill, case, mode, _, _) in zip(graded, grade_jobs):
            results[(skill, case["id"], mode)].append(record)
        for skill, case, mode, run in jobs:
            runs_done[(skill, case["id"], mode)].append(run)

    if skip_execute:
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
                failed = [c for c in rec["checks"] if c["verdict"] == "FAIL"]
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

    print(f"\n{totals['deterministic']} deterministic failure(s), {totals['intermittent']} "
          f"intermittent, {totals['unresolved']} unresolved, {totals['invalid']} "
          f"harness-invalid run(s)")
    if totals["intermittent"]:
        print("An intermittent failure is a reliability finding, not a defect to patch: "
              "the rule fired once and not another time, so rewriting it is as likely to "
              "move the number by luck as by fixing anything.")
    if totals["unresolved"] or totals["invalid"]:
        print("Unresolved expectations and harness-invalid runs are not passes: the set has "
              "holes in it, and the exit code says so.")
        return 3
    return 1 if totals["deterministic"] or totals["intermittent"] else 0


if __name__ == "__main__":
    sys.exit(main())
