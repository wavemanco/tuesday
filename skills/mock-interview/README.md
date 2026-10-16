# mock-interview

A Claude skill that turns interview prep into a rehearsable pack: persona-categorized question banks with per-question answer guidance and rationale, a fit-gap map against the JD, company-values alignment, reverse questions, and an optional live drill where Claude plays the interviewer. Everything in the pack is grounded in your documents or in research — or explicitly labeled `[inferred]` / `[generic]` so you never rehearse a fabricated specific.

Part of [Tuesday](../../README.md), an applicant-side evidence system for job seekers. Fully standalone — Tuesday's shared artifacts enhance this skill; they never gate it.

For a visual walkthrough of install and first use, open **`docs/workflow.html`** in any browser — click the boxes.

## Install

Skills require code execution to be enabled. Steps below are current as of mid-2026; if a menu has moved, see https://support.claude.com (search "skills").

**Web — claude.ai**
1. Free/Pro/Max: Settings → Capabilities → enable "Code execution and file creation". Team/Enterprise: an owner enables Code execution and Skills under Organization settings → Skills.
2. Customize → Skills → upload the zip (the zip root must be the `mock-interview/` folder itself, not loose files), then toggle it on.
3. Uploaded skills are private to your account unless an org owner provisions them organization-wide.

**Desktop app**
Skills are account-level — anything enabled on claude.ai is already available; manage from Customize in the sidebar. Shortcut: if someone shares the packaged `.skill` file in a chat, the file card shows a "Save skill" button. Cowork sessions sync the skills enabled on your account at session start.

**Claude Code (CLI)**
Filesystem only — copy the `mock-interview/` folder to:
- `~/.claude/skills/mock-interview/` — personal, available in every project, or
- `.claude/skills/mock-interview/` — project-scoped, committed to the repo so teammates get it on clone.

New sessions pick it up automatically; it is also invokable directly as `/mock-interview`.

## First prompt

You don't need to name the skill — "prep me for my interview" matches its description and auto-triggers. The ideal first prompt front-loads what the skill would otherwise ask:

```
Prep me for my interview at [company] for the [role title] role.
It's a [60-min conversation / final panel / recruiter screen]
with [name], who'd be my [manager / peer / skip-level / unknown].
JD and CV attached. [Optional: "Do the deeper research pass."]
```

The bare minimum also works — "Help me prep, final round at Stripe for Product Operations Manager" — you'll just get one short setup question first and a pack with more `[inferred]` labels plus an upgrade menu telling you exactly what to add.

## What to provide

| Tier | Inputs | If missing |
|---|---|---|
| Required | Company + role title | The skill can't run |
| Sharpens | JD text, your CV | Representative-JD research; self-assessment fit worksheet |
| Optional | Interviewer profile, round schedule, a research note, a working-style assessment | Sections drop or genericize — never fabricate |
| Optional, high-leverage | A `tuesday-dossier.md` from job-underwriter | The pack is built from your raw inputs as always; without it the likeliest objection is inferred rather than evidence-derived |

The skill asks at most one clarifying message (three questions max, only for what's missing) and proceeds even if you ignore it. Late additions are cheap: paste the interviewer's profile mid-conversation and only the affected sections regenerate.

**Privacy by design:** never upload government IDs — the skill refuses them. Personality/working-style assessments are accepted only if you offer them, feed only the delivery-coaching section, and the skill will never suggest mentioning one in an interview. Candidate-side prep only; it declines employer-side screening use.

## Carrying a dossier

If you underwrote the role first with [job-underwriter](../job-underwriter/), hand this skill the `tuesday-dossier.md` it offered you. The pack then builds on evidence you already confirmed: your verified claims become story-mapped guidance instead of "pick a time when…" scaffolds, the objection the underwriting flagged becomes the deepest rehearsal in the pack instead of a guess, the risks it left unresolved become reverse questions, and any claim it marked prohibited is fenced off from every line of guidance.

At the end, the skill offers to write back — a `pack_feedback` section carrying the objections prep exposed, the requirements where no story surfaced, and the stories you told in rehearsal that your CV never mentions. Those go back to the underwriter as leads to verify, never as established facts.

None of this is required. Skills in Tuesday stand alone; the dossier just means you stop re-explaining yourself.

## Modes

- **Session** (default) — one pack for one conversation.
- **Loop** — "I have three rounds scheduled" gets a shared fit map plus per-round mini-packs.
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
│   ├── evidence-conventions.md   # mirror of conventions/ — source types, bands, labels
│   ├── reframing-audit.md        # mirror of conventions/ — six drift axes, five disciplines
│   ├── interaction-grammar.md    # mirror of conventions/ — standalone invariant, research tiers
│   ├── output-discipline.md      # mirror of conventions/ — six rules on a response's shape
│   ├── dossier-schema.md         # mirror of conventions/ — the shared dossier's schema
│   └── citations.md              # mirror of conventions/ — sources behind the outside claims, verbatim
├── evals/
│   └── evals.json                # 8 test fixtures with verifiable expectations
└── docs/
    └── workflow.html             # interactive install + first-use walkthrough (this repo only)
```

`evals/` holds development fixtures and is excluded from the installable `.skill` package. `README.md` and `docs/` do ride along inside the package, but they're inert at runtime — Claude only loads files that `SKILL.md` points to.
