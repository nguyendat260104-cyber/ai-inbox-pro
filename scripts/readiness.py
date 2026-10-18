#!/usr/bin/env python3
"""Affiliate-program readiness scoring and SCALE gating."""

from typing import Any, Dict


READINESS_WEIGHTS = {
    "ProgramOpen": 30,
    "VietnamEligible": 20,
    "ApprovalDifficulty": 15,
    "PayoutPracticality": 15,
    "CommercialTermsVerified": 20,
}
SCALE_READINESS_THRESHOLD = 60


def calculate_readiness(breakdown: Dict[str, Any]) -> int:
    """Validate and total a readiness breakdown against the configured maxima."""
    missing = set(READINESS_WEIGHTS) - set(breakdown)
    unknown = set(breakdown) - set(READINESS_WEIGHTS)
    if missing or unknown:
        raise ValueError(
            f"Invalid readiness keys; missing={sorted(missing)}, unknown={sorted(unknown)}"
        )

    total = 0
    for key, maximum in READINESS_WEIGHTS.items():
        value = breakdown[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"Readiness value for {key} must be numeric")
        if value < 0 or value > maximum:
            raise ValueError(f"Readiness value for {key} must be between 0 and {maximum}")
        total += value
    return int(total)


def apply_readiness_gate(product: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy with a calculated readiness score and enforced SCALE gate."""
    gated = dict(product)
    breakdown = gated.get("readiness_score_breakdown")
    if not isinstance(breakdown, dict):
        gated["readiness_score"] = 0
        gated["readiness_gate"] = "BLOCKED_NEEDS_VERIFICATION"
        if str(gated.get("recommendation", "")).upper().startswith("SCALE"):
            gated["recommendation"] = "HOLD"
        return gated

    readiness = calculate_readiness(breakdown)
    gated["readiness_score"] = readiness
    if readiness < SCALE_READINESS_THRESHOLD:
        gated["readiness_gate"] = "BLOCKED_BELOW_60"
        if str(gated.get("recommendation", "")).upper().startswith("SCALE"):
            gated["recommendation"] = "HOLD"
    else:
        gated["readiness_gate"] = "ELIGIBLE"
    return gated
