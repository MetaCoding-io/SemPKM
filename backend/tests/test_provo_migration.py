"""Tests for PROV-O predicate alignment (M006/S01).

Verifies that all event, comment, and query history code now uses
PROV-O predicates instead of custom sempkm: predicates.
"""

from rdflib import URIRef
from rdflib.namespace import RDFS

from app.events.models import (
    EVENT_AFFECTED,
    EVENT_DESCRIPTION,
    EVENT_OPERATION,
    EVENT_PERFORMED_BY,
    EVENT_PERFORMED_BY_ROLE,
    EVENT_TIMESTAMP,
    EVENT_TYPE,
)
from app.rdf.namespaces import PROV, SEMPKM


class TestEventPredicateConstants:
    """Verify event metadata constants point to correct URIs."""

    def test_event_type_is_sempkm(self):
        """Event type stays as sempkm:Event (with subClassOf prov:Activity)."""
        assert EVENT_TYPE == SEMPKM.Event

    def test_timestamp_is_prov(self):
        """Timestamp uses prov:startedAtTime."""
        assert EVENT_TIMESTAMP == PROV.startedAtTime
        assert str(EVENT_TIMESTAMP) == "http://www.w3.org/ns/prov#startedAtTime"

    def test_performed_by_is_prov(self):
        """Performed-by uses prov:wasAssociatedWith."""
        assert EVENT_PERFORMED_BY == PROV.wasAssociatedWith
        assert str(EVENT_PERFORMED_BY) == "http://www.w3.org/ns/prov#wasAssociatedWith"

    def test_description_is_rdfs_label(self):
        """Description uses rdfs:label."""
        assert EVENT_DESCRIPTION == RDFS.label
        assert str(EVENT_DESCRIPTION) == "http://www.w3.org/2000/01/rdf-schema#label"

    def test_operation_stays_custom(self):
        """Operation type stays custom (no PROV-O equivalent)."""
        assert EVENT_OPERATION == SEMPKM.operationType

    def test_affected_stays_custom(self):
        """Affected IRI stays custom (no PROV-O equivalent)."""
        assert EVENT_AFFECTED == SEMPKM.affectedIRI

    def test_performed_by_role_stays_custom(self):
        """Performed-by role stays custom (D090)."""
        assert EVENT_PERFORMED_BY_ROLE == SEMPKM.performedByRole


class TestCommentPredicates:
    """Verify comment write code uses PROV-O predicates."""

    def test_comment_create_uses_prov_predicates(self):
        """_build_comment_create_operation should use prov:wasAttributedTo
        and prov:generatedAtTime."""
        from app.browser.comments import _build_comment_create_operation

        op = _build_comment_create_operation(
            comment_iri="urn:test:comment:1",
            object_iri="urn:test:object:1",
            body="test comment",
            author_uri=URIRef("urn:sempkm:user:test"),
        )

        # Check that the triples use PROV-O predicates
        predicates = [str(t[1]) for t in op.data_triples]
        assert "http://www.w3.org/ns/prov#wasAttributedTo" in predicates
        assert "http://www.w3.org/ns/prov#generatedAtTime" in predicates
        # Ensure old predicates are NOT present
        assert "urn:sempkm:commentedBy" not in predicates
        assert "urn:sempkm:commentedAt" not in predicates


class TestQueryHistoryPredicates:
    """Verify query execution history uses PROV-O predicates."""

    def test_executed_by_is_prov(self):
        """PRED_EXECUTED_BY should use prov:wasAssociatedWith."""
        from app.sparql.query_service import PRED_EXECUTED_BY

        assert PRED_EXECUTED_BY == "http://www.w3.org/ns/prov#wasAssociatedWith"


class TestMigrationScript:
    """Verify migration script structure and idempotency."""

    def test_migration_updates_defined(self):
        """Migration script has all 7 updates."""
        from scripts.migrate_provo import MIGRATION_UPDATES

        assert len(MIGRATION_UPDATES) == 7

    def test_verification_queries_defined(self):
        """Migration script has verification queries for all old predicates."""
        from scripts.migrate_provo import VERIFICATION_QUERIES

        assert len(VERIFICATION_QUERIES) == 6
        # Each should check for zero remaining triples
        predicate_names = [name for name, _ in VERIFICATION_QUERIES]
        assert "sempkm:timestamp" in predicate_names
        assert "sempkm:performedBy" in predicate_names
        assert "sempkm:description" in predicate_names
        assert "sempkm:commentedBy" in predicate_names
        assert "sempkm:commentedAt" in predicate_names
        assert "vocab:executedBy" in predicate_names

    def test_subclass_declaration_in_updates(self):
        """Migration includes the rdfs:subClassOf declaration."""
        from scripts.migrate_provo import MIGRATION_UPDATES

        subclass_found = any("subClassOf" in u for u in MIGRATION_UPDATES)
        assert subclass_found, "Missing rdfs:subClassOf declaration in migration"


class TestValidationReportPredicates:
    """Verify validation report uses PROV-O timestamp."""

    def test_lint_report_uses_prov_timestamp(self):
        """ValidationReport.to_structured_triples should use prov:startedAtTime."""
        from app.validation.report import ValidationReport

        report = ValidationReport(
            event_iri="urn:test:event:1",
            conforms=True,
            results=[],
            timestamp="2026-03-15T00:00:00+00:00",
        )
        triples = report.to_structured_triples(run_iri="urn:test:lint:1")
        predicates = [str(t[1]) for t in triples]
        assert "http://www.w3.org/ns/prov#startedAtTime" in predicates
        assert "urn:sempkm:timestamp" not in predicates
