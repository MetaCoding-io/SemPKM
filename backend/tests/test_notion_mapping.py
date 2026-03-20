"""Unit tests for Notion MappingConfig serialization round-trip.

Tests the to_dict() / from_dict() cycle for MappingConfig and its
component dataclasses (TypeMapping, PropertyMapping, RelationMapping)
across empty, partial, full, and edge-case configurations.
"""

import json

import pytest

from app.notion.models import (
    MappingConfig,
    PropertyMapping,
    RelationMapping,
    TypeMapping,
)


class TestMappingConfigEmpty:
    """Empty/default MappingConfig round-trip."""

    def test_empty_config_round_trip(self):
        config = MappingConfig()
        data = config.to_dict()
        restored = MappingConfig.from_dict(data)

        assert restored.version == 1
        assert restored.type_mappings == {}
        assert restored.property_mappings == {}
        assert restored.relation_mappings == {}
        assert restored.standalone_page_type_iri is None
        assert restored.standalone_page_type_label is None

    def test_empty_config_json_serializable(self):
        config = MappingConfig()
        serialized = json.dumps(config.to_dict())
        restored = MappingConfig.from_dict(json.loads(serialized))
        assert restored.version == 1


class TestMappingConfigFull:
    """Full MappingConfig with all fields populated."""

    def _make_full_config(self) -> MappingConfig:
        return MappingConfig(
            version=1,
            type_mappings={
                "Projects": TypeMapping(
                    target_type_iri="urn:example:Project",
                    target_type_label="Project",
                ),
                "People": TypeMapping(
                    target_type_iri="urn:example:Person",
                    target_type_label="Person",
                ),
                "Archive": None,  # explicitly skipped
            },
            property_mappings={
                "urn:example:Project": {
                    "Name": PropertyMapping(
                        target_property_iri="http://purl.org/dc/terms/title",
                        target_property_label="Title",
                        source="shacl",
                    ),
                    "Status": PropertyMapping(
                        target_property_iri="urn:example:status",
                        target_property_label="Status",
                        source="custom",
                    ),
                    "Notes": None,  # skipped column
                },
                "urn:example:Person": {
                    "Email": PropertyMapping(
                        target_property_iri="http://schema.org/email",
                        target_property_label="Email",
                        source="shacl",
                    ),
                },
            },
            relation_mappings={
                "Projects|Assignee": RelationMapping(
                    target_predicate_iri="urn:example:assignedTo",
                    target_predicate_label="Assigned To",
                    target_type_iri="urn:example:Person",
                    target_type_label="Person",
                ),
                "Projects|Department": None,  # skipped relation
            },
            standalone_page_type_iri="urn:example:Note",
            standalone_page_type_label="Note",
        )

    def test_full_config_round_trip(self):
        config = self._make_full_config()
        data = config.to_dict()
        restored = MappingConfig.from_dict(data)

        assert restored.version == 1
        assert len(restored.type_mappings) == 3
        assert restored.type_mappings["Projects"].target_type_iri == "urn:example:Project"
        assert restored.type_mappings["Projects"].target_type_label == "Project"
        assert restored.type_mappings["People"].target_type_iri == "urn:example:Person"
        assert restored.type_mappings["Archive"] is None

    def test_full_config_property_mappings_round_trip(self):
        config = self._make_full_config()
        data = config.to_dict()
        restored = MappingConfig.from_dict(data)

        proj_props = restored.property_mappings["urn:example:Project"]
        assert proj_props["Name"].target_property_iri == "http://purl.org/dc/terms/title"
        assert proj_props["Name"].source == "shacl"
        assert proj_props["Status"].source == "custom"
        assert proj_props["Notes"] is None

    def test_full_config_relation_mappings_round_trip(self):
        config = self._make_full_config()
        data = config.to_dict()
        restored = MappingConfig.from_dict(data)

        rm = restored.relation_mappings["Projects|Assignee"]
        assert rm.target_predicate_iri == "urn:example:assignedTo"
        assert rm.target_predicate_label == "Assigned To"
        assert rm.target_type_iri == "urn:example:Person"
        assert rm.target_type_label == "Person"
        assert restored.relation_mappings["Projects|Department"] is None

    def test_full_config_standalone_page_type_round_trip(self):
        config = self._make_full_config()
        data = config.to_dict()
        restored = MappingConfig.from_dict(data)

        assert restored.standalone_page_type_iri == "urn:example:Note"
        assert restored.standalone_page_type_label == "Note"

    def test_full_config_json_round_trip(self):
        """Verify JSON serialize → deserialize preserves all data."""
        config = self._make_full_config()
        serialized = json.dumps(config.to_dict(), indent=2)
        restored = MappingConfig.from_dict(json.loads(serialized))

        assert restored.to_dict() == config.to_dict()

    def test_version_preserved(self):
        config = MappingConfig(version=2)
        data = config.to_dict()
        restored = MappingConfig.from_dict(data)
        assert restored.version == 2


