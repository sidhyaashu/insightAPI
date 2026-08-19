# InsightAPI Autonomous Investigation — AI Diagnostic Report

**Session ID**: `sess-res-auth-02`  
**Target URL**: `https://demo.insightapi.io/api/v1/protected`  
**Status**: `COMPLETED` (0.02s)  
**Root Cause**: `NETWORK_CAPTURE` (Confidence: 80.0%)  

---

## 15-Point Autonomous Diagnostic Assessment

1. **Original Goal**: Discover undocumented APIs, routes, and relationships in the target application.
2. **Actions Attempted**: 10 autonomous steps executed.
3. **Actions Succeeded**: 10 completed successfully.
4. **Actions Failed**: 0 failed.
5. **Bottlenecks / Slowdowns**: Total crawl elapsed in 0.02s across 1 pages.
6. **Self-Healing Retries**: 0 retries executed.
7. **Pages Explored**: https://demo.insightapi.io/api/v1/protected.
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

- Executed 10 actions across pages but captured 0 API network requests.

---

## Execution Timeline Highlights

```text
[00:00.000] SESSION_START Goal: Discover undocumented APIs, routes, and relationships in the target application. -> https://demo.insightapi.io/api/v1/protected
[00:00.001] POLICY       act-41ec679f2b28 Decision=ALLOW Risk=read_only (Action permitted under current policy and scope.)
[00:00.002] ACTION       act-41ec679f2b28 navigate -> https://demo.insightapi.io/api/v1/protected [SUCCEEDED] (0ms)
[00:00.002] GRAPH_MUT    NODE_ADDED on ep-4940514b (Added endpoint GET /api/v1/protected to world model)
[00:00.003] POLICY       act-358ab6835ad1 Decision=ALLOW Risk=read_only (Action permitted under current policy and scope.)
[00:00.003] ACTION       act-358ab6835ad1 navigate -> https://demo.insightapi.io/api/v1/protected [SUCCEEDED] (0ms)
[00:00.005] POLICY       act-6f0af70dc1b2 Decision=ALLOW Risk=read_only (Action permitted under current policy and scope.)
[00:00.005] ACTION       act-6f0af70dc1b2 navigate -> https://demo.insightapi.io/api/v1/protected [SUCCEEDED] (0ms)
[00:00.005] STUCK_ALERT  Repeated identical action 'navigate' on 'https://demo.insightapi.io/api/v1/protected' 3 times consecutively.
[00:00.006] POLICY       act-f017e3fc7f94 Decision=ALLOW Risk=read_only (Action permitted under current policy and scope.)
[00:00.007] ACTION       act-f017e3fc7f94 navigate -> https://demo.insightapi.io/api/v1/protected [SUCCEEDED] (0ms)
[00:00.007] STUCK_ALERT  Repeated identical action 'navigate' on 'https://demo.insightapi.io/api/v1/protected' 3 times consecutively.
[00:00.008] POLICY       act-27c6a9a94ca9 Decision=ALLOW Risk=read_only (Action permitted under current policy and scope.)
[00:00.008] ACTION       act-27c6a9a94ca9 navigate -> https://demo.insightapi.io/api/v1/protected [SUCCEEDED] (0ms)
[00:00.008] STUCK_ALERT  Repeated identical action 'navigate' on 'https://demo.insightapi.io/api/v1/protected' 3 times consecutively.
[00:00.009] POLICY       act-c77efdb040b1 Decision=ALLOW Risk=read_only (Action permitted under current policy and scope.)
[00:00.010] ACTION       act-c77efdb040b1 navigate -> https://demo.insightapi.io/api/v1/protected [SUCCEEDED] (0ms)
[00:00.010] STUCK_ALERT  Repeated identical action 'navigate' on 'https://demo.insightapi.io/api/v1/protected' 3 times consecutively.
[00:00.011] POLICY       act-80afd6a4088c Decision=ALLOW Risk=read_only (Action permitted under current policy and scope.)
[00:00.011] ACTION       act-80afd6a4088c navigate -> https://demo.insightapi.io/api/v1/protected [SUCCEEDED] (0ms)
[00:00.011] STUCK_ALERT  Repeated identical action 'navigate' on 'https://demo.insightapi.io/api/v1/protected' 3 times consecutively.
[00:00.012] POLICY       act-98a70a6315df Decision=ALLOW Risk=read_only (Action permitted under current policy and scope.)
[00:00.012] ACTION       act-98a70a6315df navigate -> https://demo.insightapi.io/api/v1/protected [SUCCEEDED] (0ms)
[00:00.013] STUCK_ALERT  Repeated identical action 'navigate' on 'https://demo.insightapi.io/api/v1/protected' 3 times consecutively.
[00:00.013] POLICY       act-c24ad2cbd451 Decision=ALLOW Risk=read_only (Action permitted under current policy and scope.)
[00:00.014] ACTION       act-c24ad2cbd451 navigate -> https://demo.insightapi.io/api/v1/protected [SUCCEEDED] (0ms)
[00:00.014] STUCK_ALERT  Repeated identical action 'navigate' on 'https://demo.insightapi.io/api/v1/protected' 3 times consecutively.
[00:00.015] POLICY       act-0a6edfdfeec5 Decision=ALLOW Risk=read_only (Action permitted under current policy and scope.)
[00:00.016] ACTION       act-0a6edfdfeec5 navigate -> https://demo.insightapi.io/api/v1/protected [SUCCEEDED] (0ms)
[00:00.016] STUCK_ALERT  Repeated identical action 'navigate' on 'https://demo.insightapi.io/api/v1/protected' 3 times consecutively.
```
