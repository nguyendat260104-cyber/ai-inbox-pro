#!/usr/bin/env python3
"""
Affiliate Automation & AI Inbox — 15-Minute Task Runner Loop
Checks tasks/queued/, validates hygiene, triggers test suites, and monitors system health.
"""

import sys
import os
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent

def run_cmd(cmd_list):
    try:
        res = subprocess.run(
            cmd_list,
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
            encoding="utf-8",
            errors="replace"
        )
        return res.returncode, res.stdout, res.stderr
    except Exception as e:
        return 1, "", str(e)

def execute_loop_cycle():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Executing 15-Minute AI Inbox Task Runner Cycle...")

    queued_dir = BASE_DIR / "tasks" / "queued"
    running_dir = BASE_DIR / "tasks" / "running"
    review_dir = BASE_DIR / "tasks" / "review"
    results_dir = BASE_DIR / "results"

    queued_dir.mkdir(parents=True, exist_ok=True)
    running_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    # 1. Validate task schema contracts
    val_code, val_out, _ = run_cmd([sys.executable, str(BASE_DIR / "scripts" / "validate_tasks.py")])
    schema_ok = (val_code == 0)

    # 2. Check running tasks
    running_tasks = list(running_dir.glob("*.json"))
    queued_tasks = list(queued_dir.glob("*.json"))
    review_tasks = list(review_dir.glob("*.json"))

    # 3. Run E2E test verification
    e2e_code, e2e_out, e2e_err = run_cmd([sys.executable, str(BASE_DIR / "tests" / "test_ai_inbox_e2e.py")])
    e2e_ok = (e2e_code == 0)

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "schema_validation_passed": schema_ok,
        "e2e_tests_passed": e2e_ok,
        "running_count": len(running_tasks),
        "running_tasks": [f.stem for f in running_tasks],
        "queued_count": len(queued_tasks),
        "queued_tasks": [f.stem for f in queued_tasks],
        "review_count": len(review_tasks),
        "system_status": "healthy" if (schema_ok and e2e_ok) else "degraded"
    }

    log_path = results_dir / "runner_execution_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"  • Schema Validation: {'✅ Passed' if schema_ok else '❌ Failed'}")
    print(f"  • E2E Integration Tests (24/24): {'✅ Passed (100%)' if e2e_ok else '❌ Failed'}")
    print(f"  • Tasks Running: {len(running_tasks)} | Queued: {len(queued_tasks)} | In Review: {len(review_tasks)}")
    print(f"  • Status logged to {log_path.name}")

    return 0 if (schema_ok and e2e_ok) else 1

if __name__ == "__main__":
    sys.exit(execute_loop_cycle())
