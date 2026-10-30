# Citations

## Contents

- Why this file exists
- Rules
- C1 to C36, one entry per source

Canonical for every Tuesday skill. Skills carry a mirror of this file in their `references/` with a synced-from header; on a conflict between a mirror and the canonical file it names, the canonical file wins.

Claims this suite makes about the outside world — a figure from a study, a finding from a survey, what the law permits — are recorded here once, verbatim, beside their source and what weakens them. Prose elsewhere cites an entry as `(cite C1)`, and a quotation followed by a marker may quote only text the entry holds. CI enforces that.

## Why this file exists

The suite requires every line a skill proposes to trace to a quoted source in a cell. The conventions that impose the rule did not follow it: they paraphrased external sources from memory, and a paraphrase that sits in one file while its source sits in another is never read beside it — which is the suite's own test, in its contributing guide, for when a sentence has to become a slot.

The record of what that cost, in the order it was found:

- A hedge was dropped and a population widened inside an attributed sentence: "favours established candidates", for a source that says a shift "may have important implications, including favoring established workers". Found by adversarial review.
- The correction was declared *restored verbatim* and was not. It had been copied from the cover-letter spec, whose own quotation was already a compression, so the error passed through the step meant to fix it. Found by the author re-reading the source to build this file.
- Around the time this file was built, the author introduced four errors while correcting others, and a second review panel found all four:
  - A spec line saying employers are advised not to ask about citizenship was "corrected" with evidence about *work authorization* — a different question the source keeps separate — and recorded here as a case of the source contradicting the spec. It did not; and a third review found US federal guidance saying almost what the spec line had said (C32). The line was right and uncited, and the correction was the error.
  - A figure of 52% was recorded as an error because a secondary source rounded it to "over half"; the primary source says 52%.
  - A 41% share of *people* who say they have used hidden text was set against a 1% share of *résumés* found to contain it, and called a gap between saying and doing. People and documents are different units, and the two figures do not conflict.
  - A 51% fall and a 5% rise were set against each other as "the finding" — written three commits before this file existed (63c0070), and carried into it. They are relative changes on different bases and measures, and the authors call the rise substantial.

- This file then said it held every claim the suite makes about the outside world, and all three `SKILL.md` files repeated it. A third review found seven claims in shipped reference files with no entry, and two were wrong as well as uncited once the sources were read: a self-preference effect had been described as a share of comparisons, and the 23 of 25 interviewed recruiters whose systems do not auto-reject had become "the overwhelming majority of applications". Entries C23–C30 were added for the shipped files and C31 for the cover-letter spec.
- The correction of the self-preference figure was itself wrong twice, and a fourth review found both: it quoted the definition of a different metric from the one behind the 67–82% range, and it called the paper's 23–60% shortlisting figure a relative change when it is a gap in percentage points. The same review found the tested comparison was between two versions of a résumé's summary section, not two résumés.

These are why the rules below are strict about units, bases and primary sources, and why an entry's own **Claim** field is held to what its **Verbatim** says.

## Rules

- **Verbatim means character for character.** The only concession is an omission shown as `…` inside the Verbatim itself, and the verifier inspects every omission: it may skip a footnote number or ordinary words, never a hedge or a negation. Prose quoting an entry may not add an omission the entry did not make.
- **Cite the primary source when one can be read.** A secondary source may round, paraphrase or drop a caveat; if only reporting can be read, the entry names the reporting and says so.
- **The Claim field states what the Verbatim supports and no more.** It is a label for the quotation, not a reading of it. Readings belong in prose, labelled as inference.
- **Record what weakens it** — a vendor surveying behaviour its product addresses, a single platform standing in for a labour market, a result significant at 10% and not 5%, a lower bound, a different unit from the figure it will be read beside.
- **Figures with different units, bases or constructs are not compared as if they shared one.** Say what each counts.
- **Scope, stated honestly:** every figure, research finding, survey result and statement of law in the conventions, the skills' shipped files and the specs has an entry here, as of the sweep recorded above. Practitioner heuristics — interviewer personas, company archetypes, question stems — are the skills' own priors, presented as priors, and are not cited. The ledger records this repository's history and cites where it states an outside finding. A claim without an entry reads as an inference or is removed. CI catches a quotation that strays from its entry and a paraphrase in quotation marks; a paraphrase without them it cannot see, so this scope is kept by review as well as by CI.
- **Every quotation in an entry is the source's words.** Verbatim holds what prose may quote; a Weakens field may quote the source too, and the verifier reads every quotation in the entry. This suite's own earlier wording, recorded as history, is set in italics, not quotation marks.
- **Re-verify rather than re-remember.** The suite's citation verifier, which lives in its source repository and ships with no skill, refetches every source and reports each entry as verified, not found, malformed, or unreachable. It needs the network, so it runs by hand rather than in CI, and unreachable is reported as unchecked, never as a pass.

