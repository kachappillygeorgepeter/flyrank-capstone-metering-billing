import psycopg2
from app.core.config import DATABASE_URL

# Returns a new PostgreSQL connection, closes after the request. Done for each request
# We do it for safety and simplicity
def get_connection():
    return psycopg2.connect(DATABASE_URL)

# FastAPI dependency that yields a DB connection and ensures it closes after the request
def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()