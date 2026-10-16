# Job Underwriter + Evidence Recovery Skill
## Full Specification and Build Plan

## 1. Product Definition

### Name
**Job Underwriter + Evidence Recovery**

### One-line purpose
Help a job seeker evaluate a specific opportunity, recover overlooked but truthful evidence from their history, identify genuine capability gaps and role red flags, and produce an approved, evidence-backed application plan.

### What it is
A portable AI skill that runs inside an agent client. It takes a job description (JD), a CV/resume, and optional additional context. It returns a structured **Job Underwriting Dossier** and optionally renders it as an ephemeral, editable review document.

### What it is not
- Not an auto-apply bot.
- Not a generic ATS keyword scorer.
- Not a system that fabricates experience, metrics, credentials, or outcomes.
- Not a single black-box fit score.
- Not initially a standalone web product, browser extension, CRM, or custom MCP server.

### Primary user promise
> Do not treat a missing CV bullet as proof that I cannot do the work. Help me distinguish omitted evidence, adjacent experience, real gaps, and bad opportunities—and let me validate every claim before it affects my application.

## 2. Design Principles

1. **Evidence before language.** A polished phrase is not evidence. Every material conclusion must trace to a source or be marked as inference.
2. **Missing is not absent.** A missing CV claim may be a presentation gap, a discovery gap, a genuine capability gap, or a hard eligibility failure.
3. **Ask adaptively.** Do not front-load an interview. Ask the smallest number of high-information questions that could change the assessment.
4. **Memory is a lead, not proof.** If optional agent memory suggests relevant experience, ask the user to confirm and specify it before treating it as evidence.
5. **User controls assertions.** The user must approve factual claims, CV bullets, portfolio language, and externally visible materials.
6. **Separate applicant fit from opportunity quality.** A candidate can be qualified for a poorly scoped, misleading, under-resourced, or unacceptable role.
7. **Explain uncertainty.** Use confidence bands and reasons, not false precision.
8. **No averaging away hard problems.** Hard-gate failures and severe red flags remain visible regardless of positive fit elsewhere.
9. **Source provenance is first-class.** The skill records where every claim came from: CV, user-confirmed voice answer, uploaded document, link, memory lead, or inference.
10. **Progressive disclosure.** Provide a concise decision first; allow the user to inspect the detailed evidence map and logic.

## 3. Inputs

### Required
- **Job description:** pasted text, uploaded document, accessible URL, or extracted job-page text.
- **CV/resume:** uploaded document or pasted text.

### Optional evidence inputs
- Portfolio URL or case studies.
- GitHub repository links or code samples.
- LinkedIn/profile export.
- Prior resumes.
- Performance reviews, role descriptions, recommendations, reference notes.
- Product requirements documents, launch briefs, architecture diagrams, presentations, writing, certificates, anonymized metrics, or work samples.
- Company/recruiter/interview notes.
- Job-page URL, employer URL, or hiring-manager URL where access is available.

### Optional personal inputs
- Compensation expectations.
- Location, work authorization, remote/hybrid, schedule, travel, security clearance, or other eligibility constraints.
- Desired role type: IC/manager/executive, company stage, industry, risk profile, mission, work-style preferences.
- Stage: evaluating, applying, recruiter screen, interview loop, offer stage.
- Preferred response mode: text, voice, attachments, links.

### Optional memory input
The agent may retrieve user-approved persistent memory only for relevant leads. Memory-derived information must be marked `memory_lead` until the user validates it.

## 4. Output: Job Underwriting Dossier

The skill emits both:

1. A concise, human-readable Markdown report.
2. A structured JSON-compatible artifact for rendering, persistence, and re-analysis.

### Required sections in the readable report

1. **Decision snapshot**
   - `go`, `conditional_go`, `hold_pending_answers`, or `no_go`.
   - Brief rationale.
   - Explicit hard gates and severe red flags.

2. **Role reality**
   - Stated responsibilities.
   - Inferred first-year outcomes.
   - Scope, seniority, authority, dependencies, and unknowns.

3. **Requirement-by-requirement evidence map**
   - Priority, candidate claim, evidence, confidence, fit status, and next action.

4. **Gap recovery queue**
   - Only the 1–3 highest-value unresolved gaps for the next interaction.
   - Each includes tailored recall examples, suggested evidence types, and response options.

5. **Opportunity risk register**
   - Unknowns, risk signals, red flags, severity, quoted source language, and verification question.

6. **Application plan**
   - Truthful CV changes contingent on approved evidence.
   - Portfolio or work-sample suggestion.
   - Interview questions.
   - Research or outreach actions.

