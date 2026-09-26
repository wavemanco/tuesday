# resume-tailor

A Claude skill that tailors an existing resume to a specific job under one constraint that changes the product: **it cannot add a claim.** It reorganizes, re-emphasizes, retitles, compresses, cuts, and reframes within what your own words support — and where the posting wants something your evidence does not hold, it says so and offers to go looking, rather than writing around the gap. Every proposed change arrives as a row in an edit ledger showing the current line, the proposed line, what operation was performed, and the sentence of yours it traces to. Nothing is applied until you approve it.

Part of [Tuesday](../../README.md), an applicant-side evidence system for job seekers. Fully standalone — Tuesday's shared artifacts (like the dossier) enhance this skill; they never gate it.

## Install

Skills require code execution to be enabled. Steps below are current as of mid-2026; if a menu has moved, see https://support.claude.com (search "skills").

**Web — claude.ai**
1. Free/Pro/Max: Settings → Capabilities → enable "Code execution and file creation". Team/Enterprise: an owner enables Code execution and Skills under Organization settings → Skills.
2. Customize → Skills → upload the zip (the zip root must be the `resume-tailor/` folder itself, not loose files), then toggle it on.
3. Uploaded skills are private to your account unless an org owner provisions them organization-wide.

**Desktop app**
Skills are account-level — anything enabled on claude.ai is already available; manage from Customize in the sidebar. Shortcut: if someone shares the packaged `.skill` file in a chat, the file card shows a "Save skill" button.

**Claude Code (CLI)**
Filesystem only — copy the `resume-tailor/` folder to:
- `~/.claude/skills/resume-tailor/` — personal, available in every project, or
- `.claude/skills/resume-tailor/` — project-scoped, committed to the repo so teammates get it on clone.

New sessions pick it up automatically; it is also invokable directly as `/resume-tailor`.

## First prompt

You don't need to name the skill — "tailor my CV for this role" with a JD and a resume matches its description and auto-triggers.

```
Tailor my resume for this role. [JD pasted or attached]
[Resume pasted or attached — a file is better than pasted text, see below.]
[Optional: portfolio links, a tuesday-dossier.md, prior resume versions.]
```

Two things are required and everything else is a bonus: a target JD and a resume. Without the first there is nothing to tailor toward; without the second there is nothing to tailor.

## What you get back

- **The edit ledger** — one row per proposed change: current line, proposed line, the operation performed, the sentence of yours it traces to, a provenance label, and a status. Everything starts at *pending your approval*.
- **A coverage map** — every material requirement in the posting marked `already_evidenced`, `surfaced_by_edit`, or `not_evidenced`. The third value is the one most tools omit.
- **Gap handling** — for anything not evidenced, either a recall prompt (people forget what they have done until an example shaped like their own life jogs it) or a plainly named absence with what closing it would take.
- **A prohibited-claims list** — what this skill refused to write, and why. It is there so the refusal is visible; otherwise you cannot tell a skill that found nothing to inflate from one that inflated nothing.
- **A parse-safety check** — whether your document's content survives being turned into text. Multi-column layouts, tables, icons and header contact details break this silently.
- **The tailored resume** — only after you approve rows, and only from the rows you approved.

## What it will not do

- **Add a claim your material does not support**, in any form — including a "technically true" phrasing that gestures at a requirement without meeting it.
- **Write hidden text for automated screeners.** White-on-white text, 1pt keyword blocks, metadata instructions. The reasons are in `references/machine-readers.md`; the short version is that this skill's whole product is that you can defend every line, and a line hidden from you is the opposite of that.
- **Stuff keywords.** Truthful keywords go where the evidence already supports them, so you are findable. Invented ones are prohibited claims with a technical excuse.
- **Redesign your document.** It reports what breaks extraction. Typography and layout aesthetics are not its business.
- **Decide whether to apply** — that is [job-underwriter](../job-underwriter/) — **or prepare you for the interview** — that is [mock-interview](../mock-interview/).

## Package layout

```
resume-tailor/
├── SKILL.md                            # workflow, guardrails, input contract
├── README.md
├── LICENSE
├── references/
│   ├── edit-ledger.md                  # the row shape, the operations, a worked ledger
│   ├── coverage-and-gaps.md            # coverage map, recall prompts, prohibited claims
│   ├── machine-readers.md              # parse safety, keywords, the hidden-text refusal
│   ├── dossier-consumption.md          # reading tuesday-dossier.md as a consumer
│   ├── evidence-conventions.md         # mirror of conventions/ — source types, bands, labels
│   ├── reframing-audit.md              # mirror of conventions/ — six drift axes, five disciplines
│   ├── interaction-grammar.md          # mirror of conventions/ — standalone invariant, research tiers
│   ├── output-discipline.md            # mirror of conventions/ — six rules on a response's shape
│   ├── dossier-schema.md               # mirror of conventions/ — the shared dossier's schema
│   └── citations.md                    # mirror of conventions/ — sources behind the outside claims, verbatim
└── evals/                              # excluded from the package
    └── evals.json                      # five fixtures with verifiable expectations
```

The files marked as mirrors above are verbatim copies of the suite's canonical files, carried so the skill installs standalone. Canonical wins on conflict; a mirror that drifts is a defect and CI fails the build on it.
