#!/usr/bin/env python3
"""
Unit and integration tests for Multi-Tenant Role-Based Access Control (RBAC) & Authentication.
"""

import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ai_inbox.core.db import get_connection, init_db
from ai_inbox.core.auth import (
    generate_token,
    verify_token,
    has_permission,
    authorize_tenant_access,
    ROLE_PERMISSIONS
)


def test_token_generation_and_tampering():
    token = generate_token(staff_id="staff-01", workspace_id="ws-01", role="admin")
    assert token and "." in token
    payload = verify_token(token)
    assert payload is not None
    assert payload["staff_id"] == "staff-01"
    assert payload["workspace_id"] == "ws-01"
    assert payload["role"] == "admin"

    # Tampered signature
    tampered_sig = token[:-4] + "abcd"
    assert verify_token(tampered_sig) is None

    # Tampered payload
    parts = token.split(".")
    tampered_payload = "eyJhZG1pbiI6dHJ1ZX0." + parts[1]
    assert verify_token(tampered_payload) is None

    # Expired token
    expired_token = generate_token(staff_id="staff-01", workspace_id="ws-01", role="admin", expires_in_seconds=-10)
    assert verify_token(expired_token) is None


def test_role_permissions():
    # Admin permissions
    assert has_permission("admin", "products:delete")
    assert has_permission("admin", "billing:update")
    assert has_permission("admin", "leads:export")
    assert has_permission("admin", "inbox:takeover")

    # Manager permissions
    assert has_permission("manager", "products:create")
    assert has_permission("manager", "leads:export")
    assert not has_permission("manager", "products:delete")
    assert not has_permission("manager", "billing:update")

    # Sales Rep permissions
    assert has_permission("sales_rep", "inbox:read")
    assert has_permission("sales_rep", "inbox:write")
    assert not has_permission("sales_rep", "leads:export")
    assert not has_permission("sales_rep", "products:create")
    assert not has_permission("sales_rep", "billing:read")


def test_tenant_isolation():
    # Same workspace allows access
    assert authorize_tenant_access("ws-fashion-01", "ws-fashion-01")

    # Cross-tenant access attempt strictly forbidden
    assert not authorize_tenant_access("ws-fashion-01", "ws-fashion-02")
    assert not authorize_tenant_access("ws-hanoi", "ws-saigon")

    # Role hierarchy checks
    assert authorize_tenant_access("ws-01", "ws-01", required_role="manager", current_role="admin")
    assert not authorize_tenant_access("ws-01", "ws-01", required_role="admin", current_role="sales_rep")


def test_database_backed_verification():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_auth.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Seed workspace and staff
        conn.execute(
            "INSERT INTO workspaces (id, name, slug, created_at) VALUES ('ws-01', 'Test Shop', 'test-shop', ?)",
            (datetime.now(timezone.utc).isoformat(),)
        )
        conn.execute(
            "INSERT INTO staff (id, workspace_id, name, email, role, is_active, created_at) VALUES ('staff-active', 'ws-01', 'Sale 1', 'sale1@shop.vn', 'sales_rep', 1, ?)",
            (datetime.now(timezone.utc).isoformat(),)
        )
        conn.execute(
            "INSERT INTO staff (id, workspace_id, name, email, role, is_active, created_at) VALUES ('staff-inactive', 'ws-01', 'Sale 2', 'sale2@shop.vn', 'sales_rep', 0, ?)",
            (datetime.now(timezone.utc).isoformat(),)
        )
        conn.commit()
        conn.close()

        # Active staff token verifies
        active_token = generate_token(staff_id="staff-active", workspace_id="ws-01", role="sales_rep")
        assert verify_token(active_token, db_path=db_path) is not None

        # Inactive staff token fails
        inactive_token = generate_token(staff_id="staff-inactive", workspace_id="ws-01", role="sales_rep")
        assert verify_token(inactive_token, db_path=db_path) is None


if __name__ == "__main__":
    test_token_generation_and_tampering()
    test_role_permissions()
    test_tenant_isolation()
    test_database_backed_verification()
    print("All RBAC & Authentication tests passed successfully!")
