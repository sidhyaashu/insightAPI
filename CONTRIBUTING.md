# Contributing to InsightAPI AI

First off, thank you for considering contributing to **InsightAPI AI**! It's open-source projects like this that make the developer community an amazing place to build.

---

## 🚀 Getting Started with Local Development

### 1. Prerequisites
- Python >= 3.10
- Git
- Node.js (for Playwright browser drivers)

### 2. Fork & Clone
```bash
git clone https://github.com/<your-username>/InsightAPI.git
cd InsightAPI
```

### 3. Create Virtual Environment & Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -e "./backend[dev]"
playwright install --with-deps chromium

# Install Gitleaks pre-commit hook guard
pre-commit install
```

### 4. Running Secret & Repository Safeguard Checks
Scan your local branch for accidentally committed credentials or API keys before pushing:
```bash
pre-commit run --all-files
```

### 5. Running the Test Suite
Before submitting any Pull Request, ensure all pytest unit and integration tests pass cleanly:
```bash
pytest backend/tests/
```

### 5. Running the REST API locally
```bash
uvicorn app.main:app --reload --port 8000
```
Then visit `http://localhost:8000/docs` for interactive Swagger documentation.

---

## 📐 Coding Standards & Guidelines

- **Style**: Follow PEP 8 guidelines. Use `black` or `ruff` for code formatting.
- **Type Annotations**: Always include Python type hints (`from typing import ...`) for function signatures.
- **Error Handling**: Wrap external I/O (Playwright, network requests, LLM calls) in explicit try/except guards with fallback paths.
- **Tests**: Add unit tests in `backend/tests/` for any new feature or bugfix.

---

## 🐛 Submitting Issues & Feature Requests

When creating a new issue, please include:
1. **Description**: Clear explanation of the issue or feature request.
2. **Steps to Reproduce**: Minimal code snippet or target URL.
3. **Environment**: Python version, OS, Playwright version.

---

## 📜 License

By contributing to InsightAPI AI, you agree that your contributions will be licensed under the MIT License.
