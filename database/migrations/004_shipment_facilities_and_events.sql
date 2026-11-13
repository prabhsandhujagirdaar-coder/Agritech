-- ==============================================================================
-- AgriChain AI — Migration 004: Shipment Facilities, Multi-Hub Routing & Events Schema
-- ==============================================================================
-- Description:
-- 1. Adds intermediate transit facility reference, facility operations, scheduling,
--    and tracking/telemetry modes to the shipments table.
-- 2. Creates the shipment_events table for auditable lifecycle and facility handover events.
-- 3. Seeds initial verified events for historical shipments with ON CONFLICT DO NOTHING.
--
-- Safety & Idempotency:
-- - Uses IF NOT EXISTS for all column additions, tables, and indexes.
-- - Safe to execute multiple times without error or duplicate data insertion.
--
-- Prerequisites before applying to live PostgreSQL:
-- - PostgreSQL 14+ with PostGIS 3.0+
-- - Prior migrations (001, 002, 003) applied.
-- - Backup command: pg_dump -U agrichain -d agrichain_db -F c -b -v -f "backup_before_migration_004.dump"
-- ==============================================================================

-- 1. Add Intermediate Facility and Multi-Hub Columns to shipments table
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS intermediate_facility_id VARCHAR(64) REFERENCES storage_facilities(id) ON DELETE SET NULL;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS origin_operation VARCHAR(60);
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS destination_operation VARCHAR(60);
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS intermediate_operation VARCHAR(60);
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS planned_departure TIMESTAMPTZ;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS actual_departure TIMESTAMPTZ;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS planned_arrival TIMESTAMPTZ;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS actual_arrival TIMESTAMPTZ;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS tracking_mode VARCHAR(40) DEFAULT 'simulated';
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS telemetry_mode VARCHAR(40) DEFAULT 'simulated';

-- Indexes for shipment facility references and query routing
CREATE INDEX IF NOT EXISTS idx_shipments_intermediate_facility ON shipments(intermediate_facility_id);
CREATE INDEX IF NOT EXISTS idx_shipments_tracking_mode ON shipments(tracking_mode);

