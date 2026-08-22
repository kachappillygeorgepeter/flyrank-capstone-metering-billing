from fastapi import FastAPI
from app.core.database import get_connection

app = FastAPI(
    title="LLM Metering & Billing Engine",
    version="1.0.0"
)

# Health check
@app.get("/health")
def health_check():
    try:
        conn = get_connection()
        conn.close()
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}