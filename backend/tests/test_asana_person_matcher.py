"""Tests for Asana person matcher — SPARQL lookup, create-on-miss, LRU cache.

Runs with ``pytest --noconftest`` — no fixtures or conftest required.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# sys.path setup — import the apps/asana-sync/services package
# ---------------------------------------------------------------------------
_apps_dir = str(Path(__file__).resolve().parent.parent.parent / "apps" / "asana-sync")
if _apps_dir not in sys.path:
    sys.path.insert(0, _apps_dir)

from services.person_matcher import PersonMatcher, _slugify, _email_local_part


# ---------------------------------------------------------------------------
# Async test helpers
# ---------------------------------------------------------------------------


class MockGraphClient:
    """Mock graph_client with configurable SPARQL query results."""

    def __init__(self, results: dict | None = None):
        self._results = results if results is not None else {"results": {"bindings": []}}
        self.queries: list[str] = []

    async def query(self, sparql: str) -> dict:
        self.queries.append(sparql)
        return self._results


class MockCommandClient:
    """Mock command_client that records execute calls."""

    def __init__(self, response: dict | None = None):
        self._response = response if response is not None else {"iri": "urn:test:person:new"}
        self.calls: list[tuple[str, dict]] = []

    async def execute(self, cmd_type: str, params: dict) -> dict:
        self.calls.append((cmd_type, params))
        return self._response


def _run(coro):
    """Run a coroutine synchronously."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestSlugify:
    def test_basic(self):
        assert _slugify("Alice Smith") == "alice-smith"

    def test_special_characters(self):
        assert _slugify("O'Brien, Jr.") == "obrien-jr"

    def test_multiple_spaces(self):
        assert _slugify("  hello   world  ") == "hello-world"

    def test_already_slug(self):
        assert _slugify("alice-smith") == "alice-smith"

    def test_numbers(self):
        assert _slugify("User 42") == "user-42"


class TestEmailLocalPart:
    def test_standard(self):
        assert _email_local_part("alice@example.com") == "alice"

    def test_no_domain(self):
        assert _email_local_part("justlocal") == "justlocal"

    def test_multiple_at(self):
        assert _email_local_part("alice@sub@example.com") == "alice"


# ---------------------------------------------------------------------------
# PersonMatcher tests
# ---------------------------------------------------------------------------


class TestPersonMatcherEmailFound:
    """Test: email match found via SPARQL → returns IRI, no execute called."""

    def test_email_found_returns_iri(self):
        existing_iri = "urn:sempkm:object:person-alice"
        graph = MockGraphClient({
            "results": {
                "bindings": [{"person": {"value": existing_iri}}]
            }
        })
        commands = MockCommandClient()
        matcher = PersonMatcher(graph, commands)

        result = _run(matcher.match_or_create("alice@example.com", "Alice"))
        assert result == existing_iri
        assert len(graph.queries) == 1
        assert len(commands.calls) == 0  # No creation


class TestPersonMatcherCreateOnMiss:
    """Test: no email match → creates Person, returns new IRI."""

    def test_no_match_creates_person(self):
        graph = MockGraphClient()  # empty bindings
        new_iri = "urn:sempkm:object:person-bob"
        commands = MockCommandClient({"iri": new_iri})
        matcher = PersonMatcher(graph, commands)

        result = _run(matcher.match_or_create("bob@example.com", "Bob Smith"))
        assert result == new_iri
        assert len(graph.queries) == 1
        assert len(commands.calls) == 1
        cmd_type, params = commands.calls[0]
        assert cmd_type == "object.create"
        assert params["slug"] == "bob-smith"
        assert params["properties"]["dcterms:title"] == "Bob Smith"
        assert params["properties"]["foaf:mbox"] == "bob@example.com"


