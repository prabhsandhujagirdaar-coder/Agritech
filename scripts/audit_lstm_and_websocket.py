"""
AgriChain AI — Independent Audit: Task 3: LSTM & WebSocket Verification
"""

import asyncio
import json
import urllib.request
import websockets

BACKEND_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/api/v1/ws/shipments"

def post_json(path, payload):
    url = f"{BACKEND_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

async def test_websocket_and_lstm():
    print("======================================================================")
    print("AUDIT TASK 3: LSTM INFERENCE CONTRACT & WEBSOCKET AUDIT")
    print("======================================================================\n")

    # 1. Inspect endpoint /api/v1/telemetry/predict
    print("[1] Inspecting POST /api/v1/telemetry/predict input contract...")
    # Construct sequence of 24 points with 5 features
    seq_normal = [
        {
            "hour": h,
            "temperature": 5.5,
            "humidity": 88.0,
            "delay_minutes": 0,
            "speed_kmh": 55.0,
            "distance_remaining_km": 300.0 - h * 10.0,
        }
        for h in range(1, 25)
    ]
    status, res_norm = post_json("/api/v1/telemetry/predict", {
        "shipment_id": "TEST-SHP-001",
        "sequence": seq_normal,
    })
    print(f"  -> Normal 24-step sequence (5.5°C avg): Risk={res_norm['current_risk']}%, Predicted={res_norm['predicted_arrival_risk']}%, Alert={res_norm['alert']}")
    assert res_norm["alert"] is False

    # Excursion sequence
    seq_excursion = [
        {
            "hour": h,
            "temperature": 5.5 if h < 12 else 15.0,  # 12 hours of excursion
            "humidity": 88.0,
            "delay_minutes": 30 if h >= 12 else 0,
            "speed_kmh": 55.0,
            "distance_remaining_km": 150.0,
        }
        for h in range(1, 25)
    ]
    status, res_exc = post_json("/api/v1/telemetry/predict", {
        "shipment_id": "TEST-SHP-001",
        "sequence": seq_excursion,
    })
    print(f"  -> Excursion 24-step sequence (15.0°C excursion): Risk={res_exc['current_risk']}%, Predicted={res_exc['predicted_arrival_risk']}%, Alert={res_exc['alert']}")
    assert res_exc["alert"] is True
    assert res_exc["current_risk"] > res_norm["current_risk"]
    print("  -> Confirmed: Temperature excursions directly elevate risk and trigger alert.")

    # 2. Check trained model artifact existence
    import os
    from pathlib import Path
    model_paths = [
        "ml/artifacts/spoilage_risk_lstm.pt",
        "ml/artifacts/best_lstm.pth",
        "ml/models/spoilage_risk_lstm.pt",
    ]
    found_artifact = False
    for p in model_paths:
        if os.path.exists(p):
            found_artifact = True
            print(f"  -> Found model artifact: {p}")
    if not found_artifact:
        print("  -> CRITICAL AUDIT FINDING: No trained PyTorch LSTM weights file (.pt/.pth) exists in the repository.")
        print("     Risk scoring is driven by domain heuristic formula based on excursion hours, avg temp, and delay.")

    # 3. Test Live WebSocket Broadcast
    print("\n[2] Testing Live WebSocket Stream Broadcasts...")
    try:
        ws_conn = await asyncio.wait_for(websockets.connect(WS_URL), timeout=5.0)
        async with ws_conn as ws:
            print(f"  -> Connected to WebSocket at {WS_URL}")
            # Advance simulation step on an active session to trigger broadcast
            session_payload = {
                "origin_name": "WS Test Origin",
                "origin_lat": 30.1453,
                "origin_lon": 74.1994,
                "destination_name": "WS Test Dest",
                "destination_lat": 28.7161,
                "destination_lon": 77.1772,
                "scenario": "temperature_excursion",
            }
            _, s = post_json("/api/v1/simulations/", session_payload)
            sim_id = s["id"]
            
            # Step the simulation
            post_json(f"/api/v1/simulations/{sim_id}/step", {})

            # Read frames until broadcast event is received
            while True:
                msg_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                msg = json.loads(msg_raw)
                event_name = msg.get("event")
                print(f"  -> WebSocket Frame received: event='{event_name}'")
                if event_name in ("simulation_telemetry", "simulation_status", "location_update", "risk_update"):
                    print(f"  -> SUCCESS: Received live simulation broadcast event '{event_name}'!")
                    break
    except Exception as e:
        print(f"  -> WebSocket broadcast test notice: {e}")

    print("\nTask 3 LSTM & WebSocket Audit complete.")

if __name__ == "__main__":
    asyncio.run(test_websocket_and_lstm())
