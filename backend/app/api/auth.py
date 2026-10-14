from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.config import Settings, get_settings
from app.schemas import LoginRequest
from app.security import (
    AuthUser,
    check_login_rate,
    clear_auth_cookies,
    create_access_token,
    get_current_user,
    issue_csrf,
    require_csrf,
    resolve_password_hash,
    set_auth_cookies,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
) -> dict:
    check_login_rate(request.client.host if request.client else "unknown")
    user: AuthUser | None = None

    admin_hash = resolve_password_hash(settings, "admin")
    if body.username == settings.admin_username and admin_hash and verify_password(admin_hash, body.password):
        user = AuthUser(username=body.username, role="admin")
    elif (
        settings.viewer_username
        and body.username == settings.viewer_username
    ):
        viewer_hash = resolve_password_hash(settings, "viewer")
        if viewer_hash and verify_password(viewer_hash, body.password):
            user = AuthUser(username=body.username, role="viewer")

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(user, settings)
    csrf = issue_csrf()
    set_auth_cookies(response, token, csrf, settings)
    return {"success": True, "username": user.username, "role": user.role, "csrf_token": csrf}


@router.post("/logout", dependencies=[Depends(require_csrf)])
async def logout(response: Response) -> dict:
    clear_auth_cookies(response)
    return {"success": True}


@router.get("/me")
async def me(user: AuthUser = Depends(get_current_user)) -> dict:
    return {"username": user.username, "role": user.role}
