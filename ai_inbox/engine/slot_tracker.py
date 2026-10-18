"""Persistent, conservative order-slot collection for Vietnamese conversations."""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_inbox.core.db import get_connection


class MultiTurnSlotTracker:
    """Store only validated order details and prompt for one next detail at a time."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path

    @staticmethod
    def _normalise(value: str) -> str:
        return " ".join(value.lower().strip().split())

    @staticmethod
    def _match_option(text: str, options: List[str]) -> Optional[str]:
        from ai_inbox.engine.semantic_matcher import normalize_vietnamese
        normalised = MultiTurnSlotTracker._normalise(text)
        no_diacritic_text = normalize_vietnamese(text)
        for option in options:
            candidate = MultiTurnSlotTracker._normalise(str(option))
            if candidate and re.search(r"(?<!\w)" + re.escape(candidate) + r"(?!\w)", normalised):
                return str(option)
            no_diacritic_opt = normalize_vietnamese(str(option))
            if no_diacritic_opt and re.search(r"(?<!\w)" + re.escape(no_diacritic_opt) + r"(?!\w)", no_diacritic_text):
                return str(option)
        return None

    @staticmethod
    def _extract_quantity(text: str) -> Optional[int]:
        # A quantity must be coupled to a purchase noun so size numbers are not
        # mistaken for the requested amount.
        match = re.search(r"\b(\d{1,2})\s*(?:cái|cai|chiếc|chiec|chiáº¿c|áo|ao|Ã¡o|quần|quan|sản phẩm|san pham)\b", text.lower())
        if not match:
            return None
        quantity = int(match.group(1))
        return quantity if 1 <= quantity <= 99 else None

    @staticmethod
    def _extract_phone(text: str) -> Optional[str]:
        match = re.search(r"(?<!\d)(0\d{8,9})(?!\d)", re.sub(r"[.\s-]", "", text))
        return match.group(1) if match else None

    @staticmethod
    def _extract_address(text: str) -> Optional[str]:
        cleaned = " ".join(text.strip().split())
        lower = cleaned.lower()
        cues = ("địa chỉ", "dia chi", "gửi về", "gui ve", "ship về", "ship ve", "ship vá»", "giao về", "giao ve", "nhận tại", "nhan tai")
        has_cue = any(cue in lower for cue in cues)
        has_location = bool(re.search(r"\b\d{1,4}\s+[^,]{2,}", cleaned)) or any(
            marker in lower for marker in ("đường", "phường", "quận", "huyện", "thành phố", "tp.", "tỉnh")
        )
        if has_cue and has_location:
            for cue in cues:
                position = lower.find(cue)
                if position >= 0:
                    value = cleaned[position + len(cue):].lstrip(" :,-")
                    return value if len(value) >= 6 else None
        return None

    def get(self, conversation_id: str) -> Dict[str, Any]:
        conn = get_connection(self.db_path)
        row = conn.execute("SELECT * FROM conversation_slots WHERE conversation_id = ?", (conversation_id,)).fetchone()
        conn.close()
        return dict(row) if row else {}

    def update_from_message(
        self,
        workspace_id: str,
        conversation_id: str,
        text: str,
        product: Optional[Dict[str, Any]] = None,
        known_phone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Merge recognised values; product variants are accepted only when catalog-valid."""
        current = self.get(conversation_id)
        product = product or {}
        sizes = product.get("sizes") or []
        colors = product.get("colors") or []
        updates: Dict[str, Any] = {
            "product_id": product.get("id") or current.get("product_id"),
            "product_sku": product.get("sku") or current.get("product_sku"),
            "size": self._match_option(text, sizes) or current.get("size"),
            "color": self._match_option(text, colors) or current.get("color"),
            "quantity": self._extract_quantity(text) or current.get("quantity"),
            "shipping_address": self._extract_address(text) or current.get("shipping_address"),
            "phone_number": self._extract_phone(text) or known_phone or current.get("phone_number"),
        }

        # Products without selectable variants do not need those fields to close.
        updates["requires_size"] = bool(sizes)
        updates["requires_color"] = bool(colors)
        now = datetime.now(timezone.utc).isoformat()
        conn = get_connection(self.db_path)
        conn.execute(
            """INSERT INTO conversation_slots
               (conversation_id, workspace_id, product_id, product_sku, size, color, quantity,
                shipping_address, phone_number, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(conversation_id) DO UPDATE SET
                 workspace_id=excluded.workspace_id, product_id=excluded.product_id,
                 product_sku=excluded.product_sku, size=excluded.size, color=excluded.color,
                 quantity=excluded.quantity, shipping_address=excluded.shipping_address,
                 phone_number=excluded.phone_number, updated_at=excluded.updated_at""",
            (conversation_id, workspace_id, updates["product_id"], updates["product_sku"], updates["size"],
             updates["color"], updates["quantity"], updates["shipping_address"], updates["phone_number"], now),
        )
        conn.commit()
        conn.close()
        return updates

    @staticmethod
    def missing_slots(state: Dict[str, Any]) -> List[str]:
        missing = []
        if not state.get("product_sku"):
            missing.append("product")
        if state.get("requires_size") and not state.get("size"):
            missing.append("size")
        if state.get("requires_color") and not state.get("color"):
            missing.append("color")
        for field in ("quantity", "shipping_address", "phone_number"):
            if not state.get(field):
                missing.append(field)
        return missing

    def next_question(self, state: Dict[str, Any], product: Optional[Dict[str, Any]]) -> Optional[str]:
        missing = self.missing_slots(state)
        if not missing:
            return None
        first = missing[0]
        if first == "size":
            return f"Dạ bạn chọn giúp em size nào ({', '.join(product.get('sizes', []))}) ạ?"
        if first == "color":
            return f"Dạ bạn chọn giúp em màu nào ({', '.join(product.get('colors', []))}) ạ?"
        prompts = {
            "product": "Dạ bạn cho em xin đúng tên hoặc mã sản phẩm để em kiểm tra ạ.",
            "quantity": "Dạ bạn muốn lấy mấy chiếc ạ?",
            "shipping_address": "Dạ bạn cho em xin địa chỉ nhận hàng đầy đủ (số nhà, đường, quận/huyện) ạ.",
            "phone_number": "Dạ bạn cho em xin số điện thoại nhận hàng để nhân viên xác nhận đơn ạ.",
        }
        return prompts[first]

