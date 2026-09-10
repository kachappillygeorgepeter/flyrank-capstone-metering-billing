-- ============================================
-- Migration 001 — Initial Schema
-- LLM Metering & Billing Engine
-- ============================================
-- 1. TENANTS
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    api_key VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);
-- 2. PLANS
CREATE TABLE plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    -- 'free', 'pro'
    token_limit INTEGER NOT NULL,
    -- monthly quota
    price_usd NUMERIC(10, 2) NOT NULL,
    -- monthly price
    created_at TIMESTAMP DEFAULT NOW()
);
-- 3. SUBSCRIPTIONS
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    plan_id INTEGER NOT NULL REFERENCES plans(id),
    stripe_subscription_id VARCHAR(255),
    -- null for free plan
    status VARCHAR(50) DEFAULT 'active',
    -- active, cancelled
    started_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
-- 4. USAGE EVENTS
CREATE TABLE usage_events (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    idempotency_key VARCHAR(255) NOT NULL UNIQUE,
    -- prevents duplicates
    input_tokens INTEGER DEFAULT 0,
    cached_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
-- ============================================
-- Seed default plans
-- ============================================
INSERT INTO plans (name, token_limit, price_usd)
VALUES ('free', 100000, 0.00),
    ('pro', 10000000, 99.00);
CREATE TABLE processed_webhook_events (
    id SERIAL PRIMARY KEY,
    stripe_event_id VARCHAR(255) NOT NULL UNIQUE,
    event_type VARCHAR(255) NOT NULL,
    processed_at TIMESTAMP DEFAULT NOW()
);
ALTER TABLE tenants
ADD COLUMN password_hash VARCHAR(255);
ALTER TABLE tenants
ADD COLUMN role VARCHAR(50) DEFAULT 'tenant';