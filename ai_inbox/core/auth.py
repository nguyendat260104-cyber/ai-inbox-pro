"""
AI Inbox & Sales Management - Multi-Tenant Authentication & RBAC Engine
Cryptographic, dependency-free token authentication and role-based access control.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Set

from ai_inbox.core.db import get_connection

AUTH_SECRET_KEY = "ai-inbox-enterprise-auth-secret-key-2026"

ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "admin": {
        "inbox:read", "inbox:write", "inbox:takeover",
        "kanban:read", "kanban:write",
        "leads:export",
        "products:read", "products:create", "products:update", "products:delete",
        "billing:read", "billing:update",
        "staff:read", "staff:write"
    },
    "manager": {
        "inbox:read", "inbox:write", "inbox:takeover",
        "kanban:read", "kanban:write",
        "leads:export",
        "products:read", "products:create", "products:update",
        "billing:read",
        "staff:read"
    },
    "sales_rep": {
        "inbox:read", "inbox:write", "inbox:takeover",
        "kanban:read", "kanban:write",
        "products:read",
        "staff:read"
    }
}


def generate_token(
    staff_id: str,
    workspace_id: str,
    role: str = "sales_rep",
    expires_in_seconds: int = 86400 * 30,
    secret: str = AUTH_SECRET_KEY
) -> str:
    """Generate a tamper-proof HMAC-SHA256 signed session token."""
    payload = {
        "staff_id": staff_id,
        "workspace_id": workspace_id,
        "role": role,
        "exp": int(time.time()) + expires_in_seconds
    }
    raw_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(raw_payload).decode("ascii").rstrip("=")
    signature = hmac.new(secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded_payload}.{signature}"


def verify_token(
    token: str,
    secret: str = AUTH_SECRET_KEY,
    db_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """Verify cryptographic token signature, expiration and optional staff database record."""
    if not token or "." not in token:
        return None

    parts = token.split(".", 1)
    if len(parts) != 2:
        return None

    encoded_payload, signature = parts
    expected_sig = hmac.new(secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_sig):
        return None

    try:
        # Restore base64 padding
        padding = 4 - (len(encoded_payload) % 4)
        if padding != 4:
            encoded_payload += "=" * padding
        raw_json = base64.urlsafe_b64decode(encoded_payload.encode("ascii")).decode("utf-8")
        payload = json.loads(raw_json)

        # Check expiration
        if payload.get("exp", 0) < time.time():
            return None

        # Verify against database if db_path is provided
        if db_path:
            conn = get_connection(db_path)
            try:
                row = conn.execute(
                    "SELECT id, workspace_id, role, is_active FROM staff WHERE id = ?",
                    (payload.get("staff_id"),)
                ).fetchone()
                if not row or not row["is_active"]:
                    return None
                # Update role and workspace from DB truth
                payload["role"] = row["role"]
                payload["workspace_id"] = row["workspace_id"]
            finally:
                conn.close()

        return payload
    except Exception:
        return None


def has_permission(role: str, permission: str) -> bool:
    """Check if the given role possesses the requested permission."""
    allowed = ROLE_PERMISSIONS.get(role, set())
    return permission in allowed


def authorize_tenant_access(
    staff_workspace_id: str,
    target_workspace_id: str,
    required_role: Optional[str] = None,
    current_role: Optional[str] = None
) -> bool:
    """
    Enforce strict tenant isolation:
    Staff from workspace A can NEVER access or mutate records belonging to workspace B.
    """
    if not staff_workspace_id or not target_workspace_id:
        return False

    if staff_workspace_id != target_workspace_id:
        return False

    if required_role and current_role:
        role_hierarchy = {"admin": 3, "manager": 2, "sales_rep": 1}
        if role_hierarchy.get(current_role, 0) < role_hierarchy.get(required_role, 0):
            return False

    return True
