"""
FastAPI application entry point for Media Promo Localizer backend.
"""
import logging
#import time
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import health, jobs
from app.utils.errors import APIError, create_error_response

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("media_promo_localizer")

app = FastAPI(
    title="Media Promo Localizer API",
    description="Backend API for localizing promotional artwork",
    version="0.2.0",
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """Handle APIError exceptions."""
    return create_error_response(exc)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return create_error_response(
        APIError(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred.",
            http_status=500,
        )
    )


# Include routers
app.include_router(health.router)
app.include_router(jobs.router, prefix="/v1")

