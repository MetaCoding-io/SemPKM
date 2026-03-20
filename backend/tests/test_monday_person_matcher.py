"""Unit tests for Monday.com Sync person matcher.

Loads ``person_matcher.py`` from the apps directory using importlib.  All
graph, command, and Monday.com client interactions are mocked — no network
calls or SPARQL endpoints are needed.

Uses ``asyncio.run()`` to execute async tests without requiring pytest-asyncio.
"""

from __future__ import annotations

import asyncio
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
    / "monday-sync"
    / "services"
    / "person_matcher.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("monday_person_matcher", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["monday_person_matcher"] = mod
    spec.loader.exec_module(mod)
    return mod


pm = _load_module()


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


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


class MockMondayClient:
    """Mock Monday.com client that returns canned user data."""

    def __init__(self):
        self._users: dict[int, dict] = {}
        self.get_users_calls: list[list[int]] = []
        self._error: Exception | None = None

    def add_user(self, user_id: int, user_data: dict):
        """Register a user to return for get_users([user_id])."""
        self._users[user_id] = user_data

    def set_error(self, error: Exception):
        """Make get_users raise this error."""
        self._error = error

    async def get_users(self, user_ids: list[int]) -> list[dict]:
        self.get_users_calls.append(user_ids)
        if self._error:
            raise self._error
        result = []
        for uid in user_ids:
            if uid in self._users:
                result.append(self._users[uid])
        return result


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


def _make_matcher(
    graph: MockGraphClient | None = None,
    commands: MockCommandClient | None = None,
    monday: MockMondayClient | None = None,
) -> tuple[pm.PersonMatcher, MockGraphClient, MockCommandClient, MockMondayClient]:
    """Create a PersonMatcher with mock dependencies."""
    g = graph or MockGraphClient()
    c = commands or MockCommandClient()
    m = monday or MockMondayClient()
    matcher = pm.PersonMatcher(g, c, m)
    return matcher, g, c, m


# ===================================================================
# PersonMatcher.resolve tests
# ===================================================================

