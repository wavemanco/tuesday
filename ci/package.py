#!/usr/bin/env python3
"""Build dist/<skill>.skill from skills/<skill>/.

`check_skills.py` has always verified the packages — zip rooted at the skill
folder, `evals/` excluded, every entry byte-matching its source — while the thing
that produced them lived in whatever session happened to have skill-creator
installed. So the repo could tell you the build was stale and not how to fix it,
and the check's own docstring says why that is wrong: a step that can vanish
underneath CI is not a step. The inclusion rules here are imported from the
checker rather than restated, so the builder and its check cannot drift.

    python ci/package.py            # rebuild every skill
    python ci/package.py mock-interview
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_skills import DIST, SKILLS_DIR, packaged_files, skills


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
    print("\nNow run: python ci/check_skills.py --only package")
    return 0


if __name__ == "__main__":
    sys.exit(main())
