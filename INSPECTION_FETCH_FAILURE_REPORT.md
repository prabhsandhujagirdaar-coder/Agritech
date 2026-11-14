# AgriChain AI — Produce Specimen Inspection Investigation & Fix Report

**Date**: 2026-11-14  
**Author**: Antigravity DeepMind Agent  
**Component**: Produce Specimen Upload & Multi-Fruit Inspection Pipeline  
**Overall Status**: **RESOLVED & VERIFIED (PASS)**

---

## 1. Executive Summary

When uploading a fruit photograph and clicking **"IDENTIFY SPECIES & INSPECT PRODUCE"**, the web dashboard displayed:

```text
Inspection Error
BACKEND VALIDATION / SERVICE DIAGNOSTIC
fetch failed
```

A comprehensive investigation of the browser client, Next.js API proxy route, FastAPI backend, and PyTorch model services was conducted. The failure has been resolved with zero changes to frozen ML weights, preserving model gating integrity, and enhancing diagnostic error reporting across both frontend and backend layers.

---

## 2. Root Cause Analysis

### 2.1 Failing Endpoint
- **Browser-facing Request**: `POST /api/inspect?mode=auto&fruit=guava` (via Next.js App Router)
- **Backend-facing Request**: `POST http://127.0.0.1:8000/api/v1/cnn/inspect?mode=auto&fruit=guava`

### 2.2 Mechanism of Failure
1. **Uninformative Node.js Fetch Failure Masking**:
   In `apps/web/app/api/inspect/route.js`, the catch block caught any failed fetch attempt to the FastAPI backend and returned:
   ```javascript
   return NextResponse.json({ detail: error.message || "..." }, { status: 503 });
   ```
   In Node.js 18+ (which uses `undici` for global `fetch`), any connection refusal (`ECONNREFUSED`), socket error, or timeout sets `error.message = "fetch failed"`, with the underlying cause nested in `error.cause`. Returning raw `error.message` wiped out the target URL, the socket error code, and any troubleshooting advice.

2. **IPv4 vs IPv6 Host Resolution on Windows**:
   When Next.js runs in development mode, default hostname lookups on Windows often resolve `localhost` to IPv6 `[::1]`. Because FastAPI/Uvicorn binds strictly to IPv4 (`127.0.0.1:8000`), connection attempts to `[::1]:8000` failed immediately with `ECONNREFUSED`, manifesting as `"fetch failed"`.

3. **Stream Pipe / Duplex Body Forwarding Vulnerability**:
   `route.js` previously extracted `const file = formData.get("file")` directly from `request.formData()` and appended it to a new `FormData` without reading the buffer into memory. In Node.js server environments, forwarding a Web `File` stream between two `fetch` calls without explicit buffer reading can cause pipe exhaustion, duplex errors, or missing `Content-Type` headers.

4. **Missing Request ID & Diagnostic Classification**:
   There was no correlation identifier (`X-Request-ID`) linking the frontend proxy request with the backend server log. Errors of different natures (network offline vs invalid image dimensions vs model deficit) were all displayed identically under a generic error card.

5. **CORS Configuration on Dynamic Next.js Port Allocation**:
   When Next.js detected port 3000 in use and automatically moved to port 3001, `BACKEND_CORS_ORIGINS` in FastAPI only whitelisted port 3000, causing cross-origin requests to be rejected.

---

## 3. Before vs. After Behavior

