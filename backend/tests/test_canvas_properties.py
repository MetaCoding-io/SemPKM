"""Unit tests for canvas properties endpoint — build_property_list helper.

Pure-function tests: no Docker, no triplestore, no mocking needed.
Tests the property-building logic extracted from GET /api/canvas/properties.
"""

import pytest

from app.canvas.router import (
    RDF_TYPE,
    SEMPKM_BODY,
    _is_valid_iri,
    _local_name,
    build_property_list,
)
from app.services.shapes import NodeShapeForm, PropertyShape


# ---- Helpers ----

def make_binding(pred: str, value: str, obj_type: str = "literal") -> dict:
    """Create a SPARQL binding dict for ?p ?o."""
    return {
        "p": {"type": "uri", "value": pred},
        "o": {"type": obj_type, "value": value},
    }


def make_form(target_class: str, properties: list[PropertyShape]) -> NodeShapeForm:
    """Create a minimal NodeShapeForm."""
    return NodeShapeForm(
        shape_iri=f"urn:shapes:{target_class}",
        target_class=target_class,
        label=target_class.rsplit("/", 1)[-1],
        properties=properties,
    )


def make_prop(
    path: str,
    name: str,
    order: float = 0.0,
    datatype: str | None = None,
) -> PropertyShape:
    """Create a minimal PropertyShape."""
    return PropertyShape(path=path, name=name, order=order, datatype=datatype)


# ---- Tests: happy path ----

class TestHappyPath:
    """Typed object with SHACL form → property list with names from form."""

    def test_shacl_properties_returned_with_names(self):
        """Properties from the SHACL form use their sh:name labels."""
        form = make_form(
            "urn:type:Note",
            [
                make_prop("http://purl.org/dc/terms/title", "Title", order=1),
                make_prop("http://purl.org/dc/terms/creator", "Creator", order=2),
            ],
        )
        bindings = [
            make_binding(RDF_TYPE, "urn:type:Note", "uri"),
            make_binding("http://purl.org/dc/terms/title", "My Note"),
            make_binding("http://purl.org/dc/terms/creator", "http://example.org/alice", "uri"),
        ]
        labels = {"http://example.org/alice": "Alice"}

        result = build_property_list(bindings, [], form, labels)

        assert len(result) == 2
        assert result[0]["name"] == "Title"
        assert result[0]["path"] == "http://purl.org/dc/terms/title"
        assert result[0]["values"] == [{"value": "My Note"}]
        assert result[0]["source"] == "current"

        assert result[1]["name"] == "Creator"
        assert result[1]["values"] == [
            {"value": "http://example.org/alice", "ref_label": "Alice"}
        ]

    def test_properties_only_included_when_values_exist(self):
        """SHACL properties without matching values are excluded."""
        form = make_form(
            "urn:type:Note",
            [
                make_prop("http://purl.org/dc/terms/title", "Title", order=1),
                make_prop("http://purl.org/dc/terms/subject", "Subject", order=2),
            ],
        )
        bindings = [
            make_binding(RDF_TYPE, "urn:type:Note", "uri"),
            make_binding("http://purl.org/dc/terms/title", "My Note"),
        ]

        result = build_property_list(bindings, [], form, {})

        assert len(result) == 1
        assert result[0]["name"] == "Title"


# ---- Tests: no SHACL form ----

class TestNoShaclForm:
    """Untyped object → properties with local-name labels."""

    def test_local_name_labels_when_no_form(self):
        """Without a SHACL form, property names come from IRI local names."""
        bindings = [
            make_binding("http://purl.org/dc/terms/title", "My Object"),
            make_binding("http://xmlns.com/foaf/0.1/name", "Bob"),
        ]

        result = build_property_list(bindings, [], None, {})

        assert len(result) == 2
        names = {p["name"] for p in result}
        assert "title" in names
        assert "name" in names

    def test_fragment_based_local_name(self):
        """IRIs with # fragments use the fragment as local name."""
        bindings = [
            make_binding("http://www.w3.org/2000/01/rdf-schema#label", "Test"),
        ]
        result = build_property_list(bindings, [], None, {})
        assert result[0]["name"] == "label"


# ---- Tests: body exclusion ----

