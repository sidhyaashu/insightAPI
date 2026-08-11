"""Gateway Service Constants — Header keys, public routes, and rate limits."""

HEADER_USER_ID = "x-user-id"
HEADER_USER_TIER = "x-user-tier"
HEADER_USER_ROLE = "x-user-role"
HEADER_GATEWAY_SECRET = "x-gateway-secret"

PUBLIC_PATHS = {
    "/health",
    "/api/v1/health",
    "/api/auth/github/login",
    "/api/auth/google/login",
    "/api/auth/callback",
    "/api/auth/refresh",
    "/api/auth/register",
    "/api/auth/login",
    "/api/auth/verify-email",
    "/api/auth/resend-verification",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
}

# Rate limit requests per minute per IP for public endpoints
PUBLIC_RATE_LIMIT_PER_MINUTE = 60
