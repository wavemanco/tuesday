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
COPIED = ["skills", "dist", "conventions", "ci", "evals", "docs"]
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
    path = root / "skills/job-underwriter/references/dossier-template.md"
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
    path = root / "skills/job-underwriter/references/dossier-template.md"
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
    """ "Six rules" ahead of six numbered sections."""
    swap_once(root, "conventions/output-discipline.md", "Six rules about the *shape*",
              "Five rules about the *shape*", "break_sections_count")
    return "says 5, has 6 numbered sections"


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
    swap_once(root, "README.md", "— six rules on the shape of a delivered response",
              "— five rules on the shape of a delivered response", "break_restated_count")
    return '"five rules" beside `output-discipline.md`, which has 6 rules'



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
              "The response ends with the upgrade menu and the questions as its last two sections in that order, "
              "asks at most three questions across the whole message",
              "The response closes with an upgrade menu and asks at most three questions across the whole message",
              "break_close_contradicts_order")
    return "closing_order ends questions"


def break_close_far_from_subject(root: Path) -> str:
    """job-underwriter's original wording, which a fixed window after the subject missed:
    sixty characters and a filename's full stop between "The response" and "closes"."""
    swap_once(root, "skills/job-underwriter/evals/evals.json",
              "and its upgrade menu names what each missing input would unlock. The response closes with the "
              "dossier offer, then the upgrade menu, then the questions",
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
    """ "These five rules" ahead of six numbered sections."""
    swap_once(root, "conventions/output-discipline.md", "Six rules about the *shape*",
              "These five rules are about the *shape*", "break_count_determiner_opening")
    return "says 5, has 6 numbered sections"


def break_close_reversed(root: Path) -> str:
    """The right sections named in the wrong order."""
    swap_once(root, "skills/resume-tailor/evals/evals.json",
              "The response ends with the upgrade menu and the questions as its last two sections in that order, "
              "asks at most three questions across the whole message",
              "The response ends with the questions and the upgrade menu as its last two sections in that order, "
              "asks at most three questions across the whole message", "break_close_reversed")
    return "closing_order ends upgrade menu, then questions"


def break_close_synonym(root: Path) -> str:
    swap_once(root, "skills/job-underwriter/evals/evals.json",
              "The response closes with the dossier offer, then the upgrade menu, then the questions",
              "The response concludes with an upgrade menu", "break_close_synonym")
    return "closing_order ends questions"


def break_close_skill_subject(root: Path) -> str:
    swap_once(root, "skills/job-underwriter/evals/evals.json",
              "The response closes with the dossier offer, then the upgrade menu, then the questions",
              "The skill closes with an upgrade menu", "break_close_skill_subject")
    return "closing_order ends questions"


def break_close_incidental_word(root: Path) -> str:
    """ "questions" inside a participle clause is not the questions section."""
    swap_once(root, "skills/job-underwriter/evals/evals.json",
              "The response closes with the dossier offer, then the upgrade menu, then the questions",
              "The response closes with an upgrade menu listing the questions that would sharpen it",
              "break_close_incidental_word")
    return "closing_order ends questions"


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
    swap_once(root, "README.md", "— six rules on the shape of a delivered response",
              "— the five rules in `output-discipline.md` on the shape of a delivered response",
              "break_count_definite_frame")
    return '"five rules" beside `output-discipline.md`, which has 6 rules'


def break_close_adverb_imperative(root: Path) -> str:
    swap_once(root, "skills/job-underwriter/SKILL.md", "the assessment ends without restating itself.",
              "the assessment ends without restating itself. Always close with the upgrade menu.",
              "break_close_adverb_imperative")
    return "closing_order ends questions"


def break_close_head_subject(root: Path) -> str:
    """ "the message presenting the pack ends with the upgrade menu" is about the message."""
    swap_once(root, "skills/mock-interview/evals/evals.json",
              'and the message presenting it ends with the drill and dossier offers, then at most three questions counted across the whole message, with nothing after the questions',
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
    swap_once(root, "skills/job-underwriter/SKILL.md", "the assessment ends without restating itself.",
              "the assessment ends without restating itself. The response ends with its three calls to action: the "
              "dossier offer, then the upgrade menu, then the questions.", "keep_close_after_colon")


def keep_drill_turn(root: Path) -> None:
    swap_once(root, "skills/mock-interview/references/output-template.md", "Follow up at least twice",
              "Each drill turn ends with feedback on the answer. Follow up at least twice", "keep_drill_turn")


def keep_wrap_before_bold(root: Path) -> None:
    swap_once(root, "skills/mock-interview/SKILL.md",
              "file, the offers and questions close the message that presents it, and nothing\nfollows the questions.",
              "file, the message that presents it closes with the drill and dossier offers, then\n**any questions**, "
              "and nothing follows the questions.", "keep_wrap_before_bold")


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
              "The response closes with the dossier offer, then the upgrade menu, then the questions",
              "The response does not close with the upgrade menu: it closes with the dossier offer, then the upgrade menu, then the questions",
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

DOSSIER = "skills/job-underwriter/references/dossier-template.md"


def break_ledger_fit_cell(root: Path) -> str:
    swap_once(root, DOSSIER, "| R4 | Regulatory exposure: PSD2 / open banking / card schemes | must_have | adjacent |",
              "| R4 | Regulatory exposure: PSD2 / open banking / card schemes | must_have | direct |", "break_ledger_fit_cell")
    return "fit ledger files R4 as must_have/adjacent; the map says must_have/direct"


def break_ledger_priority_cell(root: Path) -> str:
    swap_once(root, DOSSIER, "| R6 | Data fluency: SQL, experimentation | important |",
              "| R6 | Data fluency: SQL, experimentation | must_have |", "break_ledger_priority_cell")
    return "fit ledger files R6 as important/direct; the map says must_have/direct"


def break_ledger_drops_last_row(root: Path) -> str:
    """s1r1's shape: the row added last is the one the summary leaves out."""
    swap_once(root, DOSSIER, "- `preferred` — absent: R7 (Ledger / reconciliation systems)\n", "",
              "break_ledger_drops_last_row")
    return "fit ledger omits R7"


def break_ledger_duplicate_row(root: Path) -> str:
    swap_once(root, DOSSIER, "- `important` — direct: R6 ·", "- `important` — direct: R6, R2 ·",
              "break_ledger_duplicate_row")
    return "fit ledger lists R2 2 times"


def break_ledger_envelope(root: Path) -> str:
    path = root / DOSSIER
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
    end = text.index("R4 has a credible bridge")
    path.write_text(text[:start] + "**Fit ledger.** Five of seven material requirements are `direct` (R1–R3, R6, and the eligibility gate). " + text[end:])
    return "fit ledger: "


def break_ledger_summary_count(root: Path) -> str:
    swap_once(root, DOSSIER, '"summary": "Fit as evidence_map reads it,',
              '"summary": "Strong fit (five of seven material requirements direct),', "break_ledger_summary_count")
    return "decision.summary counts the map"


def break_ledger_name(root: Path) -> str:
    swap_once(root, DOSSIER, "adjacent: R4 (Regulatory exposure)", "adjacent: R4 (Regulation)", "break_ledger_name")
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
    text = text.replace("adjacent: R4 (Regulatory exposure)", "adjacent: R4a (Regulatory exposure) · absent: R4b (Regulatory exposure)")
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
    return "the snapshot counts"


def break_ledger_sentence_only(root: Path) -> str:
    """The first probe runs' shape: "the only rows below `direct`", under a ledger listing more."""
    swap_once(root, DOSSIER, "R4 has a credible bridge with its limit named,",
              "R4 is the only row below `direct` that matters,", "break_ledger_sentence_only")
    return "the sentence after the fit ledger says"


def break_ledger_summary_universal(root: Path) -> str:
    swap_once(root, DOSSIER, '"summary": "Fit as evidence_map reads it,',
              '"summary": "Every must_have requirement is direct but R4;', "break_ledger_summary_universal")
    return "decision.summary counts the map"


def break_ledger_tier_twice(root: Path) -> str:
    swap_once(root, DOSSIER, "- `preferred` — absent: R7 (Ledger / reconciliation systems)\n",
              "- `preferred` — absent: R7 (Ledger / reconciliation systems)\n- `preferred` — absent: R7 (Ledger)\n",
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
    swap_once(root, DOSSIER, "unclear: R5 (Mentoring or leading PMs)", "unclear: R5 (the)", "break_ledger_stopword_name")
    return "in words its Requirement cell does not use"


def keep_ledger_severity_token(root: Path) -> None:
    """A severity in its full token beside a register ID is not a confidence band."""
    swap_once(root, DOSSIER, "the compensation band is unstated against the candidate's £95k floor (RR2).",
              "the compensation band is unstated against the candidate's £95k floor (RR2 (`severity: medium`)).",
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

AFTER_LEDGER = "R4 has a credible bridge with its limit named, and R3 (`medium`) is confirmed but waits on an artifact."


def break_ledger_count_words_between(root: Path) -> str:
    """"N of the M" with words before the noun: COUNTED needed "N of M" exactly."""
    swap_once(root, DOSSIER, AFTER_LEDGER, AFTER_LEDGER + " Four of the seven material requirements are `direct`.",
              "break_ledger_count_words_between")
    return "the sentence after the fit ledger says"


def break_ledger_bare_count(root: Path) -> str:
    """A count with no "of" at all."""
    swap_once(root, DOSSIER, AFTER_LEDGER, "Four rows are `direct`.", "break_ledger_bare_count")
    return "the sentence after the fit ledger says"


def break_ledger_second_paragraph(root: Path) -> str:
    """The first paragraph after the ledger is clean; the second one quantifies."""
    swap_once(root, DOSSIER, AFTER_LEDGER, AFTER_LEDGER + "\n\nThe rest are `direct`.", "break_ledger_second_paragraph")
    return "the sentence after the fit ledger says \"The rest"


def break_ledger_two_sentences(root: Path) -> str:
    """Rule 2 allows at most one sentence after the ledger, quantifier or not."""
    swap_once(root, DOSSIER, AFTER_LEDGER,
              "R4 has a credible bridge with its limit named. R3 (`medium`) is confirmed but waits on an artifact.",
              "break_ledger_two_sentences")
    return "is followed by more than one sentence"


def break_ledger_both_after(root: Path) -> str:
    swap_once(root, DOSSIER, AFTER_LEDGER, "Both R4 and R3 (`medium`) wait on an artifact.", "break_ledger_both_after")
    return "the sentence after the fit ledger says \"Both\""


def break_ledger_universal_in_verdict(root: Path) -> str:
    """A universal over a tier in a slot other than the sentence after the ledger."""
    swap_once(root, DOSSIER, "**Worth applying to — on the conditions below.",
              "**Worth applying to — every must_have requirement is direct but R4.", "break_ledger_universal_in_verdict")
    return "the snapshot counts or quantifies the map"


def break_ledger_summary_all_but(root: Path) -> str:
    swap_once(root, DOSSIER, '"summary": "Fit as evidence_map reads it,', '"summary": "Direct on all but R4;',
              "break_ledger_summary_all_but")
    return "decision.summary counts the map"


def break_ledger_summary_bare_count(root: Path) -> str:
    swap_once(root, DOSSIER, '"summary": "Fit as evidence_map reads it,', '"summary": "Four direct;',
              "break_ledger_summary_bare_count")
    return "decision.summary counts the map"


def break_ledger_summary_of_the(root: Path) -> str:
    swap_once(root, DOSSIER, '"summary": "Fit as evidence_map reads it,', '"summary": "Four of the seven direct;',
              "break_ledger_summary_of_the")
    return "decision.summary counts the map"


def break_ledger_plain_band(root: Path) -> str:
    """A band without backticks is still a band, and this one is not R3's."""
    swap_once(root, DOSSIER, "R3 (`medium`)", "R3 (high)", "break_ledger_plain_band")
    return "snapshot gives R3 `high`; the map says medium"


def break_ledger_fit_twice(root: Path) -> str:
    swap_once(root, DOSSIER, "- `must_have` — direct: R2, R3 · adjacent: R4 (Regulatory exposure)",
              "- `must_have` — direct: R2 · direct: R3 · adjacent: R4 (Regulatory exposure)", "break_ledger_fit_twice")
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
    swap_once(root, DOSSIER, "| RR1 | Authority over three squads asserted, not evidenced | unknown | — |",
              "| RR1 | Authority over three squads asserted, not evidenced | unknown | high |",
              "break_ledger_none_found_over_high")
    return "says \"none found\" while the register has"


def break_ledger_gate_wrong_fit(root: Path) -> str:
    swap_once(root, DOSSIER, "none failed (R1 `direct`, R9 `direct`)", "none failed (R1 `direct`, R9 `adjacent`)",
              "break_ledger_gate_wrong_fit")
    return "the hard-gates line gives R9 `adjacent`; the map says direct"


def break_ledger_constraints_clause(root: Path) -> str:
    """The envelope says the constraints were not given; the gates line does not say so."""
    swap_once(root, DOSSIER, '"candidate_constraints": {\n      "status": "known",',
              '"candidate_constraints": {\n      "status": "unknown",', "break_ledger_constraints_clause")
    return "the candidate's constraints were not given"


def break_quantifier_drift_rule(root: Path) -> str:
    """The rule's list gains a word the shared set does not hold (D6)."""
    swap_once(root, "skills/job-underwriter/references/evidence-model.md", '"each of", ', '"each of", "most", ',
              "break_quantifier_drift_rule")
    return "QUANTIFIERS lacks ['most']"


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


def keep_ledger_only_adverb(root: Path) -> None:
    """"only" qualifying one row, outside the sentence after the ledger, is no quantifier."""
    swap_once(root, DOSSIER, "One entry runs the other way", "R4 is only adjacent. One entry runs the other way",
              "keep_ledger_only_adverb")


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


# Every declared enum names its column (MI-11).

def break_enum_without_column(root: Path) -> str:
    swap_once(root, "skills/job-underwriter/SKILL.md", ", severity=Severity", "", "break_enum_without_column")
    return "enum_fields names 'severity' and enum_columns gives it no column"


def break_enum_column_missing(root: Path) -> str:
    swap_once(root, "skills/mock-interview/SKILL.md", "gap_type=Gap type", "gap_type=Gap kind", "break_enum_column_missing")
    return "puts 'gap_type' in 'Gap kind', which is no column"


def break_enum_column_stale(root: Path) -> str:
    swap_once(root, "skills/resume-tailor/SKILL.md", "row_status=Status", "row_status=Status, stage=Status",
              "break_enum_column_stale")
    return "maps 'stage', which enum_fields does not declare"


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


PASSES = [
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
    ("fit-ledger", "a figure with its unit beside a map word", keep_ledger_figure_with_unit),
    ("answer-keys", "a common phrase of rule prose", keep_answer_key_common_phrase),
    ("answer-keys", "the shared contract's own wording", keep_answer_key_contract),
    ("wording", "\"no network\" outside an L0 definition", keep_no_network_elsewhere),
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
    ("triggers", "description lost its reserved boundary", break_trigger_boundary),
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
    ("fit-ledger", "a name that is not the row's requirement", break_ledger_name),
    ("fit-ledger", "a band the map does not carry", break_ledger_band),
    ("fit-ledger", "a count beside an intact ledger", break_ledger_count_beside),
    ("fit-ledger", "\"the only row below\" in the sentence after the ledger", break_ledger_sentence_only),
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
    ("fit-ledger", "\"both\" after the ledger", break_ledger_both_after),
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
    ("fit-ledger", "constraints not given and no closing clause", break_ledger_constraints_clause),
    ("fit-ledger", "a quantifier the rule lists and the shared set lacks", break_quantifier_drift_rule),
    ("fit-ledger", "a grader clause missing a quantifier of the list", break_quantifier_drift_grader),
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
    ("fixtures", "an n/a target's term matching another target's query", break_term_collision),
    ("fixtures", "an n/a target whose terms match none of its hunts", break_hunt_vacuous),
    ("fixtures", "an on-target sample aimed at no term of its target", break_sample_unaimed),
    ("fixtures", "an n/a target with no hunt_samples", break_hunt_samples_missing),
    ("wording", "\"returned something\" back in a grader clause", break_retired_returned_something),
    ("wording", "\"every call was refused\" without \"or errored\"", break_retired_refused_only),
    ("wording", "a label definition without \"returned a result\"", break_labels_without_result),
    ("wording", "\"No network\" back in the L0 definition", break_l0_no_network),
    ("wording", "a story pre-mapped with no quote", break_personas_premap),
    ("wording", "the personas scope line removed", break_personas_scope_line),
    ("columns", "a declared enum with no column", break_enum_without_column),
    ("columns", "an enum mapped to a column no worked table has", break_enum_column_missing),
    ("columns", "an enum_columns entry for an undeclared field", break_enum_column_stale),
    ("evals", "an expectation naming an unknown clause", break_clause_unknown),
    ("evals", "a clause nothing uses", break_clause_unused),
    ("evals", "a clause inside a clause", break_clause_nested),
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
