#!/usr/bin/env python3
"""Suite-level routing eval.

Per-skill evals cannot test triggering *between* skills: the decision is made
across the whole available-skills list, so it has no home inside any one skill's
evals/. This runner puts every skill in front of the model at once and records
which one fires.

Method: each skill is copied into a throwaway project's `.claude/skills/`, so it
reaches the model through the same path an installed skill does — the
available-skills list, carrying its real frontmatter description. `claude -p`
then answers the case prompt and the stream is watched for which skill it
reaches for. Nothing is duplicated here; the eval always tests what ships.

Registration is deliberate. An earlier version registered each skill as a project
*command*, which put a caveat under every number it produced: commands are
addressed to the model as things the user invokes, so "the harness under-reports"
was always available as the competing explanation for a low score. Installing the
real skills retires that caveat.

Usage:
    python evals/run_routing.py                 # all cases, 3 runs each
    python evals/run_routing.py --runs 1        # quick pass
    python evals/run_routing.py --case 9 --case 10
    python evals/run_routing.py --cases evals/routing-arm-b.json   # another case file
    python evals/run_routing.py --arm tuesday                      # the front door, skills/tuesday
    python evals/run_routing.py --arm tuesday --cases evals/suite-explicit.json
    python evals/run_routing.py --arm tuesday --layout plugin       # the skills outside the case folder
    python evals/run_routing.py --merge e1.json --rerun e1.gap-1.json --json-out e1.merged.json

Two arms (evals/README.md, "The Tuesday arm"). `skills`, the default, installs
the three module skills as they ship. `tuesday` installs the front door,
`skills/tuesday/`, as it ships, beside the three modules with
`disable-model-invocation: true` added, as the Claude Code builds add it.

`--layout` says where either arm's skills are installed (evals/README.md, "Layouts"):
the case folder's `.claude/skills/` (`project`, the default), a config folder of each
run's own (`personal`), or a plugin (`plugin`, the front-door arm only).

`--merge` runs nothing: it fills an arm cut short by the usage limit from re-runs of its
killed and never-started runs (`merge_arm`; evals/README.md, "Recovering a cut-short arm").
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import posixpath
import re
import select
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from child_env import child_env  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SKILLS = ["job-underwriter", "mock-interview", "resume-tailor"]
SUITE = REPO / "evals" / "suite-routing.json"
ARMS = ("skills", "tuesday")
LAYOUTS = ("project", "personal", "plugin")
# The folder, beside the case folders, that holds each case's skills outside its own
# folder. Its name is neutral, as is each folder under it (`case-<id>`, or `case-<id>-<run>`
# for a run's config folder), so no folder path the model meets carries the hub's name but
# the hub's own folder.
OUTSIDE = {"personal": "config", "plugin": "plugins"}
HUB = "tuesday"
# Outcomes that are not evidence about routing: set aside, never scored.
SET_ASIDE = ("timeout", "error", "void")
# The bar re-runs an arm with more than this share of its runs set aside, void ones
# counted with timeouts and errors: a mostly-void arm would otherwise be scored on
# whatever survived, and its zero counts read as gates met.
SET_ASIDE_LIMIT = 0.10
# Where a Bash command's words split: its operators, and the characters around a word.
SHELL_SEPARATOR = re.compile(r"&&|\|\||[;|&\n()]")
SHELL_WORD = re.compile(r"""[^\s"'`<>=]+""")
# An E2 run that loaded the named module and reached no other: the explicit case's pass.
FOCUSED = "focused"
# Seconds a run gets when --timeout is not given. A skills-arm routing run stops at its
# first fire; a run read to the end of its turn (the front-door arm, an explicit case)
# carries the module's whole job, which outlasts that. Round 2's measurement ran its
# front-door arm at the shorter default by an omitted flag, and six mock-interview runs
# that had routed right were cut off and set aside (evals/README.md).
TIMEOUT_FIRST_FIRE = 240
TIMEOUT_WHOLE_TURN = 900
# The message the CLI leaves in a session's transcript when the account's usage limit stops the
# run: the proof `merge_arm` needs before it replaces an `error` run with a re-run.
LIMIT = re.compile(r"You've hit your (?:weekly |session |usage )?limit", re.I)
# The init event's keys that differ on every run: the session's own ids and the process's state.
# They are left out of `init_sha256` and `init_events`, so runs that started alike share one
# entry. The run's `session_id` is on its record, and the copy of its stream holds the whole event.
INIT_PER_RUN = ("session_id", "uuid", "startup_timing", "scratchpad_path", "messaging_socket_path")
# A results file's spellings from before the code-name rename (E25), read as the names they became.
SAVED_ARMS = {"frontdoor": "tuesday"}
SAVED_KEYS = {"tuesday_sha256": "frontdoor_sha256"}
# What an install leaves out of a module's folder, at any depth (`install_one`, `modules_sha256`).
INSTALL_IGNORED = ("evals", "__pycache__", "*.pyc", ".DS_Store")
# The runner's own code, whose sha256 a results file records (`harness_sha256`): a re-run made with
# other code is not a re-run of the arm (`merge_arm`).
HARNESS_FILES = ("evals/run_routing.py", "evals/child_env.py", "ci/sync.py")

sys.path.insert(0, str(REPO / "ci"))
import sync  # noqa: E402  (ci/: the front door's generator, its digest, and the hiding transform)
from sync import HIDDEN_KEY, hide  # noqa: E402,F401


def install_one(skill: str, dest: Path, name: str, override: Path | None = None) -> None:
    """Copy `skills/<skill>/` to `dest` as it ships, its frontmatter `name` set to `name`.

    Install what ships: the packager keeps evals/ out of the .skill file, so a copy
    that carried them would put files in front of the model that no installed user
    ever has, and the hub ships its SKILL.md, LICENSE and references/ alone
    (`sync.hub_shipped`), never its README. A skill's directory name and its frontmatter
    `name` must agree, so both are renamed together. `override` substitutes a different SKILL.md.
    """
    if skill == HUB:
        for rel in sync.hub_shipped(REPO / "skills" / skill):
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / "skills" / skill / rel, dest / rel)
    else:
        shutil.copytree(REPO / "skills" / skill, dest, ignore=shutil.ignore_patterns(*INSTALL_IGNORED))
    skill_md = dest / "SKILL.md"
    if override:
        skill_md.write_text(override.read_text())
    text = skill_md.read_text()
    renamed = re.sub(rf"^name:\s*{re.escape(skill)}\s*$", f"name: {name}", text,
                     count=1, flags=re.MULTILINE)
    if renamed == text:
        raise SystemExit(f"{skill}: frontmatter name not found to rename")
    skill_md.write_text(renamed)


def install_skills(dest_root: Path, run_id: str,
                   overrides: dict[str, Path] | None = None) -> dict[str, str]:
    """Copy each module skill into `dest_root`, the layout's skills folder; return skill ->
    installed name. The hub is never one of them: SKILLS names the three modules.

    The name carries a per-run suffix so a match in the stream can only have come
    from this run's copy, never from a skill the host machine happens to have
    installed.

    `overrides` substitutes a different SKILL.md for a skill without touching the
    working tree — how a description generation is A/B'd against the one that
    ships. Extract the old one with `git show <ref>:skills/<name>/SKILL.md`.
    """
    dest_root.mkdir(parents=True, exist_ok=True)
    names = {}
    for skill in SKILLS:
        names[skill] = f"{skill}-{run_id}"
        install_one(skill, dest_root / names[skill], names[skill], (overrides or {}).get(skill))
    return names


def install_tuesday(dest_root: Path, run_id: str) -> dict[str, str]:
    """The front-door arm: the three modules, hidden, and the hub, `skills/tuesday/` as it
    ships, in `dest_root`, the layout's skills folder; return name -> installed name.

    The hub's references/ are committed, generated by ci/sync.py; an install refuses a
    working tree where they are out of date with the modules, since the run would then
    measure neither what ships nor the modules beside it.
    """
    stale = [p for p in sync.out_of_date() if p.startswith(f"skills/{HUB}/")]
    if stale:
        raise SystemExit(f"the front door's references are out of date ({', '.join(stale[:3])}): "
                         f"run python ci/sync.py")
    names = install_skills(dest_root, run_id)
    for skill, name in names.items():
        skill_md = dest_root / name / "SKILL.md"
        skill_md.write_text(hide(skill_md.read_text()))
    names[HUB] = f"{HUB}-{run_id}"
    install_one(HUB, dest_root / names[HUB], names[HUB])
    return names


def install_plugin(plugin: Path, run_id: str, module: str | None = None) -> dict[str, str]:
    """The plugin layout: the front-door arm's skills under `plugin/skills/` — or, given `module`,
    that one module alone and visible, as the fixture runner's module-alone arm installs it in this
    layout (evals/README.md, "Through Tuesday") — and the manifest that makes the folder a plugin,
    named by `plugin_prefix`; return name -> installed name."""
    if module:
        names = {module: f"{module}-{run_id}"}
        install_one(module, plugin / "skills" / names[module], names[module])
    else:
        names = install_tuesday(plugin / "skills", run_id)
    manifest = plugin / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"name": plugin_prefix(names, "plugin"), "version": "0.0.0",
                                    "description": "A throwaway copy for one routing run"}) + "\n")
    return names


def home(root: Path, layout: str, run: int = 0) -> Path | None:
    """The folder outside the case folder that holds a run's skills: the run's own config folder,
    `config/<case>-<run>`, in the personal layout; the case's plugin in the plugin layout; None in
    the project layout."""
    if layout == "personal":
        return root.parent / OUTSIDE[layout] / f"{root.name}-{run}"
    return root.parent / OUTSIDE[layout] / root.name if layout in OUTSIDE else None


def skills_root(root: Path, layout: str, run: int = 0) -> Path:
    """The folder that holds a run's installed skills, the hub and the modules side by side."""
    return (home(root, layout, run) or root / ".claude") / "skills"