7. **Evidence status**
   - Verified facts, unverified leads, rejected inferences, and evidence needed.

## 5. Core Reasoning Workflow

### Step A: Intake and normalization

1. Extract text from all supplied documents and permitted links.
2. Identify document type, source, date if available, and reliability.
3. Detect contradictory claims across sources; do not silently resolve them.
4. Ask only minimal orientation questions at first:
   - What stage are you at?
   - Any non-negotiables or hard constraints?
   - Do you have additional material you want considered?
   - Do you prefer voice or text for gap follow-ups?

### Step B: Build the role profile

Extract and normalize:
- Job title, organization, location, employment type.
- Stated responsibilities.
- Must-have, preferred, and implied requirements.
- Hard gates: terms the candidate meets or does not — authorization, license, location, clearance, schedule, pay, travel, credentials, legal constraints. A length-of-experience requirement is `must_have`, not a gate, unless the posting ties it to a legal or credential bar (the rule is `skills/job-underwriter/references/evidence-model.md`, "A gate is met, not established, or failed").
- Expected outcomes in the first 90 days and first year, if stated or carefully inferred.
- Scope signals: team size, ownership, budget, decision rights, reporting line, customer/problem domain, company stage.
- JD unknowns, contradictions, risk signals, and red flags.

Do not infer requirements merely because a related buzzword appears. Mark uncertain inferences as `inferred` and state why.

### Step C: Build the candidate evidence inventory

For each source, extract only claims that can be attributed to the user or clearly identified as self-description. Store:
- Claim.
- Source quote or reference.
- Source type.
- Project/role.
- Time period, if known.
- Candidate’s stated ownership.
- Scope: team, users, revenue, technical complexity, budget, stakeholders, decision rights.
- Outcome or metric.
- Verifiability.

### Step D: Map requirements to evidence

For every material requirement, create:

```yaml
requirement: "..."
priority: hard_gate | must_have | important | preferred
requirement_source:
  type: jd_quote | inferred
  text: "..."
fit_status: direct | adjacent | unclear | absent | hard_gate_fail
candidate_claim: "..."
evidence:
  - source_type: cv | attachment | link | user_confirmed_voice | user_confirmed_text | memory_lead | inference
    reference: "..."
    quote_or_summary: "..."
verified: true | false
confidence: high | medium | low | none
reasoning: "..."
gap_type: none | presentation | discovery | transferability | capability | hard_gate
next_action: "..."
```

### Step E: Classify gaps

Use this taxonomy:

| Gap type | Definition | Appropriate next action |
|---|---|---|
| Presentation gap | Relevant verified evidence exists, but the CV does not communicate it clearly or in JD-relevant terms | Propose an approved, truthful repositioning or CV edit |
| Discovery gap | Evidence may exist but the current inputs are inconclusive | Ask targeted question; suggest exact documents/links/artifacts |
| Transferability gap | No direct match, but there is credible adjacent work | Explain transferable case and its limitation; recommend a work sample or positioning approach |
| Capability gap | No credible direct or adjacent evidence | Suggest realistic closure path, or mark as material risk |
| Hard-gate gap | Required eligibility/credential/constraint is not met | Surface clearly; do not imply wording can solve it |

### Step F: Select the next-best questions

Rank questions with this heuristic:

```text
priority = requirement_importance
         × uncertainty
         × expected_evidence_recovery_probability
         × decision_impact
         ÷ user_effort
```

Operational rules:
- Ask at most 3 questions in one turn.
- Prefer questions that can change `go` / `conditional_go` / `no_go`.
- Do not ask for details already supplied.
- Offer voice, text, attachment, link, and skip options.
- Give tailored examples of work that may count.
- If a user says the experience is confidential, permit a high-level description and mark verifiability appropriately.

### Step G: Update evidence and recommendations

When the user replies by voice, text, attachment, or link:
1. Extract candidate claims.
2. Identify missing specifics: ownership, scope, stakeholder set, timeframe, result, artifact.
3. Present an evidence confirmation card.
4. Only after user confirmation, upgrade evidence confidence or draft CV language.
5. Re-run only the affected requirement mappings and dependent recommendations.

## 6. Adaptive Discovery Prompt Template

Every important unresolved requirement should use this structure:

```text
Requirement: [exact JD requirement or concise paraphrase]
Importance: [must-have / important / preferred]

What I currently see:
[what the CV and existing evidence do or do not establish]

Why this matters:
[how it affects eligibility, role success, or application strategy]

Experience that may count:
- [JD-specific example 1]
- [JD-specific example 2]
- [JD-specific example 3]

Useful evidence to attach or link:
- [specific document/artifact examples]

Question:
[one focused question]

Respond using: [Speak] [Type] [Attach] [Add link] [Skip]
```

