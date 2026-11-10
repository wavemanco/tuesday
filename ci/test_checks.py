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
COPIED = ["skills", "dist", "conventions", "ci", "evals", "docs", ".claude-plugin"]
# Files, not directories: the ledger lives in README.md and the ledger check reads it.
# docs/ and CONTRIBUTING.md joined when the citations check did: it reads both, and a
# staged repo without them would let every citation in a spec pass by being unseen.
COPIED_FILES = ["README.md", "CONTRIBUTING.md"]


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


def run(root: Path, group: str | None) -> tuple[int, str]:
    """Run one group, or every group when group is None."""
    command = [sys.executable, "ci/check_skills.py"] + (["--only", group] if group else [])
    proc = subprocess.run(command, cwd=root, capture_output=True, text=True)
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


def break_routing_variant_edited(root: Path) -> str:
    """Hand-edit a generated variant's message: the diagnostic would measure a
    prompt no committed script produced."""
    path = root / "evals/routing-arm-b.json"
    data = json.loads(path.read_text())
    data["cases"][0]["prompt"] += " Thanks!"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return "regenerate it, never edit it"


def break_routing_suite_not_regenerated(root: Path) -> str:
    """Change an attachment in the suite and leave the variant files as they were:
    arm B would paste the old document beside the new file."""
    path = root / "evals/suite-routing.json"
    data = json.loads(path.read_text())
    case = next(c for c in data["cases"] if c.get("attachments"))
    name = next(iter(case["attachments"]))
    case["attachments"][name] += "\nRemote-first."
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return "is not what evals/routing_variants.py generates"


def break_routing_variant_id_collides(root: Path) -> str:
    """Give a variant a suite case's id: `--case` and the results would conflate the two."""
    path = root / "evals/routing-arm-c.json"
    data = json.loads(path.read_text())
    data["cases"][0]["id"] = data["cases"][0]["derived_from"]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return "collides with a suite case's"


def break_routing_either_without_siblings(root: Path) -> str:
    """Drop the skills a spanning case spans: its verdict would fall back to a guess,
    and case 21 scored a correct resume-tailor fire as a miss that way."""
    path = root / "evals/suite-routing.json"
    data = json.loads(path.read_text())
    case = next(c for c in data["cases"] if c.get("expected") == "either")
    case.pop("siblings", None)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return "must list the two or more installed skills it spans"


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


def break_command_pointer_missing(root: Path) -> str:
    """Delete the line pointing to the slash-command rule from one SKILL.md."""
    path = root / "skills/mock-interview/SKILL.md"
    lines = path.read_text().split("\n")
    path.write_text("\n".join(line for line in lines if "`/mock-interview`" not in line))
    return "mock-interview: SKILL.md has 0 lines above its first heading"


def break_command_pointer_buried(root: Path) -> str:
    """Move the pointer below the body's first heading, where a command reads it late."""
    path = root / "skills/resume-tailor/SKILL.md"
    lines = path.read_text().split("\n")
    pointer = next(line for line in lines if "`/resume-tailor`" in line)
    lines.remove(pointer)
    at = next(i for i, line in enumerate(lines) if line.startswith("## Workflow"))
    lines[at + 1:at + 1] = ["", pointer]
    path.write_text("\n".join(lines))
    return "resume-tailor: SKILL.md has 0 lines above its first heading"


def break_command_pointer_unanchored(root: Path) -> str:
    """Point the line at the wrong section of the grammar, where the rule is not."""
    path = root / "skills/job-underwriter/SKILL.md"
    lines = path.read_text().split("\n")
    at = next(i for i, line in enumerate(lines) if "`/job-underwriter`" in line)
    lines[at] = lines[at].replace("`references/interaction-grammar.md` §6", "`references/interaction-grammar.md` §7")
    path.write_text("\n".join(lines))
    return "job-underwriter: SKILL.md has 0 lines above its first heading"


def break_trigger_hub_row_missing(root: Path) -> str:
    """Drop Tuesday's row from the grammar's trigger-hygiene table: it is read like a module's."""
    path = root / "conventions/interaction-grammar.md"
    text = path.read_text()
    path.write_text(re.sub(r"^\| `tuesday` \|[^\n]*\n", "", text, count=1, flags=re.MULTILINE))
    return "tuesday: no row in the trigger-hygiene table"


def break_trigger_hub_boundary_word(root: Path) -> str:
    """A word of Tuesday's row missing from its description, the rest of the boundary intact."""
    path = root / "skills/tuesday/SKILL.md"
    text = path.read_text()
    line = re.search(r"^description: .*$", text, re.MULTILINE).group(0)
    path.write_text(text.replace(line, line.replace("proofreading, ", ""), 1))
    return "tuesday: description misses its reserved boundary"


def break_command_rule_missing(root: Path) -> str:
    """Drop the slash-command rule's paragraph from the grammar's §6."""
    path = root / "conventions/interaction-grammar.md"
    text = path.read_text()
    path.write_text(re.sub(r"^\*\*A skill started by its own slash command[^\n]*\n", "", text, flags=re.MULTILINE))
    return "states the slash-command rule under 0 bold labels"


def break_qualifier_column_missing(root: Path) -> str:
    """Delete the column a skill's qualifier_fields points at.

    The bug this reproduces ran for three skill versions: `reasoning` was in the
    row spec and in the JSON envelope, the compound-cell rule said to put the
    qualifier there, and the rendered table had no such column. `none/low` went
    into the Confidence cell beside it.
    """
    path = root / "skills/job-underwriter/references/dossier-worked-report.md"
    text = path.read_text()
    mutated = text.replace("| Confidence | Gap | Reasoning | Provenance | Next action |",
                           "| Confidence | Gap | Provenance | Next action |", 1)
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


def break_provenance_column_missing(root: Path) -> str:
    """Strip the Provenance column from a section declared to carry one.

    This is the register, exactly as it stood: the project ledger asserted for
    weeks that this table had a Provenance cell, it never had, and it took a
    grader reading generated output to notice.
    """
    path = root / "skills/job-underwriter/references/dossier-worked-report.md"
    text = path.read_text()
    mutated = text.replace("| Hypothesis | Provenance | Verification question |",
                           "| Hypothesis | Verification question |", 1)
    if mutated == text:
        raise SystemExit("break_provenance_column_missing found no register header — it has gone stale")
    path.write_text(mutated)
    return "has no Provenance column"


def break_provenance_section_unknown(root: Path) -> str:
    """Declare a provenance section that is not a section at all."""
    path = root / "skills/resume-tailor/SKILL.md"
    text = path.read_text()
    mutated = text.replace("provenance_sections: The coverage map, Recovery per gap, A worked ledger",
                           "provenance_sections: The coverage map, The parse report, A worked ledger", 1)
    if mutated == text:
        raise SystemExit("break_provenance_section_unknown found nothing to rename — it has gone stale")
    path.write_text(mutated)
    return "not a '## ' section with a table"


def break_qualifier_without_label(root: Path) -> str:
    """A free-text column left standing with no Provenance cell beside it.

    Made twice in one session. The register's Hypothesis column shipped without a
    label and was fixed after graders found it; the evidence map's Reasoning
    column shipped without one in the same commit and was not, and six graders in
    the next run-set pointed straight at it.
    """
    path = root / "skills/job-underwriter/references/dossier-worked-report.md"
    text = path.read_text()
    mutated = text.replace("| Gap | Reasoning | Provenance | Next action |",
                           "| Gap | Reasoning | Next action |", 1)
    if mutated == text:
        raise SystemExit("break_qualifier_without_label found no evidence-map header — it has gone stale")
    path.write_text(mutated)
    return "no Provenance cell"


def break_unmirrored_canonical(root: Path) -> str:
    """Delete a mirror of a canonical file that declares skills mirror it.

    The gap this reproduces stood for four months. interaction-grammar.md has
    opened with "skills mirror in references/" since it was written, and no skill
    mirrored it. The existing check validates every mirror that exists and is
    silent about one that should — so a canonical file declaring its own
    requirement had nobody verifying the declaration.
    """
    path = root / "skills/resume-tailor/references/interaction-grammar.md"
    if not path.exists():
        raise SystemExit("break_unmirrored_canonical found no mirror to delete — it has gone stale")
    path.unlink()
    return "declares that skills mirror it"



def break_dangling_reference(root: Path) -> str:
    """Delete a mirror that another mirror points at.

    Mirroring interaction-grammar.md introduced six of these in one commit, all
    to dossier-schema.md — in the change that fixed the identical defect one
    level up. Skills are dependency-free, so "see `x.md`" naming a file the
    folder does not carry is a pointer the reader cannot follow.
    """
    path = root / "skills/mock-interview/references/dossier-schema.md"
    if not path.exists():
        raise SystemExit("break_dangling_reference found no dossier-schema mirror — it has gone stale")
    path.unlink()
    return "point at a canonical file this skill does not carry"


def break_skill_local_reference(root: Path) -> str:
    """Name a skill-local file from canonical text mirrored everywhere.

    The narrower gate could not see this: `evidence-model.md` belongs to
    job-underwriter alone, so canonical text naming it put a pointer into
    nothing inside mock-interview's and resume-tailor's mirrors. Committed three
    times in the change that fixed the same class one level up.
    """
    path = root / "skills/mock-interview/references/evidence-conventions.md"
    text = path.read_text()
    mutated = text.replace("The skill that owns an evidence map requires",
                           "`evidence-model.md` requires", 1)
    if mutated == text:
        raise SystemExit("break_skill_local_reference found no reworded pointer — it has gone stale")
    path.write_text(mutated)
    return "point at a canonical file this skill does not carry"


def break_unreferenced_file(root: Path) -> str:
    """Carry a reference file that nothing names.

    Two canonical mirrors were added to all three skills and listed in none of
    their SKILL.md reference sections — present, byte-perfect, and unreachable.
    The forward check (a pointer to a missing file) could not see it; this is the
    same defect in the other direction.
    """
    import re
    path = root / "skills/job-underwriter/SKILL.md"
    text = path.read_text()
    mutated = re.sub(r"^- `references/interaction-grammar\.md`.*\n", "", text, count=1, flags=re.M)
    if mutated == text:
        raise SystemExit("break_unreferenced_file found no listing to remove — it has gone stale")
    mutated = mutated.replace("`references/interaction-grammar.md`", "the interaction grammar")
    if "interaction-grammar.md" in mutated:
        raise SystemExit("break_unreferenced_file left a mention behind — it has gone stale")
    path.write_text(mutated)
    return "not named in SKILL.md"


def break_paraphrase_as_quote(root: Path) -> str:
    """Restore the exact defect: a compression inside quotation marks, cited.

    The authors wrote "This shift may have important implications, including
    favoring established workers". The conventions shipped "may favour
    established workers" in quotation marks, and a correction certified it
    verbatim. citations.md holds the real sentence, so the paraphrase fails.
    """
    path = root / "conventions/evidence-conventions.md"
    text = path.read_text()
    mutated = text.replace(
        '"This shift may have important implications, including favoring established\nworkers at the expense of newcomers trying to enter the market." (cite C3)',
        '"may favour established workers at the expense of newcomers trying to enter\nthe market." (cite C3)', 1)
    if mutated == text:
        raise SystemExit("break_paraphrase_as_quote found no C3 quotation — it has gone stale")
    path.write_text(mutated)
    return "Verbatim does not contain it"


def break_uncited_source_quote(root: Path) -> str:
    """Quote a source verbatim and drop its markers.

    Both markers go: a marker covers every quotation earlier in its sentence, so
    dropping only the first leaves the second citing both, correctly.
    """
    path = root / "skills/resume-tailor/references/machine-readers.md"
    text = path.read_text()
    mutated = text.replace('bypass AI filters" (cite C17), and of the rest, "52% say they are considering it"\n(cite C17).',
                           'bypass AI filters", and of the rest, "52% say they are considering it".', 1)
    if mutated == text:
        raise SystemExit("break_uncited_source_quote found no C17 quotation — it has gone stale")
    path.write_text(mutated)
    return "verbatim without (cite"


def break_dangling_cite(root: Path) -> str:
    """Cite an entry that does not exist."""
    path = root / "docs/cover-letter-spec-v0.md"
    text = path.read_text()
    mutated = text.replace("(cite C5)", "(cite C99)", 1)
    if mutated == text:
        raise SystemExit("break_dangling_cite found no C5 marker — it has gone stale")
    path.write_text(mutated)
    return "names no entry"


def break_unused_citation(root: Path) -> str:
    """Leave an entry that no claim rests on."""
    path = root / "conventions/citations.md"
    path.write_text(path.read_text() + """
## C99

- **Claim:** An orphan.
- **Verbatim:** "a sentence nothing cites"
- **Source:** nowhere — https://example.invalid/
- **Retrieved:** 2026-09-26
""")
    return "cited nowhere"


def break_stale_count(root: Path) -> str:
    """Restore "Two overrides" above three bullets — the first of two real cases."""
    path = root / "conventions/evidence-conventions.md"
    text = path.read_text()
    mutated = text.replace("Three overrides that beat every label:", "Two overrides that beat every label:", 1)
    if mutated == text:
        raise SystemExit("break_stale_count found no overrides lead-in — it has gone stale")
    path.write_text(mutated)
    return "says 2, has 3 items"


def break_list_outgrows_count(root: Path) -> str:
    """Put the procedure back inside the disciplines list — the second real case."""
    path = root / "conventions/reframing-audit.md"
    text = path.read_text()
    anchor = "- **Drift in the flattering direction is the one to hunt"
    i = text.find(anchor)
    if i < 0:
        raise SystemExit("break_list_outgrows_count found no disciplines list — it has gone stale")
    end = text.index("\n", i)
    mutated = text[:end + 1] + "- **Cut or ask.** A clause that cannot be traced is cut or asked about.\n" + text[end + 1:]
    path.write_text(mutated)
    return "says 5, has 6 items"


def break_dangling_section(root: Path) -> str:
    """Point a qualified reference at a section the file does not have."""
    path = root / "skills/resume-tailor/SKILL.md"
    text = path.read_text()
    mutated = text.replace("`references/interaction-grammar.md` §4", "`references/interaction-grammar.md` §19", 1)
    if mutated == text:
        raise SystemExit("break_dangling_section found no §4 reference — it has gone stale")
    path.write_text(mutated)
    return "has no section 19"


def break_ambiguous_section(root: Path) -> str:
    """A bare §N meaning another file, where this file has no such section."""
    path = root / "skills/mock-interview/references/question-rubric.md"
    text = path.read_text()
    mutated = text.replace("Confidence (`evidence-conventions.md` §2)", "Confidence (§2 of the mirror)", 1)
    if mutated == text:
        raise SystemExit("break_ambiguous_section found no qualified §2 — it has gone stale")
    path.write_text(mutated)
    return "bare §2"



def swap_once(root: Path, rel: str, old: str, new: str, name: str) -> None:
    path = root / rel
    text = path.read_text()
    if text.count(old) != 1:
        raise SystemExit(f"{name} expected one {old!r} in {rel} — it has gone stale")
    path.write_text(text.replace(old, new))


# The next four each passed the first sections check. The citing file has a
# section with that number, so a bare §N resolved — to the wrong file.

def break_qualified_by_word(root: Path) -> str:
    """ "(grammar §8)" in the build brief, which has an §8 of its own."""
    swap_once(root, "docs/job-underwriter-build-brief.md", "(`interaction-grammar.md` §8)",
              "(grammar §8)", "break_qualified_by_word")
    return 'bare §8 after "grammar"'


def break_qualified_by_possessive(root: Path) -> str:
    """ "resume-tailor's §8" in the cover-letter spec, which has an §8 of its own."""
    swap_once(root, "docs/cover-letter-spec-v0.md", "`resume-tailor-spec-v0.md` §8",
              "resume-tailor's §8", "break_qualified_by_possessive")
    return 'bare §8 after "resume-tailor"'


def break_block_names_file(root: Path) -> str:
    """A bare §2 in a list item that names `evidence-conventions.md` two words earlier."""
    swap_once(root, "docs/job-underwriter-build-brief.md", "confidence bands (`evidence-conventions.md` §2)",
              "confidence bands (§2)", "break_block_names_file")
    return "bare §2 in a block naming `evidence-conventions.md`"


def break_label_names_section(root: Path) -> str:
    """ "**Truthfulness core** (§6)" — another file's §6 title, not this file's."""
    swap_once(root, "docs/job-underwriter-build-brief.md", "**Truthfulness core** (`evidence-conventions.md` §6)",
              "**Truthfulness core** (§6)", "break_label_names_section")
    return 'bare §6 labelled "truthfulness core"'



def break_qualified_after(root: Path) -> str:
    """ "§8 in the resume-tailor spec" — the qualifier after the number, not before."""
    swap_once(root, "docs/cover-letter-spec-v0.md", "`resume-tailor-spec-v0.md` §8",
              "§8 in the resume-tailor spec", "break_qualified_after")
    return 'bare §8 after "resume-tailor"'


def break_block_names_base(root: Path) -> str:
    """A block naming interaction-grammar without its `.md`."""
    swap_once(root, "docs/job-underwriter-build-brief.md", "(`interaction-grammar.md` §5)",
              "(§5, interaction-grammar)", "break_block_names_base")
    return "bare §5 in a block naming `interaction-grammar.md`"



# Each of the next eight passed the first counts check, which read one shape:
# count word first, colon on the same line, bullets below.

def break_table_count(root: Path) -> str:
    """ "six axes" over a six-row table, made five."""
    swap_once(root, "conventions/reframing-audit.md", "on six axes:", "on five axes:", "break_table_count")
    return "says 5, has 6 table rows"


def break_heading_count(root: Path) -> str:
    """A heading counting the bullets beneath it."""
    swap_once(root, "skills/resume-tailor/references/dossier-consumption.md", "## Five rules for consumption",
              "## Four rules for consumption", "break_heading_count")
    return "says 4, has 5 items"


def break_wrapped_count(root: Path) -> str:
    """A lead-in hard-wrapped before its colon."""
    swap_once(root, "skills/job-underwriter/references/evidence-model.md", "Three readings this skill adds on top",
              "Two readings this skill adds on top", "break_wrapped_count")
    return "says 2, has 3 items"


def break_sections_count(root: Path) -> str:
    """ "Seven rules" ahead of seven numbered sections."""
    swap_once(root, "conventions/output-discipline.md", "Seven rules about the *shape*",
              "Five rules about the *shape*", "break_sections_count")
    return "says 5, has 7 numbered sections"


def break_mid_sentence_count(root: Path) -> str:
    """The count moved off the front of the lead-in, and made wrong."""
    swap_once(root, "conventions/reframing-audit.md", "Five disciplines make the audit actually catch things:",
              "The audit has four disciplines that make it catch things:", "break_mid_sentence_count")
    return "says 4, has 5 items"


def break_subsection_count(root: Path) -> str:
    """A heading counting its own subheadings."""
    swap_once(root, "skills/mock-interview/references/personas.md", "## The seven personas",
              "## The six personas", "break_subsection_count")
    return "says 6, has 7 subsections"


def break_indented_count(root: Path) -> str:
    """A counted list nested inside another list's item."""
    swap_once(root, "conventions/evidence-conventions.md", "Three legitimate uses this rule does not touch",
              "Two legitimate uses this rule does not touch", "break_indented_count")
    return "says 2, has 3 items"


def break_restated_count(root: Path) -> str:
    """README restating output-discipline.md's count — the drift that actually happened."""
    swap_once(root, "README.md", "— seven rules on the shape of a delivered response",
              "— five rules on the shape of a delivered response", "break_restated_count")
    return '"five rules" beside `output-discipline.md`, which has 7 rules'



def break_readme_tree_omits(root: Path) -> str:
    """A skill README's folder tree missing a file the folder has — all three were."""
    path = root / "skills/job-underwriter/README.md"
    lines = path.read_text().split("\n")
    kept = [line for line in lines if "── citations.md" not in line]
    if len(kept) == len(lines):
        raise SystemExit("break_readme_tree_omits found no citations.md in the tree — it has gone stale")
    path.write_text("\n".join(kept))
    return "tree omits references/citations.md"


def break_readme_tree_phantom(root: Path) -> str:
    """A tree naming a file the folder does not have."""
    swap_once(root, "skills/job-underwriter/README.md", "│   ├── evidence-model.md ",
              "│   ├── worked-examples.md\n│   ├── evidence-model.md ", "break_readme_tree_phantom")
    return "worked-examples.md, which does not exist"


def break_readme_fixture_count(root: Path) -> str:
    """mock-interview's README described four fixtures while evals.json held six."""
    swap_once(root, "skills/mock-interview/README.md", "# 8 test fixtures", "# 4 test fixtures",
              "break_readme_fixture_count")
    return '"4 test fixtures" — evals.json has 8'


def break_fenced_restatement(root: Path) -> str:
    """A count in a folder tree's comment, beside the file it comes from."""
    swap_once(root, "skills/job-underwriter/README.md", "six drift axes, five disciplines",
              "five drift axes, five disciplines", "break_fenced_restatement")
    return '"five drift axes" beside `reframing-audit.md`, which has 6 axes'



# The next three each passed the first citations check, which compared a
# quotation with its entry only when straight quotation marks were followed
# directly by the marker. They are the panel's reproductions of the original
# defect arriving by the other doors.
PARAPHRASE = "This shift may favour established workers at the expense of newcomers trying\nto enter the market."


def break_marker_after_words(root: Path) -> str:
    """The paraphrase in quotation marks, the marker a few words later."""
    swap_once(root, "conventions/evidence-conventions.md", '"This shift may have important implications, including favoring established\nworkers at the expense of newcomers trying to enter the market." (cite C3)',
              '"' + PARAPHRASE + '" in the authors\' words (cite C3)', "break_marker_after_words")
    return "is close to C3's source but not its words"


def break_curly_paraphrase(root: Path) -> str:
    """The paraphrase in curly quotation marks, marker adjacent."""
    swap_once(root, "conventions/evidence-conventions.md", '"This shift may have important implications, including favoring established\nworkers at the expense of newcomers trying to enter the market." (cite C3)',
              "\u201c" + PARAPHRASE + "\u201d (cite C3)", "break_curly_paraphrase")
    return "and C3's Verbatim does not contain it"


def break_unmarked_paraphrase(root: Path) -> str:
    """The paraphrase in quotation marks with no marker at all — the defect as it shipped."""
    swap_once(root, "conventions/evidence-conventions.md", '"This shift may have important implications, including favoring established\nworkers at the expense of newcomers trying to enter the market." (cite C3)',
              '"' + PARAPHRASE + '"', "break_unmarked_paraphrase")
    return "is close to C3's source but not its words"



def break_close_contradicts_order(root: Path) -> str:
    """The expectation resume-tailor v0.1 shipped, and PR #9 fixed by hand: the
    response "closes with an upgrade menu", where closing_order puts questions last."""
    swap_once(root, "skills/resume-tailor/evals/evals.json",
              "The response ends with the upgrade menu, then the questions, then the watch-out line, in that order, "
              "asks at most three questions across the whole message",
              "The response closes with an upgrade menu and asks at most three questions across the whole message",
              "break_close_contradicts_order")
    return "closing_order ends watch-out"


def break_close_far_from_subject(root: Path) -> str:
    """job-underwriter's original wording, which a fixed window after the subject missed:
    sixty characters and a filename's full stop between "The response" and "closes"."""
    swap_once(root, "skills/job-underwriter/evals/evals.json",
              "and its upgrade menu names what each missing input would unlock. The response closes with the "
              "dossier offer, then the upgrade menu, then the questions, then the watch-out line",
              "and closes with an upgrade menu naming what each missing input would unlock",
              "break_close_far_from_subject")
    return '"closes with an upgrade menu naming what each missing input'


def break_budget_restated(root: Path) -> str:
    """A reference restating the question budget as a different number."""
    swap_once(root, "skills/job-underwriter/references/gap-taxonomy-and-questions.md",
              "**At most three questions per turn", "**At most four questions per turn", "break_budget_restated")
    return "question_budget is 3"



# The third panel's reproductions, each a form the previous version passed.
C11_SENTENCE = 'Tailored letters drew a **53% higher callback rate**\nthan no letter (cite C11).'
C3_QUOTE = ('"This shift may have important implications, including favoring established\n'
            'workers at the expense of newcomers trying to enter the market." (cite C3)')
PARAPHRASE_C3 = "This shift may favour established workers at the expense of newcomers trying\nto enter the market."


def break_marker_before_quote(root: Path) -> str:
    """Author-date order: the marker first, then a quotation with a wrong figure."""
    swap_once(root, "docs/cover-letter-spec-v0.md", C11_SENTENCE,
              'ResumeGo (cite C11) reports tailored letters drew a "35% higher callback rate" than no letter.',
              "break_marker_before_quote")
    return "carries a figure in a cited sentence"


def break_marker_after_et_al(root: Path) -> str:
    """ "et al." read as a sentence end cut the quotation off from its marker."""
    swap_once(root, "docs/cover-letter-spec-v0.md", C11_SENTENCE,
              'Tailored letters drew a "35% higher callback rate" than no letter, in the study by Kazmi et al. (cite C11).',
              "break_marker_after_et_al")
    return "carries a figure in a cited sentence"


def break_multi_id_marker(root: Path) -> str:
    """ "(cite C1, C2)" was not a marker at all, so nothing it covered was checked."""
    swap_once(root, "docs/cover-letter-spec-v0.md", "| **fell 51%** | (cite C1) |",
              '| "fell by 15%" | (cite C1, C2) |', "break_multi_id_marker")
    return "malformed marker"


def break_single_quoted_source(root: Path) -> str:
    """The shipped paraphrase in curly single quotation marks, marker adjacent: read as a quotation."""
    swap_once(root, "conventions/evidence-conventions.md", C3_QUOTE,
              "\u2018" + PARAPHRASE_C3 + "\u2019 (cite C3)", "break_single_quoted_source")
    return "and C3's Verbatim does not contain it"


def break_blockquoted_source(root: Path) -> str:
    """The shipped paraphrase as a Markdown blockquote, marker inside it."""
    swap_once(root, "conventions/evidence-conventions.md", C3_QUOTE,
              "\n> " + PARAPHRASE_C3.replace("\n", "\n> ") + " (cite C3)\n", "break_blockquoted_source")
    return "a blockquote carrying a marker"


def break_short_verbatim_uncited(root: Path) -> str:
    """A four-word source quotation with no marker — under the old six-word floor."""
    swap_once(root, "docs/cover-letter-spec-v0.md", C11_SENTENCE,
              C11_SENTENCE + '\nSuch questions "should generally be avoided".', "break_short_verbatim_uncited")
    return "quotes C29's source verbatim without (cite C29)"


