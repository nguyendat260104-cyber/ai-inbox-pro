# Affiliate Automation Command Center

Local-first, agent-driven command center for automated affiliate marketing research, content production, scoring, and performance tracking.

Portfolio decisions use two separate scores: opportunity potential and Affiliate Readiness. Readiness is weighted as Program open (30), Vietnam eligible (20), Approval difficulty (15), Payout practicality (15), and Commercial terms verified (20). A score below 60 blocks SCALE.

Built with Python 3.13, dependency-light vanilla frontend, and a filesystem-based queue state machine.

---

## Roles
- **Strategic Lead / Reviewer**: ChatGPT (portfolio decisions, experiment design, scale/kill verdicts)
- **Primary Executor**: Antigravity (research, coding, content drafting, task automation, reports)

---

## Getting Started

### Prerequisites
- Python 3.13+ (standard library only, zero pip dependencies required)
- Git (optional for local history tracking)

### Running the Dashboard
```bash
python scripts/serve_dashboard.py --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

### Daily Automation
```bash
# 1. Generate today's queue
python scripts/daily_tasks.py

# 2. Claim top task to run
python scripts/claim_task.py

# 3. Complete running task into review
python scripts/complete_task.py --id <TASK_ID> --summary "Done" --decision "TEST"

# 4. Generate daily executive report
python scripts/daily_report.py

# Validate the task engine, dashboard, and readiness gate
python tests/test_suite.py
```

---

## Directory Structure
- `tasks/`: Queue directories (`queued`, `running`, `review`, `done`, `failed`)
- `research/`: Market research products (`products/`) and reports (`reports/`)
- `content/`: Scripts, posts, articles, and marketing assets
- `metrics/`: Daily rollups and split test tracking
- `config/`: Affiliate policy and 7-dimension scoring criteria
- `scripts/`: Python automation scripts
- `dashboard/`: Lightweight UI (HTML, CSS, JS)
- `docs/`: System documentation and operational runbooks
- `templates/`: Standardized JSON schemas
