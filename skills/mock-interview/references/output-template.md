# Output template

## Contents

- Session-mode pack skeleton
- The message that presents the pack
- The fit snapshot
- The prohibited list
- Question banks
- Target accounting in Sources
- Loop mode
- Drill mode
- The dossier offer
- Regeneration (Step 5 of SKILL.md)


## Session-mode pack skeleton

Deliver these sections in this order. The conditionality column is binding — a section whose condition fails is dropped entirely, not filled with padding, because an empty-calorie section teaches the candidate to skim.

| # | Section | Include when | Content spec |
|---|---|---|---|
| 1 | Title block | Always | Role, company, interviewer name + relationship if known; one line on what changed if this is a regeneration |
| 2 | How to use + type key | Always | Personas = how it's asked, types = what's scored; the five type tags with one-line meanings; "guidance is scaffolding, not a script" |
| 3 | Prep triage | Prep time known | A prioritized schedule sized to the stated time: the few things done well, in order, each tied to a section or question ID — closing with an explicit "everything else is insurance" line. Never pad it to look busy |
| 4 | Fit snapshot | Always | The table worked below under **The fit snapshot**. Confidence holds exactly one of `high`, `medium`, `low`, `none`; provenance exactly one of `[grounded]`, `[inferred]`, `[generic]`; gap type exactly one of the six in `references/evidence-conventions.md` §3, chosen by the routing rule below the worked table. With no background at all — no CV, nothing about the candidate's past in the conversation or a dossier — it is the worksheet variant: the same columns, every evidence cell `none given`, confidence `none`, gap type `discovery` except a gate row, which the routing rule makes `hard_gate` with the cell that rule gives it, and every other row's bridge column holding what strong evidence looks like, then an answer slot (F3's shape) where a raising source raises the requirement, otherwise a selection scaffold ending in its honest branch, both as defined in `references/question-rubric.md`; where only some requirements have no quote, those rows take that shape and the snapshot stays a normal one. Where the requirements come from: the JD's own words, quoted; with no JD, the recruiter's or interviewer's own words, quoted, `[grounded]`; then a fetched representative JD, quoted with its source named, `[inferred]`; otherwise role-family requirements as plain unquoted prose, `[generic]`, with the representative-JD search in the upgrade menu. Only text that exists in the user's inputs or a fetched page goes inside quotation marks |
| 5 | Graded deliverables | Recruiter/HR pre-declared a deliverable (POV, presentation, take-home) | One build section per declared deliverable: the grounded facts to build on — any about the candidate given as the fit-snapshot row it draws on (F#) and a sentence quoted exactly from that row's evidence cell, per the pack-cell rule in `references/question-rubric.md` — 2–3 defensible theses each with a mandatory concession, differentiation strategy against the consensus answer (with the anti-pick where the role warrants saying no), and the requested close (e.g., customer benefit) if HR named one. In loop mode these are shared sections, like the values cheat sheet |
| 6 | Grounding brief | L2 research ran, or an equivalent strategy brief was provided | Learn-the-vocabulary company section: current segmentation language, headline numbers, live leadership and strategy context, recent moves. The candidate should sound current, not archival; flag stale framings in provided documents without coaching the candidate to correct the interviewer |
| 7 | Reading the interviewer | Real interviewer info exists | Career pattern, self-described style, 2–4 practical implications, the mirror opportunities (shared jumps, shared vocabulary) — a shared jump pairs the interviewer's public path with a sentence quoted exactly from a named fit-snapshot row's evidence cell (F#), never a summary of it; where no row's evidence carries the candidate's side of the jump, it is not offered as one. Public footprint only |
| 8 | Persona table | Always | Persona × how it shows up × likelihood **with the reasoning shown** × counter-strategy. A counter-strategy is a rehearsal method, not a claim: wherever it is applied to this candidate — a named story, an arc, a walkthrough — the quote-or-slot rule in `references/question-rubric.md` applies |
| 9 | Question banks | Always | One sub-table per persona, ordered by weight, in the shape worked below under **Question banks**: Provenance comes before the guidance and carries every candidate sentence the guidance rests on. Provenance is its own column, never a tag trailing the rationale — as a suffix it is punctuation the writer drops, as a column it is a cell that renders empty |
| 10 | Values / principles cheat sheet | A values-style round detected, as `references/research-checklist.md` defines it, and the company's published values in hand, fetched or pasted | Table: value (official name) × working meaning (paraphrased) × the candidate's mapped story — the fit-snapshot row ID and a sentence quoted exactly from that row's evidence cell where one carries a story, otherwise a selection scaffold ending in its honest branch (`references/question-rubric.md`) |
| 11 | Reverse questions | Always | ≥5, each with "why it lands"; ≥1 tied to the interviewer's path when a profile exists; 1 reciprocity question when peer |
| 12 | Delivery coaching | Assessment provided | Table: assessed trait (the report's own framing) × where it helps in this loop × where it could cost you → counter-move, keyed to question IDs. Restate the ground rules: never mention the assessment in the interview; tuning, not content |
| 13 | Prohibited claims | Always | What this pack will not coach, and why: each entry with its basis and its honest form, in the shape worked below under **The prohibited list**. From a dossier's `prohibited_claims` and `evidence_state.rejected_inferences` where one is present; **built locally from the fit snapshot otherwise** — the claims a candidate reaches for under pressure. What may be listed, what is an answer slot instead, and the honest form of each kind of entry are defined once, in the prohibited-list rule of `references/question-rubric.md`. Present in every pack, not only when something was refused: otherwise the candidate cannot tell a pack that found nothing to inflate from one that inflated nothing. Built before the question banks, so the banks are written against it |
| 14 | Sources | Always | Provided documents; every search and fetch sent, refused ones included, by query, with what came back: the URLs it returned, "no results" or "nothing attributable" — each of which is a returned result — or "refused" or "errored" for a call that returned nothing. The label each outcome gives its target is the target accounting's, below. When a dossier was consumed, say so and name which sections it supplied. Plus the **target accounting** worked below — the `Research tier` line, which is the only place the tier is stated, then one row per declared target in `references/research-checklist.md`, each marked `yes`, `skipped`, `n/a` or `unavailable` |
| 15 | Upgrade menu | Always | Each missing input → what adding it unlocks, concretely ("interviewer's profile → personalized persona weights + a tailored reverse question"; "JD text → six `[inferred]` rows become `[grounded]`"). With no dossier present, one line on what one would add — never phrased as a prerequisite |

Formatting: markdown tables; no pipe characters inside cells; question IDs letter-by-persona (A1, A2, B1…) so the drill and the coaching section can reference them; cells crisp — guidance speakable in 90–120 seconds, rationales 2–3 sentences.

File conventions: save as `{company}_{role-slug}_interview_pack.md` to the outputs directory and present it. The file ends at the upgrade menu: its last line is the menu's last item, and, per rule 7 of `references/output-discipline.md`, it holds no offer, no question and no watch-out line. The offers, the questions and the watch-out line close the message that presents it (`closing_order` in SKILL.md), worked below under **The message that presents the pack**. Offer a Word (.docx) conversion in one line rather than producing one by default — most candidates iterate in markdown and convert once at the end.

## The message that presents the pack

The saved file and the message presenting it are two things, and the watch-out line belongs to the message. The rule is `references/output-discipline.md` rule 7; this is its worked form, for a session-mode pack saved as a file.

The saved file's last lines — the upgrade menu, and nothing after it:

```text
## Upgrade menu

- The interviewer's name → a tailored reverse question, and persona weights read from their public footprint
- The recruiter's prep email → coverage of any pre-declared deliverable
```

The message that presents it, whole:

```text
Your prep pack is saved as {company}_{role-slug}_interview_pack.md. I built it for a hiring-manager round, since your note didn't say who you're meeting.

Say the word and I'll play the Skeptic on B2, the question the pack names as its highest-ROI prep.
I can also save a tuesday-dossier.md recording the gaps this prep exposed, for you to carry into later sessions.
If you'd like the pack as a Word document, say so and I'll convert it.

Is the person you're meeting your future manager, or a peer on the team? The answer reweights every bank.

**Watch-out:** Suggested answers can make your experience sound bigger than what you told me — rehearse only what you actually did, in your own words.
```

The Word offer sits with the other offers. The message's last line is the `watch_out` sentence (rule 7).

## The fit snapshot

The pack's spine, and the section every question bank reads from. Its columns
are worked here rather than described, because this file spent three versions
naming them in a sentence — including the sentence explaining that an enum with
no column to live in gets invented at write time. A table described is not a
table rendered, and what the writer copies is the shape on the page.

| # | Requirement (source) | Evidence, verbatim | Confidence | Provenance | Gap type | Gap and bridge language |
|---|---|---|---|---|---|---|
| F1 | "own the grants pipeline from call to award" — JD | "Ran the small-grants round for three years" — your CV | medium | [grounded] | transferability | Your material says the round, not the pipeline, with nothing inspected behind it, and the words stay there: "For three years I ran the small-grants round." Answer slot: the JD's call-to-award line makes a probe on the round's stages likely. If any were yours to set, say which and how you decided, in your own words; if there was no such step, or it was not yours, say so plainly and stay with the round you ran |
| F2 | "maintain conflict-of-interest declarations for assessment panels" — JD | "Kept the conflict-of-interest register for every assessment panel" — your CV | medium | [grounded] | none | No gap, but a CV line with nothing inspected behind it, so expect a probe on it. Lead with the register in the quote's own terms — you kept it, for every assessment panel — because a named record beats an adjective |
| F3 | "define and track outcome measures for funded projects" — JD | "Collected end-of-grant reports from every funded group" — your CV | low | [inferred] | discovery | Collecting reports is not defining measures, and the bridge should not be stretched. Answer slot: if any of those reports were scored or counted, say what was counted; if none were, say so, and say what you would measure first |
| F4 | "prepare grant spend for the annual external audit" — JD | "I've never been involved in an audit" — your message | none | [grounded] | capability | A gap wording cannot close, and the candidate has said so. Words: "I haven't been involved in an audit." Then how you would learn it, said as a plan and never as a past. Never a claim to audit work, and nothing added to make the gap feel smaller |

Seven rules the columns enforce, in the order they get broken:

- **`Confidence`, `Provenance` and `Gap type` hold one token each.** `low-medium`
  and `[grounded, partial]` are both real failures from real runs, and both are
  a qualifier squeezed into a cell with room for one answer. The gap type never
  appears as prose in the bridge — written there, `presentation` became "bring
  the specifics", which is an instruction to supply them.
- **`Evidence, verbatim` holds the candidate's own words and nothing else.** Each
  cell is either `none given`, or one or more of their sentences in double
  quotation marks, each followed by its own dash and where it came from, named as
  exactly one of: your CV (a résumé is "your CV" too), your message, the coach's
  notes, or a dossier row (`dossier R3`). Two such segments are separated only by
  what adds no words — a comma, semicolon, full stop, line break, space or "and". No summary, no paraphrase, nothing
  appended to the quote. A summary in this column is the first place a pack
  invents: in a measured run it turned an amount the candidate said they had
  influenced into a target they had reported against, and the question banks then
  cited that summary as something the candidate had said. Everything the pack says
  about the candidate's past draws on these quotes and on nothing else.
- **`Requirement (source)` quotes only what was supplied or fetched.** A
  requirement in quotation marks must exist in the user's inputs or a fetched
  page, with its source named; a role-family requirement written from no source
  is plain prose labeled `[generic]`, and it raises no answer slot.
- **The qualifier goes in `Gap and bridge language`** — this skill's declared
  `qualifier_fields`, and the only free-text column here. That is why it exists.
- **A gap row still gets words, and the words have a source.** F4's are a
  negative the candidate stated, so the pack may give them back; F3's gap is
  something the material is silent on, so its words are an answer slot. A plain
  acknowledgment the candidate never stated is as much an invention as a claim
  they never made.
- **The gap type follows the evidence cell, not the writer's sense of the row.**
  This is the one statement of the routing; `SKILL.md` points here. A gate is
  decided first, and every other bullet applies only to a requirement that is
  not a gate, or is a gate the material shows met:
  - `hard_gate` when the requirement is a gate, as
    `references/evidence-conventions.md` §3 defines one, and the material does
    not show it met, whether it shows it unmet or says nothing. That section
    governs the row: surfaced, never bridged, and its cell asks nothing. Where
    the material says nothing about the gate, the cell says, as the pack's own
    observation, that your material does not establish it. Where the candidate
    stated it unmet, or a dossier records it, the cell's words come only from
    that stated negative or the dossier field, as for `capability`. The one
    question that section allows, whether the gate is met, is asked only where
    `SKILL.md` Step 1 item (d) asks it. A gate the material shows met routes by
    its evidence cell like any other row.
  - `none` when a quote already reaches the requirement in role-relevant terms
    (F2). The band plays no part here: confidence is the other axis, set by
    `references/evidence-conventions.md` §2 alone.
  - `presentation` only when the evidence cell holds a quote that already reaches
    the requirement in other terms. Its bridge rewords only that quote, adds no
    practice, figure or event, and never tells the candidate to supply specifics.
  - `transferability` when a quote carries adjacent work that does not reach the
    requirement (F1). Its words are that quote at its own scope; any wider step is
    an answer slot inside the quote's scope.
  - `discovery` when the evidence may exist and the material does not show it:
    the cell is `none given`, or its quote touches the requirement without showing
    whether it reaches it (F3), and the candidate has stated no absence. Its words
    are an answer slot. Silence is `discovery`, never `capability`.
  - `capability` only when the candidate stated the absence, or a dossier records
    it (F4). Its words come only from the stated negative or the dossier field.
- **Bridge language is spoken aloud, so `reframing-audit.md` governs every clause
  of it** — six axes, and the incident-or-practice axis is the one that slips:
  F1 ran a round, and running a round does not mean setting its stages. That is
  why F1's bridge asks rather than says. This row once read "I owned which
  integrations shipped in what order" beside evidence that said only that the
  candidate led them — the worked example added the practice the pack exists to
  stop adding, and packs copied it. Its next version sat in a fixture's own domain
  and presupposed an event no quote carried. These rows sit in a domain no fixture
  uses, so that copying their wording hands no fixture its answer; their gap
  shapes are the ones every pack meets, because teaching those shapes is what the
  table is for.

`Confidence` grades the candidate's evidence and `Provenance` grades what this
skill wrote about it: F3 is `low` because the evidence is thin, and `[inferred]`
because the bridge is this skill's derivation. Gap type is a third call: F2 is
`medium` because a CV line alone has nothing inspected behind it, and `none`
because its quote already says what the JD asks. On a gap row, Provenance grades the
pack's statement of the gap, not a capability claim: F4's gap is one the candidate
stated, so it is `[grounded]` on that quote, and a worksheet row's `none given`
takes the label of its requirement's source — `[grounded]` for a supplied JD or the
recruiter's or interviewer's words, `[inferred]` for a representative JD,
`[generic]` for a role-family requirement. The "—" that
`references/evidence-conventions.md` §5 gives `none` evidence means no capability
claim is written from it, and these rows write none.

With a dossier, the evidence cell quotes `evidence_map.evidence[].quote_or_summary`
or `handoff_to_mock_interview.verified_candidate_evidence` exactly, with the
dossier row as its origin — never `candidate_claim`, which is the underwriter's
restatement and can be the widened form, and never `reasoning`. A confidence note
appended to a verified claim is not part of the quote: it goes to `Confidence` and
into the bridge as a stated limit. The map's `confidence` and `gap_type` are the
same vocabulary as this table's; its `reasoning` is the underwriter's analysis,
which a bridge may cite as a limit and never as something the candidate did.

## The prohibited list

Section 13, built from the snapshot above before a bank is written. Each entry
names its basis, because the basis decides the honest form, under the
prohibited-list rule in `references/question-rubric.md`:

| Not coached | Basis | Honest form |
|---|---|---|
| Owned the grants pipeline | Inflated form of F1 | F1's quote at its own scope. The limit is the pack's observation, not words for the candidate: the material says the round, not the pipeline. A2's slot stays inside the round |
| Defined outcome measures for funded projects | Inflated form of F3 | F3's quote at its own scope. A4's slot asks only what those reports counted |
| Has prepared grant spend for audit | Negative the candidate stated, F4 | The plain acknowledgment F4 gives: "I haven't been involved in an audit." No slot |

## Question banks

One sub-table per persona, in this shape. Provenance sits before the guidance
because it is chosen first: the sentences a row may draw on are fixed before a
word of guidance is written, rather than found afterwards to fit guidance that
already exists.

| # | Question | Type | Provenance | Answer guidance | Rationale |
|---|---|---|---|---|---|
| A1 | "Walk me through how you ran the small-grants round." | EXP | [grounded] "Ran the small-grants round for three years" | Story-mapped on F1: the round, and the three years, which are the beats the quote states; tell them in your own words. Answer slot: the JD's call-to-award line makes a probe on the round's stages likely. If any stage was yours to set, say which and how you decided; if there was no such decision, or it was not yours, say so plainly and describe how you ran the round | F1 is the evidence for the pipeline requirement and the likeliest place to be probed; EXP because it tests what was actually the candidate's |
| A2 | "What part of a grants pipeline have you owned yourself?" | JD | [grounded] "Ran the small-grants round for three years" | The highest-ROI rehearsal in this pack, and the hold is only what the quote carries: "For three years I ran the small-grants round." Answer slot: if any stage of the round was yours to set, say which and how you decided, in your own words; if none was, say so plainly and describe how you ran the round — the honest branch is a limit, not a confession. Hold through two follow-ups by returning to the round, never by adding to it | F1 is where the role's pipeline mandate presses hardest, so this objection arrives in some form; JD because it scores the stated requirement |
| A3 | "An assessor tells you on the morning of a panel that she knows one of the applicants. What do you do?" | CASE | [generic] | Structure it: what you would ask her first, what you would do about this application today, how the panel's decision stays sound, and what you would record. The question needs no claim about your past, so the guidance makes none | A live problem from the JD's conflict-of-interest line (F2's requirement), asked as a decision rather than a record; `[generic]` because it is a pattern for the problem, not a fact about this employer |
| A4 | "The role tracks outcome measures for funded projects. What have you measured?" | EXP | [inferred] "Collected end-of-grant reports from every funded group" | Say what you collected and from whom, in those words. Answer slot: if any of it was scored or counted, say what was counted; if none was, say so plainly and say what you would measure first. Never describe a measure you did not track | F3's thin bridge, rehearsed so the honest answer is ready before the probe arrives; the question's premise is the JD's, and the guidance does not adopt it |

Rules this shape enforces:

- **Provenance carries every sentence the guidance's claims about the candidate
  rest on, each quoted exactly as it appears in the fit snapshot** — except a
  dossier item a plain acknowledgment rests on, which is named and quoted as the
  plain-acknowledgment paragraph of `references/question-rubric.md` says. A row reference
  ("see F1"), "as above", or a paraphrase is not a quote. A row whose guidance makes
  no claim about the candidate, like A3, carries its label alone.
- **Any clause in a bank cell that says what the candidate did, owned, decided or
  was responsible for rests on one of its own row's Provenance quotes and says
  nothing the quote does not, or it is an answer slot.** That holds whatever the
  label: `[inferred]` names a derivation about the role or the fit, and never
  stands in for the candidate's sentence. Where the sentence must be on every
  other surface is the pack-cell rule in `references/question-rubric.md`.
- **The Question is the interviewer's line.** What it may presuppose is defined
  once, in `references/question-rubric.md`. Here A1 is premised on F1's own quote;
  A2 and A4 presuppose what the JD raises and the quotes do not carry, so each
  holds a slot whose second branch lets the premise be false; A3 is a live problem
  and presupposes nothing about the candidate's past.
- **Rationale refers to the candidate's history only by fit-snapshot row ID** —
  "F1 is the evidence for…" — and never restates or extends it.
- **An answer slot is not a question to the user.** It is addressed to the
  candidate's answer in the interview, it is an instruction rather than a question,
  and it asks for no reply in this conversation, so it does not count under
  `output-discipline.md` rule 1. Where an answer would make the pack better, that
  belongs in one upgrade-menu line naming the rows it would upgrade, never in the
  closing questions.

## Target accounting in Sources

One row per declared target — the L1 targets, then the L2 ones when L2 ran. It is a table because `interaction-grammar.md` §4
sends a skipped search here, and a search that ran wastefully leaves a pack
identical to one that skipped correctly — prose cannot tell them apart, and an
unfilled row can.

Research tier: L1 — searches 3 of 6, fetches 1 of 2

| Target | Status | What it moved, or would have |
|---|---|---|
| 1. `{company} values` | yes | Values cheat sheet, section 10 — four principles by name |
| 2. `{company} interview process {role family}` | yes | Loop structure; persona weights follow the named rounds |
| 3. `{company} strategy` / recent news | skipped | Could not have moved the CO bank: the strategy brief the user pasted already supplies current priorities and recent moves |
| 4. `{interviewer name} {company}` | n/a | No name was given, so there was no query to form; the interviewer read is absent and the upgrade menu says what a name would unlock |
| 5. representative `{role title}` JD | skipped | The JD the user supplied fixes the fit snapshot and the JD-tagged questions |

This is an L1 run; an L2 run adds rows 6 to 9 below these, in
`references/research-checklist.md` order.

The label follows what happened, facts first, per `interaction-grammar.md` §4. A
target a call was sent for is `yes` if any call returned a result — an empty or
unattributable one included, said as "not established" — and `unavailable` only
if every call was refused or errored; it is never `skipped` or `n/a`, and if it
moved nothing its `yes` row says so. A target no call was sent for is `n/a` if
the inputs cannot form its query — no name at all; a first name with a title and
the company is a name — `skipped` if the inputs already fix every output it
feeds, and otherwise `unavailable`: this host offers no search, the user chose L0
or declined research, or the budget went on higher-priority targets first, with
what it would have moved, which the upgrade menu then offers. A judgement that a
search was not worth running is never `unavailable`. An input fixes an output
only when its content is in hand — a pasted values page can, and "I've read their
values page" cannot. In a host with no search, rows 1 and 2 above would read
`unavailable`, each naming what it would have moved, and rows 3 to 5 would not
change, because the inputs decide them and the host does not. A search sent
outside every declared target gets an un-numbered `yes` row after these, saying
what it was and what it moved. A `yes` row's search appears among the queries the
Sources section lists; an accounting reporting a search the pack shows no query
for is the failure this table exists to make visible. So a `yes` row has at least
one listed query for its target that returned URLs, "no results" or "nothing
attributable", and an `unavailable` row whose target had calls sent has every one
of them listed as "refused" or "errored".

## Loop mode

Use when the user faces multiple scheduled rounds. Ask which rounds are on the calendar (this piggybacks on the Step 1 message — it does not add a second elicitation round). Structure: one shared fit snapshot + sources block, then a mini-pack per round with that round's persona weights, its own bank (8–12 questions), and its own reverse questions. The values cheat sheet lives with whichever round a loop source names as values-style (`references/research-checklist.md`). The upgrade menu is shared and sits at the end.

A known multi-session round with an *unknown* schedule — "the final round" at companies whose finals are several back-to-back sessions — is not loop mode. Run session mode with blended persona weights, and offer per-session mini-packs in the upgrade menu for when the user has the schedule. Do not assert how this company's final is structured unless a loop source, as `references/research-checklist.md` defines it, established it; the upgrade-menu line can be conditional — "if your final is several sessions, send the schedule" — which needs no claim at all. Loop mode needs a schedule to key on; guessing one fabricates structure.

## Drill mode

Offer one drill after delivering any pack — a single line, no pressure. The pack is preparation; rehearsal is transfer, and the delivery flaws the coaching section predicts only surface out loud.

Running a drill:

1. The user picks a persona and optionally a question ID. Default when they don't choose: the highest-weight persona, on the question the pack named as highest-ROI.
2. Adopt the persona's register and ask the question. Follow up at least twice, and make the follow-ups react to what the candidate actually said — a scripted follow-up teaches nothing. Pressure-persona drills interrupt and time-box; prober drills ask for the denominator; peer drills push on the seam.
3. Stay in persona during the exchange. Break persona to give feedback only when the exchange is done.
4. Score against three things: the pack's own guidance for that question, the pack's named rehearsal priorities, and the type-specific bar from `question-rubric.md` (metric answers name their weakest assumption, or say plainly they do not know how the figure was counted; pressure answers hold-then-concede; values answers land the hard truth). An answer slot is met when the candidate answered either branch from their own experience or said plainly the practice was not theirs; it is never scored against the practice it names.
5. Feedback is measured against that question's guidance cell — the beats it named, the weakest-assumption move, the hold-then-concede structure — because the cell is the rubric and was written first. Format: what landed / what to change / one line worth stealing verbatim. "What to change" may repeat an answer slot's question and never prescribes the practice it names; the line worth stealing comes from the candidate's own drill words or the cell's quotes, and it is proposed language, so the reframing audit governs it. There is no numeric score: a number would average away the one beat they missed, which is the entire finding. Then offer another round or a different persona — and, once, the dossier offer above: a drill is where `rehearsal_gaps` with `observed_in: drill` actually come from. The feedback message ends with the watch-out line; the in-character turns before it carry none (`references/output-discipline.md` rule 7).
6. If the candidate shows real distress — interview anxiety is real and drills can spike it — drop the persona immediately and be a person about it. The drill serves the candidate, never the reverse.

## The dossier offer

One line at delivery, alongside the drill offer, and again after any drill: an offer to emit or update `tuesday-dossier.md` with this engagement's `pack_feedback` — the objections the fit snapshot exposed, the requirements where no credible story surfaced, and the stories told in prep that the CV doesn't carry. Full spec in `references/dossier-handoff.md`.

Keep the offer to what it buys the candidate: those leads are what the underwriter would want to verify next, and carrying them costs one file. Never gate the pack on it, never re-offer after a decline, and never let a lead recorded in feedback flow back into this pack's guidance as though it were confirmed evidence.

## Regeneration (Step 5 of SKILL.md)

When new inputs arrive, open the delivered pack, regenerate the affected sections, and lead the new version's title block with a one-line changelog ("relationship updated to peer → persona weights recomputed, bank G added, reverse questions retuned"). A fact the user states as input, outside a drill — an answer to an answer slot included — is new quoted material: it enters the fit snapshot's evidence column verbatim, and the rows that drew on it regenerate. Something said inside a drill is not: it stays a lead, recorded in `pack_feedback` if the candidate takes the dossier offer, and becomes material only when they say it outside the drill. Consistency check before redelivering: no section may contradict the new fact — a stale "hiring manager" framing surviving in the interviewer read while the persona table says "peer" is the failure mode to catch.
