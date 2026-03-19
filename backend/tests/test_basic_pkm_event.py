"""Acceptance tests for basic-pkm v2.1.0 (Event type).

Validates the complete bpkm:Event type addition:
  - Manifest v2.1.0 with 7 icons
  - 7 OWL classes including Event
  - 7 NodeShapes including EventShape with 5 property groups
  - 21 ViewSpecs (7 types × 3 renderers) and 8 SavedQueries
  - 4 seed Event instances
  - pyshacl fires zero errors on seed+ontology
"""

from pathlib import Path

import pyshacl
import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from app.models.loader import load_archive
from app.models.manifest import parse_manifest
from app.models.validator import validate_archive

# Namespaces
BPKM = Namespace("urn:sempkm:model:basic-pkm:")
SH = Namespace("http://www.w3.org/ns/shacl#")
SEMPKM = Namespace("urn:sempkm:vocab:")
GIST = Namespace("https://w3id.org/semanticarts/ns/ontology/gist/")
DCTERMS = Namespace("http://purl.org/dc/terms/")
SCHEMA = Namespace("https://schema.org/")

MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "basic-pkm"


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def manifest():
    return parse_manifest(MODEL_DIR)


@pytest.fixture(scope="module")
def archive(manifest):
    return load_archive(MODEL_DIR, manifest)


# ── Manifest Tests ──────────────────────────────────────────────────


def test_manifest_version_2_1(manifest):
    """Manifest parses as v2.1.0 with 7 icons including Event."""
    assert manifest.version == "2.1.0"
    assert manifest.modelId == "basic-pkm"
    assert len(manifest.icons) == 7
    icon_types = {icon.type for icon in manifest.icons}
    assert "bpkm:Event" in icon_types
    # Verify Event icon properties
    event_icon = next(i for i in manifest.icons if i.type == "bpkm:Event")
    assert event_icon.icon == "calendar"
    assert event_icon.color == "#8b5cf6"


# ── Archive Loading Tests ───────────────────────────────────────────


def test_archive_loads_all_graphs(archive):
    """All five graphs (ontology, shapes, views, seed, rules) load non-empty."""
    assert archive.ontology is not None and len(archive.ontology) > 0
    assert archive.shapes is not None and len(archive.shapes) > 0
    assert archive.views is not None and len(archive.views) > 0
    assert archive.seed is not None and len(archive.seed) > 0
    assert archive.rules is not None and len(archive.rules) > 0


# ── Validation Tests ────────────────────────────────────────────────


def test_archive_validates_zero_errors(archive):
    """Archive passes offline validation with zero errors (warnings OK)."""
    report = validate_archive(archive)
    assert report.is_valid, (
        f"Archive validation failed with {len(report.errors)} errors: "
        + "; ".join(e.message for e in report.errors)
    )


# ── Ontology Structure ─────────────────────────────────────────────


def test_ontology_has_seven_classes(archive):
    """Ontology defines exactly 7 OWL classes in bpkm namespace."""
    bpkm_classes = [
        s
        for s in archive.ontology.subjects(RDF.type, OWL.Class)
        if str(s).startswith(str(BPKM))
    ]
    assert len(bpkm_classes) == 7
    class_names = {str(c).split(":")[-1] for c in bpkm_classes}
    expected = {"Project", "Person", "Note", "Concept", "Task", "Milestone", "Event"}
    assert class_names == expected


def test_event_class_subclass_of_gist_event(archive):
    """bpkm:Event is rdfs:subClassOf gist:Event."""
    superclasses = list(archive.ontology.objects(BPKM.Event, RDFS.subClassOf))
    assert GIST.Event in superclasses, (
        f"bpkm:Event should be subClassOf gist:Event, got: {superclasses}"
    )


def test_event_properties_exist(archive):
    """Key Event-specific properties are defined in the ontology."""
    expected_datatype = [
        "eventStatus", "location", "timeZone", "allDay", "visibility",
        "showAs", "conferenceUrl", "recurrenceRule", "recurringEventId",
        "responseStatus", "reminderMinutes", "calendarName", "meetingNotes",
    ]
    expected_object = [
        "attendee", "organizer", "eventProject", "hasEvents",
        "generatedTask", "eventNote",
    ]
    for prop_name in expected_datatype:
        prop_uri = BPKM[prop_name]
        types = list(archive.ontology.objects(prop_uri, RDF.type))
        assert OWL.DatatypeProperty in types, (
            f"bpkm:{prop_name} should be owl:DatatypeProperty, got: {types}"
        )
    for prop_name in expected_object:
        prop_uri = BPKM[prop_name]
        types = list(archive.ontology.objects(prop_uri, RDF.type))
        assert OWL.ObjectProperty in types, (
            f"bpkm:{prop_name} should be owl:ObjectProperty, got: {types}"
        )


