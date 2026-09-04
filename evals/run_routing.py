#!/usr/bin/env python3
"""Suite-level routing eval.

Per-skill evals cannot test triggering *between* skills: the decision is made
across the whole available-skills list, so it has no home inside either skill's
evals/. This runner puts both skills in front of the model at once and records
which one fires.

Method: each skill's real frontmatter description is read from its SKILL.md and
registered as a project command, so the model sees the same text it would see
installed. `claude -p` then answers the case prompt, and the stream is watched
for which skill it reaches for. Descriptions are never duplicated here — the
eval always tests what actually ships.

Usage:
    python evals/run_routing.py                 # all cases, 3 runs each
    python evals/run_routing.py --runs 1        # quick pass
    python evals/run_routing.py --case 9 --case 10
"""

from __future__ import annotations

import argparse
import json
import os
import re
import select
import subprocess
import sys
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = ["job-underwriter", "mock-interview"]


def read_description(skill: str) -> str:
    """Pull the live frontmatter description so the eval can't drift from what ships."""
    text = (REPO / "skills" / skill / "SKILL.md").read_text()
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        raise SystemExit(f"{skill}: no frontmatter found")
    body = match.group(1)
    desc = re.search(r"^description:\s*(.+?)(?=\n[a-z-]+:|\Z)", body, re.DOTALL | re.MULTILINE)
    if not desc:
        raise SystemExit(f"{skill}: no description in frontmatter")
    return " ".join(desc.group(1).split())


def write_commands(root: Path, descriptions: dict[str, str], run_id: str) -> dict[str, str]:
    """Register each skill as a project command; return skill -> unique command name."""
    commands = root / ".claude" / "commands"
    commands.mkdir(parents=True, exist_ok=True)
    names = {}
    for skill, desc in descriptions.items():
        name = f"{skill}-{run_id}"
        names[skill] = name
        indented = "\n  ".join(desc.split("\n"))
        (commands / f"{name}.md").write_text(
            f"---\ndescription: |\n  {indented}\n---\n\n# {skill}\n\nThis skill handles: {desc}\n"
        )
    return names


def which_fired(prompt: str, root: Path, names: dict[str, str], timeout: int, model: str | None) -> str:
    """Run one query; return the skill that fired, 'neither', or 'timeout'.

    'timeout' is kept distinct from 'neither' on purpose: a run cut short says
    nothing about routing, and folding the two together would let a slow or
    rate-limited harness manufacture negatives that look like findings.

    Watches partial stream events so the verdict lands as soon as the model
    reaches for a skill, rather than after the skill's work completes.
    """
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--include-partial-messages"]
    if model:
        cmd += ["--model", model]
    # CLAUDECODE guards interactive terminal nesting; a subprocess run is safe.
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    def match(blob: str) -> str | None:
        for skill, name in names.items():
            if name in blob:
                return skill
        return None

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            cwd=str(root), env=env)
    buffer, accumulated, pending = "", "", None
    start = time.time()
    try:
        while time.time() - start < timeout:
            if proc.poll() is not None:
                rest = proc.stdout.read()
                if rest:
                    buffer += rest.decode("utf-8", errors="replace")
                break
            ready, _, _ = select.select([proc.stdout], [], [], 1.0)
            if not ready:
                continue
            chunk = os.read(proc.stdout.fileno(), 8192)
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if event.get("type") == "stream_event":
                    se = event.get("event", {})
                    kind = se.get("type", "")
                    if kind == "content_block_start":
                        block = se.get("content_block", {})
                        if block.get("type") == "tool_use" and block.get("name") in ("Skill", "Read"):
                            pending, accumulated = block.get("name"), ""
                    elif kind == "content_block_delta" and pending:
                        delta = se.get("delta", {})
                        if delta.get("type") == "input_json_delta":
                            accumulated += delta.get("partial_json", "")
                            hit = match(accumulated)
                            if hit:
                                return hit
                    elif kind in ("content_block_stop", "message_stop"):
                        if pending:
                            hit = match(accumulated)
                            if hit:
                                return hit
                            pending = None
                        # Deliberately no early exit here: a model often writes a
                        # sentence of reasoning before reaching for the skill, so
                        # the end of a message is not the end of the decision.
                        # Only `result` (or process exit) settles a negative.

                elif event.get("type") == "assistant":
                    for item in event.get("message", {}).get("content", []):
                        if item.get("type") != "tool_use":
                            continue
                        blob = json.dumps(item.get("input", {}))
                        hit = match(blob)
                        if hit:
                            return hit
                elif event.get("type") == "result":
                    return "neither"
        else:
            return "timeout"
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    return "neither"


def verdict(expected: str, fired: list[str]) -> tuple[bool, str]:
    """An 'either' case passes when exactly one sibling fires, consistently."""
    timeouts = fired.count("timeout")
    fired = [f for f in fired if f != "timeout"]
    if not fired:
        return False, f"inconclusive: all {timeouts} run(s) timed out"
    suffix = f" [{timeouts} timed out]" if timeouts else ""
    unique = set(fired)
    if expected == "either":
        if unique <= {"job-underwriter", "mock-interview"} and unique:
            return True, f"one sibling fired every run ({'/'.join(sorted(unique))}){suffix}"
        return False, f"a spanning request must reach a sibling; got {sorted(unique)}{suffix}"
    if unique == {expected}:
        return True, f"{expected} on every run{suffix}"
    if expected in unique:
        return False, f"inconsistent: {sorted(unique)} (expected {expected} every run){suffix}"
    return False, f"routed to {sorted(unique)}, expected {expected}{suffix}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3, help="runs per case (routing is probabilistic)")
    ap.add_argument("--case", type=int, action="append", help="limit to case id(s)")
    ap.add_argument("--model", default=None)
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--workers", type=int, default=3, help="parallel runs; high values invite rate limiting")
    ap.add_argument("--json-out", default=None, help="write full results here")
    args = ap.parse_args()

    spec = json.loads((REPO / "evals" / "suite-routing.json").read_text())
    cases = [c for c in spec["cases"] if not args.case or c["id"] in args.case]
    descriptions = {s: read_description(s) for s in SKILLS}

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        names = write_commands(root, descriptions, uuid.uuid4().hex[:8])

        jobs = [(c, i) for c in cases for i in range(args.runs)]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            outcomes = list(pool.map(
                lambda job: which_fired(job[0]["prompt"], root, names, args.timeout, args.model),
                jobs,
            ))

    fired_by_case: dict[int, list[str]] = {}
    for (case, _), got in zip(jobs, outcomes):
        fired_by_case.setdefault(case["id"], []).append(got)

    results, passed = [], 0
    for case in cases:
        fired = fired_by_case[case["id"]]
        ok, note = verdict(case["expected"], fired)
        passed += ok
        results.append({"id": case["id"], "expected": case["expected"],
                        "fired": fired, "passed": ok, "note": note})
        print(f"{'PASS' if ok else 'FAIL'}  case {case['id']:>2}  expected {case['expected']:<16} {note}")

    print(f"\n{passed}/{len(cases)} routing cases passed ({args.runs} run(s) each)")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            {"runs_per_case": args.runs, "passed": passed, "total": len(cases), "results": results},
            indent=2) + "\n")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
