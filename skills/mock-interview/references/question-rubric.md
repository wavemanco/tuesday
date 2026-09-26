# Question types, coverage rules, and writing rules

Personas describe how a question arrives; types describe what it's scoring. Tag every question with a type so the candidate can see the pack's coverage at a glance — and so you can see where coverage is thin before delivering.

## The five types

| Tag | Name | What it's really testing | Tends to dominate |
|---|---|---|---|
| **VAL** | Behavioral / values alignment | Whether past behavior demonstrates the company's *published* values, not generic virtue | Dedicated values rounds; cross-functional interviewers |
| **EXP** | Work-experience deep-dive | Whether the CV's claims survive scrutiny; attribution honesty; what the candidate actually did | Probers; anyone who read the CV closely |
| **JD** | Role / JD-driven | Stated responsibilities and qualifications — can the candidate do the listed job, including its gaps | Hiring managers; skeptics |
| **CO** | Company & strategy knowledge | Homework depth: strategy, competition, recent moves; whether the candidate can think at the company's altitude | Executives; strategy-adjacent roles |
| **CASE** | Hypothetical / live problem | Structure and reasoning on a problem from the actual role, delivered live | Hiring managers; case-led loops |

Dual-tagging is normal — list the primary type first and let the rationale explain the call ("JD content, CASE delivery"). A question with no clear type is usually a question that doesn't belong in the pack.

## Coverage rules

These exist because packs fail by omission, and the omissions are predictable:

- **Every hard requirement in the JD gets at least one JD-tagged question, and every other stated requirement gets one or a stated reason it does not.** The JD is the interviewer's scoring sheet; a requirement with no rehearsed answer is a free miss. The ones that go missing are never the headline requirements — they are the mid-list items, a named methodology or a specific tool, that appear once in the JD, get noted in the fit snapshot, and are never converted into a question. Check the finished banks against the JD's own list before delivering, not against your memory of it.
- **Every headline metric on the CV gets a defend-the-number EXP question.** Quantified claims are magnet targets for probers; the rehearsal is precise attribution — the sizing shape, the sensitivity, the weakest assumption named first, and exactly what was the candidate's own contribution.
- **Every published company value gets at least one VAL question with a mapped story** when research detects a values-style round. Slogan familiarity isn't the bar; a specific decision that demonstrates the value is.
- **At least one CO or CASE question grounded in the company's current strategy** when research at L1+ succeeded. These are the differentiator questions most candidates can't touch — and they go generic without research, which is the honest cost of declining the deep tier.
- **The single most predictable objection to this specific candidate gets the deepest rehearsal** — usually a Skeptic or Pressure item born from the fit snapshot's biggest gap. Name it in the pack as the highest-ROI prep, because it is: this question will be asked in some form, and a rehearsed non-defensive answer changes the interview.
- **Every pre-declared deliverable — a POV, presentation, or take-home the recruiter announced — gets its own build section.** Announced deliverables are graded deliverables: thesis options with a mandatory concession, a differentiation strategy, and the requested close (customer benefit, recommendation) if one was named. A pack that rehearses questions but not the assignment fails the loop.
- **When a provided research artifact is equally available to interviewers or rival candidates, differentiate from it — never recite it.** A public report's shortlist is the consensus answer any prepared candidate assembles; bring one consensus item to prove grounding, then one thesis-driven divergence, and where the role's real job includes saying no, the anti-pick. Reciting a shared source scores as homework; departing from it, with reasons, scores as judgment.
- **The pack carries a requirement-coverage line.** One short table mapping each stated JD requirement to the question IDs that cover it, with `— none, and why` where a requirement earns no question. Checking the banks against the JD before delivering is what the rule above asks for and what does not happen; a table that has to be filled in is what makes an uncovered requirement visible to the writer as well as the reader. It is also the section a candidate scans first to decide whether the pack is worth their evening.
- **Session totals: roughly 18–26 questions.** Depth follows persona weight (4–5 / 3 / 2). Below ~18 the pack under-covers; above ~26 the candidate can't rehearse it all and the pack stops being prioritized advice.

## Provenance labels

Every question row carries one label, in its own Provenance column — not appended to the rationale, where it reads as punctuation and goes missing under exactly the conditions that matter most.

