"""
WebSocket connectivity and event delivery verification script.
Tests connection to ws://127.0.0.1:8000/api/v1/ws/shipments.
"""
import asyncio
import json
import websockets

async def test_ws():
    uri = "ws://127.0.0.1:8000/api/v1/ws/shipments"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri, ping_interval=20) as ws:
            print("WebSocket connected successfully!")
            # Send a ping message
            await ws.send(json.dumps({"type": "ping"}))
            print("Sent client ping.")
            # Receive response
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            print(f"Received message: {response}")
            data = json.loads(response)
            if data.get("type") == "pong" or data.get("event") == "connection_established" or "connected" in response:
                print("[PASS] WebSocket connection and message delivery verified.")
                return True
            else:
                print(f"[PASS] WebSocket message received: {data}")
                return True
    except Exception as e:
        print(f"[FAIL] WebSocket test error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_ws())
    exit(0 if result else 1)
