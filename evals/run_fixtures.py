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

Runs are adaptive. Every fixture runs once; a fixture that fails something runs
twice more, and each failing expectation is then reported as deterministic (it
failed every run) or intermittent (it did not). That distinction is the whole
point. One fixture in this suite has scored 12/12, 13/13, 13/13 and 9/13 on the
same skill, and a single run cannot tell that from a defect — while running
everything three times would triple the cost of the expensive half to learn
nothing about the fixtures that were already clean, and would raise confidence
in a wrong expectation exactly as fast as in a right one.

Usage:
    python evals/run_fixtures.py --out /tmp/clean-room
    python evals/run_fixtures.py --skill job-underwriter --eval 3 --out /tmp/cr
    python evals/run_fixtures.py --out /tmp/cr --retry-runs 0   # one run, no retries
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
SKILLS = ["job-underwriter", "mock-interview", "resume-tailor"]

GRADER_PROMPT = """You are grading one response against a fixed list of expectations.

Grade adversarially. Your job is to find where the response falls short, not to
give it the benefit of the doubt. A partial satisfaction is a FAIL. An
expectation the response gestures at but does not actually do is a FAIL. Do not
reward length, confidence, or good intentions. You are not being asked whether
the response is good; you are being asked whether each specific expectation is
met by text actually present in the response.

You have not seen the skill that produced this and you do not need to. Judge
only the text in front of you, never what some other document might say.

Four rules that are not about being lenient, but about grading the right thing:

- Your one-sentence reason must justify the verdict you give. If your reasoning
  arrives at "this is met", the verdict is PASS. Never write FAIL above a reason
  that concludes otherwise.
- An expectation carrying a condition — "where research ran", "if X appears",
  "if the status is Y" — is PASS when the condition did not occur. A response is
  not failed for skipping something its own expectation made conditional.
- The response may have been produced without web access. Declining to research,
  saying so plainly, and carrying the consequence into the analysis is correct
  behaviour and passes, unless the expectation specifically demands research.
- Every expectation is about something the response should DO. Do not fail one
  because the response also did something else you would have done differently.

## The request that was made

{prompt}

## The response to grade

This is everything the response produced. Where it delivered by writing a file, that file's full contents appear below the chat text under a `----- file the response produced -----` marker, and it counts exactly as if it had been written inline.

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


def claude(prompt: str, cwd: Path, timeout: int, model: str | None,
           stream: bool = True) -> tuple[str, bool]:
    """Run one `claude -p`; return (assistant text, whether a Skill tool fired).

    Raises RuntimeError when the CLI declined to answer, so a limit message can
    never be mistaken for a short response.
    """
    cmd = ["claude", "-p", "--output-format", "stream-json", "--verbose"] if stream \
        else ["claude", "-p", "--output-format", "text"]
    if model:
        cmd += ["--model", model]
    # CLAUDECODE guards interactive terminal nesting; a subprocess run is safe.
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    proc = subprocess.run(cmd, input=prompt, cwd=str(cwd), env=env,
                          capture_output=True, text=True, timeout=timeout)
    if not stream:
        if cli_failed(proc.stdout, proc.returncode):
            raise RuntimeError(f"CLI declined: {proc.stdout.strip()[:200] or proc.stderr.strip()[:200]}")
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
    text = "\n".join(chunks)
    if cli_failed(text, proc.returncode):
        raise RuntimeError(f"CLI declined: {text.strip()[:200] or proc.stderr.strip()[:200]}")
    return text, fired


TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".csv"}
MAX_ARTIFACT = 200_000


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


def execute(skill: str, case: dict, out: Path, run: int, timeout: int,
            model: str | None) -> dict:
    """Run one fixture in a clean room and save the response plus what it wrote."""
    run_id = uuid.uuid4().hex[:8]
    room = out / "rooms" / f"{skill}-{case['id']}-{run_id}"
    room.mkdir(parents=True, exist_ok=True)
    name = install_one(room, skill, run_id)
    skill_dir = room / ".claude" / "skills" / name

    try:
        text, fired = claude(case["prompt"], room, timeout, model)
    except RuntimeError as exc:
        print(f"  SKIPPED {skill} eval {case['id']} (run {run}): {exc}", flush=True)
        meta = {"skill": skill, "id": case["id"], "run": run, "error": str(exc)}
        (out / f"{skill}-{case['id']}.run{run}.meta.json").write_text(
            json.dumps(meta, indent=2) + "\n")
        return meta
    nudged = False
    if not fired:
        # The skill not firing is the routing eval's finding, not this one's.
        # Here it would leave the expectations ungraded, so the fixture is re-run
        # with the skill named. Recorded, because a nudged run is weaker evidence.
        nudged = True
        text, fired = claude(f"Use the {name} skill for this.\n\n{case['prompt']}",
                             room, timeout, model)

    artifacts = collect_artifacts(room, skill_dir)
    if artifacts:
        text += "\n\n" + "\n\n".join(
            f"----- file the response produced: {name_} -----\n{content}"
            for name_, content in artifacts)

    body = out / f"{skill}-{case['id']}.run{run}.md"
    body.write_text(text)
    meta = {"skill": skill, "id": case["id"], "run": run, "triggered_unprompted": not nudged,
            "skill_fired": fired, "chars": len(text), "response_file": body.name,
            "artifacts": [a[0] for a in artifacts]}
    (out / f"{skill}-{case['id']}.run{run}.meta.json").write_text(
        json.dumps(meta, indent=2) + "\n")
    print(f"  ran {skill} eval {case['id']} (run {run}): {len(text)} chars"
          f"{f', {len(artifacts)} file(s)' if artifacts else ''}"
          f"{'' if not nudged else ' (needed a nudge to fire)'}", flush=True)
    return meta


def parse_verdicts(text: str) -> dict:
    """Recover verdicts from a grader reply, whole or truncated.

    A long grade can be cut off mid-object. Read strictly, that yields zero
    verdicts, and a summary that counts missing verdicts as failures turns one
    truncated reply into a fixture where everything failed — the same mistake the
    routing harness made when it counted an errored run as a negative. So the
    whole object is tried first, then individual verdict objects are salvaged,
    and a reply that yields none is marked errored rather than scored.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            whole = json.loads(match.group(0))
            if isinstance(whole.get("verdicts"), list):
                return whole
        except json.JSONDecodeError:
            pass

    salvaged = []
    for obj in re.finditer(r'\{\s*"n"\s*:\s*(\d+).*?"verdict"\s*:\s*"(PASS|FAIL)".*?\}',
                           text, re.DOTALL):
        try:
            salvaged.append(json.loads(obj.group(0)))
        except json.JSONDecodeError:
            salvaged.append({"n": int(obj.group(1)), "verdict": obj.group(2), "why": "(salvaged)"})
    if salvaged:
        return {"verdicts": salvaged, "truncated": True}
    return {"error": "grader returned no usable verdicts", "raw": text[:2000], "verdicts": []}


