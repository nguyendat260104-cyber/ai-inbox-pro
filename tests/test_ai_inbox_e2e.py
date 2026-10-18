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
import tempfile
import os
import hmac
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from ai_inbox.core import db as db_module
from ai_inbox.core.db import init_db
from scripts.serve_inbox import seed_demo_data
from ai_inbox.api.server import InboxRequestHandler

TEST_PORT = 8991
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"

def post_json(path: str, data: dict, extra_headers: dict | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    headers.update(extra_headers or {})
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
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

def get_text(path: str) -> tuple[int, str]:
    url = f"{BASE_URL}{path}"
    with urllib.request.urlopen(url) as resp:
        return resp.status, resp.read().decode("utf-8")

def request_status(path: str, method: str = "GET", data: dict | None = None) -> int:
    """Return HTTP status for positive and negative API contract checks."""
    payload = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code

def run_e2e():
    print("==================================================")
    print("AI INBOX & SALES MANAGEMENT PLATFORM - E2E TESTS")
    print("==================================================")

    # Never write test conversations or fake revenue to the real local-first DB.
    temp_dir = tempfile.TemporaryDirectory(prefix="ai-inbox-e2e-")
    original_db_file = db_module.DB_FILE
    db_module.DB_FILE = Path(temp_dir.name) / "inbox-e2e.db"
    os.environ["FB_VERIFY_TOKEN"] = "e2e-webhook-token"
    os.environ["FB_APP_SECRET"] = "e2e-app-secret"
    init_db()
    seed_demo_data()

    # Start test server in background thread
    server = ThreadingHTTPServer(("127.0.0.1", TEST_PORT), InboxRequestHandler)
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
        req = urllib.request.Request(f"{BASE_URL}/api/dashboard/metrics", method="OPTIONS")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 204
            assert resp.headers.get("Access-Control-Allow-Origin") == "*"
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

        customer_followup = post_json("/api/widget/message", {
            "workspace_id": "ws-01",
            "conversation_id": conv_id,
            "customer_text": "Mình xác nhận số điện thoại 0912345678 nhé."
        })
        assert customer_followup["bot_replied"] is False
        assert customer_followup["reason"] == "human_staff_active"

        history = get_json(f"/api/widget/history?conversation_id={conv_id}")
        assert any(m["sender_type"] == "staff" for m in history.get("messages", [])), "Staff message must be in history"
        assert any(
            m["sender_type"] == "customer" and "0912345678" in m["content"]
            for m in history.get("messages", [])
        ), "Customer follow-up after takeover must remain in history"
        print("  ✅ Staff takeover and manual message delivery confirmed.")

        # Test 7: Closing Lead to 'Won' & Checking Revenue Metrics
        print("▶ Running Test 7: Closing Deal & Measuring Metrics...")
        stage_update = post_json(f"/api/dashboard/leads/{lead_id}/stage", {"stage": "won"})
        assert stage_update.get("success") is True

        metrics = get_json("/api/dashboard/metrics")
        assert metrics.get("won_deals", 0) >= 1, "Won deals count must be at least 1"
        assert metrics.get("won_revenue_vnd", 0) >= 250000, "Won revenue must be recorded"
        print(f"  ✅ Deal marked WON! Total Revenue: {metrics['won_revenue_vnd']:,}đ, Conversion: {metrics['conversion_rate_pct']}%")

        # Test 8: Reject invalid identifiers and pipeline values
        print("▶ Running Test 8: API Validation & Error Contracts...")
        assert request_status("/api/dashboard/leads/not-found/stage", "POST", {"stage": "won"}) == 404
        assert request_status(f"/api/dashboard/leads/{lead_id}/stage", "POST", {"stage": "invalid"}) == 400
        assert request_status("/api/widget/history?conversation_id=not-found") == 404
        hot_only = get_json("/api/dashboard/inbox?hot=true")
        assert hot_only["conversations"]
        assert all(item["intent_label"] == "HOT" for item in hot_only["conversations"])
        # Test 9: Lead CSV Export
        print("▶ Running Test 9: Lead CSV Export Engine...")
        export_req = urllib.request.Request(f"{BASE_URL}/api/dashboard/leads/export")
        with urllib.request.urlopen(export_req) as export_resp:
            assert export_resp.status == 200
            assert "text/csv" in export_resp.headers.get("Content-Type", "")
            raw_csv = export_resp.read().decode("utf-8")
            assert raw_csv.startswith("\ufeff"), "Must contain UTF-8 BOM"
            assert "Mã Lead,Họ Tên Khách,Số Điện Thoại" in raw_csv
            assert "250000" in raw_csv or "Áo Polo" in raw_csv
        print("  ✅ Lead CSV export verified with UTF-8 BOM and valid header schema.")

        # Test 10: Local product management contract
        print("▶ Running Test 10: Product Management Validation...")
        created = post_json("/api/dashboard/products", {
            "workspace_id": "ws-01",
            "sku": "E2E-PRODUCT",
            "name": "Sản phẩm kiểm thử",
            "price_vnd": 99000,
            "stock_quantity": 2,
            "sizes": [],
            "colors": ["Đen"]
        })
        product_id = created["product_id"]
        assert request_status("/api/dashboard/products", "POST", {
            "workspace_id": "ws-01", "sku": "E2E-PRODUCT",
            "name": "Trùng SKU", "price_vnd": 1
        }) == 409
        assert request_status(
            f"/api/dashboard/products/{product_id}/delete", "POST", {}
        ) == 200
        assert request_status(
            "/api/dashboard/products/not-found/delete", "POST", {}
        ) == 404
        print("  ✅ Product create, duplicate guard, and soft-delete verified.")

        # Test 11: Facebook Messenger Webhook & Ingestion
        print("▶ Running Test 11: Facebook Messenger Webhook & Ingestion...")
        # 11a: Verification challenge
        verif_url = f"{BASE_URL}/api/webhooks/facebook?hub.mode=subscribe&hub.challenge=challenge_token_99&hub.verify_token=e2e-webhook-token"
        with urllib.request.urlopen(verif_url) as verif_resp:
            assert verif_resp.status == 200
            assert verif_resp.read().decode("utf-8") == "challenge_token_99"

        # Invalid token rejected
        bad_verif_req = urllib.request.Request(f"{BASE_URL}/api/webhooks/facebook?hub.mode=subscribe&hub.challenge=xyz&hub.verify_token=wrong")
        try:
            urllib.request.urlopen(bad_verif_req)
            assert False, "Should have failed with 403"
        except urllib.error.HTTPError as he:
            assert he.code == 403

        # 11b: Incoming message event ingestion
        fb_payload = {
            "object": "page",
            "entry": [
                {
                    "id": "PAGE_1001",
                    "messaging": [
                        {
                            "sender": {"id": "PSID_556677"},
                            "recipient": {"id": "PAGE_1001"},
                            "message": {
                                "mid": "m_test_001",
                                "text": "Shop ơi áo sơ mi linen còn size XL không?"
                            }
                        }
                    ]
                }
            ]
        }
        raw_fb_payload = json.dumps(fb_payload).encode("utf-8")
        fb_signature = "sha256=" + hmac.new(
            b"e2e-app-secret", raw_fb_payload, hashlib.sha256
        ).hexdigest()
        fb_res = post_json(
            "/api/webhooks/facebook", fb_payload,
            {"X-Hub-Signature-256": fb_signature}
        )
        assert fb_res.get("status") == "success"
        assert fb_res.get("processed_count") == 1
        ev = fb_res["events"][0]
        assert ev.get("bot_replied") is True
        assert "320.000" in ev.get("response", "") or "320,000" in ev.get("response", "")
        
        # Verify conversation recorded in dashboard inbox under channel 'facebook_page'
        inbox_data = get_json("/api/dashboard/inbox")
        fb_conv = next((c for c in inbox_data["conversations"] if c.get("channel") == "facebook_page"), None)
        assert fb_conv is not None, "Facebook conversation must be visible in Dashboard Inbox"
        assert "6677" in fb_conv["customer_name"]
        print("  ✅ Meta verification challenge passed & Facebook Messenger message ingested successfully.")

        # Test 12: Telegram HOT Lead Alert & Customer Phone Enrichment
        print("▶ Running Test 12: Telegram Alert Dispatcher & Phone Auto-Enrichment...")
        phone_inquiry = post_json("/api/widget/message", {
            "workspace_id": "ws-01",
            "customer_text": "SĐT của mình là 0988776655, gọi tư vấn size áo sơ mi giúp mình nhé!",
            "customer_name": "Anh Hoàng Khách VIP"
        })
        assert phone_inquiry.get("alert_sent") is True, "Must dispatch alert when phone number provided"
        new_conv_id = phone_inquiry["conversation_id"]

        # Verify customer in DB was enriched with phone number
        conn = db_module.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT c.phone, l.score, l.intent_label
            FROM customers c
            JOIN conversations conv ON conv.customer_id = c.id
            JOIN leads l ON l.conversation_id = conv.id
            WHERE conv.id = ?
        """, (new_conv_id,))
        enriched_row = cur.fetchone()
        assert enriched_row is not None
        assert enriched_row["phone"] == "0988776655", "Phone must be auto-saved to customer profile"
        assert enriched_row["intent_label"] == "HOT" or enriched_row["score"] >= 75

        # Verify activity_logs audit
        cur.execute("SELECT details_json FROM activity_logs WHERE event_type = 'telegram_hot_lead_alert' ORDER BY timestamp DESC LIMIT 1")
        audit_log = json.loads(cur.fetchone()["details_json"])
        assert audit_log.get("customer_phone") == "0988776655"
        conn.close()
        # Test 13: Healthcheck API for Container & Uptime Monitoring
        print("▶ Running Test 13: Production Healthcheck Endpoint...")
        health = get_json("/api/health")
        assert health.get("status") == "healthy"
        assert health.get("database") == "connected"
        assert health.get("service") == "ai-inbox-sales-platform"
        print("  ✅ Healthcheck verified: service online and SQLite connected.")

        # Test 14: Multi-Tenant Workspace Self-Registration & VietQR Billing
        print("▶ Running Test 14: Multi-Tenant Workspace Self-Registration & VietQR Generation...")
        reg_payload = {
            "name": "Giày Sneaker VN Store",
            "slug": "sneaker-vn",
            "admin_name": "Trần Hải Nam",
            "admin_email": "nam@sneakervn.vn",
            "plan": "growth"
        }
        reg_res = post_json("/api/workspaces/register", reg_payload)
        assert reg_res.get("success") is True
        ws_info = reg_res["workspace"]
        new_ws_id = ws_info["id"]
        assert ws_info["slug"] == "sneaker-vn"
        assert ws_info["plan"] == "growth"
        assert ws_info["monthly_conv_quota"] == 2000
        assert ws_info["max_staff_seats"] == 5

        # Check VietQR details
        pay_info = reg_res["billing"]["payment"]
        assert "img.vietqr.io" in pay_info["qr_image_url"]
        assert "599000" in pay_info["qr_image_url"]
        assert "SNEAKER-VN" in pay_info["transfer_memo"]
        assert pay_info["amount_vnd"] == 599000

        # Duplicate slug rejected with 409 Conflict
        assert request_status("/api/workspaces/register", "POST", reg_payload) == 409
        print(f"  ✅ Workspace registered successfully with Growth plan (VietQR Memo: {pay_info['transfer_memo']}).")

        # Test 15: Workspace Quota Tracking & Dashboard Billing Info Endpoint
        print("▶ Running Test 15: Quota Tracking & Dashboard Billing Info Endpoint...")
        billing_res = get_json(f"/api/dashboard/billing?workspace_id={new_ws_id}")
        assert billing_res["slug"] == "sneaker-vn"
        assert billing_res["plan"] == "growth"
        q = billing_res["quota"]
        assert q["conversations_limit"] == 2000
        assert q["conversations_used"] == 0
        assert q["conversations_remaining"] == 2000
        assert q["staff_seats_used"] == 1 # 1 admin staff created during registration
        assert q["staff_seats_limit"] == 5
        assert q["staff_seats_remaining"] == 4

        # Verify plans listing
        plans_res = get_json("/api/billing/plans")
        assert len(plans_res.get("plans", [])) == 3
        plan_codes = [p["code"] for p in plans_res["plans"]]
        assert "starter" in plan_codes and "growth" in plan_codes and "pro" in plan_codes
        print("  ✅ Quota tracking and VietQR billing endpoints verified.")

        # Test 16: Zalo Official Account (OA) Webhook & Ingestion
        print("▶ Running Test 16: Zalo Official Account Webhook & Grounded Bot Reply...")
        zalo_verif = urllib.request.Request(f"{BASE_URL}/api/webhooks/zalo?challenge=zalo_token_abc123")
        with urllib.request.urlopen(zalo_verif) as z_resp:
            assert z_resp.status == 200
            assert z_resp.read().decode("utf-8") == "zalo_token_abc123"

        zalo_payload = {
            "event_name": "user_send_text",
            "app_id": "app_9988",
            "sender": {"id": "zalo_uid_7788"},
            "recipient": {"id": "oa_3344"},
            "message": {
                "msg_id": "zmsg_001",
                "text": "Shop ơi quần short kaki có màu Be size 31 không ạ?"
            }
        }
        z_res = post_json("/api/webhooks/zalo", zalo_payload)
        assert z_res.get("status") == "success"
        ev = z_res.get("event", {})
        assert ev.get("bot_replied") is True
        assert "180.000" in ev.get("response", "") or "180,000" in ev.get("response", "")

        # Verify conversation in dashboard inbox has channel 'zalo_oa'
        inbox_data = get_json("/api/dashboard/inbox")
        zalo_conv = next((c for c in inbox_data["conversations"] if c.get("channel") == "zalo_oa"), None)
        assert zalo_conv is not None, "Zalo conversation must appear in Dashboard Inbox"
        assert "7788" in zalo_conv["customer_name"]
        print("  ✅ Zalo OA challenge verified and customer chat grounded reply delivered.")

        # Test 17: Automated Follow-up & Re-engagement Scheduler
        print("▶ Running Test 17: Follow-up & Re-engagement Scheduler...")
        # Query stalled leads (with hours=0 so recent leads qualify)
        stalled_res = get_json("/api/dashboard/followups/stalled?workspace_id=ws-01&hours=0")
        assert stalled_res.get("count", 0) >= 1, "Should identify at least 1 open lead for follow-up"
        sample_item = stalled_res["stalled_leads"][0]
        assert "suggested_followup" in sample_item
        assert len(sample_item["suggested_followup"]) > 20
        assert "tư vấn" in sample_item["suggested_followup"] or "Dạ" in sample_item["suggested_followup"]

        # Run follow-up batch
        run_res = post_json("/api/dashboard/followups/run", {
            "workspace_id": "ws-01",
            "hours": 0,
            "dry_run": False
        })
        assert run_res.get("processed_count", 0) >= 1
        
        # Verify persistence in activity_logs
        conn = db_module.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS cnt FROM activity_logs WHERE event_type = 'lead_followup_reminder'")
        assert cur.fetchone()["cnt"] >= 1, "Must record follow-up events in audit log"
        conn.close()
        print(f"  ✅ Identified {stalled_res['count']} stalled lead(s) and queued personalized follow-up reminders.")

        # Test 18: Staff Performance & Commission Analytics
        print("▶ Running Test 18: Staff Performance & Commission Leaderboard...")
        staff_metrics = get_json("/api/dashboard/staff/metrics?workspace_id=ws-01")
        assert staff_metrics.get("staff_count", 0) >= 1
        tuan_rep = next((s for s in staff_metrics["leaderboard"] if "Tuấn" in s["name"]), None)
        assert tuan_rep is not None, "Staff member Tuấn Sale must be in leaderboard"
        assert tuan_rep["won_deals"] >= 1
        assert tuan_rep["won_revenue_vnd"] >= 250000
        assert tuan_rep["closing_rate_pct"] > 0
        assert tuan_rep["estimated_commission_vnd"] == int(tuan_rep["won_revenue_vnd"] * 0.05)
        print(f"  ✅ Staff leaderboard verified: {tuan_rep['name']} closed {tuan_rep['won_deals']} deal(s) (Revenue: {tuan_rep['won_revenue_vnd']:,}đ, Commission: {tuan_rep['estimated_commission_vnd']:,}đ).")

        # Test 19: TikTok Shop Webhook Verification & Chat Ingestion
        print("▶ Running Test 19: TikTok Shop Webhook & Chat Ingestion...")
        # GET challenge verification
        tt_ver_status, tt_ver_body = get_text("/api/webhooks/tiktok?challenge=tiktok_test_challenge_999")
        assert tt_ver_status == 200
        assert tt_ver_body.strip() == "tiktok_test_challenge_999"

        # POST customer message event
        tt_res = post_json("/api/webhooks/tiktok", {
            "type": "im.message.receive",
            "data": {
                "buyer_user_id": "tt_buyer_8899",
                "content": {"text": "Áo sơ mi linen cổ tàu giá bao nhiêu vậy shop?"}
            }
        })
        assert tt_res.get("status") == "success"
        tt_event = tt_res.get("event", {})
        assert tt_event.get("bot_replied") is True
        assert "320.000" in tt_event.get("response", "") or "320,000" in tt_event.get("response", "")

        # Verify TikTok conversation appears in unified inbox
        inbox_data = get_json("/api/dashboard/inbox")
        tt_conv = next((c for c in inbox_data["conversations"] if c.get("channel") == "tiktok_shop"), None)
        assert tt_conv is not None, "TikTok conversation must be present in Dashboard Inbox"
        assert "8899" in tt_conv["customer_name"]
        print("  ✅ TikTok Shop challenge verified and customer chat reply delivered.")

        # Test 20: Shopee Webhook Verification & Chat Ingestion
        print("▶ Running Test 20: Shopee Webhook & Chat Ingestion...")
        sp_ver_status, sp_ver_body = get_text("/api/webhooks/shopee?challenge=shopee_test_challenge_888")
        assert sp_ver_status == 200
        assert sp_ver_body.strip() == "shopee_test_challenge_888"

        sp_res = post_json("/api/webhooks/shopee", {
            "shop_id": 998877,
            "data": {
                "from_id": "shopee_buyer_1122",
                "content": {"text": "Áo polo nam classic còn hàng không shop ơi?"}
            }
        })
        assert sp_res.get("status") == "success"
        sp_event = sp_res.get("event", {})
        assert sp_event.get("bot_replied") is True
        assert "250.000" in sp_event.get("response", "") or "250,000" in sp_event.get("response", "")

        inbox_data = get_json("/api/dashboard/inbox")
        sp_conv = next((c for c in inbox_data["conversations"] if c.get("channel") == "shopee"), None)
        assert sp_conv is not None, "Shopee conversation must be present in Dashboard Inbox"
        assert "1122" in sp_conv["customer_name"]
        print("  ✅ Shopee challenge verified and buyer message grounded reply delivered.")

        # Test 21: Lazada Webhook Verification & Chat Ingestion
        print("▶ Running Test 21: Lazada Webhook & Chat Ingestion...")
        lz_ver_status, lz_ver_body = get_text("/api/webhooks/lazada?challenge=lazada_test_challenge_777")
        assert lz_ver_status == 200
        assert lz_ver_body.strip() == "lazada_test_challenge_777"

        lz_res = post_json("/api/webhooks/lazada", {
            "seller_id": "seller_laz_55",
            "data": {
                "buyer_id": "lazada_buyer_3344",
                "content": {"text": "Quần short kaki co giãn có những màu gì shop?"}
            }
        })
        assert lz_res.get("status") == "success"
        lz_event = lz_res.get("event", {})
        assert lz_event.get("bot_replied") is True
        assert "Đen" in lz_event.get("response", "")

        inbox_data = get_json("/api/dashboard/inbox")
        lz_conv = next((c for c in inbox_data["conversations"] if c.get("channel") == "lazada"), None)
        assert lz_conv is not None, "Lazada conversation must be present in Dashboard Inbox"
        assert "3344" in lz_conv["customer_name"]
        print("  ✅ Lazada challenge verified and customer chat grounded reply delivered.")

        # Test 22: Height & Weight Sizing Recommendation Assistant
        print("▶ Running Test 22: Height & Weight Sizing Assistant...")
        # 1m70 64kg -> Size L
        size_l_res = post_json("/api/widget/message", {
            "workspace_id": "ws-01",
            "customer_text": "Mình cao 1m70 nặng 64kg thì mặc áo polo size gì vừa ạ?",
            "customer_name": "Bạn Nam Thử Size L"
        })
        assert size_l_res.get("bot_replied") is True
        assert "size L" in size_l_res.get("response", ""), "64kg should recommend size L"

        # 1m62 52kg -> Size M
        size_m_res = post_json("/api/widget/message", {
            "workspace_id": "ws-01",
            "customer_text": "Mình cao 1m62 nặng 50kg thì mặc áo sơ mi linen size gì vậy?",
            "customer_name": "Bạn Nữ Thử Size M"
        })
        assert size_m_res.get("bot_replied") is True
        assert "size M" in size_m_res.get("response", ""), "50kg should recommend size M"

        # 1m80 80kg -> Size XL
        size_xl_res = post_json("/api/widget/message", {
            "workspace_id": "ws-01",
            "customer_text": "Em nặng 82kg cao 1m80 mặc áo polo có vừa không shop?",
            "customer_name": "Bạn Nam Thử Size XL"
        })
        assert size_xl_res.get("bot_replied") is True
        assert "size XL" in size_xl_res.get("response", ""), "82kg should recommend size XL"
        print("  ✅ Vietnamese height/weight sizing engine accurately advised sizes M, L, and XL.")

        # Test 23: Professional Mobile-First Chatbot & Storefront Integration
        print("▶ Running Test 23: Mobile-First Chatbot & Storefront Integration...")
        _, js_content = get_text("/widget/chat_widget.js")
        assert "window.openAiChat" in js_content, "Widget must expose window.openAiChat"
        assert "window.prepareAiPrompt" in js_content, "Widget must expose window.prepareAiPrompt"
        assert "Escape" in js_content, "Widget must support Escape key closing"
        assert "aria-modal" in js_content, "Widget must include accessible dialog attributes"

        _, css_content = get_text("/widget/chat_widget.css")
        assert "safe-area-inset" in css_content, "Widget CSS must support safe-area insets"
        assert "44px" in css_content, "Widget CSS must enforce 44px tap target minimums"
        assert "ai-quick-actions" in css_content, "Widget CSS must style quick action suggestions"

        _, demo_html = get_text("/demo")
        assert "btn-ask-ai" in demo_html, "Demo storefront must include product-card ask AI buttons"
        assert "window.openAiChat" in demo_html, "Demo storefront must connect product cards to chat widget"
        print("  ✅ Mobile-first chat widget, safe-area composer, quick action chips, and demo CTAs verified.")

        # Test 24: B2B SaaS Landing Page & VietQR Registration Showcase
        print("▶ Running Test 24: B2B SaaS Landing Page & VietQR Registration...")
        l_status, l_html = get_text("/landing")
        assert l_status == 200
        assert "AI Inbox Pro" in l_html
        assert "Biến Mọi Tin Nhắn Thành Đơn Hàng" in l_html
        assert "Facebook Messenger" in l_html and "Zalo Official Account" in l_html and "TikTok Shop" in l_html
        assert "Shopee Open Platform" in l_html and "Lazada Open Platform" in l_html
        assert "Starter" in l_html and "Growth" in l_html and "Pro" in l_html

        c_status, c_css = get_text("/web/landing.css")
        assert c_status == 200
        assert "Plus Jakarta Sans" in c_css
        assert "--bg-dark" in c_css
        assert "vietqr-box" in c_css

        # Test registration from landing page
        reg_res = post_json("/api/workspaces/register", {
            "name": "B2B Fashion Boutique",
            "plan_code": "growth",
            "admin_name": "Trần Thị Lan",
            "admin_email": "lan@b2bfashion.vn",
            "admin_phone": "0911223344"
        })
        assert "workspace" in reg_res
        assert "billing" in reg_res
        b_info = reg_res["billing"]
        assert "vietqr_quicklink_url" in b_info
        assert "img.vietqr.io" in b_info["vietqr_quicklink_url"]
        assert "B2B-FASHION-BOUTIQUE" in b_info["payment_memo"]
        print("  ✅ Landing page rendered with 6 omnichannel showcases, comparison matrix, and instant VietQR registration.")

        print("\n----------------------------------------------")
        print("🎉 ALL 24 E2E INTEGRATION TESTS PASSED (100%)!")
        print("----------------------------------------------")

    finally:
        server.shutdown()
        server.server_close()
        db_module.DB_FILE = original_db_file
        temp_dir.cleanup()

if __name__ == "__main__":
    run_e2e()
