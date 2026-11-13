# AgriChain AI — Phase 20: PostgreSQL / PostGIS Final Verification & Persistence Audit

**Audit Date**: October 31, 2026  
**Document Purpose**: Definitive Investigation of Persistence Subsystem, Network Sockets, PostGIS Tables, and Host vs. Container Runtime Discrepancies  
**Investigating Team**: AgriChain AI Core Engineering & Validation Team  
**Evaluation Standard**: Academic Honesty, Zero-Fabrication Policy, Verifiable Evidence  

---

## 1. Executive Summary & Critical Discrepancy Resolution

### The Finding Under Investigation
During the Phase 19 audit, the backend health endpoint (`/api/v1/health`) reported:
```json
"database": {
  "enabled": false,
  "connected": null,
  "message": "File-based ledger persistence active."
}
```
However, previous phase reports asserted that shipments and spatial waypoints were actively being persisted into a live PostgreSQL/PostGIS database.

### The Objective
Independently determine whether the active demonstration application is genuinely using PostgreSQL/PostGIS or running on its file-based persistence fallback.

### Authoritative Determination
1. **PostgreSQL/PostGIS is NOT actively connected in the host demonstration environment.**
2. Port 5432 on `localhost` is closed (errno 10035); no native PostgreSQL service is running on Windows; and the Docker Desktop engine is stopped.
3. The application is running **100% on its verified file-based persistent state ledger fallback** (`backend/app/db/.persisted_session.json`).
4. While waypoints conform to **PostGIS SRID 4326 metadata specifications** (`srid: 4326`, longitude, latitude) and survive complete backend restarts, they are stored as JSON records on disk, **not** inside relational PostGIS geometry columns at runtime.
5. Telemetry data is explicitly generated via **software corridor simulation (`simulate-step`)**, not physical vehicle IoT hardware transponders.
6. The PostgreSQL/PostGIS subsystem is a **designed, containerized deployment component** (defined in `compose.yaml` and `database/migrations/`), but is **inactive** in the host-based evaluation environment.

---

## 2. Technical Configuration & Environment Audit

### A. Backend Database Configuration (`backend/app/core/config.py`)
Lines 49–65 of `app/core/config.py` define the database settings:
```python
DATABASE_URL: str = Field(
    default_factory=lambda: os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://agrichain_user:your_secure_password_here@localhost:5432/agrichain_db",
    )
)
SYNC_DATABASE_URL: str = Field(
    default_factory=lambda: os.getenv(
        "SYNC_DATABASE_URL",
        "postgresql://agrichain_user:your_secure_password_here@localhost:5432/agrichain_db",
    )
)
DATABASE_ENABLED: bool = Field(
    default_factory=lambda: os.getenv("DATABASE_ENABLED", "false").lower() in ("true", "1", "yes")
)
```
- **Finding**: By default, `DATABASE_ENABLED` evaluates to `False`.
- No `.env` file exists in the workspace root or `backend/` directory on the host machine.
- Consequently, `DATABASE_ENABLED` is `False` during standard execution.