---

## C1

- **Claim:** After an AI writing tool arrived, cover-letter tailoring was less correlated with callbacks and with offers.
- **Verbatim:** "The correlation between cover-letter tailoring and receiving a callback fell by 51% after the launch of the AI tool, and the correlation with receiving an offer fell by 79%."
- **Source:** Cui, J., Dias, G. & Ye, J. (2025, v2), *Signaling in the Age of AI: Evidence from Cover Letters*, Yale Department of Economics — https://arxiv.org/pdf/2509.25054v2
- **Weakens it:** One platform (Freelancer.com): international workers, short-term and mostly remote jobs, two skill categories (PHP and Internet Marketing), eight months. Relative changes: the tailoring coefficient is 0.0485 before the tool, so a 51% fall is about 0.025 in absolute terms. The paper's callback is being interviewed. Generalising to hiring at large is an inference.
- **Retrieved:** 2026-09-26

## C2

- **Claim:** Over the same period, the correlation between callbacks and workers' review scores rose.
- **Verbatim:** "The correlation between callbacks and workers’ review scores—the platform’s proprietary metric summarizing past work experiences on the platform and determining the default ranking of applications—rose by 5%."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Weakens it:** The same estimate as C22, worded for the abstract: the paper's callback is being interviewed, and its bid score is this review score, which also sets the default ordering — so the rise mixes employer judgment with platform ordering. It is at the interview stage; for hiring decisions the authors find no corresponding increase (C22). A relative change on a larger base than C1's; the 5% and the 51% are not on one scale and should not be set against each other.
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

- **Claim:** The callback effect is significant only at the 10% level and faded within two months, and the effect on awards is too imprecise to conclude from.
- **Verbatim:** "However, the results for callbacks are significant at the 10% level but not at the 5% level. A dynamic effect specification shows that the effect on callbacks tapered off after two months." and "In contrast, the estimates on actual awards are too imprecise to draw definitive conclusions."
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

- **Claim:** Most AI-assisted letters were submitted within a minute of generating the draft, and weaker prior writers concentrated there.
- **Verbatim:** "The majority of AI-assisted cover letters appear to be submitted with little or no modification: over 75% were finalized within one minute of clicking the tool." and "Workers below the median in pre-AI writing ability show a pronounced concentration of editing times between 0 and 1 minute, suggesting they often accept the AI output with minimal changes, whereas those above the median spread their editing effort over longer durations."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Retrieved:** 2026-09-26

## C10

- **Claim:** In their discussion the authors decline a causal reading of the association between editing time and hiring; their introduction words the same result causally.
- **Verbatim:** "these results should not be interpreted as evidence of a causal relationship: the decision to spend more time editing a cover letter is unlikely to be random … and may correlate with unobserved bid characteristics that employers find appealing." and "human revision enhances the effectiveness of AI-generated cover letters"
- **Source:** Cui, Dias & Ye (2025), as C1. The `…` stands for a page number the PDF's text places mid-sentence; no words are omitted.
- **Weakens it:** The paper says both; this suite follows the discussion's refusal, and says the introduction reads otherwise.
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

- **Claim:** The same source reports that citizenship-status discrimination is prohibited, and advises employers to avoid citizenship-only language in job ads except when legally required.
- **Verbatim:** "Discrimination based on citizenship status is expressly prohibited by the Immigration and Nationality Act's anti-discrimination provision, 8 U.S.C. § 1324b." and "except when legally required, we would encourage employers to avoid such language as"
- **Source:** Mayer Brown (2022), as C14. The second span introduces a list that begins "Must be a US citizen".
- **Weakens it:** Who is protected is limited — see C16.
- **Retrieved:** 2026-09-26

## C16

