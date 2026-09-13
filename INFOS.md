# LLM Metering & Billing Engine — Complete Project Reference

## Table of Contents

1. Project Overview
2. Tech Stack
3. Architecture
4. Database Schema
5. API Endpoints
6. Pricing Model
7. Plans & Quotas
8. Metering Flow
9. Idempotency Strategy
10. Stripe Integration
11. Webhook System
12. Error Codes
13. Environment Variables
14. File Structure
15. Key Design Decisions
16. Authentication System
17. Role Based Access Control

---

## 1. Project Overview

A production-grade **Usage Metering & Billing Engine** for LLM APIs.

Built as a capstone project to demonstrate:

- Real-time token usage tracking
- Quota enforcement per billing plan
- Idempotent billing (no double charging on retries)
- Stripe payment integration
- Webhook signature verification and deduplication
- Cost calculation by token type
- JWT authentication with bcrypt password hashing
- Role based access control (admin vs tenant)

The engine sits between an LLM API and its customers. Every time a tenant makes a billable request, the engine records usage, checks quotas, and calculates cost — all in real time.

---

## 2. Tech Stack

| Layer            | Technology       | Version | Why                                   |
| ---------------- | ---------------- | ------- | ------------------------------------- |
| Language         | Python           | 3.13    | Modern, async-friendly                |
| Web Framework    | FastAPI          | 0.111.0 | Fast, auto-docs, modern Python        |
| Server           | Uvicorn          | 0.29.0  | ASGI server for FastAPI               |
| Database         | PostgreSQL       | 16      | Reliable, ACID compliant              |
| DB Driver        | psycopg2-binary  | 2.9.12  | Standard PostgreSQL driver for Python |
| Payments         | Stripe           | 15.5.1  | Industry standard payment platform    |
| Validation       | Pydantic         | 2.13.4  | Request/response validation           |
| Env Management   | python-dotenv    | 1.2.2   | Secure secret management              |
| JWT              | python-jose      | latest  | JWT creation and verification         |
| Password Hashing | passlib + bcrypt | latest  | Secure password storage               |
| Testing          | Pytest           | 9.1.1   | Industry standard test framework      |
| HTTP Testing     | HTTPX            | 0.28.1  | FastAPI test client dependency        |

---

## 3. Architecture

Client
│
▼
FastAPI (uvicorn)
│
├── POST /auth/register ──► Create tenant + hash password
├── POST /auth/login ─────► Verify password → issue JWT
├── GET /auth/me ────────► Decode JWT → return tenant info
│
├── POST /generate ───────► Flexible Auth → MeterService
│ │
│ ├── Validate Auth (JWT or API Key)
│ ├── Check Quota
│ ├── Check Idempotency
│ └── Record Usage Event
│
├── GET /usage ───────────► Flexible Auth → Pricing Engine
│ │
│ └── Calculate Cost
│
├── POST /subscribe/checkout ──► Flexible Auth → Stripe API
│ │
│ └── Return Checkout URL
│
├── POST /webhooks/stripe ──► Webhook Handler
│ │
│ ├── Verify Stripe Signature
│ ├── Check Deduplication
│ └── Update Tenant Plan
│
├── GET /admin/tenants ───► require_admin → All Tenants
├── GET /admin/usage ─────► require_admin → All Usage + Cost
└── GET /admin/stats ─────► require_admin → System Stats

PostgreSQL
├── tenants (id, name, email, api_key, password_hash, role)
├── plans (id, name, token_limit, price_usd)
├── subscriptions (id, tenant_id, plan_id, stripe_subscription_id, status)
├── usage_events (id, tenant_id, idempotency_key, input/cached/output/reasoning tokens)
└── processed_webhook_events (id, stripe_event_id, event_type)

---

## 4. Database Schema

### Table: `tenants`

Stores every customer using the API.

