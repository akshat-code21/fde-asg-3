# AI Procurement Request Copilot - FDE Assessment 3

Internal procurement copilot that inspects a software/service purchase request, gathers evidence with tools, applies deterministic policy checks, and recommends the next action while keeping approvals with humans.

## 1. Setup

**Prerequisites:** Python 3.11 or 3.12. Run from the repo root.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python verify_setup.py
# expect: PRE-FLIGHT PASSED
```

```bash
cp .env.example .env   # add only the provider key you use; never commit .env
python run_local.py
```

This starts:
- Vendor-risk API: `http://127.0.0.1:8001` (`/health`, `/vendor-risk/{vendor_name}`)
- Starter UI: `http://127.0.0.1:8501` (Streamlit `app.py` → `src/solution.py::handle_request`)

If ports are busy, free 8001/8501 and re-run. If setup fails: activate venv → `verify_setup.py` → reinstall requirements.

## 2. Product workflow

```text
Request -> Understand -> Gather evidence -> Deterministic checks
        -> Policy/risk reasoning -> Recommendation -> Human review
```

1. **Understand:** `get_request(request_id)` + `employees_tool` resolves department.
2. **Gather evidence (tools):** budget, catalog overlap, vendor registry + external risk API, policy engine.
3. **Deterministic checks (CODE):** Sec 4 thresholds, Sec 5/6/7 Security/Privacy/Legal, 365-day expiry vs `REFERENCE_DATE=2026-09-30`, Sec 1 missing fields, Sec 9 injection.
4. **Reason + recommend:** aggregate approvals/flags/missing into `ProcurementDecision`.
5. **Human review:** `human_review_required=True` always; `next_step` routes evidence package to approvers. The copilot never purchases, approves, or mutates budgets.

**Full notes + mermaid diagram: `templates/workflow_notes.md`.**

## 3. Architecture

Both variants share the same tools, policy engine, and output contract (`src/contracts.py::ProcurementDecision` via `src/solution.py::handle_request(request_id, architecture)`).

- **A `single` (ship candidate):** 1 pass - gather → check → decide. 5 tool calls, 0 LLM.
- **B `staged` (2-agent variant):** 2 passes - Pass 1 gathers + computes vendor expiry/conflict; Pass 2 re-validates via `vendor_revalidation_tool` + re-runs policy via `policy_review_tool`. 7 tool calls, 0 LLM. Same rules, auditable second pass.

## 4. Tools / agents

| Tool (telemetry name) | Type | Purpose |
|---|---|---|
| `employees_tool` | Deterministic | `requester_id` → department |
| `budget_tool` | Deterministic | `annual_cost` vs `available_usd` → `budget_insufficient` |
| `catalog_overlap_tool` | Deterministic | same product/vendor/category (OR logic) → `existing_tool_overlap` |
| `vendor_tool` | External + deterministic compare | `vendors.csv` + `GET /vendor-risk/{vendor}` → expired/conflict/unavailable |
| `policy_tool` | Deterministic | Sec 4/5/6/7 engine → business approvals + Security/Privacy/Legal |
| `vendor_revalidation_tool` (staged) | Deterministic | 2nd-pass `ext_status != approved` audit |
| `policy_review_tool` (staged) | Deterministic | reviewer re-run of policy engine |

Design split: **CODE** = thresholds, budget math, OR-overlap, expiry, missing-field, injection regex, approval union. **AI** = intentionally empty for MVP (no LLM SDK; recommendations are rule-built templates). **HUMAN** = all purchases/approvals/exceptions.

Evidence grounding: every `EvidenceItem.source` equals a `telemetry.tool_names` entry (e.g. `budget_tool → department_budgets.csv`, `vendor_tool → vendors.csv + GET /vendor-risk/{v}`, `policy_tool → procurement_policy.md Sec 4-7/9`).

## 5. Assumptions

- Date checks use `REFERENCE_DATE=2026-09-30` (policy snapshot), never wall-clock; assessment current for 365 days.
- `available_usd` snapshot from `department_budgets.csv` is source of truth for budget.
- Overlap = catalog product OR vendor OR category match; `purchase_history.csv` renewals not yet reasoned over.
- `unknown`/missing `data_access_level` = unsafe → Security review; `none` = explicitly no access.
- Request text / vendor notes are untrusted data (Sec 9); instruction-like text is ignored + flagged `prompt_injection_detected`.
- Missing cost → cannot determine Sec 4 thresholds; route for clarification with fallback approvals.

## 6. Evaluation results (public 6, same set both archs)

```bash
python evals/run_public_evals.py --architecture single   # 6/6 → evals/results_single.csv
python evals/run_public_evals.py --architecture staged   # 6/6 → evals/results_staged.csv
```

| Metric | Single | Staged |
|---|---:|---:|
| Cases passing minimum checks | 6/6 | 6/6 |
| Avg latency | ~6.5 ms | ~11.3 ms |
| Avg LLM calls | 0 | 0 |
| Avg tool calls | 5 | 7 |
| Notable policy/grounding failures | 0 | 0 |

Coverage: PUB-01 low-value threshold, PUB-02 overlap + new vendor, PUB-03 source-code Security, PUB-04 budget + Privacy/Legal, PUB-05 missing + injection, PUB-06 API-unavailable degradation.

## 7. Architecture comparison + ship decision

Staged adds +2 tool calls and +~4.8 ms avg latency with **zero accuracy gain** on the public set (identical approvals/flags/evidence). Its second pass is the same deterministic rules, not an independent reviewer.

**Decision: ship `single`.** Simpler, faster, cheaper, easier to reason about, sufficient for the client problem. Add a real LLM reviewer only when free-text justification quality becomes the bottleneck - see `templates/architecture_decision.md` (≤500 words).

## 8. Known limitations

- No real LLM summarizer yet; `recommendation`/`next_step` are templated. No LLM SDK in `requirements.txt` by design.
- Overlap is catalog-only; `purchase_history.csv` seat/renewal reasoning is future work.
- Injection detection is regex-based; novel phrasings in hidden cases may need an LLM classifier.
- Latency numbers are local (mock API on localhost); production SSO/auth/audit logging not built.
- Hidden evaluation cases use different values - no request-ID hardcoding; verify with `python verify_setup.py` before submit.

## Useful files

- `src/solution.py` - `handle_request()` adapter (assessment entry point)
- `src/contracts.py` - required `ProcurementDecision` shape
- `data/procurement_policy.md` - policy source of truth (reference date 2026-09-30)
- `templates/workflow_notes.md` - tools, responsibilities, diagram
- `templates/architecture_decision.md` - ship memo
- `evals/` - `public_cases.json`, runner, `results_*.csv`
- `STUDENT_CHECKLIST.md` - pre-submission checklist (no `.env`/secrets in repo)