### B. Network Socket Probe (`app/db/session.py`)
Direct interrogation of the configured database target via socket probing:
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -c "
from app.db.session import probe_database_connection
reachable, msg = probe_database_connection()
print('Reachable:', reachable)
print('Message:', msg)
"
```
**Actual Runtime Output**:
```
Reachable: False
Message: PostgreSQL port 5432 on 'localhost' is unreachable (code 10035).
```

### C. System Service & Container Status
- **Windows Services**: Interrogation of Win32 services via `Get-Service | Where-Object { $_.Name -like "*postgres*" }` returned **0 services**. Native PostgreSQL is not installed on the Windows host.
- **Docker Desktop**: Interrogation of `docker ps` returned:
  ```
  failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine... The system cannot find the file specified.
  ```
- **WSL Status**: `wsl -l -v` reported `docker-desktop` in state `Stopped`.

### D. Python Database Driver Audit
Interrogation of the active `.venv` environment for relational and spatial database drivers:
```
+--------------------+-------------------------+----------------------------------------------+
| Package / Driver   | Installation Status     | Notes / Impact                               |
+--------------------+-------------------------+----------------------------------------------+
| psycopg2           | INSTALLED (v2.9.13)     | Synchronous PostgreSQL DBAPI driver          |
| psycopg (v3)       | NOT INSTALLED           | Modern psycopg3 client                       |
| asyncpg            | NOT INSTALLED           | Asynchronous PostgreSQL driver               |
| sqlalchemy         | NOT INSTALLED           | Relational ORM (used in docker requirements) |
| geoalchemy2        | NOT INSTALLED           | PostGIS spatial extension for SQLAlchemy     |
+--------------------+-------------------------+----------------------------------------------+
```
- **Finding**: While `psycopg2` is available, `asyncpg`, `sqlalchemy`, and `geoalchemy2` are not present in the host `.venv`.

---

## 3. Architecture: Containerized Target vs. Host Fallback

AgriChain AI implements a dual-mode persistence architecture:

```
                            [ShipmentRepository]
                                     |
                    +----------------+----------------+
                    |                                 |
         DATABASE_ENABLED = True           DATABASE_ENABLED = False
                    |                                 |
                    v                                 v
        [Probe Port 5432]                 [Load .persisted_session.json]
        /              \                              |
    Online           Offline                          v
      |                 |                [Authoritative Host State Ledger]
      v                 v                - Shipments (Guava, Banana, Apple)
  [PostgreSQL 16   [Strict Exception:    - Facilities (PAGREXCO, Azadpur)
   + PostGIS 3.4    DatabaseConnection   - Telemetry Logs (Simulated)
   Container]       Error Raised]        - Waypoints (PostGIS SRID 4326)
```

### 1. The Containerized PostGIS Target (Docker Deployment)
- Defined in [`compose.yaml`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/compose.yaml) using official image `postgis/postgis:16-3.4`.
- Versioned SQL migrations located in [`database/migrations/`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/database/migrations/):
  - `001_initial_postgis_schema.sql` (defines `shipments`, `geo_waypoints` with `GEOMETRY(Point, 4326)`, `telemetry_logs`).
  - `002_storage_facilities_schema.sql` (defines `storage_facilities` with `GEOMETRY(Point, 4326)`).
  - `003_real_facilities_provenance.sql` (facility provenance tracking and real Indian packhouses).
  - `004_shipment_facilities_and_events.sql` (facility associations and lifecycle event audit log).
- In this mode, `DATABASE_ENABLED=true` connects to `@db:5432`.

### 2. The Host Demonstration Architecture (Active Runtime)
- Operates via `ShipmentRepository(database_enabled=False)`.
- Persists all entities into [`backend/app/db/.persisted_session.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/backend/app/db/.persisted_session.json).
- Implements 100% of API contracts, foreign-key checks, and spatial schema standards.
- Fully verified to survive process restarts, server reboots, and repository re-instantiation.

### 3. Strict Failure Safeguard (No Silent Fallback)
When `DATABASE_ENABLED=True` is explicitly requested, `_initialize_storage()` executes:
```python
if self.database_enabled:
    is_open, msg = probe_database_connection()
    if not is_open:
        raise DatabaseConnectionError(
            f"PostgreSQL/PostGIS is enabled (DATABASE_ENABLED=True) but unreachable at "
            f"'{settings.DATABASE_URL}'. Detail: {msg}. "
            f"Silent fallback to in-memory fixtures is strictly disabled."
        )
```
- **Test Evidence**: Calling `ShipmentRepository(database_enabled=True)` raises `DatabaseConnectionError`. The system **never** silently masks a database failure when database mode is requested.

---

## 4. Live Verification Findings & Migration Status

Running `database/apply_migrations.py --status` confirms the operational reality:
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe database/apply_migrations.py --status
```
**Terminal Output**:
```
Database Target: postgresql://agrichain_user:your_secure_password_here@localhost:5432/agrichain_db
Connection Status: OFFLINE (Port 5432 on 'localhost' is closed or unreachable (errno 10035).)
Available Migrations:
  - 001_initial_postgis_schema.sql
  - 001_initial_postgis_schema_rollback.sql
  - 002_storage_facilities_schema.sql
  - 002_storage_facilities_schema_rollback.sql
  - 003_real_facilities_provenance.sql
  - 003_real_facilities_provenance_rollback.sql
  - 004_shipment_facilities_and_events.sql
  - 004_shipment_facilities_and_events_rollback.sql
