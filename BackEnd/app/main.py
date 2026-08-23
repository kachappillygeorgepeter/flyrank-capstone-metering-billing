from fastapi import FastAPI
from app.core.database import get_connection
from app.routers import generate, subscribe, webhooks

app = FastAPI(
    title="LLM Metering & Billing Engine",
    version="1.0.0"
)

# Register routers
app.include_router(generate.router)
app.include_router(subscribe.router)
app.include_router(webhooks.router)


@app.get("/health")
def health_check():
    """Quick check that the server and DB are alive."""
    try:
        conn = get_connection()
        conn.close()
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}


@app.get("/success")
def success():
    return {"message": "Payment successful! You are now on Pro plan."}


@app.get("/cancel")
def cancel():
    return {"message": "Payment cancelled. You are still on Free plan."}