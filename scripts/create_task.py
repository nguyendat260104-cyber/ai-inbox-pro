#!/usr/bin/env python3
"""
Task Creation Script
Creates and registers a new task adhering strictly to the Affiliate Automation contract.
Saves the task directly to tasks/queued/<task_id>.json.
"""

import sys
import os
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from validate_tasks import validate_task_dict, get_base_dir

def get_next_task_id(base_dir: Path, date_str: str) -> str:
    """Finds next available ID for the given date (e.g. AFF-20261018-001)"""
    tasks_dir = base_dir / "tasks"
    existing_indices = []
    prefix = f"AFF-{date_str}-"
    
    # Check all subfolders for existing task files with this prefix
    for sub in ["queued", "running", "review", "done", "failed"]:
        folder = tasks_dir / sub
        if folder.exists():
            for f in folder.glob(f"{prefix}*.json"):
                # Extract number part
                parts = f.stem.split("-")
                if len(parts) >= 3 and parts[-1].isdigit():
                    existing_indices.append(int(parts[-1]))
                    
    next_index = max(existing_indices) + 1 if existing_indices else 1
    return f"{prefix}{next_index:03d}"

def create_task(
    task_id: str = None,
    task_type: str = "product_research",
    goal: str = "",
    context: str = "",
    requirements: List[str] = None,
    deliverables: List[str] = None,
    acceptance_criteria: List[str] = None,
    priority: str = "high",
    dependencies: List[str] = None,
    template_path: str = None,
    executor: str = "antigravity",
    base_dir: Path = None
) -> Path:
    if base_dir is None:
        base_dir = get_base_dir()

    today_str = datetime.now().astimezone().strftime("%Y%m%d")
    now_iso = datetime.now(timezone.utc).isoformat()
    
    task_data: Dict[str, Any] = {}

    # Load from template if provided or if matches known types
    if template_path:
        tpl_file = Path(template_path)
        if not tpl_file.is_absolute():
            tpl_file = base_dir / tpl_file
        if tpl_file.exists():
            with open(tpl_file, "r", encoding="utf-8") as f:
                task_data = json.load(f)
    elif task_type:
        default_tpl = base_dir / "templates" / f"{task_type.split('_')[0]}_task.json"
        if default_tpl.exists():
            with open(default_tpl, "r", encoding="utf-8") as f:
                task_data = json.load(f)

    # Resolve ID
    if not task_id:
        task_id = get_next_task_id(base_dir, today_str)

    # Populate/override fields
    task_data["id"] = task_id
    task_data["type"] = task_type or task_data.get("type", "product_research")
    task_data["executor"] = executor or task_data.get("executor", "antigravity")
    if goal:
        task_data["goal"] = goal
    elif "goal" not in task_data:
        task_data["goal"] = "Unspecified goal"

    if context:
        task_data["context"] = context
    elif "context" not in task_data:
        task_data["context"] = "Execution context"

    if requirements is not None:
        task_data["requirements"] = requirements
    elif "requirements" not in task_data:
        task_data["requirements"] = []

    if deliverables is not None:
        task_data["deliverables"] = deliverables
    elif "deliverables" not in task_data:
        task_data["deliverables"] = []

    if acceptance_criteria is not None:
        task_data["acceptance_criteria"] = acceptance_criteria
    elif "acceptance_criteria" not in task_data:
        task_data["acceptance_criteria"] = []

    task_data["priority"] = priority or task_data.get("priority", "high")
    task_data["dependencies"] = dependencies if dependencies is not None else task_data.get("dependencies", [])
    task_data["suggested_branch"] = f"task/{task_id}"
    task_data["status"] = "queued"
    task_data["created_at"] = now_iso
    task_data["started_at"] = None
    task_data["completed_at"] = None
    task_data["result"] = None
    task_data["artifacts"] = task_data.get("artifacts", [])
    task_data["metrics"] = task_data.get("metrics", {})

    target_path = base_dir / "tasks" / "queued" / f"{task_id}.json"
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Validate
    errors = validate_task_dict(task_data, target_path)
    if errors:
        raise ValueError(f"Task validation failed: {'; '.join(errors)}")

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(task_data, f, indent=2, ensure_ascii=False)

    return target_path

def main():
    parser = argparse.ArgumentParser(description="Create a new affiliate automation task.")
    parser.add_argument("--id", help="Task ID (e.g. AFF-20261018-001). Auto-generated if omitted.")
    parser.add_argument("--type", default="product_research", help="Task type (e.g. product_research, content_production)")
    parser.add_argument("--goal", help="Clear objective of the task")
    parser.add_argument("--context", help="Contextual background or constraints")
    parser.add_argument("--priority", default="high", choices=["critical", "high", "medium", "low"])
    parser.add_argument("--requirements", nargs="*", help="List of requirements")
    parser.add_argument("--deliverables", nargs="*", help="List of expected deliverables")
    parser.add_argument("--acceptance-criteria", nargs="*", help="List of acceptance criteria")
    parser.add_argument("--dependencies", nargs="*", help="List of dependent task IDs")
    parser.add_argument("--template", help="Path to template JSON file")

    args = parser.parse_args()

    try:
        path = create_task(
            task_id=args.id,
            task_type=args.type,
            goal=args.goal,
            context=args.context,
            requirements=args.requirements,
            deliverables=args.deliverables,
            acceptance_criteria=args.acceptance_criteria,
            priority=args.priority,
            dependencies=args.dependencies,
            template_path=args.template
        )
        print(f"✅ Created task: {path.name} in {path.parent}")
    except Exception as e:
        print(f"❌ Error creating task: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
