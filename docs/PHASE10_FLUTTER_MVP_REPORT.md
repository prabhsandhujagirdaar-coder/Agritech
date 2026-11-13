# AgriChain AI — Phase 10: Flutter Android MVP Report

**Document Version:** 1.0.0  
**Target Crop:** Guava (*Psidium guajava* L.)  
**Framework:** Flutter 3.47.2 / Dart 3.13.2  
**Android Target:** Android SDK 36.0.0 (Compile SDK 36, Target SDK 36, Platform android-37.0)  
**Execution Date:** October 2026  
**Status:** Successfully Implemented, Tested & Verified (Debug APK Built)  

---

## Executive Summary

Phase 10 delivers the first functional Android mobile client for **AgriChain AI** (`apps/mobile/`), fulfilling the practical mobile implementation requirement of the App Development curriculum and closing the primary gap identified in the Phase 8 and Phase 9 integration audits.

The mobile application connects directly to the existing FastAPI backend (`backend/app/main.py`), utilizing Guava (*Psidium guajava* L.) as the active demonstration crop. It implements an Android-first Material 3 user experience tailored for field intake inspectors and packhouse operators across the Punjab citrus and fruit corridors.

All code quality gates, unit tests, widget tests, static analysis (`flutter analyze`), and an end-to-end Android Gradle debug APK build (`flutter build apk --debug`) were executed and verified with zero errors.

---

## 1. Mobile Environment Audit

Before initialization, a comprehensive audit of the local environment was conducted:

| Component | Detected Specification / Path | Readiness Status |
| :--- | :--- | :---: |
| **Flutter SDK** | Flutter 3.47.2 (channel stable, framework revision `d3b14c8769`) | **VERIFIED** |
| **Dart SDK** | Dart 3.13.2 | **VERIFIED** |
| **Android SDK** | Android SDK 36.0.0 at `C:\Users\PrabSandhu\AppData\Local\Android\sdk` | **VERIFIED** |
| **Android Platform / Build Tools** | Platform `android-37.0`, Build-tools `36.0.0` | **VERIFIED** |
| **Java / JDK Toolchain** | OpenJDK 25.0.2 at `C:\Program Files\Android\Android Studio\jbr\bin\java` | **VERIFIED** |
| **Android Licenses** | All Android SDK licenses accepted | **VERIFIED** |
| **Initial `apps/mobile/` State** | Stub directory containing only `.gitkeep` (0 source files) | **INITIALIZED** |

### Project Scaffold Command
The application was initialized using standard Flutter tooling:
```powershell
flutter create --org com.agrichain --project-name agrichain_mobile --platforms android apps/mobile
```

### Dependencies Installed (`pubspec.yaml`)
- `http: ^1.6.0`: Standard HTTP transport client for REST API communication.
- `http_parser: ^4.1.2`: MIME media type handling for multipart image uploads.
- `image_picker: ^1.2.4`: Hardware camera capture and gallery image selection on Android.
- `flutter_test`: Unit and widget test framework.
- `flutter_lints: ^6.0.0`: Recommended Dart/Flutter style analysis.

### Android Manifest Permissions (`AndroidManifest.xml`)
Configured in `apps/mobile/android/app/src/main/AndroidManifest.xml`:
- `<uses-permission android:name="android.permission.INTERNET"/>`: Required for REST and socket networking.
- `android:usesCleartextTraffic="true"`: Required on Android 9+ (API 28+) to permit local HTTP development connections (`http://10.0.2.2:8000` and LAN IPs).

---

## 2. Implemented Screens & User Interface Architecture

The application adopts an accessible agricultural visual hierarchy using a deep forest green palette (`#1B5E20`), leaf green accents (`#2E7D32`), amber alert indicators, and Material 3 cards:

```
apps/mobile/lib/
├── config/
│   └── app_config.dart                  # Network constants, disclaimers, runtime base URL notifier
├── models/
│   ├── cnn_prediction.dart              # Guava CNN prediction schema & Phase 7 uncertainty heuristics
│   ├── risk_info.dart                   # Cold-chain risk scoring model
│   ├── service_status.dart              # Health probe response parser
│   ├── shipment.dart                    # Shipment lifecycle model & alert flags
│   └── telemetry.dart                   # Telemetry point & 4–8°C thermal excursion detector
├── services/
│   └── api_service.dart                 # REST client wrapping all FastAPI endpoints
├── screens/
│   ├── dashboard_screen.dart            # Service health, shipment metrics, quick ingest action
│   ├── guava_inspection_screen.dart     # Camera/gallery intake, inference, uncertainty warnings
│   ├── shipment_detail_screen.dart      # Metadata, cold-chain risk, telemetry logs, add reading
│   └── shipment_list_screen.dart        # Search, filter chips, pull-to-refresh shipment cards
├── widgets/
│   ├── empty_view.dart                  # Accessible empty state display
│   ├── error_view.dart                  # Network error / HTTP 503 state with host switcher
│   ├── scientific_disclaimer_card.dart  # Regulatory and academic integrity disclosures
│   └── status_chip.dart                 # Color-coded lifecycle status chips
└── main.dart                            # MainNavigationShell with bottom navigation bar
```

