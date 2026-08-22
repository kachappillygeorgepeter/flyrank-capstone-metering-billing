from fastapi import FastAPI
from app.core.database import get_connection
from app.routers import generate

app = FastAPI(
    title="LLM Metering & Billing Engine",
    version="1.0.0"
)

app.include_router(generate.router)

# Health check
@app.get("/health")
def health_check():
    try:
        conn = get_connection()
        conn.close()
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}