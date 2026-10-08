"""Assemble grounded EvidenceItems from tool outputs. Each source == telemetry name."""
from __future__ import annotations
from src.contracts import EvidenceItem

def build_evidence(*, emp_rows, dept, requester_id, budget, catalog, internal, external, ext_status, ext_date, vendor_name, vendor_unavailable, vendor_conflict, policy, required_approvals, injected) -> list[EvidenceItem]:
    evidence: list[EvidenceItem] = []
    if emp_rows:
        evidence.append(EvidenceItem(source="employees_tool", finding=f"Requester {requester_id} is in {dept}", reference=f"employees.csv:{requester_id}"))
    if budget.get("missing_cost"):
        evidence.append(EvidenceItem(source="budget_tool", finding=f"Annual cost missing; cannot verify against {dept} budget", reference="department_budgets.csv"))
    elif budget.get("budget_available") is not None:
        verdict = "within" if budget.get("can_afford") else "exceeds"
        evidence.append(EvidenceItem(source="budget_tool", finding=f"Annual cost ${budget.get('annual_cost'):,.0f} {verdict} {dept} available ${budget.get('budget_available'):,.0f}", reference="department_budgets.csv"))
    if catalog.get("overlap"):
        names = ", ".join(f"{q.get('product_name')} ({q.get('vendor_name')}/{q.get('category')})" for q in catalog.get("existing_products", [])[:3])
        evidence.append(EvidenceItem(source="catalog_overlap_tool", finding=f"Catalog overlap: {names}", reference="software_catalog.csv"))
    else:
        evidence.append(EvidenceItem(source="catalog_overlap_tool", finding="No same-product/vendor/category match in approved catalog", reference="software_catalog.csv"))
    if vendor_unavailable:
        evidence.append(EvidenceItem(source="vendor_tool", finding=f"Vendor-risk service unavailable for {vendor_name}; could not verify assessment", reference=f"GET /vendor-risk/{vendor_name}"))
    else:
        evidence.append(EvidenceItem(source="vendor_tool", finding=f"Internal registry: {internal.get('procurement_status')}/{internal.get('security_status')} review {internal.get('security_review_date')}; external: {ext_status or 'unknown'} review {ext_date or (external or {}).get('last_review_date')}", reference=f"vendors.csv + GET /vendor-risk/{vendor_name}"))
        if vendor_conflict:
            evidence.append(EvidenceItem(source="vendor_tool", finding="Internal registry and vendor-risk service disagree; routed for manual review", reference="Policy section 5"))
    evidence.append(EvidenceItem(source="policy_tool", finding=f"Policy Sec 4 minimum approvals: {', '.join(required_approvals) if required_approvals else 'to be determined pending cost'}; Security={policy.get('need_security')}, Privacy={policy.get('need_privacy')}, Legal={policy.get('need_legal')}", reference="procurement_policy.md Sec 4-7"))
    if injected:
        evidence.append(EvidenceItem(source="policy_tool", finding="Request text contains instruction-like language; treated as untrusted data and ignored", reference="Policy section 9"))
    return evidence
