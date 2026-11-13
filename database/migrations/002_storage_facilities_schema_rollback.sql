-- ==============================================================================
-- AgriChain AI — Migration 002 Rollback: Storage Facilities Schema
-- ==============================================================================

ALTER TABLE shipments DROP COLUMN IF EXISTS origin_facility_id;
ALTER TABLE shipments DROP COLUMN IF EXISTS destination_facility_id;
DROP TABLE IF EXISTS storage_facilities CASCADE;
