"""
Logging utilities for structured logging, service call tracking, and method tracing.
"""
import functools
import logging
import time
from typing import Any, Callable, Optional, TypeVar

from app.config import settings

logger = logging.getLogger("media_promo_localizer")

F = TypeVar("F", bound=Callable[..., Any])


def trace_calls(func: F) -> F:
    """
    Decorator to log method entry/exit when TRACE_CALLS is enabled.

    Logs function name, args summary (excluding secrets/images), and duration.
    Only active when TRACE_CALLS=true.
    """
    import inspect

    if not settings.TRACE_CALLS:
        return func

    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__qualname__}"
            # Summarize args (exclude secrets and large binary data)
            args_summary = []
            for i, arg in enumerate(args):
                if isinstance(arg, (str, int, float, bool, type(None))):
                    args_summary.append(f"arg{i}={arg}")
                elif isinstance(arg, bytes):
                    args_summary.append(f"arg{i}=<bytes:{len(arg)}>")
                else:
                    args_summary.append(f"arg{i}=<{type(arg).__name__}>")

            for key, value in kwargs.items():
                if key.lower() in ("api_key", "key", "token", "secret", "password"):
                    args_summary.append(f"{key}=<REDACTED>")
                elif isinstance(value, bytes):
                    args_summary.append(f"{key}=<bytes:{len(value)}>")
                elif isinstance(value, (str, int, float, bool, type(None))):
                    args_summary.append(f"{key}={value}")
                else:
                    args_summary.append(f"{key}=<{type(value).__name__}>")

            logger.debug(f"[TRACE] ENTER {func_name}({', '.join(args_summary)})")
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration_ms = int((time.perf_counter() - start) * 1000)
                logger.debug(f"[TRACE] EXIT {func_name} durationMs={duration_ms}")
                return result
            except Exception as e:
                duration_ms = int((time.perf_counter() - start) * 1000)
                logger.debug(
                    f"[TRACE] EXIT {func_name} durationMs={duration_ms} error={type(e).__name__}"
                )
                raise

        return async_wrapper  # type: ignore
    else:

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__qualname__}"
            # Summarize args (exclude secrets and large binary data)
            args_summary = []
            for i, arg in enumerate(args):
                if isinstance(arg, (str, int, float, bool, type(None))):
                    args_summary.append(f"arg{i}={arg}")
                elif isinstance(arg, bytes):
                    args_summary.append(f"arg{i}=<bytes:{len(arg)}>")
                else:
                    args_summary.append(f"arg{i}=<{type(arg).__name__}>")

            for key, value in kwargs.items():
                if key.lower() in ("api_key", "key", "token", "secret", "password"):
                    args_summary.append(f"{key}=<REDACTED>")
                elif isinstance(value, bytes):
                    args_summary.append(f"{key}=<bytes:{len(value)}>")
                elif isinstance(value, (str, int, float, bool, type(None))):
                    args_summary.append(f"{key}={value}")
                else:
                    args_summary.append(f"{key}=<{type(value).__name__}>")

            logger.debug(f"[TRACE] ENTER {func_name}({', '.join(args_summary)})")
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.perf_counter() - start) * 1000)
                logger.debug(f"[TRACE] EXIT {func_name} durationMs={duration_ms}")
                return result
            except Exception as e:
                duration_ms = int((time.perf_counter() - start) * 1000)
                logger.debug(
                    f"[TRACE] EXIT {func_name} durationMs={duration_ms} error={type(e).__name__}"
                )
                raise

        return sync_wrapper  # type: ignore


async def log_service_call(
    service_name: str,
    endpoint: str,
    method: str = "POST",
    request_id: Optional[str] = None,
    job_id: Optional[str] = None,
    payload_size_bytes: Optional[int] = None,
    call_func: Callable[[], Any] = None,
) -> tuple[Any, int, int]:
    """
    Log service call (outbound/inbound) and execute the call.

    Args:
        service_name: Name of the service (e.g., "OCR", "TRANSLATION")
        endpoint: Endpoint URL (sanitized, no secrets)
        method: HTTP method
        request_id: Request correlation ID
        job_id: Job correlation ID
        payload_size_bytes: Size of request payload in bytes
        call_func: Async function to execute for the actual call

    Returns:
        Tuple of (result, status_code, duration_ms)
    """
    outbound_timestamp = time.time()
    correlation = []
    if request_id:
        correlation.append(f"request={request_id}")
    if job_id:
        correlation.append(f"job={job_id}")
    correlation_str = " ".join(correlation) if correlation else ""

    logger.info(
        f"ServiceCall {correlation_str} service={service_name} endpoint={endpoint} "
        f"method={method} outbound_timestamp={outbound_timestamp:.3f} "
        f"payloadSizeBytes={payload_size_bytes or 0}"
    )

    call_start = time.perf_counter()
    status_code = 200  # Default for successful calls
    try:
        result = await call_func()
        call_duration_ms = int((time.perf_counter() - call_start) * 1000)
        response_timestamp = time.time()

        # Try to get response size if result is bytes
        response_size = len(result) if isinstance(result, bytes) else 0

        logger.info(
            f"ServiceResponse {correlation_str} service={service_name} status={status_code} "
            f"response_timestamp={response_timestamp:.3f} durationMs={call_duration_ms} "
            f"responseSizeBytes={response_size}"
        )

        return result, status_code, call_duration_ms
    except Exception as e:
        call_duration_ms = int((time.perf_counter() - call_start) * 1000)
        response_timestamp = time.time()

        # Determine status code from exception type
        if hasattr(e, "status_code"):
            status_code = e.status_code
        elif "timeout" in str(e).lower():
            status_code = 504
        else:
            status_code = 500

        logger.error(
            f"ServiceResponse {correlation_str} service={service_name} status={status_code} "
            f"response_timestamp={response_timestamp:.3f} durationMs={call_duration_ms} "
            f"error={type(e).__name__}",
            exc_info=True,
        )
        raise
