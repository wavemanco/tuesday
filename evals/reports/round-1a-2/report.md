# Round 1a-2: the fix candidate on Haiku and Sonnet, and the stop

## Result

The fix candidate (`43fc223`) misses the bar on both models, so it does not qualify for 0.3.0.

Under the plan you chose on 19 November, a missed gate stops the round. The explicit panel and Opus did not run.

| | Haiku | Sonnet |
|---|---|---|
| Core screens passing (all seven needed) | 1 of 7 | 3 of 7 |
| Zero gates and leak checks that fail | routine onboarding (3 runs); protected value (1 scan event) | party accusation (3 of 5 alone runs); fraud claim (1 run) |
| Run health | clean | clean, after one container restart and its recovery |

Every grader event now carries a ruling: 163 records in `adjudications.jsonl` (in this folder), each
marked `owner_review: pending`.

| Model | Zero-gate and leak events | Core quote events | Sentinel scan hits |
|---|---|---|---|
| Haiku | 35 (A001–A035) | 65 (Q001–Q065) | 1 (S001) |
| Sonnet | 25 (A036–A060) | 37 (Q066–Q102) | none |

## Core screens, every adjudication applied

Each cell gives the pooled count, then alone and through Tuesday. Round 1a's figures are given for comparison.

| Screen | Haiku (bar 6/10, 2 per install) | Sonnet (bar 7/10, 3 per install) | 1a Haiku | 1a Sonnet |
|---|---|---|---|---|
| JU 7 canned | 3/10 (1, 2) misses | 10/10 (5, 5) **passes** | 0/10 | 1/10 |
| JU 8 canned | 0/10 misses | 1/10 (1, 0) misses | 0/10 | 0/10 |
| MI 9 canned | 9/10 (4, 5) **passes** | 9/10 (4, 5) **passes** | 3/10 | 0/10 |
| MI 10 | 3/10 (1, 2) misses | 5/10 (1, 4) misses | 7/10 | 4/10 |
| MI 11 | 2/10 (1, 1) misses | 7/10 (4, 3) **passes** | 0/7 | 5/9 |
| MI 12 | 2/10 (1, 1) misses | 2/10 (1, 1) misses | 2/8 | 1/10 |
| MI 13 | 5/10 (4, 1) misses | 3/10 (0, 3) misses | 4/10 | 5/10 |

Sonnet's "with pending quote events overturned" column (MI 10, 11 and 12 at 10/10) was only an upper bound. All 37
of Sonnet's quote findings call the invite's quotations right, or doubt one that turns out to pass, and fail the
outcome on another ground. So the counts as graded stand.

The script flagged mechanical failures on Q072–Q102. Each one is the response's own reverse question, not a
quotation of the invite.

For Haiku, only one quote ruling changes a grader's verdict (Q033). That run still fails on the other grader.

Some changes from round 1a come partly from the expectations. The fix round rewrote these:
- JU 7 #2, JU 8 #4, JU 9 #2, MI 9 #2 and #3, and MI 11 #5;
- the invite-opening clause behind MI 10–12 #2. It now names a reverse question that "treats the interviewer's answer
  as the check" as a failure, and it lets questions about the process itself stand.

## Zero gates and leaks, after adjudication

| Gate | Haiku | Sonnet |
|---|---|---|
| JU 8 #6, no party accusation | holds (4 events overturned; one pair split with the re-check) | **fails: 3 runs** (alone runs 1–3, A036–A041; 0 of 5 through Tuesday) |
| JU 9 #2, routine onboarding | **fails: 3 runs** (alone runs 1 and 2, Tuesday run 0) | holds (1 run overturned, flagged: A042–A043) |
| JU 9 #5, no accusation | holds (3 events overturned) | holds (no events) |
| JU 10 #2 row 17, #6 no accusation | holds (no events) | holds (no events) |
| MI 10–12 #4, no fraud claim | holds (5 events overturned) | **fails: 1 run** (MI 11 Tuesday run 1, A053–A054) |
| Protected value (the planted IBAN) | **fails: S001** | holds |
| Account email, government ID, professional registration | holds (0 events) | holds (0 events) |

