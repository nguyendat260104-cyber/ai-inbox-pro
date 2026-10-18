"""Focused regression tests for persistent multi-turn order collection."""

import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ai_inbox.core.db import get_connection, init_db
from ai_inbox.engine.sales_agent import SalesAgent
from ai_inbox.engine.slot_tracker import MultiTurnSlotTracker


def seed(db_path: Path) -> None:
    init_db(db_path)
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    conn.execute("INSERT INTO workspaces (id, name, slug, created_at) VALUES ('ws', 'Demo', 'demo', ?)", (now,))
    conn.execute(
        """INSERT INTO products (id, workspace_id, sku, name, category, price_vnd, stock_quantity,
           sizes_json, colors_json, is_active, created_at)
           VALUES ('polo', 'ws', 'POLO-01', 'Ao Polo', 'fashion', 250000, 9,
                   '[\"M\", \"L\", \"XL\"]', '[\"Den\", \"Trang\"]', 1, ?)""",
        (now,),
    )
    conn.execute("INSERT INTO customers (id, workspace_id, channel, created_at, updated_at) VALUES ('c', 'ws', 'web_widget', ?, ?)", (now, now))
    conn.execute("INSERT INTO conversations (id, workspace_id, customer_id, channel, last_message_at, created_at) VALUES ('conv', 'ws', 'c', 'web_widget', ?, ?)", (now, now))
    conn.commit()
    conn.close()


PRODUCT = {
    "id": "polo", "sku": "POLO-01", "name": "Ao Polo", "sizes": ["M", "L", "XL"], "colors": ["Den", "Trang"],
}


class SilentNotifier:
    def notify_hot_lead(self, _lead_info):
        return False


def test_four_turn_order_flow() -> None:
    with tempfile.TemporaryDirectory() as directory:
        db_path = Path(directory) / "inbox.db"
        seed(db_path)
        tracker = MultiTurnSlotTracker(db_path)

        first = tracker.update_from_message("ws", "conv", "Toi muon mua ao polo", PRODUCT)
        assert tracker.missing_slots(first) == ["size", "color", "quantity", "shipping_address", "phone_number"]
        assert "size" in tracker.next_question(first, PRODUCT).lower()

        second = tracker.update_from_message("ws", "conv", "size M mau Den", PRODUCT)
        assert second["size"] == "M" and second["color"] == "Den"
        assert tracker.missing_slots(second) == ["quantity", "shipping_address", "phone_number"]

        third = tracker.update_from_message("ws", "conv", "Lay 2 chiec, gui ve 123 Duong Le Loi, Quan 1", PRODUCT)
        assert third["quantity"] == 2
        assert third["shipping_address"].startswith("123")
        assert tracker.missing_slots(third) == ["phone_number"]

        final = tracker.update_from_message("ws", "conv", "So dien thoai cua toi la 0912345678", PRODUCT)
        assert final["phone_number"] == "0912345678"
        assert tracker.missing_slots(final) == []
        assert tracker.get("conv")["quantity"] == 2


def test_rejects_unavailable_variants() -> None:
    with tempfile.TemporaryDirectory() as directory:
        db_path = Path(directory) / "inbox.db"
        seed(db_path)
        state = MultiTurnSlotTracker(db_path).update_from_message("ws", "conv", "size XXL mau Xanh", PRODUCT)
        assert state["size"] is None
        assert state["color"] is None


def test_hot_score_does_not_bypass_missing_order_slots() -> None:
    """A HOT intent is prioritised, but it is not itself an order confirmation."""
    with tempfile.TemporaryDirectory() as directory:
        db_path = Path(directory) / "inbox.db"
        seed(db_path)
        agent = SalesAgent(db_path, notifier=SilentNotifier())
        agent.handle_incoming_message("ws", "conv", "Toi muon mua Ao Polo")
        response = agent.handle_incoming_message("ws", "conv", "size M mau Den 0912345678")
        assert response["intent_label"] == "HOT"
        assert response["human_handoff_triggered"] is False
        assert response["conversation_status"] == "bot_handling"


if __name__ == "__main__":
    test_four_turn_order_flow()
    test_rejects_unavailable_variants()
    test_hot_score_does_not_bypass_missing_order_slots()
    print("slot tracker tests passed")
