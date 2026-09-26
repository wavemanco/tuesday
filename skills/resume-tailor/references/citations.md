<!-- SYNCED FROM: conventions/citations.md
     Canonical wins on conflict. Everything below this comment block is a
     verbatim copy of the canonical file — do not edit it here. Fixes flow
     canonical -> mirror, never the reverse; a mirror that drifts is a defect.
     A byte check strips this header and compares the remainder to canonical. -->
# Citations

Canonical for every Tuesday skill. Skills carry a mirror of this file in their `references/` with a synced-from header; this copy wins on conflict.

Claims this suite makes about the outside world — a figure from a study, a finding from a survey, what the law permits — are recorded here once, verbatim, beside their source and what weakens them. Prose elsewhere cites an entry as `(cite C1)`, and a quotation followed by a marker may quote only text the entry holds. CI enforces that.

## Why this file exists

The suite requires every line a skill proposes to trace to a quoted source in a cell. The conventions that impose the rule did not follow it: they paraphrased external sources from memory, and a paraphrase that sits in one file while its source sits in another is never read beside it — which is `CONTRIBUTING.md`'s own test for when a sentence has to become a slot.

The record of what that cost, in the order it was found:

- A hedge was dropped and a population widened inside an attributed sentence: "favours established candidates", for a source that says a shift "may have important implications, including favoring established workers". Found by adversarial review.
- The correction was declared *restored verbatim* and was not. It had been copied from the cover-letter spec, whose own quotation was already a compression, so the error passed through the step meant to fix it. Found by the author re-reading the source to build this file.
- Building this file, the author then introduced four errors while correcting others, and a second review panel found all four:
  - A spec line saying employers are advised not to ask about citizenship was "corrected" with evidence about *work authorization* — a different question the source keeps separate — and recorded here as a case of the source contradicting the spec. It did not.
  - A figure of 52% was recorded as an error because a secondary source rounded it to "over half"; the primary source says 52%.
  - A 41% share of *people* who say they have used hidden text was set against a 1% share of *résumés* found to contain it, and called a gap between saying and doing. People and documents are different units, and the two figures do not conflict.
  - A 51% fall and a 5% rise were compared as if on one scale and called "the finding". They are relative changes on bases about four times apart, and the authors describe the rise as substantial.

- This file then said it held every claim the suite makes about the outside world, and all three `SKILL.md` files repeated it. A third review found seven claims in shipped reference files with no entry, and two of them were wrong as well as uncited once the sources were read: a self-preference effect measured as a difference between probabilities had been described as a share of comparisons, and 2 of 25 interviewed recruiters had become "the overwhelming majority of applications". Entries C23–C31 were added from the sources, and the scope below says what the file covers rather than everything.

The last six are why the rules below are strict about units, bases and primary sources, and why an entry's own **Claim** field is held to what its **Verbatim** says.

## Rules

- **Verbatim means character for character.** The only concession is an omission shown as `…` inside the Verbatim itself, and the verifier inspects every omission: it may skip a footnote number or ordinary words, never a hedge or a negation. Prose quoting an entry may not add an omission the entry did not make.
- **Cite the primary source when one can be read.** A secondary source may round, paraphrase or drop a caveat; if only reporting can be read, the entry names the reporting and says so.
- **The Claim field states what the Verbatim supports and no more.** It is a label for the quotation, not a reading of it. Readings belong in prose, labelled as inference.
- **Record what weakens it** — a vendor surveying behaviour its product addresses, a single platform standing in for a labour market, a result significant at 10% and not 5%, a lower bound, a different unit from the figure it will be read beside.
- **Figures with different units, bases or constructs are not compared as if they shared one.** Say what each counts.
- **Scope, stated honestly:** every figure, research finding, survey result and statement of law in the conventions, the skills' shipped files and the specs has an entry here, as of the sweep recorded above. Practitioner heuristics — interviewer personas, company archetypes, question stems — are the skills' own priors, presented as priors, and are not cited. The ledger records this repository's history and cites where it states an outside finding. A claim without an entry reads as an inference or is removed. CI catches a quotation that strays from its entry and a paraphrase in quotation marks; a paraphrase without them it cannot see, so this scope is kept by review as well as by CI.
- **Re-verify rather than re-remember.** `ci/verify_citations.py` refetches every source and reports each entry as verified, not found, malformed, or unreachable. It needs the network, so it runs by hand rather than in CI, and unreachable is reported as unchecked, never as a pass.

