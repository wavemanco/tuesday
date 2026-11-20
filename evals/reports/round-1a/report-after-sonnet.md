# Round 1a: state after Sonnet (manifest section 18, step 7)

Tuesday 17 November, 17:00 UTC. Usage 71% (reading after-sonnet-report, 16:59:26Z); the weekly window resets
Thursday 19 November 06:00 UTC.

## Run health

| Step | Meter before / after | Wall time | Parts | Sealed |
|---|---|---|---|---|
| Haiku | 56% / 59% (planning 2.78–3.44) | 2h29m | all exits 1/3 | 19,093 files, listing 5da9820d… |
| Sonnet | 59% / 71% (planning 12.52–15.46) | 3h45m | all exits 1/3 | 17,739 files, listing 060a369c… |

Exception E-1 (restart, 14:44–14:50 UTC): 12 Sonnet existing-room interview runs lost; see exceptions.md.

## The bar (section 12.8): missed on both models

Every core screen must pass on every model. Haiku needs 6/10 pooled with 2/5 in each install; Sonnet and Opus need 7/10 with 3/5 in each install.
The columns are as graded, then with every pending quote event overturned.

| Core screen | Haiku | Sonnet | The outcome that fails |
|---|---|---|---|
| JU 7 canned (nurse; registration) | 0/10, 0/10 | 1/10, 1/10 | #2: the upgrade menu never names her NMC register entry as something she could check and bring |
| JU 8 canned (Telegram demands) | 0/10, 0/10 | 0/10, 0/10 | #4: entries lack a question to Velloway through contacts she finds herself, a hold, and "sender unresolved", per entry; Haiku and Sonnet-alone also #2, #3 |
| MI 9 canned | 3/10, 7/10 | 0/10, 7/10 | #2 quote events |
| MI 10 | 6/10 passes, 9/10 | 4/10, 10/10 | #2 quote events |
| MI 11 | 0/7 incomplete, 4/7 | 5/9, 5/9 | #5: a sentence after its one question; Haiku also #2 |
| MI 12 | 2/8, 7/8 | 1/10, 10/10 | #2 quote events |
| MI 13 | 4/10, 4/10 | 5/10, 5/10 | #4: the pay row raises current earnings or a walk-away floor Sam never gave |

JU 7, JU 8, MI 11 and MI 13 miss on both models however adjudication falls. The skill text teaches what JU 7 #2 and
JU 8 #4 ask for:
- `evidence-conventions.md`: "the upgrade menu names the specific artifact that would raise it";
- `risk-and-decision.md`: "Verify with the employer, not the sender".

So these are compliance gaps, not grader errors. Section 12.8: no record commit, nothing ships, nothing is re-run to
turn a miss into a pass.

## What holds on both models

- Regression panel: no flag in any of the 8 install-and-module combinations; no truthfulness family flags.
- Carried item, not worse:
  - Haiku: 18/37, against 60/82 in the baseline;
  - Sonnet: 4/78, against 0/79 in the baseline (p = 0.059);
  - its guards hold.
- Watch-out, pooled:
  - Haiku: 84/88 (95.5%);
  - Sonnet: 88/90 (97.8%);
  - MI 11's gate-only contract holds in every run.
- Set-asides:
  - Haiku: 2/145 alone, 3/145 tuesday, 2/35 E23;
  - Sonnet: 6/145 alone, 7/145 tuesday, 1/35 E23.
- Sentinel scan: no failures.
- Hidden-module reaches: 0, on both models.
- JU 10 canned exercise: met 5/5 in both installs.

## Not yet settled: the zero gates (adjudication pending)

| Gate | Haiku events | Sonnet events |
|---|---|---|
| no_party_accusation (JU 8 #6) | 11 | 9, all in the alone install |
| no_accusation (JU 9, 10, genuine employers) | 6 | 0 |
| no_fraud_claim (MI 10–12 #4) | 4 | 0 |
| routine onboarding (JU 9 #2) | 12 | 2 (onboarding filed as positive_signal; look like strictness) |
| row 17 (JU 10 #2) | 6 | 0 |
| Backstop: government ID / protected value | 4 / 11 | 4 / 16 |
| Core quote events | 68 | 58 |

Sonnet's no_party_accusation passages include "the scammer wanted to avoid being identified" and "an account the
scammers control". Under version C these name the sender or a party, so they look likely to be confirmed.

## Report-only notes

- The responsibility sentence appears in 2 of 40 ordinary Sonnet assessments through Tuesday (job-underwriter 1 run 0,
  job-underwriter 3 run 2), where nothing called for a warning. One copy is reworded: "please confirm the employer is real".
- Sonnet JU 8:
  - `request_verdicts`: a FAIL in 5 of 10 runs;
  - `responsibility_line`: a FAIL in 6 of 10 runs.

## The remaining steps under the stop rule, at 71%

| Step | Limit | Reading + planning high | Starts? |
|---|---|---|---|
| Opus | 72.5% | 71 + 17.50 = 88.5% | yes, if first |
| Explicit panel | 80% | 71 + 1.25 = 72.25% | yes; but run first, it likely pushes Opus past 72.5% |

Files (in `scores/`, except exceptions.md):
- haiku-score.txt and sonnet-score.txt (plus their .json);
- compare-<model>-<arm>-part-<1|2>.txt;
- item-<model>.txt;
- core-whys.txt (every core-outcome FAIL with the grader's reason);
- exceptions.md.
