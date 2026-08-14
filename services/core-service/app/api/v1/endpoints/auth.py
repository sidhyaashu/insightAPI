"""Core Service — Auth Endpoints (Email/Password & OAuth)."""
from __future__ import annotations

import logging
import contextlib
from fastapi import APIRouter, HTTPException, Depends, Response, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from app.core.database import get_db
from app.repositories.user_repo import UserRepository, TIER_ADMIN, ROLE_ADMIN, TIER_FREE, ROLE_USER
from app.services.token_service import TokenService, SessionRepository
from app.services.auth_service import AuthService
from app.services.email_service import EmailService
from app.services.oauth_service import exchange_github_code, exchange_google_code
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterPayload(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


class ResendVerificationPayload(BaseModel):
    email: EmailStr


class ForgotPasswordPayload(BaseModel):
    email: EmailStr


class ResetPasswordPayload(BaseModel):
    token: str
    new_password: str


@router.post("/register")
async def register(payload: RegisterPayload, response: Response):
    async with contextlib.asynccontextmanager(get_db)() as db:
        user_repo = UserRepository(db)
        session_repo = SessionRepository()
        auth_service = AuthService(user_repo, session_repo)

        try:
            result = await auth_service.register_email_user(
                email=payload.email,
                password=payload.password,
                name=payload.name,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        response.set_cookie(
            key="refresh_token",
            value=result["refresh_token"],
            httponly=True,
            secure=settings.APP_ENV == "production",
            samesite="lax",
            max_age=7 * 24 * 3600,
            path="/api/auth/refresh",
        )

        return {
            "access_token": result["access_token"],
            "token_type": "bearer",
            "user": result["user"],
        }


@router.post("/login")
async def login(payload: LoginPayload, response: Response):
    async with contextlib.asynccontextmanager(get_db)() as db:
        user_repo = UserRepository(db)
        session_repo = SessionRepository()
        auth_service = AuthService(user_repo, session_repo)

        try:
            result = await auth_service.login_email_user(
                email=payload.email,
                password=payload.password,
            )
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))

        response.set_cookie(
            key="refresh_token",
            value=result["refresh_token"],
            httponly=True,
            secure=settings.APP_ENV == "production",
            samesite="lax",
            max_age=7 * 24 * 3600,
            path="/api/auth/refresh",
        )

        return {
            "access_token": result["access_token"],
            "token_type": "bearer",
            "user": result["user"],
        }


@router.get("/verify-email")
async def verify_email(token: str):
    async with contextlib.asynccontextmanager(get_db)() as db:
        user_repo = UserRepository(db)
        session_repo = SessionRepository()
        auth_service = AuthService(user_repo, session_repo)
        success = await auth_service.verify_email(token)
        if not success:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(payload: ResendVerificationPayload):
    async with contextlib.asynccontextmanager(get_db)() as db:
        user_repo = UserRepository(db)
        session_repo = SessionRepository()
        auth_service = AuthService(user_repo, session_repo)
        try:
            await auth_service.resend_verification_email(payload.email)
        except ValueError as e:
            raise HTTPException(status_code=429, detail=str(e))
        return {"message": "Verification email resent successfully"}


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordPayload):
    async with contextlib.asynccontextmanager(get_db)() as db:
        user_repo = UserRepository(db)
        session_repo = SessionRepository()
        auth_service = AuthService(user_repo, session_repo)
        try:
            await auth_service.request_password_reset(payload.email)
        except ValueError as e:
            raise HTTPException(status_code=429, detail=str(e))
        return {"message": "If the email is registered, a password reset link has been dispatched."}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordPayload):
    async with contextlib.asynccontextmanager(get_db)() as db:
        user_repo = UserRepository(db)
        session_repo = SessionRepository()
        auth_service = AuthService(user_repo, session_repo)
        try:
            success = await auth_service.reset_password(payload.token, payload.new_password)
            if not success:
                raise HTTPException(status_code=400, detail="Invalid or expired password reset token")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"message": "Password updated successfully. You may now sign in."}


@router.get("/github/login")
async def github_login():
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&scope=read:user,user:email"
        f"&redirect_uri={settings.OAUTH_REDIRECT_URI}"
    )
    return RedirectResponse(url)


@router.get("/google/login")
async def google_login():
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&response_type=code"
        f"&scope=openid email profile"
        f"&redirect_uri={settings.OAUTH_REDIRECT_URI}"
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
                profile = await exchange_google_code(code, settings.OAUTH_REDIRECT_URI)
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
async def refresh_token(request: Request, response: Response):
    """
    Silent token refresh endpoint using HttpOnly cookie or Bearer token.
    Validates refresh token, executes single-use rotation, and issues a new token pair.
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            refresh_token = auth_header[7:].strip()

    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    async with contextlib.asynccontextmanager(get_db)() as db:
        user_repo = UserRepository(db)
        session_repo = SessionRepository()
        token_svc = TokenService(session_repo)

        try:
            from app.core.security import decode_token
            payload = decode_token(refresh_token)
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token payload")

            user = await user_repo.get_by_id(user_id)
            if not user or not user.is_active:
                raise HTTPException(status_code=401, detail="User not found or inactive")

            tokens = await token_svc.rotate_tokens(refresh_token, user.tier)

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
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))
        except Exception as e:
            logger.error(f"Refresh token error: {e}")
            raise HTTPException(status_code=401, detail="Failed to refresh token")


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Revoke refresh token session and clear browser cookie."""
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        session_repo = SessionRepository()
        token_svc = TokenService(session_repo)
        await token_svc.revoke_session(refresh_token)

    response.delete_cookie(
        key="refresh_token",
        path="/api/auth/refresh",
    )
    return {"message": "Logged out successfully"}
