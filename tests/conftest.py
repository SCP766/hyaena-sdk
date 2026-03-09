from __future__ import annotations

import pytest

from hyaena._client import HyaenaClient
from hyaena._scope import Scope


@pytest.fixture
def scope() -> Scope:
    return Scope()


@pytest.fixture
def mock_client() -> HyaenaClient:
    """
    Returns a HyaenaClient with transport send stubbed to a no-op.
    Prevents any real HTTP calls during tests.
    """
    client = HyaenaClient(
        dsn="http://localhost:9999",
        service="test-service",
        environment="test",
        release="0.0.1",
    )
    client.stub_transport_send(None)
    return client
