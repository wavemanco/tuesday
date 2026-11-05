# Worked dossier: the envelope

## Contents

- The envelope — its sections in order: `decision`, `role_profile`, `candidate_constraints`, `evidence_map`, `gap_queue`, `risk_register`, `application_plan`, `evidence_state`, `handoff_to_mock_interview`

The fenced JSON envelope of the worked `tuesday-dossier.md` whose report is `references/dossier-worked-report.md`. In the emitted file it follows the upgrade menu directly, as the file's last block, and every line of the report that an envelope field holds renders from it (`references/dossier-emission.md`). Field names follow `references/dossier-schema.md`, and the `evidence_map` rows are `references/evidence-model.md`'s row shape, serialized.

## The envelope

```json
{
  "dossier_version": "1.2",
  "generated_by": { "skill": "job-underwriter", "at": "2026-08-16" },
  "role": {
    "title": "Senior Programme Manager, Community Energy Fund",
    "company": "Penhallow Foundation",
    "stage": "evaluating"
  },
  "sections": {
    "decision": {
      "status": "conditional_go",
      "summary": "Fit as evidence_map reads it, with R4 (must_have, adjacent) carrying a credible bridge, its limit named; sound but under-specified opportunity (RR1 award authority and RR2 contract basis unverified; RR4 salary withheld). Conditions: RR1 and RR2 verify acceptably; retrofit bridge framed as adjacent, never as community-energy expertise.",
      "hard_gates": [],
      "severe_red_flags": []
    },
    "role_profile": {
      "title": "Senior Programme Manager, Community Energy Fund",
      "company": "Penhallow Foundation",
      "responsibilities": [
        "Lead the Community Energy Fund across its feasibility, capital, and community-ownership strands",
        "Open the capital-grants strand in year one",
        "Publish the fund's first impact report in year one"
      ],
      "requirements": [
        { "id": "R1", "text": "UK work eligibility without sponsorship", "priority": "hard_gate" },
        { "id": "R2", "text": "Grant programme management, open call to evaluation", "priority": "must_have" },
        { "id": "R3", "text": "Due diligence on capital projects", "priority": "must_have" },
        { "id": "R4", "text": "Community energy knowledge: generation, grid connection, share offers", "priority": "must_have" },
        { "id": "R5", "text": "Line-managing grants officers", "priority": "important" },
        { "id": "R6", "text": "Grants data: grant-management database, portfolio reporting", "priority": "important" },
        { "id": "R7", "text": "Social investment or repayable finance experience", "priority": "preferred" },
        { "id": "R8", "text": "A permanent contract, not fixed-term (the candidate's hard constraint)", "priority": "hard_gate" },
        { "id": "R9", "text": "A start date no earlier than February 2027 (the candidate's hard constraint)", "priority": "hard_gate" }
      ],
      "inferred_outcomes": [
        "Year-one success is judged on the capital strand opening and the first impact report [grounded - stated in JD]"
      ],
      "unknowns": [
        "Award authority versus the trustees' grants committee",
        "Contract basis",
        "Salary",
        "Ownership of the impact measures"
      ]
    },
    "candidate_constraints": {
      "status": "known",
      "items": [
        { "constraint": "Permanent contract only (no fixed-term post)", "kind": "hard", "source": "user_confirmed_text", "satisfied_by_role": "unknown" },
        { "constraint": "Start date no earlier than 1 February 2027", "kind": "hard", "source": "user_confirmed_text", "satisfied_by_role": "yes" },
        { "constraint": "UK work eligibility held (no sponsorship needed)", "kind": "hard", "source": "user_confirmed_text", "satisfied_by_role": "yes" }
      ]
    },
    "evidence_map": [
      {
        "requirement_id": "R1",
        "priority": "hard_gate",
        "requirement": "UK work eligibility without sponsorship",
        "requirement_source": { "type": "jd_quote", "text": "must have the right to work in the UK; we cannot sponsor" },
        "fit_status": "direct",
        "candidate_claim": "UK citizen; no sponsorship needed",
        "evidence": [
          { "source_type": "user_confirmed_text", "reference": "intake message", "quote_or_summary": "UK citizen" }
        ],
        "verified": true,
        "confidence": "high",
        "gap_type": "none",
        "reasoning": "Gate confirmed directly by the user; nothing to inspect and nothing contested.",
        "provenance": "[grounded] user-confirmed at intake",
        "next_action": "none"
      },
      {
        "requirement_id": "R2",
        "priority": "must_have",
        "requirement": "Grant programme management, open call to evaluation",
        "requirement_source": { "type": "jd_quote", "text": "you have run a grant programme from open call through to evaluation" },
        "fit_status": "direct",
        "candidate_claim": "Programme manager for a regional funder's environment grants, from open call to evaluation",
        "evidence": [
          { "source_type": "cv", "reference": "CV, Experience", "quote_or_summary": "Programme Manager, Environment Grants, 2022-2026" },
          { "source_type": "link", "reference": "end-of-programme report (fetched)", "quote_or_summary": "Names her as programme manager from the open call through the evaluation" }
        ],
        "verified": true,
        "confidence": "high",
        "gap_type": "none",
        "reasoning": "Specific, confirmed, and inspectable - CV plus a read artifact agree.",
        "provenance": "[grounded] CV plus a read artifact agree",
        "next_action": "none"
      },
      {
        "requirement_id": "R3",
        "priority": "must_have",
        "requirement": "Due diligence on capital projects",
        "requirement_source": { "type": "jd_quote", "text": "you have carried out due diligence on capital projects" },
        "fit_status": "direct",
        "candidate_claim": "Led due diligence on the regional funder's capital round",
        "evidence": [
          { "source_type": "user_confirmed_text", "reference": "recovery turn 1", "quote_or_summary": "Led due diligence for the capital round: the checklist, the site visits, and the finance review with the treasurer" }
        ],
        "verified": true,
        "confidence": "medium",
        "gap_type": "none",
        "reasoning": "Confirmed and specific, but no inspectable artifact yet - medium, with the caveat named where this claim is used: expect a probe.",
        "provenance": "[grounded] recovery-turn answer, specific",
        "next_action": "Offer stands: a sanitized due-diligence checklist or site-visit report raises this to high"
      },
      {
        "requirement_id": "R4",
        "priority": "must_have",
        "requirement": "Community energy knowledge: generation, grid connection, share offers",
        "requirement_source": { "type": "jd_quote", "text": "at home with community energy: generation schemes, grid connections and share offers" },
        "fit_status": "adjacent",
        "candidate_claim": "Assessed and funded retrofit projects on community buildings through the capital round",
        "evidence": [
          { "source_type": "user_confirmed_text", "reference": "recovery turn 1", "quote_or_summary": "Funded insulation and heat-pump retrofits on village halls across two capital rounds" }
        ],
        "verified": true,
        "confidence": "medium",
        "gap_type": "transferability",
        "reasoning": "Credible adjacency: the same technical scrutiny of contractors and costings. Limit: no exposure to community generation, grid connection, or share offers - named wherever the bridge is used.",
        "provenance": "[inferred] adjacency derived from the retrofit grants she described, not from a community-energy claim",
        "next_action": "Gap queue G1: probe for any generation, heat-network, or share-offer contact"
      },
      {
        "requirement_id": "R5",
        "priority": "important",
        "requirement": "Line-managing grants officers",
        "requirement_source": { "type": "jd_quote", "text": "you will line-manage the fund's grants officers" },
        "fit_status": "unclear",
        "candidate_claim": null,
        "evidence": [],
        "verified": false,
        "confidence": "low",
        "gap_type": "discovery",
        "reasoning": "CV silent; the one question asked was skipped. Per policy it is not re-asked; carried as a minor risk.",
        "provenance": "[grounded] CV silence; the question was skipped",
        "next_action": "none - user skipped; reopens only if the user volunteers"
      },
      {
        "requirement_id": "R6",
        "priority": "important",
        "requirement": "Grants data: grant-management database, portfolio reporting",
        "requirement_source": { "type": "jd_quote", "text": "confident with a grant-management database and portfolio reporting" },
        "fit_status": "direct",
        "candidate_claim": "Built the funder's portfolio-reporting workbook; uses the grants database daily",
        "evidence": [
          { "source_type": "cv", "reference": "CV, Tools", "quote_or_summary": "Grants database and Excel listed among tools" },
          { "source_type": "link", "reference": "end-of-programme report (fetched)", "quote_or_summary": "Portfolio-reporting workbook described with its reporting fields and a sample quarterly return" }
        ],
        "verified": true,
        "confidence": "high",
        "gap_type": "presentation",
        "reasoning": "The evidence is strong; the CV buries it in a tools list. The gap is in communication, not capability.",
        "provenance": "[grounded] linked end-of-programme report inspected",
        "next_action": "CV edit E1 pending approval"
      },
      {
        "requirement_id": "R7",
        "priority": "preferred",
        "requirement": "Social investment or repayable finance experience",
        "requirement_source": { "type": "jd_quote", "text": "bonus: you have worked with social investment or repayable finance" },
        "fit_status": "absent",
        "candidate_claim": null,
        "evidence": [],
        "verified": false,
        "confidence": "none",
        "gap_type": "capability",
        "reasoning": "No direct or adjacent evidence after discovery. Preferred-priority, so a minor risk, not a blocker.",
        "provenance": "[grounded] no direct or adjacent evidence found after discovery",
        "next_action": "Closure path if desired: the community-ownership strand's repayable grants are learnable on the job; a short course in community finance would pre-empt the objection"
      },
      {
        "requirement_id": "R8",
        "priority": "hard_gate",
        "requirement": "A permanent contract, not fixed-term (the candidate's hard constraint)",
        "requirement_source": { "type": "inferred", "text": "candidate_constraints: permanent contract only, kind hard" },
        "fit_status": "unclear",
        "candidate_claim": "Will not take a fixed-term post",
        "evidence": [
          { "source_type": "user_confirmed_text", "reference": "intake message", "quote_or_summary": "I'd only move for a permanent post" }
        ],
        "verified": true,
        "confidence": "high",
        "gap_type": "hard_gate",
        "reasoning": "Confidence grades the constraint, which is the user's own and confirmed. Fit is unclear because the posting does not state the contract basis; RR2 closes it.",
        "provenance": "[grounded] user-confirmed constraint; posting silent on contract basis",
        "next_action": "RR2's question, before investing in the loop"
      },
      {
        "requirement_id": "R9",
        "priority": "hard_gate",
        "requirement": "A start date no earlier than February 2027 (the candidate's hard constraint)",
        "requirement_source": { "type": "inferred", "text": "candidate_constraints: start date no earlier than 1 February 2027, kind hard" },
        "fit_status": "direct",
        "candidate_claim": "Cannot start before February 2027, on three months' notice",
        "evidence": [
          { "source_type": "user_confirmed_text", "reference": "intake message", "quote_or_summary": "I'm on three months' notice, so February at the earliest" }
        ],
        "verified": true,
        "confidence": "high",
        "gap_type": "none",
        "reasoning": "Confidence grades the constraint, which is the user's own and confirmed. Fit is direct because the JD's spring 2027 start meets it.",
        "provenance": "[grounded] JD and user-confirmed constraint",
        "next_action": "none"
      }
    ],
    "gap_queue": [
      {
        "requirement_id": "R4",
        "gap_type": "transferability",
        "provenance": "[inferred] bridge derived from the retrofit grants she described; [generic] that this is the likeliest interview objection",
        "prompt": {
          "what_i_currently_see": "Confirmed retrofit grants for community buildings; nothing touching community generation, grid connection, or share offers directly.",
          "why_this_matters": "R4 is a must_have row at adjacent; a stronger bridge narrows the likeliest interview objection.",
          "experience_that_may_count": [
            "An applicant's project that included solar panels or a heat network",
            "Work alongside a community-benefit society or its share offer",
            "A feasibility study you assessed that raised grid capacity"
          ],
          "useful_evidence": ["Sanitized assessment note", "Site-visit report", "Programme excerpt"],
          "question": "Have you touched community generation, grid connections, or share offers in any project - even peripherally?"
        },
        "response_modes": "Answer in text, paste a voice transcript, attach a document, drop a link, or say skip."
      }
    ],
    "risk_register": [
      {
        "signal": "Authority over awards asserted, not evidenced",
        "class": "unknown",
        "severity": null,
        "source_quote": "lead the fund across its three strands",
        "hypothesis": "Role may carry the fund's outcomes while award decisions sit with the trustees' grants committee.",
        "provenance": "[inferred] from the JD's strand count against its silence on decision rights",
        "verification_question": "Which award decisions does this role make alone, and which go to the grants committee?",
        "decision_rule": "Proceed if authority is concrete and consistent across at least two interviewers.",
        "status": "unresolved"
      },
      {
        "signal": "Contract basis unstated against a permanent-only constraint (R8)",
        "class": "risk_signal",
        "severity": "medium",
        "source_quote": "see the fund through its first phase",
        "hypothesis": "The post may be fixed-term, funded only for the fund's first phase.",
        "provenance": "[inferred] from the JD's tie of the post to the first phase against its silence on contract basis",
        "verification_question": "Is this post permanent, or fixed-term to the end of the fund's first phase?",
        "decision_rule": "Confirm the contract basis before investing in the interview loop.",
        "status": "unresolved"
      },
      {
        "signal": "First-year outcomes explicitly stated in the JD",
        "class": "positive_signal",
        "severity": null,
        "source_quote": "publish the fund's first impact report in year one",
        "hypothesis": "Role scope is genuinely defined; success is measurable.",
        "provenance": "[grounded] JD states both outcomes",
        "verification_question": "Who owns the impact-report measures today?",
        "decision_rule": null,
        "status": "noted"
      },
      {
        "signal": "Salary withheld",
        "class": "unknown",
        "severity": null,
        "source_quote": "salary on application",
        "hypothesis": "The figure may sit below the role-family band in role reality, or the foundation may simply not publish salaries.",
        "provenance": "[inferred] from the posting's withheld figure, against the [generic] band",
        "verification_question": "What salary is budgeted for this post?",
        "decision_rule": "Ask in the loop, before any offer stage; set the figure against the band, never read the band as the offer.",
        "status": "unresolved"
      }
    ],
    "application_plan": {
      "resume_edits_pending_approval": [
        {
          "id": "E1",
          "current": "Tools: grants database, Excel",
          "proposed": "Built the portfolio-reporting workbook (grantee returns, spend against award); the grants database daily for monitoring and payments",
          "source": "end-of-programme report (fetched); CV tools list",
          "note": "Reorganizes verified material; adds no new facts. Not final until approved."
        }
      ],
      "portfolio_or_work_sample": [
        "One-page sanitized due-diligence note: raises R3 to high and doubles as the R4 bridge artifact"
      ],
      "interview_questions": [
        "Which award decisions does this role make alone, and which go to the grants committee?",
        "Is this post permanent, or fixed-term to the end of the fund's first phase?",
        "Who owns the impact-report measures today?",
        "What salary is budgeted for this post?"
      ],
      "research_actions": [
        "Confirm the contract basis with the recruiter before investing in the loop",
        "Ask a current grantee or a sector contact for an introduction before applying cold [generic]"
      ]
    },
    "evidence_state": {
      "verified": [
        "UK work eligibility (user-confirmed)",
        "Programme manager for a regional funder's environment grants, open call to evaluation (CV + fetched report)",
        "Due diligence on the capital round (user-confirmed; no artifact yet)",
        "Portfolio-reporting workbook and daily grants-database use (CV + fetched report)",
        "Retrofit grants for community buildings across two capital rounds (user-confirmed)",
        "Permanent-contract constraint (user-confirmed)",
        "Start no earlier than February 2027 (user-confirmed)"
      ],
      "unverified_leads": [
        "Participatory-grantmaking pilot mentioned in prior context - memory_lead, unconfirmed"
      ],
      "rejected_inferences": [
        "Awarded grants under delegated authority - inferred from 'led the assessment panel', corrected by user: the panel recommended, the committee decided"
      ]
    },
    "handoff_to_mock_interview": {
      "high_priority_requirements": [
        "Grant programme management, open call to evaluation (R2)",
        "Due diligence on capital projects (R3)",
        "Community energy knowledge (R4)"
      ],
      "verified_candidate_evidence": [
        "Programme manager for a regional funder's environment grants, open call to evaluation - high confidence, inspectable",
        "Due diligence on the capital round - medium confidence: confirmed, limited inspectable proof, expect a probe",
        "Portfolio-reporting workbook + daily grants-database use - high confidence, inspectable",
        "Retrofit grants for community buildings across two capital rounds - medium confidence: confirmed, limited inspectable proof, expect a probe"
      ],
      "uncertain_or_weak_areas": [
        { "requirement": "Line-managing grants officers (R5)", "gap_type": "discovery", "confidence": "low", "allowed_interview_strategy": "clarify" },
        { "requirement": "Social investment or repayable finance (R7)", "gap_type": "capability", "confidence": "none", "allowed_interview_strategy": "acknowledge_gap" }
      ],
      "likely_interviewer_objections": [
        "No community-generation or share-offer work - the highest-ROI rehearsal: bridge from retrofit grants with the limit named"
      ],
      "opportunity_risks_to_validate": [
        "Award authority versus the trustees' grants committee (RR1)",
        "Contract basis versus the permanent-only constraint (RR2)",
        "Salary withheld; only the role-family band is known (RR4)"
      ],
      "questions_for_employer": [
        "Which award decisions does this role make alone, and which go to the grants committee?",
        "Is this post permanent, or fixed-term to the end of the fund's first phase?",
        "Who owns the impact-report measures today?",
        "What salary is budgeted for this post?"
      ],
      "prohibited_claims": [
        "Direct community-energy, grid-connection, or share-offer experience",
        "Awarding grants under delegated authority: the panel recommended, the committee decided",
        "The participatory-grantmaking pilot (unconfirmed memory lead)"
      ]
    }
  }
}
```
