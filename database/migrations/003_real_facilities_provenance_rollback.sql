-- ==============================================================================
-- AgriChain AI — Migration 003 Rollback: Real Sourced Storage Facilities & Provenance Schema
-- ==============================================================================

DROP INDEX IF EXISTS idx_storage_facilities_verif_status;
DROP INDEX IF EXISTS idx_storage_facilities_source_name;

ALTER TABLE storage_facilities DROP COLUMN IF EXISTS contact_phone;
ALTER TABLE storage_facilities DROP COLUMN IF EXISTS contact_email;
ALTER TABLE storage_facilities DROP COLUMN IF EXISTS supported_commodities;
ALTER TABLE storage_facilities DROP COLUMN IF EXISTS source_name;
ALTER TABLE storage_facilities DROP COLUMN IF EXISTS source_url;
ALTER TABLE storage_facilities DROP COLUMN IF EXISTS source_record;
ALTER TABLE storage_facilities DROP COLUMN IF EXISTS verification_status;
ALTER TABLE storage_facilities DROP COLUMN IF EXISTS verification_date;
ALTER TABLE storage_facilities DROP COLUMN IF EXISTS last_source_check;
ALTER TABLE storage_facilities DROP COLUMN IF EXISTS coordinate_source;
ALTER TABLE storage_facilities DROP COLUMN IF EXISTS geocoding_confidence;
ALTER TABLE storage_facilities DROP COLUMN IF EXISTS data_provenance;
