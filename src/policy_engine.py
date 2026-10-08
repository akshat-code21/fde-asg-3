"""Policy engine tool (Sec 4/5/6/7). Deterministic — no LLM."""
from __future__ import annotations


def policy_threshold_tool(annual_cost, data_access_level, integrations, vendor_internal, vendor_external, vendor_unavailable, vendor_expired_or_missing, vendor_conflict, counter) -> dict:
    """Deterministic: implement procurement_policy.md Sec 4,5,6,7 as if/else."""
    counter.record_tool_call("policy_tool")

    business_approvals: list[str] = []
    if annual_cost is None:
        business_approvals = []
    elif annual_cost <= 1000:
        business_approvals = ["Manager"]
    elif annual_cost <= 10000:
        business_approvals = ["Department Head", "Procurement"]
    elif annual_cost <= 25000:
        business_approvals = ["Department Head", "Finance", "Procurement"]
    else:
        business_approvals = ["Department Head", "Finance", "CFO", "Procurement"]

    data_lower = str(data_access_level or "").lower()
    integ_text = " ".join([str(x) for x in (integrations or [])]).lower()

    security_data_triggers = [
        "source_code", "source code",
        "production",
        "confidential",
        "employee_pii", "employee pii",
        "customer_pii", "customer pii",
        "credentials", "secrets", "secret",
    ]
    needs_security_for_data = any(t in data_lower for t in security_data_triggers)
    if "pii" in data_lower:
        needs_security_for_data = True
    needs_security_for_integration = ("production" in integ_text) or ("cloud" in integ_text)

    needs_security_for_vendor = bool(vendor_unavailable or vendor_expired_or_missing or vendor_conflict)
    ext_status = ""
    stores_outside = False
    processes_personal = False
    if isinstance(vendor_external, dict):
        ext_status = str(vendor_external.get("security_review_status", "") or "").lower()
        stores_outside = bool(vendor_external.get("stores_data_outside_region", False))
        processes_personal = bool(vendor_external.get("processes_personal_data", False))
        if ext_status and ext_status != "approved":
            needs_security_for_vendor = True

    if data_lower in ("", "unknown", "none", "null") and data_lower != "none":
        if data_lower != "none":
            needs_security_for_data = True

    need_security = bool(
        needs_security_for_data or needs_security_for_integration or needs_security_for_vendor
    )

    need_privacy = False
    if ("employee_pii" in data_lower or "employee pii" in data_lower
            or "customer_pii" in data_lower or "customer pii" in data_lower
            or "pii" in data_lower):
        need_privacy = True
    if stores_outside:
        need_privacy = True

    need_legal = False
    procurement_status = str((vendor_internal or {}).get("procurement_status", "") or "")
    legal_terms = str((vendor_internal or {}).get("legal_terms_status", "") or "")
    is_new_vendor = procurement_status.strip().lower() != "approved"
    try:
        cost_for_legal = float(annual_cost) if annual_cost is not None else None
    except (TypeError, ValueError):
        cost_for_legal = None
    if is_new_vendor and cost_for_legal is not None and cost_for_legal >= 10000:
        need_legal = True
    if legal_terms.strip().lower() not in ("approved", "standard", "approved/standard"):
        need_legal = True
    if stores_outside or (processes_personal and ("pii" in data_lower or "confidential" in data_lower)):
        need_legal = True

    return {
        "business_approvals": business_approvals,
        "need_security": need_security,
        "need_privacy": need_privacy,
        "need_legal": need_legal,
        "reasons": {
            "security_data": needs_security_for_data,
            "security_integration": needs_security_for_integration,
            "security_vendor": needs_security_for_vendor,
            "external_status": ext_status,
        },
    }


