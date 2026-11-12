# Tuesday

Tuesday helps you look for a job with Claude. Give it a job posting and your CV, and it tells you whether the role is worth your time, prepares you for the interview, or tailors your resume to the posting. Everything it suggests rests on what you have actually done: it asks about experience your CV leaves out, and it never coaches you to claim something your experience does not support.

## What you can ask it

| You ask | It runs | You get |
|---|---|---|
| Should I apply for this role? (with the posting and your CV) | [`job-underwriter`](skills/job-underwriter/) | Each requirement checked against your experience; things you have done but left off your CV; real gaps told apart from omissions; risks in the role itself; and a decision: go, conditional go, hold or no-go |
| Help me prepare for my interview at this company | [`mock-interview`](skills/mock-interview/) | The questions each kind of interviewer is likely to ask, what a strong answer would draw on from your own background, questions for you to ask them, and, if you want, a live drill with Claude as the interviewer |
| Tailor my resume to this job | [`resume-tailor`](skills/resume-tailor/) | Proposed edits, each tied to something you wrote; what the posting asks for that your resume cannot back up; and a check that screening software can read the file. Nothing changes until you approve it, and it never adds hidden text for automated screeners |

Install Tuesday and it picks the right one of the three from what you ask, or install any of them on its own (*Install*, below).

## How it keeps you honest

- **It works from your evidence.** A strength it names, an answer it suggests or a resume line it proposes traces back to something you told it or wrote. Where it lacks something, it asks you, and if you would rather not answer, it still finishes and says what it assumed.
- **Each skill stands alone.** Each one gives a complete, useful result from just a posting, a CV or a question. Used together, they share what they learn: job-underwriter offers to save a `tuesday-dossier.md` file with the evidence you confirmed, and the other two start from it if it is there. Use one, use them all, in any order.
- **It tells you what to double-check.** Each result ends with one line telling you what to check before you rely on it, where testing found a problem that is not fully fixed (*Watch-outs*, below).

## Install

Tuesday is one skill, `tuesday`, that reads your request, picks the module it needs (job-underwriter, mock-interview or resume-tailor) and runs it. Claude chooses a skill by reading each skill's short description, so with Tuesday it reads one description instead of three. The three modules also install on their own, as separate skills. Which to use depends on where you use Claude. Every build is in [`dist/`](dist/), made from `skills/` by `ci/package.py`; CI fails a build that is out of date.

**Claude Code: the plugin (recommended).** It installs Tuesday with the three modules hidden from Claude's own choice. From your shell:

```
claude plugin marketplace add wavemanco/tuesday
claude plugin install tuesday@wavemanco-tuesday
```

Inside a session, `/plugin marketplace add wavemanco/tuesday` and then `/plugin install tuesday@wavemanco-tuesday` do the same. To try a local checkout for one session, start Claude Code in your own working folder, not in the checkout, and give the plugin's full path: `claude --plugin-dir /path/to/tuesday/dist/plugin/tuesday`. A session started in the checkout would have the modules' source files in its working folder, which is the setup Tuesday does not ship for (below). Requests go to Tuesday; to run one module directly, start your message with `/tuesday:job-underwriter`, `/tuesday:mock-interview` or `/tuesday:resume-tailor`. The plugin has been tried in Claude Code only, not as a claude.ai plugin.

**Claude Code: personal install.** Copy the four folders in [`dist/claude-code/`](dist/claude-code/) into `~/.claude/skills/`. The modules are hidden the same way; run one directly with `/job-underwriter`, `/mock-interview` or `/resume-tailor`.

**Let Tuesday read its own files.** With the plugin or a personal install, Tuesday's files sit outside your working folder, and it opens them as it runs. If Claude Code asks to read them, allow it; otherwise Tuesday cannot open a module's instructions and answers without them. To allow it ahead of time, which `claude -p` needs because nothing can ask, add a rule with `--allowedTools` or under `permissions.allow` in your settings: `Read(~/.claude/plugins/**)` for the plugin, `Read(~/.claude/skills/**)` for a personal install, or `Read(//path/to/tuesday/dist/plugin/tuesday/**)` for `--plugin-dir`. Round 3 measured Tuesday with such a rule (`evals/README.md`, "Layouts").

**Claude Code in a project, or in cloud sessions: the three modules, not Tuesday.** Unzip `dist/job-underwriter.skill`, `dist/mock-interview.skill` and `dist/resume-tailor.skill` into the project's `.claude/skills/`; each runs as `/<name>`, and each leaves out its `evals/`, as every measurement did. Tuesday does not ship here: a hidden module is hidden from Claude's choice but not from its file reads, and a project install puts the modules' files in the working folder, where in testing Haiku found them and once opened one directly, skipping Tuesday ("Tuesday, round 2" under [Tracked work](docs/tracked-work.md)). Cloud sessions load the skills enabled on your claude.ai account, and a project's cloud threads load only those, so where you use cloud sessions, keep `tuesday.skill` off that account: beside the three project copies it would make four skills compete, which was never measured.

