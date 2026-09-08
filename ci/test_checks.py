#!/usr/bin/env python3
"""Self-test for ci/check_skills.py.

A checker that silently stops checking is worse than no checker, and it fails
in the quietest possible way: everything goes green. So each mutation below
breaks the repo in one specific way and asserts that the matching group both
fails and names the problem.

    python ci/test_checks.py
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
COPIED = ["skills", "dist", "conventions", "ci", "evals"]
# Files, not directories: the ledger lives in README.md and the ledger check reads it.
COPIED_FILES = ["README.md"]


def stage(tmp: Path) -> Path:
    root = tmp / "repo"
    root.mkdir()
    for name in COPIED:
        src = REPO / name
        if src.exists():
            shutil.copytree(src, root / name)
    for name in COPIED_FILES:
        src = REPO / name
        if src.exists():
            shutil.copy2(src, root / name)
    return root


def fingerprint(root: Path) -> str:
    """Hash the staged tree, so a mutation that changes nothing can be caught.

    Both of the wording-pinned mutations this file started with went stale the
    first time a description was rewritten: they searched for prose that no
    longer existed, quietly mutated nothing, and the check they were meant to
    exercise passed for the honest reason. A no-op mutation is the self-test
    developing the exact disease it exists to detect.
    """
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def run(root: Path, group: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "ci/check_skills.py", "--only", group],
        cwd=root, capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


# Each mutation returns a substring the failure message must contain.
def break_description_length(root: Path) -> str:
    path = root / "skills/job-underwriter/SKILL.md"
    text = path.read_text()
    fm = re.match(r"^---\n(.*?)\n---", text, re.DOTALL).group(1)
    bloated = re.sub(r"^description:.*$",
                     "description: " + ("x" * 1100),
                     fm, flags=re.MULTILINE)
    path.write_text(text.replace(fm, bloated, 1))
    return "over the 1024 limit"


def break_description_brackets(root: Path) -> str:
    """Brackets go in structurally, so rewording a description cannot defuse this."""
    path = root / "skills/mock-interview/SKILL.md"
    text = path.read_text()
    path.write_text(re.sub(r"^description: ", "description: <b>Prep</b> ", text,
                           count=1, flags=re.MULTILINE))
    return "angle brackets"


def break_name_mismatch(root: Path) -> str:
    """Frontmatter name no longer matches the directory it ships in."""
    path = root / "skills/job-underwriter/SKILL.md"
    path.write_text(path.read_text().replace("name: job-underwriter", "name: underwriter", 1))
    return "does not match its directory"


def break_name_not_kebab(root: Path) -> str:
    """Directory and name agree, but the name is not kebab-case.

    Renaming both is what makes this test the kebab rule rather than the
    directory-match rule, which would otherwise fire first and mask it.
    """
    skill = root / "skills/job-underwriter"
    path = skill / "SKILL.md"
    path.write_text(path.read_text().replace("name: job-underwriter", "name: job_underwriter", 1))
    skill.rename(root / "skills/job_underwriter")
    return "kebab-case"


def break_missing_license(root: Path) -> str:
    (root / "skills/mock-interview/LICENSE").unlink()
    return "no LICENSE"


def break_stale_dist(root: Path) -> str:
    path = root / "skills/job-underwriter/SKILL.md"
    path.write_text(path.read_text() + "\n\nAn edit that was never rebuilt.\n")
    return "stale against source"


def break_unpackaged_file(root: Path) -> str:
    (root / "skills/mock-interview/references/new-reference.md").write_text("# added, never packaged\n")
    return "absent from the build"


def break_zip_root(root: Path) -> str:
    artifact = root / "dist/job-underwriter.skill"
    with zipfile.ZipFile(artifact, "a") as archive:
        archive.writestr("loose-file.md", "not under the skill folder\n")
    return "zip root must be the skill folder"


def break_evals_leaked(root: Path) -> str:
    artifact = root / "dist/mock-interview.skill"
    with zipfile.ZipFile(artifact, "a") as archive:
        archive.writestr("mock-interview/evals/evals.json", "{}\n")
    return "evals/ must be excluded"


def break_mirror_drift(root: Path) -> str:
    path = root / "skills/mock-interview/references/evidence-conventions.md"
    path.write_text(path.read_text().replace("`high`", "`very high`", 1))
    return "drifted from"


def break_evals_empty_expectations(root: Path) -> str:
    path = root / "skills/job-underwriter/evals/evals.json"
    data = json.loads(path.read_text())
    data["evals"][0]["expectations"] = []
    path.write_text(json.dumps(data, indent=2))
    return "passes vacuously"


def break_evals_duplicate_ids(root: Path) -> str:
    path = root / "skills/mock-interview/evals/evals.json"
    data = json.loads(path.read_text())
    data["evals"][1]["id"] = data["evals"][0]["id"]
    path.write_text(json.dumps(data, indent=2))
    return "duplicate eval ids"


def break_routing_route(root: Path) -> str:
    """Point a case at a route the file does not declare.

    The name is derived rather than hard-coded. This mutation used to name a
    then-hypothetical skill, and went quiet the day that skill shipped and the
    route became legitimate — the same staleness the fingerprint guard exists to
    catch, arriving through the one door it cannot watch, since the mutation did
    change the file.
    """
    path = root / "evals/suite-routing.json"
    data = json.loads(path.read_text())
    undeclared = "no-such-skill"
    while undeclared in data["routes"]:
        undeclared += "-x"
    data["cases"][0]["expected"] = undeclared
    path.write_text(json.dumps(data, indent=2))
    return "is not a declared route"


def break_undeclared_parameter(root: Path) -> str:
    """Drop one declared output-discipline parameter from a skill."""
    path = root / "skills/resume-tailor/SKILL.md"
    text = path.read_text()
    mutated = re.sub(r"^sibling_mentions:.*$", "", text, count=1, flags=re.MULTILINE)
    if mutated == text:
        raise SystemExit("break_undeclared_parameter found nothing to remove — it has gone stale")
    path.write_text(mutated)
    return "undeclared output-discipline parameter"


def break_missing_parameter_section(root: Path) -> str:
    """Remove a skill's parameter declarations entirely."""
    path = root / "skills/mock-interview/SKILL.md"
    text = path.read_text()
    mutated = re.sub(r"^## Output discipline\s*$.*?(?=^## )", "", text,
                     count=1, flags=re.MULTILINE | re.DOTALL)
    if mutated == text:
        raise SystemExit("break_missing_parameter_section found nothing to remove — it has gone stale")
    path.write_text(mutated)
    return "no '## Output discipline' section"


