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

The engine sits between an LLM API and its customers. Every time a tenant makes a billable request, the engine records usage, checks quotas, and calculates cost — all in real time.

---

## 2. Tech Stack

| Layer          | Technology      | Version | Why                                   |
| -------------- | --------------- | ------- | ------------------------------------- |
| Language       | Python          | 3.13    | Modern, async-friendly                |
| Web Framework  | FastAPI         | 0.111.0 | Fast, auto-docs, modern Python        |
| Server         | Uvicorn         | 0.29.0  | ASGI server for FastAPI               |
| Database       | PostgreSQL      | 16      | Reliable, ACID compliant              |
| DB Driver      | psycopg2-binary | 2.9.12  | Standard PostgreSQL driver for Python |
| Payments       | Stripe          | 15.5.1  | Industry standard payment platform    |
| Validation     | Pydantic        | 2.13.4  | Request/response validation           |
| Env Management | python-dotenv   | 1.2.2   | Secure secret management              |
| Testing        | Pytest          | 9.1.1   | Industry standard test framework      |
| HTTP Testing   | HTTPX           | 0.28.1  | FastAPI test client dependency        |

---

## 3. Architecture

Client
│
▼
FastAPI (uvicorn)
│
├── POST /generate ──────► MeterService
│ │
│ ├── Validate API Key
│ ├── Check Quota
│ ├── Check Idempotency
│ └── Record Usage Event
│
├── GET /usage ──────────► Pricing Engine
│ │
│ └── Calculate Cost
│
├── POST /subscribe/checkout ──► Stripe API
│ │
│ └── Return Checkout URL
│
└── POST /webhooks/stripe ──► Webhook Handler
│
├── Verify Signature
├── Check Deduplication
└── Update Tenant Plan

PostgreSQL
├── tenants
├── plans
├── subscriptions
├── usage_events
└── processed_webhook_events

---

## 4. Database Schema

### Table: `tenants`

Stores every customer using the API.

| Column     | Type         | Constraints      | Description           |
| ---------- | ------------ | ---------------- | --------------------- |
| id         | SERIAL       | PRIMARY KEY      | Auto-incrementing ID  |
| name       | VARCHAR(255) | NOT NULL         | Company/customer name |
| email      | VARCHAR(255) | NOT NULL, UNIQUE | Contact email         |
| api_key    | VARCHAR(255) | NOT NULL, UNIQUE | Authentication key    |
| created_at | TIMESTAMP    | DEFAULT NOW()    | Account creation time |

### Table: `plans`

Stores available billing plans.

| Column      | Type          | Constraints      | Description           |
| ----------- | ------------- | ---------------- | --------------------- |
| id          | SERIAL        | PRIMARY KEY      | Auto-incrementing ID  |
| name        | VARCHAR(50)   | NOT NULL, UNIQUE | Plan name (free, pro) |
| token_limit | INTEGER       | NOT NULL         | Monthly token quota   |
| price_usd   | NUMERIC(10,2) | NOT NULL         | Monthly price in USD  |
| created_at  | TIMESTAMP     | DEFAULT NOW()    | Plan creation time    |

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

### GET /health

**Purpose:** Check server and database are alive.
**Auth:** None
**Response:**

```json
{ "status": "ok", "database": "connected" }
```

---

### POST /generate

**Purpose:** Dummy billable LLM endpoint. Records usage.
**Auth:** `x-api-key` header

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
  "tenant": "Test Company",
  "prompt": "Your prompt here",
  "response": "Generated response for: Your prompt here",
  "tokens": {
    "input": 100,
    "cached": 0,
    "output": 50,
    "reasoning": 0
  },
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

- `401` — Invalid API key
- `402` — No active plan found
- `429` — Quota exceeded

---

### GET /usage

**Purpose:** Returns tenant usage summary and cost breakdown.
**Auth:** `x-api-key` header

**Success Response (200):**

```json
{
  "tenant": "Test Company",
  "plan": "free",
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

**Error Responses:**

- `401` — Invalid API key
- `402` — No active plan found

---

### POST /subscribe/checkout

**Purpose:** Creates a Stripe Checkout session for plan upgrade.
**Auth:** `x-api-key` header

**Success Response (200):**

```json
{
  "checkout_url": "https://checkout.stripe.com/...",
  "session_id": "cs_test_..."
}
```

**Error Responses:**

- `401` — Invalid API key
- `400` — Stripe error

---

### POST /webhooks/stripe

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
  "event": "...",
  "message": "Event already processed — ignored"
}
```

**Error Responses:**

- `400` — Invalid or forged webhook signature

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
- (reasoning_tokens/ 1000 × 0.015)

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
- Quota is checked **before** recording usage
- At exactly the limit → blocked (429)
- Just under the limit → allowed
- Over the limit → blocked (429)
- No active plan → 402 Payment Required

### Demo Tenant Setup

