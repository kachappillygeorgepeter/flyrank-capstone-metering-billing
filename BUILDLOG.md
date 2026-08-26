# Build Log

## Phase 1 — Design ✅

### Part 1 — Project Setup ✅

- [x] PostgreSQL 16 installed and running on port 5432
- [x] LLM-METERING-BILLING database created in pgAdmin 4
- [x] Folder structure created under BackEnd/
- [x] Root files created (.env.example, capstone.yaml, BUILDLOG.md, API_CONTRACT.md)
- [x] Python venv created and activated
- [x] FastAPI + all dependencies installed
- [x] requirements.txt generated

### Part 2 — Database Schema Design ✅

- [x] 4 tables designed and created (tenants, plans, subscriptions, usage_events)
- [x] Migration file written: 001_initial_schema.sql
- [x] Foreign key relationships established
- [x] UNIQUE constraint on idempotency_key for duplicate prevention
- [x] Plans seeded: free (100k tokens) and pro (10M tokens)
- [x] Schema verified in pgAdmin 4

### Part 3 — API Contract Design ✅

- [x] All endpoints defined
- [x] Status codes documented for every endpoint
- [x] Idempotency strategy documented
- [x] Metering flow designed
- [x] API_CONTRACT.md created

## Phase 2 — Core Billing Logic ✅

### Part 1 — Project Base & Database Connection ✅

- [x] FastAPI app entry point created (main.py)
- [x] FastAPI connected to PostgreSQL
- [x] .env configured for secrets
- [x] DB models/query layer created (queries.py)
- [x] Health check endpoint working
- [x] Swagger UI accessible at /docs

### Part 2 — Usage Metering (Idempotency) ✅

- [x] POST /generate built
- [x] MeterService built
- [x] Idempotency key logic implemented
- [x] Duplicate prevention verified — one row in DB despite two requests
- [x] API key validation working — 401 on invalid key

### Part 3 — Quota Enforcement ✅

- [x] check_quota() method built in MeterService
- [x] 429 Too Many Requests on quota exceeded
- [x] 402 Payment Required on no active plan
- [x] Clear error messages with usage details
- [x] Quota check runs before idempotency check
- [x] Both tests passed in Swagger UI

## Phase 3 — Stripe Integration ✅

### Part 1 — Stripe Account & Checkout Flow ✅

- [x] Stripe account created in test mode
- [x] Stripe CLI installed and forwarding webhooks
- [x] POST /subscribe/checkout built
- [x] Stripe Checkout Session created successfully
- [x] Test payment completed with card 4242 4242 4242 4242
- [x] Redirected to /success page
- [x] Stripe events firing correctly

### Part 2 — Webhook Handler ✅

- [x] POST /webhooks/stripe built
- [x] Stripe signature verification working
- [x] checkout.session.completed handled
- [x] customer.subscription.updated handled
- [x] customer.subscription.deleted handled
- [x] Forged webhook returns 400
- [x] Valid webhook returns 200

### Part 3 — Webhook Deduplication & Plan Sync ✅

- [x] processed_webhook_events table created
- [x] Duplicate webhook prevention implemented
- [x] Tenant plan updated from verified webhook events
- [x] Full flow tested: Checkout → webhook → Free → Pro flip
- [x] Replay webhook ignored as duplicate
- [x] Forged webhook rejected with 400

## Phase 4 — Cost Calculation & Finalization ✅

### Part 1 — Cost Calculation Engine ✅

- [x] pricing.py created with pinned constants
- [x] calculate_cost() function built
- [x] get_tenant_usage_breakdown() query added
- [x] GET /usage endpoint built
- [x] Cost math verified manually

### Part 2 — Full Test Suite 🔲

- [ ] Testing

## Phase 5 — Demo Prep 🔲

### Part 1 — Seed Data & Demo Rehearsal

- [ ] Tenant seeded near quota limit
- [ ] Full demo flow rehearsed
