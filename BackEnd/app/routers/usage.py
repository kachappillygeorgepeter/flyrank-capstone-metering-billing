# GET /usage — Returns tenant usage summary and cost rollup

from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.core.pricing import calculate_cost
from app.models.queries import (
    get_tenant_plan,
    get_tenant_usage_breakdown
)
from app.services.auth import get_current_tenant_flexible
from fastapi import HTTPException

router = APIRouter()


@router.get("/usage")
def get_usage(
    current_tenant=Depends(get_current_tenant_flexible),
    conn=Depends(get_db)
):
    tenant_id   = current_tenant["id"]
    tenant_name = current_tenant.get("email", "Unknown")

    # Get plan info
    plan = get_tenant_plan(conn, tenant_id)
    if not plan:
        raise HTTPException(
            status_code=402,
            detail="No active plan found"
        )

    plan_name   = plan[0]
    token_limit = plan[1]

    # Get token breakdown
    breakdown        = get_tenant_usage_breakdown(conn, tenant_id)
    input_tokens     = breakdown[0]
    cached_tokens    = breakdown[1]
    output_tokens    = breakdown[2]
    reasoning_tokens = breakdown[3]

    # Calculate totals
    total_used = input_tokens + cached_tokens + output_tokens + reasoning_tokens
    remaining  = max(0, token_limit - total_used)

    # Calculate cost
    cost_usd = calculate_cost(
        input_tokens,
        cached_tokens,
        output_tokens,
        reasoning_tokens
    )

    return {
        "tenant":    tenant_name,
        "plan":      plan_name,
        "auth_method": current_tenant["auth_method"],
        "usage": {
            "used_tokens":      total_used,
            "limit":            token_limit,
            "remaining":        remaining,
            "percentage_used":  round((total_used / token_limit) * 100, 2)
        },
        "breakdown": {
            "input_tokens":     input_tokens,
            "cached_tokens":    cached_tokens,
            "output_tokens":    output_tokens,
            "reasoning_tokens": reasoning_tokens
        },
        "cost_usd": cost_usd
    }