def config_dir(root: Path, layout: str, run: int = 0) -> Path | None:
    """The config folder a run starts with (child_env), in the personal layout; else None, and the
    run keeps the runner's."""
    return home(root, layout, run) if layout == "personal" else None


def runner_config() -> Path:
    """The config folder the runner's own sessions use: its CLAUDE_CONFIG_DIR, else ~/.claude."""
    return Path(child_env().get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def keep_transcripts(config: Path | None) -> None:
    """Copy a run's transcripts from its own config folder into the runner's, where the other
    layouts' runs write theirs, before the temporary folder that holds it is removed."""
    if config is not None and (config / "projects").is_dir():
        shutil.copytree(config / "projects", runner_config() / "projects", dirs_exist_ok=True)


def plugin_prefix(names: dict[str, str], layout: str) -> str | None:
    """The plugin's name, which prefixes every skill it holds: the installed name of the skill it
    lists, in the plugin layout — the hub's, `tuesday-<run id>`, or in a plugin holding one module
    alone (`install_plugin`) that module's; None in the others."""
    if layout != "plugin":
        return None
    return names[HUB] if HUB in names else next(iter(names.values()))


def installed_command(name: str, prefix: str | None = None) -> str:
    """A skill's id as the CLI lists it and its command types it: `<plugin>:<name>` in a plugin."""
    return f"{prefix}:{name}" if prefix else name


def skill_id(skill: str) -> str:
    """A Skill call's name as the CLI reads it: trimmed, and without one leading `/`."""
    skill = skill.strip()
    return skill[1:] if skill.startswith("/") else skill


def local_name(skill: str) -> str:
    """A listed or called skill's name without a plugin prefix: the part of its id (skill_id)
    after the colon."""
    return skill_id(skill).split(":")[-1]


def tuesday_base(skill: str) -> str:
    """A listed or called skill's name without a plugin prefix or a run suffix."""
    return re.sub(r"-[0-9a-f]{8}$", "", local_name(skill))


def foreign_tuesday(listed: list, names: dict[str, str]) -> list[str]:
    """Tuesday skills in the init list that this run did not install (a synced copy, D22).

    Any such skill can take the fire meant for the run's own copy, so the run is void.
    """
    ours = set(names.values())
    bases = set(SKILLS) | {HUB}
    return [s for s in listed if isinstance(s, str) and tuesday_base(s) in bases and local_name(s) not in ours]


def known_arm(arm: str) -> str:
    """`arm`, when it is one of ARMS. Every branch on the arm tests for `tuesday` and gives any
    other value the skills arm's install and reading, so a results file's `arm` from before the
    code-name rename, `frontdoor` on every Tuesday-arm file then, is refused, never read as the
    skills arm."""
    if arm not in ARMS:
        raise ValueError(f"arm {arm!r} is not one of {', '.join(ARMS)}: a results file saved before the "
                         f"code-name rename spells the Tuesday arm 'frontdoor'")
    return arm


def saved_arm(arm: str) -> str:
    """A results file's `arm`, read under either spelling (E25): `frontdoor`, as every Tuesday-arm
    file saved before the code-name rename records it, is the Tuesday arm. For reading a saved
    file only; a run, its timeout and its install take `known_arm`, which refuses the old one."""
    return known_arm(SAVED_ARMS.get(arm, arm))


def saved_value(data: dict, key: str):
    """A results file's `key`, or its value under the key's old spelling (SAVED_KEYS) in a file saved
    before the code-name rename, which records Tuesday's digest as `frontdoor_sha256`. The file is
    read, never rewritten."""
    return data[key] if key in data else data.get(SAVED_KEYS.get(key, key))


def file_sha256(path: Path) -> str:
    """The sha256 of a file's bytes: a results file's `cases_sha256`, of the case file it ran."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def files_sha256(files: list[tuple[str, Path]]) -> str:
    """One sha256 over named files, in name order: each file's name, its length and its bytes."""
    digest = hashlib.sha256()
    for name, path in sorted(files):
        data = Path(path).read_bytes()
        digest.update(f"{name}\0{len(data)}\0".encode("utf-8"))
        digest.update(data)
    return digest.hexdigest()


def modules_sha256(skills_dir: Path = REPO / "skills") -> str:
    """A results file's `modules_sha256`: the three module skills as `install_one` copies them
    (`files_sha256` over each file by its path under skills/, INSTALL_IGNORED left out), before any
    `--skill-md` substitution, which the file records apart (`skill_md`). The skills arm records no
    other digest of what it installed."""
    files = []
    for skill in SKILLS:
        base = skills_dir / skill
        for path in base.rglob("*"):
            rel = path.relative_to(base)
            if path.is_file() and not any(fnmatch.fnmatch(part, pattern)
                                          for part in rel.parts for pattern in INSTALL_IGNORED):
                files.append((f"{skill}/{rel.as_posix()}", path))
    return files_sha256(files)


def harness_sha256(repo: Path = REPO) -> str:
    """A results file's `harness_sha256`: the runner's own code (HARNESS_FILES), by path."""
    return files_sha256([(name, repo / name) for name in HARNESS_FILES])


def init_evidence(event: dict) -> tuple[str, dict]:
    """An init event as a results file keeps it: without the keys that differ on every run
    (INIT_PER_RUN), with its sha256 over canonical JSON, the run's `init_sha256`."""
    kept = {k: v for k, v in event.items() if k not in INIT_PER_RUN}
    text = json.dumps(kept, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest(), kept


def timeout_for(arm: str, prompt: str, given: int | None = None) -> int:
    """The seconds one run gets: `--timeout` when given, else what its reader waits for."""
    known_arm(arm)
    if given:
        return given
    whole_turn = arm == "tuesday" or bool(explicit_command(prompt))
    return TIMEOUT_WHOLE_TURN if whole_turn else TIMEOUT_FIRST_FIRE


def explicit_command(prompt: str) -> str | None:
    """The module a prompt invokes by its slash command (`/mock-interview …`), or None."""
    match = re.match(r"/([a-z0-9-]+)(?=\s|$)", prompt)
    return match.group(1) if match and match.group(1) in SKILLS else None


def explicit_prompt(prompt: str, names: dict[str, str], prefix: str | None = None) -> str:
    """The prompt with its slash command renamed to the installed copy's command.

    The runner suffixes every installed skill, so `/mock-interview` would invoke
    nothing in the throwaway project: E2 has to type `/mock-interview-<run id>`,
    and in the plugin layout, under the plugin's `prefix`, `/tuesday-<run id>:mock-interview-<run id>`.
    """
    command = explicit_command(prompt)
    if command is None:
        return prompt
    return f"/{installed_command(names[command], prefix)}" + prompt[len(command) + 1:]


def child_command(prompt: str, root: Path, names: dict[str, str], model: str | None,
                  layout: str = "project", run: int = 0) -> list[str]:
    """The `claude -p` command one run starts: the prompt as E2 types it in this layout, the
    case's plugin folder in the plugin layout, and outside the project layout leave to read the
    files in the run's skills folder, which a project install has by sitting in the case folder
    (evals/README.md, "Layouts")."""
    cmd = ["claude", "-p", explicit_prompt(prompt, names, plugin_prefix(names, layout)),
           "--output-format", "stream-json", "--verbose", "--include-partial-messages"]
    if model:
        cmd += ["--model", model]
    if layout == "plugin":
        cmd += ["--plugin-dir", str(home(root, layout))]
    if layout in OUTSIDE:
        cmd += ["--allowedTools", read_rule(root, layout, run)]
    return cmd


def read_rule(root: Path, layout: str, run: int = 0) -> str:
    """The permission rule that lets the Read tool open any file in a run's skills folder outside
    the case folder (evals/README.md, "Layouts")."""
    return f"Read(/{skills_root(root, layout, run).absolute().as_posix()}/**)"


def result_outcome(event: dict) -> str:
    """Classify a `result` event: a run the CLI failed is not a run that fired nothing.

    Extracted so the decline path has a test. Every bug this harness has had was a
    non-result recorded as a result, and none of them was caught by anything but a
    person reading output.
    """
    if event.get("is_error") or event.get("subtype") not in (None, "success"):
        return "error"
    return "neither"


def exit_outcome(reader: "RunReader", returncode: int | None) -> str:
    """The outcome of a run whose process exited before its stream decided one. Outside the
    project layout a non-zero exit with no result event read is a run the CLI failed, `error`,
    as a failed sign-in under the personal layout's config folder can be; otherwise the stream
    read settles it, as it did before the layouts."""
    return "error" if returncode and reader.layout != "project" else reader.exited()


def write_attachments(root: Path, case: dict) -> None:
    """Materialise the documents a case's prompt claims are attached.

    A prompt saying "JD and CV attached" in a project containing neither is not
    testing routing. The model looks for the file, does not find it, and asks for
    it rather than starting work — which is correct behaviour and scores as a
    no-fire. Measured before this existed: cases claiming an attachment reached a
    skill on 22% of runs against 55% for self-contained prose.
    """
    for name, content in (case.get("attachments") or {}).items():
        (root / name).write_text(content)


def case_project(tmp: Path, case: dict, run_id: str, overrides: dict[str, Path] | None = None,
                 arm: str = "skills", layout: str = "project", runs: int = 1) -> tuple[Path, dict[str, str]]:
    """One throwaway project per case: the skills where its layout puts them, and that case's
    attachments only. In the personal layout each of the case's `runs` gets a config folder of
    its own, the same skills in each, so no run meets another's transcript or settings.

    The runner used to write every case's attachments into one shared root, on the
    stated assumption that file names were distinct across cases. They were not:
    five cases attach a `jd.txt`, so in a run of several cases each saw the last
    case's posting, and a self-contained case ran beside documents no prompt of
    its own mentioned. A project per case shows each prompt exactly its own files.
    """
    known_arm(arm)
    if layout == "plugin" and arm != "tuesday":
        raise SystemExit("--layout plugin is for the front-door arm: today's three skills do not ship as a plugin")
    root = tmp / f"case-{case['id']}"
    root.mkdir()
    skills = skills_root(root, layout)
    if arm == "tuesday":
        if overrides:
            raise SystemExit("--skill-md substitutes a module description; the front-door arm hides them")
        names = install_plugin(home(root, layout), run_id) if layout == "plugin" else install_tuesday(skills, run_id)
    else:
        names = install_skills(skills, run_id, overrides)
    if layout == "personal":
        for run in range(1, runs):
            shutil.copytree(skills, skills_root(root, layout, run))
    write_attachments(root, case)
    return root, names


def load_cases(path: Path, ids: list[int] | None = None, raw: bytes | None = None) -> list[dict]:
    """The cases of a routing case file, limited to `ids` when given; from `raw`, the file's bytes,
    when the caller has read them, so the cases run are the bytes it hashed (`cases_sha256`).

    A variant file (`--cases`) has the suite's shape. An id asked for that the
    file does not hold is an error, not an empty selection: a typo would
    otherwise report "0/0 passed" as a clean run.
    """
    cases = json.loads((Path(path).read_bytes() if raw is None else raw).decode("utf-8"))["cases"]
    if ids:
        missing = sorted(set(ids) - {c["id"] for c in cases})
        if missing:
            raise SystemExit(f"{path}: no case with id {missing}")
        cases = [c for c in cases if c["id"] in ids]
    return cases


class RunReader:
    """One run's stream events in, its outcome out, once the stream has decided one.

    Its reading is pure, so every label has a test (CONTRIBUTING.md, "Harnesses
    report three outcomes, not two"); only `record`, for an explicit run, reads a
    file. Feed it parsed events with `feed`; it returns the outcome
    once the stream has decided one, else None. `exited` and `timed_out` settle a
    run whose stream never did.

    The labels, by arm:

    - `skills`: the module whose installed name a Skill or Read call carries. The
      run is read up to that call and no further.
    - `tuesday`: the module whose playbook, `tuesday-<id>/references/<m>.md`, is
      read first after the hub fires; `tuesday-unrouted` when the hub fired and the
      run ended with no playbook read; `hidden-<m>` when a hidden module is called,
      or any tool call names its folder, at any point in the turn, which the arm
      exists to prevent. The run is read to its end: round 2 found a hidden
      module's files read after the routing decision, where a reader that stopped
      at the decision never looked.
    - explicit (a prompt that starts with `/<m>`, either arm): read to the end of
      the run. `focused` when the named module loaded and no other module was
      reached; otherwise the first other module reached — `hidden-<other>` when
      it was called by any name or its folder named, `<other>` when its playbook
      was named (`<other>.md`, read through the hub or not) — or `unconfirmed`
      when nothing showed the command loaded. The hub firing is not a failure in
      itself: it is recorded apart (`hub_fired`), since what it does next is
      what the case tests. The CLI's stream-json does not carry the command's
      expansion (measured: none in a run whose transcript holds it), so `record`
      looks for it in the session transcript (`command_loaded`) before settling.
      A timeout is set aside even after a confirmed load, so E2 runs with a
      longer `--timeout` (evals/README.md).
    - a Skill call is read by the name it gives, too (`skill_named`): a module or
      the hub called by its shipped name, with no run suffix, or under a plugin
      prefix, is that module or the hub, in the front-door arm and in E2. The
      name is read as the CLI reads it, trimmed and without one leading `/`.
    - every arm: `neither`, `timeout`, `error`, and `void` when the init event lists
      a Tuesday skill this run did not install.
    - every layout (evals/README.md, "Layouts"): the hub's name is the hub only where
      no colon follows it, so a module's plugin-qualified id, `tuesday-<id>:<m>-<id>`,
      is that module and no hub fire.

    In the front-door arm and in E2, `record` also carries `hub_fired` and
    `reached`, every other module reached in the order reached (the labels
    above), and in E2 `loaded`, whether the named module loaded. Outside the
    project layout it also carries the measures reported and never scored:
    `skills_root_named`, `refused`, `output_tokens`, `cost_usd` (the result
    event's `total_cost_usd`, an API-price equivalent), `result_read` (whether
    the run was read to its result event), the `seconds` `run_once` gives it,
    and in a run with a hub `hub_path_contact`; and the run's evidence:
    `session_id`, which finds its session transcript (`merge_arm`), and
    `init_sha256`, which names its init event in the results file's
    `init_events` (`init_evidence`).
    """

    def __init__(self, names: dict[str, str], arm: str = "skills", explicit: str | None = None,
                 layout: str = "project", root: Path | None = None, run: int = 0):
        self.names = {m: n for m, n in names.items() if m != HUB}
        self.hub = names.get(HUB)
        self.arm, self.explicit = known_arm(arm), explicit
        self.all_names = names
        self.layout = layout
        # The command E2 types, as the transcript records its expansion.
        self.command = installed_command(names[explicit], plugin_prefix(names, layout)) if explicit else None
        # The case folder, where the session starts: a relative path in a tool call is read from it.
        self.cwd = root.absolute().as_posix() if root else None
        # The run's own config folder (personal layout), where its transcript is; None: the runner's.
        self.config = config_dir(root, layout, run) if root else None
        # A skills folder of this layout, any case's or run's, ending a path or followed by a glob.
        self.skills_folder = re.compile(
            rf"(?:^|/){OUTSIDE[layout]}/case-[^/]+/skills(?:/[*?\[{{].*)?$") if layout in OUTSIDE else None
        # The hub's SKILL.md or a playbook, by its path in the hub's folder.
        self.hub_file = re.compile(rf"(?:^|/){re.escape(self.hub)}/(?:SKILL|references/(?:"
                                   + "|".join(map(re.escape, SKILLS)) + r"))\.md$") if self.hub else None
        self.hub_called = False
        self.hub_path_contact = False
        self.skills_root_named = False
        self.refused: list | None = None
        self.output_tokens: int | None = None
        self.cost_usd: float | None = None
        self.result_read = False
        self.init_event: dict | None = None
        self.init_sha256: str | None = None
        self.init_skills: list | None = None
        self.slash_commands: list | None = None
        self.hub_fired = False
        self.expanded = False
        self.loaded = False
        self.reached: list[str] = []
        self.routed: str | None = None
        self.session: dict = {}
        self.message_ids: list[str] = []
        self.pending: str | None = None
        self.accumulated = ""
        self._transcript: bool | None = None

    @property
    def whole_turn(self) -> bool:
        """Whether the run is read to its end rather than to its first fire."""
        return bool(self.explicit) or self.arm == "tuesday"

    def reach(self, label: str) -> None:
        if label not in self.reached:
            self.reached.append(label)

    def names_hub(self, blob: str) -> bool:
        """Whether a tool call's input names the hub: its installed name followed by anything
        but a colon. Followed by a colon it is the plugin prefix of another skill's id, and
        `tuesday-<id>:mock-interview-<id>` is that module. Nothing following it is a partial
        input cut there, and the next piece decides."""
        return bool(self.hub) and re.search(rf"{re.escape(self.hub)}(?=[^:])", blob) is not None

    def observe(self, tool: str | None, given) -> None:
        """Read one whole tool call for the measures reported and never scored, by the paths
        its input names (`paths_named`)."""
        if tool == "Skill":
            skill = given.get("skill") if isinstance(given, dict) else None
            if isinstance(skill, str) and tuesday_base(skill) == HUB:
                self.hub_called = True
            return
        paths = paths_named(tool, given, self.cwd)
        if self.skills_folder and any(self.skills_folder.search(p) for p in paths):
            self.skills_root_named = True
        if not self.hub_called and self.hub_file and any(self.hub_file.search(p) for p in paths):
            self.hub_path_contact = True

    def match(self, blob: str) -> str | None:
        """Read one tool call's input: return the outcome it decides in the skills arm;
        in the front-door arm and in E2, record what it reached and return None."""
        if not self.whole_turn:
            for module, name in self.names.items():
                if name in blob:
                    return module
            return None
        if self.names_hub(blob):
            self.hub_fired = True
        for module, name in self.names.items():
            if name in blob:
                if module == self.explicit:
                    self.loaded = True
                else:
                    self.reach(f"hidden-{module}")
        named = []
        for module in self.names:
            if module == self.explicit:
                continue
            # A playbook's file name, whole. In E2, any mention of another playbook:
            # through the hub's path, or a Bash `cat` from inside its folder. In the
            # front-door arm the call must also name the hub's folder: its full path,
            # or `cd` into it and `cat <module>.md` in one call, the form round 2's
            # measurement scored unrouted twice (evals/README.md). No module ships a
            # file of a playbook's name, so the hub's folder is where one is read.
            hit = re.search(rf"(?<![\w-]){re.escape(module)}\.md(?![\w-])", blob)
            if hit and (self.explicit or self.names_hub(blob)):
                named.append((hit.start(), module))
        # One call can name two playbooks: the first named is the first reached.
        for _, module in sorted(named):
            self.reach(module)
            if not self.explicit and self.routed is None:
                self.routed = module
        return None

    def skill_named(self, given) -> str | None:
        """Read a Skill call by the name it gives, when that name is not this run's
        installed copy: the shipped name (`job-underwriter`), a plugin's
        (`anthropic-skills:job-underwriter`) or another run's. `match` finds only this
        run's suffixed names, so a call by the name the hub's own table uses went
        unseen. The skills arm, outside E2, reads names as it always has. Records
        what it reached; decides no outcome."""
        skill = given.get("skill") if isinstance(given, dict) else None
        if not isinstance(skill, str) or not self.whole_turn:
            return None
        skill = skill_id(skill)
        if local_name(skill) in self.all_names.values():
            return None
        base = tuesday_base(skill)
        if base == HUB:
            self.hub_fired = True
        elif base in self.names and base != self.explicit:
            # The named module by another name loads nothing; it neither passes nor fails.
            self.reach(f"hidden-{base}")
        return None

    def feed(self, event: dict) -> str | None:
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":
            self.init_sha256, self.init_event = init_evidence(event)
            self.init_skills = list(event.get("skills") or [])
            self.slash_commands = list(event.get("slash_commands") or [])
            self.session = {"session_id": event.get("session_id"), "cwd": event.get("cwd")}
            if foreign_tuesday(self.init_skills, self.all_names):
                return "void"
        elif kind == "stream_event":
            se = event.get("event", {})
            sk = se.get("type", "")
            if sk == "content_block_start":
                block = se.get("content_block", {})
                if block.get("type") == "tool_use" and block.get("name") in ("Skill", "Read"):
                    self.pending, self.accumulated = block.get("name"), ""
            elif sk == "content_block_delta" and self.pending:
                delta = se.get("delta", {})
                if delta.get("type") == "input_json_delta":
                    self.accumulated += delta.get("partial_json", "")
                    return self.match(self.accumulated)
            elif sk in ("content_block_stop", "message_stop"):
                if self.pending:
                    hit = self.match(self.accumulated)
                    if not hit and self.pending == "Skill":
                        try:
                            hit = self.skill_named(json.loads(self.accumulated))
                        except json.JSONDecodeError:
                            pass
                    self.pending = None
                    if hit:
                        return hit
                # Deliberately no early exit here: a model often writes a
                # sentence of reasoning before reaching for the skill, so
                # the end of a message is not the end of the decision.
                # Only `result` (or process exit) settles a negative.
        elif kind == "assistant":
            mid = event.get("message", {}).get("id")
            if mid and mid not in self.message_ids:
                self.message_ids.append(mid)
            for item in event.get("message", {}).get("content", []):
                if item.get("type") == "tool_use":
                    blob = json.dumps(item.get("input", {}))
                    self.observe(item.get("name"), item.get("input"))
                    hit = self.match(blob)
                    if not hit and item.get("name") == "Skill":
                        hit = self.skill_named(item.get("input"))
                    if hit:
                        return hit
        elif kind == "user" and self.explicit:
            # The CLI's expansion of a slash command arrives as user content, not a
            # tool call: the sign that `/name` loaded the module.
            content = (event.get("message") or {}).get("content")
            texts = [content] if isinstance(content, str) else \
                [c.get("text", "") for c in content or [] if isinstance(c, dict) and c.get("type") == "text"]
            if any(self.names[self.explicit] in text for text in texts):
                self.expanded = True
        elif kind == "result":
            self.result_read = True
            cost = event.get("total_cost_usd")
            # A cost the event does not give as a number is unread (None), never zero.
            self.cost_usd = float(cost) if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None
            self.refused = [d.get("tool_name") for d in event.get("permission_denials") or [] if isinstance(d, dict)]
            self.output_tokens = (event.get("usage") or {}).get("output_tokens")
            outcome = result_outcome(event)
            return outcome if outcome == "error" else self.settle()
        return None

    def settle(self) -> str:
        """The outcome of a run read to its end (or, in the skills arm, of one that
        ended without a deciding tool call)."""
        if self.explicit:
            if self.reached:
                return self.reached[0]
            return FOCUSED if self.expanded or self.loaded else "unconfirmed"
        hidden = [r for r in self.reached if r.startswith("hidden-")]
        if hidden:
            return hidden[0]
        if self.routed:
            return self.routed
        return "tuesday-unrouted" if self.hub_fired else "neither"

    def exited(self) -> str:
        return self.settle()

    def timed_out(self) -> str:
        """A run cut off is set aside, an E2 run whose module had loaded and an E1 run
        already routed included: the rest of the turn, which the cut-off never showed,
        is where a hidden reach or another module's playbook would be."""
        return "timeout"

    def transcript_loaded(self) -> bool:
        """Whether the session transcript shows the named command expanded (cached)."""
        if self._transcript is None:
            self._transcript = transcript_confirms(self)
        return self._transcript

    def record(self, outcome: str, seconds: float | None = None) -> dict:
        """The run's record: its outcome, and what this reader holds beside it. `seconds` is the
        run's wall time from its start to this outcome, which only the runner knows."""
        rec = {"outcome": outcome, "init_skills": self.init_skills}
        if self.explicit:
            loaded = self.expanded or self.loaded
            if not loaded and outcome not in SET_ASIDE:
                loaded = self.transcript_loaded()
            if outcome == "unconfirmed" and loaded:
                outcome = FOCUSED
            rec.update(outcome=outcome, slash_commands=self.slash_commands, loaded=loaded)
        if self.whole_turn:
            rec.update(hub_fired=self.hub_fired, reached=list(self.reached))
        if self.layout != "project":
            rec.update(skills_root_named=self.skills_root_named, refused=self.refused,
                       output_tokens=self.output_tokens, seconds=seconds, cost_usd=self.cost_usd,
                       result_read=self.result_read, session_id=self.session.get("session_id"),
                       init_sha256=self.init_sha256)
            if self.hub:
                rec["hub_path_contact"] = self.hub_path_contact
        return rec


def strings_in(value) -> list[str]:
    """Every string in a tool call's input, however deep."""
    if isinstance(value, str):
        return [value]
    items = value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
    return [s for item in items for s in strings_in(item)]


def paths_named(tool: str | None, given, cwd: str | None) -> list[str]:
    """Every word of a tool call's input read as a path, absolute and normalised, so `.` and `..`
    are resolved: a relative one from the case folder (`cwd`), or from the folder a `cd` earlier
    in the same string moved to. A Glob's pattern is read from its path, as the tool reads it.
    A word after `~`, or after a `cd` that cannot be followed, is not read; globs stay as written."""
    texts = strings_in(given)
    if tool == "Glob" and isinstance(given, dict) and isinstance(given.get("pattern"), str):
        texts.append(posixpath.join(given.get("path") or "", given["pattern"]))
    found = []
    for text in texts:
        here = cwd
        for segment in SHELL_SEPARATOR.split(text):
            words = SHELL_WORD.findall(segment)
            if words[:1] == ["cd"]:
                here = resolve_path(here, words[1]) if len(words) > 1 else None
                found += [here] if here else []
                continue
            found += [p for p in (resolve_path(here, w) for w in words) if p]
    return found


def resolve_path(here: str | None, word: str) -> str | None:
    """A word as an absolute, normalised path from the folder `here`; None when it cannot be."""
    if word.startswith("~") or word == "-":
        return None
    if word.startswith("/"):
        return posixpath.normpath(word)
    return posixpath.normpath(posixpath.join(here, word)) if here else None


def command_loaded(lines: list[str], message_id: str, installed: str) -> bool:
    """Whether the transcript shows `/installed` expanded ahead of this run's reply.

    Child runs inherit the parent's session id, so runs of one case can share a
    transcript file. The run is found by its own assistant message id, and only
    the entries on its parent chain are read, so another run's expansion in the
    same file never confirms this one.
    """
    entries, start = {}, None
    for line in lines:
        try:
            entry = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(entry, dict) or not entry.get("uuid"):
            continue
        entries[entry["uuid"]] = entry
        if entry.get("type") == "assistant" and (entry.get("message") or {}).get("id") == message_id:
            start = start or entry
    marker = f"<command-name>/{installed}</command-name>"
    entry, seen = start, set()
    while entry and entry["uuid"] not in seen:
        seen.add(entry["uuid"])
        content = (entry.get("message") or {}).get("content")
        texts = [content] if isinstance(content, str) else \
            [c.get("text", "") for c in content or [] if isinstance(c, dict) and c.get("type") == "text"]
        if entry.get("type") == "user" and any(marker in text for text in texts):
            return True
        entry = entries.get(entry.get("parentUuid"))
    return False


def transcript_path(session: dict, config: Path | None = None) -> Path | None:
    """Where the CLI keeps a session's transcript: the projects/ of the config folder the run
    started with (child_env: `config`, else the runner's), under the cwd with every character
    but letters and digits turned to '-'."""
    if not session.get("session_id") or not session.get("cwd"):
        return None
    return ((config or runner_config()) / "projects" / re.sub(r"[^A-Za-z0-9]", "-", session["cwd"])
            / f"{session['session_id']}.jsonl")


def transcript_confirms(reader: "RunReader") -> bool:
    """Whether an E2 run's transcript shows its command expanded, found by the run's own reply."""
    if not reader.message_ids:
        return False
    path = transcript_path(reader.session, reader.config)
    try:
        lines = path.read_text(encoding="utf-8").splitlines() if path else []
    except OSError:
        return False
    return command_loaded(lines, reader.message_ids[0], reader.command)


def run_once(prompt: str, root: Path, names: dict[str, str], timeout: int, model: str | None,
             arm: str = "skills", layout: str = "project", run: int = 0, stream_to: Path | None = None,
             init_events: dict | None = None) -> dict:
    """Run one query, the case's `run`-th; return {"outcome", "init_skills"} (and the slash
    commands, for E2).

    `stream_to`, a file that must not exist, receives every byte of the stream the runner read,
    as read, flushed after each read so a runner stopped by a signal leaves the copy whole: in the
    skills arm through the read that carried the first fire, which can hold later events the
    reader never parsed; the whole turn in a run read to its end. It is opened before the CLI
    starts, so a copy refused starts no run. `init_events` (sha256 -> event) gains the run's init
    event as `init_evidence` keeps it, once per distinct event.

    Outcomes other than a route are kept distinct from 'neither' on purpose. A
    run cut short ('timeout'), a run the CLI failed ('error', typically a rate
    limit) and a run that could see a Tuesday skill it did not install ('void')
    say nothing about routing; folding any of them into 'neither' lets the
    harness manufacture negatives that look like findings.

    Watches partial stream events so, in the skills arm, the verdict lands as soon
    as the model reaches for a skill, rather than after the skill's work
    completes. A front-door or explicit run is read to the end of its turn
    (`RunReader`), so it needs the longer `--timeout` evals/README.md gives.
    """
    reader = RunReader(names, arm, explicit_command(prompt), layout, root, run)
    cmd = child_command(prompt, root, names, model, layout, run)
    # Only the room's own skills: no synced account skills, no parent session, and in the
    # personal layout the run's own config folder (child_env).
    env = child_env(config_dir=reader.config)

    def consume(buffer: str) -> tuple[str | None, str]:
        """Parse whole lines out of the buffer; return a verdict once one lands."""
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                outcome = reader.feed(event)
                if outcome:
                    return outcome, buffer
        return None, buffer

    # Exclusive, and before the CLI starts: a copy never writes over another run's (main refuses a
    # used streams folder), and a copy refused starts no run.
    copy = open(stream_to, "xb") if stream_to else None
    start = time.time()
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                cwd=str(root), env=env)
    except BaseException:
        if copy is not None:
            copy.close()
        raise

    def take(data: bytes) -> str:
        """Bytes read from the stream: copied as read and flushed, since a SIGTERM, as the fix
        round's guard stops a step, runs no `finally`; then decoded."""
        if copy is not None:
            copy.write(data)
            copy.flush()
        return data.decode("utf-8", errors="replace")

    def returncode() -> int | None:
        """The exit status once the stream has ended; None if the process is still running."""
        try:
            return proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            return None

    def done(outcome: str) -> dict:
        """The run's record, with its wall time from start to this outcome."""
        return reader.record(outcome, round(time.time() - start, 1))

    buffer = ""
    try:
        while time.time() - start < timeout:
            exited = proc.poll() is not None
            if exited:
                rest = proc.stdout.read()
                if rest:
                    buffer += take(rest)
            else:
                ready, _, _ = select.select([proc.stdout], [], [], 1.0)
                if not ready:
                    continue
                chunk = os.read(proc.stdout.fileno(), 8192)
                if not chunk:
                    exited = True
                else:
                    buffer += take(chunk)

            # Parse before honouring the exit. The first version of this loop
            # broke out the moment the process was gone, discarding whatever was
            # still sitting unparsed in the pipe — so a run that fired a skill
            # and finished quickly was recorded as 'neither'. Every negative this
            # harness reports has to be a negative it actually read.
            outcome, buffer = consume(buffer)
            if outcome:
                return done(outcome)
            if exited:
                # Trailing line with no newline.
                if buffer.strip():
                    outcome, _ = consume(buffer + "\n")
                    if outcome:
                        return done(outcome)
                return done(exit_outcome(reader, returncode()))
        else:
            return done(reader.timed_out())
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        if copy is not None:
            copy.close()
        if init_events is not None and reader.init_event is not None:
            init_events.setdefault(reader.init_sha256, reader.init_event)
        keep_transcripts(reader.config)
    return done(reader.exited())


def which_fired(prompt: str, root: Path, names: dict[str, str], timeout: int, model: str | None,
                arm: str = "skills", layout: str = "project") -> str:
    """Run one query; return its outcome label alone (see `run_once`)."""
    return run_once(prompt, root, names, timeout, model, arm, layout)["outcome"]


def verdict(expected: str, fired: list[str], siblings: list[str] | None = None) -> tuple[bool, str]:
    """A spanning ('either') case passes when every run that reached a verdict fired
    one of the skills it spans — its `siblings` in the suite — whichever one.

    Timed-out, errored and void runs are set aside rather than counted as
    negatives, and reported alongside the verdict so a case decided on one
    surviving run cannot pass for a clean one. Every other label is a route:
    `tuesday-unrouted` and `hidden-<m>` fail any case, as a wrong skill does.
    """
    aborted = {kind: fired.count(kind) for kind in SET_ASIDE if kind in fired}
    fired = [f for f in fired if f not in SET_ASIDE]
    if not fired:
        detail = ", ".join(f"{n} {kind}" for kind, n in aborted.items())
        return False, f"inconclusive: no run reached a verdict ({detail})"
    suffix = (" [" + ", ".join(f"{n} {kind}" for kind, n in aborted.items()) + "]") if aborted else ""
    unique = set(fired)
    if expected == "either":
        if not siblings:
            raise ValueError("an 'either' case must declare the skills it spans as 'siblings'")
        if unique <= set(siblings):
            return True, f"a sibling fired every run ({'/'.join(sorted(unique))}){suffix}"
        return False, f"a spanning request must reach one of {sorted(siblings)}; got {sorted(unique)}{suffix}"
    if unique == {expected}:
        return True, f"{expected} on every run{suffix}"
    if expected in unique:
        return False, f"inconsistent: {sorted(unique)} (expected {expected} every run){suffix}"
    return False, f"routed to {sorted(unique)}, expected {expected}{suffix}"


def reach(cases: list[dict], runs_by_case: dict[int, list[dict]]) -> dict:
    """How often the runs of the routing cases reached a skill at all, and how often the wrong one.

    The attachment diagnostic (evals/README.md) is decided on this rate, not on
    pass counts: a case that fires its skill on four runs of five fails, and is
    four reaches. Timed-out, errored and void runs are set aside, never counted
    as misses. A wrong skill is one that is not the case's route — for an
    `either` case, not one of the `siblings` it declares. In the front-door arm a
    reach is a playbook read; the hub firing with none read (`tuesday_unrouted`)
    and a hidden module reached (`hidden`) are counted apart, and
    `reached_tuesday` counts the runs whose record says the hub fired
    (`hub_fired`), whatever their outcome: a run that routed and then reached a
    hidden module is `hidden-<m>`, and the hub still fired in it. An explicit
    case (a prompt opening with a module's command) is not a routing case: its
    runs are summarised by `explicit_summary`, and none is counted here.
    """
    decided = reached = wrong = unrouted = hidden = hub = set_aside = 0
    by_skill: dict[str, int] = {}
    for case in cases:
        if explicit_command(case["prompt"]):
            continue
        for run in runs_by_case.get(case["id"], []):
            got = run["outcome"]
            if got in SET_ASIDE:
                set_aside += 1
                continue
            decided += 1
            unrouted += got == "tuesday-unrouted"
            hidden += got.startswith("hidden-")
            hub += bool(run.get("hub_fired"))
            if got in SKILLS:
                reached += 1
                by_skill[got] = by_skill.get(got, 0) + 1
                allowed = case.get("siblings", []) if case["expected"] == "either" else [case["expected"]]
                if got not in allowed:
                    wrong += 1
    return {"decided": decided, "reached": reached, "wrong_skill": wrong, "by_skill": by_skill,
            "tuesday_unrouted": unrouted, "reached_tuesday": hub, "hidden": hidden, "set_aside": set_aside}


def passes_on(case: dict) -> str:
    """The label every run of a case must carry to pass: `focused` for an explicit
    case (its `expected` names the module its command starts), else `expected`."""
    return FOCUSED if explicit_command(case["prompt"]) else case["expected"]


def explicit_summary(cases: list[dict], runs_by_case: dict[int, list[dict]]) -> dict:
    """E2 across its explicit cases: focused runs, hub fires and other modules reached.

    Set-aside runs (timeout, error, void) are counted apart and nothing else is
    read from them. A hub fire is reported, never scored: the run is scored on
    whether another module was reached, which `reached` already holds whether it
    went through the hub or not. `other_reached` counts runs by the first other
    module each reached (their outcome); `reached_any` counts every label any run
    reached, so a run that reached two modules shows in both.
    """
    out = {"decided": 0, "focused": 0, "unconfirmed": 0, "hub_fired": 0, "hub_fired_focused": 0,
           "other_reached": {}, "reached_any": {}, "set_aside": 0}
    for case in cases:
        if not explicit_command(case["prompt"]):
            continue
        for run in runs_by_case.get(case["id"], []):
            got = run["outcome"]
            if got in SET_ASIDE:
                out["set_aside"] += 1
                continue
            out["decided"] += 1
            out["focused"] += got == FOCUSED
            out["unconfirmed"] += got == "unconfirmed"
            hub = bool(run.get("hub_fired"))
            out["hub_fired"] += hub
            out["hub_fired_focused"] += hub and got == FOCUSED
            if got not in (FOCUSED, "unconfirmed"):
                out["other_reached"][got] = out["other_reached"].get(got, 0) + 1
            for label in run.get("reached") or []:
                out["reached_any"][label] = out["reached_any"].get(label, 0) + 1
    return out


def median(values: list[float]) -> float | None:
    """The middle value, or the mean of the middle two; None for no values."""
    ordered = sorted(values)
    middle = len(ordered) // 2
    if not ordered:
        return None
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def result_was_read(run: dict) -> bool:
    """Whether a run was read to its result event: its `result_read`, or, in a record saved before
    that key existed, whether it has a refusal list, which only the result event gives
    (evals/README.md, "Layouts")."""
    return bool(run["result_read"]) if "result_read" in run else run.get("refused") is not None


def reported(cases: list[dict], runs_by_case: dict[int, list[dict]]) -> dict:
    """The measures recorded and never scored, over the arm's decided runs, routing and explicit
    cases alike: runs with `hub_path_contact`, runs with `skills_root_named`, refused tool calls
    and the runs that had any, and `refused_unread`, the runs that ended before their result
    event: their refusals were never read, so they are not counted as none.

    `result_read` counts the decided runs read to their result event (`result_was_read`) and
    `stopped_before_result` the others: a skills-arm run stops at its first fire. Wall time,
    output tokens and cost (`cost_usd`, the result event's `total_cost_usd`, an API-price
    equivalent) are summed, and given as a median a run, over the runs read to their result event
    only, so a run stopped early never lowers them; `seconds_read`, `tokens_read` and `cost_read`
    count the runs among those whose record holds a value. A total over no run is 0 and its median
    None: read a total with its count. Set-aside runs (timeout, error, void) are not counted, an
    error run read to its result event and costed included."""
    out = {"decided": 0, "hub_path_contact": 0, "skills_root_named": 0, "refused": 0, "runs_refused": 0,
           "refused_unread": 0}
    seconds, tokens, costs, read = [], [], [], 0
    for case in cases:
        for run in runs_by_case.get(case["id"], []):
            if run["outcome"] in SET_ASIDE:
                continue
            out["decided"] += 1
            out["hub_path_contact"] += bool(run.get("hub_path_contact"))
            out["skills_root_named"] += bool(run.get("skills_root_named"))
            refused = run.get("refused")
            if refused is None:
                out["refused_unread"] += 1
            else:
                out["refused"] += len(refused)
                out["runs_refused"] += bool(refused)
            if not result_was_read(run):
                continue
            read += 1
            if run.get("seconds") is not None:
                seconds.append(run["seconds"])
            if run.get("output_tokens") is not None:
                tokens.append(run["output_tokens"])
            if run.get("cost_usd") is not None:
                costs.append(run["cost_usd"])
    out.update(result_read=read, stopped_before_result=out["decided"] - read,
               seconds=round(sum(seconds), 1), seconds_median=median(seconds), seconds_read=len(seconds),
               output_tokens=sum(tokens), output_tokens_median=median(tokens), tokens_read=len(tokens),
               cost_usd=round(sum(costs), 4), cost_usd_median=median(costs), cost_read=len(costs))
    return out


def measures_line(measures: dict, arm: str) -> list[str]:
    """The `reported, not scored:` line, and, when any decided run was stopped before its result
    event, the line that says what its tokens, seconds and cost then cover. It takes `reported`'s
    own dict: a `reported` saved before `result_read` summed every decided run's seconds, so a
    saved file is summarised from its runs (`reported` over them), never from that dict.

    Refused tool calls are read from the result event too, so they are given over the runs read to
    it, never as a measured zero for runs whose refusals went unread."""
    n, r, s = measures["decided"], measures["result_read"], measures["stopped_before_result"]
    # The runs with a refusal list: the runs read to their result event, in any record the runner writes.
    q = n - measures["refused_unread"]

    def were(count: int) -> str:
        return f"{count} {'was' if count == 1 else 'were'}"

    def over(count: int, what: str) -> str:
        return f", over the {count} that recorded {what}" if count != r else ""
    hub = (f"the hub's files reached by path before any Skill call to it on {measures['hub_path_contact']}/{n}; "
           if arm == "tuesday" else "")
    head = (f"reported, not scored: {hub}the skills folder named on {measures['skills_root_named']}/{n}; "
            f"of {n} decided run{'' if n == 1 else 's'}, {were(r)} read to the result event and {were(s)} stopped "
            f"before it; ")
    refusals = (f"{measures['refused']} tool calls refused, on {measures['runs_refused']} runs"
                + over(q, "a refusal list"))
    if not r:
        unread = "refused tool calls, wall time, output tokens and cost" if not q else \
            f"{refusals}; wall time, output tokens and cost"
        lines = [head + f"{unread}: none read to their result event"]
    else:
        w, t, c = measures.get("seconds_read"), measures["tokens_read"], measures["cost_read"]
        wall = ("wall time: none recorded" if measures["seconds_median"] is None else
                f"wall time {measures['seconds']}s, median {round(measures['seconds_median'], 2)}s a run"
                + (over(w, "it") if w is not None else ""))
        tokens = ("output tokens: none recorded" if not t else
                  f"output tokens {measures['output_tokens']}, median {measures['output_tokens_median']} a run"
                  + over(t, "them"))
        cost = ("cost: none recorded" if not c else
                f"cost ${measures['cost_usd']:.4f} (API-price-equivalent estimate, from result events), "
                f"median ${measures['cost_usd_median']:.4f} a run" + over(c, "one"))
        lines = [head + f"over {'it' if r == 1 else f'those {r}'}: "
                        f"{refusals if q else 'refused tool calls: none recorded'}; {wall}; {tokens}; {cost}"]
    if s:
        why = "a skills-arm run stops at its first fire" if arm != "tuesday" else "the CLI exited before writing one"
        lines.append(f"tokens, seconds and cost above cover only runs read to their result event: {s} "
                     f"run{'s' if s != 1 else ''} stopped before it ({why}), so these figures do not compare "
                     f"with an arm read to the end of each turn")
    return lines


def summary_lines(summary: dict, explicit: dict, arm: str, measures: dict | None = None) -> list[str]:
    """The lines a run prints after its cases: the reach lines for the routing cases,
    the `explicit:` line for the explicit ones, each only when its suite had runs,
    so a passing E2 never prints a reach rate of 0; and outside the project layout the
    `reported` line, `measures`."""
    lines = []
    if summary["decided"] or summary["set_aside"]:
        rate = f"{100 * summary['reached'] / summary['decided']:.0f}%" if summary["decided"] else "n/a"
        lines.append(f"reached a skill on {summary['reached']}/{summary['decided']} decided runs ({rate}); "
                     f"wrong skill on {summary['wrong_skill']}; "
                     f"{summary['set_aside']} timed out, errored or void, set aside")
        if arm == "tuesday":
            lines.append(f"tuesday fired on {summary['reached_tuesday']}/{summary['decided']} "
                         f"({summary['tuesday_unrouted']} unrouted); hidden modules reached {summary['hidden']}")
    if explicit["decided"] or explicit["set_aside"]:
        lines.append(f"explicit: focused on {explicit['focused']}/{explicit['decided']} decided runs; "
                     f"another module reached on {sum(explicit['other_reached'].values())} "
                     f"{dict(sorted(explicit['other_reached'].items()))}; unconfirmed {explicit['unconfirmed']}; "
                     f"the hub fired on {explicit['hub_fired']} (reported, not scored; "
                     f"{explicit['hub_fired_focused']} of them focused); "
                     f"{explicit['set_aside']} timed out, errored or void, set aside")
    if measures is not None:
        lines += measures_line(measures, arm)
    return lines


def set_aside_problem(summary: dict) -> str | None:
    """Why an arm's runs cannot be scored, or None: more than SET_ASIDE_LIMIT of them set aside.

    The bar re-runs such an arm. Void runs count with timeouts and errors: a host
    whose init list carries a synced Tuesday skill voids every run, and an arm
    scored on what survived would read its empty counts as gates met.
    """
    total = summary["decided"] + summary["set_aside"]
    if total and summary["set_aside"] / total > SET_ASIDE_LIMIT:
        return (f"{summary['set_aside']} of {total} runs timed out, errored or were void "
                f"(over {SET_ASIDE_LIMIT:.0%}): this arm is not scored; fix the cause and re-run it")
    return None


class MergeRefused(ValueError):
    """A merge `merge_arm` will not make: the reason is the message, and nothing is written."""


# What every file of a merge must share with the arm it fills, read under either spelling (E25).
MERGE_FROZEN = ("arm", "layout", "model", "hub_sha256", "tuesday_sha256")
# What a file records only since recovery existed: compared where both files record it, so an arm
# saved before still merges. `cases_sha256` falls back to the case file's name.
MERGE_RECORDED = ("cases_sha256", "modules_sha256", "harness_sha256", "skill_md")
# The digests a merge holds to the measured commit's (`expect`), where a file records them.
MERGE_EXPECTED = ("hub_sha256", "tuesday_sha256", "cases_sha256", "modules_sha256")
# A results file's summaries, recomputed by a merge from its runs, never carried over.
MERGE_RECOMPUTED = ("unscored", "passed", "total", "reach", "explicit", "reported", "init_events", "streams",
                    "results", "merged")


def frozen_of(data: dict) -> dict:
    """The fields a re-run must share with the arm it fills (MERGE_FROZEN), the arm and Tuesday's
    digest read under either spelling: a saved file's `frontdoor` and `frontdoor_sha256` are
    `tuesday` and `tuesday_sha256`."""
    out = {key: saved_value(data, key) for key in MERGE_FROZEN}
    try:
        out["arm"] = saved_arm(out["arm"])
    except ValueError as exc:
        raise MergeRefused(str(exc)) from None
    return out


def merge_arm(primary: dict | None, reruns: list[dict], transcripts: Callable[[str], str | None],
              expect: dict, cases: list[dict]) -> dict:
    """An arm's results (`primary`) with its killed and never-started runs filled from `reruns`,
    every summary recomputed with this runner's own functions; MergeRefused when the files cannot
    be merged. Pure: `transcripts` gives a session's transcript text by its session id, or None;
    `expect` holds the measured commit's digests (MERGE_EXPECTED), each checked where a file
    records it; `cases` are the case file's cases, which the summaries need (prompts, siblings).

    - It replaces only `error` runs proven killed: a run whose `session_id`, shared with no other
      run of the arm, finds a transcript holding the usage-limit message (LIMIT).
    - It fills never-started slots: a case holding fewer runs than `runs_per_case`.
    - Per case the re-runs must number the kills plus the slots, exactly. It refuses re-runs for
      a case with neither, re-runs for a case the arm does not hold, and re-runs for a case that
      also holds an `error` run left unproven, its slots included: a re-run carries no mark of the
      run it stands for, so beside an error not proven killed it may stand for that error (beside a
      proven kill too, the mixed kill/error batch). An unproven error in a case offered no re-run is
      kept, and counts toward the set-aside share as any error does. A refusal names why each
      error is unproven (`unproven`).
    - It refuses a file that differs from the arm in arm, layout, model or Tuesday's digests
      (MERGE_FROZEN); in its case file (`cases_sha256` where both record it, else the file's name),
      module or harness digest, or `--skill-md` substitutions, where both record them
      (MERGE_RECORDED); a re-run of a case at another `timeout` or route; and any recorded digest
      that is not `expect`'s.
    - It confirms each file's cases against what it ran: the case file's ids, or the `--case` ids
      it records (`case_ids`), where it records them, and no case twice. A file saved before
      `case_ids` is held to the case file's ids by membership only; `merged.cases_not_held` lists
      the case file's ids the arm does not hold.
    - A re-run's session id must be no other run's, so the merged arm can prove a kill again.
    - With no primary, the arm wrote no results: run it again whole.

    The primary's own fields are kept as saved, its old spellings included; `init_events` is the
    union of every file's; `merged` says what was filled, and nests a primary's own `merged`."""
    if primary is None:
        raise MergeRefused("no results: run the arm again whole")
    files = [("the arm", primary)] + [(f"re-run file {n}", d) for n, d in enumerate(reruns, 1)]
    arm_frozen = frozen_of(primary)
    case_file_ids = [c["id"] for c in cases]
    for label, data in files:
        if data is not primary:
            for key, value in frozen_of(data).items():
                if value != arm_frozen[key]:
                    raise MergeRefused(f"{label}: {key} {value!r} differs from the arm's {arm_frozen[key]!r}")
            for key in MERGE_RECORDED:
                ours, theirs = data.get(key), primary.get(key)
                if ours is not None and theirs is not None and ours != theirs:
                    raise MergeRefused(f"{label}: {key} {ours} differs from the arm's {theirs}")
            named, arm_named = data.get("cases_file"), primary.get("cases_file")
            if not (data.get("cases_sha256") and primary.get("cases_sha256")) \
                    and Path(str(named)).name != Path(str(arm_named)).name:
                raise MergeRefused(f"{label}: cases file {named} is not the arm's {arm_named}")
        for key in MERGE_EXPECTED:
            got, want = saved_value(data, key), expect.get(key)
            if got is not None and want is not None and got != want:
                raise MergeRefused(f"{label}: {key} {got} is not the measured commit's {want}")
        held = [res["id"] for res in data["results"]]
        twice = sorted({cid for cid in held if held.count(cid) > 1})
        if twice:
            raise MergeRefused(f"{label}: case(s) {twice} listed more than once")
        if "case_ids" in data:
            ran = case_file_ids if data["case_ids"] is None else data["case_ids"]
            if sorted(held) != sorted(ran):
                raise MergeRefused(f"{label}: holds cases {sorted(held)}, but ran "
                                   + ("the whole case file, " if data["case_ids"] is None else "--case ")
                                   + f"{sorted(ran)}")

    by_id = {c["id"]: c for c in cases}
    fills: dict[int, list[dict]] = {}
    offered: dict[int, list[tuple[str, dict]]] = {}
    for label, data in files[1:]:
        for res in data["results"]:
            fills.setdefault(res["id"], []).extend(res["runs"])
            offered.setdefault(res["id"], []).append((label, res))
    primary_sessions = Counter(run.get("session_id") for res in primary["results"] for run in res["runs"]
                               if run.get("session_id"))
    seen = Counter(primary_sessions)
    for label, data in files[1:]:
        for res in data["results"]:
            for run in res["runs"]:
                sid = run.get("session_id")
                if sid and seen[sid]:
                    raise MergeRefused(f"{label}: case {res['id']}: session {sid} is already a run of the arm, "
                                       f"or of another re-run: a re-run is a session of its own")
                if sid:
                    seen[sid] += 1

    def unproven(run: dict) -> str | None:
        """Why an `error` run is not proven killed, or None when its transcript proves the kill."""
        sid = run.get("session_id")
        if not isinstance(sid, str) or not sid:
            return ("it recorded no session id: a run saved before session ids were recorded, a project-layout "
                    "run, or one whose init event was never read cannot prove a kill")
        if primary_sessions[sid] != 1:
            return f"its session id {sid} is shared with another run of the arm"
        text = transcripts(sid)
        if text is None:
            return f"no transcript was found for its session id {sid}"
        if not LIMIT.search(text):
            return f"its transcript, found by its session id {sid}, holds no usage-limit message"
        return None

    per_case = primary["runs_per_case"]
    results, runs_by_case, used, passed, filled = [], {}, [], 0, 0
    killed_by_case, never_started, kept, replaced = {}, {}, {}, {}
    for old in primary["results"]:
        cid = old["id"]
        case = by_id.get(cid)
        if case is None:
            raise MergeRefused(f"case {cid}: not in the cases file")
        if passes_on(case) != old["expected"]:
            raise MergeRefused(f"case {cid}: the cases file expects {passes_on(case)}, "
                               f"the arm recorded {old['expected']}")
        for label, res in offered.get(cid, []):
            if res.get("expected", old["expected"]) != old["expected"]:
                raise MergeRefused(f"case {cid}: {label} recorded the route {res['expected']}, the arm {old['expected']}")
            if res.get("timeout") is not None and old.get("timeout") is not None and res["timeout"] != old["timeout"]:
                raise MergeRefused(f"case {cid}: {label} ran at timeout {res['timeout']}, the arm at "
                                   f"{old['timeout']}: a re-run is made with the arm's flags")
        runs = list(old["runs"])
        if len(runs) > per_case:
            raise MergeRefused(f"case {cid}: {len(runs)} runs, more than the arm's runs_per_case {per_case}")
        errors = [k for k, run in enumerate(runs) if run["outcome"] == "error"]
        why = {k: unproven(runs[k]) for k in errors}
        proven = [k for k in errors if why[k] is None]
        doubted = [k for k in errors if why[k] is not None]
        missing = per_case - len(runs)
        queue = fills.pop(cid, [])
        if queue and doubted:
            causes = "; ".join(f"run {k}: {why[k]}" for k in doubted)
            if proven:
                raise MergeRefused(f"case {cid}: {len(queue)} re-run(s) offered beside {len(proven)} proven kill(s) and "
                                   f"{len(doubted)} error run(s) not proven killed ({causes}): a mixed kill/error "
                                   f"batch, where a killed run cannot be told from a real error")
            raise MergeRefused(f"case {cid}: {len(queue)} re-run(s) offered for a case whose {len(doubted)} error "
                               f"run(s) are not proven killed ({causes}): an error not proven killed is kept, and its "
                               f"case takes no re-run, its never-started slots included, since a re-run carries no "
                               f"mark of the run it stands for")
        if queue and not proven and not missing:
            raise MergeRefused(f"case {cid}: {len(queue)} re-run(s) for a case with no killed or never-started run")
        if len(queue) != len(proven) + missing:
            raise MergeRefused(f"case {cid}: {len(proven)} killed run(s) and {missing} never-started slot(s), "
                               f"but {len(queue)} re-run(s)")
        if doubted:
            kept[cid] = len(doubted)
        if proven:
            killed_by_case[cid] = len(proven)
            replaced[cid] = [runs[k]["session_id"] for k in proven]
        if missing:
            never_started[cid] = missing
        for k in proven:
            runs[k] = queue.pop(0)
        runs += queue
        filled += len(proven) + missing
        runs_by_case[cid] = runs
        used.append(case)
        fired = [run["outcome"] for run in runs]
        ok, note = verdict(old["expected"], fired, case.get("siblings"))
        passed += ok
        results.append({**old, "fired": fired, "runs": runs, "passed": ok, "note": note})
    if fills:
        raise MergeRefused(f"re-runs for cases the arm does not hold: {sorted(fills)}")

    summary = reach(used, runs_by_case)
    explicit = explicit_summary(used, runs_by_case)
    measures = reported(used, runs_by_case) if primary.get("layout") != "project" else None
    init_events: dict = {}
    for _, data in files:
        init_events.update(data.get("init_events") or {})
    merged = {k: v for k, v in primary.items() if k not in MERGE_RECOMPUTED}
    merged.update(unscored=set_aside_problem({k: summary[k] + explicit[k] for k in ("decided", "set_aside")}),
                  passed=passed, total=len(results), reach=summary,
                  **({"explicit": explicit} if explicit["decided"] or explicit["set_aside"] else {}),
                  **({"reported": measures} if measures is not None else {}),
                  **({"init_events": init_events} if init_events or "init_events" in primary else {}),
                  results=results,
                  merged={"reruns": len(reruns), "runs_filled": filled, "killed_by_case": killed_by_case,
                          "never_started_by_case": never_started, "errors_kept_by_case": kept,
                          "replaced_sessions": replaced,
                          "cases_not_held": [cid for cid in case_file_ids if cid not in runs_by_case],
                          **({"previous": primary["merged"]} if "merged" in primary else {}),
                          "note": "error runs whose session transcript holds the usage-limit message, and slots "
                                  "that never started, filled by re-runs of the same arm, layout, model, digests, "
                                  "cases file and timeouts; every summary recomputed (evals/README.md, \"Recovering "
                                  "a cut-short arm\")"})
    return merged


def transcript_reader(projects: Path) -> Callable[[str], str | None]:
    """`merge_arm`'s `transcripts`: a session's transcript text from `projects/<folder>/<id>.jsonl`,
    the CLI's transcript folder, where every layout's runs leave theirs (`keep_transcripts`), or
    None when there is none. Only a session id of letters, digits and hyphens is looked up."""
    def read(session_id: str) -> str | None:
        if not re.fullmatch(r"[A-Za-z0-9-]+", session_id or ""):
            return None
        found = sorted(projects.glob(f"*/{session_id}.jsonl"))
        return "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in found) if found else None
    return read


def merge_main(args: argparse.Namespace) -> int:
    """`--merge PRIMARY --rerun FILE... --json-out OUT`: write the merged arm to OUT, which must not
    exist, and print its summary. Exit 2 on a refusal, with nothing written; otherwise as a run
    exits (0 every case passed, 1 not, 3 unscored)."""
    def refuse(why: str) -> int:
        print(f"merge refused: {why}", file=sys.stderr)
        return 2

    if not args.json_out:
        return refuse("--merge writes a new results file: give it --json-out OUT")
    out = Path(args.json_out)
    if out.exists():
        return refuse(f"{out} exists: a merge never writes over a results file")
    primary_path = Path(args.merge)
    if not primary_path.is_file():
        return refuse(f"{primary_path}: no results: run the arm again whole")
    try:
        primary = json.loads(primary_path.read_text(encoding="utf-8"))
        reruns = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.rerun]
    except (OSError, ValueError) as exc:
        return refuse(f"a results file cannot be read: {exc}")
    cases_file = Path(primary.get("cases_file") or "")
    cases_file = cases_file if cases_file.is_absolute() else REPO / cases_file
    if not cases_file.is_file():
        return refuse(f"the arm's cases file {cases_file} is not there")
    if args.expect:
        # The measured commit's payload, named: the module digest is then held across the files only.
        expect = {"hub_sha256": args.expect[0], "tuesday_sha256": args.expect[1]}
    else:
        expect = {**{k: v for k, v in sync.digests().items() if k in MERGE_EXPECTED},
                  "modules_sha256": modules_sha256()}
    projects = args.projects or runner_config() / "projects"
    try:
        # Read once: the cases merged are the bytes hashed.
        raw = cases_file.read_bytes()
        expect["cases_sha256"] = hashlib.sha256(raw).hexdigest()
        cases = load_cases(cases_file, raw=raw)
    except (OSError, ValueError, KeyError) as exc:
        return refuse(f"the arm's cases file {cases_file} cannot be read: {exc!r}")
    try:
        merged = merge_arm(primary, reruns, transcript_reader(projects), expect, cases)
    except MergeRefused as exc:
        return refuse(str(exc))
    except (KeyError, TypeError) as exc:
        return refuse(f"a results file is not one this runner wrote: {exc!r}")
    merged["merged"]["files"] = [str(primary_path), *map(str, args.rerun)]
    # Each file's stream copies stay beside it (`streams`, relative to that file's folder).
    merged["merged"]["streams"] = [str(Path(p).parent / d["streams"]) if d.get("streams") else None
                                   for p, d in zip([primary_path, *args.rerun], [primary, *reruns])]
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "x", encoding="utf-8") as handle:
        handle.write(json.dumps(merged, indent=2) + "\n")
    info = merged["merged"]
    print(f"merged {primary_path} with {len(reruns)} re-run file(s): filled {info['runs_filled']} run(s); "
          f"killed by case {info['killed_by_case'] or 'none'}; "
          f"never started by case {info['never_started_by_case'] or 'none'}; "
          f"real errors kept {info['errors_kept_by_case'] or 'none'}; {merged['passed']}/{merged['total']} passed; "
          f"wrote {out}")
    if info["cases_not_held"]:
        print(f"the arm holds {merged['total']} of its case file's {merged['total'] + len(info['cases_not_held'])} "
              f"cases: not {info['cases_not_held']}")
    arm = saved_arm(primary["arm"])
    explicit = merged.get("explicit") or explicit_summary([], {})
    for line in summary_lines(merged["reach"], explicit, arm, merged.get("reported")):
        print(line)
    if merged["unscored"]:
        print(f"\nWARNING: {merged['unscored']}")
        return 3
    return 0 if merged["passed"] == merged["total"] else 1


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3, help="runs per case (routing is probabilistic)")
    ap.add_argument("--arm", choices=ARMS, default="skills",
                    help="skills: the three modules as they ship; tuesday: skills/tuesday, modules hidden")
    ap.add_argument("--layout", choices=LAYOUTS, default="project",
                    help="where the skills are installed: project, the case folder's .claude/skills/; personal, "
                         "a config folder of the case's own; plugin, a plugin (front-door arm only)")
    ap.add_argument("--cases", type=Path, default=SUITE, metavar="FILE",
                    help="the case file to run (default: evals/suite-routing.json)")
    ap.add_argument("--case", type=int, action="append", help="limit to case id(s)")
    ap.add_argument("--model", default=None)
    ap.add_argument("--timeout", type=int, default=None,
                    help=f"seconds per run (default: {TIMEOUT_WHOLE_TURN} for a run read to the end of its "
                         f"turn, the front-door arm or an explicit case; {TIMEOUT_FIRST_FIRE} otherwise)")
    ap.add_argument("--workers", type=int, default=3, help="parallel runs; high values invite rate limiting")
    ap.add_argument("--json-out", default=None,
                    help="write full results here, and a copy of each run's stream under streams/<its stem>/ beside it")
    ap.add_argument("--skill-md", action="append", default=[], metavar="SKILL=PATH",
                    help="substitute a SKILL.md for one skill, to A/B a description generation")
    ap.add_argument("--merge", type=Path, default=None, metavar="PRIMARY",
                    help="run nothing: merge this arm's results file with the --rerun files of its killed and "
                         "never-started runs into --json-out, which must not exist")
    ap.add_argument("--rerun", type=Path, action="extend", nargs="+", default=[], metavar="FILE",
                    help="with --merge: a results file of re-runs, same arm, layout, model, digests, cases file and timeout")
    ap.add_argument("--expect", nargs=2, default=None, metavar=("HUB", "TUESDAY"),
                    help="with --merge: the measured commit's hub_sha256 and tuesday_sha256 (default: this checkout's, "
                         "and its modules_sha256 too)")
    ap.add_argument("--projects", type=Path, default=None, metavar="DIR",
                    help="with --merge: the CLI's transcript folder, where a killed run's session transcript is "
                         "(default: the runner's config folder's projects/)")
    return ap