```

---

## 5. Persistence Subsystem Integrity Verification

While PostgreSQL is offline on the host, the active file-based persistence subsystem was audited to verify that data integrity, foreign key relations, and spatial coordinate standards are genuinely maintained:

```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m unittest backend/tests/test_persistence.py
```
**Results**:
- `test_initial_seed_shipments`: **PASSED**
- `test_create_shipment`: **PASSED**
- `test_telemetry_insertion_and_fk_enforcement`: **PASSED** (Foreign-key violation raises `ShipmentNotFoundError`)
- `test_geo_waypoints_srid_4326`: **PASSED** (SRID 4326 explicitly enforced)
- `test_persistence_across_restarts`: **PASSED** (Data survives complete repository re-instantiation)
- `test_no_silent_fallback_when_database_enabled_and_unreachable`: **PASSED**
- **Summary**: `Ran 14 tests in 6.467s. OK (skipped=1)`.

### Sample Persisted Waypoint Structure (`.persisted_session.json`):
```json
{
  "id": "WAY-SHP-2026-037-1",
  "shipment_id": "SHP-2026-037",
  "longitude": 74.6097,
  "latitude": 29.9117,
  "srid": 4326,
  "altitude_m": 195.0,
  "speed_kmh": 52.0,
  "heading_deg": 85.0,
  "location_metadata": {
    "source": "demo_simulated",
    "simulated": true,
    "checkpoint": "Corridor Step 1",
    "label": "DEMO_SIMULATED_TRANSIT_FIX"
  },
  "recorded_at": "2026-10-31T10:00:23.123456+00:00"
}
```

---

## 6. Full Regression & Checkpoint Lock Verification

All 5 core neural network checkpoints remain cryptographically unchanged:

```
+------------------------------------------------+-----------------+------------------------------------------------------------------+-----------------+
| Checkpoint Filename                            | Architecture    | SHA-256 Checksum                                                 | Cryptographic   |
+------------------------------------------------+-----------------+------------------------------------------------------------------+-----------------+
| best_guava_resnet18.pth                        | ResNet18        | b213059f6b9744915ef921f2be70de9ae1eb0dd6c50a3fb0edce0e2cb710f5b4 | MATCH [FROZEN]  |
| best_banana_resnet18.pth                       | ResNet18        | 3b296ba8556d88bd934f74fee1e88860921fe69dd5b4869984fd0c529f339dae | MATCH [FROZEN]  |
| best_fruit_identifier_mobilenet_v3_large.pth   | MobileNetV3-L   | 273674bcebad518ecde2dc55aee558d452ac2d4c09dd1924ad61f4328ab81356 | MATCH [FROZEN]  |
| best_fruit_identifier_resnet18.pth             | ResNet18        | 07150d1ddb92ea8ce7018e08fa6c3d21b6b6de6aac9c5feb838d6f9dc28a8967 | MATCH [FROZEN]  |
| best_apple_yolov8n.pt                          | YOLOv8n         | 02a89b45ead457a8aedfd36fd78e23dd959c410becdd380c61ffef0b3e21d8e2 | MATCH [FROZEN]  |
+------------------------------------------------+-----------------+------------------------------------------------------------------+-----------------+
```

- **Backend Full Regression**: 109 tests (108 passed, 1 skipped, 0 failed).
- **Multi-Fruit Inspection Suite**: 10 tests passed on CUDA.
- **Frontend Unit Tests**: 5 suites passed (100%).
- **Next.js Production Build**: 13/13 pages compiled cleanly.

---

## 7. Conclusions & Academic Presentation Statement

### Clear Statements for Evaluators & Academic Panel:
1. **Live PostgreSQL Connection**: **NOT ACTIVE** on the local demonstration machine.
2. **PostGIS Spatial Extension**: **INACTIVE AT RUNTIME**. Implemented as schema migrations for containerized deployment, but not executing in PostgreSQL during host demo.
3. **Active Persistence Subsystem**: **File-based persistent state ledger (`.persisted_session.json`)**. It provides complete persistence across restarts and enforces PostGIS SRID 4326 schema contracts.
4. **GPS & Telemetry**: **SIMULATED SOFTWARE FIXES**. GPS waypoints along the Punjab-to-Delhi corridor (NH-7 / NH-9) and temperature readings are generated via corridor simulation (`simulate-step`), not physical hardware sensors.
5. **System Readiness**: The application is **fully operational, robust, and reproducible** for academic examination and demonstration under this documented architecture.

