#!/usr/bin/env python3
"""Tests for the eval harnesses.

These exist because the harnesses have had four bugs and, until now, no tests.
Every one of the four was the same mistake wearing different clothes — a
non-result recorded as a result — and every one was found by a person reading
output that looked wrong, which is the slowest and least reliable detector
available:

1. The routing reader broke out of its loop when the CLI process exited,
   discarding whatever was still unparsed in the pipe. A run that fired a skill
   and finished quickly was recorded as `neither`.
2. A run the CLI failed, usually a rate limit, was also recorded as `neither`.
3. A grader reply truncated mid-object yielded zero verdicts, and the summary
   counted twelve missing verdicts as twelve failures.
4. A session usage-limit message was saved as a 48-character response and graded
   as a fixture that had produced almost nothing.

The rule those four earned is in CONTRIBUTING.md: every path where an external
process can decline needs an explicit third outcome beside success and failure.
The tests below assert that third outcome on each path, so the rule has a
mechanism rather than a paragraph.

The research rooms added more such paths — a search server that can fail to
start or answer with an error, a room that is not the mode it claims, a stream
cut off by a timeout, a grader reply that covers six expectations of sixteen, a
response with no accounting table — and each has its third outcome tested here
too: harness-invalid, incomplete, unresolved, absent or unparseable, never a pass
and never a skill failure it was not.

    python evals/test_harness.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import backfill_tools
import output_checks
import ledger_rules  # noqa: E402  (ci/, put on the path by output_checks)
import recurring
import run_fixtures
import run_routing
import routing_variants

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ci"))
import sync  # noqa: E402  (ci/: the front door's generator and the generated-copy sync)

FAILURES: list[str] = []
SERVER = Path(__file__).resolve().parent / "research_server.py"


def check(name: str, got, want) -> None:
    if got == want:
        print(f"  ok   {name}")
    else:
        FAILURES.append(f"{name}: got {got!r}, wanted {want!r}")
        print(f"  FAIL {name}: got {got!r}, wanted {want!r}")


def check_true(name: str, got: bool) -> None:
    check(name, bool(got), True)


def verdict_of(result: dict, check_name: str, target="all") -> str | None:
    """The verdict a check reported, or None if it reported nothing."""
    hits = [c["verdict"] for c in result["checks"]
            if c["check"] == check_name and c["target"] == str(target)]
    return "FAIL" if "FAIL" in hits else (hits[0] if hits else None)


# --- Decline path 1 & 2: routing classifies a failed or aborted run distinctly ---

def test_routing_declines() -> None:
    print("routing: a run that did not reach a verdict is not a negative")
    check("clean result is a genuine no-fire",
          run_routing.result_outcome({"type": "result", "subtype": "success"}), "neither")
    check("is_error result is an error, not a no-fire",
          run_routing.result_outcome({"type": "result", "is_error": True}), "error")
    check("non-success subtype is an error",
          run_routing.result_outcome({"type": "result", "subtype": "error_max_turns"}), "error")

    ok, note = run_routing.verdict("job-underwriter", ["job-underwriter"] * 3)
    check("consistent fire passes", ok, True)
    ok, note = run_routing.verdict("job-underwriter", ["job-underwriter", "neither", "job-underwriter"])
    check("one genuine no-fire fails the case", ok, False)

    ok, note = run_routing.verdict("job-underwriter", ["job-underwriter", "error", "job-underwriter"])
    check("an errored run is set aside, not counted against the case", ok, True)
    check_true("and it is reported", "error" in note)

    ok, note = run_routing.verdict("mock-interview", ["timeout", "error", "error"])
    check("a case with no run that reached a verdict is inconclusive, not a failure to fire", ok, False)
    check_true("and says so rather than reporting a route", "inconclusive" in note)

    ok, _ = run_routing.verdict("neither", ["neither"] * 3)
    check("a clean negative passes", ok, True)
    ju_mi = ["job-underwriter", "mock-interview"]
    ok, _ = run_routing.verdict("either", ["job-underwriter", "mock-interview", "job-underwriter"], ju_mi)
    check("a spanning case passes when some sibling fires every run", ok, True)
    ok, _ = run_routing.verdict("either", ["job-underwriter", "neither", "job-underwriter"], ju_mi)
    check("a spanning case fails when a run reaches neither sibling", ok, False)
    # Case 21 spans job-underwriter and resume-tailor. A hard-coded pair once scored
    # its correct resume-tailor fires as misses; the case's own siblings decide now.
    ju_rt = ["job-underwriter", "resume-tailor"]
    ok, _ = run_routing.verdict("either", ["resume-tailor", "job-underwriter", "resume-tailor"], ju_rt)
    check("a spanning case passes on any of its own siblings", ok, True)
    ok, _ = run_routing.verdict("either", ["mock-interview", "job-underwriter", "job-underwriter"], ju_rt)
    check("a skill the spanning case does not span fails it", ok, False)
    try:
        run_routing.verdict("either", ["job-underwriter"])
        check("an 'either' verdict without siblings is refused", False, True)
    except ValueError:
        check("an 'either' verdict without siblings is refused", True, True)


def test_routing_cases() -> None:
    print("\nrouting: --cases picks the case file, and each case runs in a project of its own")
    suite_path = Path(__file__).resolve().parent / "suite-routing.json"
    suite = json.loads(suite_path.read_text())
    default = run_routing.parser().parse_args([])
    check("without --cases the runner reads the suite", default.cases.resolve(), suite_path)
    check("and runs every suite case, in the suite's order",
          run_routing.load_cases(default.cases, default.case), suite["cases"])
    check("--case still limits the suite to the ids asked for",
          [c["id"] for c in run_routing.load_cases(default.cases, [9, 3])], [3, 9])
    try:
        run_routing.load_cases(default.cases, [3, 999])
        check("an id the file does not hold is an error, not an empty run", "no error", "SystemExit")
    except SystemExit as exc:
        check_true("an id the file does not hold is an error, not an empty run", "999" in str(exc))
    arm_b = Path(__file__).resolve().parent / routing_variants.OUTPUTS["B"]
    args = run_routing.parser().parse_args(["--cases", str(arm_b), "--case", "203"])
    picked = run_routing.load_cases(args.cases, args.case)
    check("--cases reads another file, and --case selects within it",
          [(c["id"], c["derived_from"]) for c in picked], [(203, 3)])

    # Five suite cases attach a jd.txt. One shared project root, as the runner had,
    # showed every case the last case's posting.
    cases = [{"id": 1, "attachments": {"jd.txt": "first posting"}},
             {"id": 2, "attachments": {"jd.txt": "second posting"}}, {"id": 3}]
    with tempfile.TemporaryDirectory() as tmp:
        made = {c["id"]: run_routing.case_project(Path(tmp), c, "ab12cd34") for c in cases}
        check("two cases attaching the same file name each see their own",
              [(made[n][0] / "jd.txt").read_text() for n in (1, 2)], ["first posting", "second posting"])
        check("a case with no attachment sees no other case's",
              sorted(p.name for p in made[3][0].iterdir()), [".claude"])
        check("every project installs every skill under this run's names",
              [sorted(p.name for p in (made[n][0] / ".claude" / "skills").iterdir()) for n in (1, 3)],
              [sorted(f"{s}-ab12cd34" for s in run_routing.SKILLS)] * 2)
        check("and the runner is told those names", made[1][1],
              {s: f"{s}-ab12cd34" for s in run_routing.SKILLS})

    summary = run_routing.reach(
        [{"id": 1, "expected": "job-underwriter", "prompt": "p"},
         {"id": 2, "expected": "either", "siblings": ["job-underwriter", "mock-interview"], "prompt": "p"}],
        {1: runs("job-underwriter", "neither", "resume-tailor", "timeout", "error"),
         2: runs("mock-interview", "resume-tailor", "neither")})
    check("the reach rate counts decided runs only; a wrong skill is one off the case's route or siblings",
          {k: summary[k] for k in ("decided", "reached", "wrong_skill", "set_aside")},
          {"decided": 6, "reached": 4, "wrong_skill": 2, "set_aside": 2})
    check("and fires are listed by skill",
          summary["by_skill"], {"job-underwriter": 1, "resume-tailor": 2, "mock-interview": 1})


def test_child_env() -> None:
    print("\nrooms: a measured session inherits no synced skills and no parent session")
    import child_env
    base = {"PATH": "/usr/bin", "HTTPS_PROXY": "http://proxy", "CLAUDECODE": "1",
            "CLAUDE_CODE_SYNC_SKILLS": "1", "CLAUDE_CODE_SESSION_ID": "abc",
            "CLAUDE_CODE_REMOTE_SESSION_ID": "cse_abc"}
    env = child_env.child_env(base)
    check("the sync flag, the parent session (local and remote id) and the nesting guard are dropped",
          sorted(k for k in base if k not in env),
          ["CLAUDECODE", "CLAUDE_CODE_REMOTE_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_SYNC_SKILLS"])
    check("everything else is kept, the proxy included", {k: env[k] for k in ("PATH", "HTTPS_PROXY")},
          {"PATH": "/usr/bin", "HTTPS_PROXY": "http://proxy"})
    check("without a config folder the parent's CLAUDE_CONFIG_DIR is kept, or none set, as before",
          (child_env.child_env({**base, "CLAUDE_CONFIG_DIR": "/runner"})["CLAUDE_CONFIG_DIR"],
           "CLAUDE_CONFIG_DIR" in env), ("/runner", False))
    check("a config folder given (the personal layout) is the child's CLAUDE_CONFIG_DIR, over the parent's",
          child_env.child_env({**base, "CLAUDE_CONFIG_DIR": "/runner"}, Path("/tmp/x/config/case-1"))["CLAUDE_CONFIG_DIR"],
          "/tmp/x/config/case-1")
    for runner in ("run_routing.py", "run_fixtures.py"):
        source = (Path(__file__).resolve().parent / runner).read_text()
        check_true(f"{runner} starts its sessions with child_env()", re.search(r"\benv = child_env\(", source))
        check_true(f"{runner} builds no environment of its own", "os.environ.items()" not in source)


def test_routing_timeouts() -> None:
    print("\nrouting: a run read to the end of its turn gets the long timeout without a flag")
    t = run_routing.timeout_for
    check("skills arm, routing case: stops at its first fire, so the short default",
          t("skills", "help me decide on this role"), run_routing.TIMEOUT_FIRST_FIRE)
    check("front-door arm, routing case: read to the end of the turn",
          t("frontdoor", "help me decide on this role"), run_routing.TIMEOUT_WHOLE_TURN)
    check("an explicit case is read to the end in either arm",
          (t("skills", "/mock-interview prep me"), t("frontdoor", "/mock-interview prep me")),
          (run_routing.TIMEOUT_WHOLE_TURN, run_routing.TIMEOUT_WHOLE_TURN))
    check("a given --timeout wins everywhere", (t("skills", "x", 30), t("frontdoor", "/mock-interview x", 30)), (30, 30))
    check("the long default is longer than the short one",
          run_routing.TIMEOUT_WHOLE_TURN > run_routing.TIMEOUT_FIRST_FIRE, True)
    check("the parser leaves --timeout unset unless given", run_routing.parser().parse_args([]).timeout, None)
    source = (Path(__file__).resolve().parent / "run_routing.py").read_text()
    check_true("every run's timeout comes from timeout_for",
               "timeout_for(args.arm, job[0][\"prompt\"], args.timeout)" in source and "args.timeout, args.model" not in source)


def test_routing_variants() -> None:
    print("\nrouting: the diagnostic's variant files are the generator's output")
    here = Path(__file__).resolve().parent
    suite = json.loads((here / "suite-routing.json").read_text())
    built = routing_variants.build(suite)
    check("each committed variant file is exactly what the generator writes from the suite",
          {name: (here / name).read_text() == text for name, text in built.items()},
          {name: True for name in routing_variants.OUTPUTS.values()})
    by_id = {c["id"]: c for c in suite["cases"]}
    arms = {arm: json.loads(built[name])["cases"] for arm, name in routing_variants.OUTPUTS.items()}
    check("arm B derives from the six attachment cases, arm C from the nine self-contained positives",
          {arm: [c["derived_from"] for c in cases] for arm, cases in arms.items()},
          {"B": [3, 9, 15, 17, 18, 21], "C": [1, 2, 4, 5, 6, 7, 8, 10, 16]})
    every = [c for cases in arms.values() for c in cases]
    check("no variant id is a suite id, and none repeats",
          (sorted(set(by_id) & {c["id"] for c in every}), len({c["id"] for c in every}) == len(every)), ([], True))
    check("every variant keeps its source's route", [c["id"] for c in every
                                                     if c["expected"] != by_id[c["derived_from"]]["expected"]], [])
    check_true("arm B: the message opens with the suite's, carries each attachment verbatim, and the files stay",
               all(c["prompt"].startswith(by_id[c["derived_from"]]["prompt"] + "\n\n")
                   and c["attachments"] == by_id[c["derived_from"]]["attachments"]
                   and all(f"{name}:\n{text}" in c["prompt"] for name, text in c["attachments"].items())
                   for c in arms["B"]))
    words = lambda text: text.split()  # noqa: E731
    lead = routing_variants.ATTACHED_SENTENCE
    moved = [c for c in arms["C"] if "unchanged" not in c]
    check_true("arm C: the message is the fixed sentence and intent spans, the file the rest — "
               "together exactly the suite's words",
               all(c["prompt"].startswith(lead + " ") and sorted(c["attachments"]) == [routing_variants.ATTACHED_FILE]
                   and not set(c["attachments"]) & set(by_id[c["derived_from"]].get("attachments") or {})
                   for c in moved)
               and all(sorted(words(c["prompt"][len(lead):]) + words(c["attachments"][routing_variants.ATTACHED_FILE]))
                       == sorted(words(by_id[c["derived_from"]]["prompt"])) for c in moved))
    check("parity: every arm-A message, and every arm-C message, names what its ask is about",
          {arm: [n for n in ids if not routing_variants.topic_nouns(text(n))] for arm, ids, text in
           (("A", routing_variants.ARM_B_CASES, lambda n: by_id[n]["prompt"]),
            ("C", [c["id"] for c in arms["C"]], lambda n: next(c for c in arms["C"] if c["id"] == n)["prompt"]))},
          {"A": [], "C": []})
    check_true("and a moved message keeps its topic noun from its own spans, not from the fixed sentence",
               all(routing_variants.topic_nouns(c["prompt"][len(lead):]) for c in moved)
               and not routing_variants.topic_nouns(lead))
    check("arm C: only case 8, which carries no domain content, runs as it stands",
          [(c["derived_from"], c["prompt"] == by_id[c["derived_from"]]["prompt"], "attachments" in c)
           for c in arms["C"] if "unchanged" in c], [(8, True, False)])
    # Arms A and D run suite cases by hand-typed --case lists in the README; each must
    # pick the cases its paired variant arm derives from, or the per-case pairing breaks.
    readme = (here / "README.md").read_text()
    typed = {arm.upper(): [int(n) for n in re.findall(r"--case (\d+)", ids)] for arm, ids in
             re.findall(r"--json-out arm-([ad])\.json \\\n((?:\s*--case \d+)+)", readme)}
    check("the README's arm A and D commands run exactly the cases arms B and C derive from",
          typed, {"A": list(routing_variants.ARM_B_CASES), "D": list(routing_variants.ARM_C_CASES)})
    edited = json.loads(json.dumps(suite))
    next(c for c in edited["cases"] if c["id"] == 6)["prompt"] = "How should I tailor my answers to her?"
    try:
        routing_variants.build(edited)
        check("a suite edit that breaks an intent span stops the generator", "built", "SystemExit")
    except SystemExit as exc:
        check_true("a suite edit that breaks an intent span stops the generator", "case 6" in str(exc))


# --- The front-door arm: generation, clashes, install, labels, explicit naming ---

def module_tree(root: Path, files: dict[str, dict[str, str]], bodies: dict[str, str] | None = None) -> Path:
    """A synthetic skills/ folder: module -> {reference name: text}."""
    for module, refs in files.items():
        (root / module / "references").mkdir(parents=True)
        text = (bodies or {}).get(module, f"# {module}\n\nRead `references/{next(iter(refs))}`.\n")
        (root / module / "SKILL.md").write_text(f"---\nname: {module}\ndescription: Does {module}.\n---\n\n{text}")
        for name, ref in refs.items():
            (root / module / "references" / name).write_text(ref)
    return root


def test_frontdoor_generation() -> None:
    print("\nfront door: references/ is generated, deterministically, from the module sources")
    repo = Path(__file__).resolve().parent.parent
    files = sync.generate()
    check("generating twice gives the same files", files == sync.generate(), True)
    check("a playbook per module", sorted(n for n in files if n[:-3] in run_routing.SKILLS),
          [f"{s}.md" for s in run_routing.SKILLS])
    for module in run_routing.SKILLS:
        source = (repo / "skills" / module / "SKILL.md").read_text()
        playbook = files[f"{module}.md"]["text"]
        check(f"{module}'s playbook is its SKILL.md body with the frontmatter stripped, its contents listed, "
              f"and only clash paths moved",
              playbook, sync.with_paths_note(sync.with_contents(
                  sync.body(source).replace("references/rationale.md", f"references/{module}-rationale.md"))))
        listing_end = playbook.index("\n\n", playbook.index("## Contents\n\n") + len("## Contents\n\n"))
        check(f"{module}'s playbook says where its paths resolve, first thing after its contents list",
              playbook[listing_end:listing_end + 2 + len(sync.PATHS_NOTE)], "\n\n" + sync.PATHS_NOTE)
        lines = playbook.splitlines()
        check(f"{module}'s playbook opens with '## Contents' directly under its H1, as a file over 100 lines must",
              [line for line in lines[:3] if line.strip()], [lines[0], "## Contents"])
        headings = [line.lstrip("#").strip() for line in sync.body(source).splitlines()
                    if line.startswith(("## ", "### "))]
        listed = [line.strip()[2:] for line in playbook.partition("## Contents\n\n")[2].split("\n\n", 1)[0].splitlines()]
        check(f"{module}'s contents list names its ## and ### headings, in order", listed, headings)
        check_true(f"{module}'s playbook names only files the hub carries",
                   set(sync.LINK.findall(playbook)) <= set(files))
        check(f"{module}'s rationale.md, which clashes, is carried as {module}-rationale.md, unchanged",
              files[f"{module}-rationale.md"]["text"],
              (repo / "skills" / module / "references" / "rationale.md").read_text())
    check("no file is carried under its clashing name", "rationale.md" in files, False)
    mirror = (repo / "skills" / "resume-tailor" / "references" / "citations.md").read_text()
    check("a convention mirror is one byte-identical file", files["citations.md"]["text"], mirror)
    check("every distinct module reference and mirror is carried once, beside one playbook per module",
          len(files), len({(p.name, p.read_text()) for m in sync.modules()
                           for p in (repo / "skills" / m / "references").glob("*.md")})
          + len(run_routing.SKILLS))
    hub = sync.HUB.read_text()
    check("the committed hub links every generated file directly, and nothing else",
          sync.hub_links(hub), set(files))
    # Round 2: Haiku read a playbook's files from the hidden module's own folder.
    section3 = hub.partition("## 3. Run the chosen module")[2].partition("\n## ")[0]
    check_true("the hub's section 3, which the paths note points to, says whose references/ a path means "
               "and rules out the modules' own folders",
               "this skill's own `references/`" in section3 and "never read from them" in " ".join(section3.split()))
    check_true("the paths note names no references/ file, so it adds no link the hub must carry",
               not sync.LINK.findall(sync.PATHS_NOTE))
    check_true("the paths note points to the hub without saying SKILL.md, which section 3 item 1 says "
               "means the playbook inside one",
               "SKILL.md" not in sync.PATHS_NOTE and "section 3" in sync.PATHS_NOTE)


def test_frontdoor_clashes() -> None:
    print("\nfront door: a name clash is resolved by renaming, or refused")
    with tempfile.TemporaryDirectory() as tmp:
        root = module_tree(Path(tmp) / "a", {
            "alpha": {"notes.md": "alpha's notes", "shared.md": "same text", "own.md": "see rationale and notes.md"},
            "beta": {"notes.md": "beta's notes", "shared.md": "same text"}},
            bodies={"alpha": "# Alpha\n\nRead `references/notes.md`, then `references/own.md` and "
                             "`references/shared.md`; not `conventions/notes.md`.\n"})
        files = sync.generate(root)
        check("different text under one name: each module's copy gets its module's prefix",
              {n: files[n]["text"] for n in ("alpha-notes.md", "beta-notes.md")},
              {"alpha-notes.md": "alpha's notes", "beta-notes.md": "beta's notes"})
        check("the same text under one name is one shared file", files["shared.md"]["text"], "same text")
        check("the playbook's path moves to its own module's copy; other paths are untouched",
              files["alpha.md"]["text"],
              "# Alpha\n\n" + sync.PATHS_NOTE + "\n\nRead `references/alpha-notes.md`, then "
              "`references/own.md` and `references/shared.md`; not `conventions/notes.md`.\n")
        check("a module's own file that names a clashing file points at that module's copy",
              files["own.md"]["text"], "see rationale and alpha-notes.md")

        bad = module_tree(Path(tmp) / "b", {
            "alpha": {"notes.md": "a", "shared.md": "read notes.md"},
            "beta": {"notes.md": "b", "shared.md": "read notes.md"}})
        try:
            sync.generate(bad)
            check("a shared file naming a clashing file is refused, not guessed", "generated", "refused")
        except SystemExit as exc:
            check_true("a shared file naming a clashing file is refused, not guessed", "cannot be resolved" in str(exc))

        collide = module_tree(Path(tmp) / "c", {
            "alpha": {"notes.md": "a", "alpha-notes.md": "already here"},
            "beta": {"notes.md": "b"}})
        try:
            sync.generate(collide)
            check("a renamed file that would overwrite another is refused", "generated", "refused")
        except SystemExit as exc:
            check_true("a renamed file that would overwrite another is refused", "already is" in str(exc))

        playbook_name = module_tree(Path(tmp) / "d", {"alpha": {"beta.md": "alpha's note on beta"},
                                                     "beta": {"x.md": "x"}})
        files = sync.generate(playbook_name)
        check("a module file named like a playbook is renamed, so the playbook keeps its name",
              (files["alpha-beta.md"]["text"], files["beta.md"]["from"]),
              ("alpha's note on beta", "skills/beta/SKILL.md (body)"))

        fenced = module_tree(Path(tmp) / "f", {"alpha": {"x.md": "x"}},
                             bodies={"alpha": "# Alpha\n\nIntro.\n\n## One\n\n```text\n## not a heading\n```\n\n"
                                              "### One a\n\n## Two\n"})
        check("a playbook's contents list its ## and ### headings, ### nested, and skip fenced code",
              sync.generate(fenced)["alpha.md"]["text"],
              "# Alpha\n\n## Contents\n\n- One\n  - One a\n- Two\n\n" + sync.PATHS_NOTE + "\n\nIntro.\n\n"
              "## One\n\n```text\n## not a heading\n```\n\n### One a\n\n## Two\n")
        listed = "# Alpha\n\n## Contents\n\n- One\n\n## One\n"
        check("a playbook that already opens with its contents is left as it is",
              sync.with_contents(listed), listed)
        check("the paths note goes after an existing contents list, under a bare H1, or first with no H1",
              (sync.with_paths_note(listed), sync.with_paths_note("# A\n\nBody.\n"),
               sync.with_paths_note("Body.\n")),
              (f"# Alpha\n\n## Contents\n\n- One\n\n{sync.PATHS_NOTE}\n\n## One\n",
               f"# A\n\n{sync.PATHS_NOTE}\n\nBody.\n", f"{sync.PATHS_NOTE}\n\nBody.\n"))

        dangling = module_tree(Path(tmp) / "e", {"alpha": {"x.md": "x"}},
                               bodies={"alpha": "Read `references/missing.md`.\n"})
        try:
            sync.generate(dangling)
            check("a playbook naming a file the hub would not carry is refused", "generated", "refused")
        except SystemExit as exc:
            check_true("a playbook naming a file the hub would not carry is refused", "missing.md" in str(exc))


def test_frontdoor_install() -> None:
    print("\nfront door: the arm installs the hub and the three modules, hidden")
    repo = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory() as tmp:
        root, names = run_routing.case_project(Path(tmp), {"id": 7, "attachments": {"jd.txt": "x"}},
                                               "ab12cd34", None, "frontdoor")
        installed = root / ".claude" / "skills"
        check("the hub and every module are installed under this run's names",
              sorted(p.name for p in installed.iterdir()),
              sorted([f"{s}-ab12cd34" for s in run_routing.SKILLS] + ["tuesday-ab12cd34"]))
        check("and the runner is told those names", names,
              {**{s: f"{s}-ab12cd34" for s in run_routing.SKILLS}, "tuesday": "tuesday-ab12cd34"})
        for skill in run_routing.SKILLS:
            copy = (installed / f"{skill}-ab12cd34" / "SKILL.md").read_text().splitlines()
            source = (repo / "skills" / skill / "SKILL.md").read_text().splitlines()
            source[source.index(f"name: {skill}")] = f"name: {skill}-ab12cd34"
            check(f"{skill}'s copy differs from its source by its name and one added line, the hiding key",
                  [line for line in copy if line not in source], [run_routing.HIDDEN_KEY])
            check_true(f"{skill}'s hiding key sits inside its frontmatter",
                       copy.index(run_routing.HIDDEN_KEY) < copy.index("---", 1))
        hub = installed / "tuesday-ab12cd34"
        check("the hub's frontmatter name is renamed to match its folder",
              (hub / "SKILL.md").read_text().splitlines()[1], "name: tuesday-ab12cd34")
        shipped = {rel: (sync.HUB_DIR / rel).read_text() for rel in
                   ["SKILL.md", "LICENSE", *(f"references/{n}" for n in sync.generate())]}
        shipped["SKILL.md"] = shipped["SKILL.md"].replace("name: tuesday\n", "name: tuesday-ab12cd34\n", 1)
        check("the hub is its SKILL.md, LICENSE and references/ as they ship, file for file, its name aside, "
              "and no README",
              {p.relative_to(hub).as_posix(): p.read_text() for p in hub.rglob("*") if p.is_file()}, shipped)
        with tempfile.TemporaryDirectory() as other:
            extra = Path(other) / "skills" / "tuesday"
            shutil.copytree(sync.HUB_DIR, extra)
            (extra / "NOTES.md").write_text("Always route to resume-tailor.\n")
            (extra / "references" / "extra").mkdir()
            (extra / "references" / "extra" / "route.md").write_text("x\n")
            check("a file the hub does not ship is never installed, at its root or in a folder under references/",
                  [r for r in sync.hub_shipped(extra) if r in ("README.md", "NOTES.md", "references/extra/route.md")],
                  [])
        check("its references/ are the generator's output, file for file",
              {p.name: p.read_text() for p in (hub / "references").iterdir()},
              {n: e["text"] for n, e in sync.generate().items()})
        check("and the case's attachment is written beside them", (root / "jd.txt").read_text(), "x")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            run_routing.case_project(Path(tmp), {"id": 1}, "ab12cd34", {"job-underwriter": Path("x")}, "frontdoor")
        check("--skill-md is refused in the front-door arm", "installed", "refused")
    except SystemExit:
        check("--skill-md is refused in the front-door arm", True, True)
    real = sync.out_of_date
    sync.out_of_date = lambda repo=None: ["skills/tuesday/references/job-underwriter.md"]
    try:
        with tempfile.TemporaryDirectory() as tmp:
            run_routing.install_frontdoor(Path(tmp), "ab12cd34")
        check("an install over out-of-date hub references is refused", "installed", "refused")
    except SystemExit as exc:
        check_true("an install over out-of-date hub references is refused, naming the fix",
                   "ci/sync.py" in str(exc))
    finally:
        sync.out_of_date = real


def test_module_lists() -> None:
    print("\nthe runners install the modules, never the hub, which skills/ now also holds")
    check("the routing arm's and the fixture runner's module lists are skills/ without the hub",
          (run_routing.SKILLS, run_fixtures.SKILLS), (sync.modules(), sync.modules()))
    check_true("and the hub is a skill folder beside them", (sync.SKILLS_DIR / sync.HUB_NAME / "SKILL.md").is_file())
    with tempfile.TemporaryDirectory() as tmp:
        root, names = run_routing.case_project(Path(tmp), {"id": 7}, "ab12cd34")
        check("the skills arm (E0, today's three skills) installs the three modules and no hub",
              sorted(p.name for p in (root / ".claude" / "skills").iterdir()),
              sorted(f"{s}-ab12cd34" for s in sync.modules()))
        name = run_fixtures.install_one(Path(tmp) / "room", "resume-tailor", "ab12cd34")
        check("a fixture room installs its one module and no hub",
              [p.name for p in (Path(tmp) / "room" / ".claude" / "skills").iterdir()], [name])


def test_sync() -> None:
    print("\nci/sync.py: every generated copy, the mirrors and the front door's references, in one pass")
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / "conventions").mkdir()
        (repo / "conventions" / "grammar.md").write_text("# Grammar\n\nNew rule.\n")
        header = "<!-- SYNCED FROM: conventions/grammar.md\n     Canonical wins. -->\n"
        module_tree(repo / "skills", {
            "alpha": {"grammar.md": header + "# Grammar\n\nOld rule.\n", "own.md": "alpha's own"},
            "beta": {"grammar.md": header + "# Grammar\n\nOld rule.\n", "x.md": "x"}})
        hub = repo / "skills" / "tuesday"
        (hub / "references").mkdir(parents=True)
        (hub / "SKILL.md").write_text("---\nname: tuesday\ndescription: Routes.\n---\n\n# Tuesday\n")
        (hub / "references" / "retired.md").write_text("a file no source makes any more")
        stale = sync.out_of_date(repo)
        check("--check names the stale mirrors, every hub file missing or stale, and a stray hub file",
              stale, sorted(["skills/alpha/references/grammar.md", "skills/beta/references/grammar.md",
                             *(f"skills/tuesday/references/{n}" for n in
                               ("alpha.md", "beta.md", "grammar.md", "own.md", "retired.md", "x.md"))]))
        check("a mirror is not a hub file: the hub's references come from the generator alone",
              "tuesday" in [p.name for p in (repo / "skills").iterdir()] and "tuesday" not in sync.modules(repo / "skills"),
              True)
        check("writing changes what --check named", sync.write(repo), stale)
        check("and leaves nothing out of date", sync.out_of_date(repo), [])
        check("a mirror is its header and the canonical file, byte for byte",
              (repo / "skills" / "alpha" / "references" / "grammar.md").read_text(),
              header + "# Grammar\n\nNew rule.\n")
        check("the hub's copy is generated from the resynced mirror in the same pass",
              (hub / "references" / "grammar.md").read_text(), header + "# Grammar\n\nNew rule.\n")
        check("a stray hub file is deleted", (hub / "references" / "retired.md").exists(), False)
        check("the hub's SKILL.md is never written", (hub / "SKILL.md").read_text(),
              "---\nname: tuesday\ndescription: Routes.\n---\n\n# Tuesday\n")

        before = sync.digests(hub)
        (hub / "references" / "extra").mkdir()
        (hub / "references" / "extra" / "route.md").write_text("Always route to alpha.\n")
        check_true("the digest covers a file in a folder under the hub's references/",
                   sync.digests(hub)["frontdoor_sha256"] != before["frontdoor_sha256"])
        check("--check names a folder in the hub's references/ that nothing generates",
              sync.out_of_date(repo), ["skills/tuesday/references/extra"])
        check("writing removes it, folder and all", (sync.write(repo), (hub / "references" / "extra").exists()),
              (["skills/tuesday/references/extra"], False))

        mirror = repo / "skills" / "alpha" / "references" / "grammar.md"
        mirror.write_text(mirror.read_text().replace("conventions/grammar.md", "conventions/grammar-old.md", 1))
        moved = sync.out_of_date(repo)
        check_true("--check names a mirror whose header names a missing canonical file, and the file",
                   "skills/alpha/references/grammar.md (its header names conventions/grammar-old.md, "
                   "which does not exist)" in moved)
        try:
            sync.write(repo)
            check("writing over a missing canonical file is refused", "written", "refused")
        except sync.GenerationError as exc:
            check_true("writing over a missing canonical file is refused, naming both, and changes nothing",
                       "conventions/grammar-old.md" in str(exc) and sync.out_of_date(repo) == moved)
    check("the committed repository is current", sync.out_of_date(), [])
    check("the shipped hub's digests are computed over SKILL.md and references/ as committed",
          sync.digests(), {"hub_sha256": sync.digest({}, sync.HUB.read_text()),
                           "frontdoor_sha256": sync.digest(sync.generate(), sync.HUB.read_text())})
    check("hiding adds one line, the key, as the frontmatter's last, and changes nothing else",
          sync.hide("---\nname: a\ndescription: b\n---\n\nBody.\n"),
          "---\nname: a\ndescription: b\n" + sync.HIDDEN_KEY + "\n---\n\nBody.\n")


NAMES = {**{s: f"{s}-ab12cd34" for s in run_routing.SKILLS}, "tuesday": "tuesday-ab12cd34"}


def read_events(events: list[dict], arm: str = "frontdoor", explicit: str | None = None,
                end: str = "exit") -> str:
    """Feed events to a RunReader as the runner does; settle as the process would end."""
    reader = run_routing.RunReader(NAMES if arm == "frontdoor" else
                                   {s: NAMES[s] for s in run_routing.SKILLS}, arm, explicit)
    for event in events:
        outcome = reader.feed(event)
        if outcome:
            return outcome
    return reader.timed_out() if end == "timeout" else reader.exited()


def call(name: str, given: dict) -> dict:
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": given}]}}


def partial(name: str, chunks: list[str]) -> list[dict]:
    """A tool call as the partial stream delivers it: start, input in pieces, stop."""
    return ([{"type": "stream_event", "event": {"type": "content_block_start",
                                                "content_block": {"type": "tool_use", "name": name}}}]
            + [{"type": "stream_event", "event": {"type": "content_block_delta",
                                                  "delta": {"type": "input_json_delta", "partial_json": c}}}
               for c in chunks]
            + [{"type": "stream_event", "event": {"type": "content_block_stop"}}])


def init(*skills: str) -> dict:
    return {"type": "system", "subtype": "init", "skills": list(skills), "slash_commands": list(skills)}


DONE = {"type": "result", "subtype": "success"}
HUB_DIR = "/tmp/case-1/.claude/skills/tuesday-ab12cd34"


def runs(*outcomes: str, hub: bool = False) -> list[dict]:
    """Run records as `run_once` returns them, one per outcome, for `reach`."""
    return [{"outcome": o, "hub_fired": hub} for o in outcomes]


def test_frontdoor_labels() -> None:
    print("\nfront door: every run gets exactly one of the arm's labels")
    ours = init(*NAMES.values())
    fire = call("Skill", {"skill": "tuesday-ab12cd34"})
    check("the playbook read first after tuesday fires is the route",
          read_events([ours, fire, call("Read", {"file_path": f"{HUB_DIR}/references/citations.md"}),
                       call("Read", {"file_path": f"{HUB_DIR}/references/resume-tailor.md"}),
                       call("Read", {"file_path": f"{HUB_DIR}/references/job-underwriter.md"})]), "resume-tailor")
    check("a playbook path arriving in pieces is read once whole",
          read_events([ours, fire] + partial("Read", ['{"file_path": "' + HUB_DIR, "/references/mock-",
                                                      'interview.md"}'])), "mock-interview")
    # Round 2: Opus and Haiku read the right playbook with `cd <hub>/references && cat <m>.md`
    # and did its job; a reader that knew only the full path scored both tuesday-unrouted.
    check("a playbook read by `cat` after a `cd` into the hub's folder, in one call, is the route",
          read_events([ours, fire, call("Bash", {"command": f"cd {HUB_DIR}/references && cat mock-interview.md"}),
                       DONE]), "mock-interview")
    check("and so is one read by a path relative to the hub's folder",
          read_events([ours, fire, call("Bash", {"command": f"cd {HUB_DIR} && ls -R references && "
                                                             "cat references/resume-tailor.md"}), DONE]), "resume-tailor")
    check("a playbook's file name with no hub folder in the call is no route",
          read_events([ours, fire, call("Bash", {"command": "cat resume-tailor.md"}), DONE]), "tuesday-unrouted")
    check("one call naming two playbooks routes to the first it names",
          read_events([ours, fire, call("Bash", {"command": f"cd {HUB_DIR}/references && cat resume-tailor.md "
                                                             "job-underwriter.md"}), DONE]), "resume-tailor")
    check("a renamed clash file is not its module's playbook",
          read_events([ours, fire, call("Read", {"file_path": f"{HUB_DIR}/references/job-underwriter-rationale.md"}),
                       DONE]), "tuesday-unrouted")
    check("tuesday firing with no playbook read is tuesday-unrouted, a miss",
          read_events([ours, fire, DONE]), "tuesday-unrouted")
    check("a hidden module reached for by name is hidden-<module>",
          read_events([ours, call("Skill", {"skill": "mock-interview-ab12cd34"})]), "hidden-mock-interview")
    check("so is a hidden module's file read directly, even after tuesday fired",
          read_events([ours, fire, call("Read", {"file_path": "/tmp/case-1/.claude/skills/"
                                                              "job-underwriter-ab12cd34/references/evidence-model.md"})]),
          "hidden-job-underwriter")
    check("a hidden module called by its shipped name, with no run suffix, is hidden-<module>",
          read_events([ours, call("Skill", {"skill": "job-underwriter"}), DONE]), "hidden-job-underwriter")
    check("and so when it is called after the hub fired, before any playbook read",
          read_events([ours, fire, call("Skill", {"skill": "resume-tailor"}),
                       call("Read", {"file_path": f"{HUB_DIR}/references/resume-tailor.md"})]), "hidden-resume-tailor")
    check("a shipped-name call read from the partial stream is the same call",
          read_events([ours] + partial("Skill", ['{"skill": "job-', 'underwriter"}'])), "hidden-job-underwriter")
    check("the hub called by its shipped name is the hub firing",
          read_events([ours, call("Skill", {"skill": "tuesday"}), DONE]), "tuesday-unrouted")
    # Round 2: Haiku routed right, then read the playbook's files from the hidden
    # module's own folder, which a listing had shown it. A reader that stopped at
    # the routing decision scored that run job-underwriter.
    routed = [ours, fire, call("Read", {"file_path": f"{HUB_DIR}/references/job-underwriter.md"})]
    check("the run is read past the routing decision: a hidden module reached for later is hidden-<module>",
          read_events(routed + [call("Skill", {"skill": "resume-tailor-ab12cd34"}), DONE]), "hidden-resume-tailor")
    check("and so is the routed module's own hidden folder, entered by Bash to read the playbook's files",
          read_events(routed + [call("Bash", {"command": "cd /tmp/case-21/.claude/skills/job-underwriter-ab12cd34/"
                                                         "references && cat risk-and-decision.md"}), DONE]),
          "hidden-job-underwriter")
    reader = run_routing.RunReader(NAMES, "frontdoor")
    check("the routing decision is not settled until the turn ends: the reader returns nothing at the playbook",
          [reader.feed(e) for e in routed], [None, None, None])
    check("a listing that merely prints hidden paths reaches nothing: only a tool call's input is read",
          read_events(routed + [{"type": "user", "message": {"content": [{"type": "tool_result", "content":
                       "./.claude/skills/job-underwriter-ab12cd34/references/risk-and-decision.md"}]}}, DONE]),
          "job-underwriter")
    check("a run routed and then cut off by the timeout is set aside: the rest of the turn was never seen",
          read_events(routed, end="timeout"), "timeout")
    check("the skills arm reads Skill names as it did at e1e6a13: a shipped name it did not install is no fire",
          read_events([init(*(NAMES[s] for s in run_routing.SKILLS)), call("Skill", {"skill": "job-underwriter"}),
                       DONE], arm="skills"), "neither")
    check("no fire at all is neither", read_events([ours, DONE]), "neither")
    check("an errored run is error, even after tuesday fired",
          read_events([ours, fire, {"type": "result", "is_error": True}]), "error")
    check("a run cut off by the timeout is timeout, even after tuesday fired",
          read_events([ours, fire], end="timeout"), "timeout")
    check("a run that lists a synced Tuesday skill it did not install is void",
          read_events([init(*NAMES.values(), "anthropic-skills:mock-interview"), fire]), "void")
    check("so is one listing another run's copy",
          read_events([init(*NAMES.values(), "tuesday-ffff0000"), fire]), "void")
    check("an unrelated skill in the list is not a Tuesday skill",
          read_events([init(*NAMES.values(), "pdf", "skill-creator"), fire, DONE]), "tuesday-unrouted")
    check("the skills arm still labels the module whose name a call carries",
          read_events([init(*(NAMES[s] for s in run_routing.SKILLS)),
                       call("Skill", {"skill": "resume-tailor-ab12cd34"})], arm="skills"), "resume-tailor")
    check("and calls a void run void too",
          read_events([init("job-underwriter")], arm="skills"), "void")
    reader = run_routing.RunReader(NAMES, "frontdoor")
    reader.feed(init("tuesday-ab12cd34", "pdf"))
    check("the init skill list is recorded with the outcome, with the hub fire and what was reached",
          reader.record("neither"), {"outcome": "neither", "init_skills": ["tuesday-ab12cd34", "pdf"],
                                     "hub_fired": False, "reached": []})
    reader = run_routing.RunReader(NAMES, "frontdoor")
    for event in routed + [call("Read", {"file_path": f"{HUB_DIR}/references/resume-tailor.md"})]:
        reader.feed(event)
    check("every playbook a front-door run reads is recorded in order; the first is the route",
          (reader.feed(DONE), reader.record("job-underwriter")["reached"], reader.hub_fired),
          ("job-underwriter", ["job-underwriter", "resume-tailor"], True))
    reader = run_routing.RunReader({s: NAMES[s] for s in run_routing.SKILLS}, "skills")
    reader.feed(init(*(NAMES[s] for s in run_routing.SKILLS)))
    check("the skills arm records only the outcome and the init list, as before",
          sorted(reader.record("neither")), ["init_skills", "outcome"])

    ok, note = run_routing.verdict("job-underwriter", ["job-underwriter", "void", "job-underwriter"])
    check("a void run is set aside like a timeout, and reported", (ok, "1 void" in note), (True, True))
    ok, _ = run_routing.verdict("neither", ["neither", "tuesday-unrouted", "neither"])
    check("tuesday firing on a negative fails it, routed or not", ok, False)
    ok, _ = run_routing.verdict("job-underwriter", ["job-underwriter", "hidden-job-underwriter"])
    check("a hidden module firing fails the case even when it is the right module", ok, False)
    cases21 = [{"id": n, "expected": "neither", "prompt": "p"} for n in range(1, 22)]
    all_void = run_routing.reach(cases21, {n: runs(*["void"] * 4, "neither") for n in range(1, 22)})
    check("a mostly-void arm is not scored, though its hidden and wrong counts read zero",
          (all_void["hidden"], all_void["wrong_skill"], bool(run_routing.set_aside_problem(all_void))), (0, 0, True))
    check_true("and the reason names void with timeouts and errors",
               "timed out, errored or were void" in (run_routing.set_aside_problem(all_void) or ""))
    check("one set-aside run in ten is within the bar; two are over it",
          [bool(run_routing.set_aside_problem(run_routing.reach(
              [{"id": 1, "expected": "neither", "prompt": "p"}], {1: runs(*["void"] * k, *["neither"] * (10 - k))})))
           for k in (1, 2)],
          [False, True])
    check("an arm with no runs has nothing to set aside",
          run_routing.set_aside_problem(run_routing.reach([], {})), None)
    summary = run_routing.reach([{"id": 1, "expected": "job-underwriter", "prompt": "p"}],
                                {1: runs("job-underwriter", "tuesday-unrouted", "mock-interview", hub=True)
                                    + runs("hidden-mock-interview", "void", "neither")})
    check("reach counts playbook reads as reaches, and unrouted, hidden and void runs apart",
          {k: summary[k] for k in ("decided", "reached", "wrong_skill", "tuesday_unrouted", "reached_tuesday",
                                   "hidden", "set_aside")},
          {"decided": 5, "reached": 2, "wrong_skill": 1, "tuesday_unrouted": 1, "reached_tuesday": 3,
           "hidden": 1, "set_aside": 1})
    # Round 2's case 21 on Haiku: the hub fired and routed on every run, and one run
    # then reached the hidden module. Hub fires are read from `hub_fired`, not outcomes.
    case21 = [{"id": 21, "expected": "either", "siblings": ["job-underwriter", "resume-tailor"], "prompt": "p"}]
    summary = run_routing.reach(case21, {21: runs(*["job-underwriter"] * 4, "hidden-job-underwriter", hub=True)})
    check("tuesday fired counts every run whose record says the hub fired, a hidden reach after routing included",
          (summary["reached_tuesday"], summary["hidden"], summary["decided"]), (5, 1, 5))
    check("a hidden reach with no hub fire is not counted as one",
          run_routing.reach(case21, {21: runs("hidden-job-underwriter")})["reached_tuesday"], 0)
    explicit_cases = [{"id": 1, "expected": "mock-interview", "prompt": "/mock-interview x"}]
    explicit_runs = {1: runs(*["focused"] * 5, hub=True)}
    summary = run_routing.reach(explicit_cases, explicit_runs)
    check("an explicit case is not a routing case: reach counts none of its runs",
          (summary["decided"], summary["reached"], summary["set_aside"]), (0, 0, 0))
    lines = run_routing.summary_lines(summary, run_routing.explicit_summary(explicit_cases, explicit_runs),
                                      "frontdoor")
    check_true("so a fully focused E2 prints its explicit line and no reach rate of 0",
               len(lines) == 1 and lines[0].startswith("explicit: focused on 5/5 decided runs"))
    lines = run_routing.summary_lines(run_routing.reach(case21, {21: runs("job-underwriter", hub=True)}),
                                      run_routing.explicit_summary(case21, {}), "frontdoor")
    check("a routing suite prints the reach and tuesday lines, and no explicit line",
          [line.split(" on ")[0] for line in lines], ["reached a skill", "tuesday fired"])


def test_explicit_naming() -> None:
    print("\nfront door: E2 types the installed name, and reads only the named module as a pass")
    here = Path(__file__).resolve().parent
    names = {s: f"{s}-ab12cd34" for s in run_routing.SKILLS}
    check("a leading slash command is renamed to the installed copy's name, the rest kept",
          run_routing.explicit_prompt("/mock-interview should I apply?\nPosting below.", names),
          "/mock-interview-ab12cd34 should I apply?\nPosting below.")
    check("a prompt with no module command is sent as written",
          [run_routing.explicit_prompt(p, names) for p in ("should I apply?", "/mock-interviewer x", "use /resume-tailor")],
          ["should I apply?", "/mock-interviewer x", "use /resume-tailor"])
    cases = run_routing.load_cases(here / "suite-explicit.json")
    check("suite-explicit holds design §6's four cases, each expecting the module its command names",
          [(run_routing.explicit_command(c["prompt"]), c["expected"]) for c in cases],
          [("mock-interview", "mock-interview"), ("job-underwriter", "job-underwriter"),
           ("resume-tailor", "resume-tailor"), ("mock-interview", "mock-interview")])
    check_true("and every one is sent under the installed name",
               all(run_routing.explicit_prompt(c["prompt"], names).startswith(f"/{c['expected']}-ab12cd34 ")
                   for c in cases))
    ours = init(*NAMES.values())
    expansion = {"type": "user", "message": {"content": [{"type": "text", "text":
                 "<command-name>/mock-interview-ab12cd34</command-name>"}]}}
    own = call("Read", {"file_path": "/tmp/case-1/.claude/skills/mock-interview-ab12cd34/references/personas.md"})
    reader = run_routing.RunReader(NAMES, "frontdoor", "mock-interview")
    check("E2: the named module's own files opened does not end the run: what follows is the case",
          [reader.feed(ours), reader.feed(own)], [None, None])
    check("E2: the named module's own files opened, then a clean end, is focused",
          read_events([ours, own, DONE], explicit="mock-interview"), "focused")
    check("E2: a focused case passes; one run that reached another module fails it",
          (run_routing.verdict(run_routing.passes_on({"prompt": "/mock-interview x", "expected": "mock-interview"}),
                               ["focused"] * 5)[0],
           run_routing.verdict("focused", ["focused"] * 4 + ["job-underwriter"])[0]), (True, False))
    check("a routing case still passes on its expected label",
          run_routing.passes_on({"prompt": "should I apply?", "expected": "job-underwriter"}), "job-underwriter")
    # Round 2: every run in which the hub fired deferred to the named module and read
    # no other playbook. The hub firing is reported apart; what it does next is scored.
    hub_fire = call("Skill", {"skill": "tuesday-ab12cd34"})
    own_via_hub = call("Read", {"file_path": f"{HUB_DIR}/references/mock-interview.md"})
    check("E2: the hub firing, then deferring to the named module's own playbook, is focused",
          read_events([ours, expansion, hub_fire, own_via_hub,
                       call("Read", {"file_path": f"{HUB_DIR}/references/output-discipline.md"}), DONE],
                      explicit="mock-interview"), "focused")
    check("E2: so is the hub called by its shipped name",
          read_events([ours, expansion, call("Skill", {"skill": "tuesday"}), DONE], explicit="mock-interview"),
          "focused")
    check("E2: the hub firing, then another playbook read through it, is that playbook",
          read_events([ours, own, hub_fire, call("Read", {"file_path": f"{HUB_DIR}/references/job-underwriter.md"}),
                       DONE], explicit="mock-interview"), "job-underwriter")
    check("E2: another playbook named in a Bash call from inside the hub's folder is reached too",
          read_events([ours, expansion, hub_fire,
                       call("Bash", {"command": f"cd {HUB_DIR}/references && cat job-underwriter.md"}), DONE],
                      explicit="mock-interview"), "job-underwriter")
    check("E2: a renamed clash file is not its module's playbook, and the named module's own playbook is not another's",
          read_events([ours, expansion, call("Read", {"file_path": f"{HUB_DIR}/references/job-underwriter-rationale.md"}),
                       call("Bash", {"command": f"wc -c {HUB_DIR}/references/mock-interview.md"}), DONE],
                      explicit="mock-interview"), "focused")
    check("E2: the timeout is set aside even after its own files opened: the rest of the turn was never seen",
          (read_events([ours, own], explicit="mock-interview", end="timeout"),
           read_events([ours], explicit="mock-interview", end="timeout")), ("timeout", "timeout"))
    check("E2: the command's expansion seen, then a clean end, is focused",
          read_events([ours, expansion, DONE], explicit="mock-interview"), "focused")
    check("E2: a clean end with no sign the command loaded is unconfirmed, not a pass",
          read_events([ours, DONE], explicit="mock-interview"), "unconfirmed")
    check("E2: another module reached for by name fails it, whatever was loaded",
          read_events([ours, expansion, call("Skill", {"skill": "job-underwriter-ab12cd34"}), DONE],
                      explicit="mock-interview"), "hidden-job-underwriter")
    check("E2: another module called by its shipped name, no run suffix, fails it too",
          read_events([ours, call("Skill", {"skill": "job-underwriter"}), DONE], explicit="mock-interview"),
          "hidden-job-underwriter")
    check("E2: so does another module under a plugin prefix",
          read_events([ours, call("Skill", {"skill": "anthropic-skills:resume-tailor"}), DONE],
                      explicit="mock-interview"), "hidden-resume-tailor")
    check("E2: so does another module's folder named in a Bash call",
          read_events([ours, expansion, call("Bash", {"command": "ls .claude/skills/job-underwriter-ab12cd34/"}), DONE],
                      explicit="mock-interview"), "hidden-job-underwriter")
    check("E2: listing the skills folder without naming a module reaches nothing",
          read_events([ours, expansion, call("Bash", {"command": "ls .claude/skills/ .claude/skills/*/"}), DONE],
                      explicit="mock-interview"), "focused")
    check("E2: the first other module reached is the outcome",
          read_events([ours, expansion, call("Skill", {"skill": "resume-tailor"}), hub_fire,
                       call("Read", {"file_path": f"{HUB_DIR}/references/job-underwriter.md"}), DONE],
                      explicit="mock-interview"), "hidden-resume-tailor")
    check("E2: the named module called by its shipped name loads nothing, and neither passes nor fails",
          read_events([ours, call("Skill", {"skill": "mock-interview"}), DONE], explicit="mock-interview"),
          "unconfirmed")
    reader = run_routing.RunReader(NAMES, "frontdoor", "mock-interview")
    for event in [ours, expansion, hub_fire, call("Skill", {"skill": "job-underwriter-ab12cd34"}),
                  call("Read", {"file_path": f"{HUB_DIR}/references/resume-tailor.md"})]:
        reader.feed(event)
    outcome = reader.feed(DONE)
    check("E2: the record carries whether the named module loaded, the hub fire, and every module reached, "
          "in order",
          {k: v for k, v in reader.record(outcome).items() if k not in ("init_skills", "slash_commands")},
          {"outcome": "hidden-job-underwriter", "loaded": True, "hub_fired": True,
           "reached": ["hidden-job-underwriter", "resume-tailor"]})
    runs = {1: [{"outcome": "focused", "hub_fired": True, "reached": []},
                {"outcome": "focused", "hub_fired": False, "reached": []},
                {"outcome": "hidden-job-underwriter", "hub_fired": True,
                 "reached": ["hidden-job-underwriter", "job-underwriter"]},
                {"outcome": "timeout", "hub_fired": True, "reached": ["job-underwriter"]}],
            2: [{"outcome": "unconfirmed", "hub_fired": False, "reached": []}],
            3: [{"outcome": "job-underwriter", "hub_fired": False, "reached": ["job-underwriter"]}]}
    summary = run_routing.explicit_summary(
        [{"id": 1, "prompt": "/mock-interview x"}, {"id": 2, "prompt": "/resume-tailor y"},
         {"id": 3, "prompt": "should I apply?"}], runs)
    check("E2 summary: focused, unconfirmed and hub fires counted over decided runs, a set-aside run apart, "
          "a routing case not read",
          summary, {"decided": 4, "focused": 2, "unconfirmed": 1, "hub_fired": 2, "hub_fired_focused": 1,
                    "other_reached": {"hidden-job-underwriter": 1},
                    "reached_any": {"hidden-job-underwriter": 1, "job-underwriter": 1}, "set_aside": 1})
    # The CLI's stream-json never carries the expansion: a smoke run whose transcript
    # holds it streamed none. The transcript is read instead, by the run's own reply.
    def entry(uuid, parent, kind, content, mid=None):
        message = {"content": content, **({"id": mid} if mid else {})}
        return json.dumps({"uuid": uuid, "parentUuid": parent, "type": kind, "message": message})
    shared = [entry("a1", None, "user", "<command-message>mock-interview-ab12cd34</command-message>\n"
                                        "<command-name>/mock-interview-ab12cd34</command-name>"),
              entry("b1", None, "user", "a run of the same case whose command did not expand"),
              entry("a2", "a1", "user", [{"type": "text", "text": "Base directory for this skill: …"}]),
              entry("b2", "b1", "assistant", [{"type": "text", "text": "reply"}], "msg_B"),
              entry("a3", "a2", "assistant", [{"type": "text", "text": "reply"}], "msg_A")]
    check("E2 transcript: the expansion on this run's own chain confirms the load",
          run_routing.command_loaded(shared, "msg_A", "mock-interview-ab12cd34"), True)
    check("E2 transcript: another run's expansion in the same file does not",
          run_routing.command_loaded(shared, "msg_B", "mock-interview-ab12cd34"), False)
    check("E2 transcript: nor does an expansion of another installed name, or a reply not in the file",
          (run_routing.command_loaded(shared, "msg_A", "mock-interview-ffff0000"),
           run_routing.command_loaded(shared, "msg_C", "mock-interview-ab12cd34")), (False, False))
    check("E2 transcript: found under the cwd with every non-alphanumeric character turned to '-'",
          run_routing.transcript_path({"session_id": "s1", "cwd": "/tmp/tmpab_1/case-3"}).parts[-2:],
          ("-tmp-tmpab-1-case-3", "s1.jsonl"))
    check("E2 transcript: no session in the init event, no path", run_routing.transcript_path({}), None)
    # End to end: Sonnet's streams never carry the expansion, so a run whose hub fired and
    # deferred is `focused` only through `record` reading the transcript (round 2, case 1
    # runs 2 and 4). The reader finds the file from the init event and its own reply.
    with tempfile.TemporaryDirectory() as tmp:
        cwd = f"{tmp}/case-1"
        folder = Path(tmp) / "config" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", cwd)
        folder.mkdir(parents=True)
        (folder / "s1.jsonl").write_text("\n".join(shared) + "\n", encoding="utf-8")
        (folder / "s2.jsonl").write_text("\n".join(shared[1:]) + "\n", encoding="utf-8")

        def transcript_run(session: str, mid: str, *events: dict) -> run_routing.RunReader:
            reader = run_routing.RunReader(NAMES, "frontdoor", "mock-interview")
            for event in [{**ours, "session_id": session, "cwd": cwd},
                          {"type": "assistant", "message": {"id": mid, "content": [{"type": "text", "text": "x"}]}},
                          *events]:
                reader.feed(event)
            return reader

        def recorded(reader: run_routing.RunReader, outcome: str) -> tuple:
            rec = reader.record(outcome)
            return rec["outcome"], rec["loaded"]

        saved = os.environ.get("CLAUDE_CONFIG_DIR")
        os.environ["CLAUDE_CONFIG_DIR"] = str(Path(tmp) / "config")
        try:
            hub_then_own = transcript_run("s1", "msg_A", hub_fire, own_via_hub)
            check("E2 record: a stream with no expansion settles unconfirmed",
                  (hub_then_own.feed(DONE), hub_then_own.expanded, hub_then_own.loaded),
                  ("unconfirmed", False, False))
            check("E2 record: the transcript showing the command expanded turns unconfirmed into focused",
                  recorded(hub_then_own, "unconfirmed"), ("focused", True))
            check("E2 record: a run that reached another module keeps that outcome, now marked loaded",
                  recorded(transcript_run("s1", "msg_A", hub_fire), "hidden-job-underwriter"),
                  ("hidden-job-underwriter", True))
            check("E2 record: no expansion on this run's chain, or no transcript at all, stays unconfirmed",
                  (recorded(transcript_run("s1", "msg_B"), "unconfirmed"),
                   recorded(transcript_run("s2", "msg_A"), "unconfirmed"),
                   recorded(transcript_run("s9", "msg_A"), "unconfirmed")),
                  (("unconfirmed", False),) * 3)
            check("E2 record: a set-aside run is not rescued by the transcript",
                  recorded(transcript_run("s1", "msg_A"), "timeout"), ("timeout", False))
        finally:
            if saved is None:
                os.environ.pop("CLAUDE_CONFIG_DIR", None)
            else:
                os.environ["CLAUDE_CONFIG_DIR"] = saved
    check("E2: a tool result echoing the name is not the expansion",
          read_events([ours, {"type": "user", "message": {"content": [
              {"type": "tool_result", "content": "mock-interview-ab12cd34"}]}}, DONE], explicit="mock-interview"),
          "unconfirmed")


def files_of(folder: Path) -> dict[str, str]:
    """Every file under a folder, by its path inside it: what an install wrote, file for file."""
    return {p.relative_to(folder).as_posix(): p.read_text() for p in sorted(folder.rglob("*")) if p.is_file()}


def test_layouts_install() -> None:
    print("\nlayouts: each installs where it says, and nothing but the documents in the case folder outside it")
    check("--layout defaults to project, the layout every earlier measurement used",
          run_routing.parser().parse_args([]).layout, "project")
    check("and accepts the two outside the working folder",
          [run_routing.parser().parse_args(["--layout", lay]).layout for lay in ("personal", "plugin")],
          ["personal", "plugin"])
    case = {"id": 7, "attachments": {"jd.txt": "x"}}
    with tempfile.TemporaryDirectory() as tmp:
        made = {}
        for arm, layout in (("skills", "project"), ("frontdoor", "project"), ("skills", "personal"),
                            ("frontdoor", "personal"), ("frontdoor", "plugin")):
            base = Path(tmp) / f"{arm}-{layout}"
            base.mkdir()
            made[arm, layout] = (base, *run_routing.case_project(base, case, "ab12cd34", None, arm, layout))
        for (arm, layout), (base, root, _) in made.items():
            if layout != "project":
                check(f"{arm} arm, {layout} layout: the case folder holds the case's documents and nothing else",
                      sorted(p.relative_to(root).as_posix() for p in root.rglob("*")), ["jd.txt"])
        project = {arm: made[arm, "project"][1] / ".claude" / "skills" for arm in ("skills", "frontdoor")}
        base, root, names = made["skills", "personal"]
        check("personal layout: the skills sit in skills/ of a config folder of the run's own, beside the case folder",
              files_of(base / "config" / "case-7-0" / "skills"), files_of(project["skills"]))
        check("each run starts with its own config folder, by its index",
              [run_routing.config_dir(root, "personal", n) for n in (0, 2)],
              [base / "config" / "case-7-0", base / "config" / "case-7-2"])
        check("and the runner is told the names the project layout gives", names,
              {s: f"{s}-ab12cd34" for s in run_routing.SKILLS})
        base, root, names = made["frontdoor", "personal"]
        check("personal layout, front-door arm: the hub and the hidden modules, file for file as the project layout's",
              files_of(base / "config" / "case-7-0" / "skills"), files_of(project["frontdoor"]))
        runs = Path(tmp) / "runs"
        runs.mkdir()
        root3, _ = run_routing.case_project(runs, case, "ab12cd34", None, "frontdoor", "personal", 3)
        check("a case of three runs gets three config folders, the same skills in each, and nothing else beside it",
              ({p.name for p in (runs / "config").iterdir()},
               [files_of(run_routing.skills_root(root3, "personal", n)) == files_of(project["frontdoor"])
                for n in range(3)]), ({"case-7-0", "case-7-1", "case-7-2"}, [True] * 3))
        check("the other layouts keep one folder for every run of a case",
              [run_routing.skills_root(made["frontdoor", lay][1], lay, 2) == run_routing.skills_root(
                  made["frontdoor", lay][1], lay) for lay in ("project", "plugin")], [True, True])
        base, root, names = made["frontdoor", "plugin"]
        plugin = run_routing.home(root, "plugin")
        check("plugin layout: the plugin is a folder of the case's own, under a neutral name, beside the case folder",
              plugin, base / "plugins" / "case-7")
        check("it holds the manifest and skills/, nothing else",
              sorted(p.name for p in plugin.iterdir()), [".claude-plugin", "skills"])
        check("the manifest names the plugin as the hub is installed, tuesday-<run id>",
              json.loads((plugin / ".claude-plugin" / "plugin.json").read_text())["name"], "tuesday-ab12cd34")
        check("its skills/ holds the hub and the hidden modules, file for file as the project layout's",
              files_of(plugin / "skills"), files_of(project["frontdoor"]))
        check("folder and frontmatter names are the project layout's, so the runner is told the same names",
              names, NAMES)
        check("its runs keep the runner's config folder", run_routing.config_dir(root, "plugin"), None)
        for (arm, layout), (base, root, names) in made.items():
            if arm == "frontdoor":
                hub = run_routing.skills_root(root, layout) / names["tuesday"]
                stray = [p for p in base.rglob("*") if p.is_dir() and "tuesday-ab12cd34" in p.as_posix()
                         and p != hub and hub not in p.parents]
                check(f"{layout} layout: no folder path carries the hub's name but the hub's own folder", stray, [])
        check("outside the project layout the reader knows the layout's skills folder for what it is",
              [bool(run_routing.RunReader(NAMES, "frontdoor", None, lay, made["frontdoor", lay][1]).skills_folder.search(
                  run_routing.skills_root(made["frontdoor", lay][1], lay).as_posix())) for lay in ("personal", "plugin")],
              [True, True])
    with tempfile.TemporaryDirectory() as tmp:
        try:
            run_routing.case_project(Path(tmp), {"id": 1}, "ab12cd34", None, "skills", "plugin")
            check("--arm skills --layout plugin is refused", "installed", "refused")
        except SystemExit as exc:
            check_true("--arm skills --layout plugin is refused: today's three skills do not ship as a plugin",
                       "plugin" in str(exc))
        check("and nothing is installed", list(Path(tmp).iterdir()), [])
    root = Path("/tmp/tmpab/case-7")
    today = ["claude", "-p", "/mock-interview-ab12cd34 prep me", "--output-format", "stream-json", "--verbose",
             "--include-partial-messages", "--model", "m"]
    check("project layout: the command a run starts is today's",
          run_routing.child_command("/mock-interview prep me", root, NAMES, "m"), today)
    check("personal layout: today's command, and leave for Read in the run's own skills folder; the config folder "
          "travels in the environment",
          run_routing.child_command("/mock-interview prep me", root, NAMES, "m", "personal", 2),
          today + ["--allowedTools", "Read(//tmp/tmpab/config/case-7-2/skills/**)"])
    check("plugin layout: E2 types the namespaced command, the run loads the case's plugin folder, and Read may open "
          "its skills folder",
          run_routing.child_command("/mock-interview prep me", root, NAMES, None, "plugin", 2),
          ["claude", "-p", "/tuesday-ab12cd34:mock-interview-ab12cd34 prep me", "--output-format", "stream-json",
           "--verbose", "--include-partial-messages", "--plugin-dir", "/tmp/tmpab/plugins/case-7",
           "--allowedTools", "Read(//tmp/tmpab/plugins/case-7/skills/**)"])
    check("a routing prompt is sent as written in every layout",
          [run_routing.child_command("should I apply?", root, NAMES, None, lay)[2] for lay in run_routing.LAYOUTS],
          ["should I apply?"] * 3)
    source = (Path(__file__).resolve().parent / "run_routing.py").read_text()
    check_true("main installs every case in the layout asked for, a config folder for each run, and runs each "
               "job by its index (test_layout_runs follows one run through)",
               "case_project(Path(tmp), c, run_id, overrides, args.arm, args.layout, args.runs)" in source
               and "args.arm, args.layout, job[1])," in source)


PLUGIN_SKILLS = "/tmp/tmpab/plugins/case-1/skills"
PLUGIN_HUB = f"{PLUGIN_SKILLS}/tuesday-ab12cd34"
QUALIFIED = {m: f"tuesday-ab12cd34:{n}" for m, n in NAMES.items()}


def layout_reader(events: list[dict], layout: str = "plugin", explicit: str | None = None,
                  arm: str = "frontdoor", end: str = "exit") -> tuple[str, "run_routing.RunReader"]:
    """Feed events to a RunReader of case 1's run 0 in a layout; return the outcome as the runner
    settles it, and the reader."""
    names = NAMES if arm == "frontdoor" else {s: NAMES[s] for s in run_routing.SKILLS}
    reader = run_routing.RunReader(names, arm, explicit, layout, Path("/tmp/tmpab/case-1"))
    for event in events:
        outcome = reader.feed(event)
        if outcome:
            return outcome, reader
    return (reader.timed_out() if end == "timeout" else reader.exited()), reader


def test_layout_naming() -> None:
    print("\nlayouts: names, commands and detection hold in every layout")
    ours = init(*QUALIFIED.values())
    hub_q = call("Skill", {"skill": QUALIFIED["tuesday"]})

    def outcome_hub(events, **kw):
        outcome, reader = layout_reader(events, **kw)
        return outcome, reader.hub_fired
    check("a module's plugin-qualified id is that module, never a hub fire, though it holds the hub's name",
          outcome_hub([ours, call("Skill", {"skill": QUALIFIED["mock-interview"]}), DONE]),
          ("hidden-mock-interview", False))
    check("so too in the partial stream, where the plugin prefix arrives before the module's name",
          outcome_hub([ours] + partial("Skill", ['{"skill": "tuesday-ab12cd34', ':mock-interview-', 'ab12cd34"}'])
                      + [DONE]), ("hidden-mock-interview", False))
    check("the hub's own id, tuesday-<id>:tuesday-<id>, is the hub firing, and the playbook read next the route",
          outcome_hub([ours, hub_q, call("Read", {"file_path": f"{PLUGIN_HUB}/references/resume-tailor.md"}), DONE]),
          ("resume-tailor", True))
    check("and arriving in pieces it is the hub firing too",
          outcome_hub([ours] + partial("Skill", ['{"skill": "tuesday-ab12cd34', ':tuesday-ab12cd34', '"}']) + [DONE]),
          ("tuesday-unrouted", True))
    check("a module's shipped name under the plugin's prefix is that module, no hub fire",
          outcome_hub([ours, call("Skill", {"skill": "tuesday-ab12cd34:job-underwriter"}), DONE]),
          ("hidden-job-underwriter", False))
    check("the hub's shipped name under the prefix is the hub",
          outcome_hub([ours, call("Skill", {"skill": "tuesday-ab12cd34:tuesday"}), DONE]), ("tuesday-unrouted", True))
    check("a module's folder in the plugin, reached after routing, is that module",
          outcome_hub([ours, hub_q, call("Read", {"file_path": f"{PLUGIN_HUB}/references/job-underwriter.md"}),
                       call("Read", {"file_path": f"{PLUGIN_SKILLS}/job-underwriter-ab12cd34/references/"
                                                  "evidence-model.md"}), DONE]), ("hidden-job-underwriter", True))
    check("a playbook read by `cd` into the hub's folder in the plugin and `cat` is the route",
          outcome_hub([ours, hub_q, call("Bash", {"command": f"cd {PLUGIN_HUB}/references && cat mock-interview.md"}),
                       DONE]), ("mock-interview", True))
    check("a module's qualified call naming another playbook in its input reaches that module alone: the hub's "
          "name before a colon opens no playbook",
          layout_reader([ours, call("Skill", {"skill": QUALIFIED["mock-interview"],
                                              "args": "then read resume-tailor.md"}), DONE])[1].reached,
          ["hidden-mock-interview"])
    config_hub = "/tmp/tmpab/config/case-1-0/skills/tuesday-ab12cd34"
    personal = init(*NAMES.values())
    check("personal layout: the hub by its name, then a playbook in the config folder's hub, is the route",
          outcome_hub([personal, call("Skill", {"skill": "tuesday-ab12cd34"}),
                       call("Read", {"file_path": f"{config_hub}/references/job-underwriter.md"}), DONE],
                      layout="personal"), ("job-underwriter", True))
    check("personal layout: a module's folder beside the hub is that module",
          outcome_hub([personal, call("Bash", {"command": "cat /tmp/tmpab/config/case-1-0/skills/"
                                                          "resume-tailor-ab12cd34/SKILL.md"}), DONE],
                      layout="personal"), ("hidden-resume-tailor", False))
    check("a Skill call's name is read as the CLI reads it, trimmed and one leading slash dropped: "
          "a module's shipped name, its qualified id, the hub's bare and qualified ids",
          [outcome_hub([ours, call("Skill", {"skill": name}), DONE]) for name in
           ("/mock-interview", " /tuesday-ab12cd34:job-underwriter-ab12cd34", "/tuesday", "/tuesday-ab12cd34:tuesday")],
          [("hidden-mock-interview", False), ("hidden-job-underwriter", False), ("tuesday-unrouted", True),
           ("tuesday-unrouted", True)])
    check("E2: another module's shipped name with a slash is that module; the named module's is no other",
          [outcome_hub([ours, expansion, call("Skill", {"skill": name}), DONE], explicit="mock-interview")
           for expansion in [{"type": "user", "message": {"content": "<command-name>/tuesday-ab12cd34:"
                                                          "mock-interview-ab12cd34</command-name>"}}]
           for name in ("/job-underwriter", "/mock-interview")],
          [("hidden-job-underwriter", False), ("focused", False)])
    expansion_q = {"type": "user", "message": {"content": [{"type": "text", "text":
                   "<command-name>/tuesday-ab12cd34:mock-interview-ab12cd34</command-name>"}]}}
    check("E2, plugin layout: another module's qualified id is that module, and no hub fire",
          outcome_hub([ours, expansion_q, call("Skill", {"skill": QUALIFIED["job-underwriter"]}), DONE],
                      explicit="mock-interview"), ("hidden-job-underwriter", False))
    check("E2, plugin layout: the hub's id, then deferring to the named module's playbook, is focused, a hub fire",
          outcome_hub([ours, expansion_q, hub_q, call("Read", {"file_path": f"{PLUGIN_HUB}/references/mock-interview.md"}),
                       DONE], explicit="mock-interview"), ("focused", True))
    check("E2, plugin layout: the expansion of the namespaced command is the sign the named module loaded",
          outcome_hub([ours, expansion_q, DONE], explicit="mock-interview"), ("focused", False))

    names = {s: f"{s}-ab12cd34" for s in run_routing.SKILLS}
    check("the plugin's prefix is the hub's installed name, in the plugin layout only",
          [run_routing.plugin_prefix(NAMES, lay) for lay in run_routing.LAYOUTS], [None, None, "tuesday-ab12cd34"])
    check("E2 types the namespaced command under the plugin's prefix, the rest of the prompt kept",
          run_routing.explicit_prompt("/mock-interview should I apply?\nPosting below.", names, "tuesday-ab12cd34"),
          "/tuesday-ab12cd34:mock-interview-ab12cd34 should I apply?\nPosting below.")
    cases = run_routing.load_cases(Path(__file__).resolve().parent / "suite-explicit.json")
    check_true("every explicit case is sent under its namespaced command in the plugin layout",
               all(run_routing.explicit_prompt(c["prompt"], names, "tuesday-ab12cd34")
                   .startswith(f"/tuesday-ab12cd34:{c['expected']}-ab12cd34 ") for c in cases))
    check("a prompt with no module command is sent as written under a plugin too",
          run_routing.explicit_prompt("use /resume-tailor", names, "tuesday-ab12cd34"), "use /resume-tailor")
    check("E2's reader looks for the command as typed: namespaced in the plugin layout, bare in the others",
          [run_routing.RunReader(NAMES, "frontdoor", "mock-interview", lay).command for lay in run_routing.LAYOUTS],
          ["mock-interview-ab12cd34", "mock-interview-ab12cd34", "tuesday-ab12cd34:mock-interview-ab12cd34"])

    check("void rule: this run's own plugin-qualified ids are its own",
          run_routing.foreign_tuesday(list(QUALIFIED.values()), NAMES), [])
    check("void rule: another run's plugin, a shipped tuesday plugin's hub and modules, and a synced skill are not",
          run_routing.foreign_tuesday(["tuesday-ffff0000:mock-interview-ffff0000", "tuesday-ffff0000:tuesday-ffff0000",
                                       "tuesday:tuesday", "tuesday:job-underwriter",
                                       "anthropic-skills:resume-tailor"], NAMES),
          ["tuesday-ffff0000:mock-interview-ffff0000", "tuesday-ffff0000:tuesday-ffff0000",
           "tuesday:tuesday", "tuesday:job-underwriter", "anthropic-skills:resume-tailor"])
    check("void rule: a plugin named like the hub that lists no Tuesday skill cannot take the fire",
          run_routing.foreign_tuesday(["tuesday-ffff0000:pdf", "tuesday:pdf", "example:pdf", "session-start-hook"],
                                      NAMES), [])
    check("a plugin-layout run whose init list holds another run's plugin is void",
          layout_reader([init(*QUALIFIED.values(), "tuesday-ffff0000:mock-interview-ffff0000"), hub_q])[0], "void")


def test_layout_transcript() -> None:
    print("\nlayouts: E2 reads its transcript from the run's own config folder")
    check("personal layout: the transcript is under the run's config folder, whatever the runner's",
          run_routing.transcript_path({"session_id": "s1", "cwd": "/tmp/tmpab/case-3"},
                                      Path("/tmp/tmpab/config/case-3-1")),
          Path("/tmp/tmpab/config/case-3-1/projects/-tmp-tmpab-case-3/s1.jsonl"))

    def entry(uuid, parent, kind, content, mid=None):
        message = {"content": content, **({"id": mid} if mid else {})}
        return json.dumps({"uuid": uuid, "parentUuid": parent, "type": kind, "message": message})

    def transcript(command: str) -> str:
        return "\n".join([entry("a1", None, "user", f"<command-name>/{command}</command-name>"),
                          entry("a2", "a1", "assistant", [{"type": "text", "text": "reply"}], "msg_A")]) + "\n"

    with tempfile.TemporaryDirectory() as tmp:
        cwd = f"{tmp}/case-1"
        folder = re.sub(r"[^A-Za-z0-9]", "-", cwd)
        runner, case_config = Path(tmp) / "runner", Path(tmp) / "config" / "case-1-1"
        (runner / "projects" / folder).mkdir(parents=True)
        (case_config / "projects" / folder).mkdir(parents=True)
        (runner / "projects" / folder / "p1.jsonl").write_text(
            transcript("tuesday-ab12cd34:mock-interview-ab12cd34"), encoding="utf-8")
        (case_config / "projects" / folder / "s1.jsonl").write_text(transcript("mock-interview-ab12cd34"),
                                                                     encoding="utf-8")

        def recorded(session: str, layout: str, run: int = 1) -> tuple:
            reader = run_routing.RunReader(NAMES, "frontdoor", "mock-interview", layout, Path(cwd), run)
            for event in [{**init(*NAMES.values()), "session_id": session, "cwd": cwd},
                          {"type": "assistant", "message": {"id": "msg_A", "content": [{"type": "text", "text": "x"}]}}]:
                reader.feed(event)
            rec = reader.record(reader.feed(DONE))
            return rec["outcome"], rec["loaded"]

        saved = os.environ.get("CLAUDE_CONFIG_DIR")
        os.environ["CLAUDE_CONFIG_DIR"] = str(runner)
        try:
            check("personal layout: the expansion in the run's own config folder confirms the load",
                  recorded("s1", "personal"), ("focused", True))
            check("another run's config folder is not this run's: run 0 finds nothing there",
                  recorded("s1", "personal", 0), ("unconfirmed", False))
            check("the same run read from the runner's config folder, as before this round, finds nothing",
                  recorded("s1", "project"), ("unconfirmed", False))
            check("plugin layout: the runner's transcript, holding the namespaced command, confirms the load",
                  recorded("p1", "plugin"), ("focused", True))
            run_routing.keep_transcripts(case_config)
            check("a personal-layout run's transcripts are copied into the runner's config folder, beside the "
                  "other layouts' runs, and what was there is kept",
                  sorted(p.name for p in (runner / "projects" / folder).iterdir()), ["p1.jsonl", "s1.jsonl"])
            run_routing.keep_transcripts(None)
            check("a run with no config folder of its own copies nothing",
                  sorted(p.name for p in (runner / "projects" / folder).iterdir()), ["p1.jsonl", "s1.jsonl"])
            check("an expansion of the bare name where the namespaced command was typed confirms nothing",
                  run_routing.command_loaded(transcript("mock-interview-ab12cd34").splitlines(), "msg_A",
                                             "tuesday-ab12cd34:mock-interview-ab12cd34"), False)
        finally:
            if saved is None:
                os.environ.pop("CLAUDE_CONFIG_DIR", None)
            else:
                os.environ["CLAUDE_CONFIG_DIR"] = saved


def test_reported_measures() -> None:
    print("\nlayouts: measures are recorded per run and summarised per arm, and never scored")
    ours = init(*QUALIFIED.values())
    hub_q = call("Skill", {"skill": QUALIFIED["tuesday"]})

    def contact(*events: dict) -> bool:
        return layout_reader([ours, *events, DONE])[1].hub_path_contact
    check("the hub's SKILL.md read by its path before any Skill call to the hub is hub_path_contact",
          contact(call("Read", {"file_path": f"{PLUGIN_HUB}/SKILL.md"})), True)
    check("so is a playbook read by `cd` into the hub's folder and `cat`, or by a path through `..`, before the "
          "Skill call",
          [contact(call("Bash", {"command": f"cd {PLUGIN_HUB}/references && cat job-underwriter.md"}), hub_q),
           contact(call("Bash", {"command": f"cd {PLUGIN_HUB} && cat SKILL.md"})),
           contact(call("Read", {"file_path": f"{PLUGIN_SKILLS}/mock-interview-ab12cd34/../tuesday-ab12cd34/"
                                              "references/resume-tailor.md"}))], [True, True, True])
    check("a playbook read after the hub fired through the Skill tool is no contact",
          contact(hub_q, call("Read", {"file_path": f"{PLUGIN_HUB}/references/job-underwriter.md"})), False)
    check("nor after the hub's Skill call by its shipped name, with a leading slash or without",
          [contact(call("Skill", {"skill": name}), call("Read", {"file_path": f"{PLUGIN_HUB}/SKILL.md"}))
           for name in ("tuesday", "/tuesday-ab12cd34", "/tuesday-ab12cd34:tuesday-ab12cd34")], [False] * 3)
    check("a module's SKILL.md, or a file of the hub's that is no playbook, is no contact with the hub",
          (contact(call("Read", {"file_path": f"{PLUGIN_SKILLS}/mock-interview-ab12cd34/SKILL.md"})),
           contact(call("Read", {"file_path": f"{PLUGIN_HUB}/references/evidence-model.md"}))), (False, False))
    check("a call that names the hub's folder and opens a module's SKILL.md elsewhere is no contact with the hub "
          "(round 2's `cd <hub> ... cd ../<module>` shape, a listing then a cat, a Grep for the hub's name)",
          [contact(call("Bash", {"command": f"cd {PLUGIN_HUB} && ls -la references/ 2>/dev/null; "
                                            "cd ../job-underwriter-ab12cd34 && wc -l SKILL.md && cat SKILL.md | head -5"})),
           contact(call("Bash", {"command": f"ls {PLUGIN_HUB}/references | head; "
                                            f"cat {PLUGIN_SKILLS}/mock-interview-ab12cd34/SKILL.md"})),
           contact(call("Grep", {"pattern": "tuesday-ab12cd34", "path": "/tmp/tmpab/", "glob": "SKILL.md"}))],
          [False, False, False])
    check("a module's qualified Skill call is no Skill call to the hub",
          contact(call("Skill", {"skill": QUALIFIED["resume-tailor"]}),
                  call("Read", {"file_path": f"{PLUGIN_HUB}/SKILL.md"})), True)

    def named(command: dict, layout: str = "plugin") -> bool:
        return layout_reader([ours, call(*command.popitem()), DONE], layout=layout)[1].skills_root_named
    check("the plugin's skills/ named by its path, with or without a trailing slash, is skills_root_named",
          [named({"Bash": {"command": f"ls {PLUGIN_SKILLS}/"}}), named({"Bash": {"command": f"ls {PLUGIN_SKILLS}"}})],
          [True, True])
    check("so is a glob over it, or its path from the case folder",
          [named({"Bash": {"command": f"ls {PLUGIN_SKILLS}/*/references"}}),
           named({"Glob": {"pattern": "*/SKILL.md", "path": PLUGIN_SKILLS}}),
           named({"Bash": {"command": "ls ../plugins/case-1/skills"}})], [True, True, True])
    check("so is a path that resolves to it: through a skill's folder and `..`, `.` after it, a `cd` before it",
          [named({"Bash": {"command": f"ls {PLUGIN_HUB}/.."}}),
           named({"Bash": {"command": f"cd {PLUGIN_HUB}/.. && ls"}}),
           named({"Bash": {"command": f"cd {PLUGIN_HUB} && ls .."}}),
           named({"Glob": {"pattern": "*/SKILL.md", "path": f"{PLUGIN_HUB}/.."}}),
           named({"Bash": {"command": f"ls {PLUGIN_SKILLS}/."}}),
           named({"Bash": {"command": "cd /tmp/tmpab/plugins/case-1 && ls skills"}})], [True] * 6)
    check("and another case's skills folder, which holds the same hub and modules",
          named({"Bash": {"command": "ls ../plugins/case-2/skills"}}), True)
    check("a path into one skill's folder, or a folder whose name merely starts the same, does not name it",
          [named({"Read": {"file_path": f"{PLUGIN_HUB}/references/mock-interview.md"}}),
           named({"Bash": {"command": f"ls {PLUGIN_SKILLS}-old"}})], [False, False])
    check("nor does a path above it: `find ..` is not counted, so the measure is a lower bound",
          [named({"Bash": {"command": "find .. -name SKILL.md"}}), named({"Bash": {"command": "ls ../plugins"}})],
          [False, False])
    check("personal layout: a run's config folder's skills/ is named, its own or another's; the runner's own "
          "personal skills are not it",
          [named({"Bash": {"command": "ls /tmp/tmpab/config/case-1-0/skills/"}}, "personal"),
           named({"Bash": {"command": "ls ../config/case-2-3/skills"}}, "personal"),
           named({"Bash": {"command": "ls ~/.claude/skills"}}, "personal")], [True, True, False])

    denials = [{"tool_name": "Bash", "tool_use_id": "t1"}, {"tool_name": "Write", "tool_use_id": "t2"}]
    _, reader = layout_reader([ours, hub_q, {**DONE, "permission_denials": denials, "usage": {"output_tokens": 812}}])
    check("refused tool calls and output tokens are read from the result event, and the seconds given are kept",
          {k: v for k, v in reader.record("tuesday-unrouted", 41.5).items() if k in ("refused", "output_tokens", "seconds")},
          {"refused": ["Bash", "Write"], "output_tokens": 812, "seconds": 41.5})
    _, reader = layout_reader([ours, hub_q, DONE])
    check("a run with a result event and no denial refused none", reader.record("tuesday-unrouted")["refused"], [])
    _, reader = layout_reader([ours, hub_q], end="timeout")
    check("a run that never reached its result event has no count and no tokens, never zero",
          (reader.record("timeout")["refused"], reader.record("timeout")["output_tokens"]), (None, None))
    read = [ours, hub_q, call("Read", {"file_path": f"{PLUGIN_HUB}/references/mock-interview.md"})]
    outside = [layout_reader(read, layout=lay)[1] for lay in ("plugin", "personal")]
    check("outside the project layout a CLI that exits non-zero before any result event is error, whatever the "
          "stream read (a failed sign-in)",
          [run_routing.exit_outcome(r, code) for r in outside for code in (1, -9)], ["error"] * 4)
    check("a clean exit, or a status not yet read, is settled from the stream",
          [run_routing.exit_outcome(r, code) for r in outside for code in (0, None)], ["mock-interview"] * 4)
    _, project = layout_reader([init(*NAMES.values()), call("Skill", {"skill": "tuesday-ab12cd34"}),
                                call("Read", {"file_path": "/tmp/tmpab/case-1/.claude/skills/tuesday-ab12cd34/"
                                                           "references/mock-interview.md"})], layout="project")
    check("in the project layout a non-zero exit is settled from the stream, as before the layouts",
          run_routing.exit_outcome(project, 1), "mock-interview")
    outcome, reader = layout_reader([init(*(NAMES[s] for s in run_routing.SKILLS)),
                                     call("Skill", {"skill": "job-underwriter-ab12cd34"})],
                                    layout="personal", arm="skills")
    check("a skills-arm run stops at its first fire, so its refusals and tokens go unread, and it has no hub to contact",
          (outcome, reader.record(outcome, 12.0)),
          ("job-underwriter", {"outcome": "job-underwriter", "init_skills": [NAMES[s] for s in run_routing.SKILLS],
                               "skills_root_named": False, "refused": None, "output_tokens": None, "seconds": 12.0}))
    _, reader = layout_reader([ours, hub_q, DONE])
    check("a front-door run outside the project layout records all five",
          sorted(k for k in reader.record("tuesday-unrouted") if k in ("hub_path_contact", "skills_root_named", "refused",
                                                                      "output_tokens", "seconds")),
          ["hub_path_contact", "output_tokens", "refused", "seconds", "skills_root_named"])
    _, reader = layout_reader([init(*NAMES.values()), call("Skill", {"skill": "tuesday-ab12cd34"}), DONE],
                              layout="project")
    check("a project-layout run records none of them: its record is as before",
          sorted(reader.record("tuesday-unrouted", 3.0)), ["hub_fired", "init_skills", "outcome", "reached"])

    cases = [{"id": 1, "expected": "job-underwriter", "prompt": "p"}, {"id": 2, "expected": "mock-interview",
                                                                       "prompt": "/mock-interview x"}]
    runs_by_case = {1: [{"outcome": "job-underwriter", "hub_path_contact": True, "skills_root_named": True,
                         "refused": ["Bash", "Bash"], "seconds": 100.0, "output_tokens": 9000},
                        {"outcome": "hidden-job-underwriter", "hub_path_contact": False, "skills_root_named": True,
                         "refused": [], "seconds": 60.5, "output_tokens": 7000},
                        {"outcome": "timeout", "hub_path_contact": True, "skills_root_named": True, "refused": None,
                         "seconds": 900.0, "output_tokens": None}],
                    2: [{"outcome": "focused", "hub_path_contact": False, "skills_root_named": False, "refused": None,
                         "seconds": 20.0, "output_tokens": None}]}
    measures = run_routing.reported(cases, runs_by_case)
    check("the arm's summary counts decided runs, routing and explicit cases alike; a set-aside run is not read; "
          "wall time and tokens are summed, with a median a run, tokens over the runs that read them",
          measures, {"decided": 3, "hub_path_contact": 1, "skills_root_named": 2, "refused": 2, "runs_refused": 1,
                     "refused_unread": 1, "seconds": 180.5, "seconds_median": 60.5, "output_tokens": 16000,
                     "output_tokens_median": 8000.0, "tokens_read": 2})
    check("an arm with no decided run has no median", run_routing.reported(cases, {})["seconds_median"], None)
    lines = run_routing.summary_lines(run_routing.reach(cases, runs_by_case),
                                      run_routing.explicit_summary(cases, runs_by_case), "frontdoor", measures)
    check("the run prints them as reported, not scored",
          lines[-1], "reported, not scored: the hub's files reached by path before any Skill call to it on 1/3; "
                     "the skills folder named on 2/3; 2 tool calls refused, on 1 runs (1 ended before their result "
                     "event, uncounted); wall time 180.5s, median 60.5s a run; output tokens 16000, median 8000.0 a "
                     "run, on the 2 runs that reached their result event")
    check_true("the skills arm's line leaves out the hub, which it does not install",
               run_routing.summary_lines(run_routing.reach(cases, runs_by_case),
                                         run_routing.explicit_summary(cases, runs_by_case), "skills",
                                         measures)[-1].startswith("reported, not scored: the skills folder"))
    check("and a project-layout run prints no such line",
          [line for line in run_routing.summary_lines(run_routing.reach(cases, runs_by_case),
                                                      run_routing.explicit_summary(cases, runs_by_case), "frontdoor")
           if line.startswith("reported")], [])
    source = (Path(__file__).resolve().parent / "run_routing.py").read_text()
    check_true("every results file records its layout, and outside the project layout the reported measures",
               '"layout": args.layout' in source and '{"reported": measures} if measures is not None' in source
               and 'measures = reported(cases, runs_by_case) if args.layout != "project" else None' in source)


STUB_CLI = r'''#!{python}
"""A stand-in for the claude CLI: it writes what one run would, from the command and environment it got."""
import json, os, re, sys, time
prompt, config, cwd = sys.argv[2], os.environ.get("CLAUDE_CONFIG_DIR", ""), os.getcwd()
with open(os.environ["STUB_LOG"], "a") as log:
    log.write(json.dumps({"argv": sys.argv[1:], "config": config}) + "\n")


def emit(event):
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


emit({"type": "system", "subtype": "init", "skills": [], "session_id": "s1", "cwd": cwd})
if prompt == "crash":
    os.close(1)
    time.sleep(0.5)
    os._exit(1)
folder = os.path.join(config, "projects", re.sub(r"[^A-Za-z0-9]", "-", cwd))
os.makedirs(folder, exist_ok=True)
with open(os.path.join(folder, "s1.jsonl"), "w") as f:
    f.write(json.dumps({"uuid": "a1", "parentUuid": None, "type": "user",
                        "message": {"content": "<command-name>" + prompt.split()[0] + "</command-name>"}}) + "\n")
    f.write(json.dumps({"uuid": "a2", "parentUuid": "a1", "type": "assistant",
                        "message": {"id": "msg_A", "content": []}}) + "\n")
folders = [os.path.relpath(a[len("Read(/"):-len("/**)")], cwd) for a in sys.argv if a.startswith("Read(/")]
emit({"type": "assistant", "message": {"id": "msg_A", "content": [
    {"type": "tool_use", "name": "Bash", "input": {"command": "ls " + " ".join(folders)}}]}})
emit({"type": "result", "subtype": "success", "usage": {"output_tokens": 321},
      "permission_denials": [{"tool_name": "Bash"}]})
'''


def test_layout_runs() -> None:
    print("\nlayouts: one run followed through run_once, against a stand-in CLI")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        stub, runner, log = tmp / "bin", tmp / "runner", tmp / "log.jsonl"
        stub.mkdir()
        (stub / "claude").write_text(STUB_CLI.replace("{python}", sys.executable))
        (stub / "claude").chmod(0o755)
        saved = {k: os.environ.get(k) for k in ("PATH", "CLAUDE_CONFIG_DIR", "STUB_LOG")}
        os.environ.update(PATH=f"{stub}{os.pathsep}{os.environ.get('PATH', '')}", CLAUDE_CONFIG_DIR=str(runner),
                          STUB_LOG=str(log))
        try:
            def started() -> dict:
                return json.loads(log.read_text().splitlines()[-1])

            def run(base: str, case: dict, arm: str, layout: str, index: int = 0, runs: int = 1) -> dict:
                (tmp / base).mkdir()
                root, names = run_routing.case_project(tmp / base, case, "ab12cd34", None, arm, layout, runs)
                return run_routing.run_once(case["prompt"], root, names, 30, None, arm, layout, index)

            e2 = {"id": 1, "prompt": "/mock-interview prep me"}
            rec = run("personal", e2, "frontdoor", "personal", 1, 2)
            got = started()
            check("personal layout, run 1: the CLI starts with that run's config folder, and Read is let into "
                  "its skills folder",
                  (got["config"], got["argv"][-2:]),
                  (str(tmp / "personal/config/case-1-1"),
                   ["--allowedTools", f"Read(/{tmp}/personal/config/case-1-1/skills/**)"]))
            check("E2 confirms the load from that run's transcript; the skills folder named from the case folder "
                  "is read as such; refusals, tokens and a wall time are recorded",
                  {k: rec.get(k) for k in ("outcome", "loaded", "skills_root_named", "refused", "output_tokens")},
                  {"outcome": "focused", "loaded": True, "skills_root_named": True, "refused": ["Bash"],
                   "output_tokens": 321})
            check_true("the run's seconds are its wall time",
                       isinstance(rec.get("seconds"), float) and rec["seconds"] >= 0)
            slug = re.sub(r"[^A-Za-z0-9]", "-", str(tmp / "personal" / "case-1"))
            check_true("and its transcript is kept in the runner's config folder",
                       (runner / "projects" / slug / "s1.jsonl").is_file())
            rec = run("plugin", e2, "frontdoor", "plugin")
            got = started()
            check("plugin layout: the runner's config folder, the case's plugin, and Read let into its skills folder",
                  (got["config"], got["argv"][-4:]),
                  (str(runner), ["--plugin-dir", str(tmp / "plugin/plugins/case-1"),
                                 "--allowedTools", f"Read(/{tmp}/plugin/plugins/case-1/skills/**)"]))
            check("E2 confirms the namespaced command's load from the runner's transcript",
                  {k: rec.get(k) for k in ("outcome", "loaded", "skills_root_named")},
                  {"outcome": "focused", "loaded": True, "skills_root_named": True})
            crash = {"id": 2, "prompt": "crash"}
            check("a CLI that closes its stream and then exits non-zero is error outside the project layout, "
                  "read from its exit status once it has exited",
                  run("crash-personal", crash, "skills", "personal")["outcome"], "error")
            check("and in the project layout settled from the stream, as before the layouts",
                  run("crash-project", crash, "skills", "project"), {"outcome": "neither", "init_skills": []})
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


# --- Decline path 3: the CLI declining to answer is not a short answer ---

def test_cli_refusal() -> None:
    print("\nfixtures: a CLI refusal is not a response")
    check_true("a session-limit message is a refusal",
               run_fixtures.cli_failed("You've hit your session limit · resets 7am (UTC)", 0))
    check_true("so is a usage-limit message",
               run_fixtures.cli_failed("Usage limit reached", 0))
    check_true("a non-zero exit is a refusal whatever it printed",
               run_fixtures.cli_failed("x" * 5000, 1))
    check("a long normal answer is not a refusal",
          run_fixtures.cli_failed("x" * 5000, 0), False)
    check("a short genuine answer is not a refusal",
          run_fixtures.cli_failed("Yes — three of the four requirements are evidenced.", 0), False)
    check("a long answer that merely discusses rate limits is not a refusal",
          run_fixtures.cli_failed("The role involves rate limit tuning. " * 40, 0), False)


# --- The stream: what fired, what was called, whether it finished ---

def ev_init(skills, tools=("Skill", "WebSearch", "WebFetch"), servers=()):
    return {"type": "system", "subtype": "init", "claude_code_version": "2.1.301",
            "model": "claude-sonnet-5", "permissionMode": "default", "tools": list(tools),
            "mcp_servers": list(servers), "skills": list(skills), "session_id": "s"}


def ev_tool(tid, name, given, parent=None):
    return {"type": "assistant", "parent_tool_use_id": parent,
            "message": {"content": [{"type": "tool_use", "id": tid, "name": name, "input": given}]}}


def ev_result_of(tid, content, is_error=None, parent=None):
    item = {"type": "tool_result", "tool_use_id": tid, "content": content}
    if is_error is not None:
        item["is_error"] = is_error
    return {"type": "user", "parent_tool_use_id": parent, "message": {"content": [item]}}


def ev_text(text, parent=None):
    return {"type": "assistant", "parent_tool_use_id": parent,
            "message": {"content": [{"type": "text", "text": text}]}}


def ev_result(denials=()):
    return {"type": "result", "subtype": "success", "is_error": False, "num_turns": 4,
            "modelUsage": {"claude-sonnet-5": {"outputTokens": 10}},
            "permission_denials": list(denials)}


def stream(*events) -> list[str]:
    return [json.dumps(e) for e in events]


def test_parse_stream() -> None:
    print("\nfixtures: the stream says which skill fired and whether the run finished")
    name = "job-underwriter-ab12cd34"
    host = ["dataviz", name, "anthropic-skills:job-underwriter"]
    fired = run_fixtures.parse_stream(stream(
        ev_init(host), ev_tool("t1", "Skill", {"skill": name}),
        ev_result_of("t1", "Launching skill"), ev_text("Decision: apply."), ev_result()), name)
    check("the installed skill firing is a fire", fired["fire"], "fired")
    check("a host skill sharing its name is recorded as competing",
          fired["init"]["competing_skills"], ["anthropic-skills:job-underwriter"])
    check("the loaded skill count is recorded", fired["init"]["skills"], 3)

    wrong = run_fixtures.parse_stream(stream(
        ev_init(host), ev_tool("t1", "Skill", {"skill": "anthropic-skills:job-underwriter"}),
        ev_text("x"), ev_result()), name)
    check("a host skill of the same name firing is wrong_skill, not a fire", wrong["fire"],
          "wrong_skill")
    none = run_fixtures.parse_stream(stream(ev_init(host), ev_text("x"), ev_result()), name)
    check("no Skill call is not_fired", none["fire"], "not_fired")

    denied = {"tool_name": "WebSearch", "tool_use_id": "t2",
              "tool_input": {"query": "Harborlight careers"}}
    run = run_fixtures.parse_stream(stream(
        ev_init(host), ev_tool("t1", "Skill", {"skill": name}),
        ev_tool("t2", "WebSearch", {"query": "Harborlight careers"}),
        ev_result_of("t2", "Claude requested permissions to use WebSearch, but you haven't "
                           "granted it yet.", is_error=True),
        ev_tool("t3", "Read", {"file_path": "x"}, parent="t9"),
        ev_result_of("t3", "contents", parent="t9"),
        ev_text("a subagent's note", parent="t9"),
        ev_text("the answer"), ev_result([denied])), name)
    call = next(c for c in run["tool_calls"] if c["id"] == "t2")
    check("a tool_use is joined to its tool_result, error flag kept", call["is_error"], True)
    check("permission denials come from the result event",
          [d["tool_use_id"] for d in run["result"]["permission_denials"]], ["t2"])
    sub = next(c for c in run["tool_calls"] if c["id"] == "t3")
    check("a subagent's tool call is recorded with its parent", sub["parent_tool_use_id"], "t9")
    check("a subagent's text is not the response", run["text"], "the answer")
    check("a finished stream is not incomplete", run["result"]["incomplete"], False)
    cut = run_fixtures.parse_stream(stream(ev_init(host), ev_tool("t1", "Skill", {"skill": name}),
                                           ev_text("half an answ")), name)
    check("a stream with no result event is incomplete", cut["result"]["incomplete"], True)

    log = run_fixtures.build_research_log(run["tool_calls"], run["result"]["permission_denials"], [])
    check("the refused search is in the research log as refused",
          [(e["tool"], e["outcome"]) for e in log], [("WebSearch", "refused")])


# --- The research server, driven over its pipes ---

CORPUS = {
    "entity_tokens": ["Kestrel Analytics", "kestrel"],
    "pages": [
        {"url": "https://kestrel.test/careers", "title": "Careers at Kestrel",
         "text": "Kestrel came from an experimentation-platform team. Open roles.",
         "target": 1, "keywords": ["careers", "jobs", "kestrel"]},
        {"url": "https://kestrel.test/about", "title": "About Kestrel",
         "text": "Founded 2019 in Leeds.", "target": 1, "keywords": ["about", "company"]},
        {"url": "https://survey.test/analyst", "title": "Analyst pay survey",
         "text": "Median $147,300.", "target": 2, "keywords": ["salary", "compensation"]},
    ],
}


def drive_server(requests: list[dict], tmp: Path, served: dict | None = None) -> tuple[list[dict], Path, Path]:
    corpus = tmp / "corpus.json"
    corpus.write_text(json.dumps(served or CORPUS))
    log = tmp / "calls.jsonl"
    cwd = tmp / "cwd"
    cwd.mkdir()
    proc = subprocess.run([sys.executable, "-I", str(SERVER), str(corpus), str(log)],
                          input="\n".join(json.dumps(r) for r in requests) + "\n",
                          cwd=cwd, capture_output=True, text=True, timeout=30)
    replies = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    return replies, log, cwd


def test_server_url_identity() -> None:
    print("\nresearch server: one URL identity with the checks")
    import importlib.util
    spec = importlib.util.spec_from_file_location("research_server_copy", SERVER)
    server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server)
    pairs = [("https://www.Kestrel.test/careers/", "kestrel.test/careers"),
             ("http://kestrel.test/careers#roles", "https://kestrel.test/careers"),
             ("https://kestrel.test/Careers", "https://kestrel.test/careers"),
             ("https://kestrel.test/careers?id=2", "https://kestrel.test/careers?id=1"),
             ("https://kestrel.test/careers", "https://kestrel.test/careers/eng"),
             ("https://kestrel.test", "https://kestrel.test/"),
             ("https://kestrel.test/a//", "https://kestrel.test/a")]
    check("the room and the checks treat every URL pair alike",
          [server.same_url(a, b) for a, b in pairs], [output_checks.same_url(a, b) for a, b in pairs])
    check_true("and the pairs exercise both answers",
               {output_checks.same_url(a, b) for a, b in pairs} == {True, False})


def test_research_server() -> None:
    print("\nresearch server: deterministic, logged, and silent outside its log")
    def call(i, tool, **args):
        return {"jsonrpc": "2.0", "id": i, "method": "tools/call",
                "params": {"name": tool, "arguments": args}}
    requests = [
        {"jsonrpc": "2.0", "id": 0, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        call(2, "search", query="Kestrel Analytics careers"),
        call(3, "search", query="Kestrel Analytics careers"),
        call(4, "search", query="Kestrel Analytics"),
        call(5, "fetch", url="https://kestrel.test/careers/"),
        call(6, "fetch", url="https://kestrel.test/careers/"),
        call(7, "fetch", url="https://nowhere.test/"),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        replies, log_path, cwd = drive_server(requests, Path(tmp))
        by_id = {r["id"]: r for r in replies}
        check("it exits on EOF and answered every request with an id", sorted(by_id),
              [0, 1, 2, 3, 4, 5, 6, 7])
        check("initialize echoes the protocol version",
              by_id[0]["result"]["protocolVersion"], "2025-06-18")
        check("tools/list offers search and fetch",
              [t["name"] for t in by_id[1]["result"]["tools"]], ["search", "fetch"])
        text = lambda i: by_id[i]["result"]["content"][0]["text"]
        check("the same search twice returns the same text", text(2), text(3))
        check_true("and it found the careers page", "https://kestrel.test/careers" in text(2))
        check_true("a canary in a page's opening is visible in the snippet",
                   "experimentation-platform team" in text(2))
        check_true("the company name alone surfaces nothing", text(4).startswith("No results found"))
        check("a miss is not an error", by_id[4]["result"]["isError"], False)
        check("the same fetch twice returns the same page", text(5), text(6))
        check_true("an unknown URL is said plainly, not as a failure",
                   text(7) == "No page at https://nowhere.test/" and "fail" not in text(7).lower())
        log = [json.loads(line) for line in log_path.read_text().splitlines()]
        check("it logs initialize and tools/list", [l.get("rpc") for l in log[:2]],
              ["initialize", "tools/list"])
        first = next(l for l in log if l.get("id") == 2)
        check("a search's log line carries the URLs it returned",
              first["returned_urls"], ["https://kestrel.test/careers"])
        check("and the targets those pages are tagged with", first["targets"], [1])
        check("outcomes are logged as hit / no_results / fetch_miss",
              [l["outcome"] for l in log if "outcome" in l],
              ["hit", "hit", "no_results", "hit", "hit", "fetch_miss"])
        check("it writes nothing in its working directory", list(cwd.iterdir()), [])


# --- Rooms: flags, research file locations, artifacts ---

def test_rooms() -> None:
    print("\nfixtures: a room is the mode it claims, and its research files stay outside it")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        room = out / "rooms" / "job-underwriter-1-canned-ab12cd34"
        room.mkdir(parents=True)
        first = run_fixtures.research_paths(out, room, "first")
        nudged = run_fixtures.research_paths(out, room, "nudged")
        canned = run_fixtures.room_flags("canned", first)
        denied = run_fixtures.room_flags("denied")
        tail = canned[canned.index("--disallowedTools"):] if "--disallowedTools" in canned else []
        check("a canned room disallows the built-in web tools", tail[:3],
              ["--disallowedTools", "WebSearch", "WebFetch"])
        check_true("and loads only the fixture's server",
                   "--strict-mcp-config" in canned and str(first["mcp"]) in canned)
        check("a denied room drops user settings and MCP servers",
              denied, ["--setting-sources", "project", "--strict-mcp-config"])
        check("and never disallows the web tools: refused, not absent",
              "--disallowedTools" in denied, False)
        check_true("research files are absolute",
                   all(p.is_absolute() for p in first.values()))
        check("and outside the room", any(room.resolve() in p.parents for p in first.values()),
              False)
        check("each invocation gets its own call log", first["calls"] == nudged["calls"], False)
        try:
            run_fixtures.research_paths(room, room, "first")
            check("research files inside the room are refused", "accepted", "refused")
        except run_fixtures.RoomLeak:
            check("research files inside the room are refused", "refused", "refused")

        skill_dir = room / ".claude" / "skills" / "x"
        skill_dir.mkdir(parents=True)
        (room / "pack.md").write_text("the delivered pack")
        run_fixtures.write_research_files({"research": CORPUS}, first)
        found = dict(run_fixtures.collect_artifacts(room, skill_dir))
        check("collect_artifacts ignores <out>/research", sorted(found), ["pack.md"])


def test_stems() -> None:
    print("\nfixtures: one name per run, mode-aware only where modes exist")
    legacy = {"id": 3, "research": {"modes": ["denied"]}}
    plain = {"id": 3}
    both = {"id": 3, "research": {"modes": ["canned", "denied"]}}
    check("a denied-only fixture keeps the old stem",
          run_fixtures.stem_for("s", legacy, "denied", 2), "s-3.run2")
    check("so does one with no research block", run_fixtures.stem_for("s", plain, "denied", 0),
          "s-3.run0")
    check("a two-mode fixture carries the mode",
          run_fixtures.stem_for("s", both, "canned", 1), "s-3.canned.run1")


# --- Decline path 4: a grader that returned nothing graded nothing ---

def test_grade_parsing() -> None:
    print("\nfixtures: a grade that did not parse is not a fixture that failed")
    whole = json.dumps({"verdicts": [{"n": 1, "why": "a", "verdict": "PASS"},
                                     {"n": 2, "why": "b", "verdict": "FAIL"}]})
    got = run_fixtures.parse_verdicts(whole, 2)
    check("a why-first whole reply parses", [v["verdict"] for v in got["verdicts"]], ["PASS", "FAIL"])
    check("and is neither truncated nor incomplete", (got.get("truncated"), got["incomplete"]),
          (None, []))

    cut = ('{"verdicts": [{"n": 1, "why": "fine", "verdict": "PASS"}, '
           '{"n": 2, "why": "the response says the band is high and then it cu')
    got = run_fixtures.parse_verdicts(cut, 2)
    check("a reply cut mid-why keeps the verdicts it did contain", len(got["verdicts"]), 1)
    check_true("and is marked truncated", got.get("truncated"))
    check("and the cut expectation is incomplete, not failed", got["incomplete"], [2])

    shuffled = ('{"verdicts": [{"why": "w", "verdict": "FAIL", "n": 1}, '
                '{"verdict": "PASS", "n": 2, "why": "x"}, {"n": 3, "verdict": "PASS", "why": "trunc')
    got = run_fixtures.parse_verdicts(shuffled, 3)
    check("salvage accepts any key order", [(v["n"], v["verdict"]) for v in got["verdicts"]],
          [(1, "FAIL"), (2, "PASS")])

    tricky = ('{"verdicts": [{"n": 1, "why": "it writes {company} and the word verdict: PASS '
              'appears in its notes", "verdict": "FAIL"}, {"n": 2, "why": "cut')
    got = run_fixtures.parse_verdicts(tricky, 2)
    check("braces and the word verdict inside a why do not fool salvage",
          [(v["n"], v["verdict"]) for v in got["verdicts"]], [(1, "FAIL")])

    six = json.dumps({"verdicts": [{"n": i, "why": "ok", "verdict": "PASS"} for i in range(1, 7)]})
    got = run_fixtures.parse_verdicts(six, 16)
    check("a whole reply covering 6 of 16 is incomplete for the other ten",
          got["incomplete"], list(range(7, 17)))
    check("and they are missing, not failed",
          [v for v in got["verdicts"] if v["verdict"] == "FAIL"], [])

    dup = json.dumps({"verdicts": [{"n": 1, "why": "a", "verdict": "PASS"},
                                   {"n": 1, "why": "b", "verdict": "FAIL"},
                                   {"n": 2, "why": "c", "verdict": "PASS"}]})
    got = run_fixtures.parse_verdicts(dup, 2)
    check("a conflicting duplicate makes that number invalid",
          ([v["n"] for v in got["verdicts"]], got["incomplete"]), ([2], [1]))
    check_true("and it is reported", any(i["n"] == 1 for i in got["invalid"]))

    lower = json.dumps({"verdicts": [{"n": 1, "why": "a", "verdict": "pass"}]})
    got = run_fixtures.parse_verdicts(lower, 1)
    check("a lowercase pass is invalid, not a pass", (got["verdicts"], got["incomplete"]), ([], [1]))

    got = run_fixtures.parse_verdicts("the grader said nothing useful at all", 3)
    check("an unusable reply yields no verdicts", got["verdicts"], [])
    check_true("and carries an error", bool(got.get("error")))


def test_classification() -> None:
    print("\nfixtures: deterministic, intermittent and unresolved are told apart")
    def rec(run, grader, verdicts, expected=(1, 2)):
        return {"run": run, "grader": grader, "expected": list(expected),
                "verdicts": [{"n": n, "why": f"why {n}", "verdict": v} for n, v in verdicts]}
    results = [
        rec(0, 1, [(1, "FAIL"), (2, "PASS")]), rec(0, 2, [(1, "FAIL"), (2, "PASS")]),
        rec(1, 1, [(1, "FAIL"), (2, "PASS")]), rec(1, 2, [(1, "PASS"), (2, "PASS")]),
        # run 2: grader 1 skipped #1, grader 2 passed it
        rec(2, 1, [(2, "PASS")]), rec(2, 2, [(1, "PASS"), (2, "PASS")]),
    ]
    got = {i["key"]: i["kind"] for i in run_fixtures.classify(results, [], [0, 1, 2], 2)["items"]}
    check("one grader skipping #n where the other passed, #n failing every other run, "
          "is unresolved", got.get("#1"), "unresolved (1 partially graded)")
    check("an expectation every grader passed everywhere is not listed", "#2" in got, False)

    two = [r for r in results if r["run"] in (0, 1)]
    got = {i["key"]: i["kind"] for i in run_fixtures.classify(two, [], [0, 1], 2)["items"]}
    check("one grader failing is enough to fail the run", got.get("#1"), "deterministic")
    mixed = two + [rec(2, 1, [(1, "PASS"), (2, "PASS")]), rec(2, 2, [(1, "PASS"), (2, "PASS")])]
    got = {i["key"]: i["kind"] for i in run_fixtures.classify(mixed, [], [0, 1, 2], 2)["items"]}
    check("a fully graded passing run makes it intermittent", got.get("#1"), "intermittent")

    checks = [{"run": 0, "status": "fail", "checks": [
                  {"check": "accept", "target": "1", "verdict": "FAIL", "why": "w", "kind": "judgement"}]},
              {"run": 1, "status": "harness-invalid", "checks": [], "info": ["server failed"]}]
    got = run_fixtures.classify(two, checks, [0, 1], 2)
    check("a harness-invalid run leaves every denominator",
          (got["valid_runs"], sorted(got["invalid_runs"])), ([0], [1]))
    check("a check failure is classified like a grader's",
          {i["key"]: i["kind"] for i in got["items"]}.get("chk:accept:1"), "deterministic")


# --- Decline path 5: a run that never executed has nothing to grade ---

def test_missing_response() -> None:
    print("\nfixtures: a skipped execution is not a fixture that produced nothing")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        case = {"id": 1, "prompt": "irrelevant", "expectations": ["a", "b", "c"]}
        got = run_fixtures.grade("s", case, out, run=0, grader=1, timeout=1, model=None)
        check("grading a run with no response returns no verdicts", got["verdicts"], [])
        check_true("and carries an error rather than three failures", bool(got.get("error")))


def test_declined_grade_prints_no_score() -> None:
    """A grade that produced nothing must not print as a score of zero.

    The fifth instance of this bug class, and the first in the reporting rather
    than the data: a run-set killed by a weekly usage limit printed "SKIPPED
    grading ..." and then "graded ... 0/12" on the next line for every grader.
    The data was correct — nothing was recorded as failed — and a person reading
    the log saw twelve zeros.
    """
    print("\nfixtures: a declined or timed-out grade does not print a score")
    import contextlib
    import io
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        case = {"id": 1, "prompt": "irrelevant", "expectations": ["a", "b", "c"]}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_fixtures.grade("s", case, out, run=0, grader=1, timeout=1, model=None)
        printed = buf.getvalue()
        check("no score is printed", "0/3" in printed, False)
        check_true("and the reason is", "no verdicts" in printed)

        (out / "s-1.run0.md").write_text("a response")
        (out / "s-1.run0.meta.json").write_text(json.dumps({"skill_fired": True}))
        real, run_fixtures.claude = run_fixtures.claude, timing_out
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                got = run_fixtures.grade("s", case, out, run=0, grader=1, timeout=1, model=None)
        finally:
            run_fixtures.claude = real
        check("a grader that times out yields no verdicts", got["verdicts"], [])
        check("every expectation is incomplete, none failed", got["incomplete"], [1, 2, 3])
        check("and no score is printed", "0/3" in buf.getvalue(), False)


# --- The artifact collector, which produced its own false negative once ---

def test_artifact_collection() -> None:
    print("\nfixtures: delivered files are collected, the installed skill is not")
    with tempfile.TemporaryDirectory() as tmp:
        room = Path(tmp) / "room"
        skill_dir = room / ".claude" / "skills" / "x-123"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("the skill itself, not an artifact")
        (room / "pack.md").write_text("the delivered pack")
        (room / "notes.bin").write_bytes(b"\x00\x01binary")
        found = dict(run_fixtures.collect_artifacts(room, skill_dir))
        check("the delivered file is collected", found.get("pack.md"), "the delivered pack")
        check("the installed skill is excluded", "SKILL.md" in found, False)
        check("a non-text file is excluded", "notes.bin" in found, False)


def test_skill_installation() -> None:
    print("\nfixtures: an installed skill is what ships, renamed")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        name = run_fixtures.install_one(root, "resume-tailor", "abc123")
        dest = root / ".claude" / "skills" / name
        check("the directory carries the unique run id", name, "resume-tailor-abc123")
        check_true("the frontmatter name matches the directory",
                   f"name: {name}" in (dest / "SKILL.md").read_text())
        check("evals are excluded, as the packager excludes them",
              (dest / "evals").exists(), False)


# --- The room is checked, not assumed ---

def invocation(fire="fired", tools=("Skill", "mcp__web__search", "mcp__web__fetch"),
               servers=({"name": "web", "status": "connected"},), calls=(), denials=()):
    return {"fire": fire, "init": {"tools": list(tools), "mcp_servers": list(servers)},
            "tool_calls": list(calls), "result": {"permission_denials": list(denials)}}


INIT_LOG = [{"rpc": "initialize"}, {"rpc": "tools/list"}]


def test_classify_room() -> None:
    print("\nfixtures: a room that is not its mode is harness-invalid, not a skill result")
    status, _ = run_fixtures.classify_room("canned", invocation(), INIT_LOG)
    check("a connected canned room with zero calls is valid: not searching is the skill's choice",
          status, "ok")
    status, why = run_fixtures.classify_room(
        "canned", invocation(servers=({"name": "web", "status": "failed"},)), INIT_LOG)
    check("a server that failed to connect is invalid", status, "harness-invalid")
    status, _ = run_fixtures.classify_room(
        "canned", invocation(tools=("Skill", "WebSearch", "mcp__web__search", "mcp__web__fetch")),
        INIT_LOG)
    check("WebSearch present in a canned room is invalid", status, "harness-invalid")
    status, _ = run_fixtures.classify_room("canned", invocation(), [])
    check("a server log with no initialize line is invalid", status, "harness-invalid")
    crash = {"id": "t1", "name": "mcp__web__search", "is_error": True,
             "result_excerpt": "MCP error -32603: internal error"}
    status, _ = run_fixtures.classify_room("canned", invocation(calls=[crash]), INIT_LOG)
    check("an error from the server itself is invalid", status, "harness-invalid")
    blocked = dict(crash, result_excerpt="Claude requested permissions to use mcp__web__search")
    status, _ = run_fixtures.classify_room("canned", invocation(calls=[blocked]), INIT_LOG)
    check("a permission denial is not a server error", status, "ok")
    live = {"id": "t1", "name": "WebSearch", "is_error": False, "result_excerpt": "results"}
    status, _ = run_fixtures.classify_room(
        "denied", invocation(tools=("Skill", "WebSearch"), servers=(), calls=[live]), [])
    check("a search that succeeded in a denied room is a mode mismatch", status, "harness-invalid")
    status, _ = run_fixtures.classify_room(
        "denied", invocation(tools=("Skill", "WebSearch"), servers=()), [])
    check("a denied room with nothing returned is valid", status, "ok")
    status, why = run_fixtures.classify_room("denied", invocation(fire="not_fired", servers=()), [])
    check("a run that never fired the installed skill is invalid", status, "harness-invalid")


# --- execute(): timeouts and nudges, with a fake CLI ---

def timing_out(prompt, cwd, timeout, extra_args=(), output="stream", installed=""):
    raise run_fixtures.CLITimeout(f"timed out after {timeout}s",
                                  json.dumps(ev_init([installed])) + "\n")


def test_execute_timeout() -> None:
    print("\nfixtures: a run that times out is a skipped run with a reason, never nudged")
    calls = []
    def fake(*a, **k):
        calls.append(a)
        return timing_out(*a, **k)
    case = {"id": 1, "prompt": "p", "expectations": ["a"]}
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        real, run_fixtures.claude = run_fixtures.claude, fake
        try:
            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()):
                meta = run_fixtures.execute("resume-tailor", case, out, 0, 1, None)
        finally:
            run_fixtures.claude = real
        check("it does not crash and records the timeout", meta.get("outcome"), "timeout")
        check_true("with a reason", "timed out" in meta.get("error", ""))
        check("and it is not nudged", len(calls), 1)
        check("no response is saved to be graded", (out / "resume-tailor-1.run0.md").exists(), False)
        saved = json.loads((out / "resume-tailor-1.run0.meta.json").read_text())
        check("the saved record is harness-invalid", saved["harness"]["status"], "harness-invalid")


def test_execute_nudge() -> None:
    print("\nfixtures: a nudge is a new room; the first attempt's files and calls are not credited")
    case = {"id": 1, "prompt": "p", "expectations": ["a"],
            "research": {"modes": ["canned"], "pages": CORPUS["pages"],
                         "entity_tokens": CORPUS["entity_tokens"]}}
    seen = []
    def fake(prompt, cwd, timeout, extra_args=(), output="stream", installed=""):
        cfg = json.loads(Path(extra_args[extra_args.index("--mcp-config") + 1]).read_text())
        log = Path(cfg["mcpServers"]["web"]["args"][-1])
        nudged = prompt.startswith("Use the")
        seen.append((Path(cwd), log))
        log.write_text(json.dumps({"rpc": "initialize"}) + "\n" + json.dumps(
            {"id": 1, "tool": "search", "args": {"query": "first" if not nudged else "second"},
             "returned_urls": ["https://kestrel.test/careers"], "targets": [1], "outcome": "hit"}) + "\n")
        (Path(cwd) / ("second.md" if nudged else "first.md")).write_text("written")
        events = [ev_init([installed], ("Skill", "mcp__web__search", "mcp__web__fetch"),
                          ({"name": "web", "status": "connected"},)),
                  ev_tool("q1", "mcp__web__search", {"query": "first" if not nudged else "second"}),
                  ev_result_of("q1", "results", is_error=False)]
        if nudged:
            events.append(ev_tool("s1", "Skill", {"skill": installed}))
        events += [ev_text("second answer" if nudged else "first answer"), ev_result()]
        parsed = run_fixtures.parse_stream(stream(*events), installed)
        parsed["stdout"] = ""
        return parsed
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        real, run_fixtures.claude = run_fixtures.claude, fake
        try:
            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()):
                meta = run_fixtures.execute("resume-tailor", case, out, 0, 1, None)
        finally:
            run_fixtures.claude = real
        check("the nudge ran in a different room", seen[0][0] == seen[1][0], False)
        check("with its own call log", seen[0][1] == seen[1][1], False)
        check("both invocations are recorded, the second graded",
              (len(meta["invocations"]), meta["graded_invocation"]), (2, 1))
        body = (out / "resume-tailor-1.canned.run0.md").read_text()
        check("the graded response is the nudged one", body.startswith("second answer"), True)
        check("the first attempt's file is not collected", "first.md" in body, False)
        check("the graded research log holds only the nudged run's call",
              [e["query_or_url"] for e in meta["research_log"]], ["second"])
        check("the room is valid", meta["harness"]["status"], "ok")


def test_via_frontdoor() -> None:
    print("\nfixtures --via frontdoor: the front door installed as the plugin ships it, a fire only through the hub")
    source = (Path(__file__).resolve().parent / "run_fixtures.py").read_text()
    check_true("--via defaults to the module alone, accepts frontdoor, and reaches every run",
               run_fixtures.VIAS == ("skill", "frontdoor")
               and 'ap.add_argument("--via", choices=VIAS, default="skill",' in source
               and "args.model, j[2], args.via)" in source)
    with tempfile.TemporaryDirectory() as tmp:
        room = Path(tmp) / "rooms" / "case-3-denied-ab12cd34"
        room.mkdir(parents=True)
        plugin, names = run_fixtures.install_via_frontdoor(room, "ab12cd34")
        check("the room holds nothing: the plugin sits beside it, where the routing arm's plugin layout puts it",
              (list(room.iterdir()), plugin), ([], run_routing.home(room, "plugin")))
        reference = Path(tmp) / "reference"
        check("its files and names are the routing arm's plugin layout's",
              (files_of(plugin), names), (files_of(reference) if run_routing.install_plugin(reference, "ab12cd34")
                                          else None, NAMES))
        rule = run_routing.read_rule(room, "plugin")
        denied = run_fixtures.via_frontdoor_flags(run_fixtures.room_flags("denied"), room)
        check("a denied room gains the plugin and a rule to read its skills folder",
              denied, run_fixtures.room_flags("denied") + ["--allowedTools", rule, "--plugin-dir", str(plugin)])
        paths = {"mcp": Path("/x/mcp.json")}
        canned = run_fixtures.via_frontdoor_flags(run_fixtures.room_flags("canned", paths), room)
        check("a canned room keeps one --allowedTools list, the read rule joined to its search tools",
              (canned.count("--allowedTools"), canned[canned.index("--allowedTools") + 1:canned.index("--allowedTools") + 4]),
              (1, [rule, "mcp__web__search", "mcp__web__fetch"]))

    hub = f"{Path('/r/rooms/plugins/case-3-denied-ab12cd34/skills')}/tuesday-ab12cd34"
    own = [ev_init(list(QUALIFIED.values())), ev_tool("s", "Skill", {"skill": QUALIFIED["tuesday"]})]
    def fire(*events, skill="resume-tailor"):
        return run_fixtures.frontdoor_fire(stream(*events), NAMES, skill, Path("/r/rooms/case-3-denied-ab12cd34"))
    read = lambda module: ev_tool("r", "Read", {"file_path": f"{hub}/references/{module}.md"})
    check("the module's playbook read through the hub is a fire",
          fire(*own, read("resume-tailor"), ev_result()), "fired")
    check("another module's playbook is that module, not a fire",
          fire(*own, read("job-underwriter"), ev_result()), "job-underwriter")
    check("the hub with no playbook read is unrouted",
          fire(*own, ev_text("Which would you like?"), ev_result()), "tuesday-unrouted")
    check("the right playbook, then a hidden module's folder, is that hidden reach",
          fire(*own, read("resume-tailor"),
               ev_tool("h", "Read", {"file_path": f"{hub}/../resume-tailor-ab12cd34/SKILL.md"}), ev_result()),
          "hidden-resume-tailor")
    check("nothing fired is neither", fire(ev_init(list(QUALIFIED.values())), ev_text("hi"), ev_result()), "neither")
    check("a room listing a Tuesday skill it did not install is void",
          fire(ev_init(list(QUALIFIED.values()) + ["anthropic-skills:resume-tailor"]), read("resume-tailor"),
               ev_result()), "void")

    case = {"id": 3, "prompt": "Tailor this.", "expectations": ["a"]}
    seen = []
    def fake(prompt, cwd, timeout, extra_args=(), output="stream", installed=""):
        nudged = prompt.startswith("Use the")
        seen.append((Path(cwd), list(extra_args), prompt, installed))
        folder = run_routing.home(Path(cwd), "plugin") / "skills" / installed.split(":")[-1]
        module = "resume-tailor" if nudged else "job-underwriter"
        lines = stream(ev_init([installed, installed.split(":")[0] + ":resume-tailor-" + installed[-8:]]),
                       ev_tool("s", "Skill", {"skill": installed}),
                       ev_tool("r", "Read", {"file_path": f"{folder}/references/{module}.md"}),
                       ev_text("second answer" if nudged else "first answer"), ev_result())
        parsed = run_fixtures.parse_stream(lines, installed)
        parsed["stdout"] = "\n".join(lines) + "\n"
        return parsed
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        real, run_fixtures.claude = run_fixtures.claude, fake
        try:
            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()):
                meta = run_fixtures.execute("resume-tailor", case, out, 0, 1, None, None, "frontdoor")
        finally:
            run_fixtures.claude = real
        check("a run that routed to another module is not a fire, and says so, and is nudged",
              [i["fire"] for i in meta["invocations"]], ["job-underwriter", "fired"])
        second = meta["invocations"][-1]
        check("its nudge names the hub, by its plugin id, in a fresh room",
              [(prompt.startswith(f"Use the {name} skill"), name.count("tuesday-"), room) for room, _, prompt, name in seen[1:]],
              [(True, 2, seen[-1][0])] if len(seen) == 2 and seen[0][0] != seen[1][0] else "two rooms")
        check("each room is named for the case, never for the module whose route is measured",
              ["resume-tailor" in str(room) for room, *_ in seen], [False, False])
        check("each run loads the plugin from beside its room",
              [args[args.index("--plugin-dir") + 1] for _, args, *_ in seen],
              [str(run_routing.home(room, "plugin")) for room, *_ in seen])
        check("the nudged run read resume-tailor's playbook through the hub, graded as valid",
              (second["fire"], meta["harness"]["status"], meta["via"]), ("fired", "ok", "frontdoor"))
        check("the graded response is the nudged one", (out / "resume-tailor-3.run0.md").read_text(), "second answer")
        status, why = run_fixtures.classify_room("denied", dict(invocation(fire="job-underwriter", servers=()),
                                                                via="frontdoor"), [])
        check("a run that did not reach the module through the hub is harness-invalid, and the reason says so",
              (status, why), ("harness-invalid",
                              ["the module's playbook was not read through the front door (job-underwriter)"]))


# --- 6a. Research accounting, read from verbatim saved outputs ---

# Cut verbatim from saved runs, so the parser is tested against what skills actually
# wrote rather than against what a test author imagined they would. Paths are
# relative to the session scratchpad the sets were saved in; nothing reads them now.
# scratchpad/final2/ju/job-underwriter-1.run0.md:78-82
JU1_RUN0 = (
    '| Target | Status | What it would have moved |\n'
    '|---|---|---|\n'
    "| Company official site / careers page | unavailable (search tool not authorized this session) | RR3 resolution; role reality's org-context confidence |\n"
    "| Role-family sweep (title/scope/comp norms) | unavailable (same reason) | Role reality's market-calibration line; RR2's comp band |\n"
    '| Hiring manager public footprint | n/a | No hiring manager name was given |'
)

# scratchpad/final2/ju/job-underwriter-1.run2.md:78-84
JU1_RUN2 = (
    '| Target | Result |\n'
    '|---|---|\n'
    "| Company official site / careers page (verify entity + live posting) | unavailable — WebSearch permission wasn't granted this turn; would have resolved RR1 |\n"
    '| Role-family sweep (title/scope/comp norms) | unavailable — same reason; would have given a `[generic]` comp band for RR2/RR3 |\n'
    '| Hiring manager public footprint | n/a — no name given |\n'
    '\n'
    'Searches attempted: 3. Completed: 0.'
)

# scratchpad/final2/mi/mock-interview-5.run3.md:202-209
MI5_RUN3 = (
    '**Research tier:** L1 attempted; web search was unavailable in this session (tool-access error), so the pack degrades to L0 for anything requiring live lookup. Target accounting:\n'
    '\n'
    '| Target | Ran | What it moved, or could not have |\n'
    '|---|---|---|\n'
    '| 1. `{company} values` | unavailable | Would have supplied a values/principles cheat sheet (dropped from this pack entirely — no values-round content exists here) |\n'
    "| 2. `{company} interview process` | n/a | Not needed — the recruiter's email supplied the exact loop structure directly and more reliably than search would have |\n"
    '| 3. `{company} strategy` / recent news | unavailable | Would have supplied a Grounding brief and sharper, company-specific §5 theses; your own (unread-by-this-pack) strategy report is the real substitute — see the question below |\n'
    '| 4. `{interviewer} {company}` | n/a | Only first names were given — insufficient to search reliably even with a working tool; persona weights were built from stated titles instead |'
)

# diag/harness/fx/mock-interview-5.canned.8bad1381.md:249-258
MI5_8BAD = (
    'Research tier: L1. Four searches and two fetches used, out of six and two.\n'
    '\n'
    '| Target | Ran | What it moved, or could not have |\n'
    '|---|---|---|\n'
    '| 1. Kelverton values | yes | Values in 4a and the two VAL questions |\n'
    "| 2. Kelverton interview process | yes | Only forum reports; the recruiter's email is more specific and took priority |\n"
    '| 3. Kelverton strategy | yes | POV facts, A-bank and G2 |\n'
    "| 4. Interviewer name and company | unavailable | First names only, so a public footprint couldn't be attributed safely; the interviewer read is absent |\n"
    '| Extra: representative JD search | yes | Returned nothing usable, so requirements are inferred |\n'
    '| Extra: UK rail market context search | yes | Returned no external sources, so the pack makes no market claims |'
)

# Cut from the canned probe run while this harness was built (job-underwriter eval 1,
# canned room, claude-sonnet-5): a numbered table with the target in column two.
JU1_CANNED_PROBE = (
    'Research tier: L1 — searches 2 of 5, fetches 0 of 2\n'
    '\n'
    '| # | Target | Status | Reason |\n'
    '|---|---|---|---|\n'
    "| 1 | Company official site / careers page | yes | Search returned the company's own About page: ~420 employees, Series C (Northbay Ventures, March 2025), care-navigation app, Boston HQ — consistent with the posting. |\n"
    "| 2 | Role-family sweep (title, scope, compensation norms) | yes | Returned a pay-survey-style figure (~$147K median), but from a domain that doesn't resolve as a legitimate production site — flagged as low-reliability rather than asserted as a confirmed band. |\n"
    '| 3 | Hiring manager public footprint | n/a | No hiring manager was named in the inputs, so this target has no query to run. |'
)

# The same run's fit ledger: bold tokens, and a parenthetical that is not how its
# Requirement begins.
JU1_CANNED_LEDGER = (
    '**Fit ledger** (from the evidence map below):\n'
    '- **must_have** — direct: R1, R2, R3, R4, R5a, R7; adjacent: R5b (partner with product managers *and clinicians*)\n'
    '- **important** — unclear: R6 (mentor two junior analysts)\n'
    '- **preferred** — adjacent: R8 (healthcare data experience (HIPAA))'
)

def test_parse_accounting() -> None:
    print("\nchecks: the accounting table is absent, unparseable or checked — never guessed")
    got = output_checks.parse_accounting(JU1_RUN0)
    check("unnumbered rows cannot be keyed: unparseable (ju-1 run0)", got["outcome"], "unparseable")
    check("and each unnumbered row is a format violation",
          sum("target number" in p for _, p in got["format"]), 3)
    got = output_checks.parse_accounting(JU1_RUN2)
    check("a target table with no Status column is unparseable (ju-1 run2)", got["outcome"],
          "unparseable")
    check("the free-prose count beside it is no tally", output_checks.parse_tally(JU1_RUN2)["outcome"],
          "absent")
    got = output_checks.parse_accounting(MI5_RUN3)
    check("numbered rows under a legacy 'Ran' header are checked (mi-5 run3)",
          {n: r["label"] for n, r in got["rows"].items()},
          {1: "unavailable", 2: "n/a", 3: "unavailable", 4: "n/a"})
    check("a prose research-tier line is an unparseable tally",
          output_checks.parse_tally(MI5_RUN3)["outcome"], "unparseable")
    got = output_checks.parse_accounting(MI5_8BAD)
    check("the canned prototype's numbered rows are read (8bad1381)",
          {n: r["label"] for n, r in got["rows"].items()},
          {1: "yes", 2: "yes", 3: "yes", 4: "unavailable"})
    check("its two 'Extra:' rows, bare `yes` after the numbered ones, are off-target rows",
          ([e["target"][:6] for e in got["extra"]], sum("Extra:" in p for _, p in got["format"])),
          (["Extra:", "Extra:"], 0))
    got = output_checks.parse_accounting(JU1_CANNED_PROBE)
    check("a numbered table with the target in column two is read, not absent (canned probe)",
          {n: r["label"] for n, r in got["rows"].items()}, {1: "yes", 2: "yes", 3: "n/a"})
    check_true("and a number in its own column is the same table, not a format violation",
               not any("not the first column" in p for _, p in got["format"]))
    moved = JU1_CANNED_PROBE.replace("| # | Target | Status | Reason |", "| Status | Target | # | Reason |")
    check_true("a table with its target moved further along is still a format violation",
               any("not the first column" in p for _, p in output_checks.parse_accounting(moved)["format"])
               or output_checks.parse_accounting(moved)["outcome"] != "checked")
    check("its tally line is read", output_checks.parse_tally(JU1_CANNED_PROBE)["searches"], 2)
    got = output_checks.parse_accounting("A response with no table at all.")
    check("a response with no table is absent", got["outcome"], "absent")
    qualified = JU1_RUN0.replace("| Company official", "| 1. Company official") \
        .replace("| Role-family", "| 2. Role-family").replace("| Hiring", "| 3. Hiring")
    got = output_checks.parse_accounting(qualified)
    check("a qualifier in a status cell is a format violation, its label still read",
          (got["rows"][1]["label"], any("bare label" in p for _, p in got["format"])),
          ("unavailable", True))
    both = MI5_8BAD + "\n\n----- file the response produced: pack.md -----\n" + \
        MI5_8BAD.replace("| 3. Kelverton strategy | yes", "| 3. Kelverton strategy | skipped")
    got = output_checks.parse_accounting(both)
    check_true("chat and file tables that disagree are a format violation",
               any("disagree" in p for _, p in got["format"]))


RESEARCH = {
    "modes": ["canned", "denied"],
    "budget": {"tier": "L1", "searches": 5, "fetches": 2},
    "targets": [
        {"n": 1, "name": "company site", "terms": ["careers", "about"],
         "accept": {"canned": ["yes"], "denied": ["unavailable"]}},
        {"n": 2, "name": "role-family sweep", "terms": ["salary", "compensation"],
         "accept": ["yes", "unavailable", "skipped"]},
        {"n": 3, "name": "hiring manager", "terms": ["imogen"], "accept": ["n/a", "yes"]},
    ],
    "pages": CORPUS["pages"],
    "canaries": [{"target": 1, "page": "https://kestrel.test/careers",
                  "text": "came from an experimentation-platform team"}],
}


def accounting(labels: dict, tally: str = "Research tier: L1 — searches 2 of 5, fetches 0 of 2",
               extra: str = "") -> str:
    rows = "\n".join(f"| {n}. target | {label} | why |" for n, label in labels.items())
    return f"{extra}\n\n{tally}\n\n| Target | Status | What it moved |\n|---|---|---|\n{rows}\n"


def entry(query, outcome="returned", kind="search", targets=(), urls=()):
    return {"tool": "mcp__web__search" if kind == "search" else "mcp__web__fetch", "kind": kind,
            "query_or_url": query, "outcome": outcome, "urls_returned": list(urls),
            "targets": list(targets)}


def test_check_accounting() -> None:
    print("\nchecks: each label is judged against the calls aimed at its target")
    two = [entry("Kestrel careers", targets=[1], urls=["https://kestrel.test/careers"]),
           entry("analyst salary", targets=[2])]
    canary = "It came from an experimentation-platform team."
    good = output_checks.check_accounting(
        accounting({1: "yes", 2: "yes", 3: "n/a"}, extra=canary), RESEARCH, "canned", two)
    check("a consistent canned run passes every check",
          [c["check"] for c in good["checks"] if c["verdict"] == "FAIL"], [])

    got = output_checks.check_accounting(
        accounting({1: "yes", 2: "yes", 3: "yes"}, extra=canary), RESEARCH, "canned", two)
    check("`yes` with no call aimed at the target fails", verdict_of(got, "yes_has_call", 3), "FAIL")

    refused = [entry("Kestrel careers", "refused"), entry("analyst salary", "refused")]
    got = output_checks.check_accounting(
        accounting({1: "unavailable", 2: "skipped", 3: "n/a"}), RESEARCH, "denied", refused)
    check("`skipped` with a call aimed at it fails, a refused call included",
          verdict_of(got, "skip_has_no_call", 2), "FAIL")
    check("`unavailable` in a denied room needs nothing more",
          verdict_of(got, "unavailable_has_refusal", 1), None)

    got = output_checks.check_accounting(
        accounting({1: "unavailable", 2: "unavailable", 3: "n/a"}, "Research tier: L0 — no searches"),
        RESEARCH, "canned", [])
    check("`unavailable` in a canned room with nothing refused fails",
          verdict_of(got, "unavailable_has_refusal", 1), "FAIL")

    zero = dict(RESEARCH, zero_calls=True)
    got = output_checks.check_accounting(accounting({1: "yes", 2: "yes", 3: "n/a"}, extra=canary),
                                         zero, "canned", two)
    check("a call in a zero-calls fixture fails", verdict_of(got, "zero_calls"), "FAIL")

    off = output_checks.check_accounting(
        accounting({1: "yes", 2: "yes", 3: "n/a"}, "Research tier: L1 — searches 3 of 5, fetches 0 of 2",
                   canary), RESEARCH, "canned", two)
    check("a tally one search off the record fails", verdict_of(off, "tally_searches"), "FAIL")
    got = output_checks.check_accounting(
        accounting({1: "yes", 2: "yes", 3: "n/a"}, "", canary), RESEARCH, "canned", two)
    check("no tally line fails", verdict_of(got, "tally"), "FAIL")

    got = output_checks.check_accounting(accounting({1: "yes", 2: "yes", 3: "n/a"}),
                                         RESEARCH, "canned", two)
    check("a canned `yes` whose page's canary never reached the response fails",
          verdict_of(got, "canary", 1), "FAIL")
    got = output_checks.check_accounting(
        accounting({1: "unavailable", 2: "unavailable", 3: "n/a"}, extra=canary),
        RESEARCH, "denied", refused[:1])
    check("a canary in a denied room's response fails the negative control",
          verdict_of(got, "canary_absent", 1), "FAIL")

    got = output_checks.check_accounting(accounting({1: "yes", 2: "yes", 3: "n/a"}, extra=canary),
                                         RESEARCH, "canned", None)
    check("with no research log, the checks that need one are not run",
          (verdict_of(got, "yes_has_call", 1), "yes_has_call" in got["unchecked"]), (None, True))
    got = output_checks.check_accounting("no table", RESEARCH, "denied", [])
    check("an absent table fails every target's row check",
          [verdict_of(got, "row", n) for n in (1, 2, 3)], ["FAIL"] * 3)


# --- 6b. Fit ledger ---

LEDGER_OK = """## Decision snapshot

