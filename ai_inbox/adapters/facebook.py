#!/usr/bin/env python3
"""
Facebook Messenger Webhook Adapter & Ingestion Engine
Handles Meta Webhook Verification and bidirectional Messenger communication.
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

DEFAULT_VERIFY_TOKEN = os.getenv("FB_VERIFY_TOKEN", "inbox_verify_token_secret")
PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
GRAPH_API_VERSION = "v19.0"

class FacebookAdapter:
    def __init__(
        self,
        verify_token: Optional[str] = None,
        page_access_token: Optional[str] = None,
        db_path: Optional[Path] = None,
        sender_fn: Optional[Callable[[str, str], bool]] = None
    ):
        self.verify_token = verify_token or DEFAULT_VERIFY_TOKEN
        self.page_access_token = page_access_token or PAGE_ACCESS_TOKEN
        self.db_path = db_path
        self.sender_fn = sender_fn

    def verify_webhook(self, params: Dict[str, List[str]]) -> Tuple[int, str]:
        """
        Meta Hub challenge verification handler (GET /api/webhooks/facebook).
        Checks mode == 'subscribe' and token match.
        """
        mode = params.get("hub.mode", [""])[0]
        token = params.get("hub.verify_token", [""])[0]
        challenge = params.get("hub.challenge", [""])[0]

        if mode == "subscribe" and token == self.verify_token:
            return 200, challenge
        return 403, "Verification failed: invalid token or mode"

    def handle_webhook_event(self, payload: Dict[str, Any], default_workspace_id: str = "ws-01") -> Dict[str, Any]:
        """
        Ingests incoming Facebook Messenger payload (POST /api/webhooks/facebook).
        """
        obj_type = payload.get("object")
        if obj_type != "page":
            return {"status": "ignored", "reason": f"unsupported object type '{obj_type}'"}

        entries = payload.get("entry", [])
        processed_events = []

        for entry in entries:
            page_id = entry.get("id")
            messaging_list = entry.get("messaging", [])

            for event in messaging_list:
                sender = event.get("sender", {})
                recipient = event.get("recipient", {})
                sender_id = sender.get("id")
                recipient_id = recipient.get("id")

                message = event.get("message")
                if not sender_id or not message:
                    continue

                if message.get("is_echo", False):
                    continue

                # Extract message text (from normal text or quick_reply payload)
                text = message.get("text", "")
                if not text and "quick_reply" in message:
                    text = message["quick_reply"].get("payload", "")

                if not text:
                    continue

                ingest_res = self._ingest_message(
                    workspace_id=default_workspace_id,
                    sender_id=str(sender_id),
                    page_id=str(recipient_id or page_id or ""),
                    text=text.strip()
                )
                processed_events.append(ingest_res)

        return {
            "status": "success",
            "processed_count": len(processed_events),
            "events": processed_events
        }

    def _ingest_message(
        self,
        workspace_id: str,
        sender_id: str,
        page_id: str,
        text: str
    ) -> Dict[str, Any]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        external_id = f"fb_{sender_id}"

        # 1. Find or create Customer
        cur.execute(
            "SELECT id, name FROM customers WHERE workspace_id = ? AND external_id = ?",
            (workspace_id, external_id)
        )
        cust_row = cur.fetchone()
        if not cust_row:
            customer_id = str(uuid.uuid4())
            customer_name = f"FB User #{sender_id[-4:]}"
            cur.execute(
                """INSERT INTO customers (id, workspace_id, name, channel, external_id, created_at, updated_at)
                   VALUES (?, ?, ?, 'facebook_page', ?, ?, ?)""",
                (customer_id, workspace_id, customer_name, external_id, now_iso, now_iso)
            )
        else:
            customer_id = cust_row["id"]
            customer_name = cust_row["name"]

        # 2. Find or create active Conversation
        cur.execute(
            """SELECT id, status FROM conversations
               WHERE workspace_id = ? AND customer_id = ? AND channel = 'facebook_page'
               ORDER BY last_message_at DESC LIMIT 1""",
            (workspace_id, customer_id)
        )
        conv_row = cur.fetchone()

        if not conv_row or conv_row["status"] == "closed":
            conversation_id = str(uuid.uuid4())
            cur.execute(
                """INSERT INTO conversations (id, workspace_id, customer_id, channel, status, unread_count, last_message_at, created_at)
                   VALUES (?, ?, ?, 'facebook_page', 'bot_handling', 0, ?, ?)""",
                (conversation_id, workspace_id, customer_id, now_iso, now_iso)
            )
            conv_status = "bot_handling"
        else:
            conversation_id = conv_row["id"]
            conv_status = conv_row["status"]

        conn.commit()
        conn.close()

        # 3. If human staff has taken over, record message and do not bot-reply
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

        # 4. Otherwise, run SalesAgent
        agent = SalesAgent(db_path=self.db_path)
        agent_res = agent.handle_incoming_message(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            customer_text=text
        )

        # 5. If bot replied, dispatch back to Facebook Messenger
        if agent_res.get("bot_replied") and agent_res.get("response"):
            send_success = self.send_facebook_message(
                recipient_id=sender_id,
                message_text=agent_res["response"]
            )
            agent_res["fb_dispatched"] = send_success

        agent_res["conversation_id"] = conversation_id
        agent_res["customer_id"] = customer_id
        return agent_res

    def send_facebook_message(self, recipient_id: str, message_text: str) -> bool:
        """
        Sends reply back to Facebook Messenger user.
        Uses custom sender_fn if configured, otherwise posts to Meta Graph API,
        or logs cleanly if token is not configured (mock/local mode).
        """
        if self.sender_fn:
            return self.sender_fn(recipient_id, message_text)

        if not self.page_access_token:
            # Fallback/mock mode: Log dispatch safely without crashing
            print(f"[FacebookAdapter][MockDispatch] To PSID {recipient_id}: {message_text[:80]}...")
            return True

        url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/messages?access_token={self.page_access_token}"
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": message_text}
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status in (200, 201)
        except Exception as exc:
            print(f"[FacebookAdapter][SendError] {exc}")
            return False
