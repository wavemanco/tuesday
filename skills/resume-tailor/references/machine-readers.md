# The machine readers

A resume is read twice before a person forms an opinion of it: once by a parser
turning a document into text, and once — increasingly — by a language model
summarizing that text and handing a recruiter a fit score with a rationale. The
two fail differently and only one of them is about words.

This file exists because the folklore around this is dense, often wrong, and
expensive to believe. What follows is what the cited evidence supports, which is
often one small study, and each says so.

## What actually screens a resume

- **Content-based auto-rejection is rarer than the folklore says.** A résumé-builder vendor interviewed 25 US recruiters and reports "AI/content auto-rejection configured: 8% of recruiters" (cite C25) — two people, counted as recruiters rather than applications. The image of software silently binning every resume for missing a keyword quota does not match what those recruiters describe, though a sample that small cannot say how rare it is.
- **What can reject without a person is knockout questions** — "yes/no eligibility checks (work authorization, required license, location)", which a team can "flip a setting to route them straight to reject" (cite C26). They are answered in the application form, not the resume, and nothing this skill writes changes them. Where a knockout looks likely to fail, that is job-underwriter's hard gate, and the candidate should know before they invest in tailoring.
- **Keywords matter for ranking, not gating.** In the same interviews, "Many teams use match scores/filters to prioritize who gets reviewed first", and "Low score ≠ auto-reject, but in high-volume roles, it can push you to the bottom of the pile" (cite C27). So the position is neither "stuff them" nor "ignore them": place truthful keywords where the evidence already supports them, so the candidate is *findable*, and never invent one.
- **Parsing failure is real, mechanical, and silent.** It is the failure mode worth actual attention, because it destroys the evidence before any reader sees it.
- **Position is a lever that adds nothing to a claim.** Language models answering questions over long inputs have been measured doing best when "relevant information occurs at the beginning or end of the input context" (cite C28). A resume is short and screening is not that task, so whether it carries over is an inference; a reader who stops early has in any case read what came first. Ordering is `reorder`, which the ledger already permits.

One thing worth saying plainly to a candidate who asks why this skill will not
optimize harder: what helps an LLM summarize someone correctly — explicit scope,
named ownership, unambiguous outcomes, the strongest evidence early — is what the
truthfulness core already requires. This is the rare case where the honest move
and the effective move are the same move.

## The parse-safety check

Run over the current resume, reported as risks. **This skill reports; it does not
redesign.** A finding says what breaks and what it costs, and stops there.

| Check | What breaks | What it costs |
|---|---|---|
| Multi-column layout | Parsers read linearly and serialize columns as row-1-col-1, row-1-col-2 | Text interleaves into word salad; dates detach from the roles they belong to |
| Tables and text boxes | Cell contents are re-ordered or dropped | Whole sections can vanish silently |
| Images, icons, skill-level bars | Rendered as garbage characters, or the line is skipped | The information in them is simply absent |
| Content in headers or footers | Treated as page furniture and discarded | Contact details are the usual casualty — the candidate becomes unreachable |
| Non-standard section headings | Section detection looks for conventional labels | "My Journey" may not be recognized as Experience |
| Unusual file type | Varies by parser | Worth one line: a `.docx` or a text-layer PDF is the safe pair |

Two disciplines keep this honest. **Report what is observable.** Where the resume
arrived as pasted text rather than a file, say which checks could not be run
rather than guessing at layout. And **never dress a design preference as a parsing
finding** — "this would look better in one column" is not a parse risk, and a
skill that smuggles taste in under a technical justification has started doing the
thing this whole suite exists to avoid.

## The hidden-text refusal

Instructions aimed at an automated screener — white text on white, near-zero font
size, text in document metadata, an invisible block of keywords — are refused.

This is not a fringe request. In a hiring-software vendor's survey of 1,200 US
job seekers, "41% admit to using prompt injections, hidden text designed to
bypass AI filters" (cite C17), and of the rest, "52% say they are considering it"
(cite C17). How often it turns up in résumés is a separate question with less
settled answers: one platform disclosed white text in 1% of the résumés it
processed over half a year (cite C19); an academic–industry study found prompt
injections in about 1% and calls that a lower bound (cite C20); a staffing firm
reports hidden text in about 10% of those it scans with AI (cite C18).

Those figures count different things — people who say they have ever used it,
and résumés found to contain it, measured different ways — so they are not a
gap between saying and doing, and they are not ranked here by reliability. What
they support is only this: a candidate asking for hidden text is not being
exotic, and has probably been told it works.

Refuse it, and give the reason rather than a bare decline:

- **It is deception aimed at a machine acting for the employer**, which is deception of the employer. The distinction candidates draw here — "I'm not lying to a person" — does not survive being said out loud in an interview.
- **It is looked for.** One hiring platform reports how often it finds white text (cite C19), and a staffing firm reports what its AI scanning turns up (cite C18); neither could give a rate without searching. Whether detection is growing is something these sources do not measure, so it is not claimed here.
- **The downside is not a rejected application.** It is a candidate who cannot be considered anywhere in that organisation again, over a line they did not write themselves and could not defend.
- **It contradicts the premise of everything else here.** This skill's entire product is that the candidate can defend every line. A line hidden from them is the exact opposite, and shipping one would make the rest of the ledger meaningless.

Offer the legitimate version instead, because there usually is one and the request
usually comes from a real fear: run the parse-safety check so their real content
survives extraction, place truthful keywords where the evidence supports them, and
put the strongest traceable evidence where position rewards it.

**The mirror image is a service.** A candidate's resume may already contain hidden
text they did not author — from a template, a previous tool, or a service they
paid. Where a file can be inspected, flag it: they are carrying a liability they
cannot see. Where it cannot be inspected, say that this check could not run.

## One dynamic, disclosed rather than exploited

In one controlled experiment, language models choosing between two resumes
preferred the one they had generated over a human-written one: "The bias against
human-written resumes is particularly substantial, with self-preference bias
ranging from 67% to 82% across major commercial and open-source models" (cite
C23). That range is the larger models', and "The difference between these
probabilities provides a direct measure of self-preference bias" (cite C23) — how
much more often a model picks its own resume, not the share of comparisons it
decides. In simulated pipelines the same authors estimate that "candidates using
the same LLM as the evaluator are 23% to 60% more likely to be shortlisted than
equally qualified applicants submitting human-written resumes" (cite C24). This
file once described that range as a share of comparisons, and the model's own
output as its "model family"; both were wrong.

This skill does not optimize for that, and could not do so honestly: the lever is
"sound more like a machine wrote you", which is the opposite of keeping the
candidate's own defensible sentences. Where the candidate's own phrasing already
works, the traceability rule keeps it — which is the right outcome for reasons
that have nothing to do with this finding.

It is written down because a candidate who learns of it elsewhere deserves to know
the choice was deliberate rather than an oversight, and because the finding may
not survive the next generation of screening models. It is a finding about the
models tested, not a principle.
