"""Unit tests for Todoist Sync person matcher.

Loads ``person_matcher.py`` from the apps directory using importlib. All
graph and command interactions are mocked — no network calls or SPARQL
endpoints are needed.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load person_matcher module from apps directory
# ---------------------------------------------------------------------------

_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "todoist-sync"
    / "services"
    / "person_matcher.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("todoist_person_matcher", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["todoist_person_matcher"] = mod
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
                {"person": {"type": "uri", "value": person_iri}}
            ]
        }
    }


def _empty_result() -> dict:
    return {"results": {"bindings": []}}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPersonMatcherMatch:
    """Tests for PersonMatcher.match()."""

    @pytest.mark.asyncio
    async def test_none_input_returns_none(self):
        matcher = pm.PersonMatcher(MockGraphClient(), MockCommandClient())
        assert await matcher.match(None) is None

    @pytest.mark.asyncio
    async def test_empty_dict_returns_none(self):
        matcher = pm.PersonMatcher(MockGraphClient(), MockCommandClient())
        assert await matcher.match({}) is None

    @pytest.mark.asyncio
    async def test_no_name_no_email_returns_none(self):
        matcher = pm.PersonMatcher(MockGraphClient(), MockCommandClient())
        assert await matcher.match({"name": "", "email": None}) is None

    @pytest.mark.asyncio
    async def test_email_match_returns_existing_iri(self):
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:sempkm:person:alice"))
        matcher = pm.PersonMatcher(graph, MockCommandClient())

        result = await matcher.match({"name": "Alice", "email": "alice@example.com"})
        assert result == "urn:sempkm:person:alice"
        assert len(graph.queries) == 1
        assert "alice@example.com" in graph.queries[0]

    @pytest.mark.asyncio
    async def test_name_fallback_when_no_email_match(self):
        graph = MockGraphClient()
        # Email lookup returns nothing
        graph.add_result(_empty_result())
        # Name/externalId lookup returns match
        graph.add_result(_sparql_result("urn:sempkm:person:bob"))
        matcher = pm.PersonMatcher(graph, MockCommandClient())

        result = await matcher.match({"name": "Bob", "email": "bob@example.com"})
        assert result == "urn:sempkm:person:bob"
        assert len(graph.queries) == 2

    @pytest.mark.asyncio
    async def test_name_only_lookup(self):
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:sempkm:person:carol"))
        matcher = pm.PersonMatcher(graph, MockCommandClient())

        result = await matcher.match({"name": "Carol", "email": None})
        assert result == "urn:sempkm:person:carol"
        # Should skip email lookup, go straight to externalId
        assert len(graph.queries) == 1
        assert "externalId" in graph.queries[0]

    @pytest.mark.asyncio
    async def test_creates_person_when_no_match(self):
        graph = MockGraphClient()
        # No email match, no name match
        graph.add_result(_empty_result())
        graph.add_result(_empty_result())
        cmd = MockCommandClient(iri="urn:sempkm:person:new-dan")
        matcher = pm.PersonMatcher(graph, cmd)

        result = await matcher.match({"name": "Dan Smith", "email": "dan@example.com"})
        assert result == "urn:sempkm:person:new-dan"
        assert len(cmd.commands) == 1
        cmd_type, params = cmd.commands[0]
        assert cmd_type == "object.create"
        assert params["type"] == "urn:sempkm:model:basic-pkm:Person"
        assert params["properties"]["dcterms:title"] == "Dan Smith"
        assert params["properties"]["foaf:mbox"] == "dan@example.com"

    @pytest.mark.asyncio
    async def test_creates_person_name_only(self):
        graph = MockGraphClient()
        graph.add_result(_empty_result())  # externalId lookup
        cmd = MockCommandClient(iri="urn:sempkm:person:eve")
        matcher = pm.PersonMatcher(graph, cmd)

        result = await matcher.match({"name": "Eve", "email": None})
        assert result == "urn:sempkm:person:eve"
        assert len(cmd.commands) == 1
        _, params = cmd.commands[0]
        assert "foaf:mbox" not in params["properties"]
        assert params["properties"]["dcterms:title"] == "Eve"

    @pytest.mark.asyncio
    async def test_creates_person_email_only(self):
        graph = MockGraphClient()
        graph.add_result(_empty_result())  # email lookup
        cmd = MockCommandClient(iri="urn:sempkm:person:frank")
        matcher = pm.PersonMatcher(graph, cmd)

        result = await matcher.match({"name": "", "email": "frank@example.com"})
        assert result == "urn:sempkm:person:frank"
        assert len(cmd.commands) == 1
        _, params = cmd.commands[0]
        assert params["properties"]["dcterms:title"] == "frank"
        assert params["slug"] == "frank"

    @pytest.mark.asyncio
    async def test_cache_hit_on_second_call(self):
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:sempkm:person:alice"))
        matcher = pm.PersonMatcher(graph, MockCommandClient())

        await matcher.match({"name": "Alice", "email": "alice@example.com"})
        result = await matcher.match({"name": "Alice", "email": "alice@example.com"})
        assert result == "urn:sempkm:person:alice"
        # Only one query — second call was cached
        assert len(graph.queries) == 1

    @pytest.mark.asyncio
    async def test_cache_key_uses_email_when_available(self):
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:sempkm:person:alice"))
        matcher = pm.PersonMatcher(graph, MockCommandClient())

        await matcher.match({"name": "Alice", "email": "alice@example.com"})
        # Same email, different name — should still cache hit
        result = await matcher.match({"name": "Alice B", "email": "alice@example.com"})
        assert result == "urn:sempkm:person:alice"
        assert len(graph.queries) == 1

    @pytest.mark.asyncio
    async def test_cache_key_uses_name_without_email(self):
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:sempkm:person:bob"))
        matcher = pm.PersonMatcher(graph, MockCommandClient())

        await matcher.match({"name": "Bob", "email": None})
        result = await matcher.match({"name": "Bob", "email": None})
        assert result == "urn:sempkm:person:bob"
        assert len(graph.queries) == 1

    @pytest.mark.asyncio
    async def test_different_people_not_cached_together(self):
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:sempkm:person:alice"))
        graph.add_result(_sparql_result("urn:sempkm:person:bob"))
        matcher = pm.PersonMatcher(graph, MockCommandClient())

        r1 = await matcher.match({"name": "Alice", "email": "alice@example.com"})
        r2 = await matcher.match({"name": "Bob", "email": "bob@example.com"})
        assert r1 == "urn:sempkm:person:alice"
        assert r2 == "urn:sempkm:person:bob"
        assert len(graph.queries) == 2


class TestSlugify:
    """Tests for the _slugify helper."""

    def test_basic(self):
        assert pm._slugify("Alice Smith") == "alice-smith"

    def test_special_characters(self):
        assert pm._slugify("O'Brien Jr.") == "obrien-jr"

    def test_multiple_spaces(self):
        assert pm._slugify("  John   Doe  ") == "john-doe"

    def test_already_lowercase(self):
        assert pm._slugify("alice") == "alice"

    def test_empty_string(self):
        assert pm._slugify("") == ""
