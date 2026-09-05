# Suite-level evals

Per-skill evals live in `skills/<name>/evals/` and test one skill's behaviour.
What they cannot test is **routing**: which skill fires at all. That decision is
made across the whole available-skills list, so an assertion about it has no
honest home inside either skill — hence this directory.

## Routing

`suite-routing.json` holds realistic requests and the route each should take:
a named skill, `either` (a genuinely spanning request), or `neither` (a
near-miss that must not pull either skill). The near-misses matter most — they
share the domain's whole vocabulary and are where over-triggering shows up.

`run_routing.py` puts both skills in front of the model at once and records
which one it reaches for. Three properties keep it honest:

- **It installs the real skills**, copying each one into a throwaway project's
  `.claude/skills/`, so they reach the model the way installed skills do and
  carry the descriptions that actually ship. Nothing is duplicated here.
- **Registration is the production surface.** The first version registered each
  skill as a project *command* instead, which put a caveat under every number it
  produced: commands are addressed to the model as things the user invokes, so
  "the harness under-reports" was always available as the competing explanation
  for a low score. Installing the real skills retires it.
- **A negative has to be a negative the harness actually read.** The first read
  loop broke out the moment the CLI process exited, discarding whatever was
  still sitting unparsed in the pipe — so a run that fired a skill and finished
  quickly was recorded as `neither`. It cost two rounds of chasing a triggering
  problem that was partly a reading problem, and it was only caught by running a
  "never fires" case by hand and watching it fire. Runs that time out or error
  are reported as `timeout` and `error` for the same reason: a run that never
  reached a verdict is not evidence about routing, and folding either into
  `neither` lets a slow or throttled harness manufacture findings.

```bash
python evals/run_routing.py                    # every case, 3 runs each
python evals/run_routing.py --runs 1           # quick pass
python evals/run_routing.py --case 9 --case 10 # just the spanning cases
python evals/run_routing.py --workers 1        # serial, if rate-limited
```

To A/B a description generation against the one that ships, substitute a
`SKILL.md` without touching the working tree:

```bash
git show <ref>:skills/job-underwriter/SKILL.md > /tmp/old-SKILL.md
python evals/run_routing.py --skill-md job-underwriter=/tmp/old-SKILL.md
```

That control is not optional when a description changes. A rewrite can move
which cases fire without moving how often anything fires, and only the previous
generation measured on the same harness tells the two apart.

Routing is probabilistic, so a single run proves little; the default of three
runs per case is the minimum that distinguishes "routes here" from "routes here
sometimes". Cases are scored on consistency — a case that fires the right skill
on two runs of three is a *fail*, because that is what a user meets.

## Clean-room fixtures

`run_fixtures.py` runs each skill's own `evals/evals.json` fixtures in a project
that contains only that skill — no repository, no spec, no conversation about
what the skill was meant to do — and grades the responses with graders that see
only the response and the expectations.

```bash
python evals/run_fixtures.py --out /tmp/clean-room
python evals/run_fixtures.py --skill job-underwriter --eval 3 --out /tmp/cr
python evals/run_fixtures.py --out /tmp/cr --skip-execute   # re-grade, no re-run
```

The point is authoring context. A fixture graded in the session that wrote the
skill is graded by a reader who already knows what it meant, supplies the
charitable reading, and scores the intent rather than the output.

Two things the first clean-room pass taught, both about the *expectations*
rather than the skills:

- **An expectation that refers to knowledge the grader lacks is unfalsifiable.**
  One asked whether anything "beyond the spec's owed outputs" arrived as a
  labeled offer. A grader who cannot see the spec cannot answer that, so it
  guessed, and failed a section that was owed. Expectations are now written to
  be self-contained — they name what they mean rather than pointing at a
  document the grader does not have.
- **A grader needs to be told what does not count as a failure.** The first
  grader failed conditional expectations whose condition never occurred ("where
  research ran…", in a run with no web access), and once wrote FAIL above a
  sentence reasoning its way to PASS. Those rules are now in the grader prompt.

A third lesson, this one about the harness rather than the evals: **grade the
artifact, not the cover note.** mock-interview delivers by saving its pack as a
file and presenting it, so capturing only the chat stream scored a four-sentence
summary against expectations about a 27,000-character pack. Worse, the first
attempt at a fix scanned only the project directory and found nothing — making a
skill that had delivered look like one that falsely claimed to. The packs were in
the scratchpad a nested `claude -p` is handed outside its working directory.
`collect_artifacts` now looks in both, and the same three fixtures went from
1/9, 5/10 and 4/12 to 8/9, 10/10 and 12/12 on the identical responses.

All three are defects that only appear outside the room where the eval was
written, which is the whole argument for running it there.

These evals are not run in CI: they need a model, cost real tokens, and take
minutes. Run them in a session against any change that could plausibly move
triggering — a description edit, a new skill, a boundary reworded.
