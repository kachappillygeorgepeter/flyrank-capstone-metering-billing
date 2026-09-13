# ============================================
# Admin Router — System wide data
# Admin only — requires role: admin in JWT
# ============================================

from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.core.pricing import calculate_cost
from app.models.queries import get_all_tenants, get_all_usage
from app.services.auth import require_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


# ============================================
# GET /admin/tenants — All tenants list
# ============================================

@router.get("/tenants")
def list_all_tenants(
    current_tenant=Depends(require_admin),
    conn=Depends(get_db)
):
    """
    Returns all tenants with their plan and status.
    Admin only.
    """
    tenants = get_all_tenants(conn)

    return {
        "admin":        current_tenant["email"],
        "total_tenants": len(tenants),
        "tenants": [
            {
                "id":         t[0],
                "name":       t[1],
                "email":      t[2],
                "role":       t[3],
                "plan":       t[4],
                "status":     t[5],
                "created_at": str(t[6])
            }
            for t in tenants
        ]
    }


# ============================================
# GET /admin/usage — All tenants usage
# ============================================

@router.get("/usage")
def list_all_usage(
    current_tenant=Depends(require_admin),
    conn=Depends(get_db)
):
    """
    Returns usage summary and cost for ALL tenants this month.
    Admin only.
    """
    usage_rows = get_all_usage(conn)

    tenants_usage = []
    total_system_cost = 0.0

    for row in usage_rows:
        tenant_id       = row[0]
        name            = row[1]
        email           = row[2]
        plan            = row[3]
        token_limit     = row[4]
        total_tokens    = row[5]
        input_tokens    = row[6]
        cached_tokens   = row[7]
        output_tokens   = row[8]
        reasoning_tokens = row[9]

        cost = calculate_cost(
            input_tokens,
            cached_tokens,
            output_tokens,
            reasoning_tokens
        )

        total_system_cost += cost

        tenants_usage.append({
            "id":           tenant_id,
            "name":         name,
            "email":        email,
            "plan":         plan,
            "usage": {
                "used_tokens":     total_tokens,
                "limit":           token_limit,
                "remaining":       max(0, token_limit - total_tokens),
                "percentage_used": round((total_tokens / token_limit) * 100, 2)
                                   if token_limit > 0 else 0
            },
            "breakdown": {
                "input_tokens":     input_tokens,
                "cached_tokens":    cached_tokens,
                "output_tokens":    output_tokens,
                "reasoning_tokens": reasoning_tokens
            },
            "cost_usd": cost
        })

    return {
        "admin":             current_tenant["email"],
        "month":             "current",
        "total_tenants":     len(tenants_usage),
        "total_system_cost": round(total_system_cost, 6),
        "tenants":           tenants_usage
    }


# ============================================
# GET /admin/stats — System wide stats
# ============================================

@router.get("/stats")
def system_stats(
    current_tenant=Depends(require_admin),
    conn=Depends(get_db)
):
    """
    Returns high level system stats.
    Admin only.
    """
    with conn.cursor() as cur:
        # Total tenants
        cur.execute("SELECT COUNT(*) FROM tenants")
        total_tenants = cur.fetchone()[0]

        # Tenants by plan
        cur.execute(
            """
            SELECT p.name, COUNT(*) as count
            FROM subscriptions s
            JOIN plans p ON s.plan_id = p.id
            WHERE s.status = 'active'
            GROUP BY p.name
            """
        )
        plans = {row[0]: row[1] for row in cur.fetchall()}

        # Total usage events
        cur.execute("SELECT COUNT(*) FROM usage_events")
        total_events = cur.fetchone()[0]

        # Total tokens this month
        cur.execute(
            """
            SELECT COALESCE(SUM(
                input_tokens + cached_tokens +
                output_tokens + reasoning_tokens
            ), 0)
            FROM usage_events
            WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', NOW())
            """
        )
        total_tokens_this_month = cur.fetchone()[0]

        # Total processed webhooks
        cur.execute("SELECT COUNT(*) FROM processed_webhook_events")
        total_webhooks = cur.fetchone()[0]

    return {
        "admin": current_tenant["email"],
        "stats": {
            "total_tenants":          total_tenants,
            "tenants_by_plan":        plans,
            "total_usage_events":     total_events,
            "total_tokens_this_month": total_tokens_this_month,
            "total_webhooks_processed": total_webhooks
        }
    }