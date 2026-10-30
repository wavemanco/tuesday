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
import ledger_rules  # noqa: E402  (ci/, put on the path by output_checks)
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


def test_server_url_identity() -> None:
    print("\nresearch server: one URL identity with the checks")
    import importlib.util
    spec = importlib.util.spec_from_file_location("research_server_copy", SERVER)
    server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server)
    pairs = [("https://www.Kestrel.test/careers/", "kestrel.test/careers"),
             ("http://kestrel.test/careers#roles", "https://kestrel.test/careers"),
             ("https://kestrel.test/Careers", "https://kestrel.test/careers"),
             ("https://kestrel.test/careers?id=2", "https://kestrel.test/careers?id=1"),
             ("https://kestrel.test/careers", "https://kestrel.test/careers/eng"),
             ("https://kestrel.test", "https://kestrel.test/"),
             ("https://kestrel.test/a//", "https://kestrel.test/a")]
    check("the room and the checks treat every URL pair alike",
          [server.same_url(a, b) for a, b in pairs], [output_checks.same_url(a, b) for a, b in pairs])
    check_true("and the pairs exercise both answers",
               {output_checks.same_url(a, b) for a, b in pairs} == {True, False})


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
    '| Target | Status | What it would have moved |\n'
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
    '| Target | Ran | What it moved, or could not have |\n'
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
    '| Target | Ran | What it moved, or could not have |\n'
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
    check("its two 'Extra:' rows, bare `yes` after the numbered ones, are off-target rows",
          ([e["target"][:6] for e in got["extra"]], sum("Extra:" in p for _, p in got["format"])),
          (["Extra:", "Extra:"], 0))
    got = output_checks.parse_accounting(JU1_CANNED_PROBE)
    check("a numbered table with the target in column two is read, not absent (canned probe)",
          {n: r["label"] for n, r in got["rows"].items()}, {1: "yes", 2: "yes", 3: "n/a"})
    check_true("and a number in its own column is the same table, not a format violation",
               not any("not the first column" in p for _, p in got["format"]))
    moved = JU1_CANNED_PROBE.replace("| # | Target | Status | Reason |", "| Status | Target | # | Reason |")
    check_true("a table with its target moved further along is still a format violation",
               any("not the first column" in p for _, p in output_checks.parse_accounting(moved)["format"])
               or output_checks.parse_accounting(moved)["outcome"] != "checked")
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
    "canaries": [{"target": 1, "page": "https://kestrel.test/careers",
                  "text": "came from an experimentation-platform team"}],
}


def accounting(labels: dict, tally: str = "Research tier: L1 — searches 2 of 5, fetches 0 of 2",
               extra: str = "") -> str:
    rows = "\n".join(f"| {n}. target | {label} | why |" for n, label in labels.items())
    return f"{extra}\n\n{tally}\n\n| Target | Status | What it moved |\n|---|---|---|\n{rows}\n"


def entry(query, outcome="returned", kind="search", targets=(), urls=()):
    return {"tool": "mcp__web__search" if kind == "search" else "mcp__web__fetch", "kind": kind,
            "query_or_url": query, "outcome": outcome, "urls_returned": list(urls),
            "targets": list(targets)}


def test_check_accounting() -> None:
    print("\nchecks: each label is judged against the calls aimed at its target")
    two = [entry("Kestrel careers", targets=[1], urls=["https://kestrel.test/careers"]),
           entry("analyst salary", targets=[2])]
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

**Opportunity ledger.** Authority is asserted and not evidenced (RR1).

- **Hard gates:** none failed (R1 `direct`).
- **Severe red flags:** none found.

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

## Risk register

