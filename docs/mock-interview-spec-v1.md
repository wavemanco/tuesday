# mock-interview — spec v1

**Status: written after the fact.** mock-interview shipped first and shipped
without a spec. This document is a description of the skill as built, not a
contract it was built against, and it is versioned v1 rather than v0 to keep that
honest — v0 would imply it came first.

Writing it is not archaeology for its own sake. The skill's own `n + x` rule opens
*"the sections this skill's spec defines are n"*, which has been referring to a
document that did not exist since the day it was written. A rule whose subject is
missing cannot be checked, and this session found a defect that lived exactly in
that blind spot: Step 1 licensed a turn that delivered clarifying questions and no
pack, contradicting the repository's one rule, and it survived three rounds of
grading because there was nothing to check the skill against. The point of writing
this down is that the next such contradiction is visible on paper.

## 1. What it is for

A candidate has an interview coming. They need to walk in knowing which questions
are likely, why each one is being asked, what their own material offers as an
answer, and where they are weakest.

The market norm for this is a list of questions. A list is nearly useless: the
candidate rehearses answers to the questions that appear and freezes on the
follow-up, because they learned answers rather than why the question exists.

This skill builds a pack organised on two axes that a list does not have.
**Personas** describe how the interview will feel — who is asking, in what style.
**Question types** describe what is being scored. Every question carries answer
guidance grounded in the candidate's real material *and* a rationale explaining
both its inclusion and its categorisation, so a candidate who disagrees with a
call can disagree intelligently.

Its credibility rests on one discipline: everything in the pack is traceable to a
provided document, traceable to research, or explicitly labeled generic. A
fabricated specific — an invented interviewer fact, a made-up round — burns the
candidate live, which is worse than no pack.

## 2. The owed output (*n*)

This section is what the `n + x` rule has been pointing at. Delivered complete in
the first response, from whatever inputs exist.

| # | Section | Condition | Contents |
|---|---|---|---|
| 1 | **Fit snapshot** | Always | JD requirement × the candidate's evidence, quoted verbatim × gap-and-bridge language. With a dossier, the underwriter's `evidence_map` supplies the grading and its evidence quotes supply the cells |
| 2 | **Interviewer read** | Only with real interviewer information | Career pattern, self-described style, what lands with them and why |
| 3 | **Persona weights** | Always | Relationship priors adjusted by interviewer signals and company archetype, reasoning shown |
| 4 | **Question banks** | Always | Per persona, under the rubric's coverage rules. Roughly 18–26 questions, depth following persona weight |
| 5 | **Values cheat sheet** | Only when a values-style round is detected | Each published value mapped to a specific candidate story — or, where research could not establish the values, the omission stated and the bank labeled generic |
| 6 | **Reverse questions** | Always | With a "why it lands" for each; at least one tied to the interviewer's own path when a profile exists |
| 7 | **Delivery coaching** | Only when an assessment was provided | Never solicited; feeds from the assessment alone |
| 8 | **Graded-deliverable build** | Only when the recruiter pre-declared one | A POV, presentation or take-home gets its own build section — theses with mandatory concessions, differentiation strategy, the requested close |
| 9 | **Upgrade menu** | Always | Each missing input and what adding it would unlock |

Two offers ride the delivery and are never pushed: the live drill, and emitting or
updating `tuesday-dossier.md` with this pack's `pack_feedback`.

**Everything in this table is owed unconditionally where its condition holds.** A
turn that delivers questions instead is not a lighter version of this skill; it is
a different and worse product, and the rule that says so is §3.1.

## 3. The rules that bind it

### 3.1 The standalone invariant

The first response delivers a complete pack. Clarifying questions ride *with* it,
never before it. Whatever is missing, the pack is built on a stated assumption and
the questions are framed as what would restructure it.

This is the repository's one rule and it is stated here because its absence from a
spec is precisely how it was violated. The degradation ladder (§4) exists so a
pack can always be built; the elicitation policy exists so questions cost nothing
extra. Neither is a licence to wait.

The converse is also owed: delivering does not retire the questions. A pack
shipped with none attached has quietly decided its own assumptions are good
enough, which is the candidate's call.

### 3.2 Grounding

Company values, loop structure and current strategy come from research or provided
documents, never from model memory — these are the facts that drift. Where
research cannot run or comes back non-attributable, say so plainly, label the
affected sections `[generic]`, and never fill the gap from memory. A values bank
that names principles the research could not confirm is the single most damaging
thing this skill could produce, because the candidate will quote them.

