# Operating Model — Affiliate Automation Command Center

## 1. Principles of Collaboration

This project operates on an asynchronous, two-agent model:
1. **Strategic Leadership (ChatGPT)** defines direction, evaluates economics, and acts as the gatekeeper before any offer or campaign advances.
2. **Autonomous Execution (Antigravity)** implements code, queries and parses data, writes content drafts, maintains the test suite, and packages deliverables for inspection.

---

## 2. Information Flow & Contract Handoff

```
   [ChatGPT / Lead]
          │
          │ 1. Directives & Strategy
          ▼
   [Task Backlog in tasks/queued/]
          │
          │ 2. Claim & Execute
          ▼
   [Antigravity / Executor]
          │
          │ 3. Generates Artifacts (research/, content/, metrics/)
          │ 4. Produces results/<task_id>-review.json
          ▼
   [tasks/review/<task_id>.json]
          │
          │ 5. Review & Strategic Decision
          ▼
   [ChatGPT / Lead] ────► [Scale / Test / Retest / Kill] ────► [tasks/done/]
```

### Lead Review Output Contract
Every execution package submitted to `tasks/review/` has an associated `results/<task_id>-review.json` with this schema:

```json
{
  "task_id": "AFF-YYYYMMDD-001",
  "executive_summary": "Comprehensive market research on 20 SaaS and AI affiliate opportunities for Vietnam.",
  "key_findings": [
    "High search demand for local banking / MoMo payment support in AI productivity suites.",
    "Top 5 candidates achieved an average score of 84.6/100."
  ],
  "recommended_decision": "SCALE",
  "confidence": 0.88,
  "business_metrics": {
    "opportunities_evaluated": 20,
    "top_candidates_count": 5,
    "avg_top_score": 84.6
  },
  "artifacts": [
    "research/products/20261018-products.json",
    "research/reports/20261018-opportunity-report.md"
  ],
  "questions_for_lead": [
    "Confirm whether to prioritize TikTok short-form vs SEO review tutorials for the top candidate."
  ],
  "next_task_suggestions": [
    "Draft high-retention video script for top candidate",
    "Perform deep funnel tear-down on candidate #2"
  ]
}
```

---

## 3. Grounding & Anti-Hallucination Directives

In automated affiliate marketing, fabricated data leads to burned capital and banned accounts. Antigravity adheres to these immutable rules:
- **Never fabricate affiliate commissions**: If an offer's payout percentage or cookie duration is unconfirmed, mark it explicitly as `"needs_verification"`.
- **Never invent pricing**: Official tier prices must be verified or marked `"needs_verification"`.
- **Never simulate false testimonials or metrics**: Real conversions or null.
- **Mandatory Disclosures**: All drafted content must include compliant affiliate disclosures:
  > *"Disclosure: This post contains affiliate links. If you purchase through them, we may earn a commission at no additional cost to you."*
