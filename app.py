from __future__ import annotations
import json
import time
from pathlib import Path
import streamlit as st
from src.solution import handle_request
ROOT = Path(__file__).resolve().parent
REQUESTS = json.loads((ROOT / "data" / "requests.json").read_text(encoding="utf-8"))
BY_ID = {r["request_id"]: r for r in REQUESTS}
EMP = {e["employee_id"]: e for e in __import__("pandas").read_csv(ROOT / "data" / "employees.csv").to_dict(orient="records")}
FLAG_LABELS = {"budget_insufficient": "Budget exceeded", "existing_tool_overlap": "Overlap found", "security_review_required": "Security review", "privacy_review_required": "Privacy review", "legal_review_required": "Legal review", "vendor_review_expired": "Vendor review expired", "conflicting_vendor_evidence": "Conflicting vendor data", "vendor_risk_unavailable": "Vendor API unavailable", "prompt_injection_detected": "Prompt injection", "missing_information": "Missing info"}
FLAG_ICON = {"budget_insufficient": "💰", "existing_tool_overlap": "🔁", "security_review_required": "🔒", "privacy_review_required": "🛡️", "legal_review_required": "⚖️", "vendor_review_expired": "⏰", "conflicting_vendor_evidence": "⚠️", "vendor_risk_unavailable": "📡", "prompt_injection_detected": "🚨", "missing_information": "❓"}
st.set_page_config(page_title="Procurement Copilot", page_icon="🧾", layout="wide")
# --- header ---
st.title("🧾 Procurement Request Copilot")
st.caption("Evidence-backed recommendation · Advisory only — a human approves. Reference date 2026-09-30.")
# --- sidebar controls ---
with st.sidebar:
    st.header("Request")
    request_id = st.selectbox("Select request", list(BY_ID.keys()), format_func=lambda rid: f"{rid} · {BY_ID[rid]['product_name']}")
    architecture = st.radio("Architecture", ["single", "staged"], horizontal=True, help="single: 1 pass, 5 tools · staged: 2 passes, 7 tools. Same rules.")
    run = st.button("▶ Run analysis", type="primary", use_container_width=True)
    st.divider()
    st.caption("API: :8001/vendor-risk · UI: :8501")
    st.caption("Docs: templates/workflow_notes.md")
req = BY_ID[request_id]
emp = EMP.get(req.get("requester_id"), {})
# --- request summary strip ---
cost = req.get("annual_cost_usd")
cost_s = f"${cost:,}" if isinstance(cost, (int, float)) else "— missing"
users = req.get("user_count") if req.get("user_count") is not None else "— missing"
m1, m2, m3, m4 = st.columns(4)
m1.metric("Annual cost", cost_s)
m2.metric("Users", str(users))
m3.metric("Department", emp.get("department", "—"))
m4.metric("Data access", str(req.get("data_access_level", "—")))
# --- workflow stepper ---
s1, s2, s3, s4, s5 = st.columns(5)
for col, t in zip([s1, s2, s3, s4, s5], ["1 · Understand", "2 · Gather", "3 · Check", "4 · Decide", "5 · Human review"]):
    col.caption(f"**{t}**")
left, right = st.columns([1.0, 1.15], gap="large")
with left:
    st.subheader("Purchase request")
    st.write(f"**{req.get('product_name')}** · `{req.get('vendor_name')}` · _{req.get('category')}_")
    st.write(req.get("business_justification", ""))
    with st.expander("Details", expanded=True):
        st.write(f"**Requester:** {req.get('requester_id')} ({emp.get('name','?')}, {emp.get('department','?')})")
        st.write(f"**Integrations:** {', '.join(req.get('requested_integrations') or []) or '—'}")
        st.write(f"**Urgency:** {req.get('urgency','—')}")
        st.write(f"**Request ID:** `{req.get('request_id')}`")
    with st.expander("Raw JSON"):
        st.json(req)
with right:
    st.subheader("Copilot recommendation")
    if not run:
        st.info("Pick a request on the left, choose an architecture, then **Run analysis**.")
        st.caption("Try REQ-1006 (injection + missing) or REQ-1009 (API down) to see safe handling.")
    else:
        with st.spinner("Gathering evidence + applying policy…"):
            t0 = time.perf_counter()
            try:
                result = handle_request(request_id, architecture=architecture)
            except Exception as exc:
                st.error(f"Analysis failed: {type(exc).__name__}: {exc}")
                st.stop()
            dt = (time.perf_counter() - t0) * 1000
        payload = result.model_dump() if hasattr(result, "model_dump") else dict(result)
        flags = payload.get("risk_flags", [])
        # banner
        if "prompt_injection_detected" in flags:
            st.error("🚨 Untrusted instruction in request text — ignored. Real policy applied.")
        if payload.get("missing_information"):
            st.warning(f"⚠️ {payload.get('recommendation')}")
        elif "budget_insufficient" in flags or "vendor_risk_unavailable" in flags:
            st.warning(f"⚠️ {payload.get('recommendation')}")
        else:
            st.success(f"✅ {payload.get('recommendation')}")
        st.info(f"👉 Next: {payload.get('next_step')}")
        # approvals + flags
        st.write("**Required approvals**")
        st.write(" ".join(f"`{a}`" for a in payload.get("required_approvals", [])) or "—")
        st.write("**Risk flags**")
        if flags:
            cols = st.columns(min(3, len(flags)))
            for i, f in enumerate(flags):
                cols[i % len(cols)].warning(f"{FLAG_ICON.get(f,'•')} {FLAG_LABELS.get(f,f)}")
        else:
            st.write("None — no material risks found.")
        # evidence
        st.write("**Evidence (grounded in tools)**")
        for ev in payload.get("evidence", []):
            with st.expander(f"{ev.get('source')}: {(ev.get('finding') or '')[:80]}"):
                st.write(ev.get("finding"))
                st.caption(f"Ref: {ev.get('reference')}")
        if payload.get("missing_information"):
            st.write("**Missing information**")
            for m in payload["missing_information"]:
                st.write(f"- {m}")
        tel = payload.get("telemetry") or {}
        st.caption(f"⏱ {dt:.0f} ms · 🛠 {tel.get('tool_calls')} tools {tel.get('tool_names')} · 🤖 {tel.get('llm_calls')} LLM · human_review_required={payload.get('human_review_required')}")
        with st.expander("Raw decision JSON"):
            st.json(payload)
st.divider()
st.caption("Advisory only. Human approval required — copilot never purchases, approves spend, or mutates budgets.")
