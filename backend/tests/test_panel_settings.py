from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings
from app.panel_settings import (
    PanelSettings,
    load_overrides,
    merge_panel_settings,
    save_panel_settings,
)


def test_save_and_merge_overrides(tmp_path: Path):
    db = tmp_path / "panel.db"
    settings = Settings(
        panel_settings_db=str(db),
        web_listen="",
        web_domain="",
        web_port=8000,
        web_cert_file="",
        web_key_file="",
        web_base_path="/",
    )

    assert merge_panel_settings(settings).web_port == 8000

    saved = save_panel_settings(
        PanelSettings(
            web_listen="127.0.0.1",
            web_domain="monitor.example.com",
            web_port=8443,
            web_cert_file="/certs/fullchain.pem",
            web_key_file="/certs/privkey.pem",
            web_base_path="secret",
        ),
        settings,
    )
    assert saved.web_base_path == "/secret"
    assert db.exists()

    loaded = load_overrides(db)
    assert loaded is not None
    assert loaded.web_port == 8443
    assert loaded.web_domain == "monitor.example.com"
    assert loaded.tls_enabled() is True

    merged = merge_panel_settings(settings)
    assert merged.web_listen == "127.0.0.1"
    assert merged.web_port == 8443
    assert merged.normalized_base_path() == "/secret"


def test_invalid_port_rejected(tmp_path: Path):
    db = tmp_path / "panel.db"
    settings = Settings(panel_settings_db=str(db))
    with pytest.raises(ValueError):
        save_panel_settings(PanelSettings(web_port=0), settings)
