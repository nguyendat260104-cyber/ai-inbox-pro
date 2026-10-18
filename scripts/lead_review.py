#!/usr/bin/env python3
"""Rank campaign preparation for a daily human lead review."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

SCORING_WEIGHTS = {
    "accessibility": 20,
    "demand_hotness_evidence": 25,
    "purchase_ease": 20,
    "content_fit": 20,
    "compliance_measurement": 15,
}


def rank_campaigns(campaigns: Iterable[Dict[str, Any]], accounts: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    account_map = {str(a.get("platform", "")).lower(): a for a in accounts}
    ranked = []
    for campaign in campaigns:
        item = dict(campaign)
        account = account_map.get(str(item.get("platform", "")).lower(), {})
        metrics = item.get("metrics") or {}
        clicks = metrics.get("clicks") if isinstance(metrics.get("clicks"), (int, float)) else 0
        orders = metrics.get("orders") if isinstance(metrics.get("orders"), (int, float)) else 0
        score, components, gates = score_campaign(item, account, clicks, orders)
        item["lead_review_score"] = score
        item["lead_review_components"] = components
        item["lead_review_gate"] = "BLOCKED" if gates else ("TEST_WITH_EVIDENCE" if score >= 60 else "PREP_ONLY")
        item["hard_gates"] = gates
        item["observed_conversion_rate"] = (orders / clicks) if clicks > 0 else None
        ranked.append(item)
    return sorted(ranked, key=lambda x: (x["lead_review_score"], x.get("campaign_id", "")), reverse=True)


def score_campaign(campaign: Dict[str, Any], account: Dict[str, Any], clicks: float = 0, orders: float = 0):
    """Score only observable evidence; missing evidence never becomes a hotness claim."""
    affiliate_link = campaign.get("affiliate_url")
    source_url = campaign.get("source_url")
    hard_gates = []
    if not affiliate_link or affiliate_link == "needs_verification":
        hard_gates.append("affiliate_link_missing")
    if not campaign.get("commission_source"):
        hard_gates.append("commission_source_missing_needs_verification")
    components = {
        "accessibility": 20 if account.get("status") == "approved" and (affiliate_link or source_url) else 0,
        "demand_hotness_evidence": min(25, int(campaign.get("demand_evidence_points", 0))),
        "purchase_ease": min(20, int(campaign.get("purchase_ease_points", 0))),
        "content_fit": min(20, int(campaign.get("content_fit_points", 0))),
        "compliance_measurement": min(15, int(campaign.get("compliance_points", 0))),
    }
    # Observed outcomes add evidence only after a link exists; no forecast is inferred.
    if affiliate_link and clicks >= 30:
        components["demand_hotness_evidence"] = min(25, components["demand_hotness_evidence"] + min(5, int(clicks // 30)))
    if affiliate_link and orders > 0:
        components["purchase_ease"] = min(20, components["purchase_ease"] + min(5, int(orders)))
    return sum(components.values()), components, hard_gates