| Column        | Type         | Constraints      | Description                 |
| ------------- | ------------ | ---------------- | --------------------------- |
| id            | SERIAL       | PRIMARY KEY      | Auto-incrementing ID        |
| name          | VARCHAR(255) | NOT NULL         | Company/customer name       |
| email         | VARCHAR(255) | NOT NULL, UNIQUE | Contact email               |
| api_key       | VARCHAR(255) | NOT NULL, UNIQUE | Machine-to-machine auth key |
| password_hash | VARCHAR(255) | NULLABLE         | bcrypt hashed password      |
| role          | VARCHAR(50)  | DEFAULT 'tenant' | tenant or admin             |
| created_at    | TIMESTAMP    | DEFAULT NOW()    | Account creation time       |

### Table: `plans`

Stores available billing plans.

| Column      | Type          | Constraints      | Description           |
| ----------- | ------------- | ---------------- | --------------------- |
| id          | SERIAL        | PRIMARY KEY      | Auto-incrementing ID  |
| name        | VARCHAR(50)   | NOT NULL, UNIQUE | Plan name (free, pro) |
| token_limit | INTEGER       | NOT NULL         | Monthly token quota   |
| price_usd   | NUMERIC(10,2) | NOT NULL         | Monthly price in USD  |
| created_at  | TIMESTAMP     | DEFAULT NOW()    | Plan creation time    |

**Seeded Plans:**
| id | name | token_limit | price_usd |
|---|---|---|---|
| 1 | free | 100,000 | $0.00 |
| 2 | pro | 10,000,000 | $99.00 |

### Table: `subscriptions`

Links tenants to plans.

| Column                 | Type         | Constraints      | Description            |
| ---------------------- | ------------ | ---------------- | ---------------------- |
| id                     | SERIAL       | PRIMARY KEY      | Auto-incrementing ID   |
| tenant_id              | INTEGER      | FK → tenants.id  | Which tenant           |
| plan_id                | INTEGER      | FK → plans.id    | Which plan             |
| stripe_subscription_id | VARCHAR(255) | NULLABLE         | Stripe subscription ID |
| status                 | VARCHAR(50)  | DEFAULT 'active' | active, cancelled      |
| started_at             | TIMESTAMP    | DEFAULT NOW()    | Subscription start     |
| updated_at             | TIMESTAMP    | DEFAULT NOW()    | Last update            |

### Table: `usage_events`

Records every billable action.

| Column           | Type         | Constraints      | Description                |
| ---------------- | ------------ | ---------------- | -------------------------- |
| id               | SERIAL       | PRIMARY KEY      | Auto-incrementing ID       |
| tenant_id        | INTEGER      | FK → tenants.id  | Which tenant               |
| idempotency_key  | VARCHAR(255) | NOT NULL, UNIQUE | Prevents duplicate billing |
| input_tokens     | INTEGER      | DEFAULT 0        | Standard input tokens      |
| cached_tokens    | INTEGER      | DEFAULT 0        | Cached input tokens        |
| output_tokens    | INTEGER      | DEFAULT 0        | Generated output tokens    |
| reasoning_tokens | INTEGER      | DEFAULT 0        | Model reasoning tokens     |
| created_at       | TIMESTAMP    | DEFAULT NOW()    | Event timestamp            |

### Table: `processed_webhook_events`

Tracks processed Stripe webhook events for deduplication.

| Column          | Type         | Constraints      | Description          |
| --------------- | ------------ | ---------------- | -------------------- |
| id              | SERIAL       | PRIMARY KEY      | Auto-incrementing ID |
| stripe_event_id | VARCHAR(255) | NOT NULL, UNIQUE | Stripe event ID      |
| event_type      | VARCHAR(255) | NOT NULL         | Event type string    |
| processed_at    | TIMESTAMP    | DEFAULT NOW()    | Processing timestamp |

---

## 5. API Endpoints

### Public Endpoints (No Auth)

#### POST /auth/register

**Purpose:** Register a new tenant account.

**Request Body:**

```json
{
  "name": "My Company",
  "email": "me@example.com",
  "password": "securepassword123"
}
```

**Success Response (201):**

```json
{
  "message": "Account created successfully",
  "tenant": {
    "id": 4,
    "name": "My Company",
    "email": "me@example.com",
    "api_key": "ak_abc123...",
    "role": "tenant"
  }
}
```

**Error Responses:**

- `400` — Email already registered

---

#### POST /auth/login

