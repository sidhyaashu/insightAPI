# AGENTS.md — InsightAPI AI North-Star Engineering Rules

> **This file is the permanent north-star for AI coding agents working on InsightAPI AI.**
>
> Read this before planning, coding, refactoring, adding dependencies, changing architecture, or proposing new product features.
>
> The purpose of this document is to prevent random feature work, over-engineering, framework-chasing, and short-term decisions that move the codebase away from the long-term product.

---

# 1. PRODUCT NORTH STAR

## What InsightAPI is

**InsightAPI = an autonomous computer-use intelligence layer for discovering hidden, undocumented APIs and understanding how modern web applications actually communicate.**

The primary problem is:

> Modern web applications often expose more API behavior than their official documentation reveals. InsightAPI should autonomously explore the application, observe its behavior, discover the API surface, infer relationships, verify discoveries, and produce an evidence-backed model of that application.

The product should eventually become a platform for:

1. API discovery
2. API intelligence
3. API testing
4. API drift detection
5. Security intelligence
6. Attack-surface analysis
7. Authentication analysis
8. Regression testing
9. API documentation
10. Continuous application/API monitoring

The long-term platform idea is:

```text
                INSIGHTAPI RUNTIME
                       |
          +------------+------------+
          |            |            |
      Discovery     Security      Testing
          |            |            |
          +------------+------------+
                       |
              APPLICATION GRAPH
                       |
                EVIDENCE + MEMORY
                       |
                COMPUTER USE
```

**The runtime is the platform. Individual features are products built on top of the runtime.**

---

# 2. PRIMARY GOAL FOR THE CURRENT PRODUCT

## Immediate goal: V3 beta / free launch

The current priority is **rapid, reliable progress toward a usable V3 beta/free launch**.

The agent must not let future ambitions prevent shipping.

The current optimization target is:

> **Build the smallest robust autonomous API-discovery runtime that demonstrates the core vision end-to-end.**

The V3 beta must be able to take an authorized target application and:

```text
target application
        ↓
authentication if supplied
        ↓
browser exploration
        ↓
network observation
        ↓
API discovery
        ↓
route/parameter inference
        ↓
relationship inference
        ↓
verification
        ↓
application/API graph
        ↓
evidence-backed report
        ↓
OpenAPI / Postman / tests
```

Do not attempt to implement the complete future security platform before V3.

---

# 3. THE CORE PRODUCT PROMISE

The product should be understandable in one sentence:

> **“Give InsightAPI an authorized web application and it discovers the APIs the application actually uses — including undocumented ones — and proves what it found.”**

The differentiator is NOT:

- “we use AI”
- “we use agents”
- “we use LangGraph”
- “we use Gemini”
- “we have a chatbot”

The differentiator is:

> **Autonomous behavioral discovery + evidence-backed application intelligence.**

---

# 4. THE CORE ENGINEERING IDEA

Do NOT build:

```text
LLM → tool → answer
```

The target architecture is:

```text
Goal
  ↓
State
  ↓
World Model
  ↓
Hypotheses
  ↓
Planner
  ↓
Action
  ↓
Observation
  ↓
Evidence
  ↓
Reflection
  ↓
Verification
  ↓
Memory
  ↓
Next Action
```

The agent should become a **stateful investigator**, not merely a tool-calling chatbot.

---

# 5. WHAT ALREADY EXISTS — PRESERVE IT

The current project already contains important foundations:

- Playwright browser automation
- accessibility-tree/UI exploration
- network observation
- REST/XHR/fetch handling
- GraphQL handling
- WebSocket/SSE support
- HTTP probing
- cURL execution
- schema inference
- dynamic route normalization
- dependency chaining
- authentication handling
- security analysis foundations
- generated tests
- OpenAPI/Postman/Markdown exports
- persistent sessions
- vector/semantic memory
- multi-model providers
- streaming agentic chat
- approval/safety concepts
- sandbox/egress controls