class TestBodyExclusion:
    """Body properties excluded from output."""

    def test_sempkm_body_excluded(self):
        """urn:sempkm:body is never in the output."""
        bindings = [
            make_binding(SEMPKM_BODY, "Some markdown body text"),
            make_binding("http://purl.org/dc/terms/title", "My Note"),
        ]
        result = build_property_list(bindings, [], None, {})

        assert len(result) == 1
        assert result[0]["name"] == "title"

    def test_shacl_body_property_excluded(self):
        """A SHACL property named 'Body' (case-insensitive) is excluded."""
        form = make_form(
            "urn:type:Note",
            [
                make_prop("urn:sempkm:model:basic-pkm:body", "Body", order=0),
                make_prop("http://purl.org/dc/terms/title", "Title", order=1),
            ],
        )
        bindings = [
            make_binding(RDF_TYPE, "urn:type:Note", "uri"),
            make_binding("urn:sempkm:model:basic-pkm:body", "Some body"),
            make_binding("http://purl.org/dc/terms/title", "My Note"),
        ]

        result = build_property_list(bindings, [], form, {})

        assert len(result) == 1
        assert result[0]["name"] == "Title"

    def test_shacl_body_case_insensitive(self):
        """Body exclusion is case-insensitive (body, BODY, Body all excluded)."""
        form = make_form(
            "urn:type:Note",
            [
                make_prop("urn:model:body", "BODY", order=0),
                make_prop("http://purl.org/dc/terms/title", "Title", order=1),
            ],
        )
        bindings = [
            make_binding(RDF_TYPE, "urn:type:Note", "uri"),
            make_binding("urn:model:body", "Content"),
            make_binding("http://purl.org/dc/terms/title", "My Note"),
        ]

        result = build_property_list(bindings, [], form, {})
        assert len(result) == 1
        assert result[0]["name"] == "Title"


# ---- Tests: multi-value properties ----

class TestMultiValue:
    """Property with multiple values returns array."""

    def test_multi_value_array(self):
        """Multiple values for the same predicate are collected into values array."""
        bindings = [
            make_binding("http://purl.org/dc/terms/subject", "Topic A"),
            make_binding("http://purl.org/dc/terms/subject", "Topic B"),
            make_binding("http://purl.org/dc/terms/subject", "Topic C"),
        ]

        result = build_property_list(bindings, [], None, {})

        assert len(result) == 1
        assert result[0]["name"] == "subject"
        assert len(result[0]["values"]) == 3
        vals = [v["value"] for v in result[0]["values"]]
        assert vals == ["Topic A", "Topic B", "Topic C"]


# ---- Tests: inferred properties ----

class TestInferredProperties:
    """Inferred properties tagged and deduplicated."""

    def test_inferred_tagged_with_source(self):
        """Properties from the inferred graph have source='inferred'."""
        inferred = [
            make_binding("http://example.org/inferred-prop", "Inferred Value"),
        ]

        result = build_property_list([], inferred, None, {})

        assert len(result) == 1
        assert result[0]["source"] == "inferred"
        assert result[0]["name"] == "inferred-prop"

    def test_inferred_deduplicated_against_current(self):
        """Inferred values that exist in current graph are excluded."""
        bindings = [
            make_binding("http://example.org/prop", "Same Value"),
        ]
        inferred = [
            make_binding("http://example.org/prop", "Same Value"),
            make_binding("http://example.org/prop", "Extra Inferred"),
        ]

        result = build_property_list(bindings, inferred, None, {})

        # Current property
        current_props = [p for p in result if p["source"] == "current"]
        assert len(current_props) == 1
        assert current_props[0]["values"] == [{"value": "Same Value"}]

        # Inferred: only the non-duplicate value
        inferred_props = [p for p in result if p["source"] == "inferred"]
        assert len(inferred_props) == 1
        assert inferred_props[0]["values"] == [{"value": "Extra Inferred"}]

    def test_inferred_rdf_type_excluded(self):
        """rdf:type in the inferred graph is excluded."""
        inferred = [
            make_binding(RDF_TYPE, "urn:type:InferredType", "uri"),
            make_binding("http://example.org/prop", "Value"),
        ]

        result = build_property_list([], inferred, None, {})
        assert len(result) == 1
        assert result[0]["name"] == "prop"


