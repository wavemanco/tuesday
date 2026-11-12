#!/usr/bin/env python3
"""Regenerate every generated copy in skills/ from its source, or check that none is out of date.

Two kinds of file in skills/ are written by this tool and never edited by hand:

- the convention mirrors: each `skills/<module>/references/<name>.md` that opens with a
  `<!-- SYNCED FROM: conventions/<name>.md … -->` header carries that header and then the
  canonical file, byte for byte;
- the front door's `skills/tuesday/references/`: generated from the module skills by
  `generate`, as skills/tuesday/README.md ("How references/ is made") states.

    python ci/sync.py            # rewrite whatever is out of date
    python ci/sync.py --check    # report what is out of date, and exit 1 if anything is
    python ci/sync.py --list     # list the front door's generated files and where each comes from

The generator lives here so that CI (`check_skills.py`), the packager and the eval harness
share one definition of the front door's references and of `digest`, the hash a measurement
records. `hide` is the one transform the Claude Code builds make, shared the same way.
Standard library only, like the rest of ci/.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
from pathlib import Path
from typing import Callable

REPO = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO / "skills"
HUB_NAME = "tuesday"
HUB_DIR = SKILLS_DIR / HUB_NAME
HUB = HUB_DIR / "SKILL.md"
# What skills/tuesday/ holds. Its SKILL.md and its references/, one flat folder, are what round 3
# installed; its LICENSE is the one every skill folder carries. Those ship. Its README.md is for
# whoever maintains the repository and ships nowhere (CONTRIBUTING.md, "The front door ships what
# was measured").
HUB_SHIPS = ("SKILL.md", "LICENSE")
HUB_SOURCE_ONLY = ("README.md",)

MIRROR_HEADER = re.compile(r"\A<!-- SYNCED FROM: (\S+)\n.*?-->\n", re.DOTALL)
FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
LINK = re.compile(r"references/([A-Za-z0-9._-]+\.md)")
CONTENTS = "## Contents"
# Where a playbook's paths resolve, said in the playbook itself: its mentions of
# `references/<file>` were written for the module's own folder, and the hidden
# modules' folders sit beside the hub holding files of the same names. Haiku,
# having listed them, once read a playbook's files from the hidden module's own
# folder (in round 1's runs, diagnosed while round 2 was built). The hub's
# section 3 states the rule; this line, generated into every playbook, points to
# it where the paths are read.
PATHS_NOTE = ("**Paths.** The `tuesday` skill runs this playbook: every `references/` path in it, and in the "
              "files it names, means the folder that holds this file, never a module's own skill folder, "
              "even one a listing shows (the `tuesday` skill's own instructions, section 3).")
# The one line the Claude Code builds add to a module's frontmatter. Claude Code alone reads it;
# a claude.ai upload refuses it, so it is never in skills/ or in a .skill file.
HIDDEN_KEY = "disable-model-invocation: true"


class GenerationError(SystemExit):
    """The module sources cannot be generated into one flat references/ folder."""


def hub_ships(rel: str) -> bool:
    """Whether the file at `rel` in skills/tuesday/ ships in a build and in the harness's install:
    a file of HUB_SHIPS, or a file directly in references/."""
    parts = rel.split("/")
    return rel in HUB_SHIPS or (len(parts) == 2 and parts[0] == "references")


def hub_shipped(hub_dir: Path = HUB_DIR) -> list[str]:
    """The files of the hub that ship, as paths in its folder, sorted."""
    return sorted(rel for rel in (p.relative_to(hub_dir).as_posix() for p in hub_dir.rglob("*") if p.is_file())
                  if hub_ships(rel))


def modules(skills_dir: Path = SKILLS_DIR) -> list[str]:
    """Every module skill: a folder under skills/ with a SKILL.md, the hub itself excepted."""
    return sorted(p.name for p in skills_dir.iterdir()
                  if (p / "SKILL.md").is_file() and p.name != HUB_NAME)


def body(skill_md: str) -> str:
    """A SKILL.md without its frontmatter: what loads when the module runs."""
    match = FRONTMATTER.match(skill_md)
    if not match:
        raise GenerationError("a module SKILL.md has no frontmatter to strip")
    return skill_md[match.end():].lstrip("\n")


def hide(skill_md: str) -> str:
    """The frontmatter with HIDDEN_KEY added as its last key, and nothing else changed: the
    module keeps `/name` and leaves the listing, in Claude Code only."""
    match = re.match(r"\A---\n(.*?\n)---\n", skill_md, re.DOTALL)
    if not match:
        raise SystemExit("a module SKILL.md has no frontmatter to add the hiding key to")
    return f"---\n{match.group(1)}{HIDDEN_KEY}\n---\n" + skill_md[match.end():]


def with_contents(text: str) -> str:
    """The playbook with a contents list of its `##` and `###` headings under its H1.

    A playbook is read in full and runs past 100 lines, where the guidance asks a
    reference file to open with its contents. The module SKILL.md carries none,
    since a SKILL.md body is not a reference file, so the list is generated here,
    in heading order, `###` headings nested under theirs. Headings inside fenced
    code are not headings. A body that already opens with `## Contents` under its
    H1, or has no H1 or no headings, is left as it is.
    """
    lines = text.split("\n")
    h1 = next((i for i, line in enumerate(lines) if line.startswith("# ")), None)
    if h1 is None:
        return text  # nowhere for a list to sit; the guidance group fails such a file if it is long
    following = [line for line in lines[h1 + 1:] if line.strip()]
    if following and following[0].strip() == CONTENTS:
        return text
    items, fenced = [], False
    for line in lines[h1 + 1:]:
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith("## "):
            items.append(f"- {line[3:].strip()}")
        elif not fenced and line.startswith("### "):
            items.append(f"  - {line[4:].strip()}")
    if not items:
        return text
    return "\n".join(lines[:h1 + 1] + ["", CONTENTS, ""] + items + lines[h1 + 1:])


def with_paths_note(text: str) -> str:
    """The playbook with PATHS_NOTE as its first paragraph after its H1 and its contents list.

    After the contents list, not above it: a file over 100 lines opens with its
    contents directly under its H1. A playbook with no H1 gets the line first.
    """
    lines = text.split("\n")
    h1 = next((i for i, line in enumerate(lines) if line.startswith("# ")), None)
    if h1 is None:
        return f"{PATHS_NOTE}\n\n{text}"
    at = h1 + 1
    i = at
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].strip() == CONTENTS:
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        while i < len(lines) and lines[i].lstrip().startswith("- "):
            i += 1
        at = i
    return "\n".join(lines[:at] + ["", PATHS_NOTE] + lines[at:])


def renamed(module: str, name: str) -> str:
    return f"{module}-{name}"


def rewrite(text: str, names: dict[str, str]) -> str:
    """Point every mention of a renamed file at its new name.

    A mention is the file name alone or under `references/`, not part of a longer
    name or path: `references/rationale.md` and `rationale.md` are rewritten,
    `conventions/rationale.md` and `old-rationale.md` are not.
    """
    for old, new in sorted(names.items()):
        text = re.sub(rf"(?<![\w./-])(references/)?{re.escape(old)}(?![\w-])",
                      lambda m: (m.group(1) or "") + new, text)
    return text


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def generate(skills_dir: Path = SKILLS_DIR, read: Callable[[Path], str] = read_file) -> dict[str, dict]:
    """Every file of the hub's references/: name -> {"text", "from", "transform"}.

    Deterministic: modules and files are read in sorted order and nothing but the
    sources decides the output. Fails (GenerationError) rather than guess when a
    clash cannot be resolved by renaming, or a playbook names a file that would
    not be there. `read` gives a source file's text; `plan` passes one that sees
    the convention mirrors as they will be once resynced.
    """
    mods = modules(skills_dir)
    playbooks = {f"{m}.md" for m in mods}
    by_name: dict[str, dict[str, str]] = {}
    for m in mods:
        for ref in sorted((skills_dir / m / "references").glob("*.md")):
            by_name.setdefault(ref.name, {})[m] = read(ref)

    # A clash is a name two modules carry with different text, or a module file
    # named like a playbook. Identical copies (the convention mirrors) are one file.
    clashes = {name for name, copies in by_name.items()
               if len(set(copies.values())) > 1 or name in playbooks}
    renames = {m: {name: renamed(m, name) for name in clashes if m in by_name[name]} for m in mods}

    out: dict[str, dict] = {}

    def put(name: str, text: str, source: str, transform: str) -> None:
        if name in out:
            raise GenerationError(f"front door: {source} would be written as references/{name}, "
                                  f"which {out[name]['from']} already is")
        out[name] = {"text": text, "from": source, "transform": transform}

    for name, copies in sorted(by_name.items()):
        if name in clashes:
            continue
        holders = sorted(copies)
        text = copies[holders[0]]
        if len(holders) == 1:
            # One module's own file: a mention of a clashing name means that module's copy.
            moved = rewrite(text, renames[holders[0]])
            put(name, moved, f"skills/{holders[0]}/references/{name}",
                "copy" if moved == text else "copy, clash paths rewritten")
            continue
        for clash in sorted(clashes):
            if rewrite(text, {clash: "x"}) != text:
                raise GenerationError(
                    f"front door: references/{name} is shared by {', '.join(holders)} and names "
                    f"{clash}, which differs between modules — the mention cannot be resolved")
        put(name, text, " = ".join(f"skills/{m}/references/{name}" for m in holders), "copy")

    for m in mods:
        for name in sorted(renames[m]):
            put(renames[m][name], rewrite(by_name[name][m], renames[m]),
                f"skills/{m}/references/{name}", "renamed (name clash)")
    for m in mods:
        text = with_paths_note(with_contents(
            rewrite(body(read(skills_dir / m / "SKILL.md")), renames[m])))
        put(f"{m}.md", text, f"skills/{m}/SKILL.md (body)",
            "frontmatter stripped, contents listed, paths note" + (", clash paths rewritten" if renames[m] else ""))

    for m in mods:
        missing = sorted({n for n in LINK.findall(out[f"{m}.md"]["text"]) if n not in out})
        if missing:
            raise GenerationError(f"front door: references/{m}.md names "
                                  f"{', '.join('references/' + n for n in missing)}, which is not generated")
    return dict(sorted(out.items()))


def hub_links(hub_text: str) -> set[str]:
    """The reference files a hub SKILL.md links, by the path that resolves in the installed skill."""
    return set(LINK.findall(body(hub_text)))


def digest(files: dict[str, dict], hub_text: str) -> str:
    """One hash over the hub and every generated file, recorded with each run."""
    h = hashlib.sha256(hub_text.encode())
    for name, entry in sorted(files.items()):
        h.update(name.encode() + b"\0" + entry["text"].encode() + b"\0")
    return h.hexdigest()


def tree_digest(files: dict[str, bytes]) -> str:
    """One hash over a tree of files, path -> bytes: every path and its bytes, in path order."""
    h = hashlib.sha256()
    for name, data in sorted(files.items()):
        h.update(name.encode() + b"\0" + data + b"\0")
    return h.hexdigest()


def shipped(hub_dir: Path = HUB_DIR) -> tuple[str, dict[str, dict]]:
    """The hub as it ships: its SKILL.md text, and every file under its references/, by its path
    there, in `generate`'s shape. A file in a folder below references/ is read too, so the digest
    covers it; the frontdoor group fails it."""
    refs = hub_dir / "references"
    files = {p.relative_to(refs).as_posix(): {"text": read_file(p)}
             for p in sorted(refs.rglob("*")) if p.is_file()} if refs.is_dir() else {}
    return read_file(hub_dir / "SKILL.md"), files


def digests(hub_dir: Path = HUB_DIR) -> dict[str, str]:
    """The two hashes a front-door measurement records, of the hub as it ships: the hub's
    SKILL.md alone, and the hub with every file in its references/."""
    hub_text, files = shipped(hub_dir)
    return {"hub_sha256": digest({}, hub_text), "frontdoor_sha256": digest(files, hub_text)}


def plan(repo: Path = REPO) -> tuple[dict[Path, str], list[Path], dict[Path, str]]:
    """What every generated copy should hold: (path -> text, generated files and folders to
    delete, mirrors that cannot be written -> the canonical file their header names).

    The module mirrors come first, and the front door is generated from the modules'
    files as they will be once their mirrors are resynced, so one pass fixes both. A
    mirror whose header names a file that does not exist is left as it is and reported.
    """
    skills_dir = repo / "skills"
    wanted: dict[Path, str] = {}
    broken: dict[Path, str] = {}
    for m in modules(skills_dir):
        for mirror in sorted((skills_dir / m / "references").glob("*.md")):
            header = MIRROR_HEADER.match(read_file(mirror))
            if header and (repo / header.group(1)).is_file():
                wanted[mirror] = header.group(0) + read_file(repo / header.group(1))
            elif header:
                broken[mirror] = header.group(1)
    hub_refs = skills_dir / HUB_NAME / "references"
    for name, entry in generate(skills_dir, lambda p: wanted.get(p) or read_file(p)).items():
        wanted[hub_refs / name] = entry["text"]
    stray = [p for p in sorted(hub_refs.iterdir()) if p not in wanted] if hub_refs.is_dir() else []
    return wanted, stray, broken


def out_of_date(repo: Path = REPO) -> list[str]:
    """Every generated copy that differs from what `plan` says it should hold, and every file or
    folder in the hub's references/ that nothing generates, as a repo path. A mirror that cannot
    be written is listed with the missing file its header names."""
    wanted, stray, broken = plan(repo)
    stale = [p for p, text in wanted.items() if not p.is_file() or read_file(p) != text]
    return sorted([p.relative_to(repo).as_posix() for p in stale + stray]
                  + [f"{p.relative_to(repo).as_posix()} (its header names {target}, which does not exist)"
                     for p, target in broken.items()])


def write(repo: Path = REPO) -> list[str]:
    """Bring every generated copy up to date, delete what nothing generates in the hub's
    references/, files and folders alike, and return what changed, as repo paths. Refuses,
    changing nothing, when a mirror's header names a file that does not exist."""
    wanted, stray, broken = plan(repo)
    if broken:
        raise GenerationError("cannot resync: " + "; ".join(
            f"{p.relative_to(repo).as_posix()} names {target} in its header, which does not exist"
            for p, target in broken.items()))
    stale = out_of_date(repo)
    for path in stray:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
    for path, text in wanted.items():
        if not path.is_file() or read_file(path) != text:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    return stale


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="report what is out of date; change nothing")
    mode.add_argument("--list", action="store_true", help="list the front door's generated files and their sources")
    args = ap.parse_args()
    if args.list:
        for name, entry in generate().items():
            print(f"  references/{name:<36} {entry['transform']:<58} {entry['from']}")
        return 0
    if args.check:
        stale = out_of_date()
        for path in stale:
            print(f"  out of date: {path}")
        print(f"{len(stale)} generated file(s) out of date — run python ci/sync.py" if stale
              else "every generated copy is current")
        return 1 if stale else 0
    try:
        changed = write()
    except GenerationError as exc:
        print(exc)
        return 1
    print("\n".join(f"  rewrote {p}" for p in changed) if changed else "every generated copy was already current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