### Screen Descriptions

#### 1. Dashboard Screen (`DashboardScreen`)
- **Backend Service Health Card**: Real-time probe of backend health, target crop (`GUAVA`), CNN model readiness with execution device (`cuda` or `cpu`), and database connection mode (PostGIS vs fallback JSON ledger).
- **Shipment Metrics Bar**: Total shipments in ledger, active in-transit count, and thermal risk alert count.
- **Quick Ingest Action**: One-tap banner navigating directly to Guava maturity inspection.
- **Recent Shipments**: Live preview cards of recorded shipments with origin/destination, quantity, status chips, and direct navigation to details.
- **Dynamic Host Switcher**: Top-bar action button allowing inspectors to switch between Android Emulator (`10.0.2.2:8000`), Localhost (`127.0.0.1:8000`), or custom LAN addresses without rebuilding the application.

#### 2. Shipment List Screen (`ShipmentListScreen`)
- **Search Bar**: Real-time filtering by shipment ID, origin, destination mandi, or produce type.
- **Status Filter Chips**: Toggle between *All*, *In Transit*, *Created*, *Delivered*, and *Delayed*.
- **Shipment Cards**: Displays shipment ID, route, produce quantity (kg), status chip, and color-coded risk badge.
- **State Handling**: Smooth loading spinner, empty state illustration, and network error retry banner.

#### 3. Shipment Detail & Telemetry Screen (`ShipmentDetailScreen`)
- **Header Metadata**: Complete shipment route, crate count, quantity, created timestamp.
- **Cold-Chain Spoilage Risk Card**: Real-time metrics from `GET /api/v1/shipments/{id}/risk`:
  - `current_risk` percentage (0–100%)
  - `predicted_arrival_risk` percentage
  - `alert` flag with red/green status banner
  - `avg_temperature_c` across journey
  - `excursion_events` count
- **Telemetry Sequence List**: Chronological timeline of recorded sensor readings.
  - Thermal Excursion Highlighting: Readings within the optimal transit window (4.0°C–8.0°C) display green; readings outside display an orange/red excursion badge.
  - Sensor ID, location checkpoint, and timestamp.
- **Add Sensor Reading Modal**: Bottom sheet form allowing field inspectors to record new temperature and humidity readings via `POST /api/v1/shipments/{id}/telemetry`. Automatically re-queries the risk engine upon submission.

#### 4. Guava Maturity Inspection Screen (`GuavaInspectionScreen`)
- **Target Crop Banner**: Explicit identification of Guava (*Psidium guajava* L.) and ResNet18 classifier.
- **Dual Intake Modes**: Capture photo via device camera or select image from gallery.
- **Inference Pipeline**: Sends image bytes via multipart form upload to `POST /api/v1/cnn/predict`.
- **Classification Results**:
  - Predicted Maturity Stage: Large badge displaying `GREEN`, `MATURE GREEN`, or `RIPE`.
  - Heuristic Softmax Score: Percentage confidence with explicit uncalibrated disclaimer.
  - Execution Metadata: Compute device (`CUDA` / `CPU`) and wall-clock latency (ms).
  - Class Distribution Meters: Color-coded probability bars for all 3 classes.
  - Phase 7 Uncertainty Warning Notice: Automatically triggers if top score is $< 60\%$ or if the score margin between the top two classes is $< 15\%$, instructing the inspector to perform secondary manual grading.
- **Error States**: Diagnostic card handling HTTP 503 (model checkpoint uninitialized or offline) vs transport connection errors.

---

## 3. API Integration & Network Configuration

The application reuses the exact FastAPI backend endpoints documented in the monorepo contracts. No mock data or invented endpoints were introduced.

### Integrated Endpoints

