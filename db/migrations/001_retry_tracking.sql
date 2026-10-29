-- ============================================================
-- Migracja 001 — śledzenie błędów i ponowień analizy
-- ============================================================
-- schema.sql wykonuje się tylko przy pierwszym starcie wolumenu Postgresa,
-- więc istniejące bazy trzeba zmigrować ręcznie:
--
--   docker compose exec -T postgres psql -U postgres -d pulsingfeed \
--     < db/migrations/001_retry_tracking.sql
--
-- Migracja jest idempotentna — można ją uruchomić wielokrotnie.

ALTER TABLE articles ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMPTZ;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS retry_count   INTEGER NOT NULL DEFAULT 0;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS error_message TEXT;
