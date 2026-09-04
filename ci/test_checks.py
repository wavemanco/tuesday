#!/usr/bin/env python3
"""Self-test for ci/check_skills.py.

A checker that silently stops checking is worse than no checker, and it fails
in the quietest possible way: everything goes green. So each mutation below
breaks the repo in one specific way and asserts that the matching group both
fails and names the problem.

    python ci/test_checks.py
"""

from __future__ import annotations

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


def stage(tmp: Path) -> Path:
    root = tmp / "repo"
    root.mkdir()
    for name in COPIED:
        src = REPO / name
        if src.exists():
            shutil.copytree(src, root / name)
    return root


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
    path = root / "skills/mock-interview/SKILL.md"
    text = path.read_text()
    path.write_text(text.replace("Generate a personalized", "Generate a <b>personalized</b>", 1))
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
    path = root / "evals/suite-routing.json"
    data = json.loads(path.read_text())
    data["cases"][0]["expected"] = "resume-tailor"
    path.write_text(json.dumps(data, indent=2))
    return "is not a declared route"


def break_trigger_boundary(root: Path) -> str:
    path = root / "skills/job-underwriter/SKILL.md"
    text = path.read_text()
    path.write_text(text.replace(
        "and not for interview rehearsal or prep packs (that is rehearsal, not evaluation).",
        "and it is candidate-side only.", 1))
    return "reserved boundary"


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
            needle = mutate(root)
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
