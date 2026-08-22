# Dummy billable endpoint for testing purposes

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.core.database import get_db
from app.models.queries import get_tenant_by_api_key
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


# API Key Dependency
def get_tenant(
    x_api_key: str = Header(..., description="Your tenant API key"),
    conn=Depends(get_db)):
    tenant = get_tenant_by_api_key(conn, x_api_key)
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return tenant, conn


# Route
@router.post("/generate")
def generate(
    body: GenerateRequest,
    tenant_conn=Depends(get_tenant)
):
    tenant, conn = tenant_conn

    tenant_id = tenant[0]
    tenant_name = tenant[1]

    # Record usage via MeterService
    meter = MeterService(conn)
    result = meter.record(
        tenant_id=tenant_id,
        idempotency_key=body.idempotency_key,
        input_tokens=body.input_tokens,
        cached_tokens=body.cached_tokens,
        output_tokens=body.output_tokens,
        reasoning_tokens=body.reasoning_tokens
    )

    return {
        "tenant": tenant_name,
        "prompt": body.prompt,
        "response": f"Generated response for: {body.prompt}",
        "tokens": {
            "input": body.input_tokens,
            "cached": body.cached_tokens,
            "output": body.output_tokens,
            "reasoning": body.reasoning_tokens
        },
        "metering": result
    }