# ── Shapes Structure ───────────────────────────────────────────────


def test_shapes_has_seven_nodeshapes(archive):
    """Shapes file has 7 NodeShapes targeting the 7 OWL classes."""
    node_shapes = [
        s
        for s in archive.shapes.subjects(RDF.type, SH.NodeShape)
        if str(s).startswith(str(BPKM))
    ]
    assert len(node_shapes) == 7


def test_event_shape_targets_event(archive):
    """EventShape targets bpkm:Event."""
    targets = list(archive.shapes.objects(BPKM.EventShape, SH.targetClass))
    assert BPKM.Event in targets


def test_event_shape_has_five_groups(archive):
    """EventShape uses 5 property groups."""
    expected_groups = {
        BPKM.EventInfoGroup,
        BPKM.EventScheduleGroup,
        BPKM.EventAttendeesGroup,
        BPKM.EventSyncGroup,
        BPKM.EventMetadataGroup,
    }
    # Find all group nodes defined in the shapes graph
    actual_groups = set()
    for g in expected_groups:
        types = list(archive.shapes.objects(g, RDF.type))
        if SH.PropertyGroup in types:
            actual_groups.add(g)
    assert actual_groups == expected_groups, (
        f"Missing groups: {expected_groups - actual_groups}"
    )


def test_event_shape_enum_constraints(archive):
    """EventShape has enum constraints for eventStatus, visibility, showAs, responseStatus."""
    # Get all property shapes from EventShape
    prop_shapes = list(archive.shapes.objects(BPKM.EventShape, SH.property))

    enum_checks = {
        str(BPKM.eventStatus): {"confirmed", "tentative", "cancelled"},
        str(BPKM.visibility): {"public", "private", "confidential"},
        str(BPKM.showAs): {"free", "tentative", "busy", "out-of-office", "working-elsewhere"},
        str(BPKM.responseStatus): {"needs-action", "accepted", "declined", "tentative"},
    }

    for prop_shape in prop_shapes:
        paths = list(archive.shapes.objects(prop_shape, SH.path))
        if not paths:
            continue
        path_str = str(paths[0])
        if path_str in enum_checks:
            # Find sh:in list values
            in_lists = list(archive.shapes.objects(prop_shape, SH["in"]))
            assert len(in_lists) >= 1, f"Property {path_str} should have sh:in"
            # Collect all values from the RDF list
            values = set()
            from rdflib.collection import Collection
            for in_list in in_lists:
                coll = Collection(archive.shapes, in_list)
                values.update(str(v) for v in coll)
            expected = enum_checks[path_str]
            assert values == expected, (
                f"Enum mismatch for {path_str}: expected {expected}, got {values}"
            )


def test_show_as_includes_outlook_values(archive):
    """showAs enum includes out-of-office and working-elsewhere (Outlook values per D212)."""
    # This is already checked in test_event_shape_enum_constraints, but
    # explicit test per the must-haves checklist
    prop_shapes = list(archive.shapes.objects(BPKM.EventShape, SH.property))
    for prop_shape in prop_shapes:
        paths = list(archive.shapes.objects(prop_shape, SH.path))
        if paths and str(paths[0]) == str(BPKM.showAs):
            from rdflib.collection import Collection
            in_lists = list(archive.shapes.objects(prop_shape, SH["in"]))
            values = set()
            for in_list in in_lists:
                coll = Collection(archive.shapes, in_list)
                values.update(str(v) for v in coll)
            assert "out-of-office" in values
            assert "working-elsewhere" in values
            return
    pytest.fail("showAs property shape not found in EventShape")


# ── Views Structure ────────────────────────────────────────────────


def test_views_has_21_viewspecs(archive):
    """Views file has 21 ViewSpecs (7 types × 3 renderers)."""
    viewspecs = list(archive.views.subjects(RDF.type, SEMPKM.ViewSpec))
    assert len(viewspecs) == 21


def test_views_has_8_saved_queries(archive):
    """Views file has 8 SavedQueries including upcoming-events and past-events."""
    queries = list(archive.views.subjects(RDF.type, SEMPKM.SavedQuery))
    assert len(queries) == 8

    query_ids = {str(q) for q in queries}
    assert "urn:sempkm:model:basic-pkm:query:upcoming-events" in query_ids
    assert "urn:sempkm:model:basic-pkm:query:past-events" in query_ids


