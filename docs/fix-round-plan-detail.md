# The fix round: plan and bar in full

This document is the plan for the fix round and the bar the round is held to, in full.
`fix-round-plan.md` is its short version, and where the two differ this one holds. It
is in the repository before any measured run, so the bar is fixed in advance. Once the
owner approves it, nothing in sections 4 and 5 changes.

## 1. What this round is for

The quality check through Tuesday ran every fixture of the three modules through
Tuesday and with each module alone, on Sonnet, Haiku and Opus 5.5. The routing rounds
measured which skill each request reaches. Together they left a list of misses, gaps
and proposed fixes, verified in one summary (appendix). The owner chose to make every
fix at once, in three steps:

1. Before any run: one text change, and the harness, check and fixture changes that
   the owner's decisions call for (section 2).
2. One measured round, after the weekly usage meter resets on Thursday 12 November
   2026 at 06:00 UTC (section 3), held to the bar in section 4.
3. A record of the result: the README ledger, and CI's record of measured text if
   the bar is met (section 5).

The round answers four questions:

- Does each module do as well through Tuesday as alone, now that both arms install
  it the same way? The quality check's alone arm used an older install, so its gaps
  could not be read as Tuesday's.
- Did the text change fix what it aims at: more than one sentence after
  job-underwriter's fit ledger, and research calls beyond a quick check of what the
  user pasted?
- Does routing still hold? The change touches text Claude reads after Tuesday fires
  and after a slash command.
- What do Opus case 10 and Haiku case 3 look like with ten times the runs?

### Terms

These words are used throughout and explained once here.

- **Module.** One of the three job-search skills: job-underwriter, mock-interview and
  resume-tailor. **Tuesday** is the skill that sends each request to one module and
  runs it from its own copy of that module's instructions.
- **Fixture.** A saved request that a module is tested on, with the expectations a
  good answer meets (each module's `evals/evals.json`). A fixture runs in one or two
  **research rooms**: *denied*, where every web call is refused, and *canned*, where
  a stub server answers with saved pages.
- **Run.** One fresh, headless Claude Code session that answers one fixture in one
  room.
- **Arm.** One of the two ways a comparison installs a module. *Alone* installs the
  module by itself, exactly as Tuesday is installed (`--layout plugin`). *Through
  Tuesday* installs Tuesday with the three modules hidden, as the plugin ships.
- **Grader.** A separate Sonnet session that reads a run's response and passes or
  fails each expectation. Every run has two. The **graded pass rate** is the share of
  all their verdicts that pass.
- **Automatic check.** Code in `evals/output_checks.py` that reads a response for one
  rule, with no model. A **check family** is a set of checks that read one defect,
  counted once per run, so one defect is never counted twice (`evals/README.md`,
  "Comparing two arms").
- **Nudge.** When a run through Tuesday does not reach its module, the harness runs
  it once more in a fresh room with Tuesday named. Nudged runs count, and they are
  reported.
- **Set aside.** A run that says nothing about the skill, such as one whose module
  never ran even after a nudge, or whose canned room never connected. It is kept out
  of every rate. The harness calls such a run harness-invalid.
- **Routing case.** A saved request in `evals/suite-routing.json`, scored by which
  skill it reached. *Today's skills* are the three modules installed alone as personal
  skills. An *explicit command* is a message that opens with a module's slash command.
- **p.** How often luck alone would produce a gap at least this large: an exact
  two-sided Fisher test on runs, unless a section says otherwise.
- **False-alarm rate and power.** A false-alarm rate is how often an item would miss
  with no real change. Power is how often it would catch a real change of a stated
  size. Section 4 gives both for every gated item, and section 4.5 for the whole bar.
- **Meter.** The account's weekly usage meter, read in percent. A "point" is one
  percentage point of it.

The labels G1 to G5 and H1 below are the verified summary's names for its proposed
text fixes and for the open issue it numbered first.

### The owner's decisions this round rests on

All ten are final.

1. One round: one text change, then one measured round after the weekly reset, with
   its bar fixed before it runs.
2. A re-cut quote is not a defect. A re-cut quote is the candidate's own words,
   verbatim, cut otherwise than the fit snapshot cuts them. No question is added about
   it, since mock-interview's watch-out already asks the user to check. So there is
   no quoting text change, and the checks pass re-cut quotes and keep reporting them.
3. A quick, reported check that the user's material is still current and genuine, a
   couple of calls, is not a defect, in either module. Opus's one news search on
   mock-interview eval 8 is one; job-underwriter's look at a pasted posting and its
   company on eval 5 is another. The research rules and checks allow it and keep
   reporting it, and calls beyond a quick check still count.
4. Runs may save inside their room, in both arms, as a user who approves the save
   would.
5. Tuesday's description stays as it is until a fourth module is planned.
6. The quality check's saved runs are not regraded. This round re-runs both arms with
   the matched install.
7. One folder per application is agreed, and is measured on its own after this round.
8. Mock-interview's watch-out line stays as it is.
9. The standing rules hold. A bar is fixed before its run. An issue that two
   iterations have not closed goes to the owner (`CONTRIBUTING.md`, "When an issue
   survives two iterations"). Fixtures model what users typically send. Documentation
   says each thing once, in plain sentences. The old working name for Tuesday appears
   in no README.
10. Opus routing case 10 stays open, and Haiku case 3 is not gated.

## 2. Step 1: before any run

Step 1 runs in this order, and none of it spends a model call:

1. **This plan**, in this document and its short version, approved by the owner. It
   fixes the bar.
2. **The harness commit.** The harness, check, fixture and documentation changes in
   section 2.2. It changes no shipped file, so CI passes in full.
3. **The text commit.** The one text change in section 2.1, with its generated
   copies, its builds, and the CI edits that only pass with the new text. Two of CI's
   steps fail on it until the round is scored (section 2.3).
4. **A dry run of the record commit**, on a scratch copy, which must pass every CI
   step (section 2.3).
5. **A re-check of the saved runs** under the harness commit's checks (section 2.4).

### 2.1 The one text change

The text change edits seven sources by hand: Tuesday's `SKILL.md`, `ci/sync.py`,
`conventions/interaction-grammar.md`, mock-interview's
`references/research-checklist.md`, and job-underwriter's `SKILL.md`,
`references/risk-and-decision.md` and `references/dossier-worked-report.md`.
Everything else that changes is generated by `ci/sync.py` (the mirrors and Tuesday's
`references/`) or built by `ci/package.py` (`dist/`). No skill's description changes,
so nothing in this change can move whether Tuesday fires at all.

The text quoted in this section is the only source for the change. A scratch copy of
the current commit with these seven sources edited as quoted here, synced and built,
fails only the group that guards measured text, and `sync.py --check` and
`evals/test_harness.py` pass. The CI and README edits listed below have not been built
yet; the dry run in section 2.3 checks the whole commit.

#### G1. Remove the old name from the three places Claude reads it

The old working name, "front door", is replaced in the three places Claude reads it.
No routing prompt and no nudge contains it.

| Where | Now | New |
|---|---|---|
| Tuesday's `SKILL.md`, line 8 | "Tuesday is one front door to three job-search modules." | "Tuesday is one skill that holds three job-search modules." |
| `PATHS_NOTE` in `ci/sync.py`, generated into each of Tuesday's three playbooks | "The front door runs this playbook: … (the front door's own instructions, section 3)." | "The `tuesday` skill runs this playbook: every `references/` path in it, and in the files it names, means the folder that holds this file, never a module's own skill folder, even one a listing shows (the `tuesday` skill's own instructions, section 3)." |
| The slash-command rule in `interaction-grammar.md` §6, mirrored into every module and into Tuesday's `references/` | "not a front door that routes between the skills" | "not the `tuesday` skill that routes between the modules" |

Why each:

- "Holds" is literally true, since the modules' instructions sit in Tuesday's
  `references/`. The next sentence already says each turn runs at most one module.
- The paths note keeps what the harness test requires of it: it says "section 3",
  never "SKILL.md", and links no file. Its bold label "Paths." is unchanged.
- In `interaction-grammar.md`, "Tuesday" names the suite, so the skill is written
  `tuesday`, in code. The rule's bold label, which CI reads, is unchanged.

The same commit adds the two-word name to the retired wordings that `check_skills.py
--only wording` fails, so it cannot come back unnoticed in any file that group reads,
and adds one clause naming it to `CONTRIBUTING.md`'s paragraph that lists every phrase
that group reads ("Retired wordings stay retired"). Comments, messages and identifiers
in `ci/` and `evals/` are left to a separate tidy-up (section 8, question 3).

#### G2. Tuesday's row in the routing table, and the install line

`interaction-grammar.md` §6 gains a row after resume-tailor's:

```
| `tuesday` | Candidate-side job-search requests, routed to one module per turn | Not for employers screening applicants, job-market questions, networking messages, resume design, proofreading, or shortening a resume with no target role |
```

Under the table it gains one paragraph: "Where Claude chooses among installed skills,
install the `tuesday` skill or the modules, never both: side by side they compete for
every request. The Claude Code builds carry the modules beside it but hide them from
that choice."

Why:

- The README's backlog asks for both.
- The row's boundary is the end of Tuesday's own description, word for word. That is
  the test CI's triggers group applies to every module's row.
- The install line is qualified because the plugin and the personal install do ship
  the modules beside Tuesday, hidden. An unqualified "never both" would be false
  there.
