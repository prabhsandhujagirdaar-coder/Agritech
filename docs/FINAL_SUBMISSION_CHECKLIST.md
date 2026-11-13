# AgriChain AI — Final Submission Checklist & Quick Reference

**Milestone**: Phase 19 Final Submission Freeze  
**Target Deadline**: November 7, 2026  
**Status**: **VERIFIED & CERTIFIED FOR SUBMISSION**

---

## 1. Quick Startup Commands (For Evaluation Machine)

To run the application cleanly on any evaluation machine with Windows / PowerShell:

### Step 1: Open Terminal 1 — Start FastAPI Backend (Port 8000)
```powershell
# In project root:
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Verify terminal output displays:
```
INFO: Started server process
[INFO] agrichain.services.cnn: CNNService: Model loaded successfully on cuda for guava.
[INFO] agrichain.services.cnn: CNNService: Model loaded successfully on cuda for banana.
[INFO] agrichain.services.cnn: AppleDetectionService: Apple YOLOv8n detector loaded successfully from 'best_apple_yolov8n.pt'.
[INFO] agrichain.services.cnn: FruitIdentifierService: Fruit Identifier (mobilenet_v3_large) loaded successfully on cuda.
[INFO] Uvicorn running on http://127.0.0.1:8000
```

### Step 2: Open Terminal 2 — Start Next.js Frontend (Port 3000)
```powershell
# In project root:
npm --prefix apps/web run start -- -p 3000
```
Verify terminal output displays:
```
▲ Next.js 14.2.35
- Local: http://localhost:3000
✓ Ready in ~1.2s
```

### Step 3: Open Web Browser
Navigate to:
```
http://localhost:3000
```
or directly to dashboard:
```
http://localhost:3000/dashboard
```

---

## 2. Verification Checklist Matrix

| Section | Verification Item | Target Standard | Verified Result | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Environment** | Operating System | Windows 11 x86_64 | Microsoft Windows 11 Home Single Language (Build 26300) | [x] PASSED |
| **Environment** | Python Runtime | 3.10+ (Active: 3.13.7) | Python 3.13.7 (AMD64) | [x] PASSED |
| **Environment** | PyTorch & CUDA | PyTorch 2.x + CUDA 12.x | PyTorch 2.11.0+cu128 / CUDA 12.8 | [x] PASSED |
| **Environment** | GPU Accelerator | NVIDIA RTX GPU | GeForce RTX 4050 Laptop GPU (6GB) | [x] PASSED |
| **Environment** | Node.js & npm | Node.js >= 18 | Node v22.19.0 / npm 10.9.3 | [x] PASSED |
| **Checkpoints** | Guava ResNet18 | SHA-256 match `b213...f5b4` | Exact Match (42.7 MB) | [x] PASSED |
| **Checkpoints** | Banana ResNet18 | SHA-256 match `3b29...9dae` | Exact Match (42.7 MB) | [x] PASSED |
| **Checkpoints** | Stage 1 MobileNet | SHA-256 match `2736...1356` | Exact Match (16.2 MB) | [x] PASSED |
| **Checkpoints** | Stage 1 ResNet18 | SHA-256 match `0715...8967` | Exact Match (42.7 MB) | [x] PASSED |
| **Checkpoints** | Apple YOLOv8n | SHA-256 match `02a8...d8e2` | Exact Match (6.0 MB) | [x] PASSED |
| **Inference** | Guava Classification | 3 Stages (Green, Mature, Ripe)| ResNet18 -> Mature Green (81.47%) | [x] PASSED |
| **Inference** | Banana Classification| 4 Stages (Unripe..Overripe) | ResNet18 -> Ripe (89.89%) | [x] PASSED |
| **Inference** | Apple Detection | YOLOv8n bounding boxes | 2 Apples Detected (88.67% avg conf) | [x] PASSED |
| **Inference** | Apple License Notice | CC BY-NC 4.0 Non-Commercial | Displayed on UI & API Response | [x] PASSED |
| **Inference** | Mango Gated Deficit | Zero synthetic hallucination | Status: unavailable, honest reason | [x] PASSED |
| **Inference** | Stage 1 Auto Fruit ID| Confidence >= 0.80, Margin>=0.15| Identified: Guava (100% conf) | [x] PASSED |
| **Inference** | Foliage Fallback | `negative_background` trigger | `is_uncertain=True`, prompts manual | [x] PASSED |
| **UX & RBAC** | First-Time Modal | Centered, zero dashboard leak | Onboarding backdrop shields views | [x] PASSED |
| **UX & RBAC** | Farmer Workspace | Produce inspection & harvest | Strictly 3 views in sidebar | [x] PASSED |
| **UX & RBAC** | Logistics Workspace | PostGIS corridor tracking map | Strictly 2 views in sidebar | [x] PASSED |
| **UX & RBAC** | Dealer Workspace | Mandi intake & auction pool | Strictly 3 views in sidebar | [x] PASSED |
| **UX & RBAC** | Buyer Workspace | Verified B2B produce marketplace| Strictly 2 views in sidebar | [x] PASSED |
| **UX & RBAC** | Admin Workspace | CUDA hardware & model registry | Strictly 3 views in sidebar | [x] PASSED |
| **UX & RBAC** | Access Safeguard | Unauthorized tab blocked | Displays Access Restricted card | [x] PASSED |
| **UX & RBAC** | Switch Role Action | Header & sidebar controls | Instant switch & redirect to default | [x] PASSED |
| **Persistence** | PostgreSQL Runtime | Port 5432 network check | Offline (code 10035, Docker stopped) | [!] INACTIVE (HOST) |
| **Persistence** | PostGIS Extension | Containerized schema migrations| Present in migrations 001-004 | [!] INACTIVE (HOST) |
| **Persistence** | State Ledger Resiliency| Authoritative file ledger | Active (.persisted_session.json) | [x] PASSED |
| **Persistence** | PostGIS SRID 4326 | Standard coordinate metadata | 3 waypoints recorded (SRID 4326) | [x] PASSED |
| **Persistence** | Sensor Telemetry | Cold-chain temperature/humidity| 3 logs recorded (5.8°C / 86.5%, SIM)| [x] PASSED |
| **Persistence** | Restart Resilience | Ledger reload verification | 100% data intact across reload | [x] PASSED |
| **Regression** | Backend Test Suite | 109 Unit & Integration Tests | 108 Passed, 1 Skipped, 0 Failed | [x] PASSED |
| **Regression** | Frontend Unit Tests | 5 Test Suites in apps/web | All 5 Suites Passed (100%) | [x] PASSED |
| **Regression** | Next.js Build | Static page generation | 13/13 Pages compiled cleanly | [x] PASSED |

---

## 3. Demonstration Script (5-Minute Walkthrough for Panel)

### Minute 1: Introduction & Role Selection
1. Open `http://localhost:3000/dashboard`.
2. Point out that before choosing an identity, the system presents a **zero-leakage onboarding backdrop**.
3. Select the **Farmer** role card and click *"Continue to Farmer Workspace"*.

