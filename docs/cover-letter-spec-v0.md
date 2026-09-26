# cover-letter — spec v0

**Status: specification only.** No skill files exist. This document was written
before any, deliberately, because the one time this repository drafted a spec
from assumption and researched afterwards — `resume-tailor-spec-v0.md` §8 — the
first draft asserted things about screening that turned out to be folklore and
missed a refusal the skill needed.

The research came first this time, and it changed the design. §2 is the evidence;
§3 is the thesis that falls out of it. Reading §3 without §2 will make the
design look like a preference. It is not.

## 1. What it is for

A candidate has decided to apply and needs the letter that goes with the
application. job-underwriter decided *whether*; resume-tailor fixed the resume;
mock-interview rehearses what comes after. Nothing in the suite writes the
document that accompanies the submission, and it is the only one of the four that
is **generative** — a resume edit has a current line to trace against, and a
cover letter has a blank page.

That difference is the whole design problem, and it is why this skill is the
riskiest in the suite rather than the easiest.

## 2. The evidence

### 2.1 The finding that should drive the design

The strongest available evidence is Cui, Dias & Ye (2025), *Signaling in the Age
of AI: Evidence from Cover Letters* — Yale Department of Economics, funded by the
Cowles Foundation (cite C36). It studies a tool launched on one platform — "On
April 19, 2023, Freelancer.com launched the AI Bid Writer." (cite C36) — with
application-level data on both access to the tool and actual usage, and "a
difference-in-differences design comparing workers with and without access"
(cite C36). That observability is the point. The authors, citing other work, note that
"Current detection tools are error-prone and unreliable" (cite C36); this study
does not have to detect anything, because the platform knows.

What it found:

| Result | Number | Source |
|---|---|---|
| Access to the tool raised cover-letter tailoring | +0.16 SD | (cite C6) |
| Actual usage raised tailoring | +1.36 SD | (cite C6) |
| Access raised callback probability | +0.43 pp | (cite C4) |
| Usage raised callback probability | +3.56 pp, a 51% lift on a 7.02% baseline | (cite C4) |
| **Correlation between tailoring and callback, after the tool** | **fell 51%** | (cite C1) |
| **Correlation between tailoring and offer, after the tool** | **fell 79%** | (cite C1) |
| Correlation between callbacks and worker review scores (past work history) — interviews only; no corresponding rise for hiring | rose 5% | (cite C2) (cite C22) |
| Uptake | 62% of eligible workers used it at least once; 17% of all cover letters | (cite C8) |

Two caveats the authors state and this spec keeps: the callback effects are
significant at the 10% level but **not at 5%**, and the effect on callbacks
**tapered off after two months** (cite C5). On awards, "the estimates on actual
awards are too imprecise to draw definitive conclusions" (cite C5).

The structural finding is not the lift. It is the collapse. Tailoring — measured
as TF-IDF keyword overlap between the letter and the job post — used to predict
callbacks, and after a tool made that overlap cheap for everyone, its
correlation with callbacks fell by about half and with offers by about
four-fifths (cite C1). The authors say where employers went: "In response,
employers shifted toward alternative signals, including workers’ prior work
histories." (cite C21) That shift is in whom employers interviewed; for hiring
itself the authors find "no corresponding increase" (cite C22).

The authors also find AI **substitutes for** writing skill rather than
complementing it: workers who already wrote well gained half as much as the
weakest writers (cite C7). The gap narrows. They flag the distributional consequence
plainly, and hedged: "This shift may have important implications, including
favoring established workers at the expense of newcomers trying to enter the
market." (cite C3)

### 2.2 The finding about editing

The paper's fifth question is whether people revise the drafts and whether it
matters. Most do not: "over 75% were finalized within one minute of clicking the
tool" (cite C9), and below-median writers show a pronounced concentration of
editing times **between 0 and 1 minute**, accepting the output nearly as-is,
while above-median writers spread effort over longer durations (cite C9). Time spent
editing goes with better outcomes *within* a worker, "controlling for worker fixed
effects" (cite C31): for offers "The coefficient on editing time is positive and
highly significant" (cite C31), and for callbacks "likewise" (cite C31).

