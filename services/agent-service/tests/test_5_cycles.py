import os
import sys
import time
import requests
import json

# Ensure UTF-8 output encoding for Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:8000"

# Output directories to save generated reports
PROJECT_REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "reports"))
ARTIFACT_REPORTS_DIR = r"C:\Users\ashut\.gemini\antigravity-ide\brain\e7c9f2ae-2708-499a-9a7e-8827195aebaa\reports"

os.makedirs(PROJECT_REPORTS_DIR, exist_ok=True)
os.makedirs(ARTIFACT_REPORTS_DIR, exist_ok=True)

# Boundary-pushing test targets across 5 cycles
HARD_TEST_CYCLES = [
    {
        "cycle": 1,
        "name": "Nested Route & Dynamic Query Parameters",
        "url": "https://httpbin.org/anything/users/123/orders/999?filter=active&sort=desc",
        "max_pages": 3,
        "prefix": "cycle_1_httpbin"
    },
    {
        "cycle": 2,
        "name": "Scheme-less Host & AXTree DOM Distillation",
        "url": "example.com",  # Missing https:// scheme!
        "max_pages": 2,
        "prefix": "cycle_2_example"
    },
    {
        "cycle": 3,
        "name": "Nested Resource Route Parameterization & List Arrays",
        "url": "https://jsonplaceholder.typicode.com/posts/1/comments",
        "max_pages": 2,
        "prefix": "cycle_3_jsonplaceholder"
    },
    {
        "cycle": 4,
        "name": "Non-Standard HTTP Status Codes & Headers",
        "url": "https://httpbin.org/status/201",
        "max_pages": 2,
        "prefix": "cycle_4_httpbin_status"
    },
    {
        "cycle": 5,
        "name": "Complex Pagination API Payload & Triple Exporters",
        "url": "https://reqres.in/api/users?page=2",
        "max_pages": 3,
        "prefix": "cycle_5_reqres"
    }
]


def save_report_file(prefix: str, suffix: str, content: str):
    filename = f"{prefix}_{suffix}"
    
    # Save to project backend/reports/
    p_path = os.path.join(PROJECT_REPORTS_DIR, filename)
    with open(p_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Save to artifact brain directory/reports/
    a_path = os.path.join(ARTIFACT_REPORTS_DIR, filename)
    with open(a_path, "w", encoding="utf-8") as f:
        f.write(content)

    return p_path, a_path


def run_hard_5_cycle_tests():
    print("==========================================================================")
    print("[START] STARTING CONTINUOUS 5-CYCLE PIPELINE TESTS & REPORT GENERATION")
    print(f"[PATH] Saving Reports to: {PROJECT_REPORTS_DIR}")
    print("==========================================================================\n")

    generated_report_files = []

    for tc in HARD_TEST_CYCLES:
        cycle_num = tc["cycle"]
        name = tc["name"]
        raw_url = tc["url"]
        max_pages = tc["max_pages"]
        prefix = tc["prefix"]

        print(f"==========================================================================")
        print(f"[*] CYCLE {cycle_num}/5: {name.upper()}")
        print(f"    Input Target URL: '{raw_url}' (Max Pages: {max_pages})")
        print(f"==========================================================================")

        # 1. Start Crawl Session & Test URL Scheme Auto-Repair
        start_res = requests.post(
            f"{BASE_URL}/api/v1/crawls/start",
            json={"url": raw_url, "max_pages": max_pages, "headless": True}
        )
        assert start_res.status_code == 200, f"Cycle {cycle_num} Start Failed: {start_res.text}"
        start_data = start_res.json()
        session_id = start_data["session_id"]
        sanitized_url = start_data["target_url"]

        print(f"  [1/6] POST /api/v1/crawls/start -> 200 OK | Session ID: {session_id}")
        print(f"        Sanitized Target URL: '{sanitized_url}'")

        # 2. Poll Status until completion
        completed = False
        final_session_data = None
        for poll_idx in range(15):
            time.sleep(2)
            status_res = requests.get(f"{BASE_URL}/api/v1/crawls/{session_id}/status")
            assert status_res.status_code == 200, f"Cycle {cycle_num} Poll #{poll_idx+1} Failed"
            final_session_data = status_res.json()
            curr_status = final_session_data.get("status")
            print(f"  [2/6] GET /api/v1/crawls/{session_id}/status (Poll #{poll_idx+1}) -> {curr_status}")
            if curr_status in ["completed", "failed"]:
                completed = True
                break

        assert completed and final_session_data["status"] == "completed", f"Cycle {cycle_num} failed"

        # 3. Save & Validate OpenAPI 3.0.3 Spec
        openapi_res = requests.get(f"{BASE_URL}/api/v1/reports/{session_id}/export?format=openapi")
        assert openapi_res.status_code == 200
        openapi_text = openapi_res.text
        p_openapi, _ = save_report_file(prefix, "openapi.json", openapi_text)
        print(f"  [3/6] Saved OpenAPI Spec -> {p_openapi}")

        # 4. Save & Validate Postman Collection v2.1
        postman_res = requests.get(f"{BASE_URL}/api/v1/reports/{session_id}/export?format=postman")
        assert postman_res.status_code == 200
        postman_text = postman_res.text
        p_postman, _ = save_report_file(prefix, "postman.json", postman_text)
        print(f"  [4/6] Saved Postman Collection -> {p_postman}")

        # 5. Save & Validate Markdown API Docs
        md_res = requests.get(f"{BASE_URL}/api/v1/reports/{session_id}/export?format=markdown")
        assert md_res.status_code == 200
        md_text = md_res.text
        p_md, _ = save_report_file(prefix, "API_DOCS.md", md_text)
        print(f"  [5/6] Saved Markdown Documentation -> {p_md}")

        generated_report_files.append({
            "cycle": cycle_num,
            "target": sanitized_url,
            "openapi": p_openapi,
            "postman": p_postman,
            "markdown": p_md
        })

        # 6. Delete Session
        del_res = requests.delete(f"{BASE_URL}/api/v1/crawls/{session_id}")
        assert del_res.status_code == 200
        print(f"  [6/6] Session {session_id} cleaned up.")
        print(f"[SUCCESS] CYCLE {cycle_num}/5 REPORTS SAVED SUCCESSFULLY!\n")

    print("==========================================================================")
    print("🎉 ALL 15 REPORT FILES (5 OpenAPI, 5 Postman, 5 Markdown) GENERATED!")
    print("==========================================================================")


if __name__ == "__main__":
    run_hard_5_cycle_tests()
