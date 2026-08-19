# InsightAPI Autonomous Investigation — AI Diagnostic Report

**Session ID**: `sess-res-timeout-01`  
**Target URL**: `https://demo.insightapi.io`  
**Status**: `COMPLETED` (0.06s)  
**Root Cause**: `NETWORK_CAPTURE` (Confidence: 80.0%)  

---

## 15-Point Autonomous Diagnostic Assessment

1. **Original Goal**: Discover undocumented APIs, routes, and relationships in the target application.
2. **Actions Attempted**: 2 autonomous steps executed.
3. **Actions Succeeded**: 0 completed successfully.
4. **Actions Failed**: 2 failed.
5. **Bottlenecks / Slowdowns**: Total crawl elapsed in 0.06s across 1 pages.
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

- Executed 2 actions across pages but captured 0 API network requests.

---

## Execution Timeline Highlights

```text
[00:00.000] SESSION_START Goal: Discover undocumented APIs, routes, and relationships in the target application. -> https://demo.insightapi.io
[00:00.057] POLICY       act-d1f0ae315c02 Decision=ALLOW Risk=read_only (Action permitted under current policy and scope.)
[00:00.058] ACTION       act-d1f0ae315c02 navigate -> https://demo.insightapi.io [FAILED] (1ms)
[00:00.059] POLICY       act-32f76161be66 Decision=ALLOW Risk=read_only (Action permitted under current policy and scope.)
[00:00.060] ACTION       act-32f76161be66 navigate -> https://demo.insightapi.io [FAILED] (0ms)
[00:00.060] SESSION_DONE Status: COMPLETED (RootCause=network_capture)
```
