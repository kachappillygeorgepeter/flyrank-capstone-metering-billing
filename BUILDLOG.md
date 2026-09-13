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

- [ ] Tests to be completed

## Phase 5 — Demo Prep ✅

### Part 1 — Seed Data & Demo Rehearsal ✅

- [x] Demo tenant seeded with 99,800/100,000 tokens used
- [x] Demo script written and rehearsed
- [x] All 7 demo scenes documented
- [x] Pre-demo checklist created
- [x] Everything pushed to GitHub

## Phase 6 — Authentication & Security ✅

### Part 1 — Theory & Foundation ✅

- [x] Authentication vs Authorization understood
- [x] JWT structure and signing understood
- [x] bcrypt password hashing understood
- [x] Session vs Token based auth understood
- [x] RBAC concepts understood

### Part 2 — Tenant Login System ✅

- [x] python-jose and passlib installed
- [x] password_hash column added to tenants
- [x] role column added to tenants
- [x] JWT config added to .env
- [x] app/services/auth.py built
- [x] Auth queries added to queries.py
- [x] POST /auth/register built
- [x] POST /auth/login built
- [x] GET /auth/me built
- [x] Registration tested — 201 returned
- [x] Login tested — JWT returned
- [x] Wrong password tested — 401 returned
- [x] Duplicate email tested — 400 returned

### Part 3 — JWT Protected Endpoints ✅

- [x] Flexible auth dependency built — API Key OR JWT
- [x] GET /usage updated to support JWT
- [x] POST /generate updated to support JWT
- [x] POST /subscribe/checkout updated to support JWT
- [x] auth_method shown in responses
- [x] JWT auth tested — 200 with auth_method: jwt
- [x] API key auth tested — 200 with auth_method: api_key
- [x] No auth tested — 401 returned
- [x] Invalid JWT tested — 401 returned

### Part 4 — Role Based Access Control ✅

- [x] Admin queries built — get_all_tenants, get_all_usage
- [x] GET /admin/tenants built — admin only
- [x] GET /admin/usage built — admin only
- [x] GET /admin/stats built — admin only
- [x] Admin router registered in main.py
- [x] Admin password seeded via bcrypt
- [x] Admin login tested — JWT with role:admin returned
- [x] Admin can see all tenants — 200 returned
- [x] Admin can see all usage — 200 returned
- [x] Tenant cannot access admin endpoints — 403 returned
- [x] No token on admin endpoint — 401 returned