class TestMappingConfigPartial:
    """Partial configs with some mappings, some None entries."""

    def test_only_type_mappings(self):
        config = MappingConfig(
            type_mappings={
                "Tasks": TypeMapping(
                    target_type_iri="urn:example:Task",
                    target_type_label="Task",
                ),
            },
        )
        data = config.to_dict()
        restored = MappingConfig.from_dict(data)

        assert len(restored.type_mappings) == 1
        assert restored.property_mappings == {}
        assert restored.relation_mappings == {}
        assert restored.standalone_page_type_iri is None

    def test_multiple_dbs_same_type(self):
        """Two databases mapped to the same RDF type."""
        config = MappingConfig(
            type_mappings={
                "Active Tasks": TypeMapping(
                    target_type_iri="urn:example:Task",
                    target_type_label="Task",
                ),
                "Archived Tasks": TypeMapping(
                    target_type_iri="urn:example:Task",
                    target_type_label="Task",
                ),
            },
        )
        data = config.to_dict()
        restored = MappingConfig.from_dict(data)

        assert len(restored.type_mappings) == 2
        assert (
            restored.type_mappings["Active Tasks"].target_type_iri
            == restored.type_mappings["Archived Tasks"].target_type_iri
        )

    def test_only_relation_mappings(self):
        config = MappingConfig(
            relation_mappings={
                "Tasks|Owner": RelationMapping(
                    target_predicate_iri="urn:example:ownedBy",
                    target_predicate_label="Owned By",
                    target_type_iri="urn:example:Person",
                    target_type_label="Person",
                ),
            },
        )
        data = config.to_dict()
        restored = MappingConfig.from_dict(data)

        assert len(restored.relation_mappings) == 1
        assert restored.type_mappings == {}

    def test_all_none_type_mappings(self):
        """All databases explicitly skipped."""
        config = MappingConfig(
            type_mappings={
                "Db1": None,
                "Db2": None,
            },
        )
        data = config.to_dict()
        restored = MappingConfig.from_dict(data)

        assert restored.type_mappings["Db1"] is None
        assert restored.type_mappings["Db2"] is None

    def test_standalone_page_type_only(self):
        config = MappingConfig(
            standalone_page_type_iri="urn:example:Page",
            standalone_page_type_label="Page",
        )
        data = config.to_dict()
        restored = MappingConfig.from_dict(data)

        assert restored.standalone_page_type_iri == "urn:example:Page"
        assert restored.standalone_page_type_label == "Page"
        assert restored.type_mappings == {}


class TestIndividualDataclasses:
    """Edge cases for individual mapping dataclass fields."""

    def test_type_mapping_fields(self):
        tm = TypeMapping(
            target_type_iri="urn:example:Thing",
            target_type_label="Thing",
        )
        assert tm.target_type_iri == "urn:example:Thing"
        assert tm.target_type_label == "Thing"

    def test_property_mapping_custom_source(self):
        pm = PropertyMapping(
            target_property_iri="urn:custom:field",
            target_property_label="Custom Field",
            source="custom",
        )
        assert pm.source == "custom"

    def test_relation_mapping_all_fields(self):
        rm = RelationMapping(
            target_predicate_iri="urn:example:relatesTo",
            target_predicate_label="Relates To",
            target_type_iri="urn:example:Other",
            target_type_label="Other",
        )
        assert rm.target_predicate_iri == "urn:example:relatesTo"
        assert rm.target_type_iri == "urn:example:Other"

    def test_from_dict_missing_optional_fields(self):
        """from_dict with minimal data — missing optional keys default correctly."""
        data = {"version": 1}
        config = MappingConfig.from_dict(data)

        assert config.type_mappings == {}
        assert config.property_mappings == {}
        assert config.relation_mappings == {}
        assert config.standalone_page_type_iri is None

    def test_from_dict_default_version(self):
        """from_dict without version key defaults to 1."""
        data = {}
        config = MappingConfig.from_dict(data)
        assert config.version == 1