---

## C1

- **Claim:** After an AI writing tool arrived, cover-letter tailoring was less correlated with callbacks and with offers.
- **Verbatim:** "The correlation between cover-letter tailoring and receiving a callback fell by 51% after the launch of the AI tool, and the correlation with receiving an offer fell by 79%."
- **Source:** Cui, J., Dias, G. & Ye, J. (2025, v2), *Signaling in the Age of AI: Evidence from Cover Letters*, Yale Department of Economics — https://arxiv.org/pdf/2509.25054v2
- **Weakens it:** One platform (Freelancer.com): remote, short-term work. Relative changes: the tailoring coefficient is 0.0485 before the tool, so a 51% fall is about 0.025 in absolute terms. Generalising to hiring at large is an inference.
- **Retrieved:** 2026-09-26

## C2

- **Claim:** Over the same period, the correlation between callbacks and workers' review scores rose.
- **Verbatim:** "The correlation between callbacks and workers’ review scores—the platform’s proprietary metric summarizing past work experiences on the platform and determining the default ranking of applications—rose by 5%."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Weakens it:** The metric also sets default ranking, so the rise mixes employer judgment with platform ordering. A relative change on a larger base than C1's; the 5% and the 51% are not on one scale and should not be set against each other.
- **Retrieved:** 2026-09-26

## C3

- **Claim:** The authors name a possible distributional consequence, hedged.
- **Verbatim:** "This shift may have important implications, including favoring established workers at the expense of newcomers trying to enter the market."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Weakens it:** "May have … implications" is the authors' hedge; "workers" are freelancers on one platform, not job applicants generally.
- **Retrieved:** 2026-09-26

## C4

- **Claim:** Using the tool raised the probability of a callback.
- **Verbatim:** "we find that access to the generative AI tool increased the probability of receiving a callback by 0.43 percentage points, and usage raised it by 3.56 percentage points. The latter represents a 51% increase relative to the pre-rollout average callback rate of 7.02%."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Weakens it:** See C5.
- **Retrieved:** 2026-09-26

## C5

- **Claim:** The callback effect is significant only at the 10% level and faded within two months.
- **Verbatim:** "However, the results for callbacks are significant at the 10% level but not at the 5% level. A dynamic effect specification shows that the effect on callbacks tapered off after two months."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Retrieved:** 2026-09-26

## C6

- **Claim:** Tailoring rose with access to the tool and more with its use.
- **Verbatim:** "access to the generative AI writing tool increased cover-letter tailoring by 0.16 standard deviations, while actual usage raised tailoring by 1.36 standard deviations."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Retrieved:** 2026-09-26

## C7

- **Claim:** The strongest prior writers gained half as much as the weakest.
- **Verbatim:** "the best writers gained half as much as the weakest ones."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Retrieved:** 2026-09-26

## C8

- **Claim:** Uptake among eligible users, and the share of letters written with the tool.
- **Verbatim:** "Following its launch, 62% of eligible users used it at least once in their applications, and 17% of all cover letters were written with its assistance."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Retrieved:** 2026-09-26

## C9

- **Claim:** Weaker prior writers mostly spent under a minute editing the draft.
- **Verbatim:** "Workers below the median in pre-AI writing ability show a pronounced concentration of editing times between 0 and 1 minute, suggesting they often accept the AI output with minimal changes, whereas those above the median spread their editing effort over longer durations."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Retrieved:** 2026-09-26

## C10

- **Claim:** The authors decline a causal reading of the association between editing time and hiring.
- **Verbatim:** "these results should not be interpreted as evidence of a causal relationship: the decision to spend more time editing a cover letter is unlikely to be random … and may correlate with unobserved bid characteristics that employers find appealing."
- **Source:** Cui, Dias & Ye (2025), as C1. The omission is a footnote marker.
- **Retrieved:** 2026-09-26

## C11

