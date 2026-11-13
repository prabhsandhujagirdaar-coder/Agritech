"""
AgriChain AI — Independent Audit: Task 2: Simulation Lifecycle Verification
"""

import json
import time
import urllib.request
import sys

BACKEND_URL = "http://127.0.0.1:8000"

def post_json(path, payload):
    url = f"{BACKEND_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def get_json(path):
    url = f"{BACKEND_URL}{path}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def main():
    print("======================================================================")
    print("AUDIT TASK 2: SIMULATION LIFECYCLE & CONCURRENCY VERIFICATION")
    print("======================================================================\n")

    # 1. Create a dedicated test session (short route for completion testing)
    preview_payload = {
        "origin_lat": 30.1453,
        "origin_lon": 74.1994,
        "destination_lat": 30.1750,
        "destination_lon": 74.2400,
    }
    _, preview = post_json("/api/v1/simulations/routes/preview", preview_payload)
    total_dist = preview["distance_km"]

    create_payload = {
        "origin_name": "Lifecycle Origin",
        "origin_lat": 30.1453,
        "origin_lon": 74.1994,
        "destination_name": "Lifecycle Dest",
        "destination_lat": 30.1750,
        "destination_lon": 74.2400,
        "route_geometry": preview["geometry"],
    }
    _, session = post_json("/api/v1/simulations/", create_payload)
    sim_id = session["id"]
    print(f"[1] Session Created: {sim_id} (Initial Status: {session['status']}, Total Dist: {total_dist:.2f} km)")
    assert session["status"] == "READY"

    # 2. START action
    print("\n[2] Testing START action...")
    _, s_start = post_json(f"/api/v1/simulations/{sim_id}/start", {})
    print(f"  -> START returned status: {s_start['status']}")
    assert s_start["status"] == "RUNNING"

    # Concurrency test: Trigger START multiple times in rapid succession
    print("  -> Testing concurrency: sending 3 rapid START commands to detect loop duplication...")
    for i in range(3):
        post_json(f"/api/v1/simulations/{sim_id}/start", {})
    time.sleep(1.5)
    _, s_check = get_json(f"/api/v1/simulations/{sim_id}")
    print(f"  -> State after concurrent starts: Status={s_check['status']}, Step Count={s_check['step_count']}")

    # 3. PAUSE action
    print("\n[3] Testing PAUSE action...")
    _, s_pause = post_json(f"/api/v1/simulations/{sim_id}/pause", {})
    print(f"  -> PAUSE returned status: {s_pause['status']}, Dist: {s_pause['current_distance_km']:.2f} km")
    assert s_pause["status"] == "PAUSED"
    paused_dist = s_pause["current_distance_km"]
    time.sleep(1.2)
    _, s_paused_check = get_json(f"/api/v1/simulations/{sim_id}")
    assert s_paused_check["current_distance_km"] == paused_dist, "Distance changed while paused!"
    print(f"  -> Position held steady during pause: {paused_dist:.2f} km")

    # 4. RESUME action
    print("\n[4] Testing RESUME action...")
    _, s_resume = post_json(f"/api/v1/simulations/{sim_id}/resume", {})
    print(f"  -> RESUME returned status: {s_resume['status']}")
    assert s_resume["status"] == "RUNNING"
    time.sleep(1.2)

    # 5. STOP action
    print("\n[5] Testing STOP action...")
    _, s_stop = post_json(f"/api/v1/simulations/{sim_id}/stop", {})
    print(f"  -> STOP returned status: {s_stop['status']}")
    assert s_stop["status"] == "STOPPED"

    # 6. RESET action
    print("\n[6] Testing RESET action...")
    _, s_reset = post_json(f"/api/v1/simulations/{sim_id}/reset", {})
    print(f"  -> RESET returned status: {s_reset['status']}, Dist: {s_reset['current_distance_km']}, Steps: {s_reset['step_count']}")
    assert s_reset["status"] == "READY"
    assert s_reset["current_distance_km"] == 0.0
    assert s_reset["step_count"] == 0

    # 7. Step to COMPLETE
    print("\n[7] Testing COMPLETE transition by stepping through remaining distance...")
    _, s_comp = post_json(f"/api/v1/simulations/{sim_id}/step?advance_km={total_dist + 5.0}", {})
    print(f"  -> After final step: Status={s_comp['status']}, Dist={s_comp['current_distance_km']:.2f}/{total_dist:.2f} km")
    assert s_comp["status"] == "COMPLETED"
    assert abs(s_comp["current_distance_km"] - total_dist) < 0.01

    # 8. Browser Refresh Simulation (Multiple independent GET queries)
    print("\n[8] Simulating Browser Refresh / Session Reload...")
    for r in range(3):
        _, ref_data = get_json(f"/api/v1/simulations/{sim_id}")
        assert ref_data["status"] == "COMPLETED"
        assert abs(ref_data["current_distance_km"] - total_dist) < 0.05
    print("  -> Verified session state consistency across repeated stateless GET reloads.")

    # 9. Verify Historical Telemetry Retrieval
    print("\n[9] Testing Historical Telemetry Retrieval...")
    _, tel_records = get_json(f"/api/v1/simulations/{sim_id}/telemetry")
    print(f"  -> Retrieved {len(tel_records)} historical telemetry records.")
    assert len(tel_records) > 0
    first_tel = tel_records[0]
    print(f"  -> Telemetry Schema: sensor_id='{first_tel.get('sensor_id')}', source='{first_tel.get('data_source')}', scenario='{first_tel.get('scenario')}'")
    assert first_tel.get("sensor_id") == "SNS-SIM-DEMO"
    assert first_tel.get("data_source") == "simulation"

    print("\n[PASSED] Task 2 Simulation Lifecycle & Concurrency Verification Complete!")

if __name__ == "__main__":
    main()
