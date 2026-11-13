# AgriChain AI — Final Academic Demonstration Runbook

**Purpose**: Exact Operational Guide, Startup Commands, Demonstration Sequence, and Troubleshooting for Academic Evaluators  
**Submission Milestone**: Final Submission Freeze  
**Target Examination Date**: November 7, 2026  
**Authoritative Environment**: Microsoft Windows 11 Home Single Language (Build 26300, x86_64) | Python 3.13.7 | PyTorch 2.11.0+cu128 | CUDA 12.8 | NVIDIA GeForce RTX 4050 Laptop GPU (6GB VRAM) | Next.js 14.2.35 | Node.js v22.19.0

---

## 1. System URLs & Port Mappings

| Service Component | Port | Network URL | Purpose & Endpoint Function |
| :--- | :---: | :--- | :--- |
| **Next.js Web Portal** | `3000` | `http://localhost:3000` | Landing Page & Stakeholder Portal |
| **Role Dashboard Shell** | `3000` | `http://localhost:3000/dashboard` | Role-partitioned workspaces & modal |
| **FastAPI Backend Server**| `8000` | `http://127.0.0.1:8000` | REST API, ML Inference & Data Services |
| **Backend API Docs (Swagger)**| `8000`| `http://127.0.0.1:8000/docs` | Interactive OpenAPI / Swagger UI |
| **Backend Health Probe** | `8000` | `http://127.0.0.1:8000/api/v1/health` | Liveness, CUDA GPU & DB Status Probe |
| **Model Registry Catalog** | `8000`| `http://127.0.0.1:8000/api/v1/cnn/registry` | Supported & Available Crop Registry |

---

## 2. Startup Instructions (Exact Terminal Commands)

Open **two separate PowerShell terminals** in the project root (`c:\Users\PrabSandhu\Documents\codes\Agritech_`):

### Terminal 1: Launch FastAPI Backend
```powershell
# Set backend directory on Python path and launch Uvicorn
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
**Expected Startup Output**:
```
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
[INFO] agrichain.services.cnn: CNNService: Model loaded successfully on cuda for guava.
[INFO] agrichain.services.cnn: CNNService: Model loaded successfully on cuda for banana.
[INFO] agrichain.services.cnn: AppleDetectionService: Apple YOLOv8n detector loaded successfully from 'best_apple_yolov8n.pt'.
[INFO] agrichain.services.cnn: FruitIdentifierService: Fruit Identifier (mobilenet_v3_large) loaded successfully on cuda.
[INFO] agrichain.api: CNN Inspection Service initialized: crop='guava', available=True, device=cuda
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Terminal 2: Launch Next.js Web Portal
```powershell
# Launch optimized Next.js production server on Port 3000
npm --prefix apps/web run start -- -p 3000
```
**Expected Startup Output**:
```
> agrichain-web@0.1.0 start
> next start -p 3000

  ▲ Next.js 14.2.35
  - Local:        http://localhost:3000

 ✓ Starting...
 ✓ Ready in 1000-1300ms
```

---

## 3. Recommended 7-Step Demonstration Sequence

### Step 1: Onboarding & Pre-Auth Shielding
1. Open browser at: `http://localhost:3000/dashboard`
2. **Key Evaluator Talking Point**:
   - Notice that before a role is selected, the application **completely unmounts** the dashboard and navigation behind a branded backdrop. No unauthorized operational views or features are exposed.
3. Observe the 5 distinct stakeholder identity cards: **Farmer**, **Logistics**, **Dealer**, **Buyer**, and **Admin**.
4. Select the **Farmer** card and click *"Continue to Farmer Workspace"*.

### Step 2: Farmer Produce Inspection (Dual-Mode AI)
1. In the **Farmer Workspace**, select **Produce Inspection** in the sidebar.
2. **Manual Mode (Guava)**:
   - Select crop: **Guava**.
   - Browse to: `ml/data/guava_classification/Local Sindhi/Mature Green/237.jpg`.
   - Click *"Evaluate Guava Maturity (ResNet18)"*.
   - View output: **Mature Green** (confidence ~81.47%, latency ~11ms on CUDA).
