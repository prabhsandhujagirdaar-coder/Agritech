# AgriChain AI — Phase 5: Guava CNN End-to-End Verification Report

**Document Version:** 1.0.0  
**Target Crop:** Guava (*Psidium guajava* L.)  
**Model Architecture:** ResNet18 Transfer Learning Baseline (v2.0.0)  
**Checkpoint Artifact:** [`ml/artifacts/best_guava_resnet18.pth`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/artifacts/best_guava_resnet18.pth)  
**Execution Environment:** NVIDIA GeForce RTX 4050 Laptop GPU (CUDA 12.8, PyTorch 2.11.0+cu128)  
**Operating System:** Windows 11  
**Verification Date:** October 2026  
**Status:** Verification Completed  

---

## Executive Summary

Phase 5 end-to-end verification confirms that the Guava ResNet18 model operates with complete integrity across the backend FastAPI service, the Next.js API proxy, and the farmer dashboard user interface.

Key findings and verification outcomes:
1. **Live Backend Inspection:** Port 8000 status and hardware connectivity were inspected. The FastAPI application loads the checkpoint cleanly on `cuda` (NVIDIA RTX 4050 Laptop GPU) when started with `$env:TARGET_CROP="guava"` and `$env:GUAVA_MODEL_ACTIVATED="true"`.
2. **CNN Endpoint & Request Contract:** The active prediction endpoint is `POST /predict` (with alias `POST /api/v1/cnn/predict`), expecting multipart form-data with key `file` containing JPEG, PNG, or WEBP image bytes.
3. **Real Image Inference:** All three maturity stages from the held-out test manifest were evaluated through the real HTTP prediction endpoint. All returned `200 OK` with 100% agreement to ground truth labels (`Green` -> `Green`, `Mature Green` -> `Mature Green`, `Ripe` -> `Ripe`) with ~13–17 ms inference latency on GPU.
4. **Input Rejection Validation:** Invalid inputs (missing file part, unsupported PDF, corrupted JPEG stream, and oversized file >10 MB) are strictly rejected with standard HTTP status codes (`422`, `415`, `400`).
5. **Frontend Defect Remediation:** Identified and corrected a label mapping bug in `apps/web/lib/constants.js` and `apps/web/app/dashboard/page.js` where Guava class names were inadvertently mapped to Kinnow labels in probability breakdown views. Added explicit "Uncalibrated score" disclaimers on softmax confidence values.
6. **Zero Regression:** All 39 backend tests and all frontend taxonomy tests pass with zero errors.

---

## 1. Actual Health Endpoint Response

When initialized with Guava environment configuration:
- `TARGET_CROP=guava`
- `GUAVA_MODEL_ACTIVATED=true`
- `GUAVA_MODEL_WEIGHTS_PATH=ml/artifacts/best_guava_resnet18.pth`

### Route: `GET http://127.0.0.1:8000/health`
**HTTP Status:** `200 OK`  
**Response Body:**
```json
{
  "status": "healthy",
  "target_crop": "guava",
  "model": "resnet18",
  "model_version": "2.0.0",
  "device": "cuda",
  "model_available": true,
  "message": "Model loaded successfully on cuda for guava.",
  "database": {
    "enabled": false,
    "connected": null,
    "message": "File-based ledger persistence active."
  }
}
```

### Route: `GET http://127.0.0.1:8000/api/v1/cnn/status`
**HTTP Status:** `200 OK`  
**Response Body:**
```json
{
  "status": "ready",
  "target_crop": "guava",
  "model_available": true,
  "model_name": "resnet18",
  "model_version": "2.0.0",
  "weights_path": "C:\\Users\\PrabSandhu\\Documents\\codes\\Agritech_\\ml\\artifacts\\best_guava_resnet18.pth",
  "weights_exist": true,
  "device": "cuda",
  "class_mapping_verified": true,
  "class_mapping_status": "VERIFIED_GROUND_TRUTH_METADATA",
  "message": "Model loaded successfully on cuda for guava."
}
```

---

## 2. Actual Prediction Endpoint & Request Format

### Endpoint Registration
- **Root Legacy Compatibility Route:** `POST /predict`
- **Versioned API Route:** `POST /api/v1/cnn/predict`
- **Next.js Frontend Proxy:** `POST /api/predict` (proxies to backend `POST /predict`)

