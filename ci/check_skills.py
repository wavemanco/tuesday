#!/usr/bin/env python3
"""Repository checks for the Tuesday skill suite.

Deliberately self-contained: no third-party imports, and no dependency on
skill-creator or any other tooling outside this repo. Those live in whatever
session happens to be running and have already moved once; a check that can
vanish underneath CI is not a check.

Run everything:      python ci/check_skills.py
Run one group:       python ci/check_skills.py --only mirrors

Groups (each is described, with what it does not read, in CONTRIBUTING.md):
  frontmatter  SKILL.md frontmatter is present, well-formed, and within the
               limits the Skills API enforces on upload
  package      each dist/<skill>.skill matches its source, is rooted at the
               skill folder, and excludes evals/
  mirrors      every references/ mirror is byte-identical to its canonical
               file once the synced-from header is stripped
  evals        every evals JSON parses, its clauses expand, and it carries the
               fields the runners read
  triggers     each skill's description carries the negative boundary the
               interaction grammar's trigger-hygiene table reserves for it
  parameters   declared output-discipline parameters, and restatements of them
  columns      qualifier, provenance and enum declarations name real columns
  citations, sections, counts, readmes, ledger
               the documentation's own claims
  fit-ledger   the worked dossier's snapshot, by ci/ledger_rules.py
  answer-keys  installed skill text shares no run of words with its fixtures
  fixtures     the fixture fields the harness reads are what it assumes
  wording      retired wordings stay retired
  watch-out    each skill's one watch-out sentence, and every copy of it, exact
  guidance     Anthropic's skill-authoring limits: contents lists, SKILL.md size,
               a third-person description, and every reference linked
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
sys.path.insert(0, str(REPO / "evals"))
from fixture_clauses import ClauseError, expand_spec, unused_clauses  # noqa: E402
import output_checks  # noqa: E402  (the harness's readers, for the checks that lint what it reads)
import research_server  # noqa: E402  (the canned room's own search, for the fixtures lint)
import run_fixtures  # noqa: E402  (the modes a fixture runs in)
sys.path.insert(0, str(REPO / "ci"))
# The fit-ledger and snapshot rules, shared with evals/output_checks.py so the two
# checks of one rule cannot disagree (ci/ledger_rules.py says why).
import ledger_rules  # noqa: E402
from ledger_rules import (BANDS, COUNT_WORDS, FIT_ORDER, PRIORITY_ORDER, ROW_ID,  # noqa: E402,F401
                          COUNTED, FRACTION, TIER_WORDS)
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
        fm = parse_frontmatter((skill / "SKILL.md").read_text(encoding="utf-8"))
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
            text = mirror.read_text(encoding="utf-8")
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
            if body != canonical_path.read_text(encoding="utf-8"):
                fail(group, f"{rel}: drifted from {header.group('path')} — fix flows canonical to mirror, never the reverse")
            else:
                ok(group, f"{rel} is byte-identical to canonical")
    # The inverse check, which is the one that was missing. check_mirrors above
    # validates every mirror that exists and says nothing about one that should.
    # interaction-grammar.md opened with "skills mirror in references/" from the
    # day it was written and was mirrored by nobody for four months — a canonical
    # file declaring its own requirement, with no one verifying the declaration.
    declares = re.compile(r"[Ss]kills (?:carry a )?mirror")
    for canonical in sorted(CONVENTIONS.glob("*.md")):
        if not declares.search(canonical.read_text(encoding="utf-8")):
            continue
        rel = f"conventions/{canonical.name}"
        missing = [s.name for s in skills()
                   if not (s / "references" / canonical.name).exists()]
        if missing:
            fail(group, f"{rel} declares that skills mirror it, and these do not: "
                        f"{', '.join(missing)}")
        else:
            ok(group, f"{rel} is mirrored by every skill, as it declares")

    # A reference pointing at a canonical file the skill does not carry is a
    # pointer into nothing: skills are dependency-free, so a mirror that says
    # "see `x.md`" when x.md is not in this folder names a file the reader
    # cannot open. Mirroring interaction-grammar.md introduced six of these in
    # one commit, each to dossier-schema.md, in the change that fixed the same
    # defect one level up.
    # Every filename the repo carries as a canonical or reference document. The
    # gate is membership in this set rather than in conventions/ alone: canonical
    # text naming a skill-local file (`evidence-model.md`, which only the
    # underwriter has) put a dangling pointer in two other skills' mirrors, and a
    # conventions-only gate could not see it. Names outside the set are ignored —
    # `tuesday-dossier.md` is an emitted artifact, not a file to open.
    known_refs = {p.name for p in CONVENTIONS.glob("*.md")}
    for s in skills():
        known_refs |= {p.name for p in (s / "references").glob("*.md")}
    for skill in skills():
        present = {f.name for f in (skill / "references").glob("*.md")}
        dangling = set()
        for ref in sorted((skill / "references").glob("*.md")):
            for match in re.finditer(r"`([a-z0-9-]+\.md)`", ref.read_text(encoding="utf-8")):
                name = match.group(1)
                if name in present or name not in known_refs:
                    continue  # present here, or not a reference file at all
                dangling.add(f"{ref.name} -> {name}")
        if dangling:
            fail(group, f"{skill.name}: reference(s) point at a canonical file this skill does "
                        f"not carry: {', '.join(sorted(dangling))}")
        else:
            ok(group, f"{skill.name}: every canonical file its references name is present")

    # The other direction. The check above catches a reference naming a file the
    # skill lacks; this catches a file the skill carries that nothing names. Two
    # canonical mirrors were added to all three skills and listed in none of
    # their SKILL.md reference sections — present, byte-perfect, and unreachable,
    # which is how a rule written in them binds nobody.
    for skill in skills():
        body = (skill / "SKILL.md").read_text(encoding="utf-8")
        for ref in sorted((skill / "references").glob("*.md")):
            # SKILL.md specifically, not "anywhere in the folder". A mention
            # buried in a sibling is reachable only by someone already reading
            # that sibling; the reference list is the index, and a file missing
            # from it is one a run is never told to open.
            if ref.name in body:
                ok(group, f"{skill.name}: {ref.name} is named in SKILL.md")
            else:
                fail(group, f"{skill.name}: references/{ref.name} is carried but not named in "
                            f"SKILL.md — a file no run is told to open binds nothing")

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
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(group, f"{skill.name}: evals.json does not parse: {exc}")
            continue

        if data.get("skill_name") != skill.name:
            fail(group, f"{skill.name}: evals skill_name is '{data.get('skill_name')}'")
        try:
            cases = expand_spec(data)
        except ClauseError as exc:
            fail(group, f"{skill.name}: {exc}")
            continue
        for name in unused_clauses(data):
            fail(group, f"{skill.name}: clause \"{name}\" is defined and never used — text a reader would trust that grades nothing")
        if not isinstance(cases, list) or not cases:
            fail(group, f"{skill.name}: evals must be a non-empty list")
            continue

        ids = [c.get("id") for c in cases]
        if len(set(ids)) != len(ids):
            fail(group, f"{skill.name}: duplicate eval ids: {ids}")
        for case in cases:
            label = f"{skill.name} eval {case.get('id')}"
            # A reference the loader cannot expand — a clause inside a clause, a name
            # with a capital or a space — reaches the grader as literal braces.
            for field in ("expected_output", "expectations"):
                for text in ([case.get(field)] if isinstance(case.get(field), str) else case.get(field) or []):
                    if isinstance(text, str) and ("{{" in text or "}}" in text):
                        fail(group, f"{label}: {field} keeps an unexpanded clause reference "
                                    f"({re.search(r'.{0,20}(?:[{]{2}|[}]{2}).{0,20}', text).group(0)!r}) — "
                                    f"clauses are {{{{lower_snake}}}} names, one level deep")
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
            spec = json.loads(routing.read_text(encoding="utf-8"))
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
            if case.get("expected") == "either":
                sib = case.get("siblings")
                if not (isinstance(sib, list) and len(set(sib)) >= 2 and set(sib) <= installed):
                    fail(group, f"suite-routing case {case.get('id')}: an 'either' case must list the two or more "
                                f"installed skills it spans as 'siblings', got {sib!r}")
        ok(group, f"suite-routing: {len(spec.get('cases', []))} case(s) over routes {sorted(routes)}")
        check_routing_variants(group, spec, installed)


def check_routing_variants(group: str, suite: dict, installed: set[str]) -> None:
    """The attachment diagnostic's variant files (evals/README.md, "The attachment
    diagnostic") are output of `evals/routing_variants.py`, never edited. Each is
    held to the suite's route rules, its ids to ones no suite case uses, each
    variant to the suite case it names, and the whole file to what the generator
    writes from the committed suite, so a hand edit, or a suite edit not
    regenerated, fails here rather than measuring something no script made."""
    import routing_variants  # evals/, on the path above
    try:
        built = routing_variants.build(suite)
    except SystemExit as exc:
        fail(group, f"evals/routing_variants.py cannot build from the suite: {exc}")
        return
    by_id = {c.get("id"): c for c in suite.get("cases", [])}
    for name, text in built.items():
        path = REPO / "evals" / name
        if not path.exists():
            fail(group, f"evals/{name} is missing — run python evals/routing_variants.py")
            continue
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(group, f"evals/{name} does not parse: {exc}")
            continue
        routes = set(spec.get("routes", []))
        if not installed <= routes:
            fail(group, f"evals/{name} routes {sorted(routes)} do not cover every skill: {sorted(installed)}")
        for case in spec.get("cases", []):
            n, source = case.get("id"), by_id.get(case.get("derived_from"))
            if case.get("expected") not in routes:
                fail(group, f"evals/{name} case {n}: expected '{case.get('expected')}' is not a declared route")
            if n in by_id:
                fail(group, f"evals/{name} case {n}: its id collides with a suite case's")
            if source is None:
                fail(group, f"evals/{name} case {n}: derived_from {case.get('derived_from')!r} is no suite case")
            elif case.get("expected") != source.get("expected"):
                fail(group, f"evals/{name} case {n}: expected '{case.get('expected')}', but suite case "
                            f"{source.get('id')} expects '{source.get('expected')}'")
        if path.read_text(encoding="utf-8") != text:
            fail(group, f"evals/{name} is not what evals/routing_variants.py generates from the suite — "
                        f"regenerate it, never edit it")
        else:
            ok(group, f"{name}: {len(spec.get('cases', []))} variant(s), as generated from the suite")


def check_triggers() -> None:
    """The grammar's trigger-hygiene table reserves an explicit non-goal per skill."""
    group = "triggers"
    grammar = (CONVENTIONS / "interaction-grammar.md").read_text(encoding="utf-8")
    table = {}
    for row in re.finditer(r"^\|\s*`(?P<skill>[a-z0-9-]+)`\s*\|[^|]*\|\s*(?P<boundary>[^|]+?)\s*\|", grammar, re.MULTILINE):
        table[row.group("skill")] = row.group("boundary")

    for skill in skills():
        boundary = table.get(skill.name)
        if not boundary:
            fail(group, f"{skill.name}: no row in the trigger-hygiene table")
            continue
        fm = parse_frontmatter((skill / "SKILL.md").read_text(encoding="utf-8")) or {}
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


def load_evals(path: Path) -> list[dict] | None:
    """A skill's eval cases, or None when there are none to read.

    A stray comma in evals.json used to end the whole gate in a traceback from
    whichever group read it first; the evals group reports it properly, and the
    others now skip it rather than hide every other failure.
    """
    try:
        cases = expand_spec(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return None
    return cases if isinstance(cases, list) else None


def check_parameters() -> None:
    """Every skill declares every parameter the output-discipline convention names.

    The convention carries invariants that are absolute and parameters that are
    the skill's own call. A skill that simply omits one has not chosen a value, it
    has failed to notice a decision — so the declaration is a slot, and a missing
    slot fails the build. This is the same mechanism as the provenance columns:
    an empty cell is visible where a silent default is not.
    """
    group = "parameters"
    convention = CONVENTIONS / "output-discipline.md"
    if not convention.exists():
        fail(group, "conventions/output-discipline.md is missing")
        return
    expected = re.findall(r"\*\*Parameter:\s*`([a-z_]+)`\*\*", convention.read_text(encoding="utf-8"))
    if not expected:
        fail(group, "output-discipline.md names no parameters — the check would pass vacuously")
        return

    for skill in skills():
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        section = re.search(r"^## Output discipline\s*$(.*?)(?=^## |\Z)", text,
                            re.MULTILINE | re.DOTALL)
        if not section:
            fail(group, f"{skill.name}: no '## Output discipline' section declaring its parameters")
            continue
        body = section.group(1)
        missing = [name for name in expected
                   if not re.search(rf"^\s*{re.escape(name)}\s*:", body, re.MULTILINE)]
        if missing:
            fail(group, f"{skill.name}: undeclared output-discipline parameter(s): "
                        f"{', '.join(missing)}")
        else:
            ok(group, f"{skill.name} declares all {len(expected)} output-discipline parameters")
        values = dict(re.findall(r"^\s*([a-z_]+)\s*:\s*(.+?)\s*$", body, re.MULTILINE))
        check_parameter_agreement(group, skill, values)


BUDGET_PHRASE = re.compile(
    r"\b(?:at most|no more than|up to|a maximum of|never (?:ask )?more than|asks? more than)\s+"
    r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:[a-z-]+\s+){0,2}?questions?\b"
    r"|\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:[a-z-]+\s+){0,2}?questions?"
    r"(?:\s*(?:at most|max(?:imum)?|or fewer)\b|\*{0,2},\s+counted across)", re.IGNORECASE)
# A budget about one topic is not the message's budget: "at most one question
# about the interviewer". "On any turn" is the message's budget.
SUB_BUDGET = re.compile(r"\s+(?:about|on|regarding|concerning|for each)\s+(?!(?:any |each |every |a |the )?"
                        r"(?:turn|message|response|reply)\b)", re.IGNORECASE)
# In mock-interview "questions" are mostly the pack's interview questions. A
# budget is the clarifying budget only in a sentence about the message.
BUDGET_CONTEXT = re.compile(r"\b(?:turn|message|response|reply|clarifying|ask|asks|asked|asking)\b", re.IGNORECASE)
# The subjects whose close closing_order governs. A pack, a rationale cell or a
# story also "ends with" things, and those are other parameters' business: "The
# pack ends with an upgrade menu" is mock-interview's skeleton, not its message.
CLOSE_VERB = re.compile(
    r"\b(?:closes|ends|close|end|closing|ending|concludes|conclude|finishes|finish|wraps up|wrap up)"
    r"\s+(?:with|on)\s+(?P<obj>[^.;:\n]+)", re.IGNORECASE)
RESPONSE_SUBJECTS = {"response", "message", "reply", "assessment", "skill", "output"}
LEAD_WORDS = {"always", "finally", "then", "and", "so", "it", "this", "first", "last", "lastly", "instead"}
OTHER_SUBJECTS = {"pack", "rationale", "cell", "story", "row", "section", "table", "file", "letter",
                  "bullet", "line", "label", "column", "guidance", "answer", "question", "ledger"}
# Where an object stops naming sections: "an upgrade menu naming what each input
# unlocks" names one section, and "and asks at most three questions" is a new clause.
OBJECT_END = re.compile(
    r",?\s+(?:not|rather than|instead of)\b|\s+(?:naming|listing|showing|saying|that|which|who|with|without|so|because|counted|"
    r"and\s+(?:then\s+)?(?:asks|offers|names|gives|says|puts|keeps|carries|lists|includes|is|are|has))\b"
    r"|\s+—(?!\s*(?:and|then)\b)", re.IGNORECASE)


def close_subject(text: str, at: int) -> str | None:
    """The nearest subject noun before a "closes with", within its sentence.

    A fixed window missed "The response offers a tuesday-dossier.md rather than
    emitting or forcing one, and closes with an upgrade menu": sixty characters
    and a filename's full stop between subject and verb. The scan runs back to the
    sentence break instead, and a full stop inside a filename is not one. An
    imperative at the start of a sentence — "End with the upgrade menu" — is an
    instruction about the response.
    """
    start = max([m.end() for m in re.finditer(r"[.!?;](?=\s+[A-Za-z*\"`])", text[:at])] + [0])
    words = [w.lower() for w in re.findall(r"[A-Za-z]+", text[start:at])]
    # The clause's subject, not the nearest noun: "the message presenting the
    # pack ends with" is about the message.
    for word in words:
        if word in RESPONSE_SUBJECTS or word in OTHER_SUBJECTS:
            return word
    if all(word in LEAD_WORDS for word in words):
        return "response"                   # an instruction: "Always close with …"
    return None


def closing_items(value: str) -> list[set[str]]:
    """Each closing_order item as the words that identify it among its siblings."""
    items = [re.findall(r"[a-z]+", part.lower()) for part in value.split(",")]
    stop = {"and", "the", "a", "an", "of"}
    return [{w.rstrip("s") for w in words if w not in stop} for words in items]


