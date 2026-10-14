from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import ServerConfig, TokenAuth, PasswordAuth
from app.sources.xui_api import MonitorScopeError, XuiApiSource
from mock_xui import create_mock_panel, sample_client


@pytest.mark.asyncio
async def test_list_clients_token_auth():
    app = create_mock_panel(
        clients=[sample_client("a@x", up=10, down=20)],
        token="good",
    )
    transport = ASGITransport(app=app)
    # Drive mock via real httpx against ASGI by patching client base
    source = XuiApiSource(
        ServerConfig(
            name="s1",
            base_url="http://test",
            web_base_path="/",
            auth=TokenAuth(token="good"),
        )
    )
    source._client = AsyncClient(transport=transport, base_url="http://test", headers={"X-Requested-With": "XMLHttpRequest"})
    clients = await source.list_clients()
    assert len(clients) == 1
    assert clients[0].email == "a@x"
    assert clients[0].up == 10
    await source.close()


@pytest.mark.asyncio
async def test_bad_token_401():
    app = create_mock_panel(token="good")
    transport = ASGITransport(app=app)
    source = XuiApiSource(
        ServerConfig(name="s1", base_url="http://test", auth=TokenAuth(token="bad"))
    )
    source._client = AsyncClient(transport=transport, base_url="http://test", headers={"X-Requested-With": "XMLHttpRequest"})
    with pytest.raises(Exception):
        await source.list_clients()
    await source.close()


@pytest.mark.asyncio
async def test_monitor_scope_clear_error():
    app = create_mock_panel(token="mon", scope="monitor")
    transport = ASGITransport(app=app)
    source = XuiApiSource(
        ServerConfig(name="s1", base_url="http://test", auth=TokenAuth(token="mon"))
    )
    source._client = AsyncClient(transport=transport, base_url="http://test", headers={"X-Requested-With": "XMLHttpRequest"})
    with pytest.raises(MonitorScopeError, match="admin scope"):
        await source.list_clients()
    await source.close()


@pytest.mark.asyncio
async def test_password_relogin_after_401():
    app = create_mock_panel(require_password=True, clients=[sample_client("b@x", up=1, down=2)])
    transport = ASGITransport(app=app)
    source = XuiApiSource(
        ServerConfig(
            name="s1",
            base_url="http://test",
            auth=PasswordAuth(username="admin", password="secret"),
        )
    )
    source._client = AsyncClient(transport=transport, base_url="http://test", headers={"X-Requested-With": "XMLHttpRequest"})
    clients = await source.list_clients()
    assert clients[0].email == "b@x"
    # Force re-login path
    app.state["logged_in"] = False
    clients = await source.list_clients()
    assert len(clients) == 1
    await source.close()