### Example: cross-functional leadership

```text
Requirement: Lead cross-functional delivery across product, engineering, design, and go-to-market.
Importance: Must-have.

What I currently see:
Your CV establishes product-building work, but not which functions or stakeholders you coordinated, your decision authority, or launch ownership.

Experience that may count:
- Taking a product, feature, experiment, or client project from idea to release.
- Coordinating an engineer, designer, contractor, customer, partner, or marketing effort.
- Setting priorities or resolving a product, business, or technical trade-off.
- Running a feedback cycle that changed what shipped.

Useful evidence to attach or link:
A launch plan, roadmap, Notion project board, portfolio write-up, GitHub repo, product brief, analytics screenshot, or a short voice walkthrough.

Question:
Is there a project where you personally coordinated two or more stakeholders to get something shipped? What did you own, who was involved, and what happened?
```

### Example: production AI/LLM requirement

```text
Requirement: Production experience with LLM applications, including evaluation and monitoring.
Importance: Must-have.

What I currently see:
Your CV mentions AI-related work, but does not establish deployment to real users, model/workflow ownership, evaluation, monitoring, or measurable outcomes.

Experience that may count:
- Designing prompts, agent workflows, RAG systems, evaluations, or guardrails.
- Selecting models and managing quality, latency, reliability, or cost trade-offs.
- Running pilots, collecting user feedback, measuring outputs, or handling failure modes.
- Shipping a prototype, internal tool, client system, or production feature.

Useful evidence to attach or link:
A repo, README, architecture diagram, evaluation sheet, prompt/test set, demo, product spec, launch note, or a voice explanation of the system.

Question:
Which parts of an AI system have you personally owned, did it reach users beyond a private prototype, and how did you evaluate whether it worked?
```

## 7. Red-Flag and Opportunity-Risk Logic

The skill must independently assess the opportunity, not just candidate alignment.

### Signal classes

| Class | Meaning | Output action |
|---|---|---|
| Unknown | Material information is missing without evidence of harm | Ask a verification question |
| Risk signal | Wording or structure plausibly indicates a problem | Add to risk register; investigate |
| Red flag | Terms or structure appear materially unreasonable, misleading, incompatible, or unacceptable to the user | Highlight prominently; may force `no_go` |
| Positive signal | Clear outcomes, authority, resources, transparency, or realistic scope | Increase opportunity confidence |

### Detectable examples
- Responsibility without authority, resources, or dependencies.
- Multiple specialized roles bundled into one low-level title.
- Unrealistic experience/seniority combinations.
- Explicit always-on/unpaid availability expectations.
- Incoherent, contradictory, or obviously copied JD language.
- Evasive or contradictory compensation/employment terms.
- Role success metrics absent from an otherwise highly demanding mandate.
- Perpetually open role or process inconsistencies, when available from user-provided evidence.

### Red-flag record

```yaml
signal: "Responsibility-authority mismatch"
severity: low | medium | high
source_quote: "Own revenue growth across ..."
hypothesis: "Candidate may be accountable without decision rights or resources."
verification_question: "Which revenue levers does this role directly control, and what people, budget, and authority are committed?"
decision_rule: "Proceed only if authority and resources are concrete and consistent across interviewers."
status: unresolved | reduced | confirmed
```

## 8. User Confirmation and Truthfulness Policy

### Never do these
- Add unverified claims to a CV, cover letter, outreach note, or work sample.
- Convert memory fragments into asserted experience.
- Inflate a prototype into production experience.
- Equate participation with leadership.
- Invent metrics, team sizes, customer counts, revenue, dates, credentials, or titles.
- Hide hard-gate failures or severe red flags in an aggregate score.

### Required approvals
Obtain explicit user approval before:
- Exporting a CV revision.
- Generating final externally shared application material.
- Saving a claim as verified persistent evidence.
- Using private links/documents beyond the requested analysis.

### Confidence guide

| Confidence | Meaning |
|---|---|
| High | Specific, user-confirmed claim supported by a CV, artifact, link, or direct document evidence |
| Medium | User-confirmed specific claim with plausible detail but limited inspectable proof |
| Low | Vague claim, indirect context, partial evidence, or unconfirmed memory lead |
| None | No supporting evidence or direct contradiction |

## 9. Ephemeral Human-Review UI Contract

The skill must work without UI. When a host supports ephemeral artifacts, render the output as a temporary interactive review document.

### UI purpose
Enable the user to inspect, correct, enrich, and approve the analysis. The UI is not the core reasoning engine.