**claude.ai, on the web and in the desktop app.** Enable code execution (Settings → Capabilities), then upload under Customize → Skills either [`dist/tuesday.skill`](dist/tuesday.skill) alone or one module's `.skill`, never both: with both, Tuesday and the module compete for every request. The desktop app follows your claude.ai account. claude.ai has no slash command for an uploaded skill, and naming a module at the start of a message was never tested, so to get one module dependably there, upload that module alone. Tuesday was measured in Claude Code only; on claude.ai it is untested.

**Which model.** In Claude Code, where it was measured, Tuesday works best on Sonnet and Opus. On Haiku, start with the module's command: a command kept every model on the module it named, while Haiku picked the right module on its own less often ("Tuesday, round 3" under [Tracked work](docs/tracked-work.md)).

**Keep one copy of each skill.** A skill uploaded to claude.ai also reaches Claude Code: a terminal session signed in with your claude.ai account downloads it, and a cloud session loads it. There it competes with the plugin, a personal install or a project's skills. On a machine where you use the plugin or a personal install, upload nothing to claude.ai, or set `syncClaudeAiSkills` to `false` in Claude Code's user settings there; `/skills` lists what synced, under "claude.ai sync". For the same reason, do not also install a module the way its own README describes.

## Watch-outs: what to double-check

Each skill ends its output with one sentence telling you what to double-check. Each one is there because we measured a problem in testing and could not fully fix it, so the skill tells you where to look instead.

| Skill | Watch-out | Why it's there |
|---|---|---|
| job-underwriter | A summary line here can contradict the evidence table — before you act on a count, an "only" or an all-clear, check it against the table's rows. | In testing, about one run in three still had a sentence about the requirements — a count, an "only", or an all-clear like "you clear every must-have" — that the evidence table below it did not bear out: 10 of 35 runs in the latest round, after four rounds of fixes. See "Counts, rounds 7 to 9" under [Tracked work](docs/tracked-work.md). |
| mock-interview | Suggested answers can make your experience sound bigger than what you told me — rehearse only what you actually did, in your own words. | Suggested answers sometimes stretch what you said by one step — "proposed" becomes "drove", or a habit you never mentioned appears. Fixes halved it, but it still happened in at least four test runs out of five on every test case. See "What was done about each" under [Tracked work](docs/tracked-work.md). |
| resume-tailor | The words I quote as yours beside each edit can differ slightly from what you wrote — before you approve a line or send the resume, check that quote and the new line against what you actually wrote. | The quotes of your own words beside each suggested edit came out slightly changed in about one test run in three (33%), across three separate batches of tests, even after a rule saying to quote word for word. That was measured in September 2026, after one fix, and has not been measured since. See "Cross-set recurrence" under [Tracked work](docs/tracked-work.md). |

