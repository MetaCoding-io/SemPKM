"""Unit tests for the Google Calendar person matcher.

Loads ``person_matcher.py`` from the apps directory via importlib so the
app does not need to be installed as a package.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load app module from apps directory
# ---------------------------------------------------------------------------

_SERVICES_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "google-calendar"
    / "services"
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_person_matcher = _load_module(
    "person_matcher", _SERVICES_DIR / "person_matcher.py"
)

PersonMatcher = _person_matcher.PersonMatcher
_slugify = _person_matcher._slugify
_email_local_part = _person_matcher._email_local_part


# ===================================================================
# Mock clients
# ===================================================================


class MockGraphClient:
    """Stub for GraphClient.query() — programmable SPARQL results."""

    def __init__(self, email_to_iri: dict[str, str] | None = None):
        self.email_to_iri = email_to_iri or {}
        self.queries: list[str] = []

    async def query(self, sparql: str) -> dict:
        self.queries.append(sparql)
        # Check if the query is looking up a known email
        for email, iri in self.email_to_iri.items():
            if email.lower() in sparql.lower():
                return {
                    "results": {
                        "bindings": [
                            {"person": {"type": "uri", "value": iri}}
                        ]
                    }
                }
        return {"results": {"bindings": []}}


class MockCommandClient:
    """Stub for CommandClient.execute() — returns synthesized IRIs."""

    def __init__(self):
        self.commands: list[dict] = []

    async def execute(self, command_type: str, params: dict) -> dict:
        self.commands.append({"command": command_type, "params": params})
        slug = params.get("slug", "unknown")
        return {"iri": f"https://example.org/data/Person/{slug}"}


# ===================================================================
# Tests
# ===================================================================


class TestPersonMatcherEmailLookup:
    """Test SPARQL email lookup path."""

    @pytest.mark.asyncio
    async def test_email_match_returns_iri(self):
        """When a person with the email exists, return its IRI."""
        graph = MockGraphClient(
            email_to_iri={"alice@example.com": "https://example.org/data/Person/alice"}
        )
        commands = MockCommandClient()
        matcher = PersonMatcher(graph, commands)

        result = await matcher.match_or_create("alice@example.com", "Alice Smith")

        assert result == "https://example.org/data/Person/alice"
        assert len(graph.queries) == 1
        assert len(commands.commands) == 0  # no creation

    @pytest.mark.asyncio
    async def test_no_match_creates_person(self):
        """When no person matches, create one and return its IRI."""
        graph = MockGraphClient()  # no matches
        commands = MockCommandClient()
        matcher = PersonMatcher(graph, commands)

        result = await matcher.match_or_create("bob@example.com", "Bob Jones")

        assert result == "https://example.org/data/Person/bob-jones"
        assert len(commands.commands) == 1
        cmd = commands.commands[0]
        assert cmd["command"] == "object.create"
        assert cmd["params"]["slug"] == "bob-jones"
        assert cmd["params"]["properties"]["dcterms:title"] == "Bob Jones"
        assert cmd["params"]["properties"]["foaf:mbox"] == "bob@example.com"


class TestPersonMatcherCache:
    """Test LRU cache behaviour."""

    @pytest.mark.asyncio
    async def test_cache_hit_skips_query(self):
        """Second call for the same email should return cached IRI."""
        graph = MockGraphClient(
            email_to_iri={"alice@example.com": "https://example.org/data/Person/alice"}
        )
        commands = MockCommandClient()
        matcher = PersonMatcher(graph, commands)

        # First call: query + cache
        result1 = await matcher.match_or_create("alice@example.com", "Alice")
        # Second call: cache hit
        result2 = await matcher.match_or_create("alice@example.com", "Alice")

        assert result1 == result2
        assert len(graph.queries) == 1  # only one SPARQL query

    @pytest.mark.asyncio
    async def test_cache_key_is_case_insensitive(self):
        """Cache keys should be lowercased — same email different case hits cache."""
        graph = MockGraphClient(
            email_to_iri={"alice@example.com": "https://example.org/data/Person/alice"}
        )
        commands = MockCommandClient()
        matcher = PersonMatcher(graph, commands)

        result1 = await matcher.match_or_create("Alice@Example.COM", "Alice")
        result2 = await matcher.match_or_create("alice@example.com", "Alice")

        assert result1 == result2
        assert len(graph.queries) == 1  # only one query


class TestPersonMatcherEdgeCases:
    """Test None/empty email and slug generation."""

    @pytest.mark.asyncio
    async def test_none_email_returns_none(self):
        """None email should return None without queries."""
        graph = MockGraphClient()
        commands = MockCommandClient()
        matcher = PersonMatcher(graph, commands)

        result = await matcher.match_or_create(None, "Some Name")

        assert result is None
        assert len(graph.queries) == 0
        assert len(commands.commands) == 0

    @pytest.mark.asyncio
    async def test_empty_email_returns_none(self):
        """Empty string email should return None."""
        graph = MockGraphClient()
        commands = MockCommandClient()
        matcher = PersonMatcher(graph, commands)

        result = await matcher.match_or_create("", "Some Name")

        assert result is None
        assert len(graph.queries) == 0

    @pytest.mark.asyncio
    async def test_display_name_used_for_slug(self):
        """When display name is provided, slug should be derived from it."""
        graph = MockGraphClient()
        commands = MockCommandClient()
        matcher = PersonMatcher(graph, commands)

        await matcher.match_or_create("charlie@test.com", "Charlie Brown")

        cmd = commands.commands[0]
        assert cmd["params"]["slug"] == "charlie-brown"
        assert cmd["params"]["properties"]["dcterms:title"] == "Charlie Brown"

    @pytest.mark.asyncio
    async def test_email_local_part_used_when_no_display_name(self):
        """When display_name is None, slug from email local part."""
        graph = MockGraphClient()
        commands = MockCommandClient()
        matcher = PersonMatcher(graph, commands)

        await matcher.match_or_create("dsmith@company.org", None)

        cmd = commands.commands[0]
        assert cmd["params"]["slug"] == "dsmith"
        assert cmd["params"]["properties"]["dcterms:title"] == "dsmith"


class TestSlugify:
    """Test the internal _slugify function."""

    def test_basic_slugify(self):
        assert _slugify("Hello World") == "hello-world"

    def test_special_chars_removed(self):
        assert _slugify("O'Brien-Smith Jr.") == "obrien-smith-jr"

    def test_multiple_spaces(self):
        assert _slugify("  multiple   spaces  ") == "multiple-spaces"
