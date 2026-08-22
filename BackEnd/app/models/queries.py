
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