| Endpoint | HTTP Method | Payload / Params | Response Model | Description |
| :--- | :---: | :--- | :--- | :--- |
| `/api/v1/health` | `GET` | None | `ServiceStatus` | System health, target crop, CNN availability, database status. |
| `/api/v1/shipments` | `GET` | None | `List[Shipment]` | Query active shipments from repository. |
| `/api/v1/shipments/{id}` | `GET` | `shipment_id` in path | `Shipment` | Single shipment record details. |
| `/api/v1/shipments/{id}/risk` | `GET` | `shipment_id` in path | `ShipmentRiskInfo` | Cold-chain spoilage risk, excursions, arrival risk. |
| `/api/v1/shipments/{id}/telemetry` | `GET` | `limit=50` query param | `List[TelemetryRecord]` | Timestamped sensor sequence. |
| `/api/v1/shipments/{id}/telemetry` | `POST` | `temperature`, `humidity`, `sensor_id`, `location` | `TelemetryRecord` | Ingest live sensor reading. |
| `/api/v1/cnn/predict` | `POST` | Multipart `file` (JPEG/PNG/WEBP) | `CNNPredictionResult` | ResNet18 Guava maturity prediction. |

### Network Address Architecture

Android devices operate in an isolated network namespace from the host machine:

1. **Android Virtual Device (AVD Emulator):**
   - The emulator routes the development host's loopback interface via `10.0.2.2`.
   - Emulator Base URL: `http://10.0.2.2:8000/api/v1`
2. **Physical Android Device (USB / Wi-Fi):**
   - Physical devices cannot use `10.0.2.2`. They must connect to the host machine's Local Area Network IP (e.g., `http://192.168.1.50:8000/api/v1`).
   - The host machine's Windows Defender Firewall must allow inbound traffic on port 8000.
3. **Desktop / Web Test Runners:**
   - Loopback Base URL: `http://127.0.0.1:8000/api/v1`

Configuration is managed via `AppConfig`:
- Compile-time default: `--dart-define=API_BASE_URL=...`
- Runtime switching: Users can tap the settings icon in the app bar on the Dashboard to input or select preset addresses dynamically.

---

## 4. Verification, Testing & Build Evidence

### 4.1 Static Analysis (`flutter analyze`)
```powershell
flutter analyze
```
**Output:**
```
Analyzing mobile...                                             
No issues found! (ran in 1.9s)
```
- **Result:** 0 errors, 0 warnings, 0 lints.

### 4.2 Unit and Widget Test Suite (`flutter test`)
Executed across `test/models_test.dart` and `test/widget_test.dart`:
```powershell
flutter test
```
**Output:**
```
00:00 +0: loading C:/Users/PrabSandhu/Documents/codes/Agritech_/apps/mobile/test/models_test.dart
00:00 +0: Model Serialization & Logic Tests Shipment.fromJson parses correctly
00:00 +1: Model Serialization & Logic Tests Shipment alert flag triggers when riskIndex > 50
00:00 +2: Model Serialization & Logic Tests TelemetryRecord thermal excursion detection (4°C - 8°C)
00:00 +3: Model Serialization & Logic Tests ShipmentRiskInfo parses correctly
00:00 +4: Model Serialization & Logic Tests CNNPredictionResult parses and handles clear prediction
00:00 +5: Model Serialization & Logic Tests CNNPredictionResult triggers uncertainty on low score (<60%)
00:00 +6: Model Serialization & Logic Tests CNNPredictionResult triggers uncertainty on close margin (<15%)
00:00 +7: Widget Tests ScientificDisclaimerCard renders disclaimers accurately
00:01 +8: Widget Tests StatusChip renders formatted status string
00:01 +9: Widget Tests Main Navigation Shell renders tabs
00:02 +10: All tests passed!
```
- **Assertions Tested:**
  - JSON deserialization and schema fidelity against backend models.
  - Risk threshold alerting ($> 50.0\%$).
  - Cold-chain thermal excursion detection ($< 4.0^\circ\text{C}$ or $> 8.0^\circ\text{C}$).
  - CNN prediction parsing and class index alignment.
  - Low top score heuristic threshold ($< 60\%$).
  - Close score margin heuristic threshold ($< 15\%$).
  - Disclaimer card rendering with uncalibrated softmax disclosure.
  - Status chip color and label formatting.
  - Bottom navigation bar destination switching.
- **Pass Rate:** **10 Passed, 0 Failed (100% Pass Rate)**.

### 4.3 Android Debug APK Build (`flutter build apk --debug`)
```powershell
flutter build apk --debug
```
**Output:**
```
Running Gradle task 'assembleDebug'...                            408.8s
√ Built build\app\outputs\flutter-apk\app-debug.apk
```