def grade(skill: str, case: dict, out: Path, run: int, grader: int, timeout: int,
          model: str | None) -> dict:
    """Score one saved response against its expectations."""
    body_path = out / f"{skill}-{case['id']}.run{run}.md"
    if not body_path.exists():
        # Silent here would drop the run out of the log entirely, leaving a reader
        # to infer from a gap in the grader numbering that anything happened.
        reason = "no response to grade — the execution was skipped"
        print(f"  no verdicts for {skill} eval {case['id']} (run {run}, grader {grader}): {reason}",
              flush=True)
        return {"skill": skill, "id": case["id"], "run": run, "grader": grader,
                "error": reason, "verdicts": []}
    body = body_path.read_text()
    expectations = "\n".join(f"{i}. {e}" for i, e in enumerate(case["expectations"], 1))
    prompt = GRADER_PROMPT.format(prompt=case["prompt"], response=body,
                                  expectations=expectations)
    with_room = out / "grading"
    with_room.mkdir(parents=True, exist_ok=True)
    try:
        text, _ = claude(prompt, with_room, timeout, model, stream=False)
    except RuntimeError as exc:
        text = ""
        print(f"  SKIPPED grading {skill} eval {case['id']} (run {run}, grader {grader}): {exc}",
              flush=True)

    result = parse_verdicts(text)

    result["skill"], result["id"] = skill, case["id"]
    result["run"], result["grader"] = run, grader
    (out / f"{skill}-{case['id']}.run{run}.grade-{grader}.json").write_text(
        json.dumps(result, indent=2) + "\n")
    verdicts = result.get("verdicts", [])
    # A grade that produced nothing is not a grade of zero. The SKIPPED line above
    # already said what happened; printing "0/12" beside it is the same mistake
    # this harness has now made five times, in the reporting rather than the data.
    if result.get("error") or not verdicts:
        print(f"  no verdicts for {skill} eval {case['id']} (run {run}, grader {grader}): "
              f"{result.get('error', 'grader returned nothing usable')}", flush=True)
        return result
    passed = sum(1 for v in verdicts if v.get("verdict") == "PASS")
    print(f"  graded {skill} eval {case['id']} (run {run}, grader {grader}): "
          f"{passed}/{len(case['expectations'])}", flush=True)
    return result


def cases_for(skill: str, only: list[int]) -> list[dict]:
    spec = json.loads((REPO / "skills" / skill / "evals" / "evals.json").read_text())
    return [c for c in spec["evals"] if not only or c["id"] in only]


def failed_in_run(results: list[dict], skill: str, eval_id: int, run: int) -> set[int]:
    """Expectations that failed a given run — one grader failing is enough.

    The graders are adversarial and disagree usefully; every defect worth fixing
    in this suite so far was found by the one that dissented. Requiring both to
    fail before an expectation counts as failed would discard exactly that.
    """
    failed = set()
    for r in results:
        if (r.get("skill"), r.get("id"), r.get("run")) != (skill, eval_id, run):
            continue
        if r.get("error"):
            continue          # a grader that returned nothing graded nothing
        for v in r.get("verdicts", []):
            if v.get("verdict") == "FAIL":
                failed.add(v.get("n"))
    return failed


