from __future__ import annotations

from contextvars import ContextVar, Token
from types import TracebackType
from typing import Any


class Scope:
    """
    Mutable context for a single capture operation.
    Holds tags, user info, and extra data to be merged into an event.

    Isolated per async context via ContextVar — concurrent requests
    cannot bleed scope into each other.
    """

    def __init__(self) -> None:
        self._tags: dict[str, str] = {}
        self._user: dict[str, str] = {}
        self._extras: dict[str, Any] = {}

    def set_tag(self, key: str, value: str) -> None:
        self._tags[key] = value

    def set_user(self, user: dict[str, str]) -> None:
        self._user = user

    def set_extra(self, key: str, value: Any) -> None:
        self._extras[key] = value

    @property
    def tags(self) -> dict[str, str]:
        return dict(self._tags)

    @property
    def user(self) -> dict[str, str]:
        return dict(self._user)

    @property
    def extras(self) -> dict[str, Any]:
        return dict(self._extras)

    def merge(self, other: Scope) -> Scope:
        """
        Returns a new Scope with other layered on top of self.
        Used to merge a push_scope() onto the ambient scope.
        """
        merged = Scope()
        merged._tags = {**self._tags, **other._tags}
        merged._user = {**self._user, **other._user}
        merged._extras = {**self._extras, **other._extras}
        return merged

    def clone(self) -> Scope:
        cloned = Scope()
        cloned._tags = dict(self._tags)
        cloned._user = dict(self._user)
        cloned._extras = dict(self._extras)
        return cloned


_current_scope: ContextVar[Scope] = ContextVar("hyaena_scope", default=Scope())


class ScopeContext:
    """
    Context manager returned by push_scope().
    Creates a child scope isolated to the current async context.
    Restores the previous scope on exit.
    """

    def __init__(self) -> None:
        self._scope: Scope = _current_scope.get().clone()
        self._token: Token[Scope] | None = None

    def __enter__(self) -> Scope:
        self._token = _current_scope.set(self._scope)
        return self._scope

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._token is not None:
            _current_scope.reset(self._token)


def get_current_scope() -> Scope:
    return _current_scope.get()
