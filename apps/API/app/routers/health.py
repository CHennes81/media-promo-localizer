"""
Health check endpoint.
"""
import time

from fastapi import APIRouter

from app.main import _startup_time

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    uptime_seconds = time.time() - _startup_time
    return {
        "status": "ok",
        "uptimeSeconds": int(uptime_seconds),
        "version": "0.2.0",
    }
