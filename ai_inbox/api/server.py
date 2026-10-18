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
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from ai_inbox.core.db import get_connection, init_db, DB_FILE
from ai_inbox.engine.sales_agent import SalesAgent

class InboxRequestHandler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

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
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            raw_body = self.wfile if False else self.rfile.read(content_length).decode("utf-8")
            return json.loads(raw_body)
        return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

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
            return self.send_json(200, {
                "conversation_id": conv_id,
                "status": c_row["status"] if c_row else "bot_handling",
                "messages": rows
            })

        # 2. API: Dashboard Inbox List
        if path == "/api/dashboard/inbox":
            workspace_id = qs.get("workspace_id", ["ws-01"])[0]
            status_filter = qs.get("status", [None])[0]
            conn = get_connection()
            cur = conn.cursor()
            query = """
                SELECT c.id, c.customer_id, c.channel, c.status, c.unread_count, c.last_message_at,
                       cust.name AS customer_name, cust.phone AS customer_phone,
                       l.score AS lead_score, l.intent_label, l.status AS lead_status,
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
                          l.score AS lead_score, l.intent_label, l.status AS lead_status,
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

            conversion_rate = round((won_deals / total_leads * 100), 1) if total_leads > 0 else 0.0

            conn.close()
            return self.send_json(200, {
                "total_conversations": total_convs,
                "total_leads": total_leads,
                "hot_leads": hot_leads,
                "won_deals": won_deals,
                "won_revenue_vnd": won_revenue,
                "conversion_rate_pct": conversion_rate,
                "avg_ai_response_time_sec": 0.45
            })

        # Static File Serving (Widget, Admin Web, Demo Shop)
        self.serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self.read_json_body()

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
            cur.execute(
                "UPDATE conversations SET status = 'assigned_human', assigned_staff_id = ?, last_message_at = ? WHERE id = ?",
                (staff_id, now_iso, conv_id)
            )
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
            conn = get_connection()
            cur = conn.cursor()
            now_iso = datetime.now(timezone.utc).isoformat()
            cur.execute(
                "UPDATE leads SET status = ?, updated_at = ? WHERE id = ?",
                (new_stage, now_iso, lead_id)
            )
            conn.commit()
            conn.close()
            return self.send_json(200, {"success": True, "lead_id": lead_id, "stage": new_stage})

        return self.send_json(404, {"error": "Endpoint not found"})

    def serve_static(self, path: str):
        """Serve widget, admin web, and demo store assets."""
        base_dir = BASE_DIR / "ai_inbox"
        clean = path.strip("/")

        # Route aliases
        if clean in ["", "admin", "admin/"]:
            file_path = base_dir / "web" / "index.html"
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

        if file_path.exists() and file_path.is_file():
            with open(file_path, "rb") as f:
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

def run_server(port: int = 8080):
    init_db()
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, InboxRequestHandler)
    print(f"⚡ AI Inbox & Sales Management Platform running at http://127.0.0.1:{port}/")
    print(f"   👉 Admin Command Center: http://127.0.0.1:{port}/admin")
    print(f"   👉 Customer Demo Store: http://127.0.0.1:{port}/demo")
    print(f"   👉 Embeddable Widget:   http://127.0.0.1:{port}/widget/chat_widget.js")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        httpd.server_close()

if __name__ == "__main__":
    run_server(port=8080)
