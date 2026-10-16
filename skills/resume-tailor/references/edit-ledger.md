# The edit ledger

The ledger is this skill's spine and its entire deliverable until the candidate
approves something. It is not a rewritten resume with a diff attached — it is a
list of proposals, each one small enough to accept or reject on its own.

The reason is not politeness. A rewritten document asks the candidate to
reverse-engineer what changed and to trust that nothing was slipped in; a ledger
puts every change in front of them with the sentence of their own it came from.
The candidate cannot defend in an interview what they never noticed had been
written for them.

## The row

| # | Section | Current line | Proposed line | Operation | Traces to | Provenance | Status |
|---|---|---|---|---|---|---|---|

Every column earns its place, and three of them exist because the suite has
watched what happens without them.

- **Operation** names what was done, from a fixed set — `reorder`, `surface`, `cut`, `retitle`, `compress`, `split`, `merge`, `reframe`. Never "improved", "strengthened", or "optimized": those describe an intention, and the candidate cannot check an intention. If no operation in the set describes the change, the change is probably adding something, which is the one thing this skill does not do.
- **Traces to** holds a quoted sentence from the candidate's own material — the resume, an attachment, an answered recall prompt, or a dossier `evidence_map` row. Quoted, not summarized, and not *referred to*: `"Ran the small-grants round for three years"` is a trace; `same sentence`, `sentences 1, 2 and 5 combined`, `see above` and `resume, Experience` are not. A cell that points at a quotation instead of containing one cannot be checked without leaving the table, which is the entire reason the column exists — and it is the shape this rule fails in, because shorthand feels like tidiness while writing. Where a row genuinely draws on more than one sentence, quote each of them in the cell. **And the quotation is verbatim, character for character.** Silently tidying it is the failure that replaces the last one: a trace reading "Coordinated the foundation's assessors" against a resume that said "our assessors" looks quoted, reads as verified, and is not checkable — and an altered quote is worse than an obvious paraphrase, because a paraphrase announces itself. The edit here is harmless and the mechanism is not: the same reflex that smooths "our" into "the foundation's" smooths "helped build" into "built". If the candidate's sentence is awkward, quote the awkward sentence. **A row whose trace cell would be empty is not proposed.** That is the whole rule; everything else in this file is a consequence of it.
- **Provenance** is `[grounded]`, `[inferred]`, or `[generic]`, in its own column rather than trailing the proposed line. It is a column because four prose rules elsewhere in this suite failed to keep these labels attached, and an empty cell is visible to the writer where a missing suffix is not.
- **Status** is `pending your approval` on delivery, and becomes `approved` or `rejected` only when the candidate says so. Nothing else may write to it.

## The operations, and what each may not do

| Operation | What it does | The line it may not cross |
|---|---|---|
| `reorder` | Moves a line earlier or later | Reordering is not re-weighting: a bullet moved to the top must not gain "primary" or "led" on the way |
| `surface` | Promotes something buried — in a tools list, a footnote, an unrelated section | What is surfaced is what was there; a tool listed is not a tool owned |
| `cut` | Removes a line irrelevant to this target | Cutting the context that qualified a claim leaves the claim larger than it was |
| `retitle` | Renames a role or section to a clearer equivalent | An equivalent, not an upgrade — "Grants Officer" may become "Grants Officer (small grants)" and never "Grants Programme Lead" |
| `compress` | Says the same thing in fewer words | The first casualty of compression is the qualifier, and the qualifier is usually the honest part |
| `split` | Separates a line doing two jobs into two lines | Each half must still trace; a split is not a licence to develop the weaker half |
| `merge` | Combines two related lines | Merging two projects into one accomplishment invents a project that never existed |
| `reframe` | Restates in language the target will recognize | The audit's six axes, in full — and never the JD's own vocabulary for the candidate's history |

## The audit is not optional and not last

Run `references/reframing-audit.md` over every proposed line **before** it enters
the ledger, not over the finished table. A row that fails the audit does not get
written and then corrected; it does not get written.