def check_parameter_agreement(group: str, skill: Path, values: dict[str, str]) -> None:
    """A skill's own prose and evals restate its parameters the way it declares them.

    Declaring a parameter was meant to end restatements drifting, and did not:
    two evals in job-underwriter required the response to close "with an upgrade
    menu" while closing_order put the questions last, and an expectation written
    for resume-tailor contradicted its own declaration for two releases. Two
    restatements are checkable without reading intent. A question budget must be
    question_budget. A sentence saying the response or message closes or ends with
    some sections must name a tail of closing_order, in closing_order's order — so
    "closes with an upgrade menu" fails where questions come last, and so does
    naming the right sections backwards. Negated sentences ("does not end with")
    are not read, and subjects other than the response are not either: a pack, a
    cell or a story ends with other things.
    """
    surfaces: list[tuple[str, str]] = [("SKILL.md", (skill / "SKILL.md").read_text(encoding="utf-8"))]
    if (skill / "README.md").exists():
        surfaces.append(("README.md", (skill / "README.md").read_text(encoding="utf-8")))
    for ref in sorted((skill / "references").glob("*.md")):
        text = ref.read_text(encoding="utf-8")
        if not SYNCED_HEADER.match(text):
            surfaces.append((f"references/{ref.name}", text))
    for case in load_evals(skill / "evals" / "evals.json") or []:
        for n, expectation in enumerate(case.get("expectations", []), 1):
            surfaces.append((f"evals.json eval {case.get('id')} #{n}", expectation))

    budget = values.get("question_budget", "")
    order = closing_items(values.get("closing_order", ""))
    declared = [part.strip() for part in values.get("closing_order", "").split(",")]
    checked = 0
    for where, raw in surfaces:
        text = re.sub(r"(?<!\n)\n(?![ \t]*(?:\n|[-*+] |\d+\. |[|#>]))", " ", raw)     # a hard wrap is not a break
        for match in BUDGET_PHRASE.finditer(text):
            sentence = re.split(r"(?<=[.!?])\s+", text[max(0, match.start() - 200):match.end() + 120])
            around = next((s for s in sentence if match.group(0) in s), match.group(0))
            if SUB_BUDGET.match(text, match.end()) or not (BUDGET_CONTEXT.search(around) or where.startswith("evals")):
                continue
            word = (match.group(1) or match.group(2)).lower()
            stated = int(word) if word.isdigit() else COUNT_WORDS[word]
            checked += 1
            if budget.isdigit() and stated != int(budget):
                fail(group, f"{skill.name} {where}: \"{match.group(0)}\" — question_budget is {budget}")
        for match in CLOSE_VERB.finditer(text):
            if close_subject(text, match.start()) not in RESPONSE_SUBJECTS:
                continue
            if re.search(r"\b(?:not|never|no longer)\s+(?:\w+\s+)?$|n't\s+$", text[max(0, match.start() - 30):match.start()]):
                continue
            full = match.group("obj")
            quoted_question = re.match(r"[\s*_]*[\"“][^\"”]*\?[\"”]", full)
            obj = "question" if quoted_question else OBJECT_END.split(full, maxsplit=1)[0].lower()
            positions = []
            for i, item in enumerate(order):
                spots = [m.start() for m in re.finditer(r"[a-z]+|\?", obj)
                         if (m.group(0).rstrip("s") in item) or (m.group(0) == "?" and "question" in item)]
                if spots:
                    positions.append((min(spots), i))
            if not positions or not order:
                continue                    # names no call to action: not a statement of the close
            checked += 1
            named = [i for _, i in sorted(positions)]
            tail = list(range(len(order) - len(named), len(order)))
            if re.search(r"\b(?:after|before|following|preceded by)\b", obj):
                named = sorted(named)       # the words carry the order; the set must still be the tail
            if named != tail:
                close = ", then ".join(declared[-len(named):])
                fail(group, f"{skill.name} {where}: \"{' '.join(match.group(0).split())[:90]}\" — "
                            f"closing_order ends {close}")
    if checked:
        ok(group, f"{skill.name}: {checked} restatements of its parameters agree with its declaration")


def check_columns() -> None:
    """A destination a rule names must exist as a column in the shape being written.

    job-underwriter's row spec declared a `reasoning` field from v0.1 and its JSON
    envelope emitted it; the markdown table the model actually writes had no such
    column. The compound-cell rule said "put the qualifier in `reasoning`" the
    whole time — true, documented, and pointing at nothing on the page. What went
    into the neighbouring `Confidence` cell instead was `none/low`, and that
    expectation failed 37 runs out of 37. The register repeated it exactly with
    `hypothesis`.

    So `qualifier_fields` is a declaration and this is its check. `none` is a
    legitimate value: it says the skill has no free-text column, visibly, which is
    the point of a slot.
    """
    group = "columns"
    for skill in skills():
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        section = re.search(r"^## Output discipline\s*$(.*?)(?=^## |\Z)", text,
                            re.MULTILINE | re.DOTALL)
        if not section:
            continue  # check_parameters already fails this
        declared = re.search(r"^\s*qualifier_fields\s*:(.*)$", section.group(1), re.MULTILINE)
        if not declared:
            continue  # likewise
        fields = [f.strip() for f in declared.group(1).split(",") if f.strip()]
        if fields == ["none"]:
            ok(group, f"{skill.name}: qualifier_fields declared as none — no free-text column, on purpose")
            fields = []

        # The header rows of the worked tables — a header row, then a separator row —
        # in the skill's own references. A mirror is not read: its tables define the
        # suite's tokens, and a column of the same name there is not a column of the
        # shape the skill writes. (Every row of every table was read once, so a
        # field named in any body cell, a mirror's included, answered as a column.)
        header_rows: list[list[str]] = []
        for ref in sorted((skill / "references").glob("*.md")):
            text = ref.read_text(encoding="utf-8")
            if not SYNCED_HEADER.match(text):
                header_rows += worked_tables(text)
        headers = {cell for row in header_rows for cell in row}
        # A free-text column is where world-claims land, so it needs a Provenance
        # cell in the same table. Learned twice in one session: the register's
        # Hypothesis column shipped without one and was fixed; the evidence map's
        # Reasoning column shipped without one in the same commit and was not.
        for field in fields:
            want = re.sub(r"[^a-z0-9]+", " ", field.lower()).strip()
            carrying = [row for row in header_rows if want in row]
            if carrying and not any("provenance" in row for row in carrying):
                fail(group, f"{skill.name}: '{field}' is a free-text column in a table with no "
                            f"Provenance cell — the qualifier has a home and its label does not")
            if want in headers:
                ok(group, f"{skill.name}: '{field}' is a rendered column")
            else:
                fail(group, f"{skill.name}: qualifier_fields names '{field}', which is not a column "
                            f"in any references/ table outside the mirrors — a rule pointing at a cell that "
                            f"does not exist")

        # Every declared enum names the one table that renders it, and the column
        # exists in that table. output-discipline.md: "every declared enum needs a
        # column to live in" — a field declared an enum with no column is invented at
        # write time, with no token set. The mapping names a file, a '## ' section and
        # a column, never a header alone: a header matched anywhere let the mirrored
        # glossary's "Gap type" answer for the fit snapshot's, so dropping the column
        # from the snapshot — the MI-11 defect — passed. A mirror is never the home: it
        # defines tokens, it is not a table the response renders.
        enums = re.search(r"^\s*enum_fields\s*:(.*)$", section.group(1), re.MULTILINE)
        mapped = re.search(r"^\s*enum_columns\s*:(.*)$", section.group(1), re.MULTILINE)
        enum_names = [f.strip() for f in enums.group(1).split(",") if f.strip()] if enums else []
        if enum_names and enum_names != ["none"]:
            if not mapped:
                fail(group, f"{skill.name}: enum_fields are declared and enum_columns is not — say which column "
                            f"holds each enum")
            else:
                homes: dict[str, tuple[str, str, str]] = {}
                for part in (p.strip() for p in mapped.group(1).split(",") if p.strip()):
                    m = ENUM_HOME.match(part)
                    if not m:
                        fail(group, f"{skill.name}: enum_columns entry {part!r} is not field=file.md#Section/Column")
                        continue
                    homes[m.group(1)] = (m.group(2), m.group(3).strip(), m.group(4).strip())
                for name in enum_names:
                    if name not in homes:
                        fail(group, f"{skill.name}: enum_fields names '{name}' and enum_columns gives it no column "
                                    f"— a declared enum with nowhere to live")
                        continue
                    file, heading, column = homes[name]
                    ref = skill / "references" / file
                    where = f"'{heading}' in {file}"
                    if not ref.is_file():
                        fail(group, f"{skill.name}: enum_columns puts '{name}' in {file}, which is not a file "
                                    f"in references/")
                    elif SYNCED_HEADER.match(ref.read_text(encoding="utf-8")):
                        fail(group, f"{skill.name}: enum_columns puts '{name}' in {file}, a mirror — a mirrored "
                                    f"glossary defines the tokens and is never the table an enum is rendered in")
                    elif heading not in (tables := section_tables(ref)):
                        fail(group, f"{skill.name}: enum_columns puts '{name}' under {where}, which is no '## ' "
                                    f"section of that file")
                    elif tables[heading] is None:
                        fail(group, f"{skill.name}: enum_columns puts '{name}' under {where}, a section with no "
                                    f"worked table (a header row, then a separator row)")
                    elif header_key(column) not in tables[heading]:
                        fail(group, f"{skill.name}: enum_columns puts '{name}' in '{column}', which is no column "
                                    f"of the table under {where}")
                    else:
                        ok(group, f"{skill.name}: enum '{name}' lives in the '{column}' column of the table under "
                                  f"{where}")
                for name in sorted(set(homes) - set(enum_names)):
                    fail(group, f"{skill.name}: enum_columns maps '{name}', which enum_fields does not declare")
        elif mapped and [c.strip() for c in mapped.group(1).split(",")] != ["none"]:
            fail(group, f"{skill.name}: enum_columns maps fields while enum_fields declares none")

        # Sections declared as carrying provenance must actually have the column, in
        # the first worked table of every section of that name outside the mirrors —
        # the same reading of a section as the enum homes above (section_tables).
        declared_sections = re.search(r"^\s*provenance_sections\s*:(.*)$", section.group(1),
                                      re.MULTILINE)
        if not declared_sections:
            continue
        wanted = [s.strip() for s in declared_sections.group(1).split(",") if s.strip()]
        if wanted == ["none"]:
            ok(group, f"{skill.name}: provenance_sections declared as none")
            continue
        found: dict[str, list[str]] = {}
        for ref in sorted((skill / "references").glob("*.md")):
            if SYNCED_HEADER.match(ref.read_text(encoding="utf-8")):
                continue
            for heading, header in section_tables(ref).items():
                if heading in wanted and header is not None:
                    found.setdefault(heading, []).append("" if "provenance" in header else ref.name)
        for name in wanted:
            if name not in found:
                fail(group, f"{skill.name}: provenance_sections names '{name}', which is not a "
                            f"'## ' section with a table in references/ outside the mirrors")
            elif any(found[name]):
                fail(group, f"{skill.name}: section '{name}' is declared a provenance carrier "
                            f"but its table has no Provenance column ({', '.join(f for f in found[name] if f)})")
            else:
                ok(group, f"{skill.name}: '{name}' carries a Provenance column")


# A mapping's home: field=file.md#Section/Column. The section is a '## ' heading,
# written as it stands; the column is the last '/'-separated part.
ENUM_HOME = re.compile(r"^([a-z_]+)\s*=\s*([A-Za-z0-9._-]+\.md)#(.+)/([^/]+)$")
TABLE_SEPARATOR = re.compile(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$")


def header_key(cell: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", cell.strip().lower()).strip()


def section_tables(ref: Path) -> dict[str, list[str] | None]:
    """Each '## ' section of a reference file, mapped to the header cells of the
    first worked table inside it — a header row, then a separator row — or None
    when it has none. The split stops at the next '## ' heading, so a later
    section's table cannot answer for this one; of two sections with one name, the
    first is read."""
    chunks = re.split(r"^## (.+)$", ref.read_text(encoding="utf-8"), flags=re.MULTILINE)
    out: dict[str, list[str] | None] = {}
    for heading, body in zip(chunks[1::2], chunks[2::2]):
        out.setdefault(heading.strip(), next(iter(worked_tables(body)), None))
    return out


def worked_tables(text: str) -> list[list[str]]:
    """The header cells of every worked table in `text`, in order: a table row
    followed by a separator row."""
    lines = text.splitlines()
    return [[header_key(c) for c in lines[i].strip().strip("|").split("|")]
            for i in range(len(lines) - 1)
            if lines[i].lstrip().startswith("|") and TABLE_SEPARATOR.match(lines[i + 1])]


# --- Citations -------------------------------------------------------------
# Shared with ci/verify_citations.py, which imports these rather than restating
# them: two normalisers would be two definitions of "verbatim", and they would
# drift apart exactly where it matters.

CITATIONS = CONVENTIONS / "citations.md"
CITE = re.compile(r"\(cite\s+(C\d+)\)")
# Any length: a floor of three characters kept "9%" and "…" from ever reaching the
# matcher, so a wrong bare figure beside a marker passed unexamined.
QUOTATION = re.compile(r'"([^"\n]+(?:\n[^"\n]+)*)"')
# Any "(cite …)" at all. Only the exact form `(cite Cn)` is a marker; anything
# else — "(cite C1, C2)", "(cite: C3)" — is refused rather than silently ignored,
# because an unparsed marker binds nothing and resolves nothing.
ANY_MARKER = re.compile(r"\(cite\b[^)\n]*\)", re.IGNORECASE)
MARKER_GROUP = re.compile(r"[.,;:?!]?\s*((?:\(cite\s+C\d+\)\s*)+)")
# A sentence break, except after an abbreviation and never before a marker:
# "write Cui et al. (cite C3)" and "the U.S. Equal Employment Opportunity
# Commission" are one sentence each.
SENTENCE_BREAK = re.compile(
    r"(?<!\bet al)(?<!\be\.g)(?<!\bi\.e)(?<!\bU\.S)(?<!\bvs)(?<!\bInc)(?<!\bNo)(?<!\bSt)"
    r"[.!?][\"”]?(?=\s+(?!\(cite)[A-Z(*`\[\"])|\n[ \t]*\n|\n(?=[ \t]*(?:[-*>] |\d+\. |\||#))")
SINGLE_QUOTED_THEN_MARKER = re.compile(r"(?:‘[^’]{3,}?’|(?<![\w])'[^'\n]{3,}'(?![\w]))[.,;:]?\s*\(cite\s+C\d+\)")
BLOCKQUOTE_MARKER = re.compile(r"^[ \t]*>.*\(cite\s+C\d+\)", re.MULTILINE)
NEAR_QUOTE = 0.7
STOPWORDS = frozenset("""a an the of to in on for and or but is are was were be been by with as at from
that this these those it its their they them we our you your he she his her not no may might can could
would should will than then so such into over under about per via have has had do does did use used get
got make made just also""".split())
FRAGMENTS = frozenset("don didn doesn isn wasn aren weren haven hasn couldn wouldn shouldn won can".split())
# Epistemic hedges: the words whose loss turned "may have important implications,
# including favoring established workers" into a finding.
EPISTEMIC = frozenset("may might could suggest suggests suggesting appears appear seems seem likely possibly probably "
                      "perhaps estimated approximately roughly".split())


def citation_text(raw: str) -> str:
    """The text the citation rules read.

    Fenced code is blanked: a JSON or YAML example is data, not a quotation.
    Inline code becomes a placeholder word rather than vanishing, so a sentence
    that opens with a `code` name still has a start. Curly single quotation marks
    around a span become double ones — British style quotes that way — while an
    apostrophe inside a word ("workers’") stays one.
    """
    lines, fenced = [], False
    for line in raw.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            lines.append("")
        else:
            lines.append("" if fenced else line)
    text = "\n".join(lines)
    text = re.sub(r"`[^`\n]*`", "CODE", text)
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"(?<!\w)\u2018((?:[^\u2018\u2019]|\u2019(?=\w))+?)\u2019(?!\w)", r'"\1"', text)


def bound_quotations(text: str) -> list[tuple[int, int, str, list[str]]]:
    """(start, end, quotation, cids) for every quotation, with the markers directly after it.

    A marker binds the quotation it follows and nothing else. The version before
    this one read a marker as covering every quotation earlier in its sentence,
    which needed a sentence splitter, and every abbreviation ("et al.", "U.S.")
    and every marker placed before its quotation became a way through or a false
    alarm. One placement, checked exactly, has neither. Stacked markers bind as a
    group: the quotation must sit inside one of them.
    """
    found = []
    for match in QUOTATION.finditer(text):
        group = MARKER_GROUP.match(text, match.end())
        cids = CITE.findall(group.group(1)) if group else []
        found.append((match.start(), match.end(), match.group(1), cids))
    return found


def cited_sentences(text: str, quotes: list[tuple[int, int, str, list[str]]]) -> list[tuple[int, int]]:
    """The spans of sentences that carry a marker. A full stop inside a quotation is not a break."""
    breaks = [m.start() for m in SENTENCE_BREAK.finditer(text)
              if not any(a < m.start() < b for a, b, _, _ in quotes)]
    cuts = [0] + breaks + [len(text)]
    return [(a, b) for a, b in zip(cuts, cuts[1:]) if CITE.search(text, a, b)]


def content_stems(tokens: list[str]) -> list[str]:
    """Content words, crudely stemmed, US and UK spellings merged: favours ~ favoring."""
    out = []
    for token in tokens:
        word = token.lower()
        # "don't" tokenises as "don" and "t"; neither half is content.
        if word in STOPWORDS or word in FRAGMENTS or len(word) <= 2 or not re.search(r"[a-z]", word):
            continue
        word = word.replace("our", "or")
        for suffix in ("ing", "ed", "es", "s"):
            if len(word) > 4 and word.endswith(suffix):
                word = word[:-len(suffix)]
                break
        out.append(word)
    return out


def common_run(a: list[str], b: list[str]) -> int:
    """Longest common subsequence of two token lists: how much of a survives, in order, in b."""
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b):
            cur.append(prev[j] + 1 if x == y else max(prev[j + 1], cur[j]))
        prev = cur
    return prev[-1]


def longest_shared_run(a: list[str], b: list[str]) -> int:
    best = 0
    for i in range(len(a)):
        for j in range(len(b)):
            k = 0
            while i + k < len(a) and j + k < len(b) and a[i + k] == b[j + k]:
                k += 1
            best = max(best, k)
    return best