| # | Signal | Class | Severity | Status |
|---|---|---|---|---|
| RR1 | Authority asserted, not evidenced | unknown | — | unresolved |
| RR2 | Compensation unstated | risk_signal | medium | unresolved |
"""


# LEDGER_OK's map as the shared rule functions take it: {id: (priority, fit)}.
LEDGER_ROWS = {rid: (row["priority"], row["fit"]) for rid, row in output_checks.evidence_map(LEDGER_OK).items()}


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
    check("a severity written as a bare band word is read as a band, and fails (rule 5)",
          ledger_fails(severity), ["snapshot_band"])
    headless = LEDGER_OK.replace("## Decision snapshot", "# Should you apply?")
    band = [c for c in output_checks.check_fit_ledger(headless)["checks"] if c["check"] == "snapshot_band"]
    check("with no snapshot heading the bands are read around the ledger (denied probe)",
          [c["verdict"] for c in band], ["PASS"])
    check("and a wrong band there still fails", ledger_fails(headless.replace(
        "R3 (`medium`) waits", "R3 (`high`) waits")), ["snapshot_band"])
    check("\"every … but R4\" in the sentence after the ledger fails: the exception is exclusive", ledger_fails(LEDGER_OK.replace(
        "R4 has a credible bridge, and R3 (`medium`) waits on an artifact.",
        "Every must-have but R4 is `direct`.")), ["ledger_sentence", "snapshot_count"])
    check("\"the only rows below\" fails there too (canned probe)", ledger_fails(LEDGER_OK.replace(
        "R4 has a credible bridge, and R3 (`medium`) waits on an artifact.",
        "R4 and R5 are the only rows below `direct`.")), ["ledger_sentence", "snapshot_count"])
    check("a next slot directly after the ledger is no sentence to judge", ledger_fails(LEDGER_OK.replace(
        "R4 has a credible bridge, and R3 (`medium`) waits on an artifact.",
        "**Opportunity ledger.** RR1 is asserted and not evidenced.")), [])
    check("a parenthetical in the Requirement's own words, reordered, passes (denied probe)",
          ledger_fails(LEDGER_OK.replace("(Mentoring or leading PMs)", "(PMs, mentoring or leading)")), [])
    check("a parenthetical using words the Requirement lacks fails, as format",
          [(c["verdict"], c["kind"]) for c in output_checks.check_fit_ledger(
              LEDGER_OK.replace("(Mentoring or leading PMs)", "(people management)"))["checks"]
           if c["check"] == "ledger_parenthetical"], [("FAIL", "format")])
    check("a parenthetical of stop words alone names nothing, though it opens the Requirement, and fails: the "
          "ledger's naming rule is ledger_rules.names_requirement, as in CI and on the hard-gates line",
          ledger_fails(LEDGER_OK.replace("unclear: R5 (Mentoring or leading PMs)", "unclear: R5 (Or)").replace(
              "| R5 | Mentoring or leading PMs |", "| R5 | Or leading PMs |")), ["ledger_parenthetical"])
    check("a canary is a whole token: 143 is not inside 1430",
          (output_checks.canary_in("143", "a team of 1430"), output_checks.canary_in("143", "143 staff")),
          (False, True))
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
            "instance from scratch\" | Lead with it | F1 |\n")



def test_review_fixes() -> None:
    print("\nchecks: what the second review of the fixes found")
    canary = "It came from an experimentation-platform team."
    errored = [entry("Kestrel careers", "error", targets=[1]), entry("analyst salary", targets=[2])]
    got = output_checks.check_accounting(accounting({1: "yes", 2: "yes", 3: "n/a"}, extra=canary),
                                         RESEARCH, "canned", errored)
    check("`yes` on a target whose only call errored fails: an error returns nothing",
          verdict_of(got, "yes_has_call", 1), "FAIL")
    got = output_checks.check_accounting(accounting({1: "unavailable", 2: "yes", 3: "n/a"}),
                                         RESEARCH, "canned", errored)
    check("`unavailable` on a target whose only call errored passes",
          verdict_of(got, "unavailable_has_refusal", 1), "PASS")
    # The grader reads the same rule in each skill's accounting clause; a clause that
    # said "refused" alone gave the grader no label for this run (NEW-RV-C, RV14).
    clauses = [json.loads((Path(__file__).resolve().parent.parent / "skills" / skill / "evals" / "evals.json")
                          .read_text(encoding="utf-8"))["clauses"]["accounting"]
               for skill in ("job-underwriter", "mock-interview")]
    check("and the graders' accounting clauses say an errored call counts as refused, as this check does",
          [("refused or errored" in c, "returned a result" in c) for c in clauses], [(True, True)] * 2)
    mixed = [entry("Kestrel careers", targets=[1]), entry("Kestrel about", "refused", targets=[1]),
             entry("analyst salary", targets=[2])]
    got = output_checks.check_accounting(accounting({1: "unavailable", 2: "yes", 3: "n/a"}),
                                         RESEARCH, "canned", mixed)
    check("`unavailable` with one call returned and one refused fails",
          verdict_of(got, "unavailable_has_refusal", 1), "FAIL")

    linked = dict(RESEARCH, user_links=["https://example.org/folio"])
    with_link = [entry("Kestrel careers", targets=[1], urls=["https://kestrel.test/careers"]),
                 entry("analyst salary", targets=[2]), entry("https://example.org/folio", kind="fetch")]
    tally = "Research tier: L1 — searches 2 of 5, fetches 0 of 2; user links read 1"
    got = output_checks.check_accounting(accounting({1: "yes", 2: "yes", 3: "n/a"}, tally, canary),
                                         linked, "canned", with_link)
    check("a fetch of a declared user link is named on the tally line, not charged",
          (verdict_of(got, "tally_fetches"), verdict_of(got, "tally_user_links")), ("PASS", "PASS"))
    got = output_checks.check_accounting(accounting({1: "yes", 2: "yes", 3: "n/a"}, tally, canary),
                                         RESEARCH, "canned", with_link)
    check("a fetch the fixture declares no user link for is research, whatever the tally calls it",
          (verdict_of(got, "tally_fetches"), verdict_of(got, "tally_user_links")), ("FAIL", "FAIL"))

    keyed = dict(RESEARCH, canaries=[{"target": 1, "page": "https://kestrel.test/about",
                                      "text": "came from an experimentation-platform team"}])
    unseen = [entry("Kestrel careers", targets=[1]), entry("analyst salary", targets=[2])]
    got = output_checks.check_accounting(accounting({1: "yes", 2: "yes", 3: "n/a"}), keyed, "canned", unseen)
    check("a canary whose page the room never returned is not asked for",
          verdict_of(got, "canary", 1), None)
    shown = [dict(entry("Kestrel careers", targets=[1]), urls_returned=["https://kestrel.test/about"]),
             entry("analyst salary", targets=[2])]
    got = output_checks.check_accounting(accounting({1: "yes", 2: "yes", 3: "n/a"}), keyed, "canned", shown)
    check("a canary whose page was returned must surface", verdict_of(got, "canary", 1), "FAIL")
    got = output_checks.check_accounting(
        accounting({1: "yes", 2: "yes", 3: "n/a"}, extra="it came from an experimentation‑platform team"),
        keyed, "canned", shown)
    check("a canary written with a non-breaking hyphen still counts", verdict_of(got, "canary", 1), "PASS")

    gated = LEDGER_OK.replace("- **Hard gates:** none failed (R1 `direct`).", "- **Hard gates:** none failed.")
    check("a hard-gates line that names no gate row fails", "gates_line" in ledger_fails(gated), True)
    check("one that names every gate row passes", "gates_line" in ledger_fails(LEDGER_OK), False)

    pasted = "THE JD: 'Own the complaints process end to end.' ME: I built the complaints spreadsheet."

    def snap(cell):
        return ("| # | Requirement (source) | Evidence, verbatim | Confidence | Bridge |\n|---|---|---|---|---|\n"
                f"| F1 | \"Own the complaints process end to end\" — JD | {cell} | high | — |\n\n"
                "| # | Question | Type | Provenance | Answer guidance | Rationale |\n|---|---|---|---|---|---|\n"
                "| A1 | q | EXP | [grounded] | g | F1 |\n")

    def quote_fails(cell, own=None, prompt=pasted):
        return sorted(c["check"] for c in output_checks.check_quotes(snap(cell), prompt, (), own)["checks"]
                      if c["verdict"] == "FAIL")
    check("`none given` is a lawful evidence cell", quote_fails("`none given`"), [])
    check("an unquoted summary in the evidence column fails", quote_fails("Built a complaints tracker"),
          ["evidence_form"])
    check("a quote with a summary appended fails",
          quote_fails('"I built the complaints spreadsheet" (your message), and ran the team'), ["evidence_form"])
    got = output_checks.check_quotes(snap('"Own the complaints process end to end" — your message'),
                                     pasted, (), None)
    check("with no candidate_text the evidence column is unchecked, never checked against the prompt",
          ([c["verdict"] for c in got["checks"] if c["check"] == "quotes" and c["target"] == "fit_snapshot"],
           "quotes" in got["unchecked"]), ([], True))
    check("the JD's words quoted as the candidate's fail against what the candidate gave",
          quote_fails('"Own the complaints process end to end" — your message',
                      ["I built the complaints spreadsheet."]), ["quotes"])
    check("a requirement in quotation marks that nothing supplied fails",
          quote_fails('"I built the complaints spreadsheet" — your message',
                      prompt="ME: I built the complaints spreadsheet."), ["quotes"])


def test_quotes() -> None:
    print("\nchecks: a quotation in a verbatim cell is a quotation of something")
    own = [PROMPT.split(": ", 1)[1]]

    def fails(cell: str) -> list[str]:
        return [c["why"] for c in output_checks.check_quotes(snapshot(cell), PROMPT, (), own)["checks"]
                if c["verdict"] == "FAIL"]
    check("a verbatim quote passes, curly quotes and dashes unified",
          fails("“Built the company’s Looker instance from scratch – 40+ governed dashboards” "
                "— your message"), [])
    check("a paraphrase in quotation marks fails",
          len(fails('"Built and governed the Looker estate" — your message; '
                    '"Built the company\'s Looker instance from scratch" — your message')), 1)
    check("each ellipsis fragment is checked, and a true pair passes",
          fails('"6 years of product analytics ... the monthly metrics memo" — your message; '
                '"Built the company\'s Looker instance from scratch" — your message'), [])
    check("one invented fragment fails the span",
          len(fails('"6 years of product analytics … led the analytics guild" — your message; '
                    '"Built the company\'s Looker instance from scratch" — your message')), 1)
    check("a two-word quote in the evidence column is checked too, and a true one passes",
          fails('"Looker instance" — your message; '
                '"Built the company\'s Looker instance from scratch" — your message'), [])


def test_evidence_cells() -> None:
    print("\nchecks: an evidence cell is `none given` or quotes with their origins, and nothing else")
    pasted = "THE JD: 'Own the complaints process end to end.' ME: I built the complaints spreadsheet."
    own = ["I built the complaints spreadsheet."]

    def snap(cell, provenance="[grounded]"):
        return ("| # | Requirement (source) | Evidence, verbatim | Confidence | Bridge |\n|---|---|---|---|---|\n"
                f"| F1 | \"Own the complaints process end to end\" — JD | {cell} | high | — |\n\n"
                "| # | Question | Type | Provenance | Answer guidance | Rationale |\n|---|---|---|---|---|---|\n"
                f"| A1 | q | EXP | {provenance} | g | F1 |\n")

    def fails(cell, candidate=own, provenance="[grounded]", prompt=pasted):
        return sorted(c["check"] for c in output_checks.check_quotes(
            snap(cell, provenance), prompt, (), candidate)["checks"] if c["verdict"] == "FAIL")
    quote = '"I built the complaints spreadsheet"'
    check("a summary after the dash is not an origin",
          fails(quote + " — your message, i.e. owned the complaints process end to end"), ["evidence_form"])
    check("a summary in parentheses is not an origin",
          fails(quote + " (owned complaints end to end for the org)"), ["evidence_form"])
    check("free text after a dash fails", fails(quote + " - and then ran the whole team"), ["evidence_form"])
    check("a quote with no origin fails", fails(quote), ["evidence_form"])
    check("an origin outside the template's set fails", fails(quote + " — LinkedIn"), ["evidence_form"])
    check("an origin in parentheses rather than after a dash fails (the template: 'followed by a dash')",
          fails(quote + " (your message)"), ["evidence_form"])
    check("one origin for two quotes fails: each quote is followed by its own",
          fails(quote + ' and "complaints spreadsheet" — your message'), ["evidence_form"])
    check("words between quotes fail", fails(quote + " and led the team — your message"), ["evidence_form"])
    check("`none given` with words after it fails", fails("none given, but led a team"), ["evidence_form"])
    check("two quotes, each with its origin, pass",
          fails(quote + ' — your message; "complaints spreadsheet" — your CV'), [])
    check("two quotes separated by a full stop, each with its origin, pass (HN5)",
          fails(quote + ' — your message. "complaints spreadsheet" — your CV.'), [])
    check("but words after the full stop still fail", fails(quote + " — your message. and led the team"),
          ["evidence_form"])
    check("and a full stop then a quote with no origin fails",
          fails(quote + ' — your message. "complaints spreadsheet"'), ["evidence_form"])
    check("a dossier row is an origin", fails(quote + " — dossier R3"), [])
    check("`None given.` with its period passes", fails("None given."), [])
    check("`none given` in backticks passes", fails("`none given`"), [])
    check("a fabricated two-word quote fails", fails('"owned quota" — your message'), ["quotes"])
    check("a fabricated one-word quote fails", fails('"quota" — your message'), ["quotes"])
    check("a genuine two-word quote passes", fails('"complaints spreadsheet" — your message'), [])
    check("a quote is matched on word boundaries: \"built the complaint\" is not in \"…complaints\"",
          fails('"built the complaint" — your message'), ["quotes"])

    mi3 = fixture("mock-interview", 3)
    worksheet = ("| # | Requirement (source) | Evidence, verbatim | Confidence | Bridge |\n|---|---|---|---|---|\n"
                 "| F1 | Cross-functional operations planning | {cell} | none | Answer slot |\n\n"
                 "| # | Question | Type | Provenance | Answer guidance | Rationale |\n|---|---|---|---|---|---|\n"
                 "| A1 | q | EXP | [generic] | g | F1 |\n")

    def mi3_quotes(cell, candidate):
        return output_checks.check_quotes(worksheet.format(cell=cell), mi3["prompt"], (), candidate)

    def mi3_fails(cell):
        return sorted(c["check"] for c in mi3_quotes(cell, mi3["candidate_text"])["checks"] if c["verdict"] == "FAIL")
    check("mi 3 (candidate_text []): a prompt sentence quoted as the candidate's fails",
          mi3_fails('"final-round interview at Stripe" — your message'), ["quotes"])
    check("mi 3: the worksheet's `none given` passes, with no JD and no CV", mi3_fails("none given"), [])
    got = mi3_quotes('"final-round interview at Stripe" — your message', None)
    check("a fixture with no candidate_text is reported unchecked, not passed",
          ("quotes" in got["unchecked"],
           [c["verdict"] for c in got["checks"] if c["check"] == "quotes" and c["target"] == "fit_snapshot"]),
          (True, []))
    from fixture_clauses import load_cases
    undeclared = [f"{path.parent.parent.name} {case['id']}"
                  for path in sorted((Path(__file__).resolve().parent.parent / "skills").glob("*/evals/evals.json"))
                  for case in load_cases(path)
                  if "quotes" in case.get("checks", []) and not isinstance(case.get("candidate_text"), list)]
    check("every fixture with the quotes check declares candidate_text as a list (D5)", undeclared, [])
    check("and a run of it is uncheckable, not ok", output_checks.run_checks(
        {"checks": ["quotes"], "prompt": mi3["prompt"]}, "denied",
        worksheet.format(cell='"final-round interview at Stripe" — your message'), None)["status"], "uncheckable")


def test_provenance_pool() -> None:
    print("\nchecks: Provenance quotes the candidate, as the fit snapshot does (mi 4)")
    mi4 = fixture("mock-interview", 4)
    evidence = ('"Wrote the internal integration playbook her team uses" — dossier; '
                '"Ran quarterly roadmap-input sessions feeding client evidence to product" — dossier')

    def pack(provenance):
        return ("| # | Requirement (source) | Evidence, verbatim | Confidence | Bridge |\n|---|---|---|---|---|\n"
                f"| F1 | \"Shipped API or platform products\" — dossier R2 | {evidence} | medium | — |\n\n"
                "| # | Question | Type | Provenance | Answer guidance | Rationale |\n|---|---|---|---|---|---|\n"
                f"| A1 | q | EXP | [grounded] \"{provenance}\" | g | F1 |\n")

    def banks(provenance):
        got = output_checks.run_checks(mi4, "denied", pack(provenance), None)
        return [c["verdict"] for c in got["checks"] if c["check"] == "quotes" and c["target"] == "banks"]
    check("the dossier's header prose in Provenance fails",
          banks("Strong adjacent fit from seven years of integration leadership"), ["FAIL"])
    check("a prohibited_claims string in Provenance fails",
          banks("Having held a product manager title or role"), ["FAIL"])
    check("a JD responsibility in Provenance fails",
          banks("Own the roadmap for the partner-facing API platform"), ["FAIL"])
    check("a verified claim cut before its confidence note, as the evidence column quotes it, passes",
          banks("Wrote the internal integration playbook her team uses"), ["PASS"])
    banks_only = pack("Wrote the internal integration playbook her team uses").split("\n\n", 1)[1]
    got = output_checks.check_quotes(banks_only, mi4["prompt"], (), mi4["candidate_text"])["checks"]
    check("with no fit snapshot table, that is one format failure, not one per Provenance cell",
          sorted((c["target"], c["verdict"], c["kind"]) for c in got if c["check"] == "quotes"),
          [("banks", "PASS", "judgement"), ("fit_snapshot", "FAIL", "format")])
    check("a candidate sentence the fit snapshot does not quote fails: Provenance quotes it as it appears there",
          banks("Led 30+ end-to-end client integrations of the vendor's REST APIs"), ["FAIL"])

    # A plain acknowledgment's source may be a dossier item named by its field
    # (question-rubric.md, "A plain acknowledgment"): the cell names the field
    # anywhere, and a quotation that is one whole item of a field it names is that
    # item; any other quotation is the candidate's (HN1; round 5 N2).
    def named(provenance):
        got = output_checks.run_checks(mi4, "denied", pack("x").replace('[grounded] "x"', provenance), None)
        return [c["verdict"] for c in got["checks"] if c["check"] == "quotes" and c["target"] == "banks"]
    check("a prohibited_claims item quoted after its field's name passes",
          named('[grounded] dossier prohibited_claims: "Having owned a product roadmap"'), ["PASS"])
    check("an acknowledge_gap area quoted after its field's name passes",
          named('[grounded] `acknowledge_gap` "Owning a roadmap and prioritization authority (R1 sub-claim)"'),
          ["PASS"])
    check("the same items named without quotation marks pass",
          named("[grounded] dossier prohibited_claims item, Having owned a product roadmap"), ["PASS"])
    check("text that is no item of the named field fails",
          named('[grounded] prohibited_claims: "Owned the roadmap for the partner API"'), ["FAIL"])
    check("a fragment of an item fails: the item is quoted whole",
          named('[grounded] prohibited_claims: "owned a product roadmap"'), ["FAIL"])
    check("one field's item under another field's name fails",
          named('[grounded] acknowledge_gap: "Having owned a product roadmap"'), ["FAIL"])
    check("a bridge area under acknowledge_gap fails: only acknowledge_gap areas are that field's",
          named('[grounded] acknowledge_gap: "3+ years product management experience (R1)"'), ["FAIL"])
    check("a field's name with no dossier in the request fails",
          [c["verdict"] for c in output_checks.check_quotes(
              pack("x").replace('[grounded] "x"', '[grounded] prohibited_claims: "Having owned a product roadmap"'),
              "no dossier here", (), mi4["candidate_text"])["checks"]
           if c["check"] == "quotes" and c["target"] == "banks"], ["FAIL"])
    check("two whole items after one naming of their field pass",
          named('[grounded] prohibited_claims: "Having owned a product roadmap", "Having held a product '
                'manager title or role"'), ["PASS"])
    for form in ('[grounded] dossier prohibited_claims ("Having owned a product roadmap")',
                 '[grounded] "Having owned a product roadmap" (dossier prohibited_claims)',
                 '[grounded] dossier prohibited_claims items: "Having owned a product roadmap"; "Having held a '
                 'product manager title or role"',
                 '[grounded] a dossier `prohibited_claim`: "Having owned a product roadmap"',
                 '[grounded] dossier acknowledge_gap area, R1: "Owning a roadmap and prioritization authority '
                 '(R1 sub-claim)"'):
        check(f"the field named anywhere in the cell, the item whole, passes: {form!r}", named(form), ["PASS"])
    check("a cell that names only acknowledge_gap cannot cite a prohibited_claims item, wherever it sits",
          named('[grounded] acknowledge_gap area, as the dossier frames it; see "Having owned a product roadmap"'),
          ["FAIL"])
    check("a field's name inside a quotation names nothing: both quotations are read as the candidate's",
          named('[grounded] "prohibited_claims" and "Having owned a product roadmap"'), ["FAIL", "FAIL"])
    check("a candidate quotation beside a field's item is still checked as the candidate's",
          named('[grounded] prohibited_claims: "Having owned a product roadmap"; "Led the roadmap for the '
                'partner API"'), ["FAIL"])


GATED_MAP = """
## Evidence map

| # | Requirement | Priority | Fit | Confidence |
|---|---|---|---|---|
| R1 | UK work eligibility without sponsorship | hard_gate | direct | high |
| R2 | On-site five days a week | hard_gate | {r2} | high |
| R3 | Base salary at or above £95k | hard_gate | {r3} | low |
| R4 | Shipped APIs consumed by external developers | must_have | direct | medium |

## Risk register

