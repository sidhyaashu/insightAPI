"""Gateway Service Constants — Header keys, public routes, and rate limits."""

HEADER_USER_ID = "x-user-id"
HEADER_USER_TIER = "x-user-tier"
HEADER_USER_ROLE = "x-user-role"
HEADER_USER_ALLOW_OVERAGE = "x-user-allow-overage"
HEADER_GATEWAY_SECRET = "x-gateway-secret"

PUBLIC_PATHS = {
    "/health",
    "/api/v1/health",
    "/api/v1/payments/plans",
    "/api/auth/github/login",
    "/api/auth/google/login",
    "/api/auth/callback",
    "/api/auth/refresh",
    "/api/auth/register",
    "/api/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/auth/verify-email",
    "/api/auth/resend-verification",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
}

# Rate limit requests per minute per IP for public endpoints
PUBLIC_RATE_LIMIT_PER_MINUTE = 60

# Admin emails automatically elevated to ADMIN tier
ADMIN_EMAILS = {"ashutoshsidhya69@gmail.com", "sidhyaasutosh@gmail.com"}

def is_admin_email(email: str | None) -> bool:
    if not email:
        return False
    return email.strip().lower() in {e.lower() for e in ADMIN_EMAILS}
