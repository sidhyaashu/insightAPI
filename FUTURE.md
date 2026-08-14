# InsightAPI AI — Future Product Roadmap (v1.1+)

This document outlines upcoming architectural enhancements, advanced AI capabilities, and enterprise platform features planned for **InsightAPI AI** post-v1.

---

## 🔮 Phase 1: Advanced AI Agent Capabilities (v1.1)

### 1. Vision Set-of-Mark (SoM) Fallback Classifier
* **Set-of-Mark Screenshots**: Overlay numeric markers over screenshot coordinates when interactive accessibility tree (AXTree) extraction is insufficient (e.g. Canvas UIs, custom webgl widgets, complex web charts).
* **Multi-Modal Vision LLM Integration**: Fall back to GPT-4o Vision or Claude 3.5 Sonnet Vision only when structural DOM snapping fails.

### 2. Multi-Step Form Synthetic Data Generator
* Context-aware LLM synthetic input generation for multi-step signup wizards, multi-field filter forms, and complex checkout steps.

---

## 🛰️ Phase 2: API Intelligence & Change Detection (v1.2)

### 1. Automated API Drift & Schema Change Detection
* Compare OpenAPI specifications across crawl sessions to detect breaking endpoint changes, deprecated fields, and missing parameters between deployments.
* Output visual API diff reports with alert notifications.

### 2. Shadow API & Security Risk Scoring
* Detect unauthenticated sensitive endpoints exposing PII, missing CORS headers, and unencrypted parameters.
* Provide an automated API Security Risk Score per crawl session.

---

## 🚀 Phase 3: Developer Ecosystem & CI/CD Integrations (v2.0)

### 1. GitHub Action & GitLab CI Pipeline Plugin
* Pre-built GitHub Action (`insightapi-action@v1`) to automatically crawl staging environments on pull request merge and block builds if API drift is detected.

### 2. On-Premises Docker Agent Runner
* Distributed worker architecture for running agent crawlers inside private corporate VPCs or behind firewalls.
