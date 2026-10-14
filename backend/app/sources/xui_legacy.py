"""Best-effort adapter for pre-v3 3x-ui panels.

Legacy endpoints (no longer in v3):
- GET /panel/api/inbounds/getClientTraffics/:email
- GET /panel/api/inbounds/getClientTrafficsById/:id
- GET /panel/api/inbounds/onlines
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import ServerConfig
from app.sources.base import ClientTrafficSnapshot
from app.sources.xui_api import XuiApiSource

logger = logging.getLogger(__name__)


class XuiLegacySource(XuiApiSource):
    """Falls back to inbound-centric endpoints when /clients/list is missing."""

    async def list_clients(self) -> list[ClientTrafficSnapshot]:
        obj = await self._request("GET", "/panel/api/inbounds/list")
        clients: list[ClientTrafficSnapshot] = []
        for inbound in obj or []:
            for traffic in inbound.get("clientStats") or []:
                clients.append(
                    ClientTrafficSnapshot(
                        email=traffic.get("email"),
                        up=int(traffic.get("up") or 0),
                        down=int(traffic.get("down") or 0),
                        total=int(traffic.get("total") or 0),
                        expiry_time=int(traffic.get("expiryTime") or 0),
                        enable=bool(traffic.get("enable", True)),
                        reset_count=int(traffic.get("resetCount") or 0),
                        client_id=int(traffic["id"]) if traffic.get("id") is not None else None,
                        last_online=int(traffic.get("lastOnline") or 0),
                        inbound_ids=[inbound.get("id")] if inbound.get("id") is not None else [],
                        raw=traffic,
                    )
                )
        return clients

    async def get_onlines(self) -> list[str]:
        try:
            obj = await self._request("GET", "/panel/api/inbounds/onlines")
            return list(obj or [])
        except Exception as exc:  # noqa: BLE001
            logger.warning("legacy onlines failed for %s: %s", self.name, exc)
            return []

    async def get_last_online(self) -> dict[str, int]:
        return {}

    async def probe_capabilities(self) -> list[str]:
        logger.warning("Server %s using legacy adapter (best effort)", self.name)
        return ["legacy_mode"]


async def build_source(config: ServerConfig) -> XuiApiSource | Any:
    if config.source_mode == "sqlite":
        from app.sources.xui_sqlite import XuiSqliteSource

        return XuiSqliteSource(config)

    api = XuiApiSource(config)
    try:
        # Probe clients/list existence without full list when possible
        await api._ensure_auth()
        resp = await api._client.get(api._url("/panel/api/clients/list"))
        if resp.status_code == 404:
            await api.close()
            return XuiLegacySource(config)
    except httpx.HTTPError:
        pass
    return api
