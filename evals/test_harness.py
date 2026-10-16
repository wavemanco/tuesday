#!/usr/bin/env python3
"""Tests for the eval harnesses.

These exist because the harnesses have had four bugs and, until now, no tests.
Every one of the four was the same mistake wearing different clothes — a
non-result recorded as a result — and every one was found by a person reading
output that looked wrong, which is the slowest and least reliable detector
available:

1. The routing reader broke out of its loop when the CLI process exited,
   discarding whatever was still unparsed in the pipe. A run that fired a skill
   and finished quickly was recorded as `neither`.
2. A run the CLI failed, usually a rate limit, was also recorded as `neither`.
3. A grader reply truncated mid-object yielded zero verdicts, and the summary
   counted twelve missing verdicts as twelve failures.
4. A session usage-limit message was saved as a 48-character response and graded
   as a fixture that had produced almost nothing.

The rule those four earned is in CONTRIBUTING.md: every path where an external
process can decline needs an explicit third outcome beside success and failure.
The tests below assert that third outcome on each path, so the rule has a
mechanism rather than a paragraph.

The research rooms added more such paths — a search server that can fail to
start or answer with an error, a room that is not the mode it claims, a stream
cut off by a timeout, a grader reply that covers six expectations of sixteen, a
response with no accounting table — and each has its third outcome tested here
too: harness-invalid, incomplete, unresolved, absent or unparseable, never a pass
and never a skill failure it was not.

    python evals/test_harness.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import backfill_tools
import output_checks
import recurring
import run_fixtures
import run_routing

FAILURES: list[str] = []
SERVER = Path(__file__).resolve().parent / "research_server.py"


def check(name: str, got, want) -> None:
    if got == want:
        print(f"  ok   {name}")
    else:
        FAILURES.append(f"{name}: got {got!r}, wanted {want!r}")
        print(f"  FAIL {name}: got {got!r}, wanted {want!r}")


def check_true(name: str, got: bool) -> None:
    check(name, bool(got), True)


def verdict_of(result: dict, check_name: str, target="all") -> str | None:
    """The verdict a check reported, or None if it reported nothing."""
    hits = [c["verdict"] for c in result["checks"]
            if c["check"] == check_name and c["target"] == str(target)]
    return "FAIL" if "FAIL" in hits else (hits[0] if hits else None)


# --- Decline path 1 & 2: routing classifies a failed or aborted run distinctly ---

def test_routing_declines() -> None:
    print("routing: a run that did not reach a verdict is not a negative")
    check("clean result is a genuine no-fire",
          run_routing.result_outcome({"type": "result", "subtype": "success"}), "neither")
    check("is_error result is an error, not a no-fire",
          run_routing.result_outcome({"type": "result", "is_error": True}), "error")
    check("non-success subtype is an error",
          run_routing.result_outcome({"type": "result", "subtype": "error_max_turns"}), "error")

    ok, note = run_routing.verdict("job-underwriter", ["job-underwriter"] * 3)
    check("consistent fire passes", ok, True)
    ok, note = run_routing.verdict("job-underwriter", ["job-underwriter", "neither", "job-underwriter"])
    check("one genuine no-fire fails the case", ok, False)

    ok, note = run_routing.verdict("job-underwriter", ["job-underwriter", "error", "job-underwriter"])
    check("an errored run is set aside, not counted against the case", ok, True)
    check_true("and it is reported", "error" in note)

    ok, note = run_routing.verdict("mock-interview", ["timeout", "error", "error"])
    check("a case with no run that reached a verdict is inconclusive, not a failure to fire", ok, False)
    check_true("and says so rather than reporting a route", "inconclusive" in note)

    ok, _ = run_routing.verdict("neither", ["neither"] * 3)
    check("a clean negative passes", ok, True)
    ok, _ = run_routing.verdict("either", ["job-underwriter", "mock-interview", "job-underwriter"])
    check("a spanning case passes when some sibling fires every run", ok, True)
    ok, _ = run_routing.verdict("either", ["job-underwriter", "neither", "job-underwriter"])
    check("a spanning case fails when a run reaches neither sibling", ok, False)


# --- Decline path 3: the CLI declining to answer is not a short answer ---

def test_cli_refusal() -> None:
    print("\nfixtures: a CLI refusal is not a response")
    check_true("a session-limit message is a refusal",
               run_fixtures.cli_failed("You've hit your session limit · resets 7am (UTC)", 0))
    check_true("so is a usage-limit message",
               run_fixtures.cli_failed("Usage limit reached", 0))
    check_true("a non-zero exit is a refusal whatever it printed",
               run_fixtures.cli_failed("x" * 5000, 1))
    check("a long normal answer is not a refusal",
          run_fixtures.cli_failed("x" * 5000, 0), False)
    check("a short genuine answer is not a refusal",
          run_fixtures.cli_failed("Yes — three of the four requirements are evidenced.", 0), False)
    check("a long answer that merely discusses rate limits is not a refusal",
          run_fixtures.cli_failed("The role involves rate limit tuning. " * 40, 0), False)


# --- The stream: what fired, what was called, whether it finished ---

def ev_init(skills, tools=("Skill", "WebSearch", "WebFetch"), servers=()):
    return {"type": "system", "subtype": "init", "claude_code_version": "2.1.301",
            "model": "claude-sonnet-5", "permissionMode": "default", "tools": list(tools),
            "mcp_servers": list(servers), "skills": list(skills), "session_id": "s"}


def ev_tool(tid, name, given, parent=None):
    return {"type": "assistant", "parent_tool_use_id": parent,
            "message": {"content": [{"type": "tool_use", "id": tid, "name": name, "input": given}]}}


def ev_result_of(tid, content, is_error=None, parent=None):
    item = {"type": "tool_result", "tool_use_id": tid, "content": content}
    if is_error is not None:
        item["is_error"] = is_error
    return {"type": "user", "parent_tool_use_id": parent, "message": {"content": [item]}}


def ev_text(text, parent=None):
    return {"type": "assistant", "parent_tool_use_id": parent,
            "message": {"content": [{"type": "text", "text": text}]}}


def ev_result(denials=()):
    return {"type": "result", "subtype": "success", "is_error": False, "num_turns": 4,
            "modelUsage": {"claude-sonnet-5": {"outputTokens": 10}},
            "permission_denials": list(denials)}


def stream(*events) -> list[str]:
    return [json.dumps(e) for e in events]


def test_parse_stream() -> None:
    print("\nfixtures: the stream says which skill fired and whether the run finished")
    name = "job-underwriter-ab12cd34"
    host = ["dataviz", name, "anthropic-skills:job-underwriter"]
    fired = run_fixtures.parse_stream(stream(
        ev_init(host), ev_tool("t1", "Skill", {"skill": name}),
        ev_result_of("t1", "Launching skill"), ev_text("Decision: apply."), ev_result()), name)
    check("the installed skill firing is a fire", fired["fire"], "fired")
    check("a host skill sharing its name is recorded as competing",
          fired["init"]["competing_skills"], ["anthropic-skills:job-underwriter"])
    check("the loaded skill count is recorded", fired["init"]["skills"], 3)

    wrong = run_fixtures.parse_stream(stream(
        ev_init(host), ev_tool("t1", "Skill", {"skill": "anthropic-skills:job-underwriter"}),
        ev_text("x"), ev_result()), name)
    check("a host skill of the same name firing is wrong_skill, not a fire", wrong["fire"],
          "wrong_skill")
    none = run_fixtures.parse_stream(stream(ev_init(host), ev_text("x"), ev_result()), name)
    check("no Skill call is not_fired", none["fire"], "not_fired")

    denied = {"tool_name": "WebSearch", "tool_use_id": "t2",
              "tool_input": {"query": "Harborlight careers"}}
    run = run_fixtures.parse_stream(stream(
        ev_init(host), ev_tool("t1", "Skill", {"skill": name}),
        ev_tool("t2", "WebSearch", {"query": "Harborlight careers"}),
        ev_result_of("t2", "Claude requested permissions to use WebSearch, but you haven't "
                           "granted it yet.", is_error=True),
        ev_tool("t3", "Read", {"file_path": "x"}, parent="t9"),
        ev_result_of("t3", "contents", parent="t9"),
        ev_text("a subagent's note", parent="t9"),
        ev_text("the answer"), ev_result([denied])), name)
    call = next(c for c in run["tool_calls"] if c["id"] == "t2")
    check("a tool_use is joined to its tool_result, error flag kept", call["is_error"], True)
    check("permission denials come from the result event",
          [d["tool_use_id"] for d in run["result"]["permission_denials"]], ["t2"])
    sub = next(c for c in run["tool_calls"] if c["id"] == "t3")
    check("a subagent's tool call is recorded with its parent", sub["parent_tool_use_id"], "t9")
    check("a subagent's text is not the response", run["text"], "the answer")
    check("a finished stream is not incomplete", run["result"]["incomplete"], False)
    cut = run_fixtures.parse_stream(stream(ev_init(host), ev_tool("t1", "Skill", {"skill": name}),
                                           ev_text("half an answ")), name)
    check("a stream with no result event is incomplete", cut["result"]["incomplete"], True)

    log = run_fixtures.build_research_log(run["tool_calls"], run["result"]["permission_denials"], [])
    check("the refused search is in the research log as refused",
          [(e["tool"], e["outcome"]) for e in log], [("WebSearch", "refused")])


# --- The research server, driven over its pipes ---

CORPUS = {
    "entity_tokens": ["Kestrel Analytics", "kestrel"],
    "pages": [
        {"url": "https://kestrel.test/careers", "title": "Careers at Kestrel",
         "text": "Kestrel came from an experimentation-platform team. Open roles.",
         "target": 1, "keywords": ["careers", "jobs", "kestrel"]},
        {"url": "https://kestrel.test/about", "title": "About Kestrel",
         "text": "Founded 2019 in Leeds.", "target": 1, "keywords": ["about", "company"]},
        {"url": "https://survey.test/analyst", "title": "Analyst pay survey",
         "text": "Median $147,300.", "target": 2, "keywords": ["salary", "compensation"]},
    ],
}


def drive_server(requests: list[dict], tmp: Path) -> tuple[list[dict], Path, Path]:
    corpus = tmp / "corpus.json"
    corpus.write_text(json.dumps(CORPUS))
    log = tmp / "calls.jsonl"
    cwd = tmp / "cwd"
    cwd.mkdir()
    proc = subprocess.run([sys.executable, "-I", str(SERVER), str(corpus), str(log)],
                          input="\n".join(json.dumps(r) for r in requests) + "\n",
                          cwd=cwd, capture_output=True, text=True, timeout=30)
    replies = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    return replies, log, cwd


def test_research_server() -> None:
    print("\nresearch server: deterministic, logged, and silent outside its log")
    def call(i, tool, **args):
        return {"jsonrpc": "2.0", "id": i, "method": "tools/call",
                "params": {"name": tool, "arguments": args}}
    requests = [
        {"jsonrpc": "2.0", "id": 0, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        call(2, "search", query="Kestrel Analytics careers"),
        call(3, "search", query="Kestrel Analytics careers"),
        call(4, "search", query="Kestrel Analytics"),
        call(5, "fetch", url="https://kestrel.test/careers/"),
        call(6, "fetch", url="https://kestrel.test/careers/"),
        call(7, "fetch", url="https://nowhere.test/"),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        replies, log_path, cwd = drive_server(requests, Path(tmp))
        by_id = {r["id"]: r for r in replies}
        check("it exits on EOF and answered every request with an id", sorted(by_id),
              [0, 1, 2, 3, 4, 5, 6, 7])
        check("initialize echoes the protocol version",
              by_id[0]["result"]["protocolVersion"], "2025-06-18")
        check("tools/list offers search and fetch",
              [t["name"] for t in by_id[1]["result"]["tools"]], ["search", "fetch"])
        text = lambda i: by_id[i]["result"]["content"][0]["text"]
        check("the same search twice returns the same text", text(2), text(3))
        check_true("and it found the careers page", "https://kestrel.test/careers" in text(2))
        check_true("a canary in a page's opening is visible in the snippet",
                   "experimentation-platform team" in text(2))
        check_true("the company name alone surfaces nothing", text(4).startswith("No results found"))
        check("a miss is not an error", by_id[4]["result"]["isError"], False)
        check("the same fetch twice returns the same page", text(5), text(6))
        check_true("an unknown URL is said plainly, not as a failure",
                   text(7) == "No page at https://nowhere.test/" and "fail" not in text(7).lower())
        log = [json.loads(line) for line in log_path.read_text().splitlines()]
        check("it logs initialize and tools/list", [l.get("rpc") for l in log[:2]],
              ["initialize", "tools/list"])
        first = next(l for l in log if l.get("id") == 2)
        check("a search's log line carries the URLs it returned",
              first["returned_urls"], ["https://kestrel.test/careers"])
        check("and the targets those pages are tagged with", first["targets"], [1])
        check("outcomes are logged as hit / no_results / fetch_miss",
              [l["outcome"] for l in log if "outcome" in l],
              ["hit", "hit", "no_results", "hit", "hit", "fetch_miss"])
        check("it writes nothing in its working directory", list(cwd.iterdir()), [])


# --- Rooms: flags, research file locations, artifacts ---

def test_rooms() -> None:
    print("\nfixtures: a room is the mode it claims, and its research files stay outside it")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        room = out / "rooms" / "job-underwriter-1-canned-ab12cd34"
        room.mkdir(parents=True)
        first = run_fixtures.research_paths(out, room, "first")
        nudged = run_fixtures.research_paths(out, room, "nudged")
        canned = run_fixtures.room_flags("canned", first)
        denied = run_fixtures.room_flags("denied")
        tail = canned[canned.index("--disallowedTools"):] if "--disallowedTools" in canned else []
        check("a canned room disallows the built-in web tools", tail[:3],
              ["--disallowedTools", "WebSearch", "WebFetch"])
        check_true("and loads only the fixture's server",
                   "--strict-mcp-config" in canned and str(first["mcp"]) in canned)
        check("a denied room drops user settings and MCP servers",
              denied, ["--setting-sources", "project", "--strict-mcp-config"])
        check("and never disallows the web tools: refused, not absent",
              "--disallowedTools" in denied, False)
        check_true("research files are absolute",
                   all(p.is_absolute() for p in first.values()))
        check("and outside the room", any(room.resolve() in p.parents for p in first.values()),
              False)
        check("each invocation gets its own call log", first["calls"] == nudged["calls"], False)
        try:
            run_fixtures.research_paths(room, room, "first")
            check("research files inside the room are refused", "accepted", "refused")
        except run_fixtures.RoomLeak:
            check("research files inside the room are refused", "refused", "refused")

        skill_dir = room / ".claude" / "skills" / "x"
        skill_dir.mkdir(parents=True)
        (room / "pack.md").write_text("the delivered pack")
        run_fixtures.write_research_files({"research": CORPUS}, first)
        found = dict(run_fixtures.collect_artifacts(room, skill_dir))
        check("collect_artifacts ignores <out>/research", sorted(found), ["pack.md"])


def test_stems() -> None:
    print("\nfixtures: one name per run, mode-aware only where modes exist")
    legacy = {"id": 3, "research": {"modes": ["denied"]}}
    plain = {"id": 3}
    both = {"id": 3, "research": {"modes": ["canned", "denied"]}}
    check("a denied-only fixture keeps the old stem",
          run_fixtures.stem_for("s", legacy, "denied", 2), "s-3.run2")
    check("so does one with no research block", run_fixtures.stem_for("s", plain, "denied", 0),
          "s-3.run0")
    check("a two-mode fixture carries the mode",
          run_fixtures.stem_for("s", both, "canned", 1), "s-3.canned.run1")


# --- Decline path 4: a grader that returned nothing graded nothing ---

def test_grade_parsing() -> None:
    print("\nfixtures: a grade that did not parse is not a fixture that failed")
    whole = json.dumps({"verdicts": [{"n": 1, "why": "a", "verdict": "PASS"},
                                     {"n": 2, "why": "b", "verdict": "FAIL"}]})
    got = run_fixtures.parse_verdicts(whole, 2)
    check("a why-first whole reply parses", [v["verdict"] for v in got["verdicts"]], ["PASS", "FAIL"])
    check("and is neither truncated nor incomplete", (got.get("truncated"), got["incomplete"]),
          (None, []))

    cut = ('{"verdicts": [{"n": 1, "why": "fine", "verdict": "PASS"}, '
           '{"n": 2, "why": "the response says the band is high and then it cu')
    got = run_fixtures.parse_verdicts(cut, 2)
    check("a reply cut mid-why keeps the verdicts it did contain", len(got["verdicts"]), 1)
    check_true("and is marked truncated", got.get("truncated"))
    check("and the cut expectation is incomplete, not failed", got["incomplete"], [2])

    shuffled = ('{"verdicts": [{"why": "w", "verdict": "FAIL", "n": 1}, '
                '{"verdict": "PASS", "n": 2, "why": "x"}, {"n": 3, "verdict": "PASS", "why": "trunc')
    got = run_fixtures.parse_verdicts(shuffled, 3)
    check("salvage accepts any key order", [(v["n"], v["verdict"]) for v in got["verdicts"]],
          [(1, "FAIL"), (2, "PASS")])

    tricky = ('{"verdicts": [{"n": 1, "why": "it writes {company} and the word verdict: PASS '
              'appears in its notes", "verdict": "FAIL"}, {"n": 2, "why": "cut')
    got = run_fixtures.parse_verdicts(tricky, 2)
    check("braces and the word verdict inside a why do not fool salvage",
          [(v["n"], v["verdict"]) for v in got["verdicts"]], [(1, "FAIL")])

    six = json.dumps({"verdicts": [{"n": i, "why": "ok", "verdict": "PASS"} for i in range(1, 7)]})
    got = run_fixtures.parse_verdicts(six, 16)
    check("a whole reply covering 6 of 16 is incomplete for the other ten",
          got["incomplete"], list(range(7, 17)))
    check("and they are missing, not failed",
          [v for v in got["verdicts"] if v["verdict"] == "FAIL"], [])

    dup = json.dumps({"verdicts": [{"n": 1, "why": "a", "verdict": "PASS"},
                                   {"n": 1, "why": "b", "verdict": "FAIL"},
                                   {"n": 2, "why": "c", "verdict": "PASS"}]})
    got = run_fixtures.parse_verdicts(dup, 2)
    check("a conflicting duplicate makes that number invalid",
          ([v["n"] for v in got["verdicts"]], got["incomplete"]), ([2], [1]))
    check_true("and it is reported", any(i["n"] == 1 for i in got["invalid"]))

    lower = json.dumps({"verdicts": [{"n": 1, "why": "a", "verdict": "pass"}]})
    got = run_fixtures.parse_verdicts(lower, 1)
    check("a lowercase pass is invalid, not a pass", (got["verdicts"], got["incomplete"]), ([], [1]))

    got = run_fixtures.parse_verdicts("the grader said nothing useful at all", 3)
    check("an unusable reply yields no verdicts", got["verdicts"], [])
    check_true("and carries an error", bool(got.get("error")))


def test_classification() -> None:
    print("\nfixtures: deterministic, intermittent and unresolved are told apart")
    def rec(run, grader, verdicts, expected=(1, 2)):
        return {"run": run, "grader": grader, "expected": list(expected),
                "verdicts": [{"n": n, "why": f"why {n}", "verdict": v} for n, v in verdicts]}
    results = [
        rec(0, 1, [(1, "FAIL"), (2, "PASS")]), rec(0, 2, [(1, "FAIL"), (2, "PASS")]),
        rec(1, 1, [(1, "FAIL"), (2, "PASS")]), rec(1, 2, [(1, "PASS"), (2, "PASS")]),
        # run 2: grader 1 skipped #1, grader 2 passed it
        rec(2, 1, [(2, "PASS")]), rec(2, 2, [(1, "PASS"), (2, "PASS")]),
    ]
    got = {i["key"]: i["kind"] for i in run_fixtures.classify(results, [], [0, 1, 2], 2)["items"]}
    check("one grader skipping #n where the other passed, #n failing every other run, "
          "is unresolved", got.get("#1"), "unresolved (1 partially graded)")
    check("an expectation every grader passed everywhere is not listed", "#2" in got, False)

    two = [r for r in results if r["run"] in (0, 1)]
    got = {i["key"]: i["kind"] for i in run_fixtures.classify(two, [], [0, 1], 2)["items"]}
    check("one grader failing is enough to fail the run", got.get("#1"), "deterministic")
    mixed = two + [rec(2, 1, [(1, "PASS"), (2, "PASS")]), rec(2, 2, [(1, "PASS"), (2, "PASS")])]
    got = {i["key"]: i["kind"] for i in run_fixtures.classify(mixed, [], [0, 1, 2], 2)["items"]}
    check("a fully graded passing run makes it intermittent", got.get("#1"), "intermittent")

    checks = [{"run": 0, "status": "fail", "checks": [
                  {"check": "accept", "target": "1", "verdict": "FAIL", "why": "w", "kind": "judgement"}]},
              {"run": 1, "status": "harness-invalid", "checks": [], "info": ["server failed"]}]
    got = run_fixtures.classify(two, checks, [0, 1], 2)
    check("a harness-invalid run leaves every denominator",
          (got["valid_runs"], sorted(got["invalid_runs"])), ([0], [1]))
    check("a check failure is classified like a grader's",
          {i["key"]: i["kind"] for i in got["items"]}.get("chk:accept:1"), "deterministic")


# --- Decline path 5: a run that never executed has nothing to grade ---

def test_missing_response() -> None:
    print("\nfixtures: a skipped execution is not a fixture that produced nothing")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        case = {"id": 1, "prompt": "irrelevant", "expectations": ["a", "b", "c"]}
        got = run_fixtures.grade("s", case, out, run=0, grader=1, timeout=1, model=None)
        check("grading a run with no response returns no verdicts", got["verdicts"], [])
        check_true("and carries an error rather than three failures", bool(got.get("error")))


def test_declined_grade_prints_no_score() -> None:
    """A grade that produced nothing must not print as a score of zero.

    The fifth instance of this bug class, and the first in the reporting rather
    than the data: a run-set killed by a weekly usage limit printed "SKIPPED
    grading ..." and then "graded ... 0/12" on the next line for every grader.
    The data was correct — nothing was recorded as failed — and a person reading
    the log saw twelve zeros.
    """
    print("\nfixtures: a declined or timed-out grade does not print a score")
    import contextlib
    import io
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        case = {"id": 1, "prompt": "irrelevant", "expectations": ["a", "b", "c"]}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_fixtures.grade("s", case, out, run=0, grader=1, timeout=1, model=None)
        printed = buf.getvalue()
        check("no score is printed", "0/3" in printed, False)
        check_true("and the reason is", "no verdicts" in printed)

        (out / "s-1.run0.md").write_text("a response")
        (out / "s-1.run0.meta.json").write_text(json.dumps({"skill_fired": True}))
        real, run_fixtures.claude = run_fixtures.claude, timing_out
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                got = run_fixtures.grade("s", case, out, run=0, grader=1, timeout=1, model=None)
        finally:
            run_fixtures.claude = real
        check("a grader that times out yields no verdicts", got["verdicts"], [])
        check("every expectation is incomplete, none failed", got["incomplete"], [1, 2, 3])
        check("and no score is printed", "0/3" in buf.getvalue(), False)


# --- The artifact collector, which produced its own false negative once ---

def test_artifact_collection() -> None:
    print("\nfixtures: delivered files are collected, the installed skill is not")
    with tempfile.TemporaryDirectory() as tmp:
        room = Path(tmp) / "room"
        skill_dir = room / ".claude" / "skills" / "x-123"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("the skill itself, not an artifact")
        (room / "pack.md").write_text("the delivered pack")
        (room / "notes.bin").write_bytes(b"\x00\x01binary")
        found = dict(run_fixtures.collect_artifacts(room, skill_dir))
        check("the delivered file is collected", found.get("pack.md"), "the delivered pack")
        check("the installed skill is excluded", "SKILL.md" in found, False)
        check("a non-text file is excluded", "notes.bin" in found, False)


def test_skill_installation() -> None:
    print("\nfixtures: an installed skill is what ships, renamed")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        name = run_fixtures.install_one(root, "resume-tailor", "abc123")
        dest = root / ".claude" / "skills" / name
        check("the directory carries the unique run id", name, "resume-tailor-abc123")
        check_true("the frontmatter name matches the directory",
                   f"name: {name}" in (dest / "SKILL.md").read_text())
        check("evals are excluded, as the packager excludes them",
              (dest / "evals").exists(), False)


# --- The room is checked, not assumed ---

def invocation(fire="fired", tools=("Skill", "mcp__web__search", "mcp__web__fetch"),
               servers=({"name": "web", "status": "connected"},), calls=(), denials=()):
    return {"fire": fire, "init": {"tools": list(tools), "mcp_servers": list(servers)},
            "tool_calls": list(calls), "result": {"permission_denials": list(denials)}}


INIT_LOG = [{"rpc": "initialize"}, {"rpc": "tools/list"}]


def test_classify_room() -> None:
    print("\nfixtures: a room that is not its mode is harness-invalid, not a skill result")
    status, _ = run_fixtures.classify_room("canned", invocation(), INIT_LOG)
    check("a connected canned room with zero calls is valid: not searching is the skill's choice",
          status, "ok")
    status, why = run_fixtures.classify_room(
        "canned", invocation(servers=({"name": "web", "status": "failed"},)), INIT_LOG)
    check("a server that failed to connect is invalid", status, "harness-invalid")
    status, _ = run_fixtures.classify_room(
        "canned", invocation(tools=("Skill", "WebSearch", "mcp__web__search", "mcp__web__fetch")),
        INIT_LOG)
    check("WebSearch present in a canned room is invalid", status, "harness-invalid")
    status, _ = run_fixtures.classify_room("canned", invocation(), [])
    check("a server log with no initialize line is invalid", status, "harness-invalid")
    crash = {"id": "t1", "name": "mcp__web__search", "is_error": True,
             "result_excerpt": "MCP error -32603: internal error"}
    status, _ = run_fixtures.classify_room("canned", invocation(calls=[crash]), INIT_LOG)
    check("an error from the server itself is invalid", status, "harness-invalid")
    blocked = dict(crash, result_excerpt="Claude requested permissions to use mcp__web__search")
    status, _ = run_fixtures.classify_room("canned", invocation(calls=[blocked]), INIT_LOG)
    check("a permission denial is not a server error", status, "ok")
    live = {"id": "t1", "name": "WebSearch", "is_error": False, "result_excerpt": "results"}
    status, _ = run_fixtures.classify_room(
        "denied", invocation(tools=("Skill", "WebSearch"), servers=(), calls=[live]), [])
    check("a search that succeeded in a denied room is a mode mismatch", status, "harness-invalid")
    status, _ = run_fixtures.classify_room(
        "denied", invocation(tools=("Skill", "WebSearch"), servers=()), [])
    check("a denied room with nothing returned is valid", status, "ok")
    status, why = run_fixtures.classify_room("denied", invocation(fire="not_fired", servers=()), [])
    check("a run that never fired the installed skill is invalid", status, "harness-invalid")


# --- execute(): timeouts and nudges, with a fake CLI ---

def timing_out(prompt, cwd, timeout, extra_args=(), output="stream", installed=""):
    raise run_fixtures.CLITimeout(f"timed out after {timeout}s",
                                  json.dumps(ev_init([installed])) + "\n")


def test_execute_timeout() -> None:
    print("\nfixtures: a run that times out is a skipped run with a reason, never nudged")
    calls = []
    def fake(*a, **k):
        calls.append(a)
        return timing_out(*a, **k)
    case = {"id": 1, "prompt": "p", "expectations": ["a"]}
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        real, run_fixtures.claude = run_fixtures.claude, fake
        try:
            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()):
                meta = run_fixtures.execute("resume-tailor", case, out, 0, 1, None)
        finally:
            run_fixtures.claude = real
        check("it does not crash and records the timeout", meta.get("outcome"), "timeout")
        check_true("with a reason", "timed out" in meta.get("error", ""))
        check("and it is not nudged", len(calls), 1)
        check("no response is saved to be graded", (out / "resume-tailor-1.run0.md").exists(), False)
        saved = json.loads((out / "resume-tailor-1.run0.meta.json").read_text())
        check("the saved record is harness-invalid", saved["harness"]["status"], "harness-invalid")


def test_execute_nudge() -> None:
    print("\nfixtures: a nudge is a new room; the first attempt's files and calls are not credited")
    case = {"id": 1, "prompt": "p", "expectations": ["a"],
            "research": {"modes": ["canned"], "pages": CORPUS["pages"],
                         "entity_tokens": CORPUS["entity_tokens"]}}
    seen = []
    def fake(prompt, cwd, timeout, extra_args=(), output="stream", installed=""):
        cfg = json.loads(Path(extra_args[extra_args.index("--mcp-config") + 1]).read_text())
        log = Path(cfg["mcpServers"]["web"]["args"][-1])
        nudged = prompt.startswith("Use the")
        seen.append((Path(cwd), log))
        log.write_text(json.dumps({"rpc": "initialize"}) + "\n" + json.dumps(
            {"id": 1, "tool": "search", "args": {"query": "first" if not nudged else "second"},
             "returned_urls": ["https://kestrel.test/careers"], "targets": [1], "outcome": "hit"}) + "\n")
        (Path(cwd) / ("second.md" if nudged else "first.md")).write_text("written")
        events = [ev_init([installed], ("Skill", "mcp__web__search", "mcp__web__fetch"),
                          ({"name": "web", "status": "connected"},)),
                  ev_tool("q1", "mcp__web__search", {"query": "first" if not nudged else "second"}),
                  ev_result_of("q1", "results", is_error=False)]
        if nudged:
            events.append(ev_tool("s1", "Skill", {"skill": installed}))
        events += [ev_text("second answer" if nudged else "first answer"), ev_result()]
        parsed = run_fixtures.parse_stream(stream(*events), installed)
        parsed["stdout"] = ""
        return parsed
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        real, run_fixtures.claude = run_fixtures.claude, fake
        try:
            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()):
                meta = run_fixtures.execute("resume-tailor", case, out, 0, 1, None)
        finally:
            run_fixtures.claude = real
        check("the nudge ran in a different room", seen[0][0] == seen[1][0], False)
        check("with its own call log", seen[0][1] == seen[1][1], False)
        check("both invocations are recorded, the second graded",
              (len(meta["invocations"]), meta["graded_invocation"]), (2, 1))
        body = (out / "resume-tailor-1.canned.run0.md").read_text()
        check("the graded response is the nudged one", body.startswith("second answer"), True)
        check("the first attempt's file is not collected", "first.md" in body, False)
        check("the graded research log holds only the nudged run's call",
              [e["query_or_url"] for e in meta["research_log"]], ["second"])
        check("the room is valid", meta["harness"]["status"], "ok")


# --- 6a. Research accounting, read from verbatim saved outputs ---

# Cut verbatim from saved runs, so the parser is tested against what skills actually
# wrote rather than against what a test author imagined they would. Paths are
# relative to the session scratchpad the sets were saved in; nothing reads them now.
# scratchpad/final2/ju/job-underwriter-1.run0.md:78-82
JU1_RUN0 = (
    '| L1 target | Status | What it would have moved |\n'
    '|---|---|---|\n'
    "| Company official site / careers page | unavailable (search tool not authorized this session) | RR3 resolution; role reality's org-context confidence |\n"
    "| Role-family sweep (title/scope/comp norms) | unavailable (same reason) | Role reality's market-calibration line; RR2's comp band |\n"
    '| Hiring manager public footprint | n/a | No hiring manager name was given |'
)

# scratchpad/final2/ju/job-underwriter-1.run2.md:78-84
JU1_RUN2 = (
    '| Target | Result |\n'
    '|---|---|\n'
    "| Company official site / careers page (verify entity + live posting) | unavailable — WebSearch permission wasn't granted this turn; would have resolved RR1 |\n"
    '| Role-family sweep (title/scope/comp norms) | unavailable — same reason; would have given a `[generic]` comp band for RR2/RR3 |\n'
    '| Hiring manager public footprint | n/a — no name given |\n'
    '\n'
    'Searches attempted: 3. Completed: 0.'
)

# scratchpad/final2/mi/mock-interview-5.run3.md:202-209
MI5_RUN3 = (
    '**Research tier:** L1 attempted; web search was unavailable in this session (tool-access error), so the pack degrades to L0 for anything requiring live lookup. Target accounting:\n'
    '\n'
    '| L1 target | Ran | What it moved, or could not have |\n'
    '|---|---|---|\n'
    '| 1. `{company} values` | unavailable | Would have supplied a values/principles cheat sheet (dropped from this pack entirely — no values-round content exists here) |\n'
    "| 2. `{company} interview process` | n/a | Not needed — the recruiter's email supplied the exact loop structure directly and more reliably than search would have |\n"
    '| 3. `{company} strategy` / recent news | unavailable | Would have supplied a Grounding brief and sharper, company-specific §5 theses; your own (unread-by-this-pack) strategy report is the real substitute — see the question below |\n'
    '| 4. `{interviewer} {company}` | n/a | Only first names were given — insufficient to search reliably even with a working tool; persona weights were built from stated titles instead |'
)

# diag/harness/fx/mock-interview-5.canned.8bad1381.md:249-258
MI5_8BAD = (
    'Research tier: L1. Four searches and two fetches used, out of six and two.\n'
    '\n'
    '| L1 target | Ran | What it moved, or could not have |\n'
    '|---|---|---|\n'
    '| 1. Kelverton values | yes | Values in 4a and the two VAL questions |\n'
    "| 2. Kelverton interview process | yes | Only forum reports; the recruiter's email is more specific and took priority |\n"
    '| 3. Kelverton strategy | yes | POV facts, A-bank and G2 |\n'
    "| 4. Interviewer name and company | unavailable | First names only, so a public footprint couldn't be attributed safely; the interviewer read is absent |\n"
    '| Extra: representative JD search | yes | Returned nothing usable, so requirements are inferred |\n'
    '| Extra: UK rail market context search | yes | Returned no external sources, so the pack makes no market claims |'
)

# Cut from the canned probe run while this harness was built (job-underwriter eval 1,
# canned room, claude-sonnet-5): a numbered table with the target in column two.
JU1_CANNED_PROBE = (
    'Research tier: L1 — searches 2 of 5, fetches 0 of 2\n'
    '\n'
    '| # | Target | Status | Reason |\n'
    '|---|---|---|---|\n'
    "| 1 | Company official site / careers page | yes | Search returned the company's own About page: ~420 employees, Series C (Northbay Ventures, March 2025), care-navigation app, Boston HQ — consistent with the posting. |\n"
    "| 2 | Role-family sweep (title, scope, compensation norms) | yes | Returned a pay-survey-style figure (~$147K median), but from a domain that doesn't resolve as a legitimate production site — flagged as low-reliability rather than asserted as a confirmed band. |\n"
    '| 3 | Hiring manager public footprint | n/a | No hiring manager was named in the inputs, so this target has no query to run. |'
)

# The same run's fit ledger: bold tokens, and a parenthetical that is not how its
# Requirement begins.
JU1_CANNED_LEDGER = (
    '**Fit ledger** (from the evidence map below):\n'
    '- **must_have** — direct: R1, R2, R3, R4, R5a, R7; adjacent: R5b (partner with product managers *and clinicians*)\n'
    '- **important** — unclear: R6 (mentor two junior analysts)\n'
    '- **preferred** — adjacent: R8 (healthcare data experience (HIPAA))'
)

def test_parse_accounting() -> None:
    print("\nchecks: the accounting table is absent, unparseable or checked — never guessed")
    got = output_checks.parse_accounting(JU1_RUN0)
    check("unnumbered rows cannot be keyed: unparseable (ju-1 run0)", got["outcome"], "unparseable")
    check("and each unnumbered row is a format violation",
          sum("target number" in p for _, p in got["format"]), 3)
    got = output_checks.parse_accounting(JU1_RUN2)
    check("a target table with no Status column is unparseable (ju-1 run2)", got["outcome"],
          "unparseable")
    check("the free-prose count beside it is no tally", output_checks.parse_tally(JU1_RUN2)["outcome"],
          "absent")
    got = output_checks.parse_accounting(MI5_RUN3)
    check("numbered rows under a legacy 'Ran' header are checked (mi-5 run3)",
          {n: r["label"] for n, r in got["rows"].items()},
          {1: "unavailable", 2: "n/a", 3: "unavailable", 4: "n/a"})
    check("a prose research-tier line is an unparseable tally",
          output_checks.parse_tally(MI5_RUN3)["outcome"], "unparseable")
    got = output_checks.parse_accounting(MI5_8BAD)
    check("the canned prototype's numbered rows are read (8bad1381)",
          {n: r["label"] for n, r in got["rows"].items()},
          {1: "yes", 2: "yes", 3: "yes", 4: "unavailable"})
    check("its two 'Extra:' rows are format violations",
          sum("Extra:" in p for _, p in got["format"]), 2)
    got = output_checks.parse_accounting(JU1_CANNED_PROBE)
    check("a numbered table with the target in column two is read, not absent (canned probe)",
          {n: r["label"] for n, r in got["rows"].items()}, {1: "yes", 2: "yes", 3: "n/a"})
    check_true("and its layout is a format violation",
               any("not the first column" in p for _, p in got["format"]))
    check("its tally line is read", output_checks.parse_tally(JU1_CANNED_PROBE)["searches"], 2)
    got = output_checks.parse_accounting("A response with no table at all.")
    check("a response with no table is absent", got["outcome"], "absent")
    qualified = JU1_RUN0.replace("| Company official", "| 1. Company official") \
        .replace("| Role-family", "| 2. Role-family").replace("| Hiring", "| 3. Hiring")
    got = output_checks.parse_accounting(qualified)
    check("a qualifier in a status cell is a format violation, its label still read",
          (got["rows"][1]["label"], any("bare label" in p for _, p in got["format"])),
          ("unavailable", True))
    both = MI5_8BAD + "\n\n----- file the response produced: pack.md -----\n" + \
        MI5_8BAD.replace("| 3. Kelverton strategy | yes", "| 3. Kelverton strategy | skipped")
    got = output_checks.parse_accounting(both)
    check_true("chat and file tables that disagree are a format violation",
               any("disagree" in p for _, p in got["format"]))


RESEARCH = {
    "modes": ["canned", "denied"],
    "budget": {"tier": "L1", "searches": 5, "fetches": 2},
    "targets": [
        {"n": 1, "name": "company site", "terms": ["careers", "about"],
         "accept": {"canned": ["yes"], "denied": ["unavailable"]}},
        {"n": 2, "name": "role-family sweep", "terms": ["salary", "compensation"],
         "accept": ["yes", "unavailable", "skipped"]},
        {"n": 3, "name": "hiring manager", "terms": ["imogen"], "accept": ["n/a", "yes"]},
    ],
    "pages": CORPUS["pages"],
    "canaries": [{"target": 1, "text": "came from an experimentation-platform team"}],
}


def accounting(labels: dict, tally: str = "Research tier: L1 — searches 2 of 5, fetches 0 of 2",
               extra: str = "") -> str:
    rows = "\n".join(f"| {n}. target | {label} | why |" for n, label in labels.items())
    return f"{extra}\n\n{tally}\n\n| L1 target | Status | What it moved |\n|---|---|---|\n{rows}\n"


def entry(query, outcome="returned", kind="search", targets=()):
    return {"tool": "mcp__web__search" if kind == "search" else "mcp__web__fetch", "kind": kind,
            "query_or_url": query, "outcome": outcome, "urls_returned": [],
            "targets": list(targets)}


def test_check_accounting() -> None:
    print("\nchecks: each label is judged against the calls aimed at its target")
    two = [entry("Kestrel careers", targets=[1]), entry("analyst salary", targets=[2])]
    canary = "It came from an experimentation-platform team."
    good = output_checks.check_accounting(
        accounting({1: "yes", 2: "yes", 3: "n/a"}, extra=canary), RESEARCH, "canned", two)
    check("a consistent canned run passes every check",
          [c["check"] for c in good["checks"] if c["verdict"] == "FAIL"], [])

    got = output_checks.check_accounting(
        accounting({1: "yes", 2: "yes", 3: "yes"}, extra=canary), RESEARCH, "canned", two)
    check("`yes` with no call aimed at the target fails", verdict_of(got, "yes_has_call", 3), "FAIL")

    refused = [entry("Kestrel careers", "refused"), entry("analyst salary", "refused")]
    got = output_checks.check_accounting(
        accounting({1: "unavailable", 2: "skipped", 3: "n/a"}), RESEARCH, "denied", refused)
    check("`skipped` with a call aimed at it fails, a refused call included",
          verdict_of(got, "skip_has_no_call", 2), "FAIL")
    check("`unavailable` in a denied room needs nothing more",
          verdict_of(got, "unavailable_has_refusal", 1), None)

    got = output_checks.check_accounting(
        accounting({1: "unavailable", 2: "unavailable", 3: "n/a"}, "Research tier: L0 — no searches"),
        RESEARCH, "canned", [])
    check("`unavailable` in a canned room with nothing refused fails",
          verdict_of(got, "unavailable_has_refusal", 1), "FAIL")

    zero = dict(RESEARCH, zero_calls=True)
    got = output_checks.check_accounting(accounting({1: "yes", 2: "yes", 3: "n/a"}, extra=canary),
                                         zero, "canned", two)
    check("a call in a zero-calls fixture fails", verdict_of(got, "zero_calls"), "FAIL")

    off = output_checks.check_accounting(
        accounting({1: "yes", 2: "yes", 3: "n/a"}, "Research tier: L1 — searches 3 of 5, fetches 0 of 2",
                   canary), RESEARCH, "canned", two)
    check("a tally one search off the record fails", verdict_of(off, "tally_searches"), "FAIL")
    got = output_checks.check_accounting(
        accounting({1: "yes", 2: "yes", 3: "n/a"}, "", canary), RESEARCH, "canned", two)
    check("no tally line fails", verdict_of(got, "tally"), "FAIL")

    got = output_checks.check_accounting(accounting({1: "yes", 2: "yes", 3: "n/a"}),
                                         RESEARCH, "canned", two)
    check("a canned `yes` whose page's canary never reached the response fails",
          verdict_of(got, "canary", 1), "FAIL")
    got = output_checks.check_accounting(
        accounting({1: "unavailable", 2: "unavailable", 3: "n/a"}, extra=canary),
        RESEARCH, "denied", refused[:1])
    check("a canary in a denied room's response fails the negative control",
          verdict_of(got, "canary_absent", 1), "FAIL")

    got = output_checks.check_accounting(accounting({1: "yes", 2: "yes", 3: "n/a"}, extra=canary),
                                         RESEARCH, "canned", None)
    check("with no research log, the checks that need one are not run",
          (verdict_of(got, "yes_has_call", 1), "yes_has_call" in got["unchecked"]), (None, True))
    got = output_checks.check_accounting("no table", RESEARCH, "denied", [])
    check("an absent table fails every target's row check",
          [verdict_of(got, "row", n) for n in (1, 2, 3)], ["FAIL"] * 3)


# --- 6b. Fit ledger ---

LEDGER_OK = """## Decision snapshot