def break_ledger_duplicate(root: Path) -> str:
    """Duplicate a Tracked-work entry, the way index-based edits actually did."""
    path = root / "README.md"
    text = path.read_text()
    # Anchor inside the ledger: the first "- **" in the file belongs to the
    # conventions list, and duplicating that one proves nothing.
    section = re.search(r"^## Tracked work\s*$(.*?)(?=^## |\Z)", text,
                        re.MULTILINE | re.DOTALL)
    if not section:
        raise SystemExit("break_ledger_duplicate found no Tracked work section — it has gone stale")
    entry = re.search(r"^- \*\*.+?\*\*.*$", section.group(1), re.MULTILINE)
    if not entry:
        raise SystemExit("break_ledger_duplicate found no ledger entry — it has gone stale")
    path.write_text(text.replace(entry.group(0), entry.group(0) + "\n" + entry.group(0), 1))
    return "duplicate ledger entr"


def break_ledger_superseded(root: Path) -> str:
    """Add an entry whose subject collides with one already there."""
    path = root / "README.md"
    text = path.read_text()
    anchor = "\n- **Routing eval coverage"
    if anchor not in text:
        raise SystemExit("break_ledger_superseded lost its anchor — it has gone stale")
    stale = "\n- **Routing eval coverage — not yet built.** Superseded predecessor left in place."
    path.write_text(text.replace(anchor, stale + anchor, 1))
    return "share a subject"


def break_trigger_boundary(root: Path) -> str:
    """Swap in a plausible description that carries no boundary at all.

    Deleting a specific sentence would tie this mutation to today's wording; the
    whole-line swap keeps it true whatever the description grows into.
    """
    path = root / "skills/job-underwriter/SKILL.md"
    text = path.read_text()
    path.write_text(re.sub(
        r"^description: .*$",
        "description: Evaluate a posted role against a CV and decide whether to pursue it.",
        text, count=1, flags=re.MULTILINE))
    return "reserved boundary"


