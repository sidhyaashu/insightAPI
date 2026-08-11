import time
import requests
import json

BASE_URL = "http://localhost:8000"

def test_endpoints():
    print("--- 1. Testing Root Endpoint GET / ---")
    r = requests.get(f"{BASE_URL}/")
    print(f"Status: {r.status_code}, Response: {r.json()}")
    assert r.status_code == 200

    print("\n--- 2. Testing Health Endpoint GET /health ---")
    r = requests.get(f"{BASE_URL}/health")
    print(f"Status: {r.status_code}, Response: {r.json()}")
    assert r.status_code == 200

    print("\n--- 3. Testing Docs Endpoint GET /docs ---")
    r = requests.get(f"{BASE_URL}/docs")
    print(f"Status: {r.status_code}")
    assert r.status_code == 200

    print("\n--- 4. Testing Start Crawl POST /api/v1/crawls/start ---")
    payload = {"url": "https://httpbin.org/get", "max_pages": 2, "headless": True}
    r = requests.post(f"{BASE_URL}/api/v1/crawls/start", json=payload)
    print(f"Status: {r.status_code}, Response: {r.json()}")
    assert r.status_code == 200
    data = r.json()
    session_id = data["session_id"]

    print(f"\n--- 5. Polling Crawl Status GET /api/v1/crawls/{session_id}/status ---")
    for i in range(15):
        time.sleep(2)
        r = requests.get(f"{BASE_URL}/api/v1/crawls/{session_id}/status")
        status_data = r.json()
        status = status_data.get("status")
        print(f"Poll #{i+1}: Status = {status}")
        if status in ["completed", "failed"]:
            print(f"Final Session Data: {json.dumps(status_data, indent=2)}")
            break

    print(f"\n--- 6. Testing Export Endpoint GET /api/v1/reports/{session_id}/export ---")
    for fmt in ["openapi", "postman", "markdown"]:
        r = requests.get(f"{BASE_URL}/api/v1/reports/{session_id}/export?format={fmt}")
        print(f"Format: {fmt}, Status: {r.status_code}, Content Length: {len(r.content)}")
        assert r.status_code == 200

if __name__ == "__main__":
    test_endpoints()
