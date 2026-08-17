# InsightAPI AI — Remediation Verification Report

> **Verification Date**: 2026-08-16  
> **Target Scope**: 12 Remediations (7 Critical + 5 Second-Priority) across API Gateway, Core Service, and Agent Service.  
> **Status**: Comprehensive line-by-line static inspection & runtime test verification completed.

---

## Executive Summary Matrix

| ID | Finding & Description | Service | Status | Primary Code Reference | Regression Test |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **F-6** | Billing IDOR in `/payments/usage-records` | Core | **PASS** | [`payments.py:172-195`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/core-service/app/api/v1/endpoints/payments.py#L172-L195) | [`test_payments.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/core-service/tests/test_payments.py) (2/2 Passed) |
| **F-15** | Drift IDOR on `/projects/{id}/drift` & Webhook | Agent | **PASS** | [`drift.py:158-161`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/api/v1/endpoints/drift.py#L158-L161), [`drift.py:220-222`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/api/v1/endpoints/drift.py#L220-L222) | [`test_drift_idor.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/tests/test_drift_idor.py) (3/3 Passed) |
| **F-5** | OAuth CSRF State Token Verification | Core | **PASS** | [`auth.py:183-229`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/core-service/app/api/v1/endpoints/auth.py#L183-L229), [`session_repo.py:56-78`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/core-service/app/repositories/session_repo.py#L56-L78) | [`test_oauth_csrf.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/core-service/tests/test_oauth_csrf.py) (3/3 Passed) |
| **F-41** | Production CORS Misconfiguration | All | **PASS** | [`config.py:12-24`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/core/config.py#L12-L24), [`agent-service/main.py:80-87`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/main.py#L80-L87) | [`test_cors.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/tests/test_cors.py) (2/2 Passed) |
| **F-3** | Gateway WebSocket Upstream URL Scheme | Gateway | **PASS** | [`ws.py:14-26`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/gateway/app/api/v1/endpoints/ws.py#L14-L26) | [`test_ws_proxy.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/gateway/tests/test_ws_proxy.py) (2/2 Passed) |
| **F-20** | Foreign Key Violation on `pattern_id="unknown"` | Agent | **PASS** | [`security_reasoner.py:450-475`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/agents/nodes/security_reasoner.py#L450-L475) | [`test_fk_approval.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/tests/test_fk_approval.py) (1/1 Passed) |
| **F-23** | Sandbox Egress Bypass on Template Paths | Agent | **PASS** | [`executor.py:130-144`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/engine/sandbox/executor.py#L130-L144), [`security_reasoner.py:506-510`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/agents/nodes/security_reasoner.py#L506-L510) | [`test_sandbox_template_path.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/tests/test_sandbox_template_path.py) (2/2 Passed) |
| **F-39** | WebSocket Publish Failure Buffering & UI Flag | Agent/UI | **PARTIAL** | [`crawls.py:122-154`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/api/v1/endpoints/crawls.py#L122-L154), [`crawls.py:616-621`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/api/v1/endpoints/crawls.py#L616-L621) | [`test_ws_publish_resilience.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/tests/test_ws_publish_resilience.py) (1/1 Passed) |
| **F-45** | Celery Worker Liveness & BackgroundTasks Fallback | Agent | **PARTIAL** | [`crawl_tasks.py:44-53`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/tasks/crawl_tasks.py#L44-L53), [`crawls.py:549-565`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/api/v1/endpoints/crawls.py#L549-L565) | [`test_celery_dispatch_fallback.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/tests/test_celery_dispatch_fallback.py) (1/1 Passed) |
| **F-38** | Snapshot Persistence Failure Ordering & Status | Agent | **PASS** | [`crawls.py:295-345`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/api/v1/endpoints/crawls.py#L295-L345) | [`test_snapshot_failure_status.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/tests/test_snapshot_failure_status.py) (1/1 Passed) |
| **F-35** | LLM Budget Bypass when `cost_manager` is None | Agent | **PASS** | [`planner.py:64-75`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/agents/nodes/planner.py#L64-L75), [`vision_planner.py:48-56`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/agents/nodes/vision_planner.py#L48-L56) | [`test_planner_default_cost_manager.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/tests/test_planner_default_cost_manager.py) (1/1 Passed) |
| **F-9** | Internal Session Endpoint Reachable by Users | Gateway/Core | **PASS** | [`proxy.py:36-45`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/gateway/app/api/v1/endpoints/proxy.py#L36-L45), [`internal.py:17-30`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/core-service/app/api/v1/endpoints/internal.py#L17-L30) | [`test_proxy_internal_blocked.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/gateway/tests/test_proxy_internal_blocked.py) (1/1 Passed), [`test_internal_endpoints.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/core-service/tests/test_internal_endpoints.py) (2/2 Passed) |

---

## Detailed Item Verification

### ═══════════════════════════════════════════════════════
### BATCH 1 — CRITICAL (7 Items)
### ═══════════════════════════════════════════════════════

#### 1. F-6 — Billing IDOR (`payments.py:172-195`)
* **Verification Status**: **PASS**
* **Code Reference**: [`services/core-service/app/api/v1/endpoints/payments.py:172-195`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/core-service/app/api/v1/endpoints/payments.py#L172-L195)
* **Executable Logic Findings**:
  - `body.user_id` is never used as the trust source. Line 194 explicitly binds `user_target_id = x_user_id`.
  - Lines 185-192 inspect `body.user_id`:
    ```python
    if body.user_id and body.user_id != x_user_id:
        logger.warning(f"[ABUSE SIGNAL] Billing IDOR attempt: x-user-id header '{x_user_id}' does not match body.user_id '{body.user_id}'")
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Cannot report usage records for a different user.",
        )
    ```
  - The security property holds: No user can report metered usage against another user's Stripe customer account.
* **Test Verification**:
  ```text
  pytest services/core-service/tests/test_payments.py
  ============================= test session starts =============================
  collected 2 items
  tests/test_payments.py ..                                                [100%]
  ============================== 2 passed in 0.80s ==============================
  ```

---

#### 2. F-15 — Drift IDOR (`drift.py:158-161`, `drift.py:220-222`)
* **Verification Status**: **PASS**
* **Code Reference**: [`services/agent-service/app/api/v1/endpoints/drift.py:158-161, 220-222`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/api/v1/endpoints/drift.py#L158-L161)
* **Executable Logic Findings**:
  - `GET /{project_id}/drift` (lines 158-160):
    ```python
    if x_user_id != project_id and (x_user_tier or "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this project.")
    ```
  - `POST /{project_id}/drift/webhook` (lines 220-221):
    ```python
    if x_user_id != project_id and (x_user_tier or "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this project.")
    ```
  - Both endpoints enforce the tenant ownership gate. In addition, `SnapshotRepository.get_latest_crawl_id_for_project` (lines 166-169) and `compare_snapshots` (lines 187-192) filter snapshots strictly by `project_id`.
* **Test Verification**:
  ```text
  pytest services/agent-service/tests/test_drift_idor.py
  ============================= test session starts =============================
  collected 3 items
  services/agent-service/tests/test_drift_idor.py ...                      [100%]
  ============================== 3 passed in 1.22s ==============================
  ```

---

#### 3. F-5 — OAuth CSRF State Token (`auth.py:183-229`, `session_repo.py:56-78`)
* **Verification Status**: **PASS**
* **Code Reference**: [`services/core-service/app/api/v1/endpoints/auth.py:183-229`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/core-service/app/api/v1/endpoints/auth.py#L183-L229), [`session_repo.py:56-78`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/core-service/app/repositories/session_repo.py#L56-L78)
* **Executable Logic Findings**:
  - `GET /github/login` (line 186) and `GET /google/login` (line 200) generate a cryptographically random token via `secrets.token_urlsafe(32)` stored in Redis at `oauth:state:{state}` with a 600-second TTL and embedded in the redirect URL as `&state={state}`.
  - `GET /callback` (lines 222-228) calls `verify_and_consume_oauth_state(state, provider)` before exchanging code.
  - Single-use property: `session_repo.py:77` calls `await redis.delete(key)`. Replaying the same state token a second time returns `False` and raises `HTTPException(400, "Invalid or expired OAuth state parameter (CSRF protection failed)")`.
* **Test Verification**:
  ```text
  pytest services/core-service/tests/test_oauth_csrf.py
  ============================= test session starts =============================
  collected 3 items
  tests/test_oauth_csrf.py ...                                             [100%]
  ============================== 3 passed in 0.91s ==============================
  ```

---

#### 4. F-41 — Production CORS Configuration (`config.py:12-24`, `main.py`)
* **Verification Status**: **PASS**
* **Code Reference**: [`services/agent-service/app/core/config.py:12-24`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/core/config.py#L12-L24), [`services/agent-service/app/main.py:80-87`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/main.py#L80-L87), [`services/gateway/app/main.py:17-23`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/gateway/app/main.py#L17-L23), [`services/core-service/app/main.py:56-62`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/core-service/app/main.py#L56-L62)
* **Executable Logic Findings**:
  - `allow_origins=settings.get_allowed_origins()` is applied consistently across all three services.
  - `ALLOWED_ORIGINS` is defined on `Settings` as `list[str] | str` with default `["http://localhost:3000", "http://localhost", "https://app.insightapi.com"]`.
  - Sourced from `.env.example:14`: `ALLOWED_ORIGINS=http://localhost:3000,http://localhost,https://app.insightapi.com`.
  - Configured origins in production resolve to `['http://localhost:3000', 'http://localhost', 'https://app.insightapi.com']`.
* **Test Verification**:
  ```text
  pytest services/agent-service/tests/test_cors.py
  ============================= test session starts =============================
  collected 2 items
  services/agent-service/tests/test_cors.py ..                             [100%]
  ============================== 2 passed in 1.52s ==============================
  ```

---

#### 5. F-3 — Gateway WebSocket Upstream URL (`ws.py:14-26`)
* **Verification Status**: **PASS**
* **Code Reference**: [`services/gateway/app/api/v1/endpoints/ws.py:14-26`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/gateway/app/api/v1/endpoints/ws.py#L14-L26)
* **Executable Logic Findings**:
  - `build_upstream_ws_url` line 20: `scheme = "wss" if agent_service_url.startswith("https://") else "ws"`.
  - Lines 17-18: Strips any leading `ws/` prefixes to prevent duplicate `/ws/ws/...` paths.
  - Line 24: Correctly appends query string (`?token=...`) if present.
* **Test Verification**:
  ```text
  pytest services/gateway/tests/test_ws_proxy.py
  ============================= test session starts =============================
  collected 2 items
  tests/test_ws_proxy.py ..                                                [100%]
  ============================== 2 passed in 0.27s ==============================
  ```

---

#### 6. F-20 — Foreign Key Violation on `pattern_id="unknown"` (`security_reasoner.py:450-475`)
* **Verification Status**: **PASS**
* **Code Reference**: [`services/agent-service/app/agents/nodes/security_reasoner.py:450-475`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/agents/nodes/security_reasoner.py#L450-L475)
* **Executable Logic Findings**:
  - In `SecurityReasonerNode.process`: When LLM proposes a destructive test case on a cache miss, lines 451-457 execute `persisted_pattern = await cls._upsert_pattern(...)` **before** calling `_queue_approval`.
  - Lines 458-471: `resolved_pattern_id = persisted_pattern.get("id")`. Only if `resolved_pattern_id` is a valid UUID does `_queue_approval` execute.
  - Literal string `"unknown"` is completely eliminated from the approval insertion path.
* **Test Verification**:
  ```text
  pytest services/agent-service/tests/test_fk_approval.py
  ============================= test session starts =============================
  collected 1 item
  services/agent-service/tests/test_fk_approval.py .                       [100%]
  ============================== 1 passed in 4.72s ==============================
  ```

---

#### 7. F-23 — Sandbox Egress Bypass on Template Paths (`executor.py:130-144`, `security_reasoner.py:506-510`)
* **Verification Status**: **PASS**
* **Code Reference**: [`services/agent-service/app/engine/sandbox/executor.py:130-144`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/engine/sandbox/executor.py#L130-L144), [`security_reasoner.py:506-510`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/agents/nodes/security_reasoner.py#L506-L510)
* **Executable Logic Findings**:
  - In `SandboxExecutor.run_test`, lines 139-143 compute `effective_domain = target_domain or urlparse(url).netloc`.
  - Lines 140-143:
    ```python
    if not effective_domain or not effective_domain.strip():
        raise ValueError(
            f"SandboxExecutor: Invalid target URL '{url}'. Absolute URL or target_domain required, got empty domain."
        )
    ```
  - In `security_reasoner.py:506-510`, caller resolves relative endpoint URLs against `target_domain` before dispatching.
* **Test Verification**:
  ```text
  pytest services/agent-service/tests/test_sandbox_template_path.py
  ============================= test session starts =============================
  collected 2 items
  services/agent-service/tests/test_sandbox_template_path.py ..            [100%]
  ============================== 2 passed in 0.79s ==============================
  ```

---

### ═══════════════════════════════════════════════════════
### BATCH 2 — SECOND PRIORITY (5 Items)
### ═══════════════════════════════════════════════════════

#### 8. F-39 — WebSocket Publish Failures & Degraded Mode (`crawls.py:122-154`, `crawls.py:616-621`)
* **Verification Status**: **PARTIAL**
* **Code Reference**: [`services/agent-service/app/api/v1/endpoints/crawls.py:122-154, 616-621`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/api/v1/endpoints/crawls.py#L122-L154)
* **Executable Logic Findings**:
  - **Backend (PASS)**: `publish_ws_event` performs 2 retry attempts with exponential backoff (`0.05 * (attempt + 1)`). On failure, events are buffered in `CRAWL_FALLBACK_EVENT_LOGS` and `CRAWL_SESSIONS[session_id]["event_logs"]`. When failures reach $\ge 3$, `degraded_realtime: True` is flagged in session state and returned in `get_crawl_status` (line 616).
  - **Frontend UI (Deficiency)**: The frontend (`CrawlActivityContext.tsx` / `CrawlReasoningMessage.tsx`) consumes the WebSocket stream directly via `useWebSocket`, but does not currently poll `GET /api/v1/crawls/{id}` to read `degraded_realtime` or display a "Live updates unavailable, falling back to polling" banner if the WebSocket drops.
* **Test Verification**:
  ```text
  pytest services/agent-service/tests/test_ws_publish_resilience.py
  ============================= test session starts =============================
  collected 1 item
  services/agent-service/tests/test_ws_publish_resilience.py .             [100%]
  ============================== 1 passed in 1.34s ==============================
  ```

---

#### 9. F-45 — Celery Dispatch vs Worker Pickup (`crawl_tasks.py:44-90`, `crawls.py:549-565`)
* **Verification Status**: **PARTIAL**
* **Code Reference**: [`services/agent-service/app/tasks/crawl_tasks.py:44-90`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/tasks/crawl_tasks.py#L44-L90), [`services/agent-service/app/api/v1/endpoints/crawls.py:549-565`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/api/v1/endpoints/crawls.py#L549-L565), [`services/agent-service/app/core/celery_app.py:50-85`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/core/celery_app.py#L50-L85)
* **Executable Logic Findings**:
  - **Worker Liveness Check & Fallback (PASS)**: `crawls.py:553` calls `is_celery_worker_active(timeout=0.5)` which pings active workers via `celery_app.control.inspect().ping()`. If zero workers are active or Celery is uninstalled, it logs a warning and falls back to `background_tasks.add_task(run_background_crawl)`.
  - **Reaper Function (Deficiency)**: `reap_stale_queued_crawls` was implemented in `crawl_tasks.py:58-90` to transition sessions stuck in `queued`/`pending` past 5 minutes to `status="failed"`. However, it is not yet registered in `celery_app.conf.beat_schedule` in `celery_app.py`, meaning it will only run if triggered externally rather than on an automated periodic schedule.
* **Test Verification**:
  ```text
  pytest services/agent-service/tests/test_celery_dispatch_fallback.py
  ============================= test session starts =============================
  collected 1 item
  services/agent-service/tests/test_celery_dispatch_fallback.py .          [100%]
  ============================== 1 passed in 1.34s ==============================
  ```

---

#### 10. F-38 — Crawl Marked Complete Despite Snapshot Failure (`crawls.py:295-345`)
* **Verification Status**: **PASS**
* **Code Reference**: [`services/agent-service/app/api/v1/endpoints/crawls.py:295-345`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/api/v1/endpoints/crawls.py#L295-L345)
* **Executable Logic Findings**:
  - Lines 296-310: Snapshot bulk-upsert executes **first** before committing final status.
  - Line 312: `final_status = "completed" if snapshot_success else "complete_no_snapshot"`.
  - Lines 318 & 335: `final_status` is written to `CRAWL_SESSIONS` and PostgreSQL `CrawlRepository.update_status` along with `warning_msg = "Crawl completed but snapshot persistence failed. Drift tracking unavailable for this run."`.
  - Drift detection integration: `drift.py:281-295` queries `CrawlSnapshot` table. A crawl with `complete_no_snapshot` has no snapshots, so `get_latest_crawl_id_for_project` skips it automatically, and manual comparison raises `404 Not Found`.
* **Test Verification**:
  ```text
  pytest services/agent-service/tests/test_snapshot_failure_status.py
  ============================= test session starts =============================
  collected 1 item
  services/agent-service/tests/test_snapshot_failure_status.py .           [100%]
  ============================== 1 passed in 1.25s ==============================
  ```

---

#### 11. F-35 — LLM Budget Bypass when `cost_manager` is None (`planner.py:64-75`)
* **Verification Status**: **PASS**
* **Code Reference**: [`services/agent-service/app/agents/nodes/planner.py:64-75`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/agents/nodes/planner.py#L64-L75), [`vision_planner.py:48-56`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/agents/nodes/vision_planner.py#L48-L56), [`reflection.py:48-56`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/agents/nodes/reflection.py#L48-L56), [`analyzer.py:434-445`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/agents/nodes/analyzer.py#L434-L445)
* **Executable Logic Findings**:
  - In `LLMPlannerStrategy.select_action`:
    ```python
    cost_manager = state.get("cost_manager")
    if cost_manager is None:
        from app.agents.nodes.llm_client import make_cost_manager
        cost_manager = make_cost_manager(
            crawl_id=state.get("crawl_id") or "fallback",
            user_id=state.get("user_id"),
        )
        state["cost_manager"] = cost_manager

    if cost_manager.is_budget_exhausted() or cost_manager.is_planner_budget_exhausted():
        return None
    ```
  - The fallback `CrawlCostManager` inherits standard limits (`LLM_TOKEN_BUDGET_PER_CRAWL=50000`, `LLM_PLANNER_MAX_CALLS=20`), preventing unbounded spend on direct SDK/CLI invocations.
* **Test Verification**:
  ```text
  pytest services/agent-service/tests/test_planner_default_cost_manager.py
  ============================= test session starts =============================
  collected 1 item
  services/agent-service/tests/test_planner_default_cost_manager.py .      [100%]
  ============================== 1 passed in 4.27s ==============================
  ```

---

#### 12. F-9 — Internal Session Endpoint Exposure (`proxy.py:36-45`, `internal.py:17-30`)
* **Verification Status**: **PASS**
* **Code Reference**: [`services/gateway/app/api/v1/endpoints/proxy.py:36-45`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/gateway/app/api/v1/endpoints/proxy.py#L36-L45), [`services/core-service/app/api/v1/endpoints/internal.py:17-30`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/core-service/app/api/v1/endpoints/internal.py#L17-L30)
* **Executable Logic Findings**:
  - In `gateway/proxy.py`: `/api/v1/internal` and `/api/internal` were removed from `ROUTE_TABLE`. `BLOCKED_PREFIXES = ("/api/v1/internal", "/api/internal")` explicitly blocks internal paths in `_resolve_upstream`, returning 404 to any external client.
  - In `core-service/internal.py:17-30`: `_verify_gateway` requires `X-Gateway-Secret` and rejects cross-user queries with:
    ```python
    if x_user_id and target_user_id and x_user_id != target_user_id:
        raise HTTPException(status_code=403, detail="Cross-user internal session query forbidden.")
    ```
* **Test Verification**:
  ```text
  pytest services/gateway/tests/test_proxy_internal_blocked.py
  ============================= test session starts =============================
  collected 1 item
  tests/test_proxy_internal_blocked.py .                                   [100%]
  ============================== 1 passed in 0.29s ==============================

  pytest services/core-service/tests/test_internal_endpoints.py
  ============================= test session starts =============================
  collected 2 items
  tests/test_internal_endpoints.py ..                                      [100%]
  ============================== 2 passed in 0.95s ==============================
  ```

---

## Additional Checks

### 13. Full Test Suite Execution Across All Services

#### A. Gateway Service (`services/gateway/`)
```text
pytest tests/
============================= test session starts =============================
platform win32 -- Python 3.13.12, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\ashut\Devlopments\InsightAPI\services\gateway
configfile: pyproject.toml
collected 3 items

tests\test_proxy_internal_blocked.py .                                   [ 33%]
tests\test_ws_proxy.py ..                                                [100%]

============================== 3 passed in 0.34s ==============================
```

#### B. Core Service (`services/core-service/`)
```text
pytest tests/
============================= test session starts =============================
platform win32 -- Python 3.13.12, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\ashut\Devlopments\InsightAPI\services\core-service
configfile: pyproject.toml
collected 7 items

tests\test_internal_endpoints.py ..                                      [ 28%]
tests\test_oauth_csrf.py ...                                             [ 71%]
tests\test_payments.py ..                                                [100%]

============================== 7 passed in 0.99s ==============================
```

#### C. Agent Service (`services/agent-service/`)
```text
pytest services/agent-service/tests/
============================= test session starts =============================
platform win32 -- Python 3.13.12, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\ashut\Devlopments\InsightAPI\services\agent-service
configfile: pyproject.toml
plugins: anyio-4.13.0, langsmith-0.9.8, logfire-4.32.0, asyncio-1.3.0, cov-7.1.0, mock-3.15.1, respx-0.23.1
collected 205 items

services\agent-service\tests\test_agents.py .....                        [  2%]
services\agent-service\tests\test_analyzer.py .......................... [ 15%]
services\agent-service\tests\test_api_v1.py .                            [ 16%]
services\agent-service\tests\test_audit.py .                             [ 16%]
services\agent-service\tests\test_auth.py ..                             [ 17%]
services\agent-service\tests\test_auto_login.py .......                  [ 20%]
services\agent-service\tests\test_azure_model_router.py ......           [ 21%]
services\agent-service\tests\test_celery_dispatch_fallback.py .          [ 21%]
services\agent-service\tests\test_cli_and_session_store.py .....         [ 24%]
services\agent-service\tests\test_compliance.py ....                     [ 26%]
services\agent-service\tests\test_cors.py ..                             [ 27%]
services\agent-service\tests\test_dom_distiller.py ..                    [ 28%]
services\agent-service\tests\test_domain_verification.py .......         [ 31%]
services\agent-service\tests\test_drift_idor.py ...                      [ 33%]
services\agent-service\tests\test_e2e_pipeline.py .                      [ 33%]
services\agent-service\tests\test_engine.py ...                          [ 35%]
services\agent-service\tests\test_fk_approval.py .                       [ 35%]
services\agent-service\tests\test_form_and_interstitial.py ......        [ 38%]
services\agent-service\tests\test_form_submission_attribution.py .....   [ 40%]
services\agent-service\tests\test_frontier_and_wiring.py ....            [ 42%]
services\agent-service\tests\test_graphql.py ..                          [ 43%]
services\agent-service\tests\test_humanizer.py ......                    [ 46%]
services\agent-service\tests\test_infinite_scroll.py .                   [ 47%]
services\agent-service\tests\test_llm_provider_registry.py ............  [ 53%]
services\agent-service\tests\test_logging.py ..                          [ 54%]
services\agent-service\tests\test_login_wall.py .                        [ 54%]
services\agent-service\tests\test_modal_trap.py .                        [ 55%]
services\agent-service\tests\test_pay_per_crawl.py ....                  [ 57%]
services\agent-service\tests\test_planner_default_cost_manager.py .      [ 57%]
services\agent-service\tests\test_playwright_test_gen.py ......          [ 60%]
services\agent-service\tests\test_popup_navigation.py .                  [ 60%]
services\agent-service\tests\test_production_readiness.py .....          [ 63%]
services\agent-service\tests\test_remediation_suite.py ....              [ 65%]
services\agent-service\tests\test_review_gate.py ...                     [ 66%]
services\agent-service\tests\test_risk_evaluator.py .....                [ 69%]
services\agent-service\tests\test_same_origin_iframes.py .               [ 69%]
services\agent-service\tests\test_sandbox_template_path.py ..            [ 70%]
services\agent-service\tests\test_security_reasoner.py ................. [ 79%]
.........                                                                [ 83%]
services\agent-service\tests\test_services.py ....                       [ 85%]
services\agent-service\tests\test_session_injection.py .....             [ 87%]
services\agent-service\tests\test_snapshot_failure_status.py .           [ 88%]
services\agent-service\tests\test_stabilizer.py ..                       [ 89%]
services\agent-service\tests\test_stagnation_and_resilience.py ..        [ 90%]
services\agent-service\tests\test_state_graph.py ...                     [ 91%]
services\agent-service\tests\test_stealth.py .                           [ 92%]
services\agent-service\tests\test_tenant_isolation_and_audit.py ......   [ 95%]
services\agent-service\tests\test_third_party_integrations.py ...        [ 96%]
services\agent-service\tests\test_vision_fallback.py ......              [ 99%]
services\agent-service\tests\test_ws_publish_resilience.py .             [100%]

================= 205 passed, 23 warnings in 89.70s (0:01:29) =================
```

---

### 14. Secondary Path & Regression Check
- **F-6 (Billing IDOR)**: Searched all router files in `core-service` (`auth.py`, `users.py`, `payments.py`, `internal.py`). Only `POST /payments/usage-records` creates Stripe invoice items, and it derives user identity strictly from `x-user-id` with no secondary override routes.
- **F-15 (Drift IDOR)**: Verified that `compare_snapshots` verifies `project_id` in repository SQL statements, preventing cross-tenant drift data access even if a caller supplies foreign crawl IDs.
- **F-23 (Sandbox Egress)**: Checked all callers of `SandboxExecutor.run_test` in `security_reasoner.py`, `executor.py`, and `dynamic_executor.py`. All callers supply an absolute URL or a verified `target_domain`.

---

### 15. Material Implementation Divergence Analysis

1. **Item 8 (F-39 — Degraded Realtime)**:
   - *Prompt Expectation*: Frontend UI checks and displays `degraded_realtime` banner when Redis publishing fails.
   - *Actual Implementation*: Backend sets `degraded_realtime: True` in `CRAWL_SESSIONS` and returns it via `GET /api/v1/crawls/{id}`, but the React frontend currently consumes WebSocket frames directly without an active HTTP fallback polling loop to query `get_crawl_status`. Flagged as **PARTIAL**.

2. **Item 9 (F-45 — Scheduled Reaper)**:
   - *Prompt Expectation*: Reaper/monitor is registered in a real scheduled runner (e.g. Celery beat schedule).
   - *Actual Implementation*: `reap_stale_queued_crawls` is defined as a Celery task in `crawl_tasks.py`, but `celery_app.conf.update` does not have a configured `beat_schedule` entry. Flagged as **PARTIAL**.
