# InsightAPI Autonomous Investigation — AI Diagnostic Report

**Session ID**: `sess-bench-v3-e2e`  
**Target URL**: `https://demo.insightapi.io`  
**Status**: `COMPLETED` (0.04s)  
**Root Cause**: `NETWORK_CAPTURE` (Confidence: 80.0%)  

---

## 15-Point Autonomous Diagnostic Assessment

1. **Original Goal**: Discover all undocumented, hidden, and parameterized APIs in benchmark app
2. **Actions Attempted**: 5 autonomous steps executed.
3. **Actions Succeeded**: 5 completed successfully.
4. **Actions Failed**: 0 failed.
5. **Bottlenecks / Slowdowns**: Total crawl elapsed in 0.04s across 1 pages.
6. **Self-Healing Retries**: 0 retries executed.
7. **Pages Explored**: https://demo.insightapi.io.
8. **Endpoints Discovered**: **0** API routes indexed in Application Graph.
9. **Endpoints Verified**: **0** backed by replay/probe evidence.
10. **Unresolved Hypotheses**: 0 behavioral hypotheses pending verification.
11. **Unexplored Application Regions**: None identified within authorized scope.
12. **Last Successful Progress Point**: Exploration initialized.
13. **Investigation Stopping Reason**: Investigation finished successfully.
14. **Primary Root Cause**: `network_capture`.
15. **Recommended Next Experiment**: Target may use embedded WebSockets, custom AJAX protocols, or static hydration. Verify network interceptor filters.

---

## Root Cause Evidence Breakdown

- Executed 5 actions across pages but captured 0 API network requests.

---

## Execution Timeline Highlights

```text
[00:00.000] SESSION_START Goal: Discover all undocumented, hidden, and parameterized APIs in benchmark app -> https://demo.insightapi.io
[00:00.001] POLICY       act-48fa3f232e23 Decision=ALLOW Risk=read_only (Action permitted under current policy and scope.)
[00:00.002] ACTION       act-48fa3f232e23 navigate -> https://demo.insightapi.io [SUCCEEDED] (0ms)
[00:00.002] GRAPH_MUT    NODE_ADDED on ep-f1a5be0a (Added endpoint POST /api/v1/auth/login to world model)
[00:00.002] GRAPH_MUT    NODE_ADDED on ep-07bb2eba (Added endpoint GET /api/v1/projects to world model)
[00:00.002] GRAPH_MUT    NODE_ADDED on ep-df37bc55 (Added endpoint GET /api/v1/projects/{id} to world model)
[00:00.002] GRAPH_MUT    NODE_ADDED on ep-029c5531 (Added endpoint POST /api/v1/projects/{id}/export to world model)
[00:00.002] GRAPH_MUT    NODE_ADDED on ep-4cfbf636 (Added endpoint GET /api/v1/orgs/{id}/members to world model)
[00:00.003] GRAPH_MUT    NODE_ADDED on ep-b9b302b2 (Added endpoint POST /api/v1/orders to world model)
[00:00.003] GRAPH_MUT    NODE_ADDED on ep-1e624bfc (Added endpoint DELETE /api/v1/projects/{id} to world model)
[00:00.003] GRAPH_MUT    NODE_ADDED on ep-74a970f3 (Added endpoint POST /graphql to world model)
[00:00.003] GRAPH_MUT    NODE_ADDED on ep-ac8bac23 (Added endpoint GET /api/v1/stream/events to world model)
[00:00.003] GRAPH_MUT    NODE_ADDED on ep-9f95825b (Added endpoint GET /api/v1/internal/health to world model)
[00:00.003] GRAPH_MUT    NODE_ADDED on ep-bf2f050c (Added endpoint GET /api/v1/hidden/debug-info to world model)
[00:00.004] POLICY       act-11e5d6229484 Decision=ALLOW Risk=read_only (Action permitted under current policy and scope.)
[00:00.004] ACTION       act-11e5d6229484 navigate -> https://demo.insightapi.io [SUCCEEDED] (0ms)
[00:00.005] POLICY       act-4195bc4dea46 Decision=ALLOW Risk=read_only (Action permitted under current policy and scope.)
[00:00.006] ACTION       act-4195bc4dea46 navigate -> https://demo.insightapi.io [SUCCEEDED] (0ms)
[00:00.006] STUCK_ALERT  Repeated identical action 'navigate' on 'https://demo.insightapi.io' 3 times consecutively.
[00:00.007] POLICY       act-07382aaa281a Decision=ALLOW Risk=read_only (Action permitted under current policy and scope.)
[00:00.007] ACTION       act-07382aaa281a navigate -> https://demo.insightapi.io [SUCCEEDED] (0ms)
[00:00.007] STUCK_ALERT  Repeated identical action 'navigate' on 'https://demo.insightapi.io' 3 times consecutively.
[00:00.008] POLICY       act-0731a6df6778 Decision=ALLOW Risk=read_only (Action permitted under current policy and scope.)
[00:00.009] ACTION       act-0731a6df6778 navigate -> https://demo.insightapi.io [SUCCEEDED] (0ms)
[00:00.009] STUCK_ALERT  Repeated identical action 'navigate' on 'https://demo.insightapi.io' 3 times consecutively.
[00:00.016] GRAPH_MUT    NODE_ADDED on ep-68ff60dc (Added endpoint POST / to world model)
[00:00.023] GRAPH_MUT    NODE_ADDED on ep-078223eb (Added endpoint GET / to world model)
[00:00.027] GRAPH_MUT    NODE_ADDED on ep-6f30e266 (Added endpoint GET /{id} to world model)
[00:00.035] SESSION_DONE Status: COMPLETED (RootCause=network_capture)
```
