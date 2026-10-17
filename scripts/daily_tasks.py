#!/usr/bin/env python3
"""
Daily Task Generator Script
Generates the daily task queue for the Affiliate Automation system.
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

def generate_daily_tasks(date_str: Optional[str] = None, force: bool = False, base_dir: Optional[Path] = None) -> List[Path]:
    if base_dir is None:
        base_dir = get_base_dir()

    if not date_str:
        date_str = datetime.now().astimezone().strftime("%Y%m%d")

    existing_type_map = get_existing_tasks_for_date(base_dir, date_str)

    task_definitions = [
        {
            "suffix": "001",
            "type": "product_research",
            "goal": "Find and rank affiliate opportunities relevant to Vietnam, prioritizing digital, AI, and SaaS products.",
            "context": "Execute 7-dimension scoring framework (Demand, BuyerIntent, CommissionEconomics, ContentFit, Competition, Trend, ComplianceRisk). Flag unknown metrics as 'needs_verification'.",
            "priority": "high",
            "dependencies": [],
            "requirements": [
                "Research active affiliate programs compatible with Vietnam and global traffic",
                "Assess target buyer persona, urgency, and monetization models",
                "Apply rubric weights from config/scoring.json",
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
                "Explicit risks documented"
            ]
        },
        {
            "suffix": "002",
            "type": "deep_research",
            "goal": "Deep research top candidates from daily opportunity research.",
            "context": "Conduct thorough funnel, audience, and payout analysis on top shortlisted scale/test candidates.",
            "priority": "high",
            "dependencies": [f"AFF-{date_str}-001"],
            "requirements": [
                "Map user journey and landing page conversion friction",
                "Analyze competitor keyword positioning and organic traffic hooks",
                "Document exact cookie duration, payout frequencies, and local banking options"
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
            "goal": "Create production-ready content for selected test candidates.",
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
            "type": "system_maintenance",
            "goal": "Validate queue/results/metrics and report problems.",
            "context": "Perform daily hygiene checks on task queues, deliverables, metric schemas, and health endpoints.",
            "priority": "medium",
            "dependencies": [],
            "requirements": [
                "Execute schema validation on all tasks",
                "Verify file existence for listed deliverables and review artifacts",
                "Aggregate daily metrics and log system health"
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
        }
    ]

    created_paths = []

    for t_def in task_definitions:
        t_type = t_def["type"]
        if not force and t_type in existing_type_map:
            print(f"⏭️  [SKIP] Task for type '{t_type}' already exists for {date_str} (ID: {existing_type_map[t_type]})")
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
    parser.add_argument("--date", help="Target date in YYYYMMDD format (defaults to current UTC date)")
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
