# Billing Logic
# Client → POST /generate → Validate API Key → Check Quota → Check Idempotency → Record Usage → Return Response

from fastapi import HTTPException
from app.models.queries import (
    check_idempotency_key,
    record_usage_event,
    get_tenant_plan,
    get_tenant_usage
)

class MeterService:

    # constructor
    def __init__(self, conn):  
        self.conn = conn

    # Check Quota
    def check_quota(self, tenant_id: int):

        # Get tenant's current plan
        plan = get_tenant_plan(self.conn, tenant_id)

        # No plan found — payment required
        if not plan:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "No active plan found",
                    "message": "Please subscribe to a plan to continue",
                    "code": "NO_PLAN"
                }
            )

        plan_name = plan[0]
        token_limit = plan[1]

        # Get current month usage
        used_tokens = get_tenant_usage(self.conn, tenant_id)

        # Over limit — block request
        if used_tokens >= token_limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Quota exceeded",
                    "message": f"You have used {used_tokens:,} of {token_limit:,} tokens on the {plan_name} plan",
                    "used": used_tokens,
                    "limit": token_limit,
                    "code": "QUOTA_EXCEEDED",
                    "upgrade_hint": "Upgrade to Pro for 10,000,000 tokens/month"
                }
            )

        return {
            "plan_name": plan_name,
            "token_limit": token_limit,
            "used_tokens": used_tokens,
            "remaining": token_limit - used_tokens
        }

    # Check Quota → Check Idempotency → Record Usage
    def record(self, tenant_id: int, idempotency_key: str,
               input_tokens: int, cached_tokens: int,
               output_tokens: int, reasoning_tokens: int) -> dict:

        # Check quota FIRST before anything else
        quota = self.check_quota(tenant_id)

        # Check if this request was already processed
        existing = check_idempotency_key(self.conn, idempotency_key)

        if existing:
            # Already processed — return without recording again
            return {
                "duplicate": True,
                "message": "Duplicate request — no usage recorded"
            }

        # New request — record the usage event
        record_usage_event(
            self.conn,
            tenant_id,
            idempotency_key,
            input_tokens,
            cached_tokens,
            output_tokens,
            reasoning_tokens
        )

        return {
            "duplicate": False,
            "message": "Usage recorded successfully",
            "quota": quota
        }