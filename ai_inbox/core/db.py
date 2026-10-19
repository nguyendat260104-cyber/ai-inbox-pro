#!/usr/bin/env python3
"""
AI Inbox & Sales Management Platform - Database Layer
Local-first, zero-dependency SQLite architecture with multi-tenant workspace isolation.
"""

import sqlite3
import os
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

DB_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "inbox.db"

def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target = db_path or DB_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize schema for multi-tenant AI Inbox & Lead Management."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.executescript("""
    -- 1. Workspaces (Multi-tenant)
    CREATE TABLE IF NOT EXISTS workspaces (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        plan TEXT NOT NULL DEFAULT 'starter',
        monthly_conv_quota INTEGER NOT NULL DEFAULT 500,
        max_staff_seats INTEGER NOT NULL DEFAULT 2,
        subscription_status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL
    );

    -- 2. Staff / Users
    CREATE TABLE IF NOT EXISTS staff (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'sales_rep', -- 'admin', 'manager', 'sales_rep'
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
    );

    -- 3. Product Catalog (Grounded Truth for AI)
    CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        sku TEXT NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price_vnd INTEGER NOT NULL,
        stock_quantity INTEGER NOT NULL DEFAULT 0,
        sizes_json TEXT DEFAULT '[]',
        colors_json TEXT DEFAULT '[]',
        description TEXT,
        shipping_policy TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
    );

    -- 4. Customers
    CREATE TABLE IF NOT EXISTS customers (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        name TEXT,
        phone TEXT,
        channel TEXT NOT NULL, -- 'web_widget', 'facebook_page', 'zalo_oa'
        external_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
    );

    -- 5. Conversations
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        channel TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'bot_handling', -- 'bot_handling', 'assigned_human', 'closed'
        assigned_staff_id TEXT,
        unread_count INTEGER DEFAULT 0,
        last_message_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
        FOREIGN KEY (assigned_staff_id) REFERENCES staff(id) ON DELETE SET NULL
    );

    -- 5b. Order details collected by the AI across chat turns.  Keeping this
    -- separate from conversations makes the state explicit and avoids storing
    -- personal delivery data in message parsing scratch space.
    CREATE TABLE IF NOT EXISTS conversation_slots (
        conversation_id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        product_id TEXT,
        product_sku TEXT,
        size TEXT,
        color TEXT,
        quantity INTEGER,
        shipping_address TEXT,
        phone_number TEXT,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
    );

    -- 6. Messages
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        sender_type TEXT NOT NULL, -- 'customer', 'bot', 'staff'
        sender_name TEXT,
        content TEXT NOT NULL,
        intent TEXT,
        metadata_json TEXT DEFAULT '{}',
        timestamp TEXT NOT NULL,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
    );

    -- 7. Leads (Sales Pipeline)
    CREATE TABLE IF NOT EXISTS leads (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        conversation_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'new', -- 'new', 'ai_qualified', 'assigned', 'contacted', 'negotiating', 'won', 'lost'
        score INTEGER NOT NULL DEFAULT 0,    -- 0 to 100
        intent_label TEXT NOT NULL DEFAULT 'COLD', -- 'HOT', 'WARM', 'COLD'
        interested_product_id TEXT,
        estimated_value_vnd INTEGER DEFAULT 0,
        notes TEXT,
        assigned_staff_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
        FOREIGN KEY (interested_product_id) REFERENCES products(id) ON DELETE SET NULL,
        FOREIGN KEY (assigned_staff_id) REFERENCES staff(id) ON DELETE SET NULL
    );

    -- 8. Draft orders and soft inventory locks. Drafts do not decrement stock;
    -- active locks are considered when another checkout attempts a reservation.
    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        customer_id TEXT,
        conversation_id TEXT,
        product_id TEXT NOT NULL,
        sku TEXT NOT NULL,
        quantity INTEGER NOT NULL CHECK (quantity > 0),
        unit_price_vnd INTEGER NOT NULL,
        subtotal_vnd INTEGER NOT NULL,
        shipping_fee_vnd INTEGER NOT NULL,
        total_vnd INTEGER NOT NULL,
        shipping_address TEXT,
        status TEXT NOT NULL DEFAULT 'draft',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
    );

    CREATE TABLE IF NOT EXISTS inventory_locks (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        product_id TEXT NOT NULL,
        order_id TEXT NOT NULL,
        quantity INTEGER NOT NULL CHECK (quantity > 0),
        status TEXT NOT NULL DEFAULT 'active',
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_inventory_locks_active
        ON inventory_locks(product_id, status, expires_at);

    -- 9. Activity & Audit Logs
    CREATE TABLE IF NOT EXISTS activity_logs (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        details_json TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
    );
    """)

    # Backward compatibility migrations for existing SQLite databases
    cur.execute("PRAGMA table_info(workspaces)")
    existing_cols = {row["name"] for row in cur.fetchall()}
    if "plan" not in existing_cols:
        cur.execute("ALTER TABLE workspaces ADD COLUMN plan TEXT NOT NULL DEFAULT 'starter'")
    if "monthly_conv_quota" not in existing_cols:
        cur.execute("ALTER TABLE workspaces ADD COLUMN monthly_conv_quota INTEGER NOT NULL DEFAULT 500")
    if "max_staff_seats" not in existing_cols:
        cur.execute("ALTER TABLE workspaces ADD COLUMN max_staff_seats INTEGER NOT NULL DEFAULT 2")
    if "subscription_status" not in existing_cols:
        cur.execute("ALTER TABLE workspaces ADD COLUMN subscription_status TEXT NOT NULL DEFAULT 'active'")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_FILE}")