- **Claim:** In one pre-AI field experiment, tailored letters drew more callbacks than none.
- **Verbatim:** "applications that included cover letters tailored specifically to the job at hand had a 53% higher callback rate than applications with no cover letter at all"
- **Source:** ResumeGo, *Cover Letters: Just How Important Are They?* — https://www.resumego.net/research/cover-letters/
- **Weakens it:** Predates generative AI, and C1 is a finding that tailoring's relation to callbacks changed afterwards. A résumé-writing company's study of whether résumé-writing matters; states no limitations; not peer reviewed.
- **Retrieved:** 2026-09-26

## C12

- **Claim:** The same experiment's dates, size and where the applications went.
- **Verbatim:** "In the field experiment that was conducted between July 15, 2019 and January 10, 2020, a total of 7,287 fictitious job applications were submitted to job openings found on job boards such as ZipRecruiter, Glassdoor, and Indeed."
- **Source:** ResumeGo, as C11.
- **Weakens it:** "Such as" — the boards named are examples, not the full list.
- **Retrieved:** 2026-09-26

## C13

- **Claim:** The experiment's three groups of applications.
- **Verbatim:** "These job applications did not include a cover letter at all." and "These job applications included a well-composed, but generic, cover letter that provided a short summary of the candidate's qualifications." and "These job applications included a cover letter tailored to the exact job being applied for, providing details on how the candidate would be a great fit for the company culture and requirements of the job description."
- **Source:** ResumeGo, as C11.
- **Retrieved:** 2026-09-26

## C14

- **Claim:** A law firm reports the questions about work authorization and sponsorship that the DOJ permits employers to ask.
- **Verbatim:** "Generally, DOJ permits an employer to ask job applicants a specific set of questions to help the employer inquire about a candidate's employment eligibility and sponsorship." and "Are you legally authorized to work in the United States?" and "Will you now or in the future require sponsorship for employment visa status (e.g., H-1B visa status)?"
- **Source:** Mayer Brown (2022), *Unlawful US Hiring Questions about Visa Status and Citizenship* — https://www.mayerbrown.com/en/insights/publications/2022/07/unlawful-us-hiring-questions-about-visa-status-and-citizenship-are-your-policies-in-compliance-a-2022-primer-with-tips-on-avoiding-discriminatory-practices
- **Weakens it:** A law firm's guidance to employers, not a statute or legal advice to candidates. US federal law only. These questions concern work authorization and sponsorship; they are not questions about citizenship, which the same source treats separately (C15).
- **Retrieved:** 2026-09-26

## C15

- **Claim:** The same source reports that citizenship-status discrimination is prohibited, and advises employers against requiring citizenship.
- **Verbatim:** "Discrimination based on citizenship status is expressly prohibited by the Immigration and Nationality Act's anti-discrimination provision, 8 U.S.C. § 1324b." and "we would encourage employers to avoid such language as"
- **Source:** Mayer Brown (2022), as C14. The second span introduces a list that begins "Must be a US citizen".
- **Weakens it:** Who is protected is limited — see C16.
- **Retrieved:** 2026-09-26

## C16

- **Claim:** The same source reports that, per DOJ guidance, nonimmigrant visa holders are not among the classes protected from citizenship-status discrimination.
- **Verbatim:** "According to DOJ guidance, while nonimmigrant visa holders and recipients of Deferred Action for Childhood Arrivals (DACA) are protected from national origin discrimination, they are not considered to be among the classes protected from citizenship status (alienage) discrimination."
- **Source:** Mayer Brown (2022), as C14.
- **Weakens it:** As C14. Guidance as reported by a law firm in 2022.
- **Retrieved:** 2026-09-26

## C17

- **Claim:** In a vendor's survey, 41% of US job seekers said they had used hidden text or prompt injection, and 52% of the rest said they were considering it.
- **Verbatim:** "Of the 1,200 U.S. job seekers surveyed, 41% admit to using prompt injections, hidden text designed to bypass AI filters" and "of those who don't use this tactic, 52% say they are considering it."
- **Source:** Greenhouse (2025-11-19), newsroom release on its 2025 AI in Hiring Report — https://www.greenhouse.com/newsroom/an-ai-trust-crisis-70-of-hiring-managers-trust-ai-to-make-faster-and-better-hiring-decisions-only-8-of-job-seekers-call-it-fair
- **Weakens it:** Self-report. Counts *people* who say they have used it, not résumés containing it, so it is not comparable with C18–C20. Run by an AI hiring platform (C19 describes Greenhouse so).
- **Retrieved:** 2026-09-26

## C18