def break_qualifier_column_missing(root: Path) -> str:
    """Delete the column a skill's qualifier_fields points at.

    The bug this reproduces ran for three skill versions: `reasoning` was in the
    row spec and in the JSON envelope, the compound-cell rule said to put the
    qualifier there, and the rendered table had no such column. `none/low` went
    into the Confidence cell beside it.
    """
    path = root / "skills/job-underwriter/references/dossier-template.md"
    text = path.read_text()
    mutated = text.replace("| Confidence | Gap | Reasoning | Next action |",
                           "| Confidence | Gap | Next action |", 1)
    if mutated == text:
        raise SystemExit("break_qualifier_column_missing found no Reasoning column — it has gone stale")
    path.write_text(mutated)
    return "not a column in any references/ table"


def break_qualifier_field_renamed(root: Path) -> str:
    """Declare a qualifier field the skill's tables do not carry."""
    path = root / "skills/mock-interview/SKILL.md"
    text = path.read_text()
    mutated = text.replace("qualifier_fields: gap-and-bridge language",
                           "qualifier_fields: bridge notes", 1)
    if mutated == text:
        raise SystemExit("break_qualifier_field_renamed found nothing to rename — it has gone stale")
    path.write_text(mutated)
    return "not a column in any references/ table"


CASES: list[tuple[str, str, callable]] = [
    ("frontmatter", "description over the length limit", break_description_length),
    ("frontmatter", "angle brackets in description", break_description_brackets),
    ("frontmatter", "name does not match its directory", break_name_mismatch),
    ("frontmatter", "name not kebab-case", break_name_not_kebab),
    ("frontmatter", "missing per-skill LICENSE", break_missing_license),
    ("package", "source edited without a rebuild", break_stale_dist),
    ("package", "new source file not packaged", break_unpackaged_file),
    ("package", "zip not rooted at the skill folder", break_zip_root),
    ("package", "evals leaked into the package", break_evals_leaked),
    ("mirrors", "mirror drifted from canonical", break_mirror_drift),
    ("evals", "eval with no expectations", break_evals_empty_expectations),
    ("evals", "duplicate eval ids", break_evals_duplicate_ids),
    ("evals", "routing case with an undeclared route", break_routing_route),
    ("triggers", "description lost its reserved boundary", break_trigger_boundary),
    ("ledger", "a duplicated ledger entry", break_ledger_duplicate),
    ("ledger", "a superseded entry left beside its successor", break_ledger_superseded),
    ("parameters", "a declared parameter dropped", break_undeclared_parameter),
    ("parameters", "the parameter section removed", break_missing_parameter_section),
    ("columns", "the column a qualifier_field points at deleted", break_qualifier_column_missing),
    ("columns", "a qualifier_field naming no column at all", break_qualifier_field_renamed),
]



def main() -> int:
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)

        clean = tmp / "clean"
        clean.mkdir()
        root = stage(clean)
        code, out = run(root, "frontmatter")
        if code != 0:
            print("clean repo does not pass its own checks:\n" + out)
            return 1
        print("  ok   baseline: clean repo passes\n")

        failed = []
        for index, (group, label, mutate) in enumerate(CASES):
            work = tmp / f"case{index}"
            work.mkdir()
            root = stage(work)
            before = fingerprint(root)
            needle = mutate(root)
            if fingerprint(root) == before:
                failed.append(f"{group}/{label}: mutation changed nothing — it has gone stale")
                print(f"  FAIL {group}: {label} — mutation is a no-op")
                shutil.rmtree(work)
                continue
            code, out = run(root, group)
            if code == 0:
                failed.append(f"{group}/{label}: check PASSED but should have failed")
                print(f"  FAIL {group}: {label} — not detected")
            elif needle not in out:
                failed.append(f"{group}/{label}: failed, but message lacked '{needle}'")
                print(f"  FAIL {group}: {label} — detected, wrong message")
            else:
                print(f"  ok   {group}: {label} — detected")
            shutil.rmtree(work)

        print()
        if failed:
            print(f"{len(failed)} self-test failure(s):")
            for line in failed:
                print(f"  {line}")
            return 1
        print(f"All {len(CASES)} mutations detected.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