**Do not rewrite these systems blindly.**

Prefer:

- adapters
- interfaces
- incremental migrations
- wrappers
- shared typed models
- compatibility layers

over wholesale rewrites.

---

# 6. PLAYWRIGHT POLICY

## Playwright is the primary browser/computer-use backend.

Do NOT replace Playwright just because another agent system uses a different browser technology.

Playwright is the initial:

> **hands + eyes + computer-use actuator**

The intelligence should live above it.

Create a clean abstraction such as:

```text
ComputerUse
BrowserAdapter
```

with an implementation:

```text
PlaywrightBrowserAdapter
```

The runtime should eventually be able to support another browser backend without redesigning the planner or agents.

Future possibilities may include:

- remote browser
- cloud browser
- Chrome integration
- mobile computer use

But these are **future adapters**, not V3 priorities.

---

# 7. THE TARGET RUNTIME ARCHITECTURE

The preferred architecture is:

```text
+---------------------------------------------------+
|                  INSIGHTAPI                       |
|       Autonomous API Intelligence Runtime         |
+---------------------------------------------------+
| Goal / Task Layer                                 |
+---------------------------------------------------+
| Supervisor / Planner / Agent Loop                 |
+---------------------------------------------------+
| Specialized Agents                                |
| Explorer | Network Intelligence | Verification   |
+---------------------------------------------------+
| Computer Use Layer                                |
| Browser / Playwright / AXTree / Screenshots      |
+---------------------------------------------------+
| API Execution Layer                               |
| HTTP / GraphQL / WebSocket / SSE / cURL          |
+---------------------------------------------------+
| Observation / Event Bus                           |
+---------------------------------------------------+
| Application World Model / Application Graph       |
+---------------------------------------------------+
| Memory / Persistence                              |
+---------------------------------------------------+
| Policy / Scope / Approval / Safety                |
+---------------------------------------------------+
| Verification / Confidence / Evidence              |
+---------------------------------------------------+
| Artifacts                                         |
| OpenAPI / Postman / Tests / Reports              |
+---------------------------------------------------+
```

This is the architectural direction.

Do not drift into unrelated product architecture.

---

# 8. APPLICATION GRAPH IS A CORE FUTURE ASSET

The system should evolve from:

> “I found 37 endpoints.”

to:

> “I discovered the behavioral communication graph of this application.”

The graph should eventually represent:

```text
Application
  ├── Pages
  ├── UI elements
  ├── UI actions
  ├── Endpoints
  ├── Parameters
  ├── Entities
  ├── Authentication
  ├── Sessions
  ├── Requests
  ├── Responses
  ├── GraphQL operations
  ├── WebSocket channels
  ├── SSE streams
  ├── Dependencies
  ├── Evidence
  └── Hypotheses
```

Useful relationships:

```text
Page -> contains -> UIElement
UIElement -> triggers -> Endpoint
Page -> causes -> NetworkObservation
Endpoint -> returns -> Entity
Endpoint -> requires -> Authentication
Endpoint -> depends_on -> Endpoint
Endpoint -> uses -> Parameter
Endpoint -> produces -> Identifier
Identifier -> feeds -> Endpoint
Evidence -> supports -> Endpoint
Evidence -> supports -> Hypothesis
```

The graph may initially use relational/JSONB storage.

Do NOT add a graph database merely because a graph sounds sophisticated.

Prove the need first.

---

# 9. OBSERVATIONS MUST BECOME FIRST-CLASS DATA

Do not let every tool return unrelated arbitrary dictionaries forever.

Create a normalized observation/event model.

At minimum:

```text
Observation
- id
- session_id
- timestamp
- source
- type
- target
- page_context
- action
- request
- response
- entities
- relationships
- evidence_refs
- confidence
- metadata
```

Potential sources:

- browser
- network
- HTTP
- GraphQL
- WebSocket
- SSE
- authentication
- schema
- security
- planner
- verification

