"""Deterministic policy helpers (CODE). No LLM, no I/O side effects."""
from __future__ import annotations
import re
from datetime import date
from src.constants import _INJECTION_PATTERNS

def norm_status(value: object) -> str:
    return str(value or "").strip().lower()

def parse_date(value: object):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        return None

def detect_injection(*texts: object) -> bool:
    blob = " ".join(str(t or "") for t in texts).lower()
    return any(re.search(p, blob) for p in _INJECTION_PATTERNS)

def missing_information(request: dict, dept) -> list[str]:
    missing: list[str] = []
    if not request.get("requester_id") or not dept:
        missing.append("Requester and department must be confirmed")
    if not request.get("product_name") or not request.get("vendor_name"):
        missing.append("Product/vendor must be specified")
    if request.get("annual_cost_usd") is None:
        missing.append("Annual cost (or reasonable annual estimate) is missing")
    if request.get("user_count") is None:
        missing.append("Number of users/licenses is missing")
    if not str(request.get("business_justification") or "").strip():
        missing.append("Business purpose is missing")
    data_level = norm_status(request.get("data_access_level"))
    if data_level in ("", "unknown", "null", "unspecified"):
        missing.append("Intended data access level is missing or unknown")
    if request.get("requested_integrations") is None:
        missing.append("Required integrations must be confirmed")
    return missing
