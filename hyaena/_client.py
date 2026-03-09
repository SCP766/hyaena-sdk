from __future__ import annotations

import logging

from hyaena._event import EventBuilder
from hyaena._scope import Scope
from hyaena._transport import AsyncTransport

logger = logging.getLogger("hyaena.client")


class HyaenaClient:
    def __init__(
        self,
        dsn: str,
        service: str,
        environment: str,
        release: str | None = None,
    ) -> None:
        self._transport = AsyncTransport(dsn=dsn)
        self._builder = EventBuilder(
            service=service,
            environment=environment,
            release=release,
        )

    async def start(self) -> None:
        await self._transport.start()

    async def stop(self) -> None:
        await self._transport.stop()

    def capture_exception(
        self,
        exc: BaseException,
        scope: Scope,
        severity: str = "error",
    ) -> None:
        try:
            payload = self._builder.build_from_exception(exc, scope, severity)
            self._transport.send(payload.to_dict())
        except Exception as build_exc:
            logger.warning("Hyaena failed to build event: %s", build_exc)

    def capture_message(
        self,
        message: str,
        scope: Scope,
        severity: str = "info",
    ) -> None:
        """
        Build and fire-and-forget a message event.
        Never raises.
        """
        try:
            payload = self._builder.build_from_message(message, scope, severity)
            self._transport.send(payload.to_dict())
        except Exception as build_exc:
            logger.warning("Hyaena failed to build message event: %s", build_exc)

    def stub_transport_send(self, replacement: None) -> None:
        """
        Replace the transport send with a no-op. Intended for use in tests only.
        Accepts None to patch send to a callable that discards all payloads.
        """
        from typing import Any

        def _noop(payload: dict[str, Any]) -> None:
            pass

        self._transport.send = _noop  # type: ignore[method-assign]