def test_event_viewspecs_exist(archive):
    """Three Event ViewSpecs exist: table, card, graph."""
    expected = {
        str(BPKM["view-event-table"]),
        str(BPKM["view-event-card"]),
        str(BPKM["view-event-graph"]),
    }
    viewspecs = {str(s) for s in archive.views.subjects(RDF.type, SEMPKM.ViewSpec)}
    assert expected.issubset(viewspecs), (
        f"Missing Event ViewSpecs: {expected - viewspecs}"
    )


# ── Seed Data ──────────────────────────────────────────────────────


def test_seed_has_four_event_instances(archive):
    """Seed graph contains exactly 4 Event instances."""
    events = list(archive.seed.subjects(RDF.type, BPKM.Event))
    assert len(events) == 4


def test_seed_event_types(archive):
    """Seed events cover: timed, all-day, recurring master, recurring exception."""
    standup = BPKM["seed-event-standup"]
    offsite = BPKM["seed-event-offsite"]
    review = BPKM["seed-event-review"]
    exception = BPKM["seed-event-review-exception"]

    # Timed event: has xsd:dateTime start, allDay=false
    start = list(archive.seed.objects(standup, SCHEMA.startDate))
    assert len(start) == 1
    assert start[0].datatype == XSD.dateTime

    all_day = list(archive.seed.objects(standup, BPKM.allDay))
    assert len(all_day) == 1
    assert all_day[0].toPython() is False

    # All-day event: has xsd:date start, allDay=true
    start = list(archive.seed.objects(offsite, SCHEMA.startDate))
    assert len(start) == 1
    assert start[0].datatype == XSD.date

    all_day = list(archive.seed.objects(offsite, BPKM.allDay))
    assert len(all_day) == 1
    assert all_day[0].toPython() is True

    # Recurring master: has recurrenceRule
    rrule = list(archive.seed.objects(review, BPKM.recurrenceRule))
    assert len(rrule) == 1
    assert "FREQ=WEEKLY" in str(rrule[0])

    # Recurring exception: has recurringEventId
    recurring_id = list(archive.seed.objects(exception, BPKM.recurringEventId))
    assert len(recurring_id) == 1


def test_seed_event_attendees(archive):
    """Seed events have attendee relationships to Person instances."""
    standup = BPKM["seed-event-standup"]
    attendees = list(archive.seed.objects(standup, BPKM.attendee))
    assert len(attendees) == 2
    assert BPKM["seed-person-alice"] in attendees
    assert BPKM["seed-person-bob"] in attendees


def test_seed_event_date_types_match_shapes(archive):
    """Seed data date types match SHACL shape constraints (K002).

    dcterms:created uses xsd:dateTime.
    schema:startDate uses xsd:dateTime for timed events and xsd:date for all-day.
    """
    standup = BPKM["seed-event-standup"]
    created = list(archive.seed.objects(standup, DCTERMS.created))
    assert len(created) == 1
    assert created[0].datatype == XSD.dateTime

    # Timed event: xsd:dateTime
    start = list(archive.seed.objects(standup, SCHEMA.startDate))
    assert start[0].datatype == XSD.dateTime

    # All-day event: xsd:date
    offsite = BPKM["seed-event-offsite"]
    start = list(archive.seed.objects(offsite, SCHEMA.startDate))
    assert start[0].datatype == XSD.date


# ── pyshacl Validation ─────────────────────────────────────────────


def test_pyshacl_zero_errors_on_events(archive):
    """pyshacl fires zero errors on the full archive including Event seed data.

    allow_warnings=True so the overdue task warning doesn't fail this test.
    """
    data_graph = archive.seed + archive.ontology
    shapes_graph = archive.shapes + archive.rules

    conforms, results_graph, results_text = pyshacl.validate(
        data_graph,
        shacl_graph=shapes_graph,
        advanced=True,
        allow_infos=True,
        allow_warnings=True,
    )

    assert conforms, (
        f"pyshacl validation failed with errors:\n{results_text}"
    )

    # Verify no sh:Violation results exist
    violations = list(
        results_graph.triples((None, SH.resultSeverity, SH.Violation))
    )
    assert len(violations) == 0, (
        f"Expected zero violations, got {len(violations)}:\n{results_text}"
    )
