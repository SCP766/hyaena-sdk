from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hyaena._transport import AsyncTransport, MAX_RETRIES


class TestAsyncTransport:
    def test_send_schedules_task(self) -> None:
        """send() must not block — it creates an asyncio task."""
        transport = AsyncTransport(dsn="http://localhost:9999")
        tasks_created: list[str] = []

        async def run() -> None:
            await transport.start()

            original = asyncio.create_task

            def tracking_create_task(
                coro: object, **kwargs: object
            ) -> asyncio.Task[object]:
                task: asyncio.Task[object] = original(coro, **kwargs)  # type: ignore[arg-type]
                tasks_created.append("created")
                return task

            with patch(
                "hyaena._transport.asyncio.create_task",
                side_effect=tracking_create_task,
            ):
                transport.send({"event_id": "abc"})

            await transport.stop()

        asyncio.run(run())
        assert len(tasks_created) == 1

    def test_send_before_start_logs_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        transport = AsyncTransport(dsn="http://localhost:9999")

        import logging

        with caplog.at_level(logging.WARNING, logger="hyaena.transport"):
            asyncio.run(transport.send_and_wait({"event_id": "abc"}))

        assert "not started" in caplog.text

    def test_retries_on_5xx(self) -> None:
        transport = AsyncTransport(dsn="http://localhost:9999")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "internal server error"

        mock_client: AsyncMock = AsyncMock()
        mock_client.post.return_value = mock_response
        transport.set_client(mock_client)

        async def run() -> None:
            with patch("hyaena._transport.asyncio.sleep", new_callable=AsyncMock):
                await transport.send_and_wait({"event_id": "abc"})

        asyncio.run(run())
        assert mock_client.post.call_count == MAX_RETRIES

    def test_no_retry_on_4xx(self) -> None:
        transport = AsyncTransport(dsn="http://localhost:9999")

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "bad request"

        mock_client: AsyncMock = AsyncMock()
        mock_client.post.return_value = mock_response
        transport.set_client(mock_client)

        asyncio.run(transport.send_and_wait({"event_id": "abc"}))
        assert mock_client.post.call_count == 1

    def test_no_retry_on_2xx(self) -> None:
        transport = AsyncTransport(dsn="http://localhost:9999")

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client: AsyncMock = AsyncMock()
        mock_client.post.return_value = mock_response
        transport.set_client(mock_client)

        asyncio.run(transport.send_and_wait({"event_id": "abc"}))
        assert mock_client.post.call_count == 1

    def test_transport_error_retries(self) -> None:
        import httpx

        transport = AsyncTransport(dsn="http://localhost:9999")

        mock_client: AsyncMock = AsyncMock()
        mock_client.post.side_effect = httpx.TransportError("connection refused")
        transport.set_client(mock_client)

        async def run() -> None:
            with patch("hyaena._transport.asyncio.sleep", new_callable=AsyncMock):
                await transport.send_and_wait({"event_id": "abc"})

        asyncio.run(run())
        assert mock_client.post.call_count == MAX_RETRIES

    def test_drops_event_after_max_retries(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        import httpx
        import logging

        transport = AsyncTransport(dsn="http://localhost:9999")

        mock_client: AsyncMock = AsyncMock()
        mock_client.post.side_effect = httpx.TransportError("gone")
        transport.set_client(mock_client)

        async def run() -> None:
            with patch("hyaena._transport.asyncio.sleep", new_callable=AsyncMock):
                with caplog.at_level(logging.WARNING, logger="hyaena.transport"):
                    await transport.send_and_wait({"event_id": "test-drop"})

        asyncio.run(run())
        assert "dropping event" in caplog.text.lower()
