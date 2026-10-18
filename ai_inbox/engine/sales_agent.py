#!/usr/bin/env python3
"""
Sales AI Agent - 5-Step Execution Workflow
1. Understand customer inquiry.
2. Grounded catalog retrieval (strict zero-hallucination).
3. Probe additional needs (sizes, colors, quantity).
4. Score purchasing intent (HOT / WARM / COLD).
5. Trigger human handoff when ready to close.
"""

import re
import json
import uuid
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
from pathlib import Path

from ai_inbox.core.db import get_connection
from ai_inbox.engine.product_catalog import ProductCatalogEngine
from ai_inbox.engine.lead_scorer import LeadScorer
from ai_inbox.engine.notifier import TelegramNotifier

class SalesAgent:
    def __init__(self, db_path: Optional[Path] = None, notifier: Optional[TelegramNotifier] = None):
        self.db_path = db_path
        self.catalog = ProductCatalogEngine(db_path=db_path)
        self.scorer = LeadScorer()
        self.notifier = notifier or TelegramNotifier(db_path=db_path)

    def handle_incoming_message(
        self,
        workspace_id: str,
        conversation_id: str,
        customer_text: str
    ) -> Dict[str, Any]:
        """
        Processes incoming customer message through the 5-step Sales AI engine.
        Returns bot response, lead status, and handoff indicator.
        """
        conn = get_connection(self.db_path)
        cur = conn.cursor()

        # Fetch conversation & existing lead state
        cur.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        conv = cur.fetchone()
        if not conv:
            conn.close()
            raise ValueError(f"Conversation {conversation_id} not found.")

        # If human staff already took over, bot stays silent
        if conv["status"] == "assigned_human":
            conn.close()
            return {
                "bot_replied": False,
                "reason": "human_staff_active",
                "status": "assigned_human"
            }

        cur.execute("SELECT * FROM leads WHERE conversation_id = ?", (conversation_id,))
        lead = cur.fetchone()
        current_score = lead["score"] if lead else 0
        customer_id = conv["customer_id"]

        # Save incoming customer message
        msg_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute(
            """INSERT INTO messages (id, conversation_id, sender_type, sender_name, content, timestamp)
               VALUES (?, ?, 'customer', 'Khách hàng', ?, ?)""",
            (msg_id, conversation_id, customer_text, now_iso)
        )

        # Step 1 & 2: Understand question & Grounded Catalog Lookup
        product = self.catalog.find_product_by_query(workspace_id, customer_text)
        if not product and lead and lead["interested_product_id"]:
            # Fall back to previously discussed product
            cur.execute("SELECT * FROM products WHERE id = ?", (lead["interested_product_id"],))
            p_row = cur.fetchone()
            if p_row:
                product = {
                    "id": p_row["id"], "sku": p_row["sku"], "name": p_row["name"],
                    "price_vnd": p_row["price_vnd"], "stock_quantity": p_row["stock_quantity"],
                    "sizes": json.loads(p_row["sizes_json"] or "[]"),
                    "colors": json.loads(p_row["colors_json"] or "[]"),
                    "shipping_policy": p_row["shipping_policy"]
                }

        # Step 3: Probe Needs & Compose Grounded Response
        bot_reply, needs_handoff = self._compose_response(customer_text, product)

        # Step 4: Score Intent
        new_score, intent_label, signals = self.scorer.analyze_message(customer_text, current_score)

        # Step 5: Human Handoff Decision
        if intent_label == "HOT" or needs_handoff or "human_request" in signals:
            needs_handoff = True
            conv_status = "assigned_human"
        else:
            conv_status = "bot_handling"

        # Update Conversation
        cur.execute(
            "UPDATE conversations SET status = ?, last_message_at = ? WHERE id = ?",
            (conv_status, now_iso, conversation_id)
        )

        # Update or Insert Lead
        product_id = product["id"] if product else (lead["interested_product_id"] if lead else None)
        est_val = product["price_vnd"] if product else 0
        lead_id = lead["id"] if lead else str(uuid.uuid4())
        lead_status = "assigned" if needs_handoff else ("ai_qualified" if new_score >= 40 else "new")

        if lead:
            cur.execute(
                """UPDATE leads SET score = ?, intent_label = ?, status = ?, 
                   interested_product_id = COALESCE(?, interested_product_id), 
                   updated_at = ? WHERE id = ?""",
                (new_score, intent_label, lead_status, product_id, now_iso, lead_id)
            )
        else:
            cur.execute(
                """INSERT INTO leads (id, workspace_id, customer_id, conversation_id, status, score, 
                   intent_label, interested_product_id, estimated_value_vnd, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (lead_id, workspace_id, customer_id, conversation_id, lead_status, new_score, 
                 intent_label, product_id, est_val, now_iso, now_iso)
            )

        # Save Bot Reply Message
        bot_msg_id = str(uuid.uuid4())
        cur.execute(
            """INSERT INTO messages (id, conversation_id, sender_type, sender_name, content, intent, timestamp)
               VALUES (?, ?, 'bot', 'Trợ lý AI', ?, ?, ?)""",
            (bot_msg_id, conversation_id, bot_reply, intent_label, now_iso)
        )

        # Detect and enrich customer phone number
        phone_match = re.search(r"(0\d{9}|0\d{8})", customer_text)
        detected_phone = phone_match.group(1) if phone_match else None
        
        cur.execute("SELECT name, phone FROM customers WHERE id = ?", (customer_id,))
        cust_row = cur.fetchone()
        cust_name = cust_row["name"] if cust_row else "Khách hàng"
        cust_phone = cust_row["phone"] if (cust_row and cust_row["phone"]) else detected_phone

        if detected_phone and cust_row and not cust_row["phone"]:
            cur.execute("UPDATE customers SET phone = ?, updated_at = ? WHERE id = ?", (detected_phone, now_iso, customer_id))

        conn.commit()
        conn.close()

        # Dispatch Alert for HOT Leads (Score >= 75, HOT label, handoff, or phone provided)
        alert_sent = False
        if needs_handoff or intent_label == "HOT" or new_score >= 75 or detected_phone:
            lead_info = {
                "workspace_id": workspace_id,
                "conversation_id": conversation_id,
                "customer_name": cust_name,
                "customer_phone": cust_phone,
                "channel": conv["channel"],
                "score": new_score,
                "intent_label": intent_label,
                "product_name": product["name"] if product else None,
                "price_vnd": product["price_vnd"] if product else None,
                "message_text": customer_text
            }
            alert_sent = self.notifier.notify_hot_lead(lead_info)

        return {
            "bot_replied": True,
            "response": bot_reply,
            "lead_id": lead_id,
            "score": new_score,
            "intent_label": intent_label,
            "signals": signals,
            "human_handoff_triggered": needs_handoff,
            "conversation_status": conv_status,
            "alert_sent": alert_sent
        }

    def _compose_response(self, text: str, product: Optional[Dict[str, Any]]) -> Tuple[str, bool]:
        """Generate verified, bounded response without hallucinations."""
        lower = text.lower()

        # Guardrail: If customer explicitly demands an unauthorized discount
        if "giảm giá" in lower or "bớt không" in lower or "chiết khấu" in lower:
            return (
                "Dạ bên em đang niêm yết giá chuẩn ưu đãi trực tiếp từ xưởng rồi ạ, "
                "không áp dụng giảm thêm trừ khi có chương trình khuyến mãi theo combo. "
                "Bạn cần nhân viên tư vấn thêm chính sách ưu đãi không ạ?",
                False
            )

        # Guardrail: Asking for a product not in the catalog
        if not product:
            return (
                "Dạ bên em chuyên các mặt hàng thời trang & phụ kiện chất lượng. "
                "Bạn có thể nhắn rõ hơn tên mẫu hoặc gửi ảnh sản phẩm bạn đang quan tâm để em kiểm tra kho giúp mình nhé!",
                False
            )

        # Product is found in catalog!
        p_name = product["name"]
        price_fmt = f"{product['price_vnd']:,}đ"
        stock = product["stock_quantity"]
        sizes = product.get("sizes", [])
        colors = product.get("colors", [])
        sizes_str = ", ".join(sizes) if sizes else "Freesize"
        colors_str = ", ".join(colors) if colors else "Tiêu chuẩn"
        ship_policy = product.get("shipping_policy", "Đồng giá 25k toàn quốc.")

        # Check stock zero
        if stock <= 0:
            return (
                f"Dạ mẫu {p_name} hiện tại trong kho vừa hết hàng mất rồi ạ. "
                "Bạn có muốn em ghi nhận thông tin để khi hàng về lại em nhắn báo bạn ngay không ạ?",
                False
            )

        # 1. Customer ready to buy / give address / order
        buy_keywords = ["cho mình 1", "cho mình 2", "mua", "đặt", "lấy", "chốt", "địa chỉ", "gửi về"]
        if any(k in lower for k in buy_keywords):
            return (
                f"Dạ em đã ghi nhận bạn muốn đặt {p_name} ({price_fmt}). "
                "Em đang kết nối nhân viên tư vấn trực tiếp vào hỗ trợ bạn chốt đơn và gửi mã vận đơn ngay nhé ạ!",
                True
            )

        # 2. Customer asks about shipping / delivery
        if any(k in lower for k in ["ship", "giao hàng", "đà nẵng", "hà nội", "phí"]):
            return (
                f"Dạ {p_name} có giá {price_fmt}. Chính sách giao hàng bên em: {ship_policy} "
                f"Mẫu này hiện còn đủ size ({sizes_str}) và các màu ({colors_str}). Bạn muốn chọn màu và size nào ạ?",
                False
            )

        # 3. Customer asks about size / color
        if any(k in lower for k in ["size", "cỡ", "màu", "m"]):
            return (
                f"Dạ mẫu {p_name} hiện có sẵn size: {sizes_str} và các màu: {colors_str}. "
                f"Giá sản phẩm là {price_fmt}. Bạn muốn lấy màu nào để em kiểm tra giữ hàng cho bạn ạ?",
                False
            )

        # 4. Default verified overview & probe
        return (
            f"Dạ mẫu {p_name} bên em đang có giá {price_fmt}, hiện còn sẵn hàng trong kho ạ. "
            f"Mẫu có các màu: {colors_str} và size: {sizes_str}. "
            "Bạn cho em xin chiều cao và cân nặng để em chọn size chuẩn nhất cho mình nhé!",
            False
        )
