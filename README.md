# LLM Metering & Billing Engine

A production-grade usage metering and billing engine for LLM APIs.
Tracks token usage, enforces quotas, and handles payments via Stripe.

## Project Documentation

- [Build Log](BackEnd/BUILDLOG.md)
- [Evidence](BackEnd/EVIDENCE.md)
- [API Contract](BackEnd/API_CONTRACT.md)
- [Capstone Config](BackEnd/capstone.yaml)

## Tech Stack

- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL 16
- **Payments:** Stripe
- **Testing:** Pytest + HTTPX

## Project Structure

LLM-Metering-Billing/
└── BackEnd/
├── app/
│ ├── core/
│ │ ├── config.py # Reads .env secrets
│ │ └── database.py # PostgreSQL connection
│ ├── models/
│ │ └── queries.py # All SQL queries
│ ├── routers/
│ │ ├── generate.py # POST /generate endpoint
│ │ ├── subscribe.py # POST /subscribe/checkout
│ │ └── webhooks.py # POST /webhooks/stripe
│ ├── services/
│ │ └── meter.py # MeterService — billing brain
│ └── main.py # FastAPI entry point
├── migrations/
│ └── 001_initial_schema.sql
├── tests/ # Test suite (Phase 4)
├── API_CONTRACT.md
├── BUILDLOG.md
├── EVIDENCE.md
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

### 5. Seed a test tenant

```sql
INSERT INTO tenants (name, email, api_key)
VALUES ('Test Company', 'test@example.com', 'test-api-key-123');

INSERT INTO subscriptions (tenant_id, plan_id)
VALUES (1, 1);
```

### 6. Run the server

```bash
uvicorn app.main:app --reload
```

### 7. Start Stripe CLI (separate terminal)

```bash
.\stripe listen --forward-to localhost:8000/webhooks/stripe
```

### 8. Open Swagger UI

http://localhost:8000/docs

## API Endpoints

| Method | Endpoint              | Description              |
| ------ | --------------------- | ------------------------ |
| GET    | `/health`             | Server + DB health check |
| POST   | `/generate`           | Billable LLM endpoint    |
| GET    | `/usage`              | Usage summary + cost     |
| POST   | `/subscribe/checkout` | Stripe checkout session  |
| POST   | `/webhooks/stripe`    | Stripe webhook handler   |

## Pricing

| Token Type   | Rate per 1k tokens |
| ------------ | ------------------ |
| Input        | $0.003             |
| Cached Input | $0.0003            |
| Output       | $0.015             |
| Reasoning    | $0.015             |

## Status Codes

| Code | Meaning                           |
| ---- | --------------------------------- |
| 200  | Success                           |
| 400  | Bad Request — forged webhook      |
| 401  | Unauthorized — invalid API key    |
| 402  | Payment Required — no active plan |
| 429  | Quota Exceeded                    |

## Metering Flow

POST /generate
↓
Validate API Key → 401 if invalid
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
Update tenant plan in DB
↓
Tenant is now on Pro
