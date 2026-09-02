# GET /usage — Returns tenant usage summary
from fastapi import APIRouter, Depends, Header, HTTPException
from app.core.database import get_db
from app.core.pricing import calculate_cost
from app.models.queries import (
    get_tenant_by_api_key,
    get_tenant_plan,
    get_tenant_usage_breakdown
)

router = APIRouter()

# API Key Dependency
def get_tenant(
    x_api_key: str = Header(..., description="Your tenant API key"),
    conn=Depends(get_db)):
    tenant = get_tenant_by_api_key(conn, x_api_key)
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return tenant, conn


@router.get("/usage")
def get_usage(tenant_conn=Depends(get_tenant)):
    tenant, conn = tenant_conn
    tenant_id = tenant[0]
    tenant_name = tenant[1]
    # Get tenant plan
    plan = get_tenant_plan(conn, tenant_id)
    if not plan:
        raise HTTPException(
            status_code=402,
            detail="No active plan found"
        )

    plan_name = plan[0]
    token_limit = plan[1]

    # Get token breakdown
    breakdown = get_tenant_usage_breakdown(conn, tenant_id)
    input_tokens    = breakdown[0]
    cached_tokens   = breakdown[1]
    output_tokens   = breakdown[2]
    reasoning_tokens = breakdown[3]

    # Calculate totals
    total_used = input_tokens + cached_tokens + output_tokens + reasoning_tokens
    remaining = max(0, token_limit - total_used)

    # Calculate cost
    cost_usd = calculate_cost(
        input_tokens,
        cached_tokens,
        output_tokens,
        reasoning_tokens
    )

    return {
        "tenant": tenant_name,
        "plan": plan_name,
        "usage": {
            "used_tokens": total_used,
            "limit": token_limit,
            "remaining": remaining,
            "percentage_used": round((total_used / token_limit) * 100, 2)
        },
        "breakdown": {
            "input_tokens": input_tokens,
            "cached_tokens": cached_tokens,
            "output_tokens": output_tokens,
            "reasoning_tokens": reasoning_tokens
        },
        "cost_usd": cost_usd
    }