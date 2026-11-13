# AgriChain AI — System Architecture & Data Flow

## 1. System Overview

**AgriChain AI** is an intelligent agricultural exchange and cold-chain integrity platform. It bridges harvest-level quality inspection with real-time transit logistics, cold-storage facility matching, and perishable goods market operations across northern Indian agricultural corridors (Punjab, Haryana, Rajasthan, and Uttar Pradesh).

```mermaid
flowchart TD
    subgraph Clients["Presentation Layer"]
        WEB["Next.js 14 Web Application<br/>(Dashboard, Simulation Studio, Map)"]
        MOB["Flutter Mobile App<br/>(Farmer Intake & Transit Tracking)"]
    end

    subgraph API_GW["FastAPI Service Layer (:8000)"]
        AUTH["Role-Based Access Control<br/>(Farmer, Dealer, Buyer, Logistics, Admin)"]
        CNN_ROUTER["Produce Inspection Router<br/>(/api/v1/cnn)"]
        SHIP_ROUTER["Shipment & Logistics Router<br/>(/api/v1/shipments)"]
        SIM_ROUTER["Simulation & Geocoding Router<br/>(/api/v1/simulations)"]
        INV_ROUTER["Farmer Inventory Router<br/>(/api/v1/inventory)"]
        WS_HUB["WebSocket Real-Time Gateway<br/>(/api/v1/ws/shipments)"]
    end

    subgraph CoreServices["Application Services Engine"]
        ROUTING["Routing Service<br/>(OSRM / Indian Highway Corridors)"]
        GEO["Geocoding Service<br/>(Mandi & Facility Knowledge Base)"]
        SIM_ENG["Simulation Engine<br/>(Polyline Interpolation & Traversal)"]
        RISK_ENG["Thermal Risk Estimator<br/>(Cold-Chain Bounded Rules & LSTM Buffer)"]
    end

    subgraph ML_Subsystem["Machine Learning Inference (CUDA/PyTorch)"]
        IDENTIFIER["Fruit Identifier<br/>(MobileNetV3-Large, 100% Top-1)"]
        GUAVA_CNN["Guava Maturity Classifier<br/>(ResNet18, 97.4% Accuracy)"]
        BANANA_CNN["Banana Ripeness Classifier<br/>(ResNet18, 98.1% Accuracy)"]
        APPLE_YOLO["Apple Damage Detector<br/>(YOLOv8n Object Detector)"]
    end

    subgraph PersistenceLayer["Storage & State Ledger"]
        REPO["ShipmentRepository<br/>(Atomic JSON State Ledger / PostGIS Compatible)"]
        POSTGIS[("PostgreSQL 16 / PostGIS 3.4<br/>(Spatial Geometries & Relational Schema)")]
    end

    WEB <-->|REST & WebSocket| API_GW
    MOB <-->|REST API| API_GW
    API_GW --> CoreServices
    CNN_ROUTER --> ML_Subsystem
    SIM_ROUTER --> SIM_ENG
    SIM_ENG --> ROUTING
    SIM_ENG --> RISK_ENG
    SIM_ENG --> WS_HUB
    SHIP_ROUTER --> REPO
    INV_ROUTER --> REPO
    REPO -.->|Migration Ready| POSTGIS
```

---

## 2. Core Architectural Components

### 2.1 Presentation Layer (`apps/web` & `apps/mobile`)
- **Next.js 14 Web Portal**: App Router (`/app/dashboard`, `/app/layout`), Tailwind CSS, Leaflet (`TrackingMapClient`), dynamic simulation HUD, and real-time WebSocket state management.
- **Flutter Mobile App** (`apps/mobile`): Android/iOS client scaffold for field produce photography, farmer lot creation, and GPS transponder tracking.

### 2.2 Backend Service Gateway (`backend/app`)
- **FastAPI Framework**: Modular RESTful routing with asynchronous WebSocket event broadcaster.
- **Role-Based Access Control**: Strict multi-role interface segregation across 5 primary stakeholders:
  - **Farmer**: Harvest lot inspection, warehouse intake suitability, stock management.
  - **Dealer**: Mandi intake lots, storage suitability verification, wholesale auctions.
  - **Buyer**: B2B produce marketplace, freshness verification, order lifecycle.
  - **Logistics**: Corridor route planning, GPS telemetry, live reefer tracking.
  - **Admin**: System telemetry, model registry, CUDA status, audit ledger.

### 2.3 Deep Learning Produce Inspection (`ml/`)
- **Zero-Guesswork Fruit Identification**: Automatic fruit categorization using MobileNetV3-Large before routing to crop-specific models.
- **Guava ResNet18**: 3-class maturity taxonomy (`Green`, `Mature Green`, `Ripe`).
- **Banana ResNet18**: 4-class ripeness taxonomy (`Underripe`, `Barely Ripe`, `Ripe`, `Overripe`).
- **Apple YOLOv8n**: Bounding-box detection for surface defects and scab lesions.

### 2.4 Geospatial & Simulation Engine
- **OSRM Driving Engine**: Real-road highway driving distance and vertex geometry calculation across northern Indian transit routes (NH-7, NH-9, NH-44, NH-52).
- **Polyline Interpolation**: Strict mathematical vehicle progression along highway polylines. Clamped strictly between route start `coords[0]` and destination `coords[-1]`.
- **Session Isolation**: Every simulation session is strictly isolated by `shipment_id`.
- **Reefer Thermal Window**: Cold-chain monitoring enforcing crop-specific temperature ranges (Guava: 4°C – 8°C; Banana: 13°C – 15°C).

### 2.5 Persistence Strategy
- **Authoritative JSON State Ledger** (`backend/app/db/.persisted_session.json`): Provides high-speed, zero-dependency local development persistence that survives backend restarts.
- **PostgreSQL / PostGIS Relational Database**: Migration scripts (`database/migrations/001_initial_postgis_schema.sql` through `005_simulation_sessions_and_telemetry.sql`) ready for full PostGIS deployment.

