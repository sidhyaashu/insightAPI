# InsightAPI AI — Crawling & Ethical Use Policy

> **TL;DR**: InsightAPI AI is an open-source security, engineering, and API documentation tool.
> It is designed to autonomously explore and document **applications you own, have explicit authorization to test, or are exploring via your own authenticated user session**.
> It is **not** intended for bulk data scraping, circumventing paywalls, or crawling third-party services against their Terms of Service (ToS).

---

## 📜 Intended & Permitted Use Cases

InsightAPI AI is built for legitimate software development, API engineering, and security testing workflows:

1. **Own Applications**: Discovering, auditing, and generating OpenAPI/Postman documentation for web applications developed by your team or organization.
2. **Authorized Testing**: Performing authorized API surface exploration, staging environment validation, or security auditing under explicit permission or bug bounty scope.
3. **Personal Authenticated Sessions**: Exploring web UIs behind your own authenticated user accounts using local session injection (`insightapi login` / `storage_state`).
4. **CI/CD Integration**: Automatically outputting updated API documentation specs as part of automated build or deployment pipelines.

---

## 🚫 Prohibited Activities

Users of InsightAPI AI MUST NOT engage in any of the following activities:

1. **Unauthorized Third-Party Crawling**: Pointing the tool at third-party commercial services or websites without permission or outside authorized security testing programs.
2. **ToS Violations & Paywall Evasion**: Scraping proprietary data, circumventing anti-bot mechanisms for commercial exploitation, or bypassing access controls.
3. **Disruptive Load & Denial of Service**: Setting zero delay spacing (`--rate-limit 0`) or launching parallel high-concurrency instances to overwhelm target infrastructure.
4. **Credential Harvest or Abuse**: Using automated actions to attempt brute-force login attempts or credential stuffing.

---

## 🛡️ Built-in Compliance & Safety Features

InsightAPI AI incorporates mandatory safety guardrails out of the box:

- **Robots.txt Enforcement**: `RobotsChecker` parses target site `robots.txt` rules. If a URL or root path is disallowed, the CLI halts and requires explicit user confirmation or `--force` override.
- **Domain Rate Limiting**: `DomainRateLimiter` enforces a default minimum 500ms spacing between requests per target domain (`--rate-limit <ms>`), preventing burst traffic spikes.
- **Two-Tier Action Safety Classifier**: Automatically evaluates DOM element context before execution, refusing to click or submit high-risk actions (`delete`, `pay`, `purchase`, `update password`).
- **Data & Credential Redaction**: `NetworkFilter` automatically redacts session cookies, Bearer tokens, CSRF/XSRF tokens, and secret keys from generated OpenAPI, Postman, and Markdown outputs.

---

## ⚖️ Legal & User Responsibility

InsightAPI AI is distributed under the open-source MIT License as a developer tool. Users are solely responsible for ensuring their usage complies with all applicable local, national, and international laws (such as the Computer Fraud and Abuse Act (CFAA), GDPR, and Copyright laws) as well as the Terms of Service of any target website.
