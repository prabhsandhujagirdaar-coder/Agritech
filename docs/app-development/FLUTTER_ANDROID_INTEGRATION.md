# AgriChain AI — Flutter Android Integration & Mobile Architecture Guide

## 1. Overview
The **AgriChain AI Mobile Application** (`apps/mobile/`) is designed for field-level intake inspectors, refrigerated truck drivers, and packhouse operators across the Punjab Kinnow citrus belt (Abohar, Fazilka, Hoshiarpur).

This document outlines the networking architecture, device compatibility, API contracts, image ingest pipelines, and offline-resilience strategies for Android.

---

## 2. Android Device & Emulator Networking

A common pitfall in containerized development is attempting to use `localhost` or Docker-internal service names (e.g. `http://backend:8000`) from an Android device or emulator. The Android OS runs in its own network namespace:

### 2.1 Android Emulator (AVD)
The Android Virtual Device emulator routes its host loopback via `10.0.2.2`.
- **Backend API Base URL**: `http://10.0.2.2:8000/api/v1`
- **WebSocket Feed URL**: `ws://10.0.2.2:8000/api/v1/ws/shipments`
- **Next.js Web Portal (if webview)**: `http://10.0.2.2:3000`

### 2.2 Physical Android Device (USB Debugging / Wi-Fi)
Physical Android devices cannot access `10.0.2.2`. They must connect to the development host's Local Area Network (LAN) IP.
- Identify your host IP via PowerShell: `ipconfig` (e.g., `192.168.1.50`).
- Ensure Windows Defender Firewall allows inbound traffic on port `8000`.
- **Backend API Base URL**: `http://192.168.1.50:8000/api/v1`
- **WebSocket Feed URL**: `ws://192.168.1.50:8000/api/v1/ws/shipments`

> [!WARNING]
> Never configure Docker internal hostnames like `http://backend:8000` inside Flutter Dart code. Docker bridge networks are isolated from physical and emulated mobile devices unless routed through an exposed host port.

---

## 3. Flutter Environment Configuration Pattern

In Dart / Flutter, configure environments using compile-time environment variables (`--dart-define`):

```dart
class AppConfig {
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000/api/v1',
  );

  static const String wsUrl = String.fromEnvironment(
    'WS_URL',
    defaultValue: 'ws://10.0.2.2:8000/api/v1/ws/shipments',
  );
}
```

Run via Flutter CLI:
```powershell
# For Android Emulator
flutter run -d emulator-5554 --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1

# For Physical Phone
flutter run -d <DEVICE_ID> --dart-define=API_BASE_URL=http://192.168.1.50:8000/api/v1
```

---

## 4. API Endpoints & Contract Compatibility

### 4.1 Image Intake & Quality Classification
- **Endpoint**: `POST /api/v1/cnn/predict`
- **Content-Type**: `multipart/form-data`
- **Field Name**: `file` (Binary image bytes: JPEG or PNG)
- **Optional Form Field**: `crop_type="kinnow"`

#### Error Handling (Scientific Integrity):
If a Kinnow-specific model checkpoint is not deployed in `ml/artifacts/best_kinnow_resnet18.pth`, the backend strictly returns **HTTP 503 Service Unavailable**:
```json
{
  "detail": "Kinnow quality model is unavailable or in development. No weights loaded."
}
```
**Flutter Implementation Requirement**: The Flutter app must catch `503` responses and display an explicit diagnostic banner ("Kinnow AI model offline — manual grade entry required") rather than crashing or showing a generic network failure.

### 4.2 Telemetry Sequences & Spoilage Prediction
- **Endpoint**: `POST /api/v1/telemetry/predict`
- **Payload**:
```json
{
  "shipment_id": "SHP-ABOHAR-001",
  "readings": [
    {
      "timestamp": "2026-10-21T06:00:00Z",
      "temperature": 4.2,
      "humidity": 88.5,
      "co2": 420.0,
      "ethylene": 0.04
    }
  ]
}
```
- **Response**:
```json
{
  "risk_score": 0.12,
  "risk_level": "low",
  "shelf_life_hours": 168.0,
  "model_version": "lstm-kinnow-v1"
}
```

### 4.3 Real-Time WebSocket Telemetry
- **Endpoint**: `GET /api/v1/ws/shipments` (WebSocket upgrade)
- **Protocol**: Raw JSON broadcast with automatic ping/pong keepalive every 30 seconds.
- **Event Types**: `shipment_created`, `shipment_update`, `telemetry_update`, `waypoint_update`.

---

## 5. Offline Capabilities & Local Caching
In rural transit corridors across Punjab (e.g. Abohar to Bathinda bypass):
1. **Local SQLite / Hive Store**: Telemetry sampled from BLE temperature data loggers must be cached locally if cellular reception is lost.
2. **Batch Ingestion**: Once connectivity is restored, cached points are dispatched in bulk via `POST /api/v1/shipments/{id}/telemetry`.