The purpose is to allow all agents to reason over the same evidence model.

---

# 10. AGENT STATE

The agent needs structured state, not only chat history.

The canonical state should eventually include:

```text
goal
session_id
project_id
target_url

current_url
current_page
visited_pages
visited_states

actions_taken
failed_actions

authentication_state
session_state
auth_context

discovered_endpoints
discovered_parameters
discovered_entities

browser_observations
network_observations
http_observations

graphql_operations
websocket_channels
sse_channels

dependency_graph
application_graph

hypotheses
open_questions

completed_tasks
failed_tasks
blocked_tasks

evidence
confidence_scores

current_plan

budgets
tool_usage
model_usage

safety_state

artifacts
verification_results
```

Do not store huge raw payloads in hot state.

Use IDs/references for large data.

---

# 11. EVIDENCE IS MORE IMPORTANT THAN LLM CONFIDENCE

An LLM inference is not equivalent to observed behavior.

Use explicit evidence states:

```text
UNOBSERVED
INFERRED
TESTED
VERIFIED
STRONGLY_VERIFIED
```

For example:

```text
/api/products/{id}

status: VERIFIED
confidence: 0.96
evidence:
  - GET /api/products/123 -> 200
  - GET /api/products/124 -> 200
  - GET /api/products/999 -> 404
```

The final API inventory should distinguish observed facts from inferred facts.

Never silently convert model guesses into facts.

---

# 12. HYPOTHESIS → EXPERIMENT → EVIDENCE

This is a central InsightAPI concept.

The system should be able to say:

```text
Hypothesis:
  /api/products/{id} is a parameterized resource route.

Experiment:
  Replay route with multiple observed IDs.

Evidence:
  123 -> 200
  124 -> 200
  invalid -> 404

Conclusion:
  Verified.
```

Hypotheses should have explicit lifecycle states:

```text
CREATED
TESTING
SUPPORTED
CONTRADICTED
ABANDONED
VERIFIED
```

This is more important than adding more “AI features.”

---

# 13. PLANNER DIRECTION

The planner should eventually reason about:

```text
What do I know?
What do I not know?
What am I assuming?
What information would reduce uncertainty?
Which action is likely to provide the most useful new information?
Is the action allowed?
Is the action worth the cost/risk?
```

The target loop is:

```text
Goal
 ↓
State analysis
 ↓
Uncertainty analysis
 ↓
Hypothesis generation
 ↓
Candidate actions
 ↓
Policy check
 ↓
Action
 ↓
Observation
 ↓
World model update
 ↓
Reflection
 ↓
Next action
```

Do not depend only on fixed:

```text
MAX_REACT_STEPS
```

for long-term autonomy.

V3 may retain bounded loops for safety, but the architecture should move toward explicit completion criteria.

---

# 14. INFORMATION-GAIN EXPLORATION

The discovery planner should prefer actions that are likely to reveal something new.

Useful scoring concepts:

```text
information_gain
goal_relevance
novelty
confidence_improvement
risk
cost
latency
duplicate_penalty
failure_penalty
```

A simple explainable heuristic is preferable to an opaque “magic AI score.”

Do not build advanced reinforcement learning.

Do not build an autonomous planning research project.

Make the heuristic useful, observable, and testable.

---

# 15. SPECIALIZED AGENTS

Start with exactly three major roles.

## ExplorerAgent

Responsible for:

- browser navigation
- AXTree
- DOM/context interpretation
- clicks
- forms
- filters
- pagination
- modals
- SPA states
- UI-driven network discovery

It discovers.

It should not own final artifact generation.

## NetworkAgent

Responsible for:

- REST
- HTTP
- XHR/fetch
- GraphQL
- WebSocket
- SSE
- headers
- parameters
- schemas
- route normalization
- API relationships

It analyzes communication.

## VerificationAgent

Responsible for:

- replay
- endpoint verification
- parameter testing
- auth requirement confirmation
- schema validation
- regression test generation

