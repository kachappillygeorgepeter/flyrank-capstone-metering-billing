# Billing Logic
# Client → POST /generate → Validate API Key → Check Idempotency → Record Usage → Return Response

from app.models.queries import (
    check_idempotency_key,
    record_usage_event
)

class MeterService:

    # constructor
    def __init__(self, conn):  
        self.conn = conn

    # Check Idempotency -> Record Usage
    def record(self, tenant_id: int, idempotency_key: str,
               input_tokens: int, cached_tokens: int,
               output_tokens: int, reasoning_tokens: int) -> dict:
            
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
            "message": "Usage recorded successfully"
        }