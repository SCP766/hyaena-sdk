from __future__ import annotations

import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from hyaena._scope import Scope


@dataclass
class IngestPayload:
    """
    The wire format sent to the Hyaena ingest endpoint.
    Intentionally flat — no nested objects beyond dicts.
    """

    event_id: UUID
    service: str
    environment: str
    release: str | None
    exception_type: str
    message: str
    traceback: str
    severity: str
    timestamp: str  # ISO 8601
    tags: dict[str, str]
    user: dict[str, str]
    extra: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "service": self.service,
            "environment": self.environment,
            "release": self.release,
            "exception_type": self.exception_type,
            "message": self.message,
            "traceback": self.traceback,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "user": self.user,
            "extra": self.extra,
        }


class EventBuilder:
    """
    Constructs an IngestPayload from a live exception and the current Scope.
    Never raises — all extraction is best-effort.
    """

    def __init__(
        self,
        service: str,
        environment: str,
        release: str | None,
    ) -> None:
        self._service = service
        self._environment = environment
        self._release = release

    def build_from_exception(
        self,
        exc: BaseException,
        scope: Scope,
        severity: str = "error",
    ) -> IngestPayload:
        return IngestPayload(
            event_id=uuid4(),
            service=self._service,
            environment=self._environment,
            release=self._release,
            exception_type=self._extract_type(exc),
            message=self._extract_message(exc),
            traceback=self._extract_traceback(exc),
            severity=severity,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tags=scope.tags,
            user=scope.user,
            extra=scope.extras,
        )

    def build_from_message(
        self,
        message: str,
        scope: Scope,
        severity: str = "info",
    ) -> IngestPayload:
        return IngestPayload(
            event_id=uuid4(),
            service=self._service,
            environment=self._environment,
            release=self._release,
            exception_type="Message",
            message=message,
            traceback="",
            severity=severity,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tags=scope.tags,
            user=scope.user,
            extra=scope.extras,
        )

    def _extract_type(self, exc: BaseException) -> str:
        return type(exc).__qualname__

    def _extract_message(self, exc: BaseException) -> str:
        return str(exc) or type(exc).__qualname__

    def _extract_traceback(self, exc: BaseException) -> str:
        try:
            return "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )
        except Exception:
            return "traceback unavailable"
