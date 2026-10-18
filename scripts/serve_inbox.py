#!/usr/bin/env python3
"""
Runner script for AI Inbox & Sales Management Platform.
Initializes SQLite database, seeds realistic demo workspace and products if empty,
and serves the unified REST API, Admin Dashboard, and Demo Store.
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ai_inbox.core.db import init_db, get_connection, DB_FILE
from ai_inbox.api.server import run_server

def seed_demo_data():
    """Seed realistic initial store data if database is fresh."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS cnt FROM products")
    if cur.fetchone()["cnt"] > 0:
        conn.close()
        return

    print("[AI Inbox] Seeding realistic demo catalog and workspace data...")
    now_iso = datetime.now(timezone.utc).isoformat()

    # Workspace
    cur.execute(
        "INSERT OR IGNORE INTO workspaces (id, name, slug, created_at) VALUES ('ws-01', 'Shop Thời Trang Trẻ', 'shop-tre', ?)",
        (now_iso,)
    )

    # Staff
    cur.execute(
        "INSERT OR IGNORE INTO staff (id, workspace_id, name, email, role, is_active, created_at) VALUES ('staff-01', 'ws-01', 'Tuấn Sale', 'tuan@shoptre.vn', 'sales_rep', 1, ?)",
        (now_iso,)
    )

    # Products
    demo_products = [
        (
            'prod-01', 'ws-01', 'POLO-CLASSIC', 'Áo Polo Nam Classic', 'Thời trang nam', 250000, 50,
            '["M", "L", "XL"]', '["Đen", "Trắng", "Xanh Navy"]',
            'Chất liệu cotton 100% mềm mịn, thoáng mát, form regular fit chuẩn Hàn Quốc.',
            'Đồng giá ship 25k toàn quốc, miễn phí ship từ 2 chiếc.', 1, now_iso
        ),
        (
            'prod-02', 'ws-01', 'SHIRT-LINEN', 'Áo Sơ Mi Linen Cổ Tàu', 'Thời trang công sở', 320000, 35,
            '["L", "XL"]', '["Trắng", "Be", "Xanh Rêu"]',
            'Vải đũi linen tự nhiên thấm hút mồ hôi cực tốt, phong cách lịch lãm, tinh tế.',
            'Đồng giá ship 25k toàn quốc, miễn phí ship từ 2 chiếc.', 1, now_iso
        ),
        (
            'prod-03', 'ws-01', 'SHORT-KAKI', 'Quần Short Kaki Co Giãn', 'Quần nam', 180000, 60,
            '["29", "30", "31", "32"]', '["Đen", "Ghi", "Be"]',
            'Quần short kaki năng động, lưng chun co giãn thoải mái cho ngày hè.',
            'Đồng giá ship 25k toàn quốc, miễn phí ship từ 2 chiếc.', 1, now_iso
        )
    ]

    cur.executemany(
        """INSERT INTO products (id, workspace_id, sku, name, category, price_vnd, stock_quantity, sizes_json, colors_json, description, shipping_policy, is_active, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        demo_products
    )

    conn.commit()
    conn.close()
    print("[AI Inbox] Demo store catalog seeded successfully.")

def main():
    parser = argparse.ArgumentParser(description="Start AI Inbox & Sales Management Platform.")
    parser.add_argument("--host", type=str, default=os.getenv("HOST", "0.0.0.0"), help="Server host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 8080)), help="Server port (default: 8080)")
    args = parser.parse_args()

    init_db()
    seed_demo_data()
    run_server(host=args.host, port=args.port)

if __name__ == "__main__":
    main()
