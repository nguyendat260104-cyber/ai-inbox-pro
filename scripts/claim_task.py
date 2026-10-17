#!/usr/bin/env python3
"""
Claim Task Script
Selects the highest-priority valid task in tasks/queued, updates its status to 'running',
sets started_at timestamp, and moves it to tasks/running/<task_id>.json.
"""

import sys
import os
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from validate_tasks import get_base_dir, validate_task_dict

PRIORITY_MAP = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1
}

def claim_task(task_id: Optional[str] = None, base_dir: Optional[Path] = None) -> Optional[Path]:
    if base_dir is None:
        base_dir = get_base_dir()

    queued_dir = base_dir / "tasks" / "queued"
    running_dir = base_dir / "tasks" / "running"
    running_dir.mkdir(parents=True, exist_ok=True)

    if not queued_dir.exists():
        print("No queued directory found.", file=sys.stderr)
        return None

    candidate_files = list(queued_dir.glob("*.json"))
    if not candidate_files:
        print("No tasks currently queued.")
        return None

    target_file = None
    target_data = None

    if task_id:
        expected = queued_dir / f"{task_id}.json"
        if not expected.exists():
            print(f"Task '{task_id}' not found in tasks/queued/", file=sys.stderr)
            return None
        target_file = expected
        with open(target_file, "r", encoding="utf-8") as f:
            target_data = json.load(f)
    else:
        # Sort candidate tasks by priority (highest first) and created_at (earliest first)
        scored_candidates = []
        for f in candidate_files:
            try:
                with open(f, "r", encoding="utf-8") as tf:
                    data = json.load(tf)
                errs = validate_task_dict(data, f)
                if errs:
                    print(f"Skipping invalid queued task {f.name}: {'; '.join(errs)}", file=sys.stderr)
                    continue
                prio_val = PRIORITY_MAP.get(data.get("priority", "medium").lower(), 2)
                created = data.get("created_at", "")
                scored_candidates.append((prio_val, created, f, data))
            except Exception as e:
                print(f"Error reading {f.name}: {e}", file=sys.stderr)

        if not scored_candidates:
            print("No valid queued tasks found to claim.")
            return None

        # Sort: prio descending, created ascending
        scored_candidates.sort(key=lambda x: (-x[0], x[1]))
        target_file = scored_candidates[0][2]
        target_data = scored_candidates[0][3]

    # Update task fields
    target_data["status"] = "running"
    target_data["started_at"] = datetime.now(timezone.utc).isoformat()

    dest_file = running_dir / target_file.name

    # Validate before moving
    errs = validate_task_dict(target_data, dest_file)
    if errs:
        raise ValueError(f"Validation error upon claiming: {'; '.join(errs)}")

    with open(dest_file, "w", encoding="utf-8") as f:
        json.dump(target_data, f, indent=2, ensure_ascii=False)

    # Remove from queued
    target_file.unlink()
    return dest_file

def main():
    parser = argparse.ArgumentParser(description="Claim a queued task to running status.")
    parser.add_argument("--id", help="Optional specific task ID to claim.")
    args = parser.parse_args()

    dest = claim_task(task_id=args.id)
    if dest:
        print(f"🚀 Successfully claimed task: {dest.stem}")
        print(f"File moved to: {dest}")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