**Worth applying to. Status: `conditional_go`.**

**Fit ledger.**

- `hard_gate` — direct: R1
- `must_have` — direct: R2, R3 · adjacent: R4 (Regulatory exposure)
- `important` — direct: R6 · unclear: R5 (Mentoring or leading PMs)
- `preferred` — absent: R7 (Ledger / reconciliation systems)

R4 has a credible bridge, and R3 (`medium`) waits on an artifact.

## Evidence map

| # | Requirement | Priority | Fit | Confidence | Gap |
|---|---|---|---|---|---|
| R1 | UK work eligibility without sponsorship | hard_gate | direct | high | none |
| R2 | 5+ yrs PM, 2+ on payments/fintech | must_have | direct | high | none |
| R3 | Shipped APIs consumed by external developers | must_have | direct | medium | none |
| R4 | Regulatory exposure: PSD2 / open banking | must_have | adjacent | medium | transferability |
| R5 | Mentoring or leading PMs | important | unclear | low | discovery |
| R6 | Data fluency: SQL, experimentation | important | direct | high | presentation |
| R7 | Ledger / reconciliation systems experience | preferred | absent | none | capability |
"""


def ledger_fails(text: str) -> list[str]:
    return sorted(c["check"] for c in output_checks.check_fit_ledger(text)["checks"]
                  if c["verdict"] == "FAIL")


def test_fit_ledger() -> None:
    print("\nchecks: the fit ledger is an exact projection of the map")
    check("a correct ledger passes", ledger_fails(LEDGER_OK), [])
    check("a flipped fit fails", ledger_fails(LEDGER_OK.replace(
        "| must_have | adjacent | medium", "| must_have | unclear | medium")), ["ledger_fit"])
    check("a dropped last ID fails", ledger_fails(LEDGER_OK.replace(
        "- `preferred` — absent: R7 (Ledger / reconciliation systems)\n", "")), ["ledger_coverage"])
    check("a duplicated ID fails", "ledger_coverage" in ledger_fails(LEDGER_OK.replace(
        "direct: R2, R3 ·", "direct: R2, R3, R2 ·")), True)
    check("a wrong tier fails", ledger_fails(LEDGER_OK.replace(
        "| R6 | Data fluency: SQL, experimentation | important",
        "| R6 | Data fluency: SQL, experimentation | must_have")), ["ledger_tier"])
    check("a numeral in the ledger fails", "ledger_wording" in ledger_fails(LEDGER_OK.replace(
        "- `hard_gate` — direct: R1", "- `hard_gate` — direct: R1 (1 of 1)")), True)
    check("a quantifier in the ledger fails", "ledger_wording" in ledger_fails(LEDGER_OK.replace(
        "(Mentoring or leading PMs)", "(Mentoring or leading PMs, all of it)")), True)
    check("a band that disagrees with the map fails", ledger_fails(LEDGER_OK.replace(
        "R3 (`medium`) waits", "R3 (`high`) waits")), ["snapshot_band"])
    check("a band over no single row fails", ledger_fails(LEDGER_OK.replace(
        "R3 (`medium`) waits on an artifact", "confidence is `high` throughout")), ["snapshot_band"])
    severity = LEDGER_OK.replace("waits on an artifact.", "waits on an artifact; RR1 and RR2 are `low` severity.")
    check("a risk severity is not a confidence band", ledger_fails(severity), [])
    headless = LEDGER_OK.replace("## Decision snapshot", "# Should you apply?")
    band = [c for c in output_checks.check_fit_ledger(headless)["checks"] if c["check"] == "snapshot_band"]
    check("with no snapshot heading the band check fails as format, not judgement",
          [(c["verdict"], c["kind"]) for c in band], [("FAIL", "format")])
    probe = JU1_CANNED_LEDGER + "\n\n## Evidence map\n\n" + \
        "| # | Requirement | Priority | Fit | Confidence |\n|---|---|---|---|---|\n" + "\n".join(
            f"| {r} | {req} | {p} | {f} | {c} |" for r, req, p, f, c in (
                ("R1", "5+ years product analytics", "must_have", "direct", "medium"),
                ("R2", "Expert SQL", "must_have", "direct", "medium"),
                ("R3", "Experiment design at scale", "must_have", "direct", "medium"),
                ("R4", "Looker or similar BI tool", "must_have", "direct", "medium"),
                ("R5a", "Partner with product managers on roadmap decisions", "must_have", "direct", "medium"),
                ("R5b", "Partner with clinicians specifically", "must_have", "adjacent", "low"),
                ("R6", "Mentor two junior analysts", "important", "unclear", "low"),
                ("R7", "Strong written communication with non-technical stakeholders", "must_have", "direct", "medium"),
                ("R8", "Healthcare data experience (HIPAA)", "preferred", "adjacent", "low")))
    got = output_checks.check_fit_ledger(probe)["checks"]
    check("a bold-token ledger is still judged (canned probe): its bad parenthetical fails",
          [c["verdict"] for c in got if c["check"] == "ledger_parenthetical"], ["FAIL"])
    check("and the bold is reported as format",
          [(c["verdict"], c["kind"]) for c in got if c["check"] == "ledger_markup"], [("FAIL", "format")])
    check("the old prose form is unparseable, not passed",
          ledger_fails(LEDGER_OK.replace("**Fit ledger.**\n",
                                         "**Fit ledger:** five of seven are `direct`.\n\nx\n")),
          ["ledger_present"])


# --- 6c. Quotes ---

PROMPT = ("MY BACKGROUND: 6 years of product analytics at a meal-kit company. Built the "
          "company's Looker instance from scratch — 40+ governed dashboards. I write the "
          "monthly metrics memo the exec team reads.")


def snapshot(cell: str) -> str:
    return ("| # | Requirement | Evidence, verbatim | Confidence | Bridge |\n|---|---|---|---|---|\n"
            f"| F1 | BI | {cell} | high | — |\n\n"
            "| # | Question | Type | Provenance | Answer guidance | Rationale |\n|---|---|---|---|---|---|\n"
            "| B1 | Tell me about dashboards | DATA | [grounded] \"Built the company's Looker "
            "instance from scratch\" (your message) | Lead with it | F1 |\n")


def test_quotes() -> None:
    print("\nchecks: a quotation in a verbatim cell is a quotation of something")
    def fails(cell: str) -> list[str]:
        return [c["why"] for c in output_checks.check_quotes(snapshot(cell), PROMPT)["checks"]
                if c["verdict"] == "FAIL"]
    check("a verbatim quote passes, curly quotes and dashes unified",
          fails("“Built the company’s Looker instance from scratch – 40+ governed dashboards” "
                "(your message)"), [])
    check("a paraphrase in quotation marks fails",
          len(fails('"Built and governed the Looker estate" (your message)')), 1)
    check("each ellipsis fragment is checked, and a true pair passes",
          fails('"6 years of product analytics ... the monthly metrics memo" (your message)'), [])
    check("one invented fragment fails the span",
          len(fails('"6 years of product analytics … led the analytics guild" (your message)')), 1)
    check("a two-word quote is not checked", fails('"Looker instance" (your message)'), [])


# --- The legacy record, rebuilt from transcripts ---

def test_backfill() -> None:
    print("\nbackfill: a saved run is paired with its transcript by text, or not at all")
    def session(answer, query):
        return [{"type": "user", "parentUuid": None, "message": {"content": "prompt"}},
                {"type": "assistant", "parentUuid": "u", "message": {"content": [
                    {"type": "tool_use", "id": "w1", "name": "WebSearch", "input": {"query": query}}]}},
                {"type": "user", "parentUuid": "a", "message": {"content": [
                    {"type": "tool_result", "tool_use_id": "w1", "is_error": True,
                     "content": "Claude requested permissions to use WebSearch"}]}},
                {"type": "assistant", "parentUuid": "u", "message": {"content": [
                    {"type": "text", "text": answer}]}}]
    with tempfile.TemporaryDirectory() as tmp:
        projects = Path(tmp)
        room = projects / "-tmp-x-rooms-job-underwriter-1-aa11bb22"
        room.mkdir()
        (room / "s.jsonl").write_text("\n".join(json.dumps(e) for e in
                                                session("The answer.", "acme careers")))
        twin = projects / "-tmp-x-rooms-job-underwriter-1-cc33dd44"
        twin.mkdir()
        (twin / "s.jsonl").write_text("\n".join(json.dumps(e) for e in
                                                session("A twin answer.", "acme salary")))
        twin2 = projects / "-tmp-x-rooms-job-underwriter-1-ee55ff66"
        twin2.mkdir()
        (twin2 / "s.jsonl").write_text("\n".join(json.dumps(e) for e in
                                                 session("A twin answer.", "acme jobs")))
        pool = backfill_tools.candidates(projects, "job-underwriter", 1)
        meta = {"skill": "job-underwriter", "id": 1, "triggered_unprompted": True}
        got = backfill_tools.backfill_meta(
            meta, "The answer.\n\n----- file the response produced: x.md -----\nfile", pool)
        check("a unique match is reconstructed",
              [(e["query_or_url"], e["outcome"]) for e in got["research_log"]],
              [("acme careers", "refused")])
        check_true("with its provenance", got["research_log_provenance"]["matched_chars"] > 0)
        got = backfill_tools.backfill_meta(meta, "Nothing like it.", pool)
        check("no match is no_log, not an empty record", (got["research_log"], got.get("reason")),
              (None, "no_log"))
        got = backfill_tools.backfill_meta(meta, "A twin answer.", pool)
        check("two matches are no_log, never a guess", (got["research_log"], got.get("reason")),
              (None, "no_log"))
    meta = {"research_log": None}
    check_true("the grader is told a missing record is not a record of none",
               run_fixtures.observed_block(meta).startswith("Not recorded"))
    check_true("and an empty one is",
               run_fixtures.observed_block({"research_log": []}).startswith("Recorded: no search"))


def test_recurring() -> None:
    print("\nrecurring: verdicts pool only on identical expectation text; checks keep their own keys")
    def grade_file(d: Path, stem: str, sha, verdict: str) -> None:
        record = {"skill": "s", "id": 1, "verdicts": [{"n": 1, "why": "w", "verdict": verdict}]}
        if sha:
            record["expectation_sha256"] = {"1": sha}
        (d / f"{stem}.grade-1.json").write_text(json.dumps(record))
    def checks_file(d: Path, stem: str, status: str, verdict: str) -> None:
        (d / f"{stem}.checks.json").write_text(json.dumps({
            "skill": "s", "id": 1, "mode": "canned", "status": status,
            "checks": [{"check": "accept", "target": "2", "verdict": verdict, "why": "w"}]}))
    with tempfile.TemporaryDirectory() as tmp:
        sets = [Path(tmp) / name for name in ("a", "b", "c")]
        for d in sets:
            d.mkdir()
        grade_file(sets[0], "s-1.run0", "old", "FAIL")
        grade_file(sets[1], "s-1.run0", "new", "FAIL")
        grade_file(sets[2], "s-1.run0", None, "FAIL")
        grade_file(sets[0], "s-1.run1", None, "FAIL")
        checks_file(sets[0], "s-1.canned.run0", "fail", "FAIL")
        checks_file(sets[1], "s-1.canned.run0", "fail", "FAIL")
        checks_file(sets[2], "s-1.canned.run0", "harness-invalid", "FAIL")
        seen = recurring.scan(sets)
        check("a rewritten expectation is a different key",
              sorted(len(e["failed_sets"]) for k, e in seen.items() if k[3] == 1 and k[4] in ("old", "new")),
              [1, 1])
        check("hashless grade files still pool by position",
              len(seen[("s", 1, "denied", 1, None)]["failed_sets"]), 2)
        check("checks are keyed by check and target, invalid runs skipped",
              sorted(seen[("s", 1, "canned", ("chk", "accept", "2"), "check")]["failed_sets"]),
              ["a", "b"])


def main() -> int:
    for test in (test_routing_declines, test_cli_refusal, test_parse_stream,
                 test_research_server, test_rooms, test_stems, test_grade_parsing,
                 test_classification, test_missing_response,
                 test_declined_grade_prints_no_score, test_artifact_collection,
                 test_skill_installation, test_classify_room, test_execute_timeout,
                 test_execute_nudge, test_parse_accounting, test_check_accounting,
                 test_fit_ledger, test_quotes, test_backfill, test_recurring):
        test()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} harness test failure(s):")
        for line in FAILURES:
            print(f"  {line}")
        return 1
    print("All harness tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