### Request Specification
- **Content-Type:** `multipart/form-data`
- **Parameter Name:** `file` (Binary upload)
- **Accepted MIME Types:** `image/jpeg`, `image/jpg`, `image/png`, `image/webp`
- **Maximum Size:** `10,485,760` bytes (10 MB)
- **Preprocessing Pipeline (Parity with Evaluation):**
  1. PIL RGB conversion (`img.convert("RGB")`)
  2. Resize to `(256, 256)`
  3. Center crop to `(224, 224)`
  4. PyTorch `ToTensor()` (scales to `[0.0, 1.0]`)
  5. ImageNet normalization: `mean=[0.485, 0.456, 0.406]`, `std=[0.229, 0.224, 0.225]`

### Architecture & Checkpoint Invariants
- **Checkpoint Path:** `ml/artifacts/best_guava_resnet18.pth`
- **Backbone:** PyTorch `torchvision.models.resnet18`
- **Classifier Head:** `Dropout(p=0.2) -> Linear(in_features=512, out_features=3)`
- **Class Mapping:**
  - `0` = **Green**
  - `1` = **Mature Green**
  - `2` = **Ripe**
- **Confidence Semantics:** Uncalibrated softmax score ($\max_{c} \sigma(\mathbf{z})_c$), bounded in $[0.0, 1.0]$. It is explicitly **not** a calibrated posterior probability.
- **Cross-Crop Guard:** Checkpoints tagged with `"strawberry"` or Kinnow uncertified checkpoints are rejected or gated behind `HTTP 503`.

---

## 3. Results for Actual Test Images

