#!/usr/bin/env python3
"""
Telegram Alert Dispatcher for HOT Leads
Dispatches real-time alerts to sales teams via Telegram Bot when high buying intent is detected.
"""

import os
import json
import uuid
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone
from pathlib import Path

from ai_inbox.core.db import get_connection

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8080")

class TelegramNotifier:
    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        base_url: Optional[str] = None,
        db_path: Optional[Path] = None,
        alert_handler: Optional[Callable[[Dict[str, Any], str], bool]] = None
    ):
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.base_url = (base_url or APP_BASE_URL).rstrip("/")
        self.db_path = db_path
        self.alert_handler = alert_handler  # Custom hook for testing

    def format_hot_lead_message(self, lead_info: Dict[str, Any]) -> str:
        """Constructs human-friendly alert message with actionable closing links."""
        customer_name = lead_info.get("customer_name") or "Khách hàng"
        customer_phone = lead_info.get("customer_phone") or "Chưa cung cấp"
        channel = lead_info.get("channel") or "web_widget"
        score = lead_info.get("score", 100)
        product_name = lead_info.get("product_name") or "Sản phẩm tư vấn chung"
        price_vnd = lead_info.get("price_vnd")
        price_str = f"{price_vnd:,}đ" if price_vnd else "Liên hệ"
        customer_msg = lead_info.get("message_text", "")
        conv_id = lead_info.get("conversation_id", "")

        deep_link = f"{self.base_url}/admin?conv={conv_id}"

        msg = (
            f"🔥 <b>[HOT LEAD MỚI CẦN CHỐT ĐƠN]</b>\n\n"
            f"👤 <b>Khách hàng:</b> {customer_name}\n"
            f"📞 <b>SĐT / Liên hệ:</b> <code>{customer_phone}</code>\n"
            f"📡 <b>Kênh:</b> {channel}\n"
            f"🎯 <b>Điểm mua hàng:</b> {score}/100 (HOT LEAD)\n"
            f"🛍 <b>Sản phẩm:</b> {product_name} ({price_str})\n"
            f"💬 <b>Tin nhắn gần nhất:</b> \"<i>{customer_msg}</i>\"\n\n"
            f"👉 <a href=\"{deep_link}\">Vào Dashboard nhận khách & chốt đơn ngay</a>"
        )
        return msg

    def notify_hot_lead(self, lead_info: Dict[str, Any]) -> bool:
        """
        Sends instant Telegram alert to merchant sales group.
        Falls back to local audit logging if Telegram credentials are not set.
        """
        formatted_text = self.format_hot_lead_message(lead_info)
        workspace_id = lead_info.get("workspace_id", "ws-01")

        # 1. Custom mock handler hook (for automated tests)
        if self.alert_handler:
            result = self.alert_handler(lead_info, formatted_text)
            self._record_audit_log(workspace_id, lead_info, "mock_hook")
            return result

        # 2. Live Telegram Dispatch
        if self.bot_token and self.chat_id:
            api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": formatted_text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                api_url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    success = resp.status in (200, 201)
                    if success:
                        self._record_audit_log(workspace_id, lead_info, "telegram_live")
                    return success
            except Exception as exc:
                print(f"[TelegramNotifier][SendError] {exc}")
                self._record_audit_log(workspace_id, lead_info, f"error: {exc}")
                return False

        # 3. Fallback / Mock Mode: Print to console and persist audit log
        print(f"\n[TelegramNotifier][MockAlert] Dispatched to Telegram (Mock Mode):\n{formatted_text}\n")
        self._record_audit_log(workspace_id, lead_info, "local_mock")
        return True

    def _record_audit_log(self, workspace_id: str, lead_info: Dict[str, Any], delivery_status: str):
        """Records alert dispatch event in database activity_logs table."""
        try:
            conn = get_connection(self.db_path)
            cur = conn.cursor()
            log_id = str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).isoformat()
            cur.execute(
                """INSERT INTO activity_logs (id, workspace_id, event_type, details_json, timestamp)
                   VALUES (?, ?, 'telegram_hot_lead_alert', ?, ?)""",
                (log_id, workspace_id, json.dumps({
                    "delivery_status": delivery_status,
                    "customer_name": lead_info.get("customer_name"),
                    "customer_phone": lead_info.get("customer_phone"),
                    "score": lead_info.get("score"),
                    "conversation_id": lead_info.get("conversation_id")
                }, ensure_ascii=False), now_iso)
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            print(f"[TelegramNotifier][AuditError] {exc}")

if __name__ == "__main__":
    notifier = TelegramNotifier()
    sample_lead = {
        "workspace_id": "ws-01",
        "conversation_id": "test-conv-123",
        "customer_name": "Nguyễn Văn Tuấn",
        "customer_phone": "0987654321",
        "channel": "facebook_page",
        "score": 100,
        "product_name": "Áo Polo Nam Classic",
        "price_vnd": 250000,
        "message_text": "Ship cho anh 2 cái size L về Cầu Giấy nhé!"
    }
    sent = notifier.notify_hot_lead(sample_lead)
    print(f"Test alert result: {sent}")