The audit's discipline about the JD's vocabulary — "Never borrow the JD's
vocabulary for the candidate's own history", stated and worked in
`references/reframing-audit.md` — is tested hardest in this skill, because every
row of the ledger is a line the candidate will say about their own past.

## A worked ledger

Halima, a grants officer of six years at a regional foundation, targeting a
programme-manager role at a larger funder. The example sits in a domain none of
this skill's fixtures uses: its earlier version quoted the same candidate one of
them is built on, so a clean room graded that fixture with the answer key
installed beside the skill.

| # | Section | Current line | Proposed line | Operation | Traces to | Provenance | Status |
|---|---|---|---|---|---|---|---|
| E1 | Experience | "Ran the small-grants round" | "Ran the small-grants round for three years — call design, assessor briefing, panel scheduling, award letters" | `surface` | "Ran the small-grants round for three years — call design, assessor briefing, panel scheduling, award letters" | `[grounded]` resume, Experience | pending your approval |
| E2 | Experience | "Built the applicant-tracking spreadsheet" | "Built the applicant-tracking spreadsheet the grants team relies on" | `surface` | "Built the applicant-tracking spreadsheet our four-person grants team relies on" | `[grounded]` resume | pending your approval |
| E3 | Summary | *(no current line)* | "Ran the small-grants round for three years. Coordinated our assessors, the applicant groups and the finance team on award payments." | `merge` | "Ran the small-grants round for three years — call design, assessor briefing, panel scheduling, award letters"; "Coordinated our assessors, the applicant groups, and the finance team on award payments" | `[grounded]` resume | pending your approval |
| E4 | Experience | "Collected end-of-grant reports from every funded group" | *(unchanged — moved above the panel-scheduling bullet)* | `reorder` | "Collected end-of-grant reports from every funded group" | `[grounded]` resume | pending your approval |

Four things this ledger is doing, and one it is refusing:

- **E1 restores a qualifier rather than removing one.** The resume's own sentence carried "for three years" and the stages; the current line had compressed them away. Surfacing them is the honest direction of travel.
- **E2 keeps "the grants team" and does not reach for "foundation-wide"** — the scope axis, in the smallest possible instance.
- **E3 is a summary built only from existing sentences, and kept as two.** It is the row most likely to drift, so its trace cell quotes both in full. It is a `merge`, and merge's limit is the point: joined into one clause, the coordination would read as part of running the round, which neither sentence says. So "coordinated" has not become "led" or "managed", "on award payments" is still there, and the two claims stay separate. An earlier version of this row opened with a number of years and the word "enterprise", traced to one sentence that said neither, and was held up elsewhere as the model of a line with no predecessor.
- **E4 changes nothing but position**, and its trace cell still quotes the line in full. A reorder is the row most tempting to annotate instead of quote — "same line, moved up" says everything a writer needs and nothing a reader can check. This example carried exactly that shorthand until a clean-room run caught the skill copying it. A reorder row with an empty proposed line is normal and is not a filler row: order is a real edit — `machine-readers.md` says why position may matter, and that the case for it is partly inference.
- **What is not here:** no row proposes "programme management experience", "pipeline ownership", or "outcome measurement" — the three things this JD most wants and this resume cannot support. They belong in the coverage map as `not_evidenced` with a recall prompt, and in the prohibited-claims list. A ledger's quality is partly visible in what it declined to write.

## Recording approval

Approval is per row and attaches to specific language, not to the idea behind it.

```text
Approved: E1, E2, E4
Rejected: E3 — "I don't want a summary section at all"
```

A rejected row is recorded in the prohibited-claims list with the reason, so a
later turn does not re-derive it and re-propose it in different words. Re-proposing
a rejected line is the failure that costs the candidate's trust in everything else
in the ledger.

Where the candidate approves a row *with a change*, the changed version is a new
row: it enters the ledger, goes through the audit, and gets its own status. Their
edit is not exempt from tracing — it is the most likely place for a claim to enter,
because it arrives with the authority of having come from them, and it may still
have come from what they wish were true.
