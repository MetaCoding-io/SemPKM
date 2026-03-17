"""Tests for the body.diff command — handler, schema, and dispatcher wiring.

T01 tests cover the foundational plumbing: schemas, handler Operation output,
and dispatcher/webhook registration. T02 adds tests for _parse_stored_diff(),
event detail body.diff handling, _OP_PRIORITY, and backward compat.
"""

import pytest
from rdflib import URIRef, Variable
from rdflib.namespace import XSD

from app.commands.handlers.body_diff import handle_body_diff
from app.commands.schemas import BodyDiffCommand, BodyDiffParams
from app.events.store import Operation
from app.rdf.namespaces import SEMPKM


class TestBodyDiffHandler:
    """Tests for handle_body_diff() producing correct Operations."""

    @pytest.mark.asyncio
    async def test_produces_operation_with_correct_type(self):
        """Handler returns Operation with operation_type='body.diff'."""
        params = BodyDiffParams(
            iri="urn:sempkm:obj:test-1",
            body="new body content",
            diff_text="--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new",
        )
        op = await handle_body_diff(params, "urn:sempkm:")
        assert isinstance(op, Operation)
        assert op.operation_type == "body.diff"
        assert op.affected_iris == ["urn:sempkm:obj:test-1"]
        assert "Diff body on:" in op.description

    @pytest.mark.asyncio
    async def test_data_triples_contain_diff_and_body(self):
        """data_triples stores both sempkm:bodyDiff and the full body."""
        params = BodyDiffParams(
            iri="urn:sempkm:obj:test-1",
            body="new body",
            diff_text="the diff text",
        )
        op = await handle_body_diff(params, "urn:sempkm:")

        subject = URIRef("urn:sempkm:obj:test-1")
        # Should have exactly 2 data triples
        assert len(op.data_triples) == 2

        # First triple: the diff
        s, p, o = op.data_triples[0]
        assert s == subject
        assert p == SEMPKM.bodyDiff
        assert str(o) == "the diff text"
        assert o.datatype == XSD.string

        # Second triple: the full body
        s, p, o = op.data_triples[1]
        assert s == subject
        assert p == SEMPKM.body
        assert str(o) == "new body"
        assert o.datatype == XSD.string

    @pytest.mark.asyncio
    async def test_materialization_matches_body_set_pattern(self):
        """materialize_deletes and materialize_inserts mirror body.set."""
        params = BodyDiffParams(
            iri="urn:sempkm:obj:test-1",
            body="updated content",
            diff_text="some diff",
        )
        op = await handle_body_diff(params, "urn:sempkm:")

        subject = URIRef("urn:sempkm:obj:test-1")

        # Deletes: remove old body under default predicate
        assert len(op.materialize_deletes) == 1
        s, p, o = op.materialize_deletes[0]
        assert s == subject
        assert p == SEMPKM.body
        assert isinstance(o, Variable)

        # Inserts: new body under default predicate
        assert len(op.materialize_inserts) == 1
        s, p, o = op.materialize_inserts[0]
        assert s == subject
        assert p == SEMPKM.body
        assert str(o) == "updated content"

    @pytest.mark.asyncio
    async def test_custom_predicate_adds_canonical_cleanup(self):
        """When predicate differs from sempkm:body, also clean canonical."""
        params = BodyDiffParams(
            iri="urn:sempkm:obj:test-1",
            body="new body",
            diff_text="diff",
            predicate="urn:custom:body",
        )
        op = await handle_body_diff(params, "urn:sempkm:")

        subject = URIRef("urn:sempkm:obj:test-1")
        custom_pred = URIRef("urn:custom:body")

        # data_triples: diff uses sempkm:bodyDiff, body uses custom predicate
        assert op.data_triples[0][1] == SEMPKM.bodyDiff
        assert op.data_triples[1][1] == custom_pred

        # materialize_deletes: custom predicate + canonical cleanup
        assert len(op.materialize_deletes) == 2
        assert op.materialize_deletes[0][1] == custom_pred
        assert op.materialize_deletes[1][1] == SEMPKM.body

        # materialize_inserts: only custom predicate
        assert len(op.materialize_inserts) == 1
        assert op.materialize_inserts[0][1] == custom_pred


class TestBodyDiffSchema:
    """Tests for BodyDiffParams and BodyDiffCommand schema validation."""

    def test_params_required_fields(self):
        """BodyDiffParams requires iri, body, and diff_text."""
        params = BodyDiffParams(
            iri="urn:test:1",
            body="content",
            diff_text="diff",
        )
        assert params.iri == "urn:test:1"
        assert params.body == "content"
        assert params.diff_text == "diff"
        assert params.predicate is None

    def test_command_discriminator(self):
        """BodyDiffCommand uses 'body.diff' as discriminator."""
        cmd = BodyDiffCommand(
            command="body.diff",
            params=BodyDiffParams(
                iri="urn:test:1",
                body="content",
                diff_text="diff",
            ),
        )
        assert cmd.command == "body.diff"


