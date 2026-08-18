# V3 Deferred Features & Post-Launch Roadmap

This document captures valuable ideas and future capabilities that are intentionally deferred beyond the V3 beta launch to keep the discovery runtime reliable, focused, and shippable.

---

## 1. Offensive Security & Deep Vulnerability Automation (P1/P2)
- **Concept**: Automated exploitation, SQL injection fuzzing, IDOR probing, and autonomous privilege escalation.
- **Why Deferred**: Requires a fully proven application world model and strict policy/authorization guardrails. V3 focuses on discovery, route inference, and parameter verification.

## 2. Remote / Cloud Browser Clusters (P2)
- **Concept**: Running Playwright on remote cloud grids (e.g. Browserless.io, Playwright Grid) with mobile computer-use emulation.
- **Why Deferred**: `PlaywrightBrowserAdapter` runs locally and via headless containers reliably for V3. Remote backends can be added as adapters without redesigning the runtime.

## 3. Dedicated Graph Database (Neo4j / Amazon Neptune) (P2)
- **Concept**: Migrating `ApplicationGraph` from in-memory / JSONB models into a dedicated graph database.
- **Why Deferred**: In-memory `ApplicationGraph` with PostgreSQL persistence easily handles standard web applications without added operational overhead.

## 4. Multi-Tenant Scheduled Continuous Crawling & Drift Engine (P1)
- **Concept**: Recurring cron-based background crawls to detect API drift continuously over weeks/months.
- **Why Deferred**: Core on-demand discovery, verification, and diff generation must be solidified and launched first.

## 5. Mobile Computer-Use Actuators (P2)
- **Concept**: Native mobile app exploration via Appium or Android Accessibility APIs.
- **Why Deferred**: Focus for V3 is modern web applications, SPAs, REST, GraphQL, WebSocket, and SSE communication.