3. **Manual Mode (Banana)**:
   - Select crop: **Banana**.
   - Browse to: `ml/data/raw/banana/ripeness/Banana Ripeness Classification Dataset/Ripe/Cavendish_Ripe_Bottom_0009.jpg`.
   - Click *"Evaluate Banana Ripeness (ResNet18)"*.
   - View output: **Ripe** (confidence ~89.89%).
4. **Manual Mode (Apple Detection Only)**:
   - Select crop: **Apple**.
   - Browse to: `ml/data/processed/apple_detection_yolo/images/test/108.jpg`.
   - Click *"Detect Apples in Orchard Canopy (YOLOv8n)"*.
   - View output: **2 Apples Detected** (bounding boxes highlighted on image canvas).
   - Point out the prominent license notice: *"Academic / Non-Commercial Research Only (CC BY-NC 4.0)"*.
   - Note that maturity classification is intentionally `null`—it counts orchard fruit; it does not fabricate sugar brix or post-harvest ripeness.
5. **Ethical Gating (Mango Deficit)**:
   - Select crop: **Mango**.
   - Upload any image. The system returns an honest **Gated Deficit Notice**: *"Mango maturity prediction is unavailable. Awaiting validated multi-stage harvest dataset... Zero synthetic predictions."*
6. **Automatic Mode (Stage 1 MobileNetV3-Large)**:
   - Switch mode toggle to **"Automatic Identification"**.
   - Upload the guava image.
   - Point out that **MobileNetV3-Large** automatically identifies the species as **Guava (100% confidence)** and immediately routes it to the specialized Guava ResNet18 model without user intervention.
7. **Foliage / Out-of-Distribution Fallback**:
   - Upload non-fruit foliage: `ml/data/raw/fruitnet/Bad Quality_Fruits/Lime_Bad/IMG_7589.JPG`.
   - Stage 1 detects class **`negative_background`**, triggers `is_uncertain=True`, and prompts the user for manual selection.

### Step 3: Produce-to-Shipment Association
1. On the verified Guava inspection card, click *"Associate with Active Harvest Dispatch"*.
2. The system creates a real shipment entry linking:
   - Produce Type: `Guava (Mature Green)`
   - Origin: `FAC-PB-ABO-01` (Abohar Regional Packhouse, Punjab)
   - Destination: `FAC-DL-AZD-01` (Azadpur Terminal Mandi, Delhi)
   - Quality Grade: `Mature Green` (linked to ResNet18 verdict)

### Step 4: Role Switch to Logistics & PostGIS Fleet Tracking
1. In the header bar, click the prominent **"Switch Role"** button.
2. Select **Logistics** and confirm.
3. Observe that the sidebar immediately eliminates Farmer links and renders strictly **Logistics views** (*Shipment Tracking & Map*, *Storage Facility Directory*).
4. Click **Shipment Tracking & Map**:
   - View the interactive Leaflet map rendering the Punjab-to-Delhi highway corridor (NH-7 / NH-9).
   - Point out the **Thermal Telemetry HUD** (Guava target window: 4°C – 8°C; spoilage risk index < 15%).
   - Click *"Simulate Transit Advance"* (or step simulation). Watch the vehicle coordinate advance in real time, recording a new **PostGIS SRID 4326** GPS waypoint.

### Step 5: Role Switch to Dealer (Mandi Arrival & Intake)
1. Click **"Switch Role"**, select **Dealer**, and confirm.
2. Observe the **Dealer Workspace**:
   - Inbound consignments arriving at Azadpur Terminal Mandi.
   - Mandi intake quality certificates displaying the neural network inspection verdict.
   - Azadpur APMC trading suitability category (`verified_guava_trading`).