**Purpose:** Login and receive a JWT token.

**Request Body:**

```json
{
  "email": "me@example.com",
  "password": "securepassword123"
}
```

**Success Response (200):**

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "tenant": {
    "id": 4,
    "name": "My Company",
    "email": "me@example.com",
    "role": "tenant"
  }
}
```

**Error Responses:**

- `401` — Invalid email or password

---

#### GET /health

**Purpose:** Check server and database are alive.

**Response:**

```json
{ "status": "ok", "database": "connected" }
```

---

### Tenant Endpoints (API Key OR JWT)

#### GET /auth/me

**Purpose:** Get current tenant info from JWT.
**Auth:** `Authorization: Bearer <token>`

**Success Response (200):**

```json
{
  "id": 4,
  "name": "My Company",
  "email": "me@example.com",
  "api_key": "ak_abc123...",
  "role": "tenant"
}
```

---

#### POST /generate

**Purpose:** Dummy billable LLM endpoint. Records usage.
**Auth:** `x-api-key` OR `Authorization: Bearer <token>`

**Request Body:**

```json
{
  "idempotency_key": "unique-request-id",
  "input_tokens": 100,
  "cached_tokens": 0,
  "output_tokens": 50,
  "reasoning_tokens": 0,
  "prompt": "Your prompt here"
}
```

**Success Response (200):**

```json
{
  "tenant": "me@example.com",
  "prompt": "Your prompt here",
  "response": "Generated response for: Your prompt here",
  "tokens": {
    "input": 100,
    "cached": 0,
    "output": 50,
    "reasoning": 0
  },
  "auth_method": "jwt",
  "metering": {
    "duplicate": false,
    "message": "Usage recorded successfully",
    "quota": {
      "plan_name": "free",
      "token_limit": 100000,
      "used_tokens": 150,
      "remaining": 99850
    }
  }
}
```

**Error Responses:**

- `401` — Invalid auth
- `402` — No active plan
- `429` — Quota exceeded

---

#### GET /usage

**Purpose:** Returns tenant usage summary and cost breakdown.
**Auth:** `x-api-key` OR `Authorization: Bearer <token>`

**Success Response (200):**

```json
{
  "tenant": "me@example.com",
  "plan": "free",
  "auth_method": "api_key",
  "usage": {
    "used_tokens": 150,
    "limit": 100000,
    "remaining": 99850,
    "percentage_used": 0.15
  },
  "breakdown": {
    "input_tokens": 100,
    "cached_tokens": 0,
    "output_tokens": 50,
    "reasoning_tokens": 0
  },
  "cost_usd": 0.00105
}
```

---

#### POST /subscribe/checkout

**Purpose:** Creates a Stripe Checkout session for plan upgrade.
**Auth:** `x-api-key` OR `Authorization: Bearer <token>`

**Success Response (200):**

```json
{
  "checkout_url": "https://checkout.stripe.com/...",
  "session_id": "cs_test_...",
  "auth_method": "jwt"
}
```

---

#### POST /webhooks/stripe

**Purpose:** Receives and processes Stripe webhook events.
**Auth:** `stripe-signature` header (Stripe signs the payload)

**Success Response (200):**

```json
{ "status": "ok", "event": "checkout.session.completed" }
```

**Duplicate Response (200):**

```json
{
  "status": "duplicate",
  "event": "checkout.session.completed",
  "message": "Event already processed — ignored"
}
```

**Error Responses:**

- `400` — Invalid or forged webhook signature

---

### Admin Endpoints (JWT + Admin Role Only)

#### GET /admin/tenants

**Purpose:** Returns all tenants with plan and status.
**Auth:** `Authorization: Bearer <admin_token>`

**Success Response (200):**

```json
{
  "admin": "admin@example.com",
  "total_tenants": 4,
  "tenants": [
    {
      "id": 1,
      "name": "Test Company",
      "email": "test@example.com",
      "role": "tenant",
      "plan": "free",
      "status": "active",
      "created_at": "2026-08-21 21:41:56"
    }
  ]
}
```

**Error Responses:**

- `401` — No token
- `403` — Not an admin

---

#### GET /admin/usage

**Purpose:** Returns usage and cost for ALL tenants this month.
**Auth:** `Authorization: Bearer <admin_token>`

**Success Response (200):**

```json
{
  "admin": "admin@example.com",
  "month": "current",
  "total_tenants": 4,
  "total_system_cost": 0.05123,
  "tenants": [
    {
      "id": 1,
      "name": "Test Company",
      "email": "test@example.com",
      "plan": "pro",
      "usage": {
        "used_tokens": 150,
        "limit": 10000000,
        "remaining": 9999850,
        "percentage_used": 0.0
      },
      "breakdown": {
        "input_tokens": 100,
        "cached_tokens": 0,
        "output_tokens": 50,
        "reasoning_tokens": 0
      },
      "cost_usd": 0.00105
    }
  ]
}
```

---

#### GET /admin/stats

**Purpose:** Returns high level system statistics.
**Auth:** `Authorization: Bearer <admin_token>`

**Success Response (200):**

```json
{
  "admin": "admin@example.com",
  "stats": {
    "total_tenants": 4,
    "tenants_by_plan": {
      "free": 3,
      "pro": 1
    },
    "total_usage_events": 12,
    "total_tokens_this_month": 100150,
    "total_webhooks_processed": 8
  }
}
```

---

## 6. Pricing Model

All rates are **per 1,000 tokens** in USD:

| Token Type         | Rate    | Description                       |
| ------------------ | ------- | --------------------------------- |
| `input_tokens`     | $0.003  | Standard prompt input             |
| `cached_tokens`    | $0.0003 | Cached input — 10x cheaper        |
| `output_tokens`    | $0.015  | Generated output — most expensive |
| `reasoning_tokens` | $0.015  | Model reasoning — same as output  |

### Cost Formula

cost = (input_tokens / 1000 × 0.003)

- (cached_tokens / 1000 × 0.0003)
- (output_tokens / 1000 × 0.015)
- (reasoning_tokens / 1000 × 0.015)

### Example Calculation

100 input tokens → 100/1000 × 0.003 = $0.000300
50 output tokens → 50/1000 × 0.015 = $0.000750
Total = $0.001050

---

## 7. Plans & Quotas

| Plan     | Monthly Token Limit | Monthly Price | Stripe Required |
| -------- | ------------------- | ------------- | --------------- |
| **Free** | 100,000 tokens      | $0.00         | No              |
| **Pro**  | 10,000,000 tokens   | $99.00/month  | Yes             |

### Quota Rules

- Quota resets every calendar month
- Quota is checked BEFORE recording usage
- At exactly the limit → blocked (429)
- Just under the limit → allowed
- Over the limit → blocked (429)
- No active plan → 402 Payment Required

### Demo Tenant Setup

- Seeded with 99,800 tokens used out of 100,000
- Only 200 tokens remaining
- Next request over 200 tokens → triggers 429

---

## 8. Metering Flow

POST /generate arrives
│
▼
Flexible Auth — JWT or API Key
Invalid → 401 Unauthorized
│
▼
Get tenant's active plan
No plan → 402 Payment Required
│
▼
Get tenant's usage this month
│
▼
used_tokens >= token_limit?
YES → 429 Too Many Requests
│
▼
Check idempotency_key in usage_events
Key exists → return duplicate: true (no billing)
│
▼
INSERT into usage_events
│
▼
Return 200 with usage + quota info

---

## 9. Idempotency Strategy

### The Problem

Network issues cause clients to retry requests. Without idempotency:

Client sends request → network drops → client retries
→ Two usage events recorded → tenant billed twice ❌

### Our Solution

Every request includes a unique `idempotency_key`. The `usage_events`
table has a `UNIQUE` constraint on this column.

First request (key: "req-001")
→ Key not in DB → record usage ✅

Retry (key: "req-001")
→ Key already in DB → skip recording ✅
→ Return same response
→ No double billing ✅

### Key Rules

- Client generates unique key per request
- Keys must be unique per tenant
- Same key = same result, no side effects
- Keys stored permanently (no expiry)

---

## 10. Stripe Integration

### Test Mode

- All development uses Stripe test mode
- No real money ever charged
- Test card: `4242 4242 4242 4242`
- Any future expiry date works
- Any 3-digit CVC works

### Checkout Flow

1. Tenant calls `POST /subscribe/checkout`
2. Server creates Stripe Checkout Session with:
   - Product: Pro Plan ($99/month)
   - Tenant ID stored in metadata
   - Success URL: `http://localhost:8000/success`
   - Cancel URL: `http://localhost:8000/cancel`
