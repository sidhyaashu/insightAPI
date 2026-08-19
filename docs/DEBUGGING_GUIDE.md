# InsightAPI — Advanced Agent Debugging & Observability Guide

This guide describes how to inspect, debug, and diagnose autonomous investigations in InsightAPI V3.

---

## 1. Overview & Architecture

Every autonomous investigation runs inside a **Debug Session** (`dbg-...`) that records a complete, correlated lifecycle trace without altering agent behavior:

```text
INTENT → PLAN → DECISION → POLICY → ACTION → TOOL → OBSERVATION → WORLD MODEL → EVIDENCE → VERIFICATION → AI_DIAGNOSTIC.md
```

All sensitive data (Bearer tokens, JWTs, Passwords, API Keys, Session Cookies) are automatically redacted before persistence, telemetry, or API export.

---

## 2. Debug Directory Layout

Each investigation generates a self-contained debug bundle in `debug/<session_id>/`:

```text
debug/
  <session_id>/
    ├── summary.json          # Top-level execution metadata, profile & metrics
    ├── AI_DIAGNOSTIC.md      # 15-point AI/human-readable diagnostic report
    ├── timeline.jsonl        # Compact chronological event timeline
    ├── actions.jsonl         # Detailed action lifecycle records (ACT-...)
    ├── network.jsonl         # Correlated & sanitized HTTP/REST/GraphQL traffic (REQ-...)
    ├── hypotheses.jsonl      # Endpoint hypotheses & experiment outcomes (HYP-...)
    ├── policy.jsonl          # Scope, SSRF, risk, and approval evaluation logs
    ├── errors.jsonl          # Exception logs and error boundaries
    └── graph.json            # ApplicationGraph world model topology snapshot
```

---

## 3. Human-Readable Timeline

The `timeline.jsonl` provides a millisecond-precision chronological scan:

```text
[00:00.001] SESSION_START Goal: Discover undocumented APIs -> https://target.app
[00:00.045] PLAN         Selected navigate -> https://target.app (Root target page has not been explored yet.)
[00:00.052] POLICY       ACT-10A Decision=ALLOW Risk=low_risk (Action permitted by policy)
[00:00.812] BROWSER      navigate https://target.app -> https://target.app/dashboard (Found=True)
[00:01.120] NETWORK      REQ-41A GET /api/v1/projects -> 200 (48ms)
[00:01.145] GRAPH_MUT    NODE_ADDED on ep-92f1 (Added endpoint GET /api/v1/projects to world model)
[00:01.320] HYPOTHESIS   HYP-001 GET /api/v1/projects/{id} -> VERIFIED (Conf=0.95)
[00:01.540] VERIFIED     GET /api/v1/projects/{id} -> VERIFIED (Replay verified across multiple IDs)
[00:02.100] SESSION_DONE Status: COMPLETED (RootCause=unknown)
```

---

## 4. Automated Root-Cause Analysis

When an investigation encounters issues, `RootCauseAnalyzer` classifies the primary cause into one of 15 categories:

| Root Cause Category | Diagnostic Signature | Recommended Next Action |
|---|---|---|
| `POLICY` | Scope / SSRF / private IP rejection | Verify domain scope and authorization |
| `AUTHENTICATION` | 401/403 responses or missing tokens | Supply valid Bearer token or session credentials |
| `BROWSER_NAVIGATION` | Navigation timeout / connection dropped | Check target URL connectivity and DNS |
| `BROWSER_INTERACTION` | Missing selector / overlay blocking | Refresh AXTree / inspect semantic interactive elements |
| `NETWORK_CAPTURE` | Zero API requests captured across pages | Check for WebSockets, custom AJAX, or static data |
| `VERIFICATION` | Inconclusive replay or parameter mismatch | Check CSRF headers or dynamic query requirements |
| `BUDGET` | Max tool calls or timeout reached | Increase tool call budget or max pages |

---

## 5. "Why Was This Endpoint Not Discovered?" Analyzer

To diagnose why a specific route (e.g. `GET /api/v1/orders/{id}`) was missed:

```python
from app.runtime.debug import DebugExporter

diagnosis = DebugExporter.analyze_missing(
    target_endpoint="GET /api/v1/orders/{id}",
    session_id="session-123",
)
```

The analyzer steps backward through the 12-link execution chain:
1. `PAGE_NOT_VISITED`: Navigation path never reached the page containing the API.
2. `UI_ACTION_NOT_TRIGGERED`: Page was visited, but the button/form triggering the API was not clicked.
3. `NORMALIZATION_OR_GRAPH_UPDATE`: Request occurred on the wire but was filtered during template normalization.
4. `DISCOVERED`: Route is already in the Application Graph.

---

## 6. Developer Inspection REST APIs

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/internal/debug/investigations/{id}` | Session metadata & performance profile |
| `GET` | `/api/v1/internal/debug/investigations/{id}/timeline` | Human-readable chronological timeline |
| `GET` | `/api/v1/internal/debug/investigations/{id}/actions` | Full action lifecycle traces |
| `GET` | `/api/v1/internal/debug/investigations/{id}/network` | Sanitized network traffic & correlation IDs |
| `GET` | `/api/v1/internal/debug/investigations/{id}/errors` | Error and exception logs |
| `GET` | `/api/v1/internal/debug/investigations/{id}/hypotheses` | Behavioral hypotheses & experiment results |
| `GET` | `/api/v1/internal/debug/investigations/{id}/graph` | Serialized ApplicationGraph |
| `GET` | `/api/v1/internal/debug/investigations/{id}/bundle` | Complete debug bundle export |
| `POST`| `/api/v1/internal/debug/investigations/{id}/analyze-missing` | Missing-endpoint walkback analysis |