def reads_as_paraphrase(quotation: str, verbatim: str) -> bool:
    """A quotation that shares a source's content words, in its order, without being inside it.

    Three consecutive content words in common is enough; so are all but one of a
    short quotation's, which is the size of the original defect — "favours
    established candidates", from a sentence about established workers.
    """
    q, s = content_stems(quote_tokens(quotation)), content_stems(quote_tokens(verbatim))
    if len(q) < 3:
        return False
    return longest_shared_run(q, s) >= 3 or (len(q) >= 6 and common_run(q, s) >= NEAR_QUOTE * len(q))


def figure_blind(tokens: list[str]) -> list[str]:
    return ["#" if re.search(r"\d", tok) else tok for tok in tokens]


def misquotes_figure(quotation: str, verbatim: str) -> bool:
    """The entry's words around a different number: "fell by 15%" for "fell by 51%"."""
    q = quote_tokens(quotation)
    if not any(re.search(r"\d", tok) for tok in q) or len(q) < 2:
        return False
    return _find(figure_blind(q), figure_blind(quote_tokens(verbatim))) >= 0 and _find(q, quote_tokens(verbatim)) < 0


def drops_hedge(quotation: str, verbatim: str, sentence: str) -> bool:
    """A quotation that starts after its source's hedge, in prose that restates none.

    Prose may quote any contiguous run of an entry, so "favoring established
    workers" could be lifted from a sentence that opens "This shift may have
    important implications, including" — the original defect, with the quotation
    marks now on the true half of it.
    """
    q, s = quote_tokens(quotation), quote_tokens(verbatim)
    at = _find(q, s)
    if at < 0 or EPISTEMIC & set(q):
        return False
    if not EPISTEMIC & set(s[max(0, at - 12):at]):
        return False
    outside = quote_tokens(sentence.replace(quotation, " "))
    return not EPISTEMIC & set(outside)


def citation_entries() -> dict[str, dict[str, str]]:
    if not CITATIONS.exists():
        return {}
    out: dict[str, dict[str, str]] = {}
    for block in re.split(r"^## (?=C\d+\s*$)", CITATIONS.read_text(encoding="utf-8"), flags=re.MULTILINE)[1:]:
        cid, _, body = block.partition("\n")
        out[cid.strip()] = dict(re.findall(r"^- \*\*([A-Za-z ]+):\*\* (.*)$", body, flags=re.MULTILINE))
    return out


def quoted_spans(verbatim: str) -> list[str]:
    return [s for s in re.findall(r'"([^"]+)"', verbatim) if s.strip()]


ELLIPSIS = "\u2026"

# Words an elision must never skip. A gap that swallows one of these changes what
# the source says rather than shortening it: "may have important implications,
# including favoring" cut to "may … favoring" is the paraphrase this file exists
# to stop, and the first version of this matcher let it through.
HEDGES = frozenset("""
    not no never none nor neither cannot without may might could can would should
    must only some few little rarely seldom sometimes often unless if whether
    including includes except excluding but although though however yet while
    generally possibly probably likely unlikely perhaps approximately about around
    roughly nearly almost partly partially hardly barely less more most least
    implications suggests suggest appears seems estimated
""".split())


def quote_tokens(text: str) -> list[str]:
    """Whole tokens, case- and typography-insensitive, with nothing deleted.

    The first version stripped every one-to-three-digit number between two words
    as a presumed PDF footnote marker, which made "7 years" and "9 years" equal,
    and matched raw substrings, which made "56 percentage points" a quotation of
    "3.56 percentage points". Numbers are the content most worth protecting, so
    they are kept whole and matched whole. An ellipsis is its own token.
    """
    import html as _html
    text = _html.unescape(text).lower()
    text = text.translate(str.maketrans({"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
                                         "\u2014": " ", "\u2013": " ", "\u00a0": " "}))
    text = text.replace("...", ELLIPSIS)
    text = re.sub(r"-\n(?=[a-z])", "", text)                  # hyphenation across a line break
    text = text.replace(ELLIPSIS, f" {ELLIPSIS} ")
    tokens = []
    for raw in re.split(r"[\s\"'(),;:!?\[\]{}<>*_`|/]+", text):
        token = raw.strip(".")
        if token:
            tokens.append(token)
    return tokens


def normalise_quote(text: str) -> str:
    return " ".join(quote_tokens(text))


def _find(needle: list[str], hay: list[str], start: int = 0) -> int:
    for i in range(start, len(hay) - len(needle) + 1):
        if hay[i:i + len(needle)] == needle:
            return i
    return -1


def quote_in(span: str, entry: str) -> bool:
    """A prose quotation is a contiguous run of the entry's own tokens.

    No gaps: prose may carry an ellipsis only where the curated entry already has
    one, because the ellipsis is matched as a token like any other. Prose cannot
    introduce an elision the entry did not make. An empty span quotes nothing and
    is not a match.
    """
    needle = quote_tokens(span)
    if not [t for t in needle if t != ELLIPSIS]:
        return False
    return _find(needle, quote_tokens(entry)) >= 0


def quote_in_source(verbatim: str, source: str) -> tuple[bool, str]:
    """An entry's quotation against its source text, where extraction is noisy.

    Fragments separated by an ellipsis must appear in order, and each gap is
    inspected: a gap may skip footnote numbers and ordinary words, never a hedge
    or a negation. Returns (ok, reason).
    """
    fragments = [f for f in re.split(r"\s*(?:\u2026|\.\.\.)\s*", verbatim) if quote_tokens(f)]
    if not fragments:
        return False, "the quotation is empty"
    hay = quote_tokens(source)
    position, previous_end = 0, None
    for fragment in fragments:
        needle = quote_tokens(fragment)
        found = _find(needle, hay, position)
        if found < 0:
            return False, f"not in source: {' '.join(needle)[:70]!r}"
        if previous_end is not None:
            skipped = hay[previous_end:found]
            dropped = sorted(set(skipped) & HEDGES)
            if dropped:
                return False, f"an elision skips {', '.join(dropped)} — that changes what the source says"
            if len(skipped) > 12:
                return False, f"an elision skips {len(skipped)} words — too much to call an omission"
        position = previous_end = found + len(needle)
    return True, "ok"


def citing_files() -> list[Path]:
    """Every document the documentation checks read: all Markdown but mirrors and builds.

    The skill READMEs and evals/README.md were left out when this list was first
    written, and one of them went on describing four fixtures in a skill that had
    six — documentation outside the graded set drifts like any other.
    """
    files = [REPO / "README.md", REPO / "CONTRIBUTING.md", REPO / "evals" / "README.md"]
    files += sorted(CONVENTIONS.glob("*.md")) + sorted((REPO / "docs").glob("*.md"))
    for skill in skills():
        files += [skill / "SKILL.md", skill / "README.md"]
        files += [r for r in sorted((skill / "references").glob("*.md"))
                  if not SYNCED_HEADER.match(r.read_text(encoding="utf-8"))]   # mirrors inherit canonical's cites
    return [f for f in files if f.exists() and f != CITATIONS]


def check_citations() -> None:
    """A claim about the outside world is quoted from a recorded source, or not quoted.

    The suite requires every line a skill proposes to trace to a verbatim source
    in a cell. The conventions imposing that rule paraphrased a paper from memory,
    and a quotation later certified "verbatim" was a compression copied from a spec
    whose own quotation was already wrong. citations.md holds each source sentence
    once; this checks that nothing elsewhere quotes more than an entry holds, in
    the one form CONTRIBUTING.md sets out — double quotation marks, the marker
    directly after the quotation, one entry per marker — and refuses the forms
    around it that a reader would take for a citation and a check could not bind.
    What it cannot check is an entry against its source — that needs the network,
    and is ci/verify_citations.py.
    """
    group = "citations"
    entries = citation_entries()
    if not entries:
        fail(group, "conventions/citations.md is missing or has no entries — the check would pass vacuously")
        return

    for cid, fields in entries.items():
        missing = [k for k in ("Claim", "Verbatim", "Source", "Retrieved") if not fields.get(k)]
        if missing:
            fail(group, f"{cid}: missing field(s) {', '.join(missing)}")
        elif not quoted_spans(fields["Verbatim"]):
            fail(group, f"{cid}: Verbatim has no quoted span — nothing to check a quotation against")
        else:
            ok(group, f"{cid} is complete")

    used: set[str] = set()
    # Each quoted span of an entry is matched separately: joining them would let a
    # prose quotation straddle two sentences the entry quotes from different places.
    spans_of = {cid: quoted_spans(f.get("Verbatim", "")) for cid, f in entries.items()}
    source_text = {cid: spans for cid, spans in spans_of.items()}
    for path in citing_files():
        text = citation_text(path.read_text(encoding="utf-8"))
        rel = path.relative_to(REPO)
        for marker in ANY_MARKER.finditer(text):
            if not CITE.fullmatch(marker.group(0)):
                fail(group, f"{rel}: malformed marker {marker.group(0)!r} — one entry per marker, written (cite C1)")
        for cid in CITE.findall(text):
            used.add(cid)
            if cid not in entries:
                fail(group, f"{rel}: (cite {cid}) names no entry in citations.md")
        for match in SINGLE_QUOTED_THEN_MARKER.finditer(text):
            fail(group, f"{rel}: {' '.join(match.group(0).split())[:70]!r} — quote a source in double "
                        f"quotation marks, which is what the check reads")
        for match in BLOCKQUOTE_MARKER.finditer(text):
            fail(group, f"{rel}: a blockquote carrying a marker — quote a source inline in double "
                        f"quotation marks, with the marker directly after it")
        quotes = bound_quotations(text)
        sentences = cited_sentences(text, quotes)
        for start, end, span, cids in quotes:
            if not cids:
                continue
            spans = [s for cid in cids if cid in entries for s in source_text[cid]]
            holding = [s for s in spans if quote_in(span, s)]
            if not holding:
                fail(group, f"{rel}: quotes \"{' '.join(span.split())[:70]}\" as {' or '.join(cids)}, "
                            f"and {cids[0]}'s Verbatim does not contain it")
                continue
            sentence = next((text[a:b] for a, b in sentences if a <= start < b), span)
            if all(drops_hedge(span, s, sentence) for s in holding):
                fail(group, f"{rel}: \"{' '.join(span.split())[:60]}\" starts after its source's hedge, and the "
                            f"sentence quoting it restates none — quote from the hedge, or say it")
        # A figure quoted in a cited sentence carries its own marker: that is the
        # form in which a wrong number can be checked at all. Other quotations
        # in the sentence — an example question, a scare-quoted term — are left
        # to the tests below.
        for a, b in sentences:
            for start, end, span, cids in quotes:
                if a <= start < b and not cids and re.search(r"\d", span):
                    fail(group, f"{rel}: \"{' '.join(span.split())[:60]}\" carries a figure in a cited sentence "
                                f"with no marker beside it — put (cite Cn) directly after it")
        # A quotation with no marker is checked three ways. Verbatim somewhere in
        # an entry, it is a source quoted without its citation. The entry's words
        # around a different number, it is a misquoted figure. Sharing a run of an
        # entry's content words without being inside it, it is a paraphrase in
        # quotation marks — how the original defect shipped. Blockquotes count.
        unmarked = [span for _, _, span, cids in quotes if not cids]
        unmarked += [" ".join(line.lstrip()[1:].strip() for line in block.split("\n"))
                     for block in re.findall(r"(?:^[ \t]*>[^\n]*\n?)+", text, re.MULTILINE)]
        for span in unmarked:
            words = quote_tokens(span)
            if len(words) < 3 and not any(ch.isdigit() for ch in span):
                continue
            for cid, spans in source_text.items():
                if any(quote_in(span, s) for s in spans):
                    fail(group, f"{rel}: quotes {cid}'s source verbatim without (cite {cid}): "
                                f"\"{' '.join(span.split())[:60]}\"")
                    break
                if any(misquotes_figure(span, s) for s in spans):
                    fail(group, f"{rel}: \"{' '.join(span.split())[:60]}\" is {cid}'s wording with a different "
                                f"figure")
                    break
                if any(reads_as_paraphrase(span, s) for s in spans):
                    fail(group, f"{rel}: \"{' '.join(span.split())[:60]}\" is close to {cid}'s source "
                                f"but not its words — quote {cid} exactly and cite it, or paraphrase "
                                f"without quotation marks")
                    break

    unused = sorted(set(entries) - used, key=lambda c: int(c[1:]))
    if unused:
        fail(group, f"citations.md entries cited nowhere: {', '.join(unused)} — an entry no "
                    f"claim rests on is not evidence for anything")
    else:
        ok(group, f"all {len(entries)} citations are cited, and every marker resolves")


SECTION_REF = re.compile(r"`?(?:[A-Za-z0-9-]+/)*([A-Za-z0-9-]+\.md)`?(?:'s)?\s*§(\d+(?:\.\d+)?)"
                         r"((?:\s*(?:,|and|or)\s*§\s*\d+(?:\.\d+)?(?!\s+(?:above|below|here|of this|in this))"
                         r"|\s*(?:–|-|to)\s*§?\s*\d+(?:\.\d+)?)*)")
BARE_SECTION = re.compile(r"§(\d+(?:\.\d+)?)")
FILE_NAME = re.compile(r"(?:[A-Za-z0-9-]+/)*([A-Za-z0-9-]+\.md)\b")
HEADING = re.compile(r"^#{2,4} (\d+(?:\.\d+)?)[.\s]\s*(.*)$", re.MULTILINE)
# "this file's §3", "§3 above": the author saying in words that a bare
# reference is local, for the rare block that also names another file.
SELF_REF = re.compile(r"\bthis (?:file|spec|brief|document|schema)(?:'s)?\s*$")
SELF_AFTER = re.compile(r"^(?:'s)?\s+(?:above|below|here)\b|^\s+(?:of|in)\s+this\s+(?:file|spec|brief|document|schema)\b")
# Nouns that name a document without naming its file. "§2 of the mirror" and
# "schema §6" read as references to somewhere else and resolved against the
# citing file, which had a §2 and a §6 of its own.
DOC_NOUNS = frozenset({"mirror", "spec", "brief", "document", "schema", "grammar", "conventions"})
TITLE_STOP = frozenset("a an and the of to for in on with its it how what this that per see".split())


def section_titles(path: Path) -> dict[str, str]:
    return {num: title for num, title in HEADING.findall(path.read_text(encoding="utf-8"))}


def section_numbers(path: Path) -> set[str]:
    return set(section_titles(path))


def content_words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]+", text.lower()) if w not in TITLE_STOP]


def text_blocks(text: str) -> list[tuple[int, int]]:
    """Paragraphs, list items, table rows and headings, as (start, end) offsets."""
    bounds, start = [], 0
    for match in re.finditer(r"\n(?=[ \t]*\n)|\n(?=[ \t]*(?:[-*] |\d+\. |\||#))", text):
        bounds.append((start, match.end()))
        start = match.end()
    bounds.append((start, len(text)))
    return bounds


def stems_names(targets: dict[str, Path]) -> list[str]:
    return [name for name in targets if name not in ("README.md", "CONTRIBUTING.md", "SKILL.md")]


