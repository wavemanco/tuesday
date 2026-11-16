# Suite-level evals

Per-skill evals live in `skills/<name>/evals/` and test one skill's behaviour.
What they cannot test is **routing**: which skill fires at all. That decision is
made across the whole available-skills list, so an assertion about it has no
honest home inside any one skill — hence this directory.

## Routing

`suite-routing.json` holds realistic requests and the route each should take:
a named skill, `either` (a genuinely spanning request, which lists the skills
it spans as `siblings` and passes when every run fires one of them), or
`neither` (a near-miss that must pull no skill at all). The near-misses matter most — they
share the domain's whole vocabulary and are where over-triggering shows up.

`run_routing.py` puts every skill in front of the model at once and records
which one it reaches for. Four properties keep it honest:

- **It installs the real skills**, copying each one into a throwaway project's
  `.claude/skills/` (or outside the project, "Layouts" below), so they reach the
  model the way installed skills do and carry the descriptions that actually
  ship. Nothing is duplicated here.
- **Registration is the production surface.** The first version registered each
  skill as a project *command* instead, which put a caveat under every number it
  produced: commands are addressed to the model as things the user invokes, so
  "the harness under-reports" was always available as the competing explanation
  for a low score. Installing the real skills retires it.
- **A prompt that claims an attachment gets one.** Cases whose text says a JD or
  CV is attached carry the document in the case, and the runner writes it into the
  throwaway project before sending the prompt. A fixture claiming a file should
  have one — but be clear about what this bought. It was introduced on the theory
  that the missing files explained a large gap (attachment-claiming cases reached
  a skill on 22% of runs against 55% for self-contained prose), and re-running the
  affected cases afterwards moved the number not at all: 22% before, 22% after,
  every case identical. The correlation was real and the explanation was wrong.
  Keep it for honesty of the fixture, not for the score. Each case now runs in a
  project of its own holding only its own files: the runner used to write every
  case's documents into one shared project, on the assumption that their names
  were distinct, and five cases attach a `jd.txt`, so in a run of several cases
  each was shown the last one's posting — the "after" measurement among them.
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
python evals/run_routing.py --cases evals/routing-arm-b.json  # another case file
```

`--cases` runs another file of the suite's shape in place of
`suite-routing.json`; without it the suite runs as before, each case in its own
project (above). A `--case` id the file lacks is an error. Every run ends with
its reach rate — the share of decided runs that reached any skill — and the
number that reached a skill other than a named-route case's own. In the
Tuesday arm a second line counts the runs in which the hub fired, read from
each run's `hub_fired`, so a run that routed and then reached a hidden module
counts. An explicit case (E2, below) is not a routing case and is left out of
both: its runs end with an `explicit:` line instead.

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

A case carries every document its message names. Cases 4 and 16 did not: case 4
ended on a placeholder where its posting should be, and case 16 promised a
pasted posting and a resume below it and held neither. A run that asked for the
missing material was answering correctly and scored as a miss, so neither case
measured routing. Each now carries what it names, pasted into the message: case
4 a short posting in place of the placeholder, case 16 the posting and the
bullets after its last sentence. Each intent sentence is unchanged word for
word; case 4 loses only its `[link]` placeholder, which the posting replaces, and
case 16 keeps its bracketed marker, which `routing_variants.py` keeps as the
suite wrote it. Results for those two cases
from before the change measured a different prompt and do not compare with
results after it.

### The attachment diagnostic

The six cases that claim attached files (suite ids 3, 9, 15, 17, 18, 21) reach a
skill far less often than self-contained prose, and materialising the files did
not move them (above; the root README's Tracked-work ledger holds the finding).
The hypothesis under test: routing is decided from the message text before any
file is opened, and those are the cases whose message carries no domain content.
It is tested as a 2×2, fixed before running:

| Arm | Cases | Message | Prediction if the hypothesis holds |
|---|---|---|---|
| A | the six attachment cases, as they are | intent; the documents attached | baseline |
| B | the same six (`routing-arm-b.json`) | the documents also pasted in; still attached | rises toward D |
| C | positives 1, 2, 4, 5, 6, 7, 8, 10, 16 (`routing-arm-c.json`) | domain content moved into an attached file, intent left, after one fixed sentence claiming the file | falls toward A |
| D | those nine, as they are | self-contained | baseline |

Every arm runs on one pinned model, five runs per case.
`routing_variants.py` writes arms B and C from the suite and says, case by case,
which words of each message are its intent, keeping in each the event or
document it is about, as every arm-A message does; its files are regenerated, never
edited, and `check_skills.py --only evals` fails one that differs from what the
script writes. A variant's id is its arm's offset plus the suite id
(`derived_from` records it): 2xx in B, 3xx in C. Case 8's message is all intent,
with no domain content to move, so it runs unchanged in C, identical to D.
Every other C message opens with "Details are in the attached file.", the only
text the variants add: every arm-A message claims its files, and without a claim
nothing in the message points at the file. It is a second difference between C
and D, so D − C measures the claim and the content's removal together. The
control that would separate them, a fifth arm of D's message plus that sentence
and a file holding the same text, is not part of the 2×2.

```bash
M=<one pinned model id>
python evals/run_routing.py --model $M --runs 5 --json-out arm-a.json \
  --case 3 --case 9 --case 15 --case 17 --case 18 --case 21
python evals/run_routing.py --model $M --runs 5 --json-out arm-b.json --cases evals/routing-arm-b.json
python evals/run_routing.py --model $M --runs 5 --json-out arm-c.json --cases evals/routing-arm-c.json
python evals/run_routing.py --model $M --runs 5 --json-out arm-d.json \
  --case 1 --case 2 --case 4 --case 5 --case 6 --case 7 --case 8 --case 10 --case 16
```

Report the reach rate per arm and per case, and the wrong-skill count, which
must stay 0. **The decision rule:** if B − A ≥ 20 points and D − C ≥ 20 points,
the hypothesis holds, the README finding is updated with the mechanism, and the
fix — description wording that names the attached-files case, or one skill that
routes to the modules, as Tuesday now does — goes back to the owner as a decision. If either difference falls
short, the hypothesis is recorded as falsified, as the last one was.

### The Tuesday arm

Tuesday is one skill, `tuesday`, that routes each request to one module
and runs it from a copy of that module's instructions. It ships at
`skills/tuesday/`, and how its `references/` are generated is stated in its
README ("How references/ is made"). Rounds 1 to 3 measured it as a prototype
kept in `evals/arms/frontdoor/`; that hub is now `skills/tuesday/SKILL.md`, byte
for byte, and the folder is gone. The measurement compares it with the three
skills as they ship, so the harness has two arms. `--arm skills`, the default,
installs the three modules as before, and never Tuesday. `--arm
tuesday` installs `skills/tuesday/` as it ships, its SKILL.md, `references/`
and LICENSE without its README (`HUB_SHIPS` in `ci/sync.py`), and the three modules, each
module copy with `disable-model-invocation: true` added to its frontmatter and
nothing else changed (`hide` in `ci/sync.py`, the transform the Claude Code
builds make), so a module keeps its slash command and leaves the listing. That
key is Claude Code's alone and a claude.ai upload refuses it, which is why it is
never in `skills/`. The arm refuses a working tree whose Tuesday references
are out of date with the modules; `python ci/sync.py` regenerates them.

What a Tuesday run is scored on is the playbook read first after `tuesday`
fires, unless a hidden module was reached anywhere in the turn. Its labels:

| Label | Meaning |
|---|---|
| `<module>` | that module's playbook was read first after the hub fired, and no hidden module was reached |
| `tuesday-unrouted` | the hub fired and the run ended with no playbook read: a miss |
| `hidden-<module>` | a hidden module was called, by its installed name or its shipped one, or a tool call named its folder, at any point in the turn |
| `neither` | nothing fired |
| `timeout`, `error` | no verdict reached; set aside, as in the skills arm |
| `void` | the run could see a Tuesday skill it did not install; set aside |

A Tuesday run is read to its end. It used to stop at the routing decision,
the first playbook read; round 2's diagnosis found the hidden module reached
after it — a Bash call into the hidden module's own `references/` — in a run
that reader scored as a clean route. So a run routed right that later reaches a
hidden module is `hidden-<module>`, and a run cut off by the timeout after
routing is set aside, since the rest of the turn is where that reach would be.
Each record also carries `hub_fired` and `reached`, every playbook and hidden
module the run reached in order, so a run that read a second playbook shows it.
A tool call's input is what is read: a listing whose output prints a hidden
module's paths reaches nothing. A playbook is recognised by its whole file name
in a call that also names the hub's folder anywhere: its full path, or a path
relative to the hub's folder after a `cd` into it in the same call, such as
`cd <hub>/references && cat <module>.md` or `cd <hub> && cat references/<module>.md`.
Until round 2's measurement only the full path counted, a rule stated here before
it ran; that measurement scored two runs `tuesday-unrouted` that had read the right
playbook those ways and done its job, and the rule was changed after it. No module
ships a file of a playbook's name, so a file of that name in a call that does not
name the hub's folder is no route.
Every run records the skill list from the CLI's init event, in both arms. A list
that shows a Tuesday skill this run did not install, such as a copy synced from
claude.ai or another run's copy, voids the run, because that copy could take the
fire meant for this one.

**Explicit focus (sub-arm E2).** `suite-explicit.json` holds prompts that open
with a module's slash command, each reading like another module's job, or like
nothing in particular. The runner suffixes every installed skill with the run's
id, so it rewrites each prompt's command to the installed name, `/mock-interview`
to `/mock-interview-<run id>`, before sending it. The rest of the prompt is sent
as written. An E2 run is read to its end, because what the case tests is what
happens after the module loads. Its outcome:

| Label | Meaning |
|---|---|
| `focused` | the named module loaded and no other module was reached: the pass |
| `hidden-<module>` | another module was the first reached: called by any name (refused or not), or its folder named in a tool call |
| `<module>` | another module's playbook was the first reached: its file name, `<module>.md`, in a tool call, through the hub's path or a Bash `cat` |
| `unconfirmed` | no other module was reached, and nothing showed the command loaded: not a pass |
| `timeout`, `error`, `void` | set aside |

The hub firing is not an outcome. Round 2's diagnosis found that it fires in
E2 because the model uses it as a router after the command loads, and that in
every such run it deferred to the named module and read no other playbook; a
run that defers is `focused`, and one that routes on is scored on the playbook
it reads. Hub fires are counted and reported apart (`hub_fired` on each run,
and the `explicit` summary), never scored. Each E2 record also carries
`loaded`, whether the named module loaded, and `reached`, every other module
reached in order. The module loaded if its own files were opened or the CLI
expanded the command. The CLI's stream does not carry that expansion, so the
runner reads it from the session's transcript, following the run's own reply
back to the command, since runs of one case can share a transcript file. An E2
case's `expected` names the module its command starts; the case passes when
every run is `focused`. A run cut off by the timeout is set aside even after
the module loaded, because the rest of the turn is what the case tests and the
cut-off never showed it. A module's whole run outlasts the 240 seconds a
skills-arm routing run gets, so a run read to the end of its turn — every
Tuesday run and every explicit case — gets 900 unless `--timeout` says
otherwise, and each case's result records the seconds it had. The default
follows the reader because a flag can be left off: round 2's measurement ran its
Tuesday arm at 240, and six mock-interview runs on Sonnet and Opus that had
routed right were cut off while writing the pack and set aside. The init event's
slash-command list is recorded with each E2 run.

One run of the measurement, per model (`claude-haiku-5-5`, `claude-sonnet-5-5`,
`claude-opus-5-5`):

```bash
M=claude-sonnet-5-5
python evals/run_routing.py --arm skills --model $M --runs 5 --json-out e0-$M.json
python evals/run_routing.py --arm tuesday --model $M --runs 5 --json-out e1-$M.json
python evals/run_routing.py --arm tuesday --model $M --runs 5 --json-out e2-$M.json \
  --cases evals/suite-explicit.json
