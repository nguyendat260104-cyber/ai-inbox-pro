# Daily Workflow & Automation Routine

This guide specifies the operational routine executed daily to keep the affiliate business pipeline active, hygienic, and productive.

---

## 1. Daily Cadence (Automated & Manual)

| Step | Time / Trigger | Script / Action | Output |
|---|---|---|---|
| **1. Queue Generation** | 00:00 UTC / Morning | `python scripts/daily_tasks.py` | 4 structured tasks created in `tasks/queued/` |
| **2. Task Execution** | Sprints during the day | `python scripts/claim_task.py` | Highest priority task moved to `tasks/running/` |
| **3. Asset Production** | Executor active | Research, scoring, content drafting | Artifacts saved to `research/` and `content/` |
| **4. Handoff to Review** | On criteria completion | `python scripts/complete_task.py` | Task moved to `tasks/review/`, review JSON created |
| **5. Health & Reporting** | End of day / Continuous | `python scripts/daily_report.py` | Markdown & JSON summary in `metrics/daily/` |
| **6. Strategic Review** | Lead session | ChatGPT / Human Review | Decisions recorded, winning offers moved to `tasks/done/` |

---

## 2. Standard Daily Tasks

When `python scripts/daily_tasks.py` is invoked, it checks for existing tasks for that date to prevent duplicates. It generates:

1. **TASK 1 — Opportunity Research (`AFF-<date>-001`)**
   - Type: `product_research`
   - Scans 20 candidate affiliate products in targeted niches (AI, SaaS, Dev tools, Hosting).
   - Generates `research/products/<date>-products.json` and `research/reports/<date>-opportunity-report.md`.
2. **TASK 2 — Deep Research (`AFF-<date>-002`)**
   - Type: `deep_research` (dependent on Task 1)
   - Detailed funnel breakdown, payout tiers, tracking mechanics, and competitor review.
   - Generates `research/reports/<date>-deep-dive.md`.
3. **TASK 3 — Content Production (`AFF-<date>-003`)**
   - Type: `content_production` (dependent on Task 2)
   - Produces high-retention video script and long-form review post.
   - Generates `content/scripts/<date>-product-script.md` and `content/posts/<date>-product-post.md`.
4. **TASK 4 — System Maintenance (`AFF-<date>-004`)**
   - Type: `system_maintenance`
   - Validates JSON schemas, audits missing file references, checks dashboard health.
   - Generates `results/<date>-maintenance-log.json`.

---

## 3. Duplicate Prevention Mechanism

`daily_tasks.py` checks all status subdirectories (`queued`, `running`, `review`, `done`, `failed`) for any task matching `AFF-<date>-*.json` with the identical task type:
- If a task of that type already exists for today, it prints `[SKIP]` and leaves the existing task intact.
- If you need to force task recreation, use the `--force` flag.
