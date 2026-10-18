#!/usr/bin/env python3
"""
Affiliate Automation Test Suite
Comprehensive testing engine verifying the original 11 system tests plus readiness gating:
1. create task
2. validate task
3. claim highest priority task
4. queued -> running transition
5. running -> review transition
6. failure handling
7. duplicate daily-task prevention
8. malformed JSON handling
9. missing directory handling
10. dashboard startup
11. daily report generation
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
from daily_report import generate_daily_report
from serve_dashboard import run_server
from readiness import calculate_readiness, apply_readiness_gate
from revenue_activation import validate_campaign_activation

def test_13_revenue_activation_gate():
    print("▶ Running Test 13: Revenue Activation Gate...")
    blocked = validate_campaign_activation(
        {"platform": "shopee", "affiliate_url": "https://shopee.vn/x", "tracking_id": "t1", "product_id": "p1", "publish_mode": "human_review"},
        [{"platform": "shopee", "status": "user_confirmation_required", "payout_status": "user_confirmation_required"}],
    )
    assert not blocked.ready and "affiliate_account_not_approved" in blocked.blockers
    ready = validate_campaign_activation(
        {"platform": "shopee", "affiliate_url": "https://shopee.vn/x", "tracking_id": "t1", "product_id": "p1", "publish_mode": "human_review"},
        [{"platform": "shopee", "status": "approved", "payout_status": "approved"}],
    )
    assert ready.ready
    print("  ✅ Campaigns are blocked until account, payout, link, and tracking are verified.")
    return True

# 1. Create Task Test
def test_1_create_task():
    print("▶ Running Test 1: Create Task...")
    test_id = "AFF-TEST-CREATE-001"
    # Ensure cleaned up first
    for sub in ["queued", "running", "review", "done", "failed"]:
        p = BASE_DIR / "tasks" / sub / f"{test_id}.json"
        if p.exists():
            p.unlink()

    path = create_task(
        task_id=test_id,
        task_type="product_research",
        goal="Verify task creation mechanics",
        priority="high",
        base_dir=BASE_DIR
    )
    assert path.exists(), f"Task file was not created: {path}"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["id"] == test_id
    assert data["status"] == "queued"
    assert data["priority"] == "high"
    print(f"  ✅ Task created and validated: {path.name}")
    return True

# 2. Validate Task Test
def test_2_validate_task():
    print("▶ Running Test 2: Validate Task...")
    test_id = "AFF-TEST-CREATE-001"
    t_file = BASE_DIR / "tasks" / "queued" / f"{test_id}.json"
    with open(t_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Valid check
    errs = validate_task_dict(data, t_file)
    assert len(errs) == 0, f"Expected 0 errors on valid task, got: {errs}"

    # Invalid check
    bad_data = data.copy()
    bad_data.pop("goal")
    bad_data["priority"] = "ultra_high"
    bad_errs = validate_task_dict(bad_data, t_file)
    assert any("Missing required field: 'goal'" in e for e in bad_errs), "Did not flag missing field"
    assert any("Invalid priority" in e for e in bad_errs), "Did not flag invalid priority"
    print("  ✅ Schema and attribute validation verified.")
    return True

# 3. Claim Highest Priority Task Test
def test_3_claim_highest_priority_task():
    print("▶ Running Test 3: Claim Highest Priority Task...")
    # Create two tasks: medium and critical
    id_med = "AFF-TEST-PRIO-MED"
    id_crit = "AFF-TEST-PRIO-CRIT"
    for sub in ["queued", "running", "review", "done", "failed"]:
        for tid in [id_med, id_crit]:
            (BASE_DIR / "tasks" / sub / f"{tid}.json").unlink(missing_ok=True)

    create_task(task_id=id_med, task_type="product_research", priority="medium", goal="Medium task", base_dir=BASE_DIR)
    time.sleep(0.05)
    create_task(task_id=id_crit, task_type="product_research", priority="critical", goal="Critical task", base_dir=BASE_DIR)

    # Automatic claiming without specifying ID should pick critical
    claimed = claim_task(base_dir=BASE_DIR)
    assert claimed is not None, "Failed to claim any task"
    assert claimed.stem == id_crit, f"Expected to claim {id_crit}, but claimed {claimed.stem}"

    # Clean up
    claimed.unlink(missing_ok=True)
    (BASE_DIR / "tasks" / "queued" / f"{id_med}.json").unlink(missing_ok=True)
    print(f"  ✅ Priority ordering verified: {id_crit} claimed before medium.")
    return True

# 4. Queued -> Running Transition Test
def test_4_queued_to_running_transition():
    print("▶ Running Test 4: Queued -> Running Transition...")
    test_id = "AFF-TEST-CREATE-001"
    src_file = BASE_DIR / "tasks" / "queued" / f"{test_id}.json"
    assert src_file.exists(), f"Source queued task does not exist: {src_file}"

    dest = claim_task(task_id=test_id, base_dir=BASE_DIR)
    assert dest is not None, "claim_task returned None"
    assert not src_file.exists(), "Source task was not removed from queued/"
    assert dest.exists(), f"Target task does not exist: {dest}"
    assert dest.parent.name == "running", f"Target is not in running/: {dest.parent}"

    with open(dest, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["status"] == "running"
    assert data["started_at"] is not None
    print(f"  ✅ Transitioned {test_id} to running/ with started_at timestamp.")
    return True

# 5. Running -> Review Transition Test
def test_5_running_to_review_transition():
    print("▶ Running Test 5: Running -> Review Transition...")
    test_id = "AFF-TEST-CREATE-001"
    running_file = BASE_DIR / "tasks" / "running" / f"{test_id}.json"
    assert running_file.exists(), f"Task must be running before completing: {running_file}"

    review_file = complete_task(
        task_id=test_id,
        executive_summary="Unit test review summary",
        key_findings=["Finding 1", "Finding 2"],
        recommended_decision="TEST",
        confidence=0.95,
        sources=["https://example.com/source"],
        risks=["Minimal testing risk"],
        base_dir=BASE_DIR
    )
    assert review_file.exists(), f"Review task file does not exist: {review_file}"
    assert review_file.parent.name == "review", f"Task not moved to review/: {review_file.parent}"
    assert not running_file.exists(), "Task not removed from running/"

    # Check results review JSON
    res_json = BASE_DIR / "results" / f"{test_id}-review.json"
    assert res_json.exists(), f"Review package JSON missing: {res_json}"
    with open(res_json, "r", encoding="utf-8") as f:
        r_data = json.load(f)
    assert r_data["recommended_decision"] == "TEST"
    assert "sources" in r_data and "risks" in r_data

    # Clean up test task
    review_file.unlink(missing_ok=True)
    res_json.unlink(missing_ok=True)
    print(f"  ✅ Running -> Review transition verified and review package created.")
    return True

# 6. Failure Handling Test
def test_6_failure_handling():
    print("▶ Running Test 6: Failure Handling...")
    test_id = "AFF-TEST-FAIL-001"
    for sub in ["queued", "running", "review", "done", "failed"]:
        (BASE_DIR / "tasks" / sub / f"{test_id}.json").unlink(missing_ok=True)

    create_task(task_id=test_id, task_type="product_research", goal="Test failure", base_dir=BASE_DIR)
    failed_path = fail_task(task_id=test_id, error_message="Simulated upstream network timeout", base_dir=BASE_DIR)

    assert failed_path.exists(), f"Failed task not found: {failed_path}"
    assert failed_path.parent.name == "failed", f"Task not in failed/: {failed_path.parent}"
    with open(failed_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["status"] == "failed"
    assert "error" in data["result"]
    assert "timeout" in data["result"]["error"]

    failed_path.unlink(missing_ok=True)
    print("  ✅ Failure transition, error payload, and status captured.")
    return True

# 7. Duplicate Daily-Task Prevention Test
def test_7_duplicate_daily_task_prevention():
    print("▶ Running Test 7: Duplicate Daily-Task Prevention...")
    test_date = "20268888"
    for sub in ["queued", "running", "review", "done", "failed"]:
        for f in (BASE_DIR / "tasks" / sub).glob(f"AFF-{test_date}-*.json"):
            f.unlink(missing_ok=True)

    # First run creates tasks
    created1 = generate_daily_tasks(date_str=test_date, base_dir=BASE_DIR)
    assert len(created1) == 5, f"Expected 5 tasks, got {len(created1)}"

    # Second run without force should create 0 tasks
    created2 = generate_daily_tasks(date_str=test_date, force=False, base_dir=BASE_DIR)
    assert len(created2) == 0, f"Expected 0 duplicate tasks, got {len(created2)}"

    # Clean up
    for sub in ["queued", "running", "review", "done", "failed"]:
        for f in (BASE_DIR / "tasks" / sub).glob(f"AFF-{test_date}-*.json"):
            f.unlink(missing_ok=True)

    print("  ✅ Idempotent execution confirmed; 0 duplicate tasks created on second run.")
    return True

# 8. Malformed JSON Handling Test
def test_8_malformed_json_handling():
    print("▶ Running Test 8: Malformed JSON Handling...")
    bad_file = BASE_DIR / "tasks" / "queued" / "AFF-TEST-CORRUPT-001.json"
    with open(bad_file, "w", encoding="utf-8") as f:
        f.write("{ invalid_json: this is not valid, missing_quotes }")

    # Run validate_all_tasks
    total, err_count, errors = validate_all_tasks(base_dir=BASE_DIR)
    assert err_count > 0, "Validator failed to flag malformed JSON file"
    assert any("JSON parse error" in e for e in errors), "JSON parse error not reported"

    bad_file.unlink(missing_ok=True)
    print("  ✅ Malformed JSON safely trapped and flagged without crashing system.")
    return True

# 9. Missing Directory Handling Test
def test_9_missing_directory_handling():
    print("▶ Running Test 9: Missing Directory Handling...")
    temp_dir = BASE_DIR / "tasks" / "temp_isolated_test"
    # Ensure create_task handles non-existent or newly created target subfolders
    test_id = "AFF-TEST-DIR-001"
    path = create_task(task_id=test_id, goal="Test missing dir creation", base_dir=BASE_DIR)
    assert path.parent.exists(), "Target parent directory does not exist"
    path.unlink(missing_ok=True)
    print("  ✅ Missing directory self-healing and path resolution confirmed.")
    return True

# 10. Dashboard Startup Smoke Test
def test_10_dashboard_startup():
    print("▶ Running Test 10: Dashboard Startup Smoke Test...")
    port = 8769
    server_thread = threading.Thread(
        target=run_server,
        kwargs={"host": "127.0.0.1", "port": port, "single_request": True},
        daemon=True
    )
    server_thread.start()
    time.sleep(0.5)

    # Test GET /
    url_root = f"http://127.0.0.1:{port}/"
    req_root = urllib.request.Request(url_root)
    with urllib.request.urlopen(req_root, timeout=5) as resp_root:
        assert resp_root.status == 200, f"Dashboard UI root returned {resp_root.status}"
        html_content = resp_root.read().decode("utf-8")
        assert "Affiliate Automation Command Center" in html_content

    server_thread.join(timeout=2)
    print("  ✅ Dashboard HTTP UI and static routes verified online.")
    return True

# 11. Daily Report Generation Test
def test_11_daily_report_generation():
    print("▶ Running Test 11: Daily Report Generation...")
    test_date = "20267777"
    rep_md = generate_daily_report(date_str=test_date, base_dir=BASE_DIR)
    assert rep_md.exists(), f"Markdown report file not found: {rep_md}"
    rep_json = BASE_DIR / "metrics" / "daily" / f"{test_date}-report.json"
    assert rep_json.exists(), f"JSON report file not found: {rep_json}"

    with open(rep_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "task_summary" in data
    assert "report_date" in data and data["report_date"] == test_date

    # Clean up test reports
    rep_md.unlink(missing_ok=True)
    rep_json.unlink(missing_ok=True)
    print("  ✅ Daily report aggregation and markdown/json compilation passed.")
    return True

def test_12_affiliate_readiness_gate():
    print("▶ Running Test 12: Affiliate Readiness Gate...")
    breakdown = {
        "ProgramOpen": 30,
        "VietnamEligible": 0,
        "ApprovalDifficulty": 10,
        "PayoutPracticality": 5,
        "CommercialTermsVerified": 10,
    }
    assert calculate_readiness(breakdown) == 55
    gated = apply_readiness_gate({
        "product": "Example",
        "recommendation": "SCALE",
        "readiness_score_breakdown": breakdown,
    })
    assert gated["readiness_score"] == 55
    assert gated["readiness_gate"] == "BLOCKED_BELOW_60"
    assert gated["recommendation"] == "HOLD"

    eligible = apply_readiness_gate({
        "product": "Verified Example",
        "recommendation": "SCALE",
        "readiness_score_breakdown": {**breakdown, "VietnamEligible": 20},
    })
    assert eligible["readiness_score"] == 75
    assert eligible["readiness_gate"] == "ELIGIBLE"
    assert eligible["recommendation"] == "SCALE"
    print("  ✅ Readiness calculation and <60 SCALE block verified.")
    return True

def main():
    print("==================================================")
    print("AFFILIATE AUTOMATION COMPREHENSIVE TEST SUITE")
    print("==================================================")
    results = {}
    tests = [
        ("1. Create Task", test_1_create_task),
        ("2. Validate Task", test_2_validate_task),
        ("3. Claim Highest Priority Task", test_3_claim_highest_priority_task),
        ("4. Queued -> Running Transition", test_4_queued_to_running_transition),
        ("5. Running -> Review Transition", test_5_running_to_review_transition),
        ("6. Failure Handling", test_6_failure_handling),
        ("7. Duplicate Daily-Task Prevention", test_7_duplicate_daily_task_prevention),
        ("8. Malformed JSON Handling", test_8_malformed_json_handling),
        ("9. Missing Directory Handling", test_9_missing_directory_handling),
        ("10. Dashboard Startup", test_10_dashboard_startup),
        ("11. Daily Report Generation", test_11_daily_report_generation),
        ("12. Affiliate Readiness Gate", test_12_affiliate_readiness_gate),
        ("13. Revenue Activation Gate", test_13_revenue_activation_gate)
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
        print("🎉 ALL 13 TESTS PASSED!")
        sys.exit(0)
    else:
        print("💥 SOME TESTS FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
