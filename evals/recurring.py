#!/usr/bin/env python3
"""Find expectations that fail across independent run-sets.

`run_fixtures.py` classifies a failure within one set of runs: deterministic if it
failed every run, intermittent otherwise. That is the right call inside a set and
it is blind across them. An expectation that fails once in every three runs looks
intermittent in each set — noise, leave it — while a base rate of one in three,
holding steady across four independent sets, is a stable defect at a measurable
rate. The runner cannot see the difference. This can.

It spends no model calls: it reads grade JSON that clean-room runs already wrote.

    python evals/recurring.py /path/to/clean-room-dirs/*

Two things it deliberately does not do. It does not weight sets by age, so a
failure fixed three sets ago still counts — the output names the sets, and reading
them is the analyst's job. And it does not decide anything: a high recurrence
rate on an expectation that was rewritten between sets means the expectation
changed, not that the skill did.
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path


def scan(dirs: list[Path]) -> dict:
    """Collect per-expectation outcomes, keyed by (skill, eval id, expectation)."""
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
            if data.get("error") or not data.get("verdicts"):
                continue
            for verdict in data["verdicts"]:
                key = (data.get("skill"), data.get("id"), verdict.get("n"))
                entry = seen[key]
                entry["sets"].add(directory.name)
                entry["runs"] += 1
                if verdict.get("verdict") == "FAIL":
                    entry["failed_sets"].add(directory.name)
                    entry["fails"] += 1
                    if not entry["why"]:
                        entry["why"] = " ".join(str(verdict.get("why", "")).split())
    return seen


def main() -> int:
    args = [Path(a) for a in sys.argv[1:]]
    if not args:
        print(__doc__)
        return 2
    seen = scan(args)
    if not seen:
        print("no grade files found in the directories given")
        return 2

    rows = []
    for (skill, eval_id, n), entry in seen.items():
        sets, failed = len(entry["sets"]), len(entry["failed_sets"])
        if sets < 2 or failed < 2:
            continue
        rate = entry["fails"] / entry["runs"] if entry["runs"] else 0
        rows.append((failed / sets, rate, skill, eval_id, n, failed, sets,
                     entry["fails"], entry["runs"], entry["why"],
                     sorted(entry["failed_sets"]), sorted(entry["sets"])))
    rows.sort(reverse=True)

    print(f"{len({d.name for d in args if d.is_dir()})} run-set(s) scanned\n")
    if not rows:
        print("No expectation failed in more than one independent run-set.")
        return 0

    print("Failed in more than one independent run-set — a stable rate, not noise:\n")
    for (share, rate, skill, eval_id, n, failed, sets, fails, runs, why,
         bad_sets, all_sets) in rows:
        verdict = "persistent" if share == 1.0 else "recurring"
        print(f"  [{verdict}] {skill} eval {eval_id} #{n}")
        print(f"      {failed}/{sets} run-sets, {fails}/{runs} graded runs ({rate:.0%})")
        # Naming the sets is the whole caveat made usable: a failure appearing in
        # sets from both sides of a fix survived it; one appearing only in earlier
        # sets did not.
        clean = [s for s in all_sets if s not in bad_sets]
        print(f"      failed in: {', '.join(bad_sets)}")
        if clean:
            print(f"      clean in:  {', '.join(clean)}")
        print(f"      {why[:150]}\n")

    print(f"{len(rows)} expectation(s) failing across sets.\n")
    print("Read this against what changed between the sets. A rule fixed three sets\n"
          "ago still appears here, and an expectation rewritten between sets is a\n"
          "different question being asked, not a skill that got worse.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
