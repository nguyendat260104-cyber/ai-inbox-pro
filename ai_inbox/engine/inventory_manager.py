"""Atomic draft-order and soft stock-reservation service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ai_inbox.core.db import get_connection, init_db


class InventoryUnavailableError(ValueError):
    """Raised when committed stock minus active reservations is insufficient."""


class StockReservationManager:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path
        init_db(db_path)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def release_expired_locks(self) -> int:
        now = self._now().isoformat()
        conn = get_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.execute(
                """UPDATE inventory_locks SET status = 'released', updated_at = ?
                   WHERE status = 'active' AND expires_at <= ?""",
                (now, now),
            )
            conn.commit()
            return cur.rowcount
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def reserve_stock(
        self,
        workspace_id: str,
        sku: str,
        quantity: int,
        *,
        customer_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        shipping_address: Optional[str] = None,
        timeout_minutes: int = 15,
    ) -> Dict[str, Any]:
        if quantity <= 0:
            raise ValueError("quantity must be greater than zero")
        if timeout_minutes <= 0:
            raise ValueError("timeout_minutes must be greater than zero")

        now = self._now()
        now_iso = now.isoformat()
        expires_at = (now + timedelta(minutes=timeout_minutes)).isoformat()
        conn = get_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """UPDATE inventory_locks SET status = 'released', updated_at = ?
                   WHERE status = 'active' AND expires_at <= ?""",
                (now_iso, now_iso),
            )
            product = conn.execute(
                """SELECT id, sku, name, price_vnd, stock_quantity FROM products
                   WHERE workspace_id = ? AND LOWER(sku) = LOWER(?) AND is_active = 1""",
                (workspace_id, sku),
            ).fetchone()
            if not product:
                raise ValueError("Active product SKU was not found in this workspace")
            reserved = conn.execute(
                """SELECT COALESCE(SUM(quantity), 0) AS quantity FROM inventory_locks
                   WHERE product_id = ? AND status = 'active' AND expires_at > ?""",
                (product["id"], now_iso),
            ).fetchone()["quantity"]
            available = product["stock_quantity"] - reserved
            if available < quantity:
                raise InventoryUnavailableError(
                    f"Only {available} unit(s) remain available for {product['sku']}"
                )

            subtotal = product["price_vnd"] * quantity
            shipping_fee = 0 if quantity >= 2 else 25_000
            order_id, lock_id = str(uuid.uuid4()), str(uuid.uuid4())
            conn.execute(
                """INSERT INTO orders (
                       id, workspace_id, customer_id, conversation_id, product_id, sku,
                       quantity, unit_price_vnd, subtotal_vnd, shipping_fee_vnd, total_vnd,
                       shipping_address, status, created_at, updated_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?)""",
                (order_id, workspace_id, customer_id, conversation_id, product["id"], product["sku"],
                 quantity, product["price_vnd"], subtotal, shipping_fee, subtotal + shipping_fee,
                 shipping_address, now_iso, now_iso),
            )
            conn.execute(
                """INSERT INTO inventory_locks (
                       id, workspace_id, product_id, order_id, quantity, status, expires_at, created_at, updated_at
                   ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?)""",
                (lock_id, workspace_id, product["id"], order_id, quantity, expires_at, now_iso, now_iso),
            )
            conn.commit()
            return {
                "order_id": order_id,
                "lock_id": lock_id,
                "sku": product["sku"],
                "product_name": product["name"],
                "quantity": quantity,
                "subtotal_vnd": subtotal,
                "shipping_fee_vnd": shipping_fee,
                "total_vnd": subtotal + shipping_fee,
                "expires_at": expires_at,
                "available_after_reservation": available - quantity,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def confirm_order_purchase(self, order_id: str) -> Dict[str, Any]:
        now_iso = self._now().isoformat()
        conn = get_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
            if not order:
                raise ValueError("Order was not found")
            if order["status"] == "confirmed":
                conn.commit()
                return {"order_id": order_id, "status": "confirmed", "already_confirmed": True}
            lock = conn.execute(
                "SELECT * FROM inventory_locks WHERE order_id = ? AND status = 'active'", (order_id,)
            ).fetchone()
            if not lock or lock["expires_at"] <= now_iso:
                raise InventoryUnavailableError("Stock reservation has expired or is unavailable")
            product = conn.execute(
                "SELECT stock_quantity FROM products WHERE id = ?", (order["product_id"],)
            ).fetchone()
            if not product or product["stock_quantity"] < order["quantity"]:
                raise InventoryUnavailableError("Committed stock is no longer available")
            conn.execute(
                "UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?",
                (order["quantity"], order["product_id"]),
            )
            conn.execute("UPDATE orders SET status = 'confirmed', updated_at = ? WHERE id = ?", (now_iso, order_id))
            conn.execute("UPDATE inventory_locks SET status = 'confirmed', updated_at = ? WHERE id = ?", (now_iso, lock["id"]))
            conn.commit()
            return {"order_id": order_id, "status": "confirmed", "total_vnd": order["total_vnd"]}
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