- Tuesday's `SKILL.md` (section 3) and the paths note already say the modules' own
  folders can sit beside Tuesday. What is new is that each module's own copy of
  `interaction-grammar.md`, which the module reads when it runs alone or from its
  command, now says that Tuesday and the modules are installed together. Routing
  reports every run that reaches Tuesday's files by path or names the folder that
  holds the skills (section 4.3), so any effect of that is diagnosed run by run.

The triggers group today prints an exemption that this row makes false, so the same
commit changes three things:

- `HUB_EXEMPT["triggers"]` in `ci/check_skills.py`, which says Tuesday has no row,
  becomes: "it has no line pointing to interaction-grammar.md §6's slash-command rule:
  that rule stops a module started by its own command from starting another skill,
  and Tuesday starts none, since it runs a module from its own references/
  (skills/tuesday/README.md, beside its routing role)".
- `check_triggers` reads every skill's row against its description, Tuesday's
  included, and keeps the pointer half on modules only. `ci/test_checks.py` gains two
  mutations: Tuesday's row removed, and a boundary word missing from its description.
- Line 11 of `skills/tuesday/README.md` becomes: "Tuesday's row in the trigger-hygiene
  table of `interaction-grammar.md` §6 carries the boundary its description ends with.
  Its SKILL.md has no line pointing to that section's slash-command rule: the rule
  stops a module started by its own command from starting another skill, and Tuesday
  starts no skill at all, since it runs a module from its own `references/` (section
  3)."

#### Decision 3. A quick, reported check of pasted material

Today two things make such a check a breach. The depth rule in
`interaction-grammar.md` §4 skips any search that cannot change an output, and a
pasted page can already fix an output. And the two fixtures that test it,
job-underwriter eval 5 and mock-interview eval 8, both say "no search or fetch is
sent".

The labels need no change. A quick check is a call that was sent, so its target reads
`yes` if any call returned, or `unavailable` if every call was refused or errored, and
never `skipped` or `n/a`. The fixed tally line already counts every call. Every quick
check in the saved runs was already labelled this way.

The text change makes three edits.

1. In `interaction-grammar.md` §4, after "…that row is the visible form of a wasted
   search.", it adds: "At L1 or L2, a quick check that pasted material is still
   current and genuine is not a wasted search, since a stale or false copy would
   change what it feeds: at most two calls, searches and fetches together, each aimed
   at a target the material answers and naming the company, document or page it
   checks. That target then reads `yes`, or `unavailable` if every call was refused or
   errored, and its row says the call checked the pasted material and what it moved."
   The later sentence on the host is scoped to match: "A target the inputs answer,
   with no call sent for it, reads `skipped` whether or not this host could have
   searched for it."
2. In mock-interview's `references/research-checklist.md`, after the paragraph that
   keeps L1 searches to its targets, it adds: "Material the user pasted answers the
   target it covers, as a pasted values page answers target 1 and a strategy brief
   under ~6 months old answers target 3, and that target gets no search beyond the
   quick check of the material that `interaction-grammar.md` §4 allows."
3. In job-underwriter's `SKILL.md`, Step 2, after the sentence that sends the reader
   to `interaction-grammar.md` §4 for the labels, it adds:
   "`references/interaction-grammar.md` §4 also says what quick check of pasted
   material may still run."

Why each piece:

- "At L1 or L2", the research tiers that send calls: research at L0, and research the
  user declined, stay strict.
- "Would change what it feeds" puts the check inside the depth rule, rather than
  beside it as an exception.
