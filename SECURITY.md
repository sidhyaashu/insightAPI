# Security Policy & Credential Safeguards

At **InsightAPI AI**, protecting developer credentials, API tokens, database passwords, and environment configuration is a top priority. This document outlines our protective secret scanning safeguards, local setup instructions, vulnerability reporting, and secret revocation protocols.

---

## 🛡️ Protective Secret Scanning Architecture

We enforce secret protection across three defense layers:

1. **Local Pre-Commit Guard**: Local `gitleaks` pre-commit hooks prevent secrets from ever entering a git commit on developer machines.
2. **CI/CD Pipeline Audit**: GitHub Actions workflow automatically scans every commit diff and pull request using `gitleaks/gitleaks-action@v2`.
3. **Repository Rules & Allowlists**: Custom rules defined in `.gitleaks.toml` screen for OpenAI API keys (`sk-proj-...`), JWT keys, private keys, and high-entropy connection strings.

---

## 💻 Developer Local Setup Instructions

### 1. Install Gitleaks CLI
- **macOS**: `brew install gitleaks`
- **Windows (Scoop / Chocolatey / Winget)**: `winget install gitleaks` or `choco install gitleaks`
- **Linux / Binary Direct**: Download from [Gitleaks Releases](https://github.com/gitleaks/gitleaks/releases)

### 2. Install & Activate Pre-Commit Hooks
Run the following commands inside your virtual environment:

```bash
# 1. Install dev dependencies (includes pre-commit)
pip install -e "./backend[dev]"

# 2. Install git hook scripts
pre-commit install

# 3. Test pre-commit against all files
pre-commit run --all-files
```

### 3. Run Manual Local Scans
To scan your working directory or recent git commit history manually:

```bash
# Scan uncommitted working tree changes
gitleaks detect --verbose --config=.gitleaks.toml

# Scan full git commit history
gitleaks detect --verbose --config=.gitleaks.toml --log-opts="--all"
```

---

## 🚨 Secret Leak Incident Response Protocol

If an API key or password is accidentally committed or flagged by Gitleaks:

1. **Immediate Secret Revocation / Rotation**:
   - Immediately revoke the leaked token in the vendor dashboard (e.g. OpenAI API Dashboard, Postgres DB admin, AWS IAM console).
   - Generate a replacement key.

2. **Clean Commit History (if unpushed)**:
   ```bash
   git reset HEAD~1
   # Remove the secret from code/config
   git add .
   git commit -m "fix: remove hardcoded credential"
   ```

3. **Remediate History (if pushed)**:
   - Use `git-filter-repo` or `BFG Repo-Cleaner` to purge the secret string from all past commit histories.
   - Force push cleaned refs (if authorized).

---

## ✉️ Reporting Vulnerabilities

If you discover a security vulnerability or bypass in InsightAPI AI:
- **Do NOT** open a public GitHub issue.
- Email our core security team at `security@insightapi.ai` with a detailed description and steps to reproduce.
- We acknowledge reports within 24 hours and issue security patches promptly.
