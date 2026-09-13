# Auth Router — Register, Login, Me
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from app.core.database import get_db
from app.models.queries import (
    get_tenant_by_email,
    create_tenant,
    get_tenant_by_id
)
from app.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_tenant
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Request Schemas
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# POST /auth/register
@router.post("/register", status_code=201)
def register(body: RegisterRequest, conn=Depends(get_db)):
    # Check if email already exists
    existing = get_tenant_by_email(conn, body.email)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    password_hash = hash_password(body.password)
    api_key = f"ak_{uuid.uuid4().hex}"
    tenant = create_tenant(
        conn,
        name=body.name,
        email=body.email,
        api_key=api_key,
        password_hash=password_hash
    )
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO subscriptions (tenant_id, plan_id) VALUES (%s, 1)",
            (tenant[0],)
        )
        conn.commit()
    return {
        "message": "Account created successfully",
        "tenant": {
            "id":      tenant[0],
            "name":    tenant[1],
            "email":   tenant[2],
            "api_key": tenant[3],
            "role":    tenant[4]
        }
    }


# POST /auth/login
@router.post("/login")
def login(body: LoginRequest, conn=Depends(get_db)):
    tenant = get_tenant_by_email(conn, body.email)
    if not tenant:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    tenant_id, name, email, api_key, password_hash, role = tenant
    if not password_hash:
        raise HTTPException(
            status_code=401,
            detail="Account has no password set — use API key auth"
        )
    if not verify_password(body.password, password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = create_access_token({
        "sub":   str(tenant_id),
        "email": email,
        "role":  role
    })

    return {
        "access_token": token,
        "token_type":   "bearer",
        "tenant": {
            "id":    tenant_id,
            "name":  name,
            "email": email,
            "role":  role
        }
    }


# GET /auth/me
@router.get("/me")
def me(
    current_tenant=Depends(get_current_tenant),
    conn=Depends(get_db)
):
    tenant = get_tenant_by_id(conn, current_tenant["id"])
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return {
        "id":      tenant[0],
        "name":    tenant[1],
        "email":   tenant[2],
        "api_key": tenant[3],
        "role":    tenant[4]
    }