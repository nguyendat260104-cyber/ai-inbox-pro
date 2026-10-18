#!/usr/bin/env python3
"""Rank campaign preparation for a daily human lead review."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


def rank_campaigns(campaigns: Iterable[Dict[str, Any]], accounts: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    account_map = {str(a.get("platform", "")).lower(): a for a in accounts}
    ranked = []
    for campaign in campaigns:
        item = dict(campaign)
        account = account_map.get(str(item.get("platform", "")).lower(), {})
        metrics = item.get("metrics") or {}
        clicks = metrics.get("clicks") if isinstance(metrics.get("clicks"), (int, float)) else 0
        orders = metrics.get("orders") if isinstance(metrics.get("orders"), (int, float)) else 0
        verified_link = bool(item.get("affiliate_url")) and item.get("affiliate_url") != "needs_verification"
        evidence = (2 if account.get("status") == "approved" else 0) + (2 if verified_link else 0)
        evidence += min(4, int(clicks // 30)) + min(4, int(orders))
        item["lead_review_score"] = evidence
        item["lead_review_gate"] = "TEST_WITH_EVIDENCE" if evidence >= 5 else "PREP_ONLY"
        item["observed_conversion_rate"] = (orders / clicks) if clicks > 0 else None
        ranked.append(item)
    return sorted(ranked, key=lambda x: (x["lead_review_score"], x.get("campaign_id", "")), reverse=True)