It should be skeptical and evidence-oriented.

Later, add specialized agents such as:

- SecurityAgent
- AuthenticationAgent
- DocumentationAgent
- FuzzingAgent

ONLY when the runtime makes adding them useful.

---

# 16. SUPERVISOR / ORCHESTRATOR

The supervisor should coordinate the agents.

Conceptually:

```text
Supervisor
  |
  +-- ExplorerAgent
  |
  +-- NetworkAgent
  |
  +-- VerificationAgent
```

Child agents must have:

```text
task_id
agent_id
parent_agent_id
role
goal
allowed_tools
allowed_scope
budget
state
result
evidence
```

Implement hard limits:

```text
max depth
max concurrent agents
max total agents
timeout
token budget
tool-call budget
```

Do not allow uncontrolled agent spawning.

---

# 17. AGENT COMMUNICATION

Prefer structured messages over large transcript sharing.

Useful message types:

```text
DISCOVERY_FOUND
NEW_ENDPOINT
NEW_ENTITY
AUTH_REQUIRED
VERIFICATION_REQUEST
VERIFICATION_RESULT
HYPOTHESIS
BLOCKED
TASK_COMPLETE
TASK_FAILED
```

Pass evidence references instead of huge raw payloads.

---

# 18. COMPUTER-USE ABSTRACTION

The agent should not directly depend on Playwright everywhere.

Use a stable interface:

```text
navigate()
get_page_state()
get_accessibility_tree()
click()
type()
select()
submit()
scroll()
wait()
screenshot()
get_network_events()
get_console_events()
```

Initial implementation:

```text
PlaywrightBrowserAdapter
```

Do not add alternate browser backends during V3 unless there is a concrete user need.

---

# 19. AXTREE-FIRST

For efficient browser reasoning, prefer:

```text
AXTree
 ↓
structured DOM/metadata
 ↓
network evidence
 ↓
screenshot
 ↓
vision
```

Do not routinely dump huge HTML documents into the LLM.

Vision is a fallback/complement, not always the first choice.

---

# 20. NETWORK INTELLIGENCE

Normalize observed traffic.

Capture where available:

```text
request_id
method
url
template_url
query_parameters
headers
cookies
body
status
response_headers
response_body
timing
initiator_page
initiator_action
authentication_context
```

Redact secrets before persistence or model transmission.

---

# 21. AUTHENTICATION

Authentication is a first-class concern.

Represent:

```text
anonymous
authenticated
bearer
JWT
API key
cookie/session
basic
OAuth
```

Track:

- how authentication was obtained
- what endpoints require it
- which user/session produced evidence
- expiry where practical
- which actions are sensitive

Never leak credentials to:

- logs
- normal agent transcript
- artifacts
- exported OpenAPI
- analytics

---

# 22. POLICY AND SAFETY

Never allow the LLM to be the final authority on dangerous actions.

All actions should pass through a policy layer.

Suggested classification:

```text
READ_ONLY
LOW_RISK
MODIFYING
DESTRUCTIVE
AUTH_SENSITIVE
SECURITY_TEST
```

Policy decides.

The model requests.

Examples:

```text
GET page        -> READ_ONLY
GET endpoint    -> LOW_RISK
POST test       -> MODIFYING
DELETE request  -> DESTRUCTIVE
credential use  -> AUTH_SENSITIVE
security test   -> SECURITY_TEST
```

---

# 23. SCOPE CONTROL

Every run must have an explicit authorized scope.

At minimum:

```text
allowed_domains
allowed_urls
max_pages
max_requests
max_concurrency
max_runtime
max_payload_size
max_agent_depth
```

Never silently expand scope because the model found another domain.

The security product must be authorization-first.

---

# 24. SELF-HEALING

When an action fails:

```text
failure
 ↓
classify
 ↓
refresh observation
 ↓
select bounded recovery
 ↓
retry
 ↓
record outcome
```

Example:

