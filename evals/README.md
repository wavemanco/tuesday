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
which one it reaches for. Two properties keep it honest:

- **It reads the live frontmatter descriptions** from each `SKILL.md` rather
  than copying them here, so the eval always tests what actually ships.
- **A timed-out run reports `timeout`, never `neither`.** Folding those
  together would let a slow or rate-limited harness manufacture negatives that
  look like findings.

```bash
python evals/run_routing.py                    # every case, 3 runs each
python evals/run_routing.py --runs 1           # quick pass
python evals/run_routing.py --case 9 --case 10 # just the spanning cases
python evals/run_routing.py --workers 1        # serial, if rate-limited
```

Routing is probabilistic, so a single run proves little; the default of three
runs per case is the minimum that distinguishes "routes here" from "routes here
sometimes". Cases are scored on consistency — a case that fires the right skill
on two runs of three is a *fail*, because that is what a user meets.

These evals are not run in CI: they need a model, cost real tokens, and take
minutes. Run them in a session against any change that could plausibly move
triggering — a description edit, a new skill, a boundary reworded.