- **Claim:** The same source reports that, per DOJ guidance, nonimmigrant visa holders are not among the classes protected from citizenship-status discrimination.
- **Verbatim:** "According to DOJ guidance, while nonimmigrant visa holders and recipients of Deferred Action for Childhood Arrivals (DACA) are protected from national origin discrimination, they are not considered to be among the classes protected from citizenship status (alienage) discrimination."
- **Source:** Mayer Brown (2022), as C14.
- **Weakens it:** As C14. Guidance as reported by a law firm in 2022. The same source says the protected classes have "historically" been stated as US citizens and nationals, certain lawful permanent residents, asylees and refugees, that employers still may not use the "temporary nature" of a work authorization to discriminate, and that the area is "rapidly evolving". It concerns nonimmigrant visa holders and DACA recipients only.
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
- **Weakens it:** Disclosed to a newspaper; method not stated. The 1% is of résumés processed in the first half of the year, not of the 300 million. Overlaps with C20 rather than matching it: C20's prompt injections include white text, and C19's white text need not be an injection. Different platforms and periods.
- **Retrieved:** 2026-09-26

## C20

- **Claim:** An academic–industry study estimates hidden prompt injections in about 1% of résumés, as a lower bound.
- **Verbatim:** "approximately 1% of resumes contain hidden prompt injections" and "This estimate should be interpreted as a conservative lower bound, so the true prevalence might be even higher."
- **Source:** Zhang, M., Jia, Y., Tan, Z., Jiang, S., Gong, N. Z., Chen, T. & Song, D. (2026), *Measuring Real-World Prompt Injection Attacks in LLM-based Resume Screening* — https://arxiv.org/html/2605.28999v1
- **Weakens it:** A co-author is at hireEZ and the résumés are hireEZ's. The authors call their 1% a lower bound. Counts hidden text by any hiding method, mostly keywords rather than instructions — it overlaps with C19's white text rather than being a different construct. The authors also report prevalence rising over the past one to two years, on the same data.
- **Retrieved:** 2026-09-26

## C21

- **Claim:** The authors say employers shifted toward other signals.
- **Verbatim:** "In response, employers shifted toward alternative signals, including workers’ prior work histories." and "Instead, employers shifted toward other signals less susceptible to AI influence, such as workers’ past work experience."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Weakens it:** The shift the paper measures is at the interview stage; for hiring decisions it finds no corresponding increase (C22). The authors word the mechanism tentatively elsewhere: the change "may have prompted employers to fall back on reputation-based signals".
- **Retrieved:** 2026-09-26

## C22

- **Claim:** The authors call the rise in the bid score's predictive power for interviews substantial, and find no corresponding increase for hiring decisions.
- **Verbatim:** "We find that, following the rollout of the AI tool, the predictive power of bid score rank percentile for interviews increases substantially." and "By contrast, we detect no corresponding increase in the predictive power of rank percentile for ultimate hiring decisions."
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Weakens it:** The same roughly 5% estimate as C2: an interview is the paper's callback, and the bid score is the review score. Interviews only.
- **Retrieved:** 2026-09-26

## C23

- **Claim:** Language models choosing between two versions of a résumé's summary section — one human-written, one they generated — picked their own far more often, with content quality controlled; the authors give 67–82% for their larger models, as a gap between two selection probabilities.
- **Verbatim:** "The bias against human-written resumes is particularly substantial, with self-preference bias ranging from 67% to 82% across major commercial and open-source models." and "Larger models—such as GPT-4o, GPT-4-turbo, DeepSeek-V3, Qwen-2.5-72B, and LLaMA-3.3-70B—exhibit the strongest LLM-vs-Human self-preference, with magnitudes ranging from 67% to 82%." and "In contrast, smaller models display weaker biases" and "To evaluate equal opportunity, we assess whether self-preference persists when resumes are of equivalent quality" and "Prefers Self - Prefers Human" and "the evaluator LLM is prompted to compare two executive summaries and select the stronger one based on the overall presentation of skills and experience, following a standardized, job-agnostic evaluation instruction"
- **Source:** Xu, J., Li, G. & Jiang, J. Y. (2025; v4 revised 2026-06-06), *AI Self-preferencing in Algorithmic Hiring: Empirical Evidence and Insights* — https://arxiv.org/pdf/2509.00462v4
- **Weakens it:** Evaluators saw only the executive summary — the one section the model rewrote — under a job-agnostic instruction, not a whole résumé against a job. The figure is a gap in percentage points (prefers-self minus prefers-human, from the paper's equal-opportunity metric; its unconditional metric ranges 26–98%), not a share of comparisons and not a ratio. GPT-4o-mini, not in the authors' "larger" list, sits inside the range at 67.9%. The models tested will age. A preprint. This suite first called the range a share of comparisons, then glossed it as *how much more often* and quoted the other metric's definition; both were wrong.
- **Retrieved:** 2026-09-26

## C24

- **Claim:** In simulated hiring pipelines, the same authors estimate that candidates using the evaluator's own model are more likely to be shortlisted.
- **Verbatim:** "These simulations show that candidates using the same LLM as the evaluator are 23% to 60% more likely to be shortlisted than equally qualified applicants submitting human-written resumes"
- **Source:** Xu, Li & Jiang (2025), as C23.
- **Weakens it:** Simulated pipelines, not observed hiring: pools of five candidates, each present in both a human-written and an evaluator-written version, competing for four slots. The figure is a gap in percentage points between the two versions' shares of the shortlist (AI% minus Human% in the paper's figures), which the authors word as "more likely"; it is not a relative change. This entry first said the opposite.
- **Retrieved:** 2026-09-26

