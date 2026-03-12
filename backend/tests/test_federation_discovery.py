"""Unit tests for FederationService.discover_remote_instance_url().

Validates that the discovery logic correctly filters WebIDs to HTTP(S)
URLs and derives instance base URLs from the WebID path pattern.
"""

import logging
from unittest.mock import AsyncMock

import pytest

from app.federation.service import FederationService


def _make_bindings(*webids: str) -> dict:
    """Build a SPARQL result dict from a list of WebID strings."""
    return {
        "results": {
            "bindings": [
                {"member": {"type": "uri", "value": w}} for w in webids
            ]
        }
    }


@pytest.fixture
def service():
    """Create a FederationService with mocked dependencies."""
    client = AsyncMock()
    event_store = AsyncMock()
    return FederationService(client=client, event_store=event_store)


LOCAL_WEBID = "urn:sempkm:user:local-user-uuid"
GRAPH_IRI = "urn:sempkm:shared:test-graph-id"


# ------------------------------------------------------------------
# Happy path: HTTP(S) WebID member
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_http_webid(service):
    """HTTP WebID member → derives correct instance base URL."""
    service._client.query.return_value = _make_bindings(
        "https://instance-a.example.com/users/alice#me"
    )

    result = await service.discover_remote_instance_url(GRAPH_IRI, LOCAL_WEBID)

    assert result == "https://instance-a.example.com"


@pytest.mark.asyncio
async def test_discover_http_webid_no_users_path(service):
    """HTTP WebID without /users/ path → falls back to rsplit derivation."""
    service._client.query.return_value = _make_bindings(
        "https://other.example.com/profile/bob"
    )

    result = await service.discover_remote_instance_url(GRAPH_IRI, LOCAL_WEBID)

    assert result == "https://other.example.com/profile"


# ------------------------------------------------------------------
# URN-only members (the bug scenario)
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_urn_only_returns_none(service, caplog):
    """Only URN WebID members → returns None and logs warning."""
    service._client.query.return_value = _make_bindings(
        "urn:sempkm:user:remote-uuid-1234"
    )

    with caplog.at_level(logging.WARNING):
        result = await service.discover_remote_instance_url(GRAPH_IRI, LOCAL_WEBID)

    assert result is None
    assert "No remote HTTP(S) members found" in caplog.text


# ------------------------------------------------------------------
# Mixed HTTP and URN members
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_mixed_picks_http(service):
    """Mixed URN + HTTP members → picks the HTTP one."""
    service._client.query.return_value = _make_bindings(
        "urn:sempkm:user:remote-uuid-1234",
        "https://instance-b.example.com/users/carol#me",
    )

    result = await service.discover_remote_instance_url(GRAPH_IRI, LOCAL_WEBID)

    assert result == "https://instance-b.example.com"


# ------------------------------------------------------------------
# No members at all
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_no_members_returns_none(service):
    """No members in SPARQL results → returns None."""
    service._client.query.return_value = {"results": {"bindings": []}}

    result = await service.discover_remote_instance_url(GRAPH_IRI, LOCAL_WEBID)

    assert result is None


# ------------------------------------------------------------------
# URL derivation edge cases
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_url_derivation_strips_users_path(service):
    """WebID https://host:8080/users/alice#me → https://host:8080."""
    service._client.query.return_value = _make_bindings(
        "https://host:8080/users/alice#me"
    )

    result = await service.discover_remote_instance_url(GRAPH_IRI, LOCAL_WEBID)

    assert result == "https://host:8080"


@pytest.mark.asyncio
async def test_url_derivation_http_scheme(service):
    """Plain http:// WebID is also accepted."""
    service._client.query.return_value = _make_bindings(
        "http://local.dev/users/dev-user#me"
    )

    result = await service.discover_remote_instance_url(GRAPH_IRI, LOCAL_WEBID)

    assert result == "http://local.dev"
