"""
Health check endpoint.
"""
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request):
    """
    Basic liveness/uptime check.
    """
    startup_time = getattr(request.app.state, "startup_time", None)
    now = datetime.now(timezone.utc)

    if startup_time is None:
        uptime_seconds = 0
    else:
        uptime_seconds = int((now - startup_time).total_seconds())

    return {
        "status": "ok",
        "uptimeSeconds": uptime_seconds,
        "version": "0.2.0",  # or settings.VERSION if you have that
    }

