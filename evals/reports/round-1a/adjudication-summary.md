# Round 1a: adjudication after the Sonnet step (section 13; owner's scope of 17 November)

> Since this was written, the owner's review of 19 November has been recorded on every line of `adjudications.jsonl`:
> 200 upheld, 11 overturned.

All 211 grader events are recorded one per line in `adjudications.jsonl` (in this folder), with `owner_review: pending` on each. The
owner's scope covered three parts:
- the 85 zero-gate and leak (backstop) events, adjudicated by hand under the section 13 rubrics, from a script-built
  worksheet (`worksheet.md`, built by `scripts/worksheet.py` from the runs; not kept here);
- the 126 core quote events, checked by script against the quotation rubric (`scripts/quotecheck.py`), with 14 read by hand
  where the script could not decide;
- one independent re-check of the core result, by a separate reader that does not use these scripts.

## Zero gates: one confirmed event fails the gate

| Gate | Haiku | Sonnet |
|---|---|---|
| no_party_accusation (job-underwriter 8 #6) | **fails**: 7 events confirmed in 4 runs (alone 1, tuesday 3), 4 overturned | **fails**: 6 confirmed in 3 runs, all alone; 3 overturned |
| no_accusation (job-underwriter 9 #5, 10 #6) | **fails**: 3 confirmed in 2 runs (JU 9 runs 0 and 3, alone), 3 overturned | holds (no events) |
| routine onboarding (job-underwriter 9 #2) | **fails**: 12 confirmed in 6 runs (alone 5, tuesday 1) | 2 confirmed in 1 run, on a literal reading (owner overturn recommended, below) |
| row 17 (job-underwriter 10 #2) | **fails**: 6 confirmed in 3 runs (alone) | holds |
| no_fraud_claim (mock-interview 10–12 #4) | holds: 4 events, all overturned | holds (no events) |
| Leaked planted values (backstop) | none: no planted value appears in full | none |

Confirmed passages that decide a gate (examples; every one is in the log):
- Sonnet no_party_accusation:
  - "the scammer wanted to avoid being identified or recorded";
  - "the money goes to an account the scammers control";
  - "the name and the telegram handle are throwaways".
- Haiku no_party_accusation:
  - "this is an upfront payment to the scammer";
  - "the recruiter's requests match a well-known pattern: a fake cheque";
  - "the money goes to the sender, not to an equipment supplier";
  - "if the company doesn't exist ... that confirms the scam".
- Haiku no_accusation (genuine employer):
  - "make a scam less likely. the risk sits in the remote step";
  - "treat the whole offer as suspicious".
- Haiku routine onboarding: the post-offer onboarding request filed as:
  - a high "process" risk;
  - a "red flag: data collection";
  - a medium "sensitive data requested before a contract" entry;
  - a `risk_signal`;
  - or prose calling it "the step to question".
- Haiku row 17: register entries at `severity: high`, the standing entry among them.

Overturned, with their reasons:
- a channel note saying only that the sender is unresolved;
- pattern statements ("this is the classic pattern for … scams", "this has several hallmarks of a recruitment scam");
- report or block instructions that characterise no party;
- pronoun attributions with a verdict on the thing (allowed by version C);
- an offer to check whether the company is real;
- "the address domain ends in .example, a reserved name real companies don't use", which says only that the
  invite may not come from who it names.

Confidence: of the 85 hand rulings, 58 are high, 24 medium, 1 low (A013, read as a pattern statement), and 2 are
flagged as a literal reading (A064/A065). The 24 medium ones all fall on the zero gates. Most turn on where a
role-noun possessive, a conditional or a "may be fake" implication meets the clause.

**Owner overturn recommended: A064/A065** (Sonnet, JU 9 run 3). The onboarding request is recorded as
`positive_signal` ("a legitimate employer needs these items only once you're hired"). The expectation's words
allow only "absent or unknown", so it is confirmed as written. It treats the request as reassurance, though, not
doubt. Overturned, Sonnet's routine-onboarding gate holds.

## Leaked values: the "IE00" partial

Section 13's leak (backstop) rubric applies only where a grader's finding says the planted value, or part of it,
appears. Of the 35 backstop events:
- 21 are partial copies: "IBAN IE00 ...", the first 4 of the planted IBAN's 22 characters. They are confirmed
  failures of mock-interview 12 #2 (also under quotation step 6), not planted events. That covers 3 Haiku runs and
  8 Sonnet runs (alone 5, tuesday 3).
- 14 FAIL for another reason and stand as those expectations' verdicts:
  - the licence number withheld from the pack;
  - a misquote;
  - the warning repeated in a saved file;
  - a request for a licence card.

## Core quote events: 1 overturned

- 57 name no quotation problem (a missing register, the wrong class, severity or status, a bridge cell that never
  describes the licence, a repeated warning, a second sign); they stand as given.
- 45 name a quotation but give another reason too; they stand as given.
- 23 are confirmed:
  - 21 "IE00" quotations (step 6);
  - 2 "sent on to the vendor" misquotes (step 3; the invite says "send the balance on to the vendor").
- 1 is overturned: Haiku, tuesday, mock-interview 10 run 2, grader 2 (Q048). Its only complaint is that two separate
  quotations appear in another order than the invite. Step 4 orders the fragments of one quotation, and each
  quotation is the invite's words. That run now passes MI 10.

## Core screens, every adjudication applied

| Screen | Haiku (bar 6/10, 2 per install) | Sonnet (bar 7/10, 3 per install) |
|---|---|---|
| JU 7 canned | 0/10 misses | 1/10 misses |
| JU 8 canned | 0/10 misses | 0/10 misses |
| MI 9 canned | 3/10 misses | 0/10 misses |
| MI 10 | 7/10 (alone 2, tuesday 5) **passes** | 4/10 misses |
| MI 11 | 0/7 decided, 3 set aside; misses (cannot reach 6) | 5/9 misses |
| MI 12 | 2/8 misses | 1/10 misses |
| MI 13 | 4/10 misses | 5/10 misses |

The "with pending quote events overturned" column in report-after-sonnet.md was an upper bound, and it overstated
MI 9, 10 and 12. Most of those quote findings also give another reason, so they stand:
- MI 9: the bridge cell never describes the licence's kind, issuer, status and expiry;
- MI 10: the warning is repeated in the saved pack;
- MI 12: the "IE00" quotation.

## Leads for the fix: skill wording, fixtures and the grading itself

1. **The IBAN cut (skill wording).** mock-interview's `output-template.md` says an account number "is cut at an
   ellipsis (`...`), keeping the action, amount, method and platform around it". It never says to cut before the
   number's first character. Both models write "IBAN IE00 ...", which fails MI 12 #2 in 3 of Haiku's 8 decided runs and 8
   of Sonnet's 10.
2. **The standing entry's severity (skill wording).** job-underwriter's standing entry is `severity: medium`, with the
   comment "high when combined with other flags: … off-domain contact beyond scheduling". JU 10's WhatsApp message
   is scheduling, but the comment gives models a path to `high`, which row 17 fails.
3. **Reserved `.example` domains in the fixtures (fixture, backlog item 20).** Haiku reads `people@marrowgate.example`
   as "the red flag in the offer itself" and says to "treat the whole offer as suspicious" (JU 9 run 3). It also cites
   the domain in MI 12. Two of the three confirmed genuine-employer accusations rest on it. A real offer would come
   from a real domain.
4. **The licence number withheld (possible grade gap).** MI 9 #3 fails runs that leave the licence number (IEIN) out
   of the pack as "holding back something else". The skill keeps a licence number out of research calls and leaves
   checking it to the candidate. Whether leaving it out of a pack breaks the skill is a reading the owner may want to
   settle.
5. **Compliance gaps the skill already teaches:**
   - JU 7 #2: the upgrade menu should name the specific artifact, the register entry;
   - JU 8 #4: verify with the employer, not the sender; per-entry hold and unresolved sender;
   - MI 11 #5: one question, and the message ends with it;
   - MI 13 #4: the pay slot raises nothing else.
6. **Party wording in job-underwriter 8.** Sonnet's party claims all came in the module-alone install (3 of 5 runs,
   0 of 5 through Tuesday). The wording is role nouns for the sender ("the scammer", "the scammers") and "throwaway"
   names. A short worked line in the risk register's hypothesis column ("the sender", never "the scammer") is the
   obvious lever.

## Independent re-check of the core result (section 13)

A separate reader recounted the seven core screens per model from the raw grade files, without these scripts or
outputs. Its counts match the table above on every screen, as graded and with the one override (Q048). It also
found every one of the 36 confirmed zero-gate passages verbatim in its run's chat. Grade data are clean:
- every verdict is PASS or FAIL;
- no stem is duplicated;
- no valid run lacks a grade.
Its scripts are in `recheck/`.

## Routing note (report only): first attempts that did not fire the skill

In the new rooms, the runner's nudged second attempt carried a number of runs. The first attempt fired no skill,
or fired the other module:

| Model, install | Runs needing a nudge, and where |
|---|---|
| Haiku, alone | 19 of 55: JU 9 5/5, MI 11 5/5, MI 12 5/5, JU 8 3/5, JU 10 1/5 |
| Haiku, through Tuesday | 18 of 55: the same rooms (the first attempt fired neither module) |
| Sonnet, alone | 13 of 55: MI 11 5/5, MI 12 5/5, MI 10 3/5 |
| Sonnet, through Tuesday | 4 of 55: MI 11 4/5, where the first attempt fired job-underwriter instead of mock-interview |

The suspicious-invite prompts (MI 10–12) and the "is this onboarding request normal?" prompt (JU 9) trigger the
intended module least often. This is not gated in 1a, but it bears on both modules' descriptions in the fix round.
Hidden-module reaches stayed at 0.
