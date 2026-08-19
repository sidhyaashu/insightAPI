# InsightAPI — Debug Event & Span Schema Specification

This document defines the authoritative JSON schemas for debug traces, spans, and artifact logs generated during autonomous investigations.

---

## 1. Trace Span Schema (`TraceSpan`)

```json
{
  "span_id": "span-4a2f8b91c0e3",
  "parent_span_id": "span-1b2c3d4e5f6a",
  "trace_id": "trc-547cdc8e",
  "session_id": "547cdc8e-6118-41f0-afdb-c1903f00c88e",
  "name": "explorer.explore_page",
  "span_type": "action",
  "agent_id": "explorer",
  "task_id": "ACT-10A2B3",
  "action_id": "ACT-10A2B3",
  "status": "success",
  "start_time": "2026-08-19T03:00:00.123456Z",
  "end_time": "2026-08-19T03:00:00.890123Z",
  "duration_ms": 766,
  "attributes": {
    "target": "https://example.com/dashboard",
    "max_clicks": 15
  },
  "error_type": null,
  "error_message": null
}
```

---

## 2. Planner Decision Schema (`PlannerDecisionTrace`)

```json
{
  "decision_id": "dec-9f8e7d6c",
  "session_id": "547cdc8e-6118-41f0-afdb-c1903f00c88e",
  "timestamp": "2026-08-19T03:00:01.000000Z",
  "current_url": "https://example.com/dashboard",
  "known_endpoints_count": 8,
  "verified_endpoints_count": 4,
  "hypotheses_count": 2,
  "candidate_actions": [
    {
      "action_type": "navigate",
      "target": "https://example.com/settings",
      "score": 0.95,
      "information_gain": 0.90,
      "risk": 0.0,
      "cost": 0.0,
      "reason": "Root target page has not been explored yet."
    },
    {
      "action_type": "verify_endpoint",
      "target": "https://example.com/api/v1/projects/1",
      "score": 0.85,
      "information_gain": 0.75,
      "reason": "Endpoint GET /api/v1/projects/{id} discovered but unverified."
    }
  ],
  "selected_action": "navigate",
  "selected_target": "https://example.com/settings",
  "selection_rationale": "Explore root target application https://example.com/settings to discover interactive API surface."
}
```

---

## 3. Network Trace Schema (`NetworkTrace`)

```json
{
  "request_id": "REQ-41A89B",
  "action_id": "ACT-10A2B3",
  "endpoint_id": "ep-92f1b4",
  "observation_id": "obs-77c8e9",
  "session_id": "547cdc8e-6118-41f0-afdb-c1903f00c88e",
  "timestamp": "2026-08-19T03:00:01.500000Z",
  "protocol": "REST",
  "method": "GET",
  "url": "https://example.com/api/v1/projects?status=active",
  "normalized_template": "/api/v1/projects",
  "query_params": {
    "status": "active"
  },
  "request_headers": {
    "Authorization": "[REDACTED]",
    "Accept": "application/json"
  },
  "response_status": 200,
  "response_headers": {
    "content-type": "application/json"
  },
  "response_body": {
    "items": [{"id": 1, "name": "Alpha"}]
  },
  "duration_ms": 48,
  "initiator_page": "https://example.com/dashboard",
  "initiator_action": "click",
  "failure_type": null,
  "failure_details": null
}
```

---

## 4. AI Diagnostic Report Schema (`AIDiagnosticReport`)

```json
{
  "session_id": "547cdc8e-6118-41f0-afdb-c1903f00c88e",
  "target_url": "https://example.com",
  "goal": "Autonomous API discovery investigation",
  "status": "completed",
  "duration_seconds": 12.45,
  "total_actions": 6,
  "successful_actions": 6,
  "failed_actions": 0,
  "retries_count": 0,
  "pages_explored": ["https://example.com", "https://example.com/dashboard"],
  "endpoints_discovered_count": 11,
  "endpoints_verified_count": 11,
  "unresolved_hypotheses_count": 0,
  "stopping_reason": "Exploration and verification goals achieved.",
  "root_cause": "unknown",
  "root_cause_confidence": 0.95,
  "root_cause_evidence": [
    "Discovered 11 endpoints; successfully verified 11 with multi-identifier evidence."
  ],
  "recommended_next_experiment": "Investigation completed successfully."
}
```
