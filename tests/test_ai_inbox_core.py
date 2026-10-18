#!/usr/bin/env python3
"""
Comprehensive Test Suite for AI Inbox & Sales Management Platform Core Engine
Tests grounded catalog retrieval, zero-hallucination guardrails, 5-step sales flow,
lead intent scoring, and human handoff mechanics.
"""

import sys
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root is in path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from ai_inbox.core.db import init_db, get_connection
from ai_inbox.engine.sales_agent import SalesAgent

TEST_DB_PATH = BASE_DIR / "data" / "test_inbox.db"

def setup_test_data(db_path: Path):
    """Seed test workspace, staff, and product catalog."""
    if db_path.exists():
        db_path.unlink()
    init_db(db_path)

    conn = get_connection(db_path)
    cur = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Workspace
    cur.execute(
        "INSERT INTO workspaces (id, name, slug, created_at) VALUES ('ws-01', 'Shop Thời Trang Trẻ', 'shop-tre', ?)",
        (now_iso,)
    )

    # 2. Staff
    cur.execute(
        "INSERT INTO staff (id, workspace_id, name, email, role, is_active, created_at) VALUES ('staff-01', 'ws-01', 'Tuấn Sale', 'tuan@shoptre.vn', 'sales_rep', 1, ?)",
        (now_iso,)
    )

    # 3. Product Catalog
    cur.execute(
        """INSERT INTO products (id, workspace_id, sku, name, category, price_vnd, stock_quantity, sizes_json, colors_json, description, shipping_policy, is_active, created_at)
           VALUES ('prod-polo-01', 'ws-01', 'POLO-CLASSIC', 'Áo Polo Nam Classic', 'Thời trang nam', 250000, 50,
                   '[\"M\", \"L\", \"XL\"]', '[\"Đen\", \"Trắng\", \"Xanh Navy\"]', 'Chất cotton 100% thoáng mát',
                   'Đồng giá ship 25k toàn quốc, miễn phí ship từ 2 chiếc.', 1, ?)""",
        (now_iso,)
    )

    # 4. Customer & Conversation
    cur.execute(
        "INSERT INTO customers (id, workspace_id, name, phone, channel, external_id, created_at, updated_at) VALUES ('cust-01', 'ws-01', 'Khách Facebook', '0912345678', 'web_widget', 'ext-101', ?, ?)",
        (now_iso, now_iso)
    )
    cur.execute(
        "INSERT INTO conversations (id, workspace_id, customer_id, channel, status, unread_count, last_message_at, created_at) VALUES ('conv-01', 'ws-01', 'cust-01', 'web_widget', 'bot_handling', 0, ?, ?)",
        (now_iso, now_iso)
    )

    conn.commit()
    conn.close()

def run_tests():
    print("==================================================")
    print("AI INBOX & SALES MANAGEMENT PLATFORM - CORE TESTS")
    print("==================================================")

    setup_test_data(TEST_DB_PATH)
    agent = SalesAgent(db_path=TEST_DB_PATH)

    # Test 1: Grounded product inquiry (Step 1-3)
    print("▶ Running Test 1: Customer asks about Size M & Shipping...")
    res1 = agent.handle_incoming_message(
        workspace_id="ws-01",
        conversation_id="conv-01",
        customer_text="Áo polo nam còn size M không, ship Đà Nẵng bao nhiêu?"
    )
    assert res1["bot_replied"] is True, "Bot should reply"
    assert "250,000đ" in res1["response"], f"Price must be grounded: {res1['response']}"
    assert "25k" in res1["response"], f"Shipping must be grounded: {res1['response']}"
    assert res1["score"] >= 40, f"Score should be at least warm: {res1['score']}"
    assert res1["intent_label"] in ["WARM", "HOT"]
    print("  ✅ Grounded catalog response & need probing verified.")

    # Test 2: Customer specifies color and makes purchase commitment (Step 4-5)
    print("▶ Running Test 2: Customer ready to buy & triggers HOT handoff...")
    res2 = agent.handle_incoming_message(
        workspace_id="ws-01",
        conversation_id="conv-01",
        customer_text="Cho mình 1 chiếc màu Đen size M nhé, gửi về 123 Nguyễn Văn Linh Đà Nẵng."
    )
    assert res2["bot_replied"] is True
    assert res2["human_handoff_triggered"] is True, "Must trigger human handoff"
    assert res2["intent_label"] == "HOT", f"Must be marked HOT: {res2['intent_label']}"
    assert res2["conversation_status"] == "assigned_human", "Status must become assigned_human"
    print(f"  ✅ HOT Lead detected (Score: {res2['score']}/100) and Human Handoff triggered.")

    # Test 3: Verify Human Staff Takeover (Bot stays silent once assigned to human)
    print("▶ Running Test 3: Human staff takeover silences bot...")
    res3 = agent.handle_incoming_message(
        workspace_id="ws-01",
        conversation_id="conv-01",
        customer_text="Alo shop ơi có ai ở đó không?"
    )
    assert res3["bot_replied"] is False, "Bot must remain silent after handoff"
    assert res3["reason"] == "human_staff_active"
    print("  ✅ Staff takeover verified: bot does not interrupt human agent.")

    # Test 4: Zero-Hallucination Guardrail Check
    print("▶ Running Test 4: Zero-Hallucination Guardrail Check...")
    # Create fresh conversation
    conn = get_connection(TEST_DB_PATH)
    cur = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    cur.execute(
        "INSERT INTO conversations (id, workspace_id, customer_id, channel, status, unread_count, last_message_at, created_at) VALUES ('conv-02', 'ws-01', 'cust-01', 'web_widget', 'bot_handling', 0, ?, ?)",
        (now_iso, now_iso)
    )
    conn.commit()
    conn.close()

    res4 = agent.handle_incoming_message(
        workspace_id="ws-01",
        conversation_id="conv-02",
        customer_text="Shop có bán iPhone 16 Pro Max không, giảm giá 50% cho mình được không?"
    )
    assert res4["bot_replied"] is True
    # Verify bot refuses to invent iPhone price or unauthorized discount
    assert "iPhone" not in res4["response"] or "chuyên các mặt hàng" in res4["response"]
    assert "niêm yết giá chuẩn" in res4["response"] or "chưa có" in res4["response"] or "không áp dụng giảm" in res4["response"]
    print("  ✅ Zero-hallucination guardrail verified: bot refuses unauthorized discounts and fake products.")

    print("\n----------------------------------------------")
    print("🎉 ALL 4 AI INBOX CORE TESTS PASSED (100%)!")
    print("----------------------------------------------")

    # Cleanup test db
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

if __name__ == "__main__":
    run_tests()
