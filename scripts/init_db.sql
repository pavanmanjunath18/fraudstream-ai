-- FraudStream AI — PostgreSQL initialization
-- This runs once when the Postgres container first starts.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Full-text search on risk factors (production use)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Indexes for common query patterns
-- (SQLAlchemy creates the tables; these supplement with additional indexes)

-- Run after tables are created by Alembic/SQLAlchemy:
-- CREATE INDEX IF NOT EXISTS idx_fraud_pred_prob ON fraud_predictions (fraud_probability DESC);
-- CREATE INDEX IF NOT EXISTS idx_fraud_pred_window ON fraud_predictions (created_at DESC, decision);
