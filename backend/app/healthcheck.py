"""Container health probe that follows merged panel port / TLS."""

from __future__ import annotations

import ssl
import sys
import urllib.error
import urllib.request

from app.panel_settings import merge_panel_settings


def main() -> int:
    panel = merge_panel_settings()
    port = panel.web_port
    scheme = "https" if panel.tls_enabled() else "http"
    url = f"{scheme}://127.0.0.1:{port}/healthz"
    # Local loopback probe only — cert may be issued for the public web_domain.
    ctx = ssl._create_unverified_context() if scheme == "https" else None
    try:
        with urllib.request.urlopen(url, timeout=5, context=ctx) as resp:  # noqa: S310
            return 0 if resp.status == 200 else 1
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"healthcheck failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
