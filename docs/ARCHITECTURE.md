# Architecture Specification — Affiliate Automation Command Center

## 1. System Overview

The **Affiliate Automation Command Center** is a local-first, agent-driven automation framework designed to discover, evaluate, draft content for, and monitor affiliate marketing opportunities. It enforces strict separation of concerns between strategic leadership (ChatGPT) and continuous execution (Antigravity).

```
affiliate-automation/
│
├── tasks/                       # Task queue filesystem-based state machine
│   ├── queued/                  # Unclaimed tasks ready for work
│   ├── running/                 # Tasks currently being executed
│   ├── review/                  # Completed tasks awaiting Lead review
│   ├── done/                    # Approved and finalized tasks
│   └── failed/                  # Tasks terminated due to errors
│
├── results/                     # Lead review packages & maintenance logs (<task_id>-review.json)
├── research/                    # Evidence-based market discovery
│   ├── products/                # Scored candidate lists (JSON)
│   └── reports/                 # Analytical opportunity reports & deep dives (Markdown)
├── content/                     # Creative marketing assets
│   ├── scripts/                 # Short/long-form video scripts (Markdown)
│   ├── posts/                   # Social media and thread drafts (Markdown)
│   ├── articles/                # Long-form tutorials and review articles (Markdown)
│   └── assets/                  # Media hooks, thumbnails, copy assets
├── metrics/                     # Quantitative performance data
│   ├── daily/                   # Daily rollups and health metrics
│   └── experiments/             # Split test results and attribution tracking
├── config/                      # System configuration
│   ├── affiliate.json           # Global parameters, niches, geos, compliance policies
│   └── scoring.json             # 7-dimension scoring weights and rubric framework
├── scripts/                     # Python CLI toolchain
│   ├── create_task.py           # Registers tasks into queued/
│   ├── claim_task.py            # Moves highest-priority queued task to running/
│   ├── complete_task.py         # Moves running task to review/ with review package
│   ├── fail_task.py             # Transitions task to failed/
│   ├── daily_tasks.py           # Idempotent daily queue generator
│   ├── daily_report.py          # Aggregates metrics & generates daily report
│   ├── validate_tasks.py        # Schema & lifecycle validator
│   └── serve_dashboard.py       # Python HTTP server + API for local dashboard
├── dashboard/                   # Lightweight dependency-free web dashboard
│   ├── index.html               # Semantic HTML UI
│   ├── app.js                   # Client-side reactivity and auto-polling
│   └── style.css                # Dark-mode command center styling
├── docs/                        # Engineering and operational runbooks
│   ├── ARCHITECTURE.md
│   ├── OPERATING_MODEL.md
│   ├── DAILY_WORKFLOW.md
│   └── ANTIGRAVITY_RUNBOOK.md
├── templates/                   # JSON schemas and task starter templates
├── AGENTS.md                    # Role boundaries and safety protocols
├── README.md                    # Getting started & CLI reference
├── .gitignore                   # Git exclusions
└── .env.example                 # Environment template
```

---

## 2. State Machine & Queue Lifecycle

The task queue is implemented purely using the filesystem, guaranteeing that state is versionable, transparent, inspectable via standard terminal tools, and independent of external database engines.

```
       [create_task.py / daily_tasks.py]
                       │
                       ▼
               ┌──────────────┐
               │ tasks/queued │
               └──────┬───────┘
                      │  [claim_task.py]
                      ▼
               ┌──────────────┐
       ┌───────┤ tasks/running├────────┐
       │       └──────┬───────┘        │
[fail_task.py]        │ [complete_task.py]     │ [fail_task.py]
       │              ▼                │
       │       ┌──────────────┐        │
       │       │ tasks/review │        │
       │       └──────┬───────┘        │
       │              │  [Lead Review: ChatGPT]
       │              ▼                │
       │       ┌──────────────┐        │
       │       │  tasks/done  │        │
       │       └──────────────┘        │
       ▼                               ▼
┌──────────────┐               ┌──────────────┐
│ tasks/failed │               │ tasks/failed │
└──────────────┘               └──────────────┘
```

1. **Queued**: Tasks generated programmatically or manually. Must pass schema validation.
2. **Running**: A single execution agent claims the task, records `started_at`, and carries out work.
3. **Review**: The task cannot be moved to `done` autonomously. The executor produces deliverables and generates `results/<task_id>-review.json`, then moves the task to `tasks/review/`.
4. **Done**: Marked `done` only after Lead (ChatGPT) or Human reviews and accepts the work.
5. **Failed**: Captures stack traces, validation failures, or unrecoverable errors.

---

## 3. Data Integrity & Scoring Engine

The scoring system (`config/scoring.json`) normalizes evaluations to a 0–100 scale across 7 weighted dimensions:

| Dimension | Weight | Description |
|---|---|---|
| **Demand** | 25 | Search volume, social buzz, active user growth, and market adoption |
| **BuyerIntent** | 20 | Urgency of problem, willingness to pay, commercial intent queries |
| **CommissionEconomics** | 15 | Commission rate, recurring vs one-time, cookie window duration |
| **ContentFit** | 15 | Visual demonstration hook potential, tutorial fit, format fit |
| **Competition** | 10 | SERP saturation vs healthy gaps in specific regional niches |
| **Trend** | 10 | Adoption curve, Google Trends trajectory, emerging tech wave |
| **ComplianceRisk** | 5 | Program stability, trademark restrictions, disclosure hurdles |

### Decision Framework
- **80–100 = SCALE CANDIDATE**: Immediate multi-channel content production, comparison pages.
- **65–79 = TEST**: Pilot 1–2 test creative assets, validate click-through rate.
- **50–64 = RETEST / NEW ANGLE**: Hold until alternate positioning or higher tier is found.
- **0–49 = KILL**: Discard; low commercial intent, poor economics, or excessive compliance risk.

---

## 4. Local-First Dashboard & API

The dashboard uses Python standard library `http.server.HTTPServer` with no external dependencies (zero npm/Node.js, zero pip installations):
- **Port**: 8000 (configurable via `--port`)
- **API Endpoint**: `GET /api/data` returns real-time JSON of tasks, offers, content, reviews, and metrics.
- **Frontend**: Vanilla JavaScript (`app.js`) with auto-polling every 5 seconds.
