# Output template

## Session-mode pack skeleton

Deliver these sections in this order. The conditionality column is binding — a section whose condition fails is dropped entirely, not filled with padding, because an empty-calorie section teaches the candidate to skim.

| # | Section | Include when | Content spec |
|---|---|---|---|
| 1 | Title block | Always | Role, company, interviewer name + relationship if known; one line on what changed if this is a regeneration |
| 2 | How to use + type key | Always | Personas = how it's asked, types = what's scored; the five type tags with one-line meanings; "guidance is scaffolding, not a script" |
| 3 | Prep triage | Prep time known | A prioritized schedule sized to the stated time: the few things done well, in order, each tied to a section or question ID — closing with an explicit "everything else is insurance" line. Never pad it to look busy |
| 4 | Fit snapshot | JD or CV present (either) | Table: JD requirement × candidate's strongest evidence × gap-and-bridge language. CV absent → self-assessment worksheet variant: requirement × "your evidence here" prompts × what strong evidence looks like. JD absent → built from the researched representative JD, labeled |
| 5 | Graded deliverables | Recruiter/HR pre-declared a deliverable (POV, presentation, take-home) | One build section per declared deliverable: the grounded facts to build on, 2–3 defensible theses each with a mandatory concession, differentiation strategy against the consensus answer (with the anti-pick where the role warrants saying no), and the requested close (e.g., customer benefit) if HR named one. In loop mode these are shared sections, like the values cheat sheet |
| 6 | Grounding brief | L2 research ran, or an equivalent strategy brief was provided | Learn-the-vocabulary company section: current segmentation language, headline numbers, live leadership and strategy context, recent moves. The candidate should sound current, not archival; flag stale framings in provided documents without coaching the candidate to correct the interviewer |
| 7 | Reading the interviewer | Real interviewer info exists | Career pattern, self-described style, 2–4 practical implications, the mirror opportunities (shared jumps, shared vocabulary). Public footprint only |
| 8 | Persona table | Always | Persona × how it shows up × likelihood **with the reasoning shown** × counter-strategy |
| 9 | Question banks | Always | One sub-table per persona, ordered by weight. Columns: # (A1, B2…) × Question × Type × Answer guidance × Rationale (inclusion + categorization) × Provenance. Provenance is its own column, never a tag trailing the rationale — as a suffix it is punctuation the writer drops, as a column it is a cell that renders empty |
| 10 | Values / principles cheat sheet | Values-style round detected | Table: value (official name) × working meaning (paraphrased) × the candidate's mapped story (or selection scaffold if no CV) |
| 11 | Reverse questions | Always | ≥5, each with "why it lands"; ≥1 tied to the interviewer's path when a profile exists; 1 reciprocity question when peer |
| 12 | Delivery coaching | Assessment provided | Table: assessed trait (the report's own framing) × where it helps in this loop × watch-out → counter-move, keyed to question IDs. Restate the ground rules: never mention the assessment in the interview; tuning, not content |
| 13 | Sources | Always | Provided documents; web sources with URLs; the research tier used. When a dossier was consumed, say so and name which sections it supplied |
| 14 | Upgrade menu | Always | Each missing input → what adding it unlocks, concretely ("interviewer's profile → personalized persona weights + a tailored reverse question"; "JD text → six `[inferred]` rows become `[grounded]`"). With no dossier present, one line on what one would add — never phrased as a prerequisite |

Formatting: markdown tables; no pipe characters inside cells; question IDs letter-by-persona (A1, A2, B1…) so the drill and the coaching section can reference them; cells crisp — guidance speakable in 90–120 seconds, rationales 2–3 sentences.

File conventions: save as `{company}_{role-slug}_interview_pack.md` to the outputs directory and present it. Offer a Word (.docx) conversion in one line rather than producing one by default — most candidates iterate in markdown and convert once at the end.

## Loop mode

Use when the user faces multiple scheduled rounds. Ask which rounds are on the calendar (this piggybacks on the Step 1 message — it does not add a second elicitation round). Structure: one shared fit snapshot + sources block, then a mini-pack per round with that round's persona weights, its own bank (8–12 questions), and its own reverse questions. The values cheat sheet lives with whichever round research says is values-focused. The upgrade menu is shared and sits at the end.

A known multi-session round with an *unknown* schedule — "the final round" at companies whose finals are several back-to-back sessions — is not loop mode. Run session mode with blended persona weights, say in the title block that the final is typically multiple sessions, and offer per-session mini-packs in the upgrade menu once the user has the schedule. Loop mode needs a schedule to key on; guessing one fabricates structure.

## Drill mode

Offer one drill after delivering any pack — a single line, no pressure. The pack is preparation; rehearsal is transfer, and the delivery flaws the coaching section predicts only surface out loud.

Running a drill:

1. The user picks a persona and optionally a question ID. Default when they don't choose: the highest-weight persona, on the question the pack named as highest-ROI.
2. Adopt the persona's register and ask the question. Follow up at least twice, and make the follow-ups react to what the candidate actually said — a scripted follow-up teaches nothing. Pressure-persona drills interrupt and time-box; prober drills ask for the denominator; peer drills push on the seam.
3. Stay in persona during the exchange. Break persona to give feedback only when the exchange is done.
4. Score against three things: the pack's own guidance for that question, the pack's named rehearsal priorities, and the type-specific bar from `question-rubric.md` (metric answers name their weakest assumption; pressure answers hold-then-concede; values answers land the hard truth).
5. Feedback format: what landed / what to change / one line worth stealing verbatim. Then offer another round or a different persona — and, once, the dossier offer above: a drill is where `rehearsal_gaps` with `observed_in: drill` actually come from.
6. If the candidate shows real distress — interview anxiety is real and drills can spike it — drop the persona immediately and be a person about it. The drill serves the candidate, never the reverse.

## The dossier offer

One line at delivery, alongside the drill offer, and again after any drill: an offer to emit or update `tuesday-dossier.md` with this engagement's `pack_feedback` — the objections the fit snapshot exposed, the requirements where no credible story surfaced, and the stories told in prep that the CV doesn't carry. Full spec in `references/dossier-handoff.md`.

Keep the offer to what it buys the candidate: those leads are what the underwriter would want to verify next, and carrying them costs one file. Never gate the pack on it, never re-offer after a decline, and never let a lead recorded in feedback flow back into this pack's guidance as though it were confirmed evidence.

## Regeneration (Step 5 of SKILL.md)

When new inputs arrive, open the delivered pack, regenerate the affected sections, and lead the new version's title block with a one-line changelog ("relationship updated to peer → persona weights recomputed, bank G added, reverse questions retuned"). Consistency check before redelivering: no section may contradict the new fact — a stale "hiring manager" framing surviving in the interviewer read while the persona table says "peer" is the failure mode to catch.
