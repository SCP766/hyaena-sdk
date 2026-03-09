from __future__ import annotations

from typing import Any
from unittest.mock import patch

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from hyaena.integrations.fastapi import HyaenaMiddleware


def _make_app(raise_exc: Exception | None = None) -> Starlette:
    async def homepage(request: Request) -> JSONResponse:
        if raise_exc is not None:
            raise raise_exc
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(HyaenaMiddleware)
    return app


class TestHyaenaMiddleware:
    def test_passes_through_successful_request(self) -> None:
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/")

        assert response.status_code == 200

    def test_captures_unhandled_exception(self) -> None:
        app = _make_app(raise_exc=ValueError("boom"))
        captured: list[BaseException] = []

        def _side_effect(exc: BaseException, **kwargs: Any) -> None:
            captured.append(exc)

        with patch(
            "hyaena.integrations.fastapi.hyaena.capture_exception",
            side_effect=_side_effect,
        ) as mock_capture:
            client = TestClient(app, raise_server_exceptions=False)
            client.get("/")

        assert mock_capture.called
        assert isinstance(captured[0], ValueError)

    def test_reraises_after_capture(self) -> None:
        """FastAPI exception handlers must still run after capture."""
        app = _make_app(raise_exc=RuntimeError("reraised"))

        with patch("hyaena.integrations.fastapi.hyaena.capture_exception"):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/")

        # Starlette returns 500 when exception propagates
        assert response.status_code == 500

    def test_strips_authorization_header(self) -> None:
        headers = {
            "authorization": "Bearer secret",
            "content-type": "application/json",
            "x-api-key": "key123",
        }
        safe = HyaenaMiddleware.safe_headers(headers)

        assert "authorization" not in safe
        assert "x-api-key" not in safe
        assert safe["content-type"] == "application/json"

    def test_strips_cookie_header(self) -> None:
        headers = {"cookie": "session=abc", "accept": "application/json"}
        safe = HyaenaMiddleware.safe_headers(headers)

        assert "cookie" not in safe
        assert "accept" in safe