- **Claim:** One staffing firm said it finds hidden text in about a tenth of the résumés it scans with AI.
- **Verbatim:** "ManpowerGroup, the biggest staffing firm in the U.S., told the NYT that it finds hidden text in around 100,000 resumes annually, about 10% of the resumes it scans with AI."
- **Source:** Entrepreneur (2025-10-08), reporting The New York Times — https://www.entrepreneur.com/business-news/job-seekers-try-to-pass-ai-screening-with-white-text-prompts/498109
- **Weakens it:** One firm's own figure, reported second-hand; method not stated. Counts résumés, and only those it scans with AI.
- **Retrieved:** 2026-09-26

## C19

- **Claim:** Greenhouse disclosed that 1% of the résumés it processed in one half-year contained white text.
- **Verbatim:** "Meanwhile, AI hiring platform Greenhouse, which reviews 300 million resumes every year for thousands of firms, disclosed to the NYT that 1% of the resumes it processed in the first half of the year contained white text messages."
- **Source:** Entrepreneur (2025-10-08), as C18.
- **Weakens it:** Disclosed to a newspaper; method not stated. The 1% is of résumés processed in the first half of the year, not of the 300 million. White text is not necessarily an injection — C20 measures a different construct.
- **Retrieved:** 2026-09-26

## C20

- **Claim:** An academic–industry study estimates hidden prompt injections in about 1% of résumés, as a lower bound.
- **Verbatim:** "approximately 1% of resumes contain hidden prompt injections" and "This estimate should be interpreted as a conservative lower bound, so the true prevalence might be even higher."
- **Source:** Zhang, M., Jia, Y., Tan, Z., Jiang, S., Gong, N. Z., Chen, T. & Song, D. (2026), *Measuring Real-World Prompt Injection Attacks in LLM-based Resume Screening* — https://arxiv.org/html/2605.28999v1
- **Weakens it:** A co-author is at hireEZ and the résumés are hireEZ's. The authors call their 1% a lower bound. Measures prompt injections, not white text generally, so it is a different construct from C19.
- **Retrieved:** 2026-09-26

## C21

- **Claim:** The authors say employers shifted toward other signals.
- **Verbatim:** "In response, employers shifted toward alternative signals, including workers’ prior work histories." and "Instead, employers shifted toward other signals less susceptible to AI influence, such as workers’ past work experience."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Retrieved:** 2026-09-26

## C22

- **Claim:** The authors describe the rise in an alternative signal's predictive power as substantial.
- **Verbatim:** "We find that, following the rollout of the AI tool, the predictive power of bid score rank percentile for interviews increases substantially."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Weakens it:** A different outcome (interviews) and measure (bid-score rank) from C2's callbacks and review scores.
- **Retrieved:** 2026-09-26

## C23

- **Claim:** Language models screening pairs of résumés preferred ones they had generated over human-written ones; the 67–82% range belongs to the larger models, and is a difference between probabilities.
- **Verbatim:** "The bias against human-written resumes is particularly substantial, with self-preference bias ranging from 67% to 82% across major commercial and open-source models." and "Larger models—such as GPT-4o, GPT-4-turbo, DeepSeek-V3, Qwen-2.5-72B, and LLaMA-3.3-70B—exhibit the strongest LLM-vs-Human self-preference, with magnitudes ranging from 67% to 82%." and "In contrast, smaller models display weaker biases" and "The difference between these probabilities provides a direct measure of self-preference bias"
- **Source:** Xu, J., Li, G. & Jiang, J. Y. (2025, v4), *AI Self-preferencing in Algorithmic Hiring: Empirical Evidence and Insights* — https://arxiv.org/pdf/2509.00462v4
- **Weakens it:** A controlled experiment on pairs of résumés, not a live hiring pipeline. The measure is how much more likely a model is to pick its own résumé than the human-written one — not a share of comparisons won, which is how this suite first described it. The models tested will age. A preprint.
- **Retrieved:** 2026-09-26

## C24

- **Claim:** In simulated hiring pipelines, the same authors estimate that candidates using the evaluator's own model are more likely to be shortlisted.
- **Verbatim:** "These simulations show that candidates using the same LLM as the evaluator are 23% to 60% more likely to be shortlisted than equally qualified applicants submitting human-written resumes"
- **Source:** Xu, Li & Jiang (2025), as C23.
- **Weakens it:** Simulated pipelines, not observed hiring. "More likely" is a relative change, not percentage points.
- **Retrieved:** 2026-09-26

