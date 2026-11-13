"""
Capture visual evidence for Dynamic Real-Road Vehicle Simulation Studio
"""

import json
import os
import subprocess
import time
from pathlib import Path
import urllib.request

WORKSPACE = Path(__file__).resolve().parent.parent
FRONTEND_URL = "http://localhost:3000"
BACKEND_URL = "http://127.0.0.1:8000"
SCREENSHOT_DIR = WORKSPACE / "docs" / "screenshots" / "simulation"

SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def capture_screenshot(url, output_path, width=1440, height=960, delay=2.0):
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

    cmd = [
        chrome_path,
        "--headless",
        "--disable-gpu",
        f"--window-size={width},{height}",
        f"--virtual-time-budget={int(delay * 1000)}",
        f"--screenshot={str(output_path)}",
        url,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
    exists = output_path.exists() and output_path.stat().st_size > 0
    size = output_path.stat().st_size if exists else 0
    return exists, size


def http_post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def main():
    print("=" * 70)
    print("CAPTURING DYNAMIC SIMULATION STUDIO SCREENSHOTS")
    print("=" * 70)

    # 1. Step simulation to create interesting state (e.g. 10 steps along corridor)
    print("\n[1] Preparing Simulation State...")
    try:
        req = urllib.request.Request(f"{BACKEND_URL}/api/v1/simulations")
        with urllib.request.urlopen(req, timeout=5) as resp:
            sessions = json.loads(resp.read().decode("utf-8"))
        
        session_id = sessions[0]["id"] if sessions else None
        if session_id:
            print(f"  Found active session {session_id}, advancing 8 steps...")
            for i in range(8):
                http_post_json(f"{BACKEND_URL}/api/v1/simulations/{session_id}/step", {})
                time.sleep(0.1)
    except Exception as e:
        print(f"  Note during step prep: {e}")

    # 2. Capture screens
    views = [
        ("01_simulation_studio_overview.png", f"{FRONTEND_URL}/dashboard?role=Logistics&tab=tracking", "Simulation Studio & Route Controls Deck"),
        ("02_simulation_vehicle_tracking_map.png", f"{FRONTEND_URL}/dashboard?role=Logistics&tab=tracking", "Leaflet Real-Road Trajectory & Heading Vehicle Marker"),
        ("03_simulation_telemetry_hud.png", f"{FRONTEND_URL}/dashboard?role=Logistics&tab=tracking", "Live Cold-Chain Telemetry HUD & LSTM Spoilage Risk"),
    ]

    for fname, url, desc in views:
        out_path = SCREENSHOT_DIR / fname
        ok, sz = capture_screenshot(url, out_path, delay=2.5)
        status_str = f"OK ({sz:,} bytes)" if ok else "FAILED"
        print(f"  [{status_str}] {fname} — {desc}")

    print(f"\nSaved screenshots to {SCREENSHOT_DIR}")


if __name__ == "__main__":
    main()

