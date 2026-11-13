# AgriChain AI — Phase Enhancement Report: Simulation Map, Farmer Inventory & Map Layout

**Date:** November 3, 2026  
**Auditor:** Lead Full-Stack & Machine Learning Systems Architect  
**Project:** AgriChain AI — Predictive Cold-Chain Agritech Exchange  
**Status:** **PASSED & VERIFIED (30/30 Test Suites Passing, Clean Build)**

---

## 1. Executive Summary

This enhancement phase implemented three targeted requirements without disturbing existing architecture, breaking APIs, or altering frozen machine learning weights:

1. **Feature 1 — Dynamic Map Marker Visibility During Simulation**:
   - In **Normal Mode**: Full PAGREXCO/PSWC/NHB storage godowns, cold chains, and active shipments are displayed with interactive popups and source verification badges.
   - In **Active Simulation Mode** (`RUNNING` or `PAUSED`): All unrelated storage godown and shipment markers are dynamically hidden. The map displays **exactly two location markers**: Point A (Simulation Origin) and Point B (Simulation Destination) with high-contrast emerald and crimson badges, coordinates, and origin/destination labels, alongside the animated virtual refrigerated truck with heading rotation and the road route polyline.
   - In **Simulation Lifecycle**: Toggling between pause and resume maintains the dual endpoint markers. Stopping, resetting, or completing the simulation automatically restores the normal facility and shipment markers. Stale layers and duplicate markers are prevented via clean Leaflet layer group resets.

2. **Feature 2 — Farmer Stock & Inventory Management**:
   - **Data Model**: Implemented `id`, `farmer_id`, `crop_type`, `crate_quantity`, `price_per_crate`, `total_stock_value`, `description`, `harvest_date`, `location`, `status`, `created_at`, `updated_at`.
   - **Server-Authoritative Calculations**: Total valuation (`total_stock_value = round(crate_quantity * price_per_crate, 2)`) is strictly computed on the backend; client-supplied tampering is rejected.
   - **Validation**: Enforced positive integers for `crate_quantity` (> 0) and positive floats for `price_per_crate` (> 0.0). Invalid crops or negative numbers are rejected with HTTP 422 `ValidationError`.
   - **Separation of Concerns**: Explicitly separated commercial trading from AI inspection capability across the 5 crops:
     - **Guava**: ResNet18 v2.0.0 (classification active)
     - **Banana**: ResNet18 v1.0.0 (classification active)
     - **Apple**: YOLOv8n (detection only under CC BY-NC 4.0; classification unavailable)
     - **Mango**: Commercial marketplace trading supported (no AI model available)
     - **Kinnow**: Commercial listing supported (no AI model available)
   - **Strict Role-Based Isolation**: Farmers manage only their own stock; unauthorized modification or deletion attempts by another farmer return **HTTP 403 Forbidden**. Admins maintain oversight.
   - **UI Component**: Built `FarmerInventoryManager.js` with responsive summary metric cards, interactive Add Stock modal, real-time estimated valuation previews, and full CRUD management embedded in the Farmer workspace (`activeTab === "farmer"`).

3. **Feature 3 — Increased Tracking Map Height**:
   - Expanded the tracking map container from `h-[420px]` to responsive Tailwind classes `h-[580px] sm:h-[620px] md:h-[680px] lg:h-[720px]`.
   - Updated map container and loading fallback targets to `min-h-[500px]`.
   - Preserved all vehicle animations, HUD telemetry overlays, Leaflet controls, and responsive responsiveness without layout clipping.

---

## 2. Test & Verification Matrix

| Test Suite | Scope | Result | Details |
| :--- | :--- | :---: | :--- |
| **TS-01** | Crop Catalogue & AI Separation | **PASS** | 5 crops verified with distinct AI classification, detection-only, and trading-only tiers |
| **TS-02** | Input Validation Constraints | **PASS** | Rejection of 0 crates, negative crates, 0 price, negative price, and uncatalogued crops |
| **TS-03** | Server-Authoritative Stock Valuation | **PASS** | Server calculates `crate_quantity * price_per_crate` with floating-point round precision |
| **TS-04** | Role Ownership & Isolation | **PASS** | Farmer B blocked with HTTP 403 on edit/delete; Farmer A edits own stock; Admin deletes |
| **TS-05** | Storage Ledger Persistence | **PASS** | Records persist across cold repository reload and atomic `.json` ledger commits |
| **TS-06** | Dynamic Marker Toggle (Feature 1) | **PASS** | `isSimActive` hides godowns and renders only Point A, Point B, vehicle marker & route |
| **TS-07** | Map Layout & Height (Feature 3) | **PASS** | `ShipmentsTracking.js` expanded to `lg:h-[720px]`; `TrackingMap.js` `min-h-[500px]` |
| **TS-08** | Next.js API Proxy Routes | **PASS** | `GET/POST /api/inventory`, `GET/PUT/DELETE /api/inventory/[id]`, `GET /api/inventory/crops` |
| **TS-09** | Next.js Production Build | **PASS** | `next build` compiled successfully (16/16 pages static + dynamic API routes) |
| **TS-10** | Frontend Unit Tests | **PASS** | All constants, geospatial boundaries, roleConfig, and Phase 13.6 tests passed (0 errors) |

---

## 3. Server Startup Instructions

The port conflict (`ERR_CONNECTION_REFUSED` / `WinError 10048`) occurred because ports 8000 and 3000 were previously occupied by killed processes. Both ports are now completely free and the full production build has been completed.

To run both servers in your terminal:

### Terminal 1: Backend (FastAPI on Port 8000)
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Terminal 2: Frontend (Next.js on Port 3000)
```powershell
npm --prefix apps/web run start -- -p 3000
```
*(Or use `npm --prefix apps/web run dev` for developer mode).*

Once started, open **`http://localhost:3000`** in your browser to access the application.

