#!/usr/bin/env python3
"""
Lazada Open Platform Webhook Adapter & Ingestion Engine
Connects Lazada seller chat webhooks to the unified AI Inbox platform.
"""

import os
import json
import uuid
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Tuple, List, Callable
from datetime import datetime, timezone
from pathlib import Path

from ai_inbox.core.db import get_connection
from ai_inbox.engine.sales_agent import SalesAgent

class LazadaAdapter:
    def __init__(
        self,
        app_key: Optional[str] = None,
        app_secret: Optional[str] = None,
        db_path: Optional[Path] = None,
        sender_fn: Optional[Callable[[str, str], bool]] = None
    ):
        self.app_key = app_key or os.getenv("LAZADA_APP_KEY", "")
        self.app_secret = app_secret or os.getenv("LAZADA_APP_SECRET", "")
        self.db_path = db_path
        self.sender_fn = sender_fn

    def verify_webhook(self, params: Dict[str, List[str]]) -> Tuple[int, str]:
        """Handles challenge verification GET requests from Lazada Open Platform."""
        challenge = params.get("challenge", [""])[0] or params.get("msg", [""])[0]
        if challenge:
            return 200, challenge
        return 200, "Lazada Webhook Endpoint Online"

    def handle_webhook_event(self, payload: Dict[str, Any], default_workspace_id: str = "ws-01") -> Dict[str, Any]:
        """Parses incoming Lazada customer chat message events."""
        data = payload.get("data", payload)
        buyer_id = data.get("buyer_id") or data.get("from_user_id") or data.get("sender_id")

        if not buyer_id:
            return {"status": "ignored", "reason": "no_buyer_id_found"}

        content = data.get("content") or data.get("message", {})
        if isinstance(content, dict):
            text = content.get("text", "").strip()
        else:
            text = str(content).strip()

        if not text:
            return {"status": "ignored", "reason": "empty_text_message"}

        seller_id = str(payload.get("seller_id") or data.get("seller_id", ""))
        ingest_res = self._ingest_message(
            workspace_id=default_workspace_id,
            buyer_id=str(buyer_id),
            seller_id=seller_id,
            text=text
        )

        return {
            "status": "success",
            "message": "OK",
            "event": ingest_res
        }

    def _ingest_message(
        self,
        workspace_id: str,
        buyer_id: str,
        seller_id: str,
        text: str
    ) -> Dict[str, Any]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        external_id = f"lazada_{buyer_id}"

        # 1. Customer resolution
        cur.execute(
            "SELECT id, name FROM customers WHERE workspace_id = ? AND external_id = ?",
            (workspace_id, external_id)
        )
        cust_row = cur.fetchone()
        if not cust_row:
            customer_id = str(uuid.uuid4())
            customer_name = f"Lazada Buyer #{buyer_id[-4:]}"
            cur.execute(
                """INSERT INTO customers (id, workspace_id, name, channel, external_id, created_at, updated_at)
                   VALUES (?, ?, ?, 'lazada', ?, ?, ?)""",
                (customer_id, workspace_id, customer_name, external_id, now_iso, now_iso)
            )
        else:
            customer_id = cust_row["id"]
            customer_name = cust_row["name"]

        # 2. Conversation resolution
        cur.execute(
            """SELECT id, status FROM conversations
               WHERE workspace_id = ? AND customer_id = ? AND channel = 'lazada'
               ORDER BY last_message_at DESC LIMIT 1""",
            (workspace_id, customer_id)
        )
        conv_row = cur.fetchone()

        if not conv_row or conv_row["status"] == "closed":
            conversation_id = str(uuid.uuid4())
            cur.execute(
                """INSERT INTO conversations (id, workspace_id, customer_id, channel, status, unread_count, last_message_at, created_at)
                   VALUES (?, ?, ?, 'lazada', 'bot_handling', 0, ?, ?)""",
                (conversation_id, workspace_id, customer_id, now_iso, now_iso)
            )
            conv_status = "bot_handling"
        else:
            conversation_id = conv_row["id"]
            conv_status = conv_row["status"]

        conn.commit()
        conn.close()

        # 3. Staff takeover check
        if conv_status == "assigned_human":
            conn = get_connection(self.db_path)
            cur = conn.cursor()
            msg_id = str(uuid.uuid4())
            cur.execute(
                """INSERT INTO messages (id, conversation_id, sender_type, sender_name, content, timestamp)
                   VALUES (?, ?, 'customer', ?, ?, ?)""",
                (msg_id, conversation_id, customer_name, text, now_iso)
            )
            cur.execute(
                """UPDATE conversations SET last_message_at = ?, unread_count = unread_count + 1
                   WHERE id = ?""",
                (now_iso, conversation_id)
            )
            conn.commit()
            conn.close()
            return {
                "conversation_id": conversation_id,
                "customer_id": customer_id,
                "bot_replied": False,
                "reason": "human_staff_active",
                "conversation_status": "assigned_human"
            }

        # 4. SalesAgent execution
        agent = SalesAgent(db_path=self.db_path)
        agent_res = agent.handle_incoming_message(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            customer_text=text
        )

        # 5. Outgoing dispatch
        if agent_res.get("bot_replied") and agent_res.get("response"):
            send_ok = self.send_lazada_message(
                buyer_id=buyer_id,
                message_text=agent_res["response"]
            )
            agent_res["lazada_dispatched"] = send_ok

        agent_res["conversation_id"] = conversation_id
        agent_res["customer_id"] = customer_id
        return agent_res

    def send_lazada_message(self, buyer_id: str, message_text: str) -> bool:
        """Dispatches reply to Lazada buyer via Lazada Open Platform Chat API."""
        if self.sender_fn:
            return self.sender_fn(buyer_id, message_text)

        print(f"[LazadaAdapter][MockDispatch] To Buyer {buyer_id}: {message_text[:80]}...")
        return True