## C25

- **Claim:** In a vendor's interviews with 25 US recruiters, two had content-based auto-rejection configured.
- **Verbatim:** "AI/content auto-rejection configured: 8% of recruiters." and "We only saw 2 of 25 using it."
- **Source:** Vasileva, D. (2025, updated 2026), *Does the ATS Reject Your Resume? 25 Recruiters Explain What Really Happens*, Enhancv — https://enhancv.com/blog/does-ats-reject-resumes/
- **Weakens it:** Enhancv sells a résumé builder. Twenty-five recruiters: the page gives 8% as "± 6 at 90% confidence" and says the findings are themes "rather than nationally representative statistics". Counts recruiters, not applications. Interviews, not configurations inspected. Internally inconsistent: the two auto-rejecting recruiters are said to use Bullhorn and BambooHR, while a recruiter on a third system is also said to auto-reject on a score threshold. Updated since publication.
- **Retrieved:** 2026-09-26

## C26

- **Claim:** The same source describes knockout questions as eligibility checks a team can set to reject without review, and as almost all of the automated filtering its recruiters use.
- **Verbatim:** "Knockouts are yes/no eligibility checks (work authorization, required license, location). Teams can route failures to a human—or flip a setting to route them straight to reject." and "When automated filters are used, they’re almost always knockout questions"
- **Source:** as C25.
- **Weakens it:** As C25.
- **Retrieved:** 2026-09-26

## C27

- **Claim:** The same source says teams use match scores to order review, and that a low score lowers a résumé rather than rejecting it.
- **Verbatim:** "Many teams use match scores/filters to prioritize who gets reviewed first." and "Low score ≠ auto-reject, but in high-volume roles, it can push you to the bottom of the pile." and "56% either ignore the feature or don’t have it available."
- **Source:** as C25.
- **Weakens it:** As C25. The same page's coded figures are less than "many": 44% of the 25 said their system has an AI or fit score, and the rest ignore it or lack it. It speaks of match scores, not keywords; that keywords drive them is an inference. In a high-volume role the bottom of the pile may never be read, so *not rejected* is not *seen*.
- **Retrieved:** 2026-09-26

## C28

- **Claim:** Language models answering questions over long inputs often did best when the relevant information sat at the start or the end.
- **Verbatim:** "In particular, we observe that performance is often highest when relevant information occurs at the beginning or end of the input context, and significantly degrades when models must access relevant information in the middle of long contexts, even for explicitly long-context models."
- **Source:** Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F. & Liang, P. (2023, v3), *Lost in the Middle: How Language Models Use Long Contexts* — https://arxiv.org/abs/2307.03172v3
- **Weakens it:** Multi-document question answering and key-value retrieval over long contexts, with 2023 models. A résumé is short and screening is neither task, so carrying the finding to résumé screening is an inference.
- **Retrieved:** 2026-09-26

## C29

