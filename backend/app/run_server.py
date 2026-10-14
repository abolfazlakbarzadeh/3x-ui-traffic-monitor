"""Start uvicorn using merged panel settings (env + SQLite)."""

from __future__ import annotations

import os
import sys

import uvicorn

from app.panel_settings import merge_panel_settings


def main() -> None:
    panel = merge_panel_settings()
    host = panel.web_listen.strip() or "0.0.0.0"
    port = int(panel.web_port)
    kwargs: dict = {
        "app": "app.main:app",
        "host": host,
        "port": port,
        "proxy_headers": True,
        "forwarded_allow_ips": "*",
    }
    if panel.tls_enabled():
        cert = panel.web_cert_file
        key = panel.web_key_file
        if os.path.isfile(cert) and os.path.isfile(key):
            kwargs["ssl_certfile"] = cert
            kwargs["ssl_keyfile"] = key
            print(f"Starting HTTPS on {host}:{port} base_path={panel.normalized_base_path()}")
        else:
            print(
                f"TLS files missing ({cert!r}, {key!r}); starting without TLS",
                file=sys.stderr,
            )
            print(f"Starting HTTP on {host}:{port} base_path={panel.normalized_base_path()}")
    else:
        print(f"Starting HTTP on {host}:{port} base_path={panel.normalized_base_path()}")

    uvicorn.run(**kwargs)


if __name__ == "__main__":
    main()
