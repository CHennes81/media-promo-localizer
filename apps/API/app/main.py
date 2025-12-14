"""
FastAPI application entry point for Media Promo Localizer backend.
"""
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.routers import health, jobs
from app.routers.jobs import _get_localization_mode
from app.utils.errors import APIError, create_error_response

# Configure logging with both stdout and file handlers
log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Create logs directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "app.log"

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(log_level)

# Remove existing handlers to avoid duplicates
root_logger.handlers.clear()

# StreamHandler for stdout
stream_handler = logging.StreamHandler()
stream_handler.setLevel(log_level)
stream_handler.setFormatter(logging.Formatter(log_format))
root_logger.addHandler(stream_handler)

# FileHandler for logfile
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(log_level)
file_handler.setFormatter(logging.Formatter(log_format))
root_logger.addHandler(file_handler)

logger = logging.getLogger("media_promo_localizer")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests with correlation IDs."""

    async def dispatch(self, request: Request, call_next):
        # Get or generate request ID
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Log request start
        start_time = time.time()
        start_timestamp = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"RequestStart request={request_id} method={request.method} path={request.url.path} "
            f"client_ip={client_ip} start_timestamp={start_timestamp}"
        )

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            response = JSONResponse(
                status_code=500,
                content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}},
            )
            logger.error(
                f"RequestError request={request_id} method={request.method} path={request.url.path} "
                f"error={type(e).__name__}",
                exc_info=True,
            )

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        end_timestamp = datetime.now(timezone.utc).isoformat()

        # Log request end
        logger.info(
            f"RequestEnd request={request_id} method={request.method} path={request.url.path} "
            f"status={status_code} durationMs={duration_ms} end_timestamp={end_timestamp}"
        )

        # Add request ID to response headers
        response.headers["X-Request-Id"] = request_id

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.
    Sets startup_time on app.state for uptime tracking.
    """
    # Startup: set the startup timestamp
    app.state.startup_time = datetime.now(timezone.utc)

    # Log resolved configuration (redacting secrets)
    mode = _get_localization_mode()
    logger.info("ConfigStart")
    logger.info(f"Config LOCALIZATION_MODE={mode}")
    logger.info(f"Config LOG_LEVEL={settings.LOG_LEVEL}")
    logger.info(f"Config TRACE_CALLS={settings.TRACE_CALLS}")
    logger.info(f"Config MAX_UPLOAD_MB={settings.MAX_UPLOAD_MB}")
    logger.info(f"Config JOB_TTL_SECONDS={settings.JOB_TTL_SECONDS}")
    logger.info(f"Config SKIP_OCR={settings.SKIP_OCR}")
    logger.info(f"Config SKIP_TRANSLATION={settings.SKIP_TRANSLATION}")
    logger.info(f"Config SKIP_INPAINT={settings.SKIP_INPAINT}")
    logger.info(f"Config SKIP_PACKAGING={settings.SKIP_PACKAGING}")
    logger.info(f"Config OCR_IMAGE_LONG_SIDE_PX={settings.OCR_IMAGE_LONG_SIDE_PX}")
    logger.info(f"Config TRANSLATION_IMAGE_LONG_SIDE_PX={settings.TRANSLATION_IMAGE_LONG_SIDE_PX}")
    logger.info(f"Config INPAINT_IMAGE_LONG_SIDE_PX={settings.INPAINT_IMAGE_LONG_SIDE_PX}")

    if mode == "live":
        ocr_client = "CloudOcrClient (Google Vision)"
        translation_client = "LlmTranslationClient (OpenAI)"
        inpainting_client = "StubInpaintingClient"
        logger.info(
            f"Config Engine=LiveLocalizationEngine "
            f"OCR={ocr_client} Translation={translation_client} "
            f"Inpainting={inpainting_client}"
        )
        # Log endpoints (sanitized, no secrets)
        ocr_endpoint = (
            settings.OCR_API_ENDPOINT or "https://vision.googleapis.com/v1/images:annotate"
        )
        ocr_endpoint_base = ocr_endpoint.split("?")[0] if "?" in ocr_endpoint else ocr_endpoint
        logger.info(f"Config OCR_ENDPOINT={ocr_endpoint_base}")
        logger.info(f"Config TRANSLATION_MODEL={settings.TRANSLATION_MODEL}")
        logger.info(f"Config OCR_API_KEY={'<SET>' if settings.OCR_API_KEY else '<NOT_SET>'}")
        logger.info(f"Config OPENAI_API_KEY={'<SET>' if settings.OPENAI_API_KEY else '<NOT_SET>'}")
    else:
        logger.info("Config Engine=MockLocalizationEngine")

    logger.info("ConfigEnd")
    logger.info("Application startup complete")
    yield
    # Shutdown: cleanup if needed (currently none)
    logger.info("Application shutdown")


app = FastAPI(
    title="Media Promo Localizer API",
    description="Backend API for localizing promotional artwork",
    version="0.2.0",
    lifespan=lifespan,
)

# Request logging middleware (must be first to capture all requests)
app.add_middleware(RequestLoggingMiddleware)

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
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        f"UnhandledException request={request_id} error={type(exc).__name__} message={str(exc)}",
        exc_info=True,
    )
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
