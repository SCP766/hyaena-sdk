from __future__ import annotations

import pytest

from hyaena._event import EventBuilder
from hyaena._scope import Scope


@pytest.fixture
def builder() -> EventBuilder:
    return EventBuilder(
        service="bifrost-api",
        environment="test",
        release="1.0.0",
    )


class TestEventBuilder:
    def test_build_from_exception_sets_type(self, builder: EventBuilder) -> None:
        scope = Scope()
        exc = ValueError("something went wrong")

        payload = builder.build_from_exception(exc, scope)

        assert payload.exception_type == "ValueError"

    def test_build_from_exception_sets_message(self, builder: EventBuilder) -> None:
        scope = Scope()
        exc = ValueError("something went wrong")

        payload = builder.build_from_exception(exc, scope)

        assert payload.message == "something went wrong"

    def test_build_from_exception_captures_traceback(
        self, builder: EventBuilder
    ) -> None:
        scope = Scope()
        try:
            raise RuntimeError("boom")
        except RuntimeError as exc:
            payload = builder.build_from_exception(exc, scope)

        assert "RuntimeError" in payload.traceback

    def test_build_from_exception_merges_scope_tags(
        self, builder: EventBuilder
    ) -> None:
        scope = Scope()
        scope.set_tag("endpoint", "/users")

        exc = ValueError("x")
        payload = builder.build_from_exception(exc, scope)

        assert payload.tags == {"endpoint": "/users"}

    def test_build_from_exception_merges_scope_user(
        self, builder: EventBuilder
    ) -> None:
        scope = Scope()
        scope.set_user({"id": "42"})

        exc = ValueError("x")
        payload = builder.build_from_exception(exc, scope)

        assert payload.user == {"id": "42"}

    def test_build_from_exception_sets_service_and_env(
        self, builder: EventBuilder
    ) -> None:
        scope = Scope()
        exc = ValueError("x")

        payload = builder.build_from_exception(exc, scope)

        assert payload.service == "bifrost-api"
        assert payload.environment == "test"
        assert payload.release == "1.0.0"

    def test_build_from_exception_default_severity(self, builder: EventBuilder) -> None:
        scope = Scope()
        exc = ValueError("x")

        payload = builder.build_from_exception(exc, scope)

        assert payload.severity == "error"

    def test_build_from_exception_custom_severity(self, builder: EventBuilder) -> None:
        scope = Scope()
        exc = ValueError("x")

        payload = builder.build_from_exception(exc, scope, severity="critical")

        assert payload.severity == "critical"

    def test_build_from_message(self, builder: EventBuilder) -> None:
        scope = Scope()

        payload = builder.build_from_message("hello", scope)

        assert payload.message == "hello"
        assert payload.exception_type == "Message"
        assert payload.traceback == ""
        assert payload.severity == "info"

    def test_to_dict_is_serialisable(self, builder: EventBuilder) -> None:
        import json

        scope = Scope()
        exc = ValueError("x")
        payload = builder.build_from_exception(exc, scope)

        # must not raise
        serialised = json.dumps(payload.to_dict())
        assert "event_id" in serialised

    def test_exception_with_no_message_falls_back_to_type(
        self, builder: EventBuilder
    ) -> None:
        scope = Scope()
        exc = ValueError()

        payload = builder.build_from_exception(exc, scope)

        assert payload.message == "ValueError"