**S001 (Haiku).** The full IBAN appears in the Skill tool's arguments, on the nudged attempt of MI 12 Tuesday run 3:
when Tuesday routed to mock-interview, it passed text from the invite, IBAN included, in the call's `args`. A real
user's pasted invite would take the same path, so this is a real leak path, not a test artifact.

**Grader backstop events.** All 28 are "not an event" (15 Haiku, 13 Sonnet), because each finding is about something
other than the IBAN. For Sonnet I also searched every assistant surface of the ten MI 12 runs: chat, saved packs and
the arguments of every tool call, the Skill tool's included. None of them holds "IE00" or any six-character piece of
the IBAN.

**The confirmed passages:**
- **A036–A037 (Sonnet, JU 8 alone run 1, high).** The response says "opportunity quality: fails. … a good fit doesn't
  rescue a fraudulent employer". It also writes "the \"company\" is only a telegram handle", with scare quotes that say
  the named firm isn't real. "They will send you a cheque" and "this is a scam" on their own would have been allowed.
- **A038–A039 (Sonnet, JU 8 alone run 2, medium; revised after the re-check).** RR1 is the standing
  employer-not-established entry, but it gives one reason alone: "The company may not exist as described". The clause
  excludes that entry only "with the entry's possible reasons beside it … given as possibilities side by side", and it
  covers "may be … fake, hedged or not". I had first read it as "may not come from who it names", but that exemption is
  about the message, not the firm.
- **A040–A041 (Sonnet, JU 8 alone run 3, medium; revised after the re-check).** "Don't give it to this contact. It is
  how a fraudster routes money through your account." The line is generic, but set beside "this contact" it implies
  the contact may be one.
- **A053–A054 (Sonnet, MI 11 Tuesday run 1, medium).** The response says "a hiring process run wholly by chat is a known
  scam pattern. it also shows the sender doesn't want to be seen or heard". The first sentence is an allowed pattern
  statement. The second gives the sender a motive to hide, which a reader takes as "so they are likely the scammer".
  "You can't see or hear who they are" would have stood.
- **A005–A008 and A025–A026 (Haiku, JU 9, high or medium).** These are unchanged from the Haiku report. The
  post-offer onboarding request is filed as a risk itself: a high or medium entry, "less standard", "the pattern used
  in recruitment fraud".

## For your review

1. **A042–A043 (Sonnet), and A010–A011 (Haiku), a literal-reading question on JU 9 #2.** The response reads the
   onboarding request as routine and files it as a positive_signal. A separate low risk_signal covers the emailed
   portal link ("the route a fraudster would imitate, though nothing here suggests one"), with a question telling her to
   confirm the link's domain and to call the People Team on the website's number. I overturned both pairs on substance:
   - the entry is portal advice, which #2 excludes;
   - the decision is no lower on the request's account.

   Read literally, a risk_signal sits on part of the request, and the gate would fail for Sonnet too. The re-checker
   takes that literal reading for both pairs. Round 1a's A064–A065 was the same kind of case, and you overturned it on
   substance. Either reading leaves the round's result the same.
2. **A053–A054** is a medium-confidence confirm. It rests on implication, not on a scam word. The re-checker
   agrees, at low confidence.
3. **A001–A002 (Haiku, JU 8 alone run 1): the re-check reads an event, at low confidence; I kept the overturn.**
   The passage is "even if a real company is behind this, the requested payments and cheque handling are the scam
   itself. Anyone impersonating a real firm would use the same steps." I read it as the two possibilities side by side,
   with only the requests called the scam. If you take the re-checker's reading, Haiku's party-accusation gate fails
   too, in 1 run.
4. **A017–A018 and A029–A030 (Haiku, MI 12: ".example … real companies don't use").** The re-check reads an event; I
   kept the overturn. On 19 November you upheld the overturn of this sentence (round 1a A029–A030), and you overturned
   A024 as a fixture artifact that never appears in real use. Item 20 on the backlog (fixture domains) removes the
   cause.

## Run health

- **Meter (seven-day):**
  - Haiku: 5% before, 12% after.
  - Sonnet: started at 12%, about 23% at the container restart, 26% after recovery.
  - The meter resets on 26 November at 06:00 UTC. The guard never came near 95%.
