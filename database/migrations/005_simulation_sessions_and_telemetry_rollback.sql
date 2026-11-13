-- ==============================================================================
-- AgriChain AI — Migration 005 Rollback: Dynamic Simulation & Telemetry Schema
-- ==============================================================================
-- Description:
-- Drops simulation_telemetry and simulation_sessions tables.
-- ==============================================================================

DROP TABLE IF EXISTS simulation_telemetry CASCADE;
DROP TABLE IF EXISTS simulation_sessions CASCADE;