def break_section_clause_qualifier(root: Path) -> str:
    """ "(as the grammar says in §8)" — the qualifier three words from the section sign."""
    swap_once(root, "docs/job-underwriter-build-brief.md", "(`interaction-grammar.md` §8)",
              "(as the grammar says in §8)", "break_section_clause_qualifier")
    return 'bare §8 after "grammar"'


def break_section_plural_possessive(root: Path) -> str:
    swap_once(root, "docs/job-underwriter-build-brief.md", "(`interaction-grammar.md` §8)",
              "(the conventions' §8)", "break_section_plural_possessive")
    return 'bare §8 after "conventions"'


def break_section_uppercase_file(root: Path) -> str:
    """`SKILL.md` §2 — a file with no numbered sections, which the old pattern could not read."""
    swap_once(root, "docs/cover-letter-spec-v0.md", "guessing is what §2 exists to prevent.",
              "guessing is what `SKILL.md` §2 exists to prevent.", "break_section_uppercase_file")
    return "`SKILL.md` §2 — that file has no section 2"


def break_section_enumeration(root: Path) -> str:
    """ "`x.md` §4 and §9": the second number belongs to the grammar, which has no §9.
    The previous version caught this through its block rule; it guards the new
    list reading, which must not let a second number escape its file."""
    swap_once(root, "docs/job-underwriter-build-brief.md", "per `interaction-grammar.md` §4 and",
              "per `interaction-grammar.md` §4 and §9, and", "break_section_enumeration")
    return "`interaction-grammar.md` §9 — that file has no section 9"


def break_count_in_digits(root: Path) -> str:
    """A README tree's digit count beside its file."""
    swap_once(root, "skills/mock-interview/README.md", "# 7 interviewer personas", "# 6 interviewer personas",
              "break_count_in_digits")
    return '"6 interviewer personas" beside `personas.md`, which has 7 personas'


def break_count_bold_lead(root: Path) -> str:
    """A lead-in whose colon sits inside bold."""
    swap_once(root, "conventions/evidence-conventions.md", "\nThree overrides that beat every label:\n",
              "\n**Two overrides that beat every label:**\n", "break_count_bold_lead")
    return "says 2, has 3 items"


def break_count_determiner_opening(root: Path) -> str:
    """ "These five rules" ahead of seven numbered sections."""
    swap_once(root, "conventions/output-discipline.md", "Seven rules about the *shape*",
              "These five rules are about the *shape*", "break_count_determiner_opening")
    return "says 5, has 7 numbered sections"


def break_close_reversed(root: Path) -> str:
    """The right sections named in the wrong order."""
    swap_once(root, "skills/resume-tailor/evals/evals.json",
              "The response ends with the upgrade menu, then the questions, then the watch-out line, in that order, "
              "asks at most three questions across the whole message",
              "The response ends with the watch-out line, then the questions, then the upgrade menu, in that order, "
              "asks at most three questions across the whole message", "break_close_reversed")
    return "closing_order ends upgrade menu, then questions, then watch-out"


def break_close_synonym(root: Path) -> str:
    swap_once(root, "skills/job-underwriter/evals/evals.json",
              "The response closes with the dossier offer, then the upgrade menu, then the questions, then the watch-out line",
              "The response concludes with an upgrade menu", "break_close_synonym")
    return "closing_order ends watch-out"


def break_close_skill_subject(root: Path) -> str:
    swap_once(root, "skills/job-underwriter/evals/evals.json",
              "The response closes with the dossier offer, then the upgrade menu, then the questions, then the watch-out line",
              "The skill closes with an upgrade menu", "break_close_skill_subject")
    return "closing_order ends watch-out"


def break_close_incidental_word(root: Path) -> str:
    """ "questions" inside a participle clause is not the questions section."""
    swap_once(root, "skills/job-underwriter/evals/evals.json",
              "The response closes with the dossier offer, then the upgrade menu, then the questions, then the watch-out line",
              "The response closes with an upgrade menu listing the questions that would sharpen it",
              "break_close_incidental_word")
    return "closing_order ends watch-out"


def break_budget_maximum(root: Path) -> str:
    swap_once(root, "skills/mock-interview/SKILL.md", "Ask at most three questions,", "Ask a maximum of four questions,",
              "break_budget_maximum")
    return "question_budget is 3"


def break_budget_readme(root: Path) -> str:
    """The README that tells users the budget."""
    swap_once(root, "skills/job-underwriter/README.md", "The skill asks at most three questions per turn",
              "The skill asks at most four questions per turn", "break_budget_readme")
    return "question_budget is 3"


def break_readme_wrong_folder(root: Path) -> str:
    """A reference file drawn under evals/: the name is present, the path is not."""
    path = root / "skills/mock-interview/README.md"
    lines = path.read_text().split("\n")
    kept = [line for line in lines if not line.startswith("│   └── citations.md")]
    if len(kept) == len(lines):
        raise SystemExit("break_readme_wrong_folder found no citations.md line — it has gone stale")
    i = next(k for k, line in enumerate(kept) if "evals.json" in line)
    kept[i] = kept[i].replace("└── evals.json", "├── evals.json")
    kept.insert(i + 1, "│   └── citations.md")
    kept = [line.replace("│   ├── dossier-schema.md", "│   └── dossier-schema.md", 1) if "dossier-schema.md" in line else line
            for line in kept]
    path.write_text("\n".join(kept))
    return "tree omits references/citations.md"


def break_readme_fixture_noun(root: Path) -> str:
    swap_once(root, "skills/mock-interview/README.md", "# 8 test fixtures", "# 4 test cases", "break_readme_fixture_noun")
    return '"4 test cases" — evals.json has 8'



# The fourth review's reproductions, each passed by the version it reviewed.

def break_misquoted_figure(root: Path) -> str:
    """An entry's words with the figure changed, unmarked: "fell by 15%" for "fell by 51%"."""
    swap_once(root, "docs/cover-letter-spec-v0.md", "It is the collapse.",
              'It is the collapse: the tailoring correlation "fell by 15%".', "break_misquoted_figure")
    return "C1's wording with a different figure"


def break_hedge_dropped_from_quote(root: Path) -> str:
    """The true half of a hedged sentence, quoted and cited, the hedge left behind."""
    swap_once(root, "docs/cover-letter-spec-v0.md", "It is the collapse.",
              'It is the collapse, and the authors find it is "favoring established workers at the expense of '
              'newcomers" (cite C3).', "break_hedge_dropped_from_quote")
    return "starts after its source's hedge"


def break_single_quoted_paraphrase(root: Path) -> str:
    """A paraphrase in curly single quotes, its marker a few words later."""
    swap_once(root, "docs/cover-letter-spec-v0.md", "It is the collapse.",
              "It is the collapse, which \u2018may favour established workers over newcomers\u2019 in the authors' "
              "words (cite C3).", "break_single_quoted_paraphrase")
    return "is close to C3's source but not its words"


def break_section_spaced_name(root: Path) -> str:
    """A file named with spaces: "the output discipline's §4" in a brief with its own §4."""
    swap_once(root, "docs/job-underwriter-build-brief.md", "- **The n + x rule**",
              "- **Closing order** (the output discipline's §4): dossier offer, upgrade menu, questions.\n- **The n + x rule**",
              "break_section_spaced_name")
    return 'after "output discipline"'


def break_section_wrapped_qualifier(root: Path) -> str:
    """The qualifier on the line before the section sign."""
    swap_once(root, "docs/cover-letter-spec-v0.md", "this skill would ship with §4 written first.",
              "this skill would ship with §4 written first, and with the n + x rule the grammar\nstates in §8.",
              "break_section_wrapped_qualifier")
    return 'bare §8 after "grammar"'


def break_count_definite_frame(root: Path) -> str:
    """ "the five rules in `output-discipline.md`" — the total, restated wrong."""
    swap_once(root, "README.md", "— seven rules on the shape of a delivered response",
              "— the five rules in `output-discipline.md` on the shape of a delivered response",
              "break_count_definite_frame")
    return '"five rules" beside `output-discipline.md`, which has 7 rules'


def break_close_adverb_imperative(root: Path) -> str:
    swap_once(root, "skills/job-underwriter/SKILL.md", "because the snapshot at the top is its one summary (Step 1).",
              "because the snapshot at the top is its one summary (Step 1). Always close with the upgrade menu.",
              "break_close_adverb_imperative")
    return "closing_order ends watch-out"


def break_close_head_subject(root: Path) -> str:
    """ "the message presenting the pack ends with the upgrade menu" is about the message."""
    swap_once(root, "skills/mock-interview/evals/evals.json",
              'and the message presenting it ends with the drill and dossier offers, then the questions, then the watch-out line, with nothing after it',
              "and the message presenting the pack ends with the upgrade menu",
              "break_close_head_subject")
    return "closing_order ends"


def break_budget_counted_across(root: Path) -> str:
    swap_once(root, "skills/resume-tailor/SKILL.md", "**Three questions, counted across the whole message",
              "**Four questions, counted across the whole message", "break_budget_counted_across")
    return "question_budget is 3"


def break_budget_on_any_turn(root: Path) -> str:
    swap_once(root, "skills/job-underwriter/README.md", "The skill asks at most three questions per turn",
              "The skill asks at most four questions on any turn", "break_budget_on_any_turn")
    return "question_budget is 3"


def keep_contraction_in_quote(root: Path) -> None:
    swap_once(root, "skills/job-underwriter/README.md", "and proceeds if you ignore them.",
              'and proceeds if you ignore them. Answering "I don\'t use LinkedIn" is fine too.', "keep_contraction_in_quote")


def keep_prompt_with_domain_words(root: Path) -> None:
    swap_once(root, "docs/cover-letter-spec-v0.md", "Five fixtures, each carrying the trap",
              'Five fixtures, each opening with a prompt like "write a cover letter for this job" and each carrying the trap',
              "keep_prompt_with_domain_words")


def keep_example_question_in_cited_sentence(root: Path) -> None:
    swap_once(root, "skills/mock-interview/references/personas.md", "and otherwise differs by topic.",
              'and otherwise differs by topic. Some interviewers still ask "Where are you from originally?" and "Most '
              'employers should not ask whether or not a job applicant is a United States citizen before making an offer '
              'of employment" (cite C32).', "keep_example_question_in_cited_sentence")


def keep_sentence_after_quoted_stop(root: Path) -> None:
    swap_once(root, "docs/cover-letter-spec-v0.md", "Tailored letters drew a **53% higher callback rate**",
              'Recruiters call this "tailoring." Tailored letters drew a **53% higher callback rate**',
              "keep_sentence_after_quoted_stop")


def keep_own_skill_name_in_spec(root: Path) -> None:
    swap_once(root, "docs/mock-interview-spec-v1.md", "Every fixture asserts §3.1",
              "Every mock-interview fixture asserts §3.1", "keep_own_skill_name_in_spec")


def keep_unnumbered_file_in_block(root: Path) -> None:
    swap_once(root, "docs/mock-interview-spec-v1.md", "Every fixture asserts §3.1",
              "Every fixture asserts §3.1, which SKILL.md opens with,", "keep_unnumbered_file_in_block")


def keep_city_code(root: Path) -> None:
    swap_once(root, "skills/mock-interview/references/personas.md", "Other jurisdictions differ, and",
              "Other jurisdictions differ — New York City bars salary-history questions under N.Y.C. Admin. Code "
              "§8-107 — and", "keep_city_code")


def keep_list_with_local_above(root: Path) -> None:
    swap_once(root, "docs/cover-letter-spec-v0.md", "§5.2 says why that misread the audit.",
              "`evidence-conventions.md` §4 and §5.2 above say why that misread the audit.", "keep_list_with_local_above")


def keep_determiner_lead(root: Path) -> None:
    swap_once(root, "conventions/evidence-conventions.md", "\nThree overrides that beat every label:\n",
              "\nThese three overrides beat every label:\n", "keep_determiner_lead")


def keep_lead_with_one_example(root: Path) -> None:
    swap_once(root, "conventions/evidence-conventions.md", "\nThree overrides that beat every label:\n",
              "\nThree overrides that beat every label, each with its reason and one example:\n", "keep_lead_with_one_example")


def keep_time_in_lead(root: Path) -> None:
    path = root / "skills/mock-interview/references/question-rubric.md"
    path.write_text(path.read_text().rstrip("\n") + "\n\nA strong plan answer covers the first 90 days:\n\n"
                    "- what they would learn\n- what they would change\n- what they would leave alone\n")


def keep_count_opening_a_preamble(root: Path) -> None:
    swap_once(root, "docs/cover-letter-spec-v0.md", "The research came first this time, and it changed the design.",
              "Two things are different this time. The research came first, and it changed the design.",
              "keep_count_opening_a_preamble")


def keep_other_axes_near_audit(root: Path) -> None:
    swap_once(root, "docs/mock-interview-spec-v1.md", "two axes that a list does not have",
              "two axes that a list does not have, and audits every line against `reframing-audit.md`",
              "keep_other_axes_near_audit")


def keep_interview_questions_budget(root: Path) -> None:
    swap_once(root, "skills/mock-interview/references/personas.md", "the top persona gets 4–5 questions",
              "the top persona gets up to five questions", "keep_interview_questions_budget")


def keep_close_after_colon(root: Path) -> None:
    swap_once(root, "skills/job-underwriter/SKILL.md", "because the snapshot at the top is its one summary (Step 1).",
              "because the snapshot at the top is its one summary (Step 1). The response ends with its three calls to "
              "action: the dossier offer, then the upgrade menu, then the questions.", "keep_close_after_colon")


def keep_drill_turn(root: Path) -> None:
    swap_once(root, "skills/mock-interview/references/output-template.md", "Follow up at least twice",
              "Each drill turn ends with feedback on the answer. Follow up at least twice", "keep_drill_turn")


def keep_wrap_before_bold(root: Path) -> None:
    swap_once(root, "skills/mock-interview/SKILL.md",
              "file, the offers, the questions and the watch-out line\nclose the message that presents it,",
              "file, the message that presents it closes with the drill and dossier offers, then\n**any questions**, "
              "then the watch-out line,", "keep_wrap_before_bold")


def keep_cases_of_something_else(root: Path) -> None:
    swap_once(root, "skills/job-underwriter/README.md", "and proceeds if you ignore them.",
              "and proceeds if you ignore them. In two cases it asks nothing at all: when the JD and CV already answer "
              "everything, and when you say skip.", "keep_cases_of_something_else")


# Must-pass: correct text in forms an earlier version refused. A false positive
# teaches authors to distort prose or switch a check off, so it fails the
# self-test the way an evasion does.

def keep_label_matches_own_heading(root: Path) -> None:
    swap_once(root, "docs/cover-letter-spec-v0.md", "guessing is what §2 exists to prevent.",
              "guessing is what the evidence (§2) exists to prevent.", "keep_label_matches_own_heading")


def keep_self_reference_of_this_spec(root: Path) -> None:
    swap_once(root, "docs/cover-letter-spec-v0.md", "guessing is what §2 exists to prevent.",
              "guessing is what §2 of this spec exists to prevent, as `evidence-conventions.md` §4 requires.",
              "keep_self_reference_of_this_spec")


def keep_statute_citation(root: Path) -> None:
    swap_once(root, "docs/cover-letter-spec-v0.md", "guessing is what §2 exists to prevent.",
              "guessing is what §2 exists to prevent. Citizenship is what 8 U.S.C. §1324b covers.",
              "keep_statute_citation")


def keep_stacked_markers(root: Path) -> None:
    swap_once(root, "docs/cover-letter-spec-v0.md", C11_SENTENCE,
              'Of "7,287 fictitious job applications" (cite C12), tailored letters had "a 53% higher callback rate" (cite C12) (cite C11).',
              "keep_stacked_markers")


def keep_curly_and_british_punctuation(root: Path) -> None:
    swap_once(root, "conventions/evidence-conventions.md", C3_QUOTE,
              "\u201cThis shift may have important implications, including favoring established\n"
              "workers at the expense of newcomers trying to enter the market\u201d. (cite C3)",
              "keep_curly_and_british_punctuation")


def keep_second_quantity_in_lead(root: Path) -> None:
    swap_once(root, "CONTRIBUTING.md", "The rule is written from four bugs, all in this repository's own harnesses, all",
              "The rule is written from four bugs, found in two harnesses, all in this repository's own harnesses, all",
              "keep_second_quantity_in_lead")


def keep_subset_beside_file(root: Path) -> None:
    swap_once(root, "README.md", "Coherence lives in [`conventions/`]",
              "Two rules in `output-discipline.md` decide where a response puts its questions. Coherence lives in [`conventions/`]",
              "keep_subset_beside_file")


def keep_negated_close(root: Path) -> None:
    swap_once(root, "skills/job-underwriter/evals/evals.json",
              "The response closes with the dossier offer, then the upgrade menu, then the questions, then the watch-out line",
              "The response does not close with the upgrade menu: it closes with the dossier offer, then the upgrade menu, then the questions, then the watch-out line",
              "keep_negated_close")


def keep_section_enumeration(root: Path) -> None:
    """ "`x.md` §4 and §5", both of which exist: refused while the second read as bare."""
    swap_once(root, "docs/job-underwriter-build-brief.md", "per `interaction-grammar.md` §4 and",
              "per `interaction-grammar.md` §4 and §5, and", "keep_section_enumeration")


def keep_topic_sub_budget(root: Path) -> None:
    swap_once(root, "skills/mock-interview/SKILL.md", "Ask at most three questions,",
              "Ask at most three questions, at most one question about the interviewer,", "keep_topic_sub_budget")


# The worked dossier's fit ledger, read against its own map. Each mutation is a
# way the old prose sentence was, or could have been, wrong without anyone seeing.

# The worked dossier is two files: the report, and the JSON envelope that closes it.
DOSSIER = "skills/job-underwriter/references/dossier-worked-report.md"
ENVELOPE = "skills/job-underwriter/references/dossier-worked-envelope.md"


def break_ledger_fit_cell(root: Path) -> str:
    swap_once(root, DOSSIER, "| R4 | Community energy knowledge: generation, grid connection, share offers | must_have | adjacent |",
              "| R4 | Community energy knowledge: generation, grid connection, share offers | must_have | direct |", "break_ledger_fit_cell")
    return "fit ledger files R4 as must_have/adjacent; the map says must_have/direct"


def break_ledger_priority_cell(root: Path) -> str:
    swap_once(root, DOSSIER, "| R6 | Grants data: grant-management database, portfolio reporting | important |",
              "| R6 | Grants data: grant-management database, portfolio reporting | must_have |", "break_ledger_priority_cell")
    return "fit ledger files R6 as important/direct; the map says must_have/direct"


def break_ledger_drops_last_row(root: Path) -> str:
    """s1r1's shape: the row added last is the one the summary leaves out."""
    swap_once(root, DOSSIER, "- `preferred` — absent: R7 (Social investment experience)\n", "",
              "break_ledger_drops_last_row")
    return "fit ledger omits R7"


def break_ledger_duplicate_row(root: Path) -> str:
    swap_once(root, DOSSIER, "- `important` — direct: R6 ·", "- `important` — direct: R6, R2 ·",
              "break_ledger_duplicate_row")
    return "fit ledger lists R2 2 times"


def break_ledger_envelope(root: Path) -> str:
    path = root / ENVELOPE
    text = path.read_text()
    old = '"requirement_id": "R4",\n        "priority": "must_have",'
    if text.count(old) != 1:
        raise SystemExit("break_ledger_envelope has gone stale")
    head, tail = text.split(old)
    tail = tail.replace('"fit_status": "adjacent"', '"fit_status": "direct"', 1)
    path.write_text(head + old + tail)
    return "the envelope says must_have/direct"


def break_ledger_back_to_prose(root: Path) -> str:
    """The v0.1 sentence itself. It must fail, not skip."""
    path = root / DOSSIER
    text = path.read_text()
    start = text.index("**Fit ledger.**")
    end = text.index("R4 — a credible bridge")
    path.write_text(text[:start] + "**Fit ledger.** Five of seven material requirements are `direct` (R1–R3, R6, and the eligibility gate). " + text[end:])
    return "fit ledger: "


def break_ledger_summary_count(root: Path) -> str:
    swap_once(root, ENVELOPE, '"summary": "Fit as evidence_map reads it,',
              '"summary": "Strong fit: five of seven material requirements are direct. Fit as evidence_map reads it,',
              "break_ledger_summary_count")
    return 'decision.summary: "five of seven material requirements" is a set claim over the map that names no row'


def keep_ledger_summary_count_named(root: Path) -> None:
    """GRADER: the same count in the summary's first sentence, which names R4: read as
    a count over the map, it names a row and passes the check; that it counts five of
    seven and names one is the grader's (the comment above Claim in ci/ledger_rules.py)."""
    swap_once(root, ENVELOPE, '"summary": "Fit as evidence_map reads it,',
              '"summary": "Strong fit (five of seven material requirements direct),', "keep_ledger_summary_count_named")


def break_ledger_name(root: Path) -> str:
    swap_once(root, DOSSIER, "adjacent: R4 (Community energy knowledge)", "adjacent: R4 (Energy policy)", "break_ledger_name")
    return "in words its Requirement cell does not use"


def break_ledger_band(root: Path) -> str:
    """s3r4's shape: a band in the snapshot the map does not carry."""
    swap_once(root, DOSSIER, "R3 (`medium`)", "R3 (`high`)", "break_ledger_band")
    return "snapshot gives R3 `high`; the map says medium"


def keep_ledger_split_rows(root: Path) -> None:
    """A requirement split into two rows is two rows, in the ledger as in the map."""
    path = root / DOSSIER
    text = path.read_text()
    row = next(line for line in text.splitlines() if line.startswith("| R4 |"))
    text = text.replace(row, row.replace("| R4 |", "| R4a |") + "\n" + row.replace("| R4 |", "| R4b |").replace("| adjacent |", "| absent |"))
    text = text.replace("adjacent: R4 (Community energy knowledge)", "adjacent: R4a (Community energy knowledge) · absent: R4b (Community energy knowledge)")
    path.write_text(text)
    path = root / ENVELOPE
    text = path.read_text()
    blocks = text.split("```json\n")
    head, rest = blocks[-1].split("\n```", 1)
    data = json.loads(head)
    emap = data["sections"]["evidence_map"]
    i = next(k for k, r in enumerate(emap) if r["requirement_id"] == "R4")
    a, b = dict(emap[i]), dict(emap[i])
    a["requirement_id"], b["requirement_id"], b["fit_status"] = "R4a", "R4b", "absent"
    emap[i:i + 1] = [a, b]
    blocks[-1] = json.dumps(data, indent=2, ensure_ascii=False) + "\n```" + rest
    path.write_text("```json\n".join(blocks))


def break_ledger_count_beside(root: Path) -> str:
    """The v0.1 sentence put back next to an intact ledger, not instead of it."""
    swap_once(root, DOSSIER, "**Fit ledger.**\n\n- `hard_gate`",
              "Five of seven material requirements are `direct`.\n\n**Fit ledger.**\n\n- `hard_gate`", "break_ledger_count_beside")
    return 'the snapshot\'s prose: "Five of seven material requirements" is a set claim over the map that names no row'


def keep_ledger_sentence_only(root: Path) -> None:
    """GRADER (round 9): the first probe runs' shape, "the only row below `direct`" under
    a ledger listing more, names R4: "only" is a named-set word, and whether R4 is the
    whole set is agreement, the grader's (the comment above Claim in ci/ledger_rules.py)."""
    swap_once(root, DOSSIER, "R4 — a credible bridge, its limit named;",
              "R4 — the only row below `direct` that matters;", "keep_ledger_sentence_only")


def break_ledger_sentence_only_unnamed(root: Path) -> str:
    """The same "only", its rows unnamed: it fails as an unnamed set claim."""
    swap_once(root, DOSSIER, AFTER_LEDGER, "The only rows below `direct` have credible bridges.",
              "break_ledger_sentence_only_unnamed")
    return 'the sentence after the fit ledger: "The only rows" is a set claim over the map that names no row'


def break_ledger_summary_universal(root: Path) -> str:
    swap_once(root, ENVELOPE, '"summary": "Fit as evidence_map reads it,',
              '"summary": "Every must_have requirement is direct. Fit as evidence_map reads it,',
              "break_ledger_summary_universal")
    return 'decision.summary: "Every must_have" is a set claim over the map that names no row'


def keep_ledger_summary_universal_but(root: Path) -> None:
    """GRADER: "every … but R4" names R4; an exception in its words is the grader's (the
    comment above Claim in ci/ledger_rules.py)."""
    swap_once(root, ENVELOPE, '"summary": "Fit as evidence_map reads it,',
              '"summary": "Every must_have requirement is direct but R4;', "keep_ledger_summary_universal_but")


def break_ledger_tier_twice(root: Path) -> str:
    swap_once(root, DOSSIER, "- `preferred` — absent: R7 (Social investment experience)\n",
              "- `preferred` — absent: R7 (Social investment experience)\n- `preferred` — absent: R7 (Social investment)\n",
              "break_ledger_tier_twice")
    return "has more than one ledger line"


def break_ledger_gate_line(root: Path) -> str:
    swap_once(root, DOSSIER, "none failed (R1 `direct`, R9 `direct`)", "none failed (R1 `direct`)", "break_ledger_gate_line")
    return "the hard-gates line names"


def break_ledger_bare_severity(root: Path) -> str:
    """A severity written like a band is read as one — the rule says write its full token."""
    swap_once(root, DOSSIER, "- **Severe red flags:** none found.", "- **Severe red flags:** RR2 (`high`).",
              "break_ledger_bare_severity")
    return "without attaching it to one row"


def break_ledger_tally_budget(root: Path) -> str:
    swap_once(root, DOSSIER, "Research tier: L1 — searches 4 of 5,", "Research tier: L1 — searches 4 of 6,",
              "break_ledger_tally_budget")
    return "SKILL.md's L1 budget is 5/2"


def break_ledger_tally_twice(root: Path) -> str:
    swap_once(root, DOSSIER, "Research tier: L1 — searches 4 of 5, fetches 1 of 2; user links read 1\n",
              "Research tier: L1 — searches 4 of 5, fetches 1 of 2; user links read 1\nResearch tier: L1 — searches 4 of 5, fetches 2 of 2\n",
              "break_ledger_tally_twice")
    return "2 Research tier lines"


def break_ledger_stopword_name(root: Path) -> str:
    swap_once(root, DOSSIER, "unclear: R5 (Line-managing grants officers)", "unclear: R5 (the)", "break_ledger_stopword_name")
    return "in words its Requirement cell does not use"


