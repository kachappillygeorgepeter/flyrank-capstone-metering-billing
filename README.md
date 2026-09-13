# LLM Metering & Billing Engine

A production-grade usage metering and billing engine for LLM APIs.
Tracks token usage, enforces quotas, handles payments via Stripe,
and secures endpoints with JWT authentication and role based access control.

## Tech Stack

- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL 16
- **Payments:** Stripe
- **Auth:** JWT (python-jose) + bcrypt (passlib)
- **Testing:** Pytest + HTTPX

## Project Documentation

- [Build Log](BackEnd/BUILDLOG.md)
- [Evidence](BackEnd/EVIDENCE.md)
- [API Contract](BackEnd/API_CONTRACT.md)
- [Full Project Reference](BackEnd/INFOS.md)
- [Capstone Config](BackEnd/capstone.yaml)

## Project Structure

LLM-Metering-Billing/
└── BackEnd/
├── app/
│ ├── core/
│ │ ├── config.py # Reads .env secrets
│ │ ├── database.py # PostgreSQL connection
│ │ └── pricing.py # Pinned pricing constants
│ ├── models/
│ │ └── queries.py # All SQL queries
│ ├── routers/
│ │ ├── auth.py # POST /auth/register, /login, /me
│ │ ├── admin.py # GET /admin/tenants, /usage, /stats
│ │ ├── generate.py # POST /generate endpoint
│ │ ├── subscribe.py # POST /subscribe/checkout
│ │ ├── webhooks.py # POST /webhooks/stripe
│ │ └── usage.py # GET /usage endpoint
│ ├── services/
│ │ ├── auth.py # JWT + bcrypt + flexible auth
│ │ └── meter.py # MeterService — billing brain
│ └── main.py # FastAPI entry point
├── migrations/
│ └── 001_initial_schema.sql
├── tests/
│ └── test_metering.py
├── API_CONTRACT.md
├── BUILDLOG.md
├── EVIDENCE.md
├── INFOS.md
├── capstone.yaml
└── .env.example

## Setup Instructions

### 1. Clone the repo

```bash
git clone <repo-url>
cd LLM-Metering-Billing/BackEnd
```

### 2. Create virtual environment

```bash
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set up environment variables

```bash
copy .env.example .env
# Fill in your values in .env
```

### 4. Set up the database

- Create a PostgreSQL database named `LLM-METERING-BILLING`
- Run the migration file in pgAdmin 4:

migrations/001_initial_schema.sql

### 5. Seed tenants

```sql
-- Test tenant
INSERT INTO tenants (name, email, api_key)
VALUES ('Test Company', 'test@example.com', 'test-api-key-123');
INSERT INTO subscriptions (tenant_id, plan_id) VALUES (1, 1);

-- Demo tenant (near quota limit)
INSERT INTO tenants (name, email, api_key)
VALUES ('Demo Company', 'demo@example.com', 'demo-api-key-456');
INSERT INTO subscriptions (tenant_id, plan_id) VALUES (2, 1);
INSERT INTO usage_events (tenant_id, idempotency_key, input_tokens)
VALUES (2, 'seed-usage-demo', 99800);

-- Admin tenant
INSERT INTO tenants (name, email, api_key, role)
VALUES ('Admin User', 'admin@example.com', 'admin-api-key-789', 'admin');
INSERT INTO subscriptions (tenant_id, plan_id) VALUES (3, 2);
```

### 6. Set admin password

```powershell
py -c "from passlib.context import CryptContext; pwd = CryptContext(schemes=['bcrypt'], deprecated='auto'); print(pwd.hash('adminpassword123'))"
```

Then in pgAdmin:

```sql
UPDATE tenants SET password_hash = 'paste_hash_here'
WHERE email = 'admin@example.com';
```

### 7. Run the server

```bash
uvicorn app.main:app --reload
```

### 8. Start Stripe CLI (separate terminal)

```bash
.\stripe listen --forward-to localhost:8000/webhooks/stripe
```

### 9. Open Swagger UI

http://localhost:8000/docs

## API Endpoints

### Auth (Public)

| Method | Endpoint         | Description       |
| ------ | ---------------- | ----------------- |
| POST   | `/auth/register` | Create account    |
| POST   | `/auth/login`    | Get JWT token     |
| GET    | `/auth/me`       | Current user info |

### Billing (API Key or JWT)

| Method | Endpoint              | Description              |
| ------ | --------------------- | ------------------------ |
| GET    | `/health`             | Server + DB health check |
| POST   | `/generate`           | Billable LLM endpoint    |
| GET    | `/usage`              | Own usage summary + cost |
| POST   | `/subscribe/checkout` | Stripe checkout session  |
| POST   | `/webhooks/stripe`    | Stripe webhook handler   |

### Admin (JWT + Admin Role Only)

| Method | Endpoint         | Description              |
| ------ | ---------------- | ------------------------ |
| GET    | `/admin/tenants` | All tenants list         |
| GET    | `/admin/usage`   | All tenants usage + cost |
| GET    | `/admin/stats`   | System wide stats        |

## Authentication Methods

| Method  | Header                          | When to Use        |
| ------- | ------------------------------- | ------------------ |
| API Key | `x-api-key: <key>`              | Machine to machine |
| JWT     | `Authorization: Bearer <token>` | After login        |

## Roles

| Role     | Access                                       |
| -------- | -------------------------------------------- |
| `tenant` | Own usage, generate, subscribe               |
| `admin`  | Everything + all tenants data + system stats |

## Pricing

| Token Type   | Rate per 1k tokens |
| ------------ | ------------------ |
| Input        | $0.003             |
| Cached Input | $0.0003            |
| Output       | $0.015             |
| Reasoning    | $0.015             |

## Plans & Quotas

| Plan | Token Limit             | Price        |
| ---- | ----------------------- | ------------ |
| Free | 100,000 tokens/month    | $0.00        |
| Pro  | 10,000,000 tokens/month | $99.00/month |

## Status Codes

| Code | Meaning                |
| ---- | ---------------------- |
| 200  | Success                |
| 201  | Created                |
| 400  | Bad Request            |
| 401  | Unauthorized           |
| 402  | Payment Required       |
| 403  | Forbidden — wrong role |
| 422  | Unprocessable Entity   |
| 429  | Quota Exceeded         |

## Auth Flow

Register → POST /auth/register → 201 + tenant info
Login → POST /auth/login → 200 + JWT token
Use JWT → Authorization: Bearer <token> on any endpoint
Admin → JWT with role:admin → access /admin/\* endpoints

## Metering Flow

POST /generate
↓
Auth — API Key or JWT → 401 if invalid
↓
Check Quota → 429 if exceeded / 402 if no plan
↓
Check Idempotency Key → return cached if duplicate
↓
Record Usage Event
↓
Return 200 with quota info

## Stripe Flow

POST /subscribe/checkout
↓
Create Stripe Checkout Session
↓
Tenant pays on Stripe hosted page
↓
Stripe fires webhook to /webhooks/stripe
↓
Verify signature → 400 if forged
↓
Check deduplication → ignore if duplicate
↓
Update tenant plan in DB → Pro ✅