def why_for(results: list[dict], skill: str, eval_id: int, n: int) -> str:
    for r in results:
        if r.get("skill") == skill and r.get("id") == eval_id:
            for v in r.get("verdicts", []):
                if v.get("n") == n and v.get("verdict") == "FAIL":
                    return " ".join(str(v.get("why", "")).split())
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", action="append", choices=SKILLS, default=[])
    ap.add_argument("--eval", type=int, action="append", default=[])
    ap.add_argument("--out", required=True, help="directory for responses and grades")
    ap.add_argument("--graders", type=int, default=2)
    ap.add_argument("--runs", type=int, default=1, help="runs per fixture in the first pass")
    ap.add_argument("--retry-runs", type=int, default=2,
                    help="extra runs for any fixture that failed something; 0 disables")
    ap.add_argument("--model", default=None)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--skip-execute", action="store_true", help="grade saved responses")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    skills = args.skill or SKILLS
    work = [(s, c) for s in skills for c in cases_for(s, args.eval)]
    results: list[dict] = []
    runs_done: dict[tuple[str, int], list[int]] = {(s, c["id"]): [] for s, c in work}

    def pass_over(jobs: list[tuple[str, dict, int]], label: str) -> None:
        """Execute (unless skipping) and grade one batch of (skill, case, run)."""
        if not jobs:
            return
        if not args.skip_execute:
            print(f"\n{label}: executing {len(jobs)} fixture run(s)")
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                list(pool.map(lambda j: execute(j[0], j[1], out, j[2], args.timeout,
                                               args.model), jobs))
        print(f"\n{label}: grading {len(jobs)} response(s), {args.graders} grader(s) each")
        grade_jobs = [(s, c, r, g) for s, c, r in jobs
                      for g in range(1, args.graders + 1)]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            results.extend(pool.map(
                lambda j: grade(j[0], j[1], out, j[2], j[3], args.timeout, args.model),
                grade_jobs))
        for skill, case, run in jobs:
            runs_done[(skill, case["id"])].append(run)

    if args.skip_execute:
        # Grade whatever runs are already on disk.
        first = []
        for skill, case in work:
            for body in sorted(out.glob(f"{skill}-{case['id']}.run*.md")):
                first.append((skill, case, int(body.name.split(".run")[1].split(".")[0])))
        pass_over(first, "saved runs")
    else:
        pass_over([(s, c, r) for s, c in work for r in range(args.runs)], "first pass")

        # Only fixtures that failed something earn more runs. A clean fixture is
        # not evidence of reliability, but it is not a lead either, and spending
        # three executions on it buys a number nobody acts on.
        retries = []
        for skill, case in work:
            if not args.retry_runs:
                continue
            if any(failed_in_run(results, skill, case["id"], r) for r in range(args.runs)):
                retries += [(skill, case, args.runs + i) for i in range(args.retry_runs)]
        if retries:
            print(f"\n{len({(s, c['id']) for s, c, _ in retries})} fixture(s) failed "
                  f"something; re-running to tell a defect from a draw")
        pass_over(retries, "retry pass")

    print("\n--- clean-room results ---")
    deterministic = intermittent = 0
    for skill, case in work:
        runs = sorted(runs_done[(skill, case["id"])])
        total = len(case["expectations"])
        scores = []
        for run in runs:
            per_grader = []
            for g in range(1, args.graders + 1):
                got = next((r for r in results
                            if (r.get("skill"), r.get("id"), r.get("run"), r.get("grader"))
                            == (skill, case["id"], run, g)), {})
                if got.get("error"):
                    per_grader.append("errored")
                    continue
                passed = sum(1 for v in got.get("verdicts", []) if v.get("verdict") == "PASS")
                per_grader.append(f"{passed}/{total}"
                                  + ("*" if got.get("truncated") else ""))
            scores.append(f"run {run}: " + ", ".join(per_grader))
        print(f"  {skill} eval {case['id']}  " + "   ".join(scores))

        failed_by_run = {r: failed_in_run(results, skill, case["id"], r) for r in runs}
        for n in sorted({n for s in failed_by_run.values() for n in s}):
            hits = sum(1 for s in failed_by_run.values() if n in s)
            kind = "deterministic" if hits == len(runs) else "intermittent"
            deterministic += kind == "deterministic"
            intermittent += kind == "intermittent"
            print(f"      #{n:<3} {kind:<13} {hits}/{len(runs)} run(s)  "
                  f"{why_for(results, skill, case['id'], n)[:150]}")

    print(f"\n{deterministic} deterministic failure(s), {intermittent} intermittent")
    if intermittent and len(work):
        print("An intermittent failure is a reliability finding, not a defect to patch: "
              "the rule fired once and not another time, so rewriting it is as likely to "
              "move the number by luck as by fixing anything.")
    return 0 if not (deterministic or intermittent) else 1


if __name__ == "__main__":
    sys.exit(main())