### Step 6: Role Switch to Buyer (B2B Marketplace & Purchase Orders)
1. Click **"Switch Role"**, select **Buyer**, and confirm.
2. Observe the **B2B Marketplace**:
   - Browse verified produce lots originating from Punjab packhouses.
   - Select lot `LST-GUA-001` (Guava Premium Crate, Ripe).
   - Click *"Purchase Produce Lot"* $\rightarrow$ submit demo order for 4 crates.
   - View order confirmation (`ORD-...`) with server-validated total (`INR 4,800.00`) and demo disclaimer.

### Step 7: Role Switch to Admin & Direct URL Interception
1. Click **"Switch Role"**, select **Admin**, and confirm.
2. View **System Hardware & Diagnostics**:
   - Active GPU device: `cuda` (NVIDIA GeForce RTX 4050 Laptop GPU).
   - Loaded model registry (5 checkpoints).
   - Network API latency (< 10ms).
3. **Access Restricted Safeguard Test**:
   - In the browser URL address bar, manually type:
     `http://localhost:3000/dashboard?role=Farmer&tab=dealer`
   - Observe that the dealer dashboard is blocked from mounting.
   - Displays the animated **Access Restricted Safeguard Card** with one-click buttons to *"Return to Farmer Workspace (analyze)"* or *"Switch Stakeholder Role"*.

---

## 4. Test Sample File Matrix (For Demonstration)

| Inspection Target | Specimen File Path | Expected System Result |
| :--- | :--- | :--- |
| **Guava Mature Green** | `ml/data/guava_classification/Local Sindhi/Mature Green/237.jpg` | Predicted: `Mature Green`, Confidence ~0.8147 |
| **Guava Ripe** | `ml/data/guava_classification/Local Sindhi/Ripe/140.jpg` | Predicted: `Ripe`, Confidence ~0.90+ |
| **Guava Green** | `ml/data/guava_classification/Local Sindhi/Green/40.jpg` | Predicted: `Green`, Confidence ~0.85+ |
| **Banana Ripe** | `ml/data/raw/banana/ripeness/Banana Ripeness Classification Dataset/Ripe/Cavendish_Ripe_Bottom_0009.jpg` | Predicted: `Ripe`, Confidence ~0.8989 |
| **Banana Unripe** | `ml/data/raw/banana/ripeness/Banana Ripeness Classification Dataset/Unripe/Ambon_Unripe_Bottom_0009.jpg` | Predicted: `Unripe`, Confidence ~0.88+ |
| **Apple Orchard Scene** | `ml/data/processed/apple_detection_yolo/images/test/108.jpg` | YOLOv8n: 2 Apples Detected (CC BY-NC 4.0) |
| **Mango Specimen** | `ml/data/raw/mango/original/IMG-37.jpeg` | Status: `unavailable` (Honest Gated Deficit) |
| **Canopy Foliage (OOD)**| `ml/data/raw/fruitnet/Bad Quality_Fruits/Lime_Bad/IMG_7589.JPG` | Identified: `negative_background`, `is_uncertain=True` |

---

## 5. Troubleshooting & Diagnostic Commands

### Port Already in Use (Port 8000 or Port 3000)
```powershell
# Identify processes occupying ports 8000 or 3000
Get-NetTCPConnection -LocalPort 8000, 3000 -ErrorAction SilentlyContinue | Select-Object LocalPort, OwningProcess

# Stop existing processes if necessary
Stop-Process -Id <OwningProcessId> -Force
```

### Checking Backend Health from Terminal
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" | ConvertTo-Json -Depth 3
```

### Verifying Active CUDA Hardware from Terminal
```powershell
.\.venv\Scripts\python.exe -c "import torch; print('CUDA Available:', torch.cuda.is_available(), '| Device:', torch.cuda.get_device_name(0))"
```

### Confirming File-Based Persistence State
```powershell
# Inspect latest shipment records in JSON ledger
.\.venv\Scripts\python.exe -c "
from app.db.repository import ShipmentRepository
repo = ShipmentRepository()
shipments = repo.list_shipments()
print(f'Total Persisted Shipments: {len(shipments)}')
if shipments:
    print('Latest:', shipments[-1]['id'], shipments[-1]['produce_type'], shipments[-1]['status'])
"
```