## C25

- **Claim:** In a vendor's interviews with 25 US recruiters, two had content-based auto-rejection configured.
- **Verbatim:** "AI/content auto-rejection configured: 8% of recruiters." and "We only saw 2 of 25 using it."
- **Source:** Vasileva, D. (2025, updated 2026), *Does the ATS Reject Your Resume? 25 Recruiters Explain What Really Happens*, Enhancv — https://enhancv.com/blog/does-ats-reject-resumes/
- **Weakens it:** Enhancv sells a résumé builder. Twenty-five recruiters, so 8% is two people, and it counts recruiters rather than applications. Interviews, not system configurations inspected. The page has been updated since it was first published.
- **Retrieved:** 2026-09-26

## C26

- **Claim:** The same source describes knockout questions as eligibility checks that a team can set to reject without review.
- **Verbatim:** "Knockouts are yes/no eligibility checks (work authorization, required license, location). Teams can route failures to a human—or flip a setting to route them straight to reject."
- **Source:** as C25.
- **Weakens it:** As C25.
- **Retrieved:** 2026-09-26

## C27

- **Claim:** The same source says teams use match scores to order review, and that a low score lowers a résumé rather than rejecting it.
- **Verbatim:** "Many teams use match scores/filters to prioritize who gets reviewed first." and "Low score ≠ auto-reject, but in high-volume roles, it can push you to the bottom of the pile."
- **Source:** as C25.
- **Weakens it:** As C25. In a high-volume role the bottom of the pile may never be read, so "not rejected" is not "seen".
- **Retrieved:** 2026-09-26

## C28

- **Claim:** Language models answering questions over long inputs did best when the relevant information sat at the start or the end.
- **Verbatim:** "In particular, we observe that performance is often highest when relevant information occurs at the beginning or end of the input context, and significantly degrades when models must access relevant information in the middle of long contexts, even for explicitly long-context models."
- **Source:** Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F. & Liang, P. (2023, v3), *Lost in the Middle: How Language Models Use Long Contexts* — https://arxiv.org/abs/2307.03172v3
- **Weakens it:** Multi-document question answering and key-value retrieval over long contexts, with 2023 models. A résumé is short and screening is neither task, so carrying the finding to résumé screening is an inference.
- **Retrieved:** 2026-09-26

## C29

- **Claim:** US EEOC guidance: pre-employment questions that may reveal protected traits are not clearly forbidden by law, may be evidence of intent to discriminate, and should generally be avoided.
- **Verbatim:** "Although state and federal equal opportunity laws do not clearly forbid employers from making pre-employment inquiries that relate to, or disproportionately screen out members based on race, color, sex, national origin, religion, or age, such inquiries may be used as evidence of an employer's intent to discriminate unless the questions asked can be justified by some business purpose." and "which may indicate the applicant's race, sex, national origin, disability status, age, religion, color or ancestry if answered, should generally be avoided."
- **Source:** U.S. Equal Employment Opportunity Commission, *Prohibited Employment Policies/Practices* — https://www.eeoc.gov/prohibited-employment-policiespractices
- **Weakens it:** US federal guidance; other jurisdictions differ, and state law may go further. Guidance, not statute. Not legal advice.
- **Retrieved:** 2026-09-26

## C30

- **Claim:** The same page says employers may not ask about disability before an offer.
- **Verbatim:** "Employers are explicitly prohibited from making pre-offer inquiries about disability."
- **Source:** as C29.
- **Weakens it:** As C29.
- **Retrieved:** 2026-09-26

## C31

- **Claim:** Within a worker, more time spent editing the tool's draft went with higher offer and callback rates, at high significance.
- **Verbatim:** "controlling for worker fixed effects" and "The coefficient on editing time is positive and highly significant: spending more minutes tailoring a cover letter after using the tool increases the probability of winning." and "For callbacks (Column 2), the coefficient on editing time is likewise positive and highly significant."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Weakens it:** An association. The sentence says "increases", and the same authors decline the causal reading (C10); this suite follows C10. Editing time is the minutes between opening the tool and submitting the bid.
- **Retrieved:** 2026-09-26
