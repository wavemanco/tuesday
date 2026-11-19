# job-underwriter

A Claude skill that underwrites a specific job opportunity: it evaluates the role against your real evidence, recovers overlooked-but-truthful experience your CV omits, classifies each gap (a presentation problem, a discovery problem, transferable-adjacent work, a genuine capability gap, or a failed hard gate), independently assesses the opportunity itself for risks and red flags, and delivers a go / conditional-go / hold / no-go decision with an evidence-backed application plan. Never a single fit score, never an invented claim — every conclusion traces to a source or is labeled as inference.

Part of [Tuesday](../../README.md), an applicant-side evidence system for job seekers. Fully standalone — Tuesday's shared artifacts (like the dossier) enhance this skill; they never gate it.

## Install

This module also comes inside Tuesday, which runs it when a request needs it. Install one or the other, not both: a module Claude can choose competes with Tuesday for every request. Tuesday's [Install section](../../README.md#install) covers every surface; to install this module on its own:

**claude.ai, on the web or in the desktop app**
1. Turn on code execution: Settings → Capabilities → *Code execution and file creation*. On a Team or Enterprise plan, an owner turns on code execution and skills under Organization settings.
2. Download [`job-underwriter.skill`](../../dist/job-underwriter.skill), upload it under Customize → Skills and switch it on. The desktop app uses the skills on your claude.ai account, so one upload covers both.

**Claude Code, in one project or in cloud sessions**
Unzip `dist/job-underwriter.skill` into the project's `.claude/skills/`. It runs as `/job-underwriter`, and Claude also picks it when a request matches its description.

**Claude Code, for yourself across your projects**
Install Tuesday's plugin or its personal install instead: both carry this module, hidden so it does not compete, and `/tuesday:job-underwriter` (the plugin) or `/job-underwriter` (the personal install) runs it directly.

Every test ran in Claude Code; this module on claude.ai is untested. A skill uploaded to claude.ai also reaches Claude Code, so keep one copy: where you use the plugin or a personal install, do not upload this module to claude.ai as well. If a menu has moved, see https://support.claude.com (search "skills").

## First prompt

You don't need to name the skill — "is this one worth applying for?" with a JD matches its description and auto-triggers. The ideal first prompt front-loads what the skill would otherwise ask:

```
Should I apply to this? [JD pasted or attached]
My CV is attached. I'm at the [evaluating / applying / interviewing] stage.
Non-negotiables: [comp floor, location/remote, authorization, schedule].
[Optional: portfolio link, prior resume, "do the deeper research pass."]
```

The bare minimum also works — a JD and a fit question — you'll get a first-pass underwriting immediately, plus at most three questions aimed at whatever would most change the decision.

## What to provide

| Tier | Inputs | If missing |
|---|---|---|
| Required | The job description | The skill can't underwrite without the role |
| Sharpens | Your CV (or background in prose), your non-negotiables | Fit side degrades to a self-assessment worksheet; hard-gate checks marked unknown |
| Optional | Portfolio, repos, prior resumes, reviews, work samples, a `tuesday-dossier.md` from an earlier session | Confidence stays where the evidence supports it — the upgrade menu says exactly what each artifact would unlock |

The skill asks at most three questions per turn, always alongside an updated analysis, and proceeds if you ignore them. It never re-asks, and "skip" is always an accepted answer.

**Privacy by design:** never upload government IDs — the skill won't repeat or use one. A professional license or registration counts as evidence, described by its kind, issuer, class, status and expiry, and its number never goes into a web search or page fetch. Candidate-side only; it declines employer-side screening use. Research on named people is public professional footprint only.

It's an AI assistant and can make mistakes. It points out warning signs in what you share, but it can't confirm who an employer, recruiter or sender really is. Please check before you act; the decision is always yours.

## The dossier

At the end, the skill offers (never forces) a `tuesday-dossier.md` — a human-readable underwriting report with a machine-readable envelope at the bottom. Carry it into a mock-interview session and the prep pack starts from your verified evidence, your likeliest objections, and the risks worth validating live, instead of from scratch.

## What's in this folder

```
job-underwriter/
├── SKILL.md                            # the skill itself — instructions Claude follows
├── README.md
├── LICENSE
├── references/
│   ├── evidence-model.md               # evidence vocabulary, map row shape, confirmation card
│   ├── gap-taxonomy-and-questions.md   # five gap types, recovery patterns, question selection
│   ├── risk-and-decision.md            # signal classes, red-flag patterns, decision semantics
│   ├── dossier-emission.md             # emission rules for tuesday-dossier.md
│   ├── dossier-worked-report.md        # worked dossier, the report: every assessment's sections
│   ├── dossier-worked-envelope.md      # worked dossier, the JSON envelope
│   ├── rationale.md                    # why the rules are shaped as they are; not required reading
│   ├── evidence-conventions.md         # mirror of conventions/ — source types, bands, labels
│   ├── reframing-audit.md              # mirror of conventions/ — six drift axes, five disciplines
│   ├── interaction-grammar.md          # mirror of conventions/ — standalone invariant, research tiers
│   ├── output-discipline.md            # mirror of conventions/ — seven rules on a response's shape
│   ├── dossier-schema.md               # mirror of conventions/ — the shared dossier's schema
│   └── citations.md                    # mirror of conventions/ — sources behind the outside claims, verbatim
└── evals/
    └── evals.json                      # 11 test fixtures with verifiable expectations
```

`evals/` holds development fixtures and is excluded from the installable `.skill` package. `README.md` rides along inside the package but is inert at runtime — Claude only loads files that `SKILL.md` points to.