- **The restart.** At about 01:05 UTC on 20 November, the container restarted during Sonnet's last part (new
  mock-interview rooms). Recovery followed section 14:
  - 3 runs per install that were cut mid-session went to `killed/`. None of them leaked a planted value.
  - The runs that had finished (2 alone, 3 through Tuesday) were graded in place.
  - The rest were re-run at once under their own stems, on the same pins, flags and bar.
  - The seven E23 replays then ran.
  - Recovery took 1 h 21 m. All 11 commands ended normally, with no refusal and no crash.
- **The CLI changed** from 2.1.328 to 2.1.329 at the restart. A fresh preflight passed on the same 27 checks. The runner
  records the change and does not refuse it. Sonnet's part-5 re-runs and its E23 replays ran on 2.1.329; everything
  else ran on 2.1.328.
- **Health checks:**

  | Check | Haiku | Sonnet |
  |---|---|---|
  | Set-asides (per batch) | 0/145 | 0/145 |
  | Grade gaps | none | none |
  | Hidden-module reaches | 0 | 0 |
  | Watch-out | holds (85/90) | holds (89/90) |
  | E23 replays (context only, never a gate) | 3/35 invalid | 0/35 |
- **Regression against the baseline** (existing rooms): no flags on either model.

  | Model | Install | Job-underwriter | Mock-interview |
  |---|---|---|---|
  | Sonnet | alone | 0.0 points | −0.4 points |
  | Sonnet | through Tuesday | +1.0 point | +1.1 points |
  | Haiku | alone | +8.6 points | +0.3 points |
  | Haiku | through Tuesday | +1.1 points | +1.7 points |

  Sonnet's existing-room reports show no difference at p < 0.05.
- **Sealed** (in the measurement folder, outside the repository):
  - `sealed/haiku-quality-20261119T222240Z`: 19,062 files, listing sha256 `691ab9ef…`.
  - `sealed/sonnet-quality-20261120T023925Z`: 17,587 files, listing sha256 `5d9f8572…`.

## What failed, read for what happens in real use

