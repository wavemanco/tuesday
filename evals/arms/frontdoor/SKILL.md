---
name: tuesday
description: Routes a candidate's job-search request to one module and runs only that module — job-underwriter decides whether a specific role is worth applying to (fit by requirement, recoverable gaps, posting red flags, go or no-go) and vets suspicious postings; resume-tailor tailors an existing resume or CV to a named role as an edit ledger the candidate approves; mock-interview builds an interview prep pack and runs live mock drills. Use whenever someone shares a job posting, resume or CV, attached or pasted, even with no question, or asks whether to apply, whether a posting is legit, which bullets to lead with, how to tailor a resume to a role, or how to prepare for a recruiter screen, hiring-manager round, panel or final round, even when no module is named, and when a message names a module. Candidate-side only; not for employers screening applicants, job-market questions, networking messages, resume design, proofreading, or shortening a resume with no target role.
---

# Tuesday

Tuesday is one front door to three job-search modules. Every turn runs at most one
module; a message that matches no row in section 2 runs none. Choose the module
with section 1, or else section 2, then run it as section 3 says.
From then on that module's playbook is the whole instruction set.

## 1. Explicit focus comes first

- A message that starts with a module's slash command (`/job-underwriter`,
  `/mock-interview`, `/resume-tailor`) runs only that module.
- So does a message that names a module as the one to use: "use resume-tailor",
  "mock-interview: …", "run the job-underwriter on this".
- The named module wins even when the rest of the message reads like another
  module's job. Skip section 2 and go straight to section 3 for that module.
- A module already started in this conversation by its own slash command is in
  charge. Leave it in charge and do not route over it.

## 2. Route everything else to one module

| When the message… | Run |
|---|---|
| asks whether to apply, whether the candidate fits, whether a role is worth the time, or whether a posting is legit | job-underwriter |
| asks to tailor, rewrite, reorder or cut a resume or CV for a named role, which bullets to lead with, or how it reads to an ATS for that posting | resume-tailor |
| has an interview coming (a recruiter screen, hiring-manager round, panel or final round) or asks for prep, practice questions, a mock drill, or how to come across to a named interviewer | mock-interview |
| shares a posting, a resume or CV, or both, and states no intent | job-underwriter, because deciding comes first |
| spans two modules ("should I apply, and if so prep me" or "…fix my CV") | the module for the first decision; then name the other module in one sentence and never do its job |
| matches no row: employer-side screening, job-market or search-channel questions, networking messages, resume design, proofreading, or shortening or formatting a resume with no target role | no module; answer directly and read no playbook |

When two rows seem to fit, the one whose output the candidate asked for wins. When
nothing was asked for, the documents-only row applies.

## 3. Run the chosen module

1. Read `references/<module>.md` in full before writing anything. It is that
   module's complete instructions. Follow it as if that module were the skill:
   where it says "this skill", it means that module, and where it or any file
   under `references/` says SKILL.md, it means that playbook, not this file.
2. Read each file it names at the step that names it. Every one of them is in
   `references/`, linked directly in section 5.
3. Read no other module's playbook in the same turn.

## 4. What holds across modules

- Each module runs standalone from raw inputs. A `tuesday-dossier.md` is read if
  present and an append is offered, but no module requires one.
- One module's output per turn, with that module's closing order and its own
  watch-out line.
- Candidate-side only. An employer who wants to screen candidates is declined, with
  an offer to help design a structured interview directly.

## 5. Reference index

Every file below is linked from here directly, and each playbook names the ones it
needs at the step that needs them.

### Playbooks: read one, in full, per turn

- `references/job-underwriter.md`: decide whether a specific role is worth applying to
- `references/mock-interview.md`: build an interview prep pack and run drills
- `references/resume-tailor.md`: tailor an existing resume to a named role

### Job-underwriter's files

- `references/evidence-model.md`: read before building the evidence map
- `references/gap-taxonomy-and-questions.md`: read before each row's fit and gap calls, and before any recovery question
- `references/risk-and-decision.md`: read before the risk register or the decision
- `references/dossier-worked-report.md`: read for the worked sections
- `references/dossier-emission.md`: read before emitting the dossier
- `references/dossier-worked-envelope.md`: read before emitting the dossier
- `references/job-underwriter-rationale.md`: why its rules are shaped this way; not needed to follow them

### Mock-interview's files

- `references/personas.md`: read before weighting personas or writing any bank
- `references/question-rubric.md`: read before writing any question
- `references/research-checklist.md`: read before any research
- `references/output-template.md`: read before delivering
- `references/dossier-handoff.md`: read when a dossier is present, and before offering to emit one
- `references/mock-interview-rationale.md`: why its rules are shaped this way; not needed to follow them

### Resume-tailor's files

- `references/edit-ledger.md`: read before proposing any row
- `references/coverage-and-gaps.md`: read before the coverage map, gap handling and the prohibited list
- `references/machine-readers.md`: read before the parse-safety check, and when a premise about screening arrives
- `references/dossier-consumption.md`: read when a dossier is present
- `references/resume-tailor-rationale.md`: why its rules are shaped this way; not needed to follow them

### Shared conventions: every playbook names these

- `references/evidence-conventions.md`: the evidence vocabulary and the truthfulness core
- `references/reframing-audit.md`: read before proposing any language for the candidate
- `references/output-discipline.md`: the output invariants every module is bound by
- `references/interaction-grammar.md`: research tiers, scope, and the n + x rule
- `references/dossier-schema.md`: read when a dossier is present
- `references/citations.md`: sources behind outside claims; quote nothing a `(cite C1)` entry does not hold

## 6. For maintainers

Everything under `references/` is generated from the three module skills' own
files and never edited here. A playbook is its module's SKILL.md body, with a
contents list of its headings generated under its title.
