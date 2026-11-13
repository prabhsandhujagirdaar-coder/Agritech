"""
AgriChain AI — Comprehensive WebSocket Verification Script
Tests:
1. Connection establishment & initial handshake
2. Heartbeat Ping / Pong exchange
3. Real-time broadcast delivery when a shipment is created and telemetry is added
"""
import asyncio
import json
import urllib.request
import websockets

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
WS_URI = f"ws://{BACKEND_HOST}:{BACKEND_PORT}/api/v1/ws/shipments"
HTTP_BASE = f"http://{BACKEND_HOST}:{BACKEND_PORT}/api/v1"

def trigger_http_post(url_path: str, data: dict):
    req = urllib.request.Request(
        f"{HTTP_BASE}{url_path}",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        return json.loads(resp.read().decode("utf-8"))

async def test_full_websocket_lifecycle():
    print(f"1. Connecting to WebSocket gateway at {WS_URI}...")
    async with websockets.connect(WS_URI, ping_interval=20) as ws:
        # Step 1: Receive greeting
        greeting_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
        greeting = json.loads(greeting_raw)
        print(f"   [GREETING RECEIVED]: event='{greeting.get('event')}', message='{greeting.get('message')}'")
        assert greeting.get("event") == "connected", "Initial event must be 'connected'"

        # Step 2: Heartbeat ping/pong
        print("2. Testing Heartbeat Ping/Pong...")
        await ws.send(json.dumps({"type": "ping"}))
        pong_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
        pong = json.loads(pong_raw)
        print(f"   [PONG RECEIVED]: type='{pong.get('type')}', timestamp='{pong.get('timestamp')}'")
        assert pong.get("type") == "pong", "Response type must be 'pong'"

        # Step 3: Real-time broadcast on shipment creation
        print("3. Testing real-time broadcast delivery during shipment creation...")
        test_shipment_data = {
            "produce_type": "Guava",
            "origin": "Abohar Nursery Hub",
            "destination": "Jalandhar Cold Terminal",
            "quantity": 520.0,
            "status": "created"
        }

        # Trigger HTTP POST in a thread so WebSocket stays listening
        loop = asyncio.get_running_loop()
        created_shipment = await loop.run_in_executor(
            None,
            lambda: trigger_http_post("/shipments", test_shipment_data)
        )
        shipment_id = created_shipment["id"]
        print(f"   [HTTP POST CREATED]: id='{shipment_id}', origin='{created_shipment['origin']}'")

        # Await real-time broadcast on WebSocket
        broadcast_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
        broadcast = json.loads(broadcast_raw)
        print(f"   [WS BROADCAST RECEIVED]: event='{broadcast.get('event')}', shipment_id='{broadcast.get('data', {}).get('id')}'")
        assert broadcast.get("event") == "shipment_created", f"Expected 'shipment_created', got {broadcast.get('event')}"
        assert broadcast.get("data", {}).get("id") == shipment_id, "Broadcast shipment ID mismatch"

        # Step 4: Real-time broadcast on telemetry addition
        print("4. Testing real-time broadcast delivery during telemetry addition...")
        telemetry_payload = {
            "temperature": 5.9,
            "humidity": 87.2,
            "sensor_id": "SNS-WS-01",
            "location": "Bathinda Bypass"
        }
        added_telemetry = await loop.run_in_executor(
            None,
            lambda: trigger_http_post(f"/shipments/{shipment_id}/telemetry", telemetry_payload)
        )
        print(f"   [HTTP POST TELEMETRY]: id='{added_telemetry['id']}', temp={added_telemetry['temperature']}C")

        # Await real-time telemetry broadcast
        telemetry_ws_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
        telemetry_ws = json.loads(telemetry_ws_raw)
        print(f"   [WS BROADCAST RECEIVED]: event='{telemetry_ws.get('event')}', reading_id='{telemetry_ws.get('data', {}).get('id')}'")
        assert telemetry_ws.get("event") == "telemetry_update", f"Expected 'telemetry_update', got {telemetry_ws.get('event')}"
        assert telemetry_ws.get("data", {}).get("temperature") == 5.9

        print("\n[ALL WEBSOCKET TESTS PASSED]: Connection, Ping/Pong, Shipment Creation Broadcast, and Telemetry Broadcast fully verified!")
        return True

if __name__ == "__main__":
    success = asyncio.run(test_full_websocket_lifecycle())
    exit(0 if success else 1)
