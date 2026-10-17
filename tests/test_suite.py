#!/usr/bin/env python3
"""
Affiliate Automation Smoke Test Suite
Runs all 7 required validation and lifecycle tests:
1. Task validation test
2. Create task test
3. Claim task test
4. Complete task into review test
5. Daily task generation test
6. Duplicate prevention test
7. Dashboard startup smoke test
"""

import sys
import os
import json
import time
import shutil
import urllib.request
import threading
from pathlib import Path

# Safe encoding on Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add scripts to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

from validate_tasks import validate_task_dict, validate_all_tasks
from create_task import create_task
from claim_task import claim_task
from complete_task import complete_task
from fail_task import fail_task
from daily_tasks import generate_daily_tasks, get_existing_tasks_for_date
from serve_dashboard import run_server

def test_1_task_validation():
    print("▶ Running Test 1: Task Validation...")
    # Validate a good task
    valid_task = {
        "id": "AFF-TEST-001",
        "type": "product_research",
        "executor": "antigravity",
        "goal": "Test goal",
        "context": "Test context",
        "requirements": ["req1"],
        "deliverables": ["del1"],
        "acceptance_criteria": ["acc1"],
        "priority": "high",
        "dependencies": [],
        "suggested_branch": "task/AFF-TEST-001",
        "status": "queued",
        "created_at": "2026-10-18T00:00:00Z",
        "started_at": None,
        "completed_at": None,
        "result": None,
        "artifacts": [],
        "metrics": {}
    }
    errs = validate_task_dict(valid_task)
    assert len(errs) == 0, f"Expected 0 errors, got: {errs}"

    # Validate an invalid task
    invalid_task = valid_task.copy()
    invalid_task.pop("id")
    invalid_task["status"] = "invalid_status"
    errs2 = validate_task_dict(invalid_task)
    assert any("Missing required field: 'id'" in e for e in errs2), "Failed to catch missing id"
    assert any("Invalid status" in e for e in errs2), "Failed to catch invalid status"
    print("  ✅ Task validation passed.")
    return True

def test_2_create_task():
    print("▶ Running Test 2: Create Task...")
    test_id = "AFF-SMOKE-001"
    # Ensure cleaned up first
    for sub in ["queued", "running", "review", "done", "failed"]:
        p = BASE_DIR / "tasks" / sub / f"{test_id}.json"
        if p.exists():
            p.unlink()

    path = create_task(
        task_id=test_id,
        task_type="product_research",
        goal="Smoke test task creation",
        priority="high",
        base_dir=BASE_DIR
    )
    assert path.exists(), f"Created file does not exist: {path}"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["id"] == test_id
    assert data["status"] == "queued"
    print(f"  ✅ Created task verified: {path.name}")
    return True