```

A Tuesday results file also records the hub's hash and one hash over the hub
and every generated file, so a result names the exact text it measured. Every
results file records:

- `cases_sha256`, the sha256 of the case file's bytes as the arm loaded them,
  before its first run;
- `case_ids`, the `--case` ids it ran, or `null` for the whole case file;
- `modules_sha256`, one sha256 over the three module skills as an install copies
  them, the skills arm's only digest of its payload;
- `harness_sha256`, one sha256 over the runner's own code: `evals/run_routing.py`,
  `evals/child_env.py` and `ci/sync.py`;
- `skill_md`, the sha256 of each SKILL.md that `--skill-md` put in place of a
  module's, by module (`{}` when none).

A run never writes over a results file: it refuses an existing `--json-out`
before it starts, and if something else writes that file during the arm, the
run keeps it and writes its results beside it, `<stem>.<run id>.json`, with a
warning.

Each of these commands is one step of the measurement, and the runner never
reads the account's usage meter. Recording the meter delta is the step's run-log
job: read the weekly meter before and after the step, and write both readings and
their difference in the step's run log beside the results file the step wrote.
The runner's own cost figure is each run's `cost_usd`, an API-price-equivalent
estimate from the CLI's result events, not meter points; `spend.md` says how the
two differ. A run records it only outside the project layout ("Layouts" below),
so these project-layout commands record no cost, and their step's meter delta is
its only cost record.

An arm with more than 10% of its runs set aside is re-run, and void runs count
toward that share with timeouts and errors. The runner prints a warning, records
the reason as `unscored` in the results file, and exits `3` when it is over: a
host whose init list carries a synced Tuesday skill voids every run in both arms,
and an arm scored on what survived would read its empty `hidden` and wrong-skill
counts as gates met. Before measuring, run one case and check that the recorded
`init_skills` hold only this run's names.

### Layouts

`--layout` says where a run's skills are installed, in either arm. Every run's
session starts in its case's own folder. Outside the project layout that folder
holds the case's documents and nothing else.

| Layout | Where the skills are | What it simulates |
|---|---|---|
| `project`, the default | the case folder's `.claude/skills/` | a project install, the layout of every measurement before round 3 |
| `personal` | `skills/` in a config folder of the run's own, `config/case-<id>-<n>/` for the case's run `n`, beside the case folder; the session starts with `CLAUDE_CONFIG_DIR` set to that folder | a personal install, outside the working folder |
| `plugin` | `skills/` in a plugin folder of the case's own, `plugins/case-<id>/`, beside the case folder, with the manifest in `.claude-plugin/plugin.json`; the session starts with `--plugin-dir` set to that folder | the Claude Code plugin, outside the working folder |

The plugin layout is for the Tuesday arm only. The runner refuses
`--arm skills --layout plugin`, because today's three skills do not ship as a
plugin.

Outside the project layout the session also starts with
`--allowedTools "Read(//<skills folder>/**)"`, which lets the Read tool open any
file in the run's skills folder. A skill opens its own files there: the hub its
playbooks, a module its references. Under `claude -p` the CLI refuses a read
outside the working folder that no rule allows. Round 3's review found every
such read refused without this rule, so no module could run its procedure. A
project install needs no rule, because its skills sit in the working folder.
The rule stands for a user who lets the skills read their own files when the
CLI asks. A read-only Bash command given the folder's path, such as `ls -R`,
runs under it too (round 3's re-check). A Bash `cd` into the folder is still
refused, because the CLI allows a `cd` only into a working folder.

The Tuesday arm installs the same files in every layout, with the folder and
frontmatter names the project layout gives them. The plugin is named as the hub
is installed, `tuesday-<run id>`, and the CLI lists each of its skills under
that name: the hub as `tuesday-<id>:tuesday-<id>`, a module as
`tuesday-<id>:mock-interview-<id>`. A module's id therefore contains the hub's
name. The reader counts the hub's name as the hub only where no colon follows
it, so a call by a module's plugin-qualified id is that module and never a hub
fire. The folders outside the case folder are named for the case and the run
alone, so no folder path the model meets carries the hub's name except the
hub's own folder.

In the plugin layout E2 types each command in the namespaced form a plugin's
skills take, `/tuesday-<id>:<module>-<id>`; the E2 paragraph above gives the
form the other layouts type. The CLI records a plugin command's expansion under
the namespaced command, whichever form was typed. E2 reads the transcript from
the config folder the run started with: the run's own in the personal layout,
the runner's in the others.

Each personal-layout run has a config folder of its own because the CLI writes
the session's transcript and settings there, beside the `skills/` folder whose
path it gives when the hub fires. In a folder shared by a case's runs, a later
run could read an earlier run's transcript. When a run ends, the runner copies
its transcripts into its own config folder's `projects/`, where the other
layouts' runs write theirs, so they outlast the temporary folder.

The void rule holds under a plugin prefix. A listed skill is read by its name
after the prefix, so another run's plugin, or a shipped `tuesday` plugin, listing
a Tuesday skill voids the run.

A config folder of the run's own replaces the runner's, so the personal layout
drops the host's own personal skills: on the host this harness was built on,
`session-start-hook`, which the other layouts list. Whether the CLI
authenticates under a fresh `CLAUDE_CONFIG_DIR` depends on the environment; it
did in the cloud container where round 3 was probed. Outside the project
layout, a run whose CLI exits non-zero before its result event is `error`, as a
run that fails to authenticate can be. In the project layout such a run is
settled from what its stream showed, as before round 3. An `error` run is set
aside, so an environment where authentication fails leaves the arm unscored.
Run the one-case check above in each layout before measuring it.

Outside the project layout each run records seven measures, reported and never
scored (`reported` in the results file). The run prints the first two as counts
over the arm's decided runs. It counts the decided runs read to their result
event (`result_read`) and those stopped before it (`stopped_before_result`). It
prints the refused tool calls over the runs read to their result event, and
output tokens, seconds and cost summed over those runs only, each with a median
a run, so a run stopped early never lowers a count, a total or a median. In
`reported` a total over no run is 0 and its median `null`, so read each total
with its count: `result_read`, `seconds_read`, `tokens_read` or `cost_read`.

- `hub_path_contact`, in the Tuesday arm: before any Skill call to the hub,
  a tool call named the hub's `SKILL.md` or a playbook,
  `references/<module>.md`, by a path into the hub's folder. In round 2 three
  of Haiku's four path contacts led to a hidden reach.
- `skills_root_named`: a tool call named a skills folder of the layout, the
  plugin's or a config folder's `skills/`, this run's or another's, ending there
  or at a glob. It is the step before a sibling reach. A path into one skill's
  folder does not name it, and neither does a path above it, such as
  `find .. -name SKILL.md`, so the count is a lower bound.
- `refused`: the tool calls the CLI refused for want of permission, by tool
  name, from the result event's `permission_denials`.
- `output_tokens`: from the result event's `usage`.
- `cost_usd`: the result event's `total_cost_usd`, an API-price-equivalent
  estimate (`spend.md`), not money spent and not meter points. It is read from
  the result event alone. A result event that gives no number there records
  `null`, and the run is left out of `cost_read`.
- `result_read`: whether the run was read to its result event. A record saved
  before this field existed is read from `refused`: a run with a refusal list,
  which only the result event gives, was read to it, and one without was not.
- `seconds`: the run's wall time, from its start to its outcome.

The two path measures read every word of a call's input as a path, with `.`
and `..` resolved: a relative path from the case folder, or from the folder a
`cd` earlier in the same command moved to. A skills-arm run is read only up to
its first fire, where a Tuesday run is read to the end of its turn. So a
skills-arm run's measures cover the calls before the fire, and its `seconds`
end there. A run that ended before its result event, a skills-arm run that
fired or a timed-out one, has no `refused` list, no `output_tokens` and no
`cost_usd` (`null`), never an empty or zero one. A skills-arm run stops at its
first fire, so that arm's tokens, seconds and cost cover none or few of its
runs, those that fired nothing, and do not compare with a Tuesday arm read to
the end of each turn. Whenever a decided run was stopped before its result
event, the run prints a second line saying how many, and that its figures do
not compare. With none read to the end, the refusals and measures read `none
read to their result event`, never zeros, and a measure that no run read to
the end recorded reads `none recorded`.

Every results file records its layout. The round 3 measurement, per model (its files
record the arm as `frontdoor` and its second digest as `frontdoor_sha256`, the names
before the code-name rename):

```bash
M=claude-sonnet-5-5
python evals/run_routing.py --arm skills --layout personal --model $M --runs 5 --json-out e0-$M.json
for L in plugin personal; do
  python evals/run_routing.py --arm tuesday --layout $L --model $M --runs 5 --json-out e1-$L-$M.json
  python evals/run_routing.py --arm tuesday --layout $L --model $M --runs 5 --json-out e2-$L-$M.json \
    --cases evals/suite-explicit.json
done
```

### Recovering a cut-short arm

Outside the project layout each run's record also carries the evidence a
recovery needs:

- `session_id`, from the run's init event. It finds the session's transcript in
  the CLI's `projects/` folder, where a personal-layout run's is copied (above).
- `init_sha256`, which names the run's init event in the results file's
  `init_events`. The file keeps each distinct init event once, without the keys
  that differ on every run: `session_id` and `uuid`, and the process's
  `startup_timing`, `scratchpad_path` and `messaging_socket_path`. Its tool,
  skill, plugin, agent, MCP-server and slash-command lists, its output style and
  the CLI's version are kept, and runs that started alike share one entry.
  `init_sha256` is the sha256 of that kept event as canonical JSON (keys sorted,
  `,` and `:` as separators with no spaces, UTF-8 with non-ASCII characters
  kept), so hashing the init line of a stream copy gives another value.

With `--json-out`, every byte of each run's stream that the runner read is
copied, as read, to `streams/<results file's stem>/case-<id>-<run>.jsonl` beside
the results file, which records that folder as `streams`. A skills-arm run's
copy holds the bytes read through the read that carried its first fire. A read
can carry events the runner never parsed, the result event and its cost among
them, while the run's record says `result_read` false and `cost_usd` null. A
Tuesday or explicit run's copy holds the whole turn. Each copy holds the whole
init event, and is flushed after every read: a runner stopped by a signal, as
the fix round's guard stops a step with SIGTERM, runs no clean-up, and its
copies still hold every byte it read.

A copy never writes over another, and is opened before the run's CLI starts. A
run whose streams folder already holds files is refused before it starts, as is
a run into an existing results file, so give each arm a results file of its own
name. A results file names its streams folder by the stem it was written under,
and keeps naming it when the file is renamed, as `<arm>.limit.json` is. So never
move a streams folder: name another `--json-out` instead. The project layout
keeps its run records as they were, with no measure and no evidence key, and
its streams are copied too.

An arm cut short by the account's usage limit is filled, not run again whole:

```bash
python evals/run_routing.py --merge e1.json --rerun e1.gap-1.json --json-out e1.merged.json
```

`--merge` runs nothing. It reads the arm's results file and each `--rerun` file,
which re-ran only the arm's killed and never-started runs on the same commit,
and writes the merged arm to `--json-out`, which must not exist. A merge never
writes over a file. It:

- replaces an `error` run, in its place, only when the run is proven killed:
  its `session_id`, shared with no other run of the arm, finds a transcript
  that holds the usage-limit message, in the CLI's transcript folder
  (`--projects`, by default the runner's config folder's `projects/`);
- fills a never-started slot, a case holding fewer runs than `runs_per_case`;
- needs, per case, exactly as many re-runs as kills and slots;
- refuses re-runs for a case with neither, for a case the arm does not hold,
  and for a case that also holds an `error` run not proven killed, its
  never-started slots included. A re-run carries no mark of the run it stands
  for, so beside such an error it may stand for that error. Beside a proven
  kill too, that is the mixed kill/error batch, where a killed run cannot be
  told from a real error. The refusal names why each error is unproven: it
  recorded no session id, another run shares its session id, no transcript was
  found, or its transcript holds no usage-limit message. An unproven error in a
  case offered no re-run is kept, and counts toward the set-aside share as any
  error does;
- refuses a re-run file whose arm, layout, model, `hub_sha256` or
  `tuesday_sha256` differs from the arm's;
- refuses one whose case file, `modules_sha256`, `harness_sha256` or `skill_md`
  differs from the arm's where both files record it (the case file by
  `cases_sha256`, else by name);
- refuses one that re-ran a case at another `timeout` than the arm's, or
  recorded another route for it, and one with a run whose session id another run
  of the merge has;
- refuses any digest that is not the measured commit's: this checkout's
  `hub_sha256`, `tuesday_sha256` and `modules_sha256`, or the two given with
  `--expect HUB TUESDAY`, the module digest then held across the files only;
  and the case file's sha256 as the file is now;
- confirms each file's cases against what it ran: the case file's ids for a
  whole-file run (`case_ids` `null`), else its `--case` ids, with no case
  listed twice. A file saved before `case_ids` is held only to cases its case
  file has, and `merged.cases_not_held` lists the case file's ids the merged
  arm does not hold, which the merge prints;
- recomputes `passed`, `reach`, `explicit`, `reported` and `unscored` with the
  runner's own functions, never edits them, and records under `merged` what it
  filled and whose sessions it replaced.

An arm that wrote no results file is refused with "no results: run the arm again
whole". A refusal exits `2` and writes nothing; otherwise a merge exits as a run
does. A file saved before the code-name rename merges under its old spellings:
`frontdoor` and `frontdoor_sha256` are read as `tuesday` and `tuesday_sha256` and
matched by value, and its own fields are kept as saved. A file saved before
runs recorded a session id cannot prove any of its `error` runs killed, and
neither can a project-layout run or a run whose init event was never read. So
`--merge` cannot redo round 3's merges, which matched a case's transcripts by
its run suffix; a saved file's never-started slots can still be filled.

## Clean-room fixtures

`run_fixtures.py` runs each skill's own `evals/evals.json` fixtures in a project
that contains only that skill — no repository, no spec, no conversation about
what the skill was meant to do — and grades the responses with graders that see
only the response, the expectations, and the harness's own record of what
research the run did.

A rule several fixtures of one skill grade — the accounting labels, say — is
written once, under the top-level `"clauses"` key of that skill's evals.json,
and an expectation or `expected_output` includes it as `{{name}}`. Everything
that reads a fixture (this runner, `ci/check_skills.py`, the self-tests) reads it
through `fixture_clauses.load_cases`, so a grader is shown the expanded text and
nothing else, and CI fails a reference to a clause the file does not define and
a clause nothing uses. `fixture_clauses.py` says why.

```bash
python evals/run_fixtures.py --out /tmp/clean-room --model claude-sonnet-5
python evals/run_fixtures.py --skill job-underwriter --eval 3 --out /tmp/cr
python evals/run_fixtures.py --out /tmp/cr --retry-runs 0    # one run, no retries
python evals/run_fixtures.py --out /tmp/cr --skip-execute    # grade saved, ungraded runs
python evals/run_fixtures.py --regrade-from /tmp/cr --out /tmp/cr2 --expectation 14
python evals/run_fixtures.py --skill job-underwriter --cases probe.json --out /tmp/p
```

**Runs are adaptive, and a failure is classified rather than counted.** Every
fixture runs once. A fixture that fails something — a grader verdict or a
deterministic check — runs twice more, and each failure is reported as
`deterministic` (failed every valid run), `intermittent` (at least one fully
graded run passed it) or `unresolved`. An expectation fails a run if *either*
grader fails it — the dissenting grader has found every defect worth fixing in
this suite so far, and requiring both would discard exactly that. It passes a
run only when *every* grader returned a valid PASS. A run where one grader
returned nothing for it, and no grader failed it, is partially graded and does
not pass it: the expectation is then intermittent if another run failed it and a
fully graded run passed it, and unresolved otherwise, never clean. The old
summary used every run as its denominator and counted only explicit failures, so
a grader that skipped an expectation turned a deterministic failure into an
intermittent one.

The distinction is the point. One fixture here has scored 12/12, 13/13, 13/13
and 9/13 on the same skill; a single run cannot tell that from a defect, and
chasing it as a defect means rewriting a rule that already worked. Running
*everything* three times was the obvious alternative and is worse: it triples
the cost of the expensive half — executions generate 20k–36k character packs —
to learn nothing about fixtures that were already clean, and it raises
confidence in a wrong expectation exactly as fast as in a right one. Seven
expectations in this suite turned out to be testing the environment rather than
the skill; three runs each would have made every one of them look more real.

