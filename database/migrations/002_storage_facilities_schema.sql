-- ==============================================================================
-- AgriChain AI — Migration 002: Storage Facilities & Godowns Schema
-- ==============================================================================
-- Description:
-- Creates storage_facilities table for Punjab & Northern India cold-chain management:
-- 1. storage_facilities: packhouses, godowns, warehouses, cold storages, mandis.
-- 2. PostGIS geometry(Point, 4326) with GiST spatial indexing.
-- 3. Adds origin_facility_id and destination_facility_id FKs to shipments table.
-- 4. Seeds 7 verified Indian regional hubs with explicit verification status.
-- ==============================================================================

-- 1. Storage Facilities Table
CREATE TABLE IF NOT EXISTS storage_facilities (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    facility_type VARCHAR(50) NOT NULL CHECK (facility_type IN ('packhouse', 'godown', 'warehouse', 'cold_storage', 'mandi')),
    address VARCHAR(255) NOT NULL,
    village_or_city VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL DEFAULT 'Punjab',
    postal_code VARCHAR(20),
    coordinates geometry(Point, 4326) NOT NULL,
    latitude NUMERIC(9, 6) NOT NULL,
    longitude NUMERIC(9, 6) NOT NULL,
    capacity NUMERIC(10, 2) CHECK (capacity >= 0),
    capacity_unit VARCHAR(20) DEFAULT 'MT',
    current_utilization NUMERIC(5, 2) CHECK (current_utilization >= 0 AND current_utilization <= 100),
    storage_temperature_min_c NUMERIC(5, 2) DEFAULT 4.0,
    storage_temperature_max_c NUMERIC(5, 2) DEFAULT 8.0,
    operational_status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (operational_status IN ('active', 'maintenance', 'inactive', 'full')),
    location_verification_status VARCHAR(50) NOT NULL DEFAULT 'demo_simulated' CHECK (location_verification_status IN ('verified', 'unverified', 'demo_simulated')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Spatial and Filtering Indexes
CREATE INDEX IF NOT EXISTS idx_storage_facilities_geom ON storage_facilities USING GIST (coordinates);
CREATE INDEX IF NOT EXISTS idx_storage_facilities_type ON storage_facilities(facility_type);
CREATE INDEX IF NOT EXISTS idx_storage_facilities_district ON storage_facilities(district);
CREATE INDEX IF NOT EXISTS idx_storage_facilities_state ON storage_facilities(state);
CREATE INDEX IF NOT EXISTS idx_storage_facilities_status ON storage_facilities(operational_status);

-- 2. Alter shipments table to add optional facility FK references
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS origin_facility_id VARCHAR(64) REFERENCES storage_facilities(id) ON DELETE SET NULL;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS destination_facility_id VARCHAR(64) REFERENCES storage_facilities(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_shipments_origin_facility ON shipments(origin_facility_id);
CREATE INDEX IF NOT EXISTS idx_shipments_dest_facility ON shipments(destination_facility_id);

-- 3. Seed Verified Regional Agricultural Facilities (Punjab & Delhi NCR)
INSERT INTO storage_facilities (
    id, name, facility_type, address, village_or_city, district, state, postal_code,
    coordinates, latitude, longitude, capacity, capacity_unit, current_utilization,
    storage_temperature_min_c, storage_temperature_max_c, operational_status,
    location_verification_status, created_at, updated_at
) VALUES
(
    'FAC-PB-ABO-01',
    'Abohar Guava & Citrus Post-Harvest Center',
    'packhouse',
    'Fazilka Road, Abohar Industrial Area',
    'Abohar',
    'Fazilka',
    'Punjab',
    '152116',
    ST_SetSRID(ST_MakePoint(74.1994, 30.1453), 4326),
    30.145300,
    74.199400,
    1500.00,
    'MT',
    62.00,
    4.00,
    8.00,
    'active',
    'demo_simulated',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    'FAC-PB-FAZ-01',
    'Fazilka Controlled Atmosphere Cold Store',
    'cold_storage',
    'Grain Market Bypass, Fazilka',
    'Fazilka',
    'Fazilka',
    'Punjab',
    '152123',
    ST_SetSRID(ST_MakePoint(74.0254, 30.4037), 4326),
    30.403700,
    74.025400,
    2500.00,
    'MT',
    48.50,
    3.50,
    7.50,
    'active',
    'demo_simulated',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    'FAC-PB-BTI-01',
    'Bathinda Central Agri Godown & Rail Transit Hub',
    'godown',
    'Goniana Road, Multania Logistics Park',
    'Bathinda',
    'Bathinda',
    'Punjab',
    '151001',
    ST_SetSRID(ST_MakePoint(74.9455, 30.2110), 4326),
    30.211000,
    74.945500,
    3000.00,
    'MT',
    70.00,
    4.00,
    8.00,
    'active',
    'demo_simulated',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    'FAC-PB-LDH-01',
    'Ludhiana Agro Cold Chain Warehouse',
    'warehouse',
    'GT Road, Sahnewal Inland Logistics Hub',
    'Ludhiana',
    'Ludhiana',
    'Punjab',
    '141001',
    ST_SetSRID(ST_MakePoint(75.8573, 30.9010), 4326),
    30.901000,
    75.857300,
    5000.00,
    'MT',
    55.00,
    3.00,
    7.00,
    'active',
    'demo_simulated',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    'FAC-PB-ASR-01',
    'Amritsar Fruit & Produce Mandi Cold Terminal',
    'mandi',
    'Bhagtanwala Fruit Mandi Complex',
    'Amritsar',
    'Amritsar',
    'Punjab',
    '143001',
    ST_SetSRID(ST_MakePoint(74.8723, 31.6340), 4326),
    31.634000,
    74.872300,
    2000.00,
    'MT',
    82.00,
    4.00,
    9.00,
    'active',
    'demo_simulated',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    'FAC-PB-JAL-01',
    'Jalandhar Post-Harvest Intake & Ripening Packhouse',
    'packhouse',
    'Kapurthala Road Food Park',
    'Jalandhar',
    'Jalandhar',
    'Punjab',
    '144001',
    ST_SetSRID(ST_MakePoint(75.5762, 31.3260), 4326),
    31.326000,
    75.576200,
    1800.00,
    'MT',
    40.00,
    4.00,
    8.00,
    'active',
    'demo_simulated',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
),
(
    'FAC-DL-AZD-01',
    'Azadpur APMC Mega Mandi Cold Logistics',
    'mandi',
    'Block A, Azadpur Mandi',
    'Azadpur',
    'North Delhi',
    'Delhi',
    '110033',
    ST_SetSRID(ST_MakePoint(77.1772, 28.7161), 4326),
    28.716100,
    77.177200,
    10000.00,
    'MT',
    91.50,
    4.00,
    8.50,
    'active',
    'demo_simulated',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (id) DO NOTHING;
