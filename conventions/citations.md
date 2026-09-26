# Citations

Canonical for every Tuesday skill. Skills carry a mirror of this file in their `references/` with a synced-from header; this copy wins on conflict.

Every claim this suite makes about the outside world — a figure from a study, a finding from a survey, what the law permits — is recorded here once, verbatim, beside its source. Prose elsewhere cites it as `(cite C1)` and may quote only text that appears in the entry's **Verbatim** field. CI enforces both.

## Why this file exists

The suite requires every line a skill proposes to trace to a quoted source in a cell, and it built that rule for skill output. The conventions that impose it did not follow it. They paraphrased external sources from memory, and a paraphrase that sits in one file while its source sits in another is never compared with it — which is `CONTRIBUTING.md`'s own test for when a sentence has to become a slot.

It was not hypothetical. Before this file existed:

- A hedge was dropped and a population widened inside an attributed sentence — "favours established candidates" for a source that wrote "may have important implications, including favoring established workers".
- The corrected version was then declared restored *verbatim* and was not. It had been compressed to "may favour" — copied from a spec whose own quotation was already a paraphrase, so the error travelled through the very step meant to fix it.
- A legal claim in a spec — that employers are advised not to ask about citizenship at the application stage — rested on a search tool's summary and was contradicted by the source it cited, which lists work authorization and sponsorship as questions the Department of Justice permits employers to ask.
- A skill shipped to users stated that a staffing firm finds hidden text in "around 10%" of the résumés it scans, and omitted that the same reporting gives about 1% at platform scale — with the larger, more rigorous measurements on the low side.

None was caught by the author. Adversarial review caught the first; re-reading sources caught the rest. This file makes the comparison structural: the quotation and its source sit in one entry, and CI checks that nothing elsewhere quotes more than the entry holds.

## Rules

- **Verbatim means character for character**, apart from two standard concessions stated per entry: footnote markers are omitted, and an omission inside a quotation is shown as `…`. Spelling, tense and number stay as the source wrote them.
- **Record the source you read.** Where a figure reached us through reporting, the entry names the reporting, not the original it quotes. A claim about what The New York Times was told, read in Entrepreneur, is cited to Entrepreneur.
- **Record what weakens it.** A vendor surveying the behaviour its product detects, a single platform standing in for a labour market, a result significant at 10% and not 5% — these belong in the entry, because the reader of a paraphrase never sees them.
- **A claim with no entry here is not stated as a fact about the world.** It is stated as an inference, or not at all.
- **Re-verify rather than re-remember.** `ci/verify_citations.py` refetches every source and reports each entry as verified, not found, or unreachable. It needs the network, so it runs by hand rather than in CI.

---

## C1

- **Claim:** Once an AI tool made cover-letter tailoring cheap, tailoring predicted callbacks and offers far less.
- **Verbatim:** "The correlation between cover-letter tailoring and receiving a callback fell by 51% after the launch of the AI tool, and the correlation with receiving an offer fell by 79%."
- **Source:** Cui, J., Dias, G. & Ye, J. (2025, v2), *Signaling in the Age of AI: Evidence from Cover Letters*, Yale Department of Economics — https://arxiv.org/pdf/2509.25054v2
- **Weakens it:** One platform (Freelancer.com): remote, short-term work, where a platform-native review score exists (see C2). Generalising to hiring at large is an inference.
- **Retrieved:** 2026-09-26

## C2

- **Claim:** In the same period, employers' reliance on the platform's record of past work rose — by much less than tailoring's predictive power fell.
- **Verbatim:** "The correlation between callbacks and workers’ review scores—the platform’s proprietary metric summarizing past work experiences on the platform and determining the default ranking of applications—rose by 5%."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Weakens it:** A proprietary metric that also sets default ranking, so the rise mixes employer judgment with platform ordering.
- **Retrieved:** 2026-09-26

## C3

- **Claim:** The authors name a distributional consequence, hedged.
- **Verbatim:** "This shift may have important implications, including favoring established workers at the expense of newcomers trying to enter the market."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Weakens it:** "May have … implications" is the authors' own hedge; "workers" are freelancers on one platform, not job applicants generally.
- **Retrieved:** 2026-09-26

## C4

- **Claim:** Using the tool raised callbacks.
- **Verbatim:** "we find that access to the generative AI tool increased the probability of receiving a callback by 0.43 percentage points, and usage raised it by 3.56 percentage points. The latter represents a 51% increase relative to the pre-rollout average callback rate of 7.02%."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Weakens it:** See C5.
- **Retrieved:** 2026-09-26

## C5

- **Claim:** The callback effect is weak and short-lived.
- **Verbatim:** "However, the results for callbacks are significant at the 10% level but not at the 5% level. A dynamic effect specification shows that the effect on callbacks tapered off after two months."
- **Source:** Cui, Dias & Ye (2025), as C1. Footnote marker omitted.
- **Retrieved:** 2026-09-26

## C6

- **Claim:** Tailoring rose with the tool.
- **Verbatim:** "access to the generative AI writing tool increased cover-letter tailoring by 0.16 standard deviations, while actual usage raised tailoring by 1.36 standard deviations."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Retrieved:** 2026-09-26

## C7

- **Claim:** The tool narrowed the gap between strong and weak writers.
- **Verbatim:** "the best writers gained half as much as the weakest ones."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Retrieved:** 2026-09-26

## C8