def check_sections() -> None:
    """Every section reference points at a section that exists — the one meant.

    A `file.md` §N is a claim that the section is there and says something, and
    none had ever been checked. The rule has two halves: a reference into another
    file names it, written `name.md` §N, and a bare §N means this file.

    The first version enforced only the second half's arithmetic — a bare §N had
    to exist here — so "(grammar §8)" in a file with its own §8 passed, and so did
    fourteen other references into other files. A bare §N is therefore also
    refused when the words around it point elsewhere:

      - a qualifier: a file name, a skill name or a document noun within the five
        words before it in its clause ("grammar §8", "as the grammar says in
        §8", "resume-tailor's §8", "the conventions' §8"), or after "of"/"in"
        ("§2 of the mirror") — unless the label is this file's own heading;
      - its block — paragraph, list item or table row — names another file, with
        or without the `.md`;
      - its label is another file's heading for that number and not this one's
        ("**Truthfulness core** (§6)" in a file whose §6 is about evals).

    A bare §N the author means locally, in a block that names another file, is
    written "this file's §N", "§N of this spec", or "§N above". A statute's §
    ("8 U.S.C. §1324b") is not a section. What no rule here reads is intent
    carried by an earlier paragraph; the fifteen were found by reading all fifty
    bare references, and the self-test holds one of each kind above.

    Only the § sign is read. "Section 13 of the output template" names a row of a
    pack's skeleton table, not a heading, and is not checked; a heading reference
    is written with §, so the check sees it.
    """
    group = "sections"
    targets: dict[str, Path] = {}
    for path in list(CONVENTIONS.glob("*.md")) + list((REPO / "docs").glob("*.md")):
        targets[path.name] = path
    for skill in skills():
        for ref in (skill / "references").glob("*.md"):
            targets.setdefault(ref.name, ref)
    # Files a reference can name but that have no numbered sections to point at.
    for path in [REPO / "README.md", REPO / "CONTRIBUTING.md"] + [s / "SKILL.md" for s in skills()]:
        targets.setdefault(path.name, path)
    titles = {name: section_titles(path) for name, path in targets.items()}
    # A qualifier is a whole file name or a skill name, not a fragment of one:
    # "evidence" and "ledger" are ordinary words, and read as file names they
    # refused "the evidence (§2)" in a file whose §2 is "The evidence".
    stems: dict[str, set[str]] = {}
    for name in targets:
        if name not in ("README.md", "CONTRIBUTING.md", "SKILL.md"):   # "skill" is a word
            stems.setdefault(name[:-3].lower(), set()).add(name)
    # Files are also named in prose with spaces: "the reframing audit".
    spaced = {name[:-3].replace("-", " "): name for name in stems_names(targets) if "-" in name}
    skill_names = {skill.name for skill in skills()}

    checked = 0
    for path in citing_files() + [CITATIONS]:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO)
        spans = []
        for match in SECTION_REF.finditer(text):
            spans.append(match.span())
            name = match.group(1)
            # "`x.md` §4 and §5", "§4–6": the file carries across the list.
            numbers = [match.group(2)] + re.findall(r"\d+(?:\.\d+)?", match.group(3))
            target = targets.get(name)
            for number in numbers:
                checked += 1
                if target is None:
                    fail(group, f"{rel}: §{number} of `{name}` — no such file")
                elif number not in titles[name]:
                    fail(group, f"{rel}: `{name}` §{number} — that file has no section {number}")
        own = section_titles(path)
        for start, end in text_blocks(text):
            block = text[start:end]
            others = sorted({m.group(1) for m in FILE_NAME.finditer(block)
                             if m.group(1) != path.name and titles.get(m.group(1))}
                            | {name for name in targets if name != path.name and "-" in name
                               and re.search(rf"(?<![\w/-]){re.escape(name[:-3])}(?![\w.-])", block)})
            for match in BARE_SECTION.finditer(block):
                at = start + match.start()
                if any(a <= at < b for a, b in spans):
                    continue
                number = match.group(1)
                # A statute, not a section: "8 U.S.C. §1324b".
                if (len(number.split(".")[0]) >= 3 or re.match(r"-\d", text[at + len(match.group(0)):])
                        or re.search(r"(?:U\.S\.C\.|C\.F\.R\.|Code|Law|Stat\.|Act)[^.;\n]{0,20}$",
                                     text[max(0, at - 30):at])):
                    continue
                checked += 1
                line = text[:at].count("\n") + 1
                where = f"{rel}:{line}: bare §{number}"
                if number not in own:
                    fail(group, f"{where} — this file has no such section. "
                                f"A reference into another file names that file")
                    continue
                before = text[max(0, at - 60):at]
                after = text[at + len(match.group(0)):at + len(match.group(0)) + 40]
                if SELF_REF.search(before) or SELF_AFTER.match(after):
                    continue
                label = content_words(re.sub(r"[*_`]", "", before).rsplit("\n", 1)[-1])[-2:]
                if label and set(label) <= set(content_words(own[number])):
                    continue                        # labelled with this file's own heading
                # The qualifier may be anywhere in the clause: "(as the grammar says
                # in §8)" means the grammar as plainly as "(grammar §8)" does.
                # A hard wrap is not a clause boundary; a list marker or blank line is.
                joined = re.sub(r"\n(?![ \t]*(?:\n|[-*+] |\d+\. |[|#>]))", " ", before)
                clause = re.split(r"[,;:(|—\n]|[.!?]\s", joined)[-1]
                of_the = re.match(r"\s+(?:of|in)\s+(?:the\s+)?`?([A-Za-z][\w-]*)", after)
                words = [re.sub(r"['’]s?$", "", w).lower() for w in re.findall(r"[A-Za-z][\w'’-]*", clause)][-5:]
                adjacent = words[-1:]
                if of_the:
                    words.append(of_the.group(1).lower())
                    adjacent.append(of_the.group(1).lower())
                own_skill = next((s for s in skill_names if path.stem.startswith(s) or s in path.parts), None)
                named = [w for w in words if w in DOC_NOUNS or (w in stems and path.name not in stems[w])]
                # A skill's name qualifies only right beside the number ("resume-tailor's
                # §8"), and never in that skill's own spec, which names it constantly.
                named += [w for w in adjacent if w in skill_names and w != own_skill]
                low_clause = " ".join(words)
                named += [phrase for phrase, name in spaced.items() if name != path.name and phrase in low_clause]
                if named:
                    fail(group, f"{where} after \"{named[0]}\" — a reference into another file is "
                                f"written `name.md` §{number}; a local one, \"this file's §{number}\"")
                    continue
                if others:
                    fail(group, f"{where} in a block naming `{others[0]}` — write `{others[0]}` "
                                f"§{number} if that is meant, or \"this file's §{number}\"")
                    continue
                if label:
                    elsewhere = sorted(name for name, heads in titles.items()
                                       if name != path.name and number in heads
                                       and set(label) <= set(content_words(heads[number])))
                    if elsewhere:
                        fail(group, f"{where} labelled \"{' '.join(label)}\" — that is `{elsewhere[0]}` "
                                    f"§{number} (\"{titles[elsewhere[0]][number]}\"); this file's "
                                    f"§{number} is \"{own[number]}\"")
    if checked == 0:
        fail(group, "no section references found — the check would pass vacuously")
    elif not any(f.startswith("[sections]") for f in failures):
        ok(group, f"all {checked} section references resolve")


# COUNT_WORDS (zero to twelve) is imported from ledger_rules, which counts with it too.
# A count is a number word with a noun after it, so "forbade all three" and
# "exactly one of" are not counts. The noun may carry one modifier ("five
# question types"); the lazy group tries the bare noun first, so "Four things
# this ledger" counts things rather than "this".
# Digits count too: "# 7 interviewer personas" in a README tree is a restatement
# like any other. One or two digits only, and never after §, $ or £.
COUNT_PHRASE = re.compile(
    r"(?<![§$£\w.–-])\b(two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|\d{1,2})\s+"
    r"(?:[*_`]*([a-z][a-z-]*)[*_`]*\s+)??[*_`]*([a-z]+s|people|criteria)\b", re.IGNORECASE)
NOT_NOUNS = frozenset("this is was has does his its us as plus less across thus always unless "
                      "whereas perhaps yes".split())
TIME_NOUNS = frozenset("seconds minutes hours days weeks months years".split())
SECTION_NOUNS = frozenset("rules sections parts principles steps stages phases disciplines".split())
# "Four things …, and one it is refusing": the "one" is a second count only in
# that form, and never in "and one-line reasons" or "and one example".
AND_ONE = re.compile(r",\s+(?:and|plus)\s+one\s+(?=(?:it|that|which|this|they|we|is|was|are)\b)", re.IGNORECASE)
PARTITIVE = re.compile(r"(?:\bof the|\bthe other)\s+$", re.IGNORECASE)
COORDINATED = re.compile(r"\b(?:and|plus)\s+$", re.IGNORECASE)
ITEM = re.compile(r"^([ \t]*)(?:- |\* |\d+\. )")
TABLE_ROW = re.compile(r"^[ \t]*\|")
TABLE_RULE = re.compile(r"^[ \t]*\|[\s:|-]+\|\s*$")
HEADING_LINE = re.compile(r"^(#{2,6}) ")


def count_phrases(text: str, digits: bool = False) -> list[tuple[int, str, re.Match]]:
    """(count, noun, match) for every counted noun phrase in the text.

    Digits are read only where asked — a README tree's "# 7 interviewer
    personas" — because in a lead-in "the first 90 days:" is not a count of the
    list below it. Time units are never counts.
    """
    found = []
    for match in COUNT_PHRASE.finditer(text):
        noun = match.group(3).lower()
        word = match.group(1).lower()
        if noun in NOT_NOUNS or noun in TIME_NOUNS or (word.isdigit() and not digits):
            continue
        found.append((int(word) if word.isdigit() else COUNT_WORDS[word], noun, match))
    return found


def stated_count(lead: str) -> int:
    """The count a lead-in states: its first count, plus any coordinated with it.

    "Four things …, and one it is refusing" is five. "Four bugs, found in two
    harnesses" is four — summing every count in the sentence made a lead-in wrong
    for mentioning a second quantity, and "of the six axes, these two" is two.
    """
    found = count_phrases(lead)
    phrases = [(n, m) for n, _, m in found if not PARTITIVE.search(lead[:m.start()])] or [(n, m) for n, _, m in found[:1]]
    if not phrases:
        return len(AND_ONE.findall(lead))
    total = phrases[0][0]
    for n, m in phrases[1:]:
        if COORDINATED.search(lead[:m.start()]):
            total += n
    return total + len(AND_ONE.findall(lead))


def unfenced(lines: list[str]) -> list[str]:
    """The lines with fenced code blanked out, so a YAML comment is never a lead-in."""
    out, fenced = [], False
    for line in lines:
        if line.lstrip().startswith("```"):
            fenced = not fenced
            out.append("")
        else:
            out.append("" if fenced else line)
    return out


def items_at(lines: list[str], j: int) -> tuple[int, str | None]:
    """Count the list or table starting at line j, after any blank lines.

    A list counts items at its first item's indent, so nested bullets under an
    item are not items of the list; a table counts rows below its header.
    """
    while j < len(lines) and not lines[j].strip():
        j += 1
    if j >= len(lines):
        return 0, None
    if TABLE_ROW.match(lines[j]):
        rows = 0
        while j < len(lines) and TABLE_ROW.match(lines[j]):
            rows += 0 if TABLE_RULE.match(lines[j]) else 1
            j += 1
        return rows - 1, "table rows"
    first = ITEM.match(lines[j])
    if not first:
        return 0, None
    indent, count = len(first.group(1)), 0
    while j < len(lines):
        line = lines[j]
        item = ITEM.match(line)
        if item and len(item.group(1)) == indent:
            count += 1
        elif (item and len(item.group(1)) > indent) or (line.strip() and line[:indent + 1].isspace()
                                                        and len(line) - len(line.lstrip()) > indent):
            pass                                    # a nested item, or an item's continuation
        elif not line.strip():
            k = j + 1
            while k < len(lines) and not lines[k].strip():
                k += 1
            nxt = ITEM.match(lines[k]) if k < len(lines) else None
            if nxt and len(nxt.group(1)) >= indent:
                j = k
                continue
            break
        else:
            break
        j += 1
    return count, "items"


def paragraph_blocks(lines: list[str]):
    """(first line, last line, joined text, is_heading) for each heading and prose paragraph.

    Joining the lines is the point: a lead-in hard-wrapped before its colon was
    invisible to a check that read one line at a time.
    """
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or ITEM.match(line) or TABLE_ROW.match(line):
            i += 1
            continue
        if HEADING_LINE.match(line):
            yield i, i, line, True
            i += 1
            continue
        start, parts = i, []
        while (i < len(lines) and lines[i].strip() and not ITEM.match(lines[i])
               and not TABLE_ROW.match(lines[i]) and not HEADING_LINE.match(lines[i])):
            parts.append(lines[i].strip())
            i += 1
        yield start, i - 1, " ".join(parts), False


LINK_TAIL = re.compile(r"`?(?:'s)?(?:\]\([^)]*\))?`?")


def linked_restatements(text: str) -> list[tuple[str, int, str, int, str]]:
    """(file, count, noun, offset, phrase) for each count tied to a file by syntax.

    Nearness was tried and misread in both directions: a sentence either side
    paired "two axes" in mock-interview with the reframing audit's six, and a
    subset exception written for "two rules in `x.md` decide" let "the five
    rules in `x.md`" through. A count is now read as restating a file only when
    the text ties it there:
      - on the same line of a code block, as a README tree's comment is;
      - after the file name and a dash, colon or #, in the same clause —
        "`reframing-audit.md` — six axes of drift and five disciplines";
      - as the file's possessive — "`x.md`'s six rules";
      - as "the N nouns in/of `x.md`".
    """
    found: list[tuple[str, int, str, int, str]] = []
    fenced_lines, offset, fenced = set(), 0, False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif fenced:
            fenced_lines.add(offset)
        offset += len(line) + 1
    for mention in FILE_NAME.finditer(text):
        name = mention.group(1)
        line_start = text.rfind("\n", 0, mention.start()) + 1
        line_end = text.find("\n", mention.end())
        line_end = len(text) if line_end < 0 else line_end
        tail_at = LINK_TAIL.match(text, mention.end()).end()
        spans = []
        if line_start in fenced_lines:
            spans.append((tail_at, line_end))
        appositive = re.match(r"\s*(?:—|–|:|#)\s*", text[tail_at:line_end])
        if appositive:
            clause = re.search(r"[.;]\s|$", text[tail_at + appositive.end():line_end])
            spans.append((tail_at, tail_at + appositive.end() + min(clause.start(), 120)))
        if text.startswith("'s", mention.end()) or text.startswith("`'s", mention.end()):
            spans.append((tail_at, min(line_end, tail_at + 40)))
        for a, b in dict.fromkeys(spans):
            for count, noun, match in count_phrases(text[a:b], digits=True):
                found.append((name, count, noun, a + match.start(), match.group(0)))
        definite = re.search(r"\bthe\s+((?:two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+"
                             r"(?:[a-z-]+\s+)??[a-z]+s)\s+(?:in|of|from)\s+`?(?:[\w/-]+/)?$",
                             text[max(0, mention.start() - 80):mention.start()], re.IGNORECASE)
        if definite:
            for count, noun, match in count_phrases(definite.group(1)):
                found.append((name, count, noun, mention.start(), match.group(0)))
    return found


def counted_lists(path: Path) -> list[tuple[int, int, int, str, str]]:
    """Every count in a file paired with what it counts: (line, stated, actual, what, lead).

    This is the one place the shapes are listed. A count in words or digits in:
      - a paragraph ending in a colon (emphasis around it ignored), above a list
        — nested lists count at their own indent — or a table;
      - a heading above a list or a table, above its own subheadings, above one
        introductory paragraph and then a list, or above paragraphs that each
        open with a bold label;
      - a paragraph opening with a count, after emphasis or "These", ahead of
        numbered `## 1.` sections, the way output-discipline.md introduces its
        rules.
    In a paragraph lead-in only the sentence carrying the colon is read.
    """
    lines = unfenced(path.read_text(encoding="utf-8").split("\n"))
    found = []
    blocks = list(paragraph_blocks(lines))
    for index, (start, end, text, is_heading) in enumerate(blocks):
        if is_heading:
            lead = text
        elif re.sub(r"[*_`\s]+$", "", text).endswith(":"):
            # Only the sentence carrying the colon. An earlier sentence's count
            # is usually about something else — "The two axes measure different
            # things: … They meet whenever …:" sits above a four-row table.
            lead = re.split(r"(?<=[.!?])[*_]*\s+(?=[A-Z*`])", text)[-1]
        else:
            continue
        if not count_phrases(lead) and not AND_ONE.search(lead):
            continue
        actual, what = items_at(lines, end + 1)
        if not what and is_heading:
            level = len(HEADING_LINE.match(text).group(1))
            subs = 0
            for line in lines[end + 1:]:
                heading = HEADING_LINE.match(line)
                if heading and len(heading.group(1)) <= level:
                    break
                if heading and len(heading.group(1)) == level + 1:
                    subs += 1
            if subs:
                actual, what = subs, "subsections"
            elif index + 1 < len(blocks) and not blocks[index + 1][3]:
                actual, what = items_at(lines, blocks[index + 1][1] + 1)
        if what:
            found.append((start + 1, stated_count(lead), actual, what, lead))
    text = "\n".join(lines)
    numbered = re.findall(r"^## (\d+)\. ", text, re.MULTILINE)
    first = re.search(r"^## 1\. ", text, re.MULTILINE)
    if first:
        before = text[:first.start()].count("\n")
        for start, end, para, is_heading in blocks:
            if start < before and not is_heading:
                opening = [o for o in count_phrases(para) if o[1] in SECTION_NOUNS]
                if opening and re.fullmatch(r"\s*(?:[*_]+\s*)?(?:(?:These|The|Its|Our)\s+)?(?:[*_]+\s*)?",
                                            para[:opening[0][2].start()]):
                    found.append((start + 1, opening[0][0], len(numbered), "numbered sections",
                                  opening[0][2].group(0)))
    return found


def check_counts() -> None:
    """A count agrees with what it counts, in its own file and wherever it is restated.

    "Two overrides that beat every label:" sat above three bullets, and "Five
    disciplines make the audit actually catch things:" above six, after a sixth
    was added and the lead-in was not updated — with "five disciplines" restated
    in a dozen places, so settling which side to change meant reading every one.

    The first version recognised one shape: the count word first on the line, the
    colon on the same line, a bulleted list below. The repository writes counts
    in the other shapes counted_lists names, and the check passed them all
    without a word. And
    README.md, restating output-discipline.md as "five rules" after a sixth was
    added, was exactly the cross-file drift it declared out of scope.

    So a count is now read wherever it introduces a list, table or run of
    sections (counted_lists names the shapes), and a count the text ties to the
    file holding its list — "`reframing-audit.md` — six axes" — is checked against
    that list, matched on the noun; linked_restatements says what counts as tied,
    and why nearness was not enough. A restatement not tied to a file is
    unchecked: "axes" means persona and question-type axes in mock-interview, and
    a check keyed on the word alone misfires on it.
    """
    group = "counts"
    checked = 0
    targets: dict[str, Path] = {}
    for path in list(CONVENTIONS.glob("*.md")) + list((REPO / "docs").glob("*.md")):
        targets[path.name] = path
    for skill in skills():
        for ref in (skill / "references").glob("*.md"):
            targets.setdefault(ref.name, ref)
    by_noun: dict[str, dict[str, set[int]]] = {}
    for name, path in targets.items():
        for _, _, actual, _, lead in counted_lists(path):
            for _, noun, _ in count_phrases(lead):
                by_noun.setdefault(name, {}).setdefault(noun, set()).add(actual)

    for path in citing_files() + [CITATIONS]:
        rel = path.relative_to(REPO)
        for line, stated, actual, what, lead in counted_lists(path):
            checked += 1
            if stated != actual:
                fail(group, f"{rel}:{line}: says {stated}, has {actual} {what} — \"{lead.strip()[:70]}\"")
        text = path.read_text(encoding="utf-8")
        for name, count, noun, at, phrase in linked_restatements(text):
            held = by_noun.get(name, {}).get(noun)
            if name == path.name or not held:
                continue
            checked += 1
            if count not in held:
                fail(group, f"{rel}:{text[:at].count(chr(10)) + 1}: \"{' '.join(phrase.split())}\" beside "
                            f"`{name}`, which has {' or '.join(map(str, sorted(held)))} {noun}")
    if checked == 0:
        fail(group, "no counted lists found — the check would pass vacuously")
    elif not any(f.startswith("[counts]") for f in failures):
        ok(group, f"all {checked} counts agree with what they count")


