"""
middleware.py

All middleware for the OrthoBite API.
Call setup_middleware(app) from main.py to register everything.
"""

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from config.settings import settings

logger = logging.getLogger("orthobite")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ---------------------------------------------------------------------------
# Allowed origins for CORS (loaded from environment)
# ---------------------------------------------------------------------------

_configured = settings.FRONTEND_URL.strip()

ALLOWED_ORIGINS = list({
    _configured,
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:3000",
})


# ---------------------------------------------------------------------------
# Request Logging Middleware
# Logs every incoming request with method, path, status code, and duration.
# ---------------------------------------------------------------------------

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip logging for websocket requests if needed
        if request.url.path.startswith("/ws/"):
            return await call_next(request)

        request_id = str(uuid.uuid4())[:8]  # short ID for log correlation
        start = time.perf_counter()

        logger.info(
            f"[{request_id}] → {request.method} {request.url.path}"
            + (f"?{request.url.query}" if request.url.query else "")
        )

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"[{request_id}] ← {response.status_code} "
            f"({duration_ms:.1f}ms)"
        )

        # Attach request ID to response headers for client-side tracing
        response.headers["X-Request-ID"] = request_id
        return response


# ---------------------------------------------------------------------------
# Security Headers Middleware
# Adds HTTP security headers to every response.
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/ws/"):
            return await call_next(request)

        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        return response


# ---------------------------------------------------------------------------
# setup_middleware — call this once from main.py
# ---------------------------------------------------------------------------

def setup_middleware(app: FastAPI) -> None:
    """Register all middleware on the FastAPI app instance."""

    # Custom middlewares
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # CORS — must be added last so it runs outermost (first on every request)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,   # required for Authorization: Bearer header
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
