#!/usr/bin/env python3
"""Run each skill's own eval fixtures in a clean room, then grade them.

The problem this solves is authoring context. A fixture graded in the session
that wrote the skill is graded by a reader who already knows what the skill
meant — who supplies the charitable reading, and scores the intent rather than
the output. This runner puts the fixture in front of a session that has only
the skill installed and nothing else: no repository, no spec, no conversation
about what the skill was supposed to do.

Two phases, separable so a long execute pass is graded without re-running it:

    execute   one throwaway project per skill, containing only that skill;
              each fixture prompt is sent raw and the full response saved.
    grade     each response is scored against its own expectations by graders
              that never see the skill, only the response and the expectations.

Graders are deliberately adversarial and deliberately more than one. Every
defect worth fixing in this suite so far was found by the grader that disagreed,
and two of them were found in responses another grader had passed outright.

Usage:
    python evals/run_fixtures.py --out /tmp/clean-room
    python evals/run_fixtures.py --skill job-underwriter --eval 3 --out /tmp/cr
    python evals/run_fixtures.py --out /tmp/cr --skip-execute   # re-grade only
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = ["job-underwriter", "mock-interview"]

GRADER_PROMPT = """You are grading one response against a fixed list of expectations.

Grade adversarially. Your job is to find where the response falls short, not to
give it the benefit of the doubt. A partial satisfaction is a FAIL. An
expectation the response gestures at but does not actually do is a FAIL. Do not
reward length, confidence, or good intentions. You are not being asked whether
the response is good; you are being asked whether each specific expectation is
met by text actually present in the response.

You have not seen the skill that produced this and you do not need to. Judge
only what is in front of you.

## The request that was made

{prompt}

## The response to grade

{response}

## The expectations

{expectations}

Return ONLY a JSON object, no prose around it:

{{"verdicts": [{{"n": 1, "verdict": "PASS" or "FAIL", "why": "one sentence, quoting the response where it matters"}}, ...]}}

One entry per expectation, numbered from 1 in the order given.
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


def claude(prompt: str, cwd: Path, timeout: int, model: str | None,
           stream: bool = True) -> tuple[str, bool]:
    """Run one `claude -p`; return (assistant text, whether a Skill tool fired)."""
    cmd = ["claude", "-p", "--output-format", "stream-json", "--verbose"] if stream \
        else ["claude", "-p", "--output-format", "text"]
    if model:
        cmd += ["--model", model]
    # CLAUDECODE guards interactive terminal nesting; a subprocess run is safe.
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    proc = subprocess.run(cmd, input=prompt, cwd=str(cwd), env=env,
                          capture_output=True, text=True, timeout=timeout)
    if not stream:
        return proc.stdout, False

    chunks, fired = [], False
    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "assistant":
            continue
        for item in event.get("message", {}).get("content", []):
            if item.get("type") == "text":
                chunks.append(item["text"])
            elif item.get("type") == "tool_use" and item.get("name") == "Skill":
                fired = True
    return "\n".join(chunks), fired


def execute(skill: str, case: dict, out: Path, timeout: int, model: str | None) -> dict:
    """Run one fixture in a clean room and save the response."""
    run_id = uuid.uuid4().hex[:8]
    room = out / "rooms" / f"{skill}-{case['id']}-{run_id}"
    room.mkdir(parents=True, exist_ok=True)
    name = install_one(room, skill, run_id)

    text, fired = claude(case["prompt"], room, timeout, model)
    nudged = False
    if not fired:
        # The skill not firing is the routing eval's finding, not this one's.
        # Here it would leave the expectations ungraded, so the fixture is re-run
        # with the skill named. Recorded, because a nudged run is weaker evidence.
        nudged = True
        text, fired = claude(f"Use the {name} skill for this.\n\n{case['prompt']}",
                             room, timeout, model)

    body = out / f"{skill}-{case['id']}.md"
    body.write_text(text)
    meta = {"skill": skill, "id": case["id"], "triggered_unprompted": not nudged,
            "skill_fired": fired, "chars": len(text), "response_file": body.name}
    (out / f"{skill}-{case['id']}.meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    shutil.rmtree(room, ignore_errors=True)
    print(f"  ran {skill} eval {case['id']}: {len(text)} chars"
          f"{'' if not nudged else ' (needed a nudge to fire)'}", flush=True)
    return meta


def grade(skill: str, case: dict, out: Path, grader: int, timeout: int,
          model: str | None) -> dict:
    """Score one saved response against its expectations."""
    body = (out / f"{skill}-{case['id']}.md").read_text()
    expectations = "\n".join(f"{i}. {e}" for i, e in enumerate(case["expectations"], 1))
    prompt = GRADER_PROMPT.format(prompt=case["prompt"], response=body,
                                  expectations=expectations)
    with_room = out / "grading"
    with_room.mkdir(parents=True, exist_ok=True)
    text, _ = claude(prompt, with_room, timeout, model, stream=False)

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        result = {"error": "grader returned no JSON", "raw": text[:2000]}
    else:
        try:
            result = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            result = {"error": f"grader JSON did not parse: {exc}", "raw": text[:2000]}

    result["skill"], result["id"], result["grader"] = skill, case["id"], grader
    (out / f"{skill}-{case['id']}.grade-{grader}.json").write_text(
        json.dumps(result, indent=2) + "\n")
    verdicts = result.get("verdicts", [])
    passed = sum(1 for v in verdicts if v.get("verdict") == "PASS")
    print(f"  graded {skill} eval {case['id']} (grader {grader}): "
          f"{passed}/{len(case['expectations'])}", flush=True)
    return result


def cases_for(skill: str, only: list[int]) -> list[dict]:
    spec = json.loads((REPO / "skills" / skill / "evals" / "evals.json").read_text())
    return [c for c in spec["evals"] if not only or c["id"] in only]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", action="append", choices=SKILLS, default=[])
    ap.add_argument("--eval", type=int, action="append", default=[])
    ap.add_argument("--out", required=True, help="directory for responses and grades")
    ap.add_argument("--graders", type=int, default=2)
    ap.add_argument("--model", default=None)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--skip-execute", action="store_true", help="grade saved responses")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    skills = args.skill or SKILLS
    work = [(s, c) for s in skills for c in cases_for(s, args.eval)]

    if not args.skip_execute:
        print(f"executing {len(work)} fixture(s) in clean rooms")
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(lambda job: execute(job[0], job[1], out, args.timeout, args.model), work))

    print(f"\ngrading {len(work)} response(s) with {args.graders} grader(s) each")
    jobs = [(s, c, g) for s, c in work for g in range(1, args.graders + 1)]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(
            lambda job: grade(job[0], job[1], out, job[2], args.timeout, args.model), jobs))

    print("\n--- clean-room results ---")
    failures = 0
    for skill, case in work:
        line = [f"{skill} eval {case['id']}"]
        for grader in range(1, args.graders + 1):
            got = next((r for r in results if r["skill"] == skill and r["id"] == case["id"]
                        and r["grader"] == grader), {})
            verdicts = got.get("verdicts", [])
            passed = sum(1 for v in verdicts if v.get("verdict") == "PASS")
            total = len(case["expectations"])
            failures += total - passed
            line.append(f"grader {grader}: {passed}/{total}")
        print("  " + "  ".join(line))
    print(f"\n{failures} expectation-level failure(s) across all graders")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
