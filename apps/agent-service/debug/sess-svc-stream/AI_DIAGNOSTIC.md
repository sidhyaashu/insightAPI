# InsightAPI Autonomous Investigation — AI Diagnostic Report

**Session ID**: `sess-svc-stream`  
**Target URL**: `https://api.example.com`  
**Status**: `COMPLETED` (2.68s)  
**Root Cause**: `NETWORK_CAPTURE` (Confidence: 80.0%)  

---

## 15-Point Autonomous Diagnostic Assessment

1. **Original Goal**: Explore dashboard
2. **Actions Attempted**: 1 autonomous steps executed.
3. **Actions Succeeded**: 1 completed successfully.
4. **Actions Failed**: 0 failed.
5. **Bottlenecks / Slowdowns**: Total crawl elapsed in 2.68s across 1 pages.
6. **Self-Healing Retries**: 0 retries executed.
7. **Pages Explored**: https://api.example.com.
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

- Executed 1 actions across pages but captured 0 API network requests.

---

## Execution Timeline Highlights

```text
[00:00.000] SESSION_START Goal: Explore dashboard -> https://api.example.com
[00:00.061] POLICY       act-bccb6a9bd6d9 Decision=ALLOW Risk=read_only (Action permitted under current policy and scope.)
[00:02.681] ACTION       act-bccb6a9bd6d9 navigate -> https://api.example.com [SUCCEEDED] (2620ms)
[00:02.681] SESSION_DONE Status: COMPLETED (RootCause=network_capture)
```