class TestPersonMatcherResolve:

    def test_none_user_id_returns_none(self):
        matcher, _, _, _ = _make_matcher()
        result = _run(matcher.resolve(None))
        assert result is None

    def test_email_match_found_via_foaf_mbox(self):
        """When email is provided and SPARQL finds via foaf:mbox, returns it."""
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:alice"))
        matcher, _, commands, _ = _make_matcher(graph=graph)

        result = _run(matcher.resolve(12345, "Alice", "alice@example.com"))

        assert result == "urn:person:alice"
        assert len(commands.commands) == 0
        assert "foaf/0.1/mbox" in graph.queries[0]

    def test_email_match_found_via_crm_email(self):
        """SPARQL query uses UNION on foaf:mbox and crm:email."""
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:bob"))
        matcher, _, commands, _ = _make_matcher(graph=graph)

        result = _run(matcher.resolve(67890, "Bob", "bob@example.com"))

        assert result == "urn:person:bob"
        assert "crm:email" in graph.queries[0]
        assert len(commands.commands) == 0

    def test_email_fetch_from_monday_api_when_not_provided(self):
        """When no email provided, fetches from Monday.com API and looks up."""
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:charlie"))
        monday = MockMondayClient()
        monday.add_user(111, {
            "id": 111,
            "email": "charlie@example.com",
            "name": "Charlie Brown",
        })
        matcher, _, commands, _ = _make_matcher(graph=graph, monday=monday)

        result = _run(matcher.resolve(111, "Charlie"))

        assert result == "urn:person:charlie"
        assert len(monday.get_users_calls) == 1
        assert monday.get_users_calls[0] == [111]
        assert len(commands.commands) == 0

    def test_user_id_fallback_via_external_id(self):
        """Fallback to bpkm:externalId lookup when email lookups fail."""
        graph = MockGraphClient()
        graph.add_result(_empty_result())   # email lookup miss
        graph.add_result(_sparql_result("urn:person:david"))  # externalId hit
        monday = MockMondayClient()
        monday.add_user(222, {
            "id": 222,
            "email": "david@example.com",
            "name": "David",
        })
        matcher, _, commands, _ = _make_matcher(graph=graph, monday=monday)

        result = _run(matcher.resolve(222))

        assert result == "urn:person:david"
        assert len(commands.commands) == 0

    def test_person_creation_on_full_miss(self):
        """Creates a new Person when all lookups fail."""
        graph = MockGraphClient()
        graph.add_result(_empty_result())   # email lookup
        graph.add_result(_empty_result())   # externalId lookup
        monday = MockMondayClient()
        monday.add_user(333, {
            "id": 333,
            "email": "newuser@example.com",
            "name": "New User",
        })
        commands = MockCommandClient(iri="urn:person:created")
        matcher, _, _, _ = _make_matcher(graph=graph, commands=commands, monday=monday)

        result = _run(matcher.resolve(333, "New User"))

        assert result == "urn:person:created"
        assert len(commands.commands) == 1
        cmd_type, params = commands.commands[0]
        assert cmd_type == "object.create"
        assert params["type"] == pm._BPKM_PERSON_TYPE
        assert params["slug"] == "new-user"
        assert params["properties"]["dcterms:title"] == "New User"
        assert params["properties"]["foaf:mbox"] == "newuser@example.com"
        assert params["properties"][pm._BPKM_EXTERNAL_ID] == "333"

    def test_cache_hit_on_repeat_resolve(self):
        """Second resolve for same user_id uses cache — no extra queries."""
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:cached"))
        matcher, _, _, monday = _make_matcher(graph=graph)

        result1 = _run(matcher.resolve(444, "User", "user@example.com"))
        result2 = _run(matcher.resolve(444, "User", "user@example.com"))

        assert result1 == "urn:person:cached"
        assert result2 == "urn:person:cached"
        assert len(graph.queries) == 1  # Only one query, second was cache
        assert len(monday.get_users_calls) == 0

    def test_cache_key_is_string_of_user_id(self):
        """Numeric and string user IDs with same value share cache entry."""
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:same"))
        matcher, _, _, _ = _make_matcher(graph=graph)

        result1 = _run(matcher.resolve(555, "User", "u@example.com"))
        result2 = _run(matcher.resolve("555", "User", "u@example.com"))

        assert result1 == "urn:person:same"
        assert result2 == "urn:person:same"
        assert len(graph.queries) == 1

    def test_monday_api_failure_handled_gracefully(self):
        """When Monday.com API call fails, falls back to externalId lookup."""
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:fallback"))
        monday = MockMondayClient()
        monday.set_error(ConnectionError("API down"))
        matcher, _, commands, _ = _make_matcher(graph=graph, monday=monday)

        result = _run(matcher.resolve(666))

        assert result == "urn:person:fallback"
        assert len(monday.get_users_calls) == 1
        assert len(commands.commands) == 0

    def test_monday_api_failure_then_create(self):
        """API fails and externalId misses → creates person with user_id as title."""
        graph = MockGraphClient()
        graph.add_result(_empty_result())  # externalId miss
        monday = MockMondayClient()
        monday.set_error(ConnectionError("API down"))
        commands = MockCommandClient(iri="urn:person:api-fail-created")
        matcher, _, _, _ = _make_matcher(graph=graph, commands=commands, monday=monday)

        result = _run(matcher.resolve(777))

        assert result == "urn:person:api-fail-created"
        assert len(commands.commands) == 1
        _, params = commands.commands[0]
        assert params["properties"]["dcterms:title"] == "777"
        assert params["properties"][pm._BPKM_EXTERNAL_ID] == "777"
        assert "foaf:mbox" not in params["properties"]

    def test_creation_with_display_name_only(self):
        """Creates person using display_name when no email available."""
        graph = MockGraphClient()
        graph.add_result(_empty_result())  # externalId miss
        monday = MockMondayClient()
        monday.set_error(ConnectionError("API down"))
        commands = MockCommandClient(iri="urn:person:display-only")
        matcher, _, _, _ = _make_matcher(graph=graph, commands=commands, monday=monday)

        result = _run(matcher.resolve(888, "Display Name Only"))

        assert result == "urn:person:display-only"
        _, params = commands.commands[0]
        assert params["slug"] == "display-name-only"
        assert params["properties"]["dcterms:title"] == "Display Name Only"
        assert "foaf:mbox" not in params["properties"]
        assert params["properties"][pm._BPKM_EXTERNAL_ID] == "888"

    def test_creation_with_email_fallback_for_slug(self):
        """Uses email local part for slug when no display_name."""
        graph = MockGraphClient()
        graph.add_result(_empty_result())  # email miss
        graph.add_result(_empty_result())  # externalId miss
        commands = MockCommandClient(iri="urn:person:email-slug")
        matcher, _, _, _ = _make_matcher(graph=graph, commands=commands)

        result = _run(matcher.resolve(999, email="jane.doe@example.com"))

        assert result == "urn:person:email-slug"
        _, params = commands.commands[0]
        assert params["slug"] == "janedoe"
        assert params["properties"]["dcterms:title"] == "jane.doe"
        assert params["properties"]["foaf:mbox"] == "jane.doe@example.com"

    def test_email_provided_skips_monday_api(self):
        """When email is provided, Monday.com API is never called."""
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:direct"))
        matcher, _, _, monday = _make_matcher(graph=graph)

        _run(matcher.resolve(1010, "User", "user@example.com"))

        assert len(monday.get_users_calls) == 0

    def test_email_miss_then_external_id_miss_creates(self):
        """Full miss path: email SPARQL miss → externalId miss → create."""
        graph = MockGraphClient()
        graph.add_result(_empty_result())  # email miss
        graph.add_result(_empty_result())  # externalId miss
        commands = MockCommandClient(iri="urn:person:full-miss")
        matcher, _, _, _ = _make_matcher(graph=graph, commands=commands)

        result = _run(matcher.resolve(1111, "Full Miss", "full@miss.com"))

        assert result == "urn:person:full-miss"
        assert len(commands.commands) == 1
        assert len(graph.queries) == 2

    def test_api_provides_display_name_for_creation(self):
        """Monday.com API displayName used when caller didn't provide one."""
        graph = MockGraphClient()
        graph.add_result(_empty_result())  # email miss from API fetch
        graph.add_result(_empty_result())  # externalId miss
        monday = MockMondayClient()
        monday.add_user(1212, {
            "id": 1212,
            "email": "api@example.com",
            "name": "API Provided Name",
        })
        commands = MockCommandClient(iri="urn:person:api-named")
        matcher, _, _, _ = _make_matcher(graph=graph, commands=commands, monday=monday)

        result = _run(matcher.resolve(1212))

        assert result == "urn:person:api-named"
        _, params = commands.commands[0]
        assert params["properties"]["dcterms:title"] == "API Provided Name"
        assert params["slug"] == "api-provided-name"
        assert params["properties"]["foaf:mbox"] == "api@example.com"

    def test_different_user_ids_not_cached(self):
        """Different user_ids get separate cache entries."""
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:one"))
        graph.add_result(_sparql_result("urn:person:two"))
        matcher, _, _, _ = _make_matcher(graph=graph)

        r1 = _run(matcher.resolve(2001, "One", "one@example.com"))
        r2 = _run(matcher.resolve(2002, "Two", "two@example.com"))

        assert r1 == "urn:person:one"
        assert r2 == "urn:person:two"
        assert len(graph.queries) == 2

    def test_sparql_email_query_is_case_insensitive(self):
        """SPARQL email lookup uses LCASE for case-insensitive matching."""
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:case"))
        matcher, _, _, _ = _make_matcher(graph=graph)

        _run(matcher.resolve(3001, "Test", "Test@Example.COM"))

        assert "LCASE" in graph.queries[0]

    def test_monday_api_returns_empty_users_list(self):
        """When Monday.com API returns no users, falls through to create."""
        graph = MockGraphClient()
        graph.add_result(_empty_result())  # externalId miss
        monday = MockMondayClient()
        # Don't add user — get_users returns empty list
        commands = MockCommandClient(iri="urn:person:empty-api")
        matcher, _, _, _ = _make_matcher(graph=graph, commands=commands, monday=monday)

        result = _run(matcher.resolve(4001))

        assert result == "urn:person:empty-api"
        assert len(monday.get_users_calls) == 1
        assert len(commands.commands) == 1

    def test_external_id_stored_as_string(self):
        """bpkm:externalId is stored as string representation of user_id."""
        graph = MockGraphClient()
        graph.add_result(_empty_result())  # externalId miss
        monday = MockMondayClient()
        monday.set_error(ConnectionError("down"))
        commands = MockCommandClient(iri="urn:person:str-id")
        matcher, _, _, _ = _make_matcher(graph=graph, commands=commands, monday=monday)

        _run(matcher.resolve(5001, "User"))

        _, params = commands.commands[0]
        assert params["properties"][pm._BPKM_EXTERNAL_ID] == "5001"
        # Verify externalId query used string
        assert '"5001"' in graph.queries[0]


# ===================================================================
# _slugify tests
# ===================================================================

class TestSlugify:

    def test_basic_name(self):
        assert pm._slugify("Alice Smith") == "alice-smith"

    def test_extra_whitespace(self):
        assert pm._slugify("  Bob   Jones  ") == "bob-jones"

    def test_special_characters(self):
        assert pm._slugify("John O'Malley III") == "john-omalley-iii"

    def test_numeric_id_string(self):
        assert pm._slugify("12345") == "12345"

    def test_email_local_part(self):
        assert pm._slugify("jane.doe") == "janedoe"

    def test_unicode_stripped(self):
        assert pm._slugify("Ñoño García") == "oo-garca"

    def test_empty_after_strip(self):
        assert pm._slugify("!!!") == ""

    def test_consecutive_hyphens_collapsed(self):
        assert pm._slugify("a - - b") == "a-b"