### Required views
1. **Decision snapshot:** go / conditional-go / hold / no-go; hard gates and severe flags.
2. **Requirements table:** JD requirement, priority, evidence, confidence, gap type, action.
3. **Evidence cards:** source provenance, extracted claim, user correction/approval controls.
4. **Gap queue:** adaptive questions with `Speak`, `Type`, `Attach`, `Add link`, `Skip`.
5. **Risk register:** quote, hypothesis, severity, interview verification questions.
6. **Proposed edits:** CV/portfolio language with `Accept`, `Edit`, `Reject`.

### Voice flow

```text
User selects Speak on a gap card
  → record/transcribe according to host capability
  → extract potential claim, role, ownership, scope, outcome, and artifact
  → display confirmation card
  → user confirms/edits/rejects
  → evidence map updates
```

## 10. Structured Output Schema (v0.1)

```json
{
  "analysis_id": "string",
  "stage": "evaluating|applying|interviewing|offer",
  "decision": {
    "status": "go|conditional_go|hold_pending_answers|no_go",
    "summary": "string",
    "hard_gates": [],
    "severe_red_flags": []
  },
  "role_profile": {
    "title": "string",
    "company": "string|null",
    "responsibilities": [],
    "requirements": [],
    "inferred_outcomes": [],
    "unknowns": []
  },
  "candidate_constraints": {
    "status": "known|unknown",
    "items": []
  },
  "evidence_map": [
    {
      "requirement_id": "string",
      "priority": "hard_gate|must_have|important|preferred",
      "requirement": "string",
      "fit_status": "direct|adjacent|unclear|absent|hard_gate_fail",
      "candidate_claim": "string|null",
      "evidence": [],
      "confidence": "high|medium|low|none",
      "gap_type": "none|presentation|discovery|transferability|capability|hard_gate",
      "reasoning": "string",
      "next_action": "string"
    }
  ],
  "gap_queue": [],
  "risk_register": [],
  "application_plan": {
    "resume_edits_pending_approval": [],
    "portfolio_or_work_sample": [],
    "interview_questions": [],
    "research_actions": []
  },
  "evidence_state": {
    "verified": [],
    "unverified_leads": [],
    "rejected_inferences": []
  }
}
```

## 11. Implementation Plan

### Phase 0: Choose a host

Use one skill-capable agent host first. Do not optimize for cross-platform support before the workflow has been validated.

The chosen host needs:
- File upload or pasted text.
- Long enough context for a JD and CV.
- Optional voice/transcription support, or the ability to accept a pasted transcript.
- Optional artifact/ephemeral UI capability.
- Ability to run a skill with structured output instructions.

### Phase 1: Build the text-only skill

Create the first version as a `SKILL.md` with:
- The product definition and principles above.
- Input contract.
- Full reasoning workflow.
- Gap taxonomy.
- Output schema.
- Truthfulness rules.
- Three worked examples.

Do not build persistence, browser automation, custom tools, or visual UI in this phase.

**Acceptance test:** Given a JD and CV, the skill creates a requirement-by-requirement evidence map, identifies at least one unknown versus one genuine gap where appropriate, and asks no more than three high-value follow-up questions.

### Phase 2: Run three real-case evaluations

Test on three roles:
1. A direct-fit role.
2. An adjacent/pivot role.
3. A role with a suspicious or poor opportunity profile.

For each test, record:
- Requirements the skill missed.
- Incorrect inference or unsupported claim risks.
- Questions that felt generic or low-value.
- Recall prompts that elicited useful overlooked evidence.
- Whether the final recommendation was useful.
- Whether an approved CV edit was truly stronger and still accurate.

Revise the rubric, examples, and stop/go decision rules based on observed failure modes.

### Phase 3: Add evidence recovery interaction

Add explicit response modes for each gap card:
- Voice.
- Typed answer.
- Upload document.
- Add link.
- Skip / mark absent.

**Acceptance test:** A user can answer a gap by voice, review extracted facts, correct them, and cause only the related requirements to update.

### Phase 4: Add ephemeral review UI

Render the structured output as an interactive artifact.

Keep the logic in the skill and the UI thin. The UI must render the same JSON schema that the text report uses.

**Acceptance test:** A user can inspect a requirement, see the exact evidence source, correct an inference, approve a CV change, and see an updated decision without losing the audit trail.

### Phase 5: Add optional persistence and MCP adapters

Only after repeated use demonstrates value, add persistence for:
- User-approved evidence library.
- Role dossiers.
- Interview answers.
- Application outcomes.
- Calibration metrics.

Prefer existing document/GitHub/search/storage connectors. Build a custom MCP only if stable cross-client functions are needed, such as:

