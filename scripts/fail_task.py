#!/usr/bin/env python3
"""
Fail Task Script
Transitions a queued or running task into 'failed' status and records failure details.
Moves task JSON to tasks/failed/<task_id>.json.
"""

import sys
import os
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from validate_tasks import get_base_dir, validate_task_dict

def fail_task(task_id: str, error_message: str, base_dir: Optional[Path] = None) -> Path:
    if base_dir is None:
        base_dir = get_base_dir()

    tasks_dir = base_dir / "tasks"
    failed_dir = tasks_dir / "failed"
    failed_dir.mkdir(parents=True, exist_ok=True)

    # Search for task in running or queued
    src_file = None
    for sub in ["running", "queued", "review"]:
        candidate = tasks_dir / sub / f"{task_id}.json"
        if candidate.exists():
            src_file = candidate
            break

    if not src_file:
        raise FileNotFoundError(f"Task '{task_id}' not found in running, queued, or review folders.")

    with open(src_file, "r", encoding="utf-8") as f:
        task_data = json.load(f)

    now_iso = datetime.now(timezone.utc).isoformat()
    task_data["status"] = "failed"
    task_data["completed_at"] = now_iso
    task_data["result"] = {
        "status": "failed",
        "error": error_message,
        "failed_at": now_iso
    }

    dest_file = failed_dir / f"{task_id}.json"

    # Validate before write
    errs = validate_task_dict(task_data, dest_file)
    if errs:
        raise ValueError(f"Task validation failed: {'; '.join(errs)}")

    with open(dest_file, "w", encoding="utf-8") as f:
        json.dump(task_data, f, indent=2, ensure_ascii=False)

    src_file.unlink()
    return dest_file

def main():
    parser = argparse.ArgumentParser(description="Transition a task to failed status.")
    parser.add_argument("--id", required=True, help="Task ID (e.g. AFF-20261018-001)")
    parser.add_argument("--error", required=True, help="Error message / failure reason")

    args = parser.parse_args()

    try:
        dest = fail_task(task_id=args.id, error_message=args.error)
        print(f"⚠️ Task marked as failed: {dest.name}")
        print(f"Moved to: {dest}")
    except Exception as e:
        print(f"❌ Error failing task: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
