#!/usr/bin/env python3
"""Repository checks for the Tuesday skill suite.

Deliberately self-contained: no third-party imports, and no dependency on
skill-creator or any other tooling outside this repo. Those live in whatever
session happens to be running and have already moved once; a check that can
vanish underneath CI is not a check.

Run everything:      python ci/check_skills.py
Run one group:       python ci/check_skills.py --only mirrors

Groups:
  frontmatter  SKILL.md frontmatter is present, well-formed, and within the
               limits the Skills API enforces on upload
  package      each dist/<skill>.skill matches its source, is rooted at the
               skill folder, and excludes evals/
  mirrors      every references/ mirror is byte-identical to its canonical
               file once the synced-from header is stripped
  evals        every evals JSON parses and carries the fields the runners read
  triggers     each skill's description carries the negative boundary the
               interaction grammar's trigger-hygiene table reserves for it
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO / "skills"
DIST = REPO / "dist"
CONVENTIONS = REPO / "conventions"

# Mirrors excluded from packaging, matching the packager's own behaviour.
ROOT_EXCLUDED = {"evals"}
EXCLUDED_ANYWHERE = {"__pycache__", "node_modules"}
EXCLUDED_FILES = {".DS_Store"}

# Limits the Skills API enforces at upload time.
MAX_NAME = 64
MAX_DESCRIPTION = 1024
ALLOWED_FRONTMATTER = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}

SYNCED_HEADER = re.compile(r"\A<!--\s*SYNCED FROM:\s*(?P<path>\S+).*?-->\n+", re.DOTALL)

failures: list[str] = []
checks_run = 0


def fail(group: str, message: str) -> None:
    failures.append(f"[{group}] {message}")


def ok(group: str, message: str) -> None:
    global checks_run
    checks_run += 1
    print(f"  ok   {group}: {message}")


def skills() -> list[Path]:
    return sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir() and (p / "SKILL.md").exists())


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Minimal frontmatter reader — avoids a PyYAML dependency in CI.

    Handles the flat `key: value` frontmatter these skills use, including
    values that run to the end of the line and contain colons.
    """
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return None
    fields: dict[str, str] = {}
    key = None
    for line in match.group(1).split("\n"):
        header = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
        if header:
            key = header.group(1)
            fields[key] = header.group(2).strip()
        elif key and line.strip():
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields


def check_frontmatter() -> None:
    group = "frontmatter"
    for skill in skills():
        fm = parse_frontmatter((skill / "SKILL.md").read_text())
        if fm is None:
            fail(group, f"{skill.name}: no YAML frontmatter")
            continue

        unexpected = set(fm) - ALLOWED_FRONTMATTER
        if unexpected:
            fail(group, f"{skill.name}: unexpected frontmatter key(s): {', '.join(sorted(unexpected))}")

        name = fm.get("name", "")
        if not name:
            fail(group, f"{skill.name}: missing name")
        elif name != skill.name:
            fail(group, f"{skill.name}: name '{name}' does not match its directory")
        elif not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
            fail(group, f"{skill.name}: name must be kebab-case")
        elif len(name) > MAX_NAME:
            fail(group, f"{skill.name}: name exceeds {MAX_NAME} characters")

        desc = fm.get("description", "")
        if not desc:
            fail(group, f"{skill.name}: missing description")
        elif len(desc) > MAX_DESCRIPTION:
            fail(group, f"{skill.name}: description is {len(desc)} chars, over the {MAX_DESCRIPTION} limit")
        elif "<" in desc or ">" in desc:
            fail(group, f"{skill.name}: description cannot contain angle brackets")
        else:
            ok(group, f"{skill.name} ({len(desc)} char description)")

        nested = [p for p in skill.rglob("SKILL.md")
                  if p != skill / "SKILL.md"
                  and not set(p.relative_to(skill).parts[:-1]) & EXCLUDED_ANYWHERE]
        if nested:
            names = ", ".join(str(p.relative_to(skill)) for p in nested)
            fail(group, f"{skill.name}: extra SKILL.md files reject on upload: {names}")

        if not (skill / "LICENSE").exists():
            fail(group, f"{skill.name}: no LICENSE — packaged skills must travel self-describing")


def packaged_files(skill: Path) -> set[str]:
    """Files the packager would include, as paths relative to skills/."""
    included = set()
    for path in skill.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(skill)
        if set(rel.parts[:-1]) & EXCLUDED_ANYWHERE or path.name in EXCLUDED_FILES:
            continue
        if rel.parts and rel.parts[0] in ROOT_EXCLUDED:
            continue
        if path.suffix == ".pyc":
            continue
        included.add(f"{skill.name}/{rel.as_posix()}")
    return included


def check_package() -> None:
    group = "package"
    for skill in skills():
        artifact = DIST / f"{skill.name}.skill"
        if not artifact.exists():
            fail(group, f"{skill.name}: dist/{skill.name}.skill is missing — rebuild before committing")
            continue

        with zipfile.ZipFile(artifact) as archive:
            entries = set(archive.namelist())

            rooted = [n for n in entries if not n.startswith(f"{skill.name}/")]
            if rooted:
                fail(group, f"{skill.name}: zip root must be the skill folder; stray: {sorted(rooted)[:3]}")

            leaked = sorted(n for n in entries if f"/{next(iter(ROOT_EXCLUDED))}/" in n)
            if leaked:
                fail(group, f"{skill.name}: evals/ must be excluded from the package: {leaked[:3]}")

            expected = packaged_files(skill)
            missing = sorted(expected - entries)
            extra = sorted(entries - expected)
            if missing:
                fail(group, f"{skill.name}: source files absent from the build: {missing[:3]}")
            if extra:
                fail(group, f"{skill.name}: build carries files not in source: {extra[:3]}")

            stale = []
            for name in sorted(expected & entries):
                built = hashlib.sha256(archive.read(name)).hexdigest()
                source = hashlib.sha256((SKILLS_DIR / name).read_bytes()).hexdigest()
                if built != source:
                    stale.append(name)
            if stale:
                fail(group, f"{skill.name}: build is stale against source: {stale[:3]}")
            elif not missing and not extra and not rooted and not leaked:
                ok(group, f"{skill.name}.skill matches source ({len(entries)} entries)")


