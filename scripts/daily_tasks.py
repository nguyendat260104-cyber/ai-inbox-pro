#!/usr/bin/env python3
"""
Daily Task Generator Script
Generates the daily task queue for the Affiliate Automation system.
Follows the 5-step daily workflow:
01 Opportunity Radar
02 Deep Research
03 Content Production
04 Data / Metrics Validation
05 Daily Report
Prevents duplicate tasks for the same date and task type.
"""

import sys
import os
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from validate_tasks import get_base_dir, validate_task_dict
from create_task import create_task

def get_existing_tasks_for_date(base_dir: Path, date_str: str) -> Dict[str, str]:
    """
    Returns a dict mapping task_type -> task_id for all tasks matching the given date
    across all status directories (queued, running, review, done, failed).
    """
    tasks_dir = base_dir / "tasks"
    existing_types = {}
    prefix = f"AFF-{date_str}-"

    for sub in ["queued", "running", "review", "done", "failed"]:
        folder = tasks_dir / sub
        if not folder.exists():
            continue
        for task_file in folder.glob(f"{prefix}*.json"):
            try:
                with open(task_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                task_type = data.get("type")
                if task_type:
                    existing_types[task_type] = data.get("id", task_file.stem)
            except Exception:
                pass
    return existing_types

def is_type_existing(t_type: str, existing_types: Dict[str, str]) -> Optional[str]:
    # Check exact match or known aliases
    aliases = {
        "opportunity_radar": ["opportunity_radar", "product_research"],
        "product_research": ["opportunity_radar", "product_research"],
        "metrics_validation": ["metrics_validation", "system_maintenance"],
        "system_maintenance": ["metrics_validation", "system_maintenance"],
        "daily_reporting": ["daily_reporting", "daily_report"]
    }
    candidates = aliases.get(t_type, [t_type])
    for c in candidates:
        if c in existing_types:
            return existing_types[c]
    return None

def generate_daily_tasks(date_str: Optional[str] = None, force: bool = False, base_dir: Optional[Path] = None) -> List[Path]:
    if base_dir is None:
        base_dir = get_base_dir()

    if not date_str:
        date_str = datetime.now().astimezone().strftime("%Y%m%d")

    existing_type_map = get_existing_tasks_for_date(base_dir, date_str)

    task_definitions = [
        {
            "suffix": "001",
            "type": "opportunity_radar",
            "goal": "01 Opportunity Radar — Find and rank affiliate opportunities relevant to Vietnam, prioritizing digital, AI, and SaaS products.",
            "context": "Execute 7-dimension opportunity scoring plus Affiliate Readiness. Flag unknown metrics as 'needs_verification'; readiness below 60 blocks SCALE.",
            "priority": "high",
            "dependencies": [],
            "requirements": [
                "Research active affiliate programs compatible with Vietnam and global traffic",
                "Assess target buyer persona, urgency, and monetization models",
                "Apply rubric weights from config/scoring.json",
                "Score Affiliate Readiness: Program open 30, Vietnam eligible 20, Approval difficulty 15, Payout practicality 15, Commercial terms verified 20",
                "Verify program terms and disclosure rules"
            ],
            "deliverables": [
                f"research/products/{date_str}-products.json",
                f"research/reports/{date_str}-opportunity-report.md"
            ],
            "acceptance_criteria": [
                "20 candidates where reasonably available",
                "Source URL for factual claims",
                "No invented commission values",
                "Buyer persona for every candidate",
                "At least 3 content angles per shortlisted candidate",
                "Score 0-100 normalized",
                "Top 5 shortlist highlighted",
                "Explicit risks documented",
                "No SCALE recommendation when readiness_score is below 60"
            ]
        },
        {
            "suffix": "002",
            "type": "deep_research",
            "goal": "02 Deep Research — Conduct deep research and funnel breakdown for top shortlisted candidates.",
            "context": "Priority: Make.com, Hostinger, ElevenLabs. Secondary: NordVPN, Grammarly, ClickUp. Verify all facts from current official sources and mark unknowns needs_verification.",
            "priority": "high",
            "dependencies": [f"AFF-{date_str}-001"],
            "requirements": [
                "Map user journey and landing page conversion friction",
                "Analyze competitor keyword positioning and organic traffic hooks",
                "Document exact cookie duration, payout frequencies, and local banking options",
                "Verify Vietnam eligibility, approval, prohibited methods, personas, buyer-intent keywords, and five short-form angles per offer"
            ],
            "deliverables": [
                f"research/reports/{date_str}-deep-dive.md"
            ],
            "acceptance_criteria": [
                "Detailed funnel analysis for top candidates",
                "Competitive pricing and payout matrix verified",
                "Tracking links and cookie attribution mechanics documented",
                "Conversion hook recommendations finalized"
            ]
        },
        {
            "suffix": "003",
            "type": "content_production",
            "goal": "03 Content Production — Create production-ready content assets for selected test candidates.",
            "context": "Draft multi-channel creative assets complying with disclosure guidelines and targeting commercial search queries.",
            "priority": "high",
            "dependencies": [f"AFF-{date_str}-002"],
            "requirements": [
                "Write high-retention video script (YouTube Shorts / TikTok)",
                "Write comprehensive tutorial/review post for blog or newsletter",
                "Incorporate mandatory affiliate disclosure statement",
                "Include parameterized tracking link placeholders"
            ],
            "deliverables": [
                f"content/scripts/{date_str}-product-script.md",
                f"content/posts/{date_str}-product-post.md"
            ],
            "acceptance_criteria": [
                "Includes persona, funnel stage, channel, hook, CTA",
                "Mandatory affiliate disclosure included",
                "Tracking link placeholders with subid parameters included",
                "No misleading income guarantees or fake claims",
                "B-roll, thumbnail, and visual cues specified"
            ]
        },
        {
            "suffix": "004",
            "type": "metrics_validation",
            "goal": "04 Data / Metrics Validation — Validate queue integrity, results schemas, and metrics data.",
            "context": "Perform daily hygiene checks on task queues, deliverables, metric schemas, and health endpoints.",
            "priority": "medium",
            "dependencies": [],
            "requirements": [
                "Execute schema validation on all tasks",
                "Verify file existence for listed deliverables and review artifacts",
                "Audit metrics consistency and log system health"
            ],
            "deliverables": [
                f"results/{date_str}-maintenance-log.json"
            ],
            "acceptance_criteria": [
                "Zero schema validation errors across tasks/",
                "Missing or corrupted files flagged explicitly",
                "Summary log stored in results/",
                "Queue health status confirmed"
            ]
        },
        {
            "suffix": "005",
            "type": "daily_reporting",
            "goal": "05 Daily Report — Compile executive summary report and metrics rollups for ChatGPT Lead Review.",
            "context": "Synthesize task progress, top opportunities, content assets, and blockers into daily report artifacts.",
            "priority": "medium",
            "dependencies": [f"AFF-{date_str}-004"],
            "requirements": [
                "Run daily_report.py to aggregate metrics and status counts",
                "Ensure JSON and Markdown report versions exist",
                "Highlight key findings and strategic decision requests for Lead"
            ],
            "deliverables": [
                f"metrics/daily/{date_str}-report.json",
                f"metrics/daily/{date_str}-report.md"
            ],
            "acceptance_criteria": [
                "Accurate counts across all queue statuses",
                "Top research candidates highlighted",
                "Review packages summarized with questions for Lead"
            ]
        }
    ]

    created_paths = []

    for t_def in task_definitions:
        t_type = t_def["type"]
        existing_id = is_type_existing(t_type, existing_type_map)
        if not force and existing_id:
            print(f"⏭️  [SKIP] Task for type '{t_type}' already exists for {date_str} (ID: {existing_id})")
            continue

        target_id = f"AFF-{date_str}-{t_def['suffix']}"

        task_path = create_task(
            task_id=target_id,
            task_type=t_type,
            goal=t_def["goal"],
            context=t_def["context"],
            requirements=t_def["requirements"],
            deliverables=t_def["deliverables"],
            acceptance_criteria=t_def["acceptance_criteria"],
            priority=t_def["priority"],
            dependencies=t_def["dependencies"],
            base_dir=base_dir
        )
        print(f"✅ [CREATED] {target_id} ({t_type}) -> {task_path.name}")
        created_paths.append(task_path)

    return created_paths

def main():
    parser = argparse.ArgumentParser(description="Generate daily affiliate automation task queue.")
    parser.add_argument("--date", help="Target date in YYYYMMDD format (defaults to current local date)")
    parser.add_argument("--force", action="store_true", help="Force creation even if duplicate types exist")

    args = parser.parse_args()

    try:
        created = generate_daily_tasks(date_str=args.date, force=args.force)
        print(f"\nSummary: {len(created)} tasks created for daily queue.")
    except Exception as e:
        print(f"❌ Error generating daily tasks: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