def keep_ledger_severity_token(root: Path) -> None:
    """A severity in its full token beside a register ID is not a confidence band."""
    swap_once(root, DOSSIER, "the contract basis is unstated against the candidate's permanent-only constraint (RR2).",
              "the contract basis is unstated against the candidate's permanent-only constraint (RR2 (`severity: medium`)).",
              "keep_ledger_severity_token")


def break_answer_key(root: Path) -> str:
    """The rubric's old Provenance example: a fixture's own sentence, installed beside the skill."""
    swap_once(root, "skills/mock-interview/references/question-rubric.md",
              '`[grounded] "Ran the small-grants round for three years"`',
              '`[grounded] "ran the site\'s peak-season surge plan two years running"`', "break_answer_key")
    return "quoted from this skill's own fixtures"


def keep_answer_key_other_skill(root: Path) -> None:
    """Another skill's fixture is not this skill's answer key: a room installs one skill."""
    swap_once(root, "skills/job-underwriter/references/risk-and-decision.md",
              '("we\'re a family, and families pitch in after hours")',
              '("ran the site\'s peak-season surge plan two years running")', "keep_answer_key_other_skill")

# What the first fit-ledger fixes still let through (cross-cutting F1, JU-11, JU-2,
# JU-8): each is a reading of the map the rule forbids, in a shape the narrower
# patterns did not reach.

AFTER_LEDGER = "R4 — a credible bridge, its limit named; R3 (`medium`) — confirmed, waiting on an artifact."
# A must-pass sentence after the ledger is written in rule 2's list form, which the group
# holds the worked sentence to; a must-fail one may stay in prose, failing the form too.


def break_ledger_count_words_between(root: Path) -> str:
    """"N of the M" with words before the noun: COUNTED needed "N of M" exactly."""
    swap_once(root, DOSSIER, AFTER_LEDGER, AFTER_LEDGER + " Four of the seven material requirements are `direct`.",
              "break_ledger_count_words_between")
    return 'the sentence after the fit ledger: "Four of the seven material requirements" is a set claim over the map that names no row'


def break_ledger_bare_count(root: Path) -> str:
    """A count with no "of" at all."""
    swap_once(root, DOSSIER, AFTER_LEDGER, "Four rows are `direct`.", "break_ledger_bare_count")
    return 'the sentence after the fit ledger: "Four rows" is a set claim over the map that names no row'


def break_ledger_second_paragraph(root: Path) -> str:
    """The first paragraph after the ledger is clean; the second one quantifies."""
    swap_once(root, DOSSIER, AFTER_LEDGER, AFTER_LEDGER + "\n\nThe rest are `direct`.", "break_ledger_second_paragraph")
    return "the sentence after the fit ledger: \"The rest are `direct`\" is a complement"


def break_ledger_two_sentences(root: Path) -> str:
    """Rule 2 allows at most one sentence after the ledger, quantifier or not."""
    swap_once(root, DOSSIER, AFTER_LEDGER,
              "R4 — a credible bridge, its limit named. R3 (`medium`) — confirmed, waiting on an artifact.",
              "break_ledger_two_sentences")
    return "is followed by more than one sentence"


def break_ledger_form_prose(root: Path) -> str:
    """The sentence the worked example used to teach, back: one sentence, and no list."""
    swap_once(root, DOSSIER, AFTER_LEDGER,
              "R4 has a credible bridge with its limit named, and R3 (`medium`) is confirmed but waits on an artifact.",
              "break_ledger_form_prose")
    return "the sentence after the fit ledger is not in rule 2's list form: the item 'R4 has a credible bridge"


def break_ledger_form_item_unopened(root: Path) -> str:
    """A second item that does not open with its row IDs."""
    swap_once(root, DOSSIER, AFTER_LEDGER,
              "R4 — a credible bridge, its limit named; and R3 (`medium`) is confirmed, waiting on an artifact.",
              "break_ledger_form_item_unopened")
    return "the item 'and R3 (`medium`) is confirmed"


def break_ledger_form_no_dash(root: Path) -> str:
    """Each item its row ID, then a colon where the dash goes."""
    swap_once(root, DOSSIER, AFTER_LEDGER,
              "R4: a credible bridge, its limit named; R3 (`medium`): confirmed, waiting on an artifact.",
              "break_ledger_form_no_dash")
    return "not in rule 2's list form: the item 'R4: a credible bridge"


def break_ledger_form_range(root: Path) -> str:
    """A range where the item's IDs go: the dash in it is not the item's."""
    swap_once(root, DOSSIER, AFTER_LEDGER, AFTER_LEDGER.replace("R3 (`medium`) — confirmed", "R2–R3 confirmed"),
              "break_ledger_form_range")
    return "the item 'R2–R3 confirmed"


def keep_ledger_form_grouped(root: Path) -> None:
    """An item for a group of rows, the IDs joined by "and", a band beside one of them."""
    swap_once(root, DOSSIER, AFTER_LEDGER,
              "R4 and R5 — named limits on the bridges; R3 (`medium`) — confirmed, waiting on an artifact.",
              "keep_ledger_form_grouped")


def keep_ledger_form_one_item(root: Path) -> None:
    """One item is a list of one."""
    swap_once(root, DOSSIER, AFTER_LEDGER, "R4 — a credible bridge, its limit named.", "keep_ledger_form_one_item")


def keep_ledger_form_hyphen(root: Path) -> None:
    """A spaced hyphen as the dash, and a semicolon inside a parenthesis that ends no item."""
    swap_once(root, DOSSIER, AFTER_LEDGER,
              "R4 - a credible bridge (its limit named; see RR1); R3 (`medium`) - confirmed, waiting on an artifact.",
              "keep_ledger_form_hyphen")


def break_ledger_both_after(root: Path) -> str:
    """"both" over a set the sentence leaves unnamed (round 7: named, it is lawful)."""
    swap_once(root, DOSSIER, AFTER_LEDGER, "Both wait on an artifact.", "break_ledger_both_after")
    return "the sentence after the fit ledger: \"Both\" is a set claim over the map that names no row"


def keep_ledger_both_named(root: Path) -> None:
    """"both" over the rows the sentence names: the set is those rows, and nothing is left to resolve."""
    swap_once(root, DOSSIER, AFTER_LEDGER, "R4 and R3 (`medium`) — both wait on an artifact.", "keep_ledger_both_named")


def break_ledger_universal_in_verdict(root: Path) -> str:
    """A universal over a tier in a slot other than the sentence after the ledger."""
    swap_once(root, DOSSIER, "**Worth applying to — on the conditions below.",
              "**Worth applying to — every must_have requirement is direct.", "break_ledger_universal_in_verdict")
    return 'the snapshot\'s prose: "every must_have" is a set claim over the map that names no row'


def keep_ledger_universal_but_in_verdict(root: Path) -> None:
    """GRADER: the same universal with "but R4" names R4; an exception in its words is
    the grader's (the comment above Claim in ci/ledger_rules.py)."""
    swap_once(root, DOSSIER, "**Worth applying to — on the conditions below.",
              "**Worth applying to — every must_have requirement is direct but R4.",
              "keep_ledger_universal_but_in_verdict")


def break_ledger_summary_all_but(root: Path) -> str:
    swap_once(root, ENVELOPE, '"summary": "Fit as evidence_map reads it,', '"summary": "Direct on all but R4;',
              "break_ledger_summary_all_but")
    return 'decision.summary: "all but" is a complement'


def break_ledger_summary_bare_count(root: Path) -> str:
    swap_once(root, ENVELOPE, '"summary": "Fit as evidence_map reads it,', '"summary": "Four direct. Fit as evidence_map reads it,',
              "break_ledger_summary_bare_count")
    return 'decision.summary: "Four direct" is a set claim over the map that names no row'


def break_ledger_summary_of_the(root: Path) -> str:
    swap_once(root, ENVELOPE, '"summary": "Fit as evidence_map reads it,',
              '"summary": "Four of the seven direct. Fit as evidence_map reads it,', "break_ledger_summary_of_the")
    return 'decision.summary: "Four of the seven direct" is a set claim over the map that names no row'


def keep_ledger_summary_counts_named(root: Path) -> None:
    """GRADER: "Four direct" and "Four of the seven direct" in the summary's first
    sentence, which names R4: each names a row and passes the check; that each counts
    four and names one, and M, are the grader's (the comment above Claim in ci/ledger_rules.py)."""
    swap_once(root, ENVELOPE, '"summary": "Fit as evidence_map reads it,',
              '"summary": "Four direct, four of the seven direct;', "keep_ledger_summary_counts_named")


def break_ledger_plain_band(root: Path) -> str:
    """A band without backticks is still a band, and this one is not R3's."""
    swap_once(root, DOSSIER, "R3 (`medium`)", "R3 (high)", "break_ledger_plain_band")
    return "snapshot gives R3 `high`; the map says medium"


def break_ledger_fit_twice(root: Path) -> str:
    swap_once(root, DOSSIER, "- `must_have` — direct: R2, R3 · adjacent: R4 (Community energy knowledge)",
              "- `must_have` — direct: R2 · direct: R3 · adjacent: R4 (Community energy knowledge)", "break_ledger_fit_twice")
    return "fit direct appears twice under must_have"


def break_ledger_severity_mismatch(root: Path) -> str:
    """A full severity token the register does not carry: RR2 is medium."""
    swap_once(root, DOSSIER, "- **Severe red flags:** none found.", "- **Severe red flags:** RR2 (`severity: high`).",
              "break_ledger_severity_mismatch")
    return "snapshot gives RR2 `severity: high`; the register says medium"


def break_ledger_severity_unknown_id(root: Path) -> str:
    swap_once(root, DOSSIER, "- **Severe red flags:** none found.", "- **Severe red flags:** RR9 (`severity: high`).",
              "break_ledger_severity_unknown_id")
    return "RR9 is not in the risk register"


def break_ledger_none_found_over_high(root: Path) -> str:
    """The register gains a high entry; the snapshot still says none found."""
    swap_once(root, DOSSIER, "| RR1 | Authority over awards asserted, not evidenced | unknown | — |",
              "| RR1 | Authority over awards asserted, not evidenced | unknown | high |",
              "break_ledger_none_found_over_high")
    return "says \"none found\" while the register has"


def break_ledger_gate_wrong_fit(root: Path) -> str:
    swap_once(root, DOSSIER, "none failed (R1 `direct`, R9 `direct`)", "none failed (R1 `direct`, R9 `adjacent`)",
              "break_ledger_gate_wrong_fit")
    return "the hard-gates line gives R9 `adjacent`; the map says direct"


def _refit_row(root: Path, rid: str, old_fit: str, new_fit: str, ledger_old: str, ledger_new: str,
               gates_old: str | None = None, gates_new: str | None = None) -> None:
    """Move one row to another fit everywhere the worked dossier states it — the map's
    Fit cell, the envelope's fit_status, the ledger and, for a gate, the hard-gates
    line — so the only rule left broken is the one the mutation names."""
    envelope = root / ENVELOPE
    env = envelope.read_text()
    key = f'"requirement_id": "{rid}",'
    head, _, tail = env.partition(key)  # the evidence_map entry comes first
    if f'"fit_status": "{old_fit}"' not in tail.split("},\n      {")[0]:
        raise SystemExit(f"_refit_row: the envelope's {rid} is not {old_fit} — it has gone stale")
    envelope.write_text(head + key + tail.replace(f'"fit_status": "{old_fit}"', f'"fit_status": "{new_fit}"', 1))
    path = root / DOSSIER
    text = path.read_text()
    row = next(line for line in text.splitlines() if line.startswith(f"| {rid} |"))
    if f"| {old_fit} |" not in row:
        raise SystemExit(f"_refit_row: {rid} is not {old_fit} — it has gone stale")
    text = text.replace(row, row.replace(f"| {old_fit} |", f"| {new_fit} |", 1))
    for old, new in ((ledger_old, ledger_new), (gates_old, gates_new)):
        if old is None:
            continue
        if text.count(old) != 1:
            raise SystemExit(f"_refit_row expected one {old!r} — it has gone stale")
        text = text.replace(old, new)
    path.write_text(text)


def break_ledger_gate_adjacent(root: Path) -> str:
    """A gate row at `adjacent`, consistent everywhere: rule 4's line would file it as met."""
    _refit_row(root, "R9", "direct", "adjacent",
               "- `hard_gate` — direct: R1, R9 · unclear: R8",
               "- `hard_gate` — direct: R1 · adjacent: R9 (Start date no earlier than February 2027) · unclear: R8",
               "none failed (R1 `direct`, R9 `direct`)", "none failed (R1 `direct`, R9 `adjacent`)")
    return "R9 is a hard_gate row at `adjacent`"


def break_ledger_gate_absent(root: Path) -> str:
    """A gate row at `absent`: a gate nothing settles is unclear, one the candidate lacks is failed."""
    _refit_row(root, "R9", "direct", "absent",
               "- `hard_gate` — direct: R1, R9 · unclear: R8 (Permanent contract, not fixed-term)",
               "- `hard_gate` — direct: R1 · unclear: R8 (Permanent contract, not fixed-term) · "
               "absent: R9 (Start date no earlier than February 2027)",
               "none failed (R1 `direct`, R9 `direct`)", "none failed (R1 `direct`, R9 `absent`)")
    return "R9 is a hard_gate row at `absent`"


def break_ledger_fail_off_gate(root: Path) -> str:
    """`hard_gate_fail` on a must_have row: a failed gate the hard-gates line never reads."""
    _refit_row(root, "R4", "adjacent", "hard_gate_fail",
               "adjacent: R4 (Community energy knowledge)", "hard_gate_fail: R4 (Community energy knowledge)")
    return "R4 is a must_have row at `hard_gate_fail`"


def break_ledger_constraints_clause(root: Path) -> str:
    """The envelope says the constraints were not given; the gates line does not say so."""
    swap_once(root, ENVELOPE, '"candidate_constraints": {\n      "status": "known",',
              '"candidate_constraints": {\n      "status": "unknown",', "break_ledger_constraints_clause")
    return "the candidate's constraints were not given"


def break_quantifier_drift_rule(root: Path) -> str:
    """The rule's list gains a word the shared set does not hold (D6)."""
    swap_once(root, "skills/job-underwriter/references/evidence-model.md", '"each of", ', '"each of", "most", ',
              "break_quantifier_drift_rule")
    return "ci/ledger_rules.py lacks ['most'] from evidence-model.md's named-set words"


def break_quantifier_drift_grader(root: Path) -> str:
    """A grader clause drops a word of the list."""
    path = root / "skills/job-underwriter/evals/evals.json"
    data = json.loads(path.read_text())
    old = data["clauses"]["ledger_counts"]
    data["clauses"]["ledger_counts"] = old.replace("'neither', ", "")
    if data["clauses"]["ledger_counts"] == old:
        raise SystemExit("break_quantifier_drift_grader has gone stale")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return "lists quantifiers without ['neither']"


def break_quantifier_drift_grader_extra_complement(root: Path) -> str:
    """A grader clause lists a complement the rule does not (round 9)."""
    clause_swap(root, JU, "ledger_counts", "'all but', 'all except')", "'all but', 'all except', 'every other')",
                 "break_quantifier_drift_grader_extra_complement")
    return "lists ['every other'] among the complements, which evidence-model.md's list does not"


def break_quantifier_drift_grader_extra_named(root: Path) -> str:
    """A grader clause lists a named-set word the rule does not (round 9)."""
    clause_swap(root, JU, "ledger_counts", "'only', 'the one')", "'only', 'the one', 'just')",
                 "break_quantifier_drift_grader_extra_named")
    return "lists ['just'] among the named-set words, which evidence-model.md's list does not"


def keep_ledger_only_adverb(root: Path) -> None:
    """"only" qualifying one row, outside the sentence after the ledger, is no quantifier."""
    swap_once(root, DOSSIER, "One entry runs the other way", "R4 is only adjacent. One entry runs the other way",
              "keep_ledger_only_adverb")


def keep_ledger_only_adverb_unnamed(root: Path) -> None:
    """"only" qualifying evidence before a map word, with no row ID in the sentence: a
    pin that fails if bare "only" is read anywhere (round 9)."""
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "Some of the CV is only adjacent evidence. " + SNAPSHOT_PROSE,
              "keep_ledger_only_adverb_unnamed")


# Round 5: one count reader (N4), plural gates and gaps and the map's predicates
# (N1), "no other" over the map anywhere (N5), and one item grammar (FX-N4), each
# held in CI on the worked dossier as the harness holds it on runs.

SNAPSHOT_PROSE = "One entry runs the other way"


def break_ledger_plural_gates(root: Path) -> str:
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "Both gates hold. " + SNAPSHOT_PROSE, "break_ledger_plural_gates")
    return "the snapshot's prose: \"Both gates\""


def break_ledger_gate_predicate(root: Path) -> str:
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "Every gate passes. " + SNAPSHOT_PROSE, "break_ledger_gate_predicate")
    return "the snapshot's prose: \"Every gate\""


def break_ledger_fit_noun(root: Path) -> str:
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "Five direct fits back it. " + SNAPSHOT_PROSE, "break_ledger_fit_noun")
    return "the snapshot's prose: \"Five direct\""


def break_ledger_ratio_alone(root: Path) -> str:
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "Fit: 4 of 7 met. " + SNAPSHOT_PROSE, "break_ledger_ratio_alone")
    return "the snapshot's prose: \"4 of 7\""


def break_ledger_no_other(root: Path) -> str:
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "R8 is the open gate; no other gate is in doubt. " + SNAPSHOT_PROSE,
              "break_ledger_no_other")
    return "the snapshot's prose: \"no other gate\""


def keep_ledger_ratio_of_other_noun(root: Path) -> None:
    """A ratio followed by a noun that is not the map's counts that noun."""
    swap_once(root, DOSSIER, SNAPSHOT_PROSE,
              "The post is one of two openings, with a 24/7 on-call rota (RR3). " + SNAPSHOT_PROSE,
              "keep_ledger_ratio_of_other_noun")


def keep_summary_ratio_of_other_noun(root: Path) -> None:
    """decision.summary is read by the same reader as the snapshot (N4)."""
    swap_once(root, ENVELOPE, '"summary": "Fit as evidence_map reads it,',
              '"summary": "One of two openings, with a 24/7 on-call rota. Fit as evidence_map reads it,',
              "keep_summary_ratio_of_other_noun")


# Round 6: a ratio counts rows when it ends its clause, read by its own test rather
# than the map-word one (C5-1); a singular gate or gap and the adjectives are map
# words except before a listed ordinary head (N1). Both directions are held here.

def break_summary_ratio_predicate(root: Path) -> str:
    """A ratio whose clause ends in a predicate the old follower list lacked."""
    swap_once(root, ENVELOPE, '"summary": "Fit as evidence_map reads it,',
              '"summary": "Conditional go: 5 of 7 covered. Fit as evidence_map reads it,',
              "break_summary_ratio_predicate")
    return "decision.summary: \"5 of 7\" is a set claim over the map that names no row"


def break_after_ledger_fraction(root: Path) -> str:
    """After the ledger "N of M" is a set claim in every form, "four out of seven" included."""
    swap_once(root, DOSSIER, AFTER_LEDGER, "The fit leaves four out of seven covered.", "break_after_ledger_fraction")
    return "the sentence after the fit ledger: \"four out of seven\" is a set claim over the map that names no row"


def break_after_ledger_slash(root: Path) -> str:
    swap_once(root, DOSSIER, AFTER_LEDGER, "The fit sits at 5/7 covered.", "break_after_ledger_slash")
    return "the sentence after the fit ledger: \"5/7\" is a set claim over the map that names no row"


def keep_after_ledger_ratios_named(root: Path) -> None:
    """GRADER: the same ratios in the sentence that names R4 and R3: read as counts of
    rows, they name a row and pass the check; N and M are the grader's (the comment above Claim in ci/ledger_rules.py)."""
    swap_once(root, DOSSIER, "R4 — a credible bridge, its limit named;",
              "R4 — a credible bridge, its limit named, leaving four out of seven covered, fit at 5/7;",
              "keep_after_ledger_ratios_named")


def break_ledger_gate_unlisted_verb(root: Path) -> str:
    """A singular gate before a verb no list names is still the map's gate."""
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "Every gate checks out. " + SNAPSHOT_PROSE,
              "break_ledger_gate_unlisted_verb")
    return "the snapshot's prose: \"Every gate\""


def break_ledger_direct_unlisted_noun(root: Path) -> str:
    """"direct" before a noun that is not one of its ordinary heads is the fit."""
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "Two direct hits back it. " + SNAPSHOT_PROSE,
              "break_ledger_direct_unlisted_noun")
    return "the snapshot's prose: \"Two direct\""


def keep_ledger_direct_unlisted_noun_named(root: Path) -> None:
    """GRADER: the same count naming its rows passes the check; whether two is the
    map's number of `direct` rows is the grader's (the comment above Claim in ci/ledger_rules.py)."""
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "Two direct hits: R2 and R3. " + SNAPSHOT_PROSE,
              "keep_ledger_direct_unlisted_noun_named")


def keep_ledger_candidate_ratio(root: Path) -> None:
    """The candidate's own figures and a date are not counts of rows (C5-1)."""
    swap_once(root, DOSSIER, SNAPSHOT_PROSE,
              "He ranked 1 of 40 in the cohort and was 2 of 3 on the panel; the start date 3/15 is fixed (RR1). "
              + SNAPSHOT_PROSE, "keep_ledger_candidate_ratio")


def break_years_stray_negation(root: Path) -> str:
    """A negation that governs neither "hard gate" nor "years" exempts nothing (C5-2)."""
    swap_once(root, "skills/job-underwriter/SKILL.md", "hard gates (authorization, license, location, schedule, pay,",
              "hard gates — never bridged — (authorization, license, location, schedule, pay, travel, years,",
              "break_years_stray_negation")
    return "years listed as a hard gate is the retired gate list"


def break_years_negated_elsewhere(root: Path) -> str:
    swap_once(root, EVIDENCE_MODEL, "\n- **The row is the unit",
              "\n- Hard gates, never bridged, are authorization, licence, location, pay and years of experience.\n"
              "- A hard gate isn't a fit question; list authorization, location, pay and years.\n"
              "- **The row is the unit", "break_years_negated_elsewhere")
    return "years listed as a hard gate is the retired gate list"


def break_years_second_gate_list(root: Path) -> str:
    """One negated "hard gate" does not cover a second, unnegated one in the sentence."""
    swap_once(root, EVIDENCE_MODEL, "\n- **The row is the unit",
              "\n- R1 is not a hard gate; hard gates are authorization, pay and years.\n"
              "- **The row is the unit", "break_years_second_gate_list")
    return "years listed as a hard gate is the retired gate list"


def keep_ledger_nested_name(root: Path) -> None:
    """A ledger item's Requirement words may hold a parenthesis: one item grammar (FX-N4)."""
    swap_once(root, DOSSIER, "adjacent: R4 (Community energy knowledge)",
              "adjacent: R4 (Community energy knowledge (generation, grid connection))", "keep_ledger_nested_name")


def break_retired_old_name(root: Path) -> str:
    """Tuesday's old working name back in the line Claude reads first."""
    swap_once(root, "skills/tuesday/SKILL.md", "Tuesday is one skill that holds three job-search modules.",
              "Tuesday is one front door to three job-search modules.", "break_retired_old_name")
    return "skills/tuesday/SKILL.md: \"front door\" is Tuesday's retired working name"


def break_retired_old_name_hyphenated(root: Path) -> str:
    """The same name hyphenated, in a module's README."""
    path = root / "skills/resume-tailor/README.md"
    path.write_text(path.read_text() + "\nIt also runs through the front-door skill.\n")
    return "skills/resume-tailor/README.md: \"front door\" is Tuesday's retired working name"


def keep_old_name_identifier(root: Path) -> None:
    """The one-word identifiers are commands and constants, renamed apart, and pass."""
    path = root / "skills/tuesday/README.md"
    path.write_text(path.read_text() + "\nIts routing runs with `run_routing.py --arm frontdoor`.\n")


def keep_years_negated_gate(root: Path) -> None:
    """The rule that retired years as a gate, stated as a negation, is not the retired list (N6)."""
    swap_once(root, "skills/job-underwriter/SKILL.md", "terms, never a length of experience",
              "terms, never years of experience", "keep_years_negated_gate")
    swap_once(root, EVIDENCE_MODEL, "\n- **The row is the unit",
              "\n- Here R1 is not a hard gate: five years of sales experience keeps the tier the posting gives it, read on the fit scale.\n"
              "- **The row is the unit", "keep_years_negated_gate")


def keep_budget_grounds_reversed(root: Path) -> None:
    """The amended accounting rule with its two grounds in the other order (N6)."""
    clause_swap(root, JU, "accounting",
                "right only when the user chose L0 or declined research (and the tally then reads L0 — no searches), "
                "or when the search budget was fully spent and every search went to a lower-numbered "
                "(higher-priority) target",
                "right only when the search budget was fully spent and every search went to a lower-numbered "
                "(higher-priority) target, or when the user chose L0 or declined research (and the tally then "
                "reads L0 — no searches)", "keep_budget_grounds_reversed")


def keep_ledger_figure_with_unit(root: Path) -> None:
    """The candidate's own figures are not counts of rows, beside a map word or not."""
    swap_once(root, DOSSIER, "One entry runs the other way",
              "The candidate's 9 years clear an 8+ requirement. One entry runs the other way",
              "keep_ledger_figure_with_unit")


# The answer-key check, read as runs of words rather than whole quotes (N6, F10, N9).

RUBRIC = "skills/mock-interview/references/question-rubric.md"
RUBRIC_EXAMPLE = '`[grounded] "Ran the small-grants round for three years"`'


def break_answer_key_near_quote(root: Path) -> str:
    """The mi 2 sentence with one word changed: an exact-substring test passed it."""
    swap_once(root, RUBRIC, RUBRIC_EXAMPLE, '`[grounded] "ran the site\'s peak-season surge plan for two years"`',
              "break_answer_key_near_quote")
    return "quoted from this skill's own fixtures"


def break_answer_key_single_quotes(root: Path) -> str:
    swap_once(root, RUBRIC, RUBRIC_EXAMPLE, "`[grounded]` 'ran the site's peak-season surge plan two years running'",
              "break_answer_key_single_quotes")
    return "quoted from this skill's own fixtures"