| Dimension | Before Fix | After Fix |
| :--- | :--- | :--- |
| **Backend Unreachable** | Displays `fetch failed` with no URL or troubleshooting guidance. | Displays `Backend Connectivity / Offline` badge with exact diagnostic message, target URL, and hint to run `.\start.bat`. |
| **Host Resolution** | Single URL lookup (susceptible to IPv6 `::1` refusal on Windows). | Dual-host candidate fallback (`127.0.0.1:8000` and `localhost:8000`) with auto-retry. |
| **Payload Integrity** | Forwarded raw Web `File` stream; prone to stream consumption errors. | Reads `arrayBuffer()` into memory `Buffer` + typed `Blob` with explicit filename and MIME type. |
| **Request Traceability** | Zero request IDs in Next.js or FastAPI logs. | Generates and propagates `X-Request-ID` across proxy, backend logs, and response headers. |
| **Backend Route Coverage** | Only `/api/v1/cnn/inspect` and root `/inspect`. | Added `/api/inspect` alias alongside `/api/v1/cnn/inspect` and `/inspect`. |
| **CORS Origins** | Allowed only `localhost:3000` and `127.0.0.1:3000`. | Extended to `3000`, `3001`, and `3002` on both `localhost` and `127.0.0.1`. |
| **UI Error Handling** | Single static text block; no retry button. | Categorized badges (`NETWORK`, `VALIDATION`, `MODEL GATED`), troubleshooting hint box, and a **"Retry Inspection"** button. |

---

## 4. Files Changed

1. **`apps/web/app/api/inspect/route.js`**:
   - Implemented `getCandidateBaseUrls()` with automatic `127.0.0.1` and `localhost` fallback.
   - Converted incoming `file` stream to in-memory `Blob` with guaranteed filename and MIME type.
   - Added `AbortSignal.timeout(30000)` to prevent unbounded hangs.
   - Added `X-Request-ID` generation and header propagation.
   - Structured error classification (`network`, `validation`, `model_unavailable`, `backend_error`).

2. **`backend/app/api/v1/endpoints/cnn.py`**:
   - Injected `Response` and extracted/generated `X-Request-ID`.
   - Added structured logging for incoming requests (`size`, `filename`, `content_type`, `mode`, `fruit`).
   - Propagated `X-Request-ID` into response headers and exception responses.

3. **`backend/app/main.py`**:
   - Added `@app.post("/api/inspect")` proxy compatibility route.
   - Synchronized `root_inspect` parameter signatures to use `Query("manual")` and `Query(None)`.

4. **`backend/app/core/config.py`**:
   - Updated `BACKEND_CORS_ORIGINS` to include ports `3000`, `3001`, and `3002`.

5. **`apps/web/app/dashboard/page.js`**:
   - Enhanced `runAnalysis()` to parse structured error envelopes and capture `request_id`, `category`, and `hint`.
   - Updated error display card with category-specific badges, troubleshooting hints, and a **"Retry Inspection"** button.

---

## 5. Verification & Test Execution Results

### 5.1 End-to-End Browser-to-Backend Inspection Flow (`scripts/test_inspection_flow.mjs`)

Executed live against active Next.js (port 3001) and FastAPI (port 8000) servers:

```text
=================================================================
  AgriChain AI — Produce Specimen Inspection Test Suite
=================================================================

[PASS] 1. FastAPI Backend Health Check (/health)
       Details: {"status":200,"target_crop":"guava","model_available":true,"device":"cuda"}
[PASS] 2. Auto Mode: Identify Species & Inspect Produce (Guava)
       Details: {"status":200,"identified_fruit":"guava","maturity_verdict":"Mature Green","confidence":0.6618,"requestId":"insp_1794676716404_evqy33"}
[PASS] 3. Manual Mode: Guava Harvest Maturity (ResNet18)
       Details: {"status":200,"target_fruit":"guava","predicted_class":"Mature Green","confidence":0.6618}
[PASS] 4. Manual Mode: Banana Ripeness Classifier (ResNet18)
       Details: {"status":200,"target_fruit":"banana","predicted_class":"Unripe","model":"resnet18"}
[PASS] 5. Manual Mode: Apple YOLOv8n Object Detection (CC BY-NC 4.0)
       Details: {"status":200,"task_type":"object_detection","model":"yolov8n","license":"Academic / Non-Commercial Research Only (CC BY-NC 4.0)"}
[PASS] 6. Gated Mango Inspection: Honest Deficit Disclosure
       Details: {"status":200,"target_fruit":"mango","status_field":"unavailable","unavailable_reason":"Mango maturity prediction is unavailable. Awaiting validated..."}
[PASS] 7. Security & Validation: Reject Non-Image File Format
       Details: {"status":415,"expected":"415 Unsupported Media Type or 400 Bad Request","detail":"Unsupported content type 'text/plain'. Expected one of ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'].","error_category":"validation"}
[PASS] 8. Validation: Reject Empty Specimen Upload
       Details: {"status":400,"error_category":"validation","detail":"No produce image file uploaded. Please upload a JPEG, PNG, or WEBP image."}

=================================================================
  VERDICT: ALL 8 INSPECTION FLOW TESTS PASSED 100%
=================================================================
```