- Seeded with **99,800 tokens used** out of 100,000
- Only **200 tokens remaining** — near quota limit
- Next request over 200 tokens → triggers 429

---

## 8. Metering Flow

POST /generate arrives
│
▼
Validate API Key
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

Network issues can cause clients to retry requests. Without idempotency:

Client sends request → network drops → client retries
→ Two usage events recorded → tenant billed twice ❌

### Our Solution

Every request includes a unique `idempotency_key`. The `usage_events` table has a `UNIQUE` constraint on this column.

First request (key: "req-001")
→ Key not in DB → record usage ✅

Retry (key: "req-001")
→ Key already in DB → skip recording ✅
→ Return same response
→ No double billing ✅

### Key Rules

- Client is responsible for generating unique keys per request
- Keys must be unique per tenant
- Same key = same result, no side effects
- Keys are stored permanently (no expiry)

---

## 10. Stripe Integration

### Test Mode

- All development uses Stripe **test mode**
- No real money is ever charged
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

Every webhook from Stripe is signed with `STRIPE_WEBHOOK_SECRET`. We verify this before processing.

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

Stripe's signature is computed against the **raw bytes** of the request. If we parse it to JSON first, the bytes change and signature verification fails.

### Webhook Deduplication

Stripe guarantees **at least once delivery** — same event can arrive multiple times. We store every processed `stripe_event_id` in `processed_webhook_events` to prevent duplicate processing.

### Stripe CLI

Used during development to forward Stripe webhooks to localhost:

```bash
.\stripe listen --forward-to localhost:8000/webhooks/stripe
```

Provides a temporary `whsec_...` secret for local testing.

---

## 12. Error Codes

| Code | Name                 | When                             |
| ---- | -------------------- | -------------------------------- |
| 200  | OK                   | Request successful               |
| 400  | Bad Request          | Forged/invalid webhook signature |
| 401  | Unauthorized         | Missing or invalid API key       |
| 402  | Payment Required     | No active subscription plan      |
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

### Security Rules

- `.env` is **never committed to Git**
- `.env.example` is committed as a template
- Stripe keys must be rotated if accidentally exposed
- GitHub secret scanning will block pushes containing exposed keys

---

## 14. File Structure

LLM-Metering-Billing/
├── LICENSE.md
├── README.md # Project overview + setup
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
│ ├── main.py # FastAPI entry point, router registration
│ ├── core/
│ │ ├── init.py
│ │ ├── config.py # Reads .env variables
│ │ ├── database.py # PostgreSQL connection + get_db dependency
│ │ └── pricing.py # Pinned token pricing constants + calculate_cost()
│ ├── models/
│ │ ├── init.py
│ │ └── queries.py # All SQL queries in one place
│ ├── routers/
│ │ ├── init.py
│ │ ├── generate.py # POST /generate — billable endpoint
│ │ ├── subscribe.py # POST /subscribe/checkout — Stripe checkout
│ │ ├── webhooks.py # POST /webhooks/stripe — webhook handler
│ │ └── usage.py # GET /usage — usage summary + cost
│ └── services/
│ ├── init.py
│ └── meter.py # MeterService — quota + idempotency + recording
├── migrations/
│ └── 001_initial_schema.sql # Full DB schema + seed data
└── tests/
├── conftest.py # Pytest fixtures
└── test_metering.py # Full test suite

---

## 15. Key Design Decisions

### Why FastAPI over Flask?

FastAPI auto-generates Swagger UI, has built-in request validation via Pydantic, and is significantly faster. For an API-first project this is the right choice.

### Why Per-Request DB Connections?

Simple, safe, and predictable. Each request gets its own connection that closes when done. No shared state, no connection leaks. A connection pool would be used in production.

### Why Raw SQL over ORM?

Keeps the query layer transparent and explicit. Every SQL statement is visible in `queries.py` — no magic, no hidden queries. Better for learning and debugging.

### Why Idempotency at the DB Level?

The `UNIQUE` constraint on `idempotency_key` means the database itself enforces no duplicates. Even if two concurrent requests arrive with the same key, the DB constraint catches it — not application logic.

### Why Store Webhook Event IDs?

Stripe guarantees at-least-once delivery. Without deduplication, a retried webhook could flip a tenant's plan twice or process a payment twice. Storing event IDs in `processed_webhook_events` makes webhook handling safe.

### Why Pinned Pricing Constants?

Prices in `pricing.py` are module-level constants. If anyone changes them, pinned tests break immediately. This prevents accidental pricing changes from going unnoticed.

### Why Separate Token Types?

Different token types have different computational costs. Cached tokens are cheapest (already computed), output tokens are most expensive (generated fresh). Tracking separately allows accurate billing and mirrors real LLM API pricing.

### Why `DATE_TRUNC('month', NOW())`?

Quota resets monthly. This SQL function truncates timestamps to the start of the current month, so only this month's usage counts toward the quota.