```text
click failed
 ↓
refresh AXTree
 ↓
find equivalent semantic target
 ↓
retry
```

Retries must be bounded.

The agent must learn from failure rather than loop forever.

---

# 25. MEMORY

Use layers:

## Working Memory
Current AgentState.

## Session Memory
Investigation history.

## Application Memory
Structured application graph.

## Historical Memory
Prior crawl/session discoveries.

## Semantic Memory
Vector retrieval for useful historical evidence.

Structured state is authoritative.

Vector search is a retrieval mechanism, NOT truth.

---

# 26. PERSISTENCE AND RESUMABILITY

A long-running investigation should be resumable.

Persist:

```text
session
goal
state
events
observations
hypotheses
evidence
agent tasks
tool results
artifacts
verification results
```

Do not make restart destroy the investigation.

---

# 27. EVENT BUS

Create a structured execution event stream.

Useful events:

```text
SESSION_STARTED
PLAN_CREATED
ACTION_REQUESTED
POLICY_CHECK
TOOL_STARTED
TOOL_COMPLETED
OBSERVATION_CREATED
HYPOTHESIS_CREATED
HYPOTHESIS_TESTED
ENDPOINT_DISCOVERED
ENDPOINT_VERIFIED
SUBAGENT_STARTED
SUBAGENT_COMPLETED
APPROVAL_REQUIRED
APPROVAL_RECEIVED
VERIFICATION_STARTED
VERIFICATION_COMPLETED
ARTIFACT_CREATED
SESSION_COMPLETED
```

The event stream should eventually support:

- UI
- auditing
- debugging
- observability
- replay
- analytics
- evaluation

---

# 28. OBSERVABILITY

Track:

```text
session_id
agent_id
task_id
tool
duration
status
model
prompt_tokens
output_tokens
total_tokens
cost
errors
retry_count
```

Do not make observability frontend-dependent.

---

# 29. BUDGETS

The runtime must know its limits.

Possible budgets:

```text
max_runtime
max_tool_calls
max_model_calls
max_tokens
max_concurrent_agents
max_browser_actions
max_http_requests
max_retries
max_cost
```

The agent must understand remaining budget.

Stopping conditions should include:

```text
goal achieved
budget exhausted
scope exhausted
blocked
insufficient evidence
no useful next action
```

---

# 30. VERIFICATION AND COMPLETION

Do not decide “done” only because the LLM says it is done.

Completion should evaluate:

```text
exploration coverage
verified endpoint coverage
unresolved hypotheses
unexplored high-value regions
authentication states
expected API categories
remaining information value
remaining budget
```

The agent should be able to state:

> “I have high confidence in these discoveries, and these areas remain unexplored.”

That is better than pretending certainty.

---

# 31. ARTIFACTS

Treat artifacts as product outputs.

Core artifacts:

```text
API inventory
Application graph
OpenAPI specification
Postman collection
Markdown documentation
Regression tests
Discovery report
Evidence report
```

Future:

```text
Attack surface
Security findings
Continuous monitoring report
Drift report
```

Whenever practical, artifacts should link back to evidence.

---

# 32. CHAT/UI DIRECTION

The chatbot is an interface to the agent runtime, not the runtime itself.

The UI should eventually show:

```text
Planning
Exploring
Inspecting network
Found endpoint
Testing hypothesis
Delegating verification
Waiting for approval
Verified
Generated artifact
```

Use existing structured UI components where possible.

Do not expose private model chain-of-thought.

---

# 33. MULTI-MODEL ARCHITECTURE

Keep provider independence.

Current model/provider infrastructure is valuable.

Prefer task routing:

```text
FAST
SMART
VISION
```

Potential future roles:

```text
PLANNER
EXPLORER
VERIFIER
SECURITY
VISION
SUMMARY
```

Do not scatter provider-specific logic into agents/tools.

The runtime should depend on a model interface.

---

# 34. DETERMINISTIC CODE VS LLM WORK

