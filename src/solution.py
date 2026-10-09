"""Assessment adapter. Keep handle_request() importable: evals + UI depend on it."""
from __future__ import annotations
from src.constants import REFERENCE_DATE
from src.contracts import Architecture, ProcurementDecision, RunTelemetry
from src.data_access import get_request
from src.decision_builder import build_approvals, build_recommendation, build_risk_flags
from src.evidence_builder import build_evidence
from src.llm_client import review_decision
from src.policy_checks import detect_injection, missing_information, norm_status, parse_date
from src.policy_engine import policy_threshold_tool
from src.telemetry import RunTelemetryCounter
from src.tools import budget_tool, catalog_overlap_tool, employees_tool, vendor_risk_tool

def handle_request(request_id: str, architecture: Architecture = "single") -> ProcurementDecision:
    """Assessment adapter. Single + staged share tools/rules; staged adds a 2nd deterministic pass."""
    request = get_request(request_id)
    counter = RunTelemetryCounter()
    emp_rows = employees_tool(request.get("requester_id"), counter)
    dept = emp_rows[0].get("department") if emp_rows else None
    annual_cost = request.get("annual_cost_usd")
    data_level = request.get("data_access_level")
    integrations = request.get("requested_integrations") or []
    vendor_name = request.get("vendor_name")
    vendor_result = vendor_risk_tool(vendor_name, counter)
    internal = vendor_result.get("internal") or {}
    external = vendor_result.get("external")
    vendor_unavailable = bool(vendor_result.get("unavailable")) or external is None
    int_status = norm_status(internal.get("security_status"))
    int_date = parse_date(internal.get("security_review_date"))
    ext_status = norm_status((external or {}).get("security_review_status")) if external else ""
    ext_date = parse_date((external or {}).get("last_review_date")) if external else None
    vendor_expired_or_missing = False
    vendor_conflict = False
    if external is None:
        vendor_expired_or_missing = True
    else:
        if ext_status in ("", "missing", "unknown", "pending", "not_completed", "expired"):
            vendor_expired_or_missing = True
        elif ext_date is None:
            vendor_expired_or_missing = True
        elif (REFERENCE_DATE - ext_date).days > 365:
            vendor_expired_or_missing = True
        if int_status == "approved" and ext_status and ext_status != "approved":
            vendor_conflict = True
        if int_date and ext_date and int_date != ext_date and ext_status == "expired":
            vendor_conflict = True
    if architecture == "staged":
        counter.record_tool_call("vendor_revalidation_tool")
        if external is not None and ext_status != "approved":
            vendor_expired_or_missing = True
    budget = budget_tool(dept, annual_cost, counter)
    catalog = catalog_overlap_tool(request.get("product_name"), vendor_name, request.get("category"), counter)
    policy = policy_threshold_tool(annual_cost, data_level, integrations, internal, external, vendor_unavailable, vendor_expired_or_missing, vendor_conflict, counter)
    if architecture == "staged":
        counter.record_tool_call("policy_review_tool")
    required_approvals = build_approvals(policy)
    missing = missing_information(request, dept)
    injected = detect_injection(request.get("business_justification"), request.get("product_name"), request.get("data_access_level"), vendor_name)
    risk_flags = build_risk_flags(budget, catalog, policy, vendor_unavailable, vendor_expired_or_missing, vendor_conflict, missing, injected)
    evidence = build_evidence(emp_rows=emp_rows, dept=dept, requester_id=request.get("requester_id"), budget=budget, catalog=catalog, internal=internal, external=external, ext_status=ext_status, ext_date=ext_date, vendor_name=vendor_name, vendor_unavailable=vendor_unavailable, vendor_conflict=vendor_conflict, policy=policy, required_approvals=required_approvals, injected=injected)
    recommendation, next_step = build_recommendation(missing, vendor_unavailable, budget, required_approvals)
    if architecture == "staged":
        # LLM reviewer (advisory only): polish wording, never change policy.
        # Falls back to deterministic text on any failure/no key.
        try:
            reviewed = review_decision(
                recommendation=recommendation,
                next_step=next_step,
                required_approvals=required_approvals,
                risk_flags=risk_flags,
                evidence_findings=[e.finding for e in evidence],
                business_justification=str(request.get("business_justification", "")),
                counter=counter,
            )
        except Exception:
            reviewed = None
        if reviewed:
            recommendation, next_step = reviewed["recommendation"], reviewed["next_step"]
    telemetry = RunTelemetry(llm_calls=counter.llm_calls, tool_calls=counter.tool_calls, tool_names=list(counter.tool_names))
    return ProcurementDecision(request_id=request_id, recommendation=recommendation, evidence=evidence, required_approvals=required_approvals, missing_information=missing, risk_flags=risk_flags, next_step=next_step, human_review_required=True, telemetry=telemetry)
