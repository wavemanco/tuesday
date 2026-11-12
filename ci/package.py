#!/usr/bin/env python3
"""Build everything under dist/ from skills/, and the marketplace file that lists the plugin.

`check_skills.py` has always verified the packages — zip rooted at the skill
folder, `evals/` excluded, every entry byte-matching its source — while the thing
that produced them lived in whatever session happened to have skill-creator
installed. So the repo could tell you the build was stale and not how to fix it,
and the check's own docstring says why that is wrong: a step that can vanish
underneath CI is not a step. The inclusion rules and the build plan here are
imported from the checker rather than restated, so the builder and its check
cannot drift.

What it writes (README.md, "Install", says who installs which):
  dist/<skill>.skill           one per skill, the front door's `tuesday.skill` included,
                               for a claude.ai upload: the source as it ships (packaged_files)
  dist/claude-code/<skill>/    the personal install: each module hidden (sync.hide)
  dist/plugin/tuesday/         the plugin: its manifest, and the same folders under skills/
  .claude-plugin/marketplace.json   the marketplace entry for the plugin

    python ci/package.py            # rebuild everything
    python ci/package.py mock-interview   # rebuild one .skill file, and the trees
"""

from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_skills import CLAUDE_CODE, DIST, PLUGIN, REPO, SKILLS_DIR, builds, packaged_files, skills


def build(skill: Path) -> Path:
    artifact = DIST / f"{skill.name}.skill"
    DIST.mkdir(exist_ok=True)
    # Deterministic: sorted names, fixed timestamps, so an unchanged skill
    # produces an identical file and a rebuild is not noise in the diff.
    with zipfile.ZipFile(artifact, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(packaged_files(skill)):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, (SKILLS_DIR / name).read_bytes())
    return artifact


def build_trees() -> int:
    """Write the Claude Code builds and the marketplace file afresh; return how many files."""
    for tree in (CLAUDE_CODE, PLUGIN):
        if tree.exists():
            shutil.rmtree(tree)
    files = builds()
    for name, data in files.items():
        path = REPO / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return len(files)


def main() -> int:
    wanted = set(sys.argv[1:])
    targets = [s for s in skills() if not wanted or s.name in wanted]
    unknown = wanted - {s.name for s in targets}
    if unknown:
        print(f"no such skill(s): {', '.join(sorted(unknown))}")
        return 2
    for skill in targets:
        artifact = build(skill)
        print(f"  built {artifact.relative_to(artifact.parent.parent)} "
              f"({len(packaged_files(skill))} entries)")
    print(f"  built {CLAUDE_CODE.relative_to(REPO)}/, {PLUGIN.relative_to(REPO)}/ and the marketplace file "
          f"({build_trees()} files)")
    print("\nNow run: python ci/check_skills.py --only package --only builds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