class TestBodyDiffWiring:
    """Tests for dispatcher and webhook registration."""

    def test_handler_registered_in_dispatcher(self):
        """body.diff handler is in HANDLER_REGISTRY after registration."""
        from app.commands.dispatcher import HANDLER_REGISTRY, _register_handlers

        _register_handlers()
        assert "body.diff" in HANDLER_REGISTRY

    def test_webhook_event_mapping(self):
        """body.diff maps to 'object.changed' webhook event."""
        from app.commands.router import _COMMAND_EVENT_MAP

        assert _COMMAND_EVENT_MAP["body.diff"] == "object.changed"


class TestOpPriority:
    """Tests for _OP_PRIORITY containing body.diff."""

    def test_body_diff_in_op_priority(self):
        """body.diff is in _OP_PRIORITY list."""
        from app.events.query import _OP_PRIORITY

        assert "body.diff" in _OP_PRIORITY

    def test_body_diff_after_body_set(self):
        """body.diff appears after body.set in priority order."""
        from app.events.query import _OP_PRIORITY

        set_idx = _OP_PRIORITY.index("body.set")
        diff_idx = _OP_PRIORITY.index("body.diff")
        assert diff_idx == set_idx + 1

    def test_get_primary_operation_body_diff(self):
        """get_primary_operation recognizes body.diff as a primary op."""
        from app.events.query import get_primary_operation

        primary, secondary = get_primary_operation("body.diff")
        assert primary == "body.diff"
        assert secondary == []


class TestParseStoredDiff:
    """Tests for EventQueryService._parse_stored_diff()."""

    def _make_service(self):
        """Create an EventQueryService with a dummy client."""
        from app.events.query import EventQueryService
        return EventQueryService(client=None)

    def test_parse_additions_and_removals(self):
        """Correctly parses +/- lines from unified diff."""
        svc = self._make_service()
        diff_text = "--- a\n+++ b\n@@ -1,2 +1,2 @@\n-old line\n+new line\n context"
        result = svc._parse_stored_diff(diff_text)
        assert result == [
            {"type": "remove", "text": "old line"},
            {"type": "add", "text": "new line"},
            {"type": "context", "text": "context"},
        ]

    def test_parse_empty_diff(self):
        """Empty diff text returns no-changes marker."""
        svc = self._make_service()
        result = svc._parse_stored_diff("")
        assert result == [{"type": "context", "text": "(no changes)"}]

    def test_parse_context_only(self):
        """Lines without +/- prefix are context lines."""
        svc = self._make_service()
        diff_text = " line one\n line two"
        result = svc._parse_stored_diff(diff_text)
        assert result == [
            {"type": "context", "text": "line one"},
            {"type": "context", "text": "line two"},
        ]

    def test_skips_header_lines(self):
        """Skips --- +++ and @@ header lines."""
        svc = self._make_service()
        diff_text = "--- a/file\n+++ b/file\n@@ -1 +1 @@\n+added"
        result = svc._parse_stored_diff(diff_text)
        assert result == [{"type": "add", "text": "added"}]


class TestEventDetailBodyDiffHandling:
    """Tests for get_event_detail() handling body.diff events (T02)."""

    def _make_service(self):
        from app.events.query import EventQueryService
        return EventQueryService(client=None)

    def test_body_diff_reads_stored_diff(self):
        """body.diff events parse diff from data_triples, not computed."""
        svc = self._make_service()
        # Simulate what get_event_detail() does for body.diff
        op_type = "body.diff"
        data_triples = [
            ("urn:s", "urn:sempkm:bodyDiff", "-old\n+new"),
            ("urn:s", "urn:sempkm:body", "new body"),
        ]

        # Extract diff from data_triples (mirrors get_event_detail logic)
        body_diff = None
        if "body.diff" in op_type:
            diff_text = None
            for s, p, o in data_triples:
                if p == "urn:sempkm:bodyDiff":
                    diff_text = o
                    break
            if diff_text:
                body_diff = svc._parse_stored_diff(diff_text)

        assert body_diff is not None
        assert body_diff == [
            {"type": "remove", "text": "old"},
            {"type": "add", "text": "new"},
        ]

    def test_body_set_backward_compat(self):
        """body.set events still use _compute_body_diff() on the fly."""
        svc = self._make_service()
        old_body = "line one\nline two"
        new_body = "line one\nline three"
        result = svc._compute_body_diff(old_body, new_body)
        # Should contain a removal and an addition
        types = [line["type"] for line in result]
        assert "remove" in types
        assert "add" in types
