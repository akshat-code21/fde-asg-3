"""Build approvals, flags, recommendation from tool outputs. Pure logic."""
from __future__ import annotations

def build_approvals(policy: dict) -> list[str]:
    approvals: list[str] = list(policy.get("business_approvals", []))
    if policy.get("need_security") and "Security" not in approvals:
        approvals.append("Security")
    if policy.get("need_privacy") and "Privacy" not in approvals:
        approvals.append("Privacy")
    if policy.get("need_legal") and "Legal" not in approvals:
        approvals.append("Legal")
    if not approvals:
        approvals = ["Department Head", "Procurement"]
        if policy.get("need_security") and "Security" not in approvals:
            approvals.append("Security")
    return approvals

def build_risk_flags(budget: dict, catalog: dict, policy: dict, vendor_unavailable: bool, vendor_expired_or_missing: bool, vendor_conflict: bool, missing: list[str], injected: bool) -> list[str]:
    flags: list[str] = []
    if budget.get("can_afford") is False:
        flags.append("budget_insufficient")
    if catalog.get("overlap"):
        flags.append("existing_tool_overlap")
    if policy.get("need_security"):
        flags.append("security_review_required")
    if policy.get("need_privacy"):
        flags.append("privacy_review_required")
    if policy.get("need_legal"):
        flags.append("legal_review_required")
    if vendor_unavailable:
        flags.append("vendor_risk_unavailable")
    if vendor_expired_or_missing and not vendor_unavailable:
        flags.append("vendor_review_expired")
    if vendor_conflict:
        flags.append("conflicting_vendor_evidence")
    if missing and "missing_information" not in flags:
        flags.append("missing_information")
    if injected and "prompt_injection_detected" not in flags:
        flags.append("prompt_injection_detected")
    return flags

def build_recommendation(missing: list[str], vendor_unavailable: bool, budget: dict, required_approvals: list[str]) -> tuple[str, str]:
    where = ", ".join(required_approvals) if required_approvals else "hiring manager"
    if missing:
        return (
            "Request clarification before approval - material information missing",
            f"Ask requester for {'; '.join(missing)} and resubmit; route evidence package to {where} for human review.",
        )
    if vendor_unavailable:
        return (
            "Route for required reviews before approval - vendor assessment unverified",
            f"Send the evidence package to {where} for human review; do not approve until vendor security assessment is verified.",
        )
    if budget.get("can_afford") is False:
        return (
            "Route for Finance budget exception review before approval",
            f"Send the evidence package to {where} for human review; Finance must decide the budget exception.",
        )
    return (
        "Route for required reviews before approval",
        f"Send the evidence package to {where} for human review.",
    )