- "At most two calls": the quick checks in the saved runs were one call (Opus's news
  search) or two (Sonnet's fetch of the posting and a search for the company). Every
  input to this plan proposed two for the owner's "a couple". The harness and the
  fixtures use the same number, and CI ties them.
- "Naming the company, document or page it checks" says in the text what the check
  enforces. A search for more of the same kind, such as "senior data engineer salary
  US 2026", hunts; it does not check.
- The scoping clause keeps a refused check's `unavailable` from contradicting the
  sentence about the host.
- The mock-interview paragraph replaces the summary's one-line proposal for target 3
  (a pasted brief answers it), now that a quick check of the brief is allowed.
- job-underwriter's line is only a pointer. §4 already says that a pasted page fixes
  the outputs it covers, so the line does not say it again. Its `SKILL.md` body is
  close to the guidance group's limit, about 4,942 of 5,000 estimated tokens with the
  line. It names its file in full, because a bare section number there fails the
  sections group.

#### H1. More than one sentence after the fit ledger (iteration 1)

The rule is `risk-and-decision.md` rule 2, which allows at most one sentence after the
fit ledger. The check is `ledger_sentence`, which CI's fit-ledger group and the harness
both run through `ci/ledger_rules.py`.

What the saved runs with a ledger show, 207 in all, counting the sentences after the
ledger:

- A second sentence appears on every model, alone and through Tuesday, in 131 runs.
  Alone, then through Tuesday: Sonnet 19 of 40 and 12 of 40, Haiku 15 of 20 and 20 of
  27, Opus 33 of 40 and 32 of 40.
- It always sits in one paragraph directly under the ledger. In 92 of the 131 runs the
  second sentence reads a different group of rows from the first.
- The worked example teaches two readings joined by ", and". Writers copy the two
  readings but not the conjunction. Runs that pass join the same two readings in one
  sentence.
- On Opus it fails in every run of 4 of 8 fixture-rooms alone and 3 of 8 through
  Tuesday, and elsewhere it persists across two measured sets. The smoke, on the
  matched install, showed the same: Opus 4 of 4, Sonnet 1 of 4.

`CONTRIBUTING.md` would allow one rewording first, but it asks of any fix that a
compliant and a non-compliant output differ at a glance, and a reworded sentence would
not: two sentences and one long one look alike. So the change is to the slot's shape:
the sentence becomes a list in the ledger's own notation, so two readings are one
sentence by construction.

- Rule 2's tail, "Then at most one sentence on what matters: it names the rows it is
  about, and any set claim it makes is judged under…", becomes "Then at most one
  sentence on what matters, written as a list so that two readings stay one sentence:
  an item for each row, or group of rows, it reads, each item its row IDs, a dash and
  a few words, and the items separated by semicolons. Any set claim it makes is judged
  under…". The rest of the rule is unchanged.
- The worked sentence in `dossier-worked-report.md`, "R4 has a credible bridge with
  its limit named, and R3 (`medium`) is confirmed but waits on an artifact.", becomes
  "R4 — a credible bridge, its limit named; R3 (`medium`) — confirmed, waiting on an
  artifact."
- The worked example says what it taught, as `CONTRIBUTING.md` asks ("A worked
  example is part of the rule"). The commentary after the snapshot's slots, which the
  fit-ledger group does not read, gains one sentence: "An earlier version of the
  sentence under the ledger joined two readings with ", and"; runs copied them as two
  sentences, which rule 2 forbids, so each reading is now an item of one list."

Why this shape, and not another:

- It keeps "the one sentence after the fit ledger", which `evidence-model.md`, CI's
  checks and the fixtures' expectations all anchor on.
- A bulleted list would break the ledger's parsing.
- Removing the sentence would ripple through every file that anchors on it, and would
  push the readings into the next free-text surface.
- Allowing two sentences that each name their rows would pass most saved runs, but it
  changes what counts as compliant, which is the owner's call (section 8, question 2).

The same commit carries the check and its tests:

- `ledger_sentence` keeps its verdicts exactly as they are. It is the gated reading.
- A new reading, `ledger_sentence_form`, in `ci/ledger_rules.py`: each
  semicolon-separated item opens with row IDs, a band beside them allowed, then a dash.
  Its prototype passes the new worked line, fails the old one, and passes only 4 of the
  207 saved regions, the ones with no sentence. So it measures uptake of the form
  apart from the sentence count. CI's fit-ledger group holds the worked sentence to
  it. The harness records it on runs, and `compare_arms` prints its uptake as a
  reported row and leaves it out of the units it gates, by name, with a test.
- `ci/test_checks.py` moves six constants to the new worked sentence, then gains form
  mutations and must-pass cases. `evals/test_harness.py` gains form cases.
- `CONTRIBUTING.md`'s fit-ledger paragraph and `evals/README.md`'s list of checks each
  gain one sentence on the form.

#### What the text change leaves alone

- Every quoting rule (decision 2).
- Tuesday's description (decision 5).
- Mock-interview's watch-out line (decision 8). Haiku's watch-out slips through
  Tuesday, 6 of 50 runs against 1 of 50 alone (p ≈ 0.11), get no text either. The gap
  is within chance. Two of the slips put the line in a saved file, and this round
  changes saving. A Tuesday-side line would be a second change on the same check, so
  the round could not tell which one worked.
- resume-tailor's trace rule. The new traces check fails 2 of 150 saved runs; the 33%
  in its watch-out row came from graders reading older text (section 8, question 4).

### 2.2 Harness, check and fixture changes

All of these go in the harness commit. None touches a shipped file or the skill text a
room installs, so `MEASURED_FRONTDOOR` does not move. That `check_skills.py --only
frontdoor` and `--only builds` pass with the constant untouched is one of this commit's
gates. The figures below come from re-checking the saved runs under a prototype of
each change.

#### a. Runs may save inside their room (decision 4)

What the smoke showed. Rooms run in the CLI's default permission mode, which refuses
any save that no rule allows. In a plugin install the room is empty and is the model's
working folder; the model aimed its first save at it, and the save was refused. After a
refused save, 4 of the 24 plugin-installed mock-interview runs delivered their pack
only in chat. The quality check's refused saves had the same cause.

The change:

- `run_fixtures.plugin_flags`, which both arms go through, adds one allow rule,
  `Edit(//<room>/**)`, to the room's one `--allowedTools` list, beside the existing
  read rule. When the room is reached through a symlink, a second rule names its
  resolved path.
- It is a rule, not a permission mode. A mode is session-wide and can approve some
  shell commands, while decision 4 covers saves only. The rule models a user who
  answers the save prompt with "allow edits in this folder".
- It reaches only the room. The plugin folder is the room's sibling and stays
  unwritable, and saves aimed anywhere else are still refused and recorded.
- The project layout gets no rule, since this round does not use it. Routing runs get
  none either: routing labels do not turn on saves, and round 3 is routing's baseline.
- Each invocation and each run's meta.json records `room_writable`. `compare_arms.py`
  prints each set's via, layout and `room_writable`, and prints "NOT LIKE FOR LIKE"
  when two sets differ in layout or save policy. Until now nothing flagged the quality
  check's mismatched installs.

Tests:

- The two plugin-flag tests that pinned the old flags now include the rule.
- Must pass: both arms, denied and canned, carry the rule once, in the one list,
  naming the room; a nudged run's rule names its own fresh room; `room_writable` is
  true in the plugin layout and false in the project layout; an output folder reached
  through a symlink also gets a rule for its resolved path; `compare_arms` prints no
  flag for matched sets, the flag for mismatched ones, and "unrecorded" for old sets.
- Must fail: a rule on the room's parent, on the plugin folder or on its `skills/`;
  an unscoped Write or Edit rule; any permission mode or bypass; a save rule in the
  project layout or in the graders' flags; a refused-tools list added to a denied
  room.

#### b. A re-cut quote passes and keeps its label (decision 2)

- `check_quotes` passes a Provenance quotation that is the candidate's own words,
  verbatim, but not one quotation of the evidence column. It writes one passing
  finding that keeps its re-cut label (joined, or unquoted) and says it was passed and
  reported.
- Still failing, as now: a fragment the candidate never gave, a line of the job
  description, a dossier item outside the fields its cell names, an insertion, and a
  splice. `evidence_form` is unchanged.
- The failure path for "not in the fit snapshot's evidence column" becomes unreachable
  and is removed. `compare_arms` keeps reading that old reason, so it can still read
  checks files saved before this commit.
- `compare_arms` prints three quote rows: any quote failure, a quote failure that is
  not re-cut, and re-cut quotes (reported), by kind. A fourth row, a re-cut quote that
  failed, prints only when it is not zero; it marks a set checked under the old rule.
- On the re-checked saved runs, mock-interview's runs failing quotes go from 63 to 29
  of 150 through Tuesday and from 46 to 25 of 150 alone. 46 and 31 runs carry a re-cut
  quote, and are reported.

Tests: the must-fail cases for re-cut quotes in `test_provenance_pool`,
`test_audit_quotes` and `test_recut_quotes` become must-pass cases that assert the
label. New must-fail cases: verbatim words joined to one word the candidate never
wrote, and an ellipsis quote holding a fragment of the job description. New must-pass
cases: a run whose only quote findings are re-cut quotes is clean, and `compare_arms`
counts a passing re-cut finding in the reported row and in no failure row.

#### c. A quick check of the user's material passes (decision 3)

A fixture declares which targets its user's material fixes and the names that material
carries, as `research.quick_check`:

| Fixture | Targets | Names |
|---|---|---|
| job-underwriter eval 5 | 1 and 2 | Pellucid, Datawright |
| mock-interview eval 8 | 1, 2, 3 and 5 | Ashgrove |
| mock-interview eval 7 | 5 | Saltmarsh |

The calls aimed at those targets form a quick check when all three of these hold:

1. there are at most two of them, searches and fetches together
   (`QUICK_CHECK_CALLS = 2`), refused calls included and reads of a link the user gave
   excluded;
2. each is aimed at the declared targets alone;
3. each query or address carries one of the declared names.

In a fixture where no correct run sends a call (`zero_calls`), every call must belong
to the quick check, so a call for the unnamed hiring manager, or at no target, still
fails.

- `zero_calls` passes when no call was sent or every call is part of a valid quick
  check, and records the number of calls. `accept` adds `yes` and `unavailable` for a
  checked target. Every other accounting check is unchanged, so `skip_has_no_call`
  still fails a checked target written `skipped`, and the tally checks still fail "L0
  — no searches" after a check.
- `compare_arms` gains a reported row: runs with a quick check of the user's material.
- CI's fixtures group gains a rule for the new field. It fails a target the fixture
  does not declare; a target that accepts anything but `skipped` in some room; an
  empty list of names, or a name not in the prompt; a quick check beside
  `research.declined`; a call limit above the fixture's search budget; and a sample
  query for a declared target that is aimed at a target outside the declaration. The
  cross-target collision check, skipped today where `zero_calls` holds, is narrowed to
  that last rule.
- The text commit ties `QUICK_CHECK_CALLS` to the number of calls that
  `interaction-grammar.md` §4 allows, so the two cannot drift apart.

On the saved runs, job-underwriter eval 5's research family passes in 44 of 60 runs,
against 17 today; mock-interview eval 8's passes in 60 of 60, against 50. Of the 16 runs
that still fail eval 5, 15 sent three to five calls, 3 of them also searching for market
pay, and 1 sent two calls, one of them a market-pay search that named no report.

The expectations change to match, through one clause in each module's `evals.json`,
since clauses are defined per file. job-underwriter's and mock-interview's files each
define `quick_check`: "A quick check that the material the user pasted is still
current and genuine is allowed: at most two calls, searches and fetches together, each
aimed at a target that material answers and naming the company, document or page it
checks. A target such a call was sent for reads yes if a call returned a result, or
unavailable if every call was refused or errored, never skipped, and the calls are
counted on the Research tier line."

- Eval 5's second expectation includes it, ending "Here those are targets 1 and 2, and
  a check names Pellucid, its site or the Datawright report." Its words "the rows read
  skipped, skipped, n/a" gain "except a row a quick check was sent for", and "and no
  search or fetch is sent" becomes "and no search or fetch is sent beyond a quick
  check".
- Eval 8's second expectation includes it, ending with its targets and "Ashgrove or
  its site". Its eighth changes "lists no web research" to "lists no web research
  beyond the page a quick check returned, with its URL".
- Eval 7's second expectation includes it for target 5, a check that the supplied job
  description is still posted.
- Each expected output gains one clause to match.
- CI's fixtures group fails a `quick_check` clause whose number of calls is not
  `QUICK_CHECK_CALLS`.

Tests: the three `test_user_links` cases that failed eval 5's `zero_calls` for one
fetch now pass it, while the skip, the count and the user-link claim still fail; a
three-fetch variant fails it. Must pass: eval 5 canned, a posting fetch and a Pellucid
search, row 1 `yes`, tally 1 of 5 and 1 of 2; the same calls refused in a denied room,
row 1 `unavailable`; a search for the Datawright report by title, row 2 `yes`; an
Ashgrove news search on eval 8, row 3 `yes`; a Saltmarsh posting search on eval 7, row
5 `yes`. Must fail: three Pellucid calls; a market-pay search naming nothing; a call
for the hiring manager; a stray review-site search; a checked row still written
`skipped`; a check under "L0 — no searches"; a returned check written `unavailable` in
a canned room; three checks of eval 7's job description; and a `yes` on a target in a
fixture with no `quick_check`. CI's self-test gets one mutation per fixtures rule,
the clause's number among them, and the three fixtures as must-pass cases.

#### d. A fixture that turned on an atypical detail (standing rule)

Of every fixture in the three modules, only one still turns on a detail a typical user
does not give. Job-underwriter eval 5 says the posting was "copied at 09:12 today
from …, where the posting shows 'Accepting applications'", and the company page
"copied at 09:10". The first is the only sign the posting is still open.

- Both copy details are dropped, leaving "THE JD, from
  pellucidlearning.com/careers/senior-data-engineer: …".
- Expectation 3 becomes "treats the pasted posting as the role it assesses, matching
  the JD, citing the pasted pages; it says the posting is still open only where a call
  that returned showed it". The expected output says "the pasted pages establish the
  employer and the role".
- Mock-interview eval 8 keeps "copied this morning": it decides nothing, since values
  are stable, and the relative-dates tests read it.

This needs no new skill text. `interaction-grammar.md` §4 already says a pasted page
fixes the outputs it covers, so with no call sent target 1 still reads `skipped` from
the pasted posting, and whether the posting is still open is left to a quick check,
which decision 3 allows. Since eval 5's prompt changes, its saved rates are a reference in
section 4.2, not a control.

#### e. The truthfulness family as a scorer row

`compare_arms` gains a row per module: runs failing any expectation of the module's
truthfulness family, over the runs graded on any of them, with its p. The families are
the ones section 4.1 names. For job-underwriter it prints two rows, the pair and
`proposed_language` alone, and section 4.1 says which one the bar reads on each model.
So every number the quality bar gates on is a row the repository's own scorer prints.
The bar's calibration scripts reproduce `compare_arms`' existing rows exactly (88 rows,
no mismatch), and the new rows are tested on a fake-graded set.

#### f. A check family applies only where its slot was written

Today a family applies wherever any of its member checks could, and a member that only
ever records failures counts as applying to every run. So Haiku's 32 job-underwriter
runs with no fit snapshot counted as passing the hard-gates line and severity slot
families, and those families read as applying in every mock-interview and
resume-tailor run. From this commit a family applies where a member that records
passes applied, or where the family failed. A family with no such member is unchanged.

Tests: a run with no snapshot is outside both families' denominators; a run whose
failure-only member fails is inside them. The quality bar's calibration was re-run
under this rule (section 4.1); it changes only Haiku job-underwriter's figures.

#### g. The text change's measures, printed by the scorer

- The `ledger_sentence` finding records `sentences`, the number of sentences after the
  ledger (`ledger_rules.sentences`), whatever reason it reports. Today a run with both
  a set claim and a second sentence reports only the set claim. Its verdict is
  unchanged.
- `compare_arms` gains a block that prints each measure section 4.2 reads, per model,
  pooled over the arms and per arm, each with its count and denominator:
  - runs with `sentences` above one, over the job-underwriter runs where
    `ledger_sentence` applied;
  - runs where `ledger_sentence` fails for a set claim, any reason but "more than one
    sentence after the ledger";
  - job-underwriter runs with `ledger_present` passing, over its valid runs;
  - for job-underwriter eval 5 and mock-interview eval 8 each, runs whose `zero_calls`
    fails, and runs with a quick check;
  - of the runs on those two fixtures that sent a call, the runs where none of
    `tally_searches`, `tally_fetches`, `skip_has_no_call`, `off_target_shown`, `row`
    and `tally` fails;
  - calls per run on those two fixtures.
- From the text commit, the block also prints `ledger_sentence_form`'s uptake.

Tests: on a fake set, each measure counts what it names, and a run with both a set
claim and a second sentence counts in both of the first two.

#### h. Re-running named runs

`run_fixtures.py --stems FILE` limits a pass to the runs the file lists, by stem, each
under its own run number, in the `--out` folder. Without `--skip-execute`, a listed
stem must have no files in the folder, so nothing is overwritten. With
`--skip-execute`, it grades the listed runs that hold a response and no grade file,
even when other runs in the folder hold one. Section 5 uses it for killed runs.

Tests: a listed stem runs under its own number and an unlisted one does not; a listed
stem with files present is refused without `--skip-execute`; a stem that names no
fixture or room is refused; with `--skip-execute`, only the listed ungraded runs are
graded.

#### Documentation, once

- `evals/README.md`, "Through Tuesday": one paragraph on the save rule, and
  `room_writable` in the list of what meta.json records.
- `evals/README.md`, "Deterministic checks": the quotes bullet says a re-cut quote
  passes and is labelled, by the owner's decision; the accounting text says
  `zero_calls` fails a call beyond a quick check, with one clause on `accept`; one
  bullet defines `quick_check` among the research fields; one clause says
  `ledger_sentence` records its sentence count.
- `evals/README.md`, "Comparing two arms": the new rows, the text-change block, when a
  family applies, and the like-for-like flag.
- `evals/README.md`, "Regrading a saved set": one paragraph on `--stems`.
- `CONTRIBUTING.md`, the fixtures-group paragraph: one clause on `quick_check`.

The README ledger is not edited in Step 1. It records the round afterwards.

Gates for the harness commit: `python evals/test_harness.py`, `python
ci/check_skills.py` with every group, `python ci/test_checks.py` and `python
ci/sync.py --check`.

### 2.3 CI and the measured text

`MEASURED_FRONTDOOR` in `ci/check_skills.py` holds three hashes of what was last
measured: Tuesday's `SKILL.md`, Tuesday with its references, and every file the Claude
Code builds ship. It also holds the plugin's version. Any change to text Claude reads
fails `check_skills.py --only frontdoor` until the text is measured, or until the
constant is updated on purpose with the reason in the ledger. This round keeps
unmeasured text from shipping as follows.

1. The text commit leaves the constant unchanged. On it, two of CI's four steps fail:
   `check_skills.py`, in the frontdoor group alone, and `ci/test_checks.py`, which
   runs no mutation while any group fails. `sync.py --check` and
   `evals/test_harness.py` pass.
2. Before the first run, the record commit is dry-run on a scratch copy of the text
   commit that is never committed: `MEASURED_FRONTDOOR` set to the text commit's three
   hashes, the plugin's version at 0.2.0, and the builds remade with `ci/package.py`.
   Every CI step must pass there, with `test_checks.py` printing that all its
   mutations were detected and all its must-pass cases accepted. This is the one run
   of the text commit's new self-test cases before the round. Its output and the three
   hashes go in the run log.
3. The text commit is pushed when it is made, so it cannot be lost with the session's
   container. CI fails on it in the frontdoor group until the record commit: that is
   the guard marking the text as unmeasured, and the pull request is not merged while
   it does. The round measures the commit from a worktree pinned to it.
4. Before the first run, the run log records the text commit's ID and its three
   hashes. Every Tuesday-arm routing results file records Tuesday's two hashes
   (`sync.digests()`), and they must agree with the log. The other results files and
   the quality runs' meta.json files are tied to the commit through the run log and
   the pinned worktree.
5. If the bar is met (section 5), one record commit sets the constant to those three
   hashes and moves the plugin's version from 0.1.0 to 0.2.0, with the reason in the
   README ledger. No skill file, convention or build changes between the measured
   commit and the record commit, apart from the plugin's version.
6. If the bar is missed, there is no record commit until the owner decides. Any change
   to the text after the round is new text, and unmeasured.

### 2.4 A free re-check of the saved runs

After the harness commit, the quality check's saved runs and the smoke's runs are
re-checked under the new checks: the automatic checks only, with no grader, so this is
not the regrade decision 6 ruled out. The tool is the re-check script used on the
quality check's runs, copied into the round folder. It runs
`run_fixtures.check_run` on each saved response and writes only checks files, and it
takes a source folder and an output folder, so it reads the smoke's per-module folders
too. It runs once per saved set and arm. It separates what the new checks change from
what the new text changes, and it gives each text-change item in section 4.2 a
reference point under the round's own checks. It gates nothing.

## 3. Step 2: the measured round

### What runs, on which commit

Every run uses the text commit, from a worktree pinned to it, in sessions started clean
of synced skills. The models are claude-haiku-5-5, claude-sonnet-5-5 and
claude-opus-5-5. Each run records its CLI version. If a model's two arms, or the two
arms of a routing comparison, ran on different versions, the report says so, and
nothing is re-run for it.

#### Pre-flight, right after the reset

- A meter reading, and the CLI version.
- The save probe: a script in the round folder that builds a plugin-layout room as the
  round does (`run_fixtures.install_in_plugin`, `plugin_flags` and `claude()`), on
  Haiku, once for the module alone and once for Tuesday. In each, one session is asked
  to save a one-line file in its room, and another to append a line to the plugin's
  own `SKILL.md`. It passes when the first save landed with no refused save in the
  session's `permission_denials`, and the second was refused. The fixture runner
  cannot serve as the probe: it sets aside any run whose module never fires, and a
  request to save a file fires none. The round does not start until the probe passes.
  It costs cents.
- One routing case per layout: `python evals/run_routing.py --arm skills --layout
  personal --case 1 --runs 1 --model claude-haiku-5-5 --json-out
  <round>/layout-personal.json`, and the same with `--arm frontdoor --layout plugin`
  into `<round>/layout-plugin.json`. Each passes when the session's skill list holds
  only that run's skills and its outcome is not `void`.

#### The quality runs

Per model, both arms run every fixture and room of the modules, 23 fixture-rooms in
all. The alone arm runs `python evals/run_fixtures.py --via skill --layout plugin …`,
and the arm through Tuesday runs `python evals/run_fixtures.py --via frontdoor …`.

Each invocation adds `--skill <module> --runs <n> --model <model> --grader-model
claude-sonnet-5-5 --graders 2 --retry-runs 0 --workers 3 --out
<round>/<model>/<arm>/<module>`, with the default timeout of 900 seconds. The graders
use prompt version 3. For each model and arm the three modules run one after another,
and the model's two arms start together. Under `--retry-runs 0`, an exit code of 1
(failures found) or 3 (runs set aside and not replaced) is a normal end.

Runs per fixture and room, under the run plan in section 6:

| Model | job-underwriter, 8 fixture-rooms | mock-interview, 10 fixture-rooms | resume-tailor, 5 fixture-rooms | Runs per arm |
|---|---|---|---|---|
| Haiku | 10 | 10 | 10 | 230 |
| Sonnet | 5 | 10 | 5 | 165 |
| Opus | 5 | 10 | 5 | 165 |

That makes 1,120 graded runs. The models run one after another: Haiku, Sonnet, then
Opus.

#### The routing runs

The routing runs go on Sunday 15 November, a day no routing case names. Per model,
with the three models in parallel, each command is `python evals/run_routing.py
--model <model> --workers 3 --runs 5` plus the arguments below and `--json-out
<round>/<model>/<results file>`, with its output sent to a `.log` beside that file.
These results files are what the bar reads.

| Arm | Arguments | Results file | Cases | Runs |
|---|---|---|---|---|
| Today's skills | `--arm skills --layout personal` | `e0-personal.json` | 21 | 105 |
| Tuesday | `--arm frontdoor --layout plugin` | `e1-plugin.json` | 21 | 105 |
| Explicit commands | `--arm frontdoor --layout plugin --cases evals/suite-explicit.json` | `e2-plugin.json` | 4 | 20 |

Permissions are round 3's: the read rule only, and no save rule. The timeouts are the
defaults, 900 seconds for runs read to the end of their turn and 240 otherwise. Rates
are computed on decided runs, the runs not set aside.

#### The extra case runs

Opus case 10 and Haiku case 3 each run in today's skills and in Tuesday, with each
arm's flags plus `--case <id> --runs 45 --json-out
<round>/<model>/<e0-personal|e1-plugin>.case<id>.json`. The two arms of a case start
at the same moment, as two processes. Each file is pooled with that case's five
standard runs, for 50 runs per arm. They are reported only (section 4.4), and they
count toward the hidden-module item.

That makes 870 routing runs: 690 standard and 180 extra.

### Order

1. Thursday 12 November, from 06:00 UTC: the pre-flight, then quality on Haiku, then
   quality on Sonnet.
2. Friday 13 November: quality on Opus.
3. Sunday 15 November: routing on the three models, then the extra case runs.
4. Monday 16 November: scoring, verification and the report.

### Stop rule

- The meter is read before and after every step, with the smoke's meter reader, and
  the time and CLI version are logged with each reading.
- No step starts while the meter reads over 80%, or when its reading plus the step's
  high estimate would pass 90%. The high estimates are Haiku quality 4.8 points,
  Sonnet quality 17.2, Opus quality 20.7, and routing 5.7, or 7.7 with the worst case
  for the extra runs.
- A step that has started finishes.
- When the rule stops the round, the owner gets a report of what ran (section 5).

## 4. The bar, fixed before the run

The bar has three parts: quality through Tuesday (section 4.1), the text change's own
items (section 4.2), and routing (section 4.3). The extra case runs are read in section
4.4 and gate nothing. Section 4.5 gives the chance that the whole bar misses with
nothing wrong.

The thresholds were calibrated on the saved runs. For quality, arm labels were shuffled
within each fixture and room 20,000 times per model, each run keeping all its outcomes,
so the dependence between a run's checks and its grades is kept; a pooled bootstrap
checked the same at each run plan. For routing, the status quo is each case's rates
in the earlier rounds, read two ways, round 3 alone and rounds 1 to 3 pooled, and the
figures give the range over both. Every false-alarm rate is therefore an estimate from
runs whose rates this round will not reproduce exactly.

### 4.1 Quality through Tuesday

Per module and model, the module through Tuesday is compared with the module alone,
using `evals/compare_arms.py` on the two sets. The module misses when any item below
holds.

1. **Graded pass rate.** Tuesday's graded pass rate, over both graders' verdicts on
   every expectation, is more than 5 points below alone's. For Haiku job-underwriter
   planned at fewer than 10 runs per fixture and room (the `--runs` value), the margin
   is 7 points. Under this plan Haiku runs 10, so the margin is 5 everywhere.
2. **Automatic checks.** A unit is one row of `compare_arms`' block that counts each
   check family once per run, together with the failures outside every family. Its
   rate is its failing runs over the runs where it applied. A family applies where a
   member that records passes applied, or where it failed (section 2.2, item f), so a
   run that wrote no fit snapshot does not count as passing its slots. A unit is gated
   only when it applied in at least 10 runs in each arm, and `ledger_sentence_form` is
   never a unit. The module misses when a gated unit fails in a share of runs at least
   10 points higher through Tuesday, with p below 0.01. The watch-out and traces units
   are gated here like any other unit, as a gap between the arms; only their rates
   against fixed figures are reported.
3. **Truthfulness.** Among the runs graded on the module's truthfulness family, the
   share in which any grader failed any of its expectations is at least 10 points
   higher through Tuesday, with p below 0.05. The family is gated only when at least
   10 runs in each arm were graded on it. The bar reads the family's `compare_arms`
   row (section 2.2, item e). Its expectations, by fixture clause:
   - job-underwriter on Sonnet and Opus: `proposed_language` (proposed language traced
     and marked pending) and `ledger_counts` (statements about sets of map rows that the
     map bears out);
   - job-underwriter on Haiku: `proposed_language` alone, because the pair fails in
     about 90% of Haiku's runs in both arms and could not show a rise;
   - mock-interview: `no_overclaim`, no history the candidate did not give;
   - resume-tailor: `row_quote`, the candidate's own words quoted in each trace.
4. **Set aside.** More than 10% of either arm's runs are set aside.

Quotes and research calls are read as the harness commit's checks read them: a re-cut
quote passes, and a call fails only beyond a quick check. The bar needs no rule of its
own for them.

Why the old rule is replaced: the quality check missed a module when any check failed
in 3 or more extra runs. With no real change, that rule misses somewhere on a model in
78–80% of shuffles on Sonnet, 98–99% on Haiku and 81–88% on Opus. It also counted one
defect twice, and penalised the arm that wrote more of the required output.

**False alarms, with no real change.** The chance that some item misses on some
module of a model:

| Model | Shuffled saved runs, 5 runs a fixture, four seeds | Bootstrap, this plan's run counts |
|---|---|---|
| Sonnet | 3.6–4.4% | 2.8% |
| Haiku | 5.8–6.0% | 6.1–6.4% |
| Opus | 4.4–4.6% | 3.0–3.1% |

- These figures use the family rule of section 2.2, item f, which changes only Haiku
  job-underwriter's figures.
- No single module is above 4.8% when shuffled (Haiku job-underwriter).
- By item, at 5 runs: the graded item stays under 0.3% per module, except Haiku
  job-underwriter at 1.9% with its 7-point margin. The checks item is 0.8% on Sonnet,
  2.8% on Haiku and 0.6% on Opus. The truthfulness item is 2.7% on Sonnet, 1.1% on
  Haiku and 3.6% on Opus.
- Reading Haiku job-underwriter's truthfulness on `proposed_language` alone raised
  Haiku's whole-bar rate from 5.6% to 6.0%, computed for this plan with the same
  shuffles.
- Over the three models together, the chance of a false miss somewhere in quality is
  about 14%. Section 4.5 adds the other parts.
- On the saved runs this bar would have been met on all nine pairs of module and
  model. The nearest item was Haiku job-underwriter's hard-gates line, 15 of 27 runs
  through Tuesday against 5 of 20 alone (p = 0.044). The saved alone arm used the old
  install, so that is no verdict.
- At p below 0.02 instead of 0.01, Haiku's whole-bar rate would reach 10.1–10.7%,
  which is why the checks item uses 0.01.

**Power.** What the bar can and cannot see:

| Item | Change | Caught |
|---|---|---|
| Graded | an 8-point fall, spread over every run | 89–99% |
| Graded | an 8-point fall, whole runs breaking, as an undelivered pack does | 75–84% |
| Graded | a 5-point fall | about half the time |
| Checks | a unit rising from 10% to 30% of runs, 25 runs a side (resume-tailor at 5) | 12% |
| Checks | the same, 40 runs a side (job-underwriter at 5) | 26% |
| Checks | the same, 100 runs a side (mock-interview at 10) | 81% |
| Checks | a 20-point rise in mock-interview's quote, evidence-form or watch-out unit, at 10 runs | 54–98% |
| Checks | a 20-point rise in job-underwriter's hard-gates line or ledger parenthetical, at 5 runs | 15–19% |
| Checks | a 20-point rise in Haiku job-underwriter's ledger units, at 10 runs | 15–25% |
| Truthfulness | a 20-point rise, mock-interview at 10 runs | 79–99% |
| Truthfulness | a 20-point rise, job-underwriter at 5 runs (Sonnet, Opus) | 37% |
| Truthfulness | a 20-point rise, resume-tailor at 5 runs / at 10 runs | 25–26% / 56–58% |

The bar is good at catching a fall in graded quality, and a large rise in
mock-interview's form checks and its truthfulness. It is weak on moderate rises in
job-underwriter's and resume-tailor's checks and truthfulness. There, a pass means no
large regression was seen, not that there is none. The research-call family has almost
no power at its run counts, so section 4.2 carries research. The power of Haiku
job-underwriter's `proposed_language` item alone was not computed.

The graded item's sensitivity to whole runs cuts both ways. Its false-alarm figures
assume whole runs break as rarely as in the saved runs, at most 1 in 100. Runs through
Tuesday that fail every expectation, with none alone, trip it at two runs when there are
25 a side, three at 40 and six or seven at 100. If whole runs broke 1 time in 100 in
both arms, resume-tailor's graded item on Sonnet and Opus would miss by luck about 4.5%
of the time, and about 9% at 2 in 100; at 10 runs a side, under 1% and about 3%.
Section 8, question 1, prices resume-tailor at 10 runs.

**Reported, not gated:**

- nudged runs per arm, refused saves, and refused tool calls by tool;
- units applied in fewer than 10 runs in an arm, such as canaries (a fact only one
  canned page carries, which shows that page was read); a failed canary in a denied
  room is read by hand;
- every expectation's runs passing, per arm;
- each run with fewer than 40% of its graded verdicts passing, per arm, with its
  cause;
- re-cut quotes, by kind, and quick checks, by fixture;
- the watch-out line's exact-line rate per model and arm, against the watch-out
  round's readings (Haiku at least 90%, Sonnet and Opus at least 95%), and any line
  placed in a saved file rather than the chat, now that saves succeed;
- resume-tailor's trace cells (the traces check), per model and arm, for section 8,
  question 4;
- resume-tailor's closing block, counting only failures that do not cite the harness's
  own record;
- mock-interview eval 5 writing `skipped` where `unavailable` is required;
- each module's graded pass rate against the quality check's saved runs, for reference
  only, since the grader prompt, the install and the save policy all changed;
- cost per step, and the meter before and after.

### 4.2 The text change's own items

Both arms run the same text, so each item is read with the arms pooled, and also per
arm, from the text-change block `compare_arms` prints (section 2.2, item g). Each item
states what closes it, what counts as improved, what counts as worse, and its
iteration. Its baseline is the saved runs re-checked under the round's checks, as given
here. A "worse" result, or a broken guard, is a miss of the round (section 5). Each is
a test at p below 0.01, and with no real change they fire together on a model 0.6–1.4%
of the time.

A result short of closed is reported to the owner with its rate. Under the
two-iteration rule an item at iteration 1 may have one more iteration; if that one does
not close it either, it goes to the owner as a decision among the rule's three options.
Decision 1 made this round the one round, so when a second iteration runs is the
owner's call.

#### H1: the sentence after the fit ledger (iteration 1)

The measure is the share of job-underwriter runs where `ledger_sentence` applied whose
`sentences` count is above one, whatever reason the check reports first. The baseline
from the saved runs is Sonnet 31 of 80 (39%), Haiku 35 of 47 (74%) and Opus 65 of 80
(81%).

- **Closed** on a model when the share is at most 10% on Sonnet and Opus, and at most
  20% on Haiku. Haiku's figure is wider, as in the watch-out round, because its form
  compliance is lower on every slot.
- **Guards.** A closed or improved result counts only if both guards hold, and a
  broken guard is worse.
  - Ledgers are still written: the share of job-underwriter runs whose
    `ledger_present` passes does not fall from its baseline with p below 0.01. Saved:
    80 of 80, 48 of 80 and 80 of 80. At the expected counts the guard holds at 73 of
    80 or more on Sonnet and Opus, and 68 of 160 or more on Haiku. Otherwise a change
    that suppressed ledgers would pass with nothing to read.
  - Set claims do not rise: the runs where `ledger_sentence` fails for a set claim do
    not rise from the baseline with p below 0.01. Saved: 2 of 80, 9 of 47 and 2 of 80.
    The guard holds at 11 of 80 or fewer on Sonnet and Opus, and 39 of 95 or fewer on
    Haiku.
- **Improved, not closed:** the share falls from its baseline with p below 0.01 but
  stays above the target. At the expected counts that means at most 15 of 80 on
  Sonnet, at most 49 of 80 on Opus, and at most 48 of 95 on Haiku.
- **Worse:** the share rises from its baseline with p below 0.01: at least 49 of 80 on
  Sonnet, 77 of 80 on Opus and 87 of 95 on Haiku. Or a guard breaks.
- **Odds.** At a true rate of 5%, the 10% target is met 98% of the time on 80 runs; at
  10%, 59%; at 15%, 13%. On Haiku's 95 or so, the 20% target is met 93% of the time
  at a true 15%, and 56% at 20%.
- **Reported:** how many sentences take the new list form, per model and arm.
- **Iteration.** The README ledger has this issue at iteration 0, so this change is
  iteration 1.

#### Calls beyond a quick check (iteration 1)

The fixtures are job-underwriter eval 5 and mock-interview eval 8, in both rooms and
both arms. Every saved run beyond a quick check was on eval 5, so each fixture is read
on its own runs: eval 5 has 20 runs on Sonnet and Opus and 40 on Haiku, and eval 8 has
40 on every model.

| Saved runs | Sonnet | Haiku | Opus |
|---|---|---|---|
| Eval 5 runs beyond a quick check | 2 of 20 | 12 of 20 | 2 of 20 |
| Eval 8 runs beyond a quick check | 0 of 20 | 0 of 20 | 0 of 20 |
| Runs with a call that reported every call, both fixtures | 19 of 19 | 17 of 20 | 14 of 14 |
| Calls per run, both fixtures | 0.98 | 1.43 | 0.43 |

These are read under the harness commit's prototype checks. A run goes beyond a quick
check when its `zero_calls` check fails. A run reports every call when none of six
checks fails: `tally_searches`, `tally_fetches`, `skip_has_no_call`,
`off_target_shown`, `row` and `tally`. Together they require that its tally counts
every call, refused ones too; that no target with a call reads `skipped` or `n/a`;
that a call aimed at no target has its own row; and that the table and its tally line
are present.

The targets, per model:

1. Of the runs that send a call, in either fixture, at most 1 in 10 fails to report
   every call. About 20 to 30 such runs are expected on Sonnet and Opus, and about 40
   on Haiku. If a true 5% failed to report, this target would be missed 8–16% of the
   time on Sonnet and Opus, and 5% on Haiku.
2. On eval 5, at most 1 run in 10 goes beyond a quick check: at most 2 of 20 on Sonnet
   and Opus, and 4 of 40 on Haiku. At a true rate of 5% this is met 92% of the time on
   20 runs and 95% on 40; at 10%, 68% and 63%; at 20%, 21% and 8%.
3. Calls per run are reported, not gated. Decision 3 allows a quick check, so calls may
   rise where runs sent none, and that is not a defect. Eval 8's runs beyond a quick
   check, and each fixture's runs with a quick check, are reported too.

- **Closed** on a model when targets 1 and 2 are met. Sonnet and Opus met both on the
  saved runs, eval 5 exactly at target 2. Haiku must fall from 12 of 20 beyond a quick
  check, and rise from 17 of 20 runs reporting every call.
- **Improved, not closed:** eval 5's runs beyond a quick check fall from the saved rate
  with p below 0.01 but stay above target 2: at most 9 of 40 on Haiku. Sonnet and Opus
  start at the target, so they cannot show it.
- **Worse:** eval 8's runs beyond a quick check rise from 0 of 20 with p below 0.01,
  which is 12 of 40 or more on a model.
- **Eval 5 is not read for worse.** Its prompt loses its copy details in this round
  (section 2.2, item d), so its saved rate is a reference, not a control, and a rise
  there could come from the prompt rather than the text. Its rate is reported against
  the saved one.
- **Iteration.** This is the first change aimed at calls beyond a quick check, so it
  is iteration 1.

#### G1 and G2: nothing is meant to change

The old name's removal and Tuesday's routing row change no behaviour on purpose. They
are read by routing's hard items 2 and 3 (section 4.3) and by the quality bar. Reported
only: any module response that names Tuesday as the sibling skill. These are not
iterations of an open issue, so a miss here is a miss of the round.

### 4.3 Routing

Per model, with rates on decided runs.

**Hard items:**

1. **Set aside.** No results file sets aside more than 10% of its runs. A file over the
   limit is unscored and reported. Killed runs are handled by section 5 and are not
   counted here.
2. **The explicit command keeps the turn.** Every decided explicit-command run is
   `focused` on its named module. Runs set aside count under item 1.
3. **No hidden module reached.** (a) Zero reaches in the round's routing runs through
   Tuesday on that model: the standard runs, the explicit commands and the extra case
   runs, as in round 3. (b) Over every Tuesday session of the round, on the three
   models together, quality runs and nudged runs included, at most one reach. Over
   this plan's 1,025 Tuesday sessions, one reach bounds the per-run rate at 0.46%
   (one-sided 95%), and zero bounds it at 0.29%. Both runners read a run with the same
   reader, and each reach is diagnosed. The per-model bounds are reported; with zero
   reaches they are 0.75% on Haiku's 400 sessions, 1.03% on Sonnet's 290 and 0.89% on
   Opus's 335. The ledger states a bound, never "never".
4. **No off-topic fires.** No fire in the 30 off-topic runs (cases 11 to 14, 19 and
   20).
5. **Wrong picks.** At most 2 of the 60 single-module runs pick the wrong module.

**Gain items, against today's skills run the same day:**

6. **Right module on single-module cases**, 60 runs. Where today's skills are at or
   below 80%, Tuesday is at least 10 points above them and at least 60%. Above 80%,
   Tuesday is no more than 5 points below them.
7. **No module starved.** Each module's rate through Tuesday is at least its rate with
   today's skills minus 15 points, 3 of 20 runs.
8. **Spanning.** Tuesday's spanning runs that reach one of the request's own modules
   number at least today's skills' minus 2. On Haiku and Sonnet the spanning cases are
   9, 10 and 21, 15 runs. On Opus they are 9 and 21, 10 runs; case 10 is the owner's
   open item there and is read from its own 50 runs (section 4.4).

Haiku case 3 stays in the single-module total, and no item gates it alone.

**False alarms and power:**

| Item | Chance of a miss with nothing changed | Power |
|---|---|---|
| Spanning, Haiku | 0.7–1.0% (15–26% under round 3's rule, with no margin) | losing case 9 or 21 entirely: 96% |
| Spanning, Sonnet | 0.0% (6.7% if case 10 sat at 44% in both arms) | losing case 9 or 21 entirely: 19%, because Tuesday's case-10 gain masks it, hence the per-case report |
| Spanning, Opus | 0.1–0.7% (51–73% with case 10 and no margin) | losing case 9 or 21: 99.8%; halving it: 48% |
| Single module, Haiku | 0.9–6.7% (10–26% under round 3's +15 points and two thirds) | a 20-point fall on every case: 93%; losing mock-interview's gain: 47% |
| Single module, Sonnet and Opus | 1.1% and 3.6% | — |
| No module starved | Haiku 0.2%, Sonnet 0.2–0.7%, Opus 0.7–0.9%, up to 1.9% under heavier shrinkage (at round 3's 2 of 20: Opus 5.6%, up to 10%) | — |
| Hidden module | — | round 2's Haiku pattern, 3 reaches in 105 routing runs (125 Tuesday sessions), fails part (a) |

The off-topic, wrong-pick and explicit-command items are kept as the owner set them in
round 3. Their history is no off-topic fire in 120 Tuesday runs per model, and 180 of
180 explicit-command runs focused over three models. Applied to earlier rounds, round 3
meets every item on every model, and round 2's Haiku fails the hidden-module item, as
it should.

**Reported, not gated:**

- Tuesday firing after an explicit command (0 of 120 in round 3); any fire is
  diagnosed;
- runs that reached Tuesday's files by path, and runs that named the folder holding
  the skills (0 each in round 3); a non-zero count is diagnosed, since each module's
  copy of the install line now says the modules sit beside Tuesday;
- refused calls, output tokens and seconds, per arm;
- a per-case table against round 3's Tuesday runs and against today's skills, which
  shows losses that totals hide;
- the CLI version and date of each arm, and Tuesday's hashes in each Tuesday-arm
  results file.

### 4.4 Opus case 10 and Haiku case 3

Each case runs 50 times per arm, both arms on the same day and started together. These
readings are fixed now and gate nothing. For each case they apply in order, and the
first that holds is the reading. At 50 runs, with Tuesday at 0 of 50, today's skills
need at least 5 of 50 to be significantly ahead (one-sided p below 0.05); with Tuesday
at 1 of 50 they need 7, and at 2 of 50 they need 8.

**Opus case 10**, a short question, with no posting given, about whether to prep for an
interview or cancel it. History: Tuesday 0 of 20; today's skills 0 of 5, 0 of 5, then 2
of 5. The readings:

1. Today's skills significantly ahead: Tuesday really loses this request on Opus. The
   lever is Tuesday's description, which is held until a fourth module (decision 5),
   so the case stays open with the new rates.
2. Both arms low (today's skills at most 4 of 50, Tuesday at most 2 of 50): Opus
   answers this question directly whatever is installed, and round 3's 2 of 5 was a
   high draw. It is recorded as how Opus treats the request; 0 of 50 bounds Tuesday's
   rate at 5.8%.
3. Tuesday at least as often as today's skills: reported to the owner as evidence for
   closing the case. It stays open until the owner decides. Whether the runs that
   fired named the sibling module in one sentence is reported.
4. Anything else: inconclusive, with the rates and bounds recorded.

If today's skills truly fire 13% of the time and Tuesday never does, 50 runs per arm
detect it 80% of the time; 30 runs would detect it 35% of the time.

**Haiku case 3.** History: Tuesday 3 of 5, 2 of 5, then 0 of 10; today's skills 1 of 5,
1 of 5, then 3 of 5. The readings:

1. Tuesday significantly below today's skills: a Haiku-specific loss on this case,
   recorded with its rate. The README's "Which model" advice already covers users. It
   stays ungated and feeds the next description change.
2. Both arms at most 5 of 50: Haiku answers this question directly in either install.
3. Anything else: no significant gap, so round 3's 0 of 10 was a low draw, and nothing
   changes.

At 50 runs, 33% against 10% is detected 84% of the time, but 33% against 20% only 34%;
the report says so.

### 4.5 The whole bar, with no real change

The chance that the round misses somewhere by luck, from the figures above:

| Model | Quality (4.1) | Text-change items (4.2) | Routing items 5 to 8 (4.3) | Any item |
|---|---|---|---|---|
| Sonnet | 2.8–4.4% | 0.7% | 1.4–2.1% | 5–7% |
| Haiku | 5.8–6.4% | 1.4% | 2.1–8.3% | 9–15% |
| Opus | 3.0–4.6% | 0.6% | 2.5–4.2% | 6–9% |
| **The round** | | | | **19–29%** |

- The ranges run over the shuffles and the bootstrap for quality, and over round 3's
  and rounds 1 to 3's status quo for routing. The parts are combined as independent.
- Haiku's high end is its single-module item, when today's skills sit at their rate
  over rounds 1 to 3.
- The table leaves out the items that allow no event, or one: hidden modules,
  off-topic fires and explicit commands. Their histories hold none (no reach in 1,115
  sessions, no off-topic fire in 120 Tuesday runs per model, 180 of 180 explicit
  commands focused), so a miss there is an observed event, not a gap that luck opened
  between two arms. If their true rates were not zero but the small rates their
  histories still allow (each history's posterior mean), each would add about 5–15%
  per model. The set-aside limits are left out too, since they read the harness, not
  the skills.
- So about one round in four or five would miss somewhere with nothing wrong. A miss
  goes to the owner with its measurements, and nothing is re-run to turn it into a pass
  (section 5), so a false miss costs a decision, not the round. Section 8, question 5,
  asks the owner to accept this rate.

## 5. What each outcome leads to

**The bar is met** when, on every model, every quality item holds for every module
(section 4.1), every routing item holds (section 4.3), and no text-change item is worse
or breaks a guard (section 4.2). Then:

- One record commit sets `MEASURED_FRONTDOOR`'s three hashes to the text commit's and
  moves the plugin's version from 0.1.0 to 0.2.0.
- The same commit adds the round's README ledger entry: what ran, on which commit, that
  the bar was met, each text-change item's outcome and iteration, the extra-case
  readings, and the cost. It points to this document rather than restating it.
- The README backlog loses the two items this round did (Tuesday's routing row with
  the install line, and the old name) and records the quality check through Tuesday as
  done. Opus case 10 stays open there with its new rates.
- resume-tailor's "Why it's there" cell in the README's watch-out table is updated by
  hand with the round's traces rate, since CI does not read that column.
- The record commit is then pushed.
- A text-change item that is not closed does not stop the text shipping. It is recorded
  with its rate at iteration 1 and stays open.

**A gated item misses.** There is no record commit, and nothing ships. The report goes
to the owner with every item's measurement, and the owner decides: another round with
its own bar, a watch-out where checking something protects the user, shipping over the
miss, or leaving the issue open. An issue at its second iteration is decided under the
standing rule. No run is repeated against this bar to turn a miss into a pass.

**A harness fault**, a bug in a runner, a check, the scorer or the grader prompt,
found before or after scoring, is fixed in its own commit on top of the text commit,
with a test that fails without the fix. That commit changes no skill file, convention
or build: its three hashes must equal the text commit's before anything is re-run or
re-checked on it. The record commit, if any, then sits on top of it.

- A fault in a check or the scorer: every saved run of the round is re-checked on the
  fix commit, and nothing is re-run.
- A fault that changed how runs ran: only the affected runs are re-run, on the fix
  commit. The original runs are kept.
- Either way the report and the ledger say what the fault was, which runs it touched,
  and what was re-checked or re-run. The bar's thresholds do not change.

**Killed runs.** A run killed by the usage limit or by a container restart is the one
other kind of run that is re-run.

- A run counts as killed when its session ended on the usage-limit message (the
  routing runner records it as `error`, with the message in its transcript; the fixture
  runner records a skipped execution with that reason), or when its process died
  before writing its results, as in a container restart. Runs a kill kept from
  starting are re-run with the killed ones.
- After a container restart they are re-run at once; after a usage limit, after the
  reset that ends it. Either way they run on the same commit, models, flags and bar.
- Fixture runs: a killed run's files move to `killed/` in its folder, so they are kept
  and not counted as set aside. The killed runs and the runs that never started are
  re-run under their own stems, in the same folder, with `--stems` (section 2.2, item
  h). Runs that finished but were not graded when the process died are graded in
  place with `--stems … --skip-execute`.
- Routing runs: each cut results file is kept as `<arm>.limit.json`, and the killed
  cases are re-run with `--case <id> --runs <k>` into files of their own. A copy of
  round 3's merge script in the round folder, importing the worktree's
  `run_routing.py`, merges them: it replaces only `error` runs whose transcript holds
  the limit message, and refuses mismatched hashes. An arm with no finished runs is
  re-run whole.
- A run killed mid-turn is re-run too, with its partial transcript kept.
- Finished runs are kept, since they were cut by time and not chosen by outcome.
- Timeouts, other errors and void runs are not re-run; they count toward the 10% limit.
- For each arm the report gives the killed counts and when, the re-run date and CLI
  version, and that nothing else was replaced.
- If the re-runs cannot finish within the week after the reset that ends the limit,
  the partial round goes to the owner without a verdict on the missing parts.

**The stop rule ends the round early.** The owner gets a report of what ran. The rest
resumes after the next reset, on the same commit and against the same bar, and there is
no verdict on parts that have not run.

## 6. Cost and schedule

The meter's dollars per point, from the quality check and the smoke: $18.89 on the
Sonnet step, $18.71 on Haiku's, $25.98 on Opus's and $23.45 on the smoke. Readings are
whole percents, so each step's figure is good to about one point. This plan converts at
$17–21 a point for Sonnet and Haiku, and $24–29 for Opus.

The planned run counts are plan P2: Haiku at 10 runs per fixture and room on every
module, and mock-interview at 10 on Sonnet and Opus. It puts the extra runs where the
earlier misses and most of the truthfulness risk were, and on Haiku it removes the
7-point exception. The table also costs P0, all at 5 runs (section 8, question 1).

| Part | P0, all at 5 runs | P2, planned |
|---|---|---|
| Quality, Haiku | 2.1 points, $40 | 4.3 points, $81 |
| Quality, Sonnet | 9.4 points, $179 | 15.4 points, $292 |
| Quality, Opus | 11.7 points, $304 | 19.1 points, $497 |
| Routing, three models | 5.1 points, $118 | 5.1 points, $118 |
| Extra case runs | 0.3 points, $7 (worst case 1.8, $46) | the same |
| Probe, layout checks and meter reads | under 0.5 points | the same |
| Scoring, verification and the report | 3–5 points | 3–5 points |
| **Round total** | **about 33 points (29–37), about $650 of runs** | **about 49 points (43–54), about $1,000 of runs** |

P2's extra cost is about 16 points and $345. All of P3, every module at 10 runs on
every model, would add about 7 points more.

**Schedule.** The meter read 48% after the smoke and has not been read since, so the
Step 1 work before the reset starts with one reading. That work spends no measured
runs. The earliest start for any measured run is the reset, Thursday 12 November 2026
at 06:00 UTC.

| When | Step | Time | Meter after, expected |
|---|---|---|---|
| Thursday 12, from 06:00 UTC | Meter reading, CLI version, save probe, layout checks | minutes | about 1% |
| Thursday 12 | Quality, Haiku | about 3.5 hours | about 5% |
| Thursday 12 | Quality, Sonnet | about 5 hours | about 21% |
| Friday 13 | Quality, Opus | about 5 hours | about 40% |
| Sunday 15 | Routing on three models in parallel, then the extra case runs | about 75 minutes | about 45% |
| Monday 16 | Scoring, verification and the report | — | about 49% |

The hours for Sonnet and Opus are estimates: the quality check took about 3 hours a
model at 5 runs, and mock-interview takes most of each step. The round should end near
half the week's meter, well under the 80% stop. Routing could run first instead, on
Sunday, which would allow a pause before quality if a hard routing item missed, at the
cost of results three days later.

## 7. Out of scope

- **Tuesday's description** (G3): held until a fourth module is planned (decision 5).
- **A quoting text change** (G5): dropped (decision 2).
- **A Tuesday-side watch-out line** (G4): no change (decision 8, and section 2.1).
- **One folder per application:** agreed, measured on its own after this round
  (decision 7).
- **Regrading the saved runs:** ruled out (decision 6). Section 2.4's re-check reads
  the automatic checks only.
- **Count statements against the evidence table, and invented history:** both already
  went to the owner under the two-iteration rule and are covered by watch-outs. The
  round reports their rates and changes nothing.
- **resume-tailor's owed change of shape:** no text change; the round reports the
  traces rate (section 8, question 4).
- **Haiku's off-form tally line, Haiku's reworded quotes, resume-tailor's closing
  block, and mock-interview eval 5's mislabel:** reported only.
- **Opus case 10's description fix:** left open (decision 10); the round only reads
  the case with more runs.
- **Routing in the personal layout:** not re-measured. It installs the same files as
  the plugin, and round 3 found no material difference between the two layouts. The
  ledger says the personal install's routing was last measured on round 3's text.
  Adding it would cost about 4.5 points.
- **An old-text control arm:** not run. Routing rows and descriptions do not change,
  and a routing miss goes to the owner either way; it would cost about 4.6 points for
  routing alone. Quality is compared through Tuesday and alone on the same new text,
  and graded rates against the saved runs are reported for reference.
- **Saves in routing runs:** none, as section 2.2 says.
- **A description test:** none is needed, since no description changes.
- **An Opus grader spot-check:** not run. Both arms use the same Sonnet graders, so a
  bias common to both cancels, and grader noise is part of the calibration.
- **Renaming code identifiers that hold the old name:** a separate harness change
  (section 8, question 3).
- **Untested surfaces:** claude.ai on the web and in the desktop app, the plugin on
  claude.ai, the marketplace install with the private repository, permission prompts
  in a normal session, quality through the personal install, cloud sessions with
  synced copies of the skills, live drills, second turns, and live web research. None
  is measured here.

## 8. Open questions for the owner

1. **Run plan.** This plan runs P2: Haiku at 10 runs per fixture and room on every
   module, and mock-interview at 10 on Sonnet and Opus, for about 49 points and $1,000
   of runs. P0, all at 5 runs, costs about 33 points and $650; it leaves the checks and
   truthfulness items weaker, and Haiku job-underwriter on its 7-point margin. P3, all
   at 10, adds about 7 points more and mostly helps job-underwriter's checks.
   Resume-tailor alone at 10 on Sonnet and Opus would add about 3 points and $70, and
   would stop two broken runs from tripping its graded item (section 4.1).
   Recommendation: P2. The thresholds are the same under every plan.
2. **H1, what counts as compliant.** This plan keeps rule 2's "at most one sentence"
   and gives that sentence a list form. The alternative is to allow two sentences that
   each name their rows, which would have passed most saved runs (Sonnet 78 of 80, Opus
   68 of 80, Haiku 27 of 47), but changes the rule rather than meeting it.
   Recommendation: keep one sentence, with the list form.
3. **Code identifiers that hold the old name as one word:** `--via frontdoor`, `--arm
   frontdoor`, `check_skills.py --only frontdoor`, `MEASURED_FRONTDOOR` and the
   `evals/arms/frontdoor/` folder. They appear in `README.md`'s backlog, in
   `evals/README.md` and in `CONTRIBUTING.md`. No README holds the two-word name.
   Recommendation: they are commands and constants, not the name in prose, so decision
   9 does not reach them this round; rename them in a separate harness commit after the
   round, so that the harness this round measures with is the one tested here.
4. **resume-tailor's owed change of shape.** Its watch-out row cites 33% altered quotes,
   measured by graders on older text, and says a change of shape is still owed. The new
   traces check fails 2 of 150 saved runs. Recommendation: decide after the round, with
   its traces rate. If the check fails in at most 1 run in 20 on every model, record the
   issue as closed by measurement and keep the watch-out line, whose wording is yours to
   change or keep.
5. **The whole bar's false-miss rate.** With nothing wrong, the round would miss
   somewhere about one time in four or five: 5–7% on Sonnet, 9–15% on Haiku and 6–9%
   on Opus (section 4.5). It comes from gating nine pairs of module and model and three
   routing comparisons at once. This plan already made every text-change guard a test
   and widened the starved margin to 3 of 20. Lowering the rate further means loosening
   items that earlier rounds found real losses on, such as Haiku's single-module item.
   Recommendation: accept it, since a false miss costs a decision, not a re-run.

## 9. Choices made in this plan

Where the inputs to this plan disagreed or left a gap, this plan decided as follows.

1. **A quick check names what it checks.** All inputs set the limit at two calls; only
   the harness required each call to name the material. This plan adds that to the
   text, so the text and the check agree.
2. **Eval 5 drops its copy details; eval 8 keeps "copied this morning".** §4 already
   says a pasted page answers its target, so dropping them needs no new text.
3. **Mock-interview eval 7 declares its target 5 quick-checkable**, for consistency
   with eval 8. It moves no saved figure.
4. **The install line is the qualified one**, since the Claude Code builds do carry the
   modules beside Tuesday.
5. **CI edits that pass only with the new text go in the text commit**: the H1 form
   reading, its exclusion from the gated units, and the test constants; the triggers
   group; and the tie of the call limit to the text.
6. **`MEASURED_FRONTDOOR` stays unchanged until the round is scored.** Every input
   agreed. The text commit is still pushed when it is made, with CI failing in the
   frontdoor group until then, so that it cannot be lost with the session's container.
7. **H1's targets are the quality bar's**, 10% on Sonnet and Opus and 20% on Haiku,
   rather than the text input's "1 run in 5", because their odds were computed and
   they match the watch-out round's practice of a wider figure for Haiku.
8. **H1 is read by its sentence count**, not by the reason the check reports first, so
   a run with both a set claim and a second sentence counts in both.
9. **Every "worse" result and guard is a test at p below 0.01.** A fixed 5-point margin
   on set claims would fire by luck 13–27% of the time on Haiku.
10. **The calls item reads each fixture on its own runs**, and only eval 8, whose prompt
    does not change, is read for worse.
11. **The checks item uses p below 0.01.** At 0.02, Haiku's whole-bar false-alarm rate
    would pass 10%.
12. **Haiku job-underwriter's truthfulness reads `proposed_language` alone.** The full
    pair cannot move on Haiku. This plan calibrated the change: Haiku's whole-bar rate
    goes from 5.6% to 6.0%.
13. **`ledger_counts` stays bundled with the hard-gates line in job-underwriter's
    fixtures.** The calibration was built on that bundling, and splitting it would
    change the graded expectations.
14. **A check family applies only where its slot was written**, so a run with no fit
    snapshot does not pass the snapshot's slots.
15. **The truthfulness family becomes a `compare_arms` row**, two for job-underwriter,
    and section 4.2's measures a block, so every gated number is one the repository's
    scorer prints.
16. **Haiku's single-module routing item is +10 points and at least 60%**, not round
    3's +15 points and two thirds, which misses by luck 10–26% of the time.
17. **No module starved allows 3 of 20 runs**, not round 3's 2, which would miss by
    luck 5.6% of the time on Opus.
18. **Spanning gets a 2-run margin, and Opus case 10 leaves Opus's spanning item**, to
    be read from its own 50 runs.
19. **The hidden-module item keeps round 3's zero rule on routing runs**, and adds a
    limit of one reach over every Tuesday session of the round, quality runs included,
    since one reader reads both.
20. **Tuesday firing after an explicit command stays reported, not gated**, as in round
    3. The explicit-command item already gates that the named module keeps the turn.
21. **The extra case runs are 50 per arm, not 30**, for about $2 more and power of 80%
    instead of 35%.
22. **Quality runs first, Thursday and Friday; routing runs on Sunday 15**, a day no
    case names.
23. **A text-change item that is not closed does not stop the text shipping**, unless
    it is worse than its baseline or breaks a guard.

## Appendix: evidence

The evidence behind this plan is kept outside the repository, with the session that
wrote it: the verified summary of every miss, gap and failure; the quality check's and
the smoke's saved runs, their bars and their re-checks; the routing rounds' results;
the text change's trial on a scratch copy; the harness prototype; and the calibration
scripts and their outputs. The README ledger's entries record each of those steps.