3. Server returns `checkout_url`
4. Tenant opens URL in browser
5. Tenant completes payment on Stripe's hosted page
6. Stripe redirects to success URL
7. Stripe fires webhook events

### Stripe Events We Handle

| Event                           | Trigger           | Our Action         |
| ------------------------------- | ----------------- | ------------------ |
| `checkout.session.completed`    | Payment succeeded | Flip tenant to Pro |
| `customer.subscription.updated` | Plan changed      | Sync status        |
| `customer.subscription.deleted` | Cancelled         | Flip back to Free  |

---

## 11. Webhook System

### Signature Verification

Every webhook from Stripe is signed with `STRIPE_WEBHOOK_SECRET`.
We verify this before processing.

Webhook arrives at POST /webhooks/stripe
│
▼
Read raw request body (not parsed JSON)
│
▼
stripe.Webhook.construct_event(payload, sig, secret)
Invalid signature → 400 Bad Request ❌
│
▼
Check stripe_event_id in processed_webhook_events
Already processed → return duplicate: ignored ✅
│
▼
Handle event by type
│
▼
INSERT stripe_event_id into processed_webhook_events
│
▼
Return 200 OK ✅

### Why Raw Body?

Stripe's signature is computed against the raw bytes of the request.
If we parse it to JSON first, the bytes change and verification fails.

