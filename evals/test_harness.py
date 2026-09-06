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

    python evals/test_harness.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_fixtures
import run_routing

FAILURES: list[str] = []


def check(name: str, got, want) -> None:
    if got == want:
        print(f"  ok   {name}")
    else:
        FAILURES.append(f"{name}: got {got!r}, wanted {want!r}")
        print(f"  FAIL {name}: got {got!r}, wanted {want!r}")


def check_true(name: str, got: bool) -> None:
    check(name, bool(got), True)


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


# --- Decline path 4: a grader that returned nothing graded nothing ---

def test_grade_parsing() -> None:
    print("\nfixtures: a grade that did not parse is not a fixture that failed")
    whole = json.dumps({"verdicts": [{"n": 1, "verdict": "PASS", "why": "a"},
                                     {"n": 2, "verdict": "FAIL", "why": "b"}]})
    got = run_fixtures.parse_verdicts(whole)
    check("a whole reply parses", len(got["verdicts"]), 2)
    check("and is not marked truncated", got.get("truncated"), None)

    cut = '{"verdicts": [{"n": 1, "verdict": "PASS", "why": "fine"}, {"n": 2, "verdict": "FAIL", "why": "cut off'
    got = run_fixtures.parse_verdicts(cut)
    check("a truncated reply keeps the verdicts it did contain", len(got["verdicts"]), 1)
    check_true("and is marked truncated", got.get("truncated"))

    got = run_fixtures.parse_verdicts("the grader said nothing useful at all")
    check("an unusable reply yields no verdicts", got["verdicts"], [])
    check_true("and carries an error", bool(got.get("error")))


def test_failure_classification() -> None:
    print("\nfixtures: deterministic and intermittent are told apart")
    results = [
        {"skill": "s", "id": 1, "run": 0, "grader": 1,
         "verdicts": [{"n": 1, "verdict": "FAIL", "why": "one grader caught it"},
                      {"n": 2, "verdict": "PASS"}]},
        {"skill": "s", "id": 1, "run": 0, "grader": 2,
         "verdicts": [{"n": 1, "verdict": "PASS"}, {"n": 2, "verdict": "PASS"}]},
        {"skill": "s", "id": 1, "run": 1, "grader": 1,
         "error": "grader returned no usable verdicts", "verdicts": []},
    ]
    check("one grader failing is enough to fail the run",
          run_fixtures.failed_in_run(results, "s", 1, 0), {1})
    check("an errored grade fails nothing",
          run_fixtures.failed_in_run(results, "s", 1, 1), set())
    check("the reason is recoverable for the report",
          run_fixtures.why_for(results, "s", 1, 1), "one grader caught it")


# --- Decline path 5: a run that never executed has nothing to grade ---

def test_missing_response() -> None:
    print("\nfixtures: a skipped execution is not a fixture that produced nothing")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        case = {"id": 1, "prompt": "irrelevant", "expectations": ["a", "b", "c"]}
        got = run_fixtures.grade("s", case, out, run=0, grader=1, timeout=1, model=None)
        check("grading a run with no response returns no verdicts", got["verdicts"], [])
        check_true("and carries an error rather than three failures", bool(got.get("error")))


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


def main() -> int:
    for test in (test_routing_declines, test_cli_refusal, test_grade_parsing,
                 test_failure_classification, test_missing_response,
                 test_artifact_collection, test_skill_installation):
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
