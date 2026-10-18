#!/usr/bin/env python3
"""
Automated Follow-up & Re-engagement Scheduler Engine
Monitors leads in the sales pipeline and automatically generates personalized re-engagement
prompts for customers whose conversations have stalled.
"""

import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path

from ai_inbox.core.db import get_connection

class FollowupScheduler:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path

    def find_stalled_leads(
        self,
        workspace_id: str = "ws-01",
        threshold_hours: float = 24.0
    ) -> List[Dict[str, Any]]:
        """
        Retrieves leads where conversation has been inactive for longer than threshold_hours,
        and the deal is not yet closed (won/lost).
        """
        conn = get_connection(self.db_path)
        cur = conn.cursor()

        cutoff_dt = datetime.now(timezone.utc) - timedelta(hours=threshold_hours)
        cutoff_iso = cutoff_dt.isoformat()

        query = """
            SELECT l.id AS lead_id, l.status AS lead_status, l.score, l.intent_label,
                   l.interested_product_id, l.estimated_value_vnd,
                   c.id AS conversation_id, c.channel, c.status AS conv_status, c.last_message_at,
                   cust.id AS customer_id, cust.name AS customer_name, cust.phone AS customer_phone,
                   p.name AS product_name, p.price_vnd
            FROM leads l
            JOIN conversations c ON l.conversation_id = c.id
            JOIN customers cust ON l.customer_id = cust.id
            LEFT JOIN products p ON l.interested_product_id = p.id
            WHERE l.workspace_id = ?
              AND l.status NOT IN ('won', 'lost')
              AND c.status != 'closed'
              AND c.last_message_at <= ?
            ORDER BY c.last_message_at ASC
        """
        cur.execute(query, (workspace_id, cutoff_iso))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        stalled = []
        for r in rows:
            suggestion = self.compose_reengagement_message(r)
            r["suggested_followup"] = suggestion
            stalled.append(r)

        return stalled

    def compose_reengagement_message(self, lead_data: Dict[str, Any]) -> str:
        """Generates friendly, non-pushy Vietnamese follow-up template."""
        c_name = lead_data.get("customer_name") or "mình"
        p_name = lead_data.get("product_name")

        if p_name:
            return (
                f"Dạ em chào {c_name}, em thấy mình đang quan tâm mẫu {p_name}. "
                f"Không biết mình có cần tư vấn thêm về chọn size chuẩn hoặc màu sắc ưng ý không ạ? "
                f"Shop vẫn đang hỗ trợ ship nhanh toàn quốc cho mình nhé!"
            )
        else:
            return (
                f"Dạ em chào {c_name}, hôm trước mình có nhắn tin cần tư vấn sản phẩm. "
                f"Không biết shop em có thể hỗ trợ gì thêm để mình chọn được món đồ phù hợp nhất không ạ?"
            )

    def process_followups(
        self,
        workspace_id: str = "ws-01",
        threshold_hours: float = 24.0,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Identifies stalled leads and creates follow-up reminder logs in activity_logs.
        """
        stalled_leads = self.find_stalled_leads(workspace_id, threshold_hours)
        processed = []
        now_iso = datetime.now(timezone.utc).isoformat()

        if not dry_run and stalled_leads:
            conn = get_connection(self.db_path)
            cur = conn.cursor()

            for item in stalled_leads:
                log_id = str(uuid.uuid4())
                details = {
                    "lead_id": item["lead_id"],
                    "conversation_id": item["conversation_id"],
                    "customer_name": item["customer_name"],
                    "customer_phone": item["customer_phone"],
                    "product_name": item["product_name"],
                    "suggested_message": item["suggested_followup"],
                    "hours_inactive": threshold_hours,
                    "action": "queued_followup_reminder"
                }
                cur.execute(
                    """INSERT INTO activity_logs (id, workspace_id, event_type, details_json, timestamp)
                       VALUES (?, ?, 'lead_followup_reminder', ?, ?)""",
                    (log_id, workspace_id, json.dumps(details, ensure_ascii=False), now_iso)
                )
                processed.append({
                    "lead_id": item["lead_id"],
                    "customer_name": item["customer_name"],
                    "suggested_message": item["suggested_followup"]
                })

            conn.commit()
            conn.close()

        return {
            "workspace_id": workspace_id,
            "threshold_hours": threshold_hours,
            "stalled_leads_count": len(stalled_leads),
            "processed_count": len(processed) if not dry_run else 0,
            "dry_run": dry_run,
            "leads": stalled_leads
        }

if __name__ == "__main__":
    scheduler = FollowupScheduler()
    res = scheduler.process_followups(workspace_id="ws-01", threshold_hours=0.0, dry_run=True)
    print(f"Stalled leads found: {res['stalled_leads_count']}")
