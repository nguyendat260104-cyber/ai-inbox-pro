#!/usr/bin/env python3
"""
Automated End-to-End (E2E) Test Suite for AI Inbox & Sales Management Platform
Spins up local HTTP server on a test port, simulates customer chat, tests grounded bot responses,
lead qualification, human takeover, and sales metrics tracking.
"""

import sys
import json
import time
import threading
import urllib.request
import urllib.error
from pathlib import Path
from http.server import HTTPServer

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from ai_inbox.core.db import init_db
from scripts.serve_inbox import seed_demo_data
from ai_inbox.api.server import InboxRequestHandler

TEST_PORT = 8991
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"

def post_json(path: str, data: dict) -> dict:
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_json(path: str) -> dict:
    url = f"{BASE_URL}{path}"
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_status(path: str) -> int:
    url = f"{BASE_URL}{path}"
    with urllib.request.urlopen(url) as resp:
        return resp.status

def run_e2e():
    print("==================================================")
    print("AI INBOX & SALES MANAGEMENT PLATFORM - E2E TESTS")
    print("==================================================")

    init_db()
    seed_demo_data()

    # Start test server in background thread
    server = HTTPServer(("127.0.0.1", TEST_PORT), InboxRequestHandler)
    t = threading.Thread(target=server.serve_forever)
    t.daemon = True
    t.start()
    time.sleep(0.5)

    try:
        # Test 1: Static Route Health Checks
        print("▶ Running Test 1: Static Routes (/admin, /demo, /widget)...")
        assert get_status("/") == 200, "Admin route should return 200"
        assert get_status("/demo") == 200, "Demo store route should return 200"
        assert get_status("/widget/chat_widget.js") == 200, "Widget JS should return 200"
        assert get_status("/widget/chat_widget.css") == 200, "Widget CSS should return 200"
        print("  ✅ All frontend & widget assets online.")

        # Test 2: Product Catalog API
        print("▶ Running Test 2: Product Catalog Lookup...")
        prods = get_json("/api/dashboard/products")
        assert len(prods.get("products", [])) >= 3, "Demo products should be present"
        polo = next(p for p in prods["products"] if p["sku"] == "POLO-CLASSIC")
        assert polo["price_vnd"] == 250000
        print(f"  ✅ Verified {len(prods['products'])} active products in grounded catalog.")

        # Test 3: Customer Sends Inquiry Message via Widget
        print("▶ Running Test 3: Customer Chat Inquiry & Grounded Bot Reply...")
        chat1 = post_json("/api/widget/message", {
            "workspace_id": "ws-01",
            "customer_text": "Áo polo nam còn size M không, ship Đà Nẵng bao nhiêu?"
        })
        conv_id = chat1.get("conversation_id")
        assert conv_id is not None, "Should generate conversation_id"
        assert chat1["bot_replied"] is True
        assert "250,000đ" in chat1["response"], "Must quote verified price"
        assert "25k" in chat1["response"], "Must quote verified shipping"
        print(f"  ✅ Bot replied accurately. Conversation ID: {conv_id}")

        # Test 4: Customer Places Order -> Triggers HOT Lead Handoff
        print("▶ Running Test 4: Customer Order Intent & HOT Lead Handoff...")
        chat2 = post_json("/api/widget/message", {
            "workspace_id": "ws-01",
            "conversation_id": conv_id,
            "customer_text": "Cho mình 1 áo màu Đen size M nhé, ship về 123 Nguyễn Văn Linh Đà Nẵng."
        })
        assert chat2["human_handoff_triggered"] is True, "Must trigger human handoff"
        assert chat2["intent_label"] == "HOT"
        assert chat2["conversation_status"] == "assigned_human"
        print(f"  ✅ HOT Lead flagged (Score: {chat2['score']}/100). Handoff triggered successfully.")

        # Test 5: Verify Dashboard Inbox & Lead Kanban State
        print("▶ Running Test 5: Dashboard Inbox & Kanban Synchronization...")
        inbox = get_json("/api/dashboard/inbox")
        conv_entry = next((c for c in inbox.get("conversations", []) if c["id"] == conv_id), None)
        assert conv_entry is not None, "Conversation must appear in inbox"
        assert conv_entry["intent_label"] == "HOT"

        kanban = get_json("/api/dashboard/leads/kanban")
        assigned_leads = kanban.get("stages", {}).get("assigned", [])
        assert any(l["conversation_id"] == conv_id for l in assigned_leads), "Lead must be in 'assigned' column"
        lead_id = next(l["id"] for l in assigned_leads if l["conversation_id"] == conv_id)
        print(f"  ✅ Inbox & Kanban synchronized. Lead ID: {lead_id}")

        # Test 6: Human Staff Takeover & Manual Reply
        print("▶ Running Test 6: Staff Takeover & Human Reply...")
        takeover = post_json(f"/api/dashboard/conversations/{conv_id}/takeover", {"staff_id": "staff-01"})
        assert takeover.get("success") is True

        reply = post_json(f"/api/dashboard/conversations/{conv_id}/reply", {
            "staff_name": "Tuấn Sale",
            "message": "Dạ em chào anh, em là Tuấn phụ trách đơn. Em đã giữ 1 áo Polo Đen size M cho anh rồi ạ!"
        })
        assert reply.get("success") is True

        history = get_json(f"/api/widget/history?conversation_id={conv_id}")
        assert any(m["sender_type"] == "staff" for m in history.get("messages", [])), "Staff message must be in history"
        print("  ✅ Staff takeover and manual message delivery confirmed.")

        # Test 7: Closing Lead to 'Won' & Checking Revenue Metrics
        print("▶ Running Test 7: Closing Deal & Measuring Metrics...")
        stage_update = post_json(f"/api/dashboard/leads/{lead_id}/stage", {"stage": "won"})
        assert stage_update.get("success") is True

        metrics = get_json("/api/dashboard/metrics")
        assert metrics.get("won_deals", 0) >= 1, "Won deals count must be at least 1"
        assert metrics.get("won_revenue_vnd", 0) >= 250000, "Won revenue must be recorded"
        print(f"  ✅ Deal marked WON! Total Revenue: {metrics['won_revenue_vnd']:,}đ, Conversion: {metrics['conversion_rate_pct']}%")

        print("\n----------------------------------------------")
        print("🎉 ALL 7 E2E INTEGRATION TESTS PASSED (100%)!")
        print("----------------------------------------------")

    finally:
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    run_e2e()