| # | Signal | Class | Severity | Status |
|---|---|---|---|---|
| RR1 | Office attendance stated as five days | risk_signal | {rr1} | unresolved |
| RR2 | Compensation unstated | risk_signal | medium | unresolved |
"""


def gated(gates="- **Hard gates:** failed: R2 (On-site five days a week); unconfirmed: R3 (Base salary at or above "
                "£95k); met: R1 `direct`.",
          flags="- **Severe red flags:** RR1 (`severity: high`).", status="No. Status: `no_go`.",
          after="R3 waits on the band.", r2="hard_gate_fail", r3="unclear", rr1="high", tail="") -> str:
    ledger = {("hard_gate_fail", "unclear"): "- `hard_gate` — direct: R1 · unclear: R3 (Base salary at or above "
                                             "£95k) · hard_gate_fail: R2 (On-site five days a week)",
              ("direct", "unclear"): "- `hard_gate` — direct: R1, R2 · unclear: R3 (Base salary at or above £95k)",
              ("direct", "direct"): "- `hard_gate` — direct: R1, R2, R3"}[(r2, r3)]
    return (f"## Decision snapshot\n\n**{status}**\n\n**Fit ledger.**\n\n{ledger}\n"
            f"- `must_have` — direct: R4\n\n{after}\n\n**Opportunity ledger.** RR1 reads the office terms.\n\n"
            f"{gates}\n{flags}\n" + GATED_MAP.format(r2=r2, r3=r3, rr1=rr1) + tail)


def test_gates_line() -> None:
    print("\nchecks: the hard-gates line is the slot, and names every gate row (D3)")
    # Round 5 FX-N4: a Requirement's own words may hold a parenthesis ("Fully remote
    # (UK)"), and the fit ledger and the hard-gates line read them with one item
    # grammar (ledger_rules.ITEM_WORDS), so a name one accepts the other accepts.
    def slot(line: str) -> str:
        return f"## Decision snapshot\n\n- **Hard gates:** {line}\n"
    remote = {"R6": {"priority": "hard_gate", "fit": "unclear", "requirement": "Fully remote (UK)"}}
    check("an unconfirmed gate named in Requirement words that hold a parenthesis passes",
          ledger_rules.gates_line_problems(slot(
              "none failed; unconfirmed: R6 (Fully remote (UK)); candidate constraints not given — checks against "
              "them unknown"), remote, True), [])
    check("a failed gate named so passes",
          ledger_rules.gates_line_problems(slot("failed: R6 (Remote (US) or our Denver office)"), {
              "R6": {"priority": "hard_gate", "fit": "hard_gate_fail",
                     "requirement": "Remote (US) or our Denver office"}}, False), [])
    check("words its Requirement does not use still fail, parenthesis or not",
          [k for k, _ in ledger_rules.gates_line_problems(slot(
              "none failed; unconfirmed: R6 (Fully remote (UK) — Leeds office)"), remote, False)], ["form"])
    nested = output_checks.parse_fit_ledger("**Fit ledger.**\n\n- `hard_gate` — unclear: R6 (Fully remote (UK))\n")
    check("and the fit ledger reads the same item the same way",
          (nested["outcome"], nested["lines"][0]["groups"][0]["items"] if nested["lines"] else None),
          ("checked", [{"id": "R6", "note": "Fully remote (UK)"}]))
    check("failed, unconfirmed and met rows, each in its clause, pass", ledger_fails(gated()), [])
    check("a met gate row left out beside a failed one fails", ledger_fails(gated(
        gates="- **Hard gates:** failed: R2 (On-site five days a week); unconfirmed: R3 (Base salary at or above "
              "£95k).")), ["gates_line"])
    check("a failed row filed as met fails", ledger_fails(gated(
        gates="- **Hard gates:** unconfirmed: R3 (Base salary at or above £95k); met: R1 `direct`, R2 `direct`.")),
        ["gates_line"])
    check("\"none failed\" while a gate row failed fails", ledger_fails(gated(
        gates="- **Hard gates:** none failed (R1 `direct`, R2 `direct`); unconfirmed: R3 (Base salary at or above "
              "£95k).")), ["gates_line"])
    check("\"hard gates\" in the status line is not the slot: the slot below it is read", ledger_fails(gated(
        status="No — the hard gates fail. Status: `no_go`.")), [])
    check("a decoy naming the right rows does not stand in for a wrong slot", ledger_fails(gated(
        status="No — the hard gates are R1, R2 and R3. Status: `no_go`.",
        gates="- **Hard gates:** failed: R2 (On-site five days a week).")), ["gates_line"])
    check("no slot fails as format, and the judgement is left unchecked",
          ([(c["check"], c["verdict"], c["kind"]) for c in output_checks.check_fit_ledger(gated(gates=""))["checks"]
            if c["check"].startswith("gates")],
           "gates_line" in output_checks.check_fit_ledger(gated(gates=""))["unchecked"]),
          ([("gates_form", "FAIL", "format")], True))
    check("two slots fail as format", ledger_fails(gated(gates=gated.__defaults__[0] + "\n" + gated.__defaults__[0])),
          ["gates_form"])
    check("a plain 'Hard gates:' label is the slot", ledger_fails(gated(
        gates="Hard gates: failed: R2 (On-site five days a week); unconfirmed: R3 (Base salary at or above "
              "£95k); met: R1 `direct`.")), [])
    check("none failed, with met rows in its parentheses and an unconfirmed row, passes", ledger_fails(gated(
        r2="direct", status="Yes. Status: `conditional_go`.",
        gates="- **Hard gates:** none failed (R1 `direct`, R2 `direct`); unconfirmed: R3 (Base salary at or "
              "above £95k).")), [])
    check("an unconfirmed row without its Requirement's words fails as format", ledger_fails(gated(
        gates="- **Hard gates:** failed: R2 (On-site five days a week); unconfirmed: R3; met: R1 `direct`.")),
        ["gates_form"])
    check("a met row given the wrong fit fails", ledger_fails(gated(
        r2="direct", r3="direct", status="Yes. Status: `go`.",
        gates="- **Hard gates:** none failed (R1 `direct`, R2 `adjacent`, R3 `direct`).")), ["gates_line"])
    envelope = '\n```json\n{"sections": {"candidate_constraints": {"status": "unknown", "items": []}}}\n```\n'
    check("constraints not given: a line without the closing clause fails", ledger_fails(gated(tail=envelope)),
          ["gates_line"])
    check("and one ending with it passes", ledger_fails(gated(
        tail=envelope, gates="- **Hard gates:** failed: R2 (On-site five days a week); unconfirmed: R3 (Base salary "
                             "at or above £95k); met: R1 `direct`; candidate constraints not given — checks against "
                             "them unknown.")), [])
    flagged = ("- **Hard gates:** failed: R2 (On-site five days a week); unconfirmed: R3 (Base salary at or above "
               "£95k); met: R1 `direct`; candidate constraints not given — checks against them unknown.")

    def gate_verdict(text, declared):
        return verdict_of(output_checks.check_fit_ledger(text, declared), "gates_line")
    check("a fixture declaring constraints unknown: the line without the clause fails, with it passes",
          (gate_verdict(gated(), "unknown"), gate_verdict(gated(gates=flagged), "unknown")), ("FAIL", "PASS"))
    check("a fixture declaring constraints known: the clause fails, its absence passes",
          (gate_verdict(gated(gates=flagged), "known"), gate_verdict(gated(), "known")), ("FAIL", "PASS"))
    check("the fixture's declaration settles it over the response's own envelope",
          gate_verdict(gated(tail=envelope), "known"), "PASS")
    check("run_checks hands the fixture's declaration to the ledger check",
          verdict_of(output_checks.run_checks({"checks": ["fit_ledger"], "candidate_constraints": "unknown"},
                                              "denied", gated(), None), "gates_line"), "FAIL")
    # A fixture's candidate_constraints is the only source of truth for a fixture
    # (NP-8): missing or misspelt, it is a fixture error, and the response's own
    # envelope never decides.
    known_env = '\n```json\n{"sections": {"candidate_constraints": {"status": "known", "items": []}}}\n```\n'
    for case in ({"checks": ["fit_ledger"]}, {"checks": ["fit_ledger"], "candidate_constraints": "Unknown"}):
        got = output_checks.run_checks(case, "denied", gated(tail=known_env), None)
        check(f"a fit_ledger fixture whose candidate_constraints is {case.get('candidate_constraints')!r} fails as a "
              f"fixture error, and its envelope does not judge the closing clause",
              (verdict_of(got, "candidate_constraints"),
               next((c["kind"] for c in got["checks"] if c["check"] == "candidate_constraints"), None),
               got["status"], any("not judged" in i for i in got["info"])), ("FAIL", "fixture", "fail", True))
    check("a fixture declaring it exactly raises no fixture error", verdict_of(output_checks.run_checks(
        {"checks": ["fit_ledger"], "candidate_constraints": "known"}, "denied", gated(), None),
        "candidate_constraints"), None)
    # decision.summary is read with map_claim, the one count reader CI, snapshot_count
    # and the sentence after the ledger use (NP-6; round 5 N4), which reads a ratio as
    # the comment above ledger_rules.MAP_WORDS says (round 6 C5-1).
    def summary(text):
        return gated(tail='\n```json\n{"sections": {"decision": {"status": "no_go", "summary": '
                          + json.dumps(text) + '}}}\n```\n')
    check("a summary that counts the map fails summary_count",
          verdict_of(output_checks.check_fit_ledger(summary("Four of the seven must-haves are direct.")),
                     "summary_count"), "FAIL")
    check("a summary that names rows passes",
          verdict_of(output_checks.check_fit_ledger(summary("R2 fails the on-site gate; R3 waits on the band.")),
                     "summary_count"), "PASS")
    for text in ("Fit: 4 of 7 met.", "Conditional go: 4/7 direct.", "Go: four out of seven met.",
                 "Conditional go: R8 is the open gate; no other gate is in doubt.",
                 # round 6 C5-1: a ratio ending its clause in a predicate no list once held
                 "conditional_go: 5 of 7 covered; R4 is the stretch.", "Go: 6 of 7 satisfied, R4 open.",
                 "Six of nine look solid.", "Fit: 5/7 strong.",
                 # round 6 N1: a singular gate or "direct" before an unlisted word
                 "Conditional go: every gate checks out.", "Go: two direct hits, R2 and R3."):
        check(f"a summary that counts the map fails summary_count: {text!r}",
              verdict_of(output_checks.check_fit_ledger(summary(text)), "summary_count"), "FAIL")
    for text in ("Conditional go: the 24/7 on-call rota (RR2) is unverified.",
                 "Pass: the role is one of two openings and pay is withheld (RR4).",
                 "Go: the band covers 3 of 5 years of experience (RR3).",
                 # round 6 C5-1: the candidate's own figures and a date
                 "Go: he ranked 1 of 40 in the cohort (RR1).", "Go: the start date 3/15 is fixed (RR3)."):
        check(f"a ratio that counts something else passes summary_count, as it passes snapshot_count: {text!r}",
              (verdict_of(output_checks.check_fit_ledger(summary(text)), "summary_count"),
               ledger_rules.map_claim(text)), ("PASS", None))
    got = output_checks.check_fit_ledger(gated())
    check("with no JSON envelope summary_count is unchecked, not passed",
          (verdict_of(got, "summary_count"), "summary_count" in got["unchecked"]), (None, True))
    for case_id, status in ((1, "unknown"), (2, "unknown"), (3, "known"), (4, "unknown"), (5, "unknown")):
        case = fixture("job-underwriter", case_id)
        clause = "the line must end with its 'candidate constraints not given' clause" if status == "unknown" \
            else "must not carry the 'candidate constraints not given' clause"
        check_true(f"job-underwriter {case_id}: declares constraints {status}, and its hard-gates expectation "
                   f"says so", case.get("candidate_constraints") == status
                   and any(clause in e for e in case["expectations"] if "'- **Hard gates:** …'" in e))
    nogate = LEDGER_OK.replace("| hard_gate | direct | high |", "| must_have | direct | high |").replace(
        "- `hard_gate` — direct: R1\n- `must_have` — direct: R2, R3", "- `must_have` — direct: R1, R2, R3")
    check("with no gate rows, \"none stated\" passes", ledger_fails(nogate.replace(
        "none failed (R1 `direct`).", "none stated.")), [])
    check("with no gate rows, a line naming a row fails", ledger_fails(nogate), ["gates_line"])
    # The slot is in every snapshot, gate rows or not (amended D3, rule 4).
    slotless = nogate.replace("- **Hard gates:** none failed (R1 `direct`).\n", "")
    for declared in ("unknown", "known"):
        got = output_checks.check_fit_ledger(slotless, declared)
        check(f"with no gate rows and constraints {declared}, a snapshot with no slot fails as format",
              ([(c["check"], c["verdict"], c["kind"]) for c in got["checks"] if c["check"].startswith("gates")],
               "gates_line" in got["unchecked"]), ([("gates_form", "FAIL", "format")], True))
    stated = nogate.replace("none failed (R1 `direct`).", "none stated.")
    check("with no gate rows and constraints unknown, \"none stated\" without the closing clause fails",
          verdict_of(output_checks.check_fit_ledger(stated, "unknown"), "gates_line"), "FAIL")
    check("and with it passes", verdict_of(output_checks.check_fit_ledger(stated.replace(
        "none stated.", "none stated; candidate constraints not given — checks against them unknown."), "unknown"),
        "gates_line"), "PASS")
    # A failed row carries its Requirement's own words in parentheses, as an
    # unconfirmed one does; the conflict belongs in what would change this (P1).
    for line, why in (("failed: R2; unconfirmed: R3 (Base salary at or above £95k); met: R1 `direct`.",
                       "a failed row with no parentheses"),
                      ("failed: R2 (on-site Austin 5 days vs remote-only); unconfirmed: R3 (Base salary at or above "
                       "£95k); met: R1 `direct`.", "a failed row whose parentheses state the conflict"),
                      ("failed: R2 (`hard_gate_fail`); unconfirmed: R3 (Base salary at or above £95k); met: R1 "
                       "`direct`.", "a failed row carrying only its fit")):
        check(f"{why} fails as format", ledger_fails(gated(gates="- **Hard gates:** " + line)), ["gates_form"])
    check("a failed row in a few of its Requirement's own words passes", ledger_fails(gated(
        gates="- **Hard gates:** failed: R2 (On-site five days); unconfirmed: R3 (Base salary at or above £95k); "
              "met: R1 `direct`.")), [])
    # A gate is met, not established, or failed (evidence-model.md): a gate row at
    # `adjacent` or `absent` is a map error the line would file as met, however
    # consistently the map, the ledger and the line agree on it.
    met_go = dict(r2="direct", r3="direct", status="Yes. Status: `go`.")
    for fit in ("adjacent", "absent"):
        off = gated(**met_go, gates=f"- **Hard gates:** none failed (R1 `direct`, R2 `{fit}`, R3 `direct`).").replace(
            "| R2 | On-site five days a week | hard_gate | direct |", f"| R2 | On-site five days a week | hard_gate | {fit} |"
        ).replace("- `hard_gate` — direct: R1, R2, R3",
                  f"- `hard_gate` — direct: R1, R3 · {fit}: R2 (On-site five days a week)")
        check(f"a gate row at `{fit}`, agreed by map, ledger and line, fails", ledger_fails(off), ["gates_line"])
        check("and the finding names the gate rule", "R2 is a hard_gate row at" in next(
            c["why"] for c in output_checks.check_fit_ledger(off)["checks"] if c["check"] == "gates_line"), True)
    off_gate = gated(**met_go, gates="- **Hard gates:** none failed (R1 `direct`, R2 `direct`, R3 `direct`).").replace(
        "| R4 | Shipped APIs consumed by external developers | must_have | direct |",
        "| R4 | Shipped APIs consumed by external developers | must_have | hard_gate_fail |").replace(
        "- `must_have` — direct: R4", "- `must_have` — hard_gate_fail: R4 (Shipped APIs)")
    check("hard_gate_fail on a must_have row fails: only a gate row fails as a gate",
          ledger_fails(off_gate), ["gates_line"])


def test_severity() -> None:
    print("\nchecks: a severity is the register's, and the severe red flags are its high entries (rule 5)")
    check("RR1 (`severity: high`) over a high entry passes", ledger_fails(gated()), [])
    check("RR1 (`high`) is a band, not a severity, and fails",
          "snapshot_band" in ledger_fails(gated(flags="- **Severe red flags:** RR1 (`high`).")), True)
    check("RR2 (`severity: high`) over a medium entry fails", "severity" in ledger_fails(gated(
        flags="- **Severe red flags:** RR1 (`severity: high`), RR2 (`severity: high`).")), True)
    check("an entry the register does not have fails", "severity" in ledger_fails(gated(
        flags="- **Severe red flags:** RR1 (`severity: high`), RR9 (`severity: high`).")), True)
    check("\"none found\" over a high entry fails", ledger_fails(gated(flags="- **Severe red flags:** none found.")),
          ["severity"])
    check("\"none found\" with no high entry passes",
          ledger_fails(gated(rr1="medium", flags="- **Severe red flags:** none found.")), [])
    check("a high entry named without its full token fails as format",
          ledger_fails(gated(flags="- **Severe red flags:** RR1.")), ["severity_form"])
    check("a severity in the opportunity ledger is checked too", "severity" in ledger_fails(gated(
        after="R3 waits on the band (RR2 (`severity: low`)).")), True)


def test_shared_ledger_rules() -> None:
    print("\nchecks: the harness and CI read the snapshot with the same rule functions")
    import ledger_rules
    rule = ledger_rules.rule_quantifiers((Path(__file__).resolve().parent.parent / "skills" / "job-underwriter" /
                                          "references" / "evidence-model.md").read_text(encoding="utf-8"))
    check("evidence-model.md's quantifier lists are found", bool(rule), True)
    check("and every quantifier in them is in the shared set", sorted(set(rule) - set(ledger_rules.QUANTIFIERS)), [])
    model = (Path(__file__).resolve().parent.parent / "skills" / "job-underwriter" / "references" /
             "evidence-model.md").read_text(encoding="utf-8")
    check("and the shared set sorts them as the rule does: inclusive, exclusive, after the ledger only",
          ledger_rules.rule_quantifier_scopes(model),
          (list(ledger_rules.INCLUSIVE), list(ledger_rules.EXCLUSIVE), list(ledger_rules.AFTER_LEDGER_ONLY)))
    check("the harness uses the module CI imports", output_checks.ledger_rules is ledger_rules, True)
    # The sentence after the ledger is read twice: by rule 2's own check, which reads
    # every word of the lists there as about the map, and as snapshot prose, which
    # reads a list word as about the map with a map word within four words. Both
    # hold it to the one rule (evidence-model.md, "The row is the unit"): a set it
    # names passes, an unnamed or inexact one and an exclusive word fail.
    for sentence, also in (("No `must_have` row sits below adjacent but R4.", True),
                           ("R4 is the gap; no other row is.", True),
                           ("R4 and R5 are the only rows below `direct`.", True),
                           ("R4 and R5 sit below `direct`; none is a gate.", False),
                           ("Both of them sit below `direct`.", True)):
        check(f"after the ledger, {sentence!r} fails", ledger_fails(LEDGER_OK.replace(
            "R4 has a credible bridge, and R3 (`medium`) waits on an artifact.", sentence)),
            ["ledger_sentence", "snapshot_count"] if also else ["ledger_sentence"])
    for sentence in ("Both R4 and R5 sit below `direct`.", "Neither R4 nor R5 is a gate.",
                     "Each of R4 and R5 needs an artifact.", "R4 and R5 both sit below `direct`."):
        check(f"after the ledger, {sentence!r} names its set and passes", ledger_fails(LEDGER_OK.replace(
            "R4 has a credible bridge, and R3 (`medium`) waits on an artifact.", sentence)), [])
    check("the v0.1 count after an intact ledger fails, as the sentence and as snapshot prose",
          ledger_fails(LEDGER_OK.replace("waits on an artifact.",
                                         "waits on an artifact. Five of seven material requirements are `direct`.")),
          ["ledger_sentence", "snapshot_count"])
    # round 6 C5-1: "N of M" is read as a count of rows after the ledger in every
    # form, so one that names fewer rows than it counts fails there, map or no map.
    for sentence in ("R4 is the stretch, leaving four out of seven covered.", "R4 is the stretch; fit is 5/7 covered."):
        check(f"after the ledger, {sentence!r} fails", (bool(ledger_rules.after_ledger_claim(sentence)), ledger_fails(
            LEDGER_OK.replace("R4 has a credible bridge, and R3 (`medium`) waits on an artifact.", sentence))),
            (True, ["ledger_sentence", "snapshot_count"]))
    # round 6 check NP-3: a date and "24/7" are not ratios after the ledger either,
    # while a ratio that is one is read there as a count of rows, whatever it counts.
    for sentence, fails in (("R4 has a credible bridge; interviews close 10/16/2026.", False),
                            ("R4 waits on RR2, a 24/7 rota.", False),
                            ("R4 and R5 sit below `direct`, 4/7 overall.", True),
                            ("R4 is 2 of 3 on the panel.", True),
                            ("Her 2 of 3 launches back R2.", True)):
        check(f"after the ledger, {sentence!r} {'fails' if fails else 'passes'}",
              bool(ledger_rules.after_ledger_claim(sentence)), fails)
    check("a sentence that names its rows and quantifies nothing passes", ledger_fails(LEDGER_OK.replace(
        "R4 has a credible bridge, and R3 (`medium`) waits on an artifact.",
        "R4 and R5 sit below `direct`, and R7 (`none`) has no evidence yet.")), [])
    check("a fraction in the snapshot's prose fails", ledger_fails(LEDGER_OK.replace(
        "**Opportunity ledger.** Authority", "**Opportunity ledger.** 4/7 direct. Authority")), ["snapshot_count"])
    check("a count that is not about map rows is outside the rule, and passes", ledger_fails(LEDGER_OK.replace(
        "**Opportunity ledger.** Authority", "**Opportunity ledger.** Two of three squads are hiring. Authority")), [])
    check("a count above the ledger fails", ledger_fails(LEDGER_OK.replace(
        "**Worth applying to.", "**Five of seven are `direct`; worth applying to.")), ["snapshot_count"])

    # What the first fixes still let through (cross-cutting F1, JU-11): a count with
    # words between it and its noun, a count with no "of", a second paragraph after
    # the ledger, a universal outside the sentence after the ledger, and a band
    # without backticks.
    sentence = "R4 has a credible bridge, and R3 (`medium`) waits on an artifact."
    for count in ("Four of the seven material requirements are `direct`.", "Four rows are `direct`.",
                  "Four direct, and R4 has a bridge.", "R4 is the only gap that matters."):
        check(f"after the ledger, {count!r} fails as the sentence and as prose",
              ledger_fails(LEDGER_OK.replace(sentence, count)), ["ledger_sentence", "snapshot_count"])
    check("a second paragraph after the ledger fails, though the first is clean", ledger_fails(LEDGER_OK.replace(
        sentence, sentence + "\n\nThe rest are `direct`.")), ["ledger_sentence", "snapshot_count"])
    check("two sentences after the ledger fail, with no quantifier in either", ledger_fails(LEDGER_OK.replace(
        sentence, "R4 has a credible bridge. R3 (`medium`) waits on an artifact.")), ["ledger_sentence"])
    said = next(c["why"] for c in output_checks.check_fit_ledger(LEDGER_OK.replace(
        sentence, "R4 has a credible bridge. R3 (`medium`) waits on an artifact."))["checks"]
        if c["check"] == "ledger_sentence")
    check_true("and the failure says it is a second sentence, not a quantifier",
               said.startswith("more than one sentence after the ledger"))
    import ledger_rules
    check_true("the shared rule tells the two cases apart",
               ledger_rules.is_second_sentence("R4 bridges. R3 waits.",
                                               ledger_rules.after_ledger_claim("R4 bridges. R3 waits."))
               and not ledger_rules.is_second_sentence("Every row is direct.",
                                                       ledger_rules.after_ledger_claim("Every row is direct.")))
    check("a decimal or an abbreviation is not a second sentence", ledger_fails(LEDGER_OK.replace(
        sentence, "R4 has a credible bridge (e.g. the PSD2 work), and R3 (`medium`) waits on v2.1.")), [])
    check("a universal over a tier in another slot fails", ledger_fails(LEDGER_OK.replace(
        "**Worth applying to.", "**Worth applying to: every must_have requirement is direct but R4.")),
        ["snapshot_count"])
    check("\"only\" qualifying one row is not a quantifier outside the sentence after the ledger",
          ledger_fails(LEDGER_OK.replace("**Opportunity ledger.** Authority",
                                         "**Opportunity ledger.** R4 is only adjacent. Authority")), [])
    check("a figure with its unit or a range is the candidate's number, not a count of rows",
          ledger_fails(LEDGER_OK.replace("**Opportunity ledger.** Authority",
                                         "**Opportunity ledger.** R2 is 9 years against an 8+ requirement, "
                                         "teams of 3–7 (R5 `low`). Authority").replace("(R5 `low`)", "(R5 (`low`))")),
          [])
    check("an enumerator is not a count", ledger_fails(LEDGER_OK.replace(
        "- **Severe red flags:** none found.",
        "- **Severe red flags:** none found.\n- **Conditions for go:** (1) RR1 verifies; (2) R4 stays adjacent.")), [])
    check("a band without backticks is still the row's, and a wrong one fails", ledger_fails(LEDGER_OK.replace(
        "R3 (`medium`) waits", "R3 (high) waits")), ["snapshot_band"])
    check("a right one passes", ledger_fails(LEDGER_OK.replace("R3 (`medium`) waits", "R3 (medium) waits")), [])
    check("a severity written as a band without backticks fails", ledger_fails(LEDGER_OK.replace(
        "(RR1).", "(RR1 (high)).")), ["snapshot_band"])

    # How the prose is read is stated once, above ledger_rules.MAP_WORDS: a year, an
    # ordinary-English map word before one of its listed ordinary heads, a row's
    # named gate, a word past an article and a count inside a parenthesis count no
    # rows (NP-2; round 6 N1). Each holds in CI and here, because both call map_claim.
    for prose in ("Sound but under-specified, with two important unknowns: award authority (RR1) and the "
                  "contract basis (RR2).",
                  "(2) one direct conversation with the hiring manager — RR1.",
                  "R8 answered — the one question a hard gate may ask.",
                  "A start before February 2027 would fail the R9 gate.",
                  "The fund launched in 2024 and its requirements are explicit.",
                  "RR1 answered in round 2 of the interviews, and the R8 gate settled.",
                  "R5 (mentor two juniors) is `unclear`.",
                  "She manages two direct reports.",
                  "One gap analysis would settle RR1.",
                  "The 24/7 on-call rota (RR2) is unverified.",
                  "The role runs 24/7.",
                  "Pay for 2024/25 is withheld (RR4).",
                  "Interviews close 10/16/2026 (RR3).",
                  "The role is one of two openings (RR4).",
                  "R2 shipped two direct-to-consumer launches.",
                  "It would matter for a role like this one if the gates were not fatal (RR1).",
                  # round 6 C5-1: the candidate's own figures and dates, which a ratio's
                  # clause-end test leaves alone
                  "R2 is `direct`: he ranked 1 of 40 in the cohort.",
                  "R4 is `adjacent`: he was 2 of 3 on the panel that set the rubric.",
                  "R7 rests on a 4/5 from the last review (RR1).",
                  "Start date 3/15 is fixed (RR3).",
                  "He scored 9 out of 10 in the test (RR1).",
                  "R2 is `direct`: he led 3 of 5 launches.",
                  # round 6 N1: an ordinary head after a map word that is also English
                  "One question, absent a reference, decides RR1.",
                  "Two direct quotes back RR1.",
                  # round 6 re-measure: phrasings saved runs carry, read as ordinary
                  "SEO (R6) is one of seven bundled functions in the mandate.",
                  "RR1 stands: 0 of 5 budgeted searches executed.",
                  "Optional: one direct message to the poster (RR1).",
                  "The role names two direct mentees (R7).",
                  # round 6 check NP-1: register entries, actions and the candidate's own
                  # facts are not map rows
                  "Two important risks remain: RR1 and RR2.", "Two direct concerns: RR1 and RR2.",
                  "She made two direct hires last year (R7).", "One direct email to the recruiter settles RR2.",
                  "Two important red flags sit in the register.",
                  # round 6 check NP-2: the candidate's own figures with an ordinary past tense
                  "R1 is `direct`: of her pilots, 4 of 5 renewed.",
                  "R2 is `direct`: of the launches she led, 3 of 4 shipped on time.",
                  "R2 is `direct`: 3 of 4 launches shipped on time, and 3 of 4 shipped early."):
        check(f"ordinary prose passes: {prose!r}", (ledger_rules.map_claim(prose, LEDGER_ROWS), ledger_fails(
            LEDGER_OK.replace("**Opportunity ledger.** Authority", f"**Opportunity ledger.** {prose} Authority"))),
            (None, []))
    for prose in ("five must-haves", "Six of nine material requirements", "only two direct", "all read direct",
                  "one adjacent one", "Two hard gates fail", "the one gap", "five important", "every requirement",
                  "two have a gap", "only R4 has a gap", "the one gap a reference would close", "two direct rows",
                  "both gates are met", "two soft spots are `important`", "the one preferred item",
                  "only the R4 gap is open", "no important rows",
                  # round 5 N1: plural gates and gaps are map words wherever they stand,
                  # and a singular gate or a fit word before a verb or a fit noun counts
                  # named, now: R2 is no gate on this map, R9 no row, and R1 and R6 are `direct` too
                  "Two gates fail outright: R1 on location and R2 on pay", "Two gates fail", "Both gates fail",
                  "All gates hold", "Two gates block this: R1 and R2", "Every gate passes", "Neither gate fails",
                  "Five direct fits: R1, R2, R3, R6 and R9", "Two direct matches, R2 and R3", "Two gaps matter",
                  "Only two gaps matter",
                  # round 5 N4: a ratio that ends its clause, or with a map word after it
                  "Fit: 4 of 7 met", "Fit: 4 of 7", "4/7 direct", "four out of seven met",
                  # round 5 N5: "no other" and "any other" are quantifiers over the map anywhere
                  "R8 is the open gate; no other gate is in doubt", "R4 is the stretch; no other must-have is "
                  "below direct", "any other requirement is direct",
                  # round 6 N1: a singular gate or gap and the adjectives are map words
                  # before any word that is not one of their listed ordinary heads
                  "Every gate checks out", "Every gate checks out except R8", "Neither gate applies to Tomás",
                  "Neither gate worries me", "Every gate gets a yes", "Two direct hits: R2 and R3",
                  "Five important skills are open",
                  # round 6 C5-1: a ratio ending its clause
                  "5 of 7 covered", "Six of nine look solid", "5 of 7 solidly evidenced", "Fit sits at 6 of 7, with R4 open",
                  "4 of 7 met by the CV", "R4 aside, a 5/7 fit", "Fit is a 5 of 7", "her 3 of 5 skills", "Fit: 5 of 7 check out",
                  # round 6 check NP-2: a listed fit predicate still counts rows
                  "Fit: R1 to R7, 5 of 7 confirmed by the CV"):
        check(f"a count or quantifier over the map still fails: {prose!r}",
              (bool(ledger_rules.map_claim(prose, LEDGER_ROWS)), ledger_fails(LEDGER_OK.replace(
                  "**Opportunity ledger.** Authority", f"**Opportunity ledger.** RR2: {prose}. Authority"))),
              (True, ["snapshot_count"]))
    # Round 7: what the rows named make lawful. Where what is said of the counted
    # rows is not in the map's words, whether it is true is left to the grader
    # (evidence-model.md, "The row is the unit"; ci/ledger_rules.py, above Claim).
    for prose in ("two gaps in R4 and R5", "Three direct strengths carry this: R1, R2 and R3"):
        check(f"a set it names, with nothing for the map to resolve, passes: {prose!r}",
              (ledger_rules.map_claim(prose, LEDGER_ROWS), ledger_fails(LEDGER_OK.replace(
                  "**Opportunity ledger.** Authority", f"**Opportunity ledger.** RR2: {prose}. Authority"))),
              (None, []))


def test_named_set_claims() -> None:
    print("\nchecks: a set claim names its rows, exactly; an exclusive quantifier fails whatever it names (round 7)")
    # The measured sentences, and the maps they are judged against: the rule is
    # evidence-model.md's "The row is the unit", and the functions are the ones CI
    # calls on the worked dossier.
    failed = {"R1": ("hard_gate", "hard_gate_fail"), "R2": ("hard_gate", "hard_gate_fail"),
              "R3": ("hard_gate", "direct"), "R4": ("must_have", "direct")}
    musts = {"R1": ("must_have", "direct"), "R2": ("must_have", "direct"), "R3": ("must_have", "direct"),
             "R4": ("important", "adjacent"), "R5": ("preferred", "absent")}
    third = dict(musts, R4=("must_have", "adjacent"))
    for sentence, rows in (("You clear every must-have directly.", musts),
                           ("Both of your hard constraints fail.", failed),
                           ("None of them is a capability problem.", musts),
                           ("All candidate claims are self-reported.", musts),
                           ("Four of the seven material requirements are `direct`.", LEDGER_ROWS)):
        for where, call in (("in prose", ledger_rules.map_claim), ("after the ledger", ledger_rules.after_ledger_claim)):
            got = call(sentence, rows)
            check(f"unnamed, {where}, {sentence!r} fails as a set that names no row",
                  bool(got) and "names no row" in got.why, True)
        check(f"and without the map too: {sentence!r}", bool(ledger_rules.map_claim(sentence)), True)
    for sentence, rows in (("R1 and R2 both fail.", failed),
                           ("Every must-have — R1, R2, R3 — is direct.", musts),
                           ("Two hard gates fail: R1 and R2.", failed),
                           ("No — R1 and R2, both hard gates, fail · `no_go`.", failed),
                           ("None of R4, R5 is a capability gap.", musts),
                           ("Neither gate — R1, R2 — is met, and R3 is.", {k: v for k, v in failed.items() if k != "R3"}
                            | {"R3": ("must_have", "direct")}),
                           ("Four of the seven requirements are `direct`: R1, R2, R3 and R6.", LEDGER_ROWS),
                           ("Four direct fits: R1, R2, R3 and R6.", LEDGER_ROWS),
                           ("Three must-haves — R2, R3 and R4 — carry the case.", LEDGER_ROWS)):
        for where, call in (("in prose", ledger_rules.map_claim), ("after the ledger", ledger_rules.after_ledger_claim)):
            got = call(sentence, rows)
            check(f"named and exact, {where}, {sentence!r} passes", got and got.why, None)
    for sentence, rows, said in (
            ("Every must-have — R1, R2, R3 — is direct.", third, "leaves out ['R4']"),
            ("Two hard gates fail: R1 and R2.", dict(failed, R3=("hard_gate", "hard_gate_fail")), "leaves out ['R3']"),
            ("R1 and R2, the only failed gates, rule it out.", dict(failed, R3=("hard_gate", "hard_gate_fail")),
             "exclusive"),
            ("Both must-haves — R1 and R2 — are direct.", musts, "leaves out ['R3']"),
            ("Five of the seven requirements are `direct`: R1, R2, R3, R6 and R7.", LEDGER_ROWS, "rows number 4"),
            ("Four of the nine requirements are `direct`: R1, R2, R3 and R6.", LEDGER_ROWS, "number 7"),
            ("Two gates block this: R1 and R2.", LEDGER_ROWS, "names ['R1']"),
            ("Both R4 and R9 sit below `direct`.", LEDGER_ROWS, "which the map does not have")):
        for where, call in (("in prose", ledger_rules.map_claim), ("after the ledger", ledger_rules.after_ledger_claim)):
            got = call(sentence, rows)
            if where == "in prose" and sentence.startswith("Both R4"):
                continue      # "both" over row IDs, with no map word in reach, is read after the ledger only
            check(f"named but inexact, {where}, {sentence!r} fails ({said})", bool(got) and said in got.why, True)
    for sentence in ("R5b and R8 are the only rows below `direct`.", "P1 names only R1–R5.",
                     "R4 is the one gap; R5 and R7 are not.", "Direct on all but R4.",
                     "Every must-have but R4 is `direct`.", "R4 waits on RR2, and no other row is open.",
                     "None of the others — R1, R2, R3, R6 — is below `direct`."):
        for where, call in (("in prose", ledger_rules.map_claim), ("after the ledger", ledger_rules.after_ledger_claim)):
            got = call(sentence, LEDGER_ROWS)
            check(f"exclusive, {where}, {sentence!r} fails whatever it names", bool(got) and "exclusive" in got.why, True)
    check("a bare \"none\" is exclusive in the sentence after the ledger, and not read elsewhere",
          (bool(ledger_rules.after_ledger_claim("R4 and R5 sit below `direct`; none is a gate.", LEDGER_ROWS)),
           ledger_rules.map_claim("R4 and R5 sit below `direct`; none is a gate.", LEDGER_ROWS)), (True, None))
    # Without the map only step 1 runs (the comment above Claim): the set names a row, and as many
    # as it counts. The map is what makes it exact.
    inexact = "Every must-have — R2 and R3 — is `direct`."
    check("without the map, a named set passes on presence; with it, the row it leaves out fails",
          (ledger_rules.map_claim(inexact), bool(ledger_rules.map_claim(inexact, LEDGER_ROWS))), (None, True))
    check("without the map, a count naming fewer rows than it gives still fails",
          bool(ledger_rules.map_claim("Four direct fits: R1 and R2.")), True)
    # End to end: each slot the harness reads holds a set claim to the run's own map.
    sentence = "R4 has a credible bridge, and R3 (`medium`) waits on an artifact."
    for text, fails in (("Every must-have — R2, R3 and R4 — has evidence behind it.", []),
                        ("Every must-have — R2 and R3 — is `direct`.", ["ledger_sentence", "snapshot_count"]),
                        ("You clear every must-have directly.", ["ledger_sentence", "snapshot_count"]),
                        ("R4 and R5 are the only rows below `direct`.", ["ledger_sentence", "snapshot_count"])):
        check(f"after the ledger, {text!r} {'fails' if fails else 'passes'}",
              ledger_fails(LEDGER_OK.replace(sentence, text)), fails)
    for status, fails in (("No — R1, a hard gate, fails. Status: `no_go`.", []),
                          ("No — both of your hard constraints fail. Status: `no_go`.", ["snapshot_count"]),
                          ("Yes — you clear every must-have directly. Status: `go`.", ["snapshot_count"])):
        check(f"the status line {status!r} {'fails' if fails else 'passes'}", ledger_fails(LEDGER_OK.replace(
            "**Worth applying to. Status: `conditional_go`.**", f"**{status}**")), fails)
    def summary(text):
        return LEDGER_OK + '\n```json\n{"sections": {"decision": {"status": "go", "summary": ' + json.dumps(text) + '}}}\n```\n'
    for text, verdict in (("Go: every must-have — R2, R3 and R4 — is direct or adjacent.", "PASS"),
                          ("Go: you clear every must-have directly.", "FAIL"),
                          ("Go: none of them is a capability problem.", "FAIL"),
                          ("Go: R4 is the only must-have below direct.", "FAIL"),
                          ("Go: every must-have — R2 and R3 — is direct.", "FAIL")):
        check(f"decision.summary {text!r} is {verdict}", verdict_of(output_checks.check_fit_ledger(summary(text)),
                                                                     "summary_count"), verdict)

    test_set_claim_subjects()


def test_set_claim_subjects() -> None:
    print("\nchecks: a set claim describes its subject's set, and what it says is true of each row it names "
          "(round 7, adversarial check)")
    HG, MH, IM, PR = "hard_gate", "must_have", "important", "preferred"
    D, A, U, AB, F = "direct", "adjacent", "unclear", "absent", "hard_gate_fail"
    # Each map holds a further row of the class the sentence's rows belong to.
    p1 = {"R1": (HG, F), "R2": (HG, F), "R8": (HG, F), "R3": (MH, D), "R4": (MH, D), "R7": (PR, D), "R5": (MH, A)}
    false4 = {"R1": (MH, D), "R2": (MH, D), "R3": (MH, D), "R4": (MH, U), "R5": (IM, D)}
    true4 = dict(false4, R4=(MH, D))
    gates3 = {"R1": (HG, F), "R2": (HG, F), "R3": (HG, U), "R4": (MH, D)}
    met9 = {"R1": (HG, F), "R2": (HG, F), "R9": (HG, D), "R4": (MH, D)}
    gaps = {"R1": (HG, D), "R2": (MH, D), "R3": (MH, D), "R4": (MH, A), "R5a": (IM, D), "R5b": (IM, U),
            "R6": (IM, D), "R7": (PR, AB), "R8": (HG, U), "R9": (HG, D)}
    split = {"R1": (HG, D), "R2": (MH, D), "R3": (MH, D), "R4a": (MH, A), "R4b": (MH, U)}
    both = (("in prose", ledger_rules.map_claim), ("after the ledger", ledger_rules.after_ledger_claim))
    after = (("after the ledger", ledger_rules.after_ledger_claim),)
    passes = (
        # P1: a quantifier over the IDs it names is over those rows, in either word order
        ("R3 and R4 are both `direct`.", p1, both), ("R3 and R4 both are `direct`.", p1, both),
        ("R1 and R2 are both `hard_gate_fail`.", p1, both), ("R3 and R4 are both must-haves.", p1, both),
        ("R1 and R2, both hard gates, fail.", p1, both), ("R1 and R2 both fail.", p1, after),
        ("R1 and R2 are both hard gates, and both fail.", met9, both),
        ("R1 and R2 are both hard gates that fail.", gates3, both),
        # P2: a named universal whose predicate is true of every row it names
        ("Every must-have — R1, R2, R3 and R4 — is `direct`.", true4, both),
        ("You clear every must-have — R1, R2, R3, R4 — directly.", true4, both),
        ("None of the must-haves — R1, R2, R3, R4 — is below `direct`.", true4, both),
        # P3: the candidate's constraints not given says nothing of the map's rows; a
        # set of them is not the gate tier
        ("Arjun states no constraints or non-negotiables of his own, so checks against them are unknown.", gates3,
         (both[0],)),
        ("No hard constraints were stated, so checks against them are unknown.", gates3, both),
        ("None of your constraints were stated.", gates3, (both[0],)),
        ("No — both of your hard constraints, R1 and R2, fail · `no_go`", gates3, both),
        ("Both of your non-negotiables — R1 and R2 — fail.", gates3, both),
        # P4, P5: an exclusive word that restricts something other than rows
        ("Only the employer can change R1 and R2 — a $150k base and a remote exception.", gates3, (both[0],)),
        ("Only the CV can confirm R4.", gates3, (both[0],)),
        ("The only thing that changes R1 is the base.", gates3, (both[0],)),
        ("The only thing R4 lacks is a shipped artifact.", gaps, (both[0],)),
        ("Go, on one condition: the one thing R4 needs is a work sample.", gaps, (both[0],)),
        ("(2) the one question for R8 — permanent or fixed-term — answered permanent", gaps, (both[0],)),
        ("The rest depends on R8.", gaps, (both[0],)),
        # P2 (checks): a verb after the noun is what is said of N, never part of M
        ("No — two of the three hard gates fail (R1, R2). Status: `no_go`.", gates3, (both[0],)),
        ("Two gaps matter: R4 and R5b.", {"R4": (MH, A), "R5b": (IM, U), "R7": (PR, AB), "R1": (HG, D)}, both),
        # P3 (checks): in "N of M <noun>", M is the noun's set
        ("One of the four gaps is a must-have: R4.", gaps, both),
        ("Two of the four rows below `direct` need an artifact: R4 and R5b.", gaps, both),
        ("Two of the four gaps carry the risk: R4 and R5b.", gaps, both),
        # P4 (checks): a noun narrowed by words the map cannot read is the grader's
        ("No — both failed hard gates, R1 and R2, rule it out. Status: `no_go`.", gates3, (both[0],)),
        ("Both hard gates you fail — R1 and R2 — rule it out.", gates3, both),
        ("Every open must-have — R4 — has a named bridge.", gaps, both),
        ("Every gap that matters — R4 and R5b — has a bridge.", gaps, both),
        # P7: two tiers joined are both, named in full
        ("Every hard gate and must-have — R1, R2, R3, R4, R8 and R9 — is in the map.", gaps, both),
        # P9: a split row named by its own IDs
        ("Every must-have — R2, R3, R4a and R4b — is covered.", split, both),
        ("Two must-haves are below `direct`: R4a and R4b.", split, both))
    for sentence, rows, where in passes:
        for name, call in where:
            got = call(sentence, rows)
            check(f"passes, {name}: {sentence!r}", got and got.why, None)
    fails = (
        ("R3 and R5 are both `direct`.", p1, both, "says R5 is `direct`"),
        ("R1 and R3 both fail.", p1, after, "says R3 is `hard_gate_fail`"),
        ("Both hard gates fail.", p1, both, "names no row"),
        ("Every `direct` row — R3, R4 — is a must-have.", p1, both, "leaves out ['R7']"),
        ("Every must-have — R1, R2, R3 and R4 — is `direct`.", false4, both, "says R4 is `direct`"),
        ("You clear every must-have — R1, R2, R3, R4 — directly.", false4, both, "says R4 is `direct`"),
        ("None of the must-haves — R1, R2, R3, R4 — is below `direct`.", false4, both, "says R4 is not below"),
        ("Neither R1 nor R4 is `direct`.", false4, both, "says R1 is not `direct`"),
        ("Four must-haves are `direct`: R1, R2, R3 and R4.", false4, both, "rows number 3"),
        ("Both of your hard constraints fail.", gates3, both, "names no row"),
        ("You fail both of your hard constraints.", gates3, both, "names no row"),
        ("Both of your hard constraints are in doubt.", gates3, both, "names no row"),
        ("Both of your stated constraints fail.", gates3, both, "names no row"),
        ("Both hard gates, R1 and R2, fail.", gates3, both, "leaves out ['R3']"),
        ("P1 names only R1–R5.", gaps, both, "exclusive"),
        ("R5b and R8 are the only rows below `direct`.", gaps, both, "exclusive"),
        ("Only the R4 and R5b rows need work.", gaps, both, "exclusive"),
        ("Two of the two hard gates fail: R1 and R2.", gates3, both, "gives 2; the map's hard_gate rows number 3"),
        ("Two gaps fail: R4.", gaps, both, "counts 2"),
        ("Two of the five gaps carry the risk: R4 and R5b.", gaps, both, "rows number 4"),
        ("Two of the four gaps carry the risk: R4 and R2.", gaps, both, "names ['R4']"),
        ("All your candidate claims are self-reported, and R4 needs a work sample.", gaps, both, "own clause"),
        ("Every hard gate and must-have — R1 and R9 — is in the map.", gaps, both, "leaves out"),
        ("R4, R5a and R5b both need evidence.", gaps, after, "stands over 3 rows"),
        ("Every must-have (R2–R4) is evidenced.", gaps, both, "a range names only its endpoints"),
        ("Every must-have — R2, R3, R4a–b — is covered.", split, both, "a range names only its endpoints"),
        ("Every must-have — R2, R3 and R4 — is covered.", split, both, "which the map splits into ['R4a', 'R4b']"))
    for sentence, rows, where, said in fails:
        for name, call in where:
            got = call(sentence, rows)
            check(f"fails, {name}: {sentence!r} ({said})", bool(got) and said in got.why, True)
    # End to end, in the slots the harness reads.
    sentence = "R4 has a credible bridge, and R3 (`medium`) waits on an artifact."
    for text, fails in (("R2 and R3 are both `direct`, and that doesn't move R4.", []),
                        ("R2 and R4 are both `direct`.", ["ledger_sentence", "snapshot_count"])):
        check(f"after the ledger, {text!r} {'fails' if fails else 'passes'}",
              ledger_fails(LEDGER_OK.replace(sentence, text)), fails)
    slot = "- **Severe red flags:** none found."
    for line, fails in (("You gave no constraints or non-negotiables, so checks against them are unknown.", []),
                        ("Only the employer can change R1 — a sponsorship exception.", []),
                        ("You clear every must-have — R2, R3, R4 — directly.", ["snapshot_count"])):
        check(f"a What-would-change line {line!r} {'fails' if fails else 'passes'}",
              ledger_fails(LEDGER_OK.replace(slot, slot + f"\n- **What would change this:** {line}")), fails)
    def summary(text):
        return LEDGER_OK + '\n```json\n{"sections": {"decision": {"status": "go", "summary": ' + json.dumps(text) + '}}}\n```\n'
    for text, verdict in (("Arjun states no constraints or non-negotiables of his own, so checks against them are "
                           "unknown.", "PASS"),
                          ("Go: every must-have — R2, R3 and R4 — is `direct`.", "FAIL")):
        check(f"decision.summary {text!r} is {verdict}", verdict_of(output_checks.check_fit_ledger(summary(text)),
                                                                     "summary_count"), verdict)


def fixture(skill: str, case_id: int) -> dict:
    from fixture_clauses import load_cases
    path = Path(__file__).resolve().parent.parent / "skills" / skill / "evals" / "evals.json"
    return next(c for c in load_cases(path) if c["id"] == case_id)


def test_user_links() -> None:
    print("\nchecks: a user link is a declared link, matched exactly, sorted the same for grader and checks")
    declared = {"user_links": ["https://acme.com/careers/senior-analyst-123"]}
    def link(url):
        return output_checks.is_user_link(entry(url, kind="fetch"), declared)
    check("the declared link with or without scheme, www., trailing slash or fragment is one",
          [link(u) for u in ("https://acme.com/careers/senior-analyst-123",
                             "http://www.ACME.com/careers/senior-analyst-123/",
                             "acme.com/careers/senior-analyst-123#apply")], [True] * 3)
    check("its home page, parent path, a truncated host, a suffix host, another case of path "
          "or another query is research",
          [link(u) for u in ("https://acme.com/", "https://acme.com", "https://acme.com/careers",
                             "https://acme.co/careers/senior-analyst-123",
                             "https://me.com/careers/senior-analyst-123",
                             "https://acme.com/careers/Senior-Analyst-123",
                             "https://acme.com/careers/senior-analyst-123?ref=x")], [False] * 7)
    check("a search is never a user link, whatever it asks",
          output_checks.is_user_link(entry("https://acme.com/careers/senior-analyst-123"), declared), False)
    check("a fixture that declares none has none, whatever its prompt names",
          output_checks.is_user_link(entry("https://acme.com/careers/senior-analyst-123", kind="fetch"),
                                     {}), False)

    ju5 = fixture("job-underwriter", 5)
    research = ju5["research"]
    check_true("ju 5's prompt names its pasted texts' sources and declares no user link",
               "pellucidlearning.com/about" in ju5["prompt"] and not research.get("user_links"))
    rows = {1: "skipped", 2: "skipped", 3: "n/a"}
    for url in ("https://pellucidlearning.com/about", "https://pellucidlearning.com",
                "https://www.pellucidlearning.com/careers"):
        got = output_checks.check_accounting(
            accounting(rows, "Research tier: L0 — no searches; user links read 1"), research, "canned",
            [entry(url, kind="fetch", targets=[1])], ju5["prompt"])
        check(f"ju 5: a fetch of {url} is research: zero_calls, target 1's skip, the count and "
              f"the user-link claim all fail",
              [verdict_of(got, "zero_calls"), verdict_of(got, "skip_has_no_call", 1),
               verdict_of(got, "tally_searches"), verdict_of(got, "tally_user_links")], ["FAIL"] * 4)

    l0 = dict(RESEARCH, user_links=["https://example.org/jd"])
    jd = [entry("https://example.org/jd", kind="fetch")]
    l0_rows = {1: "skipped", 2: "skipped", 3: "n/a"}
    got = output_checks.check_accounting(
        accounting(l0_rows, "Research tier: L0 — no searches; user links read 1"), l0, "denied", jd)
    check("L0: a declared link read and named on the line passes",
          (verdict_of(got, "tally_user_links"), verdict_of(got, "tally_searches")), ("PASS", "PASS"))
    got = output_checks.check_accounting(
        accounting(l0_rows, "Research tier: L0 — no searches"), l0, "denied", jd)
    check("L0: the same read left off the line fails", verdict_of(got, "tally_user_links"), "FAIL")
    got = output_checks.check_accounting(
        accounting(l0_rows, "Research tier: L0 — no searches; user links read 4"), l0, "denied", [])
    check("L0: user links claimed with none recorded fails", verdict_of(got, "tally_user_links"), "FAIL")
    got = output_checks.check_accounting(
        accounting(l0_rows, "Research tier: L0 — no searches; user links read 1"), l0, "denied",
        [entry("https://example.org/other", kind="fetch")])
    check("L0: an undeclared fetch called a user link fails both the claim and `no searches`",
          (verdict_of(got, "tally_user_links"), verdict_of(got, "tally_searches")), ("FAIL", "FAIL"))
    got = output_checks.check_accounting(
        accounting(l0_rows, "Research tier: L0 — no searches; user links read 1"), l0, "denied", None)
    check("with no research log the user-link count is unchecked, not passed",
          (verdict_of(got, "tally_user_links"), "tally_user_links" in got["unchecked"]), (None, True))
    # `user links read N` counts reads that returned (amended D2): a link the host
    # could not open is not a read, and the response says it could not open it.
    for outcome in ("refused", "error"):
        unopened = [entry("https://example.org/jd", outcome, kind="fetch")]
        truthful, claimed = (output_checks.check_accounting(accounting(l0_rows, line), l0, "denied", unopened)
                             for line in ("Research tier: L0 — no searches",
                                          "Research tier: L0 — no searches; user links read 1"))
        check(f"a declared link the host {outcome} is not read: the line without it passes, a claim to have "
              f"read it fails", (verdict_of(truthful, "tally_user_links"), verdict_of(truthful, "tally_searches"),
                                 verdict_of(claimed, "tally_user_links")), ("PASS", "PASS", "FAIL"))
        check_true("and the run's info says it was not opened",
                   any("user link not opened" in i for i in truthful["info"]))
    block = run_fixtures.observed_block({"research_log": [entry("https://example.org/jd", "refused", kind="fetch")]}, l0)
    check_true("the grader's record lists a refused user link apart, as not read and not counted",
               "User links not opened: 1" in block and "User links read" not in block
               and block.startswith("Recorded: no research search or fetch calls were made."))
    # Round 5 N3: the tally counts links, not fetches. One link fetched twice — the
    # second time as www. with a trailing slash, the same link after norm_url — is
    # one link read; a link refused and then fetched is read, not "not opened".
    twice = [entry("https://example.org/jd", kind="fetch"), entry("https://www.example.org/jd/", kind="fetch")]
    one, two = (output_checks.check_accounting(accounting(l0_rows, line), l0, "denied", twice)
                for line in ("Research tier: L0 — no searches; user links read 1",
                             "Research tier: L0 — no searches; user links read 2"))
    check("one link fetched twice is one link read: \"read 1\" passes, \"read 2\" fails",
          (verdict_of(one, "tally_user_links"), verdict_of(two, "tally_user_links")), ("PASS", "FAIL"))
    retried = [entry("https://example.org/jd", "refused", kind="fetch"), entry("https://example.org/jd", kind="fetch")]
    got = output_checks.check_accounting(
        accounting(l0_rows, "Research tier: L0 — no searches; user links read 1"), l0, "denied", retried)
    block = run_fixtures.observed_block({"research_log": retried}, l0)
    check("a link refused and then read counts once as read and is not listed as not opened",
          (verdict_of(got, "tally_user_links"), any("user link not opened" in i for i in got["info"]),
           "User links read: 1 link(s)" in block, "not opened" in block), ("PASS", False, True, False))
    block = run_fixtures.observed_block({"research_log": twice}, l0)
    check_true("and the grader's record asks for the link count, listing both fetches",
               "`user links read 1`" in block and "(2 fetch(es) listed below)" in block)

    meta = {"research_log": [entry("Kestrel careers", targets=[1]),
                             entry("https://example.org/jd", kind="fetch"),
                             entry("https://example.org/other", kind="fetch")]}
    block = run_fixtures.observed_block(meta, l0)
    check_true("the grader's record counts research calls without the user link",
               block.startswith("Recorded: 2 research call(s) — 1 search(es), 1 fetch(es)"))
    check_true("and lists the user link in its own group, by the checks' own classifier",
               "User links read: 1 link(s)" in block
               and block.index("example.org/jd") > block.index("User links read")
               and block.index("example.org/other") < block.index("User links read"))
    check_true("a fixture declaring no user link shows every fetch as research",
               run_fixtures.observed_block(meta).startswith("Recorded: 3 research call(s)"))
    check_true("a run that only read a user link made no research call",
               run_fixtures.observed_block({"research_log": jd}, l0)
               .startswith("Recorded: no research search or fetch calls were made."))
    shown = run_fixtures.observed_block({"research_log": [
        entry("Kestrel values", targets=[1], urls=["https://kestrel.test/values", "https://kestrel.test/careers"])]})
    check_true("a search line names the URLs the room returned for it, so which pages a run saw is graded "
               "from the record", "2 result(s): https://kestrel.test/values, https://kestrel.test/careers" in shown)


def test_budget_spent_unavailable() -> None:
    print("\nchecks: with research not declined, `unavailable` with no call is lawful only when the budget went on "
          "higher-priority targets")
    tally = "Research tier: L1 — searches 5 of 5, fetches 0 of 2"
    rows = {1: "yes", 2: "yes", 3: "unavailable"}
    def run(log):
        return output_checks.check_accounting(accounting(rows, tally), RESEARCH, "canned", log)
    spent = [entry(q, targets=[t]) for q, t in (("Kestrel careers", 1), ("Kestrel about", 1),
             ("Kestrel jobs", 1), ("analyst salary", 2), ("analyst compensation", 2))]
    got = run(spent)
    check("five of five searches on targets 1-2: target 3 `unavailable` passes accept and the refusal check",
          (verdict_of(got, "accept", 3), verdict_of(got, "unavailable_has_refusal", 3)), ("PASS", "PASS"))
    got = run(spent[:4] + [entry("imogen analyst", targets=[3])])
    check("one of them aimed at target 3 fails both",
          (verdict_of(got, "accept", 3), verdict_of(got, "unavailable_has_refusal", 3)), ("FAIL", "FAIL"))
    got = run(spent[:4] + [entry("Kestrel lawsuit")])
    check("one of them aimed at no target fails both",
          (verdict_of(got, "accept", 3), verdict_of(got, "unavailable_has_refusal", 3)), ("FAIL", "FAIL"))
    got = output_checks.check_accounting(
        accounting(rows, "Research tier: L1 — searches 4 of 5, fetches 0 of 2"), RESEARCH, "canned", spent[:4])
    check("four of five spent fails both",
          (verdict_of(got, "accept", 3), verdict_of(got, "unavailable_has_refusal", 3)), ("FAIL", "FAIL"))
    first = dict(RESEARCH, targets=[dict(t, accept={"canned": ["yes"]}) for t in RESEARCH["targets"]])
    got = output_checks.check_accounting(
        accounting({1: "unavailable", 2: "yes", 3: "yes"}, tally), first, "canned",
        [entry(q, targets=[t]) for q, t in (("analyst salary", 2), ("analyst pay", 2),
                                            ("imogen", 3), ("imogen talks", 3), ("imogen writing", 3))])
    check("a budget spent on lower-priority targets does not excuse target 1",
          (verdict_of(got, "accept", 1), verdict_of(got, "unavailable_has_refusal", 1)), ("FAIL", "FAIL"))
    got = output_checks.check_accounting(accounting(rows, tally), first, "canned", None)
    check("with no research log, a canned `unavailable` outside the accept list is unchecked, not failed",
          (verdict_of(got, "accept", 3), "accept" in got["unchecked"]), (None, True))


def test_declined_unavailable() -> None:
    print("\nchecks: `unavailable` with no call is lawful when the user declined research or chose L0")
    first = [dict(t, accept={"canned": ["yes"]}) for t in RESEARCH["targets"]]
    declined = dict(RESEARCH, targets=first, declined=True, user_links=["https://example.org/jd"])
    rows = {1: "unavailable", 2: "unavailable", 3: "unavailable"}
    l0 = "Research tier: L0 — no searches"

    def run(fixture, log, tally=l0):
        return output_checks.check_accounting(accounting(rows, tally), fixture, "canned", log)

    def verdicts(got):
        return [verdict_of(got, c, n) for n in (1, 2, 3) for c in ("accept", "unavailable_has_refusal")]

    got = run(declined, [])
    check("declined, no call sent: every `unavailable` passes accept and the refusal check, "
          "and the L0 line and zero calls pass",
          (verdicts(got), verdict_of(got, "tally_l0"), verdict_of(got, "zero_calls")),
          (["PASS"] * 6, "PASS", "PASS"))
    got = run(declined, [entry("https://example.org/jd", kind="fetch")],
              "Research tier: L0 — no searches; user links read 1")
    check("declined, only a declared user link read: still lawful, and zero calls passes",
          (verdicts(got), verdict_of(got, "tally_l0"), verdict_of(got, "zero_calls")),
          (["PASS"] * 6, "PASS", "PASS"))
    got = run(declined, [entry("analyst salary", outcome="refused", targets=[2])])
    check("declined, one refused search sent: zero calls fails",
          verdict_of(got, "zero_calls"), "FAIL")
    got = run(declined, [entry("analyst salary", targets=[2])],
              "Research tier: L1 — searches 1 of 5, fetches 0 of 2")
    check("declined, a search sent and returned: target 2's `unavailable`, the L0 line and zero calls fail",
          (verdict_of(got, "accept", 2), verdict_of(got, "unavailable_has_refusal", 2),
           verdict_of(got, "tally_l0"), verdict_of(got, "zero_calls")), ("FAIL",) * 4)
    got = run(declined, [entry("https://example.org/other", kind="fetch")])
    check("declined, a fetch of an undeclared link fails zero calls",
          verdict_of(got, "zero_calls"), "FAIL")
    got = run(declined, [], "Research tier: L1 — searches 0 of 5, fetches 0 of 2")
    check("declined, a budgeted line with nothing spent still fails the L0 line",
          verdict_of(got, "tally_l0"), "FAIL")
    got = run(declined, None)
    check("declined with no research log: accept is unchecked, not passed",
          (verdict_of(got, "accept", 1), "accept" in got["unchecked"],
           "zero_calls" in got["unchecked"]), (None, True, True))

    undeclared = dict(declined, declined=False)
    got = run(undeclared, [], "Research tier: L1 — searches 0 of 5, fetches 0 of 2")
    check("not declined and the budget unspent, no call sent: every `unavailable` fails both",
          verdicts(got), ["FAIL"] * 6)
    check("and no L0 line or zero calls is asked of it",
          (verdict_of(got, "tally_l0"), verdict_of(got, "zero_calls")), (None, None))


def test_off_target_rows() -> None:
    print("\nchecks: a call outside every target is shown as an un-numbered `yes` row after the numbered ones")
    rows = "| 1. target | yes | why |\n| 2. target | yes | why |\n| 3. target | n/a | why |\n"
    head = "Research tier: L1 — searches 3 of 5, fetches 0 of 2\n\n| Target | Status | What it moved |\n|---|---|---|\n"
    extra = "| Off-target: Kestrel lawsuit | yes | nothing moved |\n"
    canary = "It came from an experimentation-platform team.\n\n"
    log = [entry("Kestrel careers", targets=[1], urls=["https://kestrel.test/careers"]),
           entry("analyst salary", targets=[2]), entry("Kestrel lawsuit")]
    got = output_checks.check_accounting(canary + head + rows + extra, RESEARCH, "canned", log)
    check("the row is read, not a format failure, and both off-target checks pass",
          (verdict_of(got, "format"), verdict_of(got, "off_target_shown"),
           verdict_of(got, "off_target_has_call")), (None, "PASS", "PASS"))
    got = output_checks.check_accounting(canary + head + rows, RESEARCH, "canned", log)
    check("the same call with no row fails", verdict_of(got, "off_target_shown"), "FAIL")
    got = output_checks.check_accounting(
        canary + head.replace("searches 3", "searches 0") + "| 1. target | n/a | why |\n| 2. target | skipped | why |\n"
        "| 3. target | n/a | why |\n" + extra, RESEARCH, "canned", [])
    check("a row with no call recorded at all fails", verdict_of(got, "off_target_has_call"), "FAIL")
    got = output_checks.check_accounting(canary + head + extra + rows, RESEARCH, "canned", log)
    check("an un-numbered row before the numbered ones is a format failure",
          verdict_of(got, "format"), "FAIL")
    got = output_checks.check_accounting(canary + head + rows + extra.replace("| yes |", "| skipped |"),
                                         RESEARCH, "canned", log)
    check("an un-numbered row labeled anything but `yes` is a format failure",
          verdict_of(got, "format"), "FAIL")
    got = output_checks.check_accounting(canary + head + rows + extra + "| 4. target | yes | why |\n",
                                         RESEARCH, "canned", log)
    check("a numbered row after an off-target row is a format failure", verdict_of(got, "format", 4), "FAIL")
    got = output_checks.check_accounting(canary + head + rows + extra, RESEARCH, "canned", None)
    check("with no research log the off-target checks are unchecked",
          (verdict_of(got, "off_target_shown"), "off_target_shown" in got["unchecked"]), (None, True))


def test_canary_gate() -> None:
    print("\nchecks: the canary is asked for only of a page the room returned, and its page is checked")
    labels = {1: "yes", 2: "yes", 3: "n/a"}
    two = [entry("Kestrel careers", targets=[1]), entry("analyst salary", targets=[2])]
    got = output_checks.check_accounting(accounting(labels), RESEARCH, "canned", None)
    check("canned, no research log: the canary is unchecked, not judged",
          (verdict_of(got, "canary", 1), "canary" in got["unchecked"]), (None, True))
    for name, canaries in (
            ("no page", [{"target": 1, "text": "came from"}]),
            ("a page that is no page of the fixture", [{"target": 1, "page": "https://kestrel.example/about",
                                                       "text": "came from"}]),
            ("another target's page", [{"target": 1, "page": "https://survey.test/analyst",
                                        "text": "came from"}])):
        got = output_checks.check_accounting(accounting(labels), dict(RESEARCH, canaries=canaries),
                                             "canned", two)
        check(f"a canned canary naming {name} fails as a fixture error, never waived",
              [(c["verdict"], c["kind"]) for c in got["checks"] if c["check"] == "canary_fixture"],
              [("FAIL", "fixture")])
    got = output_checks.check_accounting(accounting({1: "unavailable", 2: "unavailable", 3: "n/a"}),
                                         dict(RESEARCH, canaries=[{"target": 1, "text": "came from"}]),
                                         "denied", [])
    check("a denied room needs no page: only the negative control runs",
          (verdict_of(got, "canary_fixture", 1), verdict_of(got, "canary_absent", 1)), (None, "PASS"))
    fetched = [entry("https://kestrel.test/careers/", kind="fetch", targets=[1],
                     urls=["https://kestrel.test/careers"]), entry("analyst salary", targets=[2])]
    got = output_checks.check_accounting(accounting(labels), RESEARCH, "canned", fetched)
    check("a page the room returned to a fetch is asked for", verdict_of(got, "canary", 1), "FAIL")
    missed = [entry("https://www.kestrel.test/careers", kind="fetch", targets=[]),
              entry("analyst salary", targets=[2])]
    got = output_checks.check_accounting(accounting(labels), RESEARCH, "canned", missed)
    check("a fetch the room answered with no page returns nothing to ask for",
          verdict_of(got, "canary", 1), None)
    for skill, case_id in (("job-underwriter", 4), ("mock-interview", 7)):
        case = fixture(skill, case_id)
        bad = [c for c in case["research"].get("canaries", [])
               if not any(output_checks.same_url(p.get("url", ""), c.get("page", "")) and
                          p.get("target") == c.get("target") for p in case["research"].get("pages", []))]
        check(f"{skill} {case_id}: every canary names one of its own pages for its target", bad, [])


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

# --- Misfires found by auditing a clean-room measurement ------------------------
#
# Each check below states a misfire (a correct output the check failed, or a check
# stricter than its rule) as a must-pass, beside the real violations named with it
# as must-fails, so the fix lets nothing real through.

def test_audit_quotes() -> None:
    print("\nchecks: a Provenance quote of a named non-candidate source is checked for existence (audit A-C)")
    prompt = ("ME: I ran the weekly content-drop calendar. Never led a team.\n"
              "RECRUITER'S EMAIL: we'd like you to present a short POV on operator partnerships.\n"
              "STRATEGY BRIEF: consolidate eight branches into five hubs over 2027.")
    own = ["I ran the weekly content-drop calendar. Never led a team."]
    evidence = '"I ran the weekly content-drop calendar" — your message'

    def pack(provenance, requirement="Own the calendar", corpus=(), log=None, mode="denied"):
        return ("| # | Requirement (source) | Evidence, verbatim | Confidence | Bridge |\n|---|---|---|---|---|\n"
                f"| F1 | {requirement} | {evidence} | high | — |\n\n"
                "| # | Question | Type | Provenance | Answer guidance | Rationale |\n|---|---|---|---|---|---|\n"
                f"| A1 | q | EXP | {provenance} | g | F1 |\n")

    def banks(provenance, corpus=()):
        got = output_checks.check_quotes(pack(provenance), prompt, corpus, own)["checks"]
        return sorted(c["verdict"] for c in got if c["check"] == "quotes" and c["target"] == "banks"
                      and c["verdict"] == "FAIL") or ["PASS"]
    for cell in ('[grounded] "we\'d like you to present a short POV on operator partnerships" — recruiter\'s email',
                 '[grounded] strategy brief: "consolidate eight branches into five hubs over 2027"',
                 '[grounded] "consolidate eight branches into five hubs over 2027" (strategy brief)',
                 '[grounded] "consolidate eight branches into five hubs over 2027" — strategy brief (via recruiter); '
                 '"I ran the weekly content-drop calendar" — your message',
                 '[grounded] role_profile R5 ("consolidate eight branches into five hubs")'):
        check(f"must pass: a source line quoted with its own non-candidate origin: {cell[:70]!r}",
              banks(cell), ["PASS"])
    check("must pass: a page's title quoted inside the previous quote's origin, from the room's pages",
          banks('[grounded] "Larkspur retires per-title event teams" — Saltmarsh Games, "Announcing Project '
                'Larkspur"', ["Announcing Project Larkspur\nhttps://s.test/news\nLarkspur retires per-title "
                              "event teams in favour of one group."]), ["PASS"])
    check("must pass: the template token \"none given\" quoted as a reference is no sentence (C)",
          banks('[grounded] "I ran the weekly content-drop calendar"; [inferred] derived from F2\'s "none given" '
                'row'), ["PASS"])
    check("must fail: a company line with no origin of its own (mi1.run2 D2), beside one that has one",
          banks('[grounded] "five hubs over 2027"; "we\'d like you to present a short POV" (recruiter\'s email)'),
          ["FAIL"])
    check("must fail: a source that does not hold the quote (mi7.canned.run2 A2)",
          banks('[generic]; the "don\'t overpromise" framing is [inferred] from Tobias\'s own GDC talk (researched)'),
          ["FAIL"])
    check("must fail: an origin-tagged quote that no source holds",
          banks('[grounded] "consolidate nine branches into two hubs" — strategy brief'), ["FAIL"])
    check("must fail: a candidate negative tagged as their own, absent from the snapshot (mi7.denied.run2 B2)",
          banks('[grounded] "Never led a team" — your own stated negative'), ["FAIL"])
    check("must fail: a candidate sentence stays the candidate's whatever origin it claims, and must stand in "
          "the snapshot", banks('[grounded] "Never led a team" — LinkedIn'), ["FAIL"])
    check("must fail: a candidate quote with an insertion ([years]) is no quote",
          banks('[grounded] "I ran the weekly [years] content-drop calendar"'), ["FAIL"])
    check("must fail: a spliced quote (\"I\" for \"I've\") is no quote of a source either",
          banks('[grounded] "I ran the five hubs over 2027" — strategy brief'), ["FAIL"])
    check("must fail: a dossier field's name is the dossier's material, not another source",
          banks('[grounded] prohibited_claims: "consolidate eight branches"'), ["FAIL"])

    # B: a canned room's pages are quotable by their title and URL too, and only the
    # pages the run's log shows returned.
    mi7 = fixture("mock-interview", 7)
    larkspur = "https://saltmarshgames.com/news/project-larkspur"
    title_req = '"Announcing Project Larkspur" — Saltmarsh Games news page'
    text = pack("[grounded]").replace("| F1 | Own the calendar |", f"| F1 | {title_req} |")
    shown = [{"kind": "search", "query_or_url": "Saltmarsh news", "outcome": "returned",
              "urls_returned": [larkspur], "targets": [3]}]

    def req(log):
        got = output_checks.run_checks(mi7, "canned", text, log)["checks"]
        return [c["verdict"] for c in got if c["check"] == "quotes" and c["target"] == "requirements"]
    check("must pass: a requirement quoting a returned page's title (mi7.canned.run1 F9)", req(shown), ["PASS"])
    check("must fail: the same title when the room never returned that page", req([]), ["FAIL"])
    check("must fail: quoted [generic] prose is in no page's title, URL or text (mi7.canned.run2 F9)",
          [c["verdict"] for c in output_checks.run_checks(mi7, "canned", text.replace(
              title_req, '"[generic] team/people-management experience, a near-certain probe"'), shown)["checks"]
           if c["check"] == "quotes" and c["target"] == "requirements"], ["FAIL"])


def test_audit_evidence_form() -> None:
    print("\nchecks: the evidence cell's origins and separators are the template's, no stricter (audit)")
    for cell in ('"A" — dossier (verified_candidate_evidence)', '"A" — dossier `verified_candidate_evidence`',
                 '"A" — dossier (handoff)', '"A" — dossier handoff_to_mock_interview.verified_candidate_evidence',
                 '"A" — dossier R3 (evidence_map)', '"A" — coach\'s notes', '"A" — your CV, and "B" — your message',
                 '"A" — your CV; and "B" — your CV', '"A" — your CV, <br> "B" — your CV'):
        check(f"must pass: {cell!r}", output_checks.evidence_cell_lawful(cell), True)
    for cell in ('"A" — dossier (medium confidence: expect a probe)',
                 '"A" — dossier (handoff; medium confidence, expect a probe)',
                 '"A"; "B" — dossier (handoff)', '"A" — dossier handoff, which shows ownership',
                 '"A" — dossier (verified_candidate_evidence, strong)', '"A" — coach notes',
                 '"A" — your message, i.e. you set hiring strategy', '"A" and "B" — your message',
                 '"A", "B" — your message', '"A." "B." — your message', '"A" — your CV; adjacent: "B" — your CV',
                 '"A" — your CV + "B" — your CV', '"A" — your CV / "B" — your CV',
                 '"A" — your CV, and also "B" — your CV'):
        check(f"must fail: {cell!r}", output_checks.evidence_cell_lawful(cell), False)


def test_audit_research() -> None:
    print("\nchecks: a search for the company by name is its sweep target's; terms read as the rule does (audit)")
    ju4, mi5, mi8, mi3 = (fixture("job-underwriter", 4), fixture("mock-interview", 5),
                          fixture("mock-interview", 8), fixture("mock-interview", 3))

    def aimed(case, query, mode="denied", kind="search"):
        r = case["research"]
        room = {"prompt": case["prompt"], "targets": r["targets"]}
        e = {"kind": kind, "query_or_url": query, "targets": []}
        return [t["n"] for t in r["targets"] if output_checks.aimed_at(e, t, r.get("pages", []), mode, room)]
    check("must pass: the company's name plus the request's own description is JU target 1 (ju-4)",
          aimed(ju4, "Brindlemoor insurtech pet insurance"), [1])
    check("must pass: the name alone is JU target 1", aimed(ju4, '"Brindlemoor"'), [1])
    check("must pass: MI target 3 is the company sweep (mi-5)", aimed(mi5, '"Kelverton Rail" company'), [3])
    check("must fail: a word the request does not use makes it a stray (Brindlemoor layoffs glassdoor)",
          aimed(ju4, "Brindlemoor layoffs glassdoor"), [])
    check("must fail: words outside the request stay strays (ju-5 canned run3)",
          [aimed(fixture("job-underwriter", 5), q) for q in
           ("Pellucid Learning tutoring platform Glassdoor reviews", "Pellucid Learning Crunchbase")], [[], []])
    check("must fail: no company name, no identity (mi-8 canned run3)",
          [aimed(mi8, q) for q in ("credit union member complaints regulation ombudsman",
                                   "credit union branch complaints handling financial services regulator")], [[], []])
    check("must fail: another target's term takes it out of the identity route",
          aimed(mi8, "Ashgrove Credit Union interview process"), [2])
    try:
        output_checks.aimed_at({"kind": "search", "query_or_url": "x"}, ju4["research"]["targets"][0], [], "denied")
        raised = False
    except ValueError:
        raised = True
    check("an identity target read with no room fails closed, never silently a stray", raised, True)
    check("must pass: a market sweep tied to the sector is MI-5 target 3 (D)",
          aimed(mi5, "UK rail scheduling software train operating companies partnerships market 2026"), [3])
    check("must fail: a salary market search is no sector sweep",
          aimed(mi5, "partnerships manager salary market UK"), [])
    check("must fail: a live-service best-practices search is no target (mi-7 denied run4)",
          aimed(fixture("mock-interview", 7),
                "live service mobile game content calendar post-event review KPIs best practices 2025"), [])
    check("must pass: a job-listing fetch with an encoded role title is target 5 (mi-3 run3, C)",
          aimed(mi3, "https://stripe.com/jobs/search?q=product+operations+manager", kind="fetch"), [5])
    check("must pass: the culture page stays target 1 only",
          aimed(mi3, "https://stripe.com/jobs/culture", kind="fetch"), [1])
    check("must fail: a careers search for the role is a target-5 hunt (mi-8 canned run3)",
          aimed(mi8, "Ashgrove Credit Union careers Member Experience Lead"), [5])
    check("must pass: a regulatory search with a bare 'requirements' is no JD hunt (E)",
          5 in aimed(mi8, '"credit union" complaints handling process regulatory requirements branches contact centre'),
          False)
    check("must fail: real JD hunts still match target 5",
          [5 in aimed(mi8, q) for q in ("member experience lead responsibilities requirements",
                                        "member experience lead job description credit union")], [True, True])
    check("an all-of term needs every part", (output_checks.term_matches(["careers", "lead"], "careers page"),
                                             output_checks.term_matches(["careers", "lead"], "lead careers")),
          (False, True))

    print("\nchecks: the tally line is read as a prefix; a remark after it is read apart (audit B, B2)")
    base = "Research tier: L1 — searches 4 of 5, fetches 0 of 2"
    for line in (base + " (all refused — permission wasn't granted)", base + "; user links read: 0",
                 base + ". Every L1 target was already fixed by a provided document."):
        got = output_checks.parse_tally(line)
        check(f"must pass: a correct line with a reason or a colon is read: {line[-50:]!r}",
              (got["outcome"], got.get("searches")), ("checked", 4))
        check("and its remark restates nothing",
              [bool(output_checks.TALLY_RESTATES.search(r)) for _, r in got.get("remarks", [])],
              [False] * len(got.get("remarks", [])))
    for line in ("Research tier: L1 attempted — searches 3 of 6, fetches 0 of 2", "Research tier: L0 (forced) — no searches",
                 "Research tier: L1 — searches 0 of 6 usable / completed", "Research tier: L1 — 4 of 6 searches sent",
                 "Research tier: L1 — searches 6 of 6 attempted, 0 returned"):
        check(f"must fail: a prefix that is not the form: {line!r}", output_checks.parse_tally(line)["outcome"],
              "unparseable")
    for remark in (". All three were blocked.", " (both search calls were refused)", " (all four calls refused)",
                   " — 4 attempted", "; user links read"):
        got = output_checks.parse_tally(base + remark)
        check(f"must fail: a remark that restates the line: {remark!r}",
              [bool(output_checks.TALLY_RESTATES.search(r)) for _, r in got["remarks"]], [True])
    research = {"targets": [{"n": 1, "terms": ["about"], "accept": ["unavailable"]}],
                "budget": {"searches": 5, "fetches": 2}}
    log = [{"kind": "search", "query_or_url": "x about", "outcome": "refused", "urls_returned": [], "targets": []}] * 2
    got = output_checks.check_accounting(
        "Research tier: L0 — no searches (WebSearch wasn't granted permission)\n\n| Target | Status | x |\n|---|---|---|\n"
        "| 1. about | unavailable | x |\n", research, "denied", log)
    check("must fail: an `L0 — no searches` line with a reason now parses, and its count is judged (ju-3 run3)",
          (verdict_of(got, "tally"), verdict_of(got, "tally_searches")), ("PASS", "FAIL"))
    got = output_checks.check_accounting(
        base + " (both calls refused)\n\n| Target | Status | x |\n|---|---|---|\n| 1. about | unavailable | x |\n",
        research, "denied", log)
    check("and a restating remark fails as format, apart from the counts",
          [(c["check"], c["kind"]) for c in got["checks"] if c["verdict"] == "FAIL"],
          [("tally_remark", "format"), ("tally_searches", "judgement")])


def test_audit_ledger() -> None:
    print("\nchecks: the fit ledger is read wherever the template's shape puts it (audit)")
    for note, req in (("partnering with clinicians specifically", "Partner with clinicians specifically"),
                      ("mentoring two junior analysts", "Mentor two junior analysts"),
                      ("launch coordination with sales and support", "Coordinate launches with sales and support"),
                      ("specs + delivery with two squads", "Write specs and drive delivery with two engineering squads"),
                      ("3+ years PM experience", "3+ years product management experience (must-have)"),
                      ("3+ yrs PM experience", "3+ years PM experience (must-have)")):
        check(f"must pass: {note!r} names {req!r}", ledger_rules.names_requirement(note, req), True)
    for note, req in (("vs. Leeds office four days a week", "Leeds office four days a week"),
                      ("150k vs. your $150k floor", "Base at or above 150k"),
                      ("PM eligibility", "3+ years product management experience"),
                      ("solo execution", "Team of one"), ("dbt-modelled pipelines", "dbt pipelines"),
                      ("PR experience", "Public relations"), ("BI tooling", "Business intelligence tooling")):
        check(f"must fail: {note!r} adds words {req!r} lacks", ledger_rules.names_requirement(note, req), False)

    heading = LEDGER_OK.replace("**Fit ledger.**", "## Fit ledger").replace(
        "**Opportunity ledger.** Authority", "## Opportunity ledger\n\nAuthority")
    check("must pass: a ledger under a markdown heading, with a slot heading after it", ledger_fails(heading), [])
    check("must fail: and its problems are read there (a flipped fit)", ledger_fails(heading.replace(
        "| must_have | adjacent | medium", "| must_have | unclear | medium")), ["ledger_fit"])
    check("must fail: a response with no ledger still fails ledger_present",
          ledger_fails(LEDGER_OK.replace("**Fit ledger.**\n", "").replace(
              "- `hard_gate` — direct: R1\n", "").replace("- `must_have`", "x").replace("- `important`", "x")
              .replace("- `preferred`", "x")), ["ledger_present"])
    dashed = LEDGER_OK.replace("- `hard_gate` — direct: R1", "- `hard_gate`: direct — R1")
    check("must pass: a fit group written 'fit — IDs'", ledger_fails(dashed), [])
    check("must fail: and its rows are still judged (a missing parenthetical)", ledger_fails(dashed.replace(
        "adjacent: R4 (Regulatory exposure)", "adjacent — R4")), ["ledger_parenthetical"])
    check("must fail: a fit group with an unknown fit is still no group",
          ledger_fails(dashed.replace("direct — R1", "strong — R1")), ["ledger_present"])
    h1 = LEDGER_OK.replace("## Decision snapshot", "# Decision snapshot").replace(
        "| RR2 | Compensation unstated | risk_signal | medium | unresolved |",
        "| RR2 | Compensation unstated | risk_signal | medium | unresolved |\n\n## Upgrade menu\n\n"
        "Confidence would rise to `high` overall with a reference.")
    check("must pass: an H1 snapshot ends at the next H2, so later sections' bands are not the snapshot's",
          ledger_fails(h1), [])
    check("must fail: a bare band inside that snapshot still fails", ledger_fails(h1.replace(
        "R3 (`medium`) waits on an artifact", "R3 waits on an artifact; `high` confidence overall")),
          ["snapshot_band"])
    bold_tier = LEDGER_OK.replace("**Opportunity ledger.**", "**Research tier:** L1 — searches 3 of 5, fetches 0 "
                                                           "of 2\n\n**Opportunity ledger.**")
    check("must pass: a bold Research tier line in the snapshot is the tally, not a count of the map",
          ledger_fails(bold_tier), [])
    check("must fail: a count of the map beside it still fails", ledger_fails(bold_tier.replace(
        "**Opportunity ledger.** Authority", "**Opportunity ledger.** Three of five rows are direct. Authority")),
          ["snapshot_count"])


def main() -> int:
    for test in (test_routing_declines, test_cli_refusal, test_parse_stream,
                 test_server_url_identity, test_research_server, test_rooms, test_stems, test_grade_parsing,
                 test_classification, test_missing_response,
                 test_declined_grade_prints_no_score, test_artifact_collection,
                 test_skill_installation, test_classify_room, test_execute_timeout,
                 test_execute_nudge, test_parse_accounting, test_check_accounting,
                 test_fit_ledger, test_quotes, test_review_fixes, test_evidence_cells,
                 test_provenance_pool, test_gates_line, test_severity, test_shared_ledger_rules, test_named_set_claims,
                 test_user_links,
                 test_budget_spent_unavailable, test_declined_unavailable, test_off_target_rows, test_canary_gate, test_backfill,
                 test_recurring, test_audit_quotes, test_audit_evidence_form, test_audit_research,
                 test_audit_ledger):
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
