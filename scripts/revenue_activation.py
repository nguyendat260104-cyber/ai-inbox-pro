#!/usr/bin/env python3
"""Safety gates for converting an affiliate offer into an executable campaign.

This module deliberately does not log in, publish content, spend money, or
handle payout credentials. It validates only the non-secret activation record.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
from urllib.parse import urlparse


APPROVED = "approved"


@dataclass(frozen=True)
class ActivationResult:
    ready: bool
    blockers: List[str]


def _is_http_url(value: Any) -> bool:
    try:
        parsed = urlparse(str(value))
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def validate_campaign_activation(
    campaign: Dict[str, Any], accounts: List[Dict[str, Any]]
) -> ActivationResult:
    """Return whether a campaign is safe to hand to a human for publishing."""
    blockers: List[str] = []
    platform = str(campaign.get("platform", "")).lower().strip()
    account = next(
        (a for a in accounts if str(a.get("platform", "")).lower() == platform),
        None,
    )
    if not account:
        blockers.append(f"missing_account:{platform or 'unknown'}")
    else:
        if account.get("status") != APPROVED:
            blockers.append("affiliate_account_not_approved")
        if account.get("payout_status") != APPROVED:
            blockers.append("payout_not_verified")

    if not _is_http_url(campaign.get("affiliate_url")):
        blockers.append("affiliate_url_missing_or_invalid")
    if not str(campaign.get("tracking_id", "")).strip():
        blockers.append("tracking_id_missing")
    if not str(campaign.get("product_id", "")).strip():
        blockers.append("product_id_missing")
    if campaign.get("publish_mode") not in {"human_review", "manual_publish"}:
        blockers.append("publish_mode_must_be_human_review")

    return ActivationResult(ready=not blockers, blockers=blockers)


def activation_summary(accounts: List[Dict[str, Any]], campaigns: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = [validate_campaign_activation(c, accounts) for c in campaigns]
    prep = [campaign_preparation_status(c, accounts) for c in campaigns]
    return {
        "accounts": accounts,
        "campaign_count": len(campaigns),
        "ready_campaigns": sum(r.ready for r in results),
        "blocked_campaigns": sum(not r.ready for r in results),
        "prep_ready_campaigns": sum(r["prep_ready"] for r in prep),
        "prep_blockers": {c.get("campaign_id", "unknown"): c["blockers"] for c in prep if c["blockers"]},
        "next_action": "Confirm account approval and payout, then import real affiliate URLs."
        if not all(a.get("status") == APPROVED and a.get("payout_status") == APPROVED for a in accounts if a.get("platform") in {"shopee", "lazada"})
        else "Import real affiliate URLs and tracking IDs; human review is still required before publishing.",
    }


def campaign_preparation_status(
    campaign: Dict[str, Any], accounts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Allow planning while payout is pending, without claiming publish readiness.

    Preparation only requires an approved affiliate account and non-secret
    tracking metadata. A real product/link is intentionally a user-supplied
    field; missing values are reported rather than invented.
    """
    blockers: List[str] = []
    platform = str(campaign.get("platform", "")).lower().strip()
    account = next(
        (a for a in accounts if str(a.get("platform", "")).lower() == platform), None
    )
    if not account:
        blockers.append(f"missing_account:{platform or 'unknown'}")
    elif account.get("status") != APPROVED:
        blockers.append("affiliate_account_not_approved")
    if not str(campaign.get("tracking_id", "")).strip():
        blockers.append("tracking_id_missing")
    if not str(campaign.get("product_id", "")).strip():
        blockers.append("needs_user_product_id")
    if not _is_http_url(campaign.get("affiliate_url")):
        blockers.append("needs_user_affiliate_link")
    return {
        "campaign_id": campaign.get("campaign_id", campaign.get("id", "unknown")),
        "prep_ready": not blockers,
        "payout_pending": bool(account and account.get("payout_status") != APPROVED),
        "blockers": blockers,
    }