def break_answer_key_reframing(root: Path) -> str:
    """The reframing audit's old ambiguity example, a near-quote of job-underwriter eval 3."""
    path = root / "skills/job-underwriter/references/reframing-audit.md"
    path.write_text(path.read_text() + '\n\nFor example, "growth lead, then Head of Growth, at two companies" '
                                       'is one tenure or two.\n')
    return "quoted from this skill's own fixtures"


def break_answer_key_unquoted(root: Path) -> str:
    """Eight words of a fixture's prompt pasted into rule prose with no quotation marks."""
    path = root / RUBRIC
    path.write_text(path.read_text() + "\n\nA candidate who cut mis-pick rate 40% by redesigning the pick path "
                                       "is a good case.\n")
    return "repeats this skill's own fixtures unquoted"


def break_answer_key_canned_page(root: Path) -> str:
    """A canned research page is shown to the model too (mi 7's values page)."""
    swap_once(root, RUBRIC, RUBRIC_EXAMPLE,
              '`[grounded] "when the calendar and the players disagree, the players win"`',
              "break_answer_key_canned_page")
    return "page https://saltmarshgames.com/values"


def keep_answer_key_common_phrase(root: Path) -> None:
    """A common phrase of rule prose shares too few words with any fixture to fail."""
    path = root / RUBRIC
    path.write_text(path.read_text() + '\n\nA question such as "how do you set priorities each week" is generic.\n')


def keep_answer_key_contract(root: Path) -> None:
    """The shared contract's own wording, which a dossier fixture repeats by design."""
    path = root / "skills/mock-interview/references/dossier-handoff.md"
    path.write_text(path.read_text() + '\n\nIts caveat reads "confirmed, limited inspectable proof — expect a probe".\n')


# Fixture fields the harness reads (D5).

JU = "skills/job-underwriter/evals/evals.json"
MI = "skills/mock-interview/evals/evals.json"


def mutate_case(root: Path, rel: str, case_id: int, change) -> None:
    path = root / rel
    data = json.loads(path.read_text())
    change(next(c for c in data["evals"] if c["id"] == case_id))
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def break_canary_page_typo(root: Path) -> str:
    """A canary whose page matches no page is never asked for: a check that passes in every run."""
    mutate_case(root, JU, 4, lambda c: c["research"]["canaries"][0].update(page="https://brindlemoor.co.uk/abuot"))
    return "the canary for target 1 names https://brindlemoor.co.uk/abuot"


def break_canary_other_target(root: Path) -> str:
    mutate_case(root, JU, 4, lambda c: c["research"]["canaries"][0].update(
        page="https://pricewell.example/2026-uk-pricing-analytics-pay-survey"))
    return "is not exactly one of this fixture's pages for target 1"


def break_canary_no_page(root: Path) -> str:
    mutate_case(root, MI, 7, lambda c: c["research"]["canaries"][0].pop("page"))
    return "names no page"


def break_canary_spelling(root: Path) -> str:
    mutate_case(root, JU, 4, lambda c: c["research"]["canaries"][0].update(text=["4,000 employees"]))
    return "no spelling of the canary for target 1 is in its page"


def break_candidate_text_drift(root: Path) -> str:
    mutate_case(root, MI, 2, lambda c: c["candidate_text"].__setitem__(0, c["candidate_text"][0] + " and more"))
    return "is not in the prompt"


def break_candidate_text_missing(root: Path) -> str:
    mutate_case(root, MI, 3, lambda c: c.pop("candidate_text"))
    return "declares no candidate_text list"


RT = "skills/resume-tailor/evals/evals.json"


def break_date_anchor_missing(root: Path) -> str:
    """Relative dates with no anchor: a run saved before run dates were recorded has no text to be graded on."""
    mutate_case(root, MI, 8, lambda c: c.pop("date_anchor"))
    return "declares no date_anchor as an ISO date"


def break_date_anchor_not_iso(root: Path) -> str:
    mutate_case(root, MI, 8, lambda c: c.update(date_anchor="12 October 2026"))
    return "declares no date_anchor as an ISO date"


def break_date_anchor_unused(root: Path) -> str:
    """An anchor on a fixture that writes no relative date: a key that does nothing."""
    mutate_case(root, JU, 1, lambda c: c.update(date_anchor="2026-10-12"))
    return "declares a date_anchor and writes no date relative to the run"


def break_date_ref_malformed(root: Path) -> str:
    """A reference the pattern cannot read would reach the room, and the grader, as braces."""
    mutate_case(root, MI, 8, lambda c: c.update(prompt=c["prompt"].replace("{{date+9d:day month}}", "{{date+9w:day month}}")))
    return "a date reference the loader cannot read"


def keep_date_in_expectation(root: Path) -> None:
    """A relative date in an expectation is written out at the anchor, never read as a clause's braces."""
    mutate_case(root, MI, 8, lambda c: c["expectations"].__setitem__(
        3, c["expectations"][3] + " The rounds are on {{date+9d:day month}}."))


def keep_canary_spelled_as_dated_page(root: Path) -> None:
    """A canary found in its page only once the page's relative date is written out at the anchor."""
    mutate_case(root, MI, 7, lambda c: c["research"]["canaries"][2].update(text=["August 2026"]))


def break_traces_candidate_text_missing(root: Path) -> str:
    """A traces fixture with no candidate_text: every Traces to quotation would go unchecked."""
    mutate_case(root, RT, 2, lambda c: c.pop("candidate_text"))
    return "runs the traces check and declares no candidate_text list"


def break_traces_candidate_text_drift(root: Path) -> str:
    mutate_case(root, RT, 4, lambda c: c["candidate_text"].__setitem__(0, c["candidate_text"][0] + " and more"))
    return "is not in the prompt"


def break_term_collision(root: Path) -> str:
    """RV3's shape: an n/a target's term matches another target's natural query."""
    mutate_case(root, MI, 3, lambda c: c["research"]["targets"][3]["terms"].append("the interviewer"))
    return "its terms match target 2's sample"


def break_hunt_vacuous(root: Path) -> str:
    mutate_case(root, MI, 3, lambda c: c["research"]["targets"][3].update(terms=["zzz"]))
    return "match none of its own hunt_samples"


def break_sample_unaimed(root: Path) -> str:
    mutate_case(root, MI, 3, lambda c: c["research"]["targets"][2]["on_target_samples"].append("Stripe in 2026"))
    return "is aimed at no term of it"


def break_hunt_samples_missing(root: Path) -> str:
    mutate_case(root, MI, 3, lambda c: c["research"]["targets"][3].pop("hunt_samples"))
    return "has no hunt_samples"


def break_identity_absent_name(root: Path) -> str:
    """Audit A: an identity name the prompt never uses would claim no search."""
    mutate_case(root, JU, 4, lambda c: c["research"]["targets"][0].update(identity=["zephyrine"]))
    return "identity name 'zephyrine' of target 1 is not in the prompt"


def break_identity_is_term(root: Path) -> str:
    """Audit A: the company's name as a term would aim every query at that target."""
    mutate_case(root, JU, 4, lambda c: c["research"]["targets"][0]["terms"].append("brindlemoor"))
    return "identity name 'brindlemoor' is a target's term"


def break_identity_untested(root: Path) -> str:
    mutate_case(root, MI, 5, lambda c: c["research"].update(stray_samples=["partnerships manager salary market UK"]))
    return "declares identity and no stray_samples query carries the name"


def break_identity_twice(root: Path) -> str:
    mutate_case(root, MI, 7, lambda c: c["research"]["targets"][0].update(identity=["saltmarsh"]))
    return "more than one target declares identity"


def break_stray_sample_aimed(root: Path) -> str:
    """Audit A/D/E: a query no target serves must stay a stray in every room."""
    mutate_case(root, MI, 8, lambda c: c["research"]["stray_samples"].append(
        "credit union complaints handling regulatory requirements"))
    mutate_case(root, MI, 8, lambda c: c["research"]["targets"][4]["terms"].append("requirements"))
    return "stray sample 'credit union complaints handling regulatory requirements' is aimed at target(s) [5]"


def break_constraints_missing(root: Path) -> str:
    """NP-8: a fit_ledger fixture with no candidate_constraints left the run's envelope to decide."""
    mutate_case(root, JU, 1, lambda c: c.pop("candidate_constraints"))
    return "job-underwriter eval 1: runs the fit_ledger check and declares candidate_constraints None"


def break_constraints_misspelt(root: Path) -> str:
    mutate_case(root, JU, 3, lambda c: c.update(candidate_constraints="Unknown"))
    return "declares candidate_constraints 'Unknown', not exactly"


PAGES = "yes_names_page"
PAGES_RULE = "Every `yes` row names the queries and pages"


def break_pages_check_dropped(root: Path) -> str:
    """A research fixture of a skill stating the rule that does not run the check: its pages go unjudged."""
    mutate_case(root, JU, 4, lambda c: c["checks"].remove(PAGES))
    return "job-underwriter eval 4: SKILL.md states that every `yes` row names its pages and this fixture does not run"


def break_pages_check_unstated(root: Path) -> str:
    """mock-interview states no page-naming rule; running the check there judges one it never gave."""
    mutate_case(root, MI, 7, lambda c: c["checks"].append(PAGES))
    return "mock-interview eval 7: runs the yes_names_page check, and SKILL.md does not state"


def break_pages_check_without_research(root: Path) -> str:
    mutate_case(root, JU, 2, lambda c: c["checks"].append(PAGES))
    return "job-underwriter eval 2: runs the yes_names_page check with no research block"


def break_pages_rule_reworded(root: Path) -> str:
    """The sentence reworded away: every fixture still running the check now judges an unstated rule."""
    swap_once(root, "skills/job-underwriter/SKILL.md", PAGES_RULE, "Every `yes` row names the queries",
              "break_pages_rule_reworded")
    return "job-underwriter eval 6: runs the yes_names_page check, and SKILL.md does not state"


def break_pages_rule_formless(root: Path) -> str:
    """The rule kept but its form dropped: the check reads a page as named only by title or
    address, so a skill that does not say so would be judged on a reading it never gave."""
    swap_once(root, "skills/job-underwriter/SKILL.md", "it rests on, each page by its title or address.",
              "it rests on.", "break_pages_rule_formless")
    return "job-underwriter eval 6: runs the yes_names_page check, and SKILL.md does not state"


def keep_pages_rule_rewrapped(root: Path) -> None:
    """The rule's sentence hard-wrapped at another word is the same sentence."""
    swap_once(root, "skills/job-underwriter/SKILL.md", PAGES_RULE, "Every `yes` row names the\nqueries and pages",
              "keep_pages_rule_rewrapped")


DECLINE = "Please don't look anything up — work from what I've given you."


def decline(case: dict, phrase: str | None = DECLINE, prompt: bool = True) -> None:
    case["research"]["declined"] = True
    if phrase is not None:
        case["research"]["declined_phrase"] = phrase
    if prompt:
        case["prompt"] += " " + DECLINE


def break_declined_not_bool(root: Path) -> str:
    mutate_case(root, MI, 3, lambda c: c["research"].update(declined="yes"))
    return "research.declined is 'yes', not true or false"


def break_declined_and_zero_calls(root: Path) -> str:
    mutate_case(root, JU, 5, decline)
    return "declares both research.declined and zero_calls"


def break_declined_no_phrase(root: Path) -> str:
    mutate_case(root, MI, 3, lambda c: decline(c, phrase=None))
    return "declares research.declined and no declined_phrase"


def break_declined_phrase_absent(root: Path) -> str:
    """HN3: declined set on a prompt that does not decline lets lazy no-call rows pass."""
    mutate_case(root, MI, 3, lambda c: decline(c, prompt=False))
    return "is not in the prompt — a fixture whose user did not decline research"


def break_declined_phrase_stray(root: Path) -> str:
    mutate_case(root, MI, 3, lambda c: c["research"].update(declined_phrase=DECLINE))
    return "declares a declined_phrase without research.declined: true"


def keep_declined_fixture(root: Path) -> None:
    """A fixture whose user declines research, said in the prompt and declared."""
    mutate_case(root, MI, 3, decline)


def break_user_link_is_page(root: Path) -> str:
    """RV4: a declared user link that is a research page, written another way."""
    page = "https://www.brindlemoor.co.uk/careers/senior-pricing-analyst/"
    mutate_case(root, JU, 4, lambda c: c["research"].update(user_links=[page]))
    return f"user link {page} is also a research page"


def break_user_link_is_canary_page(root: Path) -> str:
    def change(c):
        c["research"]["canaries"][0].update(page="https://brindlemoor.co.uk/abuot")
        c["research"]["user_links"] = ["https://brindlemoor.co.uk/abuot"]
    mutate_case(root, JU, 4, change)
    return "user link https://brindlemoor.co.uk/abuot is a canary's page"


def break_user_links_not_list(root: Path) -> str:
    mutate_case(root, MI, 7, lambda c: c["research"].update(user_links="https://example.com/jd"))
    return "research.user_links is str, not a list"


# Job-underwriter eval 6: a posting the user linked, which the canned room serves
# from `research.user_pages` by fetch alone.
JU6_LINK = "https://jobs.tallyboard.example/quillfield/revenue-operations-lead-2291"


def break_user_link_no_page(root: Path) -> str:
    """A canned room answers "No page at" a link it serves nothing for, which returns:
    the run would be credited with reading a page it never saw."""
    mutate_case(root, JU, 6, lambda c: c["research"].pop("user_pages"))
    return f"user link {JU6_LINK} has no page in research.user_pages"


def break_user_page_undeclared(root: Path) -> str:
    """A served page that is no declared link: its read would be counted as research."""
    other = "https://jobs.tallyboard.example/quillfield/revenue-operations-lead-2292"
    mutate_case(root, JU, 6, lambda c: c["research"]["user_pages"][0].update(url=other))
    return f"user page {other} is not one of research.user_links"


def break_user_page_canary_off_page(root: Path) -> str:
    mutate_case(root, JU, 6, lambda c: c["research"]["user_pages"][0].update(canary=["59,000"]))
    return f"no spelling of the canary of user link {JU6_LINK} is on its page"


def break_user_page_canary_on_research_page(root: Path) -> str:
    """A fact a research page also carries proves nothing about the user's link."""
    mutate_case(root, JU, 6, lambda c: c["research"]["user_pages"][0].update(canary=["Bristol"]))
    return "is also in page https://quillfield.co.uk/about"


def break_user_page_canary_in_prompt(root: Path) -> str:
    mutate_case(root, JU, 6, lambda c: c["research"]["user_pages"][0].update(canary=["Salesforce"]))
    return f"the canary of user link {JU6_LINK} ('Salesforce') is also in the prompt"


def break_user_pages_not_list(root: Path) -> str:
    mutate_case(root, JU, 6, lambda c: c["research"].update(user_pages=c["research"]["user_pages"][0]))
    return "research.user_pages is dict, not a list"


def break_answer_key_user_page(root: Path) -> str:
    """The page at a user's link is shown to the model too, so quoting it is an answer key."""
    path = root / "skills/job-underwriter/references/evidence-model.md"
    path.write_text(path.read_text() + '\n\nA posting may say "own our CRM and billing data" and nothing more.\n')
    return f"page {JU6_LINK}"


def keep_user_link_written_another_way(root: Path) -> None:
    """The declared link with a trailing slash is the same link (norm_url): it still has its page."""
    mutate_case(root, JU, 6, lambda c: c["research"].update(user_links=[JU6_LINK + "/"]))


def break_collision_canned_page(root: Path) -> str:
    """NP-4: a skipped target's page shares a keyword with another target's sample, so
    in a canned room the server returns it and the call is aimed at the skipped target."""
    mutate_case(root, MI, 7, lambda c: c["research"]["pages"].append({
        "url": "https://saltmarshgames.com/careers/live-operations-producer", "target": 5,
        "title": "Live Operations Producer", "keywords": ["careers", "interview"],
        "text": "The posting for the live operations producer role."}))
    return "in a canned room target 2's sample 'Saltmarsh Games interview process' returns its page"


# A quick check of the user's material (`research.quick_check`): one mutation per rule of the
# fixtures group, and the three declaring fixtures written another lawful way.

def break_quick_check_undeclared_target(root: Path) -> str:
    mutate_case(root, JU, 5, lambda c: c["research"]["quick_check"]["targets"].append(4))
    return "job-underwriter eval 5: quick-check target 4 is not one of this fixture's targets"


def break_quick_check_target_not_skipped(root: Path) -> str:
    """A target the material does not fix: its own research is expected, so a check is no check."""
    mutate_case(root, MI, 7, lambda c: c["research"]["quick_check"]["targets"].append(1))
    return "mock-interview eval 7: quick-check target 1 accepts ['yes'] in a canned room, not skipped alone"


def break_quick_check_no_names(root: Path) -> str:
    mutate_case(root, JU, 5, lambda c: c["research"]["quick_check"].update(names=[]))
    return "job-underwriter eval 5: research.quick_check names nothing"


def break_quick_check_name_absent(root: Path) -> str:
    mutate_case(root, MI, 8, lambda c: c["research"]["quick_check"]["names"].append("kelverton"))
    return "mock-interview eval 8: quick-check name 'kelverton' is not in the prompt"


def break_quick_check_declined(root: Path) -> str:
    mutate_case(root, MI, 7, decline)
    return "mock-interview eval 7: declares a quick check beside research.declined"


def break_quick_check_over_budget(root: Path) -> str:
    mutate_case(root, JU, 5, lambda c: c["research"]["budget"].update(searches=1))
    return "job-underwriter eval 5: a quick check may send 2 calls (output_checks.QUICK_CHECK_CALLS), above this " \
           "fixture's search budget of 1"


def break_quick_check_sample_outside(root: Path) -> str:
    """A correct check of the company that a target outside the declaration also claims would fail
    its n/a row: the collision check, skipped where zero_calls holds, still reads this one."""
    mutate_case(root, JU, 5, lambda c: c["research"]["targets"][0]["on_target_samples"].append(
        "Pellucid Learning careers head of data"))
    return "quick-check target 1's sample 'Pellucid Learning careers head of data' is aimed at target(s) [3] outside"


def break_quick_check_hunt_passes(root: Path) -> str:
    """A hunt for the hiring manager the request does not name, read as a check of the company: with
    no term of its own target, it is a search for Pellucid in the request's own words."""
    def drop(c):
        target = next(t for t in c["research"]["targets"] if t["n"] == 3)
        target["terms"] = [t for t in target["terms"] if t not in ("hiring manager", "hiring managers")]
    mutate_case(root, JU, 5, drop)
    return "job-underwriter eval 5: target 3's sample 'Pellucid Learning hiring manager' passes as a quick check"


def break_quick_check_clause_number(root: Path) -> str:
    swap_once(root, JU, "at most two calls", "at most three calls", "break_quick_check_clause_number")
    return "job-underwriter evals.json clause quick_check allows at most three calls, and the checks allow 2"


def break_quick_check_grammar_number(root: Path) -> str:
    """The text a run reads allows another number of calls than the checks."""
    swap_once(root, "conventions/interaction-grammar.md", "at most two calls", "at most three calls",
              "break_quick_check_grammar_number")
    return "interaction-grammar.md §4 allows a quick check of pasted material 3 call(s), and the checks allow 2 " \
           "(output_checks.QUICK_CHECK_CALLS)"


def keep_quick_check_names_capitalised(root: Path) -> None:
    mutate_case(root, JU, 5, lambda c: c["research"]["quick_check"].update(names=["Pellucid", "Datawright"]))


def keep_quick_check_narrowed(root: Path) -> None:
    mutate_case(root, MI, 8, lambda c: c["research"]["quick_check"].update(targets=[3]))


def keep_quick_check_name_as_written(root: Path) -> None:
    mutate_case(root, MI, 7, lambda c: c["research"]["quick_check"].update(names=["Saltmarsh Games"]))


# Retired wording and rewritten rules (NEW-RV-C, RV14, NEW-RV-I, MI-7).

def break_retired_returned_something(root: Path) -> str:
    path = root / JU
    data = json.loads(path.read_text())
    old = data["clauses"]["accounting"]
    data["clauses"]["accounting"] = old.replace("returned a result (an empty or unattributable one included)",
                                                "returned something")
    if data["clauses"]["accounting"] == old:
        raise SystemExit("break_retired_returned_something has gone stale")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return "\"returned something\" is the retired accounting wording"


def break_retired_refused_only(root: Path) -> str:
    swap_once(root, "skills/mock-interview/references/output-template.md", "if every call was refused or errored",
              "if every call was refused", "break_retired_refused_only")
    return "without \"or errored\" is the retired accounting wording"


def break_retired_budget_ground(root: Path) -> str:
    path = root / JU
    data = json.loads(path.read_text())
    old = data["clauses"]["accounting"]
    data["clauses"]["accounting"] = old.replace(
        "right only when the user chose L0 or declined research (and the tally then reads L0 — no searches), or "
        "when the search budget was fully spent", "lawful in a canned room only when the fixture's search budget "
        "was fully spent")
    if data["clauses"]["accounting"] == old:
        raise SystemExit("break_retired_budget_ground has gone stale")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return "is the retired accounting ground"


def break_retired_user_links_refused(root: Path) -> str:
    path = root / JU
    data = json.loads(path.read_text())
    old = data["clauses"]["accounting_counts"]
    data["clauses"]["accounting_counts"] = old.replace("as user links read only where a read of it returned",
                                                       "as user links read, refused ones included")
    if data["clauses"]["accounting_counts"] == old:
        raise SystemExit("break_retired_user_links_refused has gone stale")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return "is the retired tally"


def break_retired_gates_plainly(root: Path) -> str:
    swap_once(root, "skills/job-underwriter/references/risk-and-decision.md",
              "the `hard_gate_fail` rows first, after `failed:`",
              "the `hard_gate_fail` rows first, plainly, after `failed:`", "break_retired_gates_plainly")
    return "is the retired hard-gates wording"


def break_retired_slot_with_gates(root: Path) -> str:
    swap_once(root, "evals/README.md", "whether or not the map has gate", "only when the map has gate",
              "break_retired_slot_with_gates")
    return "required only with gate rows is the retired rule"


def break_retired_years_gate(root: Path) -> str:
    swap_once(root, "skills/job-underwriter/SKILL.md", "location, schedule, pay,", "location, schedule, years, pay,",
              "break_retired_years_gate")
    return "years listed as a hard gate is the retired gate list"


def break_labels_without_result(root: Path) -> str:
    path = root / MI
    data = json.loads(path.read_text())
    old = data["clauses"]["accounting"]
    data["clauses"]["accounting"] = old.replace("returned a result", "came back", 1)
    if data["clauses"]["accounting"] == old:
        raise SystemExit("break_labels_without_result has gone stale")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return "defines the yes/unavailable labels without \"returned a result\""


def break_l0_no_network(root: Path) -> str:
    swap_once(root, "skills/mock-interview/references/research-checklist.md", "L0 sends no search",
              "No network. L0 sends no search", "break_l0_no_network")
    return "an L0 definition says \"no network\""


def break_personas_premap(root: Path) -> str:
    path = root / "skills/mock-interview/references/personas.md"
    path.write_text(path.read_text().replace("### 1. The Data-Driven Prober",
                                             "- Pre-map one story per stem before the round.\n\n### 1. The Data-Driven Prober", 1))
    return "maps a story with no quoted sentence behind it"


def break_personas_scope_line(root: Path) -> str:
    path = root / "skills/mock-interview/references/personas.md"
    text = path.read_text()
    line = next(l for l in text.splitlines() if "quote-or-slot" in l)
    path.write_text(text.replace(line + "\n", "", 1))
    return "points its counter-strategies at the quote-or-slot rule"


def keep_no_network_elsewhere(root: Path) -> None:
    """"No network" outside an L0 definition is not the retired L0 wording."""
    swap_once(root, "skills/mock-interview/references/personas.md", "## Relationship priors",
              "An offline host has no network, which changes nothing here.\n\n## Relationship priors",
              "keep_no_network_elsewhere")


# Every declared enum names the one table that renders it (MI-11, NP-1).

FIT_SNAPSHOT_HOME = "gap_type=output-template.md#The fit snapshot/Gap type"


def break_enum_without_column(root: Path) -> str:
    swap_once(root, "skills/job-underwriter/SKILL.md", ", severity=dossier-worked-report.md#Opportunity risk register/Severity",
              "", "break_enum_without_column")
    return "enum_fields names 'severity' and enum_columns gives it no column"


def break_enum_column_missing(root: Path) -> str:
    swap_once(root, "skills/mock-interview/SKILL.md", FIT_SNAPSHOT_HOME,
              "gap_type=output-template.md#The fit snapshot/Gap kind", "break_enum_column_missing")
    return "puts 'gap_type' in 'Gap kind', which is no column of the table under 'The fit snapshot'"


def break_enum_column_stale(root: Path) -> str:
    swap_once(root, "skills/resume-tailor/SKILL.md", "row_status=edit-ledger.md#The row/Status",
              "row_status=edit-ledger.md#The row/Status, stage=edit-ledger.md#The row/Status",
              "break_enum_column_stale")
    return "maps 'stage', which enum_fields does not declare"


def drop_table_column(root: Path, rel: str, heading: str, column: str, name: str) -> None:
    """Delete one column — header, separator and every row — from the first table
    under a '## ' heading, leaving every other table of the file as it was."""
    path = root / rel
    lines = path.read_text().splitlines(keepends=True)
    at = lines.index(f"## {heading}\n")
    first = next(i for i in range(at + 1, len(lines)) if lines[i].startswith("|"))
    last = next((i for i in range(first, len(lines)) if not lines[i].startswith("|")), len(lines))
    cells = [c.strip() for c in lines[first].strip().strip("|").split("|")]
    if column not in cells:
        raise SystemExit(f"{name} found no {column!r} column under {heading!r} — it has gone stale")
    k = cells.index(column)
    for i in range(first, last):
        row = lines[i].rstrip("\n").strip().strip("|").split("|")
        del row[k]
        lines[i] = "|" + "|".join(row) + "|\n"
    path.write_text("".join(lines))


def break_enum_column_dropped(root: Path) -> str:
    """MI-11 itself: the fit snapshot loses its Gap type column, and the mirrored
    glossary's "Gap type" header used to answer for it."""
    drop_table_column(root, "skills/mock-interview/references/output-template.md", "The fit snapshot", "Gap type",
                      "break_enum_column_dropped")
    return "puts 'gap_type' in 'Gap type', which is no column of the table under 'The fit snapshot'"


def break_enum_status_dropped_from_one_table(root: Path) -> str:
    """Two enums share a header ("Status"); dropping it from the edit ledger's row
    must fail the one rendered there, though the coverage map still has a Status."""
    drop_table_column(root, "skills/resume-tailor/references/edit-ledger.md", "The row", "Status",
                      "break_enum_status_dropped_from_one_table")
    return "puts 'row_status' in 'Status', which is no column of the table under 'The row'"


