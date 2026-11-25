# mock-interview

A Claude skill that turns interview prep into a rehearsable pack: persona-categorized question banks with per-question answer guidance and rationale, a fit-gap map against the JD, company-values alignment, reverse questions, and an optional live drill where Claude plays the interviewer. Everything in the pack is grounded in your documents or in research — or explicitly labeled `[inferred]` / `[generic]` so you never rehearse a fabricated specific.

Part of [Tuesday](../../README.md), an applicant-side evidence system for job seekers. Fully standalone — Tuesday's shared artifacts enhance this skill; they never gate it.

For a visual walkthrough of first use, open **`docs/workflow.html`** in any browser — click the boxes. Install with the steps below: the walkthrough's own install boxes predate them.

## Install

This module also comes inside Tuesday, which runs it when a request needs it. Install one or the other, not both: a module Claude can choose competes with Tuesday for every request. Tuesday's [Install section](../../README.md#install) covers every surface; to install this module on its own:

**claude.ai, on the web or in the desktop app**
1. Turn on code execution: Settings → Capabilities → *Code execution and file creation*. On a Team or Enterprise plan, an owner turns on code execution and skills under Organization settings.
2. Download [`mock-interview.skill`](../../dist/mock-interview.skill), upload it under Customize → Skills and switch it on. The desktop app uses the skills on your claude.ai account, so one upload covers both.

**Claude Code, in one project or in cloud sessions**
Unzip `dist/mock-interview.skill` into the project's `.claude/skills/`. It runs as `/mock-interview`, and Claude also picks it when a request matches its description.

**Claude Code, for yourself across your projects**
Install Tuesday's plugin or its personal install instead: both carry this module, hidden so it does not compete, and `/tuesday:mock-interview` (the plugin) or `/mock-interview` (the personal install) runs it directly.

Every test ran in Claude Code; this module on claude.ai is untested. A skill uploaded to claude.ai also reaches Claude Code, so keep one copy: where you use the plugin or a personal install, do not upload this module to claude.ai as well. If a menu has moved, see https://support.claude.com (search "skills").

## First prompt

You don't need to name the skill — "prep me for my interview" matches its description and auto-triggers. The ideal first prompt front-loads what the skill would otherwise ask:

```
Prep me for my interview at [company] for the [role title] role.
It's a [60-min conversation / final panel / recruiter screen]
with [name], who'd be my [manager / peer / skip-level / unknown].
JD and CV attached. [Optional: "Do the deeper research pass."]
```

The bare minimum also works — "Help me prep, final round at Canva for a Senior Program Manager role" — you'll just get one short setup question first and a pack with more `[inferred]` labels plus an upgrade menu telling you exactly what to add.

## What to provide

| Tier | Inputs | If missing |
|---|---|---|
| Required | Company + role title | The skill can't run |
| Sharpens | JD text, your CV or background | Representative-JD research; a self-assessment fit worksheet when you give no background at all |
| Optional | Interviewer profile, round schedule, a research note, a working-style assessment | Sections drop or genericize — never fabricate |
| Optional, high-leverage | A `tuesday-dossier.md` from job-underwriter | The pack is built from your raw inputs as always; without it the likeliest objection is inferred rather than evidence-derived |

The skill asks at most one clarifying message (three questions max, only for what's missing) and proceeds even if you ignore it. Late additions are cheap: paste the interviewer's profile mid-conversation and only the affected sections regenerate.

**Privacy by design:** never upload government IDs — the skill won't repeat or use one. A professional license or registration counts as evidence, described by its kind, issuer, class, status and expiry, and its number never goes into a web search or page fetch. Personality/working-style assessments are accepted only if you offer them, feed only the delivery-coaching section, and the skill will never suggest mentioning one in an interview. Candidate-side prep only; it declines employer-side screening use.

It's an AI assistant and can make mistakes. It points out warning signs in what you share, but it can't confirm who an employer, recruiter or sender really is. Please check before you act; the decision is always yours.

## Carrying a dossier

If you underwrote the role first with [job-underwriter](../job-underwriter/), hand this skill the `tuesday-dossier.md` it offered you. The pack then builds on evidence you already confirmed: your verified claims become story-mapped guidance instead of "pick a time when…" scaffolds, the objection the underwriting flagged becomes the deepest rehearsal in the pack instead of a guess, the risks it left unresolved become reverse questions, and any claim it marked prohibited is fenced off from every line of guidance.

At the end, the skill offers to write back — a `pack_feedback` section carrying the objections prep exposed, the requirements where no story surfaced, and the stories you told in rehearsal that your CV never mentions. Those go back to the underwriter as leads to verify, never as established facts.

None of this is required. Skills in Tuesday stand alone; the dossier just means you stop re-explaining yourself.

## Modes

- **Session** (default) — one pack for one conversation.
- **Loop** — "My loop is three interviews over two days" gets a shared fit map plus per-round mini-packs.
- **Drill** — after any pack, ask for a rehearsal: Claude adopts a persona, asks with reactive follow-ups, then breaks character and scores you against the pack's own rubric.

## What's in this folder

```
mock-interview/
├── SKILL.md                      # the skill itself — instructions Claude follows
├── README.md
├── LICENSE
├── references/
│   ├── personas.md               # 7 interviewer personas, relationship priors, signal rules
│   ├── question-rubric.md        # 5 question types, coverage rules, guidance-writing rules
│   ├── research-checklist.md     # L0/L1/L2 research tiers, budgets, archetype fallbacks
│   ├── output-template.md        # pack skeleton, loop mode, drill mode
│   ├── dossier-handoff.md        # reading handoff_to_mock_interview, writing pack_feedback
│   ├── rationale.md              # why the rules are shaped as they are; not required reading
│   ├── evidence-conventions.md   # mirror of conventions/ — source types, bands, labels
│   ├── reframing-audit.md        # mirror of conventions/ — six drift axes, five disciplines
│   ├── interaction-grammar.md    # mirror of conventions/ — standalone invariant, research tiers
│   ├── output-discipline.md      # mirror of conventions/ — seven rules on a response's shape
│   ├── dossier-schema.md         # mirror of conventions/ — the shared dossier's schema
│   └── citations.md              # mirror of conventions/ — sources behind the outside claims, verbatim
├── evals/
│   └── evals.json                # 13 test fixtures with verifiable expectations
└── docs/
    └── workflow.html             # interactive install + first-use walkthrough (this repo only)
```

`evals/` holds development fixtures and is excluded from the installable `.skill` package. `README.md` and `docs/` do ride along inside the package, but they're inert at runtime — Claude only loads files that `SKILL.md` points to.