-- 2. Create Auditable Shipment Lifecycle Events Table
CREATE TABLE IF NOT EXISTS shipment_events (
    id VARCHAR(64) PRIMARY KEY,
    shipment_id VARCHAR(64) NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    event_type VARCHAR(60) NOT NULL,
    description TEXT NOT NULL,
    facility_id VARCHAR(64) REFERENCES storage_facilities(id) ON DELETE SET NULL,
    source VARCHAR(60) NOT NULL DEFAULT 'system_event',
    metadata JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for timeline retrieval and event type filtering
CREATE INDEX IF NOT EXISTS idx_shipment_events_shipment_id ON shipment_events(shipment_id);
CREATE INDEX IF NOT EXISTS idx_shipment_events_event_type ON shipment_events(event_type);
CREATE INDEX IF NOT EXISTS idx_shipment_events_timestamp ON shipment_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_shipment_events_facility_id ON shipment_events(facility_id);

-- 3. Seed Initial Auditable Events for Baseline Shipments
INSERT INTO shipment_events (id, shipment_id, event_type, description, facility_id, source, metadata, timestamp)
VALUES
(
    'EVT-SHP-2026-001-1',
    'SHP-2026-001',
    'shipment_created',
    'Shipment batch created for 450 crates of Guava from Alamgarh Packhouse to Azadpur APMC Mega Mandi.',
    'FAC-PB-ABO-01',
    'system_event',
    '{"produce_type": "Guava", "quantity_crates": 450}'::jsonb,
    '2026-10-18T10:00:00Z'
),
(
    'EVT-SHP-2026-001-2',
    'SHP-2026-001',
    'facility_association_updated',
    'Origin linked to FAC-PB-ABO-01; Destination linked to FAC-DL-AZD-01; Intermediate hub linked to FAC-PB-BTI-01.',
    'FAC-PB-ABO-01',
    'system_event',
    '{"origin_operation": "packhouse_cooling", "destination_operation": "market_auction", "intermediate_operation": "transit_hub"}'::jsonb,
    '2026-10-18T10:05:00Z'
),
(
    'EVT-SHP-2026-001-3',
    'SHP-2026-001',
    'shipment_dispatched',
    'Refrigerated transport vehicle dispatched from origin packhouse onto NH-7 corridor.',
    'FAC-PB-ABO-01',
    'manual_operator',
    '{"driver": "Harpreet Singh", "vehicle": "PB-03-AG-4912"}'::jsonb,
    '2026-10-18T13:45:00Z'
),
(
    'EVT-SHP-2026-001-4',
    'SHP-2026-001',
    'in_transit',
    'Vehicle crossed Malout Corridor checkpoint (30.1915° N, 74.4989° E).',
    NULL,
    'demo_simulated',
    '{"speed_kmh": 62.0, "checkpoint": "Malout Corridor", "simulated": true}'::jsonb,
    '2026-10-18T14:30:00Z'
),
(
    'EVT-SHP-2026-001-5',
    'SHP-2026-001',
    'facility_handover',
    'Transit checkpoint reached at PSWC Container Freight Station Bathinda (FAC-PB-BTI-01).',
    'FAC-PB-BTI-01',
    'demo_simulated',
    '{"hub": "Bathinda Transit Hub", "simulated": true}'::jsonb,
    '2026-10-18T15:30:00Z'
),
(
    'EVT-SHP-2026-002-1',
    'SHP-2026-002',
    'shipment_created',
    'Shipment batch created for 600 crates of Guava from Fazilka warehouse corridor to Ludhiana Agro Cold Chain.',
    'FAC-PB-FAZ-01',
    'system_event',
    '{"produce_type": "Guava", "quantity_crates": 600}'::jsonb,
    '2026-10-18T09:30:00Z'
),
(
    'EVT-SHP-2026-002-2',
    'SHP-2026-002',
    'shipment_dispatched',
    'Dispatched onto Muktsar-Kotkapura transit corridor.',
    'FAC-PB-FAZ-01',
    'manual_operator',
    '{"vehicle": "PB-05-AB-7811"}'::jsonb,
    '2026-10-18T13:45:00Z'
),
(
    'EVT-SHP-2026-003-1',
    'SHP-2026-003',
    'shipment_created',
    'Shipment batch created for 450 crates of Guava from Fazilka to Amritsar Fruit & Produce Mandi Yard.',
    'FAC-PB-FAZ-01',
    'system_event',
    '{"produce_type": "Guava", "quantity_crates": 450}'::jsonb,
    '2026-10-21T06:19:49Z'
),
(
    'EVT-SHP-2026-003-2',
    'SHP-2026-003',
    'shipment_dispatched',
    'Dispatched via Firozpur corridor to Bhagtanwala APMC Yard, Amritsar.',
    'FAC-PB-FAZ-01',
    'manual_operator',
    '{"vehicle": "PB-02-CD-1190"}'::jsonb,
    '2026-10-21T08:00:00Z'
),
(
    'EVT-SHP-2026-003-3',
    'SHP-2026-003',
    'arrival_recorded',
    'Arrival recorded at Bhagtanwala APMC Fruit & Produce Mandi Yard, Amritsar.',
    'FAC-PB-ASR-01',
    'manual_operator',
    '{"gate_entry": "Gate 2 (Tarn Taran Road)"}'::jsonb,
    '2026-10-22T13:00:00Z'
),
(
    'EVT-SHP-2026-003-4',
    'SHP-2026-003',
    'delivery_completed',
    'Produce physical handover and mandi yard intake inspection completed for wholesale auction.',
    'FAC-PB-ASR-01',
    'manual_operator',
    '{"crates_received": 450, "condition": "good"}'::jsonb,
    '2026-10-22T13:31:02Z'
)
ON CONFLICT (id) DO NOTHING;