**In their discussion the authors decline the causal reading**, and so does this
spec: "these results should not be interpreted as evidence of a causal
relationship: the decision to spend more time editing a cover letter is unlikely
to be random … and may correlate with unobserved bid characteristics that
employers find appealing." (cite C10) Their introduction words the same result
causally — "human revision enhances the effectiveness of AI-generated cover
letters" (cite C10) — and this spec follows the discussion. The effects are also
small in absolute terms (cite C31). A candidate who edits for ten minutes may
simply be a candidate who cared, and caring is not something the editing caused.

It is still the most design-relevant correlation available, for a reason that
does not depend on causality: **a tool that hands over a finished letter produces
zero-minute edits.** That is a fact about the tool's shape, not about the
candidate.

### 2.3 The pre-AI benchmark, and why it is weaker

ResumeGo ran a field experiment from 15 July 2019 to 10 January 2020, submitting
7,287 fictitious applications to openings on job boards such as ZipRecruiter,
Glassdoor and Indeed (cite C12), in three groups — no letter, a generic letter, a
tailored letter (cite C13). Tailored letters drew a **53% higher callback rate**
than no letter (cite C11).

Two limits, both material. It predates generative AI entirely, and §2.1 is
precisely a finding that the value of tailoring changed afterwards. And it is a
resume-writing company's study of whether resume-writing matters — the incentive
runs one way, the write-up states no limitations of its own, and it has not been
peer reviewed. Useful as a pre-AI anchor; not a basis for a claim about now.

### 2.4 The survey layer, which is the weakest tier

The widely cited figures on how many recruiters read cover letters, prefer them,
or expect them come almost entirely from resume-tool and AI-writing-tool content
marketing — the two listed under Sources — and those vendors sell the product the
statistic recommends. None has an entry in `citations.md`, so none is quoted
here, and nothing in this spec relies on one. An earlier draft quoted three of
them as figures.

Treat this tier as `[generic]` at best. The reading this spec takes from it is an
inference, not a finding: **the person who screens a letter first may not be the
person who decides on the interview**, and the second may read more closely. Row
7 of §4 rests on it, and is justified on grounds that hold either way.

## 3. The design thesis

**Do not optimise the letter for alignment with the job post.**

That is the thing generative AI made free, and §2.1 measures what happened to its
predictive power when it became free: down 51% for callbacks, 79% for offers
(cite C1).
Writing a skill that maximises keyword overlap with the posting would be building,
carefully and with good guardrails, the exact artifact the market has already
learned to discount.

**Optimise instead for what no model could produce from the posting alone** —
the specific, verifiable, candidate-owned content: what they did, at what scope,
with what outcome, and how they know. Employers moved toward harder-to-fake
signals in choosing whom to interview (cite C21), though not measurably in whom
they hired (cite C22); the only such signal a letter can carry is a fact about the
candidate that is true and checkable.

This is the same rare alignment resume-tailor's spec noted, and it is stronger
here: **the honest move and the effective move are the same move.** The suite's
one rule — nothing a skill writes may outrun the evidence it stands on — is not a
constraint bolted onto this skill against its interests. It is, per the best
available evidence, the strategy.

Three consequences follow, and they are what makes this a different product from
the market norm.

**The letter is assembled from claims, not generated as prose.** Every paragraph
traces to something the candidate said, wrote, or confirmed. The blank page is
the danger: with no current line to diff against, the reframing audit has nothing
to compare, so the claim inventory has to be built explicitly before any sentence
is drafted.

**The skill must not produce a zero-minute artifact.** §2.2 says most people
accept AI drafts nearly untouched, and that the ones who engage do better. A
skill that hands over a finished letter and a copy button is optimising for the
behaviour associated with the worse outcome. Approval-gated, claim-by-claim
delivery — the pattern resume-tailor's edit ledger already uses — is the
structural answer, and it is the reason to reuse that shape rather than invent a
new one.

**Where the candidate has no evidence for what the role wants, the letter says
less, not more.** A shorter honest letter beats a longer one built on adjectives.
This is the resume-tailor rule with the stakes raised, because a letter is where
the temptation to narrate past the evidence is strongest.

## 4. The owed output (*n*)

Delivered complete in the first response, from whatever inputs exist. Never
questions-only — the suite's standalone invariant binds here as everywhere.

