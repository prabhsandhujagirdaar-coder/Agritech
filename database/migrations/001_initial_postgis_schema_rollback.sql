-- ==============================================================================
-- AgriChain AI — Rollback Migration 001: Initial PostgreSQL / PostGIS Schema
-- ==============================================================================
-- Reverses 001_initial_postgis_schema.sql by safely dropping tables in FK order.
-- ==============================================================================

DROP TABLE IF EXISTS geo_waypoints CASCADE;
DROP TABLE IF EXISTS telemetry_logs CASCADE;
DROP TABLE IF EXISTS shipments CASCADE;
