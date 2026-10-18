#!/usr/bin/env python3
"""
AI Inbox & Sales Management Platform - REST API & Web Server
Lightweight, local-first HTTP server providing:
1. Widget Ingestion API (/api/widget/*)
2. Admin Dashboard & Kanban API (/api/dashboard/*)
3. Static file hosting for Widget, Dashboard, and Demo Store
"""

import sys
import os
import json
import uuid
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from ai_inbox.core.db import get_connection, init_db, DB_FILE
from ai_inbox.engine.sales_agent import SalesAgent
from ai_inbox.adapters.facebook import FacebookAdapter
from ai_inbox.adapters.zalo import ZaloAdapter
from ai_inbox.adapters.tiktok import TikTokShopAdapter
from ai_inbox.adapters.shopee import ShopeeAdapter
from ai_inbox.adapters.lazada import LazadaAdapter
from ai_inbox.api.billing import register_workspace, get_workspace_billing_info, PLANS
from ai_inbox.engine.followup_scheduler import FollowupScheduler

class InboxRequestHandler(BaseHTTPRequestHandler):
    VALID_LEAD_STAGES = {
        "new", "ai_qualified", "assigned", "contacted",
        "negotiating", "won", "lost"
    }

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "86400")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def send_json(self, status_code: int, data: Any):
        payload = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def read_json_body(self) -> Dict[str, Any]:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except ValueError as exc:
            raise ValueError("Invalid Content-Length header") from exc
        if content_length > 1_000_000:
            raise ValueError("Request body is too large")
        if content_length > 0:
            raw_bytes = self.rfile.read(content_length)
            self.raw_request_body = raw_bytes
            raw_body = raw_bytes.decode("utf-8")
            try:
                body = json.loads(raw_body)
            except json.JSONDecodeError as exc:
                raise ValueError("Request body must be valid JSON") from exc
            if not isinstance(body, dict):
                raise ValueError("Request body must be a JSON object")
            return body
        return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        # Meta Webhook Verification (Facebook Messenger)
        if path == "/api/webhooks/facebook":
            adapter = FacebookAdapter()
            code, challenge = adapter.verify_webhook(qs)
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(challenge.encode("utf-8"))
            return

        # Zalo OA Webhook Verification
        if path == "/api/webhooks/zalo":
            adapter = ZaloAdapter()
            code, challenge = adapter.verify_webhook(qs)
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(challenge.encode("utf-8"))
            return

        # TikTok Shop Webhook Verification
        if path == "/api/webhooks/tiktok":
            adapter = TikTokShopAdapter()
            code, challenge = adapter.verify_webhook(qs)
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(challenge.encode("utf-8"))
            return

        # Shopee Webhook Verification
        if path == "/api/webhooks/shopee":
            adapter = ShopeeAdapter()
            code, challenge = adapter.verify_webhook(qs)
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(challenge.encode("utf-8"))
            return

        # Lazada Webhook Verification
        if path == "/api/webhooks/lazada":
            adapter = LazadaAdapter()
            code, challenge = adapter.verify_webhook(qs)
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(challenge.encode("utf-8"))
            return

        # Health Check Route
        if path == "/api/health":
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("SELECT 1")
                conn.close()
                db_status = "connected"
            except Exception as e:
                db_status = f"error: {e}"

            return self.send_json(200, {
                "status": "healthy",
                "service": "ai-inbox-sales-platform",
                "database": db_status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        # Billing & Quota Overview
        if path == "/api/dashboard/billing":
            workspace_id = qs.get("workspace_id", ["ws-01"])[0]
            try:
                billing_info = get_workspace_billing_info(workspace_id)
                return self.send_json(200, billing_info)
            except ValueError as ve:
                return self.send_json(404, {"error": str(ve)})

        # Subscription Plans List
        if path == "/api/billing/plans":
            include_all = qs.get("all", ["false"])[0].lower() in ("true", "1")
            if include_all:
                return self.send_json(200, {"plans": list(PLANS.values())})
            core_codes = ["starter", "growth", "pro"]
            core_plans = [PLANS[c] for c in core_codes if c in PLANS]
            return self.send_json(200, {"plans": core_plans, "modular_plans": list(PLANS.values())})

        # Follow-up Stalled Leads List
        if path == "/api/dashboard/followups/stalled":
            workspace_id = qs.get("workspace_id", ["ws-01"])[0]
            try:
                hours = float(qs.get("hours", ["24"])[0])
            except ValueError:
                return self.send_json(400, {"error": "Invalid hours parameter"})
            scheduler = FollowupScheduler()
            stalled = scheduler.find_stalled_leads(workspace_id=workspace_id, threshold_hours=hours)
            return self.send_json(200, {"stalled_leads": stalled, "count": len(stalled), "threshold_hours": hours})

        # 1. API: Widget Message History
        if path == "/api/widget/history":
            conv_id = qs.get("conversation_id", [""])[0]
            if not conv_id:
                return self.send_json(400, {"error": "Missing conversation_id parameter"})
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, sender_type, sender_name, content, intent, timestamp FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC",
                (conv_id,)
            )
            rows = [dict(r) for r in cur.fetchall()]
            cur.execute("SELECT status, assigned_staff_id FROM conversations WHERE id = ?", (conv_id,))
            c_row = cur.fetchone()
            conn.close()
            if not c_row:
                return self.send_json(404, {"error": "Conversation not found"})
            return self.send_json(200, {
                "conversation_id": conv_id,
                "status": c_row["status"] if c_row else "bot_handling",
                "messages": rows
            })

        # 2. API: Dashboard Inbox List
        if path == "/api/dashboard/inbox":
            workspace_id = qs.get("workspace_id", ["ws-01"])[0]
            status_filter = qs.get("status", [None])[0]
            hot_only = qs.get("hot", ["false"])[0].lower() in {"1", "true", "yes"}
            if status_filter and status_filter not in {"bot_handling", "assigned_human", "closed"}:
                return self.send_json(400, {"error": "Invalid conversation status"})
            conn = get_connection()
            cur = conn.cursor()
            query = """
                SELECT c.id, c.customer_id, c.channel, c.status, c.unread_count, c.last_message_at,
                       cust.name AS customer_name, cust.phone AS customer_phone,
                       l.id AS lead_id, l.score AS lead_score, l.intent_label, l.status AS lead_status,
                       p.name AS product_name
                FROM conversations c
                LEFT JOIN customers cust ON c.customer_id = cust.id
                LEFT JOIN leads l ON l.conversation_id = c.id
                LEFT JOIN products p ON l.interested_product_id = p.id
                WHERE c.workspace_id = ?
            """
            params = [workspace_id]
            if status_filter:
                query += " AND c.status = ?"
                params.append(status_filter)
            if hot_only:
                query += " AND l.intent_label = 'HOT'"
            query += " ORDER BY c.last_message_at DESC"
            cur.execute(query, params)
            convs = [dict(r) for r in cur.fetchall()]
            conn.close()
            return self.send_json(200, {"conversations": convs})

        # 3. API: Conversation Messages (Admin Detail View)
        if path.startswith("/api/dashboard/conversations/") and path.endswith("/messages"):
            parts = path.strip("/").split("/")
            conv_id = parts[3]
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, sender_type, sender_name, content, intent, timestamp FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC",
                (conv_id,)
            )
            messages = [dict(r) for r in cur.fetchall()]
            cur.execute(
                """SELECT c.*, cust.name AS customer_name, cust.phone AS customer_phone,
                          l.id AS lead_id, l.score AS lead_score, l.intent_label, l.status AS lead_status,
                          p.name AS product_name, p.price_vnd AS product_price
                   FROM conversations c
                   LEFT JOIN customers cust ON c.customer_id = cust.id
                   LEFT JOIN leads l ON l.conversation_id = c.id
                   LEFT JOIN products p ON l.interested_product_id = p.id
                   WHERE c.id = ?""",
                (conv_id,)
            )
            details = cur.fetchone()
            conn.close()
            if not details:
                return self.send_json(404, {"error": "Conversation not found"})
            return self.send_json(200, {
                "conversation": dict(details) if details else None,
                "messages": messages
            })

        # 4. API: Dashboard Lead Kanban Board
        if path == "/api/dashboard/leads/kanban":
            workspace_id = qs.get("workspace_id", ["ws-01"])[0]
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                """SELECT l.*, cust.name AS customer_name, cust.phone AS customer_phone,
                          p.name AS product_name, p.price_vnd, s.name AS staff_name
                   FROM leads l
                   LEFT JOIN customers cust ON l.customer_id = cust.id
                   LEFT JOIN products p ON l.interested_product_id = p.id
                   LEFT JOIN staff s ON l.assigned_staff_id = s.id
                   WHERE l.workspace_id = ?
                   ORDER BY l.updated_at DESC""",
                (workspace_id,)
            )
            leads = [dict(r) for r in cur.fetchall()]
            conn.close()

            # Group into standard pipeline stages
            stages = ["new", "ai_qualified", "assigned", "contacted", "negotiating", "won", "lost"]
            kanban = {st: [] for st in stages}
            for ld in leads:
                st = ld.get("status", "new")
                if st in kanban:
                    kanban[st].append(ld)
                else:
                    kanban["new"].append(ld)
            return self.send_json(200, {"stages": kanban, "total_leads": len(leads)})

        # 4b. API: Export Leads as CSV
        if path == "/api/dashboard/leads/export":
            workspace_id = qs.get("workspace_id", ["ws-01"])[0]
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                """SELECT l.id, cust.name AS customer_name, cust.phone AS customer_phone, cust.channel,
                          p.name AS product_name, l.estimated_value_vnd, l.score, l.intent_label,
                          l.status AS lead_status, s.name AS staff_name, l.created_at
                   FROM leads l
                   LEFT JOIN customers cust ON l.customer_id = cust.id
                   LEFT JOIN products p ON l.interested_product_id = p.id
                   LEFT JOIN staff s ON l.assigned_staff_id = s.id
                   WHERE l.workspace_id = ?
                   ORDER BY l.created_at DESC""",
                (workspace_id,)
            )
            rows = cur.fetchall()
            conn.close()

            import csv
            import io
            output = io.StringIO()
            # Write UTF-8 BOM so Excel on Windows opens Vietnamese characters without garbled text
            output.write("\ufeff")
            writer = csv.writer(output)
            writer.writerow([
                "Mã Lead", "Họ Tên Khách", "Số Điện Thoại", "Kênh",
                "Sản Phẩm Quan Tâm", "Giá Trị Ước Tính (VNĐ)", "Điểm Intent (0-100)",
                "Phân Loại", "Trạng Thái Phễu", "Nhân Viên Phụ Trách", "Thời Gian Tạo"
            ])
            for r in rows:
                writer.writerow([
                    r["id"],
                    r["customer_name"] or "Khách Chưa Đặt Tên",
                    r["customer_phone"] or "Chưa có SĐT",
                    r["channel"],
                    r["product_name"] or "Chưa rõ sản phẩm",
                    r["estimated_value_vnd"] or 0,
                    r["score"] or 0,
                    r["intent_label"] or "COLD",
                    r["lead_status"],
                    r["staff_name"] or "Chưa phân công",
                    r["created_at"]
                ])

            csv_data = output.getvalue().encode("utf-8")
            date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="leads_export_{date_str}.csv"')
            self.send_header("Content-Length", str(len(csv_data)))
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(csv_data)
            return

        # 5. API: Dashboard Products
        if path == "/api/dashboard/products":
            workspace_id = qs.get("workspace_id", ["ws-01"])[0]
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM products WHERE workspace_id = ? AND is_active = 1", (workspace_id,))
            rows = [dict(r) for r in cur.fetchall()]
            for r in rows:
                r["sizes"] = json.loads(r.get("sizes_json") or "[]")
                r["colors"] = json.loads(r.get("colors_json") or "[]")
            conn.close()
            return self.send_json(200, {"products": rows})

        # 6. API: Dashboard Metrics
        if path == "/api/dashboard/metrics":
            workspace_id = qs.get("workspace_id", ["ws-01"])[0]
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS total_convs FROM conversations WHERE workspace_id = ?", (workspace_id,))
            total_convs = cur.fetchone()["total_convs"]

            cur.execute("SELECT COUNT(*) AS hot_leads FROM leads WHERE workspace_id = ? AND intent_label = 'HOT'", (workspace_id,))
            hot_leads = cur.fetchone()["hot_leads"]

            cur.execute("SELECT COUNT(*) AS won_deals, SUM(estimated_value_vnd) AS won_rev FROM leads WHERE workspace_id = ? AND status = 'won'", (workspace_id,))
            won_row = cur.fetchone()
            won_deals = won_row["won_deals"] or 0
            won_revenue = won_row["won_rev"] or 0

            cur.execute("SELECT COUNT(*) AS total_leads FROM leads WHERE workspace_id = ?", (workspace_id,))
            total_leads = cur.fetchone()["total_leads"] or 0

            # The Core stores both sides of an automated exchange with the same
            # timestamp, so the measurable local response time is currently zero.
            # Return measured data instead of a fabricated marketing number.
            cur.execute(
                """SELECT AVG(
                       (julianday(bot.timestamp) - julianday(customer.timestamp)) * 86400.0
                   ) AS avg_seconds
                   FROM messages bot
                   JOIN messages customer ON customer.id = (
                       SELECT m.id FROM messages m
                       WHERE m.conversation_id = bot.conversation_id
                         AND m.sender_type = 'customer'
                         AND m.timestamp <= bot.timestamp
                       ORDER BY m.timestamp DESC LIMIT 1
                   )
                   JOIN conversations c ON c.id = bot.conversation_id
                   WHERE bot.sender_type = 'bot' AND c.workspace_id = ?""",
                (workspace_id,)
            )
            avg_response_seconds = cur.fetchone()["avg_seconds"]

            conversion_rate = round((won_deals / total_leads * 100), 1) if total_leads > 0 else 0.0

            conn.close()
            return self.send_json(200, {
                "total_conversations": total_convs,
                "total_leads": total_leads,
                "hot_leads": hot_leads,
                "won_deals": won_deals,
                "won_revenue_vnd": won_revenue,
                "conversion_rate_pct": conversion_rate,
                "avg_ai_response_time_sec": round(avg_response_seconds or 0.0, 3)
            })

        # 7. API: Staff Performance & Commission Analytics
        if path == "/api/dashboard/staff/metrics":
            workspace_id = qs.get("workspace_id", ["ws-01"])[0]
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, name, email, role FROM staff WHERE workspace_id = ? AND is_active = 1",
                (workspace_id,)
            )
            staff_rows = cur.fetchall()
            leaderboard = []

            for s in staff_rows:
                s_id = s["id"]
                cur.execute(
                    "SELECT COUNT(*) AS total_leads FROM leads WHERE assigned_staff_id = ?",
                    (s_id,)
                )
                assigned_leads = cur.fetchone()["total_leads"] or 0

                cur.execute(
                    """SELECT COUNT(*) AS won_deals, SUM(estimated_value_vnd) AS won_rev
                       FROM leads WHERE assigned_staff_id = ? AND status = 'won'""",
                    (s_id,)
                )
                w_row = cur.fetchone()
                won_deals = w_row["won_deals"] or 0
                won_revenue = w_row["won_rev"] or 0

                closing_rate = round(won_deals / assigned_leads * 100, 1) if assigned_leads > 0 else 0.0
                commission_est = int(won_revenue * 0.05)

                leaderboard.append({
                    "staff_id": s_id,
                    "name": s["name"],
                    "email": s["email"],
                    "role": s["role"],
                    "assigned_leads": assigned_leads,
                    "won_deals": won_deals,
                    "won_revenue_vnd": won_revenue,
                    "closing_rate_pct": closing_rate,
                    "estimated_commission_vnd": commission_est
                })

            leaderboard.sort(key=lambda x: x["won_revenue_vnd"], reverse=True)
            conn.close()
            return self.send_json(200, {
                "workspace_id": workspace_id,
                "staff_count": len(leaderboard),
                "leaderboard": leaderboard
            })

        # Static File Serving (Widget, Admin Web, Demo Shop)
        self.serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        try:
            body = self.read_json_body()
        except (UnicodeDecodeError, ValueError) as exc:
            return self.send_json(400, {"error": str(exc)})

        # Meta Messenger Webhook Ingestion
        if path == "/api/webhooks/facebook":
            workspace_id = qs.get("workspace_id", ["ws-01"])[0]
            adapter = FacebookAdapter()
            signature = self.headers.get("X-Hub-Signature-256", "")
            if not adapter.verify_request_signature(
                getattr(self, "raw_request_body", b""), signature
            ):
                return self.send_json(403, {"error": "Invalid or unconfigured Facebook webhook signature"})
            result = adapter.handle_webhook_event(body, default_workspace_id=workspace_id)
            return self.send_json(200, result)

        # Zalo OA Webhook Ingestion
        if path == "/api/webhooks/zalo":
            workspace_id = qs.get("workspace_id", ["ws-01"])[0]
            adapter = ZaloAdapter()
            result = adapter.handle_webhook_event(body, default_workspace_id=workspace_id)
            return self.send_json(200, result)

        # TikTok Shop Webhook Ingestion
        if path == "/api/webhooks/tiktok":
            workspace_id = qs.get("workspace_id", ["ws-01"])[0]
            adapter = TikTokShopAdapter()
            result = adapter.handle_webhook_event(body, default_workspace_id=workspace_id)
            return self.send_json(200, result)

        # Shopee Webhook Ingestion
        if path == "/api/webhooks/shopee":
            workspace_id = qs.get("workspace_id", ["ws-01"])[0]
            adapter = ShopeeAdapter()
            result = adapter.handle_webhook_event(body, default_workspace_id=workspace_id)
            return self.send_json(200, result)

        # Lazada Webhook Ingestion
        if path == "/api/webhooks/lazada":
            workspace_id = qs.get("workspace_id", ["ws-01"])[0]
            adapter = LazadaAdapter()
            result = adapter.handle_webhook_event(body, default_workspace_id=workspace_id)
            return self.send_json(200, result)

        # Multi-Tenant Workspace Self-Registration
        if path == "/api/workspaces/register":
            name = body.get("name", "").strip()
            slug = body.get("slug", "").strip()
            if not slug and name:
                import re
                slug = re.sub(r'[^a-zA-Z0-9]+', '-', name).strip('-').lower()
            admin_name = body.get("admin_name", "").strip()
            admin_email = body.get("admin_email", "").strip()
            plan = (body.get("plan") or body.get("plan_code") or "starter").strip()

            try:
                reg_res = register_workspace(
                    name=name,
                    slug=slug,
                    admin_name=admin_name,
                    admin_email=admin_email,
                    plan_code=plan
                )
                return self.send_json(201, reg_res)
            except ValueError as ve:
                err_msg = str(ve)
                status_code = 409 if "already taken" in err_msg else 400
                return self.send_json(status_code, {"error": err_msg})

        # Follow-up Batch Processing Route
        if path == "/api/dashboard/followups/run":
            workspace_id = body.get("workspace_id", "ws-01")
            hours = float(body.get("hours", 24))
            dry_run = bool(body.get("dry_run", False))
            scheduler = FollowupScheduler()
            result = scheduler.process_followups(workspace_id=workspace_id, threshold_hours=hours, dry_run=dry_run)
            return self.send_json(200, result)

        # 1. API: Widget Customer Message
        if path == "/api/widget/message":
            workspace_id = body.get("workspace_id", "ws-01")
            customer_text = body.get("customer_text", "").strip()
            if not customer_text:
                return self.send_json(400, {"error": "customer_text cannot be empty"})

            conv_id = body.get("conversation_id")
            conn = get_connection()
            cur = conn.cursor()
            now_iso = datetime.now(timezone.utc).isoformat()

            cur.execute("SELECT id FROM workspaces WHERE id = ?", (workspace_id,))
            if not cur.fetchone():
                conn.close()
                return self.send_json(404, {"error": "Workspace not found"})

            # Ensure customer & conversation exist
            if not conv_id:
                cust_id = str(uuid.uuid4())
                conv_id = str(uuid.uuid4())
                c_name = body.get("customer_name") or f"Khách Web #{conv_id[:4]}"
                c_phone = body.get("customer_phone")
                cur.execute(
                    "INSERT INTO customers (id, workspace_id, name, phone, channel, created_at, updated_at) VALUES (?, ?, ?, ?, 'web_widget', ?, ?)",
                    (cust_id, workspace_id, c_name, c_phone, now_iso, now_iso)
                )
                cur.execute(
                    "INSERT INTO conversations (id, workspace_id, customer_id, channel, status, unread_count, last_message_at, created_at) VALUES (?, ?, ?, 'web_widget', 'bot_handling', 0, ?, ?)",
                    (conv_id, workspace_id, cust_id, now_iso, now_iso)
                )
                conn.commit()
            else:
                cur.execute(
                    "SELECT id, status FROM conversations WHERE id = ? AND workspace_id = ?",
                    (conv_id, workspace_id)
                )
                existing_conv = cur.fetchone()
                if not existing_conv:
                    conn.close()
                    return self.send_json(404, {"error": "Conversation not found"})

                # Once a human owns the conversation, keep recording customer
                # messages while preserving the Core contract that silences AI.
                if existing_conv["status"] == "assigned_human":
                    msg_id = str(uuid.uuid4())
                    cur.execute(
                        """INSERT INTO messages
                           (id, conversation_id, sender_type, sender_name, content, timestamp)
                           VALUES (?, ?, 'customer', 'Khách hàng', ?, ?)""",
                        (msg_id, conv_id, customer_text, now_iso)
                    )
                    cur.execute(
                        """UPDATE conversations
                           SET last_message_at = ?, unread_count = unread_count + 1
                           WHERE id = ?""",
                        (now_iso, conv_id)
                    )
                    conn.commit()
                    conn.close()
                    return self.send_json(200, {
                        "conversation_id": conv_id,
                        "bot_replied": False,
                        "reason": "human_staff_active",
                        "conversation_status": "assigned_human",
                        "human_handoff_triggered": True,
                    })
            conn.close()

            # Execute 5-step Sales AI Agent
            agent = SalesAgent()
            try:
                result = agent.handle_incoming_message(
                    workspace_id=workspace_id,
                    conversation_id=conv_id,
                    customer_text=customer_text
                )
                result["conversation_id"] = conv_id
                return self.send_json(200, result)
            except Exception as e:
                return self.send_json(500, {"error": str(e)})

        # 2. API: Staff Takeover
        if path.startswith("/api/dashboard/conversations/") and path.endswith("/takeover"):
            conv_id = path.strip("/").split("/")[3]
            staff_id = body.get("staff_id", "staff-01")
            conn = get_connection()
            cur = conn.cursor()
            now_iso = datetime.now(timezone.utc).isoformat()
            cur.execute("SELECT id FROM staff WHERE id = ? AND is_active = 1", (staff_id,))
            if not cur.fetchone():
                conn.close()
                return self.send_json(404, {"error": "Active staff member not found"})
            cur.execute(
                "UPDATE conversations SET status = 'assigned_human', assigned_staff_id = ?, last_message_at = ? WHERE id = ?",
                (staff_id, now_iso, conv_id)
            )
            if cur.rowcount == 0:
                conn.close()
                return self.send_json(404, {"error": "Conversation not found"})
            # Update associated lead
            cur.execute(
                "UPDATE leads SET status = 'assigned', assigned_staff_id = ?, updated_at = ? WHERE conversation_id = ?",
                (staff_id, now_iso, conv_id)
            )
            conn.commit()
            conn.close()
            return self.send_json(200, {"success": True, "conversation_id": conv_id, "status": "assigned_human"})

        # 3. API: Staff Manual Reply
        if path.startswith("/api/dashboard/conversations/") and path.endswith("/reply"):
            conv_id = path.strip("/").split("/")[3]
            staff_name = body.get("staff_name", "Tư vấn viên")
            reply_text = body.get("message", "").strip()
            if not reply_text:
                return self.send_json(400, {"error": "Message content cannot be empty"})

            conn = get_connection()
            cur = conn.cursor()
            now_iso = datetime.now(timezone.utc).isoformat()
            msg_id = str(uuid.uuid4())
            cur.execute("SELECT id FROM conversations WHERE id = ?", (conv_id,))
            if not cur.fetchone():
                conn.close()
                return self.send_json(404, {"error": "Conversation not found"})
            cur.execute(
                """INSERT INTO messages (id, conversation_id, sender_type, sender_name, content, timestamp)
                   VALUES (?, ?, 'staff', ?, ?, ?)""",
                (msg_id, conv_id, staff_name, reply_text, now_iso)
            )
            cur.execute(
                "UPDATE conversations SET status = 'assigned_human', last_message_at = ? WHERE id = ?",
                (now_iso, conv_id)
            )
            conn.commit()
            conn.close()
            return self.send_json(200, {"success": True, "message_id": msg_id, "timestamp": now_iso})

        # 4. API: Lead Stage Update
        if path.startswith("/api/dashboard/leads/") and path.endswith("/stage"):
            lead_id = path.strip("/").split("/")[3]
            new_stage = body.get("stage", "assigned")
            if new_stage not in self.VALID_LEAD_STAGES:
                return self.send_json(400, {
                    "error": "Invalid lead stage",
                    "allowed_stages": sorted(self.VALID_LEAD_STAGES)
                })
            conn = get_connection()
            cur = conn.cursor()
            now_iso = datetime.now(timezone.utc).isoformat()
            cur.execute(
                "UPDATE leads SET status = ?, updated_at = ? WHERE id = ?",
                (new_stage, now_iso, lead_id)
            )
            if cur.rowcount == 0:
                conn.close()
                return self.send_json(404, {"error": "Lead not found"})
            conn.commit()
            conn.close()
            return self.send_json(200, {"success": True, "lead_id": lead_id, "stage": new_stage})

        # 5. API: Create Product
        if path == "/api/dashboard/products":
            workspace_id = body.get("workspace_id", "ws-01")
            name = body.get("name", "").strip()
            sku = body.get("sku", "").strip()
            if not name or not sku:
                return self.send_json(400, {"error": "Product name and sku are required"})
            
            category = body.get("category", "Thời trang")
            try:
                price_vnd = int(body.get("price_vnd", 0))
                stock_qty = int(body.get("stock_quantity", 0))
            except (TypeError, ValueError):
                return self.send_json(400, {"error": "Price and stock must be integers"})
            if price_vnd < 0 or stock_qty < 0:
                return self.send_json(400, {"error": "Price and stock cannot be negative"})
            sizes = body.get("sizes", [])
            colors = body.get("colors", [])
            if not isinstance(sizes, list) or not isinstance(colors, list):
                return self.send_json(400, {"error": "Sizes and colors must be arrays"})
            description = body.get("description", "")
            shipping = body.get("shipping_policy", "Đồng giá ship 25k toàn quốc, miễn phí ship từ 2 chiếc.")

            prod_id = body.get("id") or str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).isoformat()

            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM workspaces WHERE id = ?", (workspace_id,))
            if not cur.fetchone():
                conn.close()
                return self.send_json(404, {"error": "Workspace not found"})
            cur.execute(
                "SELECT id FROM products WHERE workspace_id = ? AND LOWER(sku) = LOWER(?)",
                (workspace_id, sku)
            )
            if cur.fetchone():
                conn.close()
                return self.send_json(409, {"error": "SKU already exists in this workspace"})
            cur.execute(
                """INSERT INTO products (id, workspace_id, sku, name, category, price_vnd, stock_quantity, sizes_json, colors_json, description, shipping_policy, is_active, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                (prod_id, workspace_id, sku, name, category, price_vnd, stock_qty, json.dumps(sizes, ensure_ascii=False), json.dumps(colors, ensure_ascii=False), description, shipping, now_iso)
            )
            conn.commit()
            conn.close()
            return self.send_json(201, {"success": True, "product_id": prod_id, "name": name, "sku": sku})

        # 6. API: Delete Product
        if path.startswith("/api/dashboard/products/") and path.endswith("/delete"):
            prod_id = path.strip("/").split("/")[3]
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE products SET is_active = 0 WHERE id = ?", (prod_id,))
            if cur.rowcount == 0:
                conn.close()
                return self.send_json(404, {"error": "Product not found"})
            conn.commit()
            conn.close()
            return self.send_json(200, {"success": True, "product_id": prod_id, "status": "deleted"})

        return self.send_json(404, {"error": "Endpoint not found"})

    def serve_static(self, path: str):
        """Serve widget, admin web, and demo store assets."""
        base_dir = BASE_DIR / "ai_inbox"
        clean = path.strip("/")

        # Route aliases
        if clean in ["", "admin", "admin/"]:
            file_path = base_dir / "web" / "index.html"
            content_type = "text/html; charset=utf-8"
        elif clean in ["landing", "landing/", "welcome", "welcome/"]:
            file_path = base_dir / "web" / "landing.html"
            content_type = "text/html; charset=utf-8"
        elif clean in ["demo", "demo/"]:
            file_path = base_dir / "web" / "demo_shop.html"
            content_type = "text/html; charset=utf-8"
        elif clean.startswith("widget/"):
            file_path = base_dir / "widget" / clean.replace("widget/", "")
            content_type = "application/javascript" if clean.endswith(".js") else "text/css"
        elif clean.startswith("web/"):
            file_path = base_dir / clean
            content_type = "application/javascript" if clean.endswith(".js") else ("text/css" if clean.endswith(".css") else "text/html")
        else:
            file_path = base_dir / "web" / clean
            content_type = "text/plain"

        allowed_root = base_dir.resolve()
        try:
            resolved_path = file_path.resolve()
            resolved_path.relative_to(allowed_root)
        except (OSError, ValueError):
            return self.send_json(404, {"error": "File not found"})

        if resolved_path.exists() and resolved_path.is_file():
            with open(resolved_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_json(404, {"error": f"File '{clean}' not found"})

    def log_message(self, format, *args):
        # Keep server log clean
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

def run_server(host: str = "0.0.0.0", port: int = 8080):
    init_db()
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, InboxRequestHandler)
    print(f"[AI Inbox] Running at http://{host}:{port}/")
    print(f"  Admin Command Center: http://{host}:{port}/admin")
    print(f"  Customer Demo Store: http://{host}:{port}/demo")
    print(f"  B2B Sales Landing:   http://{host}:{port}/landing")
    print(f"  Embeddable Widget:   http://{host}:{port}/widget/chat_widget.js")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        httpd.server_close()

if __name__ == "__main__":
    run_server(host="0.0.0.0", port=8080)
