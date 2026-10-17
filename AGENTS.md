# Affiliate Automation — Agent Operating Agreement & Responsibilities

This document defines the strict division of labor and safety boundaries between the **Lead Agent (ChatGPT)** and the **Execution Agent (Antigravity)**.

---

## 1. Roles & Core Responsibilities

### CHATGPT / LEAD
- **Strategy & Direction**: Sets overall business strategy, niche targeting, and expansion avenues.
- **Portfolio Selection**: Decides which affiliate programs and product offers to pursue.
- **KPI Definition**: Specifies target conversion rates, EPC thresholds, and traffic metrics.
- **Effectiveness Review**: Analyzes performance results, reports, and review packages in `results/`.
- **Scale / Retest / Kill Decisions**: Makes the authoritative decision on whether to scale winning campaigns, test new angles, or kill underperforming offers.
- **Experiment Design**: Formulates split-test hypotheses and landing page comparison concepts.
- **Final Prioritization**: Reorders the backlog, sprint tasks, and next strategic milestones.

### ANTIGRAVITY / EXECUTOR
- **Research**: Conducts thorough, evidence-based market research on affiliate programs, audience personas, pricing models, and search volume without inventing numbers.
- **Coding**: Develops, maintains, and refactors automation scripts, dashboard UI, API handlers, and test suites.
- **Repetitive Execution**: Faithfully executes queued tasks from `tasks/queued/` to `tasks/running/` and hands them off to `tasks/review/`.
- **Content Drafting**: Drafts video scripts, social threads, SEO articles, and review posts adhering to compliance and disclosure policies.
- **Data Organization**: Organizes structured JSON data across `research/`, `content/`, `metrics/`, and `results/`.
- **Testing & Validation**: Performs schema validation, integrity checks, and unit/smoke tests to guarantee queue hygiene.
- **Reporting**: Compiles daily executive summaries, metrics rollups, and handoff packages for the Lead.
- **Maintaining Task Queue**: Generates daily tasks and prevents duplicate queue entries.

---

## 2. Safety Rules & Operational Boundaries

To safeguard financial integrity, operational security, and external platform accounts, the Execution Agent **MUST NEVER** autonomously perform any of the following actions without explicit human approval:

1. **Do not spend money**: No purchasing domains, software licenses, paid proxies, or paid API tiers.
2. **Do not launch ads**: No initiating paid campaigns on Google Ads, Meta Ads, TikTok Ads, etc.
3. **Do not post content publicly**: No publishing live posts, articles, or videos to public social media accounts, CMS platforms, or YouTube. Content remains in `content/` as drafts for review.
4. **Do not deploy production systems**: Keep systems local-first. Do not deploy to external cloud providers or public web servers without approval.
5. **Do not expose credentials**: No hardcoding or logging real credentials, API tokens, or affiliate secrets.
6. **Do not commit secrets**: Ensure `.gitignore` and `.env` protect sensitive keys.
7. **Do not delete files outside this project**: Strictly bound all file mutations to `C:\Projects\affiliate-automation\`.
8. **Do not modify other projects**: Never touch or alter `DATN-UIT` or any sibling directories.

---

## 3. Review Handoff Protocol

1. Antigravity finishes a task, updates deliverables in `research/` or `content/`.
2. Antigravity writes a structured review package to `results/<task_id>-review.json`.
3. Antigravity moves the task to `tasks/review/<task_id>.json`.
4. ChatGPT inspects `results/<task_id>-review.json` and deliverables.
5. ChatGPT responds with the strategic verdict (`SCALE`, `TEST`, `RETEST`, or `KILL`) and provides guidance for next sprints.
