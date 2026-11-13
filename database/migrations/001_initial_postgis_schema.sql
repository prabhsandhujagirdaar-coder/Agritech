-- ==============================================================================
-- AgriChain AI — Migration 001: Initial PostgreSQL / PostGIS Schema
-- ==============================================================================
-- Description:
-- Creates core tables for cold-chain logistics persistence:
-- 1. shipments: produce batch identities, status, physical attributes and timestamps.
-- 2. telemetry_logs: sensor readings (temp, humidity, sensor_id) with shipment FK.
-- 3. geo_waypoints: geospatial route points with PostGIS geometry(Point, 4326)
--    and GiST spatial index. Free-text locations are stored in telemetry_logs
--    without fabricating GPS coordinates.
-- ==============================================================================

-- 1. Enable Spatial Extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Shipments Table
CREATE TABLE IF NOT EXISTS shipments (
    id VARCHAR(64) PRIMARY KEY,
    produce_type VARCHAR(100) NOT NULL DEFAULT 'Kinnow Mandarin',
    produce VARCHAR(100) NOT NULL DEFAULT 'Kinnow Mandarin',
    origin VARCHAR(255) NOT NULL,
    destination VARCHAR(255) NOT NULL,
    quantity NUMERIC(10, 2) NOT NULL CHECK (quantity >= 0),
    quantity_crates INTEGER NOT NULL CHECK (quantity_crates >= 0),
    status VARCHAR(50) NOT NULL DEFAULT 'created' CHECK (status IN ('created', 'in_transit', 'delivered', 'delayed', 'quarantined')),
    temperature_c NUMERIC(5, 2),
    humidity_pct NUMERIC(5, 2) CHECK (humidity_pct >= 0 AND humidity_pct <= 100),
    risk_index NUMERIC(5, 2) DEFAULT 0.0 CHECK (risk_index >= 0 AND risk_index <= 100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Shipments Indexes
CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(status);
CREATE INDEX IF NOT EXISTS idx_shipments_created_at ON shipments(created_at);
CREATE INDEX IF NOT EXISTS idx_shipments_origin ON shipments(origin);
CREATE INDEX IF NOT EXISTS idx_shipments_destination ON shipments(destination);

-- 3. Telemetry Logs Table
CREATE TABLE IF NOT EXISTS telemetry_logs (
    id VARCHAR(64) PRIMARY KEY,
    shipment_id VARCHAR(64) NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    temperature NUMERIC(5, 2) NOT NULL,
    humidity NUMERIC(5, 2) NOT NULL CHECK (humidity >= 0 AND humidity <= 100),
    sensor_id VARCHAR(64) NOT NULL DEFAULT 'SNS-COLD-01',
    location VARCHAR(255) DEFAULT '',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Telemetry Logs Indexes
CREATE INDEX IF NOT EXISTS idx_telemetry_shipment_id ON telemetry_logs(shipment_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_telemetry_sensor_id ON telemetry_logs(sensor_id);

-- 4. Geospatial Waypoints Table (PostGIS SRID 4326)
-- Only populated when actual latitude & longitude coordinates are verified.
-- Free-text descriptions are NEVER converted into fabricated coordinates.
CREATE TABLE IF NOT EXISTS geo_waypoints (
    id VARCHAR(64) PRIMARY KEY,
    shipment_id VARCHAR(64) NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    coordinates geometry(Point, 4326) NOT NULL,
    altitude_m NUMERIC(7, 2),
    speed_kmh NUMERIC(5, 2) CHECK (speed_kmh >= 0),
    heading_deg NUMERIC(5, 2) CHECK (heading_deg >= 0 AND heading_deg <= 360),
    location_metadata JSONB DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- PostGIS GiST Spatial Index
CREATE INDEX IF NOT EXISTS idx_geo_waypoints_coords ON geo_waypoints USING GIST (coordinates);
CREATE INDEX IF NOT EXISTS idx_geo_waypoints_shipment ON geo_waypoints(shipment_id);
CREATE INDEX IF NOT EXISTS idx_geo_waypoints_recorded_at ON geo_waypoints(recorded_at);

-- 5. Seed Data for Punjab Kinnow Corridors
INSERT INTO shipments (
    id, produce_type, produce, origin, destination, quantity, quantity_crates,
    status, temperature_c, humidity_pct, risk_index, created_at, last_update
) VALUES
(
    'SHP-2026-001', 'Kinnow Mandarin', 'Kinnow Mandarin',
    'Abohar Packhouse, Punjab', 'Azadpur Mandi, Delhi',
    450.00, 450, 'in_transit', 6.20, 88.00, 18.50,
    '2026-10-18 10:00:00+00', '2026-10-18 14:00:00+00'
),
(
    'SHP-2026-002', 'Kinnow Mandarin', 'Kinnow Mandarin',
    'Fazilka Orchard Belt, Punjab', 'Vashi APMC Market, Navi Mumbai',
    600.00, 600, 'in_transit', 7.10, 86.50, 24.00,
    '2026-10-18 09:30:00+00', '2026-10-18 13:45:00+00'
)
ON CONFLICT (id) DO NOTHING;

-- Seed Telemetry Logs
INSERT INTO telemetry_logs (
    id, shipment_id, temperature, humidity, sensor_id, location, timestamp
) VALUES
(
    'TEL-001-1', 'SHP-2026-001', 6.20, 88.00, 'SNS-COLD-01',
    'Abohar, Punjab (30.1453° N, 74.1994° E)', '2026-10-18 14:00:00+00'
),
(
    'TEL-001-2', 'SHP-2026-001', 6.50, 87.50, 'SNS-COLD-01',
    'Malout Corridor, Punjab (30.1915° N, 74.4989° E)', '2026-10-18 14:30:00+00'
),
(
    'TEL-002-1', 'SHP-2026-002', 7.10, 86.50, 'SNS-COLD-02',
    'Fazilka Bypass, Punjab (30.4037° N, 74.0254° E)', '2026-10-18 13:45:00+00'
)
ON CONFLICT (id) DO NOTHING;

-- Seed Verified PostGIS Waypoints (Longitude, Latitude in SRID 4326)
INSERT INTO geo_waypoints (
    id, shipment_id, coordinates, altitude_m, speed_kmh, heading_deg, location_metadata, recorded_at
) VALUES
(
    'WAY-001-1', 'SHP-2026-001',
    ST_SetSRID(ST_MakePoint(74.1994, 30.1453), 4326),
    186.00, 45.00, 85.00,
    '{"hub": "Abohar Packhouse", "state": "Punjab"}'::jsonb,
    '2026-10-18 14:00:00+00'
),
(
    'WAY-001-2', 'SHP-2026-001',
    ST_SetSRID(ST_MakePoint(74.4989, 30.1915), 4326),
    192.00, 62.00, 78.00,
    '{"corridor": "Malout Corridor", "state": "Punjab"}'::jsonb,
    '2026-10-18 14:30:00+00'
),
(
    'WAY-002-1', 'SHP-2026-002',
    ST_SetSRID(ST_MakePoint(74.0254, 30.4037), 4326),
    178.00, 52.00, 195.00,
    '{"hub": "Fazilka Bypass", "state": "Punjab"}'::jsonb,
    '2026-10-18 13:45:00+00'
)
ON CONFLICT (id) DO NOTHING;
