#!/usr/bin/env python3
"""Suite-level routing eval.

Per-skill evals cannot test triggering *between* skills: the decision is made
across the whole available-skills list, so it has no home inside either skill's
evals/. This runner puts both skills in front of the model at once and records
which one fires.

Method: each skill is copied into a throwaway project's `.claude/skills/`, so it
reaches the model through the same path an installed skill does — the
available-skills list, carrying its real frontmatter description. `claude -p`
then answers the case prompt and the stream is watched for which skill it
reaches for. Nothing is duplicated here; the eval always tests what ships.

Registration is deliberate. An earlier version registered each skill as a project
*command*, which put a caveat under every number it produced: commands are
addressed to the model as things the user invokes, so "the harness under-reports"
was always available as the competing explanation for a low score. Installing the
real skills retires that caveat.

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
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = ["job-underwriter", "mock-interview"]


def install_skills(root: Path, run_id: str,
                   overrides: dict[str, Path] | None = None) -> dict[str, str]:
    """Copy each skill into the throwaway project; return skill -> installed name.

    The name carries a per-run suffix so a match in the stream can only have come
    from this run's copy, never from a skill the host machine happens to have
    installed. A skill's directory name and its frontmatter `name` must agree, so
    both are renamed together.

    `overrides` substitutes a different SKILL.md for a skill without touching the
    working tree — how a description generation is A/B'd against the one that
    ships. Extract the old one with `git show <ref>:skills/<name>/SKILL.md`.
    """
    dest_root = root / ".claude" / "skills"
    dest_root.mkdir(parents=True, exist_ok=True)
    names = {}
    for skill in SKILLS:
        name = f"{skill}-{run_id}"
        names[skill] = name
        dest = dest_root / name
        # Install what ships: the packager keeps evals/ out of the .skill file,
        # so a copy that carried them would put files in front of the model that
        # no installed user ever has.
        shutil.copytree(REPO / "skills" / skill, dest,
                        ignore=shutil.ignore_patterns("evals", "__pycache__", "*.pyc", ".DS_Store"))
        skill_md = dest / "SKILL.md"
        if overrides and skill in overrides:
            skill_md.write_text(overrides[skill].read_text())
        text = skill_md.read_text()
        renamed = re.sub(rf"^name:\s*{re.escape(skill)}\s*$", f"name: {name}", text,
                         count=1, flags=re.MULTILINE)
        if renamed == text:
            raise SystemExit(f"{skill}: frontmatter name not found to rename")
        skill_md.write_text(renamed)
    return names


def which_fired(prompt: str, root: Path, names: dict[str, str], timeout: int, model: str | None) -> str:
    """Run one query; return the skill that fired, 'neither', 'timeout', or 'error'.

    Two outcomes are kept distinct from 'neither' on purpose. A run cut short
    ('timeout') and a run the CLI failed ('error', typically a rate limit) say
    nothing about routing; folding either into 'neither' lets a slow or throttled
    harness manufacture negatives that look like findings.

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

    state = {"pending": None, "accumulated": ""}

    def consume(buffer: str) -> tuple[str | None, str]:
        """Parse whole lines out of the buffer; return a verdict once one lands."""
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
                        state["pending"], state["accumulated"] = block.get("name"), ""
                elif kind == "content_block_delta" and state["pending"]:
                    delta = se.get("delta", {})
                    if delta.get("type") == "input_json_delta":
                        state["accumulated"] += delta.get("partial_json", "")
                        hit = match(state["accumulated"])
                        if hit:
                            return hit, buffer
                elif kind in ("content_block_stop", "message_stop"):
                    if state["pending"]:
                        hit = match(state["accumulated"])
                        if hit:
                            return hit, buffer
                        state["pending"] = None
                    # Deliberately no early exit here: a model often writes a
                    # sentence of reasoning before reaching for the skill, so
                    # the end of a message is not the end of the decision.
                    # Only `result` (or process exit) settles a negative.

            elif event.get("type") == "assistant":
                for item in event.get("message", {}).get("content", []):
                    if item.get("type") != "tool_use":
                        continue
                    hit = match(json.dumps(item.get("input", {})))
                    if hit:
                        return hit, buffer
            elif event.get("type") == "result":
                if event.get("is_error") or event.get("subtype") not in (None, "success"):
                    return "error", buffer
                return "neither", buffer
        return None, buffer

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            cwd=str(root), env=env)
    buffer = ""
    start = time.time()
    try:
        while time.time() - start < timeout:
            exited = proc.poll() is not None
            if exited:
                rest = proc.stdout.read()
                if rest:
                    buffer += rest.decode("utf-8", errors="replace")
            else:
                ready, _, _ = select.select([proc.stdout], [], [], 1.0)
                if not ready:
                    continue
                chunk = os.read(proc.stdout.fileno(), 8192)
                if not chunk:
                    exited = True
                else:
                    buffer += chunk.decode("utf-8", errors="replace")

            # Parse before honouring the exit. The first version of this loop
            # broke out the moment the process was gone, discarding whatever was
            # still sitting unparsed in the pipe — so a run that fired a skill
            # and finished quickly was recorded as 'neither'. Every negative this
            # harness reports has to be a negative it actually read.
            verdict, buffer = consume(buffer)
            if verdict:
                return verdict
            if exited:
                # Trailing line with no newline.
                if buffer.strip():
                    verdict, _ = consume(buffer + "\n")
                    if verdict:
                        return verdict
                return "neither"
        else:
            return "timeout"
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    return "neither"


def verdict(expected: str, fired: list[str]) -> tuple[bool, str]:
    """An 'either' case passes when exactly one sibling fires, consistently.

    Timed-out and errored runs are set aside rather than counted as negatives,
    and reported alongside the verdict so a case decided on one surviving run
    cannot pass for a clean one.
    """
    aborted = {kind: fired.count(kind) for kind in ("timeout", "error") if kind in fired}
    fired = [f for f in fired if f not in ("timeout", "error")]
    if not fired:
        detail = ", ".join(f"{n} {kind}" for kind, n in aborted.items())
        return False, f"inconclusive: no run reached a verdict ({detail})"
    suffix = (" [" + ", ".join(f"{n} {kind}" for kind, n in aborted.items()) + "]") if aborted else ""
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
    ap.add_argument("--skill-md", action="append", default=[], metavar="SKILL=PATH",
                    help="substitute a SKILL.md for one skill, to A/B a description generation")
    args = ap.parse_args()

    spec = json.loads((REPO / "evals" / "suite-routing.json").read_text())
    cases = [c for c in spec["cases"] if not args.case or c["id"] in args.case]

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        overrides = {}
        for item in args.skill_md:
            skill, _, path = item.partition("=")
            if skill not in SKILLS or not path:
                raise SystemExit(f"--skill-md expects one of {SKILLS} as SKILL=PATH, got {item!r}")
            overrides[skill] = Path(path)
        names = install_skills(root, uuid.uuid4().hex[:8], overrides)

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