### Webhook Deduplication

Stripe guarantees at-least-once delivery — same event can arrive
multiple times. We store every processed `stripe_event_id` in
`processed_webhook_events` to prevent duplicate processing.

### Stripe CLI

Used during development to forward webhooks to localhost:

```bash
.\stripe listen --forward-to localhost:8000/webhooks/stripe
```

---

## 12. Error Codes

| Code | Name                 | When                             |
| ---- | -------------------- | -------------------------------- |
| 200  | OK                   | Request successful               |
| 201  | Created              | New resource created             |
| 400  | Bad Request          | Forged webhook / duplicate email |
| 401  | Unauthorized         | Missing or invalid auth          |
| 402  | Payment Required     | No active subscription plan      |
| 403  | Forbidden            | Wrong role — admin required      |
| 422  | Unprocessable Entity | Missing required fields          |
| 429  | Too Many Requests    | Monthly token quota exceeded     |

### 429 Response Example

```json
{
  "detail": {
    "error": "Quota exceeded",
    "message": "You have used 100,000 of 100,000 tokens on the free plan",
    "used": 100000,
    "limit": 100000,
    "code": "QUOTA_EXCEEDED",
    "upgrade_hint": "Upgrade to Pro for 10,000,000 tokens/month"
  }
}
```

### 403 Response Example

```json
{
  "detail": "Admin access required"
}
```

### 402 Response Example

```json
{
  "detail": {
    "error": "No active plan found",
    "message": "Please subscribe to a plan to continue",
    "code": "NO_PLAN"
  }
}
```

---

## 13. Environment Variables

| Variable                | Description                   | Example                                                              |
| ----------------------- | ----------------------------- | -------------------------------------------------------------------- |
| `DATABASE_URL`          | PostgreSQL connection string  | `postgresql://postgres:password@localhost:5432/LLM-METERING-BILLING` |
| `STRIPE_SECRET_KEY`     | Stripe API secret key         | `sk_test_...`                                                        |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | `whsec_...`                                                          |
| `JWT_SECRET_KEY`        | Secret key for signing JWTs   | `your-super-secret-key`                                              |
| `JWT_ALGORITHM`         | JWT signing algorithm         | `HS256`                                                              |
| `JWT_EXPIRY_HOURS`      | Token lifetime in hours       | `24`                                                                 |

### Security Rules