### 3.3 The reframing audit

Every guidance cell is language the candidate will speak aloud, so
`conventions/reframing-audit.md` governs it — six axes, five disciplines, clause
by clause against the candidate's own sentences. This binding was added after the
audit became canonical; before that, mock-interview was the only skill in the
suite proposing language nobody audited.

The stakes are higher here than on a resume line: a written claim can be walked
back before an interview, a spoken one is already in the room.

### 3.4 Privacy and scope

Government ID in an upload is not used and not needed — say so and proceed.
Personality assessments are accepted if offered and never solicited. Interviewer
research covers public professional footprint only: roles, career pattern,
published talks and writing. Nothing personal, no contact-detail hunting.

## 4. Inputs and degradation

| Input | Tier | If missing |
|---|---|---|
| Round type + relationship to interviewer | Structural | Full-loop pack with flat persona weights — noticeably weaker; say so. Always worth the Step 1 question: cheap, un-researchable, reshapes the skeleton |
| Full JD text | Core | Research a representative JD for the title; label JD-derived questions `[inferred]`, or `[generic]` where research could not run |
| Candidate CV / background | Core | Fit snapshot becomes a self-assessment worksheet; guidance becomes story-*selection* scaffolds rather than story-mapped answers — as it does, CV or not, for any question none of the candidate's sentences carries |
| `tuesday-dossier.md` | Enhancer | Everything is derived rather than inherited; `prohibited_claims` must then be built locally (§6) |
| Interviewer identity / profile | Enhancer | Drop the interviewer read; personas fall back to round-type priors; reverse questions go role-generic |
| Company research | Enhancer | Generated by the research module at the consented tier — never asked for, made |
| Recruiter / HR guidance | Enhancer, high-leverage | Coverage assumed from round-type priors; no graded-deliverable section |
| Prep time available | Structural-lite | Default to the full pack |

## 5. Triggering

Owns interview preparation and rehearsal. Explicit non-goal in its description:
not for deciding whether to apply. With three skills shipped the boundary is a
three-way question, and `conventions/interaction-grammar.md` §6 records the
measured decision not to add further exclusions — there has never been a
cross-firing run to fix, and a more assertive description has measurable costs.

## 6. What writing this spec surfaced

The exercise was worth it for this section alone. Three gaps, none of them
defects, all of them things a spec makes visible. **All three are now closed** —
the descriptions below are kept as written, with what was done recorded against
each, because the value is in what writing a spec surfaced rather than in the
fixes.

**A pack built without a dossier has no prohibited-claims record.** With a dossier,
`prohibited_claims` arrives from the underwriter and binds every guidance cell.
Without one, nothing plays that role — yet the same temptations exist, and the
other two skills both maintain such a list locally. job-underwriter records what it
refused to write; resume-tailor makes it a delivered section. mock-interview should
carry its own, built from the fit snapshot's gaps: the claims a candidate might
reach for under pressure that their material does not support. **Now built**: section 13 of the output template, present in every pack rather than
only when a dossier supplies one, since a pack protected by luck is not protected.

**The drill scored against a rubric that did not exist.** Sharper than first
recorded: the skill body promised a score "against the pack's own rubric" and the
template defined a feedback format with neither rubric nor score. **Now resolved**
by naming what was already there — the question's own guidance cell is the rubric,
which is why the pack is written first and why a drill on generic guidance can only
give generic feedback. There is no numeric score, and the template now says why: a
number would average away the one beat they missed, which is the entire finding.

**Loop mode is the least exercised path in the suite.** Multiple scheduled rounds
with a shared fit snapshot and per-round mini-packs is a documented mode with no
fixture covering it. Five fixtures cover session mode; none covers loop. That is a
coverage gap rather than a defect, and it is the kind that stays invisible until
someone uses the feature. **Now covered** by eval 6: three scheduled rounds for one
role — hiring manager, peer panel, values round — asserting that shared sections
appear once and that persona weights genuinely differ per round rather than being
repeated three times.

## 7. Evals

Five fixtures, all session-mode: a first pack from JD and CV, a pack with an
uploaded interviewer profile, a values-round loop with no research available, a
dossier-driven pack that must honour `prohibited_claims`, and a spec-sync fixture
carrying a recruiter-declared POV deliverable with stated prep time.

Every fixture asserts §3.1 — that the first response delivers a complete pack in
the same message as any questions. That expectation was added after the defect it
describes was found in the clean room, and its absence is the single clearest
argument for why this document should have existed first.
