# Antigravity Runbook — Operational Guide for Execution Agent

This runbook gives the Antigravity agent and operating engineers clear instructions for CLI execution, task lifecycles, and troubleshooting.

---

## 1. Quick CLI Reference

```powershell
# Change directory to project
cd C:\Projects\affiliate-automation

# 1. Validate all tasks in queue
python scripts/validate_tasks.py

# 2. Generate daily task queue
python scripts/daily_tasks.py

# 3. Claim highest-priority task
python scripts/claim_task.py

# 4. Complete running task into review with review package
python scripts/complete_task.py --id AFF-20261018-001 --summary "Market research complete" --decision "SCALE"

# 5. Fail a broken task
python scripts/fail_task.py --id AFF-20261018-001 --error "Upstream API timeout"

# 6. Generate daily executive report
python scripts/daily_report.py

# 7. Start dashboard web server
python scripts/serve_dashboard.py --port 8000
```

---

## 2. Step-by-Step Execution Protocol

1. **Check Queue Status**:
   Run `python scripts/validate_tasks.py` to ensure all task files comply with schema requirements.
2. **Claim Task**:
   Run `python scripts/claim_task.py`. This moves the task file from `tasks/queued/<id>.json` to `tasks/running/<id>.json` and records the ISO start timestamp.
3. **Execute Task**:
   - Produce all deliverables specified in the task contract under `research/`, `content/`, or `results/`.
   - Ensure every factual claim has an accompanying source URL.
   - For any unconfirmed metrics (commissions, cookie windows, pricing), explicitly set `"needs_verification"`.
4. **Handoff to Review**:
   Run `python scripts/complete_task.py --id <task_id> --decision <SCALE|TEST|RETEST|KILL>`.
   This creates `results/<task_id>-review.json` and transitions the task into `tasks/review/`.
5. **Never Mark Done Autonomously**:
   Moving a task to `tasks/done/` is reserved for Lead (ChatGPT) or human operator sign-off.

---

## 3. Scheduled Task Configuration

To automate daily queue generation and reporting with Antigravity:

- **Schedule Tool Mode**: Recurring Cron
- **Cron Expression**: `0 0 * * *` (Daily at 00:00 UTC)
- **Prompt**:
  > *"Run python scripts/daily_tasks.py to generate today's affiliate queue, validate tasks with python scripts/validate_tasks.py, and compile the daily report with python scripts/daily_report.py."*
- **Daemon Flag**: `true` (standalone recurring maintenance job)
