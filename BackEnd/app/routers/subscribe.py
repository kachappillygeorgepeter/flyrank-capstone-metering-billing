# Stripe Checkout Session — Free to Pro upgrade flow

import stripe
from fastapi import APIRouter, Depends, HTTPException
from app.core.config import STRIPE_SECRET_KEY
from app.core.database import get_db
from app.models.queries import get_tenant_by_id
from app.services.auth import get_current_tenant_flexible

stripe.api_key = STRIPE_SECRET_KEY
router = APIRouter()


@router.post("/subscribe/checkout")
def create_checkout_session(
    current_tenant=Depends(get_current_tenant_flexible),
    conn=Depends(get_db)
):
    tenant_id = current_tenant["id"]

    # Get full tenant info for email
    tenant = get_tenant_by_id(conn, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant_email = tenant[2]

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=tenant_email,
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": 9900,
                    "recurring": {"interval": "month"},
                    "product_data": {
                        "name": "Pro Plan",
                        "description": "10,000,000 tokens/month"
                    }
                },
                "quantity": 1
            }],
            metadata={"tenant_id": str(tenant_id)},
            success_url="http://localhost:8000/success",
            cancel_url="http://localhost:8000/cancel"
        )

        return {
            "checkout_url": session.url,
            "session_id":   session.id,
            "auth_method":  current_tenant["auth_method"]
        }

    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))