**Worth applying to. Status: `conditional_go`.**

**Fit ledger.**

- `hard_gate` — direct: R1
- `must_have` — direct: R2, R3 · adjacent: R4 (Regulatory exposure)
- `important` — direct: R6 · unclear: R5 (Mentoring or leading PMs)
- `preferred` — absent: R7 (Ledger / reconciliation systems)

R4 has a credible bridge, and R3 (`medium`) waits on an artifact.

**Opportunity ledger.** Authority is asserted and not evidenced (RR1).

- **Hard gates:** none failed (R1 `direct`).
- **Severe red flags:** none found.

## Evidence map

| # | Requirement | Priority | Fit | Confidence | Gap |
|---|---|---|---|---|---|
| R1 | UK work eligibility without sponsorship | hard_gate | direct | high | none |
| R2 | 5+ yrs PM, 2+ on payments/fintech | must_have | direct | high | none |
| R3 | Shipped APIs consumed by external developers | must_have | direct | medium | none |
| R4 | Regulatory exposure: PSD2 / open banking | must_have | adjacent | medium | transferability |
| R5 | Mentoring or leading PMs | important | unclear | low | discovery |
| R6 | Data fluency: SQL, experimentation | important | direct | high | presentation |
| R7 | Ledger / reconciliation systems experience | preferred | absent | none | capability |