def streams_folder(json_out: str | os.PathLike) -> Path:
    """Where a run's stream copies go: `streams/<results file's stem>/` beside the results file, a
    folder of its own, since the arms of one measurement share a folder."""
    out = Path(json_out)
    return out.parent / "streams" / out.stem


def main() -> int:
    args = parser().parse_args()
    if args.merge is not None:
        return merge_main(args)
    if args.rerun or args.expect or args.projects:
        raise SystemExit("--rerun, --expect and --projects are for --merge")
    if args.json_out and Path(args.json_out).exists():
        raise SystemExit(f"{args.json_out} exists: a run never writes over a results file; name another --json-out")
    # Read once: the cases run are the bytes `cases_sha256` names, whatever happens to the file during the arm.
    cases_raw = Path(args.cases).read_bytes()
    cases = load_cases(args.cases, args.case, cases_raw)
    streams = streams_folder(args.json_out) if args.json_out else None
    if streams is not None and streams.is_dir() and any(streams.iterdir()):
        raise SystemExit(f"{streams} already holds streams: a run never writes over another's evidence; name "
                         f"another --json-out, and leave the folder where it is: the results file that wrote it "
                         f"names it (`streams`), under any name the file is later given")
    if streams is not None:
        streams.mkdir(parents=True, exist_ok=True)
    # The init event of each run outside the project layout, once per distinct event (init_evidence).
    init_events: dict | None = {} if args.layout != "project" else None

    with tempfile.TemporaryDirectory() as tmp:
        overrides = {}
        for item in args.skill_md:
            skill, _, path = item.partition("=")
            if skill not in SKILLS or not path:
                raise SystemExit(f"--skill-md expects one of {SKILLS} as SKILL=PATH, got {item!r}")
            overrides[skill] = Path(path)
        run_id = uuid.uuid4().hex[:8]
        projects = {c["id"]: case_project(Path(tmp), c, run_id, overrides, args.arm, args.layout, args.runs)
                    for c in cases}
        frozen = sync.digests() if args.arm == "tuesday" else {}
        # What the arm ran, beside Tuesday's digests: the modules as they ship, any SKILL.md put in place
        # of one, and the runner's own code (`merge_arm` holds a re-run to them).
        frozen.update(modules_sha256=modules_sha256(), harness_sha256=harness_sha256(),
                      skill_md={skill: file_sha256(path) for skill, path in sorted(overrides.items())})

        jobs = [(c, i) for c in cases for i in range(args.runs)]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            records = list(pool.map(
                lambda job: run_once(job[0]["prompt"], *projects[job[0]["id"]],
                                     timeout_for(args.arm, job[0]["prompt"], args.timeout), args.model,
                                     args.arm, args.layout, job[1],
                                     stream_to=streams / f"case-{job[0]['id']}-{job[1]}.jsonl" if streams else None,
                                     init_events=init_events),
                jobs,
            ))

    fired_by_case: dict[int, list[str]] = {}
    runs_by_case: dict[int, list[dict]] = {}
    for (case, _), record in zip(jobs, records):
        fired_by_case.setdefault(case["id"], []).append(record["outcome"])
        runs_by_case.setdefault(case["id"], []).append(record)

    results, passed = [], 0
    for case in cases:
        fired = fired_by_case[case["id"]]
        expected = passes_on(case)
        ok, note = verdict(expected, fired, case.get("siblings"))
        passed += ok
        results.append({"id": case["id"], "expected": expected,
                        "timeout": timeout_for(args.arm, case["prompt"], args.timeout),
                        **({"command": case["expected"]} if expected == FOCUSED else {}),
                        **{k: case[k] for k in ("derived_from", "arm") if k in case},
                        "fired": fired, "runs": runs_by_case[case["id"]], "passed": ok, "note": note})
        print(f"{'PASS' if ok else 'FAIL'}  case {case['id']:>2}  expected {expected:<16} {note}")

    print(f"\n{passed}/{len(cases)} routing cases passed ({args.runs} run(s) each, arm {args.arm}, "
          f"layout {args.layout}, from {args.cases})")
    summary = reach(cases, runs_by_case)
    explicit = explicit_summary(cases, runs_by_case)
    measures = reported(cases, runs_by_case) if args.layout != "project" else None
    for line in summary_lines(summary, explicit, args.arm, measures):
        print(line)
    unscored = set_aside_problem({k: summary[k] + explicit[k] for k in ("decided", "set_aside")})
    if unscored:
        print(f"\nWARNING: {unscored}")
    if args.json_out:
        text = json.dumps(
            {"cases_file": str(args.cases), "cases_sha256": hashlib.sha256(cases_raw).hexdigest(),
             "case_ids": [c["id"] for c in cases] if args.case else None, "arm": args.arm,
             "layout": args.layout, **frozen, "model": args.model,
             "runs_per_case": args.runs, "unscored": unscored,
             "passed": passed, "total": len(cases), "reach": summary,
             **({"explicit": explicit} if explicit["decided"] or explicit["set_aside"] else {}),
             **({"reported": measures} if measures is not None else {}),
             **({"init_events": init_events} if init_events is not None else {}),
             "streams": streams.relative_to(Path(args.json_out).parent).as_posix(),
             "results": results},
            indent=2) + "\n"
        out = Path(args.json_out)
        try:
            handle = open(out, "x", encoding="utf-8")
        except FileExistsError:
            # Made during the arm by something else: kept, and these results written beside it.
            out = out.with_name(f"{out.stem}.{run_id}{out.suffix}")
            print(f"\nWARNING: {args.json_out} appeared during the run and is kept; these results are in {out}")
            handle = open(out, "x", encoding="utf-8")
        with handle:
            handle.write(text)
    if unscored:
        return 3
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
