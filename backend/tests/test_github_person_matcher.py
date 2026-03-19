"""Unit tests for GitHub Sync person matcher.

Loads ``person_matcher.py`` from the apps directory using importlib. All
graph and command interactions are mocked — no network calls or SPARQL
endpoints are needed.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Load person_matcher module from apps directory
# ---------------------------------------------------------------------------

_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "github-sync"
    / "services"
    / "person_matcher.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("github_person_matcher", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["github_person_matcher"] = mod
    spec.loader.exec_module(mod)
    return mod


pm = _load_module()


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class MockGraphClient:
    """In-memory graph client that returns canned SPARQL results."""

    def __init__(self):
        self.queries: list[str] = []
        self._results: list[dict] = []

    def add_result(self, result: dict):
        """Queue a SPARQL result to return on next query() call."""
        self._results.append(result)

    async def query(self, sparql: str) -> dict:
        self.queries.append(sparql)
        if self._results:
            return self._results.pop(0)
        return {"results": {"bindings": []}}


class MockCommandClient:
    """In-memory command client that records executed commands."""

    def __init__(self, iri: str = "urn:sempkm:person:new-person"):
        self._iri = iri
        self.commands: list[tuple[str, dict]] = []

    async def execute(self, cmd_type: str, params: dict) -> dict:
        self.commands.append((cmd_type, params))
        return {"iri": self._iri}


def _sparql_result(person_iri: str) -> dict:
    """Build a SPARQL JSON result with a single person binding."""
    return {
        "results": {
            "bindings": [
                {"person": {"value": person_iri}}
            ]
        }
    }


def _empty_result() -> dict:
    return {"results": {"bindings": []}}


# ===================================================================
# PersonMatcher.match tests
# ===================================================================

class TestPersonMatcherMatch:
    @pytest.mark.asyncio
    async def test_match_by_email_found(self):
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:alice"))
        commands = MockCommandClient()
        matcher = pm.PersonMatcher(graph, commands)

        result = await matcher.match({"login": "alice", "email": "alice@example.com"})
        assert result == "urn:person:alice"
        assert len(commands.commands) == 0  # No creation needed

    @pytest.mark.asyncio
    async def test_match_by_login_found(self):
        graph = MockGraphClient()
        graph.add_result(_empty_result())  # email lookup miss
        graph.add_result(_sparql_result("urn:person:bob"))  # login lookup hit
        commands = MockCommandClient()
        matcher = pm.PersonMatcher(graph, commands)

        result = await matcher.match({"login": "bob", "email": "bob@example.com"})
        assert result == "urn:person:bob"
        assert len(commands.commands) == 0

    @pytest.mark.asyncio
    async def test_match_miss_creates_person(self):
        graph = MockGraphClient()
        graph.add_result(_empty_result())  # email miss
        graph.add_result(_empty_result())  # login miss
        commands = MockCommandClient(iri="urn:person:new-charlie")
        matcher = pm.PersonMatcher(graph, commands)

        result = await matcher.match({"login": "charlie", "email": "charlie@example.com"})
        assert result == "urn:person:new-charlie"
        assert len(commands.commands) == 1
        cmd_type, params = commands.commands[0]
        assert cmd_type == "object.create"
        assert params["slug"] == "charlie"
        assert params["properties"]["dcterms:title"] == "charlie"
        assert params["properties"]["foaf:mbox"] == "charlie@example.com"

    @pytest.mark.asyncio
    async def test_cache_hit_skips_sparql(self):
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:alice"))
        commands = MockCommandClient()
        matcher = pm.PersonMatcher(graph, commands)

        # First call
        await matcher.match({"login": "alice", "email": "alice@example.com"})
        # Second call — should use cache
        result = await matcher.match({"login": "alice", "email": "alice@example.com"})
        assert result == "urn:person:alice"
        # Only one SPARQL query (from first call)
        assert len(graph.queries) == 1

    @pytest.mark.asyncio
    async def test_email_preferred_over_login(self):
        """When email is available, lookup by email first."""
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:email-match"))
        commands = MockCommandClient()
        matcher = pm.PersonMatcher(graph, commands)

        result = await matcher.match({"login": "someuser", "email": "user@example.com"})
        assert result == "urn:person:email-match"
        # Only one query (email lookup), never got to login lookup
        assert len(graph.queries) == 1
        assert "foaf:mbox" in graph.queries[0] or "crm:email" in graph.queries[0]

    @pytest.mark.asyncio
    async def test_null_email_falls_back_to_login(self):
        """When email is None, skip email lookup, try login."""
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:login-match"))
        commands = MockCommandClient()
        matcher = pm.PersonMatcher(graph, commands)

        result = await matcher.match({"login": "ghuser", "email": None})
        assert result == "urn:person:login-match"
        # Only one query (login lookup — email was skipped)
        assert len(graph.queries) == 1
        assert "externalId" in graph.queries[0]

    @pytest.mark.asyncio
    async def test_none_assignee_returns_none(self):
        graph = MockGraphClient()
        commands = MockCommandClient()
        matcher = pm.PersonMatcher(graph, commands)

        result = await matcher.match(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_assignee_returns_none(self):
        graph = MockGraphClient()
        commands = MockCommandClient()
        matcher = pm.PersonMatcher(graph, commands)

        result = await matcher.match({"login": "", "email": None})
        assert result is None

    @pytest.mark.asyncio
    async def test_created_person_has_correct_properties(self):
        graph = MockGraphClient()
        graph.add_result(_empty_result())  # login miss (no email)
        commands = MockCommandClient(iri="urn:person:new")
        matcher = pm.PersonMatcher(graph, commands)

        await matcher.match({"login": "devuser", "email": None})
        cmd_type, params = commands.commands[0]
        assert cmd_type == "object.create"
        assert params["type"] == pm._BPKM_PERSON_TYPE
        assert params["slug"] == "devuser"
        assert params["properties"]["dcterms:title"] == "devuser"
        assert pm._BPKM_EXTERNAL_ID in params["properties"]
        assert params["properties"][pm._BPKM_EXTERNAL_ID] == "devuser"
        # No email property when email is None
        assert "foaf:mbox" not in params["properties"]

    @pytest.mark.asyncio
    async def test_created_person_with_email(self):
        graph = MockGraphClient()
        graph.add_result(_empty_result())  # email miss
        graph.add_result(_empty_result())  # login miss
        commands = MockCommandClient(iri="urn:person:new-with-email")
        matcher = pm.PersonMatcher(graph, commands)

        await matcher.match({"login": "devuser", "email": "dev@co.com"})
        _, params = commands.commands[0]
        assert params["properties"]["foaf:mbox"] == "dev@co.com"
        assert params["properties"][pm._BPKM_EXTERNAL_ID] == "devuser"