### Minute 2: Dual-Mode Produce Inspection
1. Navigate to **Produce Inspection**.
2. **Manual Mode**: Select **Guava**, browse to `ml/data/guava_classification/Local Sindhi/Mature Green/237.jpg`, and click *"Evaluate Guava Maturity"*. Show the ResNet18 output: **Mature Green (81.47%)**.
3. **Automatic Mode**: Switch toggle to *"Automatic Identification"*. Upload the specimen. Show that **MobileNetV3-Large** automatically identifies species as Guava with 100% confidence and routes it to the specialized model.
4. Demonstrate ethical gating: Switch manual selection to **Mango**. Show that the system returns an honest **Gated Deficit notice** rather than hallucinating synthetic grades.
5. Demonstrate Apple detection: Select **Apple**. Upload `ml/data/processed/apple_detection_yolo/images/test/108.jpg`. Show YOLOv8n bounding boxes and the prominent **CC BY-NC 4.0 Research Disclaimer**.

### Minute 3: Inspection-to-Shipment Association
1. In the Guava inspection result, click *"Associate with Active Harvest Dispatch"*.
2. Show that a new shipment is created linking the ResNet18 maturity verdict to packhouse origin (`FAC-PB-ABO-01`, Abohar, Punjab) and mandi destination (`FAC-DL-AZD-01`, Azadpur, Delhi).

### Minute 4: Logistics & Cold-Chain PostGIS Tracking
1. Click the top header **"Switch Role"** button, select **Logistics**, and confirm.
2. Notice the sidebar immediately eliminates farmer views and displays only **Logistics views**.
3. Open **Shipment Tracking & Map**. Show the interactive Leaflet map rendering the NH-7 / NH-9 highway corridor.
4. Point out the **Thermal Telemetry HUD** (4°C – 8°C optimal window) and click *"Simulate Transit Advance"* to watch the vehicle advance in real time with new PostGIS SRID 4326 coordinates.

### Minute 5: Mandi Dealer, B2B Marketplace & Admin Diagnostics
1. Switch role to **Dealer**: Show arrival lot intake, quality audit certificates, and Azadpur wholesale suitability.
2. Switch role to **Buyer**: Browse verified produce lots in the B2B Marketplace and place a demo order (5 crates).
3. Switch role to **Admin**: View real-time **CUDA 12.8 GPU telemetry**, VRAM utilization, loaded model registry, and API ping latency (< 10ms).
4. Direct URL Safeguard: In browser address bar, type `http://localhost:3000/dashboard?role=Farmer&tab=dealer`. Show the **Access Restricted Safeguard** card preventing unauthorized access.

---

## 4. Key File Paths

- Final Freeze Audit Script: [`scripts/verify_final_freeze.py`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/scripts/verify_final_freeze.py)
- Final Freeze Results JSON: [`ml/experiments/final_freeze_audit_results.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/experiments/final_freeze_audit_results.json)
- Final Submission Freeze Report: [`docs/FINAL_SUBMISSION_FREEZE_REPORT.md`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/docs/FINAL_SUBMISSION_FREEZE_REPORT.md)
- Final Viva Preparation Guide: [`docs/FINAL_VIVA_PREPARATION.md`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/docs/FINAL_VIVA_PREPARATION.md)
- Final Evaluation Runbook: [`docs/FINAL_DEMO_RUNBOOK.md`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/docs/FINAL_DEMO_RUNBOOK.md)
- Phase 20 Database Verification: [`docs/PHASE20_DATABASE_VERIFICATION.md`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/docs/PHASE20_DATABASE_VERIFICATION.md)
- Full Phase 19 Audit Report: [`docs/PHASE19_FINAL_SUBMISSION_REPORT.md`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/docs/PHASE19_FINAL_SUBMISSION_REPORT.md)
- Role Configuration: [`apps/web/lib/roleConfig.js`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/apps/web/lib/roleConfig.js)
- Screenshots Directory: [`docs/screenshots/phase19_final/`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/docs/screenshots/phase19_final/)