**Where the guidance coaches a claim about the candidate's own experience, the Provenance cell carries the sentence it rests on, quoted verbatim, beside the label** — `[grounded] "ran the site's peak-season surge plan two years running"`. This is the fix that a rule could not deliver. Told in prose not to promote "ran" into "built" or "designed", packs did it anyway in every run of a fixture; asked to name the sentence the guidance stands on, the promotion has nowhere to hide, because the quote sits next to the claim and the gap between them is visible in one glance. A cell that cannot be filled is guidance resting on nothing, which is the finding, not an inconvenience. The three labels — `[grounded]`, `[inferred]`, `[generic]` — are defined in `references/evidence-conventions.md` §4, the suite's canonical vocabulary mirrored into this skill. Read the definitions there rather than from memory; the whole suite speaks one dialect, and a skill that quietly redefines a label breaks every consumer downstream of it.

Two connections that matter when writing a rationale cell:

- **Confidence and provenance are different axes.** Confidence (`evidence-conventions.md` §2) grades the *candidate's* evidence; provenance grades *what this pack wrote* on top of it. The mapping in `evidence-conventions.md` §5 says which is allowed from which — most usefully, a `low`-confidence claim may never be asserted as the candidate's story, only coached as a clarify-strategy note, and it is labeled `[inferred]` with the derivation named.
- **A `[generic]` label is an upgrade-menu argument, not an apology.** "These six `[generic]` rows become `[grounded]` if you add the JD text" tells the candidate exactly what their next five minutes of effort buys.

Why label at all: a candidate who rehearses a fabricated specific repeats it live and gets burned. The pack's honesty about its own epistemics is part of its quality.

## Writing the guidance cell

- **Speakable in 90–120 seconds.** Guidance is scaffolding for a spoken answer, not an essay. If it can't be delivered aloud in two minutes, cut it.
- **CV present → story-mapped.** Name the specific story from their material and the beat structure ("the two-org dashboard story: where interests diverged → the win-win constructed → the position held"). A dossier's `verified_candidate_evidence` is the strongest version of this: user-confirmed claims, mapped and labeled `[grounded]`, with any medium-confidence caveat coached into the answer rather than left for a prober to find.
- **CV absent → story-selection scaffold.** Give selection criteria instead: "pick a time you held a position under pressure from someone senior — it needs a named stake, a moment you didn't fold, and an intact relationship at the end."
- **Metric questions include the weakest-assumption move.** Coach the candidate to name their least defensible assumption before the interviewer does — it converts a gotcha into a credibility gain.
- **Pressure questions include the hold-then-concede structure.** Hold the position through two follow-ups, concede uncertainty explicitly and specifically, never fold on the core claim just to restore harmony.
- **The rationale covers both inclusion and categorization.** Why this question is likely for this candidate in this loop, and why it carries these tags. A reader should be able to disagree intelligently with either call.
- **Truthful attribution throughout.** Guidance rehearses precise honesty — "what was actually you" — never spin. Coaching a candidate to inflate is coaching them to fail a probe that exists specifically to catch inflation.
- **Run the reframing audit over every guidance cell.** `references/reframing-audit.md`, the suite's canonical audit mirrored verbatim into this skill: six axes, five disciplines, clause by clause against the candidate's own sentences. A guidance cell is not advice about language, it *is* language — the candidate will say these words out loud to someone who was in the room. A story-mapped beat that quietly promotes "contributed to" into "led" hands them a sentence that collapses on the first follow-up, and it is the interviewer, not the pack, who finds out. The audit's own worked examples are drawn from resume lines; nothing about them is weaker here, and the stakes are higher, because a written claim can be walked back and a spoken one is already in the room. Two shapes this fails in, both found in clean-room runs. **Guidance that tells the candidate what their work is *proof of*** — "the surge-plan work is proof you can build a playbook others execute without you" — is a claim about the work, not a rehearsal aid, and the candidate will repeat it as one. Coach them to describe what they did and let the interviewer draw the inference; an inference the candidate asserts on their own behalf is the one that gets tested. **And guidance that supplies specifics the candidate never gave** — a denominator, a timeline, a stakeholder's reaction — hands them a detail to say aloud that they cannot stand behind. Where the shape of a strong answer needs a specific, ask for it or mark the slot: "name the metric here if you have one" is scaffolding; naming it for them is invention.

## Reverse questions

Every pack includes at least five, each with a one-line "why it lands." When an interviewer profile exists, at least one ties to their own career path — it converts an interrogation into a peer conversation and signals the candidate researched *them*, not just the company. Include one reciprocity question when the interviewer is a peer ("what could a new person do in their first month that would genuinely help your team?"). Never let the pack's answer to "any questions for me?" be generic — rapport-style interviewers weight this slot heavily as a preparation signal.
