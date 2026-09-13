
# Db queries in one place

# Get tenant by API key
def get_tenant_by_api_key(conn, api_key: str):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, email FROM tenants WHERE api_key = %s",
            (api_key,)
        )
        return cur.fetchone()

# Get tenant plan
def get_tenant_plan(conn, tenant_id: int):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.name, p.token_limit
            FROM subscriptions s
            JOIN plans p ON s.plan_id = p.id
            WHERE s.tenant_id = %s AND s.status = 'active'
            ORDER BY s.started_at DESC
            LIMIT 1
            """,
            (tenant_id,)
        )
        return cur.fetchone()

# Get tenant usage
def get_tenant_usage(conn, tenant_id: int):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(SUM(
                input_tokens + cached_tokens + output_tokens + reasoning_tokens
            ), 0)
            FROM usage_events
            WHERE tenant_id = %s
            AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', NOW())
            """,
            (tenant_id,)
        )
        return cur.fetchone()[0]

# Check idempotency key
def check_idempotency_key(conn, key: str):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM usage_events WHERE idempotency_key = %s",
            (key,)
        )
        return cur.fetchone()

# Record usage event
def record_usage_event(conn, tenant_id: int, idempotency_key: str,
                        input_tokens: int, cached_tokens: int,
                        output_tokens: int, reasoning_tokens: int):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO usage_events 
            (tenant_id, idempotency_key, input_tokens, cached_tokens, 
             output_tokens, reasoning_tokens)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (tenant_id, idempotency_key, input_tokens, cached_tokens,
             output_tokens, reasoning_tokens)
        )
        conn.commit()

# Get tenant by stripe customer id
def get_tenant_by_stripe_customer_id(conn, stripe_customer_id: str):
    """Find a tenant by their Stripe customer ID."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT t.id, t.name, t.email
            FROM tenants t
            JOIN subscriptions s ON t.id = s.tenant_id
            WHERE s.stripe_subscription_id = %s
            """,
            (stripe_customer_id,)
        )
        return cur.fetchone()

# Update tenant subscription
def update_tenant_subscription(conn, tenant_id: int, plan_name: str, 
                                stripe_subscription_id: str, status: str):
    with conn.cursor() as cur:
        # Get plan id
        cur.execute("SELECT id FROM plans WHERE name = %s", (plan_name,))
        plan = cur.fetchone()
        if not plan:
            return
        plan_id = plan[0]

        # Update subscription
        cur.execute(
            """
            UPDATE subscriptions
            SET plan_id = %s,
                stripe_subscription_id = %s,
                status = %s,
                updated_at = NOW()
            WHERE tenant_id = %s
            """,
            (plan_id, stripe_subscription_id, status, tenant_id)
        )
        conn.commit()


# Get tenant by metadata
def get_tenant_by_metadata(conn, tenant_id: int):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, email FROM tenants WHERE id = %s",
            (tenant_id,)
        )
        return cur.fetchone()

# Check if a Stripe event has already been processed
def is_webhook_event_processed(conn, stripe_event_id: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM processed_webhook_events WHERE stripe_event_id = %s",
            (stripe_event_id,)
        )
        return cur.fetchone() is not None

# Mark a Stripe event as processed to prevent duplicate handling.
def mark_webhook_event_processed(conn, stripe_event_id: str, event_type: str):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO processed_webhook_events (stripe_event_id, event_type)
            VALUES (%s, %s)
            ON CONFLICT (stripe_event_id) DO NOTHING
            """,
            (stripe_event_id, event_type)
        )
        conn.commit()

# Get tenant usage breakdown of this month in the format:
# (input_tokens, cached_tokens, output_tokens, reasoning_tokens)
def get_tenant_usage_breakdown(conn, tenant_id: int):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 
                COALESCE(SUM(input_tokens), 0),
                COALESCE(SUM(cached_tokens), 0),
                COALESCE(SUM(output_tokens), 0),
                COALESCE(SUM(reasoning_tokens), 0)
            FROM usage_events
            WHERE tenant_id = %s
            AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', NOW())
            """,
            (tenant_id,)
        )
        return cur.fetchone()
def get_tenant_by_email(conn, email: str):
    """Find a tenant by email address."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, email, api_key, password_hash, role
            FROM tenants
            WHERE email = %s
            """,
            (email,)
        )
        return cur.fetchone()


def create_tenant(conn, name: str, email: str,
                  api_key: str, password_hash: str, role: str = "tenant"):
    """Create a new tenant with hashed password."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO tenants (name, email, api_key, password_hash, role)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, name, email, api_key, role
            """,
            (name, email, api_key, password_hash, role)
        )
        conn.commit()
        return cur.fetchone()


def get_tenant_by_id(conn, tenant_id: int):
    """Get tenant by ID."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, email, api_key, role
            FROM tenants
            WHERE id = %s
            """,
            (tenant_id,)
        )
        return cur.fetchone()
def get_all_tenants(conn):
    """Get all tenants — admin only."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT t.id, t.name, t.email, t.role,
                   p.name as plan, s.status,
                   t.created_at
            FROM tenants t
            JOIN subscriptions s ON t.id = s.tenant_id
            JOIN plans p ON s.plan_id = p.id
            ORDER BY t.created_at DESC
            """
        )
        return cur.fetchall()


def get_all_usage(conn):
    """Get usage summary for all tenants — admin only."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                t.id,
                t.name,
                t.email,
                p.name as plan,
                p.token_limit,
                COALESCE(SUM(
                    u.input_tokens + u.cached_tokens +
                    u.output_tokens + u.reasoning_tokens
                ), 0) as total_tokens,
                COALESCE(SUM(u.input_tokens), 0) as input_tokens,
                COALESCE(SUM(u.cached_tokens), 0) as cached_tokens,
                COALESCE(SUM(u.output_tokens), 0) as output_tokens,
                COALESCE(SUM(u.reasoning_tokens), 0) as reasoning_tokens
            FROM tenants t
            JOIN subscriptions s ON t.id = s.tenant_id
            JOIN plans p ON s.plan_id = p.id
            LEFT JOIN usage_events u ON t.id = u.tenant_id
            AND DATE_TRUNC('month', u.created_at) = DATE_TRUNC('month', NOW())
            GROUP BY t.id, t.name, t.email, p.name, p.token_limit
            ORDER BY total_tokens DESC
            """
        )
        return cur.fetchall()