- `.env` is NEVER committed to Git
- `.env.example` is committed as a template
- Stripe keys must be rotated if accidentally exposed
- GitHub secret scanning blocks pushes containing exposed keys
- JWT secret must be long and random in production

---

## 14. File Structure

LLM-Metering-Billing/
├── LICENSE.md
├── README.md
└── BackEnd/
├── .env # Real secrets (never committed)
├── .env.example # Template (committed)
├── requirements.txt # Pinned dependencies
├── capstone.yaml # Project metadata
├── BUILDLOG.md # Phase by phase build diary
├── EVIDENCE.md # Definition of Done proof
├── INFOS.md # Complete project reference
├── API_CONTRACT.md # API design document
├── app/
│ ├── init.py
│ ├── main.py # FastAPI entry point
│ ├── core/
│ │ ├── init.py
│ │ ├── config.py # Reads .env variables
│ │ ├── database.py # PostgreSQL connection
│ │ └── pricing.py # Pinned token pricing constants
│ ├── models/
│ │ ├── init.py
│ │ └── queries.py # All SQL queries
│ ├── routers/
│ │ ├── init.py
│ │ ├── auth.py # /auth/register, /login, /me
│ │ ├── admin.py # /admin/tenants, /usage, /stats
│ │ ├── generate.py # POST /generate
│ │ ├── subscribe.py # POST /subscribe/checkout
│ │ ├── webhooks.py # POST /webhooks/stripe
│ │ └── usage.py # GET /usage
│ └── services/
│ ├── init.py
│ ├── auth.py # JWT + bcrypt + flexible auth
│ └── meter.py # MeterService
├── migrations/
│ └── 001_initial_schema.sql # Full DB schema + seed data
└── tests/
├── conftest.py # Pytest fixtures
└── test_metering.py # Full test suite

---

## 15. Key Design Decisions

### Why FastAPI over Flask?

FastAPI auto-generates Swagger UI, has built-in request validation
via Pydantic, and is significantly faster. For an API-first project
this is the right choice.

### Why Per-Request DB Connections?

Simple, safe, and predictable. Each request gets its own connection
that closes when done. No shared state, no connection leaks. A
connection pool would be used in production.

### Why Raw SQL over ORM?

Keeps the query layer transparent and explicit. Every SQL statement
is visible in `queries.py` — no magic, no hidden queries. Better
for learning and debugging.

### Why Idempotency at the DB Level?

The `UNIQUE` constraint on `idempotency_key` means the database
itself enforces no duplicates. Even if two concurrent requests arrive
with the same key, the DB constraint catches it.

### Why Store Webhook Event IDs?

Stripe guarantees at-least-once delivery. Without deduplication,
a retried webhook could flip a tenant's plan twice. Storing event
IDs in `processed_webhook_events` makes webhook handling safe.

### Why Pinned Pricing Constants?

Prices in `pricing.py` are module-level constants. If anyone changes
them, pinned tests break immediately. This prevents accidental pricing
changes from going unnoticed.

### Why Separate Token Types?

Different token types have different computational costs. Cached tokens
are cheapest (already computed), output tokens are most expensive
(generated fresh). Tracking separately allows accurate billing.

### Why `DATE_TRUNC('month', NOW())`?

Quota resets monthly. This SQL function truncates timestamps to the
start of the current month, so only this month's usage counts.

### Why Support Both API Key and JWT?

API keys are for machine-to-machine requests (scripts, integrations).
JWT is for user-facing requests (after login). Supporting both keeps
backwards compatibility while adding modern auth.

### Why bcrypt for Passwords?

bcrypt is deliberately slow (100ms per hash) — fast enough for one
login, impossibly slow for brute force attacks. It also adds a random
salt automatically, so identical passwords produce different hashes.

### Why JWT over Sessions?

JWT is stateless — the server doesn't store session data. The token
is self-contained and verified by signature alone. This scales better
across multiple servers and requires no DB lookup per request.

---

## 16. Authentication System

### Packages

| Package     | Purpose                       |
| ----------- | ----------------------------- |
| python-jose | JWT creation and verification |
| passlib     | Password hashing context      |
| bcrypt      | Hashing algorithm             |

### New Environment Variables

