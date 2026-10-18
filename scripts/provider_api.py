#!/usr/bin/env python3
"""API-first provider abstraction with explicit authorization gates.

This module does not make network calls. A future provider adapter may call an
official API only after the user authorizes it and supplies a secure runtime
credential through the host environment. Secrets are never persisted here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
from urllib.parse import urlparse

API_READY = "api_ready"
USER_AUTH_REQUIRED = "user_authorization_required"
PORTAL_FALLBACK_BLOCKED = "portal_fallback_blocked"


@dataclass(frozen=True)
class ProviderGate:
    state: str
    ready: bool
    blockers: List[str]


def validate_provider_metadata(provider: Dict[str, Any]) -> ProviderGate:
    state = str(provider.get("authorization_state", "")).strip()
    blockers: List[str] = []
    if state not in {API_READY, USER_AUTH_REQUIRED, PORTAL_FALLBACK_BLOCKED}:
        blockers.append("unknown_provider_state")
    if state != API_READY:
        blockers.append("provider_api_not_authorized")
    if state == API_READY and not provider.get("api_base_url"):
        blockers.append("api_base_url_missing")
    if provider.get("credential_ref") and any(secret in str(provider.get("credential_ref")).lower() for secret in ["token", "key", "secret", "password"]):
        blockers.append("credential_ref_must_be_non_secret_reference")
    return ProviderGate(state=state, ready=not blockers, blockers=blockers)


def validate_api_campaign(campaign: Dict[str, Any], provider: Dict[str, Any]) -> ProviderGate:
    gate = validate_provider_metadata(provider)
    blockers = list(gate.blockers)
    affiliate_url = campaign.get("affiliate_url")
    if not isinstance(affiliate_url, str) or urlparse(affiliate_url).scheme not in {"http", "https"}:
        blockers.append("affiliate_link_missing_or_invalid")
    if not str(campaign.get("product_id", "")).strip():
        blockers.append("product_id_missing")
    if not str(campaign.get("tracking_id", "")).strip():
        blockers.append("tracking_id_missing")
    return ProviderGate(state=gate.state, ready=not blockers, blockers=blockers)


def build_link_request(campaign: Dict[str, Any]) -> Dict[str, Any]:
    """Create a non-secret request payload for an official provider adapter."""
    return {
        "campaign_id": campaign.get("campaign_id"),
        "source_url": campaign.get("source_url") or campaign.get("affiliate_url"),
        "product_id": campaign.get("product_id"),
        "tracking_id": campaign.get("tracking_id"),
    }


def apply_link_response(campaign: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
    """Apply an API response while rejecting malformed/secret-bearing payloads."""
    url = response.get("affiliate_url")
    if not isinstance(url, str) or urlparse(url).scheme not in {"http", "https"}:
        raise ValueError("provider response must contain a valid HTTPS/HTTP affiliate_url")
    updated = dict(campaign)
    updated["affiliate_url"] = url
    if response.get("product_id"):
        updated["product_id"] = str(response["product_id"])
    updated["link_source"] = "official_api"
    updated["status"] = "ready_for_human_review"
    return updated


def apply_metrics_response(campaign: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
    updated = dict(campaign)
    metrics = dict(updated.get("metrics") or {})
    for field in ("clicks", "orders", "confirmed_commission_vnd"):
        if field in response and isinstance(response[field], (int, float)):
            metrics[field] = response[field]
    updated["metrics"] = metrics
    updated["metrics_source"] = "official_api"
    return updated