TREE_LINE = re.compile(r"^((?:│   |    )*)[├└]── ([\w.-]+/?)", re.MULTILINE)
# "N fixtures", or "N test/eval cases" — not "two cases" of anything else.
FIXTURE_COUNT = re.compile(r"\b(\d+|two|three|four|five|six|seven|eight|nine|ten)\s+"
                           r"(?:(?:test\s+|eval\s+|evaluation\s+)?fixtures|(?:test|eval|evaluation)\s+cases)\b",
                           re.IGNORECASE)


def tree_paths(text: str) -> set[str]:
    """The file paths a README's folder tree draws, rebuilt from its indentation.

    Reading only the names let a file drawn in the wrong folder satisfy both
    halves of the check at once.
    """
    paths, stack = set(), []
    for indent, name in TREE_LINE.findall(text):
        depth = len(indent) // 4
        stack = stack[:depth]
        if name.endswith("/"):
            stack.append(name[:-1])
        else:
            paths.add("/".join(stack + [name]))
    return paths


def check_readmes() -> None:
    """A skill README's inventory matches the folder it describes.

    Each README draws its folder as a tree, and none of the three had been
    updated as mirrors arrived: between them they omitted fourteen files, and mock-interview's still described four fixtures when it had six.
    An inventory is a count and a list at once, stated a second time, so it is
    held to what it inventories: every file under references/ and evals/ appears
    in the tree, every file the tree names exists, and a fixture count matches
    evals.json.
    """
    group = "readmes"
    checked = 0
    for skill in skills():
        readme = skill / "README.md"
        if not readme.exists():
            fail(group, f"{skill.name}: no README.md")
            continue
        text = readme.read_text(encoding="utf-8")
        listed = {path.split("/", 1)[1] if path.startswith(skill.name + "/") else path
                  for path in tree_paths(text)}
        if not listed:
            fail(group, f"{skill.name}: README.md draws no folder tree")
            continue
        present = {str(f.relative_to(skill)) for f in skill.rglob("*")
                   if f.is_file() and "__pycache__" not in f.parts}
        for sub in ("references", "evals"):
            for f in sorted((skill / sub).glob("*")):
                if f.is_file():
                    checked += 1
                    if f"{sub}/{f.name}" not in listed:
                        fail(group, f"{skill.name}: README.md's tree omits {sub}/{f.name}")
        for name in sorted(listed - present):
            fail(group, f"{skill.name}: README.md's tree names {name}, which does not exist")
        evals_path = skill / "evals" / "evals.json"
        data = load_evals(evals_path)
        if data is not None:
            fixtures = len(data)
            for match in FIXTURE_COUNT.finditer(text):
                word = match.group(1).lower()
                stated = int(word) if word.isdigit() else COUNT_WORDS[word]
                checked += 1
                if stated != fixtures:
                    line = text[:match.start()].count("\n") + 1
                    fail(group, f"{skill.name}/README.md:{line}: \"{match.group(0)}\" — evals.json has {fixtures}")
    if checked == 0:
        fail(group, "no skill README inventories found — the check would pass vacuously")
    elif not any(f.startswith("[readmes]") for f in failures):
        ok(group, f"all {checked} README inventory entries match their folders")


# PRIORITY_ORDER, FIT_ORDER, BANDS, ROW_ID, COUNTED, FRACTION and TIER_WORDS come
# from ci/ledger_rules.py, as do the rule functions used below and
# LEDGER_ITEM, the one grammar of a ledger item the harness reads runs with too.
LEDGER_LINE = re.compile(r"^- `?(" + "|".join(PRIORITY_ORDER) + r")`? — (.+)$")
LEDGER_GROUP = re.compile(r"^(" + "|".join(FIT_ORDER) + r"): (.+)$")
LEDGER_ITEM = ledger_rules.LEDGER_ITEM
# The worked dossier is two files, split so no step reads more than it needs: the
# report (snapshot, map, register, target accounting) and the JSON envelope that
# closes the same emitted file. The check reads them as the one dossier they are.
WORKED_DOSSIER = "skills/job-underwriter/references/dossier-worked-report.md"
WORKED_ENVELOPE = "skills/job-underwriter/references/dossier-worked-envelope.md"


def parse_fit_ledger(snapshot: str) -> tuple[list[tuple[str, str, str, str | None]], list[str]]:
    """(priority, fit, id, name) per item of the snapshot's ledger, and what failed to parse."""
    lines = snapshot.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == "**Fit ledger.**")
    except StopIteration:
        return [], ["no **Fit ledger.** line"]
    items, problems = [], []
    body = lines[start + 1:]
    while body and not body[0].strip():
        body = body[1:]
    tiers_seen: set[str] = set()
    for line in body:
        if not line.startswith("- "):
            break
        m = LEDGER_LINE.match(line.strip())
        if not m:
            problems.append(f"unparseable ledger line: {line.strip()!r}")
            continue
        if m.group(1) in tiers_seen:
            problems.append(f"tier {m.group(1)} has more than one ledger line")
        tiers_seen.add(m.group(1))
        fits_seen: set[str] = set()
        for group in m.group(2).split(" · "):
            g = LEDGER_GROUP.match(group.strip())
            if not g:
                problems.append(f"unparseable group {group.strip()!r}")
                continue
            if g.group(1) in fits_seen:
                problems.append(f"fit {g.group(1)} appears twice under {m.group(1)}")
            fits_seen.add(g.group(1))
            for item in ledger_rules.split_top(g.group(2), (", ",)):
                i = LEDGER_ITEM.match(item.strip())
                if not i:
                    problems.append(f"unparseable item {item.strip()!r} (one ID, no ranges)")
                    continue
                items.append((m.group(1), g.group(1), i.group(1), i.group(2)))
    if not items and not problems:
        problems.append("**Fit ledger.** is followed by no ledger lines")
    return items, problems


