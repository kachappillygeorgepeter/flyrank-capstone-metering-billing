# Dummy billable endpoint for testing purposes

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.database import get_db
from app.models.queries import get_tenant_plan
from app.services.auth import get_current_tenant_flexible
from app.services.meter import MeterService

router = APIRouter()


# Request Body Schema
class GenerateRequest(BaseModel):
    idempotency_key: str
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    prompt: str = "Hello"


# Route
@router.post("/generate")
def generate(
    body: GenerateRequest,
    current_tenant=Depends(get_current_tenant_flexible),
    conn=Depends(get_db)
):
    tenant_id   = current_tenant["id"]
    tenant_name = current_tenant.get("email", "Unknown")

    # MeterService handles: Quota Check → Idempotency → Record Usage
    meter  = MeterService(conn)
    result = meter.record(
        tenant_id=tenant_id,
        idempotency_key=body.idempotency_key,
        input_tokens=body.input_tokens,
        cached_tokens=body.cached_tokens,
        output_tokens=body.output_tokens,
        reasoning_tokens=body.reasoning_tokens
    )

    return {
        "tenant":   tenant_name,
        "prompt":   body.prompt,
        "response": f"Generated response for: {body.prompt}",
        "tokens": {
            "input":     body.input_tokens,
            "cached":    body.cached_tokens,
            "output":    body.output_tokens,
            "reasoning": body.reasoning_tokens
        },
        "auth_method": current_tenant["auth_method"],
        "metering":    result
    }