**The rule behind this.** When two attempts to fix a problem have not fixed it, we stop and the maintainer decides what happens next, case by case: a watch-out, if checking something protects you; another attempt, with its own bar set in advance; or leaving it open. Whichever it is, the problem stays on record in [Tracked work](docs/tracked-work.md) with how often it happens. The full rule is in [`CONTRIBUTING.md`](CONTRIBUTING.md#when-an-issue-survives-two-iterations).

## What's shipped, what's next

| Status | Skill | What it does |
|---|---|---|
| **Shipped** | [`skills/mock-interview`](skills/mock-interview/) | Interview preparation: questions by interviewer, grounded answer guidance, live drill |
| **Shipped** | [`skills/job-underwriter`](skills/job-underwriter/) | Should you apply: evidence check, recovered experience, role risks, a go / no-go decision, and the dossier it offers to save |
| **Shipped** | [`skills/resume-tailor`](skills/resume-tailor/) | Resume tailoring where every edit traces to your own words, and nothing is applied until you approve it |
| **Shipped** | [`skills/tuesday`](skills/tuesday/) | Tuesday, not a module: one skill that runs the module a request needs, from a copy of that module's instructions, so Claude reads one skill's description to choose instead of three. It ships as the Claude Code plugin, as a personal install, and as a claude.ai upload on its own (*Install* below) |
| **Planned next module** | — | Nothing is next by default. The deferred list below is trigger-gated, and the suite's own measurement says a fourth module makes every routing case ambiguous again |
| **Absorbed** | Employer-question strategy, interview research briefs, answer coaching | Already live inside mock-interview and job-underwriter (reverse questions + risk-verification questions; research tiers + interviewer reads; drill mode) |
| **Deferred, trigger stated** | Application tracker (trigger: repeated real use — it's a persistence product), work-sample strategist (first life: an underwriter plan section), networking/outreach, search diagnostician (needs tracker data) | Built when their triggers fire, not before |

## Shared conventions

Coherence lives in [`conventions/`](conventions/) — canonical, and mirrored into each skill's `references/` with a synced-from header (canonical wins on conflict):

- [`evidence-conventions.md`](conventions/evidence-conventions.md) — evidence source types, confidence bands, the gap taxonomy, content provenance labels, and the mapping that connects them. The truthfulness core every skill is bound by.
- [`interaction-grammar.md`](conventions/interaction-grammar.md) — the standalone invariant, elicitation policy, degradation and upgrade menus, research tiers, privacy and scope, trigger hygiene.
- [`reframing-audit.md`](conventions/reframing-audit.md) — six axes of drift and five disciplines, covering every word a skill proposes the candidate say, write, or send. Canonical because it is not one skill's property: job-underwriter proposes resume lines and outreach phrasing, resume-tailor's whole output is proposed language, and two copies of it would diverge in exactly the two places it is load-bearing.
- [`output-discipline.md`](conventions/output-discipline.md) — seven rules on the shape of a delivered response, the first six each learned from a measured defect and the seventh the watch-out line every delivered output ends with. Each rule has an **invariant** the suite holds absolutely and, where variation is legitimate, a **parameter** each skill declares for itself, because the half that kept failing was never the number: two skills already said "at most three questions" and what broke was that a question inside a template did not feel like it counted. Skills declare their parameters in a `## Output discipline` block and CI fails a skill that omits one — a default nobody chose is the failure this file exists to prevent.
- [`citations.md`](conventions/citations.md) — the sources behind every figure, research finding, survey result and statement of law in the conventions, the skills and the specs, each quoted verbatim beside its URL and what weakens it. Prose cites an entry rather than paraphrasing it; CI checks each marked quotation against its entry and flags a source quoted, or paraphrased in quotation marks, without one — what it cannot see is in `CONTRIBUTING.md` — and `ci/verify_citations.py` checks every entry against its source.
- [`dossier-schema.md`](conventions/dossier-schema.md) — the versioned shared artifact: read-if-present, append-always-offered, never required. One writer per section; handoffs in both directions.

## Repository shape

```
conventions/        the shared rules every skill follows
skills/<name>/      self-contained skill packages: each module's SKILL.md, references/, evals/ and docs/; Tuesday's SKILL.md and generated references/
evals/              suite-level evals — routing between skills, which no single skill can test
ci/                 repository checks, standard-library only, with their own self-test
dist/               built installables: .skill files, the Claude Code builds and the plugin
.claude-plugin/     the marketplace file that lists the plugin
agent/              (reserved — does not exist yet; arrives when its trigger fires)
```

Skills come first. A separate agent built on the same conventions may follow, in `agent/`, under its own license (*Licensing*, below).

Skills are dependency-free by rule: nothing outside a skill's folder is required at runtime, because installation is per-skill. The conventions are therefore a canonical-plus-mirrors system, not a runtime import; mirror drift is a defect.

## Why "Tuesday"

Tuesday is *Mangalvaar* in Hindi — the day of Mangal, which names Mars and is also a word for auspiciousness. An auspicious day belonging to the god of war is exactly this system's register: it puts the applicant on a deliberate, well-armed path to the right opportunity rather than a spray of hopeful applications — and the only ammunition it ever issues is verified evidence. (Job-market folklore also holds that postings and applications peak on Tuesdays; treat that as a wink, not a citation.)

## Licensing

MIT — see [`LICENSE`](LICENSE). `conventions/` and each skill folder carry their own copy of the same grant, so a packaged skill travels with its license. A future `agent/` directory is planned to carry its own copyleft license (AGPL-3.0) when it exists; that, and the contributor agreement it will require, are in [`CONTRIBUTING.md`](CONTRIBUTING.md).

While the repository is early, only collaborators can open pull requests: the skills' contracts and the eval harness still change week to week, so an outside pull request would land on a moving target. Issues are welcome from anyone. The rationale is in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Tracked work

Changes to these skills are measured on Haiku, Sonnet and Opus against a bar set before the run, and [`docs/tracked-work.md`](docs/tracked-work.md) records every result: what was tested, what held, what missed, what was done about it and what was decided. It is long and detailed on purpose, and you do not need it to use Tuesday. Read it for the evidence behind a watch-out or an Install note, or to see how far to trust a number in this README. What the measurements used of the account's weekly usage is in [`evals/spend.md`](evals/spend.md).