| # | Section | Condition | Contents |
|---|---|---|---|
| 1 | **Claim inventory** | Always | Every claim the candidate's own material supports, each with the sentence or answer it came from. The pool every drafted line must draw on; nothing outside it may enter the letter |
| 2 | **What the posting asks for** | Always | The employer's stated priorities, separated into what the claim inventory can meet and what it cannot. Never a keyword list |
| 3 | **The letter, paragraph by paragraph** | Always | Each paragraph a row: the drafted text, the claims it rests on, the provenance label, and its approval status. Nothing is "applied" until approved |
| 4 | **What I did not write** | Always | The prohibited-claims list: what the posting invited that the evidence could not support, and what was declined. Inherited from a dossier where one exists |
| 5 | **The opening problem** | Always | The first line is where fabrication and cliché both live. Named as its own section because it is the most-rewritten sentence in the document and the one most likely to assert enthusiasm as fact |
| 6 | **Length and what was cut** | Always | What was left out and why — since §3 says the honest letter is often the shorter one, the cuts are part of the product rather than an apology for it |
| 7 | **Where this letter is weak** | Always | The paragraphs a sceptical reader would push on, and what evidence would strengthen each. This is the section that makes the letter defensible rather than merely deliverable |
| 8 | **Upgrade menu** | Always | Each missing input and what adding it would unlock |

Two things ride the delivery and are never pushed: emitting or updating
`tuesday-dossier.md`, and naming the sibling skill where a request spans one.

**§4's row 7 comes from §2.4, and does not depend on it.** If the inference there
holds, the first-pass screener may not read the letter at all, while the person
deciding on the interview reads it and will be in the room later — so a letter
optimised to survive a skim is optimised for the reader least likely to read it.
If it does not hold, naming where the letter is weak is still what makes it
defensible rather than merely deliverable, which is row 7's own reason.

## 5. The rules that bind it

### 5.1 The standalone invariant

The first response delivers a complete letter, built on stated assumptions, with
whatever questions ride alongside it. A correction or a refusal is never a gate —
resume-tailor's Step 1 rule applies verbatim, including the failure shape it
names: refusing well, explaining well, and then closing on *"want me to go ahead
on that basis?"* has delivered nothing.

### 5.2 Every paragraph traces

No sentence enters the letter that does not rest on a claim in the inventory.
`conventions/reframing-audit.md` governs every clause — six axes, five
disciplines — and the relationship axis matters more here than anywhere, because
a letter is written in the candidate's voice and will be read as their own words.

The generative case needs no new rule. The audit's baseline is the candidate's
own sentences, not an earlier version of the line, so a paragraph with no
predecessor is audited against the claim-inventory entries it rests on — each of
which quotes the candidate. resume-tailor already does this for a summary row
whose current line is empty. An earlier draft of this spec called the missing
original an unhandled case and a blocker for implementation; it had misread the
audit, which `reframing-audit.md` now says in a sentence.

### 5.3 Two modes, and the draft is not evidence

The skill runs from a blank page **or** from a draft the candidate already has,
and neither is the primary case. Someone with no letter yet and someone polishing
a third revision are both ordinary, and a skill that serves only the first tells
the second to throw away their work.

What separates the modes is not difficulty, it is what the audit has to compare
against — and the reason is worth stating because it is easy to get backwards.
In resume-tailor the current line usually does two jobs at once: it is the text
being edited *and* the evidence the edit traces to — though not always, since a
summary row with no current line traces to a sentence the candidate wrote
elsewhere. That overlap is why that skill's ledger works so cleanly.

They come apart here, in **both** modes. **A draft cover letter is not evidence.**
It is a text the candidate wrote about themselves, and it may already assert what
their record does not support — "I led the migration" over a resume that says
"supported the migration." Tracing a proposed line to the draft would launder
that claim into the ledger with a source cell that looks satisfied.

So the claim inventory is the original in both modes, and the draft is a third
thing: a starting text and a register sample.

That makes draft mode **safer** than blank-page mode rather than merely
equivalent, because it can do something blank-page cannot — diff the draft
against the inventory and report the lines the candidate has already written that
their own evidence will not carry. That is a delivered section in draft mode, not
a footnote: *what your draft claims that your record does not show* is often the
most valuable thing this skill can tell someone, and they cannot get it from a
tool that only adds.

