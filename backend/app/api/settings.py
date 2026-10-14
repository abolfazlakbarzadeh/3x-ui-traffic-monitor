from __future__ import annotations

import asyncio
import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.panel_settings import PanelSettings, merge_panel_settings, save_panel_settings
from app.security import AuthUser, require_admin, require_csrf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


class PanelSettingsIn(BaseModel):
    web_listen: str = ""
    web_domain: str = ""
    web_port: int = Field(8000, ge=1, le=65535)
    web_cert_file: str = ""
    web_key_file: str = ""
    web_base_path: str = "/"
    restart: bool = True


class PanelSettingsOut(BaseModel):
    web_listen: str
    web_domain: str
    web_port: int
    web_cert_file: str
    web_key_file: str
    web_base_path: str
    tls_enabled: bool
    restarting: bool = False


def _schedule_restart() -> None:
    async def _exit() -> None:
        await asyncio.sleep(0.6)
        logger.warning("Exiting process to apply panel settings (Docker should restart)")
        os._exit(0)

    asyncio.get_running_loop().create_task(_exit())


@router.get("/panel", response_model=PanelSettingsOut)
async def get_panel_settings(
    _: Annotated[AuthUser, Depends(require_admin)],
) -> PanelSettingsOut:
    panel = merge_panel_settings()
    return PanelSettingsOut(**panel.to_public_dict(), restarting=False)


@router.put("/panel", response_model=PanelSettingsOut, dependencies=[Depends(require_csrf)])
async def put_panel_settings(
    body: PanelSettingsIn,
    _: Annotated[AuthUser, Depends(require_admin)],
) -> PanelSettingsOut:
    panel = PanelSettings(
        web_listen=body.web_listen,
        web_domain=body.web_domain,
        web_port=body.web_port,
        web_cert_file=body.web_cert_file,
        web_key_file=body.web_key_file,
        web_base_path=body.web_base_path,
    )
    try:
        saved = save_panel_settings(panel)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    restarting = False
    if body.restart:
        restarting = True
        _schedule_restart()

    return PanelSettingsOut(**saved.to_public_dict(), restarting=restarting)