- **Claim:** Uptake was substantial.
- **Verbatim:** "Following its launch, 62% of eligible users used it at least once in their applications, and 17% of all cover letters were written with its assistance."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Retrieved:** 2026-09-26

## C9

- **Claim:** Weaker writers mostly accepted the draft as generated.
- **Verbatim:** "Workers below the median in pre-AI writing ability show a pronounced concentration of editing times between 0 and 1 minute, suggesting they often accept the AI output with minimal changes, whereas those above the median spread their editing effort over longer durations."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Retrieved:** 2026-09-26

## C10

- **Claim:** The association between editing time and hiring is not causal.
- **Verbatim:** "these results should not be interpreted as evidence of a causal relationship: the decision to spend more time editing a cover letter is unlikely to be random and may correlate with unobserved bid characteristics that employers find appealing."
- **Source:** Cui, Dias & Ye (2025), as C1. Footnote marker omitted.
- **Retrieved:** 2026-09-26

## C11

- **Claim:** Before generative AI, tailored cover letters drew more callbacks than none.
- **Verbatim:** "applications that included cover letters tailored specifically to the job at hand had a 53% higher callback rate than applications with no cover letter at all"
- **Source:** ResumeGo, *Cover Letters: Just How Important Are They?* — https://www.resumego.net/research/cover-letters/
- **Weakens it:** Predates generative AI, and C1 is a finding that tailoring's value changed afterwards. A résumé-writing company's study of whether résumé-writing matters; states no limitations; not peer reviewed.
- **Retrieved:** 2026-09-26

## C12

- **Claim:** The same field experiment's scope.
- **Verbatim:** "In the field experiment that was conducted between July 15, 2019 and January 10, 2020, a total of 7,287 fictitious job applications were submitted to job openings found on job boards such as ZipRecruiter, Glassdoor, and Indeed."
- **Source:** ResumeGo, as C11.
- **Retrieved:** 2026-09-26

## C13

- **Claim:** Employers may ask about work authorization and sponsorship.
- **Verbatim:** "Are you legally authorized to work in the United States?" and "Will you now or in the future require sponsorship for employment visa status (e.g., H-1B visa status)?", listed as the questions "DOJ permits an employer to ask job applicants".
- **Source:** Mayer Brown (2022), *Unlawful US Hiring Questions about Visa Status and Citizenship* — https://www.mayerbrown.com/en/insights/publications/2022/07/unlawful-us-hiring-questions-about-visa-status-and-citizenship-are-your-policies-in-compliance-a-2022-primer-with-tips-on-avoiding-discriminatory-practices
- **Weakens it:** US federal law only; a law firm's guidance to employers, not a statute. Not legal advice to candidates.
- **Retrieved:** 2026-09-26

## C14

- **Claim:** What US federal law prohibits is discrimination, and document demands before hiring.
- **Verbatim:** "Discrimination based on citizenship status is expressly prohibited by the Immigration and Nationality Act's anti-discrimination provision, 8 U.S.C. § 1324b." and "Before hiring an employee, do not request to see employment eligibility verification documents or require a candidate to complete the Form I-9."
- **Source:** Mayer Brown (2022), as C13.
- **Weakens it:** As C13.
- **Retrieved:** 2026-09-26

## C15

- **Claim:** Many job seekers *say* they have used hidden text on a résumé.
- **Verbatim:** "41% of US job seekers say they've tried it" and "Of those who haven't? Over half are seriously considering it.", attributed to "Greenhouse's 2025 AI in Hiring Report".
- **Source:** The Interview Guys (2025-11-27), reporting Greenhouse — https://blog.theinterviewguys.com/job-seekers-are-hiding-secret-text-in-their-resumes/
- **Weakens it:** Self-report, not measurement. The reporting carries its own caveat: "Greenhouse sells software to detect exactly this kind of behavior, so they have skin in the game." Read with C17 — the same company's measured rate is about 1%.
- **Retrieved:** 2026-09-26

## C16

- **Claim:** One staffing firm reports finding hidden text in about a tenth of the résumés it scans.
- **Verbatim:** "ManpowerGroup, the biggest staffing firm in the U.S., told the NYT that it finds hidden text in around 100,000 resumes annually, about 10% of the resumes it scans with AI."
- **Source:** Entrepreneur (2025-10-08), reporting The New York Times — https://www.entrepreneur.com/business-news/job-seekers-try-to-pass-ai-screening-with-white-text-prompts/498109
- **Weakens it:** One firm's own detection figure, reported second-hand; the denominator is résumés it scans with AI, not all applications. The same article reports C17.
- **Retrieved:** 2026-09-26

## C17

- **Claim:** Measured at platform scale, hidden text appears in about one résumé in a hundred.
- **Verbatim:** "Meanwhile, AI hiring platform Greenhouse, which reviews 300 million resumes every year for thousands of firms, disclosed to the NYT that 1% of the resumes it processed in the first half of the year contained white text messages."
- **Source:** Entrepreneur (2025-10-08), as C16.
- **Retrieved:** 2026-09-26

## C18

- **Claim:** An independent academic measurement agrees with C17.
- **Verbatim:** "approximately 1% of resumes contain hidden prompt injections"
- **Source:** *Measuring Real-World Prompt Injection Attacks in LLM-based Resume Screening* — https://arxiv.org/html/2605.28999v1
- **Retrieved:** 2026-09-26