- **Claim:** US EEOC guidance: pre-employment questions relating to race, color, sex, national origin, religion or age are not clearly forbidden by law, but may be evidence of intent to discriminate unless justified by a business purpose, and should generally be avoided.
- **Verbatim:** "Although state and federal equal opportunity laws do not clearly forbid employers from making pre-employment inquiries that relate to, or disproportionately screen out members based on race, color, sex, national origin, religion, or age, such inquiries may be used as evidence of an employer's intent to discriminate unless the questions asked can be justified by some business purpose." and "which may indicate the applicant's race, sex, national origin, disability status, age, religion, color or ancestry if answered, should generally be avoided."
- **Source:** U.S. Equal Employment Opportunity Commission, *Prohibited Employment Policies/Practices* — https://www.eeoc.gov/prohibited-employment-policiespractices
- **Weakens it:** US federal guidance, which says state laws also do not clearly forbid these inquiries; the law firm behind C14 notes that some jurisdictions' laws go further. Covers the traits it names, disability status among them; medical questions and citizenship are C30, C32 and C33. Guidance, not statute. Not legal advice.
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
- **Weakens it:** An association; this suite follows the authors' refusal of the causal reading (C10) despite "increases" here. Small in percentage points and not small against the base: a standard deviation of editing (3.5 minutes) goes with about 0.31 percentage points on a 0.6% win rate — about half the base, as the authors put it — and 0.64 points, about 9%, on a 6.8% callback rate. Only AI-assisted bids with under 60 minutes of editing, measured as the minutes between opening the tool and submitting.
- **Retrieved:** 2026-09-26

## C32

- **Claim:** US EEOC guidance: most employers should not ask whether an applicant is a US citizen before making a job offer.
- **Verbatim:** "Most employers should not ask whether or not a job applicant is a United States citizen before making an offer of employment."
- **Source:** U.S. Equal Employment Opportunity Commission, *Pre-Employment Inquiries and Citizenship* — https://www.eeoc.gov/pre-employment-inquiries-and-citizenship
- **Weakens it:** US federal guidance, and "most" employers — the page goes on to the verification every employer must do after hiring. It does not bar the work-authorization and sponsorship questions of C14. Not legal advice.
- **Retrieved:** 2026-09-26

## C33

- **Claim:** US EEOC guidance: an employer may not ask an applicant medical questions before a job offer.
- **Verbatim:** "An employer also may not ask a job applicant to answer medical questions or take a medical exam before making a job offer."
- **Source:** U.S. Equal Employment Opportunity Commission, *Pre-Employment Inquiries and Medical Questions & Examinations* — https://www.eeoc.gov/pre-employment-inquiries-and-medical-questions-examinations
- **Weakens it:** US federal law (the ADA), for employers it covers. Not legal advice.
- **Retrieved:** 2026-09-26

## C34

- **Claim:** US EEOC guidance: questions about marital status and children may violate Title VII if used to deny or limit employment.
- **Verbatim:** "Questions about marital status and number and ages of children are frequently used to discriminate against women and may violate Title VII if used to deny or limit employment opportunities." and "It is clearly discriminatory to ask such questions only of women and not men (or vice-versa)."
- **Source:** U.S. Equal Employment Opportunity Commission, *Pre-Employment Inquiries and Marital Status or Number of Children* — https://www.eeoc.gov/pre-employment-inquiries-and-marital-status-or-number-children
- **Weakens it:** "May violate … if used to": asked of both sexes, the question is evidence of intent rather than itself a violation; the same page calls asking it of one sex only "clearly discriminatory". US federal guidance. Not legal advice.
- **Retrieved:** 2026-09-26

## C35

- **Claim:** One candidate told a newspaper that a recruiter who found his hidden prompt turned him down for it.
- **Verbatim:** "One recruiter discovered the prompt hacking and turned him down because of it, he told the NYT."
- **Source:** Entrepreneur (2025-10-08), as C18.
- **Weakens it:** One anecdote, second-hand through two publications. The same article reports candidates for whom the tactic appeared to work. It says nothing about consequences beyond that application.
- **Retrieved:** 2026-09-26

## C36

- **Claim:** The study's design, its date and funding, and the authors' remark on AI-detection tools.
- **Verbatim:** "We use a difference-in-differences design comparing workers with and without access." and "On April 19, 2023, Freelancer.com launched the AI Bid Writer." and "This work was supported by funding from the Cowles Foundation for Research in Economics at Yale University." and "Current detection tools are error-prone and unreliable"
- **Source:** Cui, Dias & Ye (2025), as C1.
- **Weakens it:** The remark on detection tools is the authors citing another paper (Weber-Wulff et al., 2023), not a finding of their own.
- **Retrieved:** 2026-09-26