## Risk register

| # | Signal | Class | Severity | Status |
|---|---|---|---|---|
| RR1 | Authority asserted, not evidenced | unknown | — | unresolved |
| RR2 | Compensation unstated | risk_signal | medium | unresolved |
"""


def ledger_fails(text: str) -> list[str]:
    return sorted(c["check"] for c in output_checks.check_fit_ledger(text)["checks"]
                  if c["verdict"] == "FAIL")


def test_fit_ledger() -> None:
    print("\nchecks: the fit ledger is an exact projection of the map")
    check("a correct ledger passes", ledger_fails(LEDGER_OK), [])
    check("a flipped fit fails", ledger_fails(LEDGER_OK.replace(
        "| must_have | adjacent | medium", "| must_have | unclear | medium")), ["ledger_fit"])
    check("a dropped last ID fails", ledger_fails(LEDGER_OK.replace(
        "- `preferred` — absent: R7 (Ledger / reconciliation systems)\n", "")), ["ledger_coverage"])
    check("a duplicated ID fails", "ledger_coverage" in ledger_fails(LEDGER_OK.replace(
        "direct: R2, R3 ·", "direct: R2, R3, R2 ·")), True)
    check("a wrong tier fails", ledger_fails(LEDGER_OK.replace(
        "| R6 | Data fluency: SQL, experimentation | important",
        "| R6 | Data fluency: SQL, experimentation | must_have")), ["ledger_tier"])
    check("a numeral in the ledger fails", "ledger_wording" in ledger_fails(LEDGER_OK.replace(
        "- `hard_gate` — direct: R1", "- `hard_gate` — direct: R1 (1 of 1)")), True)
    check("a quantifier in the ledger fails", "ledger_wording" in ledger_fails(LEDGER_OK.replace(
        "(Mentoring or leading PMs)", "(Mentoring or leading PMs, all of it)")), True)
    check("a band that disagrees with the map fails", ledger_fails(LEDGER_OK.replace(
        "R3 (`medium`) waits", "R3 (`high`) waits")), ["snapshot_band"])
    check("a band over no single row fails", ledger_fails(LEDGER_OK.replace(
        "R3 (`medium`) waits on an artifact", "confidence is `high` throughout")), ["snapshot_band"])
    severity = LEDGER_OK.replace("waits on an artifact.", "waits on an artifact; RR1 and RR2 are `low` severity.")
    check("a severity written as a bare band word is read as a band, and fails (rule 5)",
          ledger_fails(severity), ["snapshot_band"])
    headless = LEDGER_OK.replace("## Decision snapshot", "# Should you apply?")
    band = [c for c in output_checks.check_fit_ledger(headless)["checks"] if c["check"] == "snapshot_band"]
    check("with no snapshot heading the bands are read around the ledger (denied probe)",
          [c["verdict"] for c in band], ["PASS"])
    check("and a wrong band there still fails", ledger_fails(headless.replace(
        "R3 (`medium`) waits", "R3 (`high`) waits")), ["snapshot_band"])
    check("a universal in the sentence after the ledger fails, true or not, when it names no row (probe)",
          ledger_fails(LEDGER_OK.replace("R4 has a credible bridge, and R3 (`medium`) waits on an artifact.",
                                         "Every must-have is `direct`.")), ["ledger_sentence", "snapshot_count"])
    # GRADER (ci/ledger_rules.py, the comment above Claim): the check reads "every" as a
    # named-set word over a named set and passes it; whether the exception holds is the grader's.
    check("GRADER: \"every … but R4\" after the ledger names R4, and passes the check", ledger_fails(LEDGER_OK.replace(
        "R4 has a credible bridge, and R3 (`medium`) waits on an artifact.",
        "Every must-have but R4 is `direct`.")), [])
    # GRADER (round 9): the canned probe's "only" names its rows, so the check passes it;
    # that R7 is below `direct` too is agreement, the grader's (the comment above Claim).
    check("GRADER: a named \"the only rows below\" passes the check there, false or not (canned probe)",
          ledger_fails(LEDGER_OK.replace("R4 has a credible bridge, and R3 (`medium`) waits on an artifact.",
                                         "R4 and R5 are the only rows below `direct`.")), [])
    check("and exact, it passes", ledger_fails(LEDGER_OK.replace(
        "R4 has a credible bridge, and R3 (`medium`) waits on an artifact.",
        "R4, R5 and R7 are the only rows below `direct`.")), [])
    check("unnamed, \"the only rows below\" fails there", ledger_fails(LEDGER_OK.replace(
        "R4 has a credible bridge, and R3 (`medium`) waits on an artifact.",
        "The only rows below `direct` have credible bridges.")), ["ledger_sentence", "snapshot_count"])
    check("a next slot directly after the ledger is no sentence to judge", ledger_fails(LEDGER_OK.replace(
        "R4 has a credible bridge, and R3 (`medium`) waits on an artifact.",
        "**Opportunity ledger.** RR1 is asserted and not evidenced.")), [])
    check("a parenthetical in the Requirement's own words, reordered, passes (denied probe)",
          ledger_fails(LEDGER_OK.replace("(Mentoring or leading PMs)", "(PMs, mentoring or leading)")), [])
    check("a parenthetical using words the Requirement lacks fails, as format",
          [(c["verdict"], c["kind"]) for c in output_checks.check_fit_ledger(
              LEDGER_OK.replace("(Mentoring or leading PMs)", "(people management)"))["checks"]
           if c["check"] == "ledger_parenthetical"], [("FAIL", "format")])
    check("a parenthetical of stop words alone names nothing, though it opens the Requirement, and fails: the "
          "ledger's naming rule is ledger_rules.names_requirement, as in CI and on the hard-gates line",
          ledger_fails(LEDGER_OK.replace("unclear: R5 (Mentoring or leading PMs)", "unclear: R5 (Or)").replace(
              "| R5 | Mentoring or leading PMs |", "| R5 | Or leading PMs |")), ["ledger_parenthetical"])
    check("a canary is a whole token: 143 is not inside 1430",
          (output_checks.canary_in("143", "a team of 1430"), output_checks.canary_in("143", "143 staff")),
          (False, True))
    probe = JU1_CANNED_LEDGER + "\n\n## Evidence map\n\n" + \
        "| # | Requirement | Priority | Fit | Confidence |\n|---|---|---|---|---|\n" + "\n".join(
            f"| {r} | {req} | {p} | {f} | {c} |" for r, req, p, f, c in (
                ("R1", "5+ years product analytics", "must_have", "direct", "medium"),
                ("R2", "Expert SQL", "must_have", "direct", "medium"),
                ("R3", "Experiment design at scale", "must_have", "direct", "medium"),
                ("R4", "Looker or similar BI tool", "must_have", "direct", "medium"),
                ("R5a", "Partner with product managers on roadmap decisions", "must_have", "direct", "medium"),
                ("R5b", "Partner with clinicians specifically", "must_have", "adjacent", "low"),
                ("R6", "Mentor two junior analysts", "important", "unclear", "low"),
                ("R7", "Strong written communication with non-technical stakeholders", "must_have", "direct", "medium"),
                ("R8", "Healthcare data experience (HIPAA)", "preferred", "adjacent", "low")))
    got = output_checks.check_fit_ledger(probe)["checks"]
    check("a bold-token ledger is still judged (canned probe): its bad parenthetical fails",
          [c["verdict"] for c in got if c["check"] == "ledger_parenthetical"], ["FAIL"])
    check("and the bold is reported as format",
          [(c["verdict"], c["kind"]) for c in got if c["check"] == "ledger_markup"], [("FAIL", "format")])
    check("the old prose form is unparseable, not passed",
          ledger_fails(LEDGER_OK.replace("**Fit ledger.**\n",
                                         "**Fit ledger:** five of seven are `direct`.\n\nx\n")),
          ["ledger_present"])


# --- 6c. Quotes ---

PROMPT = ("MY BACKGROUND: 6 years of product analytics at a meal-kit company. Built the "
          "company's Looker instance from scratch — 40+ governed dashboards. I write the "
          "monthly metrics memo the exec team reads.")


def snapshot(cell: str) -> str:
    return ("| # | Requirement | Evidence, verbatim | Confidence | Bridge |\n|---|---|---|---|---|\n"
            f"| F1 | BI | {cell} | high | — |\n\n"
            "| # | Question | Type | Provenance | Answer guidance | Rationale |\n|---|---|---|---|---|---|\n"
            "| B1 | Tell me about dashboards | DATA | [grounded] \"Built the company's Looker "
            "instance from scratch\" | Lead with it | F1 |\n")



def test_review_fixes() -> None:
    print("\nchecks: what the second review of the fixes found")
    canary = "It came from an experimentation-platform team."
    errored = [entry("Kestrel careers", "error", targets=[1]), entry("analyst salary", targets=[2])]
    got = output_checks.check_accounting(accounting({1: "yes", 2: "yes", 3: "n/a"}, extra=canary),
                                         RESEARCH, "canned", errored)
    check("`yes` on a target whose only call errored fails: an error returns nothing",
          verdict_of(got, "yes_has_call", 1), "FAIL")
    got = output_checks.check_accounting(accounting({1: "unavailable", 2: "yes", 3: "n/a"}),
                                         RESEARCH, "canned", errored)
    check("`unavailable` on a target whose only call errored passes",
          verdict_of(got, "unavailable_has_refusal", 1), "PASS")
    # The grader reads the same rule in each skill's accounting clause; a clause that
    # said "refused" alone gave the grader no label for this run (NEW-RV-C, RV14).
    clauses = [json.loads((Path(__file__).resolve().parent.parent / "skills" / skill / "evals" / "evals.json")
                          .read_text(encoding="utf-8"))["clauses"]["accounting"]
               for skill in ("job-underwriter", "mock-interview")]
    check("and the graders' accounting clauses say an errored call counts as refused, as this check does",
          [("refused or errored" in c, "returned a result" in c) for c in clauses], [(True, True)] * 2)
    mixed = [entry("Kestrel careers", targets=[1]), entry("Kestrel about", "refused", targets=[1]),
             entry("analyst salary", targets=[2])]
    got = output_checks.check_accounting(accounting({1: "unavailable", 2: "yes", 3: "n/a"}),
                                         RESEARCH, "canned", mixed)
    check("`unavailable` with one call returned and one refused fails",
          verdict_of(got, "unavailable_has_refusal", 1), "FAIL")

    linked = dict(RESEARCH, user_links=["https://example.org/folio"])
    with_link = [entry("Kestrel careers", targets=[1], urls=["https://kestrel.test/careers"]),
                 entry("analyst salary", targets=[2]), entry("https://example.org/folio", kind="fetch")]
    tally = "Research tier: L1 — searches 2 of 5, fetches 0 of 2; user links read 1"
    got = output_checks.check_accounting(accounting({1: "yes", 2: "yes", 3: "n/a"}, tally, canary),
                                         linked, "canned", with_link)
    check("a fetch of a declared user link is named on the tally line, not charged",
          (verdict_of(got, "tally_fetches"), verdict_of(got, "tally_user_links")), ("PASS", "PASS"))
    got = output_checks.check_accounting(accounting({1: "yes", 2: "yes", 3: "n/a"}, tally, canary),
                                         RESEARCH, "canned", with_link)
    check("a fetch the fixture declares no user link for is research, whatever the tally calls it",
          (verdict_of(got, "tally_fetches"), verdict_of(got, "tally_user_links")), ("FAIL", "FAIL"))

    keyed = dict(RESEARCH, canaries=[{"target": 1, "page": "https://kestrel.test/about",
                                      "text": "came from an experimentation-platform team"}])
    unseen = [entry("Kestrel careers", targets=[1]), entry("analyst salary", targets=[2])]
    got = output_checks.check_accounting(accounting({1: "yes", 2: "yes", 3: "n/a"}), keyed, "canned", unseen)
    check("a canary whose page the room never returned is not asked for",
          verdict_of(got, "canary", 1), None)
    shown = [dict(entry("Kestrel careers", targets=[1]), urls_returned=["https://kestrel.test/about"]),
             entry("analyst salary", targets=[2])]
    got = output_checks.check_accounting(accounting({1: "yes", 2: "yes", 3: "n/a"}), keyed, "canned", shown)
    check("a canary whose page was returned must surface", verdict_of(got, "canary", 1), "FAIL")
    got = output_checks.check_accounting(
        accounting({1: "yes", 2: "yes", 3: "n/a"}, extra="it came from an experimentation‑platform team"),
        keyed, "canned", shown)
    check("a canary written with a non-breaking hyphen still counts", verdict_of(got, "canary", 1), "PASS")

    gated = LEDGER_OK.replace("- **Hard gates:** none failed (R1 `direct`).", "- **Hard gates:** none failed.")
    check("a hard-gates line that names no gate row fails", "gates_line" in ledger_fails(gated), True)
    check("one that names every gate row passes", "gates_line" in ledger_fails(LEDGER_OK), False)

    pasted = "THE JD: 'Own the complaints process end to end.' ME: I built the complaints spreadsheet."

    def snap(cell):
        return ("| # | Requirement (source) | Evidence, verbatim | Confidence | Bridge |\n|---|---|---|---|---|\n"
                f"| F1 | \"Own the complaints process end to end\" — JD | {cell} | high | — |\n\n"
                "| # | Question | Type | Provenance | Answer guidance | Rationale |\n|---|---|---|---|---|---|\n"
                "| A1 | q | EXP | [grounded] | g | F1 |\n")

    def quote_fails(cell, own=None, prompt=pasted):
        return sorted(c["check"] for c in output_checks.check_quotes(snap(cell), prompt, (), own)["checks"]
                      if c["verdict"] == "FAIL")
    check("`none given` is a lawful evidence cell", quote_fails("`none given`"), [])
    check("an unquoted summary in the evidence column fails", quote_fails("Built a complaints tracker"),
          ["evidence_form"])
    check("a quote with a summary appended fails",
          quote_fails('"I built the complaints spreadsheet" (your message), and ran the team'), ["evidence_form"])
    got = output_checks.check_quotes(snap('"Own the complaints process end to end" — your message'),
                                     pasted, (), None)
    check("with no candidate_text the evidence column is unchecked, never checked against the prompt",
          ([c["verdict"] for c in got["checks"] if c["check"] == "quotes" and c["target"] == "fit_snapshot"],
           "quotes" in got["unchecked"]), ([], True))
    check("the JD's words quoted as the candidate's fail against what the candidate gave",
          quote_fails('"Own the complaints process end to end" — your message',
                      ["I built the complaints spreadsheet."]), ["quotes"])
    check("a requirement in quotation marks that nothing supplied fails",
          quote_fails('"I built the complaints spreadsheet" — your message',
                      prompt="ME: I built the complaints spreadsheet."), ["quotes"])


def test_quotes() -> None:
    print("\nchecks: a quotation in a verbatim cell is a quotation of something")
    own = [PROMPT.split(": ", 1)[1]]

    def fails(cell: str) -> list[str]:
        return [c["why"] for c in output_checks.check_quotes(snapshot(cell), PROMPT, (), own)["checks"]
                if c["verdict"] == "FAIL"]
    check("a verbatim quote passes, curly quotes and dashes unified",
          fails("“Built the company’s Looker instance from scratch – 40+ governed dashboards” "
                "— your message"), [])
    check("a paraphrase in quotation marks fails",
          len(fails('"Built and governed the Looker estate" — your message; '
                    '"Built the company\'s Looker instance from scratch" — your message')), 1)
    check("each ellipsis fragment is checked, and a true pair passes",
          fails('"6 years of product analytics ... the monthly metrics memo" — your message; '
                '"Built the company\'s Looker instance from scratch" — your message'), [])
    check("one invented fragment fails the span",
          len(fails('"6 years of product analytics … led the analytics guild" — your message; '
                    '"Built the company\'s Looker instance from scratch" — your message')), 1)
    check("a two-word quote in the evidence column is checked too, and a true one passes",
          fails('"Looker instance" — your message; '
                '"Built the company\'s Looker instance from scratch" — your message'), [])


def test_evidence_cells() -> None:
    print("\nchecks: an evidence cell is `none given` or quotes with their origins, and nothing else")
    pasted = "THE JD: 'Own the complaints process end to end.' ME: I built the complaints spreadsheet."
    own = ["I built the complaints spreadsheet."]

    def snap(cell, provenance="[grounded]"):
        return ("| # | Requirement (source) | Evidence, verbatim | Confidence | Bridge |\n|---|---|---|---|---|\n"
                f"| F1 | \"Own the complaints process end to end\" — JD | {cell} | high | — |\n\n"
                "| # | Question | Type | Provenance | Answer guidance | Rationale |\n|---|---|---|---|---|---|\n"
                f"| A1 | q | EXP | {provenance} | g | F1 |\n")

    def fails(cell, candidate=own, provenance="[grounded]", prompt=pasted):
        return sorted(c["check"] for c in output_checks.check_quotes(
            snap(cell, provenance), prompt, (), candidate)["checks"] if c["verdict"] == "FAIL")
    quote = '"I built the complaints spreadsheet"'
    check("a summary after the dash is not an origin",
          fails(quote + " — your message, i.e. owned the complaints process end to end"), ["evidence_form"])
    check("a summary in parentheses is not an origin",
          fails(quote + " (owned complaints end to end for the org)"), ["evidence_form"])
    check("free text after a dash fails", fails(quote + " - and then ran the whole team"), ["evidence_form"])
    check("a quote with no origin fails", fails(quote), ["evidence_form"])
    check("an origin outside the template's set fails", fails(quote + " — LinkedIn"), ["evidence_form"])
    check("an origin in parentheses rather than after a dash fails (the template: 'followed by a dash')",
          fails(quote + " (your message)"), ["evidence_form"])
    check("one origin for two quotes fails: each quote is followed by its own",
          fails(quote + ' and "complaints spreadsheet" — your message'), ["evidence_form"])
    check("words between quotes fail", fails(quote + " and led the team — your message"), ["evidence_form"])
    check("`none given` with words after it fails", fails("none given, but led a team"), ["evidence_form"])
    check("two quotes, each with its origin, pass",
          fails(quote + ' — your message; "complaints spreadsheet" — your CV'), [])
    check("two quotes separated by a full stop, each with its origin, pass (HN5)",
          fails(quote + ' — your message. "complaints spreadsheet" — your CV.'), [])
    check("but words after the full stop still fail", fails(quote + " — your message. and led the team"),
          ["evidence_form"])
    check("and a full stop then a quote with no origin fails",
          fails(quote + ' — your message. "complaints spreadsheet"'), ["evidence_form"])
    check("a dossier row is an origin", fails(quote + " — dossier R3"), [])
    check("`None given.` with its period passes", fails("None given."), [])
    check("`none given` in backticks passes", fails("`none given`"), [])
    check("a fabricated two-word quote fails", fails('"owned quota" — your message'), ["quotes"])
    check("a fabricated one-word quote fails", fails('"quota" — your message'), ["quotes"])
    check("a genuine two-word quote passes", fails('"complaints spreadsheet" — your message'), [])
    check("a quote is matched on word boundaries: \"built the complaint\" is not in \"…complaints\"",
          fails('"built the complaint" — your message'), ["quotes"])

    mi3 = fixture("mock-interview", 3)
    worksheet = ("| # | Requirement (source) | Evidence, verbatim | Confidence | Bridge |\n|---|---|---|---|---|\n"
                 "| F1 | Cross-functional operations planning | {cell} | none | Answer slot |\n\n"
                 "| # | Question | Type | Provenance | Answer guidance | Rationale |\n|---|---|---|---|---|---|\n"
                 "| A1 | q | EXP | [generic] | g | F1 |\n")

    def mi3_quotes(cell, candidate):
        return output_checks.check_quotes(worksheet.format(cell=cell), mi3["prompt"], (), candidate)

    def mi3_fails(cell):
        return sorted(c["check"] for c in mi3_quotes(cell, mi3["candidate_text"])["checks"] if c["verdict"] == "FAIL")
    check("mi 3 (candidate_text []): a prompt sentence quoted as the candidate's fails",
          mi3_fails('"final-round interview at Stripe" — your message'), ["quotes"])
    check("mi 3: the worksheet's `none given` passes, with no JD and no CV", mi3_fails("none given"), [])
    got = mi3_quotes('"final-round interview at Stripe" — your message', None)
    check("a fixture with no candidate_text is reported unchecked, not passed",
          ("quotes" in got["unchecked"],
           [c["verdict"] for c in got["checks"] if c["check"] == "quotes" and c["target"] == "fit_snapshot"]),
          (True, []))
    from fixture_clauses import load_cases
    undeclared = [f"{path.parent.parent.name} {case['id']}"
                  for path in sorted((Path(__file__).resolve().parent.parent / "skills").glob("*/evals/evals.json"))
                  for case in load_cases(path)
                  if "quotes" in case.get("checks", []) and not isinstance(case.get("candidate_text"), list)]
    check("every fixture with the quotes check declares candidate_text as a list (D5)", undeclared, [])
    check("and a run of it is uncheckable, not ok", output_checks.run_checks(
        {"checks": ["quotes"], "prompt": mi3["prompt"]}, "denied",
        worksheet.format(cell='"final-round interview at Stripe" — your message'), None)["status"], "uncheckable")


def test_provenance_pool() -> None:
    print("\nchecks: Provenance quotes the candidate, as the fit snapshot does (mi 4)")
    mi4 = fixture("mock-interview", 4)
    evidence = ('"Wrote the internal integration playbook her team uses" — dossier; '
                '"Ran quarterly roadmap-input sessions feeding client evidence to product" — dossier')

    def pack(provenance):
        return ("| # | Requirement (source) | Evidence, verbatim | Confidence | Bridge |\n|---|---|---|---|---|\n"
                f"| F1 | \"Shipped API or platform products\" — dossier R2 | {evidence} | medium | — |\n\n"
                "| # | Question | Type | Provenance | Answer guidance | Rationale |\n|---|---|---|---|---|---|\n"
                f"| A1 | q | EXP | [grounded] \"{provenance}\" | g | F1 |\n")

    def banks(provenance):
        got = output_checks.run_checks(mi4, "denied", pack(provenance), None)
        return [c["verdict"] for c in got["checks"] if c["check"] == "quotes" and c["target"] == "banks"]
    check("the dossier's header prose in Provenance fails",
          banks("Strong adjacent fit from seven years of integration leadership"), ["FAIL"])
    check("a prohibited_claims string in Provenance fails",
          banks("Having held a product manager title or role"), ["FAIL"])
    check("a JD responsibility in Provenance fails",
          banks("Own the roadmap for the partner-facing API platform"), ["FAIL"])
    check("a verified claim cut before its confidence note, as the evidence column quotes it, passes",
          banks("Wrote the internal integration playbook her team uses"), ["PASS"])
    banks_only = pack("Wrote the internal integration playbook her team uses").split("\n\n", 1)[1]
    got = output_checks.check_quotes(banks_only, mi4["prompt"], (), mi4["candidate_text"])["checks"]
    check("with no fit snapshot table, that is one format failure, not one per Provenance cell",
          sorted((c["target"], c["verdict"], c["kind"]) for c in got if c["check"] == "quotes"),
          [("banks", "PASS", "judgement"), ("fit_snapshot", "FAIL", "format")])
    check("a candidate sentence the fit snapshot does not quote fails: Provenance quotes it as it appears there",
          banks("Led 30+ end-to-end client integrations of the vendor's REST APIs"), ["FAIL"])

    # A plain acknowledgment's source may be a dossier item named by its field
    # (question-rubric.md, "A plain acknowledgment"): the cell names the field
    # anywhere, and a quotation that is one whole item of a field it names is that
    # item; any other quotation is the candidate's (HN1; round 5 N2).
    def named(provenance):
        got = output_checks.run_checks(mi4, "denied", pack("x").replace('[grounded] "x"', provenance), None)
        return [c["verdict"] for c in got["checks"] if c["check"] == "quotes" and c["target"] == "banks"]
    check("a prohibited_claims item quoted after its field's name passes",
          named('[grounded] dossier prohibited_claims: "Having owned a product roadmap"'), ["PASS"])
    check("an acknowledge_gap area quoted after its field's name passes",
          named('[grounded] `acknowledge_gap` "Owning a roadmap and prioritization authority (R1 sub-claim)"'),
          ["PASS"])
    check("the same items named without quotation marks pass",
          named("[grounded] dossier prohibited_claims item, Having owned a product roadmap"), ["PASS"])
    check("text that is no item of the named field fails",
          named('[grounded] prohibited_claims: "Owned the roadmap for the partner API"'), ["FAIL"])
    check("a fragment of an item fails: the item is quoted whole",
          named('[grounded] prohibited_claims: "owned a product roadmap"'), ["FAIL"])
    check("one field's item under another field's name fails",
          named('[grounded] acknowledge_gap: "Having owned a product roadmap"'), ["FAIL"])
    check("a bridge area under acknowledge_gap fails: only acknowledge_gap areas are that field's",
          named('[grounded] acknowledge_gap: "3+ years product management experience (R1)"'), ["FAIL"])
    check("a field's name with no dossier in the request fails",
          [c["verdict"] for c in output_checks.check_quotes(
              pack("x").replace('[grounded] "x"', '[grounded] prohibited_claims: "Having owned a product roadmap"'),
              "no dossier here", (), mi4["candidate_text"])["checks"]
           if c["check"] == "quotes" and c["target"] == "banks"], ["FAIL"])
    check("two whole items after one naming of their field pass",
          named('[grounded] prohibited_claims: "Having owned a product roadmap", "Having held a product '
                'manager title or role"'), ["PASS"])
    for form in ('[grounded] dossier prohibited_claims ("Having owned a product roadmap")',
                 '[grounded] "Having owned a product roadmap" (dossier prohibited_claims)',
                 '[grounded] dossier prohibited_claims items: "Having owned a product roadmap"; "Having held a '
                 'product manager title or role"',
                 '[grounded] a dossier `prohibited_claim`: "Having owned a product roadmap"',
                 '[grounded] dossier acknowledge_gap area, R1: "Owning a roadmap and prioritization authority '
                 '(R1 sub-claim)"'):
        check(f"the field named anywhere in the cell, the item whole, passes: {form!r}", named(form), ["PASS"])
    check("a cell that names only acknowledge_gap cannot cite a prohibited_claims item, wherever it sits",
          named('[grounded] acknowledge_gap area, as the dossier frames it; see "Having owned a product roadmap"'),
          ["FAIL"])
    check("a field's name inside a quotation names nothing: both quotations are read as the candidate's",
          named('[grounded] "prohibited_claims" and "Having owned a product roadmap"'), ["FAIL", "FAIL"])
    check("a candidate quotation beside a field's item is still checked as the candidate's",
          named('[grounded] prohibited_claims: "Having owned a product roadmap"; "Led the roadmap for the '
                'partner API"'), ["FAIL"])


GATED_MAP = """
## Evidence map

