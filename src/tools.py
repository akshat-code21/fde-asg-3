"""Agent tools. Each wraps a data source + records telemetry."""
from __future__ import annotations
from src.data_access import load_budgets, load_employees, load_software_catalog, load_vendors
from src.vendor_client import get_vendor_risk


def catalog_overlap_tool(product, vendor, category, counter) -> dict:
    """Deterministic: check load_software_catalog() for same product/vendor/category."""
    counter.record_tool_call("catalog_overlap_tool")

    software_catalog_df = load_software_catalog()

    catalog_overlap = software_catalog_df.loc[
        (software_catalog_df["product_name"] == product) |
        (software_catalog_df["vendor_name"] == vendor) |
        (software_catalog_df["category"] == category)
    ]

    if catalog_overlap.empty:
        return {"overlap": False}
    else:
        return {"overlap": True, "existing_products": catalog_overlap.to_dict(orient="records")}


def vendor_risk_tool(vendor_name: str, counter) -> dict:
    """External: load_vendors() + get_vendor_risk(vendor_name). Handle 404/503."""
    counter.record_tool_call("vendor_tool")

    vendors_df = load_vendors()

    vendor_row = vendors_df.loc[vendors_df["vendor_name"] == vendor_name]
    internal = None
    if not vendor_row.empty:
        internal = vendor_row.iloc[0].to_dict()

    try:
        external = get_vendor_risk(vendor_name)
    except Exception as e:
        return {"internal": internal, "external": None, "unavailable": True, "error": str(e)}

    return {"internal": internal, "external": external, "unavailable": False, "error": None}


def budget_tool(dept: str, annual_cost: float | None, counter) -> dict:
    """Deterministic: compare cost vs available_usd from load_budgets()."""
    counter.record_tool_call("budget_tool")
    budgets_df = load_budgets()

    rows = budgets_df.loc[budgets_df["department"] == dept]
    if rows.empty:
        return {
            "department": dept,
            "annual_cost": annual_cost,
            "budget_available": None,
            "can_afford": None,
            "unknown_budget": True,
        }
    budget_available = rows["available_usd"].iloc[0]
    try:
        budget_available_f = float(budget_available)
    except (TypeError, ValueError):
        budget_available_f = None

    if annual_cost is None:
        return {
            "department": dept,
            "annual_cost": None,
            "budget_available": budget_available_f,
            "can_afford": None,
            "missing_cost": True,
        }
    try:
        cost_f = float(annual_cost)
    except (TypeError, ValueError):
        return {
            "department": dept,
            "annual_cost": annual_cost,
            "budget_available": budget_available_f,
            "can_afford": None,
            "missing_cost": True,
        }
    if budget_available_f is None:
        return {
            "department": dept,
            "annual_cost": cost_f,
            "budget_available": None,
            "can_afford": None,
            "unknown_budget": True,
        }
    return {
        "department": dept,
        "annual_cost": cost_f,
        "budget_available": budget_available_f,
        "can_afford": budget_available_f >= cost_f,
    }



def employees_tool(employee_id,counter) ->dict:
    """Deterministic: load_employees() and return details for employee id."""
    counter.record_tool_call("employees_tool")
    employees_df = load_employees()
    employee_in_id = employees_df[employees_df["employee_id"] == employee_id]
    return employee_in_id.to_dict(orient="records")