An intermittent failure is a reliability finding, not a defect to patch. The
rule fired once and not another time, so rewriting it is as likely to move the
number by luck as by fixing anything — the useful responses are to make the
requirement structural, or to record the rate.

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
  sentence reasoning its way to PASS. Those rules are now in the grader prompt,
  which asks for the reason before the verdict so the verdict has to follow it.

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

### Rooms are isolated and pinned

"Only that skill installed" was not true until the rooms were checked. A default
`claude -p` loads the host's own skills — 46 on the machine these sets ran on,
one of them a host skill named mock-interview — and the old runner counted any
Skill call as a fire. Every historical room turned out to have fired the
installed skill, so no past number is contaminated, but nothing would have
noticed the first one that did not. Rooms now run with `--setting-sources
project`, which leaves no competing skill; a fire counts only when the Skill
call names the installed skill (another skill firing is `wrong_skill`); and the
stream's init event — CLI version, model, tools, MCP servers, loaded skills and
any that share the installed skill's name — is saved in the run's meta.json.

`--model` pins the rooms. The host's default model changed between measured sets,
and an unpinned comparison measures that change along with whatever else moved.
The init event records the model that actually ran either way.

A run that does not fire the installed skill is re-run with the skill named, in a
**new room**. Reusing the room credited the first attempt's files and searches to
the response being graded. Both attempts are recorded in meta.json; only the
graded one's files, research and checks count. A run that never fires the
installed skill is harness-invalid: it is not this skill's output.

### What a run keeps

Every attempt, the first and the nudged, keeps the evidence a recovery or a
re-check reads, in `--out`, beside its response:

- **Its whole stream.** The CLI's stdout goes straight to
  `streams/<room>.inflight.jsonl` as it is written, renamed to `.jsonl` when the
  run answered, or to `.partial.jsonl` on a timeout or a decline, whose stream is
  kept too. A runner stopped mid-run leaves the `.inflight.jsonl` on disk. The
  invocation records `stream` and `stream_sha256`.
- **Its init event, once.** `init/<init_sha256>.json` holds each distinct init
  event without the keys that differ on every run, as a routing results file's
  `init_events` does ("Recovering a cut-short arm"), so runs that started alike
  share one file; the stream holds the whole event. The invocation records
  `init_sha256` and `session_id`.
- **Every file it left.** Each file in the room and its scratchpad, of any suffix,
  the install alone skipped and symbolic links not followed, is copied whole to
  `files/<room>/<base>/<path>`, `<base>` being `room` or `scratchpad`
  (`scratchpad-2` and on for a further one), and listed in the invocation's
  `files` with its size, sha256 and copy. A file over
  20,000,000 bytes (`run_fixtures.MAX_COPY`) is listed and not copied, marked
  `truncated`. The graders' view of a run's files (`collect_artifacts`) is
  unchanged. An attempt cut mid-run is marked `partial_evidence`: its stream and
  files are as far as it got.
- **How it ended.** `limit_hit`, whether the usage-limit message was in a
  declined attempt's reply or stderr; for a decline, its exit code
  (`returncode`) and the first 1,000 characters of its stderr (`stderr_head`);
  in the plugin layout, `names`, the names it installed; and through Tuesday,
  `hidden_reached` ("Through Tuesday").
- **An in-flight record.** `inflight/<room>.json` exists while the attempt runs
  and is removed once the run's meta is written, so one left behind marks a run
  a restart or the owner's guard ended ("Regrading a saved set", killed runs).

The meta also records the pass that ran it (`pass_id`, below) and
`declared_watch_out`, the watch-out line the installed payload declares, with its
sha256 and the file it was read from (the watch-out check, under "Deterministic
checks"). A stream, a snapshot or a move into `killed/` never overwrites: a name
already taken gets `~<pass id>` after its stem, then a count.

**What a run sends is unchanged.** The CLI gets the prompt on stdin, and both of
its pipes are drained together, so a CLI that writes more than a pipe holds to
stderr cannot stall. On a timeout it is killed and reaped before the timeout is
recorded, so a timed-out run spends and writes nothing more; it stays in the
runner's process group, so a guard that stops the group stops it too. A fixture
run's argv, stdin, working folder and environment are byte for byte what they
were before the streams were kept (`test_launcher_golden_argv`).

**A run that answered is not a decline.** A run that exits 0 with a result event
that is no error answered, however short its reply and whatever it mentions: a
drill question about a missed quota, a rate-limit problem or an API's usage
limit is an answer. A run is declined when it exits non-zero, ends with no result
event or an error result, or replies with the usage-limit message as the whole
reply ("You've hit your session limit · resets 7am (UTC)",
`run_fixtures.LIMIT_MESSAGE`, anchored), so the 48-character limit message is
never graded as a response. Whether a decline, a timeout or a kill was the usage
limit (`limit_hit`, a kill recovered rather than set aside) is read only where
the CLI writes that message (`run_fixtures.limit_line`): stderr, stdout lines
that are not JSON, the result event's text when the result is an error or the
text is short, and the last assistant text when it is under 200 characters. A
reply's prose is never read for it, so a long pack, or a partial one cut by a
timeout, that names a usage limit is no kill. A meta saved before invocations
recorded `limit_hit` is still read by its error text, as the fix round read it.
The decline words a grader's reply is read for are unchanged.

**Passes.** Every invocation that runs or grades writes
`passes/<pass id>.json`, the id `<UTC time>-<pid>`: its argv, host, uid, CLI and
Python versions, the checkout's HEAD and count of changed files (read without
writing the index), `inventory` (the sha256 of every `evals/*.py`,
`ci/ledger_rules.py`, `ci/sync.py` and `ci/package.py`), `digests` (the hub's
two digests and each module's tree as an install copies it), `settings` (the
model, grader model, via, layout, graders, timeout, retry runs and each case
file's sha256), and when it started and finished. Every meta and grade names its
`pass_id`, so each grade says which invocation made it. A pass that differs from
an earlier pass into the same `--out` in its inventory, its digests or any
setting is not the same measurement: it is refused before any call, writes
nothing and exits `3`. A CLI version other than the folder's first pass's, or the
frozen record's, is recorded and never refused, with a note "preflight required"
unless `--expect` lists that version under `preflight`. `--expect FILE` takes a
frozen pass record, or any JSON holding `digests`, `inventory` and `settings`,
and refuses any difference from what it holds; it also refuses a `--retry-runs`
other than 0, since a retry pass adds runs to fixed cells. So a recovery pass into
a folder, `--stems` with or without `--skip-execute`, carries the flags of the
passes it completes.

```bash
python evals/run_fixtures.py --out /tmp/cr --retry-runs 0 --expect frozen-pass.json
```

### Through Tuesday

`--via tuesday` runs each module's fixtures with Tuesday installed as
the Claude Code plugin ships it, instead of the module alone. It is for a
non-inferiority check: a module run through Tuesday should do as well on
its own fixtures as the module alone, since its text is the same.

```bash
python evals/run_fixtures.py --via tuesday --out /tmp/fd --model claude-sonnet-5-5
python evals/run_fixtures.py --layout plugin --out /tmp/alone --model claude-sonnet-5-5
```

The room holds nothing. Tuesday and the three hidden modules sit in a
plugin folder beside the room, installed by the routing arm's own plugin layout
(`run_routing.install_plugin`, "Layouts" above), and the run starts with
`--plugin-dir` set to it and the routing arm's rule that lets Read open its
skills folder, joined to the room's own `--allowedTools` list. The room is named
for the case and the run alone, never for the module, because the hub's folder
path reaches the model and a module's name in it would point the route.

**A run may save inside its room**, in both arms (the owner's decision). The same
list gains one allow rule, `Edit(//<room>/**)`, and a second naming the room's
resolved path when the room is reached through a symlink
(`run_fixtures.save_rules`). It models a user who answers the save prompt with
"allow edits in this folder". It is a rule rather than a permission mode,
because a mode is session-wide and can approve some shell commands. It reaches the
room alone: the plugin folder beside it stays unwritable, and a save aimed anywhere
else is still refused and recorded. The project layout, the graders and the routing
runs get no save rule. Before it, a plugin room refused the model's first save, and
some mock-interview runs then delivered their pack only in chat.

A fire counts only when the run read that module's playbook through the hub and
reached no hidden module, read by the routing arm's own reader (`RunReader`,
Tuesday arm), so a fire here is a route there. A run that did anything else is
labelled as that reader labels it — another module, `hidden-<module>`,
`tuesday-unrouted`, `neither`, `void` — and is nudged once, in a new room, with
the hub named by its plugin id; a run that still does not route is
harness-invalid.

**Every hidden-module reach is counted, before any run is left out (E16).** The
reader that decides the fire stops at its first outcome, and settles `void` at
the init event, so a reach after either went unread. Each invocation through
Tuesday also records `hidden_reached`: the `hidden-<module>` labels of a second
routing reader of the Tuesday arm, fed every event of the stream whatever it
decided on the way. The summary prints the pool over every invocation in
`--out` and `killed/` — first, nudged, timed out, declined, void and killed
alike — each read again from its saved stream, as `hidden-module reaches: N across
M Tuesday attempt(s) (initial, nudged and incomplete included)`, then each reach
by stem and attempt (`run_fixtures.hidden_reaches`). An invocation with no saved
stream counts its recorded `hidden_reached`, or is listed as unread. A run saved
before the code-name rename, whose meta says `frontdoor`, is read too.

**A comparison through Tuesday installs the module alone with `--layout
plugin`.** That installs it exactly as Tuesday is installed: a plugin of the
room's own beside the room, holding that one module, visible, named as the
module is installed (`mock-interview-<run id>`, so the CLI lists it as
`mock-interview-<id>:mock-interview-<id>`), with the same read rule and the same
neutral room name, `case-<id>-<mode>-<run id>`. The two arms then differ only in
what the plugin holds. Both installs are `run_routing.install_plugin`, one
definition, and a Skill call by the plugin-qualified id or by the name alone,
either after one `/`, fires: the fixture runner reads a skill's name as the
routing reader does (`run_routing.local_name`). `--layout project`, the default with `--via skill`, is the install every
measurement before this one used for the module alone: the room's own
`.claude/skills/`, a room named for the module, and no plugin or read rule. It
stays, because the ledger's earlier baselines were measured with it. The quality
check through Tuesday ran its alone arm that way, so its two arms differed
in install, read rule and room name as well as in Tuesday.

Every run's meta.json records `via`, `layout`, `room_writable` (whether its flags
carried the save rule, recorded on each invocation too), and, reported and never scored,
`refused`, the graded invocation's tool calls the CLI refused for want of
permission, counted by tool, and `save_refused`, whether a save (Write, Edit,
MultiEdit or NotebookEdit) was among them (`run_fixtures.refusals`). A run that ended before its result event
has both `null`, never an empty count.

`--via tuesday` has run, as `--via frontdoor`, its name then: the quality check
through Tuesday ran it on three models, 115 runs each, 345 in all, beside 345
runs of the modules alone, and set none aside, so `--plugin-dir` works beside
the rooms' `--setting-sources project`. The bar each step was held to was fixed
by the owner before it ran.

### Dates relative to the run

A fixture whose test turns on how old something is when a run reads it writes
those dates relative to the run, as `{{date<offsets>:<form>}}`: offsets in days,
months or years applied in the order written (`+9d`, `-4m`, `-4m+2y`), then one of
four forms, `day month year`, `day month`, `month year` or `year`. So
`{{date:day month year}}` is the run's own date, and `{{date-4m:month year}}` is
the month four months before it. `fixture_clauses.dated` writes every one out,
in every string of the case — the prompt, the research pages, `candidate_text`,
the expectations — for the run's date, which the meta records as `run_date`. A
run is graded and checked against the text its own date wrote, and a grade file
hashes each expectation as the fixture writes it, its dates unwritten, so a
verdict on it is one question on every run date (`evals/recurring.py` keys
verdicts by that hash). mock-interview
eval 8 is why: its material was "copied this morning (12 October 2026)", its
interviews were "on 21 October" and its strategy brief was from June, so every
run after 21 October was shown interviews already past and a brief ageing past the
research checklist's "under ~6 months". It now always reads a brief about four
months old and interviews nine days ahead. Eval 7's news page, which a strategy
target's `yes` rests on, is written about two months old for the same rule.

A fixture with relative dates declares `date_anchor`, an ISO date: the run date
at which its references write out exactly the text it held before, which the
runs saved before `run_date` existed were sent. A run with no `run_date` is
graded and checked at the anchor, so a regrade of a saved set shows graders the
request its runs answered. CI's evals group reads each fixture at its anchor and
fails relative dates with no anchor, an anchor with none, and a reference the
pattern cannot read; the other groups read fixtures at their anchors too.

### Research rooms: denied and canned

Every research expectation in this suite used to be graded from rooms where
search was present and refused, so `unavailable` was the only label a run could
earn truthfully and `yes` and `skipped` were never measured at all. A fixture now
declares its research in an optional `research` block; a fixture without one runs
denied, as every fixture always has.

- `modes`; `budget`, the tier and its search and fetch caps; `entity_tokens`,
  the words that never score; and `zero_calls` where the inputs answer every
  target, so no research call should be sent.
