from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger("hyaena.transport")

MAX_RETRIES = 3
_BASE_BACKOFF = 0.5  # seconds
_BACKOFF_MULTIPLIER = 2.0
_REQUEST_TIMEOUT = 5.0  # seconds per attempt


class AsyncTransport:
    """
    Fire-and-forget HTTP transport.

    - Never raises into the caller.
    - Retries up to MAX_RETRIES times with exponential backoff.
    - Drops the event silently after exhausting retries — SDK must
      never crash or block the host application.
    """

    def __init__(self, dsn: str) -> None:
        self._ingest_url = dsn.rstrip("/") + "/v1/"
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(timeout=_REQUEST_TIMEOUT)
        logger.debug("HyaenaTransport started — target: %s", self._ingest_url)

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.debug("HyaenaTransport stopped")

    def send(self, payload: dict[str, Any]) -> None:
        """
        Schedule a fire-and-forget send on the running event loop.
        Returns immediately — caller is never blocked.
        """
        asyncio.create_task(self._send_with_retry(payload))

    async def send_and_wait(self, payload: dict[str, Any]) -> None:
        """
        Await the send directly. Intended for use in tests only —
        avoids fire-and-forget so assertions can be made synchronously.
        """
        await self._send_with_retry(payload)

    def set_client(self, client: httpx.AsyncClient) -> None:
        """
        Inject an httpx client. Intended for use in tests only —
        avoids accessing the private _client attribute directly.
        """
        self._client = client

    async def _send_with_retry(self, payload: dict[str, Any]) -> None:
        if self._client is None:
            logger.warning("HyaenaTransport not started — dropping event")
            return

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await self._client.post(
                    self._ingest_url,
                    json=payload,
                )
                if response.status_code < 500:
                    # 2xx success or 4xx client error (bad payload) — do not retry
                    if response.status_code >= 400:
                        logger.warning(
                            "Hyaena ingest rejected payload [%s]: %s",
                            response.status_code,
                            response.text[:200],
                        )
                    return

                # 5xx — server error, retry
                logger.warning(
                    "Hyaena ingest server error [%s] attempt %d/%d",
                    response.status_code,
                    attempt,
                    MAX_RETRIES,
                )

            except httpx.TransportError as exc:
                logger.warning(
                    "Hyaena ingest transport error attempt %d/%d: %s",
                    attempt,
                    MAX_RETRIES,
                    exc,
                )
            except Exception as exc:
                logger.warning(
                    "Hyaena ingest unexpected error attempt %d/%d: %s",
                    attempt,
                    MAX_RETRIES,
                    exc,
                )

            if attempt < MAX_RETRIES:
                backoff = _BASE_BACKOFF * (_BACKOFF_MULTIPLIER ** (attempt - 1))
                await asyncio.sleep(backoff)

        logger.warning(
            "Hyaena dropping event after %d failed attempts — event_id: %s",
            MAX_RETRIES,
            payload.get("event_id", "unknown"),
        )
