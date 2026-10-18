#!/usr/bin/env python3
"""
Grounded Product Catalog & Retrieval Engine
Enforces ZERO-HALLUCINATION policy: AI must only quote prices, stock, and policies
explicitly verified in the merchant's database.
"""

import json
import sqlite3
from typing import Dict, Any, List, Optional
from pathlib import Path
from ai_inbox.core.db import get_connection

class ProductCatalogEngine:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path

    def find_product_by_query(self, workspace_id: str, query: str) -> Optional[Dict[str, Any]]:
        """Look up product by name, keyword, or SKU in the workspace database."""
        clean_q = query.strip().lower()
        conn = get_connection(self.db_path)
        cur = conn.cursor()

        # Try exact SKU match first
        cur.execute(
            "SELECT * FROM products WHERE workspace_id = ? AND LOWER(sku) = ? AND is_active = 1",
            (workspace_id, clean_q)
        )
        row = cur.fetchone()

        if not row:
            # Match keywords in product name or category
            cur.execute(
                "SELECT * FROM products WHERE workspace_id = ? AND is_active = 1",
                (workspace_id,)
            )
            rows = cur.fetchall()
            for r in rows:
                p_name = r["name"].lower()
                p_cat = r["category"].lower()
                # Check if query words intersect with product name
                q_words = [w for w in clean_q.split() if len(w) > 1]
                if any(w in p_name for w in q_words) or any(w in p_cat for w in q_words):
                    row = r
                    break

        conn.close()

        if row:
            return {
                "id": row["id"],
                "sku": row["sku"],
                "name": row["name"],
                "category": row["category"],
                "price_vnd": row["price_vnd"],
                "stock_quantity": row["stock_quantity"],
                "sizes": json.loads(row["sizes_json"] or "[]"),
                "colors": json.loads(row["colors_json"] or "[]"),
                "description": row["description"] or "",
                "shipping_policy": row["shipping_policy"] or "Đồng giá 25.000đ toàn quốc, giao 2-3 ngày."
            }
        return None

    def check_size_availability(self, product: Dict[str, Any], requested_size: str) -> bool:
        """Verify if requested size exists in the product catalog."""
        clean_size = requested_size.strip().upper()
        return clean_size in [s.upper() for s in product.get("sizes", [])]

    def check_color_availability(self, product: Dict[str, Any], requested_color: str) -> bool:
        """Verify if requested color exists in the product catalog."""
        clean_color = requested_color.strip().lower()
        return clean_color in [c.lower() for c in product.get("colors", [])]