```text
save_role_analysis()
get_role_history()
save_verified_evidence()
update_risk_status()
log_application_outcome()
get_calibration_metrics()
```

### Phase 6: Add a plugin only if needed

A browser extension is a late-stage convenience layer:

```text
Job page → extract visible JD → invoke skill → open review artifact
```

Build it only if copying/pasting job descriptions is proven to be a meaningful recurring friction.

## 12. Evaluation Metrics

Do not optimize for a generic fit score. Track outcomes by role family and seniority.

### Workflow quality
- Percentage of material requirements mapped to explicit evidence.
- Percentage of proposed CV edits approved by the user.
- Unsupported-claim rate found during user review.
- Number of questions required before decision stabilizes.
- User-rated usefulness of questions and recall prompts.

### Candidate decision quality
- Recruiter-response rate.
- Screen-to-interview conversion.
- Final-round or offer rate per qualified application.
- Time invested per interview generated.
- Calibration: predicted fit band versus actual advancement rate.
- Regret rate: jobs pursued that later prove unacceptable, and strong roles incorrectly rejected.

### Safety quality
- Hard-gate failures never hidden in aggregate fit.
- No unapproved external-facing claims.
- Memory leads always confirmed before use as evidence.
- Every material claim traceable to a source.

## 13. Worked Example: Expected Behavior

### Situation
JD requires production LLM product ownership, cross-functional delivery, and fintech domain knowledge. The CV mentions AI projects and product building but does not state production deployment, launch scope, or fintech roles.

### Correct first-pass output
- Production LLM: `discovery_gap`, not automatically absent.
- Cross-functional delivery: `discovery_gap` or `presentation_gap`, depending on available CV evidence.
- Fintech: `transferability_gap` if there is relevant financial tooling, payment, analytics, or regulated-data work; otherwise `capability_gap`.
- Ask no more than three questions, prioritizing must-haves.

### Correct prompt behavior
The skill offers examples such as an internal tool, client system, user pilot, repository, architecture diagram, evaluation spreadsheet, product launch, payment workflow, or financial analysis project. It asks what the user owned and what artifact can substantiate it.

### Incorrect behavior
- “You have 85% fit.”
- “Add ‘production LLM’ to your CV.”
- “Your investing interest counts as fintech experience.”
- Treating a memory fragment as verified proof.
- Asking 20 broad career-history questions before providing a first-pass assessment.

## 14. Prompt for a Skill-Creator Agent

Copy the following into the skill-creator agent along with this specification:

```text
Create a portable AI skill named “Job Underwriter + Evidence Recovery.”

Use the attached specification as the source of truth. Produce a complete skill package centered on a SKILL.md file. The skill must work in a text-only agent environment first and emit strict structured JSON plus a concise Markdown report. Treat any visual artifact as an optional renderer of that same structured output.

Non-negotiable requirements:
- Accept a JD and CV, plus optional attachments, URLs, agent memory leads, user constraints, and voice transcripts.
- Map every material JD requirement through claim → evidence → confidence.
- Distinguish presentation, discovery, transferability, capability, and hard-gate gaps.
- Ask only 1–3 adaptive, high-information follow-up questions at a time.
- For every discovery prompt, state the relevant JD requirement, what the CV currently establishes, examples of candidate experience that may count, examples of useful documents/links, and response modes.
- Treat memory as an unverified lead until the user confirms it.
- Never fabricate accomplishments or propose externally visible CV language without explicit user approval.
- Independently identify JD unknowns, role risks, and red flags.
- Keep applicant fit separate from opportunity quality.
- Never reduce the result to a single opaque numerical score.
- Provide a complete v0.1 JSON schema, worked examples, edge cases, and test cases.

Deliver:
1. SKILL.md
2. output-schema.json
3. examples/direct-fit.md
4. examples/adjacent-fit.md
5. examples/red-flag-role.md
6. tests/acceptance-tests.md
7. ui-contract.md for an optional ephemeral human-review artifact

Before finalizing, self-audit the package against the non-negotiable requirements and list any host-specific assumptions.
```

## 15. Definition of Done for v0.1

The first version is complete when it can, with only a JD and CV:

- Produce a traceable evidence map for all material requirements.
- Clearly differentiate unknown, risk, red flag, and positive role signals.
- Identify presentation versus genuine capability gaps.
- Ask targeted, example-rich discovery questions.
- Accept voice/text/attachment/link answers conceptually or in the host’s available modality.
- Generate only user-approved truthful CV changes.
- Return an actionable go/conditional-go/hold/no-go recommendation.
- Render the same underlying output in text and, where supported, an ephemeral review UI.
