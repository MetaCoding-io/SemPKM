"""Tests for dcterms:created and dcterms:modified auto-injection in object.create handler."""

from datetime import datetime, timezone

import pytest
from rdflib import Literal
from rdflib.namespace import XSD

from app.commands.handlers.object_create import (
    DCTERMS_CREATED,
    DCTERMS_MODIFIED,
    handle_object_create,
)
from app.commands.schemas import ObjectCreateParams

BASE_NS = "http://example.org/data/"


@pytest.fixture
def basic_params():
    """Minimal ObjectCreateParams for a Note with a label."""
    return ObjectCreateParams(
        type="Note",
        slug="test-note",
        properties={"rdfs:label": "Test Note"},
    )


class TestTimestampInjection:
    """Verify that handle_object_create injects dcterms:created and dcterms:modified."""

    async def test_created_triple_present(self, basic_params):
        """dcterms:created triple must be present in data_triples."""
        op = await handle_object_create(basic_params, BASE_NS)
        predicates = [t[1] for t in op.data_triples]
        assert DCTERMS_CREATED in predicates, "dcterms:created triple missing"

    async def test_modified_triple_present(self, basic_params):
        """dcterms:modified triple must be present in data_triples."""
        op = await handle_object_create(basic_params, BASE_NS)
        predicates = [t[1] for t in op.data_triples]
        assert DCTERMS_MODIFIED in predicates, "dcterms:modified triple missing"

    async def test_created_is_xsd_datetime(self, basic_params):
        """dcterms:created value must be an xsd:dateTime typed Literal."""
        op = await handle_object_create(basic_params, BASE_NS)
        created_triples = [t for t in op.data_triples if t[1] == DCTERMS_CREATED]
        assert len(created_triples) == 1
        obj = created_triples[0][2]
        assert isinstance(obj, Literal), f"Expected Literal, got {type(obj)}"
        assert obj.datatype == XSD.dateTime, f"Expected xsd:dateTime, got {obj.datatype}"

    async def test_modified_is_xsd_datetime(self, basic_params):
        """dcterms:modified value must be an xsd:dateTime typed Literal."""
        op = await handle_object_create(basic_params, BASE_NS)
        modified_triples = [t for t in op.data_triples if t[1] == DCTERMS_MODIFIED]
        assert len(modified_triples) == 1
        obj = modified_triples[0][2]
        assert isinstance(obj, Literal)
        assert obj.datatype == XSD.dateTime

    async def test_timestamp_is_utc_iso8601(self, basic_params):
        """Timestamp string must parse as valid ISO 8601 with UTC timezone."""
        before = datetime.now(timezone.utc)
        op = await handle_object_create(basic_params, BASE_NS)
        after = datetime.now(timezone.utc)

        created_triples = [t for t in op.data_triples if t[1] == DCTERMS_CREATED]
        ts_str = str(created_triples[0][2])
        ts = datetime.fromisoformat(ts_str)
        assert ts.tzinfo is not None, "Timestamp must include timezone"
        assert before <= ts <= after, f"Timestamp {ts} not between {before} and {after}"

    async def test_created_and_modified_same_value(self, basic_params):
        """On creation, dcterms:created and dcterms:modified should have the same value."""
        op = await handle_object_create(basic_params, BASE_NS)
        created_val = [t[2] for t in op.data_triples if t[1] == DCTERMS_CREATED][0]
        modified_val = [t[2] for t in op.data_triples if t[1] == DCTERMS_MODIFIED][0]
        assert str(created_val) == str(modified_val)


class TestUserSuppliedTimestamps:
    """Verify user-supplied dcterms:created/modified are not overwritten."""

    async def test_user_created_not_overwritten(self):
        """If user supplies dcterms:created, the handler must not add a second one."""
        user_ts = "2025-01-15T10:30:00+00:00"
        params = ObjectCreateParams(
            type="Note",
            slug="user-ts",
            properties={
                "rdfs:label": "User TS Note",
                "dcterms:created": user_ts,
            },
        )
        op = await handle_object_create(params, BASE_NS)
        created_triples = [t for t in op.data_triples if t[1] == DCTERMS_CREATED]
        assert len(created_triples) == 1, f"Expected 1 dcterms:created, got {len(created_triples)}"
        assert str(created_triples[0][2]) == user_ts

    async def test_user_modified_not_overwritten(self):
        """If user supplies dcterms:modified, the handler must not add a second one."""
        user_ts = "2025-06-01T12:00:00+00:00"
        params = ObjectCreateParams(
            type="Note",
            slug="user-mod",
            properties={
                "rdfs:label": "User Mod Note",
                "dcterms:modified": user_ts,
            },
        )
        op = await handle_object_create(params, BASE_NS)
        modified_triples = [t for t in op.data_triples if t[1] == DCTERMS_MODIFIED]
        assert len(modified_triples) == 1, f"Expected 1 dcterms:modified, got {len(modified_triples)}"
        assert str(modified_triples[0][2]) == user_ts

    async def test_user_created_still_gets_auto_modified(self):
        """If user supplies only dcterms:created, dcterms:modified should still be auto-injected."""
        params = ObjectCreateParams(
            type="Note",
            slug="partial",
            properties={
                "rdfs:label": "Partial Note",
                "dcterms:created": "2025-01-15T10:30:00+00:00",
            },
        )
        op = await handle_object_create(params, BASE_NS)
        modified_triples = [t for t in op.data_triples if t[1] == DCTERMS_MODIFIED]
        assert len(modified_triples) == 1, "dcterms:modified should be auto-injected"

    async def test_user_full_iri_created_not_overwritten(self):
        """If user supplies dcterms:created via full IRI key, handler must not duplicate."""
        user_ts = "2025-03-20T08:00:00+00:00"
        params = ObjectCreateParams(
            type="Note",
            slug="full-iri",
            properties={
                "rdfs:label": "Full IRI Note",
                "http://purl.org/dc/terms/created": user_ts,
            },
        )
        op = await handle_object_create(params, BASE_NS)
        created_triples = [t for t in op.data_triples if t[1] == DCTERMS_CREATED]
        assert len(created_triples) == 1, f"Expected 1 dcterms:created, got {len(created_triples)}"
