"""Unit tests for the Linear→SemPKM person matcher.

Loads ``person_matcher.py`` from the apps directory via importlib so
the app does not need to be installed as a package.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load person_matcher module from apps directory
# ---------------------------------------------------------------------------

_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "linear-sync"
    / "services"
    / "person_matcher.py"
)

spec = importlib.util.spec_from_file_location("person_matcher", _MODULE_PATH)
assert spec and spec.loader
person_matcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(person_matcher)

PersonMatcher = person_matcher.PersonMatcher
_slugify = person_matcher._slugify
_email_local_part = person_matcher._email_local_part


# ===================================================================
# Mock clients
# ===================================================================


class MockGraphClient:
    """Stub for GraphClient.query() — returns pre-canned SPARQL results."""

    def __init__(self, results=None):
        self._results = results or {"results": {"bindings": []}}
        self.queries: list[str] = []

    async def query(self, sparql: str) -> dict:
        self.queries.append(sparql)
        return self._results


class MockCommandClient:
    """Stub for CommandClient.execute() — records calls and returns a fake IRI."""

    def __init__(self):
        self.commands: list[dict] = []

    async def execute(self, command_type: str, params: dict) -> dict:
        self.commands.append({"command": command_type, "params": params})
        slug = params.get("slug", "unknown")
        type_name = params["type"].split(":")[-1]
        return {"iri": f"https://example.org/data/{type_name}/{slug}"}


# ===================================================================
# Helpers
# ===================================================================


def _sparql_result_with_person(person_iri: str) -> dict:
    """Build a SPARQL JSON result with a single person binding."""
    return {
        "results": {
            "bindings": [
                {"person": {"type": "uri", "value": person_iri}}
            ]
        }
    }


# ===================================================================
# Tests — None / empty email
# ===================================================================


@pytest.mark.asyncio
async def test_none_email_returns_none():
    """None email returns None without issuing any query."""
    graph = MockGraphClient()
    cmds = MockCommandClient()
    matcher = PersonMatcher(graph, cmds)

    result = await matcher.match_or_create(None, "Alice Smith")

    assert result is None
    assert graph.queries == []
    assert cmds.commands == []


@pytest.mark.asyncio
async def test_empty_email_returns_none():
    """Empty string email returns None without issuing any query."""
    graph = MockGraphClient()
    cmds = MockCommandClient()
    matcher = PersonMatcher(graph, cmds)

    result = await matcher.match_or_create("", "Bob Jones")

    assert result is None
    assert graph.queries == []
    assert cmds.commands == []


# ===================================================================
# Tests — existing person found
# ===================================================================


@pytest.mark.asyncio
async def test_existing_person_found_via_foaf_mbox():
    """SPARQL returns a person binding → IRI returned, no create issued."""
    expected_iri = "https://example.org/data/Person/alice-smith"
    graph = MockGraphClient(results=_sparql_result_with_person(expected_iri))
    cmds = MockCommandClient()
    matcher = PersonMatcher(graph, cmds)

    result = await matcher.match_or_create("alice@example.com", "Alice Smith")

    assert result == expected_iri
    assert len(graph.queries) == 1
    assert "foaf/0.1/mbox" in graph.queries[0]
    assert cmds.commands == []


@pytest.mark.asyncio
async def test_existing_person_found_via_crm_email():
    """SPARQL returns a person via crm:email — same path as foaf:mbox."""
    expected_iri = "https://example.org/data/Person/bob"
    graph = MockGraphClient(results=_sparql_result_with_person(expected_iri))
    cmds = MockCommandClient()
    matcher = PersonMatcher(graph, cmds)

    result = await matcher.match_or_create("bob@corp.io", "Bob")

    assert result == expected_iri
    # The SPARQL query includes both predicates via UNION
    assert "crm:email" in graph.queries[0] or "urn:sempkm:model:crm:email" in graph.queries[0]
    assert cmds.commands == []


# ===================================================================
# Tests — new person created on SPARQL miss
# ===================================================================


@pytest.mark.asyncio
async def test_new_person_created_on_miss():
    """SPARQL returns empty bindings → create command issued, IRI returned."""
    graph = MockGraphClient()  # empty bindings
    cmds = MockCommandClient()
    matcher = PersonMatcher(graph, cmds)

    result = await matcher.match_or_create("carol@example.com", "Carol Danvers")

    assert result == "https://example.org/data/Person/carol-danvers"
    assert len(graph.queries) == 1  # lookup was attempted
    assert len(cmds.commands) == 1
    assert cmds.commands[0]["command"] == "object.create"


@pytest.mark.asyncio
async def test_created_person_has_correct_properties():
    """Verify the object.create params include type, slug, dcterms:title, foaf:mbox."""
    graph = MockGraphClient()
    cmds = MockCommandClient()
    matcher = PersonMatcher(graph, cmds)

    await matcher.match_or_create("dave@example.com", "Dave Grohl")

    params = cmds.commands[0]["params"]
    assert params["type"] == "urn:sempkm:model:basic-pkm:Person"
    assert params["slug"] == "dave-grohl"
    assert params["properties"]["dcterms:title"] == "Dave Grohl"
    assert params["properties"]["foaf:mbox"] == "dave@example.com"


# ===================================================================
# Tests — caching
# ===================================================================


@pytest.mark.asyncio
async def test_cache_prevents_duplicate_queries():
    """Second call with the same email returns cached IRI — no extra SPARQL."""
    graph = MockGraphClient()
    cmds = MockCommandClient()
    matcher = PersonMatcher(graph, cmds)

    iri1 = await matcher.match_or_create("eve@example.com", "Eve")
    iri2 = await matcher.match_or_create("eve@example.com", "Eve")

    assert iri1 == iri2
    assert len(graph.queries) == 1  # only first call queried
    assert len(cmds.commands) == 1  # only first call created


@pytest.mark.asyncio
async def test_cache_is_case_insensitive():
    """'Alice@example.com' and 'alice@example.com' share one cache entry."""
    graph = MockGraphClient()
    cmds = MockCommandClient()
    matcher = PersonMatcher(graph, cmds)

    iri1 = await matcher.match_or_create("Alice@Example.COM", "Alice")
    iri2 = await matcher.match_or_create("alice@example.com", "Alice")

    assert iri1 == iri2
    assert len(graph.queries) == 1
    assert len(cmds.commands) == 1


# ===================================================================
# Tests — slugification
# ===================================================================


@pytest.mark.asyncio
async def test_slug_from_display_name():
    """Display name 'Alice Smith' produces slug 'alice-smith'."""
    graph = MockGraphClient()
    cmds = MockCommandClient()
    matcher = PersonMatcher(graph, cmds)

    await matcher.match_or_create("alice@example.com", "Alice Smith")

    assert cmds.commands[0]["params"]["slug"] == "alice-smith"


@pytest.mark.asyncio
async def test_slug_from_email_when_no_name():
    """When display_name is None, slug is derived from email local part."""
    graph = MockGraphClient()
    cmds = MockCommandClient()
    matcher = PersonMatcher(graph, cmds)

    await matcher.match_or_create("j.doe@example.com", None)

    params = cmds.commands[0]["params"]
    assert params["slug"] == "jdoe"
    # Title also falls back to local part
    assert params["properties"]["dcterms:title"] == "j.doe"


# ===================================================================
# Tests — helper functions directly
# ===================================================================


def test_slugify_special_characters():
    """Slugify strips non-alphanumeric chars and collapses hyphens."""
    assert _slugify("Dr. Alice O'Brien") == "dr-alice-obrien"
    assert _slugify("  multiple   spaces  ") == "multiple-spaces"
    assert _slugify("Already-Slugged") == "already-slugged"


def test_email_local_part():
    """Email local part extraction works for normal addresses."""
    assert _email_local_part("alice@example.com") == "alice"
    assert _email_local_part("complex.name+tag@domain.co.uk") == "complex.name+tag"
