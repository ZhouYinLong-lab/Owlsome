"""Minimal admin token guard for LAN/server test deployments.

When ADMIN_TOKEN is set in the environment, admin write endpoints require
the header ``X-Admin-Token: <token>``.  When ADMIN_TOKEN is empty or unset
(typical local demo), all admin endpoints are open so existing smoke tests
and the local development workflow are unaffected.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Header, HTTPException


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parents[1]

# The admin guard is imported near the top of app.main, before other services
# load dotenv files. Load both project-level and backend-level .env files here
# so server deployments that copy .env.server.example to .env actually enforce
# ADMIN_TOKEN without requiring shell-level exports.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env", override=True)

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "").strip()


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    """FastAPI dependency that gates admin write operations.

    Callers that donʼt need the guard can omit ``dependencies=``; endpoints
    that *do* need it add ``dependencies=[Depends(require_admin_token)]``.
    """
    if not ADMIN_TOKEN:
        # No token configured → open for local demo compatibility.
        return

    if not x_admin_token:
        raise HTTPException(
            status_code=403,
            detail="管理员操作需要有效的 X-Admin-Token",
        )

    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(
            status_code=403,
            detail="管理员操作需要有效的 X-Admin-Token",
        )
