# Tuesday

Tuesday helps you look for a job with Claude. Give it a job posting and your CV (resume), and it tells you whether the role is worth your time, prepares you for the interview, or tailors your resume to the posting. Everything it suggests rests on what you have actually done: it asks about experience your CV leaves out, and it never coaches you to claim something your experience does not support.

Tuesday is one Claude skill, `tuesday`: a set of instructions Claude loads for this kind of task. It holds three modules, one for each job below, and runs the one your request needs. Each module also installs on its own (*Install*, below).

## What you can ask it

| You ask | It runs | You get |
|---|---|---|
| Should I apply for this role? (with the posting and your CV) | [`job-underwriter`](skills/job-underwriter/) | Each requirement checked against your experience; things you have done but left off your CV; which gaps are real, not just missing from your CV; risks in the role itself; and a decision: go, conditional go, hold or no-go |
| Help me prepare for my interview at this company | [`mock-interview`](skills/mock-interview/) | The questions each kind of interviewer is likely to ask, what a strong answer would draw on from your own background, questions for you to ask them, and, if you want, a live drill with Claude as the interviewer (not yet tested) |
| Tailor my resume to this job | [`resume-tailor`](skills/resume-tailor/) | Proposed edits, each tied to something you wrote; what the posting asks for that your resume cannot back up; and a check that screening software can read the file. Nothing changes until you approve it, and it never adds hidden text for automated screeners |

## How it works

- **It works from your evidence.** Every strength it names, answer it suggests and resume line it proposes traces back to something you told it or wrote. When something is missing, it asks; if you would rather not answer, it still finishes and says what it assumed.
- **Each module stands alone, and they share what they learn.** Each gives a complete, useful result from just a posting, a CV or a question. job-underwriter offers to save the evidence you confirmed in a file, `tuesday-dossier.md`, and mock-interview offers to add its notes. Keep the file (on claude.ai, download it), attach it to a later conversation, and whichever module runs starts from what is already there. Use one module or all three, in any order.
- **It tells you what to double-check.** Every result ends with one line naming what to check before you rely on it (*Watch-outs*, below).

## Install

Install either Tuesday or the modules on their own, not both side by side: a module Claude can choose competes with Tuesday for every request. (The plugin and the personal install contain the modules too, hidden so they do not compete.) Install each skill in one place only (*Keep one copy of each skill*, below). Which to use depends on where you use Claude:

| Where you use Claude | What to install |
|---|---|
| claude.ai, on the web or in the desktop app | `tuesday.skill`, or one module's `.skill` file |
| Claude Code, installed for yourself across your projects | The plugin (recommended), or a personal install in `~/.claude/skills/` |
| Claude Code, installed into one project's `.claude/skills/`, or Claude Code cloud sessions | The three modules, not Tuesday |

Why one skill: Claude picks a skill by reading its short description, so with Tuesday it reads one description instead of three.

### claude.ai, on the web and in the desktop app

Tuesday was tested in Claude Code only; on claude.ai it is untested. The desktop app uses the skills on your claude.ai account, so one upload covers both.

1. Turn on code execution: Settings → Capabilities → *Code execution and file creation*. On a Team or Enterprise plan, an owner turns on code execution and skills under Organization settings.
2. Download [`tuesday.skill`](dist/tuesday.skill) (on its GitHub page, use the download button), or one module's `.skill` file from [`dist/`](dist/). Not both: with both, Tuesday and the module compete for every request.
3. Under Customize → Skills, upload the file and switch it on.
4. In a new chat, attach your CV, paste the job posting and ask what you want, for example *Should I apply for this role?* You do not need to name the skill.

To get one module every time, upload only that module: claude.ai has no command for calling an uploaded skill by name, and naming a module at the start of a message was never tested. That is all for claude.ai; the rest of *Install* is for Claude Code.

### Claude Code: the plugin (recommended)

