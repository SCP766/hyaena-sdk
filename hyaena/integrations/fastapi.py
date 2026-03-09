from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

import hyaena
from hyaena._scope import ScopeContext

logger = logging.getLogger("hyaena.middleware")


class HyaenaMiddleware(BaseHTTPMiddleware):
    """
    FastAPI/Starlette middleware that automatically captures unhandled
    exceptions with request context pre-populated on the scope.

    Installs in one line:
        app.add_middleware(HyaenaMiddleware)

    What it captures automatically:
        - endpoint path
        - HTTP method
        - client IP
        - request body (best-effort, JSON only)
        - query params
        - response status (if exception is unhandled)

    Unhandled exceptions are re-raised after capture so FastAPI's own
    exception handlers continue to run normally.

    For exceptions you want to capture manually (e.g. handled errors),
    use push_scope() + capture_exception() directly at the call site.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        with ScopeContext() as scope:
            # Populate scope with request context before any processing
            scope.set_tag("endpoint", request.url.path)
            scope.set_tag("method", request.method)

            if request.client:
                scope.set_user({"ip": request.client.host})

            try:
                body = await request.json()
            except Exception:
                body = None

            scope.set_extra("request_body", body)
            scope.set_extra("query_params", dict(request.query_params))
            scope.set_extra(
                "headers",
                self.safe_headers(dict(request.headers)),
            )

            try:
                response = await call_next(request)
                return response
            except Exception as exc:
                hyaena.capture_exception(exc, severity="error")
                raise  # re-raise so FastAPI exception handlers still run

    @classmethod
    def safe_headers(cls, headers: dict[str, str]) -> dict[str, str]:
        """Strip sensitive headers before attaching to scope."""
        _STRIP: frozenset[str] = frozenset(
            {"authorization", "cookie", "x-api-key", "x-auth-token"}
        )
        return {k: v for k, v in headers.items() if k.lower() not in _STRIP}
