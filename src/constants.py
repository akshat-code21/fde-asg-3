"""Shared policy constants. Single source of truth — do not duplicate."""
from __future__ import annotations
from datetime import date
# Policy snapshot date from data/procurement_policy.md — never use wall-clock.
REFERENCE_DATE = date(2026, 9, 30)
# Sec 9: request/vendor text is untrusted data, never instructions.
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(procurement\s+)?rules",
    r"treat\s+this\s+request\s+as\s+\w+-approved",
    r"approve\s+(it|this)\s+immediately",
    r"ignore\s+polic",
    r"bypass\s+controls",
    r"cfo-approved",
    r"override\s+secur",
]