def break_enum_into_mirror(root: Path) -> str:
    swap_once(root, "skills/mock-interview/SKILL.md", FIT_SNAPSHOT_HOME,
              "gap_type=evidence-conventions.md#3. Fit status and the gap taxonomy/Gap type", "break_enum_into_mirror")
    return "puts 'gap_type' in evidence-conventions.md, a mirror"


def break_enum_header_only(root: Path) -> str:
    """The old form, a header with no table: it let any same-named column answer."""
    swap_once(root, "skills/mock-interview/SKILL.md", FIT_SNAPSHOT_HOME, "gap_type=Gap type",
              "break_enum_header_only")
    return "enum_columns entry 'gap_type=Gap type' is not field=file.md#Section/Column"


def break_qualifier_in_mirror_only(root: Path) -> str:
    """A qualifier field whose only column is a mirrored glossary's."""
    swap_once(root, "skills/mock-interview/SKILL.md", "qualifier_fields: gap-and-bridge language",
              "qualifier_fields: definition", "break_qualifier_in_mirror_only")
    return "names 'definition', which is not a column in any references/ table outside the mirrors"


# Round 7's rule: a statement about a set of map rows names every row of it
# (evidence-model.md, "The row is the unit"). What the check reads of it and what it
# leaves to the grader: the comment above Claim in ci/ledger_rules.py. The measured
# sentences, each in a slot of the worked dossier. Its map: R1, R8, R9
# hard_gate (R8 `unclear`); R2, R3, R4 must_have (R4 `adjacent`); R5, R6 important
# (R5 `unclear`); R7 preferred `absent`; the rest `direct`. A keep_ marked GRADER is
# a case round 7 failed; it passes the check by the boundary stated in the comment
# above Claim, and the test pins that boundary.

VERDICT = "**Worth applying to — on the conditions below."
SUMMARY = '"summary": "Fit as evidence_map reads it,'


def break_set_unnamed_status(root: Path) -> str:
    """The status line's measured recap: true, and naming nothing."""
    swap_once(root, DOSSIER, VERDICT, "**Worth applying to — you clear every must-have directly, on the conditions below.",
              "break_set_unnamed_status")
    return "the snapshot's prose: \"every must-have\" is a set claim over the map that names no row"


def keep_set_unnamed_constraints(root: Path) -> None:
    """GRADER: measured, in the candidate's vocabulary — not a set the check reads."""
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "Both of your hard constraints hold. " + SNAPSHOT_PROSE,
              "keep_set_unnamed_constraints")


def keep_set_unnamed_gap_type(root: Path) -> None:
    """GRADER: a set by gap type written without "gap" or "gaps" is not read (the
    comment above Claim in ci/ledger_rules.py)."""
    swap_once(root, ENVELOPE, SUMMARY, '"summary": "None of them is a capability problem. Fit as evidence_map reads it,',
              "keep_set_unnamed_gap_type")


def break_set_unnamed_gap_word(root: Path) -> str:
    """The same set by gap type written with "gap": a map word, read, and unnamed."""
    swap_once(root, ENVELOPE, SUMMARY, '"summary": "None of them is a capability gap. Fit as evidence_map reads it,',
              "break_set_unnamed_gap_word")
    return 'decision.summary: "None of them is a capability gap" is a set claim over the map that names no row'


def keep_set_named_inexact(root: Path) -> None:
    """GRADER: named, and the tier has a third row (R4) the sentence leaves out."""
    swap_once(root, DOSSIER, AFTER_LEDGER, "R2 and R3 — every must-have, `direct`.", "keep_set_named_inexact")


def keep_set_named_wrong_number(root: Path) -> None:
    """GRADER: named, and two of the three must-haves are `direct`, not three."""
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "Three must-haves are `direct`: R2, R3 and R4. " + SNAPSHOT_PROSE,
              "keep_set_named_wrong_number")


def keep_set_named_v01(root: Path) -> None:
    """GRADER: the v0.1 count with rows named; the map has nine rows, and five `direct`."""
    swap_once(root, DOSSIER, AFTER_LEDGER, "R1, R2, R3 and R6 — four of the seven material requirements, `direct`.",
              "keep_set_named_v01")


def keep_set_named_unknown_row(root: Path) -> None:
    """GRADER: the map has no R12."""
    swap_once(root, DOSSIER, AFTER_LEDGER, "R4 and R12 — both wait on an artifact.", "keep_set_named_unknown_row")


def break_set_unnamed_count(root: Path) -> str:
    """The v0.1 count, its rows unnamed, in the sentence after the ledger."""
    swap_once(root, DOSSIER, AFTER_LEDGER, "Four of the seven material requirements are `direct`.",
              "break_set_unnamed_count")
    return ("the sentence after the fit ledger: \"Four of the seven material requirements\" is a set claim over the "
            "map that names no row")


def keep_set_only_named(root: Path) -> None:
    """GRADER (round 9): the measured plan note — "only" over the rows it names is a
    named-set word, and whether W1 covers no other row is agreement, the grader's."""
    swap_once(root, DOSSIER, "(3) the retrofit bridge", "(3) W1 covers only R3 and R4; (4) the retrofit bridge",
              "keep_set_only_named")


def break_set_bare_none_after(root: Path) -> str:
    swap_once(root, DOSSIER, AFTER_LEDGER, "R4 and R5 sit below `direct`, and none is a gate.", "break_set_bare_none_after")
    return "the sentence after the fit ledger: \"none\" is a complement"


def keep_set_false_universal(root: Path) -> None:
    """GRADER: named, the whole tier, and false of R4, which is `adjacent`."""
    swap_once(root, DOSSIER, AFTER_LEDGER, "R2, R3 and R4 — every must-have, `direct`.", "keep_set_false_universal")


def keep_set_ids_false(root: Path) -> None:
    """GRADER: a quantifier over the IDs it names, false of R4."""
    swap_once(root, DOSSIER, AFTER_LEDGER, "R3 and R4 — both `direct`.", "keep_set_ids_false")


def keep_set_both_three(root: Path) -> None:
    """GRADER: "both" over three IDs."""
    swap_once(root, DOSSIER, AFTER_LEDGER, "R4, R5 and R7 — both wait on evidence.", "keep_set_both_three")


def keep_set_two_tiers_partial(root: Path) -> None:
    """GRADER: two tiers joined, and only R1 and R9 named."""
    swap_once(root, ENVELOPE, SUMMARY, '"summary": "Every hard gate and must-have — R1 and R9 — is met. Fit as '
              'evidence_map reads it,', "keep_set_two_tiers_partial")


def keep_set_unresolved_other_clause(root: Path) -> None:
    """GRADER: the candidate's claims, not the map's rows, with R4 in another clause."""
    swap_once(root, ENVELOPE, SUMMARY, '"summary": "All your candidate claims are self-reported, and R4 needs a work '
              'sample. Fit as evidence_map reads it,', "keep_set_unresolved_other_clause")


def keep_set_range(root: Path) -> None:
    """GRADER: a range names only its endpoints."""
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "Every must-have (R2–R4) is evidenced. " + SNAPSHOT_PROSE, "keep_set_range")


def keep_set_ratio_wrong_m(root: Path) -> None:
    """GRADER: M is the noun's set, and the map has four rows below `direct`."""
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "One of the five gaps is a must-have: R4. " + SNAPSHOT_PROSE,
              "keep_set_ratio_wrong_m")


def keep_set_ids_link_verb(root: Path) -> None:
    """Over the IDs it names, a linking verb between: R1, R6 and R9 are `direct` too."""
    swap_once(root, DOSSIER, AFTER_LEDGER, "R2 and R3 — they are both `direct`; R3 (`medium`) — waits on an artifact.",
              "keep_set_ids_link_verb")


def keep_set_true_negative(root: Path) -> None:
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "None of the hard gates — R1, R8 and R9 — is `hard_gate_fail`. "
              + SNAPSHOT_PROSE, "keep_set_true_negative")


def keep_set_constraints_not_given(root: Path) -> None:
    """The candidate's constraints, stated or not, are not the map's vocabulary."""
    swap_once(root, ENVELOPE, SUMMARY, '"summary": "No hard constraints were stated beyond the start date and the '
              'contract basis. Fit as evidence_map reads it,', "keep_set_constraints_not_given")


def keep_set_only_not_rows(root: Path) -> None:
    """"only" restricting who can act, not which rows."""
    swap_once(root, DOSSIER, "(2) the post confirmed as permanent — R8, RR2;",
              "(2) only the employer can settle R8 — the post confirmed as permanent, RR2;",
              "keep_set_only_not_rows")


def keep_set_count_verb(root: Path) -> None:
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "Two gaps matter: R4 and R5. " + SNAPSHOT_PROSE, "keep_set_count_verb")


def keep_set_narrowed_noun(root: Path) -> None:
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "Every open must-have — R4 — has a named bridge. " + SNAPSHOT_PROSE,
              "keep_set_narrowed_noun")


def break_retired_count_rule(root: Path) -> str:
    """The pre-round-7 rule, back in a grader clause: every quantifier fails, named or not."""
    clause_swap(root, JU, "no_score", "No single numeric fit score or percentage appears",
                "No single numeric fit score or percentage appears. Any number, total or set quantifier over the map "
                "fails, even when it is accurate", "break_retired_count_rule")
    return "is the retired count rule"


def keep_unnamed_rule_stated(root: Path) -> None:
    """The rule that retired it, in the same words, passes: the set it fails is unnamed."""
    clause_swap(root, JU, "no_score", "No single numeric fit score or percentage appears",
                "No single numeric fit score or percentage appears. Any quantifier over a set of rows left unnamed "
                "fails, even when it is accurate", "keep_unnamed_rule_stated")


def keep_set_named_exact_after(root: Path) -> None:
    swap_once(root, DOSSIER, AFTER_LEDGER, "R2, R3 and R4 — every must-have, with evidence; R3 (`medium`) — waits on "
              "an artifact.", "keep_set_named_exact_after")


def keep_set_named_count(root: Path) -> None:
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "Five rows are `direct`: R1, R2, R3, R6 and R9. " + SNAPSHOT_PROSE,
              "keep_set_named_count")


def keep_set_named_ratio_summary(root: Path) -> None:
    swap_once(root, ENVELOPE, SUMMARY,
              '"summary": "Five of the nine requirements are direct (R1, R2, R3, R6, R9). Fit as evidence_map reads it,',
              "keep_set_named_ratio_summary")


def keep_set_named_status(root: Path) -> None:
    """Rule 1's worked form: a reason about rows names them."""
    swap_once(root, DOSSIER, VERDICT, "**Worth applying to — R1 and R9, both hard gates, are met; on the conditions below.",
              "keep_set_named_status")


def keep_set_named_gap_type(root: Path) -> None:
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "None of R4, R5 is a capability gap. " + SNAPSHOT_PROSE,
              "keep_set_named_gap_type")


# Round 9's rule: a statement about a set of map rows agrees with the map everywhere,
# and names its rows in the snapshot and decision.summary only; "only" and "the one"
# are named-set words, and the complements fail there whatever they name
# (evidence-model.md, "The row is the unit"). Agreement is exactness, the grader's
# (the comment above Claim in ci/ledger_rules.py). The worked map's rows below
# `direct`: R4, R5, R7, R8.

def keep_set_only_exact_after(root: Path) -> None:
    """The measured named "only", exact on this map, after the ledger."""
    swap_once(root, DOSSIER, AFTER_LEDGER, "R4, R5, R7 and R8 — the only rows below `direct`.",
              "keep_set_only_exact_after")


def keep_set_the_one_named(root: Path) -> None:
    """"the one" over the row it names, in the status line: R4 is the one must-have below `direct`."""
    swap_once(root, DOSSIER, VERDICT, "**Worth applying to — R4 is the one must-have below `direct`; on the conditions "
              "below.", "keep_set_the_one_named")


def keep_set_only_named_summary(root: Path) -> None:
    """GRADER: a named "only" in decision.summary, false of the map (R5, R7 and R8 are
    below `direct` too): exactness is the grader's."""
    swap_once(root, ENVELOPE, SUMMARY, '"summary": "R4 is the only row below direct. Fit as evidence_map reads it,',
              "keep_set_only_named_summary")


def break_set_the_one_unnamed(root: Path) -> str:
    swap_once(root, ENVELOPE, SUMMARY, '"summary": "The one must-have below direct has a bridge. Fit as evidence_map '
              'reads it,', "break_set_the_one_unnamed")
    return 'decision.summary: "The one must-have" is a set claim over the map that names no row'


def break_set_only_unnamed_status(root: Path) -> str:
    swap_once(root, DOSSIER, VERDICT, "**Worth applying to — the only rows below `direct` have bridges; on the "
              "conditions below.", "break_set_only_unnamed_status")
    return "the snapshot's prose: \"the only rows\" is a set claim over the map that names no row"


def break_set_measured_complement(root: Path) -> str:
    """Measured after the ledger: named rows, then a complement that speaks for the rest."""
    swap_once(root, DOSSIER, AFTER_LEDGER, "R1 and R2 fail outright and nothing else in the map can offset that.",
              "break_set_measured_complement")
    return "the sentence after the fit ledger: \"nothing else\" is a complement"


def break_set_other_plural_unnamed(root: Path) -> str:
    """Round 9: "the other must-haves" is "the others" in its noun form, a complement named or not."""
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "The other must-haves are `direct`. " + SNAPSHOT_PROSE,
              "break_set_other_plural_unnamed")
    return "the snapshot's prose: \"The other must-haves\" is a complement"


def keep_set_other_singular(root: Path) -> None:
    """Round 9: the singular "the other hard gate" names one row; it is not "the others"."""
    swap_once(root, DOSSIER, SNAPSHOT_PROSE, "R4 waits on an artifact; the other hard gate, R1, is met. "
              + SNAPSHOT_PROSE, "keep_set_other_singular")


# Each complement, in the snapshot's prose and after the ledger, beside a named row.
COMPLEMENT_SENTENCES = (
    ("the rest", "R4 waits on an artifact; the rest are `direct`.", "the rest are `direct`"),
    ("the others", "R4 waits on an artifact; the others are `direct`.", "the others are `direct`"),
    ("everything else", "R4 waits on an artifact; everything else is `direct`.", "everything else is `direct`"),
    ("nothing else", "R4 waits on an artifact; nothing else is below `direct`.", "nothing else is below `direct`"),
    ("no other", "R4 waits on an artifact; no other row does.", "no other row"),
    ("any other", "R4 waits on an artifact longer than any other row.", "any other row"),
    ("none of the others", "R4 waits on an artifact; none of the others is below `direct`.",
     "none of the others is below `direct`"),
    ("all but", "Direct on all but R4.", "all but"),
    ("all except", "Direct on all except R4.", "all except"),
    # Round 9: "the others" in its noun form, before a plural map noun.
    ("the other must-haves", "R4 is the one real gap; the other must-haves land `direct`.", "the other must-haves"),
)


def _complement_case(phrase: str, sentence: str, words: str, after: bool):
    name = f"break_set_complement_{'after' if after else 'prose'}_{phrase.replace(' ', '_')}"

    def mutate(root: Path) -> str:
        if after:
            swap_once(root, DOSSIER, AFTER_LEDGER, sentence, name)
            return f'the sentence after the fit ledger: "{words}" is a complement'
        swap_once(root, DOSSIER, SNAPSHOT_PROSE, sentence + " " + SNAPSHOT_PROSE, name)
        return f'the snapshot\'s prose: "{words}" is a complement'
    mutate.__name__ = name
    return mutate


COMPLEMENT_CASES = [("fit-ledger", f"the complement \"{phrase}\" {'after the ledger' if after else 'in the snapshot'}",
                     _complement_case(phrase, sentence, words, after))
                    for phrase, sentence, words in COMPLEMENT_SENTENCES for after in (False, True)]


def break_retired_exclusive_word(root: Path) -> str:
    """Round 9's retired word, back in a grader clause."""
    clause_swap(root, JU, "no_score", "No single numeric fit score or percentage appears",
                "No single numeric fit score or percentage appears. An exclusive quantifier fails whatever it names",
                "break_retired_exclusive_word")
    return "is the retired word for a list"


def break_retired_response_modes(root: Path) -> str:
    """Round 9: the questions clause back to one response-modes line per question."""
    clause_swap(root, JU, "questions", "and the questions offer their response modes as prose",
                "and each offers its response modes as prose", "break_retired_response_modes")
    return "is the retired placement"


# The answer-key check reads fenced code as prose (NP-5).

def break_answer_key_fenced(root: Path) -> str:
    """An unquoted fixture run inside a worked YAML block: the fence used to hide it."""
    swap_once(root, "skills/job-underwriter/references/evidence-model.md",
              "```yaml\nrequirement_id: R1 ",
              "```yaml\nnote: Led 30+ client integrations of our REST APIs end to end\nrequirement_id: R1 ",
              "break_answer_key_fenced")
    return "repeats this skill's own fixtures unquoted"


def keep_answer_key_snake_case(root: Path) -> None:
    """Schema fields a dossier fixture repeats by contract, fenced: one word each."""
    path = root / "skills/mock-interview/references/dossier-handoff.md"
    path.write_text(path.read_text() + "\n\n```yaml\nhandoff_to_mock_interview:\n  high_priority_requirements: [...]\n"
                                       "  allowed_interview_strategy: [...]\n```\n")


# The after-ledger words are written once (D9, NP-7).

EVIDENCE_MODEL = "skills/job-underwriter/references/evidence-model.md"
RISK_AND_DECISION = "skills/job-underwriter/references/risk-and-decision.md"


def break_quantifier_scope_drift(root: Path) -> str:
    """The list scopes a new word to the sentence after the ledger; the shared set does not."""
    swap_once(root, EVIDENCE_MODEL, 'a bare "none" too', 'a bare "none" or "most" too',
              "break_quantifier_scope_drift")
    return "lacks ['most'] from evidence-model.md's words scoped to the sentence after the ledger"


def break_quantifier_set_extra(root: Path) -> str:
    """The shared set holds a word the rule does not: set equality, not a subset."""
    swap_once(root, "ci/ledger_rules.py", '("the rest", "the others",', '("the rest", "most", "the others",',
              "break_quantifier_set_extra")
    return "holds ['most'] among the complements, which evidence-model.md's list does not"


def clause_swap(root: Path, rel: str, clause: str, old: str, new: str, name: str) -> None:
    path = root / rel
    data = json.loads(path.read_text())
    if data["clauses"][clause].count(old) != 1:
        raise SystemExit(f"{name} expected one {old!r} in the {clause} clause — it has gone stale")
    data["clauses"][clause] = data["clauses"][clause].replace(old, new)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def break_grader_bare_none(root: Path) -> str:
    """NP-7: the grader told 'none' is exempt, its backticks lost."""
    clause_swap(root, JU, "ledger_counts", "the token `none` in backticks, a band or a gap type,", "the token 'none'",
                "break_grader_bare_none")
    return "quotes ['none'] outside its sentence on the sentence after the ledger"


def break_grader_scope_missing(root: Path) -> str:
    clause_swap(root, JU, "ledger_counts",
                ", and a bare 'none' fails too, because it speaks for the rows that sentence does not name", "",
                "break_grader_scope_missing")
    return "lists quantifiers without ['none'], which evidence-model.md's list scopes"


def break_rule2_unpointed(root: Path) -> str:
    swap_once(root, RISK_AND_DECISION, 'under the rule in `references/evidence-model.md` ("The row is the unit")',
              'under a rule of its own', "break_rule2_unpointed")
    return "rule 2 no longer points to evidence-model.md"


def break_rule2_spells_list(root: Path) -> str:
    swap_once(root, RISK_AND_DECISION, 'and scopes one more word to it.',
              'and scopes one more word to it, such as "no other".', "break_rule2_spells_list")
    return "rule 2 spells ['no other']"


# The clause mechanism (D1).

def break_clause_unknown(root: Path) -> str:
    path = root / JU
    data = json.loads(path.read_text())
    data["evals"][0]["expectations"].append("{{no_such_clause}}")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return "names no clause"


def break_clause_unused(root: Path) -> str:
    path = root / MI
    data = json.loads(path.read_text())
    data["clauses"]["orphan"] = "Text that grades nothing."
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return "clause \"orphan\" is defined and never used"


def break_clause_nested(root: Path) -> str:
    """A clause inside a clause is not expanded, and would reach the grader as braces."""
    path = root / JU
    data = json.loads(path.read_text())
    data["clauses"]["no_score"] += " {{closing}}"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return "keeps an unexpanded clause reference"


# --- The watch-out line (output-discipline.md rule 7) -------------------------------------

MI_WATCH = ("Suggested answers can make your experience sound bigger than what you told me — rehearse only what "
            "you actually did, in your own words.")
RT_WATCH = ("The words I quote as yours beside each edit can differ slightly from what you wrote — before you approve "
            "a line or send the resume, check that quote and the new line against what you actually wrote.")
# The parameter's value is the whole line, label included (output-discipline.md rule 7).
MI_PARAM = f"watch_out: **Watch-out:** {MI_WATCH}\n"


def break_watch_out_undeclared(root: Path) -> str:
    """The parameter line deleted from a SKILL.md."""
    swap_once(root, "skills/mock-interview/SKILL.md", MI_PARAM, "", "break_watch_out_undeclared")
    return "declares no watch_out line"


def break_watch_out_sentence_only(root: Path) -> str:
    """The parameter back to the sentence alone, leaving the model to assemble the label — the form whose
    label Haiku dropped."""
    swap_once(root, "skills/mock-interview/SKILL.md", MI_PARAM, f"watch_out: {MI_WATCH}\n",
              "break_watch_out_sentence_only")
    return "watch_out is not the whole line"


def break_watch_out_variant_label(root: Path) -> str:
    """The parameter's label spelled another way — the variant a run wrote."""
    swap_once(root, "skills/mock-interview/SKILL.md", MI_PARAM, f"watch_out: Watch out: {MI_WATCH}\n",
              "break_watch_out_variant_label")
    return "watch_out is not the whole line"


def break_watch_out_two_sentences(root: Path) -> str:
    """Extended past one sentence — the standing rule says extend it and keep it one."""
    swap_once(root, "skills/mock-interview/SKILL.md", MI_PARAM,
              MI_PARAM.replace("\n", " Check the dates too.\n"), "break_watch_out_two_sentences")
    return "watch_out is not one sentence"


def break_watch_out_too_long(root: Path) -> str:
    """One sentence, and no longer crisp."""
    swap_once(root, "skills/resume-tailor/SKILL.md", "against what you actually wrote.\n```",
              "against what you actually wrote, your original resume, your portfolio, your old cover letters, your LinkedIn profile and any "
              "reference you plan to give.\n```", "break_watch_out_too_long")
    return "over 40"


def break_watch_out_pipe(root: Path) -> str:
    """A pipe in the sentence breaks the README's table."""
    swap_once(root, "skills/mock-interview/SKILL.md", MI_PARAM, MI_PARAM.replace(" — ", " | "),
              "break_watch_out_pipe")
    return "bracket, pipe or code span"


def break_closing_order_without_watch_out(root: Path) -> str:
    """closing_order back to ending on the questions."""
    swap_once(root, "skills/resume-tailor/SKILL.md", "closing_order: upgrade menu, questions, watch-out\n",
              "closing_order: upgrade menu, questions\n", "break_closing_order_without_watch_out")
    return "closing_order does not end with watch-out"


def break_watch_out_readme_drift(root: Path) -> str:
    """The README's copy edited and the parameter not."""
    swap_once(root, "README.md", f"| mock-interview | {MI_WATCH} |",
              "| mock-interview | Suggested answers can overstate your experience — rehearse only what you did. |",
              "break_watch_out_readme_drift")
    return "README.md's watch-out table quotes mock-interview's sentence"


def break_watch_out_readme_labelled(root: Path) -> str:
    """The README's cell carrying the label too: its column header is the label, and the cell is the sentence
    after it (output-discipline.md rule 7), so one form is held, not either."""
    swap_once(root, "README.md", f"| mock-interview | {MI_WATCH} |",
              f"| mock-interview | **Watch-out:** {MI_WATCH} |", "break_watch_out_readme_labelled")
    return "README.md's watch-out table quotes mock-interview's sentence"


def break_watch_out_parameter_drift(root: Path) -> str:
    """The parameter edited and its copies not — the other direction of the same drift."""
    swap_once(root, "skills/mock-interview/SKILL.md", MI_PARAM,
              MI_PARAM.replace("in your own words", "and say it in your own words"),
              "break_watch_out_parameter_drift")
    return "README.md's watch-out table quotes mock-interview's sentence"


def break_watch_out_readme_row_missing(root: Path) -> str:
    swap_once(root, "README.md", f"| resume-tailor | {RT_WATCH} |",
              f"| resume tailoring | {RT_WATCH} |", "break_watch_out_readme_row_missing")
    return "has 0 rows for resume-tailor"


def break_watch_out_fixture_paraphrase(root: Path) -> str:
    """A fixture's closing clause paraphrasing the line a grader holds the run to."""
    swap_once(root, "skills/resume-tailor/evals/evals.json", f"**Watch-out:** {RT_WATCH}",
              "**Watch-out:** Check each quote and each new line against your original resume.",
              "break_watch_out_fixture_paraphrase")
    return "labels a watch-out line that is not the declared line"


def break_watch_out_fixture_label_dropped(root: Path) -> str:
    """A fixture's copy keeping the sentence and dropping the label: the grader would pass a run that did the same."""
    swap_once(root, "skills/resume-tailor/evals/evals.json", f"**Watch-out:** {RT_WATCH}", RT_WATCH,
              "break_watch_out_fixture_label_dropped")
    return "no expectation carries the watch-out line exactly"


def break_watch_out_fixture_typography(root: Path) -> str:
    """A fixture's code-span copy of the line with curly quotes: the clause says the harness checks it
    character for character, so CI holds the copy to the same exactness."""
    swap_once(root, "skills/job-underwriter/evals/evals.json",
              'before you act on a count, an \\"only\\" or an all-clear, check it against the table\'s rows.`',
              'before you act on a count, an “only” or an all-clear, check it against the table\'s rows.`',
              "break_watch_out_fixture_typography")
    return "labels a watch-out line that is not the declared line"


def break_watch_out_example_drift(root: Path) -> str:
    """A worked example's last line no longer the declared one."""
    swap_once(root, "skills/resume-tailor/references/coverage-and-gaps.md", f"**Watch-out:** {RT_WATCH}",
              "**Watch-out:** Check every edit against your original resume.", "break_watch_out_example_drift")
    return "a watch-out line that is not the declared one"