Use deterministic code for:

- URL parsing
- route normalization
- HTTP parsing
- schema validation
- deduplication
- policy evaluation
- scope enforcement
- budget accounting
- event serialization
- graph updates
- hashing
- comparison
- risk classification

Use LLMs for:

- semantic interpretation
- planning
- hypothesis generation
- ambiguous UI reasoning
- complex relationship inference
- strategy selection
- complex security reasoning

Do not pay model cost for deterministic problems.

---

# 35. SECURITY ROADMAP

Security is important, but NOT the V3 priority.

Correct sequence:

```text
Discovery
 ↓
World Model
 ↓
Evidence
 ↓
Verification
 ↓
Security Intelligence
```

Do not build “random AI penetration testing.”

Future security should operate against the application model:

```text
Application Graph
 ↓
Attack Surface Model
 ↓
Security Hypotheses
 ↓
Controlled Experiments
 ↓
Evidence
 ↓
Finding
 ↓
Risk / Confidence
```

All security work must be authorization-bound and policy-controlled.

---

# 36. V3 BETA PRIORITY ORDER

Prioritize in this order.

## P0 — Must ship

1. Existing discovery workflow remains reliable.
2. Browser exploration remains reliable.
3. Network capture remains reliable.
4. Endpoint normalization works.
5. OpenAPI/Postman export works.
6. Authentication flow works.
7. Evidence-backed endpoint records.
8. Basic application graph.
9. Basic agent state.
10. Basic planner loop.
11. Basic verification loop.
12. Clear agent activity UI.
13. Reliability + tests.
14. Deployable free beta.

## P1 — Important after core works

- richer graph relationships
- better information-gain planning
- resumable sessions
- specialized verification agent
- better failure recovery
- historical comparison
- API drift intelligence
- improved semantic memory

## P2 — Later

- advanced subagent hierarchy
- scheduled investigations
- advanced security agent
- continuous monitoring
- deeper attack-surface modeling
- remote browser backends
- additional computer-use environments

---

# 37. WHAT NOT TO BUILD BEFORE V3

Unless a real blocker exists, do NOT spend V3 time on:

- graph database migration
- custom LLM
- training/fine-tuning models
- multi-cloud orchestration
- mobile agents
- general-purpose coding agents
- generic autonomous internet agents
- dozens of specialized agents
- elaborate memory frameworks
- distributed agent clusters
- highly abstract plugin systems
- UI redesigns unrelated to core workflow
- speculative enterprise features
- deep penetration-testing automation
- features copied from other agent products without a user problem

---

# 38. DECISION FILTER FOR EVERY FEATURE

Before implementing any feature, ask:

### Question 1
Does this improve:

- undocumented API discovery
- verification
- application understanding
- reliability
- safety
- speed
- cost
- beta usability

?

If NO, defer it.

### Question 2
Does it improve the runtime foundation used by multiple future products?

If YES, it may be high leverage.

### Question 3
Can it be implemented incrementally?

Prefer YES.

### Question 4
Does it introduce a large new dependency or framework?

If YES, require a strong reason.

### Question 5
Does it move us closer to a beta customer value proposition?

If NO, defer it.

---

# 39. WHEN THE AGENT IS UNCERTAIN

Do NOT invent architecture.

Do this:

1. Inspect current implementation.
2. Identify the smallest change.
3. Explain trade-offs internally in the implementation plan.
4. Prefer the least disruptive path.
5. Add tests.
6. Preserve compatibility.

When several approaches are viable, prefer:

> **the simplest architecture that preserves future extensibility.**

---

# 40. CODEBASE CHANGE STRATEGY

For architecture changes:

```text
Inspect
 ↓
Map
 ↓
Design
 ↓
Add model/interface
 ↓
Add adapter
 ↓
Integrate one path
 ↓
Test
 ↓
Migrate other paths
 ↓
Remove obsolete path
```

Do not:

