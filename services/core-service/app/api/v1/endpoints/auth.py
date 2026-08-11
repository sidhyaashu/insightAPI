"""Core Service — Auth router: Email/Password Registration, Login, Verification, Password Reset & OAuth."""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Request, Response, Cookie
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field
import contextlib

from app.core.config import settings
from app.core.database import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.session_repo import SessionRepository
from app.services.oauth_service import exchange_github_code, exchange_google_code
from app.services.token_service import TokenService
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


# ── Pydantic Request Schemas ──────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="Password must be at least 8 characters.")
    name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ResendVerifyRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, description="New password must be at least 8 characters.")


# ── Email/Password Authentication Endpoints ────────────────────────────────────

@router.post("/register")
async def register(body: RegisterRequest, response: Response):
    """Register a new user with email and password."""
    async with contextlib.asynccontextmanager(get_db)() as db:
        user_repo = UserRepository(db)
        session_repo = SessionRepository()
        auth_svc = AuthService(user_repo, session_repo)

        try:
            res = await auth_svc.register_email_user(
                email=body.email,
                password=body.password,
                name=body.name,
            )

            # Set refresh token in HttpOnly cookie
            response.set_cookie(
                key="refresh_token",
                value=res["refresh_token"],
                httponly=True,
                secure=settings.APP_ENV == "production",
                samesite="lax",
                max_age=7 * 24 * 3600,
                path="/api/auth/refresh",
            )

            return {
                "access_token": res["access_token"],
                "token_type": "bearer",
                "user": res["user"],
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(body: LoginRequest, response: Response):
    """Authenticate user with email and password (enforces rate limiting)."""
    async with contextlib.asynccontextmanager(get_db)() as db:
        user_repo = UserRepository(db)
        session_repo = SessionRepository()
        auth_svc = AuthService(user_repo, session_repo)

        try:
            res = await auth_svc.login_email_user(email=body.email, password=body.password)

            response.set_cookie(
                key="refresh_token",
                value=res["refresh_token"],
                httponly=True,
                secure=settings.APP_ENV == "production",
                samesite="lax",
                max_age=7 * 24 * 3600,
                path="/api/auth/refresh",
            )

            return {
                "access_token": res["access_token"],
                "token_type": "bearer",
                "user": res["user"],
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.get("/verify-email")
async def verify_email(token: str):
    """Verify user's email address using token."""
    async with contextlib.asynccontextmanager(get_db)() as db:
        user_repo = UserRepository(db)
        session_repo = SessionRepository()
        auth_svc = AuthService(user_repo, session_repo)

        success = await auth_svc.verify_email(token)
        if not success:
            raise HTTPException(status_code=400, detail="Invalid or expired email verification token.")

        return {"message": "Email address verified successfully."}


@router.post("/resend-verification")
async def resend_verification(body: ResendVerifyRequest):
    """Resend email verification link (rate limited to 3 per hour)."""
    async with contextlib.asynccontextmanager(get_db)() as db:
        user_repo = UserRepository(db)
        session_repo = SessionRepository()
        auth_svc = AuthService(user_repo, session_repo)

        try:
            await auth_svc.resend_verification_email(body.email)
            return {"message": "If account exists, verification email has been resent."}
        except ValueError as e:
            raise HTTPException(status_code=429, detail=str(e))


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    """Initiate password reset flow (rate limited to 3 per hour)."""
    async with contextlib.asynccontextmanager(get_db)() as db:
        user_repo = UserRepository(db)
        session_repo = SessionRepository()
        auth_svc = AuthService(user_repo, session_repo)

        try:
            await auth_svc.request_password_reset(body.email)
            return {"message": "If account exists, password reset instructions have been sent."}
        except ValueError as e:
            raise HTTPException(status_code=429, detail=str(e))


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    """Reset user password using token."""
    async with contextlib.asynccontextmanager(get_db)() as db:
        user_repo = UserRepository(db)
        session_repo = SessionRepository()
        auth_svc = AuthService(user_repo, session_repo)

        try:
            success = await auth_svc.reset_password(body.token, body.new_password)
            if not success:
                raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
            return {"message": "Password reset successfully. You can now log in with your new password."}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


# ── OAuth Login Redirects ─────────────────────────────────────────────────────

@router.get("/github/login")
async def github_login():
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&scope=read:user,user:email"
        f"&redirect_uri={settings.OAUTH_REDIRECT_URI}?provider=github"
    )
    return RedirectResponse(url)


@router.get("/google/login")
async def google_login():
    redirect = f"{settings.OAUTH_REDIRECT_URI}?provider=google"
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&response_type=code"
        f"&scope=openid email profile"
        f"&redirect_uri={redirect}"
    )
    return RedirectResponse(url)


@router.get("/callback")
async def oauth_callback(
    response: Response,
    code: str,
    provider: str,
):
    async with contextlib.asynccontextmanager(get_db)() as db:
        try:
            if provider == "github":
                profile = await exchange_github_code(code)
            elif provider == "google":
                redirect = f"{settings.OAUTH_REDIRECT_URI}?provider=google"
                profile = await exchange_google_code(code, redirect)
            else:
                raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

            user_repo = UserRepository(db)
            session_repo = SessionRepository()
            token_svc = TokenService(session_repo)

            user = await user_repo.upsert_oauth_user(
                provider=profile["provider"],
                sub=profile["sub"],
                email=profile["email"],
                name=profile.get("name"),
                avatar_url=profile.get("avatar_url"),
            )

            # Auto grant admin if sidhyaasutosh@gmail.com
            user = await user_repo.check_and_grant_admin(user)

            tokens = await token_svc.issue_token_pair(user.id, user.tier)

            response.set_cookie(
                key="refresh_token",
                value=tokens["refresh_token"],
                httponly=True,
                secure=settings.APP_ENV == "production",
                samesite="lax",
                max_age=7 * 24 * 3600,
                path="/api/auth/refresh",
            )

            return {
                "access_token": tokens["access_token"],
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "avatar_url": user.avatar_url,
                    "tier": user.tier,
                    "role": user.role,
                    "is_verified": user.is_verified,
                },
            }
        except Exception as e:
            logger.error(f"OAuth callback error ({provider}): {e}")
            raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh")
async def refresh_tokens(response: Response, refresh_token: str = Cookie(default=None)):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token.")

    async with contextlib.asynccontextmanager(get_db)() as db:
        user_repo = UserRepository(db)
        session_repo = SessionRepository()
        token_svc = TokenService(session_repo)

        from jose import jwt as jose_jwt
        try:
            payload = jose_jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user = await user_repo.get_by_id(payload["sub"])
            tier = user.tier if user else "FREE"
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid refresh token.")

        try:
            tokens = await token_svc.rotate_tokens(refresh_token, tier)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))

        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            httponly=True,
            secure=settings.APP_ENV == "production",
            samesite="lax",
            max_age=7 * 24 * 3600,
            path="/api/auth/refresh",
        )

        return {"access_token": tokens["access_token"], "token_type": "bearer"}


@router.post("/logout")
async def logout(response: Response, refresh_token: str = Cookie(default=None)):
    if refresh_token:
        session_repo = SessionRepository()
        token_svc = TokenService(session_repo)
        await token_svc.revoke_session(refresh_token)

    response.delete_cookie("refresh_token", path="/api/auth/refresh")
    return {"message": "Logged out successfully."}