def break_watch_out_example_variant_label(root: Path) -> str:
    """A worked example's last line with the exact sentence under a variant label."""
    swap_once(root, "skills/mock-interview/references/output-template.md", f"**Watch-out:** {MI_WATCH}",
              f"Watch out: {MI_WATCH}", "break_watch_out_example_variant_label")
    return "a watch-out line that is not the declared one"


def break_watch_out_convention(root: Path) -> str:
    """The convention losing its definition of the slot."""
    swap_once(root, "conventions/output-discipline.md", "**Parameter: `watch_out`**", "**The sentence**",
              "break_watch_out_convention")
    return "does not define the watch-out slot"


def break_watch_out_named_warning(root: Path) -> str:
    """The slot labelled with the name it never takes, in a skill's template."""
    swap_once(root, "skills/mock-interview/references/output-template.md", "Running a drill:",
              "**Warning:** rehearse only what you did.\n\nRunning a drill:", "break_watch_out_named_warning")
    return "names a line a warning"


def break_watch_out_readme_warning(root: Path) -> str:
    swap_once(root, "README.md", "Each skill ends its output with one sentence telling you what to double-check.",
              "Each skill ends its output with a one-sentence warning telling you what to double-check.",
              "break_watch_out_readme_warning")
    return "watch-out section uses \"warning\""


def break_standing_rule_renamed(root: Path) -> str:
    """The heading the README links to, renamed."""
    swap_once(root, "CONTRIBUTING.md", "## When an issue survives two iterations\n", "## Stopping rule\n",
              "break_standing_rule_renamed")
    return "no '## When an issue survives two iterations' section"


def keep_watch_out_changed_everywhere(root: Path) -> None:
    """The sentence changed in its parameter and every copy at once: the way to change it."""
    new = MI_WATCH.replace("in your own words", "and say it in your own words")
    for rel in ("skills/mock-interview/SKILL.md", "README.md", "skills/mock-interview/evals/evals.json",
                "skills/mock-interview/references/output-template.md"):
        path = root / rel
        text = path.read_text()
        if text.count(MI_WATCH) < 1:
            raise SystemExit(f"keep_watch_out_changed_everywhere: no sentence in {rel} — it has gone stale")
        path.write_text(text.replace(MI_WATCH, new))


def keep_watch_out_readme_linked_name(root: Path) -> None:
    """The README's Skill cell written as a link in code, like the table above it."""
    swap_once(root, "README.md", f"| job-underwriter | A summary line",
              "| [`job-underwriter`](skills/job-underwriter/) | A summary line", "keep_watch_out_readme_linked_name")


def keep_warning_signs_elsewhere(root: Path) -> None:
    """"warning" about something else, not as a line's label."""
    swap_once(root, "skills/mock-interview/references/output-template.md", "Running a drill:",
              "Warning signs that a drill is going badly are covered in step 6.\n\nRunning a drill:",
              "keep_warning_signs_elsewhere")


# --- guidance: Anthropic's skill-authoring limits ----------------------------

def _drop_contents(text: str) -> str:
    """The text with its '## Contents' block (heading and list) removed."""
    mutated = re.sub(r"\n## Contents\n\n(?:[ ]*- .*\n)+", "\n", text, count=1)
    if mutated == text:
        raise SystemExit("_drop_contents found no contents list — it has gone stale")
    return mutated


def break_toc_removed(root: Path) -> str:
    """A skill's own 200-line reference file with its contents list deleted."""
    path = root / "skills/job-underwriter/references/evidence-model.md"
    path.write_text(_drop_contents(path.read_text()))
    return "starts with a table of contents"


def break_toc_below_intro(root: Path) -> str:
    """The contents list present, but under the intro rather than at the top."""
    path = root / "skills/resume-tailor/references/coverage-and-gaps.md"
    text = path.read_text()
    block = re.search(r"\n## Contents\n\n(?:[ ]*- .*\n)+", text).group(0)
    text = text.replace(block, "\n", 1)
    first_section = text.index("\n## ")
    path.write_text(text[:first_section] + block + text[first_section:])
    return "does not open with '## Contents' directly under its H1"


def break_toc_mirror(root: Path) -> str:
    """The canonical file loses its list and the resync carries the loss into every mirror."""
    canonical = root / "conventions/output-discipline.md"
    canonical.write_text(_drop_contents(canonical.read_text()))
    for mirror in root.glob("skills/*/references/output-discipline.md"):
        text = mirror.read_text()
        header = re.match(r"\A<!-- SYNCED FROM: .*?-->\n", text, re.S).group(0)
        mirror.write_text(header + canonical.read_text())
    return "references/output-discipline.md is 2"


def break_skill_body_tokens(root: Path) -> str:
    """Rationale paragraphs added back to a SKILL.md, one at a time, until it is over."""
    path = root / "skills/job-underwriter/SKILL.md"
    para = ("This rule exists because a measured run once did the opposite, and the paragraph explaining "
            "that history sat beside the rule for three releases. ")
    path.write_text(path.read_text() + "\n" + para * 12 + "\n")
    return "over the 5000-token estimate"


def break_skill_body_lines(root: Path) -> str:
    path = root / "skills/resume-tailor/SKILL.md"
    path.write_text(path.read_text() + "".join(f"\n- item {i}" for i in range(500)) + "\n")
    return "500-line limit"


def break_description_imperative(root: Path) -> str:
    """The form every description had before this check: a bare imperative."""
    swap_once(root, "skills/job-underwriter/SKILL.md", "description: Decides whether", "description: Decide whether",
              "break_description_imperative")
    return "'Decide', a bare imperative"


def break_description_imperative_ss(root: Path) -> str:
    """A bare imperative that already ends in "s"."""
    swap_once(root, "skills/resume-tailor/SKILL.md", "description: Tailors an existing", "description: Process an existing",
              "break_description_imperative_ss")
    return "'Process', a bare imperative"


def break_reference_bare_name(root: Path) -> str:
    """A reference named in SKILL.md only by its bare file name, a path that resolves nowhere."""
    path = root / "skills/resume-tailor/SKILL.md"
    text = path.read_text()
    if "`references/machine-readers.md`" not in text:
        raise SystemExit("break_reference_bare_name found no link — it has gone stale")
    path.write_text(text.replace("`references/machine-readers.md`", "`machine-readers.md`"))
    return "never links references/machine-readers.md"


def break_frontmatter_extra_key(root: Path) -> str:
    """A Claude Code-only key in source: claude.ai rejects the upload."""
    swap_once(root, "skills/mock-interview/SKILL.md", "name: mock-interview\n",
              "name: mock-interview\ndisable-model-invocation: true\n", "break_frontmatter_extra_key")
    return "unexpected frontmatter key(s): disable-model-invocation"


def keep_toc_at_100_lines(root: Path) -> None:
    """A reference file of exactly 100 lines needs no contents list: the rule is over 100."""
    (root / "skills/resume-tailor/references/notes.md").write_text(
        "# Notes\n\n" + "".join(f"Line {i}.\n" for i in range(98)))
    swap_once(root, "skills/resume-tailor/SKILL.md", "- `references/rationale.md`",
              "- `references/notes.md`\n- `references/rationale.md`", "keep_toc_at_100_lines")


def keep_body_near_limit(root: Path) -> None:
    """A body just under the estimate is accepted."""
    path = root / "skills/resume-tailor/SKILL.md"
    text = path.read_text()
    body = len(re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S))
    room = 5000 * 4 - 8 - body - 2
    if room < 10:
        raise SystemExit("keep_body_near_limit: no room left under the estimate — it has gone stale")
    path.write_text(text + "\n" + ("w" * (room - 1)) + "\n")


def keep_description_assesses(root: Path) -> None:
    """A third-person verb whose bare form ends in "ss"."""
    swap_once(root, "skills/job-underwriter/SKILL.md", "description: Decides whether", "description: Assesses whether",
              "keep_description_assesses")


def keep_reference_markdown_link(root: Path) -> None:
    """A reference linked as a markdown link carries its path and is accepted."""
    path = root / "skills/resume-tailor/SKILL.md"
    text = path.read_text()
    path.write_text(text.replace("`references/machine-readers.md`", "[machine readers](references/machine-readers.md)"))


def keep_frontmatter_license_key(root: Path) -> None:
    """One of the six keys the spec allows."""
    swap_once(root, "skills/mock-interview/SKILL.md", "name: mock-interview\n", "name: mock-interview\nlicense: MIT\n",
              "keep_frontmatter_license_key")


def _body_len(text: str) -> int:
    return len(re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S))


def _pad_body_to(root: Path, rel: str, chars: int, name: str) -> None:
    """Append one line of filler so the SKILL.md body is exactly `chars` characters."""
    path = root / rel
    text = path.read_text()
    fill = chars - _body_len(text) - 2
    if fill < 1:
        raise SystemExit(f"{name}: the body is already at or over {chars} chars — it has gone stale")
    path.write_text(text + "\n" + "w" * fill + "\n")
    if _body_len(path.read_text()) != chars:
        raise SystemExit(f"{name}: padding missed {chars} chars")


def _pad_lines_to(root: Path, rel: str, lines: int, name: str) -> None:
    """Append short lines so the SKILL.md body is exactly `lines` lines."""
    path = root / rel
    text = path.read_text()
    if not text.endswith("\n"):
        raise SystemExit(f"{name}: {rel} no longer ends with a newline — it has gone stale")
    have = len(re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S).splitlines())
    if have >= lines:
        raise SystemExit(f"{name}: the body already has {have} lines — it has gone stale")
    path.write_text(text + "".join(f"- {i}\n" for i in range(lines - have)))


def break_skill_body_tokens_at_limit(root: Path) -> str:
    """A body of exactly 20,000 chars is 5,000 estimated tokens: at the limit, so over it."""
    _pad_body_to(root, "skills/resume-tailor/SKILL.md", 5000 * 4, "break_skill_body_tokens_at_limit")
    return "over the 5000-token estimate"


def keep_body_one_token_under(root: Path) -> None:
    """A body of 19,999 chars is 4,999 estimated tokens: one under, accepted."""
    _pad_body_to(root, "skills/resume-tailor/SKILL.md", 5000 * 4 - 1, "keep_body_one_token_under")


def break_skill_body_lines_at_limit(root: Path) -> str:
    """A body of exactly 500 lines is at the limit, so over it."""
    _pad_lines_to(root, "skills/resume-tailor/SKILL.md", 500, "break_skill_body_lines_at_limit")
    return "500-line limit"


def keep_body_499_lines(root: Path) -> None:
    """A body of 499 lines is accepted."""
    _pad_lines_to(root, "skills/resume-tailor/SKILL.md", 499, "keep_body_499_lines")


def break_toc_heading_without_list(root: Path) -> str:
    """The contents heading kept, its list rewritten as a sentence."""
    path = root / "skills/job-underwriter/references/evidence-model.md"
    mutated = re.sub(r"\n## Contents\n\n(?:[ ]*- .*\n)+",
                     "\n## Contents\n\nThe vocabulary, the row, the card, the examples and the serialization.\n",
                     path.read_text(), count=1)
    if mutated == path.read_text():
        raise SystemExit("break_toc_heading_without_list found no contents list — it has gone stale")
    path.write_text(mutated)
    return "has a '## Contents' heading with no list under it"


def break_toc_no_h1(root: Path) -> str:
    """A reference over 100 lines with no H1 for its contents list to sit under."""
    swap_once(root, "skills/job-underwriter/references/evidence-model.md", "# Evidence model\n\n", "",
              "break_toc_no_h1")
    return "has no H1 for a contents list to sit under"


def break_reference_unlinked_short(root: Path) -> str:
    """A short reference file, well under 100 lines, that SKILL.md never names."""
    swap_once(root, "skills/resume-tailor/SKILL.md",
              "- `references/rationale.md` — why the rules are shaped this way; not needed to follow them\n", "",
              "break_reference_unlinked_short")
    return "never links references/rationale.md"


def break_reference_unlinked_mirror(root: Path) -> str:
    """A mirror that SKILL.md never names: a mirror ships, so it is linked like any other file."""
    path = root / "skills/resume-tailor/SKILL.md"
    text = path.read_text()
    if text.count("`references/dossier-schema.md`") < 1:
        raise SystemExit("break_reference_unlinked_mirror found no link — it has gone stale")
    text = text.replace("- `references/dossier-schema.md` (mirror)\n", "")
    path.write_text(text.replace("`references/dossier-schema.md`", "the dossier schema"))
    return "never links references/dossier-schema.md"


def break_reference_named_only_in_frontmatter(root: Path) -> str:
    """Named in the description, which is not the body that loads: still unlinked."""
    path = root / "skills/resume-tailor/SKILL.md"
    text = path.read_text()
    line = "- `references/rationale.md` — why the rules are shaped this way; not needed to follow them\n"
    if text.count(line) != 1:
        raise SystemExit("break_reference_named_only_in_frontmatter found no index line — it has gone stale")
    text = text.replace(line, "")
    path.write_text(text.replace("\n---\n", " See references/rationale.md.\n---\n", 1))
    return "never links references/rationale.md"


def keep_frontmatter_compatibility_key(root: Path) -> None:
    swap_once(root, "skills/mock-interview/SKILL.md", "name: mock-interview\n",
              "name: mock-interview\ncompatibility: Requires web search for research tiers L1 and L2\n",
              "keep_frontmatter_compatibility_key")


def keep_frontmatter_metadata_key(root: Path) -> None:
    swap_once(root, "skills/mock-interview/SKILL.md", "name: mock-interview\n",
              "name: mock-interview\nmetadata:\n  version: \"1.0\"\n", "keep_frontmatter_metadata_key")


def keep_frontmatter_allowed_tools_key(root: Path) -> None:
    swap_once(root, "skills/mock-interview/SKILL.md", "name: mock-interview\n",
              "name: mock-interview\nallowed-tools: Read Write\n", "keep_frontmatter_allowed_tools_key")


HUB_MD = "skills/tuesday/SKILL.md"
HUB_REFS = "skills/tuesday/references"


def tool(root: Path, script: str) -> None:
    """Run one of ci/'s tools in the staged repository, as an author fixing a change would."""
    proc = subprocess.run([sys.executable, f"ci/{script}"], cwd=root, capture_output=True, text=True)
    if proc.returncode:
        raise SystemExit(f"ci/{script} failed in the staged repo:\n{proc.stdout}{proc.stderr}")


def measured_now(root: Path) -> None:
    """Record the staged front door's digests as measured: the conscious update a change makes
    once its measurement is done."""
    proc = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'ci'); import json, check_skills; "
                           "print(json.dumps(check_skills.frontdoor_digests()))"],
                          cwd=root, capture_output=True, text=True)
    now = json.loads(proc.stdout)
    path = root / "ci/check_skills.py"
    text = path.read_text()
    for key, value in now.items():
        text = re.sub(rf'("{key}": ")[0-9a-f]{{64}}(")', rf"\g<1>{value}\g<2>", text, count=1)
    path.write_text(text)


def break_frontdoor_unlinked(root: Path) -> str:
    """Drop one generated file's line from the hub's index: it would be reachable
    only through a playbook, the nested pattern the guidance warns against. The
    guidance group holds every skill's links, the front door's included."""
    path = root / HUB_MD
    text = path.read_text()
    line = next(l for l in text.splitlines() if l.startswith("- `references/personas.md`"))
    path.write_text(text.replace(line + "\n", ""))
    return "tuesday: SKILL.md never links references/personas.md by that path"


def break_frontdoor_new_clash(root: Path) -> str:
    """Give a second module a file named like one of job-underwriter's, with other
    text, and do not regenerate: the committed references no longer follow the sources."""
    (root / "skills/mock-interview/references/evidence-model.md").write_text("# Mock-interview's own model\n")
    return "skills/tuesday/references/job-underwriter-evidence-model.md is missing — run python ci/sync.py"


def break_frontdoor_new_clash_synced(root: Path) -> str:
    """The same clash, regenerated: the generator renames both copies, and a hub still
    linking the old name links a file that is no longer there."""
    (root / "skills/mock-interview/references/evidence-model.md").write_text("# Mock-interview's own model\n")
    tool(root, "sync.py")
    return "the hub links references/evidence-model.md, which its references/ folder does not hold"


def break_frontdoor_dangling(root: Path) -> str:
    """Link a file the generator does not write."""
    path = root / HUB_MD
    path.write_text(path.read_text() + "\n- `references/scoring-guide.md`: read before scoring\n")
    return "the hub links references/scoring-guide.md, which its references/ folder does not hold"


def break_frontdoor_unresolvable(root: Path) -> str:
    """Make a shared mirror name a file whose name clashes between modules: which
    module's copy it means cannot be decided, so generation stops."""
    for skill in ("job-underwriter", "mock-interview", "resume-tailor"):
        path = root / f"skills/{skill}/references/citations.md"
        path.write_text(path.read_text() + "\nSee rationale.md.\n")
    return "names rationale.md, which differs between modules"


def break_frontdoor_claude_code_key(root: Path) -> str:
    """Hide the hub with a Claude Code-only key: a claude.ai upload would refuse it.
    The front door is a skill, so the frontmatter group reads it."""
    path = root / HUB_MD
    path.write_text(path.read_text().replace("name: tuesday\n", "name: tuesday\ndisable-model-invocation: true\n", 1))
    return "tuesday: unexpected frontmatter key(s): disable-model-invocation"


def break_frontdoor_explicit_expects_other(root: Path) -> str:
    """An E2 case expecting a module other than the one its command names."""
    path = root / "evals/suite-explicit.json"
    data = json.loads(path.read_text())
    data["cases"][0]["expected"] = "job-underwriter"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return "invokes /mock-interview but expects 'job-underwriter'"


def break_frontdoor_yaml_colon(root: Path) -> str:
    """Put a ': ' back in the hub's unquoted description, as the design draft had it:
    Claude Code's lenient reader takes it, a strict YAML parser does not."""
    path = root / HUB_MD
    text = path.read_text()
    path.write_text(text.replace("runs only that module — job-underwriter", "runs only that module: job-underwriter", 1))
    return "tuesday: frontmatter description is an unquoted YAML value that holds a ':' before a space"


def break_frontdoor_hand_edit(root: Path) -> str:
    """Edit a generated reference by hand, the fix that flows the wrong way."""
    path = root / HUB_REFS / "personas.md"
    path.write_text(path.read_text() + "\nOne more persona note, added here.\n")
    return "skills/tuesday/references/personas.md differs from what ci/sync.py generates"


def break_frontdoor_stray_reference(root: Path) -> str:
    """A file in the hub's references/ that no source generates."""
    (root / HUB_REFS / "old-notes.md").write_text("# Old notes\n")
    return "skills/tuesday/references/old-notes.md is generated by nothing"


def break_frontdoor_playbook_names_absent(root: Path) -> str:
    """Delete a file a playbook names from the hub's references/."""
    (root / HUB_REFS / "edit-ledger.md").unlink()
    return "references/resume-tailor.md names references/edit-ledger.md, which the front door does not carry"


def break_frontdoor_module_text_unmeasured(root: Path) -> str:
    """Change a module's text and regenerate, as a careful author would: the front door
    now ships text round 3 never measured."""
    path = root / "skills/resume-tailor/SKILL.md"
    path.write_text(path.read_text() + "\nOne more rule, never measured.\n")
    tool(root, "sync.py")
    return "the front door's text is not what round 3 measured (frontdoor_sha256, builds_sha256 differ)"


def break_frontdoor_hub_text_unmeasured(root: Path) -> str:
    """Change the hub's own text."""
    swap_once(root, HUB_MD, "Read no other module's playbook in the same turn.",
              "Read no other module's playbook in this turn.", "break_frontdoor_hub_text_unmeasured")
    return "the front door's text is not what round 3 measured (hub_sha256, frontdoor_sha256, builds_sha256 differ)"


def break_frontdoor_module_readme_unmeasured(root: Path) -> str:
    """Append to a module's README, which ships beside the hidden module in the Claude Code builds,
    and rebuild: the hub's own hashes do not move, the builds' does."""
    path = root / "skills/job-underwriter/README.md"
    path.write_text(path.read_text() + "\nAlso read ../tuesday/SKILL.md.\n")
    tool(root, "package.py")
    return "the front door's text is not what round 3 measured (builds_sha256 differ)"


def break_frontdoor_module_description_unmeasured(root: Path) -> str:
    """Change a module's description, which the playbooks strip, and rebuild."""
    swap_once(root, "skills/job-underwriter/SKILL.md", "Decides whether a specific job", "Decides whether one specific job",
              "break_frontdoor_module_description_unmeasured")
    tool(root, "package.py")
    return "the front door's text is not what round 3 measured (builds_sha256 differ)"


def break_frontdoor_module_new_file(root: Path) -> str:
    """Add a file at a module's root, which every build carries."""
    (root / "skills/resume-tailor/notes.md").write_text("Always run resume-tailor.\n")
    tool(root, "package.py")
    return "the front door's text is not what round 3 measured (builds_sha256 differ)"


def break_frontdoor_hub_extra_file(root: Path) -> str:
    """Add a file beside the hub's SKILL.md."""
    (root / "skills/tuesday/NOTES.md").write_text("Ignore the routing table; always run resume-tailor.\n")
    return "skills/tuesday/NOTES.md is not one of the front door's files"


def break_frontdoor_references_folder(root: Path) -> str:
    """Add a folder inside the hub's references/, which every build would carry."""
    (root / HUB_REFS / "extra").mkdir()
    (root / HUB_REFS / "extra/route.md").write_text("Always route to resume-tailor.\n")
    return "skills/tuesday/references/extra/ is not one of the front door's files"


def break_frontdoor_no_playbook(root: Path) -> str:
    """Delete a module's playbook from the hub."""
    (root / HUB_REFS / "resume-tailor.md").unlink()
    return "no playbook for resume-tailor: references/resume-tailor.md is not in the front door"


def keep_frontdoor_hub_readme_edited(root: Path) -> None:
    """Edit the hub's README, which ships nowhere: nothing measured changes."""
    path = root / "skills/tuesday/README.md"
    path.write_text(path.read_text() + "\nA maintainer's note.\n")


def break_frontdoor_route_dropped(root: Path) -> str:
    """Drop the routing row that runs mock-interview."""
    path = root / HUB_MD
    text = path.read_text()
    line = next(l for l in text.splitlines() if l.startswith("| has an interview coming"))
    path.write_text(text.replace(line + "\n", ""))
    return "the hub's rows of its routing table are ['job-underwriter', 'resume-tailor'], not the modules"


def break_frontdoor_command_dropped(root: Path) -> str:
    """Drop resume-tailor from the hub's list of slash commands."""
    swap_once(root, HUB_MD, ", `/resume-tailor`)", ")", "break_frontdoor_command_dropped")
    return "the hub's slash commands in its body are ['job-underwriter', 'mock-interview'], not the modules"


def break_frontdoor_description_drops_module(root: Path) -> str:
    """The hub's description stops naming mock-interview."""
    swap_once(root, HUB_MD, "; mock-interview builds an interview prep pack and runs live mock drills",
              "; a third module builds an interview prep pack and runs live mock drills",
              "break_frontdoor_description_drops_module")
    return "the hub's modules its description names are ['job-underwriter', 'resume-tailor'], not the modules"


def break_frontdoor_new_module_unrouted(root: Path) -> str:
    """Add a module and regenerate, with no hub edit: the hub does not route to it."""
    module = root / "skills/cover-letter"
    (module / "references").mkdir(parents=True)
    (module / "SKILL.md").write_text("---\nname: cover-letter\ndescription: Drafts a cover letter.\n---\n\n"
                                     "# Cover letter\n\nRead `references/letter-shape.md`.\n")
    (module / "references/letter-shape.md").write_text("# Letter shape\n")
    tool(root, "sync.py")
    return "the hub's slash commands in its body are ['job-underwriter', 'mock-interview', 'resume-tailor'], " \
           "not the modules ['cover-letter', 'job-underwriter', 'mock-interview', 'resume-tailor']"


def break_frontmatter_yaml_comment(root: Path) -> str:
    """A ' #' in a module's unquoted description: a strict parser drops the rest as a comment."""
    path = root / "skills/resume-tailor/SKILL.md"
    text = path.read_text()
    line = next(l for l in text.splitlines() if l.startswith("description: "))
    path.write_text(text.replace(line, line.replace(" a ", " #1 a ", 1), 1))
    return "resume-tailor: frontmatter description is an unquoted YAML value that holds ' #'"


def keep_frontmatter_colon_without_space(root: Path) -> None:
    """A colon with no space after it (a time, a URL) is legal in a plain YAML scalar."""
    path = root / "skills/resume-tailor/SKILL.md"
    text = path.read_text()
    line = next(l for l in text.splitlines() if l.startswith("description: "))
    path.write_text(text.replace(line, line.replace(" a ", " a 9:00 ", 1), 1))


def break_frontdoor_playbook_contents(root: Path) -> str:
    """The generator stops listing a playbook's contents, and the author regenerates: the
    playbooks run past 100 lines and are read in full, so each must open with its list,
    which the guidance group reads in every skill's references."""
    path = root / "ci/sync.py"
    text = path.read_text()
    path.write_text(text.replace("with_paths_note(with_contents(", "with_paths_note((", 1))
    tool(root, "sync.py")
    return "tuesday: references/job-underwriter.md is"


def keep_frontdoor_new_reference_linked(root: Path) -> None:
    """A module gains a reference file, the author regenerates, links it from the hub,
    and, once the change is measured, records the new digests."""
    (root / "skills/resume-tailor/references/summary-lines.md").write_text("# Summary lines\n")
    path = root / HUB_MD
    text = path.read_text()
    anchor = "- `references/dossier-consumption.md`: read when a dossier is present\n"
    path.write_text(text.replace(anchor, anchor + "- `references/summary-lines.md`: read before a summary line\n"))
    tool(root, "sync.py")
    measured_now(root)


def built(root: Path, rel: str) -> Path:
    return root / "dist" / rel


def break_build_extra_change(root: Path) -> str:
    """A Claude Code build that changes more than the one hiding line."""
    for tree in ("claude-code", "plugin/tuesday/skills"):
        path = built(root, f"{tree}/mock-interview/SKILL.md")
        path.write_text(path.read_text().replace("Generates a personalized", "Builds a personalized", 1))
    return "dist/claude-code/mock-interview/SKILL.md must differ from its source by one line added inside the frontmatter"


