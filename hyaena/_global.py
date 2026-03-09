from __future__ import annotations

import logging

from hyaena._client import HyaenaClient
from hyaena._scope import ScopeContext, get_current_scope
from hyaena.exc.errors import HyaenaNotInitializedError

logger = logging.getLogger("hyaena")

_client: HyaenaClient | None = None


def init(
    dsn: str,
    service: str,
    environment: str,
    release: str | None = None,
) -> None:
    global _client
    _client = HyaenaClient(
        dsn=dsn,
        service=service,
        environment=environment,
        release=release,
    )
    logger.info(
        "Hyaena initialized — service=%s environment=%s dsn=%s",
        service,
        environment,
        dsn,
    )


async def start() -> None:
    await _require_client().start()


async def stop() -> None:
    await _require_client().stop()


def push_scope() -> ScopeContext:
    return ScopeContext()


def capture_exception(
    exc: BaseException,
    severity: str = "error",
) -> None:

    client = _get_client()
    if client is None:
        return
    scope = get_current_scope()
    client.capture_exception(exc, scope, severity)


def capture_message(
    message: str,
    severity: str = "info",
) -> None:

    client = _get_client()
    if client is None:
        return
    scope = get_current_scope()
    client.capture_message(message, scope, severity)


def _require_client() -> HyaenaClient:
    if _client is None:
        raise HyaenaNotInitializedError(
            "hyaena.init() must be called before using the SDK."
        )
    return _client


def _get_client() -> HyaenaClient | None:

    if _client is None:
        logger.warning(
            "Hyaena capture called before init() — event dropped. "
            "Call hyaena.init() at application startup."
        )
        return None
    return _client
