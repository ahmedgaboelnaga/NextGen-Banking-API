"""
Middleware for handling internationalization in FastAPI.
"""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.core.i18n import set_language, parse_accept_language
from backend.app.core.logging import get_logger

logger = get_logger()


class LanguageMiddleware(BaseHTTPMiddleware):
    """
    Middleware to detect and set the language for each request.

    Language detection priority:
    1. 'X-Language' or 'X-Locale' custom header (explicit override)
    2. User's saved language preference from database (if authenticated)
    3. 'Accept-Language' standard header
    4. Default language from settings
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip language processing for health check endpoint to reduce logging overhead
        if request.url.path == "/health":
            return await call_next(request)

        language = None

        # Priority 1: Check for custom language header (explicit override - highest priority)
        language = request.headers.get("X-Language") or request.headers.get("X-Locale")

        # Priority 2: Check authenticated user's preference (if available)
        # Note: request.state.user will be set by your auth middleware/dependency
        if not language and hasattr(request.state, "user") and request.state.user:
            language = getattr(request.state.user, "preferred_language", None)

        # Priority 3: Check Accept-Language header
        if not language:
            accept_language = request.headers.get("Accept-Language")
            language = parse_accept_language(accept_language)

        # Set the language for this request context
        set_language(language)

        # Add language info to request state for potential use in route handlers
        request.state.language = language

        response = await call_next(request)

        # Add Content-Language header to response
        response.headers["Content-Language"] = language

        return response