Two disciplines keep it honest. A draft sentence that survives the audit is kept
in the candidate's own words — rewriting what already works is churn dressed as
work, and it wastes the one thing draft mode has that blank-page does not. And a
draft sentence that fails the audit is shown with what failed and what would fix
it, never silently replaced, because a candidate who does not learn that "led"
outran their evidence will write it again next time.

### 5.4 Enthusiasm is not a claim

"I have long admired your work in X" is either grounded in something the
candidate can point to or it is a fabrication about their own mental state,
written by a model, in their name. It is the single most common sentence in the
genre and the suite has no vocabulary for it yet: it is not a claim about the
world, so rule 6 does not catch it, and it traces to nothing, so §5.2 does.

Treat it as ungrounded unless the candidate supplies the grounding. Where they
do — they used the product, read the paper, met someone at a conference — it
becomes the strongest line in the letter, because it is the one thing no model
could have produced from the posting.

### 5.5 Never disclose what the candidate did not ask to disclose

A cover letter is free-form, which makes it the easiest place in an application
to volunteer information the reader has no need of. Visa or citizenship status,
health, caring responsibilities, age markers, pregnancy, religion, and salary
expectations are never introduced by this skill.

**This is a design choice about who controls disclosure, not a legal
requirement, and this section is not legal advice.** Its account of the law has
gone wrong twice, and neither time where the first draft did. The first draft said
US guidance advises employers not to ask about citizenship at application stage,
and cited nothing. The first correction answered it with evidence about *work
authorization* — a different question the source keeps separate — and called the
draft backwards. The second then called the draft unsupported by any source here.
Federal guidance says almost what the draft said: "Most employers should not ask
whether or not a job applicant is a United States citizen before making an offer
of employment." (cite C32) The draft was right and uncited; the corrections were
the errors. The rest is from one law firm's 2022 report, US federal law only.

Employers may ask about work authorization and sponsorship: "Are you legally
authorized to work in the United States?" (cite C14) and "Will you now or in the
future require sponsorship for employment visa status (e.g., H-1B visa status)?"
(cite C14). Those concern authorization, not citizenship. On citizenship the
source reports that "Discrimination based on citizenship status is expressly
prohibited by the Immigration and Nationality Act's anti-discrimination
provision, 8 U.S.C. § 1324b." (cite C15) — and that the protection has limits: "According to DOJ guidance, while nonimmigrant visa holders and recipients of Deferred Action for Childhood Arrivals (DACA) are protected from national origin discrimination, they are not considered to be among the classes protected from citizenship status (alienage) discrimination." (cite C16)

So the rule does not rest on what the employer may ask, and it does not rest on
the law protecting the candidate — for nonimmigrant visa holders and DACA
recipients, citizenship-status protection does not apply, per DOJ guidance as
reported in 2022 (cite C16), and the area is still moving. It rests on the
candidate controlling their own disclosure. A candidate can answer
the two authorization questions whenever they are asked; a letter volunteering a
nationality, a visa type or a timeline hands over more than those questions reach,
unprompted. The rule holds in every jurisdiction for that reason, and the US
detail above is context, not its justification.

Where the candidate raises one themselves — a visa timeline they have decided to
be upfront about — the skill supports the decision they have already made, states
plainly that it is optional, and never widens it.

### 5.6 No hidden text, and no counterfeit voice

resume-tailor's hidden-text refusal carries over unchanged. The letter-specific
addition: no imitation of a writing sample's quirks to make the letter read as
hand-written, and no instruction to the candidate on how to make it look
un-AI-assisted. Matching the candidate's genuine register from their own writing
is legitimate; manufacturing evidence of authorship is not.

## 6. Inputs and degradation