**Generated Artifact Verification:**
- **File:** `apps/mobile/build/app/outputs/flutter-apk/app-debug.apk`
- **Size:** `151,446,009 bytes` (~144.4 MB)
- **Timestamp:** October 22, 2026 16:09:40
- **Status:** Valid Android Package ready for deployment or sideloading via ADB.

### 4.4 Monorepo Regression Tests
To ensure zero regressions across other tracks:
1. **Backend Tests:**
   ```powershell
   .\.venv\Scripts\python.exe -m unittest backend/tests/test_cnn_api.py backend/tests/test_persistence.py backend/tests/test_guava_cnn_integration.py
   ```
   *Result:* **40 tests executed (39 passed, 1 skipped when Postgres port 5432 is offline, 0 failures)**.
2. **Frontend Web Tests:**
   ```powershell
   npm test --prefix apps/web
   ```
   *Result:* **All 9 test suites passed (Guava labels, produce taxonomy, uncertainty thresholds)**.

---

## 5. Scientific, Regulatory & Academic Integrity Disclosures

In accordance with project guidelines:

1. **Uncalibrated Softmax Heuristic:**
   - Raw softmax scores produced by the ResNet18 model are displayed with an explicit disclaimer: *"Softmax output scores are uncalibrated heuristic scores, not statistical probabilities."*
   - Scores must not be interpreted as mathematically calibrated confidence intervals without formal temperature scaling.
2. **Maturity-Only Scope Limitation:**
   - The vision pipeline evaluates exterior visual ripeness stages (*Green*, *Mature Green*, *Ripe*).
   - It does **not** evaluate internal flesh condition, fungal or bacterial infections, pesticide residues, food-safety compliance, or commercial statutory grade standards.
3. **Lot-Level Scope:**
   - Intake evaluations are performed on representative sample fruit specimens from an incoming crate or lot. The system does not claim or attempt to track individual fruits.
4. **Synthetic Telemetry Transparency:**
   - Telemetry logs demonstrate cold-chain monitoring logic (4.0°C–8.0°C window) and LSTM arrival risk alerting. They represent research simulations and are not connected to physical onboard hardware.

---

## 6. How to Run the Mobile Application

### Prerequisites
1. Start the FastAPI backend with Guava model enabled:
   ```powershell
   # From Agritech_ root:
   $env:TARGET_CROP="guava"
   $env:GUAVA_MODEL_ACTIVATED="true"
   .\.venv\Scripts\uvicorn.exe app.main:app --app-dir backend --host 0.0.0.0 --port 8000
   ```
   Verify at `http://127.0.0.1:8000/health`.

### Running on Android Emulator
1. Launch an Android Virtual Device (AVD) from Android Studio.
2. Run the Flutter app with emulator host mapping:
   ```powershell
   cd apps/mobile
   flutter run -d emulator-5554 --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
   ```
   *(Or launch without arguments and use the default `10.0.2.2:8000` emulator mapping).*

### Running on a Physical Android Device
1. Enable **Developer Options** and **USB Debugging** on your Android phone.
2. Connect phone via USB or Wi-Fi debugging and confirm device detection:
   ```powershell
   adb devices
   ```
3. Find your PC's LAN IP address via `ipconfig` (e.g., `192.168.1.50`).
4. Ensure Windows Defender Firewall allows incoming connections on port `8000`.
5. Run the app:
   ```powershell
   cd apps/mobile
   flutter run -d <DEVICE_ID> --dart-define=API_BASE_URL=http://192.168.1.50:8000/api/v1
   ```
6. Alternatively, install the pre-built debug APK directly via ADB:
   ```powershell
   adb install apps/mobile/build/app/outputs/flutter-apk/app-debug.apk
   ```
   Once installed, tap the settings icon in the app bar to set the PC's LAN IP.

---

## 7. Known Limitations & Future Work

1. **Offline Telemetry Queue:**
   - The current MVP transmits readings directly over HTTP. If connectivity is severed in rural transit corridors, readings fail immediately. Implementing a local SQLite / Hive offline sync queue will allow field loggers to cache points offline and sync upon reconnecting.
2. **WebSocket Live Feed:**
   - The mobile app currently utilizes REST polling and user-triggered refresh. Connecting the Flutter client to the `/api/v1/ws/shipments` gateway (restored in Phase 9) will enable real-time telemetry streaming and push alerts.
3. **Kinnow Production Weights:**
   - The backend currently runs the validated Guava ResNet18 model. When Kinnow weights are trained and verified, the mobile app is already architected to display Kinnow classes via dynamic metadata from `GET /api/v1/cnn/status`.
