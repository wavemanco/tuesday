# Output template

## Session-mode pack skeleton

Deliver these sections in this order. The conditionality column is binding — a section whose condition fails is dropped entirely, not filled with padding, because an empty-calorie section teaches the candidate to skim.

| # | Section | Include when | Content spec |
|---|---|---|---|
| 1 | Title block | Always | Role, company, interviewer name + relationship if known; one line on what changed if this is a regeneration |
| 2 | How to use + type key | Always | Personas = how it's asked, types = what's scored; the five type tags with one-line meanings; "guidance is scaffolding, not a script" |
| 3 | Prep triage | Prep time known | A prioritized schedule sized to the stated time: the few things done well, in order, each tied to a section or question ID — closing with an explicit "everything else is insurance" line. Never pad it to look busy |
| 4 | Fit snapshot | JD or CV present (either) | The five-column table worked below under **The fit snapshot**. Confidence holds exactly one of `high`, `medium`, `low`, `none`; provenance exactly one of `[grounded]`, `[inferred]`, `[generic]`. CV absent → self-assessment worksheet variant: requirement × "your evidence here" prompts × what strong evidence looks like. JD absent → built from the researched representative JD, labeled |
| 5 | Graded deliverables | Recruiter/HR pre-declared a deliverable (POV, presentation, take-home) | One build section per declared deliverable: the grounded facts to build on — any about the candidate quoted verbatim, as the question banks require — 2–3 defensible theses each with a mandatory concession, differentiation strategy against the consensus answer (with the anti-pick where the role warrants saying no), and the requested close (e.g., customer benefit) if HR named one. In loop mode these are shared sections, like the values cheat sheet |
| 6 | Grounding brief | L2 research ran, or an equivalent strategy brief was provided | Learn-the-vocabulary company section: current segmentation language, headline numbers, live leadership and strategy context, recent moves. The candidate should sound current, not archival; flag stale framings in provided documents without coaching the candidate to correct the interviewer |
| 7 | Reading the interviewer | Real interviewer info exists | Career pattern, self-described style, 2–4 practical implications, the mirror opportunities (shared jumps, shared vocabulary) — a shared jump pairs the interviewer's public path with a quoted line from the candidate's material, never a summary of it. Public footprint only |
| 8 | Persona table | Always | Persona × how it shows up × likelihood **with the reasoning shown** × counter-strategy |
| 9 | Question banks | Always | One sub-table per persona, ordered by weight, in the shape worked below under **Question banks**: Provenance comes before the guidance and carries every candidate sentence the guidance rests on. Provenance is its own column, never a tag trailing the rationale — as a suffix it is punctuation the writer drops, as a column it is a cell that renders empty |
| 10 | Values / principles cheat sheet | Values-style round detected | Table: value (official name) × working meaning (paraphrased) × the candidate's mapped story — a verbatim quote with its origin where one of their sentences carries a story, otherwise a selection scaffold |
| 11 | Reverse questions | Always | ≥5, each with "why it lands"; ≥1 tied to the interviewer's path when a profile exists; 1 reciprocity question when peer |
| 12 | Delivery coaching | Assessment provided | Table: assessed trait (the report's own framing) × where it helps in this loop × watch-out → counter-move, keyed to question IDs. Restate the ground rules: never mention the assessment in the interview; tuning, not content |
| 13 | Prohibited claims | Always | What this pack will not coach, and why. From a dossier's `prohibited_claims` and `evidence_state.rejected_inferences` where one is present; **built locally from the fit snapshot's gaps otherwise** — the claims a candidate reaches for under pressure that their material does not support. Present in every pack, not only when something was refused: otherwise the candidate cannot tell a pack that found nothing to inflate from one that inflated nothing. Built before the question banks, so the banks are written against it; a line here offering the honest version of a claim is a quote from the candidate's material or an answer slot, never a summary of what they did |
| 14 | Sources | Always | Provided documents; web sources with URLs; the research tier used. When a dossier was consumed, say so and name which sections it supplied. Plus the **target accounting** worked below — the `Research tier` line, then one row per L1 target in `references/research-checklist.md`, each marked `yes`, `skipped`, `n/a` or `unavailable` |
| 15 | Upgrade menu | Always | Each missing input → what adding it unlocks, concretely ("interviewer's profile → personalized persona weights + a tailored reverse question"; "JD text → six `[inferred]` rows become `[grounded]`"). With no dossier present, one line on what one would add — never phrased as a prerequisite |

Formatting: markdown tables; no pipe characters inside cells; question IDs letter-by-persona (A1, A2, B1…) so the drill and the coaching section can reference them; cells crisp — guidance speakable in 90–120 seconds, rationales 2–3 sentences.

File conventions: save as `{company}_{role-slug}_interview_pack.md` to the outputs directory and present it. Offer a Word (.docx) conversion in one line rather than producing one by default — most candidates iterate in markdown and convert once at the end.

## The fit snapshot

The pack's spine, and the section every question bank reads from. Five columns,
worked here rather than described, because this file spent three versions naming
these columns in a sentence — including the sentence explaining that an enum with
no column to live in gets invented at write time. A table described is not a table
rendered, and what the writer copies is the shape on the page.

| # | JD requirement | Evidence, verbatim | Confidence | Provenance | Gap and bridge language |
|---|---|---|---|---|---|
| F1 | "own the inbound logistics roadmap" | "Ran the warehouse's weekly intake schedule for three years" — your CV | medium | [grounded] | Ran the schedule, not a roadmap. Words: "For three years I ran the weekly intake schedule. Setting a roadmap is the part I haven't done." Answer slot: if you chose which deliveries waited when the dock was full, say how; if the order was set for you, say so and stay with the schedule you ran |
| F2 | "comfortable building operational tools in spreadsheets or SQL" | "Built the volunteer shift spreadsheet everyone still uses" — your CV | high | [grounded] | No gap. Lead with the spreadsheet — it is the artifact, and artifacts beat adjectives |
| F3 | "define and track supplier performance metrics" | "Collected feedback from partner pantries every quarter" — your CV | low | [inferred] | Feedback collection is not metric ownership, and the bridge should not be stretched. Answer slot: if any of that feedback was counted, say what was counted; if none was, say so, and say what you would measure first |
| F4 | "3+ years managing a logistics team" | none given | none | [grounded] | A titled-years gap wording cannot close. Words: "I haven't managed a team" — then only what F1's quote carries. Never a claim to the title, and nothing added to make the gap feel smaller |

Five rules the columns enforce, in the order they get broken:

- **`Confidence` and `Provenance` hold one token each.** `low-medium` and
  `[grounded, partial]` are both real failures from real runs, and both are a
  qualifier squeezed into a cell with room for one answer.
- **`Evidence, verbatim` is a quote, never a summary.** The candidate's own words,
  copied exactly, in quotation marks, then where they came from — your CV, your
  message, the coach's notes, a dossier row — or `none given`. A summary in this
  column is the first place a pack invents: in a measured run it turned an amount
  the candidate said they had influenced into a target they had reported against,
  and the question banks then cited that summary as something the candidate had
  said. Everything the pack says about the candidate's past draws on these quotes
  and on nothing else.
- **The qualifier goes in `Gap and bridge language`** — this skill's declared
  `qualifier_fields`, and the only free-text column here. That is why it exists.
- **A `none` row still gets words: the limit said plainly, what its quotes carry,
  and an answer slot where one helps.** F4 is the row the candidate is most afraid
  of and the one they will most need words for, and the words are the limit, not
  a way around it.
- **Bridge language is spoken aloud, so `reframing-audit.md` governs every clause
  of it** — six axes, and the incident-or-practice axis is the one that slips:
  F1 ran a schedule, and running a schedule does not mean choosing what went on
  it. That is why F1's bridge asks rather than says. This row used to read "I
  owned which integrations shipped in what order" beside evidence that said only
  that the candidate led them: the worked example added the practice the pack
  exists to stop adding, and packs copied it.

`Confidence` grades the candidate's evidence and `Provenance` grades what this
skill wrote about it: F3 is `low` because the evidence is thin, and `[inferred]`
because the bridge is this skill's derivation.

With a dossier, the evidence cell quotes `evidence_map.evidence[].quote_or_summary`
or `handoff_to_mock_interview.verified_candidate_evidence` exactly, with the
dossier row as its origin — never `candidate_claim`, which is the underwriter's
restatement and can be the widened form, and never `reasoning`. A confidence note
appended to a verified claim is not part of the quote: it goes to `Confidence` and
into the bridge as a stated limit. The map's `confidence` and `gap_type` are the
same vocabulary as this table's; its `reasoning` is the underwriter's analysis,
which a bridge may cite as a limit and never as something the candidate did.

## Question banks

One sub-table per persona, in this shape. Provenance sits before the guidance
because it is chosen first: the sentences a row may draw on are fixed before a
word of guidance is written, rather than found afterwards to fit guidance that
already exists.

| # | Question | Type | Provenance | Answer guidance | Rationale |
|---|---|---|---|---|---|
| A1 | "Walk me through how you ran intake when the dock was over capacity." | EXP | [grounded] "Ran the warehouse's weekly intake schedule for three years" | Story-mapped on F1: the schedule, and the three years. Pick one week you remember clearly; if none comes to mind, the rhythm of the three years is the answer. Answer slot: if you decided which deliveries waited, say how you chose; if someone else set the order, say so and describe how you ran the week inside it | F1 is the evidence for the roadmap requirement and the likeliest place to be probed; EXP because it tests what was actually the candidate's |
| A2 | "You've never owned a roadmap. Why should we trust you with ours?" | JD | [grounded] "Ran the warehouse's weekly intake schedule for three years" | The highest-ROI rehearsal in this pack, and the hold is only what the quote carries: "I haven't set a roadmap. For three years I ran the weekly intake schedule." Concede the specific thing — the longer horizon is what you would be learning — and hold through two follow-ups by returning to the schedule, never by adding to it | F1 and F4 meet at the role's mandate, so this objection arrives in some form; JD because it scores the stated requirement |
| A3 | "How would you cut our late-delivery rate in your first quarter?" | CASE | [generic] | Structure it: what you would measure first, the two likeliest causes, what you would try and how you would know it worked. The question needs no claim about your past, so the guidance makes none | The role's stated outcome as a live problem; `[generic]` because it is a pattern for the problem, not a fact about this company |
| A4 | "Tell me about the supplier metrics you tracked." | EXP | [inferred] "Collected feedback from partner pantries every quarter" | Say what you collected and how often, in those words. Answer slot: if any of it was counted or scored, say what and how; if it was not, say so plainly and say what you would measure first. Never describe a metric you did not track | F3's thin bridge, rehearsed so the honest answer is ready before the probe arrives |

Rules this shape enforces:

- **Provenance carries every sentence the guidance's claims about the candidate
  rest on, each quoted exactly as it appears in the fit snapshot.** A row reference
  ("see F1"), "as above", or a paraphrase is not a quote. A row whose guidance makes
  no claim about the candidate, like A3, carries its label alone.
- **Any clause in a pack cell that says what the candidate did, owned, decided or
  was responsible for has its content words inside one of the row's quotes, or it
  is an answer slot.** That holds whatever the label: `[inferred]` names a
  derivation about the role or the fit, and never stands in for the candidate's
  sentence.
- **Rationale refers to the candidate's history only by fit-snapshot row ID** —
  "F1 is the evidence for…" — and never restates or extends it.
- **An answer slot is not a question to the user.** It is addressed to the
  candidate's answer in the interview, it is an instruction rather than a question,
  and it asks for no reply in this conversation, so it does not count under
  `output-discipline.md` rule 1. Where an answer would make the pack better, that
  belongs in one upgrade-menu line naming the rows it would upgrade, never in the
  closing questions.

## Target accounting in Sources

One row per declared L1 target. It is a table because `interaction-grammar.md` §4
sends a skipped search here, and a search that ran wastefully leaves a pack
identical to one that skipped correctly — prose cannot tell them apart, and an
unfilled row can.

Research tier: L1 — searches 3 of 6, fetches 1 of 2

| L1 target | Status | What it moved, or would have |
|---|---|---|
| 1. `{company} values` | yes | Values cheat sheet, section 10 — four principles by name |
| 2. `{company} interview process {role family}` | yes | Loop structure; persona weights follow the named rounds |
| 3. `{company} strategy` / recent news | skipped | Could not have moved the CO bank: the strategy brief the user pasted already supplies current priorities and recent moves |
| 4. `{interviewer name} {company}` | n/a | No name was given, so there was no query to form; the interviewer read is absent and the upgrade menu says what a name would unlock |
| 5. representative `{role title}` JD | skipped | The JD the user supplied fixes the fit snapshot and the JD-tagged questions |

The label follows what happened, facts first, per `interaction-grammar.md` §4. A
target a search was sent for is `yes` if any call returned anything — no results
and nothing attributable included, said as "not established" — and
`unavailable` only if every call was refused; it is never `skipped` or `n/a`,
and if it moved nothing its `yes` row says so. A target no search was sent for is
`n/a` if the inputs cannot form its query — no name at all; a first name with a
title and the company is a name — `skipped` if the inputs already fix every
output it feeds, and otherwise `unavailable`: no search in this host, or research
declined, with what it would have moved, which the upgrade menu then offers. An
input fixes an output only when its content is in hand — a pasted values page
can, and "I've read their values page" cannot. In a host with no search, rows 1
and 2 above would read `unavailable`, each naming what it would have moved, and
rows 3 to 5 would not change, because the inputs decide them and the host does
not. A `yes` names research the Sources section lists; an accounting reporting a
search the pack shows no trace of is the failure this table exists to make
visible.

## Loop mode

Use when the user faces multiple scheduled rounds. Ask which rounds are on the calendar (this piggybacks on the Step 1 message — it does not add a second elicitation round). Structure: one shared fit snapshot + sources block, then a mini-pack per round with that round's persona weights, its own bank (8–12 questions), and its own reverse questions. The values cheat sheet lives with whichever round research says is values-focused. The upgrade menu is shared and sits at the end.

A known multi-session round with an *unknown* schedule — "the final round" at companies whose finals are several back-to-back sessions — is not loop mode. Run session mode with blended persona weights, and offer per-session mini-packs in the upgrade menu for when the user has the schedule. Do not assert how this company's final is structured unless research or the user established it; the upgrade-menu line can be conditional — "if your final is several sessions, send the schedule" — which needs no claim at all. Loop mode needs a schedule to key on; guessing one fabricates structure.

## Drill mode

Offer one drill after delivering any pack — a single line, no pressure. The pack is preparation; rehearsal is transfer, and the delivery flaws the coaching section predicts only surface out loud.

Running a drill:

1. The user picks a persona and optionally a question ID. Default when they don't choose: the highest-weight persona, on the question the pack named as highest-ROI.
2. Adopt the persona's register and ask the question. Follow up at least twice, and make the follow-ups react to what the candidate actually said — a scripted follow-up teaches nothing. Pressure-persona drills interrupt and time-box; prober drills ask for the denominator; peer drills push on the seam.
3. Stay in persona during the exchange. Break persona to give feedback only when the exchange is done.
4. Score against three things: the pack's own guidance for that question, the pack's named rehearsal priorities, and the type-specific bar from `question-rubric.md` (metric answers name their weakest assumption; pressure answers hold-then-concede; values answers land the hard truth). An answer slot is met when the candidate answered either branch from their own experience or said plainly the practice was not theirs; it is never scored against the practice it names.
5. Feedback is measured against that question's guidance cell — the beats it named, the weakest-assumption move, the hold-then-concede structure — because the cell is the rubric and was written first. Format: what landed / what to change / one line worth stealing verbatim. "What to change" may repeat an answer slot's question and never prescribes the practice it names; the line worth stealing comes from the candidate's own drill words or the cell's quotes, and it is proposed language, so the reframing audit governs it. There is no numeric score: a number would average away the one beat they missed, which is the entire finding. Then offer another round or a different persona — and, once, the dossier offer above: a drill is where `rehearsal_gaps` with `observed_in: drill` actually come from.
6. If the candidate shows real distress — interview anxiety is real and drills can spike it — drop the persona immediately and be a person about it. The drill serves the candidate, never the reverse.

## The dossier offer

One line at delivery, alongside the drill offer, and again after any drill: an offer to emit or update `tuesday-dossier.md` with this engagement's `pack_feedback` — the objections the fit snapshot exposed, the requirements where no credible story surfaced, and the stories told in prep that the CV doesn't carry. Full spec in `references/dossier-handoff.md`.

Keep the offer to what it buys the candidate: those leads are what the underwriter would want to verify next, and carrying them costs one file. Never gate the pack on it, never re-offer after a decline, and never let a lead recorded in feedback flow back into this pack's guidance as though it were confirmed evidence.

## Regeneration (Step 5 of SKILL.md)

When new inputs arrive, open the delivered pack, regenerate the affected sections, and lead the new version's title block with a one-line changelog ("relationship updated to peer → persona weights recomputed, bank G added, reverse questions retuned"). A fact the user states as input, outside a drill — an answer to an answer slot included — is new quoted material: it enters the fit snapshot's evidence column verbatim, and the rows that drew on it regenerate. Something said inside a drill is not: it stays a lead, recorded in `pack_feedback` if the candidate takes the dossier offer, and becomes material only when they say it outside the drill. Consistency check before redelivering: no section may contradict the new fact — a stale "hiring manager" framing surviving in the interviewer read while the persona table says "peer" is the failure mode to catch.
