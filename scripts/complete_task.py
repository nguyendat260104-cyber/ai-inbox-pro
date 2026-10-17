#!/usr/bin/env python3
"""
Complete Task Script
Transitions a running task into 'review' status once acceptance criteria and artifacts are verified.
Moves task JSON from tasks/running/ to tasks/review/.
Ensures results/<task_id>-review.json exists or generates a standardized review package for ChatGPT.
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

def complete_task(
    task_id: str,
    executive_summary: str = "",
    key_findings: Optional[List[str]] = None,
    recommended_decision: str = "TEST",
    confidence: float = 0.85,
    artifacts: Optional[List[str]] = None,
    business_metrics: Optional[Dict[str, Any]] = None,
    questions_for_lead: Optional[List[str]] = None,
    next_task_suggestions: Optional[List[str]] = None,
    review_file: Optional[str] = None,
    base_dir: Optional[Path] = None
) -> Path:
    if base_dir is None:
        base_dir = get_base_dir()

    running_dir = base_dir / "tasks" / "running"
    review_dir = base_dir / "tasks" / "review"
    results_dir = base_dir / "results"
    review_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    task_file = running_dir / f"{task_id}.json"
    if not task_file.exists():
        raise FileNotFoundError(f"Task '{task_id}' not found in tasks/running/ ({task_file})")

    with open(task_file, "r", encoding="utf-8") as f:
        task_data = json.load(f)

    now_iso = datetime.now(timezone.utc).isoformat()

    # Load or create review result package
    review_data = {}
    review_target_path = results_dir / f"{task_id}-review.json"

    if review_file:
        rf_path = Path(review_file)
        if not rf_path.is_absolute():
            rf_path = base_dir / rf_path
        if rf_path.exists():
            with open(rf_path, "r", encoding="utf-8") as f:
                review_data = json.load(f)
        else:
            raise FileNotFoundError(f"Specified review file not found: {review_file}")
    elif review_target_path.exists():
        with open(review_target_path, "r", encoding="utf-8") as f:
            review_data = json.load(f)

    # Populate / override review fields
    review_data["task_id"] = task_id
    if executive_summary:
        review_data["executive_summary"] = executive_summary
    elif "executive_summary" not in review_data:
        review_data["executive_summary"] = f"Task {task_id} completed successfully. Ready for Lead review."

    if key_findings is not None:
        review_data["key_findings"] = key_findings
    elif "key_findings" not in review_data:
        review_data["key_findings"] = [f"Deliverables generated according to task requirements."]

    if recommended_decision:
        review_data["recommended_decision"] = recommended_decision
    elif "recommended_decision" not in review_data:
        review_data["recommended_decision"] = "TEST"

    if confidence is not None:
        review_data["confidence"] = confidence
    elif "confidence" not in review_data:
        review_data["confidence"] = 0.85

    if business_metrics is not None:
        review_data["business_metrics"] = business_metrics
    elif "business_metrics" not in review_data:
        review_data["business_metrics"] = {}

    final_artifacts = list(task_data.get("artifacts", []))
    if artifacts:
        for a in artifacts:
            if a not in final_artifacts:
                final_artifacts.append(a)
    review_data["artifacts"] = final_artifacts

    if questions_for_lead is not None:
        review_data["questions_for_lead"] = questions_for_lead
    elif "questions_for_lead" not in review_data:
        review_data["questions_for_lead"] = ["Lead review requested to approve next steps."]

    if next_task_suggestions is not None:
        review_data["next_task_suggestions"] = next_task_suggestions
    elif "next_task_suggestions" not in review_data:
        review_data["next_task_suggestions"] = ["Proceed to content or deep evaluation upon approval."]

    # Write review JSON
    with open(review_target_path, "w", encoding="utf-8") as f:
        json.dump(review_data, f, indent=2, ensure_ascii=False)

    # Update task JSON
    task_data["status"] = "review"
    task_data["completed_at"] = now_iso
    task_data["result"] = f"results/{task_id}-review.json"
    task_data["artifacts"] = final_artifacts
    if business_metrics:
        task_data["metrics"].update(business_metrics)

    dest_file = review_dir / f"{task_id}.json"

    # Validate
    errs = validate_task_dict(task_data, dest_file)
    if errs:
        raise ValueError(f"Task validation failed: {'; '.join(errs)}")

    with open(dest_file, "w", encoding="utf-8") as f:
        json.dump(task_data, f, indent=2, ensure_ascii=False)

    # Remove from running
    task_file.unlink()

    return dest_file

def main():
    parser = argparse.ArgumentParser(description="Transition a running task to review with a Lead handoff review package.")
    parser.add_argument("--id", required=True, help="Task ID (e.g. AFF-20261018-001)")
    parser.add_argument("--summary", default="", help="Executive summary")
    parser.add_argument("--decision", default="TEST", choices=["SCALE", "TEST", "RETEST", "KILL", "REVIEW"], help="Recommended decision")
    parser.add_argument("--confidence", type=float, default=0.85, help="Confidence score 0.0 - 1.0")
    parser.add_argument("--artifacts", nargs="*", help="List of artifact paths")
    parser.add_argument("--findings", nargs="*", help="Key findings")
    parser.add_argument("--questions", nargs="*", help="Questions for Lead review")
    parser.add_argument("--next-tasks", nargs="*", help="Next task suggestions")
    parser.add_argument("--review-file", help="Path to existing review JSON file")

    args = parser.parse_args()

    try:
        dest = complete_task(
            task_id=args.id,
            executive_summary=args.summary,
            key_findings=args.findings,
            recommended_decision=args.decision,
            confidence=args.confidence,
            artifacts=args.artifacts,
            questions_for_lead=args.questions,
            next_task_suggestions=args.next_tasks,
            review_file=args.review_file
        )
        print(f"✅ Successfully moved task to review: {dest.name}")
        print(f"Handoff review file: results/{args.id}-review.json")
    except Exception as e:
        print(f"❌ Error completing task: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
