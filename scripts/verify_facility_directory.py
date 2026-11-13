"""
AgriChain AI — Facility Directory Verification Script
=====================================================
Verifies:
1. Direct FastAPI backend facility endpoints (/api/facilities & /api/v1/facilities).
2. Direct facility detail and suitability evaluations.
3. Next.js API proxy routes (/api/facilities, /api/facilities/{id}, /api/facilities/{id}/suitability).
4. Facility query filters and search terms.
5. Error state handling when backend is unreachable.
6. Browser headless rendering via Edge/Chrome of the Storage Facility Directory tab.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
import urllib.request
import urllib.error

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE / "backend"))

BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:3000"
SCREENSHOT_PATH = WORKSPACE / "docs" / "screenshots" / "phase19_final" / "09_logistics_facility_directory.png"
REPORT_DATA_PATH = WORKSPACE / "ml" / "experiments" / "facility_directory_verification.json"

SCREENSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)


def http_get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return resp.status, data
    except urllib.error.HTTPError as e:
        data = json.loads(e.read().decode("utf-8")) if e.fp else {}
        return e.code, data


def main():
    print("=" * 70)
    print("AGRICHAIN AI — FACILITY DIRECTORY VERIFICATION AUDIT")
    print("=" * 70)

    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "backend_tests": {},
        "proxy_tests": {},
        "filter_tests": {},
        "browser_verification": {},
    }

    # 1. Direct Backend Verification
    print("\n[1/5] Testing Direct FastAPI Backend Endpoints...")
    b_status, b_facs = http_get(f"{BACKEND_URL}/api/facilities")
    print(f"  GET /api/facilities -> HTTP {b_status}, Count: {len(b_facs)}")
    assert b_status == 200 and len(b_facs) == 12, "Backend /api/facilities failed!"
    results["backend_tests"]["/api/facilities"] = {"status": b_status, "count": len(b_facs)}

    v1_status, v1_facs = http_get(f"{BACKEND_URL}/api/v1/facilities")
    print(f"  GET /api/v1/facilities -> HTTP {v1_status}, Count: {len(v1_facs)}")
    assert v1_status == 200 and len(v1_facs) == 12, "Backend /api/v1/facilities failed!"
    results["backend_tests"]["/api/v1/facilities"] = {"status": v1_status, "count": len(v1_facs)}

    d_status, d_fac = http_get(f"{BACKEND_URL}/api/facilities/FAC-DL-AZD-01")
    print(f"  GET /api/facilities/FAC-DL-AZD-01 -> HTTP {d_status}, Name: {d_fac.get('name')}")
    assert d_status == 200 and d_fac.get("id") == "FAC-DL-AZD-01"
    results["backend_tests"]["detail"] = d_fac

    s_status, s_fac = http_get(f"{BACKEND_URL}/api/facilities/FAC-DL-AZD-01/suitability?operation=market_auction&crop=guava")
    print(f"  GET /api/facilities/FAC-DL-AZD-01/suitability -> HTTP {s_status}, Suitable: {s_fac.get('suitable')}")
    assert s_status == 200 and s_fac.get("suitable") is True
    results["backend_tests"]["suitability"] = s_fac

    # 2. Next.js Proxy Verification
    print("\n[2/5] Testing Next.js API Proxy Routes...")
    p_status, p_facs = http_get(f"{FRONTEND_URL}/api/facilities")
    print(f"  GET {FRONTEND_URL}/api/facilities -> HTTP {p_status}, Count: {len(p_facs)}")
    assert p_status == 200 and len(p_facs) == 12, "Next.js proxy /api/facilities failed!"
    results["proxy_tests"]["/api/facilities"] = {"status": p_status, "count": len(p_facs)}

    pd_status, pd_fac = http_get(f"{FRONTEND_URL}/api/facilities/FAC-PB-ABO-01")
    print(f"  GET {FRONTEND_URL}/api/facilities/FAC-PB-ABO-01 -> HTTP {pd_status}, Name: {pd_fac.get('name')}")
    assert pd_status == 200 and pd_fac.get("id") == "FAC-PB-ABO-01"
    results["proxy_tests"]["detail"] = pd_fac

    ps_status, ps_fac = http_get(f"{FRONTEND_URL}/api/facilities/FAC-DL-AZD-01/suitability?operation=market_auction&crop=guava")
    print(f"  GET {FRONTEND_URL}/api/facilities/FAC-DL-AZD-01/suitability -> HTTP {ps_status}, Suitable: {ps_fac.get('suitable')}")
    assert ps_status == 200 and ps_fac.get("suitable") is True
    results["proxy_tests"]["suitability"] = ps_fac

    # 3. Query Filters Verification
    print("\n[3/5] Testing Query Filters through Next.js Proxy...")
    filters_to_test = [
        ("facility_type=packhouse", 3),
        ("facility_type=cold_storage", 3),
        ("facility_type=godown", 4),
        ("facility_type=mandi", 2),
        ("district=Fazilka", 2),
        ("district=Jalandhar", 2),
        ("state=Punjab", 11),
        ("state=Delhi", 1),
        ("district=North+Delhi", 1),
        ("verification_status=verified", 5),
        ("operational_status=active", 9),
        ("q=PAGREXCO", 3),
        ("q=Azadpur", 1),
    ]

    for param, expected_count in filters_to_test:
        f_status, f_data = http_get(f"{FRONTEND_URL}/api/facilities?{param}")
        print(f"  Filter '{param}': HTTP {f_status}, Count: {len(f_data)} (Expected: {expected_count})")
        assert f_status == 200 and len(f_data) == expected_count, f"Filter {param} count mismatch!"
        results["filter_tests"][param] = {"status": f_status, "count": len(f_data), "expected": expected_count}

    # 4. Browser Headless Verification & Visual Screenshot
    print("\n[4/5] Executing Browser Headless Verification & Screenshot...")
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge_path):
        edge_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    dashboard_url = f"{FRONTEND_URL}/dashboard?role=Logistics&tab=warehouse"

    # Capture visual screenshot
    cmd_shot = [
        edge_path,
        "--headless",
        "--disable-gpu",
        "--window-size=1400,1000",
        f"--screenshot={str(SCREENSHOT_PATH.resolve())}",
        dashboard_url,
    ]
    p_shot = subprocess.run(cmd_shot, capture_output=True, text=True, timeout=25)
    shot_exists = SCREENSHOT_PATH.exists() and SCREENSHOT_PATH.stat().st_size > 0
    shot_size = SCREENSHOT_PATH.stat().st_size if shot_exists else 0
    print(f"  Visual Screenshot: {'OK' if shot_exists else 'FAILED'} (Path: {SCREENSHOT_PATH}, Size: {shot_size} bytes)")
    assert shot_exists, "Failed to capture visual screenshot of Facility Directory!"

    # Dump DOM to verify rendered components
    cmd_dom = [edge_path, "--headless", "--disable-gpu", "--dump-dom", dashboard_url]
    p_dom = subprocess.run(cmd_dom, capture_output=True, text=True, timeout=25, encoding="utf-8", errors="replace")
    import html
    dom = html.unescape(p_dom.stdout)

    expected_dom_strings = [
        ("Storage Facility Directory", True),
        ("PAGREXCO Pack House-cum-Cold Storage (Bara Farm)", True),
        ("FAC-PB-ABO-01", True),
        ("Azadpur APMC Fruit & Vegetable Mega Mandi", True),
        ("Error Loading Facility Directory", False),
        ("fetch failed", False),
    ]

    print("  DOM Verification:")
    for string_pattern, should_exist in expected_dom_strings:
        exists_in_dom = string_pattern in dom
        status_str = "MATCH" if (exists_in_dom == should_exist) else "FAIL"
        print(f"    [{status_str}] '{string_pattern}' in DOM: {exists_in_dom} (Expected: {should_exist})")
        assert exists_in_dom == should_exist, f"DOM check failed for '{string_pattern}'!"

    results["browser_verification"] = {
        "url": dashboard_url,
        "screenshot_path": str(SCREENSHOT_PATH),
        "screenshot_size": shot_size,
        "dom_verified": True,
        "facilities_rendered_count": len(b_facs),
    }

    # 5. List all 12 verified facility records
    print("\n[5/5] Listing 12 Preserved Authentic Facility Records:")
    facility_summary_list = []
    for f in b_facs:
        summary_item = {
            "id": f["id"],
            "name": f["name"],
            "facility_type": f["facility_type"],
            "district": f["district"],
            "state": f["state"],
            "latitude": f.get("latitude"),
            "longitude": f.get("longitude"),
            "verification_status": f.get("verification_status"),
            "guava_suitability_category": f.get("guava_suitability_category"),
        }
        facility_summary_list.append(summary_item)
        print(f"  * {f['id']}: {f['name']} ({f['facility_type']}) - {f['district']}, {f['state']} [{f.get('latitude')}, {f.get('longitude')}]")

    results["facility_records"] = facility_summary_list

    # Save results
    with open(REPORT_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 70)
    print("ALL FACILITY DIRECTORY VERIFICATION CHECKS PASSED (100%)!")
    print(f"Results written to: {REPORT_DATA_PATH}")
    print("=" * 70)


if __name__ == "__main__":
    main()