def check_fit_ledger() -> None:
    """The worked dossier's fit ledger is its own evidence map, projected.

    It was a sentence from v0.1: "five of seven material requirements are
    `direct` (R1–R3, R6, and the eligibility gate)", above a map with four, the
    gate counted once by ID and again by name. The JSON summary repeated it, the
    two copies agreed with each other, and measured runs copied the form — then
    got their own counts wrong the same way. Nothing read the sentence against the
    table it summarised, because nothing could: a count in prose has no fixed
    shape. The ledger is now a projection with a grammar, so it can be read
    exactly, and this check reads it against both the table and the envelope. A
    worked dossier whose ledger cannot be parsed fails rather than skips, so a
    revert to prose is caught, not excused.
    """
    group = "fit-ledger"
    quantifier_drift(group)  # the list's own drift check runs whether or not the dossier parses
    path = REPO / WORKED_DOSSIER
    text = path.read_text(encoding="utf-8")
    snap = re.search(r"^## Decision snapshot\s*$(.*?)(?=^## )", text, re.MULTILINE | re.DOTALL)
    table_sec = re.search(r"^## Evidence map\s*$(.*?)(?=^## )", text, re.MULTILINE | re.DOTALL)
    if not snap or not table_sec:
        fail(group, f"{WORKED_DOSSIER}: no Decision snapshot or Evidence map section")
        return
    items, problems = parse_fit_ledger(snap.group(1))
    for problem in problems:
        fail(group, f"{WORKED_DOSSIER}: fit ledger: {problem}")
    if not items:
        return

    rows = [line for line in table_sec.group(1).splitlines() if line.startswith("|")]
    header = [c.strip().strip("`").lower() for c in rows[0].strip().strip("|").split("|")] if rows else []
    try:
        cid, creq, cpri, cfit, cconf = (header.index(k) for k in ("#", "requirement", "priority", "fit", "confidence"))
    except ValueError:
        fail(group, f"{WORKED_DOSSIER}: the evidence map has no #, Requirement, Priority, Fit and Confidence columns")
        return
    table = {}
    for line in rows[2:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        table[cells[cid]] = {"requirement": cells[creq], "priority": cells[cpri].strip("`"),
                             "fit": cells[cfit].strip("`"), "confidence": cells[cconf].strip("`")}
    blocks = re.findall(r"```json\n(.*?)\n```", (REPO / WORKED_ENVELOPE).read_text(encoding="utf-8"), re.DOTALL)
    try:
        envelope = json.loads(blocks[-1])["sections"]["evidence_map"]
        env = {r["requirement_id"]: r for r in envelope}
    except (IndexError, KeyError, TypeError, ValueError):
        fail(group, f"{WORKED_ENVELOPE}: no evidence_map in the last json block")
        return

    seen: dict[str, int] = {}
    order = [(PRIORITY_ORDER.index(p), FIT_ORDER.index(f)) for p, f, _, _ in items]
    if order != sorted(order):
        fail(group, f"{WORKED_DOSSIER}: fit ledger is not in enum order (priority, then fit)")
    for priority, fit, rid, name in items:
        seen[rid] = seen.get(rid, 0) + 1
        row = table.get(rid)
        if row is None:
            fail(group, f"{WORKED_DOSSIER}: fit ledger names {rid}, which the evidence map does not have")
            continue
        if (priority, fit) != (row["priority"], row["fit"]):
            fail(group, f"{WORKED_DOSSIER}: fit ledger files {rid} as {priority}/{fit}; the map says {row['priority']}/{row['fit']}")
        e = env.get(rid)
        if e is None or (priority, fit) != (e.get("priority"), e.get("fit_status")):
            got = "missing" if e is None else f"{e.get('priority')}/{e.get('fit_status')}"
            fail(group, f"{WORKED_DOSSIER}: fit ledger files {rid} as {priority}/{fit}; the envelope says {got}")
        if fit != "direct":
            if not name:
                fail(group, f"{WORKED_DOSSIER}: fit ledger's {rid} is below direct and carries no name")
            elif not ledger_rules.names_requirement(name, row["requirement"]):
                fail(group, f"{WORKED_DOSSIER}: fit ledger names {rid} \"{name}\" in words its Requirement cell does not use")
    for rid, n in seen.items():
        if n > 1:
            fail(group, f"{WORKED_DOSSIER}: fit ledger lists {rid} {n} times")
    for rid in sorted(set(table) - set(seen)):
        fail(group, f"{WORKED_DOSSIER}: fit ledger omits {rid}, which the evidence map has")
    for rid in sorted(set(env) - set(table)):
        fail(group, f"{WORKED_DOSSIER}: the envelope's evidence_map has {rid} and the table does not")

    # The snapshot is read through its last slot: the paragraph the template adds
    # after the slots explains the rules to its reader and is not the snapshot.
    snapshot = ledger_rules.slot_extent(snap.group(1))
    for problem in ledger_rules.band_problems(snapshot, {rid: row["confidence"] for rid, row in table.items()}):
        fail(group, f"{WORKED_DOSSIER}: {problem}")

    try:
        summary = json.loads(blocks[-1])["sections"]["decision"]["summary"]
    except (KeyError, TypeError, ValueError):
        summary = ""
    # Every set claim over the map where the rule asks for naming — the summary, the
    # sentence after the ledger and the rest of the snapshot — is read by the one
    # reader the harness calls too (evidence-model.md, "The row is the unit"; what it
    # reads and what it leaves to the grader, above Claim in ci/ledger_rules.py).
    counted = ledger_rules.map_claim(summary)
    if counted:
        fail(group, f"{WORKED_ENVELOPE}: decision.summary: {counted.why}")

    # Everything between the ledger and the next slot is rule 2's "at most one
    # sentence" (after_ledger_claim), where every word of the lists and every ratio
    # is read as about the map, and a bare "none" is a complement. The rest of the
    # snapshot, like the summary above, is read by map_claim; bare "none" is not
    # read there, because the slots require "none failed" and "none found".
    after = ledger_rules.ledger_sentence(snapshot)
    hit = after and ledger_rules.after_ledger_claim(after)
    if ledger_rules.is_second_sentence(after, hit):
        fail(group, f"{WORKED_DOSSIER}: the fit ledger is followed by more than one sentence (\"{hit.text[:80]}\"); rule 2 allows one")
    elif hit:
        fail(group, f"{WORKED_DOSSIER}: the sentence after the fit ledger: {hit.why}")
    hit = ledger_rules.map_claim(ledger_rules.snapshot_prose(snapshot))
    if hit:
        fail(group, f"{WORKED_DOSSIER}: the snapshot's prose: {hit.why}")

    try:
        status = json.loads(blocks[-1])["sections"]["candidate_constraints"]["status"]
    except (KeyError, TypeError, ValueError):
        status = None
    for _, problem in ledger_rules.gates_line_problems(
            snapshot, table, None if status is None else status == "unknown"):
        fail(group, f"{WORKED_DOSSIER}: {problem}")
    register = ledger_rules.register_severities(text)
    if register is None:
        fail(group, f"{WORKED_DOSSIER}: no risk register with # and Severity columns to read severities from")
    else:
        for _, problem in ledger_rules.severity_problems(snapshot, register):
            fail(group, f"{WORKED_DOSSIER}: {problem}")

    budget = re.search(r"at most (\d+) targeted searches and (\d+) page fetches",
                       (REPO / "skills/job-underwriter/SKILL.md").read_text(encoding="utf-8"))
    # The tally line is read with the harness's own pattern (output_checks.TALLY), so
    # the worked line and a run's line are held to one form.
    tallies = [line for line in text.splitlines() if re.match(r"\s*Research tier\s*:", line)]
    if len(tallies) != 1:
        fail(group, f"{WORKED_DOSSIER}: {len(tallies)} Research tier lines; the rule is exactly one")
    else:
        m = output_checks.TALLY.search(tallies[0].strip())
        if not m:
            fail(group, f"{WORKED_DOSSIER}: the Research tier line does not read in the form SKILL.md gives: {tallies[0]!r}")
        elif m.group(1).upper() == "L1" and m.group(6):
            fail(group, f"{WORKED_DOSSIER}: the Research tier line is L1 and reads \"no searches\"")
        elif m.group(1).upper() == "L1":
            if budget and (m.group(3), m.group(5)) != budget.groups():
                fail(group, f"{WORKED_DOSSIER}: the Research tier line's budget is {m.group(3)}/{m.group(5)}; SKILL.md's L1 budget is {budget.group(1)}/{budget.group(2)}")
            elif int(m.group(2)) > int(m.group(3)) or int(m.group(4)) > int(m.group(5)):
                fail(group, f"{WORKED_DOSSIER}: the Research tier line spends more than its budget")
    if not any(f.startswith(f"[{group}]") for f in failures):
        ok(group, f"worked dossier: fit ledger matches the evidence map and the envelope, {len(items)} rows")


# A quoted span in a grader expectation: straight, curly, single or double quotes;
# an apostrophe inside a word ("ledger's") neither opens nor closes one.
GRADER_QUOTE = re.compile(r"(?<!\w)['‘\"“]((?:[^'\"‘’“”\n]|(?<=\w)['’](?=\w))+)['’\"”](?!\w)")


def quantifier_drift(group: str) -> None:
    """D9: the quantifier lists are written once, in evidence-model.md.

    Its "The row is the unit" bullet is the rule, with its words in three lists: the
    named-set words, which a named set may carry; the complements, which fail in the
    snapshot whatever they name; and the further one — a bare "none" — it makes a
    complement in the one sentence after the fit ledger. ci/ledger_rules.py holds
    exactly those lists (NAMED_SET, COMPLEMENT, AFTER_LEDGER_ONLY); risk-and-decision.md's
    rule 2 points to the bullet and spells none of it; and every job-underwriter
    expectation that speaks of quantifiers quotes each word of the lists, sorted as the
    rule sorts them — a named-set word inside the expectation's sentence on the
    named-set words, a complement inside its sentence on the complements, and the
    scoped word inside its sentence about the sentence after the ledger and nowhere
    else — so a grader is never told a named "the rest" passes, or bare 'none' is
    exempt.
    """
    refs = REPO / "skills/job-underwriter/references"
    named, complement, after_only = ledger_rules.rule_quantifier_scopes(
        (refs / "evidence-model.md").read_text(encoding="utf-8"))
    if not named or not complement or not after_only:
        fail(group, "evidence-model.md's \"The row is the unit\" lists — the named-set words, the complements, and "
                    "the word scoped to the sentence after the ledger — were not found; the drift check would pass "
                    "vacuously")
        return
    for label, rule, shared in (("named-set words", named, list(ledger_rules.NAMED_SET)),
                                ("complements", complement, list(ledger_rules.COMPLEMENT)),
                                ("words scoped to the sentence after the ledger", after_only,
                                 list(ledger_rules.AFTER_LEDGER_ONLY))):
        missing = [q for q in rule if q not in shared]
        extra = [q for q in shared if q not in rule]
        if missing:
            fail(group, f"ci/ledger_rules.py lacks {missing} from evidence-model.md's {label}")
        if extra:
            fail(group, f"ci/ledger_rules.py holds {extra} among the {label}, which evidence-model.md's list does not")
    every = named + complement + after_only

    decision = (refs / "risk-and-decision.md").read_text(encoding="utf-8")
    rule2 = re.search(r"^2\. \*\*Fit ledger\*\*.*$", decision, re.MULTILINE)
    if not rule2:
        fail(group, "risk-and-decision.md has no rule 2 (\"2. **Fit ledger**\") to read")
    else:
        if "evidence-model.md" not in rule2.group(0) or '"The row is the unit"' not in rule2.group(0):
            fail(group, "risk-and-decision.md rule 2 no longer points to evidence-model.md (\"The row is the "
                        "unit\") for the rule the sentence after the ledger is held to")
        spelled = sorted({m.group(1) for m in GRADER_QUOTE.finditer(rule2.group(0))} & set(every))
        if spelled:
            fail(group, f"risk-and-decision.md rule 2 spells {spelled} from evidence-model.md's lists — a second "
                        f"copy of them; point to the lists instead")

    def segment(expectation: str, marker: re.Pattern) -> tuple[int, int] | None:
        hit = marker.search(expectation)
        if not hit:
            return None
        stop = re.search(r"[.;](?:\s|$)", expectation[hit.start():])
        return hit.start(), hit.start() + stop.start() if stop else len(expectation)

    def quoted(text: str) -> set[str]:
        return {m.group(1) for m in GRADER_QUOTE.finditer(text)}

    for case in load_evals(REPO / "skills/job-underwriter/evals/evals.json") or []:
        for n, expectation in enumerate(case.get("expectations", []), 1):
            if "quantifier" not in expectation:
                continue
            where = f"job-underwriter eval {case.get('id')} #{n}"
            spans = {name: segment(expectation, marker) for name, marker in (
                ("named-set words", ledger_rules.NAMED_SET_MARK), ("complements", ledger_rules.COMPLEMENT_MARK),
                ("after", ledger_rules.SCOPE_TURN))}
            inside = {name: quoted(expectation[span[0]:span[1]]) if span else set() for name, span in spans.items()}
            everywhere = quoted(expectation)
            lacking = [q for q in named + complement if q not in everywhere]
            if lacking:
                fail(group, f"{where} lists quantifiers without {lacking} from evidence-model.md's lists")
            for name, words, other in (("named-set words", named, complement + after_only),
                                       ("complements", complement, named)):
                if spans[name] is None:
                    fail(group, f"{where} speaks of quantifiers without a sentence on the {name}, as "
                                f"evidence-model.md sorts them")
                    continue
                astray = [q for q in words if q in everywhere and q not in inside[name]]
                if astray:
                    fail(group, f"{where} quotes {astray} outside its sentence on the {name}")
                mixed = [q for q in other if q in inside[name] and q not in inside["after"]]
                if mixed:
                    fail(group, f"{where} quotes {mixed} in its sentence on the {name}; "
                                f"evidence-model.md does not list them there")
                # The list itself is the sentence's first parenthesis; its examples follow
                # it, so only the parenthesis is held to the rule's list, word for word.
                listed = re.search(r"\(([^()]*)\)", expectation[spans[name][0]:spans[name][1]])
                listed = quoted(listed.group(1)) if listed else set()
                if not listed:
                    fail(group, f"{where} has no parenthesised list in its sentence on the {name}; the drift "
                                f"check would pass vacuously")
                extra = sorted(listed - set(words))
                if extra:
                    fail(group, f"{where} lists {extra} among the {name}, which evidence-model.md's list does not")
            lacking = [q for q in after_only if q not in inside["after"]]
            if lacking:
                fail(group, f"{where} lists quantifiers without {lacking}, which evidence-model.md's list scopes to "
                            f"the sentence after the ledger — say so \"in the one sentence after\" the ledger")
            outside = quoted(expectation[:spans["after"][0]] + " | " + expectation[spans["after"][1]:]) \
                if spans["after"] else everywhere
            stray = [q for q in after_only if q in outside]
            if stray:
                fail(group, f"{where} quotes {stray} outside its sentence on the sentence after the ledger; "
                            f"evidence-model.md's list scopes them there, and the token `none` in backticks is "
                            f"a band or a gap type")


# Phrases an installed file shares with a fixture by design, never as an example: the
# shared contract's own words, which a fixture that feeds a skill a dossier or a
# schema field necessarily repeats. Each is masked wherever it appears, so the words
# around it are still read. Nothing else belongs here — a phrase that is merely
# common is a reason to rewrite the example, not to list it.
ANSWER_KEY_CONTRACT = {
    "confirmed, limited inspectable proof - expect a probe":
        "the verification caveat evidence-conventions.md tells a skill to name beside a `medium` claim; a "
        "dossier carries it in these words, and mock-interview eval 4's prompt is a dossier",
}
# Window sizes, measured on the clean tree (CONTRIBUTING.md says what each caught).
# A quoted span is a worked example, so three content words in a row shared with a
# fixture fail it; unquoted rule prose fails at six words in a row, stopwords
# included, which no shared collocation in the tree reaches.
QUOTED_RUN = 3
PROSE_RUN = 6
ANSWER_KEY_STOP = STOPWORDS | {"i", "me", "my", "we", "us"}
KEY_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")
KEY_QUOTES = {ord("“"): '"', ord("”"): '"', ord("‘"): "'", ord("’"): "'"}


def key_text(text: str) -> str:
    """Lower case, straight quotes, one dash: a translation that keeps every offset."""
    return text.translate(KEY_QUOTES).translate(KEY_DASHES).lower()


def key_tokens(text: str) -> list[str]:
    """Words, and a snake_case identifier as one word: `handoff_to_mock_interview` is a
    schema field a fixture repeats by contract, not five words of its prose."""
    return re.findall(r"[a-z0-9]+(?:_[a-z0-9]+)*(?:'[a-z]+)?", text)


def key_runs(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def masked_contract(text: str) -> str:
    for phrase in ANSWER_KEY_CONTRACT:
        text = text.replace(phrase, " | ")
    return text


QUOTED_SPAN = re.compile(
    r'"([^"\n]+(?:\n[^"\n]+)*?)"'                              # double, straight or curly
    r"|(?<![a-z0-9])'((?:[^'\n]|'(?=[a-z0-9])){8,}?)'(?![a-z0-9])")  # single; an apostrophe is not one
INLINE_CODE = re.compile(r"`[^`\n]+`")


def answer_key_spans(text: str) -> tuple[list[tuple[int, str]], str]:
    """(offset, span) for every quoted span — double, single and curly quotes, and
    code spans holding more than one word — and the prose left when those are taken
    out. Fenced code stays in the prose: an unquoted value in a worked YAML row is
    read like any other sentence. `text` is already key_text()."""
    spans = []
    for m in INLINE_CODE.finditer(text):
        if " " in m.group(0).strip("`").strip():
            spans.append((m.start(), m.group(0).strip("`")))
    blanked = INLINE_CODE.sub(lambda m: " " * len(m.group(0)), text)
    for m in QUOTED_SPAN.finditer(blanked):
        spans.append((m.start(), m.group(1) or m.group(2)))
    prose = QUOTED_SPAN.sub(" | ", blanked)
    return spans, prose


def fixture_haystack(cases: list[dict]) -> list[tuple[str, str]]:
    """(where, text) for everything a clean room shows the model of this skill's
    fixtures: each prompt, and each canned page's title and text — research pages
    and the pages served at links the user gave to read."""
    out = []
    for case in cases:
        out.append((f"eval {case.get('id')}'s prompt", case.get("prompt", "")))
        research = case.get("research") or {}
        for page in [*(research.get("pages") or []), *(research.get("user_pages") or [])]:
            out.append((f"eval {case.get('id')}'s page {page.get('url', '?')}",
                        f"{page.get('title', '')}\n{page.get('text', '')}"))
    return out


def shared_run(span_tokens: list[str], n: int, index: dict[tuple[str, ...], str]) -> tuple[str, str] | None:
    for run in key_runs(span_tokens, n):
        if run in index:
            return " ".join(run), index[run]
    return None


def check_answer_keys() -> None:
    """No skill's installed text shares a run of words with that skill's fixtures.

    A clean room installs a skill's package, so a worked example built from a
    fixture's material is an answer key sitting beside the model while the fixture
    is graded. It happened three times without anyone choosing it, and the exact-
    quote check that followed missed the next four: a near-quote ("growth lead, then
    Head of Growth, at two companies" for the fixture's "at two B2C subscription
    companies"), one in single quotes, and two whose wording had been compressed.
    So every file a run is told to open — SKILL.md's body and its references; not
    citations.md, which quotes sources on purpose, and not the README or docs/, which
    the package carries for people and no run is pointed at — is compared, run by run
    of words, with everything the clean room shows the model of the same skill's
    fixtures: the prompts and the canned research pages. A conventions mirror is
    installed in every skill that carries it, so each copy is read against its own
    skill's fixtures. A quoted span (double, single or curly quotes, or a code span
    of more than one word) fails on QUOTED_RUN content words in a row; the prose
    outside quotes and code spans, fenced code included, fails on PROSE_RUN words in
    a row. A snake_case identifier is one word (key_tokens). ANSWER_KEY_CONTRACT lists the
    contract wording a fixture repeats by design, each with its reason.
    """
    group = "answer-keys"
    checked = 0
    for skill in skills():
        cases = load_evals(skill / "evals" / "evals.json") or []
        content_index: dict[tuple[str, ...], str] = {}
        prose_index: dict[tuple[str, ...], str] = {}
        for where, text in fixture_haystack(cases):
            tokens = key_tokens(key_text(text))
            for run in key_runs([t for t in tokens if t not in ANSWER_KEY_STOP], QUOTED_RUN):
                content_index.setdefault(run, where)
            for run in key_runs(tokens, PROSE_RUN):
                prose_index.setdefault(run, where)
        if not content_index:
            fail(group, f"{skill.name}: no fixture text to compare against — the check would pass vacuously")
            continue
        # The matcher itself, seeded: the first prompt's opening words with one word
        # changed must be caught, or a broken matcher would report a clean tree.
        seed = [t for t in key_tokens(key_text(cases[0].get("prompt", ""))) if t not in ANSWER_KEY_STOP][:8]
        if len(seed) >= QUOTED_RUN + 2 and not shared_run(seed[:QUOTED_RUN + 1] + ["zzz"] + seed[QUOTED_RUN + 2:],
                                                          QUOTED_RUN, content_index):
            fail(group, f"{skill.name}: the matcher missed a seeded near-quote of eval {cases[0].get('id')}")
        files = [skill / "SKILL.md"] + [p for p in sorted((skill / "references").glob("*.md"))
                                         if p.name != "citations.md"]
        for path in files:
            raw = path.read_text(encoding="utf-8")
            if path.name == "SKILL.md" and path.parent == skill:
                raw = re.sub(r"\A---\n.*?\n---\n", lambda m: "\n" * m.group(0).count("\n"), raw, flags=re.S)
            text = key_text(raw)
            spans, prose = answer_key_spans(text)
            rel = f"{skill.name}/{path.relative_to(skill)}"
            for at, span in spans:
                tokens = [t for t in key_tokens(masked_contract(span)) if t not in ANSWER_KEY_STOP]
                if len(tokens) < QUOTED_RUN:
                    continue
                checked += 1
                hit = shared_run(tokens, QUOTED_RUN, content_index)
                if hit:
                    line = text[:at].count("\n") + 1
                    fail(group, f"{rel}:{line}: \"{' '.join(span.split())[:70]}\" is quoted from this skill's own "
                                f"fixtures (\"{hit[0]}\", {hit[1]}) — a worked example the clean room installs as "
                                f"an answer key")
            tokens = []
            for chunk in masked_contract(prose).split("|"):
                tokens += key_tokens(chunk) + ["|"]
            runs = {run for run in key_runs(tokens, PROSE_RUN) if "|" not in run}
            checked += 1
            for run in sorted(runs & set(prose_index)):
                fail(group, f"{rel}: \"{' '.join(run)}\" repeats this skill's own fixtures unquoted "
                            f"({prose_index[run]}) — a worked example the clean room installs as an answer key")
    if checked == 0:
        fail(group, "no quoted spans read — the check would pass vacuously")
    elif not any(f.startswith(f"[{group}]") for f in failures):
        ok(group, f"{checked} quoted spans and files of prose in installed skill text, none sharing a run of "
                  f"words with the skill's own fixtures")


def search_entry(query: str, research: dict, mode: str) -> dict:
    """The log entry a run's search for `query` would leave in a `mode` room: in a
    canned room the stub server's own answer (research_server.search over the corpus
    run_fixtures.write_research_files gives it) tags the call with the targets of the
    pages it returned; in a denied room the call is refused and returns nothing."""
    targets = []
    if mode == "canned":
        _, hits = research_server.search({"entity_tokens": research.get("entity_tokens", []),
                                          "pages": research.get("pages", [])}, query)
        targets = research_server.target_tags(hits)
    return {"kind": "search", "query_or_url": query, "targets": targets}


def check_fixtures() -> None:
    """The fixture fields the harness reads are what the harness assumes (D5).

    Each field below steers a deterministic check, and each fails quietly when it
    drifts: a canary whose `page` names no page of its fixture is never asked for, so
    its check passes in every canned run; a `candidate_text` entry that is not in the
    prompt fails correct quotes; a `candidate_constraints` that is not exactly
    "known" or "unknown" leaves the hard-gates closing clause unjudged; a
    `research.declined` with no decline in the prompt makes lazy no-call
    `unavailable` rows lawful; a `research.user_links` entry that is also a research
    page takes that page's fetch out of the target accounting; a user link a canned
    room serves no `user_pages` entry for is answered "No page at", which returns
    and is counted as read; a user page's `canary` that its page lacks, or that the
    prompt or another page also carries, proves nothing about the read; and a research
    target's `terms` decide which calls were aimed at it, so a sample of another
    target that is aimed at an `n/a` or `skipped` one — by its terms, or in a canned
    room by a page the server returns — fails a correct row, and a target whose terms
    match none of its own queries passes every hunt; and a fixture with research, of a
    skill whose SKILL.md states that every `yes` row names its pages, that does not
    run `yes_names_page` leaves those pages unjudged. Each is read here with the
    harness's own functions (evals/output_checks.py, evals/research_server.py), in
    every mode the fixture runs (run_fixtures.modes_of), so the lint and the checks
    cannot disagree.
    """
    group = "fixtures"
    linted = 0
    for skill in skills():
        # A `yes` row names the pages it rests on: judged (output_checks.YES_PAGES_CHECK)
        # in every fixture with research of a skill whose SKILL.md states it, and in no
        # other, so the check can neither go quiet nor judge a rule a skill never gave.
        states_pages = bool(output_checks.YES_PAGES_RULE.search((skill / "SKILL.md").read_text(encoding="utf-8")))
        for case in load_evals(skill / "evals" / "evals.json") or []:
            label = f"{skill.name} eval {case.get('id')}"
            prompt = output_checks.normalise_quote(case.get("prompt", ""))
            checks = case.get("checks") or []
            runs_pages = output_checks.YES_PAGES_CHECK in checks
            if case.get("research"):
                linted += 1
                if states_pages and not runs_pages:
                    fail(group, f"{label}: SKILL.md states that every `yes` row names its pages and this fixture "
                                f"does not run the {output_checks.YES_PAGES_CHECK} check — its rows' pages would go "
                                f"unchecked")
                elif runs_pages and not states_pages:
                    fail(group, f"{label}: runs the {output_checks.YES_PAGES_CHECK} check, and SKILL.md does not "
                                f"state that every `yes` row names its pages — a rule the skill never gave would "
                                f"be judged")
            elif runs_pages:
                fail(group, f"{label}: runs the {output_checks.YES_PAGES_CHECK} check with no research block — "
                            f"it never runs")
            text = case.get("candidate_text")
            if "quotes" in checks and not isinstance(text, list):
                fail(group, f"{label}: runs the quotes check and declares no candidate_text list — the evidence "
                            f"column would go unchecked ([] says nothing the candidate gave is quotable)")
            for entry in text if isinstance(text, list) else []:
                linted += 1
                if not isinstance(entry, str) or output_checks.normalise_quote(entry) not in prompt:
                    fail(group, f"{label}: candidate_text entry {str(entry)[:60]!r} is not in the prompt — "
                                f"correct quotes of the prompt would fail")
            if "fit_ledger" in checks:
                linted += 1
                if case.get("candidate_constraints") not in output_checks.CONSTRAINTS:
                    fail(group, f"{label}: runs the fit_ledger check and declares candidate_constraints "
                                f"{case.get('candidate_constraints')!r}, not exactly \"known\" or \"unknown\" — the "
                                f"hard-gates line's closing clause would go unjudged")
            research = case.get("research") or {}
            pages = research.get("pages") or []
            modes = run_fixtures.modes_of(case)
            canaries = research.get("canaries") or []

            # The two grounds for sending no call. `declined` is the fixture's word that
            # the prompt declines research or chooses L0; the prompt must say so, in the
            # words `declined_phrase` quotes. `zero_calls` is the other ground (the
            # inputs answer every target), and `declined` already brings its check.
            declined, phrase = research.get("declined"), research.get("declined_phrase")
            if "declined" in research or phrase is not None:
                linted += 1
            if "declined" in research and not isinstance(declined, bool):
                fail(group, f"{label}: research.declined is {declined!r}, not true or false")
            elif declined is True:
                if research.get("zero_calls"):
                    fail(group, f"{label}: declares both research.declined and zero_calls — two different grounds "
                                f"for sending no call, and declined already brings the zero-calls check")
                if not isinstance(phrase, str) or not phrase.strip():
                    fail(group, f"{label}: declares research.declined and no declined_phrase — the prompt's own "
                                f"words that decline research or choose L0")
                elif output_checks.normalise_quote(phrase) not in prompt:
                    fail(group, f"{label}: declined_phrase {phrase[:60]!r} is not in the prompt — a fixture whose "
                                f"user did not decline research would pass no-call unavailable rows")
            elif phrase is not None:
                fail(group, f"{label}: declares a declined_phrase without research.declined: true")

            # A declared user link is an input, never research: one that is also a page
            # (a canary's included) would take that page's fetch out of the accounting.
            links = research.get("user_links")
            if links is not None and not isinstance(links, list):
                fail(group, f"{label}: research.user_links is {type(links).__name__}, not a list")
                links = []
            for link in links or []:
                linted += 1
                if not isinstance(link, str) or not link.strip():
                    fail(group, f"{label}: research.user_links holds {link!r}, not a URL")
                elif any(output_checks.same_url(p.get("url", ""), link) for p in pages):
                    fail(group, f"{label}: user link {link} is also a research page — a fetch of it would be "
                                f"read as the user's input and never charged to the page's target")
                elif any(output_checks.same_url(c.get("page") or "", link) for c in canaries if c.get("page")):
                    fail(group, f"{label}: user link {link} is a canary's page — a user link is never research")

            # The page a canned room serves at a user link (`research.user_pages`), by
            # fetch alone. A link with none is answered "No page at …", which returns,
            # so a run would be credited with reading a page it never saw. A user
            # page's `canary` is a fact only that page carries: on the page, and in
            # neither the prompt nor any other page, or its reaching the response
            # proves nothing about the read.
            upages = research.get("user_pages")
            if upages is not None and not isinstance(upages, list):
                fail(group, f"{label}: research.user_pages is {type(upages).__name__}, not a list")
                upages = []
            for upage in upages or []:
                if not isinstance(upage, dict):
                    fail(group, f"{label}: research.user_pages holds {str(upage)[:60]!r}, not a page")
            upages = [u for u in upages or [] if isinstance(u, dict)]
            declared_links = [link for link in links or [] if isinstance(link, str) and link.strip()]
            for upage in upages:
                linted += 1
                url = str(upage.get("url") or "")
                if not url.strip() or not str(upage.get("text") or "").strip():
                    fail(group, f"{label}: a research.user_pages entry has no url or no text")
                    continue
                if not any(output_checks.same_url(url, link) for link in declared_links):
                    fail(group, f"{label}: user page {url} is not one of research.user_links — the room would "
                                f"serve it and the checks would count its read as research")
                spellings = upage.get("canary") or []
                spellings = [s for s in ([spellings] if isinstance(spellings, str) else spellings) if str(s).strip()]
                if not spellings:
                    continue

                def holds(text: str) -> list[str]:
                    body = output_checks.normalise_ws(output_checks.unify_dashes(text))
                    return [sp for sp in spellings if output_checks.canary_in(
                        output_checks.normalise_ws(output_checks.unify_dashes(sp)), body)]
                if not holds(f"{upage.get('title', '')} {upage.get('text', '')}"):
                    fail(group, f"{label}: no spelling of the canary of user link {url} is on its page")
                elsewhere = [("the prompt", case.get("prompt", ""))] + [
                    (f"page {p.get('url')}", f"{p.get('title', '')} {p.get('text', '')}")
                    for p in pages + [u for u in upages if u is not upage]]
                for where, text in elsewhere:
                    hit = holds(text)
                    if hit:
                        fail(group, f"{label}: the canary of user link {url} ({hit[0]!r}) is also in {where} — "
                                    f"a canary is a fact only its page carries")
            if "canned" in modes:
                for link in declared_links:
                    if not any(output_checks.same_url(str(u.get("url") or ""), link) for u in upages):
                        fail(group, f"{label}: user link {link} has no page in research.user_pages — a canned room "
                                    f"answers \"No page at\" it, which returns, and the run would be credited with "
                                    f"reading a page it never saw")

            for canary in canaries:
                linted += 1
                n, page = canary.get("target"), canary.get("page")
                if not page:
                    if "canned" in modes:
                        fail(group, f"{label}: the canary for target {n} names no page — in a canned room it "
                                    f"would never be asked for")
                    continue
                holders = [p for p in pages if output_checks.same_url(p.get("url", ""), page)]
                if len(holders) != 1 or holders[0].get("target") != n:
                    fail(group, f"{label}: the canary for target {n} names {page}, which is not exactly one of "
                                f"this fixture's pages for target {n}")
                    continue
                body = output_checks.normalise_ws(output_checks.unify_dashes(
                    f"{holders[0].get('title', '')} {holders[0].get('text', '')}"))
                spellings = canary.get("text") or []
                spellings = [spellings] if isinstance(spellings, str) else spellings
                if not any(output_checks.canary_in(output_checks.normalise_ws(output_checks.unify_dashes(sp)), body)
                           for sp in spellings if str(sp).strip()):
                    fail(group, f"{label}: no spelling of the canary for target {n} is in its page {page}")

            # Where no correct run sends a call (zero_calls, or declined), a collision
            # cannot fail a correct n/a: any call there fails zero_calls first.
            no_call = bool(research.get("zero_calls")) or declined is True
            targets = research.get("targets") or []
            # The room aimed_at reads a search for the company by name in: the
            # request, with every declared user link read as a correct run reads it,
            # and every target (output_checks.identity_search).
            room = {"prompt": output_checks.request_text(case.get("prompt", ""), research,
                                                         research.get("user_links")),
                    "targets": targets}

            def aimed(query: str, target: dict, mode: str) -> bool:
                return output_checks.aimed_at(search_entry(query, research, mode), target, pages, mode, room)

            for target in targets:
                names = target.get("identity")
                if names is None:
                    continue
                linted += 1
                if not isinstance(names, list) or not names or not all(isinstance(x, str) and x.strip() for x in names):
                    fail(group, f"{label}: target {target.get('n')}'s identity is {names!r}, not a list of the "
                                f"company's name tokens")
                    continue
                for name in names:
                    if not output_checks.term_in(name, case.get("prompt", "")):
                        fail(group, f"{label}: identity name {name!r} of target {target.get('n')} is not in the "
                                    f"prompt — no search for the company would carry it")
                    if any(output_checks.term_in(name, " ".join(map(str, t.get("terms") or []))) for t in targets):
                        fail(group, f"{label}: identity name {name!r} is a target's term — every query carries the "
                                    f"name, so every call would be aimed there")
                if not any(any(output_checks.term_in(n, q) for n in names) for q in research.get("stray_samples") or []):
                    fail(group, f"{label}: target {target.get('n')} declares identity and no stray_samples query "
                                f"carries the name — nothing tests that a search by name for something else stays "
                                f"a stray")
            if sum(1 for t in targets if t.get("identity")) > 1:
                fail(group, f"{label}: more than one target declares identity — a search for the company by name "
                            f"is one target's sweep")
            # Queries a run might send that serve no declared target: each must stay a
            # stray in every mode, so it is shown as an off-target row.
            for query in research.get("stray_samples") or []:
                linted += 1
                for mode in modes:
                    hit = [t.get("n") for t in targets if aimed(query, t, mode)]
                    if hit:
                        fail(group, f"{label}: stray sample {query!r} is aimed at target(s) {hit} in a {mode} room — "
                                    f"a call outside every target would be charged to one")
            for target in targets:
                linted += 1
                n = target.get("n")
                own = target.get("on_target_samples")
                if not own:
                    fail(group, f"{label}: target {n} has no on_target_samples")
                    own = []
                for query in own:
                    for mode in modes:
                        if not aimed(query, target, mode):
                            fail(group, f"{label}: target {n}'s own sample {query!r} is aimed at no term of it in "
                                        f"a {mode} room — a correct call for it would be read as a call outside "
                                        f"every target")
                quiet = [m for m in modes if set(output_checks.accepted(target, m)) & {"n/a", "skipped"}]
                if not quiet:
                    continue
                hunts = target.get("hunt_samples")
                if not hunts:
                    fail(group, f"{label}: target {n} accepts n/a or skipped and has no hunt_samples")
                else:
                    for mode in quiet:
                        if not any(aimed(q, target, mode) for q in hunts):
                            fail(group, f"{label}: target {n}'s terms match none of its own hunt_samples in a "
                                        f"{mode} room — a hunt for it would pass as no call")
                if no_call:
                    continue
                for other in targets:
                    if other is target:
                        continue
                    for query in other.get("on_target_samples") or []:
                        for mode in quiet:
                            if not aimed(query, target, mode):
                                continue
                            if aimed(query, target, "denied"):
                                fail(group, f"{label}: target {n} accepts n/a or skipped, and its terms match target "
                                            f"{other.get('n')}'s sample {query!r} — a correct run would fail its n/a")
                            else:
                                fail(group, f"{label}: target {n} accepts n/a or skipped, and in a {mode} room target "
                                            f"{other.get('n')}'s sample {query!r} returns its page — a correct run "
                                            f"would fail its n/a")
                            break
    if linted == 0:
        fail(group, "no fixture field read — the check would pass vacuously")
    elif not any(f.startswith(f"[{group}]") for f in failures):
        ok(group, f"{linted} canaries, candidate_text entries, candidate_constraints, declined grounds, user links, "
                  f"user pages, research targets and page-naming checks agree with what the harness reads")


class SentenceRule:
    """A retired claim read one sentence at a time, so the words of the claim do
    not fail a sentence that states the rule that retired it. The claim is `pattern`,
    or `pattern` then `tail` later in the same sentence (within `reach` characters).
    A sentence fails on the claim unless it matches `unless` anywhere, or `negation`
    governs the claim: it stands right before the pattern, an article at most between
    ("not a hard gate: 3+ years …"), or before the tail with nothing between that
    ends a list item — no comma, semicolon, colon, parenthesis, dash, "and" or "or"
    ("terms, never years"). A negation anywhere else in the sentence negates
    something else ("hard gates, never bridged, are … years") and exempts nothing.
    Every pairing of the pattern with a later tail is read, so one negated pairing
    does not cover another. A sentence ends at a full stop, as the phrase patterns'
    own reach does."""

    def __init__(self, pattern: str, unless: str | None = None, tail: str | None = None,
                 negation: str | None = None, reach: int = 160):
        self.pattern = re.compile(pattern, re.I)
        self.unless = re.compile(unless, re.I) if unless else None
        self.tail = re.compile(tail, re.I) if tail else None
        self.reach = reach
        self.head_negated = re.compile(r"(?:" + negation + r")\s+(?:(?:an?|the|any)\s+)?$", re.I) if negation else None
        self.tail_negated = (re.compile(r"(?:" + negation + r")(?:(?!\b(?:and|or)\b)[^,;:()\[\]—–.]){0,40}$", re.I)
                             if negation else None)

    def search(self, text: str) -> re.Match | None:
        for sentence in re.split(r"(?<=\.)\s+|\n\s*\n", text):
            if self.unless and self.unless.search(sentence):
                continue
            for head in self.pattern.finditer(sentence):
                if self.head_negated and self.head_negated.search(sentence[:head.start()]):
                    continue
                if self.tail is None:
                    return head
                stop = sentence.find(".", head.end())
                window = sentence[:min(head.end() + self.reach, len(sentence) if stop < 0 else stop)]
                for tail in self.tail.finditer(window, head.end()):
                    if not (self.tail_negated and self.tail_negated.search(sentence[:tail.start()])):
                        return tail
        return None


# A word that negates what follows it. Not a bare "no", which a gate list carries as
# a term ("no sponsorship").
NEGATION = r"\b(?:not|never|except|rather than|instead of)\b|n't\b"

# Phrasings a rule change retired. Each was rewritten everywhere once and came back
# in the place nobody re-read, so its return fails the build. A SentenceRule fails
# only the retired claim, not a sentence that states the rule that retired it.
RETIRED = [
    (re.compile(r"\breturned something\b", re.I),
     "\"returned something\" is the retired accounting wording — an error returns something too; "
     "write \"returned a result\" (interaction-grammar.md §4)"),
    (re.compile(r"\bevery call (?:was|is) refused\b(?!\s+or\s+errored)", re.I),
     "\"every call was refused\" without \"or errored\" is the retired accounting wording; an errored call "
     "counts as refused (interaction-grammar.md §4)"),
    # Round 4's rule changes, each retired in every surface at once.
    (SentenceRule(r"\bonly when the (?:fixture's )?(?:whole )?(?:declared )?search budget was fully spent\b",
                  unless=r"\bL0\b|\bdeclin\w*"),
     "\"only when the search budget was fully spent\" as the sole ground is the retired accounting ground — the "
     "user choosing L0 or declining research is the other (interaction-grammar.md §4)"),
    (re.compile(r"\buser links? read\b[^.]{0,120}\brefused ones included\b", re.I),
     "user links counted \"refused ones included\" is the retired tally — `user links read N` counts reads that "
     "returned (interaction-grammar.md §4)"),
    (re.compile(r"\b(?:hard_gate_fail|failed) rows first,?\s+plainly\b", re.I),
     "failed gate rows \"plainly\" is the retired hard-gates wording — each carries a few of its Requirement's "
     "own words (risk-and-decision.md rule 4)"),
    (re.compile(r"\bmissing (?:hard-gates |Hard gates )?slot\b[^.]{0,40}\b(?:only )?when the map has gate rows\b", re.I),
     "a hard-gates slot required only with gate rows is the retired rule — it is in every snapshot "
     "(risk-and-decision.md rule 4)"),
    (SentenceRule(r"\bhard gates?\b", tail=r"\byears(?:/level)?\b", negation=NEGATION),
     "years listed as a hard gate is the retired gate list — a gate is a term, not experience "
     "(evidence-conventions.md §3, \"A gate is a term, not experience\")"),
    # Round 7's rule change: a set claim that names its rows is lawful when exact.
    (SentenceRule(r"\bany\b[^.]{0,80}\bquantifier\b", tail=r"\bfails?,?\s+even when (?:it is )?accurate\b",
                  unless=r"\bunnamed\b|\bnames? no row\b"),
     "a quantifier over the map failing \"even when it is accurate\" whatever it names is the retired count rule — "
     "a set claim that names its rows passes when exact, and only an unnamed one or a complement fails, in the "
     "snapshot (evidence-model.md, \"The row is the unit\")"),
    # Round 9's: "only" and "the one" are named-set words, and the words that fail
    # whatever they name are the complements.
    (re.compile(r"\bexclusive quantifiers?\b", re.I),
     "\"exclusive quantifier\" is the retired word for a list that failed \"only\" and \"the one\" whatever they "
     "named — they are named-set words, lawful in the snapshot when named and exact, and the words that fail there "
     "whatever they name are the complements (evidence-model.md, \"The row is the unit\")"),
    # Round 9's response-modes line: once after the last question covers all of them.
    (re.compile(r"\beach offers its response modes\b", re.I),
     "\"each offers its response modes\" is the retired placement — the response-modes line comes after each "
     "question or once after the last for all of them (job-underwriter SKILL.md, the closing order)"),
]
LABELS_DEFINED = re.compile(r"(?=.*\byes\b)(?=.*\bunavailable\b)(?=.*\bcalls?\b)", re.I | re.S)


def wording_surfaces() -> list[tuple[str, str]]:
    """(where, text) for every place a rule is stated or graded: each skill's SKILL.md,
    README and references, conventions/, evals/README.md, and every expectation,
    expected_output and clause, expanded the way the runner expands them."""
    out = []
    for path in sorted(CONVENTIONS.glob("*.md")) + [REPO / "evals" / "README.md"]:
        if path.exists():
            out.append((str(path.relative_to(REPO)), path.read_text(encoding="utf-8")))
    for skill in skills():
        for path in [skill / "SKILL.md", skill / "README.md"] + sorted((skill / "references").glob("*.md")):
            if path.exists() and path.name != "citations.md":
                out.append((str(path.relative_to(REPO)), path.read_text(encoding="utf-8")))
        raw_path = skill / "evals" / "evals.json"
        try:
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for name, clause in (raw.get("clauses") or {}).items() if isinstance(raw, dict) else []:
            out.append((f"{skill.name} evals.json clause {name}", str(clause)))
        for case in load_evals(raw_path) or []:
            for n, text in enumerate(case.get("expectations") or [], 1):
                out.append((f"{skill.name} eval {case.get('id')} #{n}", str(text)))
            out.append((f"{skill.name} eval {case.get('id')} expected_output", str(case.get("expected_output", ""))))
    return out


def check_wording() -> None:
    """Retired wordings stay retired, and two rewritten rules keep their new form.

    The errored-call rule changed in interaction-grammar.md §4, both skills and the
    harness, and eight grader expectations kept the old labels, so a grader and the
    deterministic check gave opposite verdicts on one run. mock-interview's L0 said
    "No network" after §4 made reading a link the user gave a provided document. And
    personas.md once pre-mapped a story per stem with no quote behind it. Each is a
    phrase, so each is checked as one (round 4 added the old accounting ground, the
    user-link tally that counted refused reads, "plainly" for failed gate rows, the
    slot required only with gate rows, and years in a hard-gate list; round 7 the
    count rule that failed a named set; the first and the last two are read in
    their sentence, so the rule that retired them, stated in the same words, passes): the retired phrasings anywhere a rule is stated or graded; any expectation that defines the yes/unavailable labels carries
    "returned a result" and "or errored"; no L0 definition says "no network"; and
    personas.md keeps its pointer to the quote-or-slot rule and pre-maps nothing
    unquoted.
    """
    group = "wording"
    read = 0
    for where, raw in wording_surfaces():
        text = re.sub(r"\s+", " ", raw.replace("`", ""))
        read += 1
        for pattern, why in RETIRED:
            hit = pattern.search(text)
            if hit:
                fail(group, f"{where}: {why}")
        if (" eval " in where or "clause" in where) and LABELS_DEFINED.match(text) \
                and re.search(r"\byes if\b|\bis yes\b", text, re.I):
            for needed in ("returned a result", "or errored"):
                if needed not in text:
                    fail(group, f"{where}: defines the yes/unavailable labels without \"{needed}\" "
                                f"(interaction-grammar.md §4)")
        if where.endswith(".md"):
            heading = ""
            for block in re.split(r"\n[ \t]*\n|\n(?=[ \t]*(?:[-*+] |\d+\. |#))", raw):
                head = re.match(r"[ \t]*#{1,6}\s+(.*)", block)
                if head:
                    heading = head.group(1)
                if re.search(r"\bno network\b", block, re.I) and re.search(r"\bL0\b", block + " " + heading):
                    fail(group, f"{where}: an L0 definition says \"no network\" — L0 reads a link the user gave "
                                f"as a provided document (interaction-grammar.md §4)")
    personas = SKILLS_DIR / "mock-interview" / "references" / "personas.md"
    if personas.exists():
        text = personas.read_text(encoding="utf-8")
        for block in re.split(r"\n[ \t]*\n|\n(?=[ \t]*[-*+] )", text):
            if (re.search(r"pre-map", block, re.I) or re.search(r"\bevery\b.*\bstory ends with\b", block, re.I | re.S)) \
                    and "quoted" not in block.lower():
                fail(group, f"mock-interview/references/personas.md: \"{' '.join(block.split())[:70]}\" maps a "
                            f"story with no quoted sentence behind it (question-rubric.md's quote-or-slot rule)")
        section = re.search(r"^## The seven personas\s*$(.*?)(?=^###? )", text, re.M | re.S)
        if not section or not any("quote-or-slot" in line and "question-rubric.md" in line
                                  for line in section.group(1).splitlines()):
            fail(group, "mock-interview/references/personas.md: no line under \"## The seven personas\" points its "
                        "counter-strategies at the quote-or-slot rule in question-rubric.md")
    if read == 0:
        fail(group, "no surface read — the check would pass vacuously")
    elif not any(f.startswith(f"[{group}]") for f in failures):
        ok(group, f"{read} surfaces carry no retired wording, and the rewritten rules keep their form")


def check_ledger() -> None:
    """The Tracked-work ledger is the project's memory; it must not contradict itself.

    It did. Five entries had accumulated in it: three exact duplicates, plus a
    closed item sitting beside its replacement and a superseded one contradicting
    its successor — the ledger asserting both that mock-interview had no spec and
    that its spec was written. Index-based edits had been slicing at the wrong
    boundaries and leaving copies behind, silently, for several sessions.

    A duplicated title is mechanically detectable, which is most of the damage.
    The rest is a review question, so the failure message says what to look for.
    """
    group = "ledger"
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    section = re.search(r"^## Tracked work\s*$(.*?)(?=^## |\Z)", readme,
                        re.MULTILINE | re.DOTALL)
    if not section:
        fail(group, "README.md has no '## Tracked work' section")
        return

    titles = re.findall(r"^- \*\*(.+?)\*\*", section.group(1), re.MULTILINE)
    if not titles:
        fail(group, "the Tracked-work ledger has no entries — the check would pass vacuously")
        return

    seen, duplicated = set(), []
    for title in titles:
        if title in seen:
            duplicated.append(title)
        seen.add(title)
    if duplicated:
        fail(group, "duplicate ledger entr(ies): "
                    + "; ".join(f"'{t[:60]}'" for t in dict.fromkeys(duplicated)))
        return

    # A weaker signal for the harder half: two entries opening on the same subject
    # are usually one item and its stale predecessor.
    subjects = {}
    for title in titles:
        subject = re.split(r"\s+[—-]\s+", title, maxsplit=1)[0].strip().lower()
        subjects.setdefault(subject, []).append(title)
    collisions = {s: ts for s, ts in subjects.items() if len(ts) > 1}
    if collisions:
        detail = "; ".join(f"'{s}' appears {len(ts)} times" for s, ts in collisions.items())
        fail(group, f"ledger entries share a subject — check whether one supersedes "
                    f"the other rather than sitting beside it: {detail}")
    else:
        ok(group, f"ledger: {len(titles)} entries, no duplicate or colliding subjects")


WATCH_OUT_HEADING = re.compile(r"^## Watch-outs\b[^\n]*$(.*?)(?=^## |\Z)", re.M | re.S)
STANDING_RULE = re.compile(r"^## When an issue survives two iterations\s*$(.*?)(?=^## |\Z)", re.M | re.S)
RULE_7 = re.compile(r"^## 7\. [^\n]*$(.*?)(?=^## |\Z)", re.M | re.S)
WATCH_OUT_WORDS = 40
# The name the slot never takes, as a label or as the slot's name.
WARNING_NAME = re.compile(r"\*\*warnings?:?\*\*|^[\s>*_-]*warnings?\s*:|\bwarning (?:line|sentence|slot)s?\b",
                          re.I | re.M)


def check_watch_outs() -> None:
    """Each skill declares one watch-out sentence, and every copy of it is exact.

    output-discipline.md rule 7 defines the slot: the last line of every delivered
    output, `**Watch-out:** ` and the skill's `watch_out` sentence, copied exactly.
    The sentence is stated once, in SKILL.md, and copied where it must be read
    whole — the root README's table, each fixture's closing expectation (a grader
    sees the fixture, not SKILL.md), a worked example's last line — and a copy
    edited in one place and not another is the drift this suite keeps finding. So:
    the convention defines the slot and names its parameter; each sentence is one
    sentence of at most WATCH_OUT_WORDS words, with no brackets, pipe or code span,
    and never named a warning; each closing_order ends with `watch-out`; every
    labelled line in a skill's own SKILL.md, README and references is the declared
    line; every fixture carries the declared line in an expectation, and any
    expectation that labels one carries it exactly; the README's table has one row
    per skill quoting its sentence exactly; CONTRIBUTING.md keeps the standing rule
    the README links to; and nothing that states or grades a rule labels the slot
    a warning. What it does not read: whether a sentence is plain, or names what
    the measured defect is, or the README table's "Why it's there" column — that
    is review's. A known limit: nor does it read the prose that states the closing
    order ("nothing follows the questions", "the questions close the message"), so
    such a sentence edited back in passes; see CONTRIBUTING.md.
    """
    group = "watch-out"
    checked = 0
    convention = (CONVENTIONS / "output-discipline.md").read_text(encoding="utf-8")
    if "**Parameter: `watch_out`**" not in convention or output_checks.WATCH_OUT_LABEL not in convention:
        fail(group, "conventions/output-discipline.md does not define the watch-out slot — its line "
                    f"({output_checks.WATCH_OUT_LABEL} …) and its `watch_out` parameter")
    rule = RULE_7.search(convention)
    if rule and re.search(r"\bwarning", rule.group(1), re.I):
        fail(group, "conventions/output-discipline.md rule 7 uses \"warning\" — the slot is a watch-out, by no other name")
    declared: dict[str, str] = {}
    for skill in skills():
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        sentence = output_checks.declared_watch_out(text)
        if sentence is None:
            fail(group, f"{skill.name}: SKILL.md declares no watch_out sentence under '## Output discipline'")
            continue
        declared[skill.name] = sentence
        checked += 1
        words = len(sentence.split())
        inner = re.findall(r"[.!?](?=[\s\"”']+[A-Z])", sentence)
        if not re.search(r"[.!?][\"”']?$", sentence) or inner:
            fail(group, f"{skill.name}: watch_out is not one sentence: {sentence[:90]!r}")
        if words > WATCH_OUT_WORDS:
            fail(group, f"{skill.name}: watch_out runs to {words} words, over {WATCH_OUT_WORDS} — one crisp sentence")
        if re.search(r"[\[\]|`]", sentence):
            fail(group, f"{skill.name}: watch_out holds a bracket, pipe or code span — plain words only, and a pipe "
                        f"breaks the README's table")
        if re.search(r"\bwarning", sentence, re.I):
            fail(group, f"{skill.name}: watch_out calls itself a warning")
        section = output_checks.OUTPUT_DISCIPLINE.search(text)
        order = re.search(r"^\s*closing_order\s*:\s*(.+?)\s*$", section.group(1) if section else "", re.M)
        if not order or order.group(1).split(",")[-1].strip() != "watch-out":
            fail(group, f"{skill.name}: closing_order does not end with watch-out "
                        f"({order.group(1) if order else 'undeclared'!s})")
        line = output_checks.watch_out_line(sentence)
        surfaces = [("SKILL.md", text)]
        for path in [skill / "README.md"] + sorted((skill / "references").glob("*.md")):
            if path.exists():
                body = path.read_text(encoding="utf-8")
                if not SYNCED_HEADER.match(body):
                    surfaces.append((str(path.relative_to(skill)), body))
        for where, body in surfaces:
            for n, raw in enumerate(body.splitlines(), 1):
                if output_checks.WATCH_OUT_LABELLED.match(raw):
                    checked += 1
                    if " ".join(raw.split()) != line:
                        fail(group, f"{skill.name} {where}:{n}: a watch-out line that is not the declared one: "
                                    f"{raw.strip()[:90]!r}")
        for case in load_evals(skill / "evals" / "evals.json") or []:
            expectations = [e for e in case.get("expectations", []) if isinstance(e, str)]
            checked += 1
            if not any(line in e for e in expectations):
                fail(group, f"{skill.name} eval {case.get('id')}: no expectation carries the watch-out line exactly — "
                            f"every fixture's turn delivers output, so every fixture grades the line")
            for n, e in enumerate(expectations, 1):
                if output_checks.WATCH_OUT_LABEL in e and line not in e:
                    fail(group, f"{skill.name} eval {case.get('id')} #{n}: labels a watch-out line that is not the "
                                f"declared sentence")

    readme = (REPO / "README.md").read_text(encoding="utf-8")
    section = WATCH_OUT_HEADING.search(readme)
    if not section:
        fail(group, "README.md has no '## Watch-outs' section")
    else:
        body = section.group(1)
        if re.search(r"\bwarning", body, re.I):
            fail(group, "README.md's watch-out section uses \"warning\" — the slot is a watch-out, by no other name")
        tables = output_checks.md_tables(body)
        rows: dict[str, list[str]] = {}
        for table in tables[:1]:
            names = output_checks.header_names(table)
            if "skill" not in names or not any("watch" in h for h in names):
                fail(group, f"README.md's watch-out table has no Skill and Watch-out columns: {names}")
                continue
            s_col, w_col = names.index("skill"), next(i for i, h in enumerate(names) if "watch" in h)
            for cells in table["rows"]:
                name = re.sub(r"[`*\[\]]|\(.*?\)", "", cells[s_col]).strip() if s_col < len(cells) else ""
                rows.setdefault(name, []).append(cells[w_col].strip() if w_col < len(cells) else "")
        if not tables:
            fail(group, "README.md's watch-out section has no table")
        for name, cells in rows.items():
            if name not in {s.name for s in skills()}:
                fail(group, f"README.md's watch-out table names {name!r}, which is not a skill")
        for name, sentence in declared.items():
            checked += 1
            cells = rows.get(name, [])
            if len(cells) != 1:
                fail(group, f"README.md's watch-out table has {len(cells)} rows for {name}, not one")
            elif " ".join(cells[0].split()) != " ".join(sentence.split()):
                fail(group, f"README.md's watch-out table quotes {name}'s sentence as {cells[0][:90]!r}, not its "
                            f"SKILL.md watch_out — change the parameter and the copy together")
    contributing = (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8")
    standing = STANDING_RULE.search(contributing)
    if not standing:
        fail(group, "CONTRIBUTING.md has no '## When an issue survives two iterations' section — the standing rule "
                    "the README links to")
    elif re.search(r"\bwarning", standing.group(1), re.I):
        fail(group, "CONTRIBUTING.md's standing rule uses \"warning\" — the slot is a watch-out, by no other name")
    for where, raw in wording_surfaces():
        hit = WARNING_NAME.search(raw)
        if hit:
            fail(group, f"{where}: {hit.group(0).strip()!r} names a line a warning — the slot is a watch-out")
    if checked and not any(f.startswith(f"[{group}]") for f in failures):
        ok(group, f"{len(declared)} watch-out sentences, one sentence each, and {checked} copies and fixtures "
                  f"agree with them")
    elif not checked:
        fail(group, "no watch-out sentence read — the check would pass vacuously")


# --- Anthropic's skill-authoring guidance ------------------------------------
# The limits the guidance sets for what a skill ships, as numbers this file can
# hold. The SKILL.md body is estimated at four characters a token, the estimate the
# owner set; the guidance recommends a body under about 5,000 tokens and requires
# under 500 lines.
MAX_BODY_LINES = 500
MAX_BODY_TOKENS = 5000
CHARS_PER_TOKEN = 4
TOC_OVER_LINES = 100
CONTENTS = "## Contents"
# A third-person verb ends in "s" ("Decides", "Generates", "Tailors", "Assesses");
# a bare imperative does not ("Decide", "Generate", "Tailor", "Use"). A verb whose
# bare form already ends in "ss" ("Assess", "Process") is a bare imperative when it
# stops there, so a first word ending in "ss" fails too.
THIRD_PERSON = re.compile(r"^[A-Za-z]+(?<!s)s\b|^[A-Za-z]+ses\b")


def skill_body(text: str) -> str:
    """SKILL.md without its frontmatter: what loads when the skill triggers."""
    match = re.match(r"^---\n.*?\n---\n", text, re.DOTALL)
    return text[match.end():] if match else text


def contents_problem(text: str) -> str | None:
    """Why a reference file does not start with a table of contents, or None.

    Starts with means: after the synced-from header, if any, and the file's H1, the
    first thing is a '## Contents' heading, then a list of at least one item.
    """
    body = text[SYNCED_HEADER.match(text).end():] if SYNCED_HEADER.match(text) else text
    lines = body.splitlines()
    try:
        h1 = next(i for i, line in enumerate(lines) if line.startswith("# "))
    except StopIteration:
        return "has no H1 for a contents list to sit under"
    rest = [line for line in lines[h1 + 1:] if line.strip()]
    if not rest or rest[0].strip() != CONTENTS:
        return f"does not open with '{CONTENTS}' directly under its H1"
    after = lines[lines.index(rest[0], h1 + 1) + 1:]
    while after and not after[0].strip():
        after = after[1:]
    if not after or not after[0].lstrip().startswith("- "):
        return f"has a '{CONTENTS}' heading with no list under it"
    return None


def check_guidance() -> None:
    """What Anthropic's skill-authoring guidance asks of a shipped skill, held here.

    Each limit was met by hand once and drifted: two SKILL.md bodies passed 5,000
    tokens one rationale paragraph at a time, every description opened with a bare
    imperative, and 22 reference files over 100 lines had no contents list for a
    reader who previews the top of a file. What this reads: a contents list at the
    top of every reference file over TOC_OVER_LINES lines, as shipped (a mirror's
    header counted, since a mirror ships with it); each SKILL.md body under
    MAX_BODY_LINES lines and MAX_BODY_TOKENS estimated tokens; each description
    opening in the third person, read from its first word alone (THIRD_PERSON);
    and every file in references/ linked from SKILL.md by the path that resolves
    in the installed skill, `references/<name>`. The frontmatter keys, the
    description's length and its angle brackets are the frontmatter group's. What
    it does not read: whether a contents list matches the file's headings, whether
    the rest of a description is in the third person, and whether a link sits at
    the step that needs the file.
    """
    group = "guidance"
    for skill in skills():
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        body = skill_body(text)
        lines = len(body.splitlines())
        tokens = len(body) // CHARS_PER_TOKEN
        if lines >= MAX_BODY_LINES:
            fail(group, f"{skill.name}: SKILL.md body is {lines} lines, at or over the {MAX_BODY_LINES}-line limit")
        if tokens >= MAX_BODY_TOKENS:
            fail(group, f"{skill.name}: SKILL.md body is about {tokens} tokens ({len(body)} chars / {CHARS_PER_TOKEN}), "
                        f"over the {MAX_BODY_TOKENS}-token estimate — move rationale to a reference file")
        if lines < MAX_BODY_LINES and tokens < MAX_BODY_TOKENS:
            ok(group, f"{skill.name}: SKILL.md body is {lines} lines and about {tokens} tokens")

        fm = parse_frontmatter(text) or {}
        desc = fm.get("description", "")
        if desc and not THIRD_PERSON.match(desc):
            first = desc.split()[0]
            fail(group, f"{skill.name}: description opens with '{first}', a bare imperative — write it in the third "
                        f"person ('Generates…', not 'Generate…')")
        elif desc:
            ok(group, f"{skill.name}: description opens in the third person ('{desc.split()[0]}')")

        for ref in sorted((skill / "references").glob("*.md")):
            if f"references/{ref.name}" not in body:
                fail(group, f"{skill.name}: SKILL.md never links references/{ref.name} by that path — a reference "
                            f"is linked directly from SKILL.md, one level deep")
            ref_text = ref.read_text(encoding="utf-8")
            n = len(ref_text.splitlines())
            if n > TOC_OVER_LINES:
                problem = contents_problem(ref_text)
                if problem:
                    fail(group, f"{skill.name}: references/{ref.name} is {n} lines and {problem} — a reference "
                                f"file over {TOC_OVER_LINES} lines starts with a table of contents")
                else:
                    ok(group, f"{skill.name}: references/{ref.name} ({n} lines) opens with its contents")


GROUPS = {
    "frontmatter": check_frontmatter,
    "columns": check_columns,
    "citations": check_citations,
    "sections": check_sections,
    "counts": check_counts,
    "readmes": check_readmes,
    "fit-ledger": check_fit_ledger,
    "answer-keys": check_answer_keys,
    "fixtures": check_fixtures,
    "wording": check_wording,
    "ledger": check_ledger,
    "parameters": check_parameters,
    "package": check_package,
    "mirrors": check_mirrors,
    "evals": check_evals,
    "triggers": check_triggers,
    "watch-out": check_watch_outs,
    "guidance": check_guidance,
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
