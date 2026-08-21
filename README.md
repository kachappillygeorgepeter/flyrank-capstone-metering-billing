# LLM Metering & Billing Engine

A production-grade usage metering and billing engine for LLM APIs.
Tracks token usage, enforces quotas, and handles payments via Stripe.

## Tech Stack

- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL 16
- **Payments:** Stripe
- **Testing:** Pytest + HTTPX

## Project Structure

LLM-Metering-Billing/
└── BackEnd/
├── app/
│ ├── core/ # DB connection, config
│ ├── models/ # DB query layer
│ ├── routers/ # FastAPI route handlers
│ └── services/ # Business logic
├── migrations/ # SQL migration files
├── tests/ # Test suite
├── API_CONTRACT.md # Full API design doc
├── BUILDLOG.md # Build progress log
├── EVIDENCE.md # Definition of Done proof
├── capstone.yaml # Project metadata
└── .env.example # Environment variable template

## Setup Instructions

### 1. Clone the repo

```bash
git clone <repo-url>
cd LLM-Metering-Billing/BackEnd
```

### 2. Create virtual environment

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set up environment variables

```bash
cp .env.example .env
# Fill in your values in .env
```

### 4. Set up the database

- Create a PostgreSQL database named `LLM-METERING-BILLING`
- Run the migration file in pgAdmin 4:

```bash
migrations/001_initial_schema.sql
```

### 5. Run the server

```bash
uvicorn app.main:app --reload
```

## API Endpoints

| Method | Endpoint              | Description             |
| ------ | --------------------- | ----------------------- |
| POST   | `/generate`           | Billable LLM endpoint   |
| GET    | `/usage`              | Usage summary + cost    |
| POST   | `/subscribe/checkout` | Stripe checkout session |
| POST   | `/webhooks/stripe`    | Stripe webhook handler  |

## Status Codes

| Code | Meaning          |
| ---- | ---------------- |
| 200  | Success          |
| 400  | Bad Request      |
| 401  | Unauthorized     |
| 402  | Payment Required |
| 429  | Quota Exceeded   |