| Variable           | Description                 | Example                 |
| ------------------ | --------------------------- | ----------------------- |
| `JWT_SECRET_KEY`   | Secret key for signing JWTs | `your-super-secret-key` |
| `JWT_ALGORITHM`    | Signing algorithm           | `HS256`                 |
| `JWT_EXPIRY_HOURS` | Token lifetime in hours     | `24`                    |

### New DB Columns on tenants

| Column        | Type         | Description            |
| ------------- | ------------ | ---------------------- |
| password_hash | VARCHAR(255) | bcrypt hashed password |
| role          | VARCHAR(50)  | admin or tenant        |

### Auth Endpoints

| Method | Endpoint         | Auth       | Description                         |
| ------ | ---------------- | ---------- | ----------------------------------- |
| POST   | `/auth/register` | None       | Register with name, email, password |
| POST   | `/auth/login`    | None       | Login, receive JWT                  |
| GET    | `/auth/me`       | Bearer JWT | Current tenant profile              |

### JWT Payload Structure

```json
{
  "sub": "1",
  "email": "tenant@example.com",
  "role": "tenant",
  "exp": 1234567890
}
```

### JWT Structure

header.payload.signature
│ │ │
│ │ └── HMACSHA256(header+payload, JWT_SECRET_KEY)
│ └── base64({sub, email, role, exp})
└── base64({alg: HS256, typ: JWT})

### Password Rules

- Storage: bcrypt hash only — plain text never stored
- Verification: passlib CryptContext handles comparison
- Salt: added automatically by bcrypt — same password, different hash

### Token Rules

- Expiry: 24 hours by default
- Format: Bearer token in Authorization header
- Algorithm: HS256
- Invalid/expired token → 401 Unauthorized

### Flexible Auth Priority

Both JWT and API key provided → JWT wins
Only JWT provided → use JWT
Only API key provided → use API key
Neither provided → 401 Unauthorized

---

## 17. Role Based Access Control

### Roles

| Role     | Default | Permissions                                  |
| -------- | ------- | -------------------------------------------- |
| `tenant` | Yes     | Own usage, generate, subscribe               |
| `admin`  | No      | Everything + all tenants data + system stats |

### How Role Check Works

Request hits /admin/\* endpoint
│
▼
require_admin dependency fires
│
▼
get_current_tenant_flexible extracts JWT
│
▼
role == "admin" → allow ✅
role == "tenant" → 403 Forbidden ❌
No token → 401 Unauthorized ❌

### Admin Endpoints

| Method | Endpoint         | Description                               |
| ------ | ---------------- | ----------------------------------------- |
| GET    | `/admin/tenants` | All tenants with plan and status          |
| GET    | `/admin/usage`   | Usage and cost for all tenants this month |
| GET    | `/admin/stats`   | System wide statistics                    |

### Admin Stats Response

```json
{
  "admin": "admin@example.com",
  "stats": {
    "total_tenants": 4,
    "tenants_by_plan": {
      "free": 3,
      "pro": 1
    },
    "total_usage_events": 12,
    "total_tokens_this_month": 100150,
    "total_webhooks_processed": 8
  }
}
```

### Admin Usage Response

```json
{
  "admin": "admin@example.com",
  "month": "current",
  "total_tenants": 4,
  "total_system_cost": 0.05123,
  "tenants": [
    {
      "id": 1,
      "name": "Test Company",
      "plan": "pro",
      "usage": {
        "used_tokens": 150,
        "limit": 10000000,
        "remaining": 9999850,
        "percentage_used": 0.0
      },
      "cost_usd": 0.00105
    }
  ]
}
```

### Seeded Tenants

| id  | name                          | email             | api_key           | role   | plan     |
| --- | ----------------------------- | ----------------- | ----------------- | ------ | -------- |
| 1   | Test Company                  | test@example.com  | test-api-key-123  | tenant | free→pro |
| 2   | Demo Company                  | demo@example.com  | demo-api-key-456  | tenant | free     |
| 3   | Admin User                    | admin@example.com | admin-api-key-789 | admin  | pro      |
| 4+  | Registered via /auth/register | —                 | auto-generated    | tenant | free     |