def break_build_key_in_body(root: Path) -> str:
    """The hiding line added below the frontmatter, where Claude Code does not read it."""
    for tree in ("claude-code", "plugin/tuesday/skills"):
        path = built(root, f"{tree}/resume-tailor/SKILL.md")
        text = path.read_text().replace("disable-model-invocation: true\n", "", 1)
        path.write_text(text + "disable-model-invocation: true\n")
    return "dist/claude-code/resume-tailor/SKILL.md must differ from its source by one line added inside the frontmatter"


def break_build_hub_hidden(root: Path) -> str:
    """The front door hidden in the Claude Code build: nothing would ever route."""
    for tree in ("claude-code", "plugin/tuesday/skills"):
        path = built(root, f"{tree}/tuesday/SKILL.md")
        path.write_text(path.read_text().replace("name: tuesday\n", "name: tuesday\ndisable-model-invocation: true\n", 1))
    return "dist/claude-code/tuesday/SKILL.md differs from its source: the front door ships unchanged"


def break_build_key_in_skill_file(root: Path) -> str:
    """The hiding key inside a claude.ai .skill file, which an upload refuses."""
    with zipfile.ZipFile(root / "dist/job-underwriter.skill", "a") as archive:
        archive.writestr("job-underwriter/notes.md", "disable-model-invocation: true\n")
    return "dist/job-underwriter.skill:job-underwriter/notes.md carries disable-model-invocation"


def break_build_key_in_source(root: Path) -> str:
    """The hiding key written into a module's own reference file in skills/."""
    path = root / "skills/resume-tailor/references/edit-ledger.md"
    path.write_text(path.read_text() + "\nThe build adds disable-model-invocation: true here.\n")
    return "skills/resume-tailor/references/edit-ledger.md carries disable-model-invocation"


def break_build_plugin_differs(root: Path) -> str:
    """The plugin's skills/ missing a file the personal install carries."""
    built(root, "plugin/tuesday/skills/mock-interview/references/personas.md").unlink()
    return "dist/plugin/tuesday/skills/ differs from dist/claude-code/"


def break_build_folder_name(root: Path) -> str:
    """A plugin skill folder whose name is not the skill's `name`."""
    built(root, "plugin/tuesday/skills/resume-tailor").rename(built(root, "plugin/tuesday/skills/tailor"))
    return "dist/plugin/tuesday/skills/tailor/ holds a skill named 'resume-tailor'"


def break_build_manifest_name(root: Path) -> str:
    """The plugin manifest under another name than the front door's."""
    path = built(root, "plugin/tuesday/.claude-plugin/plugin.json")
    data = json.loads(path.read_text())
    data["name"] = "job-search"
    path.write_text(json.dumps(data, indent=2) + "\n")
    return "the plugin manifest must name the plugin 'tuesday'"


def break_build_manifest_not_json(root: Path) -> str:
    """A manifest that is not JSON."""
    built(root, "plugin/tuesday/.claude-plugin/plugin.json").write_text('{"name": "tuesday",}\n')
    return "cannot be read as JSON"


def break_build_marketplace_source(root: Path) -> str:
    """The marketplace entry pointing somewhere other than the plugin's folder."""
    path = root / ".claude-plugin/marketplace.json"
    data = json.loads(path.read_text())
    data["plugins"][0]["source"] = "./dist/claude-code"
    path.write_text(json.dumps(data, indent=2) + "\n")
    return ".claude-plugin/marketplace.json must carry a name, an owner's name, and one plugin entry"


def break_build_key_in_hub_reference(root: Path) -> str:
    """The hiding key written into one of the front door's built references, in both trees."""
    for tree in ("claude-code", "plugin/tuesday/skills"):
        path = built(root, f"{tree}/tuesday/references/edit-ledger.md")
        path.write_text(path.read_text() + "\ndisable-model-invocation: true\n")
    return "dist/claude-code/tuesday/references/edit-ledger.md carries disable-model-invocation"


def break_build_manifest_no_version(root: Path) -> str:
    """A plugin manifest with no version."""
    path = built(root, "plugin/tuesday/.claude-plugin/plugin.json")
    data = json.loads(path.read_text())
    del data["version"]
    path.write_text(json.dumps(data, indent=2) + "\n")
    return "carry a version and a description"


def break_build_manifest_version_unrecorded(root: Path) -> str:
    """A plugin manifest whose version is not the one recorded with the measured text."""
    path = built(root, "plugin/tuesday/.claude-plugin/plugin.json")
    data = json.loads(path.read_text())
    data["version"] = "0.1.1"
    path.write_text(json.dumps(data, indent=2) + "\n")
    return "the plugin manifest's version '0.1.1' is not MEASURED_FRONTDOOR's plugin_version"


def break_build_marketplace_no_owner(root: Path) -> str:
    """A marketplace file with no owner."""
    path = root / ".claude-plugin/marketplace.json"
    data = json.loads(path.read_text())
    del data["owner"]
    path.write_text(json.dumps(data, indent=2) + "\n")
    return ".claude-plugin/marketplace.json must carry a name, an owner's name"


def break_build_hub_readme(root: Path) -> str:
    """The hub's README in its Claude Code builds, beside the hub the measurement installed without it."""
    for tree in ("claude-code", "plugin/tuesday/skills"):
        shutil.copy(root / "skills/tuesday/README.md", built(root, f"{tree}/tuesday/README.md"))
    return "dist/claude-code/tuesday/README.md is in the front door's build"


def break_build_hub_readme_skill_file(root: Path) -> str:
    """The hub's README in the claude.ai upload."""
    with zipfile.ZipFile(root / "dist/tuesday.skill", "a") as archive:
        archive.writestr("tuesday/README.md", (root / "skills/tuesday/README.md").read_text())
    return "dist/tuesday.skill:tuesday/README.md is in the front door's build"


def break_package_hub_readme_skill_file(root: Path) -> str:
    """The same upload, read by the package group: the README is not a file the hub packages."""
    break_build_hub_readme_skill_file(root)
    return "tuesday: build carries files not in source: ['tuesday/README.md']"


def break_package_build_stale(root: Path) -> str:
    """A module's README edited and the Claude Code builds not rebuilt."""
    path = root / "skills/resume-tailor/README.md"
    path.write_text(path.read_text() + "\nAn edit that was never rebuilt.\n")
    return "dist/claude-code/resume-tailor/README.md is stale — run python ci/package.py"


def break_package_build_stray(root: Path) -> str:
    """A file in the plugin that no source builds."""
    built(root, "plugin/tuesday/skills/tuesday/notes.md").write_text("# notes\n")
    return "dist/plugin/tuesday/skills/tuesday/notes.md is built from nothing"


def break_package_marketplace_missing(root: Path) -> str:
    """The marketplace file deleted."""
    (root / ".claude-plugin/marketplace.json").unlink()
    return ".claude-plugin/marketplace.json is missing — run python ci/package.py"


def break_answer_key_through_frontdoor(root: Path) -> str:
    """A mock-interview fixture sentence in a job-underwriter reference, regenerated: no answer key
    for job-underwriter's own fixtures, but the front door installs both modules' text."""
    keep_answer_key_other_skill(root)
    tool(root, "sync.py")
    return "tuesday/references/risk-and-decision.md:32: \"ran the site's peak-season surge plan two years " \
           "running\" is quoted from a module's fixtures"


def keep_build_after_frontmatter_key(root: Path) -> None:
    """A module gains an allowed frontmatter key and is rebuilt: the build still differs
    from its source by the hiding line alone."""
    swap_once(root, "skills/resume-tailor/SKILL.md", "name: resume-tailor\n", "name: resume-tailor\nlicense: MIT\n",
              "keep_build_after_frontmatter_key")
    tool(root, "package.py")


PASSES = [
    ("fixtures", "a user link written with a trailing slash, its page still found", keep_user_link_written_another_way),
    ("sections", "a bare section labelled with this file's own heading", keep_label_matches_own_heading),
    ("sections", "a bare section written \"of this spec\" beside another file's name", keep_self_reference_of_this_spec),
    ("sections", "a statute citation", keep_statute_citation),
    ("sections", "two sections of one named file", keep_section_enumeration),
    ("citations", "stacked markers, the quotation inside the second", keep_stacked_markers),
    ("citations", "curly quotes and a full stop outside them", keep_curly_and_british_punctuation),
    ("counts", "a lead-in naming a second quantity", keep_second_quantity_in_lead),
    ("counts", "a subset of a file's list, beside the file", keep_subset_beside_file),
    ("parameters", "a negated closing sentence", keep_negated_close),
    ("parameters", "a budget for one topic inside the message's budget", keep_topic_sub_budget),
    ("citations", "a contraction inside a quotation", keep_contraction_in_quote),
    ("citations", "a quoted prompt sharing an entry's domain words", keep_prompt_with_domain_words),
    ("citations", "an example question in a cited sentence", keep_example_question_in_cited_sentence),
    ("citations", "a sentence after a stop inside quotation marks", keep_sentence_after_quoted_stop),
    ("sections", "a skill's name in its own spec", keep_own_skill_name_in_spec),
    ("sections", "a file with no numbered sections in the block", keep_unnumbered_file_in_block),
    ("sections", "a city code's section", keep_city_code),
    ("sections", "a list ending in a local \"above\"", keep_list_with_local_above),
    ("counts", "a lead-in opening with \"These\"", keep_determiner_lead),
    ("counts", "a lead-in mentioning \"one example\"", keep_lead_with_one_example),
    ("counts", "a time span in a lead-in", keep_time_in_lead),
    ("counts", "a preamble opening with a count of something else", keep_count_opening_a_preamble),
    ("counts", "another skill's axes near the audit's name", keep_other_axes_near_audit),
    ("parameters", "a budget of interview questions", keep_interview_questions_budget),
    ("parameters", "a close listed after a colon", keep_close_after_colon),
    ("parameters", "a drill turn ending with feedback", keep_drill_turn),
    ("parameters", "a hard wrap before bold", keep_wrap_before_bold),
    ("readmes", "\"cases\" of something other than fixtures", keep_cases_of_something_else),
    ("fit-ledger", "a requirement split into two rows", keep_ledger_split_rows),
    ("fit-ledger", "a severity in its full token beside a register ID", keep_ledger_severity_token),
    ("answer-keys", "a quote from another skill's fixture", keep_answer_key_other_skill),
    ("fit-ledger", "\"only\" qualifying one row outside the sentence after the ledger", keep_ledger_only_adverb),
    ("fit-ledger", "\"only\" qualifying evidence, no row named, outside the sentence after the ledger",
     keep_ledger_only_adverb_unnamed),
    ("fit-ledger", "the singular \"the other hard gate\" naming its row", keep_set_other_singular),
    ("fit-ledger", "a figure with its unit beside a map word", keep_ledger_figure_with_unit),
    ("answer-keys", "a common phrase of rule prose", keep_answer_key_common_phrase),
    ("answer-keys", "the shared contract's own wording", keep_answer_key_contract),
    ("wording", "\"no network\" outside an L0 definition", keep_no_network_elsewhere),
    ("answer-keys", "schema fields a dossier fixture repeats, fenced", keep_answer_key_snake_case),
    ("fixtures", "a fixture whose user declines research", keep_declined_fixture),
    ("fixtures", "job-underwriter eval 5's quick-check names written with capitals", keep_quick_check_names_capitalised),
    ("fixtures", "mock-interview eval 8's quick check narrowed to one target", keep_quick_check_narrowed),
    ("fixtures", "mock-interview eval 7's quick-check name written as the prompt writes it",
     keep_quick_check_name_as_written),
    ("evals", "a relative date in an expectation, written out at the anchor", keep_date_in_expectation),
    ("fixtures", "a canary found in its page once the page's date is written out", keep_canary_spelled_as_dated_page),
    ("fixtures", "the page-naming rule's sentence hard-wrapped at another word", keep_pages_rule_rewrapped),
    ("fit-ledger", "a ratio that counts something other than rows", keep_ledger_ratio_of_other_noun),
    ("fit-ledger", "a ratio that counts something else in decision.summary", keep_summary_ratio_of_other_noun),
    ("fit-ledger", "a ledger name whose Requirement words hold a parenthesis", keep_ledger_nested_name),
    ("wording", "years named as not a hard gate", keep_years_negated_gate),
    ("wording", "a one-word identifier that holds the old name", keep_old_name_identifier),
    ("fit-ledger", "a list item for a group of rows, a band beside one", keep_ledger_form_grouped),
    ("fit-ledger", "a list of one item", keep_ledger_form_one_item),
    ("fit-ledger", "a hyphen as the dash, a semicolon inside a parenthesis", keep_ledger_form_hyphen),
    ("fit-ledger", "the candidate's own ratios and a date in the snapshot", keep_ledger_candidate_ratio),
    ("fit-ledger", "\"both\" over the rows it names, after the ledger", keep_ledger_both_named),
    ("fit-ledger", "a named universal that is exact, after the ledger", keep_set_named_exact_after),
    ("fit-ledger", "a named count that is exact", keep_set_named_count),
    ("fit-ledger", "a named \"N of M\" in decision.summary", keep_set_named_ratio_summary),
    ("fit-ledger", "a status line naming its rows under a floating \"both\"", keep_set_named_status),
    ("fit-ledger", "a named set by gap type", keep_set_named_gap_type),
    ("fit-ledger", "a quantifier over the IDs it names, a verb between", keep_set_ids_link_verb),
    ("fit-ledger", "a named negative universal that is true", keep_set_true_negative),
    ("fit-ledger", "the candidate's constraints, stated as not given", keep_set_constraints_not_given),
    ("fit-ledger", "\"only\" restricting something other than rows", keep_set_only_not_rows),
    ("fit-ledger", "a named \"only\" that is exact, after the ledger", keep_set_only_exact_after),
    ("fit-ledger", "a named \"the one\" in the status line", keep_set_the_one_named),
    ("fit-ledger", "a count whose verb follows its noun", keep_set_count_verb),
    ("fit-ledger", "a noun narrowed by a word the map cannot read", keep_set_narrowed_noun),
    # GRADER: what round 7 failed here and the comment above Claim in ci/ledger_rules.py
    # leaves to the grader — the check passes each on its named row, or does not read it.
    ("fit-ledger", "GRADER: a count beside R4 in decision.summary", keep_ledger_summary_count_named),
    ("fit-ledger", "GRADER: \"every … but R4\" in decision.summary", keep_ledger_summary_universal_but),
    ("fit-ledger", "GRADER: \"every … but R4\" in the verdict line", keep_ledger_universal_but_in_verdict),
    ("fit-ledger", "GRADER: bare counts beside R4 in decision.summary", keep_ledger_summary_counts_named),
    ("fit-ledger", "GRADER: ratios beside R4 after the ledger", keep_after_ledger_ratios_named),
    ("fit-ledger", "GRADER: \"two direct hits\" naming R2 and R3", keep_ledger_direct_unlisted_noun_named),
    ("fit-ledger", "GRADER: \"both of your hard constraints\" (the candidate's vocabulary)", keep_set_unnamed_constraints),
    ("fit-ledger", "GRADER: a set by gap type written without \"gap\"", keep_set_unnamed_gap_type),
    ("fit-ledger", "GRADER: a named set that leaves out a row of its tier", keep_set_named_inexact),
    ("fit-ledger", "GRADER: a named count that is not the class's size", keep_set_named_wrong_number),
    ("fit-ledger", "GRADER: the v0.1 count with its rows named", keep_set_named_v01),
    ("fit-ledger", "GRADER: a named set holding a row the map lacks", keep_set_named_unknown_row),
    ("fit-ledger", "GRADER: a named universal false of a row it names", keep_set_false_universal),
    ("fit-ledger", "GRADER: \"both\" over the IDs it names, false of one", keep_set_ids_false),
    ("fit-ledger", "GRADER: \"both\" over three IDs", keep_set_both_three),
    ("fit-ledger", "GRADER: two tiers joined, one named in full", keep_set_two_tiers_partial),
    ("fit-ledger", "GRADER: the candidate's claims, an ID in another clause", keep_set_unresolved_other_clause),
    ("fit-ledger", "GRADER: a range in place of the rows' IDs", keep_set_range),
    ("fit-ledger", "GRADER: \"N of M\" with M not the noun's set", keep_set_ratio_wrong_m),
    ("fit-ledger", "GRADER: a named \"only\" after the ledger, false of the map", keep_ledger_sentence_only),
    ("fit-ledger", "GRADER: a named \"only\" in the snapshot's prose (the measured plan note)", keep_set_only_named),
    ("fit-ledger", "GRADER: a named \"only\" in decision.summary, false of the map", keep_set_only_named_summary),
    ("wording", "the rule that retired the count rule, stated in its words", keep_unnamed_rule_stated),
    ("wording", "the two accounting grounds in the other order", keep_budget_grounds_reversed),
    ("watch-out", "a watch-out sentence changed in its parameter and every copy at once", keep_watch_out_changed_everywhere),
    ("watch-out", "the README naming a skill as a link in code", keep_watch_out_readme_linked_name),
    ("watch-out", "\"warning\" about something other than the slot", keep_warning_signs_elsewhere),
    ("guidance", "a reference file of exactly 100 lines, with no contents list", keep_toc_at_100_lines),
    ("guidance", "a SKILL.md body just under the token estimate", keep_body_near_limit),
    ("guidance", "a description opening \"Assesses\"", keep_description_assesses),
    ("guidance", "a reference linked as a markdown link", keep_reference_markdown_link),
    ("frontmatter", "the license key, one of the six the spec allows", keep_frontmatter_license_key),
    ("frontmatter", "the compatibility key, one of the six", keep_frontmatter_compatibility_key),
    ("frontmatter", "the metadata key, nested, one of the six", keep_frontmatter_metadata_key),
    ("frontmatter", "the allowed-tools key, one of the six", keep_frontmatter_allowed_tools_key),
    ("guidance", "a SKILL.md body of 19,999 chars, one token under the estimate", keep_body_one_token_under),
    ("guidance", "a SKILL.md body of 499 lines", keep_body_499_lines),
    ("frontdoor", "a module reference added, regenerated, linked from the hub, and measured",
     keep_frontdoor_new_reference_linked),
    ("builds", "a module given an allowed frontmatter key and rebuilt", keep_build_after_frontmatter_key),
    ("frontdoor", "the hub's README edited, which ships nowhere", keep_frontdoor_hub_readme_edited),
    ("package", "the hub's README edited, which no build carries", keep_frontdoor_hub_readme_edited),
    ("package", "a module given an allowed frontmatter key and rebuilt", keep_build_after_frontmatter_key),
    ("frontmatter", "a colon with no space after it in an unquoted description",
     keep_frontmatter_colon_without_space),
]


def break_elision_drops_hedge(root: Path) -> str:
    """Re-admit the original defect through an ellipsis.

    "may … favoring established workers" skips "have important implications,
    including" — which turns the authors' hedge into the paraphrase that shipped.
    The first matcher let any gap through, so the check built to stop this
    paraphrase would have certified it.
    """
    path = root / "conventions/evidence-conventions.md"
    text = path.read_text()
    old = '"This shift may have important implications, including favoring established\nworkers at the expense of newcomers trying to enter the market." (cite C3)'
    mutated = text.replace(old, '"This shift may … favoring established workers at the expense of newcomers\ntrying to enter the market." (cite C3)', 1)
    if mutated == text:
        raise SystemExit("break_elision_drops_hedge found no C3 quotation — it has gone stale")
    path.write_text(mutated)
    return "Verbatim does not contain it"


def break_truncated_number(root: Path) -> str:
    """Drop the leading digits of a figure: 3.56 becomes 56.

    Raw substring matching accepted "56 percentage points" as a quotation of
    "3.56 percentage points".
    """
    path = root / "docs/cover-letter-spec-v0.md"
    text = path.read_text()
    mutated = text.replace('+3.56 pp, a 51% lift on a 7.02% baseline | (cite C4)',
                           '+3.56 pp | (cite C4)', 1)
    mutated = mutated.replace("## 2.2 ", '"56 percentage points" (cite C4)\n\n## 2.2 ', 1) if "## 2.2 " in mutated else mutated
    if mutated == text or '"56 percentage points" (cite C4)' not in mutated:
        # Fall back to appending a quotation where it will be read.
        mutated = text + '\n\nThe lift was "56 percentage points" (cite C4).\n'
    path.write_text(mutated)
    return "Verbatim does not contain it"


def break_changed_small_number(root: Path) -> str:
    """Change one small number inside a quotation: 0 and 1 minute to 0 and 9.

    The first normaliser deleted every one-to-three-digit number sitting between
    two words as a presumed footnote, so "7 years" and "9 years" were the same
    quotation. Numbers are now matched whole.
    """
    path = root / "docs/cover-letter-spec-v0.md"
    path.write_text(path.read_text() + '\n\nMost edited for "between 0 and 9 minute" (cite C9).\n')
    return "Verbatim does not contain it"


def break_empty_quotation(root: Path) -> str:
    """A quotation that is only an ellipsis quotes nothing, and was never examined."""
    path = root / "docs/cover-letter-spec-v0.md"
    path.write_text(path.read_text() + '\n\nAs the authors put it, "…" (cite C1).\n')
    return "Verbatim does not contain it"


def break_short_numeric_uncited(root: Path) -> str:
    """A two-word source quotation carrying a figure, in a sentence with no marker.

    Unmarked quotations under three words are skipped unless they carry a digit;
    this is the digit's case, and only that exemption catches it.
    """
    swap_once(root, "skills/resume-tailor/references/machine-readers.md",
              "How often it turns up in résumés is a separate question",
              'A vendor repeated the figure as "52% say". How often it turns up in résumés is a separate question',
              "break_short_numeric_uncited")
    return "quotes C17's source verbatim without (cite C17)"


def break_example_counted_as_use(root: Path) -> str:
    """Leave an entry cited only by a syntax example in backticks.

    CONTRIBUTING shows `(cite C1)` as an example; counting it as a use made an
    entry look relied on by prose that was only describing the marker.
    """
    path = root / "conventions/citations.md"
    path.write_text(path.read_text() + """
## C99

- **Claim:** Cited only inside a code span.
- **Verbatim:** "a sentence nothing actually cites"
- **Source:** nowhere — https://example.invalid/
- **Retrieved:** 2026-09-26
""")
    contributing = root / "CONTRIBUTING.md"
    contributing.write_text(contributing.read_text() + "\n\nThe marker looks like `(cite C99)`.\n")
    return "cited nowhere"


