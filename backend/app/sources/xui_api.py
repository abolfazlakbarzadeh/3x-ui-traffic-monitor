from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

import httpx

from app.config import PasswordAuth, ServerConfig, TokenAuth
from app.sources.base import REQUIRED_API_PATHS, ClientTrafficSnapshot

logger = logging.getLogger(__name__)


class MonitorScopeError(RuntimeError):
    """Raised when a monitor-scope token cannot access client endpoints."""


class XuiApiSource:
    def __init__(self, config: ServerConfig) -> None:
        self.name = config.name
        self.config = config
        self._base = config.base_url.rstrip("/") + self._normalize_base_path(config.web_base_path)
        self._client = httpx.AsyncClient(
            verify=config.verify_tls,
            timeout=30.0,
            headers={"X-Requested-With": "XMLHttpRequest"},
            follow_redirects=True,
        )
        self._csrf: str | None = None
        self._logged_in = False

    @staticmethod
    def _normalize_base_path(path: str) -> str:
        if not path or path == "/":
            return ""
        if not path.startswith("/"):
            path = "/" + path
        return path.rstrip("/")

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return urljoin(self._base + "/", path.lstrip("/"))

    async def _ensure_auth(self) -> None:
        auth = self.config.auth
        if isinstance(auth, TokenAuth):
            self._client.headers["Authorization"] = f"Bearer {auth.token}"
            return
        if self._logged_in:
            return
        await self._login_password(auth)

    async def _login_password(self, auth: PasswordAuth) -> None:
        csrf_resp = await self._client.get(self._url("/csrf-token"))
        csrf_resp.raise_for_status()
        body = csrf_resp.json()
        self._csrf = body.get("obj") or body.get("csrf")
        payload = {
            "username": auth.username,
            "password": auth.password,
        }
        if auth.totp_secret:
            payload["twoFactorCode"] = auth.totp_secret
        headers = {"X-CSRF-Token": self._csrf or ""}
        login = await self._client.post(self._url("/login"), json=payload, headers=headers)
        if login.status_code in {401, 404}:
            raise RuntimeError(f"Login failed for {self.name}: HTTP {login.status_code}")
        login.raise_for_status()
        data = login.json()
        if data.get("success") is False:
            raise RuntimeError(f"Login failed for {self.name}: {data.get('msg')}")
        self._logged_in = True

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        await self._ensure_auth()
        if self._csrf and method.upper() != "GET":
            headers = kwargs.pop("headers", {})
            headers["X-CSRF-Token"] = self._csrf
            kwargs["headers"] = headers
        resp = await self._client.request(method, self._url(path), **kwargs)
        if resp.status_code in {401, 404} and isinstance(self.config.auth, PasswordAuth):
            self._logged_in = False
            await self._login_password(self.config.auth)
            resp = await self._client.request(method, self._url(path), **kwargs)
        if resp.status_code == 401:
            raise RuntimeError(f"Unauthorized talking to {self.name} ({path})")
        if resp.status_code == 403:
            text = resp.text.lower()
            if "scope" in text or "monitor" in text or "permission" in text:
                raise MonitorScopeError(
                    f"Token for {self.name} appears to lack admin scope "
                    "(monitor-scope tokens cannot access client endpoints). "
                    "Create an admin-scope API token in 3x-ui Settings → Security."
                )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and data.get("success") is False:
            msg = str(data.get("msg") or "request failed")
            lower = msg.lower()
            if "scope" in lower or "permission" in lower or "forbidden" in lower:
                raise MonitorScopeError(
                    f"Token for {self.name} needs admin scope, not monitor scope: {msg}"
                )
            raise RuntimeError(f"{self.name} {path}: {msg}")
        return data.get("obj") if isinstance(data, dict) and "obj" in data else data

    @staticmethod
    def _from_client_obj(obj: dict[str, Any]) -> ClientTrafficSnapshot:
        traffic = obj.get("traffic") or obj
        email = obj.get("email") or traffic.get("email")
        return ClientTrafficSnapshot(
            email=email,
            up=int(traffic.get("up") or 0),
            down=int(traffic.get("down") or 0),
            total=int(traffic.get("total") or 0),
            expiry_time=int(
                obj.get("expiryTime")
                or traffic.get("expiryTime")
                or 0
            ),
            enable=bool(obj.get("enable", traffic.get("enable", True))),
            reset_count=int(traffic.get("resetCount") or obj.get("resetCount") or 0),
            client_id=(
                int(traffic["id"])
                if traffic.get("id") is not None
                else (int(obj["id"]) if obj.get("id") is not None else None)
            ),
            last_online=int(traffic.get("lastOnline") or obj.get("lastOnline") or 0),
            inbound_ids=list(obj.get("inboundIds") or []),
            raw=obj,
        )

    async def list_clients(self) -> list[ClientTrafficSnapshot]:
        try:
            obj = await self._request("GET", "/panel/api/clients/list")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise FileNotFoundError("clients/list not found; try legacy adapter") from exc
            raise
        if not obj:
            return []
        if isinstance(obj, dict) and "items" in obj:
            items = obj["items"]
        else:
            items = obj
        return [self._from_client_obj(item) for item in items]

    async def get_onlines(self) -> list[str]:
        obj = await self._request("POST", "/panel/api/clients/onlines")
        return list(obj or [])

    async def get_last_online(self) -> dict[str, int]:
        obj = await self._request("POST", "/panel/api/clients/lastOnline")
        return {k: int(v) for k, v in (obj or {}).items()}

    async def get_server_status(self) -> dict[str, Any] | None:
        try:
            return await self._request("GET", "/panel/api/server/status")
        except Exception as exc:  # noqa: BLE001
            logger.warning("server status failed for %s: %s", self.name, exc)
            return None

    async def probe_capabilities(self) -> list[str]:
        missing: list[str] = []
        try:
            await self._ensure_auth()
            resp = await self._client.get(self._url("/panel/api/openapi.json"))
            if resp.status_code != 200:
                logger.warning("openapi.json unavailable for %s (HTTP %s)", self.name, resp.status_code)
                return missing
            spec = resp.json()
            paths = set((spec.get("paths") or {}).keys())
            for required in REQUIRED_API_PATHS:
                # OpenAPI may use templated or unprefixed variants
                variants = {
                    required,
                    required.replace("/panel/api", ""),
                    required.replace("{email}", "{email}"),
                }
                if not any(v in paths or v.rstrip("/") in paths for v in variants):
                    # softer match: any path ending with the leaf
                    leaf = required.split("/panel/api")[-1]
                    if not any(leaf in p or p.endswith(leaf.strip("/")) for p in paths):
                        missing.append(required)
                        logger.warning("Panel %s OpenAPI missing path %s", self.name, required)
        except Exception as exc:  # noqa: BLE001
            logger.warning("capability probe failed for %s: %s", self.name, exc)
        return missing

    async def close(self) -> None:
        await self._client.aclose()
