# Stripe Webhook Handler
# Receives and processes events from Stripe

import stripe
from fastapi import APIRouter, Request, HTTPException
from app.core.config import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
from app.core.database import get_connection
from app.models.queries import (
    update_tenant_subscription,
    get_tenant_by_metadata
)

stripe.api_key = STRIPE_SECRET_KEY
router = APIRouter()


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):

    # Read raw body  for signature verification
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # Verify signature to reject fake webhooks
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Get DB connection
    conn = get_connection()

    try:
        event_type = event["type"]
        data = event["data"]["object"]

        # Handle checkout.session.completed
        if event_type == "checkout.session.completed":
            tenant_id = int(data["metadata"].get("tenant_id", 0))
            stripe_subscription_id = data.get("subscription")

            if tenant_id and stripe_subscription_id:
                tenant = get_tenant_by_metadata(conn, tenant_id)
                if tenant:
                    update_tenant_subscription(
                        conn,
                        tenant_id=tenant_id,
                        plan_name="pro",
                        stripe_subscription_id=stripe_subscription_id,
                        status="active"
                    )

        # Handle customer.subscription.updated
        elif event_type == "customer.subscription.updated":
            stripe_subscription_id = data["id"]
            status = data["status"]  # active, past_due, cancelled etc.

            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE subscriptions
                    SET status = %s, updated_at = NOW()
                    WHERE stripe_subscription_id = %s
                    """,
                    (status, stripe_subscription_id)
                )
                conn.commit()

        # Handle customer.subscription.deleted
        elif event_type == "customer.subscription.deleted":
            stripe_subscription_id = data["id"]

            with conn.cursor() as cur:
                # Get plan id for free
                cur.execute("SELECT id FROM plans WHERE name = 'free'")
                free_plan = cur.fetchone()
                if free_plan:
                    cur.execute(
                        """
                        UPDATE subscriptions
                        SET plan_id = %s,
                            stripe_subscription_id = NULL,
                            status = 'cancelled',
                            updated_at = NOW()
                        WHERE stripe_subscription_id = %s
                        """,
                        (free_plan[0], stripe_subscription_id)
                    )
                    conn.commit()

    finally:
        conn.close()

    return {"status": "ok", "event": event_type}