### 5.2 Backend Multi-Fruit Integration Tests (`backend/tests/test_multifruit_inspection.py`)

```text
backend/tests/test_multifruit_inspection.py::TestMultiFruitInspection::test_01_registry_catalog_completeness PASSED [ 10%]
backend/tests/test_multifruit_inspection.py::TestMultiFruitInspection::test_02_manual_guava_inspection PASSED [ 20%]
backend/tests/test_multifruit_inspection.py::TestMultiFruitInspection::test_03_manual_banana_inspection PASSED [ 30%]
backend/tests/test_multifruit_inspection.py::TestMultiFruitInspection::test_04_manual_apple_inspection PASSED [ 40%]
backend/tests/test_multifruit_inspection.py::TestMultiFruitInspection::test_05_manual_mango_gated_handling PASSED [ 50%]
backend/tests/test_multifruit_inspection.py::TestMultiFruitInspection::test_06_stage1_identify_endpoint PASSED [ 60%]
backend/tests/test_multifruit_inspection.py::TestMultiFruitInspection::test_07_auto_mode_high_confidence_cascade PASSED [ 70%]
backend/tests/test_multifruit_inspection.py::TestMultiFruitInspection::test_08_auto_mode_uncertainty_handling PASSED [ 80%]
backend/tests/test_multifruit_inspection.py::TestMultiFruitInspection::test_09_invalid_crop_rejection PASSED [ 90%]
backend/tests/test_multifruit_inspection.py::TestMultiFruitInspection::test_10_production_checkpoint_hashes PASSED [100%]

======================= 10 passed, 1 warning in 21.07s ========================
```

### 5.3 Frontend Unit & Regression Suite (`npm --prefix apps/web test`)

- Guava & Produce CNN Class Labels & Ripeness Taxonomy: **PASSED**
- Geospatial & Indian Boundary Normalization: **PASSED**
- Phase 13.5 Frontend Unit & Regression Tests: **PASSED**
- Phase 13.6 UI/UX Regression Tests: **PASSED**
- Phase 19 Role Configuration & Access Control Tests: **PASSED**

---

## 6. Cryptographic Model Checkpoint Verification

All 5 frozen production checkpoints were re-verified against their baseline SHA-256 hashes:

| Checkpoint File | Format / Architecture | Size | Expected SHA-256 Hash | Verification |
| :--- | :--- | :---: | :--- | :---: |
| `best_guava_resnet18.pth` | PyTorch ResNet-18 | 44,796,363 B | `b213059f6b9744915ef921f2be70de9ae1eb0dd6c50a3fb0edce0e2cb710f5b4` | **PASS (100%)** |
| `best_banana_resnet18.pth` | PyTorch ResNet-18 | 128,791,659 B | `3b296ba8556d88bd934f74fee1e88860921fe69dd5b4869984fd0c529f339dae` | **PASS (100%)** |
| `best_fruit_identifier_mobilenet_v3_large.pth` | MobileNetV3-Large | 17,044,655 B | `273674bcebad518ecde2dc55aee558d452ac2d4c09dd1924ad61f4328ab81356` | **PASS (100%)** |
| `best_fruit_identifier_resnet18.pth` | PyTorch ResNet-18 | 128,800,363 B | `07150d1ddb92ea8ce7018e08fa6c3d21b6b6de6aac9c5feb838d6f9dc28a8967` | **PASS (100%)** |
| `best_apple_yolov8n.pt` | Ultralytics YOLOv8n | 6,502,250 B | `02a89b45ead457a8aedfd36fd78e23dd959c410becdd380c61ffef0b3e21d8e2` | **PASS (100%)** |

**Conclusion**: Zero weights modified, retrained, or compressed. Model gating policies remain intact.