def test_3_claim_task():
    print("▶ Running Test 3: Claim Task...")
    test_id = "AFF-SMOKE-001"
    dest = claim_task(task_id=test_id, base_dir=BASE_DIR)
    assert dest is not None, "claim_task returned None"
    assert dest.exists(), f"Claimed task file does not exist: {dest}"
    assert dest.parent.name == "running", f"Task is not in tasks/running: {dest.parent}"

    with open(dest, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["status"] == "running"
    assert data["started_at"] is not None
    print(f"  ✅ Claimed task verified in running/: {dest.name}")
    return True

def test_4_complete_task_into_review():
    print("▶ Running Test 4: Complete Task into Review...")
    test_id = "AFF-SMOKE-001"
    review_dest = complete_task(
        task_id=test_id,
        executive_summary="Smoke test review executive summary",
        key_findings=["Finding A", "Finding B"],
        recommended_decision="TEST",
        confidence=0.9,
        base_dir=BASE_DIR
    )
    assert review_dest.exists(), f"Review task file not found: {review_dest}"
    assert review_dest.parent.name == "review", f"Task not in tasks/review: {review_dest.parent}"

    # Verify review package in results/
    review_json_path = BASE_DIR / "results" / f"{test_id}-review.json"
    assert review_json_path.exists(), f"Review result JSON not found: {review_json_path}"

    with open(review_json_path, "r", encoding="utf-8") as f:
        r_data = json.load(f)
    assert r_data["task_id"] == test_id
    assert r_data["recommended_decision"] == "TEST"

    # Clean up smoke test artifacts
    review_dest.unlink(missing_ok=True)
    review_json_path.unlink(missing_ok=True)
    print("  ✅ Complete task into review and results/ JSON verified.")
    return True

def test_5_daily_task_generation():
    print("▶ Running Test 5: Daily Task Generation...")
    smoke_date = "20269999"  # Dummy date so we don't interfere with real daily data
    # Clean any dummy files first
    for sub in ["queued", "running", "review", "done", "failed"]:
        for f in (BASE_DIR / "tasks" / sub).glob(f"AFF-{smoke_date}-*.json"):
            f.unlink()

    created = generate_daily_tasks(date_str=smoke_date, base_dir=BASE_DIR)
    assert len(created) == 4, f"Expected 4 created tasks, got {len(created)}"
    expected_ids = [f"AFF-{smoke_date}-001", f"AFF-{smoke_date}-002", f"AFF-{smoke_date}-003", f"AFF-{smoke_date}-004"]
    for eid in expected_ids:
        fpath = BASE_DIR / "tasks" / "queued" / f"{eid}.json"
        assert fpath.exists(), f"Expected task {eid} not found in queued/"

    print("  ✅ Daily task generation successfully created 4 tasks.")
    return True

def test_6_duplicate_prevention():
    print("▶ Running Test 6: Duplicate Prevention...")
    smoke_date = "20269999"
    # Attempting to re-run generate_daily_tasks for the same date without --force
    re_created = generate_daily_tasks(date_str=smoke_date, force=False, base_dir=BASE_DIR)
    assert len(re_created) == 0, f"Expected 0 re-created tasks due to duplicate prevention, got {len(re_created)}"

    # Clean up dummy tasks
    for sub in ["queued", "running", "review", "done", "failed"]:
        for f in (BASE_DIR / "tasks" / sub).glob(f"AFF-{smoke_date}-*.json"):
            f.unlink(missing_ok=True)

    print("  ✅ Duplicate prevention verified (0 duplicate tasks created).")
    return True

def test_7_dashboard_startup():
    print("▶ Running Test 7: Dashboard Startup Smoke Test...")
    port = 8765
    server_thread = threading.Thread(target=run_server, kwargs={"host": "127.0.0.1", "port": port, "single_request": True}, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    # Test GET /api/data
    url = f"http://127.0.0.1:{port}/api/data"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as response:
        assert response.status == 200, f"Dashboard returned status {response.status}"
        data = json.loads(response.read().decode("utf-8"))
        assert data["status"] == "healthy", f"Unexpected status: {data.get('status')}"
        assert "counts" in data, "Counts missing in API response"

    server_thread.join(timeout=2)
    print("  ✅ Dashboard startup and /api/data smoke test passed.")
    return True

def main():
    print("==================================================")
    print("AFFILIATE AUTOMATION SMOKE TEST SUITE")
    print("==================================================")
    results = {}
    tests = [
        ("1. Task Validation", test_1_task_validation),
        ("2. Create Task", test_2_create_task),
        ("3. Claim Task", test_3_claim_task),
        ("4. Complete Task into Review", test_4_complete_task_into_review),
        ("5. Daily Task Generation", test_5_daily_task_generation),
        ("6. Duplicate Prevention", test_6_duplicate_prevention),
        ("7. Dashboard Startup", test_7_dashboard_startup)
    ]

    all_passed = True
    for name, t_func in tests:
        try:
            passed = t_func()
            results[name] = "PASSED" if passed else "FAILED"
        except Exception as e:
            print(f"  ❌ {name} FAILED: {e}")
            results[name] = f"FAILED: {e}"
            all_passed = False

    print("\n---------------- TEST SUMMARY ----------------")
    for name, res in results.items():
        print(f"  {name}: {res}")
    print("----------------------------------------------")

    if all_passed:
        print("🎉 ALL 7 TESTS PASSED!")
        sys.exit(0)
    else:
        print("💥 SOME TESTS FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
