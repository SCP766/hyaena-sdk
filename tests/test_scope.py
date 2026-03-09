from __future__ import annotations

import asyncio

from hyaena._scope import Scope, ScopeContext, get_current_scope


class TestScope:
    def test_set_tag(self) -> None:
        scope = Scope()
        scope.set_tag("env", "production")
        assert scope.tags == {"env": "production"}

    def test_set_user(self) -> None:
        scope = Scope()
        scope.set_user({"id": "123", "ip": "1.2.3.4"})
        assert scope.user == {"id": "123", "ip": "1.2.3.4"}

    def test_set_extra(self) -> None:
        scope = Scope()
        scope.set_extra("body", {"key": "value"})
        assert scope.extras == {"body": {"key": "value"}}

    def test_tags_returns_copy(self) -> None:
        scope = Scope()
        scope.set_tag("k", "v")
        tags = scope.tags
        tags["mutated"] = "yes"
        assert "mutated" not in scope.tags

    def test_merge_other_takes_precedence(self) -> None:
        base = Scope()
        base.set_tag("env", "production")
        base.set_tag("service", "bifrost")

        override = Scope()
        override.set_tag("env", "staging")

        merged = base.merge(override)
        assert merged.tags["env"] == "staging"
        assert merged.tags["service"] == "bifrost"

    def test_merge_does_not_mutate_either_scope(self) -> None:
        base = Scope()
        base.set_tag("env", "production")

        override = Scope()
        override.set_tag("env", "staging")

        base.merge(override)

        assert base.tags["env"] == "production"
        assert override.tags["env"] == "staging"

    def test_clone_is_independent(self) -> None:
        original = Scope()
        original.set_tag("k", "v")

        cloned = original.clone()
        cloned.set_tag("k", "mutated")

        assert original.tags["k"] == "v"


class TestScopeContext:
    def test_push_scope_restores_on_exit(self) -> None:
        outer = get_current_scope()
        outer.set_tag("outer", "yes")

        with ScopeContext() as inner:
            inner.set_tag("inner", "yes")
            assert get_current_scope().tags.get("inner") == "yes"

        assert "inner" not in get_current_scope().tags

    def test_push_scope_inherits_parent_tags(self) -> None:
        with ScopeContext() as parent:
            parent.set_tag("parent_tag", "inherited")

            with ScopeContext() as child:
                assert child.tags.get("parent_tag") == "inherited"

    def test_concurrent_scopes_do_not_bleed(self) -> None:
        results: dict[str, str] = {}

        async def task_a() -> None:
            with ScopeContext() as scope:
                scope.set_tag("task", "a")
                await asyncio.sleep(0.01)
                results["a"] = get_current_scope().tags.get("task", "missing")

        async def task_b() -> None:
            with ScopeContext() as scope:
                scope.set_tag("task", "b")
                await asyncio.sleep(0.01)
                results["b"] = get_current_scope().tags.get("task", "missing")

        async def run() -> None:
            await asyncio.gather(task_a(), task_b())

        asyncio.run(run())

        assert results["a"] == "a"
        assert results["b"] == "b"