```text
rewrite everything
```

---

# 41. REQUIRED WORKING STYLE FOR AI CODING AGENTS

Before coding a non-trivial task:

1. Identify the relevant architecture.
2. Identify what already exists.
3. Identify the smallest safe change.
4. Check whether the change aligns with this AGENTS.md.
5. Implement incrementally.
6. Test.
7. Report what changed.
8. Identify any architectural follow-up, but do not silently implement unrelated work.

Avoid scope creep.

---

# 42. EXISTING LOCAL AGENT RULES

This repository may contain more specific `AGENTS.md` files in nested directories.

Those rules remain applicable for their scopes.

For example:

```text
apps/client/AGENTS.md
```

contains frontend-specific guidance.

This root document defines the **product/architecture north-star**.

Nested `AGENTS.md` files define **local implementation rules**.

If rules conflict:

- preserve the root product direction
- preserve local framework-specific safety/correctness rules
- choose the solution that satisfies both when possible
- do not delete local rules merely for consistency

---

# 43. PROJECT LANGUAGE

Use these concepts consistently:

### “Discovery”
Finding actual application/API behavior.

### “Observation”
Something the system actually observed.

### “Evidence”
Data supporting a claim.

### “Hypothesis”
A claim that has not yet been fully verified.

### “Verification”
An independent check of a hypothesis/discovery.

### “World Model”
Structured understanding of the target application.

### “Application Graph”
Relationships among pages, actions, endpoints, entities, auth, and evidence.

### “Agent Runtime”
The reusable system that performs autonomous investigation.

### “Computer Use”
The actuator layer used to operate digital environments.

---

# 44. FUTURE NORTH STAR

Do not lose sight of the larger goal.

Long term, InsightAPI should be able to do something like:

> “Investigate this authorized application and discover every meaningful undocumented API capability you can. Explore the application intelligently, understand state and authentication, correlate UI actions with network behavior, infer relationships, test hypotheses, verify discoveries, remember what you learned, identify what remains unexplored, and produce an evidence-backed application intelligence report.”

Eventually the same runtime should support:

```text
API Discovery
     ↓
Application Intelligence
     ↓
API Testing
     ↓
API Drift
     ↓
Security Intelligence
     ↓
Attack Surface Analysis
     ↓
Continuous Security
```

**But V3 is about proving the discovery runtime, not finishing the entire vision.**

---

# 45. THE ONE SENTENCE TO REMEMBER

> **Do not build more AI features. Build the runtime that lets AI investigate web applications reliably, safely, repeatedly, and with evidence.**

---

# 46. FINAL AGENT CHECKLIST

Before completing a significant change, ask:

```text
[ ] Does this support the InsightAPI north star?
[ ] Does it help V3 beta?
[ ] Did I inspect existing code first?
[ ] Did I preserve working behavior?
[ ] Did I avoid unnecessary new dependencies?
[ ] Is state explicit?
[ ] Is evidence explicit?
[ ] Is policy explicit?
[ ] Is scope explicit?
[ ] Is the action observable?
[ ] Is there a bounded failure/retry path?
[ ] Is there a test?
[ ] Did I avoid leaking secrets?
[ ] Did I avoid exposing private reasoning?
[ ] Did I avoid unrelated feature creep?
[ ] Did I document an architectural decision if needed?
```

If the answer is “no” to the product-alignment questions, stop and reconsider the work.

---

# 47. FINAL INSTRUCTION

**Optimize for shipping a reliable V3 beta/free launch quickly, while preserving a clean path toward the long-term autonomous application intelligence runtime.**

Do not chase competitor feature checklists.

Do not chase hype.

Do not rebuild the project merely because another agent system looks impressive.

Study useful architectural ideas from advanced agent systems, but make them **domain-specific to InsightAPI**.

The long-term moat is:

> **The ability to autonomously understand the actual behavior of a web application and construct an evidence-backed model of its API surface.**

Everything else should support that.