- `targets`, each with its number, the query `terms` that aim a call at it, and
  the labels it `accept`s, for every mode or per mode. A term is a phrase, or a
  list of phrases that must all appear
  (`["careers", "member experience lead"]`), for a word too generic to stand
  alone ("market", "requirements"). A call is aimed at a target when its query,
  or its URL with the query string decoded, carries one of the terms, it fetched
  a page tagged with the target, or in a canned room the server returned such a
  page (`output_checks.aimed_at`). The company's name cannot be a term, since
  every query carries it, so the target that owns the sweep of the company
  itself (job-underwriter's target 1, mock-interview's target 3) declares
  `identity`, the company's distinctive name tokens (never `entity_tokens`,
  which hold generic words): a search aims there when it carries the name, every
  other word but a function word is one the request uses (the prompt, and the
  page at any declared user link the run read), and it carries no other
  target's term (`output_checks.identity_search`). `stray_samples` are
  queries a run might send that serve no target ("Brindlemoor layoffs
  glassdoor"); CI fails one that any target's terms or identity claim, and an
  `identity` no stray sample tests. Each target also lists `on_target_samples`,
  queries a correct run might send for it, and a target that accepts `n/a` or
  `skipped` lists `hunt_samples`, queries that really are hunts for it. CI
  checks the terms against both with `aimed_at` itself, in every mode the
  fixture runs, a canned room's sample read as the log entry the stub server's
  own page route (`research_server.search`) would leave; where no correct run
  sends a call (`zero_calls` or `declined`), it skips the cross-target collision
  check but for a quick check's samples (`quick_check`, below).
- `quick_check`, where the user's pasted material fixes some targets and a run may
  check that it is still current and genuine (the owner's decision): `targets`, the
  targets that material fixes, and `names`, the names it carries
  (`["pellucid", "datawright"]`), one of which each call's query or decoded
  address must carry. job-underwriter eval 5 and mock-interview evals 7 and 8
  declare one, and `CONTRIBUTING.md` says what CI holds it to.
- `user_links`: the links the user gave the skill to read (absent means none).
  A URL the prompt names only as the source of text the user pasted is not one.
  In a canned room each has its page in `user_pages` (`url`, `title`, `text`),
  which the room serves by fetch alone and no search returns, so reading it stays
  an input and is never charged to a target. Without one the room would answer
  "No page at …", which returns, and the run would be credited with a read of a
  page it never saw, so CI fails a canned user link with no page, and a page that
  is no declared link. A user page may carry a `canary`, under the rule below:
  CI fails one its page lacks, or one the prompt or any other page also carries,
  since its appearing would then prove nothing about the read. job-underwriter
  eval 6 is the fixture that declares one.
- `declined`: `true` when the user's prompt declines research or chooses L0
  (absent means false). It is the fixture's word, never inferred from the run.
  With it, `declined_phrase` quotes the prompt's own words that decline research
  or choose L0; CI fails a `declined` that is not a boolean, one set beside
  `zero_calls`, one with no phrase or a phrase not in the prompt, and a phrase
  without `declined: true`.
- For canned rooms, `pages` (each with its `url`, `target`, `keywords` and text)
  and `canaries`: a fact only one page carries, the spellings that prove it was
  read, its `target`, and the `page` it sits on, which must be one of the
  fixture's pages for that target.

**What a canary may be.** A canary is a token a correct response carries over
whole: a figure ("143"), a proper name ("Pricewell") or a published title
("Small Books, Loud Errors"). Its spellings are such tokens from its page, or
one of them written another way a correct response writes it (a figure rounded),
and any one of them counts; never a paraphrase.
It is never a common-noun phrase a response may restate ("four days a week in the
Leeds office"): a correct run can say that in more ways than any list of exact
strings holds, so a fact that exists only as such a phrase is left to the
fixture's graded expectation, which judges meaning. This is the one statement of
the rule; `CONTRIBUTING.md` points here.

A fixture with the `quotes` or `traces` check also declares `candidate_text`, top-level: the
candidate's own words, against which the verbatim evidence column, the banks'
Provenance and resume-tailor's Traces to cells are checked (`[]` when the
candidate gave nothing quotable). A
fixture with the `fit_ledger` check declares `candidate_constraints`, top-level:
`"known"` when the prompt states the candidate's own constraints or
non-negotiables, `"unknown"` when it does not. It is the only source of that fact
for a fixture's run: a fit_ledger fixture without it, or with any other value,
fails the run as a `fixture` error, and the response's own envelope never stands
in for it.

- **denied** is the historical condition, now pinned: `--setting-sources project
  --strict-mcp-config`, with WebSearch and WebFetch present and refused. Never
  `--disallowedTools` here — refused, not absent, is what the historical data
  measured. A search that returns anything, or any MCP server in the room, makes
  the run harness-invalid as a mode mismatch, because a user setting could
  otherwise turn a denied room live without a trace.
- **canned** serves the fixture's own pages, and the pages at its user links,
  through `research_server.py`, a stdlib MCP server with deterministic search
  and fetch, and removes the built-in web tools so the only search the skill can
  reach is the fixture's. Pages score
  on their own keywords with the company's name removed, so the name alone
  surfaces nothing and what a call returned says what it was aimed at; the
  prototype scored on page text, and a run that searched only the company's name
  "found" its interview process. A miss is an ordinary answer, never "failed",
  which a run could fairly have read as a refusal.

The server's corpus, its config and its call log live under `<out>/research/`, a
set per invocation, never in the room or its scratchpad: anything there is
collected as a file the response produced and graded as research the skill did.
The server writes only to the log it is given. A canned room is harness-invalid
when the server is missing or not connected, its tools are not offered, the
built-in web tools are, its log has no initialize line, or it answered with an
error. A canned room that connected and offered search but saw no call is a
**valid** room — not searching is something the skill did, and the checks judge
it.

### What the graders see, and what they run with

Graders used to run as default sessions — web search, a shell, every host skill
— able to go and check a research claim themselves, with nothing recording which
model graded. They now run with `--tools ""`, `--strict-mcp-config`,
`--disable-slash-commands` and `--setting-sources project`, the prompt on stdin
and the reply read from the JSON result. `--grader-model` pins them and defaults
to `--model`. Every grade file records the model that answered, the CLI version,
the flags, the sha256 of each expectation it graded, the grader prompt's
version and the sha256 of its text (`grader_prompt_sha256`), and the pass that
made it, so a later set can be compared like with like.

The response sits between two lines the prompt names, `===== RESPONSE BEGINS
=====` and `===== RESPONSE ENDS =====`, and the prompt says once that nothing
outside them is text the response wrote. The harness's record follows the end
line. Version 2 of the prompt put the record straight after the response with
nothing marking where the response ended, and graders read it as the response's
own closing text: most closing-expectation failures in the quality check through Tuesday cited it. The
fence is prompt version 3; a grade file records its version, and grades saved
under version 2 keep it.

The grader prompt states the room's actual research mode and carries a block
headed "What the harness observed", in one of three states: not recorded for
this run (do not infer whether research was attempted, and do not grade research
counts); recorded, no calls made; or the calls themselves, each with its tool,
query or URL, and whether it returned (a search with the URLs it returned), was
refused or errored. A fetch of a
link the fixture declares in `research.user_links` is listed in a group of its
own, out of the research count, because the tally line names it apart: the reads
that returned under "User links read", and those the host refused or that errored
under "User links not opened", which are not reads and are not counted. The block
sorts calls with `output_checks.user_link_reads`, the classifier the checks use,
so a grader and the checks compare the tally with the same numbers. Graders had been
failing true claims of refused searches because nothing told them the searches
happened.
The block is ground truth for the response's claims about its own research and
never a source of content the response lacks.

Replies put the reason before the verdict. An expectation listed in a fixture's
`enumerate` also asks for every site it covers, before the reason, each marked
traced, slot or untraced, and the summary prints the untraced count per run per
grader. A reply that covers fewer expectations than it was given is recorded as
incomplete on the grade file and re-asked once for just the gaps; whatever is
still missing stays recorded as missing, never as a failure.

### Deterministic checks

Some of what graders were asked to judge has a fixed form in the skills, and a
fixed form can be read exactly. `output_checks.py` does so and writes
`{stem}.checks.json` beside each response:

- **Accounting**, for any fixture with a `research` block, judges the rule in
  `conventions/interaction-grammar.md` §4 and nothing stricter. It reads the
  tally line and the accounting table, each row by its leading number. The tally
  line's fixed form is read as the line's prefix, ending at the end of the line,
  "(", ";", "." or a spaced dash, so a reason after it does not hide the counts;
  a remark there that restates the line — "attempted", a number of its own,
  "both", or a second user-links clause — fails `tally_remark`, a format check,
  and any other remark is noted. Each declared target needs its row, a label
  from the vocabulary, and a label the fixture accepts in this mode. Against the
  record of calls: a `yes` needs a call aimed at the target that returned (an
  error returns nothing); `skipped` and `n/a` need no call aimed at it, refused
  ones included; in a canned room `unavailable` needs at least one aimed call,
  every one refused or errored — or no call aimed at it, the fixture's whole
  declared search budget sent, and every search aimed at a lower-numbered
  target, which also satisfies the accept list. Where the fixture declares
  `research.declined`, `unavailable` with no call aimed at the target is lawful
  in any room and also satisfies the accept list; the tally must read
  `L0 — no searches` (`tally_l0`), and `zero_calls` applies. Of
  interaction-grammar.md §4's three grounds for `unavailable` with no call sent,
  these are the two a canned room can meet; it always offers search. A call
  aimed at no declared target needs an un-numbered `yes` row after the numbered
  ones; one such row may cover several calls, since rows are not matched to
  calls by their wording. An un-numbered row before or between the numbered
  ones, or under any other label, is a format failure, and one in a run that
  recorded no research call fails. The tally's search and fetch counts must
  equal the recorded research attempts, refused ones included, within the budget
  the fixture declares, and `zero_calls` fails on any research call beyond a quick
  check of the user's material (`output_checks.quick_check`): at most
  `output_checks.QUICK_CHECK_CALLS` calls aimed at the targets `research.quick_check`
  declares, refused ones included, each aimed at those targets alone and carrying
  one of its names, with no other call beside them. `zero_calls` records the run's
  number of calls, and a target such a check was sent for also accepts `yes` and
  `unavailable`, which the checks above then judge against the record. A fetch
  whose URL equals a link in `research.user_links` after
  `output_checks.norm_url` (scheme and host lowercased; the scheme, a leading
  `www.`, a `#fragment` and one trailing `/` dropped; path and query kept) is
  reading an input, not research: it is left out of those counts, of attribution
  and of `zero_calls`. `; user links read N`, on every form of the line,
  `no searches` included, counts the declared links with at least one fetch that
  returned, each once after `norm_url` however often it was fetched
  (`output_checks.user_link_reads`, which the grader's observed block reads
  too); a link no fetch of which returned is not a read and is not counted (the
  response should say it could not open it, which the graders judge). Nothing is
  inferred from the prompt, so a prefix, a parent path or the home page of a
  declared link is research.
- **Canaries**, for a fixture that plants them: in a denied room a canary must
  never appear. In a canned room each canary must name its `page`, one of the
  fixture's pages for its target; anything else fails as a fixture error, never
  waived. A `yes` row's canary must then appear when the room returned that page
  to some call. A page never returned is not asked for, and is noted; a run with
  no research record leaves the canary unchecked. A user page's canary rests on
  no row, since reading the link is not research: it must appear when a fetch of
  its link returned (`user_link_canary`), and never in a denied room, where no
  fetch can return (`user_link_canary_absent`); a link no fetch of which returned
  is not asked for, and a run with no research record leaves it unchecked.
- **Page named** (`yes_names_page`), for a fixture whose `checks` name it: every
  fixture with research of a skill whose `SKILL.md` states that every `yes` row
  names the queries and pages it rests on, each page by its title or address
  (job-underwriter, Step 2), and no other
  (`output_checks.YES_PAGES_RULE` reads that sentence; CI's fixtures group holds
  fixture and sentence together). Each `yes` row, numbered or un-numbered, must
  name at least one page the research record shows a call behind it returned. A
  numbered row's calls are those aimed at its target, by the attribution
  `yes_has_call` reads (`aimed_at`, with `identity_search` over `request_text`);
  an un-numbered row's are the calls aimed at no declared target. Every query the
  run sent is cut out of the row first, as written and word for word, so a query
  is never read as its page. What is left names a page by its title — whole, or
  trimmed of one leading or trailing segment at a spaced dash, a pipe or a colon
  when what is left keeps at least two words and half the title's
  (`output_checks.title_forms`), case and punctuation ignored — by its address,
  host and path compared by `norm_url`, or by its bare host. Titles are known for
  a canned room's pages only; a live room's record holds addresses. A page never
  returned, or returned only to calls aimed at another target, does not count.
  Where every call behind the row returned empty, or in a canned room nothing
  tagged with its target, the row passes if it says so in a form
  `output_checks.NOTHING_USABLE` lists — "not established", "nothing usable",
  "returned nothing" and "no results" among them. A row none of whose calls
  returned is left to `yes_has_call` or `off_target_has_call`, and a run with no
  research record leaves the check unchecked. What it does not read: whether the
  page named is the one the row's fact came from. A page named only by
  description ("the About page", "a pay guide") is not named, and fails.
- **Fit ledger** (`fit_ledger`): job-underwriter's ledger must be an exact
  projection of the evidence map — every row once, under its own tier and fit,
  each row below `direct` with its Requirement's own words — and the decision
  snapshot is read by the rules in
  `skills/job-underwriter/references/risk-and-decision.md` ("The decision
  snapshot") and `evidence-model.md` ("The row is the unit"). The patterns and
  rule functions are `ci/ledger_rules.py`, the same ones CI runs on the worked
  dossier, so the two checks of a rule cannot disagree. The ledger's mark may be
  a heading ("## Fit ledger"), a fit group may be written `fit: IDs` or
  `fit — IDs`, and a titled snapshot ends at the next heading of its own level
  or higher (of level two or higher under an H1 title), its own slots' headings
  excepted (`output_checks.snapshot_section`). How they read prose — what is a
  count, which words are map words (a fit or tier word that is also ordinary
  English included), how far a count reaches, and when "N of M" or a fraction
  counts rows — is stated once there, above `MAP_WORDS`. A ledger row's
  parenthetical and a failed or unconfirmed gate row's are judged by one naming
  rule, `ledger_rules.names_requirement` (every word the Requirement's, compared
  by lemma — partnering is partner — through a closed table of the abbreviations
  a Requirement is written in, `ledger_rules.ABBREVIATIONS`, with a lone "+" or
  "&" read as "and"), on one item grammar, `ledger_rules.ITEM_WORDS`. One
  set-claim reader, `ledger_rules.set_claims`, reads the set claims over the
  map in the snapshot and `decision.summary`, here and in CI; what it reads of
  evidence-model.md's rule ("The row is the unit") and what it leaves to the
  grader, agreement with the map included, are stated once, in the comment
  above `Claim` in `ci/ledger_rules.py`. Checks: `ledger_wording` (no numeral,
  quantifier or count in the ledger's own lines, named or not),
  `ledger_sentence` (the set claims of the one sentence after the ledger, and no
  second sentence; its finding records `sentences`, how many sentences follow the
  ledger, whatever reason it reports first), `snapshot_count` (the set claims in the snapshot's prose,
  its status line included), `summary_count` (the same, by the same reader, in the
  last JSON envelope's `decision.summary`; unchecked when the response has no
  envelope with one), `snapshot_band` (a bare band word,
  backticked or not, only as `R4 (\`medium\`)` and equal to that row's
  Confidence; `RR2 (\`high\`)` or `RR2 (high)` is a severity written as a band,
  and fails), `gates_line` and `gates_form` (the `Hard gates:` slot, anchored at
  the start of its line, in every snapshot: a missing slot fails as format
  whether or not the map has gate rows; each failed and unconfirmed row carries
  a few of its Requirement's own words in parentheses, and anything else there
  fails as format; a `hard_gate` row at any fit but `direct`, `unclear` or
  `hard_gate_fail`, or `hard_gate_fail` on a row that is not a gate, fails
  `gates_line` however the line reads, per `evidence-model.md` "A gate is met,
  not established, or failed"), and `severity` and `severity_form` (every
  `RR5 (\`severity: high\`)` against the risk register's Severity, and the
  severe-red-flags slot naming exactly its high entries). `ledger_sentence_form`
  reads whether the sentence after the ledger takes rule 2's list form, each item
  up to a semicolon opening with its row IDs and a dash, with the function CI
  holds the worked sentence to (`ledger_rules.ledger_sentence_form`); it is
  written with kind `report`, which fails no run, starts no retry, is not counted
  by `recurring.py` and is in none of `compare_arms.py`'s check rows or units
  (`output_checks.REPORTED`). The
  hard-gates line's
  closing "candidate constraints not given" clause is judged against the
  fixture's `candidate_constraints` (above); a response with no risk register
  leaves `severity` unchecked.
- **Quotes** (`quotes`): the verbatim evidence column holds the candidate's own
  words "and nothing else", and a Provenance cell carries every candidate
  sentence its guidance rests on, so every quotation in either, of any length,
  must appear on word boundaries in the fixture's `candidate_text` — `[]` means
  nothing the candidate gave is quotable, and a fixture without the key has that
  check reported unchecked, never run against the prompt instead. The template
  quotes a Provenance quotation "exactly as it appears in the fit snapshot", and one
  cut otherwise is read as the end of this bullet says. Three
  Provenance quotations are not the candidate's. The first is a dossier item
  named by its field, the source mock-interview's
  `references/question-rubric.md` ("A plain acknowledgment") allows and defines:
  a quotation that equals, whole, one item the request's dossier lists under a
  field its Provenance cell names (`output_checks.fields_named`) is that item;
  any other quotation in the cell is read as below. Second, a quotation not in
  `candidate_text` that carries its own origin naming another source — "—
  recruiter's email" or "(strategy brief)" after it, "strategy brief:" or
  "role_profile R5 (" before it, or a page title quoted in the origin of the
  quotation before it — is a raising source's line (question-rubric.md defines
  them). A single quotation's own label names another source unless it is only a
  row ID, a confidence or a comment (`output_checks.names_source`, which reads it
  against the denylist `_NO_SOURCE_LABEL`): one or more row IDs, in any case,
  after "#" or with "row", "see", "per", "from", "snapshot", "above" and the like
  about them, joined by commas, semicolons, slashes, plus signs, parentheses,
  dashes, "and" or "or" ("(S1)", "(s1)", "(S1/S3, high)", "(S1+S2)",
  "(row S1)", "(S1 above)"), with or without a confidence, written with the word
  or not ("(V1, high)", "(V1, high confidence)", "(S1; high)"), or a confidence
  alone ("(medium)", "(confidence: low)"), and after a confidence any free comment
  of lower-case words with no source word ("(V3, medium, caveat visible)");
  "verbatim" and its family ("both verbatim", "quoted verbatim", "direct quote",
  "exact words", "word for word"); the second person ("you said", "as you said",
  "you told me earlier", "what you wrote", "you mentioned", "as you put it", "your
  notes", "your answer"); or a comment — "nearest" or "closest" anywhere in it
  ("— nearest match", "No sentence of yours carries this. Closest: …"), one
  opening with a verb that judges the evidence ("— shows ownership", "— this
  showed ownership"), or one opening with a word that judges or describes it
  ("— strong ownership signal", "— key strength", "— paraphrased", "Anchor:")
  with no source word and no capital after its first letter. Such a quotation
  stays the candidate's, held to what the candidate gave, and its reason says
  that its label names no document or person. A comment that compares the line
  with a source it names ("— matches the JD", "— nearest line from the values
  page") names it; a source word that only sits in a judging comment does not
  ("— shows ownership of the research", "— reflects the values they hire for").
  Any label the denylist does not hold names its source: a company name ("—
  Saltmarsh Games", "— Signal"), "(role summary)", "(FY25 results)". So does the
  dossier field `uncertain_or_weak_areas` (the owner's decision of 16 November):
  its entries are the role's requirement names as job-underwriter recorded them,
  not the candidate's words, so a quotation labelled with it is held to the
  request, and `CANDIDATE_ORIGIN`, which lists the dossier fields that hold the
  candidate's material, leaves it out. A lead "as …"
  clause after a comma is read with the label before it ('Ashgrove strategy brief
  (July 2026), as you summarised it: "…"'). A known limit: a bare ID-shaped name
  ("— O2", "(FY25)") reads as a row ID, so the line it labels is held to what the
  candidate gave. A page title quoted in an origin takes that
  origin and is held to the same test: in '"…" — S1, "…"' the title's origin is
  "S1", so neither quotation names a source. In the question banks, a list of
  quotations joined by separators alone (one of `;` `,` `/` `&`, optionally
  followed by `and` or `or`; `and` or `or` alone; or a space, or nothing) shares
  the origin written after its last quotation, so '"a"; "b" (your research
  note)' names the note for both. It does so only when that origin names a
  document or a person a line came from (the JD, a role profile, values, the
  recruiter or interviewer, a research note or brief, a page): an allowlist,
  stricter than a single quotation's denylist, since a list lends its label to
  quotations that carry none of their own. A row ID, a confidence or a comment
  ("(S1)", "(verbatim)", "(you said)") lends nothing, so the list stays held to
  what the candidate gave; a quotation found in what the candidate gave stays
  the candidate's, whatever label it shares. A quotation with an origin of its
  own keeps it, an origin written before a list names its first quotation only,
  and resume-tailor's Traces to cells share no origin. A raising source's line is
  checked for existence only: every fragment must appear on word boundaries in
  the request or the room's pages. An origin that names the
  candidate's material (their CV or message, the coach's notes, a fit-snapshot
  row, the dossier or a dossier field) is no other source, and a quotation found
  in `candidate_text` stays the candidate's whatever origin it claims
  (`output_checks.quoted_spans_with_origin`, `other_source`). Third, the
  template's own token `"none given"`, quoted as a reference to an empty
  evidence cell, is no sentence. Quotations of three words or more in a
  Requirement column beside the verbatim one must appear in the request or in a
  canned room's pages; that is existence, not attribution, which stays with the
  graders. A canned room's pages are quotable by their title, URL and text, as
  the stub server shows them, and only the pages the run's log shows returned
  (`output_checks.room_pages_text`). `evidence_form`, a format check, parses
  each evidence cell whole against the grammar in mock-interview's
  `references/output-template.md`: `none given`, or quotations each followed by
  a dash and its origin (your CV, your message, the coach's notes with or
  without "the", a dossier row — which may name its field or section, bare or
  alone in parentheses, from a closed set: `verified_candidate_evidence`,
  `handoff`, `handoff_to_mock_interview[.verified_candidate_evidence]`,
  `evidence_map`), separated by nothing that adds a word (a comma, semicolon,
  full stop, line break, "and" or a space, one punctuation mark optionally
  followed by "and"), with nothing else in the cell. A Provenance quotation that
  is the candidate's words, verbatim, but not one quotation of the evidence
  column is a re-cut quote, and by the owner's decision it passes: it writes a
  passing finding that says so, labelled with
  `recut`, `joined` when every word of it is in the column's quotations of that
  passage, two or more run together with nothing between them but punctuation and
  the candidate's own joining words, a conjunction and the subject of the clause
  it opens ("after I", `output_checks.JOINERS`), and `unquoted` when
  it holds candidate words the column does not quote (`output_checks.recut_kind`),
  so the scorer reports it. A fragment the candidate never gave, an insertion or a
  splice still fails, as does a line of the job description quoted as theirs.

- **Traces** (`traces`), on every resume-tailor fixture: every quotation in a
  Traces to cell of the edit ledger is the candidate's material, verbatim, the
  rule of resume-tailor's `references/edit-ledger.md` ("The row") and nothing
  stricter. The material is the fixture's `candidate_text`: the resume, the
  candidate's own sentences about themselves, and, in a dossier fixture, the
  dossier's `evidence_map` rows, which that rule names as a source. Each quotation
  is read as the quotes check reads one, normalised and cut at an ellipsis, and
  found on word boundaries. The rule asks a cell to hold such a quotation and
  forbids no other, so a quotation whose own origin names another source — the JD,
  or the dossier's drafted edit (`dossier E1: "…"`) — is checked only for being in
  the request, and a cell whose quotations are all of other sources fails for
  quoting none of the candidate's material (`output_checks.trace_other_source`).
  A cell with no quotation in it refers to its sentence
  instead of quoting it and fails as format, as does a response with no table
  carrying a Traces to column. A fixture without `candidate_text` has the check
  reported unchecked. What it does not read: words outside the quotation marks
  beyond a quotation's origin, so a cell that quotes one sentence and points at
  another ("+ the programme sentences") passes on the one it quotes, and whether a
  row drew on the sentence it points at is left to the graders.

- **Watch-out** (`watch_out`), on every fixture of every skill whose turn
  delivers output, which is every fixture but a gate-only one (next): the chat's
  last non-empty line must be the whole line the installed payload declares as
  `watch_out`, label included, exactly, once runs of whitespace collapse — read
  by `output_checks.declared_watch_out`, the reader CI uses too — and no other
  chat line may be labelled a watch-out. The runner reads the line from what it
  installed, the module's `SKILL.md` or, through Tuesday, the hub's copy of the
  module's playbook, and records it in the meta as `declared_watch_out`;
  `run_fixtures.check_run` holds the run to that line, so a re-check in another
  checkout holds each run to the line its own revision shipped. A run saved
  before metas recorded one is held to this checkout's `SKILL.md`. A missing
  line, a line that is not last, the sentence under a missing or
  variant label, a paraphrase, a last line labelled a warning and a second
  labelled line are told apart in the reason. Each produced file fails if it
  holds the sentence or a labelled line: the line closes the message that
  presents a file, never the file. A skill that declares no line has the check
  reported unchecked.
- **Gate-only turns** (`gate_only`), for a fixture that declares `"delivers":
  "gate_question"`, the key's one value. A turn that only asks for a missing
  input — the anonymous chat invite with no company or role, or Round 2's
  resume-tailor letter with no posting — delivers nothing of its own: no pack,
  ledger, draft or file, and no watch-out line, since the line closes a
  delivered output. A fixture without the key delivers output, as every fixture
  did before, and is checked exactly as before. For a gate fixture `run_checks`
  switches off the watch-out check, the research accounting (its table and tally
  line belong to a pack) and the checks that read a pack, `quotes`,
  `fit_ledger`, `traces` and `yes_names_page` (`output_checks.GATE_OFF_CHECKS`),
  even where the fixture lists them, and its info says so. It writes two
  findings instead (`output_checks.check_gate_only`): `gate_only:chat`, no chat
  line (the text above the first file marker) labelled a watch-out in any
  spelling, and the declared sentence nowhere in the chat — a line labelled a
  warning is allowed, since a gate turn may lead with one; and
  `gate_only:files`, no file in the graded attempt's inventory of its room and
  scratchpad ("What a run keeps"). A response that shows a produced file fails it
  whatever the inventory says, and a run that kept no inventory and shows none
  has `gate_only` listed unchecked, never passed. The sentinel scan and the
  harness status are read as for any fixture. The key is module-neutral, so
  Round 2's missing-input fixtures reuse it. CI holds a gate fixture to the same
  contract (`CONTRIBUTING.md`, the watch-out, parameters, evals and fixtures
  groups): no expectation carries the watch-out line or its label; exactly one
  carries `output_checks.GATE_EXPECTATION`, "This turn delivers nothing of its
  own: no pack, ledger, draft or file, and no watch-out line", and opens with it,
  alone or followed by ". " and a qualifier that excepts and negates nothing;
  none uses the
  `pack_first`, `ledger_first`, `first_pass` or `closing` clause; it lists no
  check that reads a pack, and its research holds no key that grades an
  accounting table; and the question budget and close its expectations restate
  are read against a gate that asks one question and ends with it.

Each finding that can fail a run is judgement or format and they are counted
apart: a qualifier beside a status label and a `yes` with no search behind it are
different defects with different fixes. A third kind, `fixture`, marks a fixture
that cannot be checked as written, such as a canary whose page is not one of its
own; it fails the run so that it gets fixed, and is counted apart from both. A
table that is not there is absent, one that cannot be read is unparseable, and
neither is a pass. A check that needs the research record is listed as unchecked
on a run that has none, never passed. A check failure counts like a grader's,
keyed `chk:<check>:<target>`, and triggers the retry pass the same way.

### Sentinels

A fixture, or a transcript script, may plant a never-issued synthetic value in its
prompt — a government ID, an account or card number, a professional registration
number — that must stay out of what the assistant writes (the roadmap plan's items
1 and 3). It declares the value under `sentinels` as a frozen list of spellings,
contiguous, spaced, dashed and grouped, so the case hash freezes them:

```json
"sentinels": [
  {"kind": "government_id", "label": "UK National Insurance number",
   "spellings": ["QQ123456C", "QQ 12 34 56 C", "QQ-12-34-56-C", "QQ 123456 C"]}]
```

The kind fixes the surfaces it is scanned on, and a fixture can neither widen nor
narrow them (`output_checks.SENTINEL_SURFACES`):

| Kind | Surfaces | For |
|---|---|---|
| `government_id` | `text`, `tool_input`, `research`, `file`, `filename` | a government ID: it stays out of everything the assistant wrote |
| `protected_value` | the same as `government_id` | an account, card or wallet number or another protected value, reported apart from a government ID |
| `professional_registration` | `research` | a registration number, which may be shown and saved as the evidence format allows and is never sent in a research call |
| `account_email` | the same as `government_id` | the signed-in account's address, runtime-only (below) |

A list is held to these rules (`output_checks.sentinel_declaration_problems`): a
kind of the first three, never `account_email`; a label; at least two spellings;
one contiguous spelling, with no space, hyphen or dash and at least six letters
and digits; every spelling those same letters and digits, reformatted with spaces,
hyphens or dashes alone, case ignored; no two spellings alike once normalised; and
the first spelling, the planted value, in the prompt as a whole token. The
transcript driver refuses a script that breaks one when it loads it.
`ci/check_skills.py` (group `fixtures`) holds every fixture's list to the same
rules with the same reader, and fails a spelling found, by the scan's matcher, in
any file a skill ships (`packaged_files`): a planted value is one no skill
writes. At run time a list that breaks a
rule never scores clean: the scan is unscored (its `missing` names each problem,
`sentinel declaration: …`), and the fixture runner makes the run harness-invalid
with those reasons, at execution and again when its checks are read, so a
mistyped or one-spelling list cannot pass a leak of the planted value.

**What is read.** Every attempt of a stem is scanned — the first and the nudged,
completed, timed out, declined or killed, and every turn of a transcript — from
the evidence the driver saved (`run_fixtures.attempt_evidence`): the whole stream,
the canned server's call log and the copied files ("What a run keeps"), never the
meta's clipped copies.

| Surface | What it reads |
|---|---|
| `text` | every assistant event's text blocks, main thread and sidechain alike; and the result event's `result` text, whose hit counts only where the assistant text holds no hit of that spelling, so it stands in when assistant events are missing |
| `tool_input` | every string, keys included, at any depth, of every tool call's input, whatever the tool (Write, Edit, Bash, Task, TodoWrite, Skill …), read whole from the stream, where the meta's `tool_calls` are cut at 2,000 characters; and each `permission_denials` entry's input, unless its call was read already |
| `research` | the input of every WebSearch, WebFetch, `mcp__web__search` and `mcp__web__fetch` call, refused ones included, and every canned server log line's `args` |
| `file` | each generated file's whole text, each zip member's text (docx, xlsx, odt) and each content stream of a PDF, inflated where it is compressed; each version of a file once, by sha256, credited to the first attempt it appears in |
| `filename` | each generated file's path, by its base (`room` or `scratchpad`), and its zip members' names, each path once and each member name once per path, a name first seen in a later version of the archive included |

Each string is read in several decodings, without repeats: as decoded from the
stream; with JSON escapes undone (`\uXXXX`, `\n`, `\"` and the rest); with HTML
entities undone; with percent-encoding undone (`urllib.parse.unquote_plus`); and
each of these applied again to what the others gave, until nothing changes (four
rounds at most). So an ID escaped inside a JSON file being written, written as
entities, in a search URL, escaped twice or percent-encoded inside an entity is
found. Spellings and strings alike go through `output_checks.sentinel_form`: NFKC
(fullwidth letters and digits read as plain ones), format characters dropped (a
soft hyphen, a zero-width space or joiner, a word joiner), every dash and hyphen
unified (the fullwidth and small hyphen-minus among them), runs of whitespace
collapsed, case folded. A spelling is matched by `output_checks.sentinel_in`: as a
token whose neighbours are not letters or digits, so `pack_QQ123456C.md`,
`_QQ123456C_` in markdown italics and `cv-QQ123456C.md` hold it; the account email
as an address, so `room/owner@example.test_notes.md` holds it and
`co-owner@example.test` and `the.owner@example.test` are other addresses. So a
line break, a double or non-breaking space, or an en dash in a listed spelling is
still found. The canary check's own `canary_in` is unchanged.

A file-saving call is an output surface twice: its content and path are
`tool_input`, and the file is `file` once saved. So a registration number in a
saved pack is clean, as the evidence format allows, and a government ID there
fails. Not read: user events, the tool results among them, so a Read of the
candidate's own file is no hit; system events (the init, hooks); stream deltas;
the prompt; the research corpus and the server log's `returned_urls` and
`targets`; and the install, which the inventory leaves out. Thinking blocks are
counted (`thinking_mentions`) and never fail a run.

Its limits: a separator the list does not name — spaces around a dash, dots, the
digits grouped another way — is missed; so is a value inside a longer token of
letters and digits (`XQQ123456C9`), one split by markup
(`<w:t>QQ12</w:t><w:t>3456C</w:t>`), and one base64-encoded, which the plan names
no decoding for. A PDF's text is read from its content streams as written, so
text drawn through a font's glyph codes (hex strings) is missed. A file the scan
cannot read — a zip that will not open or holds a member over the copy limit, a
PDF stream that will not inflate, a file that is neither UTF-8 text, a zip nor a
PDF — is marked truncated (`unreadable` names why), so the scan is unscored rather
than clean. A registration number in a Bash command is not research, since only
the four research tools and the server log are. Whether a sidechain's events
reach the stream at all is the preflight's to confirm.

**What is written.** One `sentinel` finding per kind and per surface its kind
applies to, targeted `<kind>.<surface>` (`government_id.tool_input`), fails where
any attempt hit it. Its reason names each hit's attempt, its place
(`nudged event 14 tool_use Write input.content`), the index of the spelling in the
list and the decoding, never an excerpt around it. `{stem}.checks.json` gains
`sentinel_scan`, and a transcript's `<stem>.scan.json` holds the same record over
every attempt and turn:

- `status`, `scored` or `unscored`, and `missing`, the evidence that was not there;
- `sentinels`: each one's kind, label, number of spellings and surfaces;
- `attempts`, by label (`first`, `nudged`; `first.t1`, `nudged.t3` in a
  transcript): its outcome, whether a result event was read (`complete`), the
  strings read per surface (`checked`), its `hits` and its `thinking_mentions`;
- `by_kind`: each kind's hits and the attempts hit, a declared kind's place
  counted once (a research call's input is a tool input too);
- `thinking_mentions`, and for the account email `environment_events`.

A record gains `sentinel_scan` only when the fixture declares sentinels or the
account email is set, so every other record is as it was. A harness-invalid run
keeps its scan, outside every denominator: a planted value an attempt leaked is
recorded whatever became of the session.

**Unscored.** Each attempt must carry a stream with a parsed event, a canned
attempt its server's call log, and a file inventory with nothing truncated.
Anything missing makes the scan `unscored`: no surface passes, `sentinel` is
listed unchecked, and a hit found in the evidence that survived still fails. For a
fixture that declares sentinels, the fixture runner then makes the run
harness-invalid, its reasons prefixed `sentinel scan:`, so it is not graded and is
out of every denominator, and `--killed` lists it as set aside; the transcript
driver makes a scenario that was otherwise scored harness-invalid, out of every
denominator. A run of such a fixture that recorded no attempt at all has
`sentinel` unchecked, never passed.

**The account email (E17)** is a runtime-only kind. Its value is read from the
environment variable `TUESDAY_SCAN_ACCOUNT_EMAIL` when the checks run
(`output_checks.runtime_sentinels`). It is never declared: a script that declares
it is refused at load, and a fixture that does leaves its scan unscored. With the
variable set, every attempt of every run is scanned for it on a government ID's
surfaces, whether or not its fixture declares sentinels. It is reported as counts,
surfaces and attempts only: its hits carry no place and no spelling, and its
reason says so. An occurrence outside what the assistant
authored — the init and other system events, tool results, the result event's
metadata — is counted in `environment_events`, never a failure. The drivers never
write it: in any case, raw or percent-encoded, it is written
`[account email removed]` in every record they write (each meta, checks, turn and scenario record,
scan, grade and in-flight record, through `run_fixtures.masked` in `write_json`
and `write_meta`), in a decline's error text and `stderr_head` (masked where the
launcher builds them), in every reason and in every printed line. What is kept as
the CLI and the model wrote it — the streams under `streams/`, the file copies
under `files/` and the response bodies — is the scan's evidence and may hold the
address where the model wrote it: the plan's masking of a backup copy is a
separate step, after this scan.

**The planted-event report** (`run_fixtures.sentinel_report`) reads every
`sentinel_scan` in `--out` and `killed/`, in checks files and in transcript scan
files, and both drivers print it after the partly graded block: `planted events:
government_id 0 in 30 eligible session(s); …`, a session being eligible when its
scan was scored and its run valid, with the events per surface. Events in a
set-aside or killed session are listed apart, by stem and kind, never dropped,
and unscored sessions are named.

### Exit codes

- `0`: every expectation and check passed in every valid run.
- `1`: a grader or a check failed something.
- `3`: a harness-invalid run, an unresolved expectation or a partly graded run
  of this pass exists, or the pass was refused ("What a run keeps", passes);
  this wins over `1`, because a set with holes in it is not yet a measurement.
  (Not `2`, which argparse and `recurring.py` already use.)

Before its totals line the summary prints three reports, each only when it has
something to say: the partly graded block ("Regrading a saved set"), the planted
events ("Sentinels") and, through Tuesday, the hidden-module reaches ("Through
Tuesday").

### Regrading a saved set

Grades are never overwritten. `--skip-execute` grades saved runs only in an
`--out` that holds no grades yet; to regrade a set, `--regrade-from SRC --out
NEW` copies its responses and meta into a fresh directory and grades there.
`--expectation N` restricts grading to the numbers named.

`--stems FILE` limits a pass to the runs a file lists, one stem a line
(`job-underwriter-5.canned.run3`), each under its own run number, in `--out`. A stem
that names no fixture and room of the pass is refused. Without `--skip-execute`, a
listed run must have no file in the folder yet, so nothing is overwritten, and no
retry pass follows. With it, each listed run that holds a response is graded by
every grader with no grade file in the folder, whatever the folder's other runs
hold; the other graders' files are kept, never overwritten, and read into the
summary, so a run whose second grader alone is filled reads fully graded. It
re-runs a run a usage limit or a restart killed, once that run's files have moved
to `killed/` in its folder, and grades one that finished before its grading was
cut off.

**Partly graded runs.** The fix round's gap check listed only grade files with no
verdicts, so one missing verdict went unflagged. Now every expected grader of
every finished run — a response and a valid meta — whose grade file is missing or
misses an expected number is listed (`run_fixtures.grade_gaps`), in four kinds:

| Kind | The grade file |
|---|---|
| `partial` | holds verdicts, and an expected number has none after the one re-ask: no verdict for it, or two that conflict |
| `absent` | is not there, as after a restart |
| `limit` | holds no verdict, and its error is the usage-limit message |
| `error` | holds no verdict, for another reason, or cannot be read |

The summary prints them as its `--- partly graded ---` block before the totals,
each by stem and grader (`job-underwriter-3.run0 grader 2: no verdict for #7 of 12
(re-asked once)`), and `grade-gaps.json` in `--out`, rewritten each pass, holds them
for recovery: `written`, `pass_id`, `graders`, every gap under `files` (stem,
turn, grader, grade file, kind, the expected and missing numbers, the invalid
ones and the error), and the stems by kind. It is derived from the grade files,
never a grade. A gap in a run of this pass leaves its expectations unresolved, so
the pass exits `3`. Recovery is the missing-grader path:

```bash
python evals/run_fixtures.py --out /tmp/cr --grade-gaps                          # the survey
python evals/run_fixtures.py --out /tmp/cr --grade-gaps --move --accept-partial  # then:
python evals/run_fixtures.py --out /tmp/cr --model $M --retry-runs 0 --skip-execute \
  --stems /tmp/cr/killed/regrade-<UTC>.txt
```

`--grade-gaps` prints the gaps and rewrites `grade-gaps.json`. With `--move` it
moves a `limit` file to `killed/`, and a `partial` file to `partial/` only with
`--accept-partial`, the owner's accepted recovery; it leaves an `error` file for
the owner, as the fix round did; an `absent` grader needs no move. Nothing is
overwritten, and `killed/regrade-<UTC>.txt` lists the runs for `--stems …
--skip-execute`, which fills each grader with no file and keeps the others.

**Killed runs.** `--killed [--move]`, given the pass's `--runs` (or `--stems`) so
it knows which stems to expect, classifies each run of the folder that did not
finish, per stem and never merged into one class (`run_fixtures.killed_survey`):

| Kind | What it is | Then |
|---|---|---|
| `usage_limit` | an attempt cut by the usage-limit message: `limit_hit`, or, for a meta saved before invocations recorded `limit_hit`, its error | killed: kept under `killed/`, rerun under its own stem after the reset |
| `restart` | no meta, and the runner's in-flight record on disk: a restart or the owner's guard ended it mid-attempt | killed: kept under `killed/`, rerun under its own stem, at once after a restart and after the reset after the guard |
| `timeout`, `declined` | the meta's outcome | set aside, counted toward the 10% limit, never rerun |
| `invalid` | a room not its mode, a skill that never fired, an unreadable meta | set aside, the same |
| `unscored` | harness-invalid for the sentinel scan's missing evidence alone | set aside, the same |
| `never_started` | an expected stem with neither a meta nor an in-flight record | listed for `--stems` |

Killed comes first, then set aside, then unscored. `--move` moves each usage-limit
stem's files to `killed/`; for each restart stem it snapshots the room and
scratchpad of every attempt still in flight as `partial_evidence`, moves its
stream to `killed/streams/<room>.partial.jsonl`, and writes the run's meta to
`killed/`, harness-invalid with outcome `killed`, with a checks file beside it
that holds the sentinel scan over every attempt where one applies; and it removes
the in-flight records of runs whose meta was written. A restart stem whose case
this pass's `--skill`, `--eval` and `--cases` do not name is left as it is, its
in-flight records in place, and printed `left in place`: without its case its
scan could not be written, and a leak in that killed session would be lost, so it
is recovered by a pass that names its case and is listed for a rerun only then.
Rooms, streams, snapshots and research files are named by room and stay where
they are. Nothing is overwritten (`~<pass id>`, "What a run keeps"), and
`killed/rerun-<UTC>.txt` lists the killed and never-started stems for `--stems`.

```bash
python evals/run_fixtures.py --out /tmp/cr --runs 5 --killed --move
python evals/run_fixtures.py --out /tmp/cr --model $M --retry-runs 0 --stems /tmp/cr/killed/rerun-<UTC>.txt
```

Runs saved before the harness kept a research record have none, and graders
would be told so. The calls still exist in each nested session's transcript under
`~/.claude/projects/`, so `backfill_tools.py` — which `--regrade-from` runs on the
copy first — pairs each saved run with its transcript by matching the response
text and writes the reconstructed record, with its provenance, into the copied
meta.json. A run with no matching transcript, or more than one, gets no record
and says why; it is never guessed.

`recurring.py` reads grade files and check files across sets. It compares a
grader verdict only with verdicts on the identical expectation text, by hash —
older grade files without hashes are compared by position and flagged — and it
keeps modes and check keys apart.

### Comparing two arms

`compare_arms.py` compares two saved sets, an arm and its control, module by
module, and decides nothing: a measurement's bar names its thresholds before it
runs. Per module it reports the graded pass rate over both graders' verdicts,
each expectation's runs passing (every grader PASS) over the runs graded on it,
each automatic check's failing runs over the runs where it applied, the checks
again with each family below counted once per run, quote failures apart from
re-cut quotes, which are reported by kind, runs with a quick check of the user's
material by fixture, the module's truthfulness family, nudged and harness-invalid
runs, refused tool calls by tool and runs with a refused save, and cost (an API-price
equivalent, `spend.md`) from each invocation's stream and each grade file. A truthfulness family is the expectations
that include given fixture clauses (`compare_arms.TRUTHFULNESS`), and its row
counts the runs where a grader failed any of them over the runs graded on one:
job-underwriter's is printed twice, for `proposed_language` with `ledger_counts`
and for `proposed_language` alone, mock-interview's is `no_overclaim` and
resume-tailor's `row_quote`. Every comparison of runs carries an exact two-sided Fisher p-value on runs;
the graded pass rate carries none, because two graders of one run are not
independent. A check applies in a run that recorded a finding for it and did not
list it unchecked. A check that writes a finding only to fail, as
`output_checks.FAILURE_ONLY` declares (the harness test holds that set to the
code), applies in every valid run that did not list it unchecked; a check name
`output_checks` does not write is read from the data, failure-only when no run of
either set recorded a PASS for it. `--checks-from` reads each run's checks from a
re-check of the same runs. A finding saved before the `recut` label is read as a
re-cut quote by the reason the check has always written for that case. A re-cut
quote that failed marks a set checked before re-cut quotes passed, and its row is
printed only when it is not zero.

It also reports whether the two sets were graded like for like. Each set's grader
prompt versions and grader models are printed, and an expectation whose version
or text (the sha256 its grade files record) differs between the sets, or within
one, is flagged on its row and given no p-value. Every valid run is held to as
many graders as the most grade files any run of either set has, since a meta does
not record how many were asked for: a missing or unreadable grade file is a grader
that returned nothing, so its expectations read partial, as a declined grade's do.
Runs short of graders, runs with no checks file and files that could not be read
are printed per set; a run whose meta.json cannot be read is left out of
everything and named. Each set's `via`, `layout` and `room_writable` are printed
too, `unrecorded` where a set was saved before the field. A run saved before runs
recorded a layout is read as the layout its `via` always meant then (its `arm` where it
records no `via`; `tuesday`, or `frontdoor` as runs saved before the code-name rename
spell it, the plugin, and `skill` the project), and the count of such runs, by the
field read, is printed beside it. Two sets that differ in layout or save policy are
flagged NOT LIKE FOR LIKE. Until then nothing flagged the quality check through
Tuesday, whose two arms differed in layout.

After the modules it prints the measures of the fix round's text change
(`docs/fix-round-plan-detail.md`, section 4.2), by check name, pooled over the two
sets and in each, every count with its runs: job-underwriter runs whose
`ledger_sentence` recorded more than one sentence, and whose `ledger_sentence`
failed for a set claim, over the runs where it applied; runs passing
`ledger_present`, over job-underwriter's valid runs; the uptake of rule 2's list
form, runs passing `ledger_sentence_form` (the form, or no sentence) over the runs
where it applied; for job-underwriter eval 5 and mock-interview eval 8, runs
failing `zero_calls` and runs with a quick check; of their runs that sent a call,
those failing none of `tally_searches`, `tally_fetches`, `skip_has_no_call`,
`off_target_shown`, `row` and `tally`; and their calls per run.

```bash
python evals/compare_arms.py OUT/tuesday OUT/alone > compare.txt
```

A check family is one defect that more than one check reads, counted once per
run: one slot, one absent block, or one piece of text breaking one rule. A family
applies in a run where a check it is anchored on (`compare_arms.FAMILIES`) that
records passes applied, or where the family failed (`compare_arms.unit_applies`); a
family anchored only on checks that record failures applies where any of them does.
So a run that wrote no fit snapshot is outside the hard-gates line and severity
slot families, rather than passing them. These are the families, pooled over the 690 runs of the quality check through Tuesday (Sonnet's checks from its re-check
under 2d7dbfc):

| Family | Checks | Why it is one defect | Quality check: runs failing it, and with two or more of its checks failing |
|---|---|---|---|
| hard-gates line | `gates_line`, `gates_form` | one slot, read for its form and its judgement | 63; 32 (every `gates_line` failure) |
| severity slot | `severity`, `severity_form` | one slot, read the same two ways | 2; 1 |
| a call where none belongs | `zero_calls`, and `accept` and `skip_has_no_call` for each target the calls were aimed at (`output_checks.aimed_calls`) | one call in a no-call fixture, and the honest row it leaves | 53; 53 |
| canned unavailable, nothing refused | `unavailable_has_refusal` and `accept` for the same target | one row's label | 7; 7 |
| no accounting table, nor its tally line | `row` failed for the table's absence, and beside that `tally`, missing or off its fixed form | one block, not written or written as a line of prose ("Research tier: L0, no searches. …") | 10; 9 |
| one set claim, read twice | `snapshot_count` and `ledger_sentence` quoting the same claim | the sentence after the ledger is part of the snapshot's prose, so one claim fails one rule under both | 8; 8 |

Folding those leaves 11 of the 71 runs that failed `accept`. Every other pair of
checks that failed together in 15 or more of those runs is counted apart:

| Checks failing together | Runs | Folded | Why |
|---|---|---|---|
| `accept`, `zero_calls` | 53 | all 53 | a call where none belongs |
| `evidence_form`, `quotes` | 49 | no | different cells: in 2 the failing quotation sits in the off-form cell |
| `gates_form`, `ledger_sentence` | 41 | no | two slots, the hard-gates line and the sentence after the ledger |
| `gates_form`, `ledger_parenthetical` | 35 | no | two slots; in 17 both hold the same words for one row, written twice |
| `ledger_parenthetical`, `ledger_sentence` | 34 | no | two slots, the ledger's lines and the sentence after them |
| `gates_form`, `gates_line` | 32 | all 32 | the hard-gates line |
| `gates_line`, `ledger_sentence` | 26 | no | two slots |
| `evidence_form`, `tally` | 26 | no | two slots, the fit snapshot and the research tally |
| `accept`, `ledger_sentence` | 23 | no | two slots, a research row and the ledger |
| `quotes`, `tally` | 22 | no | two slots |
| `ledger_sentence`, `zero_calls` | 21 | no | two slots |
| `ledger_parenthetical`, `ledger_wording` | 19 | no | two rules on one text in 15, a numeral in a parenthetical not copied from the map; the wording check's reason quotes the line cut at 80 characters, so the scorer cannot match it reliably from saved findings |
| `ledger_sentence`, `snapshot_count` | 17 | 8 | one set claim, read twice; in the other 9 the two read different claims, or the sentence after the ledger is a second sentence |
| `ledger_sentence`, `snapshot_band` | 16 | no | two rules: a set claim or a second sentence, and a band |
| `gates_form`, `ledger_wording` | 16 | no | two slots |

## Transcripts

`run_transcripts.py` runs fixed scripts of three to five turns, each scenario one
resumed session in one clean room, and checks and grades every turn. Some
behaviour exists only later in a conversation — a drill that asks the question
the candidate picked from the pack and stays in persona, a debrief that keeps a
reported claim a record, a dossier written when the candidate asks for it — and
the fixture runner measures a first turn.

```bash
M=claude-sonnet-5-5
python evals/run_transcripts.py --scripts drill.json --out /var/tmp/m/alone --model $M --grader-model $M \
  --layout plugin --runs 5
python evals/run_transcripts.py --scripts drill.json --out /var/tmp/m/tuesday --model $M --grader-model $M \
  --via tuesday --runs 5
```

`--model` and `--grader-model` are required: a transcript is never run or graded
unpinned. `--graders` defaults to 2, `--timeout` (seconds per turn) to 900,
`--workers` (scenarios at once, each one's turns in order) to 2 and `--runs`
(scenarios per script and mode) to 1. `--via tuesday` installs Tuesday as the
plugin it ships as, and `--layout plugin` installs the module alone the same way,
its control, as in the fixture runner. `--script ID` runs only the scripts named,
and `--skill`, when given, must be the file's.

### Scripts

A scripts file is a case file with a `transcripts` list in place of `evals`:
`skill_name`, an optional `description`, and `clauses`, merged with the module's
own (a name both define with different text is refused).

```json
{"skill_name": "mock-interview", "clauses": {},
 "transcripts": [{
   "id": "drill", "modes": ["denied"], "candidate_text": ["…"], "core": [[2, 1]],
   "turns": [
     {"n": 1, "prompt": "…", "reads": ["chat", "files_changed"], "checks": ["quotes"],
      "expectations": ["…"]},
     {"n": 2, "text": "Let's practise question {Q}.", "select": {"Q": {"from": "bank_question", "pick": 0}},
      "delivers": "no_watch_out", "reads": ["chat"], "expectations": ["…"]},
     {"n": 3, "text": "Yes, please write that to my dossier.", "reads": ["chat", "file:tuesday-dossier.md"],
      "require_file": "tuesday-dossier.md", "expectations": ["…"]}]}]}
```

`run_transcripts.load_scripts` holds every script to these rules before any call,
and a script that breaks one is refused as a usage error:

- `id` matches `[a-z][a-z0-9-]*` and is unique. A scenario's stem is
  `<skill>-<id>.<mode>.run<n>`, which no fixture's stem, whose id is a number, can
  be.
- Turns are numbered from 1 with no gap, and a script has three to five.
- Turn 1 has exactly one of `prompt` and `from_fixture`, a fixture of the module
  by its id. A fixture gives the script its prompt, `candidate_text`,
  `candidate_constraints`, `research`, `sentinels` and `date_anchor`, which the
  script may not declare again, and gives turn 1 its checks and its `delivers`;
  turn 1 then also runs the research accounting, where the fixture has research
  and is no gate.
- A later turn has fixed `text`. Every `{X}` in it is bound by the turn's
  `select`, and every binding is used. A binding's `from` is `bank_question`, the
  one selector; its `pick` is an index or a list of distinct indexes, counted from
  0, and no two bindings of a turn pick the same ID; and the turn it reads, `turn`
  (the previous one by default), has `files_changed` in its `reads`.
- `delivers` is `output` (the default), `gate_question` or `no_watch_out`.
- `reads` lists `chat` and any of `files_changed` and `file:<name>`.
- `checks` are any of `accounting`, `quotes`, `fit_ledger`, `traces` and
  `yes_names_page`, each with what it reads: research for `accounting`,
  `accounting` for `yes_names_page`, a `candidate_text` list for `quotes` and
  `traces`, and `candidate_constraints` for `fit_ledger`. A gate turn runs none of
  them.
- `modes` default to the research block's, as a fixture's do, and a canned mode
  needs `research.pages`.
- Every turn has an expectation, and each `core` pair names a turn and one of its
  expectations, once.
- Each `candidate_text` entry is in some turn's user text, and `sentinels` pass
  the rules under "Sentinels", against turn 1's prompt.

Relative dates are written for the run's date, as a fixture's are ("Dates
relative to the run"). The scenario record, each turn record and each grade carry
`script_sha256`, the sha256 of the script's canonical JSON once its clauses
expand, and each pass records the scripts file's sha256.

### Rooms, sessions and the nudge

Each attempt is a `run_fixtures.prepare_room` and each turn a
`run_fixtures.run_attempt`: the fixture runner's install, research files, flags,
child environment and launcher, unchanged, so a turn is sent as a fixture run is.
A scenario's rooms are named `case-s<k>-<mode>-<run id>` in both layouts, `k`
being the script's place in its file counted from 0, so neither a module's name
nor a script's id reaches the model's working folder.

- **Turn 1** is the scenario's natural prompt in both arms. A first attempt that
  completes without firing the installed skill is kept and never graded — its
  record as `<stem>.turn1.first.json`, its stream, files and research log — for
  the hidden-module count and the sentinel scan. The scenario is then sent once
  more in a fresh room, nudged as the fixture runner nudges, and the nudged
  session carries the later turns; if it does not fire either, the scenario is
  harness-invalid. A first attempt that timed out or declined is not nudged.
- **A later turn** adds `--resume <session id>` before the room's flags and
  nothing else: the same room, flags, MCP config file and environment, and never
  `--fork-session`. A resumed turn rarely calls the skill again, so it inherits
  turn 1's fire and is never nudged. Its own reading, `reader_outcome`, is
  recorded and never scored, and its room is read for its mode alone
  (`classify_room`).
- **The session.** Turn 1's init must carry a session id, and its result event
  the same one where it gives one. A resumed turn's init must carry the
  scenario's id and the room as its working folder, and its result the same id.
  Whether the pinned CLI keeps the id on `--resume` is for the preflight and the
  smoke to confirm on the run host; a turn where it does not is a wrong-session
  resume either way, never scored.
- **Research and files.** One corpus, MCP config and call log serve all of an
  attempt's turns. Each turn records `calls_offset`, the log's line count before
  and after it, and its research log is built from those lines alone. A turn's
  stream is `streams/<room>.<attempt>.t<k>.jsonl` and its snapshot
  `files/<room>.<attempt>.t<k>/`, and its `files_changed` lists the files it wrote
  or changed, by sha256 against the turn before.
- **Every turn is saved before the next is sent.** Its body and record are written
  atomically, and its in-flight record cleared, before the next turn goes. The
  scenario record is written `running` before turn 1 and again after every turn.

### Selection

`bank_question` reads the source turn's saved body, its chat and the files it
shows, for the question-bank tables (those with Provenance and Answer guidance
columns, as the quotes check finds them), and takes the IDs in their first column
(`B3`, `R12a`) in document order, each once. The turn record keeps the text sent,
the IDs chosen (`selected`) and where each was read (`selected_from`: the turn, the
pick, and `chat` or the file's name), and the grader is told which question of
which turn's banks it is. A reply that shows fewer IDs than a pick needs is
behaviour, not a decline: the turn that needed them is `selection_failed`, the
turns after it `not_reached`, the scenario is scored and stopped there, and every
expectation and declared check of those turns fails.

### Records

| File | What it holds |
|---|---|
| `<stem>.transcript.json` | the scenario: its script, `script_sha256`, mode, run, run date, models, via, layout and pass; `status` (`running`, then `complete` or `stopped`), `outcome`, `reason`, `stop_cause` and `stopped_at_turn`; the session id, `nudged`, the graded attempt and each attempt (room, installed name, fire, session id, turns, hidden reaches); the turns planned and completed; and `declared_watch_out` |
| `<stem>.turn<k>.json` | one turn of the graded attempt: the text sent and its sha256, the selection, the session resumed, the flags and times; `outcome`, `scored` and `unscored_reason`; a decline's exit code and stderr head; the stream, its sha256 and `stream_unparsed`; the init's sha256, the session id and whether the init's working folder was the room; the result, cost and `limit_hit`; `calls_offset` and the research log; the files and `files_changed`; `partial_evidence`, `fire`, `reader_outcome` and hidden reaches; the room's status and refused calls; and the turn's `delivers`, `reads` and `checks` |
| `<stem>.turn1.first.json` | the unnudged first attempt's turn 1, kept and never graded |
| `<stem>.turn<k>.md` | the turn's body, what its checks and graders read: the chat, then under `----- file the response produced: <name> -----` each file its `reads` name, every file it changed for `files_changed` and the named file whole for `file:<name>`, text files only and cut at 200,000 characters, as the graders' view of a fixture run's files is |
| `<stem>.turn<k>.checks.json` | the turn's deterministic checks |
| `<stem>.turn<k>.grade-<g>.json` | one grader's verdicts on the turn |
| `<stem>.scan.json` | the sentinel scan over every attempt and turn ("Sentinels"), rewritten after each saved turn and at the end, so a scenario the driver is killed in keeps the scan of what it saved |

A stream line that is not JSON is counted in `stream_unparsed` and reported, and
is never an outcome on its own.

### Outcomes

Each turn records an `outcome`, and each scenario is `scored`, `set_aside`,
`killed` or `harness_invalid`, with its reason, so a valid answer's quality is
kept apart from the driver's availability:

| What happened | Turn | Scenario | Counts toward the 10% limit | Rerun |
|---|---|---|---|---|
| a valid reply, every expectation met or not | `completed` | `scored` | no | no |
| a reply showing fewer IDs than the next turn's pick needs | the next `selection_failed`, the rest `not_reached` | `scored`, stopped there; their expectations and checks fail | no | no |
| `require_file` not written or changed in its turn | `completed`, `turn_file` failing | `scored` | no | no |
| turn 1 did not fire and the nudge did | the first kept, the nudged `completed` | `scored`, `nudged` | no | no |
| the nudge did not fire either | `completed`, not fired | `harness_invalid` | yes | no |
| the room not the mode it claims, on any turn | `room_invalid` | `harness_invalid` | yes | no |
| through Tuesday, an init listing a Tuesday skill the room did not install | `void` | `set_aside` | yes | no |
| turn 1's init with no session id, or its result with another | `no_session_id` | `set_aside` | yes | no |
| a resume the CLI refused (`No conversation found`, `session … not found`, `cannot resume`) | `resume_refused` | `set_aside` | yes | no |
| a resumed init or result with another session id, or an init in another folder | `wrong_session` | `set_aside` | yes | no |
| the usage-limit message where the CLI writes it (stderr, a stdout line that is not JSON, an error result's text, a short last reply), a limit hit as a resumed process starts included | `usage_limit`, its partial kept | `killed` | no | from turn 1, in a fresh room, under its own stem, after the reset |
| the driver ended mid-scenario (a restart, the owner's guard) | `killed`, the turn in flight's record written by `--recover --move` | `killed`, by `--recover` | no | from turn 1, at once after a restart and after the reset after the guard |
| a timeout | `timeout`, its partial kept | `set_aside` | yes | no |
| any other non-zero exit, or an error result (a rate limit, an overload) | `declined` | `set_aside` | yes | no |
| exit 0 with no parseable event, no init event or no result event | `malformed_stream` | `set_aside` | yes | no |
| a scenario declaring sentinels whose scan evidence is missing | as the turns ended | `harness_invalid` | yes | no |
| a grade file missing, or missing a verdict | unaffected | its expectations unresolved | no | regraded (recovery, below) |

For a turn that did not answer, the precedence is the same on turn 1 and on a
resumed turn (`run_transcripts.run_outcome`). The usage-limit message comes first:
it is read where the CLI writes it — stderr, the stdout lines that are not JSON,
the result text when the result is an error or the text is short, and the last
assistant text when it is under 200 characters (`run_fixtures.limit_line`) — and
never in a reply's prose or in tool results, so a job description, or a long
partial pack before a timeout, that mentions a usage limit is no kill; and a limit
hit as a resumed process starts, which exits non-zero with no init event, is never
read as a refused resume. Then, on a resumed turn, the refused-resume words, read
in the same places; then a timeout; then a non-zero exit; then an exit
0 whose stream is malformed; then an error result. A turn that answered — exit 0,
a result event that is no error — is completed, however short its reply and
whatever it mentions ("What a run keeps"). For a scenario, killed comes first, then
set aside, then a scan left unscored. A stopped scenario keeps every turn it
finished, and each turn's evidence. Each row has a test in `evals/test_harness.py`,
against a stub CLI on `PATH` that plays each outcome and answers as the graders.

### Checks and grades per turn

`<stem>.turn<k>.checks.json` holds the fixture runner's checks over the turn's
body (`run_transcripts.check_turn`), with three turn rules:

- The request is the cumulative user text, turn 1's prompt and every text sent
  through this turn, so a later turn quoting a line of turn 1's job description
  quotes the request; and the candidate's material is the `candidate_text`
  entries said by this turn.
- The research accounting runs only on a turn that declares `accounting`, on that
  turn's own research log, while a canned room's quotable pages are every page
  returned so far.
- `delivers` picks the watch-out rule. `output` is held to the declared line, as a
  fixture is; `gate_question` to the gate-only checks, with `gate_only:files` read
  over the files this turn changed, so an earlier turn's file is not this turn's;
  and `no_watch_out`, a turn inside an exchange such as a drill question, to
  `no_watch_out:chat`: no chat line labelled a watch-out, and the declared
  sentence nowhere in the chat.

A turn with `require_file` is checked for it (`turn_file`): the file, by its path
or its name, the room's before the scratchpad's, must be there after the turn and
written or changed in it. A turn not reached has each check it declares — its
`checks`, its watch-out rule's and `turn_file` — written as a failure, so a
missing turn never passes the checks it kept from applying, and a turn that is not
behaviour, such as a timeout, has a harness-invalid checks record. Every pass
writes the checks again from the saved evidence.

Each completed, scored turn is graded by each of `--graders` pinned graders, with
the transcript prompt, version `t1`. Its predecessor is the single-turn prompt's
version 3, which stays version 3. It keeps version 3's rules, fence and observed
block, and adds:

- `## The conversation so far`: each earlier turn's user text and its saved body,
  as its `reads` define it, between `===== TURN n: THE USER WROTE =====`, `=====
  TURN n: THE RESPONSE =====` and `===== END OF TURN n =====`, so a grader can
  read the pack a later turn is measured against;
- `## The request that was made`: this turn's text, with a note saying how the
  harness wrote any selected ID — which question of which turn's banks, read from
  which file;
- the observed block over this turn's own research calls alone; a nudged turn 1's
  says, where the first attempt made calls, that they are not credited to it.

Every grade file records the turn, the pass, `grader_prompt_version` `t1`,
`grader_prompt_predecessor` `3` and `grader_prompt_sha256`, the sha256 of the
template and the fixed parts it is filled with, beside the pinned and the
answering model, the CLI version, the flags and each expectation's hash before its
dates are written. A reply that misses some numbers is asked again once for them,
as a fixture's grader is, and a grade file is never overwritten. A killed scenario
is not graded, since it is run again from turn 1. A set-aside or harness-invalid
scenario's scored turns are graded and stay out of every denominator, and the
unnudged first attempt is never graded.

### Summary and exit codes

```
--- transcripts: mock-interview, via tuesday (plugin), model <id>, graders <id> ×2, prompt t1 ---
  mock-interview-drill.denied.run0  scored, 3/3 turns; first attempt fired
      turn 1: grader 1 9/9, grader 2 9/9, checks ok, file prep-pack.md
      turn 2: grader 1 4/4, grader 2 4/4, checks ok, selected Q B3
      turn 3: grader 1 5/5, grader 2 5/5, checks ok, file tuesday-dossier.md
  mock-interview-drill.denied.run1  set aside: timeout at turn 3: timed out after 900s (turns 1-2 saved)
  drill [denied] core screen (1 pair(s), every grader): 1 of 1 scored scenario(s) pass
batch: 2 scenario(s): 1 scored, 1 set aside (timeout 1), 0 killed, 0 harness-invalid; set aside 1/2 of the scenarios not killed (50.0%, limit 10%) — OVER THE LIMIT
nudged scenarios: 0 of 2 this pass
```

Per script, mode and turn, the expectations and checks are classified over the
scored scenarios as a fixture's are over its runs (`run_fixtures.classify`), turn
k's expectation n keyed `#t<k>.<n>` and its checks `t<k> chk:<check>:<target>`,
and a turn not reached gives each of its expectations a failing verdict, never
written as a grade file. The core screen is the joint pass of the script's `core`
pairs: a scored scenario passes it when every grader passed every pair, fails it
on one failing verdict, and is unresolved when a verdict is missing and none
failed. The batch line reads every scenario record in `--out` for the pass's
scripts and modes, whatever `--stems` lists, so a recovery pass that reruns a few
stems still reports the whole batch. It counts each outcome and cause apart, and
the share set aside or harness-invalid against the 10% limit over the scenarios
not killed: a proven kill is rerun, never set aside, so it is out of the
denominator; the partly graded block, the planted
events and, through Tuesday, `hidden-module reaches: N across M Tuesday attempt(s)
and T turn(s)`, every turn of every attempt read whole, follow.

The exit code is `0` when every scenario is scored and clean, `1` when an
expectation or a check failed, and `3`, which wins over `1`, when a scenario is
killed and not yet rerun, set aside or harness-invalid, an expectation or a core
screen is unresolved, a planned scenario has no record, a turn of this pass's
scenarios has a grade gap, or the pass was refused. A script refused at load, or a
flag misused, is argparse's `2`.

### Recovery

There is no retry pass and no `--retry-runs`: reruns are the killed-run protocol.

```bash
python evals/run_transcripts.py --scripts drill.json --out DIR --runs 5 --recover --move
python evals/run_transcripts.py --scripts drill.json --out DIR --model $M --grader-model $M --via tuesday \
  --stems DIR/killed/rerun-<UTC>.txt
python evals/run_transcripts.py --scripts drill.json --out DIR --grade-gaps --move --accept-partial
python evals/run_transcripts.py --scripts drill.json --out DIR --model $M --grader-model $M --via tuesday \
  --stems DIR/killed/regrade-<UTC>.txt --skip-execute
```

- `--recover` classifies each scenario per stem, never merged into one class:
  killed — a record left `running`, as a restart or the owner's guard leaves it; an
  in-flight record with no scenario record; or a usage-limit kill —, set aside,
  harness-invalid, scored, and never started, a stem the pass's `--runs` or
  `--stems` plans that has no record.
- `--recover --move` moves each killed scenario's files — its scenario record,
  turn records, bodies, checks, grades and scan — to `killed/`, never over a file
  there (`~<pass id>`). For a scenario the driver left running it also keeps the
  turn in flight: its stream moved to
  `killed/streams/<room>.<attempt>.t<k>.partial.jsonl`, its room and scratchpad
  snapshotted as `partial_evidence`, and a turn record with outcome `killed`; it
  marks the scenario killed and writes beside it the scan over everything it sent,
  the cut turn included, in place of the scan saved after its last finished turn.
  Each killed stem is matched to its script by its name across the whole scripts
  file, whatever `--script` selects; a scenario left running whose script the file
  does not hold is left in place, its in-flight records with it, and printed
  `left in place`, never listed for a rerun, so the scan of its cut turn is never
  lost: a pass with its scripts file recovers it. Rooms, finished turns' streams,
  snapshots and research files are named by room and stay where they are.
  `killed/rerun-<UTC>.txt` lists the killed and never-started stems; set-aside and
  harness-invalid stems are never listed.
- `--stems FILE` runs only the scenarios a file lists, one stem a line, each under
  its own run number and from turn 1 in a fresh room, and only in an `--out` that
  holds none of their files.
- `--skip-execute`, with or without `--stems`, checks the saved scenarios again
  and grades each stem, turn and grader with a saved body and no grade file.
- `--grade-gaps [--move [--accept-partial]]` is the fixture runner's ("Regrading a
  saved set"), per stem, turn and grader: each `grade-gaps.json` entry carries its
  `turn`, and the partly graded block names it.
- `--expect FILE` works as the fixture runner's. A pass records the driver's
  settings — the models, via, layout, graders, timeout, `retry_runs` 0, the
  scripts file's sha256 and the t1 prompt's — and a pass that differs from the
  folder's earlier ones is refused before any call.

These evals are not run in CI: they need a model, use the signed-in account's
weekly usage (or, with `ANTHROPIC_API_KEY` set, are billed per token), and take
minutes. What past measurements used is in `spend.md`. Run them in a session against any change that could plausibly move
triggering or output — a description edit, a new skill, a boundary reworded.
`evals/test_harness.py` does run in CI: every decline path above has a test that
spends no model calls.