| Input | Tier | If missing |
|---|---|---|
| Target job posting | Gate | Nothing to write toward — say so and ask |
| Resume, CV, or background prose | Gate | No claim inventory is possible; say so and ask |
| `tuesday-dossier.md` | Enhancer | Claims and prohibitions are re-derived rather than inherited; a letter built without one is still complete |
| An existing draft of this letter | Mode selector | Blank-page mode: the letter is built from the claim inventory alone. Neither mode is primary |
| The candidate's own writing (any sample) | Enhancer, high-leverage | Register is inferred from their intake prose and the letter says so |
| A specific reason for this employer | Enhancer, highest-leverage | §5.4 applies: the letter carries no admiration line at all rather than an invented one, and the upgrade menu names what one real detail would add |
| Named recipient | Enhancer | Standard salutation; never "Dear Hiring Manager" apologised for |
| Application-form constraints (length, prompts) | Structural-lite | Assume one page and say so |

## 7. Open questions this spec cannot settle

Recorded rather than guessed, because guessing is what §2 exists to prevent.

- **The no-original case is not open.** An earlier draft listed it here as a blocker needing a canonical amendment; §5.2 says why that misread the audit.
- **A fourth skill re-opens routing for all four.** This is measured, not theoretical: adding resume-tailor moved mock-interview from 2/12 to 7/12 on its own reserved phrasings with no change to its description. A cover-letter skill ships with its own positives, its own near-miss negatives — a thank-you note, a LinkedIn summary, a personal statement — and a re-run of the whole set. Budget for the other three's numbers moving.
- **Overlap with resume-tailor is real and unresolved.** Both take a posting plus a resume and produce approval-gated prose from a claim inventory. Whether this is a fourth skill or a mode of resume-tailor is a genuine design question, and the honest answer is that the suite has no usage data to decide it. The case for separation is that the generative problem is different in kind; the case against is two skills with one intake and a shared shape competing for the same request.
- **`n + x` requires a spec, and this is it.** Unlike mock-interview, this skill would ship with §4 written first.

## 8. Evals

Five fixtures, each carrying the trap the research identifies:

1. **The strong-fit application.** Genuine overlap; the temptation is to narrate past it. Asserts every paragraph traces and no scope widens.
2. **The thin-evidence application.** The posting wants what the candidate cannot show. Asserts the letter gets *shorter*, that the gap is named, and that no adjective substitutes for the missing claim.
3. **The admiration trap.** The candidate supplies no reason for this employer and the posting is full of mission language. Asserts §5.4 — no invented enthusiasm, and the upgrade menu names what one real detail would unlock.
4. **The disclosure trap.** The candidate mentions a visa timeline in passing while asking for the letter. Asserts §5.5 — not volunteered, the choice named as theirs, not widened.
5. **The dossier-driven run.** `prohibited_claims` present and binding, `evidence_map` consumed rather than re-derived, and the letter still complete if the dossier is absent.

Every fixture asserts the standalone invariant, the per-paragraph trace and
provenance columns, output-discipline rules 1–6, and — specific to this skill —
that the delivered artifact is not a finished letter with nothing for the
candidate to do.

## Sources

Rigorous:

- Cui, J., Dias, G. & Ye, J. (2025), *Signaling in the Age of AI: Evidence from Cover Letters*, Yale Department of Economics / Cowles Foundation — [arxiv.org/abs/2509.25054](https://arxiv.org/abs/2509.25054)

Field experiment, pre-AI, self-interested source:

- ResumeGo, *Cover Letters: Just How Important Are They?* (2019–20, n=7,287) — [resumego.net/research/cover-letters](https://www.resumego.net/research/cover-letters/)

Legal guidance on application-stage disclosure:

- Mayer Brown, *Unlawful US Hiring Questions about Visa Status and Citizenship* — [mayerbrown.com](https://www.mayerbrown.com/en/insights/publications/2022/07/unlawful-us-hiring-questions-about-visa-status-and-citizenship-are-your-policies-in-compliance-a-2022-primer-with-tips-on-avoiding-discriminatory-practices)
- Workplace Fairness, *Immigration Status* — [workplacefairness.org/immigration-status](https://www.workplacefairness.org/immigration-status/)

Survey tier — vendor content marketing, `[generic]` at best, listed so the
weakness is inspectable rather than hidden:

- Resume Genius, *Cover Letter Statistics* — [resumegenius.com](https://resumegenius.com/blog/cover-letter-help/cover-letter-statistics)
- Novoresume, *67 Cover Letter Statistics and Trends for 2026* — [novoresume.com](https://novoresume.com/career-blog/cover-letter-statistics)
