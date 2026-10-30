# Suite-level evals

Per-skill evals live in `skills/<name>/evals/` and test one skill's behaviour.
What they cannot test is **routing**: which skill fires at all. That decision is
made across the whole available-skills list, so an assertion about it has no
honest home inside any one skill — hence this directory.

## Routing

`suite-routing.json` holds realistic requests and the route each should take:
a named skill, `either` (a genuinely spanning request), or `neither` (a
near-miss that must pull no skill at all). The near-misses matter most — they
share the domain's whole vocabulary and are where over-triggering shows up.

`run_routing.py` puts every skill in front of the model at once and records
which one it reaches for. Four properties keep it honest:

- **It installs the real skills**, copying each one into a throwaway project's
  `.claude/skills/`, so they reach the model the way installed skills do and
  carry the descriptions that actually ship. Nothing is duplicated here.
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
  Keep it for honesty of the fixture, not for the score.
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
returned nothing for it is partially graded, and an expectation resting on a
partial run is unresolved, never clean: the old summary used every run as its
denominator and counted only explicit failures, so a grader that skipped an
expectation turned a deterministic failure into an intermittent one.

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
  other word but a function word is one the request uses, and it carries no
  other target's term (`output_checks.identity_search`). `stray_samples` are
  queries a run might send that serve no target ("Brindlemoor layoffs
  glassdoor"); CI fails one that any target's terms or identity claim, and an
  `identity` no stray sample tests. Each target also lists `on_target_samples`,
  queries a correct run might send for it, and a target that accepts `n/a` or
  `skipped` lists `hunt_samples`, queries that really are hunts for it. CI
  checks the terms against both with `aimed_at` itself, in every mode the
  fixture runs, a canned room's sample read as the log entry the stub server's
  own page route (`research_server.search`) would leave; where no correct run
  sends a call (`zero_calls` or `declined`), it skips the cross-target collision
  check.
- `user_links`: the links the user gave the skill to read (absent means none).
  A URL the prompt names only as the source of text the user pasted is not one.
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

A fixture with the `quotes` check also declares `candidate_text`, top-level: the
candidate's own words, against which the verbatim evidence column and the banks'
Provenance are checked (`[]` when the candidate gave nothing quotable). A
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
- **canned** serves the fixture's own pages through `research_server.py`, a
  stdlib MCP server with deterministic search and fetch, and removes the built-in
  web tools so the only search the skill can reach is the fixture's. Pages score
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
the flags, the sha256 of each expectation it graded and the grader prompt's
version, so a later set can be compared like with like.

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
  the fixture declares, and `zero_calls` fails on any research call. A fetch
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
  no research record leaves the canary unchecked.
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
  second sentence), `snapshot_count` (the set claims in the snapshot's prose,
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
  severe-red-flags slot naming exactly its high entries). The hard-gates line's
  closing "candidate constraints not given" clause is judged against the
  fixture's `candidate_constraints` (above); a response with no risk register
  leaves `severity` unchecked.
- **Quotes** (`quotes`): the verbatim evidence column holds the candidate's own
  words "and nothing else", and a Provenance cell carries every candidate
  sentence its guidance rests on, so every quotation in either, of any length,
  must appear on word boundaries in the fixture's `candidate_text` — `[]` means
  nothing the candidate gave is quotable, and a fixture without the key has that
  check reported unchecked, never run against the prompt instead. A Provenance
  quotation must also appear in the response's own evidence column, because the
  template quotes it "exactly as it appears in the fit snapshot". Three
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
  them), checked for existence only: every fragment must appear on word
  boundaries in the request or the room's pages. An origin that names the
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
  followed by "and"), with nothing else in the cell.

Each finding is judgement or format and they are counted apart: a qualifier
beside a status label and a `yes` with no search behind it are different defects
with different fixes. A third kind, `fixture`, marks a fixture that cannot be
checked as written, such as a canary whose page is not one of its own; it fails
the run so that it gets fixed, and is counted apart from both. A table that is
not there is absent, one that cannot be read is unparseable, and neither is a
pass. A check that needs the research record is listed as unchecked on a run that
has none, never passed. A check failure counts like a grader's,
keyed `chk:<check>:<target>`, and triggers the retry pass the same way.

### Exit codes

- `0`: every expectation and check passed in every valid run.
- `1`: a grader or a check failed something.
- `3`: a harness-invalid run or an unresolved expectation exists; this wins over
  `1`, because a set with holes in it is not yet a measurement. (Not `2`, which
  argparse and `recurring.py` already use.)

### Regrading a saved set

Grades are never overwritten. `--skip-execute` grades saved runs only in an
`--out` that holds no grades yet; to regrade a set, `--regrade-from SRC --out
NEW` copies its responses and meta into a fresh directory and grades there.
`--expectation N` restricts grading to the numbers named.

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

These evals are not run in CI: they need a model, cost real tokens, and take
minutes. Run them in a session against any change that could plausibly move
triggering or output — a description edit, a new skill, a boundary reworded.
`evals/test_harness.py` does run in CI: every decline path above has a test that
spends no model calls.