The plugin installs Tuesday, plus the three modules hidden from Claude's own choice of skill so they do not compete; your requests go to Tuesday. It is recommended because the quality of Tuesday's answers was tested through it; through a personal install, only the choice of module was tested. From your shell:

```
claude plugin marketplace add wavemanco/tuesday
claude plugin install tuesday@wavemanco-tuesday
```

- Inside a session, `/plugin marketplace add wavemanco/tuesday` and then `/plugin install tuesday@wavemanco-tuesday` do the same.
- To run one module directly, start your message with `/tuesday:job-underwriter`, `/tuesday:mock-interview` or `/tuesday:resume-tailor`.
- To try a local copy of this repository for one session, run `claude --plugin-dir /path/to/tuesday/dist/plugin/tuesday` from your own working folder. Started inside the repository, a session would have the modules' source files in its working folder, which Tuesday does not ship for (*Claude Code in a project*, below).
- The first time Claude Code asks to let Tuesday read its own files, allow it (*Let Tuesday read its own files*, below).
- Tests loaded the plugin from a local folder with `--plugin-dir`, in Claude Code only: the marketplace install from GitHub and the plugin on claude.ai are untested.

### Claude Code: personal install

Copy the four folders in [`dist/claude-code/`](dist/claude-code/) into `~/.claude/skills/`. The modules are hidden the same way; run one directly with `/job-underwriter`, `/mock-interview` or `/resume-tailor`.

### Let Tuesday read its own files

With the plugin or a personal install, Tuesday opens its own files, outside your working folder, as it runs. If Claude Code asks to read them, allow it; otherwise Tuesday answers without the module's instructions. To allow the reads ahead of time, which `claude -p` needs because nothing can ask, add the rule for your install with `--allowedTools` or under `permissions.allow` in your settings:

- the plugin: `Read(~/.claude/plugins/**)`
- a personal install: `Read(~/.claude/skills/**)`
- `--plugin-dir`: `Read(//path/to/tuesday/dist/plugin/tuesday/**)` (two slashes mark an absolute path)

Tuesday's third round of testing ran with such a rule (*Layouts* in [`evals/README.md`](evals/README.md)). Every test ran unattended, so the permission prompt itself is untested.

### Claude Code in a project, or in cloud sessions

Unzip `dist/job-underwriter.skill`, `dist/mock-interview.skill` and `dist/resume-tailor.skill` into the project's `.claude/skills/`, and each runs as `/<name>`. The `.skill` files leave out each module's `evals/`, as every test did.

Tuesday does not ship here. Hiding a module stops Claude from choosing it, but not from reading its files, and a project install puts those files in your working folder. In testing, Haiku found them there and once opened one directly, skipping Tuesday (*Tuesday, round 2* in [Tracked work](docs/tracked-work.md)).

If you use cloud sessions, keep `tuesday.skill` off your claude.ai account, whose skills they load: beside the project's modules it would make four skills compete, which was never tested.

### Keep one copy of each skill

A skill uploaded to claude.ai also reaches Claude Code: a terminal session signed in with your claude.ai account downloads it, and a cloud session loads it, where it competes with the plugin, a personal install or a project's skills. So where you use the plugin or a personal install, do not upload Tuesday or its modules to claude.ai, or set `syncClaudeAiSkills` to `false` in Claude Code's user settings on that machine; `/skills` lists what synced, under "claude.ai sync". For the same reason, do not also follow the install steps in a module's own README (`skills/<name>/README.md`).

### Which model

In Claude Code, where it was tested, Tuesday works best on Sonnet and Opus. On Haiku, start your message with the module's command: in testing, a command kept every model on the named module, while Haiku picked the right module on its own less often (*Tuesday, round 3* in [Tracked work](docs/tracked-work.md)).

## Watch-outs: what to double-check

Each skill ends its output with one sentence telling you what to double-check. With Tuesday, it is the sentence of the module it ran. Each one points at a problem that testing found and could not fully fix, so you know where to look. Here is each, as the skill writes it to you:

