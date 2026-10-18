#!/usr/bin/env python3
"""
Multi-Tenant Registration & VietQR Billing Integration Engine
Provides self-service merchant signup, quota enforcement, and automated VietQR generation.
"""

import os
import json
import uuid
import urllib.parse
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

from ai_inbox.core.db import get_connection

DEFAULT_BANK_BIN = os.getenv("VIETQR_BANK_BIN", "970422")  # MBBank BIN
DEFAULT_BANK_NAME = os.getenv("VIETQR_BANK_NAME", "MBBank (Ngân Hàng Quân Đội)")
DEFAULT_ACCOUNT_NO = os.getenv("VIETQR_ACCOUNT_NO", "0988888888")
DEFAULT_ACCOUNT_NAME = os.getenv("VIETQR_ACCOUNT_NAME", "AI INBOX PLATFORM VIET NAM")

PLANS: Dict[str, Dict[str, Any]] = {
    "starter": {
        "code": "starter",
        "name": "Gói Khởi Nghiệp (Starter)",
        "price_vnd": 299000,
        "monthly_conv_quota": 500,
        "max_staff_seats": 2,
        "description": "Dành cho shop online nhỏ, 1-2 nhân viên xử lý đến 500 khách/tháng."
    },
    "growth": {
        "code": "growth",
        "name": "Gói Tăng Trưởng (Growth)",
        "price_vnd": 599000,
        "monthly_conv_quota": 2000,
        "max_staff_seats": 5,
        "description": "Dành cho shop vừa chạy ads FB & Web, 5 nhân viên, đến 2.000 khách/tháng."
    },
    "pro": {
        "code": "pro",
        "name": "Gói Chuyên Nghiệp (Pro)",
        "price_vnd": 999000,
        "monthly_conv_quota": 10000,
        "max_staff_seats": 15,
        "description": "Dành cho Brand / Agency nhiều nhân sự, hỗ trợ đa kênh toàn diện."
    }
}

def generate_vietqr_payment(
    workspace_slug: str,
    plan_code: str,
    amount_vnd: int,
    bank_bin: str = DEFAULT_BANK_BIN,
    account_no: str = DEFAULT_ACCOUNT_NO,
    account_name: str = DEFAULT_ACCOUNT_NAME
) -> Dict[str, Any]:
    """Generates standard QuickLink VietQR URL and structured transfer details."""
    clean_slug = workspace_slug.strip().lower()
    memo = f"INBOX {clean_slug.upper()} {plan_code.upper()}"
    encoded_name = urllib.parse.quote(account_name)
    encoded_memo = urllib.parse.quote(memo)

    qr_image_url = (
        f"https://img.vietqr.io/image/{bank_bin}-{account_no}-compact2.png"
        f"?amount={amount_vnd}&addInfo={encoded_memo}&accountName={encoded_name}"
    )

    return {
        "bank_bin": bank_bin,
        "bank_name": DEFAULT_BANK_NAME,
        "account_no": account_no,
        "account_name": account_name,
        "amount_vnd": amount_vnd,
        "transfer_memo": memo,
        "qr_image_url": qr_image_url
    }

def register_workspace(
    name: str,
    slug: str,
    admin_name: str,
    admin_email: str,
    plan_code: str = "starter",
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Registers a new tenant workspace, provisions admin staff, and builds VietQR invoice."""
    clean_name = name.strip()
    clean_slug = slug.strip().lower()
    clean_admin = admin_name.strip()
    clean_email = admin_email.strip().lower()

    if not clean_name:
        raise ValueError("Workspace name cannot be empty")
    if not clean_slug:
        raise ValueError("Workspace slug cannot be empty")
    if not clean_admin or not clean_email:
        raise ValueError("Admin name and email are required")

    plan = PLANS.get(plan_code.lower())
    if not plan:
        raise ValueError(f"Invalid subscription plan '{plan_code}'. Must be one of: {list(PLANS.keys())}")

    conn = get_connection(db_path)
    cur = conn.cursor()

    # Check slug availability
    cur.execute("SELECT id FROM workspaces WHERE LOWER(slug) = ?", (clean_slug,))
    if cur.fetchone():
        conn.close()
        raise ValueError(f"Workspace slug '{clean_slug}' is already taken.")

    workspace_id = str(uuid.uuid4())
    staff_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Insert Workspace
    cur.execute(
        """INSERT INTO workspaces
           (id, name, slug, plan, monthly_conv_quota, max_staff_seats, subscription_status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 'active', ?)""",
        (workspace_id, clean_name, clean_slug, plan["code"], plan["monthly_conv_quota"], plan["max_staff_seats"], now_iso)
    )

    # 2. Insert Admin Staff
    cur.execute(
        """INSERT INTO staff (id, workspace_id, name, email, role, is_active, created_at)
           VALUES (?, ?, ?, ?, 'admin', 1, ?)""",
        (staff_id, workspace_id, clean_admin, clean_email, now_iso)
    )

    conn.commit()
    conn.close()

    # 3. Generate VietQR Payment Payload
    payment_info = generate_vietqr_payment(
        workspace_slug=clean_slug,
        plan_code=plan["code"],
        amount_vnd=plan["price_vnd"]
    )

    return {
        "success": True,
        "workspace": {
            "id": workspace_id,
            "name": clean_name,
            "slug": clean_slug,
            "plan": plan["code"],
            "monthly_conv_quota": plan["monthly_conv_quota"],
            "max_staff_seats": plan["max_staff_seats"],
            "created_at": now_iso
        },
        "admin_staff": {
            "id": staff_id,
            "name": clean_admin,
            "email": clean_email,
            "role": "admin"
        },
        "billing": {
            "plan_details": plan,
            "payment": payment_info
        }
    }

def get_workspace_billing_info(workspace_id: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Calculates active quota utilization and provides VietQR renewal information."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,))
    ws = cur.fetchone()
    if not ws:
        conn.close()
        raise ValueError(f"Workspace {workspace_id} not found.")

    # Count conversations
    cur.execute("SELECT COUNT(*) AS cnt FROM conversations WHERE workspace_id = ?", (workspace_id,))
    conv_count = cur.fetchone()["cnt"]

    # Count active staff
    cur.execute("SELECT COUNT(*) AS cnt FROM staff WHERE workspace_id = ? AND is_active = 1", (workspace_id,))
    staff_count = cur.fetchone()["cnt"]

    conn.close()

    plan_code = ws["plan"] if "plan" in ws.keys() else "starter"
    plan_info = PLANS.get(plan_code, PLANS["starter"])
    quota_limit = ws["monthly_conv_quota"] if "monthly_conv_quota" in ws.keys() else plan_info["monthly_conv_quota"]
    max_staff = ws["max_staff_seats"] if "max_staff_seats" in ws.keys() else plan_info["max_staff_seats"]

    payment_info = generate_vietqr_payment(
        workspace_slug=ws["slug"],
        plan_code=plan_code,
        amount_vnd=plan_info["price_vnd"]
    )

    return {
        "workspace_id": ws["id"],
        "name": ws["name"],
        "slug": ws["slug"],
        "plan": plan_code,
        "subscription_status": ws["subscription_status"] if "subscription_status" in ws.keys() else "active",
        "quota": {
            "conversations_used": conv_count,
            "conversations_limit": quota_limit,
            "conversations_remaining": max(0, quota_limit - conv_count),
            "staff_seats_used": staff_count,
            "staff_seats_limit": max_staff,
            "staff_seats_remaining": max(0, max_staff - staff_count)
        },
        "plan_details": plan_info,
        "payment": payment_info
    }
