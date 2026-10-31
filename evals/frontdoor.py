#!/usr/bin/env python3
"""Generate the front-door prototype's references/ from the module skills.

The prototype hub (`evals/arms/frontdoor/SKILL.md`) is hand-written; everything
it links under `references/` is generated here, from the module sources in
`skills/` at the same commit, and never edited. The transform, and how a name
clash is resolved, is stated once in evals/README.md ("The front-door arm").

    python evals/frontdoor.py --out DIR    # write the assembled hub to DIR/tuesday/
    python evals/frontdoor.py              # list what would be generated, and from where

`run_routing.py --arm frontdoor` installs the same output in each case's
throwaway project; `ci/check_skills.py --only frontdoor` holds the hub's links
to exactly this list.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO / "skills"
HUB = REPO / "evals" / "arms" / "frontdoor" / "SKILL.md"
HUB_NAME = "tuesday"

FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
LINK = re.compile(r"references/([A-Za-z0-9._-]+\.md)")
CONTENTS = "## Contents"


class GenerationError(SystemExit):
    """The module sources cannot be generated into one flat references/ folder."""


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
        return text  # nowhere for a list to sit; check_frontdoor fails such a file if it is long
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


def generate(skills_dir: Path = SKILLS_DIR) -> dict[str, dict]:
    """Every file of the hub's references/: name -> {"text", "from", "transform"}.

    Deterministic: modules and files are read in sorted order and nothing but the
    sources decides the output. Fails (GenerationError) rather than guess when a
    clash cannot be resolved by renaming, or a playbook names a file that would
    not be there.
    """
    mods = modules(skills_dir)
    playbooks = {f"{m}.md" for m in mods}
    by_name: dict[str, dict[str, str]] = {}
    for m in mods:
        for ref in sorted((skills_dir / m / "references").glob("*.md")):
            by_name.setdefault(ref.name, {})[m] = ref.read_text(encoding="utf-8")

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
        text = with_contents(rewrite(body((skills_dir / m / "SKILL.md").read_text(encoding="utf-8")), renames[m]))
        put(f"{m}.md", text, f"skills/{m}/SKILL.md (body)",
            "frontmatter stripped, contents listed" + (", clash paths rewritten" if renames[m] else ""))

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


def assemble(dest: Path, name: str = HUB_NAME, skills_dir: Path = SKILLS_DIR, hub: Path = HUB) -> dict[str, dict]:
    """Write the hub as an installable skill folder at dest, its frontmatter name set to `name`."""
    text = hub.read_text(encoding="utf-8")
    hub_text = re.sub(rf"^name:\s*{HUB_NAME}\s*$", f"name: {name}", text, count=1, flags=re.MULTILINE)
    if hub_text == text and name != HUB_NAME:
        raise GenerationError(f"{hub}: frontmatter name not found to rename")
    files = generate(skills_dir)
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "references").mkdir(parents=True)
    (dest / "SKILL.md").write_text(hub_text, encoding="utf-8")
    for fname, entry in files.items():
        (dest / "references" / fname).write_text(entry["text"], encoding="utf-8")
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, help="write the assembled hub to OUT/tuesday/")
    args = ap.parse_args()
    files = generate()
    for name, entry in files.items():
        print(f"  references/{name:<36} {entry['transform']:<58} {entry['from']}")
    links = hub_links(HUB.read_text(encoding="utf-8"))
    print(f"\n{len(files)} generated; the hub links {len(links & set(files))} of them"
          + (f"; unlinked: {sorted(set(files) - links)}" if set(files) - links else "")
          + (f"; dangling: {sorted(links - set(files))}" if links - set(files) else ""))
    if args.out:
        assemble(args.out / HUB_NAME)
        print(f"wrote {args.out / HUB_NAME}")
    return 0 if links == set(files) else 1


if __name__ == "__main__":
    sys.exit(main())