| Skill | Watch-out | Why it's there |
|---|---|---|
| job-underwriter | A summary line here can contradict the evidence table — before you act on a count, an "only" or an all-clear, check it against the table's rows. | About one test run in three (10 of 35 in round 9, after four rounds of fixes) still had a sentence about the requirements that the evidence table below it did not bear out: a count, an "only", or an all-clear like "you clear every must-have". See *Counts, rounds 7 to 9* in [Tracked work](docs/tracked-work.md). |
| mock-interview | Suggested answers can make your experience sound bigger than what you told me — rehearse only what you actually did, in your own words. | Suggested answers sometimes stretch what you said by one step: "proposed" becomes "drove", or a habit you never mentioned appears. Fixes halved it, but it still happened in at least four of every five test runs, on every test case. See *What was done about each* in [Tracked work](docs/tracked-work.md). |
| resume-tailor | The words I quote as yours beside each edit can differ slightly from what you wrote — before you approve a line or send the resume, check that quote and the new line against what you actually wrote. | The words quoted as yours beside a suggested edit came out slightly changed in about one test run in three, across three batches of tests, even after one fix, a rule to quote word for word. That was measured by graders in September 2026, on older text. A later automatic check of these quotes found the problem in 2 of 150 runs, both on Haiku. See *Cross-set recurrence* in [Tracked work](docs/tracked-work.md). |

**The rule behind this.** When two attempts to fix a problem have not fixed it, work stops and the maintainer decides, case by case: a watch-out, if checking something protects you; another attempt, with its own pass mark set in advance; or leaving it open. In every case, the problem stays on record in [Tracked work](docs/tracked-work.md) with how often it happens. The job-underwriter and mock-interview watch-outs came from this rule. resume-tailor's problem has had one fix, so the rule has not reached it; its watch-out is there because the maintainer asked every skill to carry one. The full rule is in [`CONTRIBUTING.md`](CONTRIBUTING.md#when-an-issue-survives-two-iterations).

## Tracked work

Changes to these skills are tested on Haiku, Sonnet and Opus against a pass mark set before the run, and [`docs/tracked-work.md`](docs/tracked-work.md) records every result: what was tested, what held, what missed, what was done about it and what was decided. It is long and detailed on purpose and not needed to use Tuesday, but it holds the evidence behind each watch-out and Install note, and shows how far to trust a number here. [`evals/spend.md`](evals/spend.md) records how much of the maintainer's weekly Claude subscription usage the testing used.

Not yet tested: Tuesday on claude.ai, and the plugin there; the marketplace install from GitHub; the permission prompt in a normal session, since every test ran unattended; answer quality through a personal install; cloud sessions with synced copies of the skills; live interview drills; replies after a conversation's first response; and live web search (tests used saved pages or none).

## For contributors

Issues are welcome from anyone. While the repository is early, only collaborators can open pull requests: the skills' contracts and the eval harness still change week to week, so an outside pull request would land on a moving target. The reasoning is in [`CONTRIBUTING.md`](CONTRIBUTING.md).

### What's shipped, what's next

All four skills have shipped: the three modules and [Tuesday](skills/tuesday/), which runs the module a request needs from its own copy of that module's instructions.

- **No new module is scheduled.** A fourth would make every existing routing case ambiguous again, so it would ship with its own routing tests and a re-run of the whole set (*Routing eval coverage* in [Tracked work](docs/tracked-work.md)).
- **Folded into existing modules instead:** employer-question strategy (now reverse questions and risk-verification questions), interview research briefs (research tiers and interviewer reads) and answer coaching (drill mode).
- **Deferred, each until its condition is met:** an application tracker, after repeated real use, since it must remember your applications between sessions; a work-sample strategist, first as a section of job-underwriter's application plan; networking and outreach; and a search diagnostician, which needs tracker data.

### Shared conventions

