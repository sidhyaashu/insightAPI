"""Core Service Constants — Centralized system configurations, tiers, and rate limits."""

# ── Tiers & Roles ────────────────────────────────────────────────────────────
TIER_FREE = "FREE"
TIER_STARTER = "STARTER"
TIER_PRO = "PRO"
TIER_ENTERPRISE = "ENTERPRISE"
TIER_ADMIN = "ADMIN"

ALL_TIERS = {TIER_FREE, TIER_STARTER, TIER_PRO, TIER_ENTERPRISE, TIER_ADMIN}

ROLE_USER = "user"
ROLE_ADMIN = "admin"

# Special Admin Account (auto-assigned ADMIN tier and admin role upon login/registration)
ADMIN_EMAILS = {"ashutoshsidhya69@gmail.com", "sidhyaasutosh@gmail.com"}
ADMIN_EMAIL = "ashutoshsidhya69@gmail.com"

def is_admin_email(email: str | None) -> bool:
    if not email:
        return False
    return email.strip().lower() in {e.lower() for e in ADMIN_EMAILS}

# ── Login Providers / Methods ────────────────────────────────────────────────
LOGIN_METHOD_EMAIL = "email"
LOGIN_METHOD_GITHUB = "github"
LOGIN_METHOD_GOOGLE = "google"

# ── Rate Limiting Constants ─────────────────────────────────────────────────
RATE_LIMIT_LOGIN_ATTEMPTS = 5         # Max failed attempts before 15-min lock
RATE_LIMIT_LOGIN_WINDOW_SECONDS = 900 # 15 minutes

RATE_LIMIT_VERIFY_RESEND_MAX = 3      # Max email verification resends per hour
RATE_LIMIT_VERIFY_WINDOW_SECONDS = 3600

RATE_LIMIT_FORGOT_PW_MAX = 3         # Max password reset requests per hour
RATE_LIMIT_FORGOT_PW_WINDOW_SECONDS = 3600

# ── Token Expiration TTLs ───────────────────────────────────────────────────
VERIFICATION_TOKEN_TTL_HOURS = 24
PASSWORD_RESET_TOKEN_TTL_HOURS = 1
