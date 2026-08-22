# API Contract

## Endpoints

### POST /generate

- Auth: X-API-Key header
- Idempotency: X-Idempotency-Key header
- 200: success or duplicate request
- 401: invalid API key
- 429: quota exceeded
- 402: plan upgrade required

### GET /usage

- Auth: X-API-Key header
- 200: returns used/limit/remaining/cost_usd

### POST /subscribe/checkout

- Auth: X-API-Key header
- 200: returns stripe checkout URL

### POST /webhooks/stripe

- Auth: Stripe-Signature header
- 200: event processed or duplicate ignored
- 400: invalid signature

## Idempotency Strategy

- Client sends unique key per request
- DB UNIQUE constraint prevents duplicate usage events
- Retries with same key return same response, no double billing

## Status Codes

- 200 OK
- 400 Bad Request
- 401 Unauthorized
- 402 Payment Required
- 429 Too Many Requests