def check_mirrors() -> None:
    """A mirror that drifts from canonical is a defect (CONTRIBUTING)."""
    group = "mirrors"
    found = 0
    for skill in skills():
        for mirror in sorted((skill / "references").glob("*.md")):
            text = mirror.read_text()
            header = SYNCED_HEADER.match(text)
            if not header:
                continue
            found += 1
            canonical_path = REPO / header.group("path")
            rel = mirror.relative_to(REPO)
            if not canonical_path.exists():
                fail(group, f"{rel}: synced-from names a missing file: {header.group('path')}")
                continue
            body = text[header.end():]
            if body != canonical_path.read_text():
                fail(group, f"{rel}: drifted from {header.group('path')} — fix flows canonical to mirror, never the reverse")
            else:
                ok(group, f"{rel} is byte-identical to canonical")
    if found == 0:
        print("  --   mirrors: no synced mirrors present yet")


def check_evals() -> None:
    group = "evals"
    for skill in skills():
        path = skill / "evals" / "evals.json"
        if not path.exists():
            fail(group, f"{skill.name}: no evals/evals.json")
            continue
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            fail(group, f"{skill.name}: evals.json does not parse: {exc}")
            continue

        if data.get("skill_name") != skill.name:
            fail(group, f"{skill.name}: evals skill_name is '{data.get('skill_name')}'")
        cases = data.get("evals")
        if not isinstance(cases, list) or not cases:
            fail(group, f"{skill.name}: evals must be a non-empty list")
            continue

        ids = [c.get("id") for c in cases]
        if len(set(ids)) != len(ids):
            fail(group, f"{skill.name}: duplicate eval ids: {ids}")
        for case in cases:
            label = f"{skill.name} eval {case.get('id')}"
            for field in ("id", "prompt", "expected_output", "expectations"):
                if field not in case:
                    fail(group, f"{label}: missing '{field}'")
            expectations = case.get("expectations")
            if isinstance(expectations, list):
                if not expectations:
                    fail(group, f"{label}: no expectations — an eval that asserts nothing passes vacuously")
                if any(not isinstance(e, str) or not e.strip() for e in expectations):
                    fail(group, f"{label}: expectations must be non-empty strings")
            elif expectations is not None:
                fail(group, f"{label}: expectations must be a list")
        ok(group, f"{skill.name}: {len(cases)} eval(s), {sum(len(c.get('expectations', [])) for c in cases)} expectations")

    routing = REPO / "evals" / "suite-routing.json"
    if routing.exists():
        try:
            spec = json.loads(routing.read_text())
        except json.JSONDecodeError as exc:
            fail(group, f"evals/suite-routing.json does not parse: {exc}")
            return
        routes = set(spec.get("routes", []))
        installed = {s.name for s in skills()}
        if not installed <= routes:
            fail(group, f"suite-routing routes {sorted(routes)} do not cover every skill: {sorted(installed)}")
        for case in spec.get("cases", []):
            if case.get("expected") not in routes:
                fail(group, f"suite-routing case {case.get('id')}: expected '{case.get('expected')}' is not a declared route")
        ok(group, f"suite-routing: {len(spec.get('cases', []))} case(s) over routes {sorted(routes)}")


def check_triggers() -> None:
    """The grammar's trigger-hygiene table reserves an explicit non-goal per skill."""
    group = "triggers"
    grammar = (CONVENTIONS / "interaction-grammar.md").read_text()
    table = {}
    for row in re.finditer(r"^\|\s*`(?P<skill>[a-z0-9-]+)`\s*\|[^|]*\|\s*(?P<boundary>[^|]+?)\s*\|", grammar, re.MULTILINE):
        table[row.group("skill")] = row.group("boundary")

    for skill in skills():
        boundary = table.get(skill.name)
        if not boundary:
            fail(group, f"{skill.name}: no row in the trigger-hygiene table")
            continue
        fm = parse_frontmatter((skill / "SKILL.md").read_text()) or {}
        desc = fm.get("description", "").lower()
        # The table states the non-goal in prose; require its distinctive words
        # rather than an exact phrase, so wording can improve without breaking CI.
        keywords = [w for w in re.findall(r"[a-z]{5,}", boundary.lower())
                    if w not in {"deciding", "whether"}]
        missing = [w for w in keywords if w not in desc]
        if missing:
            fail(group, f"{skill.name}: description misses its reserved boundary "
                        f"('{boundary.strip()}') — absent: {', '.join(missing)}")
        else:
            ok(group, f"{skill.name} carries its boundary: '{boundary.strip()}'")


GROUPS = {
    "frontmatter": check_frontmatter,
    "package": check_package,
    "mirrors": check_mirrors,
    "evals": check_evals,
    "triggers": check_triggers,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=sorted(GROUPS), action="append")
    args = parser.parse_args()

    for name in (args.only or sorted(GROUPS)):
        print(f"\n{name}:")
        GROUPS[name]()

    print()
    if failures:
        print(f"{len(failures)} problem(s) found:\n")
        for line in failures:
            print(f"  {line}")
        return 1
    print(f"All checks passed ({checks_run} assertions).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