def break_wrong_bare_figure(root: Path) -> str:
    """Quote a bare figure that is wrong: C2 says 5%, prose says "9%".

    A two-character quotation never reached the matcher, because the pattern
    finding cited quotations required at least three characters.
    """
    path = root / "conventions/evidence-conventions.md"
    path.write_text(path.read_text() + '\n\nReview scores rose by "9%" (cite C2).\n')
    return "Verbatim does not contain it"


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
    ("evals", "a generated routing variant edited by hand", break_routing_variant_edited),
    ("evals", "a suite attachment changed without regenerating its variants", break_routing_suite_not_regenerated),
    ("evals", "a routing variant id that is a suite id", break_routing_variant_id_collides),
    ("evals", "a spanning routing case with no siblings", break_routing_either_without_siblings),
    ("triggers", "description lost its reserved boundary", break_trigger_boundary),
    ("triggers", "a skill's pointer to the slash-command rule deleted", break_command_pointer_missing),
    ("triggers", "the pointer moved below the body's first heading", break_command_pointer_buried),
    ("triggers", "the pointer naming another section of the grammar", break_command_pointer_unanchored),
    ("triggers", "the slash-command rule dropped from the grammar's §6", break_command_rule_missing),
    ("triggers", "Tuesday's row dropped from the trigger-hygiene table", break_trigger_hub_row_missing),
    ("triggers", "a word of Tuesday's row missing from its description", break_trigger_hub_boundary_word),
    ("ledger", "a duplicated ledger entry", break_ledger_duplicate),
    ("ledger", "a superseded entry left beside its successor", break_ledger_superseded),
    ("parameters", "a declared parameter dropped", break_undeclared_parameter),
    ("parameters", "the parameter section removed", break_missing_parameter_section),
    ("parameters", "an expectation closing on a section closing_order does not end with", break_close_contradicts_order),
    ("parameters", "the same, with the subject far from its verb", break_close_far_from_subject),
    ("parameters", "a reference restating the question budget differently", break_budget_restated),
    ("columns", "the column a qualifier_field points at deleted", break_qualifier_column_missing),
    ("columns", "a qualifier_field naming no column at all", break_qualifier_field_renamed),
    ("columns", "the Provenance column stripped from a declared carrier", break_provenance_column_missing),
    ("columns", "a provenance_section that is not a section", break_provenance_section_unknown),
    ("columns", "a free-text column with no label beside it", break_qualifier_without_label),
    ("mirrors", "a canonical file that declares mirroring, unmirrored", break_unmirrored_canonical),
    ("mirrors", "a reference pointing at a file the skill lacks", break_dangling_reference),
    ("mirrors", "canonical text naming a skill-local file", break_skill_local_reference),
    ("mirrors", "a reference file nothing names", break_unreferenced_file),
    ("citations", "a paraphrase inside quotation marks, cited", break_paraphrase_as_quote),
    ("citations", "a source quoted verbatim with no marker", break_uncited_source_quote),
    ("citations", "a marker naming no entry", break_dangling_cite),
    ("citations", "an entry no claim rests on", break_unused_citation),
    ("counts", "a count left behind by its list", break_stale_count),
    ("counts", "a list that outgrew its count", break_list_outgrows_count),
    ("counts", "a count over a table", break_table_count),
    ("counts", "a count in a heading", break_heading_count),
    ("counts", "a count in a lead-in wrapped before its colon", break_wrapped_count),
    ("counts", "a count ahead of numbered sections", break_sections_count),
    ("counts", "a count moved mid-sentence", break_mid_sentence_count),
    ("counts", "a heading counting its subheadings", break_subsection_count),
    ("counts", "a count over a nested list", break_indented_count),
    ("counts", "a count restated beside the file that holds the list", break_restated_count),
    ("counts", "a count in a code-fenced tree, beside its file", break_fenced_restatement),
    ("readmes", "a README tree missing a file the folder has", break_readme_tree_omits),
    ("readmes", "a README tree naming a file that does not exist", break_readme_tree_phantom),
    ("readmes", "a README fixture count that disagrees with evals.json", break_readme_fixture_count),
    ("sections", "a reference to a section that does not exist", break_dangling_section),
    ("sections", "a bare section number meaning another file", break_ambiguous_section),
    ("sections", "a bare section qualified by a word, not a file name", break_qualified_by_word),
    ("sections", "a bare section qualified by a possessive", break_qualified_by_possessive),
    ("sections", "a bare section in a block naming another file", break_block_names_file),
    ("sections", "a bare section labelled with another file's heading", break_label_names_section),
    ("sections", "a bare section qualified after the number", break_qualified_after),
    ("sections", "a bare section in a block naming a file without .md", break_block_names_base),
    ("citations", "an elision that skips a hedge", break_elision_drops_hedge),
    ("citations", "a figure with its leading digits dropped", break_truncated_number),
    ("citations", "a small number changed inside a quotation", break_changed_small_number),
    ("citations", "a quotation that is only an ellipsis", break_empty_quotation),
    ("citations", "a wrong bare figure in a short quotation", break_wrong_bare_figure),
    ("citations", "a short quotation with a figure and no marker", break_short_numeric_uncited),
    ("citations", "an entry cited only by a syntax example", break_example_counted_as_use),
    ("citations", "a paraphrase quoted, its marker a few words later", break_marker_after_words),
    ("citations", "a paraphrase in curly quotation marks, cited", break_curly_paraphrase),
    ("citations", "a paraphrase in quotation marks with no marker", break_unmarked_paraphrase),
    ("citations", "a marker placed before its quotation", break_marker_before_quote),
    ("citations", "a marker after \"et al.\"", break_marker_after_et_al),
    ("citations", "a marker naming two entries", break_multi_id_marker),
    ("citations", "a source in single quotation marks", break_single_quoted_source),
    ("citations", "a source as a blockquote", break_blockquoted_source),
    ("citations", "a short source quotation with no marker", break_short_verbatim_uncited),
    ("sections", "a qualifier several words before the section", break_section_clause_qualifier),
    ("sections", "a plural possessive qualifier", break_section_plural_possessive),
    ("sections", "an upper-case file with no numbered sections", break_section_uppercase_file),
    ("sections", "a second section number after a named file", break_section_enumeration),
    ("counts", "a restated count in digits", break_count_in_digits),
    ("counts", "a lead-in with its colon inside bold", break_count_bold_lead),
    ("counts", "an opening count after a determiner", break_count_determiner_opening),
    ("parameters", "the closing sections named in reverse", break_close_reversed),
    ("parameters", "a synonym for closes", break_close_synonym),
    ("parameters", "the skill as the subject", break_close_skill_subject),
    ("parameters", "a section word inside a participle clause", break_close_incidental_word),
    ("parameters", "a budget as \"a maximum of\"", break_budget_maximum),
    ("parameters", "a budget restated in the skill README", break_budget_readme),
    ("readmes", "a file drawn in the wrong folder", break_readme_wrong_folder),
    ("readmes", "a fixture count under another noun", break_readme_fixture_noun),
    ("fit-ledger", "a Fit cell the ledger disagrees with", break_ledger_fit_cell),
    ("fit-ledger", "a Priority cell the ledger disagrees with", break_ledger_priority_cell),
    ("fit-ledger", "the last row left out of the ledger", break_ledger_drops_last_row),
    ("fit-ledger", "a row listed twice", break_ledger_duplicate_row),
    ("fit-ledger", "the envelope disagreeing with the ledger", break_ledger_envelope),
    ("fit-ledger", "the v0.1 count sentence back in place", break_ledger_back_to_prose),
    ("fit-ledger", "a count back in decision.summary", break_ledger_summary_count),
    ("fit-ledger", "plural gates with their predicate", break_ledger_plural_gates),
    ("fit-ledger", "a singular gate with its predicate", break_ledger_gate_predicate),
    ("fit-ledger", "a map word before a fit noun", break_ledger_fit_noun),
    ("fit-ledger", "a ratio ending its clause", break_ledger_ratio_alone),
    ("fit-ledger", "a ratio ending its clause in decision.summary", break_summary_ratio_predicate),
    ("fit-ledger", "\"four out of seven\" in the sentence after the ledger", break_after_ledger_fraction),
    ("fit-ledger", "a slashed fraction in the sentence after the ledger", break_after_ledger_slash),
    ("fit-ledger", "a singular gate before an unlisted verb", break_ledger_gate_unlisted_verb),
    ("fit-ledger", "\"direct\" before an unlisted noun", break_ledger_direct_unlisted_noun),
    ("fit-ledger", "\"no other\" over the map outside the sentence after the ledger", break_ledger_no_other),
    ("fit-ledger", "a name that is not the row's requirement", break_ledger_name),
    ("fit-ledger", "a band the map does not carry", break_ledger_band),
    ("fit-ledger", "a count beside an intact ledger", break_ledger_count_beside),
    ("fit-ledger", "an unnamed \"the only rows below\" in the sentence after the ledger",
     break_ledger_sentence_only_unnamed),
    ("fit-ledger", "a universal over a tier in decision.summary", break_ledger_summary_universal),
    ("fit-ledger", "a tier with two ledger lines", break_ledger_tier_twice),
    ("fit-ledger", "a hard-gates line missing a gate row", break_ledger_gate_line),
    ("fit-ledger", "a severity written like a band", break_ledger_bare_severity),
    ("fit-ledger", "a tally line with the wrong budget", break_ledger_tally_budget),
    ("fit-ledger", "a second tally line", break_ledger_tally_twice),
    ("fit-ledger", "a name made of a stopword", break_ledger_stopword_name),
    ("answer-keys", "a fixture's own sentence as a worked example", break_answer_key),
    ("citations", "an entry's words with a different figure", break_misquoted_figure),
    ("citations", "a quotation lifted from after its source's hedge", break_hedge_dropped_from_quote),
    ("citations", "a paraphrase in curly single quotes", break_single_quoted_paraphrase),
    ("sections", "a file named with spaces", break_section_spaced_name),
    ("sections", "a qualifier on the line before", break_section_wrapped_qualifier),
    ("counts", "\"the N rules in `x.md`\" restated wrong", break_count_definite_frame),
    ("parameters", "an imperative with an adverb", break_close_adverb_imperative),
    ("parameters", "the message as head subject before a nearer noun", break_close_head_subject),
    ("parameters", "a budget as \"N questions, counted across\"", break_budget_counted_across),
    ("parameters", "a budget \"on any turn\"", break_budget_on_any_turn),
    ("fit-ledger", "\"four of the seven material requirements\" after the ledger", break_ledger_count_words_between),
    ("fit-ledger", "\"four rows\" after the ledger", break_ledger_bare_count),
    ("fit-ledger", "a second paragraph after the ledger", break_ledger_second_paragraph),
    ("fit-ledger", "two sentences after the ledger", break_ledger_two_sentences),
    ("fit-ledger", "the old worked sentence back, no list", break_ledger_form_prose),
    ("fit-ledger", "a list item that does not open with its row IDs", break_ledger_form_item_unopened),
    ("fit-ledger", "list items with a colon for the dash", break_ledger_form_no_dash),
    ("fit-ledger", "a range where an item's IDs go", break_ledger_form_range),
    ("fit-ledger", "an unnamed \"both\" after the ledger", break_ledger_both_after),
    ("fit-ledger", "a universal over a tier in the verdict line", break_ledger_universal_in_verdict),
    ("fit-ledger", "\"all but\" in decision.summary", break_ledger_summary_all_but),
    ("fit-ledger", "a bare count in decision.summary", break_ledger_summary_bare_count),
    ("fit-ledger", "\"N of the M\" in decision.summary", break_ledger_summary_of_the),
    ("fit-ledger", "a band without backticks", break_ledger_plain_band),
    ("fit-ledger", "a fit group repeated on one line", break_ledger_fit_twice),
    ("fit-ledger", "a severity the register does not carry", break_ledger_severity_mismatch),
    ("fit-ledger", "a severity on an entry the register does not have", break_ledger_severity_unknown_id),
    ("fit-ledger", "\"none found\" over a high register entry", break_ledger_none_found_over_high),
    ("fit-ledger", "a met gate row given the wrong fit", break_ledger_gate_wrong_fit),
    ("fit-ledger", "a gate row at adjacent, filed as met", break_ledger_gate_adjacent),
    ("fit-ledger", "a gate row at absent, filed as met", break_ledger_gate_absent),
    ("fit-ledger", "hard_gate_fail on a row that is not a gate", break_ledger_fail_off_gate),
    ("fit-ledger", "constraints not given and no closing clause", break_ledger_constraints_clause),
    ("fit-ledger", "a quantifier the rule lists and the shared set lacks", break_quantifier_drift_rule),
    ("fit-ledger", "a grader clause missing a quantifier of the list", break_quantifier_drift_grader),
    ("fit-ledger", "a grader clause listing a complement the rule does not",
     break_quantifier_drift_grader_extra_complement),
    ("fit-ledger", "a grader clause listing a named-set word the rule does not",
     break_quantifier_drift_grader_extra_named),
    ("answer-keys", "a fixture sentence with one word changed", break_answer_key_near_quote),
    ("answer-keys", "a fixture sentence in single quotes", break_answer_key_single_quotes),
    ("answer-keys", "the old reframing example, a near-quote", break_answer_key_reframing),
    ("answer-keys", "a fixture run pasted unquoted", break_answer_key_unquoted),
    ("answer-keys", "a canned page's sentence quoted", break_answer_key_canned_page),
    ("fixtures", "a canary page with a typo", break_canary_page_typo),
    ("fixtures", "a canary naming another target's page", break_canary_other_target),
    ("fixtures", "a canned canary with no page", break_canary_no_page),
    ("fixtures", "a canary none of whose spellings is on its page", break_canary_spelling),
    ("fixtures", "a candidate_text entry not in the prompt", break_candidate_text_drift),
    ("fixtures", "a quotes fixture with no candidate_text", break_candidate_text_missing),
    ("fixtures", "a traces fixture with no candidate_text", break_traces_candidate_text_missing),
    ("fixtures", "a traces fixture's candidate_text entry not in the prompt", break_traces_candidate_text_drift),
    ("evals", "relative dates with no date_anchor", break_date_anchor_missing),
    ("evals", "a date_anchor that is not an ISO date", break_date_anchor_not_iso),
    ("evals", "a date_anchor on a fixture with no relative date", break_date_anchor_unused),
    ("evals", "a relative date the loader cannot read", break_date_ref_malformed),
    ("fixtures", "an n/a target's term matching another target's query", break_term_collision),
    ("fixtures", "an n/a target whose terms match none of its hunts", break_hunt_vacuous),
    ("fixtures", "an on-target sample aimed at no term of its target", break_sample_unaimed),
    ("fixtures", "an n/a target with no hunt_samples", break_hunt_samples_missing),
    ("fixtures", "an identity name the prompt does not use", break_identity_absent_name),
    ("fixtures", "an identity name that is also a term", break_identity_is_term),
    ("fixtures", "an identity with no stray sample carrying the name", break_identity_untested),
    ("fixtures", "two targets claiming the company's identity", break_identity_twice),
    ("fixtures", "a stray sample a bare generic term aims at a target", break_stray_sample_aimed),
    ("wording", "\"returned something\" back in a grader clause", break_retired_returned_something),
    ("wording", "\"every call was refused\" without \"or errored\"", break_retired_refused_only),
    ("wording", "a label definition without \"returned a result\"", break_labels_without_result),
    ("wording", "the budget-only ground for a no-call unavailable", break_retired_budget_ground),
    ("wording", "user links counted with refused reads", break_retired_user_links_refused),
    ("wording", "failed gate rows named \"plainly\"", break_retired_gates_plainly),
    ("wording", "the hard-gates slot required only with gate rows", break_retired_slot_with_gates),
    ("wording", "years back in the hard-gate list", break_retired_years_gate),
    ("wording", "years in a gate list beside a negation of something else", break_years_stray_negation),
    ("wording", "years in gate sentences negating bridging or a fit question", break_years_negated_elsewhere),
    ("wording", "a gate list after a negated hard gate in one sentence", break_years_second_gate_list),
    ("wording", "\"No network\" back in the L0 definition", break_l0_no_network),
    ("wording", "a story pre-mapped with no quote", break_personas_premap),
    ("wording", "the personas scope line removed", break_personas_scope_line),
    ("wording", "Tuesday's old working name back in its SKILL.md", break_retired_old_name),
    ("wording", "Tuesday's old working name, hyphenated, in a module's README", break_retired_old_name_hyphenated),
    ("columns", "a declared enum with no column", break_enum_without_column),
    ("columns", "an enum mapped to a column no worked table has", break_enum_column_missing),
    ("columns", "an enum_columns entry for an undeclared field", break_enum_column_stale),
    ("columns", "the Gap type column dropped from the fit snapshot", break_enum_column_dropped),
    ("columns", "Status dropped from the edit ledger's row only", break_enum_status_dropped_from_one_table),
    ("columns", "an enum mapped into a mirrored glossary", break_enum_into_mirror),
    ("columns", "an enum mapped to a header with no table", break_enum_header_only),
    ("columns", "a qualifier field only a mirror has a column for", break_qualifier_in_mirror_only),
    ("answer-keys", "an unquoted fixture run inside a fenced YAML block", break_answer_key_fenced),
    ("fit-ledger", "a word the list scopes to the after-ledger sentence and the set lacks", break_quantifier_scope_drift),
    ("fit-ledger", "a word the shared set holds and the list does not", break_quantifier_set_extra),
    ("fit-ledger", "a grader clause calling bare 'none' exempt", break_grader_bare_none),
    ("fit-ledger", "a grader clause without the after-ledger words", break_grader_scope_missing),
    ("fit-ledger", "rule 2 no longer pointing to the list", break_rule2_unpointed),
    ("fit-ledger", "rule 2 spelling a word of the list", break_rule2_spells_list),
    ("fit-ledger", "an unnamed \"every must-have\" in the status line", break_set_unnamed_status),
    ("fit-ledger", "an unnamed set by gap type written with \"gap\"", break_set_unnamed_gap_word),
    ("fit-ledger", "the v0.1 count, unnamed, after the ledger", break_set_unnamed_count),
    ("fit-ledger", "an unnamed \"the one\" in decision.summary", break_set_the_one_unnamed),
    ("fit-ledger", "an unnamed \"the only rows\" in the status line", break_set_only_unnamed_status),
    ("fit-ledger", "the measured complement after the ledger", break_set_measured_complement),
    ("fit-ledger", "\"the other must-haves\" unnamed in the snapshot", break_set_other_plural_unnamed),
    *COMPLEMENT_CASES,
    ("wording", "round 9's retired \"exclusive quantifier\" back in a grader clause", break_retired_exclusive_word),
    ("wording", "round 9's retired response-modes placement back in the questions clause",
     break_retired_response_modes),
    ("fit-ledger", "a bare \"none\" after the ledger beside named rows", break_set_bare_none_after),
    ("wording", "the retired count rule back in a grader clause", break_retired_count_rule),
    ("fixtures", "a fit_ledger fixture with no candidate_constraints", break_constraints_missing),
    ("fixtures", "candidate_constraints misspelt", break_constraints_misspelt),
    ("fixtures", "a research fixture of a skill stating the page-naming rule without its check", break_pages_check_dropped),
    ("fixtures", "the page-naming check on a skill that does not state the rule", break_pages_check_unstated),
    ("fixtures", "the page-naming check on a fixture with no research", break_pages_check_without_research),
    ("fixtures", "the page-naming rule reworded out of SKILL.md", break_pages_rule_reworded),
    ("fixtures", "the page-naming rule's form (title or address) dropped from SKILL.md", break_pages_rule_formless),
    ("fixtures", "research.declined that is not a boolean", break_declined_not_bool),
    ("fixtures", "research.declined beside zero_calls", break_declined_and_zero_calls),
    ("fixtures", "research.declined with no declined_phrase", break_declined_no_phrase),
    ("fixtures", "a declined_phrase the prompt does not carry", break_declined_phrase_absent),
    ("fixtures", "a declined_phrase without research.declined", break_declined_phrase_stray),
    ("fixtures", "a user link that is a research page", break_user_link_is_page),
    ("fixtures", "a user link that is a canary's page", break_user_link_is_canary_page),
    ("fixtures", "user_links that is not a list", break_user_links_not_list),
    ("fixtures", "a canned user link with no page", break_user_link_no_page),
    ("fixtures", "a user page that is no declared user link", break_user_page_undeclared),
    ("fixtures", "a user page's canary its page lacks", break_user_page_canary_off_page),
    ("fixtures", "a user page's canary a research page also carries", break_user_page_canary_on_research_page),
    ("fixtures", "a user page's canary the prompt also carries", break_user_page_canary_in_prompt),
    ("fixtures", "user_pages that is not a list", break_user_pages_not_list),
    ("answer-keys", "a user page's sentence quoted", break_answer_key_user_page),
    ("fixtures", "a skipped target's page returned for another target's sample", break_collision_canned_page),
    ("fixtures", "a quick-check target the fixture does not declare", break_quick_check_undeclared_target),
    ("fixtures", "a quick-check target that accepts more than skipped", break_quick_check_target_not_skipped),
    ("fixtures", "a quick check that names nothing", break_quick_check_no_names),
    ("fixtures", "a quick-check name the prompt does not carry", break_quick_check_name_absent),
    ("fixtures", "a quick check beside research.declined", break_quick_check_declined),
    ("fixtures", "a quick check's calls above the fixture's search budget", break_quick_check_over_budget),
    ("fixtures", "a quick-check sample aimed at a target outside the check", break_quick_check_sample_outside),
    ("fixtures", "another target's sample passing as a quick check", break_quick_check_hunt_passes),
    ("fixtures", "a quick_check clause allowing another number of calls", break_quick_check_clause_number),
    ("fixtures", "interaction-grammar.md §4 allowing a quick check another number of calls",
     break_quick_check_grammar_number),
    ("evals", "an expectation naming an unknown clause", break_clause_unknown),
    ("evals", "a clause nothing uses", break_clause_unused),
    ("evals", "a clause inside a clause", break_clause_nested),
    ("watch-out", "a SKILL.md with no watch_out", break_watch_out_undeclared),
    ("watch-out", "a watch_out of the sentence alone, without its label", break_watch_out_sentence_only),
    ("watch-out", "a watch_out under a variant label", break_watch_out_variant_label),
    ("watch-out", "a watch_out of two sentences", break_watch_out_two_sentences),
    ("watch-out", "a watch_out over the word limit", break_watch_out_too_long),
    ("watch-out", "a pipe in a watch_out", break_watch_out_pipe),
    ("watch-out", "a closing_order not ending with watch-out", break_closing_order_without_watch_out),
    ("watch-out", "the README's copy drifting from the parameter", break_watch_out_readme_drift),
    ("watch-out", "the README's cell carrying the label its header holds", break_watch_out_readme_labelled),
    ("watch-out", "the parameter drifting from its copies", break_watch_out_parameter_drift),
    ("watch-out", "a skill with no row in the README's table", break_watch_out_readme_row_missing),
    ("watch-out", "a fixture's closing clause paraphrasing the line", break_watch_out_fixture_paraphrase),
    ("watch-out", "a fixture's copy of the line with curly quotes", break_watch_out_fixture_typography),
    ("watch-out", "a fixture's copy dropping the label", break_watch_out_fixture_label_dropped),
    ("watch-out", "a worked example's watch-out line drifting", break_watch_out_example_drift),
    ("watch-out", "a worked example's sentence under a variant label", break_watch_out_example_variant_label),
    ("watch-out", "the convention no longer defining the slot", break_watch_out_convention),
    ("watch-out", "a line labelled a warning", break_watch_out_named_warning),
    ("watch-out", "the README calling it a warning", break_watch_out_readme_warning),
    ("watch-out", "the standing rule's heading renamed", break_standing_rule_renamed),
    ("guidance", "a reference file over 100 lines with its contents list deleted", break_toc_removed),
    ("guidance", "a contents list below the intro, not at the top", break_toc_below_intro),
    ("guidance", "a canonical file's contents list lost, and its mirrors with it", break_toc_mirror),
    ("guidance", "a SKILL.md body over the token estimate", break_skill_body_tokens),
    ("guidance", "a SKILL.md body of 500 lines or more", break_skill_body_lines),
    ("guidance", "a description opening with a bare imperative", break_description_imperative),
    ("guidance", "a bare imperative ending in \"ss\"", break_description_imperative_ss),
    ("guidance", "a reference named in SKILL.md by bare file name only", break_reference_bare_name),
    ("guidance", "a SKILL.md body of exactly 20,000 chars, at the token estimate", break_skill_body_tokens_at_limit),
    ("guidance", "a SKILL.md body of exactly 500 lines", break_skill_body_lines_at_limit),
    ("guidance", "a contents heading with prose, not a list, under it", break_toc_heading_without_list),
    ("guidance", "a reference over 100 lines with no H1", break_toc_no_h1),
    ("guidance", "a short reference file SKILL.md never names", break_reference_unlinked_short),
    ("guidance", "a mirror SKILL.md never names", break_reference_unlinked_mirror),
    ("guidance", "a reference named only in the frontmatter, not the body", break_reference_named_only_in_frontmatter),
    ("frontmatter", "a Claude Code-only frontmatter key in source", break_frontmatter_extra_key),
    ("guidance", "a generated file the hub does not link", break_frontdoor_unlinked),
    ("frontdoor", "a new name clash, not regenerated", break_frontdoor_new_clash),
    ("frontdoor", "a new name clash, regenerated, that the hub's links do not follow", break_frontdoor_new_clash_synced),
    ("frontdoor", "a hub link to a file the generator does not write", break_frontdoor_dangling),
    ("frontdoor", "a shared mirror naming a clashing file", break_frontdoor_unresolvable),
    ("frontmatter", "a Claude Code-only key in the hub's frontmatter", break_frontdoor_claude_code_key),
    ("frontdoor", "an explicit case expecting another module", break_frontdoor_explicit_expects_other),
    ("frontmatter", "a ': ' in the hub's unquoted description", break_frontdoor_yaml_colon),
    ("frontdoor", "a generated reference edited by hand", break_frontdoor_hand_edit),
    ("frontdoor", "a file in the hub's references/ that nothing generates", break_frontdoor_stray_reference),
    ("frontdoor", "a file a playbook names missing from the hub", break_frontdoor_playbook_names_absent),
    ("frontdoor", "a module's text changed and regenerated, not measured", break_frontdoor_module_text_unmeasured),
    ("frontdoor", "the hub's own text changed, not measured", break_frontdoor_hub_text_unmeasured),
    ("frontdoor", "a module's README changed and rebuilt, not measured", break_frontdoor_module_readme_unmeasured),
    ("frontdoor", "a module's description changed and rebuilt, not measured",
     break_frontdoor_module_description_unmeasured),
    ("frontdoor", "a new file at a module's root, not measured", break_frontdoor_module_new_file),
    ("frontdoor", "a file beside the hub's SKILL.md that it does not hold", break_frontdoor_hub_extra_file),
    ("frontdoor", "a folder inside the hub's references/", break_frontdoor_references_folder),
    ("frontdoor", "a module's playbook missing from the hub", break_frontdoor_no_playbook),
    ("frontdoor", "a routing row dropped", break_frontdoor_route_dropped),
    ("frontdoor", "a module's slash command dropped from the hub", break_frontdoor_command_dropped),
    ("frontdoor", "a module dropped from the hub's description", break_frontdoor_description_drops_module),
    ("frontdoor", "a new module, regenerated, that the hub does not route to", break_frontdoor_new_module_unrouted),
    ("builds", "a build that changes more than the hiding line", break_build_extra_change),
    ("builds", "the hiding line below the frontmatter", break_build_key_in_body),
    ("builds", "the front door hidden in a build", break_build_hub_hidden),
    ("builds", "the hiding key in a .skill file", break_build_key_in_skill_file),
    ("builds", "the hiding key in a source file", break_build_key_in_source),
    ("builds", "the plugin missing a file the personal install carries", break_build_plugin_differs),
    ("builds", "a plugin skill folder not named as its skill", break_build_folder_name),
    ("builds", "the plugin manifest under another name", break_build_manifest_name),
    ("builds", "a plugin manifest that is not JSON", break_build_manifest_not_json),
    ("builds", "the marketplace entry's source elsewhere", break_build_marketplace_source),
    ("builds", "the hiding key in one of the front door's built references", break_build_key_in_hub_reference),
    ("builds", "a plugin manifest with no version", break_build_manifest_no_version),
    ("builds", "a plugin version that is not the recorded one", break_build_manifest_version_unrecorded),
    ("builds", "a marketplace file with no owner", break_build_marketplace_no_owner),
    ("builds", "the hub's README in its Claude Code builds", break_build_hub_readme),
    ("builds", "the hub's README in its .skill file", break_build_hub_readme_skill_file),
    ("package", "the hub's README in its .skill file", break_package_hub_readme_skill_file),
    ("answer-keys", "a module's fixture quoted in another module's reference, read through the front door",
     break_answer_key_through_frontdoor),
    ("package", "a Claude Code build not rebuilt after a source edit", break_package_build_stale),
    ("package", "a file in the plugin built from nothing", break_package_build_stray),
    ("package", "the marketplace file missing", break_package_marketplace_missing),
    ("frontmatter", "a ' #' in a module's unquoted description", break_frontmatter_yaml_comment),
    ("guidance", "a generated playbook with no contents list, regenerated", break_frontdoor_playbook_contents),
]



def main() -> int:
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)

        clean = tmp / "clean"
        clean.mkdir()
        root = stage(clean)
        # The whole gate, not one group. This baseline used to run "frontmatter"
        # alone and then print "clean repo passes" — a claim about every group
        # made after checking one. With a group already failing on the clean repo,
        # a mutation of that group is not attributable to the mutation at all.
        code, out = run(root, None)
        if code != 0:
            print("clean repo does not pass its own checks — no mutation below would mean anything:\n" + out)
            return 1
        print("  ok   baseline: clean repo passes every group\n")

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
        for index, (group, label, mutate) in enumerate(PASSES):
            work = tmp / f"pass{index}"
            work.mkdir()
            root = stage(work)
            before = fingerprint(root)
            mutate(root)
            if fingerprint(root) == before:
                failed.append(f"{group}/{label}: must-pass change changed nothing — it has gone stale")
                print(f"  FAIL {group}: {label} — no-op")
            else:
                code, out = run(root, group)
                if code != 0:
                    failed.append(f"{group}/{label}: correct text was refused:\n{out[-600:]}")
                    print(f"  FAIL {group}: {label} — refused correct text")
                else:
                    print(f"  ok   {group}: {label} — accepted")
            shutil.rmtree(work)

        print()
        if failed:
            print(f"{len(failed)} self-test failure(s):")
            for line in failed:
                print(f"  {line}")
            return 1
        print(f"All {len(CASES)} mutations detected, and all {len(PASSES)} must-pass cases accepted.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
