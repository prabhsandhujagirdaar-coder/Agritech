-- ==============================================================================
-- AgriChain AI — Migration 004 Rollback: Revert Shipment Facilities & Events Schema
-- ==============================================================================

-- 1. Drop Shipment Events Table and Cascade Indexes
DROP TABLE IF EXISTS shipment_events CASCADE;

-- 2. Drop Added Columns from Shipments Table
ALTER TABLE shipments DROP COLUMN IF EXISTS intermediate_facility_id;
ALTER TABLE shipments DROP COLUMN IF EXISTS origin_operation;
ALTER TABLE shipments DROP COLUMN IF EXISTS destination_operation;
ALTER TABLE shipments DROP COLUMN IF EXISTS intermediate_operation;
ALTER TABLE shipments DROP COLUMN IF EXISTS planned_departure;
ALTER TABLE shipments DROP COLUMN IF EXISTS actual_departure;
ALTER TABLE shipments DROP COLUMN IF EXISTS planned_arrival;
ALTER TABLE shipments DROP COLUMN IF EXISTS actual_arrival;
ALTER TABLE shipments DROP COLUMN IF EXISTS tracking_mode;
ALTER TABLE shipments DROP COLUMN IF EXISTS telemetry_mode;
