from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ClientTrafficSnapshot:
    email: str
    up: int
    down: int
    total: int = 0
    expiry_time: int = 0
    enable: bool = True
    reset_count: int = 0
    client_id: int | None = None
    last_online: int = 0
    inbound_ids: list[int] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class TrafficSource(Protocol):
    name: str

    async def list_clients(self) -> list[ClientTrafficSnapshot]:
        """Fetch all clients with current cumulative traffic."""

    async def get_onlines(self) -> list[str]:
        """Emails currently online. Empty if unsupported."""

    async def get_last_online(self) -> dict[str, int]:
        """Map email -> lastOnline ms epoch."""

    async def get_server_status(self) -> dict[str, Any] | None:
        """Optional panel health payload."""

    async def probe_capabilities(self) -> list[str]:
        """Return missing expected OpenAPI paths (warnings)."""

    async def close(self) -> None:
        """Release resources."""


REQUIRED_API_PATHS = [
    "/panel/api/clients/list",
    "/panel/api/clients/traffic/{email}",
    "/panel/api/clients/get/{email}",
    "/panel/api/inbounds/list",
    "/panel/api/clients/onlines",
    "/panel/api/clients/lastOnline",
    "/panel/api/server/status",
]
