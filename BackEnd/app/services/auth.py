# Auth Service — JWT + Password Hashing

from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Header, Depends
from app.core.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRY_HOURS
from app.core.database import get_db
from app.models.queries import get_tenant_by_email

# Password hashing context — uses bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Password Helpers
def hash_password(password: str) -> str:
    return pwd_context.hash(password)
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# JWT Helpers
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )


# FastAPI Dependency
def get_current_tenant(
    authorization: str = Header(..., description="Bearer <token>"),
    conn=Depends(get_db)
):
    # Check header format
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Use: Bearer <token>"
        )
    # Extract token
    token = authorization.split(" ")[1]
    # Decode and verify
    payload = decode_access_token(token)
    # Extract tenant info
    tenant_id = payload.get("sub")
    email     = payload.get("email")
    role      = payload.get("role")

    if not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return {
        "id":    int(tenant_id),
        "email": email,
        "role":  role
    }
def require_admin(current_tenant=Depends(get_current_tenant)):
    if current_tenant["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return current_tenant