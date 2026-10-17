#!/usr/bin/env python3
"""
Task Validation Script
Ensures all tasks in the queue adhere strictly to the JSON contract, valid statuses,
folder location consistency, and naming conventions.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VALID_STATUSES = {"queued", "running", "review", "done", "failed"}
VALID_PRIORITIES = {"critical", "high", "medium", "low"}

REQUIRED_FIELDS = [
    "id",
    "type",
    "executor",
    "goal",
    "context",
    "requirements",
    "deliverables",
    "acceptance_criteria",
    "priority",
    "dependencies",
    "suggested_branch",
    "status",
    "created_at",
    "started_at",
    "completed_at",
    "result",
    "artifacts",
    "metrics"
]

def get_base_dir() -> Path:
    # Anchor to project root (parent of scripts/)
    return Path(__file__).resolve().parent.parent

def validate_task_dict(task: Dict[str, Any], file_path: Path = None) -> List[str]:
    errors = []
    
    # 1. Required fields
    for field in REQUIRED_FIELDS:
        if field not in task:
            errors.append(f"Missing required field: '{field}'")
            
    # 2. Status validity
    status = task.get("status")
    if status not in VALID_STATUSES:
        errors.append(f"Invalid status '{status}'. Must be one of: {sorted(list(VALID_STATUSES))}")
        
    # 3. Priority validity
    priority = task.get("priority")
    if priority and priority.lower() not in VALID_PRIORITIES:
        errors.append(f"Invalid priority '{priority}'. Must be one of: {sorted(list(VALID_PRIORITIES))}")
        
    # 4. List fields type check
    for list_field in ["requirements", "deliverables", "acceptance_criteria", "dependencies", "artifacts"]:
        if list_field in task and not isinstance(task[list_field], list):
            errors.append(f"Field '{list_field}' must be a list/array.")
            
    # 5. Dict fields type check
    if "metrics" in task and not isinstance(task["metrics"], dict):
        errors.append("Field 'metrics' must be a dictionary/object.")
        
    # 6. File path consistency checks
    if file_path:
        expected_stem = task.get("id")
        if file_path.stem != expected_stem:
            errors.append(f"Filename mismatch: file '{file_path.name}' does not match task id '{expected_stem}'")
            
        parent_dir_name = file_path.parent.name
        if parent_dir_name in VALID_STATUSES and status != parent_dir_name:
            errors.append(f"Folder status mismatch: file is in 'tasks/{parent_dir_name}' but status is '{status}'")
            
    return errors

def validate_all_tasks(base_dir: Path = None) -> Tuple[int, int, List[str]]:
    if base_dir is None:
        base_dir = get_base_dir()
        
    tasks_dir = base_dir / "tasks"
    total_checked = 0
    all_errors = []
    
    if not tasks_dir.exists():
        return 0, 0, [f"Tasks directory not found: {tasks_dir}"]
        
    for status_folder in VALID_STATUSES:
        folder_path = tasks_dir / status_folder
        if not folder_path.exists():
            continue
            
        for task_file in folder_path.glob("*.json"):
            total_checked += 1
            try:
                with open(task_file, "r", encoding="utf-8") as f:
                    task_data = json.load(f)
                errs = validate_task_dict(task_data, task_file)
                if errs:
                    for err in errs:
                        all_errors.append(f"[{task_file.relative_to(base_dir)}] {err}")
            except Exception as e:
                all_errors.append(f"[{task_file.relative_to(base_dir)}] JSON parse error: {str(e)}")
                
    return total_checked, len(all_errors), all_errors

def main():
    base_dir = get_base_dir()
    print(f"--- Validating Tasks in {base_dir / 'tasks'} ---")
    total, err_count, errors = validate_all_tasks(base_dir)
    print(f"Total tasks checked: {total}")
    
    if errors:
        print(f"\nFAILED with {err_count} error(s):")
        for e in errors:
            print(f"  ❌ {e}")
        sys.exit(1)
    else:
        print("✅ All tasks passed contract validation!")
        sys.exit(0)

if __name__ == "__main__":
    main()
