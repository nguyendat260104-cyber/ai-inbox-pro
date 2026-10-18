#!/usr/bin/env python3
"""Focused contract tests for typo-tolerant grounded product retrieval."""

import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ai_inbox.core.db import get_connection, init_db
from ai_inbox.engine.product_catalog import ProductCatalogEngine
from ai_inbox.engine.semantic_matcher import levenshtein_distance, normalize_vietnamese


def seed(db_path: Path) -> None:
    init_db(db_path)
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO workspaces (id, name, slug, created_at) VALUES ('ws', 'Test', 'test', ?)", (now,))
    products = [
        ('polo', 'POLO-CLASSIC', 'Áo Polo Nam Classic', 'Thời trang nam', 250000),
        ('somi', 'SHIRT-LINEN', 'Áo Sơ Mi Linen Cổ Tàu', 'Thời trang công sở', 320000),
        ('short', 'SHORT-KAKI', 'Quần Short Kaki Co Giãn', 'Quần nam', 180000),
    ]
    for product_id, sku, name, category, price in products:
        cur.execute(
            """INSERT INTO products (id, workspace_id, sku, name, category, price_vnd, stock_quantity, created_at)
               VALUES (?, 'ws', ?, ?, ?, ?, 10, ?)""",
            (product_id, sku, name, category, price, now),
        )
    conn.commit()
    conn.close()


def run_tests() -> None:
    with tempfile.TemporaryDirectory(prefix='semantic-matcher-') as directory:
        db_path = Path(directory) / 'inbox.db'
        seed(db_path)
        catalog = ProductCatalogEngine(db_path=db_path)
        cases = {
            'ao polo nam gia bao nhieu': 'POLO-CLASSIC',
            'ao phong con hang khong': 'POLO-CLASSIC',
            'ao plolo size m': 'POLO-CLASSIC',
            'ao somi linen co tau': 'SHIRT-LINEN',
            'somi size xl': 'SHIRT-LINEN',
            'quan sooc mau den': 'SHORT-KAKI',
            'quan shrot kaki': 'SHORT-KAKI',
        }
        for query, expected_sku in cases.items():
            product = catalog.find_product_by_query('ws', query)
            assert product and product['sku'] == expected_sku, (query, product)
        assert catalog.find_product_by_query('ws', 'iphone 16 pro max') is None
        assert normalize_vietnamese('Áo Đẹp') == 'ao dep'
        assert levenshtein_distance('plolo', 'polo') == 1
    print('ALL SEMANTIC MATCHER TESTS PASSED (100%)')


if __name__ == '__main__':
    run_tests()
