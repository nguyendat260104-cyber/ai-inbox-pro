#!/usr/bin/env python3
"""Focused contract tests for draft-order inventory locks."""

import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ai_inbox.core.db import get_connection, init_db
from ai_inbox.engine.inventory_manager import InventoryUnavailableError, StockReservationManager


def seed(db_path: Path) -> None:
    init_db(db_path)
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    conn.execute("INSERT INTO workspaces (id, name, slug, created_at) VALUES ('ws-1', 'Test', 'test', ?)", (now,))
    conn.execute(
        """INSERT INTO products (id, workspace_id, sku, name, category, price_vnd, stock_quantity, created_at)
           VALUES ('prod-1', 'ws-1', 'POLO-1', 'Polo', 'shirt', 250000, 3, ?)""",
        (now,),
    )
    conn.commit()
    conn.close()


def run_tests() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "inbox.db"
        seed(db_path)
        manager = StockReservationManager(db_path)

        first = manager.reserve_stock("ws-1", "POLO-1", 2)
        assert first["shipping_fee_vnd"] == 0
        assert first["total_vnd"] == 500000
        try:
            manager.reserve_stock("ws-1", "POLO-1", 2)
            raise AssertionError("over-reservation should fail")
        except InventoryUnavailableError:
            pass

        confirmed = manager.confirm_order_purchase(first["order_id"])
        assert confirmed["status"] == "confirmed"
        conn = get_connection(db_path)
        assert conn.execute("SELECT stock_quantity FROM products WHERE id = 'prod-1'").fetchone()[0] == 1
        conn.close()

        second = manager.reserve_stock("ws-1", "POLO-1", 1)
        conn = get_connection(db_path)
        expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        conn.execute("UPDATE inventory_locks SET expires_at = ? WHERE id = ?", (expired, second["lock_id"]))
        conn.commit()
        conn.close()
        assert manager.release_expired_locks() == 1
        replacement = manager.reserve_stock("ws-1", "POLO-1", 1)
        assert replacement["shipping_fee_vnd"] == 25000

    print("inventory reservation tests passed")


if __name__ == "__main__":
    run_tests()