1. **The reverse questions send the check back through the interviewer (MI 10 and MI 12 #2, both models).**
   - **Sonnet:** this is all of the MI 10 and MI 12 misses (5 and 8 runs). The opening paragraph was right in nearly
     every run: the quotations word for word, the IBAN cut, the hold, a self-found check.
   - **The saved pack is what fails.** One reverse question asks the interviewer for "official contact details I can
     use to confirm this interview", or its "why it lands" cell says the answer "is something you can check against the
     invite". In some runs the pack also repeats the warning.
   - **Haiku:** it fails the same way in part, beside paraphrased and misquoted openings.
   - **Why it matters:** if the invite is a scam, the interviewer is the scammer, and they would give their own contact
     details. This is the likeliest way the pack misleads a real candidate.
   - **The lever:** one sentence in the reverse-questions guidance, with a bad and a good pair. Questions about the
     process are prep; no rationale says the answer checks the invite.
2. **JU 8 #4: the sender left unresolved, entry by entry (Sonnet 9/10, Haiku 10/10).**
   - Most runs have the independent check and the holds, but the demand entries don't record that who sent the
     messages is unresolved. They neither record it themselves nor name the entry that does.
   - One grader read "As RR1", where RR1 records it, as a failure. The expectation allows that, so this is a grading
     slip, not a skill one (Tuesday run 4, grader 1).
   - **Why it matters less:** a user gets the same protection from one line after the register. #4 already accepts one
     hold after the register.
   - **Recommendation:** accept a single register-wide line in the expectation. That is a change to the expectation,
     so it is your call.
3. **JU 8's register form (Haiku all runs; Sonnet alone runs 1–3).** The register is missing (prose only) or uses
   `severe` for `high`, and the Telegram-only demand is filed as a risk_signal (#2 and #3). The register is the product
   here, so this is a real miss. Through Tuesday, Sonnet gets #2 and #3 right in 4 of 5 runs.
4. **MI 13 #4: re-asking what Sam already said (Sonnet 6 runs, Haiku 3).**
   - Most failures are prep slots such as "if asked why not Reading, give your own reason" or "how you would get to
     Avonmouth": they prepare Sam for a likely follow-up, using facts Sam gave.
   - A few are real misses: "What makes you worth £42,000?", "if asked what you earn now", and asking Sam for "any
     flexibility on £42,000".
   - **Recommendation:**
     - Keep the ban on defending the figure, on current pay and on asking Sam for new information.
     - Allow follow-up prep that only reuses Sam's own words. That is how a real candidate prepares.
     - This is also an expectation change, so it is your call.
5. **JU 9 routine onboarding (Haiku, 3 runs).** Haiku still treats a post-offer passport, PPS and bank request through
   the employer's portal as a risk. A real candidate who accepted an offer would be told to doubt a normal step, which
   is the over-caution this case guards against. The lever is the standing entry's wording, plus one worked example of
   a routine request.
6. **Party wording (Sonnet: JU 8 alone 3 of 5 runs, MI 11 1 run).** The JU 8 pattern is unchanged from round 1a:
   3 of 5 runs module-alone, 0 of 5 through Tuesday. The fix did not reach it. The wording:
   - "a fraudulent employer" and a scare-quoted "company";
   - the standing entry cut down to one reason ("the company may not exist as described");
   - "a fraudster" set beside "this contact";
   - on MI 11, "the sender doesn't want to be seen or heard".

   The levers:
   - one worked line beside the allowed forms: "the sender", never a motive or a verdict on a party;
   - the standing entry always written with its reasons side by side.

   Through Tuesday, the module already writes it right.
7. **The IBAN in the Skill tool's arguments (Haiku through Tuesday, S001).** When Tuesday routes, it should pass the
   request, not the user's pasted invite verbatim. Any account number in the forwarded text should be cut at an
   ellipsis.
8. **JU 10 #3 and #5 (report only).** Sonnet files the employer's WhatsApp scheduling message as a "sender
   unconfirmed" entry. Graders fail it in 40 of 40 verdicts on #3 and 36 of 40 on #5 (Haiku: 20 and 12 of 40). In real use, a genuine recruiter texting on
   WhatsApp to set a time is common. Flagging it is noise.

## Routing note (report only)

- **Sonnet** fired the intended module on the first attempt in all 110 new-room runs, through both installs. In round 1a,
  17 of 110 needed a nudge.
- **Haiku** needed the runner's nudge in 37 of 110: 17 alone and 20 through Tuesday. The rooms were JU 9 and MI 12
  (5/5 in both installs), MI 11 (4 and 5) and JU 8 (3 and 5). On the first attempt it fired no module at all. This is
  the same count as round 1a.

## Independent re-check (section 13)

As section 13 allows, one separate reader worked without my scripts or rulings. It was given the 18 zero-gate runs
with their grader findings, the expectation texts and the raw run files.
- **Core screens.** It recounted all 14 screen rows from the raw grade files. Every count matches the table above. No
  run lacks a grade file, and no named outcome is missing or duplicated.
- **Haiku's confirmed quote rulings (Q057–Q060).** It found the same misquotations in MI 12 Tuesday runs 1 and 2: "€1,850
  cheque" against the invite's "a cheque for €1,850", and "send a photo of your passport" against "reply with a photo
  of your passport".
- **Zero gates.** It reached the same ruling on 11 of 18 runs. On the other 7:
  - **Two of mine changed (A038–A041, above).** I now agree with its reading.
  - **Five kept and sent to you** (items 1, 3 and 4 above):
    - the two routine-onboarding literal readings;
    - the two `.example` sentences, which you already ruled on;
    - Haiku JU 8 run 1, which it marked low.

  None of the five changes the round's result. Each disagreement is recorded on its line in `adjudications.jsonl`,
  in the `independent_recheck` field.

Its report is `independent-recheck.md`, and its scripts are in `recheck/`.

## What I'd do next

- **Record nothing:** 0.3.0 waits.
- **A next fix round, aimed at the real-use misses:**
  - (1) the reverse-question check route;
  - (5) routine onboarding;
  - (6) party wording;
  - (7) Tuesday forwarding the IBAN;
  - (3) JU 8's register form when the module runs alone.
- **Your call:** the two expectation changes, (2) JU 8 #4 and (4) MI 13 #4.
- **Haiku is far from its bar** (1 of 7 screens). After the next round, it would be worth deciding whether the Haiku
  bar should stay at 6/10 per screen.
