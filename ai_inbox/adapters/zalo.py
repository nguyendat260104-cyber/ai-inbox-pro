#!/usr/bin/env python3
"""
Zalo Official Account (OA) Webhook Adapter & Ingestion Engine
Handles incoming Zalo OA webhook events and bidirectional customer messaging.
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

DEFAULT_ZALO_SECRET = os.getenv("ZALO_WEBHOOK_SECRET", "zalo_secret_token_default")
ZALO_OA_ACCESS_TOKEN = os.getenv("ZALO_OA_ACCESS_TOKEN", "")

class ZaloAdapter:
    def __init__(
        self,
        webhook_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        db_path: Optional[Path] = None,
        sender_fn: Optional[Callable[[str, str], bool]] = None
    ):
        self.webhook_secret = webhook_secret or DEFAULT_ZALO_SECRET
        self.access_token = access_token or ZALO_OA_ACCESS_TOKEN
        self.db_path = db_path
        self.sender_fn = sender_fn

    def verify_webhook(self, params: Dict[str, List[str]]) -> Tuple[int, str]:
        """Handles challenge verification GET requests from Zalo developers portal."""
        challenge = params.get("challenge", [""])[0] or params.get("hub.challenge", [""])[0]
        if challenge:
            return 200, challenge
        return 200, "Zalo OA Webhook Endpoint Online"

    def handle_webhook_event(self, payload: Dict[str, Any], default_workspace_id: str = "ws-01") -> Dict[str, Any]:
        """
        Parses incoming Zalo OA events (e.g. user_send_text).
        """
        event_name = payload.get("event_name", "")
        if event_name not in {"user_send_text", "user_send_image", "user_received_message"}:
            # Check fallback format
            if "message" not in payload:
                return {"status": "ignored", "reason": f"unhandled event_name '{event_name}'"}

        # Extract sender ID
        sender = payload.get("sender", {})
        sender_id = sender.get("id") or payload.get("user_id_by_app")
        if not sender_id:
            return {"status": "error", "message": "Missing sender identifier"}

        # Extract message text
        msg_obj = payload.get("message", {})
        text = msg_obj.get("text", "").strip() if isinstance(msg_obj, dict) else ""
        if not text:
            return {"status": "ignored", "reason": "empty_or_non_text_message"}

        # Ingest into customer & conversation
        ingest_res = self._ingest_message(
            workspace_id=default_workspace_id,
            sender_id=str(sender_id),
            text=text
        )

        return {
            "status": "success",
            "error": 0,
            "message": "OK",
            "event": ingest_res
        }

    def _ingest_message(
        self,
        workspace_id: str,
        sender_id: str,
        text: str
    ) -> Dict[str, Any]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        external_id = f"zalo_{sender_id}"

        # 1. Customer resolution
        cur.execute(
            "SELECT id, name FROM customers WHERE workspace_id = ? AND external_id = ?",
            (workspace_id, external_id)
        )
        cust_row = cur.fetchone()
        if not cust_row:
            customer_id = str(uuid.uuid4())
            customer_name = f"Zalo User #{sender_id[-4:]}"
            cur.execute(
                """INSERT INTO customers (id, workspace_id, name, channel, external_id, created_at, updated_at)
                   VALUES (?, ?, ?, 'zalo_oa', ?, ?, ?)""",
                (customer_id, workspace_id, customer_name, external_id, now_iso, now_iso)
            )
        else:
            customer_id = cust_row["id"]
            customer_name = cust_row["name"]

        # 2. Conversation resolution
        cur.execute(
            """SELECT id, status FROM conversations
               WHERE workspace_id = ? AND customer_id = ? AND channel = 'zalo_oa'
               ORDER BY last_message_at DESC LIMIT 1""",
            (workspace_id, customer_id)
        )
        conv_row = cur.fetchone()

        if not conv_row or conv_row["status"] == "closed":
            conversation_id = str(uuid.uuid4())
            cur.execute(
                """INSERT INTO conversations (id, workspace_id, customer_id, channel, status, unread_count, last_message_at, created_at)
                   VALUES (?, ?, ?, 'zalo_oa', 'bot_handling', 0, ?, ?)""",
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

        # 5. Outgoing dispatch back to Zalo user
        if agent_res.get("bot_replied") and agent_res.get("response"):
            send_ok = self.send_zalo_message(
                recipient_id=sender_id,
                message_text=agent_res["response"]
            )
            agent_res["zalo_dispatched"] = send_ok

        agent_res["conversation_id"] = conversation_id
        agent_res["customer_id"] = customer_id
        return agent_res

    def send_zalo_message(self, recipient_id: str, message_text: str) -> bool:
        """Sends message back to Zalo user via Official Account Customer Service API."""
        if self.sender_fn:
            return self.sender_fn(recipient_id, message_text)

        if not self.access_token:
            print(f"[ZaloAdapter][MockDispatch] To User {recipient_id}: {message_text[:80]}...")
            return True

        api_url = "https://openapi.zalo.me/v3.0/oa/message/cs"
        payload = {
            "recipient": {"user_id": recipient_id},
            "message": {"text": message_text}
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            api_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "access_token": self.access_token
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status in (200, 201)
        except Exception as exc:
            print(f"[ZaloAdapter][SendError] {exc}")
            return False
