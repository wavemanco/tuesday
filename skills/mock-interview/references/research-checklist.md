# Research tiers, budgets, and fallbacks

Research is tiered because it trades the user's time (and, at the deep tier, their research quota) for pack quality, and that trade is theirs to make. What is not optional: company values, loop structure, and current strategy come from research or provided documents, never from model memory. These are precisely the facts that drift — values pages get rewritten, loops get restructured, strategies pivot quarterly — and a confidently stale claim is worse than a labeled generic one.

## L0 — provided documents only

No network. Use when offline, when the user declines research, or in API contexts without search. Everything not traceable to a provided document is labeled `[generic]`, and the upgrade menu says plainly what research would have added.

## L1 — default targeted research

Budget: **at most 6 searches and 2 page fetches.** Targets, in priority order:

1. **`{company} values`** (or "leadership principles", "operating principles") → fetch the official page. Value *names* and definitions must come from the source, not paraphrased memory — the candidate may be quizzed on them by name.
2. **`{company} interview process {role family}`** → loop structure: named rounds, whether a dedicated values/behavioral round exists, case formats. Prefer sources under ~18 months old; candidate-guide sites are acceptable here, labeled per the source-quality rules.
3. **`{company} strategy`** or recent-news sweep → one pass, sources under ~6 months: current priorities, recent big moves, the competitive frame. Feeds CO questions.
4. **`{interviewer name} {company}`** → only when a name was given. Public professional footprint: role, career pattern, talks, posts, self-descriptions. Nothing else — see SKILL.md guardrails.

Freshness rules: values are stable (official page wins, fetch once); loop structure is semi-stable (prefer recent, note the source's age if older); strategy is perishable (under 6 months or label it).

**When results aren't attributable:** some companies return nothing usable — stealth startups, tiny firms, name collisions with bigger entities (a search for a small "Northwind" drowns in unrelated results). Using a same-named company's values or process is worse than using nothing. Treat any target you can't attribute to *this specific company* as not-established: say so plainly in the pack, drop the values cheat sheet, fall back to the archetype table below, and put the missing facts in the upgrade menu — the user's recruiter can often supply them in one email.

## L2 — deep research (consent-gated)

Offer exactly once — in the Step 1 message when one is being sent anyway, otherwise as an upgrade-menu line in the delivered pack — with the cost stated ("a deeper research pass adds several minutes — want it?"). Never auto-run it; never re-offer after a decline. What it buys, and why it matters: historically, the strongest pack content — the strategy cases, the "why do you beat competitor X in 60 seconds" drills — comes from a company strategy brief. When the user can't supply one, this tier is its substitute; without it, CO and CASE questions go generic and are labeled as such.

The L2 menu:

- **Company strategy brief**: financials trajectory, stated strategic priorities, M&A pattern, competitive set and where it's losing ground. This feeds the differentiator bank.
- **Interviewer public footprint, deep**: conference talks, blog posts, podcast appearances — their recurring themes become likely questions and strong reverse-question material.
- **Role-family loop reports**: candidate guides and forum reports for this company + role family. Forum-sourced claims are labeled `[inferred]`, always.
- **Recent org context**: leadership changes, reorgs, layoffs or hiring waves that shape what this role is really for.

In claude.ai, the platform's deep-research feature is the natural way to produce the strategy brief; elsewhere, run an expanded search budget within the same targets.

## Loop detection → archetype fallback

From L1 target 2, try to name the company's actual rounds. When research can't establish the loop, fall back to an archetype **and say so in the pack** — the candidate should know their persona weights rest on a pattern, not on this company's documented process.

| Archetype | Typical loop | Persona tilt | Values-style round? |
|---|---|---|---|
| Big-tech structured | Recruiter → HM → skills/case → behavioral/values → committee | Values/Behavioral and Case up | Usually yes — treat as guaranteed somewhere in the loop |
| Consulting / case-led | Screens → multiple case rounds → partner fit | Case/Strategist dominant; Pressure via time-boxed math | Fit round, less codified |
| High-growth startup | HM → team panel → founder chat | Skeptic (scrappiness probes) and Conversational up; expect builder stories to be tested | Rare as a named round; values probed informally |
| Finance / quant-adjacent | Screens → technical depth → fit | Prober and Pressure dominant | Rare |
| Public sector / regulated enterprise | Structured competency-based panels | Values/Behavioral (competency framework) dominant; scripted questions | Competency framework plays the role |
| Generic | Screen → HM → panel | Flat weights, said plainly | Unknown — prep one story per common value theme |

## Source quality

Official company pages > the company's own careers/candidate-hub material > reputable interview-prep guides > forums. A claim found only in forums is `[inferred]` at best. When sources conflict — two different descriptions of the loop, say — note the conflict in the pack rather than averaging it away; the candidate can ask their recruiter, which is itself a good reverse question.
