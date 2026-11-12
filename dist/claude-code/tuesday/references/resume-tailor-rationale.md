# Why resume-tailor's rules are shaped as they are

Not required reading: every rule this file explains is stated in `SKILL.md`, or in the reference file `SKILL.md` names at the step that applies it, and nothing here adds to or changes one. It holds the reasons and the measurement history that used to sit beside those rules, so that `SKILL.md` stays short enough to be read whole. Read it before changing a rule, not before following one.

## The skill as a whole

Tailor a resume the way an editor works on someone else's memoir. The market norm for this task is a model that reads a JD, reads a resume, and writes the resume the JD asked for — inventing the overlap wherever the evidence is thin, because that is what makes the output look good. This skill does the same job under one constraint that changes the product entirely.

The constraint is the product. A tailored resume the candidate can defend line by line in an interview is worth more than one that scores better and collapses on the first follow-up question. Every row of the ledger is a sentence they may have to say out loud to someone who was there.

## Step 1 — Premises, corrections and refusals

A premise is corrected before the work because working silently to a false premise leaves the candidate believing it, and they will carry it to the next twenty applications.

A correction or a refusal is never a gate. The failure has a recognisable shape and it is worth naming so it can be caught while writing: the response refuses well, explains itself well, offers the honest alternative — and then asks, as its last question, *"want me to go ahead and run the tailoring on that basis?"*. That question has spent the candidate's turn on a conversation about the work instead of the work, and it is most likely exactly when the request was most uncomfortable, which is when they can least afford to spend a turn. Refusing and delivering are not sequential.

## Step 2 — One place to ask

The recall prompt no longer carries its own `Question:` line. Counting was the rule for three versions and it failed in half of all graded runs, because a `Question:` line inside a template does not feel like it counts. Removing the second site is what counting could not do.

A second mention of a sibling is the skill lobbying rather than informing.

## Output discipline

`provenance` is not declared an enum for the reason job-underwriter gives: a recovery row's Provenance cell is free text, not a compound value.

`operation` and `row_status` are this skill's own enums and they are the ones most likely to acquire a qualifier.

`qualifier_fields: none` is a declared absence, not an oversight: the edit ledger's eight columns are all load-bearing — `Traces to` holds a verbatim quote and is not free text. Sibling skills route their qualifiers to `reasoning` or `hypothesis`. This is recorded rather than fixed because adding a ninth column changes the ledger's shape and that needs its own measurement; the exposure is real and so far unfired.

## Research

The research rules are stated rather than left silent because a rule that cannot fire is invisible from inside, and the next person to add a research step to this skill needs to find the tiers already binding rather than discover them afterwards. They are mirrored here because canonical files are mirrored whole, not because any of them fires.