Three actual specimen images from the held-out test manifest ([`ml/data/manifests/v2_grouped/test.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/manifests/v2_grouped/test.json)) were sent through the HTTP prediction endpoint:

| Test Case | Specimen Path | Ground Truth Class | Predicted Class | Softmax Confidence | Probabilities Distribution | HTTP Status | Inference Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Green** | `ml/data/guava_classification/Local Sindhi/Green/40.jpg` | **Green** (0) | **Green** (0) | **0.9706** (97.06%) | Green: 0.9706<br>Mature Green: 0.0289<br>Ripe: 0.0006 | `200 OK` | 355.61 ms (cold start pass) |
| **Mature Green** | `ml/data/guava_classification/Local Sindhi/Mature Green/237.jpg` | **Mature Green** (1) | **Mature Green** (1) | **0.8147** (81.47%) | Green: 0.1683<br>Mature Green: 0.8147<br>Ripe: 0.0170 | `200 OK` | 16.93 ms |
| **Ripe** | `ml/data/guava_classification/Local Sindhi/Ripe/140.jpg` | **Ripe** (2) | **Ripe** (2) | **0.6770** (67.70%) | Green: 0.0597<br>Mature Green: 0.2633<br>Ripe: 0.6770 | `200 OK` | 13.40 ms |

### Actual HTTP Response Payloads

#### Specimen 1: Green
```json
{
  "predicted_class": "Green",
  "class_index": 0,
  "label": "Green",
  "confidence": 0.9706,
  "probabilities": {
    "Green": 0.9706,
    "Mature Green": 0.0289,
    "Ripe": 0.0006
  },
  "target_crop": "guava",
  "model_name": "resnet18",
  "model_version": "2.0.0",
  "device": "cuda",
  "inference_ms": 355.61
}
```

#### Specimen 2: Mature Green
```json
{
  "predicted_class": "Mature Green",
  "class_index": 1,
  "label": "Mature Green",
  "confidence": 0.8147,
  "probabilities": {
    "Green": 0.1683,
    "Mature Green": 0.8147,
    "Ripe": 0.017
  },
  "target_crop": "guava",
  "model_name": "resnet18",
  "model_version": "2.0.0",
  "device": "cuda",
  "inference_ms": 16.93
}
```

#### Specimen 3: Ripe
```json
{
  "predicted_class": "Ripe",
  "class_index": 2,
  "label": "Ripe",
  "confidence": 0.677,
  "probabilities": {
    "Green": 0.0597,
    "Mature Green": 0.2633,
    "Ripe": 0.677
  },
  "target_crop": "guava",
  "model_name": "resnet18",
  "model_version": "2.0.0",
  "device": "cuda",
  "inference_ms": 13.4
}
```

---

## 4. Invalid-Input Test Results

Negative testing verified that the FastAPI validation layer strictly rejects invalid payloads:

| Negative Scenario | Request Details | Expected HTTP Status | Actual HTTP Status | Actual Error Detail | Validation Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Missing Image File** | `POST /predict` with no multipart form parts | `422 Unprocessable Entity` | `422` | `[{'type': 'missing', 'loc': ['body', 'file'], 'msg': 'Field required'}]` | **PASSED** |
| **Unsupported File Type** | `POST /predict` with `.pdf` file (`application/pdf`) | `415 Unsupported Media Type` | `415` | `Unsupported content type 'application/pdf'. Expected one of ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'].` | **PASSED** |
| **Corrupt Image Data** | `POST /predict` with invalid JPEG header / truncated byte sequence | `400 Bad Request` | `400` | `Invalid or corrupted image. Unable to decode pixel buffer.` | **PASSED** |
| **Oversized Image** | `POST /predict` with `10,486,784` bytes (> 10 MB limit) | `400 Bad Request` | `400` | `File size (10486784 bytes) exceeds the allowed limit of 10485760 bytes.` | **PASSED** |
| **Unactivated Guard State** | `POST /predict` with `GUAVA_MODEL_ACTIVATED=false` | `503 Service Unavailable` | `503` | `Guava model inference is currently unavailable.` | **PASSED** |

---

## 5. Next.js Frontend Verification & Fixes

### 5.1 Defect Audit in Existing Frontend
Inspection of `apps/web/lib/constants.js`, `apps/web/app/api/predict/route.js`, and `apps/web/app/dashboard/page.js` revealed three UI issues:
1. **Kinnow Label Leaking in Probability Map:** In `dashboard/page.js`, the probability breakdown iterated over classes (`"Green"`, `"Mature Green"`, `"Ripe"`) and called `getRipenessLabel(className)`. Because `getRipenessLabel` checked `getClassIndex(className)` (`1`) and indexed `CLASS_LABELS[1]`, `"Mature Green"` was mapped to `"Partially Ripe"`. As a result, the UI displayed `Partially Ripe (Mature Green)` to users.
2. **Raw Class Numbers in Verdict:** The card previously rendered `Class 0`, `Class 1`, or `Class 2`, which is confusing to farmers instead of showing the official maturity stages (`Green`, `Mature Green`, `Ripe`).
3. **Unqualified Confidence Claims:** The card labeled the score as `Confidence` without clarifying that the value is an uncalibrated softmax heuristic.
4. **Hardcoded Crop Heading:** The footer rendered `Target Crop: Kinnow Mandarin (guava)` when running Guava inference.

### 5.2 Targeted Fixes Applied
1. **[`apps/web/lib/constants.js`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/apps/web/lib/constants.js):**
   - Added direct checks in `getRipenessLabel` for `GUAVA_CLASS_LABELS` values (`"Green"`, `"Mature Green"`, `"Ripe"`).
   - Added support for objects specifying `target_crop: "guava"` to look up `GUAVA_CLASS_LABELS` indices.
2. **[`apps/web/app/api/predict/route.js`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/apps/web/app/api/predict/route.js):**
   - Imported `GUAVA_CLASS_LABELS`.
   - Used `GUAVA_CLASS_LABELS` as fallback if `data.target_crop === "guava"`.
3. **[`apps/web/app/dashboard/page.js`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/apps/web/app/dashboard/page.js):**
   - Changed result card sublabel to display farmer-friendly stage for Guava: `Stage: Mature Green (Index 1)`.
   - Updated confidence header to `Softmax Score` and added explicit helper caption: `Uncalibrated score`.
   - Prevented probability map labels from converting Guava classes to Kinnow aliases.
   - Updated target crop footer dynamically: `Target Crop: Guava (Psidium guajava)`.
   - Made error cards produce-agnostic (`Model Unavailable` / `Awaiting Certified Checkpoint`).
4. **[`apps/web/lib/constants.test.mjs`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/apps/web/lib/constants.test.mjs):**
   - Added unit test assertions covering `getRipenessLabel` for Guava classes and payload objects.

All existing dashboard features (Shipment tracking, Telemetry graphs, LSTM risk indicators, Leaflet maps, and WebSocket real-time gateway) were completely preserved without disruption.

---

## 6. Regression Test Counts

| Test Suite | Command | Executed Tests | Passed | Failed | Errors |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Guava CNN Integration** | `python -m unittest backend/tests/test_guava_cnn_integration.py` | 11 | **11** | 0 | 0 |
| **CNN API & Contracts** | `python -m unittest backend/tests/test_cnn_api.py` | 15 | **15** | 0 | 0 |
| **Shipment Persistence** | `python -m unittest backend/tests/test_persistence.py` | 13 | **13** | 0 | 0 |
| **Frontend Taxonomy Tests** | `npm test` (in `apps/web`) | 7 | **7** | 0 | 0 |
| **Frontend Code Quality** | `npm run lint` (in `apps/web`) | Next.js Lint | **0 Errors** (4 warnings) | 0 | 0 |
| **Total Backend Tests** | — | **39** | **39** | **0** | **0** |

---

## 7. Files Changed and Reasons

| File | Change Type | Reason |
| :--- | :--- | :--- |
| [`backend/tests/test_guava_cnn_integration.py`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/backend/tests/test_guava_cnn_integration.py) | Edit | Patched `settings.GUAVA_MODEL_ACTIVATED` in `test_06b` to reliably test the unactivated default state without collision when external shell has `GUAVA_MODEL_ACTIVATED=true` exported. |
| [`apps/web/lib/constants.js`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/apps/web/lib/constants.js) | Edit | Added Guava class string resolution to `getRipenessLabel` to eliminate inappropriate conversion of Guava classes into Kinnow ripeness stages. |
| [`apps/web/lib/constants.test.mjs`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/apps/web/lib/constants.test.mjs) | Edit | Added unit tests verifying `getRipenessLabel` resolution for `"Green"`, `"Mature Green"`, and `"Ripe"`. |
| [`apps/web/app/api/predict/route.js`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/apps/web/app/api/predict/route.js) | Edit | Imported `GUAVA_CLASS_LABELS` and applied crop-aware fallback mapping. |
| [`apps/web/app/dashboard/page.js`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/apps/web/app/dashboard/page.js) | Edit | Displayed farmer-friendly labels, added "Uncalibrated score" notice for confidence, made target crop dynamic, and preserved exact Guava probability map class keys. |
| [`docs/ml/GUAVA_PHASE5_VERIFICATION_REPORT.md`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/docs/ml/GUAVA_PHASE5_VERIFICATION_REPORT.md) | Create | Comprehensive Phase 5 end-to-end verification report. |

---

## 8. Known Limitations & Remaining Issues

1. **Uncalibrated Softmax Scores:** Softmax output scores reflect relative logit magnitudes rather than calibrated probabilities. A confidence score of 0.8147 should be interpreted as an uncalibrated ranking metric, not a mathematical certainty of ripeness. Post-hoc temperature scaling or Platt scaling would be beneficial in future phases.
2. **Held-Out Test Set Accuracy (83.24%):** While the three test specimens matched ground truth 100%, the overall model accuracy on the full 346-image held-out test split is 83.24% with a macro-F1 of 0.8122. Borderline transitional fruit between `Mature Green` and `Ripe` can occasionally experience misclassifications.
3. **Session Environment Scoping:** On Windows PowerShell, setting environment variables with `$env:KEY = "value"` scopes variables strictly to that PowerShell process. To ensure Uvicorn uses the Guava model, Uvicorn must be launched within that specific session or with environment variables passed explicitly.

---

## 9. Exact Commands to Run Backend & Frontend Locally

### Start Backend (FastAPI + Uvicorn with Guava Model Activated)
In a Windows PowerShell window at the project root `C:\Users\PrabSandhu\Documents\codes\Agritech_`:
```powershell
$env:TARGET_CROP = "guava"
$env:GUAVA_MODEL_ACTIVATED = "true"
$env:GUAVA_MODEL_WEIGHTS_PATH = "ml/artifacts/best_guava_resnet18.pth"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

### Start Frontend (Next.js 14)
In a second Windows PowerShell terminal:
```powershell
cd apps\web
npm run dev
```
Open `http://localhost:3000` in a browser.

### Run Verification Test Commands
```powershell
# 1. Run Guava CNN Integration Tests
.\.venv\Scripts\python.exe -m unittest backend/tests/test_guava_cnn_integration.py

# 2. Run All Backend Regression Tests
.\.venv\Scripts\python.exe -m unittest backend/tests/test_cnn_api.py
.\.venv\Scripts\python.exe -m unittest backend/tests/test_persistence.py

# 3. Run Frontend Unit Tests
cd apps\web; npm test; cd ..\..
```
