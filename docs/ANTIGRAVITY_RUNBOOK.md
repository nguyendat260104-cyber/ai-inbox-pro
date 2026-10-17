# Antigravity Runbook — Operational Guide for Execution Agent

This runbook gives the Antigravity agent and operating engineers explicit instructions for CLI execution, task state transitions, and the daily autonomous execution lifecycle.

---

## 1. Quick CLI Reference

```powershell
# Change directory to project root
cd C:\Projects\affiliate-automation

# 1. Validate all tasks in queue against contract schema
python scripts/validate_tasks.py

# 2. Generate daily task queue (5-stage workflow)
python scripts/daily_tasks.py

# 3. Claim highest-priority unblocked task (queued -> running)
python scripts/claim_task.py

# 4. Complete running task into review with Lead review package
python scripts/complete_task.py --id AFF-20261018-001 --summary "Done" --decision "SCALE"

# 5. Fail a broken task with error traceback
python scripts/fail_task.py --id AFF-20261018-001 --error "Upstream timeout"

# 6. Aggregate metrics and compile daily executive report
python scripts/daily_report.py

# 7. Start dashboard web server
python scripts/serve_dashboard.py --port 8000

# 8. Execute comprehensive 11-test suite
python tests/test_suite.py
```

---

## 2. Standard 9-Step Operating Protocol

Every day, Antigravity operates strictly according to this 9-step execution loop:

1. **Inspect `tasks/queued/`**:
   Scan available tasks in `tasks/queued/` and check for any unresolved dependencies.
2. **Claim Highest-Priority Unblocked Task**:
   Run `python scripts/claim_task.py`. The algorithm prioritizes by priority (`critical` > `high` > `medium` > `low`) and earliest creation time.
3. **Move to `tasks/running/`**:
   The claim script updates `status` to `"running"`, records the ISO timestamp in `started_at`, and moves the file to `tasks/running/<task_id>.json`.
4. **Execute**:
   Implement research, coding, content drafting, or data aggregation as specified in `requirements` and `deliverables`.
   - Never invent pricing, commissions, or conversion metrics. Mark unknown values explicitly as `"needs_verification"`.
   - Provide source URLs for every factual claim.
   - Include mandatory FTC/local affiliate disclosure statements.
5. **Validate Acceptance Criteria**:
   Audit all deliverables against each requirement listed in `acceptance_criteria`.
6. **Save Artifacts**:
   Store market research in `research/`, content assets in `content/`, and performance data in `metrics/`.
7. **Create Compact Lead Review JSON**:
   Generate `results/<task_id>-review.json` containing: `task_id`, `executive_summary`, `key_findings`, `recommended_decision`, `confidence`, `business_metrics`, `artifacts`, `sources`, `risks`, `questions_for_lead`, `next_task_suggestions`.
8. **Move to `tasks/review/`**:
   Run `python scripts/complete_task.py --id <task_id>`. This updates `status` to `"review"`, sets `completed_at`, links deliverables in `result`, and transfers the task JSON into `tasks/review/`.
9. **Continue Next Task**:
   Check if further unblocked tasks remain in `tasks/queued/` and repeat from Step 1.

---

## 3. Idle Protocol (When Nothing is Queued)

When `tasks/queued/` is empty or all remaining tasks are blocked by pending Lead reviews:
- **DO NOT invent arbitrary business work.**
- **DO NOT autonomously make decisions to Scale, Kill, or deploy ad campaigns.**
- **Instead:**
  1. Validate system health with `python scripts/validate_tasks.py`.
  2. Generate the daily rollup report with `python scripts/daily_report.py`.
  3. Stop and wait for Lead (ChatGPT) review.

---

## 4. Safety Guardrails & Operational Boundaries

The executor is bound by strict safety limits:
- **No money spent:** No purchasing domains, proxies, or software.
- **No public publishing:** Do not post directly to live YouTube, TikTok, CMS, or ad networks. Content stays in `content/` as drafts for human/Lead review.
- **No secret leakage:** Never log or commit real tokens or credentials.
- **Filesystem boundary:** Never modify or delete any file outside `C:\Projects\affiliate-automation\`.

---

## 5. Scheduled Automation Configuration

To automate daily maintenance using the Antigravity `schedule` tool:
- **Mode:** Recurring cron
- **Cron Expression:** `0 0 * * *` (Daily at 00:00 UTC / 07:00 Vietnam Time)
- **Prompt:**
  ```text
  Run python scripts/daily_tasks.py to generate today's affiliate queue, validate tasks with python scripts/validate_tasks.py, and compile the daily report with python scripts/daily_report.py.
  ```
- **Daemon Flag:** `true`
