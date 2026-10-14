from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

WRITE_PATHS = {
    "/panel/api/clients/resetTraffic/{email}",
    "/panel/api/clients/bulkResetTraffic",
}


def ok(obj: Any = None, msg: str = "") -> dict:
    return {"success": True, "msg": msg, "obj": obj}


def create_mock_panel(
    *,
    clients: list[dict] | None = None,
    token: str = "admin-token",
    scope: str = "admin",
    require_password: bool = False,
) -> FastAPI:
    app = FastAPI()
    state = {
        "clients": clients or [],
        "onlines": [],
        "logged_in": not require_password,
        "csrf": "test-csrf",
        "token": token,
        "scope": scope,
    }

    def _auth(authorization: str | None, xhr: str | None) -> None:
        if require_password:
            if not state["logged_in"]:
                if xhr == "XMLHttpRequest":
                    raise HTTPException(status_code=401, detail="login required")
                raise HTTPException(status_code=404, detail="not found")
            return
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing token")
        got = authorization.removeprefix("Bearer ").strip()
        if got != state["token"]:
            raise HTTPException(status_code=401, detail="bad token")
        if state["scope"] == "monitor":
            raise HTTPException(status_code=403, detail="insufficient scope: monitor")

    @app.get("/csrf-token")
    async def csrf_token():
        return ok(state["csrf"])

    @app.post("/login")
    async def login(payload: dict):
        if payload.get("username") == "admin" and payload.get("password") == "secret":
            state["logged_in"] = True
            return ok(True)
        return JSONResponse(ok(False, "bad credentials") | {"success": False}, status_code=200)

    @app.get("/panel/api/clients/list")
    async def clients_list(
        authorization: str | None = Header(default=None),
        x_requested_with: str | None = Header(default=None, alias="X-Requested-With"),
    ):
        _auth(authorization, x_requested_with)
        return ok(state["clients"])

    @app.get("/panel/api/clients/traffic/{email}")
    async def client_traffic(email: str, authorization: str | None = Header(default=None)):
        _auth(authorization, "XMLHttpRequest")
        for c in state["clients"]:
            if c["email"] == email:
                return ok(c.get("traffic") or c)
        raise HTTPException(status_code=404)

    @app.post("/panel/api/clients/onlines")
    async def onlines(authorization: str | None = Header(default=None)):
        _auth(authorization, "XMLHttpRequest")
        return ok(state["onlines"])

    @app.post("/panel/api/clients/lastOnline")
    async def last_online(authorization: str | None = Header(default=None)):
        _auth(authorization, "XMLHttpRequest")
        return ok({c["email"]: c.get("traffic", {}).get("lastOnline", 0) for c in state["clients"]})

    @app.get("/panel/api/server/status")
    async def status(authorization: str | None = Header(default=None)):
        _auth(authorization, "XMLHttpRequest")
        return ok({"cpu": 1, "mem": 1, "xray": True})

    @app.get("/panel/api/openapi.json")
    async def openapi_json():
        return {
            "paths": {
                "/panel/api/clients/list": {},
                "/panel/api/clients/traffic/{email}": {},
                "/panel/api/clients/get/{email}": {},
                "/panel/api/inbounds/list": {},
                "/panel/api/clients/onlines": {},
                "/panel/api/clients/lastOnline": {},
                "/panel/api/server/status": {},
            }
        }

    @app.get("/panel/api/inbounds/list")
    async def inbounds(authorization: str | None = Header(default=None)):
        _auth(authorization, "XMLHttpRequest")
        return ok([])

    app.state = state  # type: ignore[attr-defined]
    return app


def sample_client(
    email: str,
    *,
    up: int,
    down: int,
    client_id: int = 1,
    reset_count: int = 0,
    total: int = 0,
) -> dict:
    return {
        "email": email,
        "enable": True,
        "expiryTime": 0,
        "inboundIds": [1],
        "traffic": {
            "id": client_id,
            "email": email,
            "up": up,
            "down": down,
            "total": total,
            "enable": True,
            "expiryTime": 0,
            "resetCount": reset_count,
            "lastOnline": 0,
        },
    }