# ---- Tests: reference labels ----

class TestReferenceLabels:
    """IRI values include resolved ref_label."""

    def test_uri_values_get_ref_label(self):
        """URI-type values include ref_label from the labels dict."""
        bindings = [
            make_binding("http://example.org/relates-to", "http://example.org/other", "uri"),
        ]
        labels = {"http://example.org/other": "Other Object"}

        result = build_property_list(bindings, [], None, labels)

        assert len(result) == 1
        assert result[0]["values"] == [
            {"value": "http://example.org/other", "ref_label": "Other Object"}
        ]

    def test_literal_values_no_ref_label(self):
        """Literal-type values do NOT get ref_label even if IRI matches."""
        bindings = [
            make_binding("http://example.org/label", "http://example.org/other"),
        ]
        labels = {"http://example.org/other": "Other Object"}

        result = build_property_list(bindings, [], None, labels)

        assert len(result) == 1
        # Literal, not URI — no ref_label
        assert result[0]["values"] == [{"value": "http://example.org/other"}]

    def test_uri_without_resolved_label_has_no_ref_label_key(self):
        """URI values without a resolved label don't get an empty ref_label."""
        bindings = [
            make_binding("http://example.org/relates-to", "http://example.org/unknown", "uri"),
        ]

        result = build_property_list(bindings, [], None, {})

        assert len(result) == 1
        assert result[0]["values"] == [{"value": "http://example.org/unknown"}]
        assert "ref_label" not in result[0]["values"][0]


# ---- Tests: IRI validation ----

class TestIriValidation:
    """Invalid IRI returns 400 (tests _is_valid_iri directly)."""

    def test_valid_http_iri(self):
        assert _is_valid_iri("http://example.org/foo") is True

    def test_valid_urn(self):
        assert _is_valid_iri("urn:sempkm:12345") is True

    def test_empty_string(self):
        assert _is_valid_iri("") is False

    def test_no_scheme(self):
        assert _is_valid_iri("example.org/foo") is False

    def test_angle_brackets_rejected(self):
        assert _is_valid_iri("<http://example.org/foo>") is False

    def test_spaces_rejected(self):
        assert _is_valid_iri("http://example.org/foo bar") is False


# ---- Tests: empty result ----

class TestEmptyResult:
    """Non-existent IRI returns empty properties."""

    def test_empty_bindings_return_empty_properties(self):
        """No bindings → empty properties list."""
        result = build_property_list([], [], None, {})
        assert result == []

    def test_only_type_and_body_return_empty(self):
        """If an object has only rdf:type and body, properties list is empty."""
        bindings = [
            make_binding(RDF_TYPE, "urn:type:Note", "uri"),
            make_binding(SEMPKM_BODY, "Some body text"),
        ]
        result = build_property_list(bindings, [], None, {})
        assert result == []


# ---- Tests: local name helper ----

class TestLocalName:
    """Unit tests for _local_name."""

    def test_fragment(self):
        assert _local_name("http://www.w3.org/2000/01/rdf-schema#label") == "label"

    def test_path(self):
        assert _local_name("http://purl.org/dc/terms/title") == "title"

    def test_no_separator(self):
        assert _local_name("urn:sempkm:body") == "urn:sempkm:body"


# ---- Tests: mixed SHACL + unmatched ----

class TestMixedShaclAndUnmatched:
    """Form matches some predicates; remaining appear as unmatched."""

    def test_unmatched_predicates_appended_after_form(self):
        """Predicates not in the SHACL form still appear with local-name labels."""
        form = make_form(
            "urn:type:Note",
            [
                make_prop("http://purl.org/dc/terms/title", "Title", order=1),
            ],
        )
        bindings = [
            make_binding(RDF_TYPE, "urn:type:Note", "uri"),
            make_binding("http://purl.org/dc/terms/title", "My Note"),
            make_binding("http://example.org/custom-field", "Custom Value"),
        ]

        result = build_property_list(bindings, [], form, {})

        assert len(result) == 2
        assert result[0]["name"] == "Title"  # From SHACL form
        assert result[1]["name"] == "custom-field"  # Unmatched, local name
        assert result[1]["source"] == "current"
