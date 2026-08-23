# Evidence — Definition of Done

## Phase 1 ✅

- Database schema created and verified in pgAdmin 4
- All 4 tables exist: tenants, plans, subscriptions, usage_events
- Plans seeded: free (100k tokens, $0) and pro (10M tokens, $99)
- API contract documented in API_CONTRACT.md

## Phase 2 ✅

### Idempotency

- Sent same request twice with idempotency_key: "req-001"
- First request → 200, duplicate: false, usage recorded
- Second request → 200, duplicate: true, no new row in DB
- SELECT \* FROM usage_events confirms only ONE row

### Quota Enforcement

- Normal request → 200 with quota info in response
- Inserted fake usage event pushing tenant over 100k limit
- Next request → 429 with clear error message and upgrade hint
- Cleaned up fake event after test

### API Key Validation

- Request with valid key → 200
- Request with invalid key → 401 Unauthorized

## Phase 3 ✅

### Stripe Checkout

- POST /subscribe/checkout returns Stripe checkout URL
- Payment completed with test card 4242 4242 4242 4242
- Redirected to /success page after payment

### Webhook Handler

- Valid webhook → 200, event processed
- Forged webhook (no signature) → 400 Bad Request
- Stripe CLI shows [200] on valid events

### Webhook Deduplication

- processed_webhook_events table stores all processed event IDs
- Same event replayed → duplicate detected → ignored
- Only one row per event ID in processed_webhook_events

### Plan Sync

- Tenant was on free plan before checkout
- After checkout.session.completed webhook → tenant flipped to pro
- Verified via SELECT on subscriptions table

## Phase 4 🔲

## Phase 5 🔲
