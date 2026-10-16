# Research tiers, budgets, and fallbacks

Research is tiered because it trades the user's time (and, at the deep tier, their research quota) for pack quality, and that trade is theirs to make. What is not optional: company values, loop structure, and current strategy come from research or provided documents, never from model memory. These are precisely the facts that drift — values pages get rewritten, loops get restructured, strategies pivot quarterly — and a confidently stale claim is worse than a labeled generic one.

## L0 — provided documents only

L0 sends no search and no fetch of the skill's choosing. A link the user gave you to read is a provided document, read when the host can fetch it and named on the tally line; a host that cannot fetch says so and uses only what was pasted. A URL the user names only as where pasted text came from is not a link to read (`interaction-grammar.md` §4). Use L0 when offline, when the user declines research, or in a host without search. Everything not traceable to a provided document is labeled `[generic]`, and the upgrade menu says plainly what research would have added.

## L1 — default targeted research

Budget: **at most 6 searches and 2 page fetches.** Targets, in priority order:

1. **`{company} values`** (or "leadership principles", "operating principles") → fetch the official page. Value *names* and definitions must come from the source, not paraphrased memory — the candidate may be quizzed on them by name.
2. **`{company} interview process {role family}`** → loop structure: named rounds, whether a dedicated values/behavioral round exists, case formats. Prefer sources under ~18 months old; candidate-guide sites are acceptable here, labeled per the source-quality rules.
3. **`{company} strategy`** or recent-news sweep → one pass, sources under ~6 months: current priorities, recent big moves, the competitive frame. Feeds CO questions.
4. **`{interviewer name} {company}`** → only when a name was given. Public professional footprint: role, career pattern, talks, posts, self-descriptions. Nothing else — see SKILL.md guardrails.
5. **representative `{role title}` JD** → only when no JD was supplied: one search for a current posting of this title at a comparable company, so the fit snapshot and JD-tagged questions rest on something; label what it supplies `[inferred]`. With a JD supplied, this target is `skipped`.

Searches outside these targets do not run at L1. A question none of them covers is either an L2 item or an upgrade-menu line.

Freshness rules: values are stable (official page wins, fetch once); loop structure is semi-stable (prefer recent, note the source's age if older); strategy is perishable (under 6 months or label it).

**When results aren't attributable:** some companies return nothing usable — stealth startups, tiny firms, name collisions with bigger entities (a search for a small "Fenwick" drowns in unrelated results). Using a same-named company's values or process is worse than using nothing. Treat any target you can't attribute to *this specific company* as not-established: say so plainly in the pack, drop the values cheat sheet, fall back to the archetype table below, and put the missing facts in the upgrade menu — the user's recruiter can often supply them in one email.

## L2 — deep research (consent-gated)

Offer exactly once — in the Step 1 message when one is being sent anyway, otherwise as an upgrade-menu line in the delivered pack — with the cost stated as its caps and its time ("a deeper research pass — up to 6 more searches and 2 more fetches, several more minutes — want it?"). Never auto-run it; never re-offer after a decline. What it buys, and why it matters: historically, the strongest pack content — the strategy cases, the "why do you beat competitor X in 60 seconds" drills — comes from a company strategy brief. When the user can't supply one, this tier is its substitute; without it, CO and CASE questions go generic and are labeled as such.

The L2 targets, numbered after L1's, with a budget of **at most 6 further searches and 2 further fetches**:

6. **Company strategy brief**: financials trajectory, stated strategic priorities, M&A pattern, competitive set and where it's losing ground. This feeds the differentiator bank.
7. **Interviewer public footprint, deep**: conference talks, blog posts, podcast appearances — their recurring themes become likely questions and strong reverse-question material.
8. **Role-family loop reports**: candidate guides and forum reports for this company + role family. Forum-sourced claims are labeled `[inferred]`, always.
9. **Recent org context**: leadership changes, reorgs, layoffs or hiring waves that shape what this role is really for.

In claude.ai, the platform's deep-research feature is the natural way to produce the strategy brief; elsewhere, run these four targets within the L2 budget, and account for them in the same table, numbered 6 to 9.

## Loop detection → archetype fallback

From L1 target 2, try to name the company's actual rounds. **A loop source** is a source the pack read and names in Sources: the company's interviewing or careers page, read or pasted; a candidate guide labelled as Source quality below says; or the user's, the recruiter's or the interviewer's own words. This is the one definition of it; the template points here. When no loop source establishes the loop, fall back to an archetype **and say so in the pack** — the candidate should know their persona weights rest on a pattern, not on this company's documented process.

| Archetype | Typical loop | Persona tilt | Values-style round, as a fallback |
|---|---|---|---|
| Big-tech structured | Recruiter → HM → skills/case → behavioral/values → committee | Values/Behavioral and Case up | `yes` — usually somewhere in the loop |
| Consulting / case-led | Screens → multiple case rounds → partner fit | Case/Strategist dominant; Pressure via time-boxed math | `no` — a fit round, less codified |
| High-growth startup | HM → team panel → founder chat | Skeptic (scrappiness probes) and Conversational up; expect builder stories to be tested | `no` — values probed informally, not as a named round |
| Finance / quant-adjacent | Screens → technical depth → fit | Prober and Pressure dominant | `no` — rare |
| Public sector / regulated enterprise | Structured competency-based panels | Values/Behavioral (competency framework) dominant; scripted questions | `yes` — the competency framework plays the role |
| Generic | Screen → HM → panel | Flat weights, said plainly | `no` — unknown, so not assumed |

**A values-style round is detected** in exactly two cases; this is the one definition, and the template's section 10, `SKILL.md` Step 3 and the rubric's VAL coverage rule point here.

- **A loop source documents one.** A loop source names a round, or a part of one, that assesses values, principles, behaviours or a competency framework.
- **The fallback archetype has one.** No loop source establishes the loop, and the archetype the pack names as its fallback reads `yes` in the last column above.

In every other case no values-style round is detected: a values page read while no loop source establishes the loop does not detect one, and neither does a loop source that names no such round. Published values the pack read may still theme VAL questions, as the raising sources `references/question-rubric.md` names.

## Source quality

Official company pages > the company's own careers/candidate-hub material > reputable interview-prep guides > forums. A claim found only in forums is `[inferred]` at best. When sources conflict — two different descriptions of the loop, say — note the conflict in the pack rather than averaging it away; the candidate can ask their recruiter, which is itself a good reverse question.
