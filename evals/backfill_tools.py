#!/usr/bin/env python3
"""Reconstruct the research record of runs saved before the harness kept one.

Until the runner recorded each room's tool calls, a saved run was its response
text and a few counts — nothing said whether a search had been sent, refused or
never tried. Regrading those runs under the current grader prompt would then
tell graders "not recorded", which is honest, and would leave every research
claim in the baseline ungradeable, which is not like for like with new runs. The
calls still exist: every nested session left a transcript under
~/.claude/projects/, in a directory named after the room's working directory.

The saved meta never recorded which room a run came from, so a run is paired
with its transcript by text: the run's response, before any appended file, must
equal one transcript's main-thread assistant text. Exactly one match is written
as a reconstructed record with its provenance; no match, or more than one, is
written as `research_log: null` with `reason: no_log` — never guessed. A run that
needed a nudge is matched against the later of its room's two sessions.

It writes only into the meta.json files of the directory it is given, and it
refuses a directory that already holds grades: backfill a copy, then grade the
copy (`run_fixtures.py --regrade-from` does both).

    python evals/backfill_tools.py <dir-with-copied-runs> [--projects ~/.claude/projects]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_fixtures import build_research_log, parse_stream  # noqa: E402

FILE_SECTION = re.compile(r"\n*----- file the response produced: ")


def response_body(md_text: str) -> str:
    """The chat text of a saved run, without the files appended below it."""
    return FILE_SECTION.split(md_text, maxsplit=1)[0]


def same_text(a: str, b: str) -> bool:
    return " ".join(a.split()) == " ".join(b.split())


def read_events(path: Path) -> list[dict]:
    events = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def sessions(path: Path) -> list[list[dict]]:
    """Split one transcript into the invocations it holds.

    Nested runs inherit the parent's session id, so a nudged room's second
    invocation can land in the same file as its first; each begins with a user
    prompt that has no parent.
    """
    groups: list[list[dict]] = []
    for event in read_events(path):
        content = (event.get("message") or {}).get("content")
        is_prompt = event.get("type") == "user" and event.get("parentUuid") is None and (
            isinstance(content, str) or (isinstance(content, list) and not any(
                isinstance(c, dict) and c.get("type") == "tool_result" for c in content)))
        if is_prompt or not groups:
            groups.append([])
        groups[-1].append(event)
    return [g for g in groups if any(e.get("type") == "assistant" for e in g)]


def candidates(projects: Path, skill: str, eval_id) -> list[dict]:
    """Every invocation recorded in a room directory for this skill and fixture, in order."""
    found = []
    for directory in sorted(projects.glob(f"*rooms-{skill}-{eval_id}-*")):
        if not directory.is_dir():
            continue
        files = sorted(directory.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
        for path in files:
            for index, events in enumerate(sessions(path)):
                found.append({"dir": directory, "path": path, "index": index, "events": events})
    return found


def match_run(md_text: str, pool: list[dict], nudged: bool) -> tuple[dict | None, int, int]:
    """Return (the one matching invocation or None, how many matched, chars matched)."""
    body = response_body(md_text).strip()
    if not body:
        return None, 0, 0
    hits = [c for c in pool if same_text(parse_stream(c["events"], "")["text"], body)]
    if len(hits) > 1 and nudged and len({h["dir"] for h in hits}) == 1:
        hits = hits[-1:]                     # a nudged run is its room's later session
    if len(hits) != 1:
        return None, len(hits), 0
    return hits[0], 1, len(body)


def backfill_meta(meta: dict, md_text: str, pool: list[dict]) -> dict:
    """The meta with a reconstructed research_log, or research_log null and why."""
    nudged = meta.get("triggered_unprompted") is False
    hit, count, chars = match_run(md_text, pool, nudged)
    updated = dict(meta)
    if hit is None:
        updated.update(research_log=None, reason="no_log",
                       research_log_provenance={"method": "backfill-text-match",
                                                "matches": count})
        return updated
    parsed = parse_stream(hit["events"], "")
    updated["research_log"] = build_research_log(parsed["tool_calls"],
                                                 parsed["result"]["permission_denials"], [])
    updated["research_log_provenance"] = {"method": "backfill-text-match",
                                          "transcript": str(hit["path"]),
                                          "session_index": hit["index"],
                                          "matched_chars": chars}
    updated.pop("reason", None)
    return updated


def backfill_dir(directory: Path, projects: Path | None = None) -> list[tuple[str, str]]:
    """Backfill every run in `directory` that has no research record yet."""
    projects = projects or Path.home() / ".claude" / "projects"
    report, pools = [], {}
    for meta_path in sorted(Path(directory).glob("*.meta.json")):
        meta = json.loads(meta_path.read_text())
        if "research_log" in meta:
            continue
        stem = meta_path.name[:-len(".meta.json")]
        md_path = meta_path.with_name(f"{stem}.md")
        if not md_path.exists():
            continue
        key = (meta.get("skill"), meta.get("id"))
        if key not in pools:
            pools[key] = candidates(projects, *key) if projects.is_dir() else []
        updated = backfill_meta(meta, md_path.read_text(), pools[key])
        meta_path.write_text(json.dumps(updated, indent=2) + "\n")
        if updated.get("research_log") is None:
            outcome = f"no_log ({updated['research_log_provenance']['matches']} matching transcripts)"
        else:
            outcome = (f"{len(updated['research_log'])} call(s) from "
                       f"{Path(updated['research_log_provenance']['transcript']).parent.name}")
        report.append((stem, outcome))
        print(f"  backfill {stem}: {outcome}", flush=True)
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("directory")
    ap.add_argument("--projects", default=None, help="transcript root (default ~/.claude/projects)")
    args = ap.parse_args()
    directory = Path(args.directory)
    if not directory.is_dir():
        ap.error(f"{directory} is not a directory")
    if any(directory.glob("*.grade-*.json")):
        ap.error(f"{directory} already holds grades; backfill a copy of the set, not the set")
    report = backfill_dir(directory, Path(args.projects) if args.projects else None)
    found = sum(1 for _, outcome in report if not outcome.startswith("no_log"))
    print(f"{found} of {len(report)} run(s) reconstructed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