Coherence lives in [`conventions/`](conventions/), the rules every skill shares. Each skill installs on its own and needs nothing outside its folder to run, so it keeps exact copies of the conventions it uses in `references/`, each headed with its source file. If a copy and the original differ, the original wins: drift is a defect, and CI fails it.

- [`evidence-conventions.md`](conventions/evidence-conventions.md) — how evidence is graded and labelled: its source, how far to trust it, what kind of gap a missing requirement is, where each piece of text came from, and how these connect. It holds the truthfulness core every skill is bound by.
- [`interaction-grammar.md`](conventions/interaction-grammar.md) — how a skill works with you: a complete result from whatever you give it, what it asks and when, how it handles missing material, research depth, privacy and scope, which requests it takes, offers as text rather than fake buttons, and delivering what you are owed before offering extras.
- [`reframing-audit.md`](conventions/reframing-audit.md) — six axes of drift and five disciplines: the ways a reworded claim can grow past what you did, and the checks that catch it, applied to every word a skill proposes you say, write or send. It is shared because more than one skill writes words for you: job-underwriter proposes resume lines and outreach phrasing, and resume-tailor's whole output is proposed language. Kept in two places, it would drift apart exactly where it matters.
- [`output-discipline.md`](conventions/output-discipline.md) — seven rules on the shape of a delivered response. The first six each came from a problem found in testing; the seventh is the watch-out line every output ends with. Each rule has a fixed **invariant** and, where skills may legitimately differ, a **parameter** each skill sets in its `## Output discipline` block; CI fails a skill that leaves one out, since a default nobody chose is what this file exists to prevent. The split is there because the number was never what kept failing: two skills already said "at most three questions", but a question inside a template did not feel like it counted.
- [`citations.md`](conventions/citations.md) — the sources behind every figure, research finding, survey result and statement of law in the conventions, skills and specs, each quoted word for word beside its URL and what weakens it. Other text cites an entry rather than paraphrasing it. CI checks each marked quotation against its entry and flags a source quoted, or paraphrased in quotation marks, without a citation (`CONTRIBUTING.md` says what it misses); `ci/verify_citations.py` checks each entry against its source.
- [`dossier-schema.md`](conventions/dossier-schema.md) — the format of `tuesday-dossier.md`, the versioned file the skills share. Every skill reads it if it is there and never requires it; job-underwriter and mock-interview offer to add to it. Each section has one writer, and handoffs run both ways between those two.

### Repository layout

```
conventions/        the shared rules every skill follows
skills/<name>/      one self-contained folder per skill: SKILL.md, references/ and, in a module, evals/; Tuesday's references/ are generated
evals/              suite-level tests: routing between skills, which no single skill can test, and the harness for each skill's own test cases
ci/                 repository checks, standard-library only, with their own self-test
dist/               built installables: .skill files, the Claude Code builds and the plugin
.claude-plugin/     the marketplace file that lists the plugin
agent/              reserved; does not exist yet
```

Every build in [`dist/`](dist/) is made from `skills/` by `ci/package.py`, and CI fails a build that is out of date.

## Licensing

MIT: see [`LICENSE`](LICENSE). `conventions/` and each skill folder carry their own copy of the same grant, so a packaged skill travels with its license. Skills come first. A separate agent built on the same conventions may follow, in a future `agent/` directory planned to carry its own copyleft license, AGPL-3.0; contributions to it will require a contributor agreement, and [`CONTRIBUTING.md`](CONTRIBUTING.md) explains both.

## Why "Tuesday"

Tuesday is *Mangalvaar* in Hindi: the day of Mangal, which names Mars and is also a word for auspiciousness. An auspicious day that belongs to the god of war suits what Tuesday does: it puts you on a deliberate, well-armed path to the right opportunity instead of a spray of hopeful applications, and the only ammunition it ever hands out is verified evidence. (Job-market folklore also holds that postings and applications peak on Tuesdays; treat that as a wink, not a citation.)