| # | Requirement | Priority | Fit | Confidence |
|---|---|---|---|---|
| R1 | UK work eligibility without sponsorship | hard_gate | direct | high |
| R2 | On-site five days a week | hard_gate | {r2} | high |
| R3 | Base salary at or above £95k | hard_gate | {r3} | low |
| R4 | Shipped APIs consumed by external developers | must_have | direct | medium |

## Risk register

| # | Signal | Class | Severity | Status |
|---|---|---|---|---|
| RR1 | Office attendance stated as five days | risk_signal | {rr1} | unresolved |
| RR2 | Compensation unstated | risk_signal | medium | unresolved |
"""


def gated(gates="- **Hard gates:** failed: R2 (On-site five days a week); unconfirmed: R3 (Base salary at or above "
                "£95k); met: R1 `direct`.",
          flags="- **Severe red flags:** RR1 (`severity: high`).", status="No. Status: `no_go`.",
          after="R3 waits on the band.", r2="hard_gate_fail", r3="unclear", rr1="high", tail="") -> str:
    ledger = {("hard_gate_fail", "unclear"): "- `hard_gate` — direct: R1 · unclear: R3 (Base salary at or above "
                                             "£95k) · hard_gate_fail: R2 (On-site five days a week)",
              ("direct", "unclear"): "- `hard_gate` — direct: R1, R2 · unclear: R3 (Base salary at or above £95k)",
              ("direct", "direct"): "- `hard_gate` — direct: R1, R2, R3"}[(r2, r3)]
    return (f"## Decision snapshot\n\n**{status}**\n\n**Fit ledger.**\n\n{ledger}\n"
            f"- `must_have` — direct: R4\n\n{after}\n\n**Opportunity ledger.** RR1 reads the office terms.\n\n"
            f"{gates}\n{flags}\n" + GATED_MAP.format(r2=r2, r3=r3, rr1=rr1) + tail)


def test_gates_line() -> None:
    print("\nchecks: the hard-gates line is the slot, and names every gate row (D3)")
    # Round 5 FX-N4: a Requirement's own words may hold a parenthesis ("Fully remote
    # (UK)"), and the fit ledger and the hard-gates line read them with one item
    # grammar (ledger_rules.ITEM_WORDS), so a name one accepts the other accepts.
    def slot(line: str) -> str:
        return f"## Decision snapshot\n\n- **Hard gates:** {line}\n"
    remote = {"R6": {"priority": "hard_gate", "fit": "unclear", "requirement": "Fully remote (UK)"}}
    check("an unconfirmed gate named in Requirement words that hold a parenthesis passes",
          ledger_rules.gates_line_problems(slot(
              "none failed; unconfirmed: R6 (Fully remote (UK)); candidate constraints not given — checks against "
              "them unknown"), remote, True), [])
    check("a failed gate named so passes",
          ledger_rules.gates_line_problems(slot("failed: R6 (Remote (US) or our Denver office)"), {
              "R6": {"priority": "hard_gate", "fit": "hard_gate_fail",
                     "requirement": "Remote (US) or our Denver office"}}, False), [])
    check("words its Requirement does not use still fail, parenthesis or not",
          [k for k, _ in ledger_rules.gates_line_problems(slot(
              "none failed; unconfirmed: R6 (Fully remote (UK) — Leeds office)"), remote, False)], ["form"])
    nested = output_checks.parse_fit_ledger("**Fit ledger.**\n\n- `hard_gate` — unclear: R6 (Fully remote (UK))\n")
    check("and the fit ledger reads the same item the same way",
          (nested["outcome"], nested["lines"][0]["groups"][0]["items"] if nested["lines"] else None),
          ("checked", [{"id": "R6", "note": "Fully remote (UK)"}]))
    check("failed, unconfirmed and met rows, each in its clause, pass", ledger_fails(gated()), [])
    check("a met gate row left out beside a failed one fails", ledger_fails(gated(
        gates="- **Hard gates:** failed: R2 (On-site five days a week); unconfirmed: R3 (Base salary at or above "
              "£95k).")), ["gates_line"])
    check("a failed row filed as met fails", ledger_fails(gated(
        gates="- **Hard gates:** unconfirmed: R3 (Base salary at or above £95k); met: R1 `direct`, R2 `direct`.")),
        ["gates_line"])
    check("\"none failed\" while a gate row failed fails", ledger_fails(gated(
        gates="- **Hard gates:** none failed (R1 `direct`, R2 `direct`); unconfirmed: R3 (Base salary at or above "
              "£95k).")), ["gates_line"])
    check("\"hard gates\" in the status line is not the slot: the slot below it is read", ledger_fails(gated(
        status="No — the hard gates fail. Status: `no_go`.")), [])
    check("a decoy naming the right rows does not stand in for a wrong slot", ledger_fails(gated(
        status="No — the hard gates are R1, R2 and R3. Status: `no_go`.",
        gates="- **Hard gates:** failed: R2 (On-site five days a week).")), ["gates_line"])
    check("no slot fails as format, and the judgement is left unchecked",
          ([(c["check"], c["verdict"], c["kind"]) for c in output_checks.check_fit_ledger(gated(gates=""))["checks"]
            if c["check"].startswith("gates")],
           "gates_line" in output_checks.check_fit_ledger(gated(gates=""))["unchecked"]),
          ([("gates_form", "FAIL", "format")], True))
    check("two slots fail as format", ledger_fails(gated(gates=gated.__defaults__[0] + "\n" + gated.__defaults__[0])),
          ["gates_form"])
    check("a plain 'Hard gates:' label is the slot", ledger_fails(gated(
        gates="Hard gates: failed: R2 (On-site five days a week); unconfirmed: R3 (Base salary at or above "
              "£95k); met: R1 `direct`.")), [])
    check("none failed, with met rows in its parentheses and an unconfirmed row, passes", ledger_fails(gated(
        r2="direct", status="Yes. Status: `conditional_go`.",
        gates="- **Hard gates:** none failed (R1 `direct`, R2 `direct`); unconfirmed: R3 (Base salary at or "
              "above £95k).")), [])
    check("an unconfirmed row without its Requirement's words fails as format", ledger_fails(gated(
        gates="- **Hard gates:** failed: R2 (On-site five days a week); unconfirmed: R3; met: R1 `direct`.")),
        ["gates_form"])
    check("a met row given the wrong fit fails", ledger_fails(gated(
        r2="direct", r3="direct", status="Yes. Status: `go`.",
        gates="- **Hard gates:** none failed (R1 `direct`, R2 `adjacent`, R3 `direct`).")), ["gates_line"])
    envelope = '\n```json\n{"sections": {"candidate_constraints": {"status": "unknown", "items": []}}}\n```\n'
    check("constraints not given: a line without the closing clause fails", ledger_fails(gated(tail=envelope)),
          ["gates_line"])
    check("and one ending with it passes", ledger_fails(gated(
        tail=envelope, gates="- **Hard gates:** failed: R2 (On-site five days a week); unconfirmed: R3 (Base salary "
                             "at or above £95k); met: R1 `direct`; candidate constraints not given — checks against "
                             "them unknown.")), [])
    flagged = ("- **Hard gates:** failed: R2 (On-site five days a week); unconfirmed: R3 (Base salary at or above "
               "£95k); met: R1 `direct`; candidate constraints not given — checks against them unknown.")

    def gate_verdict(text, declared):
        return verdict_of(output_checks.check_fit_ledger(text, declared), "gates_line")
    check("a fixture declaring constraints unknown: the line without the clause fails, with it passes",
          (gate_verdict(gated(), "unknown"), gate_verdict(gated(gates=flagged), "unknown")), ("FAIL", "PASS"))
    check("a fixture declaring constraints known: the clause fails, its absence passes",
          (gate_verdict(gated(gates=flagged), "known"), gate_verdict(gated(), "known")), ("FAIL", "PASS"))
    check("the fixture's declaration settles it over the response's own envelope",
          gate_verdict(gated(tail=envelope), "known"), "PASS")
    check("run_checks hands the fixture's declaration to the ledger check",
          verdict_of(output_checks.run_checks({"checks": ["fit_ledger"], "candidate_constraints": "unknown"},
                                              "denied", gated(), None), "gates_line"), "FAIL")
    # A fixture's candidate_constraints is the only source of truth for a fixture
    # (NP-8): missing or misspelt, it is a fixture error, and the response's own
    # envelope never decides.
    known_env = '\n```json\n{"sections": {"candidate_constraints": {"status": "known", "items": []}}}\n```\n'
    for case in ({"checks": ["fit_ledger"]}, {"checks": ["fit_ledger"], "candidate_constraints": "Unknown"}):
        got = output_checks.run_checks(case, "denied", gated(tail=known_env), None)
        check(f"a fit_ledger fixture whose candidate_constraints is {case.get('candidate_constraints')!r} fails as a "
              f"fixture error, and its envelope does not judge the closing clause",
              (verdict_of(got, "candidate_constraints"),
               next((c["kind"] for c in got["checks"] if c["check"] == "candidate_constraints"), None),
               got["status"], any("not judged" in i for i in got["info"])), ("FAIL", "fixture", "fail", True))
    check("a fixture declaring it exactly raises no fixture error", verdict_of(output_checks.run_checks(
        {"checks": ["fit_ledger"], "candidate_constraints": "known"}, "denied", gated(), None),
        "candidate_constraints"), None)
    # decision.summary is read with map_claim, the one count reader CI, snapshot_count
    # and the sentence after the ledger use (NP-6; round 5 N4), which reads a ratio as
    # the comment above ledger_rules.MAP_WORDS says (round 6 C5-1).
    def summary(text):
        return gated(tail='\n```json\n{"sections": {"decision": {"status": "no_go", "summary": '
                          + json.dumps(text) + '}}}\n```\n')
    check("a summary that counts the map fails summary_count",
          verdict_of(output_checks.check_fit_ledger(summary("Four of the seven must-haves are direct.")),
                     "summary_count"), "FAIL")
    check("a summary that names rows passes",
          verdict_of(output_checks.check_fit_ledger(summary("R2 fails the on-site gate; R3 waits on the band.")),
                     "summary_count"), "PASS")
    for text in ("Fit: 4 of 7 met.", "Conditional go: 4/7 direct.", "Go: four out of seven met.",
                 "Conditional go: R8 is the open gate; no other gate is in doubt.",
                 # round 6 C5-1: a ratio ending its clause in a predicate no list once held
                 "Six of nine look solid.", "Fit: 5/7 strong.",
                 # round 6 N1: a singular gate or "direct" before an unlisted word
                 "Conditional go: every gate checks out."):
        check(f"a summary that counts the map fails summary_count: {text!r}",
              verdict_of(output_checks.check_fit_ledger(summary(text)), "summary_count"), "FAIL")
    # GRADER (ci/ledger_rules.py, the comment above Claim): these are read as counts over
    # the map, as round 6 read them, and name a row; whether N is the rows named is the
    # grader's.
    for text in ("conditional_go: 5 of 7 covered; R4 is the stretch.", "Go: 6 of 7 satisfied, R4 open.",
                 "Go: two direct hits, R2 and R3."):
        check(f"GRADER: a count that names a row is read, and passes summary_count: {text!r}",
              (read_as(text), verdict_of(output_checks.check_fit_ledger(summary(text)), "summary_count")),
              ("named", "PASS"))
    for text in ("Conditional go: the 24/7 on-call rota (RR2) is unverified.",
                 "Pass: the role is one of two openings and pay is withheld (RR4).",
                 "Go: the band covers 3 of 5 years of experience (RR3).",
                 # round 6 C5-1: the candidate's own figures and a date
                 "Go: he ranked 1 of 40 in the cohort (RR1).", "Go: the start date 3/15 is fixed (RR3)."):
        check(f"a ratio that counts something else passes summary_count, as it passes snapshot_count: {text!r}",
              (verdict_of(output_checks.check_fit_ledger(summary(text)), "summary_count"),
               ledger_rules.map_claim(text)), ("PASS", None))
    got = output_checks.check_fit_ledger(gated())
    check("with no JSON envelope summary_count is unchecked, not passed",
          (verdict_of(got, "summary_count"), "summary_count" in got["unchecked"]), (None, True))
    for case_id, status in ((1, "unknown"), (2, "unknown"), (3, "known"), (4, "unknown"), (5, "unknown")):
        case = fixture("job-underwriter", case_id)
        clause = "the line must end with its 'candidate constraints not given' clause" if status == "unknown" \
            else "must not carry the 'candidate constraints not given' clause"
        check_true(f"job-underwriter {case_id}: declares constraints {status}, and its hard-gates expectation "
                   f"says so", case.get("candidate_constraints") == status
                   and any(clause in e for e in case["expectations"] if "'- **Hard gates:** …'" in e))
    nogate = LEDGER_OK.replace("| hard_gate | direct | high |", "| must_have | direct | high |").replace(
        "- `hard_gate` — direct: R1\n- `must_have` — direct: R2, R3", "- `must_have` — direct: R1, R2, R3")
    check("with no gate rows, \"none stated\" passes", ledger_fails(nogate.replace(
        "none failed (R1 `direct`).", "none stated.")), [])
    check("with no gate rows, a line naming a row fails", ledger_fails(nogate), ["gates_line"])
    # The slot is in every snapshot, gate rows or not (amended D3, rule 4).
    slotless = nogate.replace("- **Hard gates:** none failed (R1 `direct`).\n", "")
    for declared in ("unknown", "known"):
        got = output_checks.check_fit_ledger(slotless, declared)
        check(f"with no gate rows and constraints {declared}, a snapshot with no slot fails as format",
              ([(c["check"], c["verdict"], c["kind"]) for c in got["checks"] if c["check"].startswith("gates")],
               "gates_line" in got["unchecked"]), ([("gates_form", "FAIL", "format")], True))
    stated = nogate.replace("none failed (R1 `direct`).", "none stated.")
    check("with no gate rows and constraints unknown, \"none stated\" without the closing clause fails",
          verdict_of(output_checks.check_fit_ledger(stated, "unknown"), "gates_line"), "FAIL")
    check("and with it passes", verdict_of(output_checks.check_fit_ledger(stated.replace(
        "none stated.", "none stated; candidate constraints not given — checks against them unknown."), "unknown"),
        "gates_line"), "PASS")
    # A failed row carries its Requirement's own words in parentheses, as an
    # unconfirmed one does; the conflict belongs in what would change this (P1).
    for line, why in (("failed: R2; unconfirmed: R3 (Base salary at or above £95k); met: R1 `direct`.",
                       "a failed row with no parentheses"),
                      ("failed: R2 (on-site Austin 5 days vs remote-only); unconfirmed: R3 (Base salary at or above "
                       "£95k); met: R1 `direct`.", "a failed row whose parentheses state the conflict"),
                      ("failed: R2 (`hard_gate_fail`); unconfirmed: R3 (Base salary at or above £95k); met: R1 "
                       "`direct`.", "a failed row carrying only its fit")):
        check(f"{why} fails as format", ledger_fails(gated(gates="- **Hard gates:** " + line)), ["gates_form"])
    check("a failed row in a few of its Requirement's own words passes", ledger_fails(gated(
        gates="- **Hard gates:** failed: R2 (On-site five days); unconfirmed: R3 (Base salary at or above £95k); "
              "met: R1 `direct`.")), [])
    # A gate is met, not established, or failed (evidence-model.md): a gate row at
    # `adjacent` or `absent` is a map error the line would file as met, however
    # consistently the map, the ledger and the line agree on it.
    met_go = dict(r2="direct", r3="direct", status="Yes. Status: `go`.")
    for fit in ("adjacent", "absent"):
        off = gated(**met_go, gates=f"- **Hard gates:** none failed (R1 `direct`, R2 `{fit}`, R3 `direct`).").replace(
            "| R2 | On-site five days a week | hard_gate | direct |", f"| R2 | On-site five days a week | hard_gate | {fit} |"
        ).replace("- `hard_gate` — direct: R1, R2, R3",
                  f"- `hard_gate` — direct: R1, R3 · {fit}: R2 (On-site five days a week)")
        check(f"a gate row at `{fit}`, agreed by map, ledger and line, fails", ledger_fails(off), ["gates_line"])
        check("and the finding names the gate rule", "R2 is a hard_gate row at" in next(
            c["why"] for c in output_checks.check_fit_ledger(off)["checks"] if c["check"] == "gates_line"), True)
    off_gate = gated(**met_go, gates="- **Hard gates:** none failed (R1 `direct`, R2 `direct`, R3 `direct`).").replace(
        "| R4 | Shipped APIs consumed by external developers | must_have | direct |",
        "| R4 | Shipped APIs consumed by external developers | must_have | hard_gate_fail |").replace(
        "- `must_have` — direct: R4", "- `must_have` — hard_gate_fail: R4 (Shipped APIs)")
    check("hard_gate_fail on a must_have row fails: only a gate row fails as a gate",
          ledger_fails(off_gate), ["gates_line"])


def test_severity() -> None:
    print("\nchecks: a severity is the register's, and the severe red flags are its high entries (rule 5)")
    check("RR1 (`severity: high`) over a high entry passes", ledger_fails(gated()), [])
    check("RR1 (`high`) is a band, not a severity, and fails",
          "snapshot_band" in ledger_fails(gated(flags="- **Severe red flags:** RR1 (`high`).")), True)
    check("RR2 (`severity: high`) over a medium entry fails", "severity" in ledger_fails(gated(
        flags="- **Severe red flags:** RR1 (`severity: high`), RR2 (`severity: high`).")), True)
    check("an entry the register does not have fails", "severity" in ledger_fails(gated(
        flags="- **Severe red flags:** RR1 (`severity: high`), RR9 (`severity: high`).")), True)
    check("\"none found\" over a high entry fails", ledger_fails(gated(flags="- **Severe red flags:** none found.")),
          ["severity"])
    check("\"none found\" with no high entry passes",
          ledger_fails(gated(rr1="medium", flags="- **Severe red flags:** none found.")), [])
    check("a high entry named without its full token fails as format",
          ledger_fails(gated(flags="- **Severe red flags:** RR1.")), ["severity_form"])
    check("a severity in the opportunity ledger is checked too", "severity" in ledger_fails(gated(
        after="R3 waits on the band (RR2 (`severity: low`)).")), True)


def test_shared_ledger_rules() -> None:
    print("\nchecks: the harness and CI read the snapshot with the same rule functions")
    import ledger_rules
    rule = ledger_rules.rule_quantifiers((Path(__file__).resolve().parent.parent / "skills" / "job-underwriter" /
                                          "references" / "evidence-model.md").read_text(encoding="utf-8"))
    check("evidence-model.md's quantifier lists are found", bool(rule), True)
    check("and every quantifier in them is in the shared set", sorted(set(rule) - set(ledger_rules.QUANTIFIERS)), [])
    model = (Path(__file__).resolve().parent.parent / "skills" / "job-underwriter" / "references" /
             "evidence-model.md").read_text(encoding="utf-8")
    check("and the shared set sorts them as the rule does: named-set words, complements, after the ledger only",
          tuple(sorted(scope) for scope in ledger_rules.rule_quantifier_scopes(model)),
          tuple(sorted(scope) for scope in (ledger_rules.NAMED_SET, ledger_rules.COMPLEMENT,
                                            ledger_rules.AFTER_LEDGER_ONLY)))
    check("the harness uses the module CI imports", output_checks.ledger_rules is ledger_rules, True)
    # The sentence after the ledger is read twice: by rule 2's own check, which reads
    # every word of the lists there as about the map, and as snapshot prose, which
    # reads a list word as about the map with a map word within four words. Both
    # hold it to the one rule (evidence-model.md, "The row is the unit"): a set it
    # names passes, an unnamed one and a complement fail.
    for sentence, also in (("R4 is the gap; no other row is.", True),
                           ("The only rows below `direct` have credible bridges.", True),
                           ("R4 and R5 sit below `direct`; none is a gate.", False),
                           ("Both of them sit below `direct`.", True)):
        check(f"after the ledger, {sentence!r} fails", ledger_fails(LEDGER_OK.replace(
            "R4 has a credible bridge, and R3 (`medium`) waits on an artifact.", sentence)),
            ["ledger_sentence", "snapshot_count"] if also else ["ledger_sentence"])
    for sentence in ("Both R4 and R5 sit below `direct`.", "Neither R4 nor R5 is a gate.",
                     "Each of R4 and R5 needs an artifact.", "R4 and R5 both sit below `direct`.",
                     # GRADER (the comment above Claim): "no <tier> … but R4" is read as
                     # "no <tier>" over a named set
                     "No `must_have` row sits below adjacent but R4.",
                     # GRADER (round 9): a named "only", false of R7 — agreement is the grader's
                     "R4 and R5 are the only rows below `direct`.",
                     "R4, R5 and R7 are the only rows below `direct`.", "R4 is the one must-have below `direct`."):
        check(f"after the ledger, {sentence!r} names its set and passes", ledger_fails(LEDGER_OK.replace(
            "R4 has a credible bridge, and R3 (`medium`) waits on an artifact.", sentence)), [])
    check("the v0.1 count after an intact ledger fails, as the sentence and as snapshot prose",
          ledger_fails(LEDGER_OK.replace("waits on an artifact.",
                                         "waits on an artifact. Five of seven material requirements are `direct`.")),
          ["ledger_sentence", "snapshot_count"])
    # round 6 C5-1: "N of M" is read as a count of rows after the ledger in every
    # form. GRADER (the comment above Claim): one that names a row passes the check,
    # and whether N is the rows it names is the grader's.
    for sentence in ("R4 is the stretch, leaving four out of seven covered.", "R4 is the stretch; fit is 5/7 covered."):
        check(f"GRADER: after the ledger, {sentence!r} is read as a count, names R4, and passes",
              (read_as(sentence, True), ledger_fails(
                  LEDGER_OK.replace("R4 has a credible bridge, and R3 (`medium`) waits on an artifact.", sentence))),
              ("named", []))
    for sentence in ("Fit is four out of seven covered.", "Fit is 5/7 covered."):
        check(f"after the ledger, unnamed, {sentence!r} fails", ledger_fails(
            LEDGER_OK.replace("R4 has a credible bridge, and R3 (`medium`) waits on an artifact.", sentence)),
            ["ledger_sentence", "snapshot_count"])
    # round 6 check NP-3: a date and "24/7" are not ratios after the ledger either,
    # while a ratio that is one is read there as a count of rows, whatever it counts:
    # unnamed it fails; named it passes, and N is the grader's (GRADER).
    for sentence, read in (("R4 has a credible bridge; interviews close 10/16/2026.", "no claim"),
                           ("R4 waits on RR2, a 24/7 rota.", "no claim"),
                           ("R4 and R5 sit below `direct`, 4/7 overall.", "named"),
                           ("R4 is 2 of 3 on the panel.", "named"),
                           ("Her 2 of 3 launches back R2.", "named"),
                           ("Her 2 of 3 launches back the case.", "unnamed"),
                           ("She was 2 of 3 on the panel.", "unnamed")):
        check(f"after the ledger, {sentence!r} is read as {read}",
              (read_as(sentence, True), bool(ledger_rules.after_ledger_claim(sentence))), (read, read == "unnamed"))
    check("a sentence that names its rows and quantifies nothing passes", ledger_fails(LEDGER_OK.replace(
        "R4 has a credible bridge, and R3 (`medium`) waits on an artifact.",
        "R4 and R5 sit below `direct`, and R7 (`none`) has no evidence yet.")), [])
    check("a fraction in the snapshot's prose fails", ledger_fails(LEDGER_OK.replace(
        "**Opportunity ledger.** Authority", "**Opportunity ledger.** 4/7 direct. Authority")), ["snapshot_count"])
    check("a count that is not about map rows is outside the rule, and passes", ledger_fails(LEDGER_OK.replace(
        "**Opportunity ledger.** Authority", "**Opportunity ledger.** Two of three squads are hiring. Authority")), [])
    check("a count above the ledger fails", ledger_fails(LEDGER_OK.replace(
        "**Worth applying to.", "**Five of seven are `direct`; worth applying to.")), ["snapshot_count"])

    # What the first fixes still let through (cross-cutting F1, JU-11): a count with
    # words between it and its noun, a count with no "of", a second paragraph after
    # the ledger, a universal outside the sentence after the ledger, and a band
    # without backticks.
    sentence = "R4 has a credible bridge, and R3 (`medium`) waits on an artifact."
    for count in ("Four of the seven material requirements are `direct`.", "Four rows are `direct`.",
                  "Four direct, and the stretch has a bridge.", "The only gap that matters has a bridge."):
        check(f"after the ledger, {count!r} fails as the sentence and as prose",
              ledger_fails(LEDGER_OK.replace(sentence, count)), ["ledger_sentence", "snapshot_count"])
    # GRADER (round 9): "only" over a named row is a named-set word; whether R4 is the
    # only gap that matters is agreement, the grader's.
    check("GRADER: after the ledger, 'R4 is the only gap that matters.' names R4 and passes the check",
          (read_as("R4 is the only gap that matters.", True), ledger_fails(LEDGER_OK.replace(
              sentence, "R4 is the only gap that matters."))), ("named", []))
    # GRADER (the comment above Claim): the same count beside a row ID is read, names a
    # row, and passes; that it gives four and names one is the grader's.
    check("GRADER: after the ledger, 'Four direct, and R4 has a bridge.' is read as a count and passes",
          (read_as("Four direct, and R4 has a bridge.", True), ledger_fails(LEDGER_OK.replace(
              sentence, "Four direct, and R4 has a bridge."))), ("named", []))
    check("a second paragraph after the ledger fails, though the first is clean", ledger_fails(LEDGER_OK.replace(
        sentence, sentence + "\n\nThe rest are `direct`.")), ["ledger_sentence", "snapshot_count"])
    check("two sentences after the ledger fail, with no quantifier in either", ledger_fails(LEDGER_OK.replace(
        sentence, "R4 has a credible bridge. R3 (`medium`) waits on an artifact.")), ["ledger_sentence"])
    said = next(c["why"] for c in output_checks.check_fit_ledger(LEDGER_OK.replace(
        sentence, "R4 has a credible bridge. R3 (`medium`) waits on an artifact."))["checks"]
        if c["check"] == "ledger_sentence")
    check_true("and the failure says it is a second sentence, not a quantifier",
               said.startswith("more than one sentence after the ledger"))
    import ledger_rules
    check_true("the shared rule tells the two cases apart",
               ledger_rules.is_second_sentence("R4 bridges. R3 waits.",
                                               ledger_rules.after_ledger_claim("R4 bridges. R3 waits."))
               and not ledger_rules.is_second_sentence("Every row is direct.",
                                                       ledger_rules.after_ledger_claim("Every row is direct.")))
    check("a decimal or an abbreviation is not a second sentence", ledger_fails(LEDGER_OK.replace(
        sentence, "R4 has a credible bridge (e.g. the PSD2 work), and R3 (`medium`) waits on v2.1.")), [])
    check("a universal over a tier in another slot fails", ledger_fails(LEDGER_OK.replace(
        "**Worth applying to.", "**Worth applying to: every must_have requirement is direct.")),
        ["snapshot_count"])
    # GRADER (the comment above Claim): the same universal with "but R4" names a row; an
    # exception in its words is the grader's.
    check("GRADER: \"every … but R4\" in another slot names R4, and passes the check", ledger_fails(LEDGER_OK.replace(
        "**Worth applying to.", "**Worth applying to: every must_have requirement is direct but R4.")), [])
    # Round 9: no row ID here, so this pins that bare "only" is not read where it
    # qualifies, now that a named "only" passes the check anyway.
    check("\"only\" qualifying evidence before a map word, no row named, is not read in prose",
          ledger_rules.map_claim("The CV is only adjacent evidence for the sector gap."), None)
    check("\"only\" qualifying one row is not a quantifier outside the sentence after the ledger",
          ledger_fails(LEDGER_OK.replace("**Opportunity ledger.** Authority",
                                         "**Opportunity ledger.** R4 is only adjacent. Authority")), [])
    check("a figure with its unit or a range is the candidate's number, not a count of rows",
          ledger_fails(LEDGER_OK.replace("**Opportunity ledger.** Authority",
                                         "**Opportunity ledger.** R2 is 9 years against an 8+ requirement, "
                                         "teams of 3–7 (R5 `low`). Authority").replace("(R5 `low`)", "(R5 (`low`))")),
          [])
    check("an enumerator is not a count", ledger_fails(LEDGER_OK.replace(
        "- **Severe red flags:** none found.",
        "- **Severe red flags:** none found.\n- **Conditions for go:** (1) RR1 verifies; (2) R4 stays adjacent.")), [])
    check("a band without backticks is still the row's, and a wrong one fails", ledger_fails(LEDGER_OK.replace(
        "R3 (`medium`) waits", "R3 (high) waits")), ["snapshot_band"])
    check("a right one passes", ledger_fails(LEDGER_OK.replace("R3 (`medium`) waits", "R3 (medium) waits")), [])
    check("a severity written as a band without backticks fails", ledger_fails(LEDGER_OK.replace(
        "(RR1).", "(RR1 (high)).")), ["snapshot_band"])

    # How the prose is read is stated once, above ledger_rules.MAP_WORDS: a year, an
    # ordinary-English map word before one of its listed ordinary heads, a row's
    # named gate, a word past an article and a count inside a parenthesis count no
    # rows (NP-2; round 6 N1). Each holds in CI and here, because both call map_claim.
    for prose in ("Sound but under-specified, with two important unknowns: award authority (RR1) and the "
                  "contract basis (RR2).",
                  "(2) one direct conversation with the hiring manager — RR1.",
                  "R8 answered — the one question a hard gate may ask.",
                  "A start before February 2027 would fail the R9 gate.",
                  "The fund launched in 2024 and its requirements are explicit.",
                  "RR1 answered in round 2 of the interviews, and the R8 gate settled.",
                  "R5 (mentor two juniors) is `unclear`.",
                  "She manages two direct reports.",
                  "One gap analysis would settle RR1.",
                  "The 24/7 on-call rota (RR2) is unverified.",
                  "The role runs 24/7.",
                  "Pay for 2024/25 is withheld (RR4).",
                  "Interviews close 10/16/2026 (RR3).",
                  "The role is one of two openings (RR4).",
                  "R2 shipped two direct-to-consumer launches.",
                  "It would matter for a role like this one if the gates were not fatal (RR1).",
                  # round 6 C5-1: the candidate's own figures and dates, which a ratio's
                  # clause-end test leaves alone
                  "R2 is `direct`: he ranked 1 of 40 in the cohort.",
                  "R4 is `adjacent`: he was 2 of 3 on the panel that set the rubric.",
                  "R7 rests on a 4/5 from the last review (RR1).",
                  "Start date 3/15 is fixed (RR3).",
                  "He scored 9 out of 10 in the test (RR1).",
                  "R2 is `direct`: he led 3 of 5 launches.",
                  # round 6 N1: an ordinary head after a map word that is also English
                  "One question, absent a reference, decides RR1.",
                  "Two direct quotes back RR1.",
                  # round 6 re-measure: phrasings saved runs carry, read as ordinary
                  "SEO (R6) is one of seven bundled functions in the mandate.",
                  "RR1 stands: 0 of 5 budgeted searches executed.",
                  "Optional: one direct message to the poster (RR1).",
                  "The role names two direct mentees (R7).",
                  # round 6 check NP-1: register entries, actions and the candidate's own
                  # facts are not map rows
                  "Two important risks remain: RR1 and RR2.", "Two direct concerns: RR1 and RR2.",
                  "She made two direct hires last year (R7).", "One direct email to the recruiter settles RR2.",
                  "Two important red flags sit in the register.",
                  # round 6 check NP-2: the candidate's own figures with an ordinary past tense
                  "R1 is `direct`: of her pilots, 4 of 5 renewed.",
                  "R2 is `direct`: of the launches she led, 3 of 4 shipped on time.",
                  "R2 is `direct`: 3 of 4 launches shipped on time, and 3 of 4 shipped early."):
        # not read as a set claim at all, so a row ID beside it is not what passes it
        check(f"ordinary prose passes: {prose!r}", (read_as(prose), ledger_fails(
            LEDGER_OK.replace("**Opportunity ledger.** Authority", f"**Opportunity ledger.** {prose} Authority"))),
            ("no claim", []))
    for prose in ("five must-haves", "Six of nine material requirements", "only two direct", "all read direct",
                  "one adjacent one", "Two hard gates fail", "the one gap", "five important", "every requirement",
                  "two have a gap", "the one gap a reference would close", "two direct rows",
                  "both gates are met", "two soft spots are `important`", "the one preferred item",
                  "no important rows",
                  # round 5 N1: plural gates and gaps are map words wherever they stand,
                  # and a singular gate or a fit word before a verb or a fit noun counts
                  "Two gates fail", "Both gates fail",
                  "All gates hold", "Every gate passes", "Neither gate fails", "Two gaps matter",
                  "Only two gaps matter",
                  # round 5 N4: a ratio that ends its clause, or with a map word after it
                  "Fit: 4 of 7 met", "Fit: 4 of 7", "4/7 direct", "four out of seven met",
                  # round 5 N5: "no other" and "any other" are quantifiers over the map anywhere
                  "R8 is the open gate; no other gate is in doubt", "R4 is the stretch; no other must-have is "
                  "below direct", "any other requirement is direct",
                  # round 6 N1: a singular gate or gap and the adjectives are map words
                  # before any word that is not one of their listed ordinary heads
                  "Every gate checks out", "Neither gate applies to Tomás",
                  "Neither gate worries me", "Every gate gets a yes",
                  "Five important skills are open",
                  # round 6 C5-1: a ratio ending its clause
                  "5 of 7 covered", "Six of nine look solid", "5 of 7 solidly evidenced",
                  "4 of 7 met by the CV", "Fit is a 5 of 7", "her 3 of 5 skills", "Fit: 5 of 7 check out"):
        check(f"a count or quantifier over the map still fails: {prose!r}",
              (bool(ledger_rules.map_claim(prose)), ledger_fails(LEDGER_OK.replace(
                  "**Opportunity ledger.** Authority", f"**Opportunity ledger.** RR2: {prose}. Authority"))),
              (True, ["snapshot_count"]))
    # Round 9: "only" over a row ID is a named-set word; the sentence names the row, so
    # it passes — whether R4 is the whole set is agreement, the grader's.
    for prose in ("only R4 has a gap", "only the R4 gap is open"):
        check(f"GRADER: a named \"only\" is read as a set claim and passes: {prose!r}",
              (read_as(prose), ledger_fails(LEDGER_OK.replace(
                  "**Opportunity ledger.** Authority", f"**Opportunity ledger.** RR2: {prose}. Authority"))),
              ("named", []))
    # GRADER (ci/ledger_rules.py, the comment above Claim): the same readings beside a
    # row ID. Each is still read as a set claim over the map — the rounds 5-6 readings
    # these cases guard — and names a row, so it passes the check; whether the rows it
    # names are the whole set and N is right is the grader's (on this map R2 is no
    # gate, R9 no row, and R1 and R6 are `direct` too).
    for prose in ("Two gates fail outright: R1 on location and R2 on pay", "Two gates block this: R1 and R2",
                  "Five direct fits: R1, R2, R3, R6 and R9", "Two direct matches, R2 and R3",
                  "Every gate checks out except R8", "Two direct hits: R2 and R3",
                  "Fit sits at 6 of 7, with R4 open", "R4 aside, a 5/7 fit",
                  "Fit: R1 to R7, 5 of 7 confirmed by the CV",
                  "two gaps in R4 and R5", "Three direct strengths carry this: R1, R2 and R3"):
        check(f"GRADER: read as a set claim, named, and passed: {prose!r}",
              (read_as(prose), ledger_fails(LEDGER_OK.replace(
                  "**Opportunity ledger.** Authority", f"**Opportunity ledger.** RR2: {prose}. Authority"))),
              ("named", []))


def read_as(sentence: str, after: bool = False) -> str:
    """How the shared reader takes one sentence: "no claim" (no set claim read),
    "named" (set claims read, and every one passes on its sentence's row IDs),
    "unnamed" or "complement" (the first failing claim's kind)."""
    claims = ledger_rules.set_claims(sentence, after_ledger=after)
    bad = next((c for c in claims if c.why), None)
    if not claims:
        return "no claim"
    return "named" if bad is None else ("complement" if bad.kind == "complement" else "unnamed")


# What the check reads and what it leaves to the grader: the comment above Claim in
# ci/ledger_rules.py. A case below marked GRADER is one an earlier round failed here;
# it passes the check by that boundary, and the test pins the boundary.
PROSE_AND_AFTER = (False, True)


def test_named_set_claims() -> None:
    print("\nchecks: a set claim in the snapshot names a row; a complement fails there whatever it names")
    # The measured sentences in the map's vocabulary: unnamed, they fail everywhere.
    for sentence in ("You clear every must-have directly.", "Four of the seven material requirements are `direct`.",
                     "Five of seven requirements are direct."):
        for after in PROSE_AND_AFTER:
            check(f"unnamed, {'after the ledger' if after else 'in prose'}, {sentence!r} fails",
                  (read_as(sentence, after), "names no row" in getattr(
                      (ledger_rules.after_ledger_claim if after else ledger_rules.map_claim)(sentence), "why", "")),
                  ("unnamed", True))
    # GRADER: measured sentences in the candidate's vocabulary, not the map's. Outside
    # the sentence after the ledger the check does not read them; there, every word of
    # the lists is a set claim, so the unnamed ones fail.
    for sentence in ("Both of your hard constraints fail.", "None of them is a capability problem.",
                     "All candidate claims are self-reported."):
        check(f"GRADER: in the candidate's vocabulary, {sentence!r} is not read in prose, and fails unnamed after "
              f"the ledger", (read_as(sentence), read_as(sentence, True)), ("no claim", "unnamed"))
    for sentence in ("R1 and R2 both fail.", "Every must-have — R1, R2, R3 — is direct.", "Two hard gates fail: R1 and R2.",
                     "No — R1 and R2, both hard gates, fail · `no_go`.", "None of R4, R5 is a capability gap.",
                     "Neither gate — R1, R2 — is met, and R3 is.",
                     "Four of the seven requirements are `direct`: R1, R2, R3 and R6.",
                     "Four direct fits: R1, R2, R3 and R6.", "Three must-haves — R2, R3 and R4 — carry the case."):
        for after in PROSE_AND_AFTER:
            got = (ledger_rules.after_ledger_claim if after else ledger_rules.map_claim)(sentence)
            check(f"named, {'after the ledger' if after else 'in prose'}, {sentence!r} passes", got and got.why, None)
    # GRADER: named but inexact against the maps round 7 judged them on — a row left
    # out, a wrong N or M, an ID the map lacks. The check reads that they name a row.
    for sentence in ("Every must-have — R1, R2, R3 — is direct.",       # the map had a fourth must-have
                     "Two hard gates fail: R1 and R2.",                 # a third gate failed
                     "Both must-haves — R1 and R2 — are direct.",       # there were three
                     "Five of the seven requirements are `direct`: R1, R2, R3, R6 and R7.",   # four are
                     "Four of the nine requirements are `direct`: R1, R2, R3 and R6.",       # seven rows
                     "Two gates block this: R1 and R2.",                # R2 is no gate
                     "Both R4 and R9 sit below `direct`."):             # the map has no R9
        check(f"GRADER: named, whether exact or not, {sentence!r} passes the check",
              (read_as(sentence, True), ledger_rules.map_claim(sentence)), ("named", None))
    # Round 9: "only" and "the one" are named-set words. Named, they pass the check;
    # whether the rows named are the whole set is agreement, the grader's (GRADER where
    # the measured map had a further row: R5b and R8 under a ledger listing a third).
    for sentence in ("R6, R7 and R8 are the only rows below `direct`.",   # measured, exact
                     "R5b and R8 are the only rows below `direct`.",      # GRADER: measured, a third row below
                     "P1 names only R1–R5.", "R4 is the one gap; R5 and R7 are not.",
                     "R1 and R2, the only failed gates, rule it out."):
        for after in PROSE_AND_AFTER:
            check(f"named-set word, named, {'after the ledger' if after else 'in prose'}, {sentence!r} passes",
                  read_as(sentence, after), "named")
    for sentence in ("The only rows below `direct` have bridges.", "The one gap is a must-have.",
                     "Only two rows sit below `direct`."):
        for after in PROSE_AND_AFTER:
            check(f"named-set word, unnamed, {'after the ledger' if after else 'in prose'}, {sentence!r} fails",
                  read_as(sentence, after), "unnamed")
    # Every complement fails whatever it names, in prose and after the ledger.
    for phrase, sentence in (("the rest", "R4 waits on an artifact; the rest are `direct`."),
                             ("the others", "R4 waits on an artifact; the others are `direct`."),
                             ("everything else", "R4 waits on an artifact; everything else is `direct`."),
                             ("nothing else", "R4 waits on an artifact; nothing else is below `direct`."),
                             ("no other", "R4 waits on RR2, and no other row is open."),
                             ("any other", "R4 waits on an artifact longer than any other row."),
                             ("none of the others", "None of the others — R1, R2, R3, R6 — is below `direct`."),
                             ("all but", "Direct on all but R4."), ("all except", "All except R4 are direct."),
                             # Round 9: "the others" in its noun form, before a plural map noun
                             ("the other must-haves", "R4 is the one real gap; the other must-haves land `direct`."),
                             ("the other must-haves", "The other must-haves are `direct`."),
                             ("the other rows", "R4 is open; the other rows are `direct`.")):
        for after in PROSE_AND_AFTER:
            got = (ledger_rules.after_ledger_claim if after else ledger_rules.map_claim)(sentence)
            check(f"complement {phrase!r}, {'after the ledger' if after else 'in prose'}, fails whatever it names: "
                  f"{sentence!r}", (read_as(sentence, after), bool(got) and "is a complement" in got.why),
                  ("complement", True))
    # Measured after the ledger: named rows, then a complement. In prose, with no map
    # word in reach, it is the grader's (the comment above Claim).
    measured = "R1 and R2 fail outright and nothing else in the map can offset that — a gate is met or it isn't."
    check("the measured \"nothing else in the map\" fails after the ledger, and in prose is the grader's",
          (read_as(measured, True), read_as(measured)), ("complement", "no claim"))
    # GRADER (the comment above Claim): "every … but R4" is read as its named-set word;
    # "all except", like "all but", is a complement.
    check("GRADER: \"every … but R4\" is read as \"every\" over a named set, and passes the check",
          (read_as("Every must-have but R4 is `direct`."), read_as("Every must-have but R4 is `direct`.", True)),
          ("named", "named"))
    check("the singular \"the other hard gate\" names one row, and is not \"the others\"",
          (read_as("R1 fails; the other hard gate, R9, is met."),
           read_as("R1 fails; the other hard gate, R9, is met.", True)), ("no claim", "no claim"))
    check("\"all except\" is a complement in prose and after the ledger, as the comment above Claim says",
          (read_as("All except R4 are direct."), read_as("All except R4 are direct.", True)),
          ("complement", "complement"))
    check("a bare \"none\" is a complement in the sentence after the ledger, and not read elsewhere",
          (read_as("R4 and R5 sit below `direct`; none is a gate.", True),
           ledger_rules.map_claim("R4 and R5 sit below `direct`; none is a gate.")), ("complement", None))
    # GRADER: a count naming fewer rows than it gives, and a named universal that
    # leaves a row out, pass the check on presence.
    for sentence in ("Every must-have — R2 and R3 — is `direct`.", "Four direct fits: R1 and R2."):
        check(f"GRADER: N against the names, and the whole set, are the grader's: {sentence!r} passes",
              read_as(sentence), "named")
    # End to end: each slot the harness reads holds its set claims to the rule.
    sentence = "R4 has a credible bridge, and R3 (`medium`) waits on an artifact."
    for text, fails in (("Every must-have — R2, R3 and R4 — has evidence behind it.", []),
                        # GRADER: R4 is a must-have the sentence leaves out
                        ("Every must-have — R2 and R3 — is `direct`.", []),
                        ("You clear every must-have directly.", ["ledger_sentence", "snapshot_count"]),
                        # GRADER: named, and R7 is below `direct` too
                        ("R4 and R5 are the only rows below `direct`.", []),
                        ("The only rows below `direct` have bridges.", ["ledger_sentence", "snapshot_count"]),
                        ("R4 waits on an artifact; the rest are `direct`.", ["ledger_sentence", "snapshot_count"]),
                        ("R1 and R2 fail outright and nothing else in the map can offset that.",
                         ["ledger_sentence"])):
        check(f"after the ledger, {text!r} {'fails' if fails else 'passes'}",
              ledger_fails(LEDGER_OK.replace(sentence, text)), fails)
    for status, fails in (("No — R1, a hard gate, fails. Status: `no_go`.", []),
                          # GRADER: measured, in the candidate's vocabulary
                          ("No — both of your hard constraints fail. Status: `no_go`.", []),
                          ("Yes — you clear every must-have directly. Status: `go`.", ["snapshot_count"])):
        check(f"the status line {status!r} {'fails' if fails else 'passes'}", ledger_fails(LEDGER_OK.replace(
            "**Worth applying to. Status: `conditional_go`.**", f"**{status}**")), fails)
    def summary(text):
        return LEDGER_OK + '\n```json\n{"sections": {"decision": {"status": "go", "summary": ' + json.dumps(text) + '}}}\n```\n'
    for text, verdict in (("Go: every must-have — R2, R3 and R4 — is direct or adjacent.", "PASS"),
                          ("Go: you clear every must-have directly.", "FAIL"),
                          # GRADER: a set by gap type written without "gap" is not read
                          ("Go: none of them is a capability problem.", "PASS"),
                          # with "gap" it is a map word, read, and unnamed
                          ("Go: none of them is a capability gap.", "FAIL"),
                          # round 9: a named "only", here exact
                          ("Go: R4 is the only must-have below direct.", "PASS"),
                          # GRADER: a named "only", false of R5 and R7
                          ("Go: R4 is the only row below direct.", "PASS"),
                          ("Go: the only must-have below direct has a bridge.", "FAIL"),
                          ("Go: R4 waits on an artifact, and the rest are direct.", "FAIL"),
                          # GRADER: R4 is a must-have the sentence leaves out
                          ("Go: every must-have — R2 and R3 — is direct.", "PASS")):
        check(f"decision.summary {text!r} is {verdict}", verdict_of(output_checks.check_fit_ledger(summary(text)),
                                                                     "summary_count"), verdict)

    test_set_claim_subjects()


def test_set_claim_subjects() -> None:
    print("\nchecks: which set a claim describes, and whether it is exact, are the grader's (round 7's cases)")
    # Round 7 judged each of these against a map holding a further row of the class
    # the sentence's rows belong to. The check reads presence and complements
    # only; the comment marks what the grader decides.
    for sentence, after_only in (
            ("R3 and R4 are both `direct`.", False), ("R3 and R4 both are `direct`.", False),
            ("R1 and R2 are both `hard_gate_fail`.", False), ("R3 and R4 are both must-haves.", False),
            ("R1 and R2, both hard gates, fail.", False), ("R1 and R2 both fail.", True),
            ("R1 and R2 are both hard gates, and both fail.", False),
            ("R1 and R2 are both hard gates that fail.", False),
            ("Every must-have — R1, R2, R3 and R4 — is `direct`.", False),
            ("You clear every must-have — R1, R2, R3, R4 — directly.", False),
            ("None of the must-haves — R1, R2, R3, R4 — is below `direct`.", False),
            ("Two gaps matter: R4 and R5b.", False), ("One of the four gaps is a must-have: R4.", False),
            ("No — two of the three hard gates fail (R1, R2).", False),
            ("No — both failed hard gates, R1 and R2, rule it out.", False),
            ("Two of the four rows below `direct` need an artifact: R4 and R5b.", False),
            ("Two of the four gaps carry the risk: R4 and R5b.", False),
            ("Both hard gates you fail — R1 and R2 — rule it out.", False),
            ("Every open must-have — R4 — has a named bridge.", False),
            ("Every gap that matters — R4 and R5b — has a bridge.", False),
            ("Every hard gate and must-have — R1, R2, R3, R4, R8 and R9 — is in the map.", False),
            ("Every must-have — R2, R3, R4a and R4b — is covered.", False),
            ("Two must-haves are below `direct`: R4a and R4b.", False),
            # GRADER: round 7 failed each of these as inexact or false on its map
            ("R3 and R5 are both `direct`.", False),                         # R5 is `adjacent`
            ("R1 and R3 both fail.", True),                                  # R3 is unclear
            ("Every `direct` row — R3, R4 — is a must-have.", False),        # R7 is `direct` too
            ("Neither R1 nor R4 is `direct`.", False),                       # R1 is
            ("Four must-haves are `direct`: R1, R2, R3 and R4.", False),     # three are
            ("Both hard gates, R1 and R2, fail.", False),                    # there are three gates
            ("Two of the two hard gates fail: R1 and R2.", False),           # M is three
            ("Two gaps fail: R4.", False),                                   # N against one name
            ("Two of the five gaps carry the risk: R4 and R5b.", False),     # M is four
            ("Two of the four gaps carry the risk: R4 and R2.", False),      # R2 is no gap
            ("Every hard gate and must-have — R1 and R9 — is in the map.", False),   # rows left out
            ("R4, R5a and R5b both need evidence.", True),                   # "both" over three
            ("Every must-have (R2–R4) is evidenced.", False),                # a range
            ("Every must-have — R2, R3, R4a–b — is covered.", False),        # a range of a split row
            ("Every must-have — R2, R3 and R4 — is covered.", False),        # a split row's parent ID
            ("All your candidate claims are self-reported, and R4 needs a work sample.", True)):  # another clause's ID
        for after in ((True,) if after_only else PROSE_AND_AFTER):
            check(f"read as a named set claim, {'after the ledger' if after else 'in prose'}: {sentence!r}",
                  read_as(sentence, after), "named")
    # Not a set claim the check reads: the candidate's constraints, and named-set words
    # and complements that restrict something other than rows.
    for sentence in ("Arjun states no constraints or non-negotiables of his own, so checks against them are unknown.",
                     "No hard constraints were stated, so checks against them are unknown.",
                     "None of your constraints were stated.",
                     "Only the employer can change R1 and R2 — a $150k base and a remote exception.",
                     "Only the CV can confirm R4.", "The only thing that changes R1 is the base.",
                     "The only thing R4 lacks is a shipped artifact.",
                     "Go, on one condition: the one thing R4 needs is a work sample.",
                     "(2) the one question for R8 — permanent or fixed-term — answered permanent",
                     "The rest depends on R8.",
                     # GRADER: the candidate's vocabulary, named or not
                     "No — both of your hard constraints, R1 and R2, fail · `no_go`",
                     "Both of your non-negotiables — R1 and R2 — fail.",
                     "Both of your hard constraints fail.", "You fail both of your hard constraints.",
                     "Both of your hard constraints are in doubt.", "Both of your stated constraints fail."):
        check(f"passes in prose: {sentence!r}", ledger_rules.map_claim(sentence), None)
    for sentence in ("Both hard gates fail.", "Every must-have is `direct`."):
        for after in PROSE_AND_AFTER:
            check(f"unnamed, {'after the ledger' if after else 'in prose'}, fails: {sentence!r}",
                  read_as(sentence, after), "unnamed")
    # Round 9: named-set words over the rows they name; whether those are the whole set
    # is the grader's (GRADER: R5b and R8 under a ledger listing a third).
    for sentence in ("P1 names only R1–R5.", "R5b and R8 are the only rows below `direct`.",
                     "Only the R4 and R5b rows need work."):
        for after in PROSE_AND_AFTER:
            check(f"named \"only\", {'after the ledger' if after else 'in prose'}, passes the check: {sentence!r}",
                  read_as(sentence, after), "named")
    # End to end, in the slots the harness reads.
    sentence = "R4 has a credible bridge, and R3 (`medium`) waits on an artifact."
    for text, fails in (("R2 and R3 are both `direct`, and that doesn't move R4.", []),
                        # GRADER: R4 is `adjacent`
                        ("R2 and R4 are both `direct`.", []),
                        ("Both hard gates fail.", ["ledger_sentence", "snapshot_count"])):
        check(f"after the ledger, {text!r} {'fails' if fails else 'passes'}",
              ledger_fails(LEDGER_OK.replace(sentence, text)), fails)
    slot = "- **Severe red flags:** none found."
    for line, fails in (("You gave no constraints or non-negotiables, so checks against them are unknown.", []),
                        ("Only the employer can change R1 — a sponsorship exception.", []),
                        # GRADER: R4 is `adjacent`, so "directly" is false of it
                        ("You clear every must-have — R2, R3, R4 — directly.", []),
                        ("You clear every must-have directly.", ["snapshot_count"])):
        check(f"a What-would-change line {line!r} {'fails' if fails else 'passes'}",
              ledger_fails(LEDGER_OK.replace(slot, slot + f"\n- **What would change this:** {line}")), fails)
    # A sentence is one paragraph, list item or heading's: a row ID in the line above
    # does not name a set claim in the next.
    check("a row ID on another line names nothing", ledger_fails(LEDGER_OK.replace(
        slot, slot + "\n- **What would change this:** R4 evidenced\n- **Conditions for go:** every must-have holds")),
        ["snapshot_count"])
    def summary(text):
        return LEDGER_OK + '\n```json\n{"sections": {"decision": {"status": "go", "summary": ' + json.dumps(text) + '}}}\n```\n'
    for text, verdict in (("Arjun states no constraints or non-negotiables of his own, so checks against them are "
                           "unknown.", "PASS"),
                          # GRADER: R4 is `adjacent`
                          ("Go: every must-have — R2, R3 and R4 — is `direct`.", "PASS"),
                          ("Go: every must-have is `direct`.", "FAIL")):
        check(f"decision.summary {text!r} is {verdict}", verdict_of(output_checks.check_fit_ledger(summary(text)),
                                                                     "summary_count"), verdict)


def fixture(skill: str, case_id: int) -> dict:
    from fixture_clauses import load_cases
    path = Path(__file__).resolve().parent.parent / "skills" / skill / "evals" / "evals.json"
    return next(c for c in load_cases(path) if c["id"] == case_id)


def test_user_links() -> None:
    print("\nchecks: a user link is a declared link, matched exactly, sorted the same for grader and checks")
    declared = {"user_links": ["https://acme.com/careers/senior-analyst-123"]}
    def link(url):
        return output_checks.is_user_link(entry(url, kind="fetch"), declared)
    check("the declared link with or without scheme, www., trailing slash or fragment is one",
          [link(u) for u in ("https://acme.com/careers/senior-analyst-123",
                             "http://www.ACME.com/careers/senior-analyst-123/",
                             "acme.com/careers/senior-analyst-123#apply")], [True] * 3)
    check("its home page, parent path, a truncated host, a suffix host, another case of path "
          "or another query is research",
          [link(u) for u in ("https://acme.com/", "https://acme.com", "https://acme.com/careers",
                             "https://acme.co/careers/senior-analyst-123",
                             "https://me.com/careers/senior-analyst-123",
                             "https://acme.com/careers/Senior-Analyst-123",
                             "https://acme.com/careers/senior-analyst-123?ref=x")], [False] * 7)
    check("a search is never a user link, whatever it asks",
          output_checks.is_user_link(entry("https://acme.com/careers/senior-analyst-123"), declared), False)
    check("a fixture that declares none has none, whatever its prompt names",
          output_checks.is_user_link(entry("https://acme.com/careers/senior-analyst-123", kind="fetch"),
                                     {}), False)

    ju5 = fixture("job-underwriter", 5)
    research = ju5["research"]
    check_true("ju 5's prompt names its pasted texts' sources and declares no user link",
               "pellucidlearning.com/about" in ju5["prompt"] and not research.get("user_links"))
    rows = {1: "skipped", 2: "skipped", 3: "n/a"}
    for url in ("https://pellucidlearning.com/about", "https://pellucidlearning.com",
                "https://www.pellucidlearning.com/careers"):
        got = output_checks.check_accounting(
            accounting(rows, "Research tier: L0 — no searches; user links read 1"), research, "canned",
            [entry(url, kind="fetch", targets=[1])], ju5["prompt"])
        check(f"ju 5: a fetch of {url} is research: zero_calls, target 1's skip, the count and "
              f"the user-link claim all fail",
              [verdict_of(got, "zero_calls"), verdict_of(got, "skip_has_no_call", 1),
               verdict_of(got, "tally_searches"), verdict_of(got, "tally_user_links")], ["FAIL"] * 4)

    l0 = dict(RESEARCH, user_links=["https://example.org/jd"])
    jd = [entry("https://example.org/jd", kind="fetch")]
    l0_rows = {1: "skipped", 2: "skipped", 3: "n/a"}
    got = output_checks.check_accounting(
        accounting(l0_rows, "Research tier: L0 — no searches; user links read 1"), l0, "denied", jd)
    check("L0: a declared link read and named on the line passes",
          (verdict_of(got, "tally_user_links"), verdict_of(got, "tally_searches")), ("PASS", "PASS"))
    got = output_checks.check_accounting(
        accounting(l0_rows, "Research tier: L0 — no searches"), l0, "denied", jd)
    check("L0: the same read left off the line fails", verdict_of(got, "tally_user_links"), "FAIL")
    got = output_checks.check_accounting(
        accounting(l0_rows, "Research tier: L0 — no searches; user links read 4"), l0, "denied", [])
    check("L0: user links claimed with none recorded fails", verdict_of(got, "tally_user_links"), "FAIL")
    got = output_checks.check_accounting(
        accounting(l0_rows, "Research tier: L0 — no searches; user links read 1"), l0, "denied",
        [entry("https://example.org/other", kind="fetch")])
    check("L0: an undeclared fetch called a user link fails both the claim and `no searches`",
          (verdict_of(got, "tally_user_links"), verdict_of(got, "tally_searches")), ("FAIL", "FAIL"))
    got = output_checks.check_accounting(
        accounting(l0_rows, "Research tier: L0 — no searches; user links read 1"), l0, "denied", None)
    check("with no research log the user-link count is unchecked, not passed",
          (verdict_of(got, "tally_user_links"), "tally_user_links" in got["unchecked"]), (None, True))
    # `user links read N` counts reads that returned (amended D2): a link the host
    # could not open is not a read, and the response says it could not open it.
    for outcome in ("refused", "error"):
        unopened = [entry("https://example.org/jd", outcome, kind="fetch")]
        truthful, claimed = (output_checks.check_accounting(accounting(l0_rows, line), l0, "denied", unopened)
                             for line in ("Research tier: L0 — no searches",
                                          "Research tier: L0 — no searches; user links read 1"))
        check(f"a declared link the host {outcome} is not read: the line without it passes, a claim to have "
              f"read it fails", (verdict_of(truthful, "tally_user_links"), verdict_of(truthful, "tally_searches"),
                                 verdict_of(claimed, "tally_user_links")), ("PASS", "PASS", "FAIL"))
        check_true("and the run's info says it was not opened",
                   any("user link not opened" in i for i in truthful["info"]))
    block = run_fixtures.observed_block({"research_log": [entry("https://example.org/jd", "refused", kind="fetch")]}, l0)
    check_true("the grader's record lists a refused user link apart, as not read and not counted",
               "User links not opened: 1" in block and "User links read" not in block
               and block.startswith("Recorded: no research search or fetch calls were made."))
    # Round 5 N3: the tally counts links, not fetches. One link fetched twice — the
    # second time as www. with a trailing slash, the same link after norm_url — is
    # one link read; a link refused and then fetched is read, not "not opened".
    twice = [entry("https://example.org/jd", kind="fetch"), entry("https://www.example.org/jd/", kind="fetch")]
    one, two = (output_checks.check_accounting(accounting(l0_rows, line), l0, "denied", twice)
                for line in ("Research tier: L0 — no searches; user links read 1",
                             "Research tier: L0 — no searches; user links read 2"))
    check("one link fetched twice is one link read: \"read 1\" passes, \"read 2\" fails",
          (verdict_of(one, "tally_user_links"), verdict_of(two, "tally_user_links")), ("PASS", "FAIL"))
    retried = [entry("https://example.org/jd", "refused", kind="fetch"), entry("https://example.org/jd", kind="fetch")]
    got = output_checks.check_accounting(
        accounting(l0_rows, "Research tier: L0 — no searches; user links read 1"), l0, "denied", retried)
    block = run_fixtures.observed_block({"research_log": retried}, l0)
    check("a link refused and then read counts once as read and is not listed as not opened",
          (verdict_of(got, "tally_user_links"), any("user link not opened" in i for i in got["info"]),
           "User links read: 1 link(s)" in block, "not opened" in block), ("PASS", False, True, False))
    block = run_fixtures.observed_block({"research_log": twice}, l0)
    check_true("and the grader's record asks for the link count, listing both fetches",
               "`user links read 1`" in block and "(2 fetch(es) listed below)" in block)

    meta = {"research_log": [entry("Kestrel careers", targets=[1]),
                             entry("https://example.org/jd", kind="fetch"),
                             entry("https://example.org/other", kind="fetch")]}
    block = run_fixtures.observed_block(meta, l0)
    check_true("the grader's record counts research calls without the user link",
               block.startswith("Recorded: 2 research call(s) — 1 search(es), 1 fetch(es)"))
    check_true("and lists the user link in its own group, by the checks' own classifier",
               "User links read: 1 link(s)" in block
               and block.index("example.org/jd") > block.index("User links read")
               and block.index("example.org/other") < block.index("User links read"))
    check_true("a fixture declaring no user link shows every fetch as research",
               run_fixtures.observed_block(meta).startswith("Recorded: 3 research call(s)"))
    check_true("a run that only read a user link made no research call",
               run_fixtures.observed_block({"research_log": jd}, l0)
               .startswith("Recorded: no research search or fetch calls were made."))
    shown = run_fixtures.observed_block({"research_log": [
        entry("Kestrel values", targets=[1], urls=["https://kestrel.test/values", "https://kestrel.test/careers"])]})
    check_true("a search line names the URLs the room returned for it, so which pages a run saw is graded "
               "from the record", "2 result(s): https://kestrel.test/values, https://kestrel.test/careers" in shown)


def test_user_link_fixture() -> None:
    print("\nchecks: job-underwriter eval 6, a posting the user linked, read in a canned room")
    case = fixture("job-underwriter", 6)
    research, prompt = case["research"], case["prompt"]
    link = research["user_links"][0]
    check_true("ju 6 declares one user link, the room serves a page at it, and the prompt carries the link "
               "and none of its canary", len(research["user_links"]) == 1 and link in prompt
               and [u["url"] for u in research["user_pages"]] == [link]
               and not any(output_checks.canary_in(s, prompt) for s in research["user_pages"][0]["canary"]))

    # The room: the page at the user's link is served by fetch, never by search,
    # and carries no target, so the record never charges it to one.
    def call(i, tool, **args):
        return {"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": tool, "arguments": args}}
    served = {"entity_tokens": research["entity_tokens"], "pages": research["pages"],
              "user_pages": research["user_pages"]}
    with tempfile.TemporaryDirectory() as tmp:
        replies, log_path, _ = drive_server(
            [{"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
             call(1, "fetch", url=link), call(2, "search", query="Quillfield revenue operations lead posting salary"),
             call(3, "fetch", url="https://jobs.tallyboard.example/quillfield")], Path(tmp), served)
        by_id = {r["id"]: r["result"]["content"][0]["text"] for r in replies if r.get("id") in (1, 2, 3)}
        lines = {l["id"]: l for l in map(json.loads, log_path.read_text().splitlines()) if l.get("id") in (1, 2, 3)}
        check_true("a fetch of the user's link returns its page, canary and all", "£61,500" in by_id[1])
        check("and is logged as a hit tagged with no target", (lines[1]["outcome"], lines[1]["targets"]), ("hit", []))
        check_true("a search carrying the posting's own words never returns it",
                   link not in by_id[2] and link not in lines[2]["returned_urls"])
        check("the board's parent path is no user page: the room says so", lines[3]["outcome"], "fetch_miss")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        room = out / "rooms" / "job-underwriter-6-canned-ab12cd34"
        room.mkdir(parents=True)
        paths = run_fixtures.research_paths(out, room, "a")
        run_fixtures.write_research_files(case, paths)
        check("the runner writes the user's page into the room's corpus",
              json.loads(paths["corpus"].read_text())["user_pages"], research["user_pages"])

    read = entry(link, kind="fetch", urls=[link])
    calls = [entry("Quillfield about", targets=[1], urls=["https://quillfield.co.uk/about"]),
             entry("revenue operations lead salary UK 2026", targets=[2],
                   urls=["https://ledgerline.example/2026-uk-revenue-operations-pay-guide"]),
             entry("Tamsin Achebe Quillfield", targets=[3], urls=["https://www.linkedin.example/in/tamsin-achebe"])]
    rows = {1: "yes", 2: "yes", 3: "yes"}
    line = "Research tier: L1 — searches 3 of 5, fetches 0 of 2; user links read 1"
    said = "The posting's own range, £61,500–£67,000, sits around Ledgerline's median."

    def judge(tally=line, body=said, log=(read, *calls), mode="canned", extra=""):
        return output_checks.check_accounting(accounting(rows, tally, body + extra), research, mode,
                                              None if log is None else list(log), prompt)
    names = ("tally_user_links", "tally_searches", "tally_fetches")
    canary = lambda got: verdict_of(got, "user_link_canary", "user link")  # noqa: E731

    good = judge()
    check("must pass: the link read once, named on the line, in neither count, its canary carried",
          [verdict_of(good, n) for n in names] + [canary(good)]
          + [verdict_of(good, "yes_has_call", n) for n in (1, 2, 3)],
          ["PASS"] * 7)
    check("and no call is unattributed, so no off-target row is owed",
          (verdict_of(good, "off_target_shown"), any("unattributed call" in i for i in good["info"])), (None, False))
    check("must pass: the link fetched twice is still one link read",
          verdict_of(judge(log=(read, read, *calls)), "tally_user_links"), "PASS")
    check("must pass: a figure spelled \"61.5k\" carries the canary",
          canary(judge(body="The posting pays from £61.5k.")), "PASS")
    check("must fail: the line leaves the read off", verdict_of(judge(line.split(";")[0]), "tally_user_links"),
          "FAIL")
    check("must fail: the read counted as one of the skill's own fetches",
          [verdict_of(judge("Research tier: L1 — searches 3 of 5, fetches 1 of 2; user links read 1"), n)
           for n in ("tally_fetches", "tally_user_links")], ["FAIL", "PASS"])
    check("must fail: the read counted as a fetch instead of a user link",
          [verdict_of(judge("Research tier: L1 — searches 3 of 5, fetches 1 of 2"), n)
           for n in ("tally_fetches", "tally_user_links")], ["FAIL", "FAIL"])
    check("must fail: the read counted as one of the skill's own searches",
          verdict_of(judge("Research tier: L1 — searches 4 of 5, fetches 0 of 2; user links read 1"),
                     "tally_searches"), "FAIL")
    check("must fail: the link read and its canary missing from the response",
          canary(judge(body="The posting's range sits around Ledgerline's median.")), "FAIL")
    check("must fail: a near figure is not the canary (\"161,500\")",
          canary(judge(body="It pays £161,500.")), "FAIL")
    board = entry("https://jobs.tallyboard.example/quillfield", kind="fetch")
    got = judge(log=(read, board, *calls))
    check("must fail: a fetch of the board's parent path is research, so a line that leaves it out fails "
          "and the call is unattributed", (verdict_of(got, "tally_fetches"), verdict_of(got, "off_target_shown")),
          ("FAIL", "FAIL"))
    got = judge(log=calls)
    check("the link never fetched: \"read 1\" fails, and its canary is not asked for",
          (verdict_of(got, "tally_user_links"), canary(got)), ("FAIL", None))
    got = judge(line.split(";")[0], body="", log=(entry(link, "refused", kind="fetch"), *calls))
    check("a read the host refused: not counted, the canary not asked for",
          (verdict_of(got, "tally_user_links"), canary(got),
           any("user link not opened" in i for i in got["info"])), ("PASS", None, True))
    got = judge(log=None)
    check("no research log: the canary is unchecked, not passed",
          (canary(got), "user_link_canary" in got["unchecked"]), (None, True))
    for body, want in ((said, "FAIL"), ("", "PASS")):
        got = judge(line.split(";")[0], body=body, log=[], mode="denied")
        check(f"a denied room, where no fetch can return: the canary {'present fails' if body else 'absent passes'}",
              verdict_of(got, "user_link_canary_absent", "user link"), want)
    # A search for the company by name in the posting's own words: the posting is part
    # of the request once its link was read, and not before (`request_text`).
    by_name = entry("Quillfield revenue operations lead Bristol hybrid")
    got = judge(log=(read, by_name, *calls[1:]))
    check("must pass: once the link was read, a search by name in the posting's words is target 1's",
          (verdict_of(got, "yes_has_call", 1), verdict_of(got, "off_target_shown")), ("PASS", None))
    got = judge(line.split(";")[0], log=(by_name, *calls[1:]))
    check("must fail: with the link never read, the same search is aimed at no target",
          (verdict_of(got, "yes_has_call", 1), verdict_of(got, "off_target_shown")), ("FAIL", "FAIL"))
    room = {"prompt": output_checks.request_text(prompt, research, [link]), "targets": research["targets"]}
    check("a posting-only word joins the name as a prompt word would: \"Quillfield CFO\" is target 1's, "
          "not shown as off-target (identity_search's docstring)",
          [t["n"] for t in research["targets"] if output_checks.aimed_at(entry("Quillfield CFO"), t, [], "canned", room)],
          [1])
    check("an unread or undeclared link adds nothing to the request",
          [output_checks.request_text(prompt, research, links) for links in ([], ["https://jobs.tallyboard.example"])],
          [prompt, prompt])
    block = run_fixtures.observed_block({"research_log": [read, *calls]}, research)
    check_true("the grader's record counts three searches, no fetch, and lists the link as a user link read",
               block.startswith("Recorded: 3 research call(s) — 3 search(es), 0 fetch(es)")
               and "User links read: 1 link(s)" in block and block.index(link) > block.index("User links read"))
    shown = [[link in text for text in output_checks.room_pages_text(
        [*research["pages"], *research["user_pages"]], log)] for log in ([read], calls)]
    check("a canned room's quotable text holds the user's page once it was read, and not before",
          [any(s) for s in shown], [True, False])


def test_budget_spent_unavailable() -> None:
    print("\nchecks: with research not declined, `unavailable` with no call is lawful only when the budget went on "
          "higher-priority targets")
    tally = "Research tier: L1 — searches 5 of 5, fetches 0 of 2"
    rows = {1: "yes", 2: "yes", 3: "unavailable"}
    def run(log):
        return output_checks.check_accounting(accounting(rows, tally), RESEARCH, "canned", log)
    spent = [entry(q, targets=[t]) for q, t in (("Kestrel careers", 1), ("Kestrel about", 1),
             ("Kestrel jobs", 1), ("analyst salary", 2), ("analyst compensation", 2))]
    got = run(spent)
    check("five of five searches on targets 1-2: target 3 `unavailable` passes accept and the refusal check",
          (verdict_of(got, "accept", 3), verdict_of(got, "unavailable_has_refusal", 3)), ("PASS", "PASS"))
    got = run(spent[:4] + [entry("imogen analyst", targets=[3])])
    check("one of them aimed at target 3 fails both",
          (verdict_of(got, "accept", 3), verdict_of(got, "unavailable_has_refusal", 3)), ("FAIL", "FAIL"))
    got = run(spent[:4] + [entry("Kestrel lawsuit")])
    check("one of them aimed at no target fails both",
          (verdict_of(got, "accept", 3), verdict_of(got, "unavailable_has_refusal", 3)), ("FAIL", "FAIL"))
    got = output_checks.check_accounting(
        accounting(rows, "Research tier: L1 — searches 4 of 5, fetches 0 of 2"), RESEARCH, "canned", spent[:4])
    check("four of five spent fails both",
          (verdict_of(got, "accept", 3), verdict_of(got, "unavailable_has_refusal", 3)), ("FAIL", "FAIL"))
    first = dict(RESEARCH, targets=[dict(t, accept={"canned": ["yes"]}) for t in RESEARCH["targets"]])
    got = output_checks.check_accounting(
        accounting({1: "unavailable", 2: "yes", 3: "yes"}, tally), first, "canned",
        [entry(q, targets=[t]) for q, t in (("analyst salary", 2), ("analyst pay", 2),
                                            ("imogen", 3), ("imogen talks", 3), ("imogen writing", 3))])
    check("a budget spent on lower-priority targets does not excuse target 1",
          (verdict_of(got, "accept", 1), verdict_of(got, "unavailable_has_refusal", 1)), ("FAIL", "FAIL"))
    got = output_checks.check_accounting(accounting(rows, tally), first, "canned", None)
    check("with no research log, a canned `unavailable` outside the accept list is unchecked, not failed",
          (verdict_of(got, "accept", 3), "accept" in got["unchecked"]), (None, True))


def test_declined_unavailable() -> None:
    print("\nchecks: `unavailable` with no call is lawful when the user declined research or chose L0")
    first = [dict(t, accept={"canned": ["yes"]}) for t in RESEARCH["targets"]]
    declined = dict(RESEARCH, targets=first, declined=True, user_links=["https://example.org/jd"])
    rows = {1: "unavailable", 2: "unavailable", 3: "unavailable"}
    l0 = "Research tier: L0 — no searches"

    def run(fixture, log, tally=l0):
        return output_checks.check_accounting(accounting(rows, tally), fixture, "canned", log)

    def verdicts(got):
        return [verdict_of(got, c, n) for n in (1, 2, 3) for c in ("accept", "unavailable_has_refusal")]

    got = run(declined, [])
    check("declined, no call sent: every `unavailable` passes accept and the refusal check, "
          "and the L0 line and zero calls pass",
          (verdicts(got), verdict_of(got, "tally_l0"), verdict_of(got, "zero_calls")),
          (["PASS"] * 6, "PASS", "PASS"))
    got = run(declined, [entry("https://example.org/jd", kind="fetch")],
              "Research tier: L0 — no searches; user links read 1")
    check("declined, only a declared user link read: still lawful, and zero calls passes",
          (verdicts(got), verdict_of(got, "tally_l0"), verdict_of(got, "zero_calls")),
          (["PASS"] * 6, "PASS", "PASS"))
    got = run(declined, [entry("analyst salary", outcome="refused", targets=[2])])
    check("declined, one refused search sent: zero calls fails",
          verdict_of(got, "zero_calls"), "FAIL")
    got = run(declined, [entry("analyst salary", targets=[2])],
              "Research tier: L1 — searches 1 of 5, fetches 0 of 2")
    check("declined, a search sent and returned: target 2's `unavailable`, the L0 line and zero calls fail",
          (verdict_of(got, "accept", 2), verdict_of(got, "unavailable_has_refusal", 2),
           verdict_of(got, "tally_l0"), verdict_of(got, "zero_calls")), ("FAIL",) * 4)
    got = run(declined, [entry("https://example.org/other", kind="fetch")])
    check("declined, a fetch of an undeclared link fails zero calls",
          verdict_of(got, "zero_calls"), "FAIL")
    got = run(declined, [], "Research tier: L1 — searches 0 of 5, fetches 0 of 2")
    check("declined, a budgeted line with nothing spent still fails the L0 line",
          verdict_of(got, "tally_l0"), "FAIL")
    got = run(declined, None)
    check("declined with no research log: accept is unchecked, not passed",
          (verdict_of(got, "accept", 1), "accept" in got["unchecked"],
           "zero_calls" in got["unchecked"]), (None, True, True))

    undeclared = dict(declined, declined=False)
    got = run(undeclared, [], "Research tier: L1 — searches 0 of 5, fetches 0 of 2")
    check("not declined and the budget unspent, no call sent: every `unavailable` fails both",
          verdicts(got), ["FAIL"] * 6)
    check("and no L0 line or zero calls is asked of it",
          (verdict_of(got, "tally_l0"), verdict_of(got, "zero_calls")), (None, None))


def test_off_target_rows() -> None:
    print("\nchecks: a call outside every target is shown as an un-numbered `yes` row after the numbered ones")
    rows = "| 1. target | yes | why |\n| 2. target | yes | why |\n| 3. target | n/a | why |\n"
    head = "Research tier: L1 — searches 3 of 5, fetches 0 of 2\n\n| Target | Status | What it moved |\n|---|---|---|\n"
    extra = "| Off-target: Kestrel lawsuit | yes | nothing moved |\n"
    canary = "It came from an experimentation-platform team.\n\n"
    log = [entry("Kestrel careers", targets=[1], urls=["https://kestrel.test/careers"]),
           entry("analyst salary", targets=[2]), entry("Kestrel lawsuit")]
    got = output_checks.check_accounting(canary + head + rows + extra, RESEARCH, "canned", log)
    check("the row is read, not a format failure, and both off-target checks pass",
          (verdict_of(got, "format"), verdict_of(got, "off_target_shown"),
           verdict_of(got, "off_target_has_call")), (None, "PASS", "PASS"))
    got = output_checks.check_accounting(canary + head + rows, RESEARCH, "canned", log)
    check("the same call with no row fails", verdict_of(got, "off_target_shown"), "FAIL")
    got = output_checks.check_accounting(
        canary + head.replace("searches 3", "searches 0") + "| 1. target | n/a | why |\n| 2. target | skipped | why |\n"
        "| 3. target | n/a | why |\n" + extra, RESEARCH, "canned", [])
    check("a row with no call recorded at all fails", verdict_of(got, "off_target_has_call"), "FAIL")
    got = output_checks.check_accounting(canary + head + extra + rows, RESEARCH, "canned", log)
    check("an un-numbered row before the numbered ones is a format failure",
          verdict_of(got, "format"), "FAIL")
    got = output_checks.check_accounting(canary + head + rows + extra.replace("| yes |", "| skipped |"),
                                         RESEARCH, "canned", log)
    check("an un-numbered row labeled anything but `yes` is a format failure",
          verdict_of(got, "format"), "FAIL")
    got = output_checks.check_accounting(canary + head + rows + extra + "| 4. target | yes | why |\n",
                                         RESEARCH, "canned", log)
    check("a numbered row after an off-target row is a format failure", verdict_of(got, "format", 4), "FAIL")
    got = output_checks.check_accounting(canary + head + rows + extra, RESEARCH, "canned", None)
    check("with no research log the off-target checks are unchecked",
          (verdict_of(got, "off_target_shown"), "off_target_shown" in got["unchecked"]), (None, True))


def test_yes_names_page() -> None:
    print("\nchecks: a `yes` row names a page a call aimed at its target returned (yes_names_page)")
    case = fixture("job-underwriter", 6)
    research, prompt = case["research"], case["prompt"]
    about, guide = "https://quillfield.co.uk/about", "https://ledgerline.example/2026-uk-revenue-operations-pay-guide"
    profile = "https://www.linkedin.example/in/tamsin-achebe"
    pay_query = "Revenue Operations Lead salary UK B2B software"
    calls = [entry("Quillfield invoicing software company Bristol", targets=[1], urls=[about]),
             entry(pay_query, targets=[2], urls=[guide]),
             entry("Tamsin Achebe Quillfield", targets=[3], urls=[profile])]
    named = {1: 'Searched "Quillfield invoicing software company Bristol": "About Quillfield" (quillfield.co.uk/about)',
             2: f'Searched "{pay_query}": "Ledgerline 2026 UK Revenue Operations Pay Guide". Moved the market line',
             3: 'Searched "Tamsin Achebe Quillfield": "Tamsin Achebe — Head of Revenue Operations, Quillfield"'}

    def judge(why: dict, log=tuple(calls), extra: str = "", on: bool = True):
        cells = {**named, **why}
        rows = "".join(f"| {n}. target | yes | {cells[n]} |\n" for n in (1, 2, 3))
        text = ("Research tier: L1 — searches 3 of 5, fetches 0 of 2\n\n| Target | Status | What it moved |\n"
                f"|---|---|---|\n{rows}{extra}")
        return output_checks.check_accounting(text, research, "canned", None if log is None else list(log),
                                              prompt, yes_pages=on)

    def page(got, target) -> str | None:
        return verdict_of(got, output_checks.YES_PAGES_CHECK, target)

    got = judge({})
    check("must pass: each row names its page — by title and address, by title, by a profile's whole title",
          [page(got, n) for n in (1, 2, 3)], ["PASS", "PASS", "PASS"])
    check("must pass: a row naming its page by full URL",
          page(judge({1: f"Searched for the company; read {about}."}), 1), "PASS")
    check("must pass: a row naming its page by bare host",
          page(judge({2: f'Searched "{pay_query}"; the guide at Ledgerline.example sets the band'}), 2), "PASS")
    check("must pass: a title trimmed of its leading segment, case and punctuation aside",
          page(judge({3: 'Searched "Tamsin Achebe Quillfield": the profile head of revenue operations '
                         '— quillfield'}), 3), "PASS")
    empty = [calls[0], entry(pay_query, targets=[2]), calls[2]]
    check("must pass: every call aimed at the target returned empty, and the row says so",
          page(judge({2: f'Searched "{pay_query}", which returned nothing usable; the band is [generic]'},
                     empty), 2), "PASS")
    elsewhere = [calls[0], entry(pay_query, targets=[2], urls=[about]), calls[2]]
    check("must pass: in a canned room, the target's calls brought back only another target's page, said so",
          page(judge({2: f'Searched "{pay_query}": not established'}, elsewhere), 2), "PASS")
    stray = entry("Quillfield layoffs glassdoor", urls=["https://forum.example/quillfield-layoffs"])
    off = "| Off-target: Quillfield layoffs | yes | {} |\n"
    got = judge({}, (*calls, stray),
                off.format('Searched "Quillfield layoffs glassdoor": forum.example/quillfield-layoffs; moved nothing'))
    check("must pass: an un-numbered off-target row naming the page its stray call returned",
          (page(got, "off-target 1"), verdict_of(got, "off_target_shown")), ("PASS", "PASS"))

    check("must fail: a row naming its queries only",
          page(judge({2: f'Searched "{pay_query}". Moved the market line'}), 2), "FAIL")
    check("must fail: a page the log never returned",
          page(judge({2: f'Searched "{pay_query}": "UK RevOps Salary Report" (payscale.example/revops)'}), 2), "FAIL")
    check("must fail: a page returned only to another target's call",
          page(judge({2: f'Searched "{pay_query}": "About Quillfield" (quillfield.co.uk/about)'}), 2), "FAIL")
    check("must fail: a host the query itself carries is not the page",
          page(judge({1: 'Searched "quillfield.co.uk about"'},
                     [entry("quillfield.co.uk about", targets=[1], urls=[about]), *calls[1:]]), 1), "FAIL")
    check("must fail: a page named only by description",
          page(judge({1: 'Searched "Quillfield invoicing software company Bristol": the About page'}), 1), "FAIL")
    check("must fail: an empty result the row does not own up to",
          page(judge({2: f'Searched "{pay_query}". Moved the market line'}, empty), 2), "FAIL")
    check("must fail: \"not established\" when the target's own page came back",
          page(judge({2: f'Searched "{pay_query}": not established'}), 2), "FAIL")
    got = judge({}, (*calls, stray), off.format('Searched "Quillfield layoffs glassdoor"; moved nothing'))
    check("must fail: an un-numbered row naming only its query", page(got, "off-target 1"), "FAIL")
    got = judge({}, (*calls, stray), off.format('Searched "Quillfield layoffs glassdoor": "About Quillfield" '
                                                '(quillfield.co.uk/about)'))
    check("must fail: an un-numbered row naming a page only a targeted call returned",
          page(got, "off-target 1"), "FAIL")
    check("must fail: a person's name heading a profile's title is not, alone, the profile",
          page(judge({3: 'Searched "Tamsin Achebe Quillfield": Tamsin Achebe has run revenue operations '
                         'there since 2023'}), 3), "FAIL")
    check("title_forms keeps no trimmed form under half the title or under two words",
          (sorted(output_checks.title_forms("Tamsin Achebe — Head of Revenue Operations, Quillfield")),
           sorted(output_checks.title_forms("Careers — Quillfield"))),
          (["head of revenue operations quillfield", "tamsin achebe head of revenue operations quillfield"],
           ["careers quillfield"]))
    quoted = '"Ledgerline 2026 UK Revenue Operations Pay Guide"'
    check("must fail: a query sent quoted and written unquoted is still the query, not the page",
          page(judge({2: "Searched Ledgerline 2026 UK Revenue Operations Pay Guide. Moved the market line"},
                     [calls[0], entry(quoted, targets=[2], urls=[guide]), calls[2]]), 2), "FAIL")

    got = judge({}, None)
    check("with no research log the check is unchecked, never a pass",
          (page(got, 1), output_checks.YES_PAGES_CHECK in got["unchecked"]), (None, True))
    got = judge({2: f'Searched "{pay_query}"'}, on=False)
    check("a fixture that does not run the check gets no verdict", page(got, 2), None)
    refused = [calls[0], entry(pay_query, "refused", targets=[2]), calls[2]]
    got = judge({2: f'Searched "{pay_query}"'}, refused)
    check("a row none of whose calls returned is left to yes_has_call",
          (page(got, 2), verdict_of(got, "yes_has_call", 2)), (None, "FAIL"))

    response = ("Research tier: L1 — searches 3 of 5, fetches 0 of 2\n\n| Target | Status | What it moved |\n"
                "|---|---|---|\n" + "".join(f"| {n}. target | yes | {named[n]} |\n" for n in (1, 2, 3)))
    ran = output_checks.run_checks(case, "canned", response, list(calls))
    check("run_checks runs it for a job-underwriter fixture that names it",
          [c["verdict"] for c in ran["checks"] if c["check"] == output_checks.YES_PAGES_CHECK], ["PASS"] * 3)
    mi = fixture("mock-interview", 7)
    ran = output_checks.run_checks(mi, "canned", response, list(calls))
    check("and never for a mock-interview fixture, whose skill does not state the rule",
          [c for c in ran["checks"] if c["check"] == output_checks.YES_PAGES_CHECK], [])
    for skill, states in (("job-underwriter", True), ("mock-interview", False), ("resume-tailor", False)):
        text = (Path(__file__).resolve().parent.parent / "skills" / skill / "SKILL.md").read_text()
        check(f"YES_PAGES_RULE reads {skill}'s SKILL.md as {'stating' if states else 'not stating'} the rule",
              bool(output_checks.YES_PAGES_RULE.search(text)), states)


def test_canary_gate() -> None:
    print("\nchecks: the canary is asked for only of a page the room returned, and its page is checked")
    labels = {1: "yes", 2: "yes", 3: "n/a"}
    two = [entry("Kestrel careers", targets=[1]), entry("analyst salary", targets=[2])]
    got = output_checks.check_accounting(accounting(labels), RESEARCH, "canned", None)
    check("canned, no research log: the canary is unchecked, not judged",
          (verdict_of(got, "canary", 1), "canary" in got["unchecked"]), (None, True))
    for name, canaries in (
            ("no page", [{"target": 1, "text": "came from"}]),
            ("a page that is no page of the fixture", [{"target": 1, "page": "https://kestrel.example/about",
                                                       "text": "came from"}]),
            ("another target's page", [{"target": 1, "page": "https://survey.test/analyst",
                                        "text": "came from"}])):
        got = output_checks.check_accounting(accounting(labels), dict(RESEARCH, canaries=canaries),
                                             "canned", two)
        check(f"a canned canary naming {name} fails as a fixture error, never waived",
              [(c["verdict"], c["kind"]) for c in got["checks"] if c["check"] == "canary_fixture"],
              [("FAIL", "fixture")])
    got = output_checks.check_accounting(accounting({1: "unavailable", 2: "unavailable", 3: "n/a"}),
                                         dict(RESEARCH, canaries=[{"target": 1, "text": "came from"}]),
                                         "denied", [])
    check("a denied room needs no page: only the negative control runs",
          (verdict_of(got, "canary_fixture", 1), verdict_of(got, "canary_absent", 1)), (None, "PASS"))
    fetched = [entry("https://kestrel.test/careers/", kind="fetch", targets=[1],
                     urls=["https://kestrel.test/careers"]), entry("analyst salary", targets=[2])]
    got = output_checks.check_accounting(accounting(labels), RESEARCH, "canned", fetched)
    check("a page the room returned to a fetch is asked for", verdict_of(got, "canary", 1), "FAIL")
    missed = [entry("https://www.kestrel.test/careers", kind="fetch", targets=[]),
              entry("analyst salary", targets=[2])]
    got = output_checks.check_accounting(accounting(labels), RESEARCH, "canned", missed)
    check("a fetch the room answered with no page returns nothing to ask for",
          verdict_of(got, "canary", 1), None)
    for skill, case_id in (("job-underwriter", 4), ("mock-interview", 7)):
        case = fixture(skill, case_id)
        bad = [c for c in case["research"].get("canaries", [])
               if not any(output_checks.same_url(p.get("url", ""), c.get("page", "")) and
                          p.get("target") == c.get("target") for p in case["research"].get("pages", []))]
        check(f"{skill} {case_id}: every canary names one of its own pages for its target", bad, [])


# --- The legacy record, rebuilt from transcripts ---

def test_backfill() -> None:
    print("\nbackfill: a saved run is paired with its transcript by text, or not at all")
    def session(answer, query):
        return [{"type": "user", "parentUuid": None, "message": {"content": "prompt"}},
                {"type": "assistant", "parentUuid": "u", "message": {"content": [
                    {"type": "tool_use", "id": "w1", "name": "WebSearch", "input": {"query": query}}]}},
                {"type": "user", "parentUuid": "a", "message": {"content": [
                    {"type": "tool_result", "tool_use_id": "w1", "is_error": True,
                     "content": "Claude requested permissions to use WebSearch"}]}},
                {"type": "assistant", "parentUuid": "u", "message": {"content": [
                    {"type": "text", "text": answer}]}}]
    with tempfile.TemporaryDirectory() as tmp:
        projects = Path(tmp)
        room = projects / "-tmp-x-rooms-job-underwriter-1-aa11bb22"
        room.mkdir()
        (room / "s.jsonl").write_text("\n".join(json.dumps(e) for e in
                                                session("The answer.", "acme careers")))
        twin = projects / "-tmp-x-rooms-job-underwriter-1-cc33dd44"
        twin.mkdir()
        (twin / "s.jsonl").write_text("\n".join(json.dumps(e) for e in
                                                session("A twin answer.", "acme salary")))
        twin2 = projects / "-tmp-x-rooms-job-underwriter-1-ee55ff66"
        twin2.mkdir()
        (twin2 / "s.jsonl").write_text("\n".join(json.dumps(e) for e in
                                                 session("A twin answer.", "acme jobs")))
        pool = backfill_tools.candidates(projects, "job-underwriter", 1)
        meta = {"skill": "job-underwriter", "id": 1, "triggered_unprompted": True}
        got = backfill_tools.backfill_meta(
            meta, "The answer.\n\n----- file the response produced: x.md -----\nfile", pool)
        check("a unique match is reconstructed",
              [(e["query_or_url"], e["outcome"]) for e in got["research_log"]],
              [("acme careers", "refused")])
        check_true("with its provenance", got["research_log_provenance"]["matched_chars"] > 0)
        got = backfill_tools.backfill_meta(meta, "Nothing like it.", pool)
        check("no match is no_log, not an empty record", (got["research_log"], got.get("reason")),
              (None, "no_log"))
        got = backfill_tools.backfill_meta(meta, "A twin answer.", pool)
        check("two matches are no_log, never a guess", (got["research_log"], got.get("reason")),
              (None, "no_log"))
    meta = {"research_log": None}
    check_true("the grader is told a missing record is not a record of none",
               run_fixtures.observed_block(meta).startswith("Not recorded"))
    check_true("and an empty one is",
               run_fixtures.observed_block({"research_log": []}).startswith("Recorded: no search"))


def test_recurring() -> None:
    print("\nrecurring: verdicts pool only on identical expectation text; checks keep their own keys")
    def grade_file(d: Path, stem: str, sha, verdict: str) -> None:
        record = {"skill": "s", "id": 1, "verdicts": [{"n": 1, "why": "w", "verdict": verdict}]}
        if sha:
            record["expectation_sha256"] = {"1": sha}
        (d / f"{stem}.grade-1.json").write_text(json.dumps(record))
    def checks_file(d: Path, stem: str, status: str, verdict: str) -> None:
        (d / f"{stem}.checks.json").write_text(json.dumps({
            "skill": "s", "id": 1, "mode": "canned", "status": status,
            "checks": [{"check": "accept", "target": "2", "verdict": verdict, "why": "w"}]}))
    with tempfile.TemporaryDirectory() as tmp:
        sets = [Path(tmp) / name for name in ("a", "b", "c")]
        for d in sets:
            d.mkdir()
        grade_file(sets[0], "s-1.run0", "old", "FAIL")
        grade_file(sets[1], "s-1.run0", "new", "FAIL")
        grade_file(sets[2], "s-1.run0", None, "FAIL")
        grade_file(sets[0], "s-1.run1", None, "FAIL")
        checks_file(sets[0], "s-1.canned.run0", "fail", "FAIL")
        checks_file(sets[1], "s-1.canned.run0", "fail", "FAIL")
        checks_file(sets[2], "s-1.canned.run0", "harness-invalid", "FAIL")
        seen = recurring.scan(sets)
        check("a rewritten expectation is a different key",
              sorted(len(e["failed_sets"]) for k, e in seen.items() if k[3] == 1 and k[4] in ("old", "new")),
              [1, 1])
        check("hashless grade files still pool by position",
              len(seen[("s", 1, "denied", 1, None)]["failed_sets"]), 2)
        check("checks are keyed by check and target, invalid runs skipped",
              sorted(seen[("s", 1, "canned", ("chk", "accept", "2"), "check")]["failed_sets"]),
              ["a", "b"])

# --- Misfires found by auditing a clean-room measurement ------------------------
#
# Each check below states a misfire (a correct output the check failed, or a check
# stricter than its rule) as a must-pass, beside the real violations named with it
# as must-fails, so the fix lets nothing real through.

def test_audit_quotes() -> None:
    print("\nchecks: a Provenance quote of a named non-candidate source is checked for existence (audit A-C)")
    prompt = ("ME: I ran the weekly content-drop calendar. Never led a team.\n"
              "RECRUITER'S EMAIL: we'd like you to present a short POV on operator partnerships.\n"
              "STRATEGY BRIEF: consolidate eight branches into five hubs over 2027.")
    own = ["I ran the weekly content-drop calendar. Never led a team."]
    evidence = '"I ran the weekly content-drop calendar" — your message'

    def pack(provenance, requirement="Own the calendar", corpus=(), log=None, mode="denied"):
        return ("| # | Requirement (source) | Evidence, verbatim | Confidence | Bridge |\n|---|---|---|---|---|\n"
                f"| F1 | {requirement} | {evidence} | high | — |\n\n"
                "| # | Question | Type | Provenance | Answer guidance | Rationale |\n|---|---|---|---|---|---|\n"
                f"| A1 | q | EXP | {provenance} | g | F1 |\n")

    def banks(provenance, corpus=()):
        got = output_checks.check_quotes(pack(provenance), prompt, corpus, own)["checks"]
        return sorted(c["verdict"] for c in got if c["check"] == "quotes" and c["target"] == "banks"
                      and c["verdict"] == "FAIL") or ["PASS"]
    for cell in ('[grounded] "we\'d like you to present a short POV on operator partnerships" — recruiter\'s email',
                 '[grounded] strategy brief: "consolidate eight branches into five hubs over 2027"',
                 '[grounded] "consolidate eight branches into five hubs over 2027" (strategy brief)',
                 '[grounded] "consolidate eight branches into five hubs over 2027" — strategy brief (via recruiter); '
                 '"I ran the weekly content-drop calendar" — your message',
                 '[grounded] role_profile R5 ("consolidate eight branches into five hubs")'):
        check(f"must pass: a source line quoted with its own non-candidate origin: {cell[:70]!r}",
              banks(cell), ["PASS"])
    check("must pass: a page's title quoted inside the previous quote's origin, from the room's pages",
          banks('[grounded] "Larkspur retires per-title event teams" — Saltmarsh Games, "Announcing Project '
                'Larkspur"', ["Announcing Project Larkspur\nhttps://s.test/news\nLarkspur retires per-title "
                              "event teams in favour of one group."]), ["PASS"])
    check("must pass: the template token \"none given\" quoted as a reference is no sentence (C)",
          banks('[grounded] "I ran the weekly content-drop calendar"; [inferred] derived from F2\'s "none given" '
                'row'), ["PASS"])
    check("must fail: a company line with no origin of its own (mi1.run2 D2), beside one that has one",
          banks('[grounded] "five hubs over 2027"; "we\'d like you to present a short POV" (recruiter\'s email)'),
          ["FAIL"])
    check("must fail: a source that does not hold the quote (mi7.canned.run2 A2)",
          banks('[generic]; the "don\'t overpromise" framing is [inferred] from Tobias\'s own GDC talk (researched)'),
          ["FAIL"])
    check("must fail: an origin-tagged quote that no source holds",
          banks('[grounded] "consolidate nine branches into two hubs" — strategy brief'), ["FAIL"])
    check("must fail: a candidate negative tagged as their own, absent from the snapshot (mi7.denied.run2 B2)",
          banks('[grounded] "Never led a team" — your own stated negative'), ["FAIL"])
    check("must fail: a candidate sentence stays the candidate's whatever origin it claims, and must stand in "
          "the snapshot", banks('[grounded] "Never led a team" — LinkedIn'), ["FAIL"])
    check("must fail: a candidate quote with an insertion ([years]) is no quote",
          banks('[grounded] "I ran the weekly [years] content-drop calendar"'), ["FAIL"])
    check("must fail: a spliced quote (\"I\" for \"I've\") is no quote of a source either",
          banks('[grounded] "I ran the five hubs over 2027" — strategy brief'), ["FAIL"])
    check("must fail: a dossier field's name is the dossier's material, not another source",
          banks('[grounded] prohibited_claims: "consolidate eight branches"'), ["FAIL"])

    # B: a canned room's pages are quotable by their title and URL too, and only the
    # pages the run's log shows returned.
    mi7 = fixture("mock-interview", 7)
    larkspur = "https://saltmarshgames.com/news/project-larkspur"
    title_req = '"Announcing Project Larkspur" — Saltmarsh Games news page'
    text = pack("[grounded]").replace("| F1 | Own the calendar |", f"| F1 | {title_req} |")
    shown = [{"kind": "search", "query_or_url": "Saltmarsh news", "outcome": "returned",
              "urls_returned": [larkspur], "targets": [3]}]

    def req(log):
        got = output_checks.run_checks(mi7, "canned", text, log)["checks"]
        return [c["verdict"] for c in got if c["check"] == "quotes" and c["target"] == "requirements"]
    check("must pass: a requirement quoting a returned page's title (mi7.canned.run1 F9)", req(shown), ["PASS"])
    check("must fail: the same title when the room never returned that page", req([]), ["FAIL"])
    check("must fail: quoted [generic] prose is in no page's title, URL or text (mi7.canned.run2 F9)",
          [c["verdict"] for c in output_checks.run_checks(mi7, "canned", text.replace(
              title_req, '"[generic] team/people-management experience, a near-certain probe"'), shown)["checks"]
           if c["check"] == "quotes" and c["target"] == "requirements"], ["FAIL"])


def test_audit_evidence_form() -> None:
    print("\nchecks: the evidence cell's origins and separators are the template's, no stricter (audit)")
    for cell in ('"A" — dossier (verified_candidate_evidence)', '"A" — dossier `verified_candidate_evidence`',
                 '"A" — dossier (handoff)', '"A" — dossier handoff_to_mock_interview.verified_candidate_evidence',
                 '"A" — dossier R3 (evidence_map)', '"A" — coach\'s notes', '"A" — your CV, and "B" — your message',
                 '"A" — your CV; and "B" — your CV', '"A" — your CV, <br> "B" — your CV'):
        check(f"must pass: {cell!r}", output_checks.evidence_cell_lawful(cell), True)
    for cell in ('"A" — dossier (medium confidence: expect a probe)',
                 '"A" — dossier (handoff; medium confidence, expect a probe)',
                 '"A"; "B" — dossier (handoff)', '"A" — dossier handoff, which shows ownership',
                 '"A" — dossier (verified_candidate_evidence, strong)', '"A" — coach notes',
                 '"A" — your message, i.e. you set hiring strategy', '"A" and "B" — your message',
                 '"A", "B" — your message', '"A." "B." — your message', '"A" — your CV; adjacent: "B" — your CV',
                 '"A" — your CV + "B" — your CV', '"A" — your CV / "B" — your CV',
                 '"A" — your CV, and also "B" — your CV'):
        check(f"must fail: {cell!r}", output_checks.evidence_cell_lawful(cell), False)


def test_audit_research() -> None:
    print("\nchecks: a search for the company by name is its sweep target's; terms read as the rule does (audit)")
    ju4, mi5, mi8, mi3 = (fixture("job-underwriter", 4), fixture("mock-interview", 5),
                          fixture("mock-interview", 8), fixture("mock-interview", 3))

    def aimed(case, query, mode="denied", kind="search"):
        r = case["research"]
        room = {"prompt": case["prompt"], "targets": r["targets"]}
        e = {"kind": kind, "query_or_url": query, "targets": []}
        return [t["n"] for t in r["targets"] if output_checks.aimed_at(e, t, r.get("pages", []), mode, room)]
    check("must pass: the company's name plus the request's own description is JU target 1 (ju-4)",
          aimed(ju4, "Brindlemoor insurtech pet insurance"), [1])
    check("must pass: the name alone is JU target 1", aimed(ju4, '"Brindlemoor"'), [1])
    check("must pass: MI target 3 is the company sweep (mi-5)", aimed(mi5, '"Kelverton Rail" company'), [3])
    check("must fail: a word the request does not use makes it a stray (Brindlemoor layoffs glassdoor)",
          aimed(ju4, "Brindlemoor layoffs glassdoor"), [])
    check("must fail: words outside the request stay strays (ju-5 canned run3)",
          [aimed(fixture("job-underwriter", 5), q) for q in
           ("Pellucid Learning tutoring platform Glassdoor reviews", "Pellucid Learning Crunchbase")], [[], []])
    check("must fail: no company name, no identity (mi-8 canned run3)",
          [aimed(mi8, q) for q in ("credit union member complaints regulation ombudsman",
                                   "credit union branch complaints handling financial services regulator")], [[], []])
    check("must fail: another target's term takes it out of the identity route",
          aimed(mi8, "Ashgrove Credit Union interview process"), [2])
    try:
        output_checks.aimed_at({"kind": "search", "query_or_url": "x"}, ju4["research"]["targets"][0], [], "denied")
        raised = False
    except ValueError:
        raised = True
    check("an identity target read with no room fails closed, never silently a stray", raised, True)
    check("must pass: a market sweep tied to the sector is MI-5 target 3 (D)",
          aimed(mi5, "UK rail scheduling software train operating companies partnerships market 2026"), [3])
    check("must fail: a salary market search is no sector sweep",
          aimed(mi5, "partnerships manager salary market UK"), [])
    check("must fail: a live-service best-practices search is no target (mi-7 denied run4)",
          aimed(fixture("mock-interview", 7),
                "live service mobile game content calendar post-event review KPIs best practices 2025"), [])
    check("must pass: a job-listing fetch with an encoded role title is target 5 (mi-3 run3, C)",
          aimed(mi3, "https://stripe.com/jobs/search?q=product+operations+manager", kind="fetch"), [5])
    check("must pass: the culture page stays target 1 only",
          aimed(mi3, "https://stripe.com/jobs/culture", kind="fetch"), [1])
    check("must fail: a careers search for the role is a target-5 hunt (mi-8 canned run3)",
          aimed(mi8, "Ashgrove Credit Union careers Member Experience Lead"), [5])
    check("must pass: a regulatory search with a bare 'requirements' is no JD hunt (E)",
          5 in aimed(mi8, '"credit union" complaints handling process regulatory requirements branches contact centre'),
          False)
    check("must fail: real JD hunts still match target 5",
          [5 in aimed(mi8, q) for q in ("member experience lead responsibilities requirements",
                                        "member experience lead job description credit union")], [True, True])
    check("an all-of term needs every part", (output_checks.term_matches(["careers", "lead"], "careers page"),
                                             output_checks.term_matches(["careers", "lead"], "lead careers")),
          (False, True))

    print("\nchecks: the tally line is read as a prefix; a remark after it is read apart (audit B, B2)")
    base = "Research tier: L1 — searches 4 of 5, fetches 0 of 2"
    for line in (base + " (all refused — permission wasn't granted)", base + "; user links read: 0",
                 base + ". Every L1 target was already fixed by a provided document."):
        got = output_checks.parse_tally(line)
        check(f"must pass: a correct line with a reason or a colon is read: {line[-50:]!r}",
              (got["outcome"], got.get("searches")), ("checked", 4))
        check("and its remark restates nothing",
              [bool(output_checks.TALLY_RESTATES.search(r)) for _, r in got.get("remarks", [])],
              [False] * len(got.get("remarks", [])))
    for line in ("Research tier: L1 attempted — searches 3 of 6, fetches 0 of 2", "Research tier: L0 (forced) — no searches",
                 "Research tier: L1 — searches 0 of 6 usable / completed", "Research tier: L1 — 4 of 6 searches sent",
                 "Research tier: L1 — searches 6 of 6 attempted, 0 returned"):
        check(f"must fail: a prefix that is not the form: {line!r}", output_checks.parse_tally(line)["outcome"],
              "unparseable")
    for remark in (". All three were blocked.", " (both search calls were refused)", " (all four calls refused)",
                   " — 4 attempted", "; user links read"):
        got = output_checks.parse_tally(base + remark)
        check(f"must fail: a remark that restates the line: {remark!r}",
              [bool(output_checks.TALLY_RESTATES.search(r)) for _, r in got["remarks"]], [True])
    research = {"targets": [{"n": 1, "terms": ["about"], "accept": ["unavailable"]}],
                "budget": {"searches": 5, "fetches": 2}}
    log = [{"kind": "search", "query_or_url": "x about", "outcome": "refused", "urls_returned": [], "targets": []}] * 2
    got = output_checks.check_accounting(
        "Research tier: L0 — no searches (WebSearch wasn't granted permission)\n\n| Target | Status | x |\n|---|---|---|\n"
        "| 1. about | unavailable | x |\n", research, "denied", log)
    check("must fail: an `L0 — no searches` line with a reason now parses, and its count is judged (ju-3 run3)",
          (verdict_of(got, "tally"), verdict_of(got, "tally_searches")), ("PASS", "FAIL"))
    got = output_checks.check_accounting(
        base + " (both calls refused)\n\n| Target | Status | x |\n|---|---|---|\n| 1. about | unavailable | x |\n",
        research, "denied", log)
    check("and a restating remark fails as format, apart from the counts",
          [(c["check"], c["kind"]) for c in got["checks"] if c["verdict"] == "FAIL"],
          [("tally_remark", "format"), ("tally_searches", "judgement")])


def test_audit_ledger() -> None:
    print("\nchecks: the fit ledger is read wherever the template's shape puts it (audit)")
    for note, req in (("partnering with clinicians specifically", "Partner with clinicians specifically"),
                      ("mentoring two junior analysts", "Mentor two junior analysts"),
                      ("launch coordination with sales and support", "Coordinate launches with sales and support"),
                      ("specs + delivery with two squads", "Write specs and drive delivery with two engineering squads"),
                      ("3+ years PM experience", "3+ years product management experience (must-have)"),
                      ("3+ yrs PM experience", "3+ years PM experience (must-have)")):
        check(f"must pass: {note!r} names {req!r}", ledger_rules.names_requirement(note, req), True)
    for note, req in (("vs. Leeds office four days a week", "Leeds office four days a week"),
                      ("150k vs. your $150k floor", "Base at or above 150k"),
                      ("PM eligibility", "3+ years product management experience"),
                      ("solo execution", "Team of one"), ("dbt-modelled pipelines", "dbt pipelines"),
                      ("PR experience", "Public relations"), ("BI tooling", "Business intelligence tooling")):
        check(f"must fail: {note!r} adds words {req!r} lacks", ledger_rules.names_requirement(note, req), False)

    heading = LEDGER_OK.replace("**Fit ledger.**", "## Fit ledger").replace(
        "**Opportunity ledger.** Authority", "## Opportunity ledger\n\nAuthority")
    check("must pass: a ledger under a markdown heading, with a slot heading after it", ledger_fails(heading), [])
    check("must fail: and its problems are read there (a flipped fit)", ledger_fails(heading.replace(
        "| must_have | adjacent | medium", "| must_have | unclear | medium")), ["ledger_fit"])
    check("must fail: a response with no ledger still fails ledger_present",
          ledger_fails(LEDGER_OK.replace("**Fit ledger.**\n", "").replace(
              "- `hard_gate` — direct: R1\n", "").replace("- `must_have`", "x").replace("- `important`", "x")
              .replace("- `preferred`", "x")), ["ledger_present"])
    dashed = LEDGER_OK.replace("- `hard_gate` — direct: R1", "- `hard_gate`: direct — R1")
    check("must pass: a fit group written 'fit — IDs'", ledger_fails(dashed), [])
    check("must fail: and its rows are still judged (a missing parenthetical)", ledger_fails(dashed.replace(
        "adjacent: R4 (Regulatory exposure)", "adjacent — R4")), ["ledger_parenthetical"])
    check("must fail: a fit group with an unknown fit is still no group",
          ledger_fails(dashed.replace("direct — R1", "strong — R1")), ["ledger_present"])
    h1 = LEDGER_OK.replace("## Decision snapshot", "# Decision snapshot").replace(
        "| RR2 | Compensation unstated | risk_signal | medium | unresolved |",
        "| RR2 | Compensation unstated | risk_signal | medium | unresolved |\n\n## Upgrade menu\n\n"
        "Confidence would rise to `high` overall with a reference.")
    check("must pass: an H1 snapshot ends at the next H2, so later sections' bands are not the snapshot's",
          ledger_fails(h1), [])
    check("must fail: a bare band inside that snapshot still fails", ledger_fails(h1.replace(
        "R3 (`medium`) waits on an artifact", "R3 waits on an artifact; `high` confidence overall")),
          ["snapshot_band"])
    bold_tier = LEDGER_OK.replace("**Opportunity ledger.**", "**Research tier:** L1 — searches 3 of 5, fetches 0 "
                                                           "of 2\n\n**Opportunity ledger.**")
    check("must pass: a bold Research tier line in the snapshot is the tally, not a count of the map",
          ledger_fails(bold_tier), [])
    check("must fail: a count of the map beside it still fails", ledger_fails(bold_tier.replace(
        "**Opportunity ledger.** Authority", "**Opportunity ledger.** Three of five rows are direct. Authority")),
          ["snapshot_count"])


def test_watch_out() -> None:
    """The chat ends with the skill's watch-out line, exactly; no produced file holds it."""
    print("\nchecks: the watch-out line (output-discipline.md rule 7)")
    repo = Path(__file__).resolve().parent.parent
    lines = {s: output_checks.declared_watch_out((repo / "skills" / s / "SKILL.md").read_text())
             for s in run_fixtures.SKILLS}
    check("every skill declares a watch_out line", [s for s, v in lines.items() if not v], [])
    check("every declared line is the whole line, label included, so it is copied and never assembled",
          [s for s, v in lines.items() if not (v or "").startswith(output_checks.WATCH_OUT_LABEL + " ")], [])
    line = lines["resume-tailor"]
    sentence = output_checks.watch_out_sentence(line)
    check("watch_out_sentence is the declared line after its label", (sentence or "").startswith("The words I quote"),
          True)
    check("and is None for a line that does not begin with the label",
          (output_checks.watch_out_sentence(sentence), output_checks.watch_out_sentence("Watch out: " + sentence),
           output_checks.watch_out_sentence(output_checks.WATCH_OUT_LABEL + " ")), (None, None, None))
    body = "## Edit ledger\n\n| # | Current |\n|---|---|\n| E1 | x |\n\nC1 — What did you own?\nAnswer in text, or say skip.\n"
    marker = "\n----- file the response produced: {} -----\n"

    def verdicts(response: str) -> dict:
        got = output_checks.check_watch_out(response, line)
        return {c["target"]: c["verdict"] for c in got["checks"]}

    def why(response: str, target: str = "chat") -> str:
        got = output_checks.check_watch_out(response, line)
        return next(c["why"] for c in got["checks"] if c["target"] == target)

    check("must pass: the line is the chat's last line", verdicts(body + "\n" + line + "\n"), {"chat": "PASS"})
    check("must pass: trailing blank lines and spaces after it", verdicts(body + "\n" + line + "   \n\n\n"),
          {"chat": "PASS"})
    check("must pass: a doubled space inside the line, since runs of whitespace collapse",
          verdicts(body + "\n" + line.replace(" — ", "  — ") + "\n"), {"chat": "PASS"})
    check("must fail: no watch-out line", verdicts(body), {"chat": "FAIL"})
    check_true("and says so", why(body).startswith("no watch-out line"))
    after = body + "\n" + line + "\n\nHope this helps — good luck with the application!\n"
    check("must fail: the line is not last", verdicts(after), {"chat": "FAIL"})
    check_true("and says what follows it", "not last: 1 line(s) follow it" in why(after))
    para = body + "\n**Watch-out:** Check each quote and each new line against your original resume.\n"
    check("must fail: a paraphrased line", verdicts(para), {"chat": "FAIL"})
    check_true("and says it is not word for word", "not the skill's sentence word for word" in why(para))
    curly = body + "\n" + line.replace("you wrote", "you’d written") + "\n"
    check("must fail: one word changed", verdicts(curly), {"chat": "FAIL"})
    ju = lines["job-underwriter"]
    ju_body = body + "\n" + ju
    for label, swapped in (("curly quotes", ju_body.replace('"only"', "“only”")),
                           ("a double hyphen for the dash", ju_body.replace(" — ", " -- "))):
        got = {c["target"]: c["verdict"] for c in output_checks.check_watch_out(swapped + "\n", ju)["checks"]}
        check(f"must fail: the line copied with {label}, since it is checked character for character",
              got, {"chat": "FAIL"})
    warned = body + "\n**Warning:** " + sentence + "\n"
    check("must fail: the right sentence labelled a warning", verdicts(warned), {"chat": "FAIL"})
    check_true("and says it is never called that", "labelled a warning" in why(warned))
    twice = body + "\n**Watch-out:** check the dates.\n\n" + line + "\n"
    check("must fail: a second line labelled a watch-out", verdicts(twice), {"chat": "FAIL"})
    check_true("and says the line appears once", "the line appears once" in why(twice))
    bare = body + "\n" + sentence + "\n"
    check("must fail: the sentence without its label", verdicts(bare), {"chat": "FAIL"})
    check_true("and says the label is what is missing", "not under its label" in why(bare))
    for label, variant in (("Watch out:", "Watch out: "), ("bold Watch out:", "**Watch out:** "),
                           ("unbolded Watch-out:", "Watch-out: "), ("Watch-outs:", "**Watch-outs:** "),
                           ("lower-case watch-out:", "**watch-out:** ")):
        got = body + "\n" + variant + sentence + "\n"
        check(f"must fail: the exact sentence under a variant label, {label}", verdicts(got), {"chat": "FAIL"})
        check_true(f"and says the label is not the skill's ({label})", "not under its label" in why(got))
    para_label = body + "\nWatch out: Check each quote and each new line against your original resume.\n"
    check("must fail: a paraphrase under a variant label", verdicts(para_label), {"chat": "FAIL"})
    check_true("and says it is not word for word", "not the skill's sentence word for word" in why(para_label))
    warning_elsewhere = "Warning: this posting has no salary.\n" + body + "\n" + line + "\n"
    check("must pass: a warning elsewhere in the chat is not the slot", verdicts(warning_elsewhere), {"chat": "PASS"})
    resume = "# Priya Shah\n\nProgramme manager.\n\n" + line + "\n"
    inside = body + "\n" + line + "\n" + marker.format("resume.md") + resume
    check("must fail: the line inside a produced resume file, though the chat is right", verdicts(inside),
          {"chat": "PASS", "resume.md": "FAIL"})
    check_true("and says where it belongs", "never the file" in why(inside, "resume.md"))
    moved = body + marker.format("resume.md") + resume
    check("must fail: the line moved into the file, the chat ending without it", verdicts(moved),
          {"chat": "FAIL", "resume.md": "FAIL"})
    unlabelled = body + "\n" + line + "\n" + marker.format("resume.md") + "# Priya\n\n" + sentence + "\n"
    check("must fail: the sentence in a file without its label", verdicts(unlabelled),
          {"chat": "PASS", "resume.md": "FAIL"})
    clean = body + "\n" + line + "\n" + marker.format("pack.md") + "# Pack\n\n## Upgrade menu\n- JD text\n"
    check("must pass: a produced file without it", verdicts(clean), {"chat": "PASS", "pack.md": "PASS"})

    case = {"id": 1, "prompt": "p", "expectations": ["e"]}
    got = output_checks.run_checks(case, "denied", body + "\n" + line + "\n", None, watch_out=line)
    check("run_checks runs it when given the declared line", verdict_of(got, "watch_out", "chat"), "PASS")
    got = output_checks.run_checks(case, "denied", body + "\n" + sentence + "\n", None, watch_out=line)
    check("and fails the run whose line drops the label", (verdict_of(got, "watch_out", "chat"), got["status"]),
          ("FAIL", "fail"))
    got = output_checks.run_checks(case, "denied", body, None, watch_out=line)
    check("and fails the run without the line", (verdict_of(got, "watch_out", "chat"), got["status"]),
          ("FAIL", "fail"))
    got = output_checks.run_checks(case, "denied", body, None, watch_out="")
    check("a skill that declares none is unchecked, never passed",
          (verdict_of(got, "watch_out", "chat"), "watch_out" in got["unchecked"], got["status"]),
          (None, True, "uncheckable"))
    got = output_checks.run_checks(case, "denied", body, None)
    check("left out when not asked for", verdict_of(got, "watch_out", "chat"), None)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        for skill in run_fixtures.SKILLS:
            case = fixture(skill, 1)
            stem = run_fixtures.stem_for(skill, case, "denied", 1)
            (out / f"{stem}.meta.json").write_text(json.dumps({"harness": {"status": "ok", "reasons": []}}))
            (out / f"{stem}.md").write_text("Delivered.\n\n" + lines[skill] + "\n")
            rec = run_fixtures.check_run(skill, case, out, 1, "denied")
            check(f"check_run holds {skill} eval 1 to its own SKILL.md line",
                  verdict_of(rec, "watch_out", "chat"), "PASS")
            (out / f"{stem}.md").write_text("Delivered.\n\n" + output_checks.watch_out_sentence(lines[skill]) + "\n")
            rec = run_fixtures.check_run(skill, case, out, 1, "denied")
            check(f"and fails {skill} on its sentence without the label", verdict_of(rec, "watch_out", "chat"), "FAIL")
            other = next(s for s in run_fixtures.SKILLS if s != skill)
            (out / f"{stem}.md").write_text("Delivered.\n\n" + lines[other] + "\n")
            rec = run_fixtures.check_run(skill, case, out, 1, "denied")
            check(f"and fails {skill} on a sibling's line", verdict_of(rec, "watch_out", "chat"), "FAIL")
    for skill in run_fixtures.SKILLS:
        from fixture_clauses import load_cases
        cases = load_cases(repo / "skills" / skill / "evals" / "evals.json")
        line_of = lines[skill]
        check(f"every {skill} fixture's expectations carry its watch-out line, exactly",
              [c["id"] for c in cases if not any(line_of in e for e in c["expectations"])], [])


def main() -> int:
    for test in (test_routing_declines, test_routing_cases, test_child_env, test_routing_timeouts, test_routing_variants, test_frontdoor_generation,
                 test_frontdoor_clashes, test_frontdoor_install, test_module_lists, test_sync, test_frontdoor_labels, test_explicit_naming,
                 test_layouts_install, test_layout_naming, test_layout_transcript, test_reported_measures,
                 test_layout_runs,
                 test_cli_refusal, test_parse_stream,
                 test_server_url_identity, test_research_server, test_rooms, test_stems, test_grade_parsing,
                 test_classification, test_missing_response,
                 test_declined_grade_prints_no_score, test_artifact_collection,
                 test_skill_installation, test_classify_room, test_execute_timeout,
                 test_execute_nudge, test_via_frontdoor, test_parse_accounting, test_check_accounting,
                 test_fit_ledger, test_quotes, test_review_fixes, test_evidence_cells,
                 test_provenance_pool, test_gates_line, test_severity, test_shared_ledger_rules, test_named_set_claims,
                 test_user_links, test_user_link_fixture,
                 test_budget_spent_unavailable, test_declined_unavailable, test_off_target_rows, test_yes_names_page,
                 test_canary_gate, test_backfill,
                 test_recurring, test_audit_quotes, test_audit_evidence_form, test_audit_research,
                 test_audit_ledger, test_watch_out):
        test()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} harness test failure(s):")
        for line in FAILURES:
            print(f"  {line}")
        return 1
    print("All harness tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
