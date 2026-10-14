from __future__ import annotations

import secrets
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Cookie, Depends, HTTPException, Request, Response, status

from app.config import Settings, get_settings

ph = PasswordHasher()

Role = Literal["admin", "viewer"]


@dataclass
class AuthUser:
    username: str
    role: Role


_login_attempts: dict[str, list[float]] = defaultdict(list)


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def resolve_password_hash(settings: Settings, role: Role) -> str | None:
    if role == "admin":
        if settings.admin_password_hash:
            return settings.admin_password_hash
        if settings.admin_password:
            return hash_password(settings.admin_password)
        return None
    if settings.viewer_password_hash:
        return settings.viewer_password_hash
    if settings.viewer_password:
        return hash_password(settings.viewer_password)
    return None


def check_login_rate(ip: str, limit: int = 10, window: int = 300) -> None:
    now = time.time()
    attempts = [t for t in _login_attempts[ip] if now - t < window]
    _login_attempts[ip] = attempts
    if len(attempts) >= limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")
    _login_attempts[ip].append(now)


def create_access_token(user: AuthUser, settings: Settings) -> str:
    exp = datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours)
    return jwt.encode(
        {"sub": user.username, "role": user.role, "exp": exp},
        settings.resolved_jwt_secret(),
        algorithm="HS256",
    )


def decode_token(token: str, settings: Settings) -> AuthUser:
    try:
        payload = jwt.decode(token, settings.resolved_jwt_secret(), algorithms=["HS256"])
        return AuthUser(username=payload["sub"], role=payload["role"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from exc


def issue_csrf() -> str:
    return secrets.token_urlsafe(32)


def validate_csrf(*, header_token: str | None, cookie_token: str | None) -> None:
    """Double-submit cookie check — works across process restarts (no memory store)."""
    if (
        not header_token
        or not cookie_token
        or not secrets.compare_digest(header_token, cookie_token)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")


def set_auth_cookies(response: Response, access_token: str, csrf: str, settings: Settings) -> None:
    max_age = settings.session_ttl_hours * 3600
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        samesite="lax",
        max_age=max_age,
        path="/",
    )
    response.set_cookie(
        "csrf_token",
        csrf,
        httponly=False,
        samesite="lax",
        max_age=max_age,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("csrf_token", path="/")


async def get_current_user(
    access_token: Annotated[str | None, Cookie()] = None,
    settings: Settings = Depends(get_settings),
) -> AuthUser:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return decode_token(access_token, settings)


async def require_admin(user: Annotated[AuthUser, Depends(get_current_user)]) -> AuthUser:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return user


def require_csrf(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    validate_csrf(
        header_token=request.headers.get("X-CSRF-Token"),
        cookie_token=request.cookies.get("csrf_token"),
    )
