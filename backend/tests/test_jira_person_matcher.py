"""Unit tests for Jira Sync person matcher.

Loads ``person_matcher.py`` from the apps directory using importlib. All
graph, command, and Jira client interactions are mocked — no network calls
or SPARQL endpoints are needed.

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
    / "jira-sync"
    / "services"
    / "person_matcher.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("jira_person_matcher", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["jira_person_matcher"] = mod
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


class MockJiraClient:
    """Mock Jira client that returns canned user data."""

    def __init__(self):
        self._users: dict[str, dict] = {}
        self.get_user_calls: list[str] = []
        self._error: Exception | None = None

    def add_user(self, account_id: str, user_data: dict):
        """Register a user to return for get_user(account_id)."""
        self._users[account_id] = user_data

    def set_error(self, error: Exception):
        """Make get_user raise this error."""
        self._error = error

    async def get_user(self, account_id: str) -> dict:
        self.get_user_calls.append(account_id)
        if self._error:
            raise self._error
        if account_id in self._users:
            return self._users[account_id]
        raise Exception(f"User {account_id} not found")


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
    jira: MockJiraClient | None = None,
) -> tuple[pm.PersonMatcher, MockGraphClient, MockCommandClient, MockJiraClient]:
    """Create a PersonMatcher with mock dependencies."""
    g = graph or MockGraphClient()
    c = commands or MockCommandClient()
    j = jira or MockJiraClient()
    matcher = pm.PersonMatcher(g, c, j)
    return matcher, g, c, j


# ===================================================================
# PersonMatcher.resolve tests
# ===================================================================

class TestPersonMatcherResolve:

    def test_none_account_id_returns_none(self):
        matcher, _, _, _ = _make_matcher()
        result = _run(matcher.resolve(None))
        assert result is None

    def test_email_match_found_in_sparql(self):
        """When email is provided and SPARQL finds a match, returns it."""
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:alice"))
        matcher, _, commands, _ = _make_matcher(graph=graph)

        result = _run(matcher.resolve("acc-123", "Alice", "alice@example.com"))

        assert result == "urn:person:alice"
        assert len(commands.commands) == 0
        assert "foaf:mbox" in graph.queries[0] or "crm:email" in graph.queries[0]

    def test_account_id_fallback_via_jira_api(self):
        """When no email provided, fetches from Jira API and looks up by email."""
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:bob"))
        jira = MockJiraClient()
        jira.add_user("acc-456", {
            "emailAddress": "bob@example.com",
            "displayName": "Bob Smith",
        })
        matcher, _, commands, _ = _make_matcher(graph=graph, jira=jira)

        result = _run(matcher.resolve("acc-456", "Bob Smith"))

        assert result == "urn:person:bob"
        assert len(jira.get_user_calls) == 1
        assert len(commands.commands) == 0

    def test_account_id_match_in_sparql(self):
        """Fallback to bpkm:externalId lookup when email lookups fail."""
        graph = MockGraphClient()
        graph.add_result(_empty_result())  # email lookup from API
        graph.add_result(_sparql_result("urn:person:charlie"))  # externalId hit
        jira = MockJiraClient()
        jira.add_user("acc-789", {
            "emailAddress": "charlie@example.com",
            "displayName": "Charlie",
        })
        matcher, _, commands, _ = _make_matcher(graph=graph, jira=jira)

        result = _run(matcher.resolve("acc-789"))

        assert result == "urn:person:charlie"
        assert len(commands.commands) == 0

    def test_person_creation_on_miss(self):
        """Creates a new Person when all lookups fail."""
        graph = MockGraphClient()
        graph.add_result(_empty_result())
        graph.add_result(_empty_result())
        jira = MockJiraClient()
        jira.add_user("acc-new", {
            "emailAddress": "newuser@example.com",
            "displayName": "New User",
        })
        commands = MockCommandClient(iri="urn:person:created")
        matcher, _, _, _ = _make_matcher(graph=graph, commands=commands, jira=jira)

        result = _run(matcher.resolve("acc-new", "New User"))

        assert result == "urn:person:created"
        assert len(commands.commands) == 1
        cmd_type, params = commands.commands[0]
        assert cmd_type == "object.create"
        assert params["type"] == pm._BPKM_PERSON_TYPE
        assert params["slug"] == "new-user"
        assert params["properties"]["dcterms:title"] == "New User"
        assert params["properties"]["foaf:mbox"] == "newuser@example.com"
        assert params["properties"][pm._BPKM_EXTERNAL_ID] == "acc-new"

    def test_cache_hit_on_repeat_resolve(self):
        """Second resolve for same account_id uses cache."""
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:cached"))
        matcher, _, _, jira = _make_matcher(graph=graph)

        result1 = _run(matcher.resolve("acc-cached", "User", "user@example.com"))
        result2 = _run(matcher.resolve("acc-cached", "User", "user@example.com"))

        assert result1 == "urn:person:cached"
        assert result2 == "urn:person:cached"
        assert len(graph.queries) == 1
        assert len(jira.get_user_calls) == 0

    def test_jira_get_user_failure_handled_gracefully(self):
        """When Jira API call fails, falls back to externalId lookup."""
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:fallback"))
        jira = MockJiraClient()
        jira.set_error(ConnectionError("API down"))
        matcher, _, commands, _ = _make_matcher(graph=graph, jira=jira)

        result = _run(matcher.resolve("acc-fail"))

        assert result == "urn:person:fallback"
        assert len(jira.get_user_calls) == 1
        assert len(commands.commands) == 0

    def test_creation_with_display_name_only(self):
        """Creates person using display_name when no email available."""
        graph = MockGraphClient()
        graph.add_result(_empty_result())
        jira = MockJiraClient()
        jira.set_error(ConnectionError("API down"))
        commands = MockCommandClient(iri="urn:person:display-only")
        matcher, _, _, _ = _make_matcher(graph=graph, commands=commands, jira=jira)

        result = _run(matcher.resolve("acc-nomail", "Display Name Only"))

        assert result == "urn:person:display-only"
        assert len(commands.commands) == 1
        _, params = commands.commands[0]
        assert params["slug"] == "display-name-only"
        assert params["properties"]["dcterms:title"] == "Display Name Only"
        assert "foaf:mbox" not in params["properties"]
        assert params["properties"][pm._BPKM_EXTERNAL_ID] == "acc-nomail"

    def test_creation_with_account_id_fallback(self):
        """Creates person using account_id when no display_name or email."""
        graph = MockGraphClient()
        graph.add_result(_empty_result())
        jira = MockJiraClient()
        jira.set_error(ConnectionError("API down"))
        commands = MockCommandClient(iri="urn:person:id-only")
        matcher, _, _, _ = _make_matcher(graph=graph, commands=commands, jira=jira)

        result = _run(matcher.resolve("acc-minimal"))

        assert result == "urn:person:id-only"
        _, params = commands.commands[0]
        assert params["slug"] == "acc-minimal"
        assert params["properties"]["dcterms:title"] == "acc-minimal"

    def test_email_provided_skips_jira_api(self):
        """When email is provided, Jira API is never called."""
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:direct"))
        matcher, _, _, jira = _make_matcher(graph=graph)

        _run(matcher.resolve("acc-direct", "User", "user@example.com"))

        assert len(jira.get_user_calls) == 0

    def test_email_miss_then_external_id_miss_creates(self):
        """Full miss path: email SPARQL miss → externalId miss → create."""
        graph = MockGraphClient()
        graph.add_result(_empty_result())  # email miss
        graph.add_result(_empty_result())  # externalId miss
        commands = MockCommandClient(iri="urn:person:full-miss")
        matcher, _, _, _ = _make_matcher(graph=graph, commands=commands)

        result = _run(matcher.resolve("acc-fullmiss", "Full Miss", "full@miss.com"))

        assert result == "urn:person:full-miss"
        assert len(commands.commands) == 1
        assert len(graph.queries) == 2

    def test_jira_api_provides_display_name_for_creation(self):
        """Jira API displayName used when resolve caller didn't provide one."""
        graph = MockGraphClient()
        graph.add_result(_empty_result())
        graph.add_result(_empty_result())
        jira = MockJiraClient()
        jira.add_user("acc-api-name", {
            "emailAddress": "api@example.com",
            "displayName": "API Provided Name",
        })
        commands = MockCommandClient(iri="urn:person:api-named")
        matcher, _, _, _ = _make_matcher(graph=graph, commands=commands, jira=jira)

        result = _run(matcher.resolve("acc-api-name"))

        assert result == "urn:person:api-named"
        _, params = commands.commands[0]
        assert params["properties"]["dcterms:title"] == "API Provided Name"
        assert params["slug"] == "api-provided-name"

    def test_cache_keyed_by_account_id(self):
        """Cache uses account_id as key, not email."""
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:first"))
        matcher, _, _, _ = _make_matcher(graph=graph)

        _run(matcher.resolve("acc-same", "User A", "a@example.com"))
        result = _run(matcher.resolve("acc-same", "User A", "b@example.com"))

        assert result == "urn:person:first"
        assert len(graph.queries) == 1

    def test_different_account_ids_not_cached(self):
        """Different account_ids get separate cache entries."""
        graph = MockGraphClient()
        graph.add_result(_sparql_result("urn:person:one"))
        graph.add_result(_sparql_result("urn:person:two"))
        matcher, _, _, _ = _make_matcher(graph=graph)

        r1 = _run(matcher.resolve("acc-1", "One", "one@example.com"))
        r2 = _run(matcher.resolve("acc-2", "Two", "two@example.com"))

        assert r1 == "urn:person:one"
        assert r2 == "urn:person:two"
        assert len(graph.queries) == 2
