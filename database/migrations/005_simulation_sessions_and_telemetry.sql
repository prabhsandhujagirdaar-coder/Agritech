-- ==============================================================================
-- AgriChain AI — Migration 005: Dynamic Real-Road Vehicle Simulation & Telemetry Schema
-- ==============================================================================
-- Description:
-- 1. Creates simulation_sessions table for tracking real-road vehicle movement sessions.
-- 2. Creates simulation_telemetry table for distance-indexed sensor readings, LSTM risk evaluations,
--    and synthetic telemetry tagging.
-- 3. Enables PostGIS SRID 4326 geometry columns for LineString routes and Point fixes.
--
-- Safety & Idempotency:
-- - Uses IF NOT EXISTS for all table, column, and index definitions.
-- - Safe to execute multiple times without data corruption.
-- ==============================================================================

-- 1. Create Simulation Sessions Table
CREATE TABLE IF NOT EXISTS simulation_sessions (
    id VARCHAR(64) PRIMARY KEY,
    shipment_id VARCHAR(64) REFERENCES shipments(id) ON DELETE SET NULL,
    origin_name VARCHAR(255) NOT NULL,
    origin_lat DOUBLE PRECISION NOT NULL,
    origin_lon DOUBLE PRECISION NOT NULL,
    destination_name VARCHAR(255) NOT NULL,
    destination_lat DOUBLE PRECISION NOT NULL,
    destination_lon DOUBLE PRECISION NOT NULL,
    route_geojson JSONB NOT NULL,
    total_distance_km DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    estimated_duration_s DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    current_distance_km DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    current_lat DOUBLE PRECISION NOT NULL,
    current_lon DOUBLE PRECISION NOT NULL,
    current_heading_deg DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    current_speed_kmh DOUBLE PRECISION NOT NULL DEFAULT 50.0,
    speed_multiplier DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    status VARCHAR(40) NOT NULL DEFAULT 'CREATED',
    scenario VARCHAR(60) NOT NULL DEFAULT 'normal',
    step_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Spatial and relational indexes for simulation_sessions
CREATE INDEX IF NOT EXISTS idx_sim_sessions_shipment_id ON simulation_sessions(shipment_id);
CREATE INDEX IF NOT EXISTS idx_sim_sessions_status ON simulation_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sim_sessions_created_at ON simulation_sessions(created_at);

-- Optional PostGIS geometry column if PostGIS extension is loaded
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'simulation_sessions' AND column_name = 'route_geom'
        ) THEN
            ALTER TABLE simulation_sessions ADD COLUMN route_geom GEOMETRY(LineString, 4326);
            CREATE INDEX IF NOT EXISTS idx_sim_sessions_route_geom ON simulation_sessions USING GIST(route_geom);
        END IF;
    END IF;
END $$;


-- 2. Create Simulation Telemetry Table
CREATE TABLE IF NOT EXISTS simulation_telemetry (
    id VARCHAR(64) PRIMARY KEY,
    simulation_id VARCHAR(64) NOT NULL REFERENCES simulation_sessions(id) ON DELETE CASCADE,
    shipment_id VARCHAR(64) REFERENCES shipments(id) ON DELETE SET NULL,
    sequence_step INT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    heading_deg DOUBLE PRECISION DEFAULT 0.0,
    speed_kmh DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    distance_travelled_km DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    distance_remaining_km DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    temperature_c DOUBLE PRECISION NOT NULL,
    humidity_pct DOUBLE PRECISION NOT NULL,
    delay_minutes INT NOT NULL DEFAULT 0,
    risk_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    predicted_arrival_risk DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    alert BOOLEAN NOT NULL DEFAULT FALSE,
    scenario VARCHAR(60) NOT NULL DEFAULT 'normal',
    data_source VARCHAR(40) NOT NULL DEFAULT 'simulation',
    sensor_id VARCHAR(60) NOT NULL DEFAULT 'SNS-SIM-DEMO',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for time-series queries and simulation telemetry retrieval
CREATE INDEX IF NOT EXISTS idx_sim_telemetry_sim_id ON simulation_telemetry(simulation_id);
CREATE INDEX IF NOT EXISTS idx_sim_telemetry_shipment_id ON simulation_telemetry(shipment_id);
CREATE INDEX IF NOT EXISTS idx_sim_telemetry_step ON simulation_telemetry(simulation_id, sequence_step);
CREATE INDEX IF NOT EXISTS idx_sim_telemetry_timestamp ON simulation_telemetry(timestamp);

-- Optional PostGIS point geometry for simulation fixes
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'simulation_telemetry' AND column_name = 'coordinates'
        ) THEN
            ALTER TABLE simulation_telemetry ADD COLUMN coordinates GEOMETRY(Point, 4326);
            CREATE INDEX IF NOT EXISTS idx_sim_telemetry_coords ON simulation_telemetry USING GIST(coordinates);
        END IF;
    END IF;
END $$;

