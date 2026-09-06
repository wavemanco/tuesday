# The machine readers

A resume is read twice before a person forms an opinion of it: once by a parser
turning a document into text, and once — increasingly — by a language model
summarizing that text and handing a recruiter a fit score with a rationale. The
two fail differently and only one of them is about words.

This file exists because the folklore around this is dense, mostly wrong, and
expensive to believe. What follows is what the evidence supports.

## What actually screens a resume

- **Content-based auto-rejection is largely myth.** A small minority of recruiters enable it; the overwhelming majority of applications are ranked and surfaced for human review. The image of software silently binning a resume for missing a keyword quota does not match how these pipelines are configured.
- **What does auto-reject is knockout questions** — work authorization, a required licence, a hard minimum on years — answered in the application form, not the resume. Nothing this skill writes changes them. Where a knockout looks likely to fail, that is job-underwriter's hard gate, and the candidate should know before they invest in tailoring.
- **Keywords matter for retrieval and ranking, not gating.** Recruiters search the pile; an LLM layer ranks what surfaces. So the position is neither "stuff them" nor "ignore them": place truthful keywords where the evidence already supports them, so the candidate is *findable*, and never invent one.
- **Parsing failure is real, mechanical, and silent.** It is the failure mode worth actual attention, because it destroys the evidence before any reader sees it.
- **The LLM layer weights position.** Primacy and recency effects are well documented: what sits first and last carries more. That makes ordering a genuine lever — and ordering is `reorder`, which the ledger already permits and which adds nothing to a claim.

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

This is not a fringe request. One 2025 survey found 41% of job seekers admitted to
using hidden text or prompt injection to get past AI filters, with over half the
remainder considering it; a large staffing firm reports finding hidden text in
around 10% of the resumes it scans. A candidate asking for this is not being
exotic. They have probably been told it works.

Refuse it, and give the reason rather than a bare decline:

- **It is deception aimed at a machine acting for the employer**, which is deception of the employer. The distinction candidates draw here — "I'm not lying to a person" — does not survive being said out loud in an interview.
- **It is increasingly detected, and specifically looked for.** Detection is now a product category. The trend line runs against the technique.
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

LLM screeners rate resumes written by their own model family more favourably —
self-preference in the region of two-thirds to four-fifths of comparisons, worth a
materially higher chance of being shortlisted, independent of the candidate's
actual qualifications.

This skill does not optimize for that, and could not do so honestly: the lever is
"sound more like a machine wrote you", which is the opposite of keeping the
candidate's own defensible sentences. Where the candidate's own phrasing already
works, the traceability rule keeps it — which is the right outcome for reasons
that have nothing to do with this finding.

It is written down because a candidate who learns of it elsewhere deserves to know
the choice was deliberate rather than an oversight, and because the finding may
not survive the next generation of screening models. It is a fact about today's
tools, not a principle.