class TestPersonMatcherCacheHit:
    """Test: cache hit on second call → no SPARQL query."""

    def test_cache_hit_skips_query(self):
        existing_iri = "urn:sempkm:object:person-alice"
        graph = MockGraphClient({
            "results": {
                "bindings": [{"person": {"value": existing_iri}}]
            }
        })
        commands = MockCommandClient()
        matcher = PersonMatcher(graph, commands)

        result1 = _run(matcher.match_or_create("alice@example.com", "Alice"))
        result2 = _run(matcher.match_or_create("alice@example.com", "Alice"))

        assert result1 == existing_iri
        assert result2 == existing_iri
        assert len(graph.queries) == 1  # Only one SPARQL query
        assert len(commands.calls) == 0


class TestPersonMatcherNoneEmail:
    """Test: None email → returns None."""

    def test_none_email_returns_none(self):
        graph = MockGraphClient()
        commands = MockCommandClient()
        matcher = PersonMatcher(graph, commands)

        result = _run(matcher.match_or_create(None, "Alice"))
        assert result is None
        assert len(graph.queries) == 0
        assert len(commands.calls) == 0


class TestPersonMatcherEmptyEmail:
    """Test: empty email → returns None."""

    def test_empty_email_returns_none(self):
        graph = MockGraphClient()
        commands = MockCommandClient()
        matcher = PersonMatcher(graph, commands)

        result = _run(matcher.match_or_create("", "Alice"))
        assert result is None
        assert len(graph.queries) == 0
        assert len(commands.calls) == 0


class TestPersonMatcherDisplayNameSlug:
    """Test: display_name used for slug when present."""

    def test_display_name_used_for_slug(self):
        graph = MockGraphClient()
        commands = MockCommandClient({"iri": "urn:test:person:new"})
        matcher = PersonMatcher(graph, commands)

        _run(matcher.match_or_create("alice@example.com", "Alice Wonderland"))
        _, params = commands.calls[0]
        assert params["slug"] == "alice-wonderland"
        assert params["properties"]["dcterms:title"] == "Alice Wonderland"


class TestPersonMatcherEmailLocalPartSlug:
    """Test: email local part used for slug when no display_name."""

    def test_no_display_name_uses_email_local(self):
        graph = MockGraphClient()
        commands = MockCommandClient({"iri": "urn:test:person:new"})
        matcher = PersonMatcher(graph, commands)

        _run(matcher.match_or_create("jane.doe@example.com", None))
        _, params = commands.calls[0]
        assert params["slug"] == "janedoe"
        assert params["properties"]["dcterms:title"] == "jane.doe"


class TestPersonMatcherMultipleEmails:
    """Test: multiple different emails → separate lookups."""

    def test_different_emails_separate_lookups(self):
        graph = MockGraphClient()
        commands = MockCommandClient({"iri": "urn:test:person:new"})
        matcher = PersonMatcher(graph, commands)

        _run(matcher.match_or_create("a@x.com", "A"))
        _run(matcher.match_or_create("b@x.com", "B"))

        assert len(graph.queries) == 2
        assert len(commands.calls) == 2


class TestPersonMatcherCaseInsensitiveCache:
    """Test: same email different case → cache hit (case-insensitive)."""

    def test_case_insensitive_cache(self):
        existing_iri = "urn:sempkm:object:person-alice"
        graph = MockGraphClient({
            "results": {
                "bindings": [{"person": {"value": existing_iri}}]
            }
        })
        commands = MockCommandClient()
        matcher = PersonMatcher(graph, commands)

        result1 = _run(matcher.match_or_create("Alice@Example.COM", "Alice"))
        result2 = _run(matcher.match_or_create("alice@example.com", "Alice"))

        assert result1 == existing_iri
        assert result2 == existing_iri
        assert len(graph.queries) == 1  # Only one lookup


class TestPersonMatcherEmptyDisplayNameFallback:
    """Test: empty string display_name falls back to email local part."""

    def test_empty_display_name_uses_email(self):
        graph = MockGraphClient()
        commands = MockCommandClient({"iri": "urn:test:person:new"})
        matcher = PersonMatcher(graph, commands)

        _run(matcher.match_or_create("user@corp.com", ""))
        _, params = commands.calls[0]
        # Empty string is falsy, so should fall back to email local part
        assert params["slug"] == "user"
        assert params["properties"]["dcterms:title"] == "user"
