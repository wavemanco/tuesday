#!/usr/bin/env python3
"""Find expectations that fail across independent run-sets.

`run_fixtures.py` classifies a failure within one set of runs: deterministic if it
failed every run, intermittent otherwise. That is the right call inside a set and
it is blind across them. An expectation that fails once in every three runs looks
intermittent in each set — noise, leave it — while a base rate of one in three,
holding steady across four independent sets, is a stable defect at a measurable
rate. The runner cannot see the difference. This can.

It spends no model calls: it reads grade JSON and `*.checks.json` that clean-room
runs already wrote.

    python evals/recurring.py /path/to/clean-room-dirs/*

What it compares, and what it will not:

- **A grader verdict is compared only with verdicts on the same words.** Grade
  files record the sha256 of every expectation they graded, and two verdicts on
  #14 count as the same question only when the hashes match — an expectation
  rewritten between sets is a different question, and pooling its old failures
  with its new passes measured the rewrite, not the skill. Grade files written
  before hashes existed are compared by position, as they always were, and the
  output says so beside every row that rests on them.
- **A check is keyed by what it checks.** Deterministic check failures are read
  from `*.checks.json` under (`chk`, check, target), never mixed into expectation
  numbers. A run the harness marked invalid is skipped; a check that could not run
  on a run (no research record) has no entry, so it is skipped rather than
  counted either way.
- **Modes are kept apart.** A fixture run in a canned and a denied room asks two
  questions; the mode is part of the key.

Two things it deliberately does not do. It does not weight sets by age, so a
failure fixed three sets ago still counts — the output names the sets, and reading
them is the analyst's job. And it does not decide anything: a high recurrence
rate on an expectation that was rewritten between sets means the expectation
changed, not that the skill did.
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

STEM = re.compile(r"^(?P<fixture>.+?)(?:\.(?P<mode>denied|canned))?\.run(?P<run>\d+)\.")


def mode_of(data: dict, path: Path) -> str:
    if data.get("mode"):
        return data["mode"]
    match = STEM.match(path.name)
    return (match and match.group("mode")) or "denied"


def scan(dirs: list[Path]) -> dict:
    """Collect per-item outcomes, keyed by (skill, eval id, mode, item, expectation hash)."""
    seen: dict = collections.defaultdict(
        lambda: {"sets": set(), "failed_sets": set(), "why": "", "runs": 0, "fails": 0})
    for directory in dirs:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.grade-*.json")):
            try:
                data = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            # A grade that errored graded nothing; counting it would repeat the
            # mistake this suite has now made four times.
            if data.get("harness_invalid") or not data.get("verdicts"):
                continue
            hashes = data.get("expectation_sha256") or {}
            mode = mode_of(data, path)
            for verdict in data["verdicts"]:
                if verdict.get("verdict") not in ("PASS", "FAIL"):
                    continue
                n = verdict.get("n")
                key = (data.get("skill"), data.get("id"), mode, n, hashes.get(str(n)))
                record(seen[key], directory.name, verdict.get("verdict") == "FAIL",
                       verdict.get("why", ""))
        for path in sorted(directory.glob("*.checks.json")):
            try:
                data = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if data.get("status") == "harness-invalid":
                continue
            mode = mode_of(data, path)
            outcomes: dict = {}
            for item in data.get("checks", []):
                if item.get("verdict") not in ("PASS", "FAIL"):
                    continue
                key = (data.get("skill"), data.get("id"), mode,
                       ("chk", item.get("check"), item.get("target")), "check")
                failed, why = outcomes.get(key, (False, ""))
                if item["verdict"] == "FAIL" and not failed:
                    failed, why = True, item.get("why", "")
                outcomes[key] = (failed, why)
            for key, (failed, why) in outcomes.items():
                record(seen[key], directory.name, failed, why)
    return seen


def record(entry: dict, set_name: str, failed: bool, why: str) -> None:
    entry["sets"].add(set_name)
    entry["runs"] += 1
    if failed:
        entry["failed_sets"].add(set_name)
        entry["fails"] += 1
        if not entry["why"]:
            entry["why"] = " ".join(str(why).split())


def label(item) -> str:
    if isinstance(item, tuple):
        return ":".join(map(str, item))
    return f"#{item}"


def main() -> int:
    args = [Path(a) for a in sys.argv[1:]]
    if not args:
        print(__doc__)
        return 2
    seen = scan(args)
    if not seen:
        print("no grade or check files found in the directories given")
        return 2

    rows = []
    for (skill, eval_id, mode, item, digest), entry in seen.items():
        sets, failed = len(entry["sets"]), len(entry["failed_sets"])
        if sets < 2 or failed < 2:
            continue
        rate = entry["fails"] / entry["runs"] if entry["runs"] else 0
        rows.append((failed / sets, rate, str(skill), str(eval_id), mode, label(item), digest,
                     failed, sets, entry["fails"], entry["runs"], entry["why"],
                     sorted(entry["failed_sets"]), sorted(entry["sets"])))
    rows.sort(reverse=True)

    print(f"{len({d.name for d in args if d.is_dir()})} run-set(s) scanned\n")
    if not rows:
        print("No expectation or check failed in more than one independent run-set.")
        return 0

    print("Failed in more than one independent run-set — a stable rate, not noise:\n")
    by_position = 0
    for (share, rate, skill, eval_id, mode, item, digest, failed, sets, fails, runs, why,
         bad_sets, all_sets) in rows:
        verdict = "persistent" if share == 1.0 else "recurring"
        if digest is None:
            by_position += 1
            basis = "  (compared by position: these grade files record no expectation hash)"
        elif digest == "check":
            basis = ""
        else:
            basis = f"  (expectation {digest[:10]})"
        print(f"  [{verdict}] {skill} eval {eval_id} [{mode}] {item}{basis}")
        print(f"      {failed}/{sets} run-sets, {fails}/{runs} graded runs ({rate:.0%})")
        # Naming the sets is the whole caveat made usable: a failure appearing in
        # sets from both sides of a fix survived it; one appearing only in earlier
        # sets did not.
        clean = [s for s in all_sets if s not in bad_sets]
        print(f"      failed in: {', '.join(bad_sets)}")
        if clean:
            print(f"      clean in:  {', '.join(clean)}")
        print(f"      {why[:150]}\n")

    print(f"{len(rows)} item(s) failing across sets.\n")
    if by_position:
        print(f"{by_position} of them rest on grade files with no expectation hash, compared by\n"
              "position: if an expectation was rewritten between those sets, the row pools two\n"
              "different questions.\n")
    print("Read this against what changed between the sets. A rule fixed three sets\n"
          "ago still appears here, and an expectation rewritten between sets is a\n"
          "different question being asked, not a skill that got worse.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
