"""PPV model ontology expansion validation tests.

Validates all M047/S02 artifacts:
  - PillarScore and GuidingPrinciples classes in ontology
  - 22 new ontology properties
  - PillarScoreShape and GuidingPrinciplesShape in SHACL shapes
  - Score constraint (sh:minInclusive 1, sh:maxInclusive 10)
  - New reflection PropertyGroups on review shapes
  - 4 new ViewSpecs in views file
  - PillarScoreDateDenormRule in rules file (with schema prefix)
  - Manifest icon entries for new types
  - Combined graph parse success (all files together)
"""

from pathlib import Path

import pytest
import yaml
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

# ── Constants ───────────────────────────────────────────────────────

PPV = Namespace("urn:sempkm:model:ppv:")
SH = Namespace("http://www.w3.org/ns/shacl#")
SEMPKM = Namespace("urn:sempkm:vocab:")
DCTERMS = Namespace("http://purl.org/dc/terms/")
SCHEMA = Namespace("https://schema.org/")

MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "ppv"

ONTOLOGY_FILE = MODEL_DIR / "ontology" / "ppv.jsonld"
SHAPES_FILE = MODEL_DIR / "shapes" / "ppv.jsonld"
VIEWS_FILE = MODEL_DIR / "views" / "ppv.jsonld"
RULES_FILE = MODEL_DIR / "rules" / "ppv.ttl"
MANIFEST_FILE = MODEL_DIR / "manifest.yaml"


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def ontology_graph():
    g = Graph()
    g.parse(str(ONTOLOGY_FILE), format="json-ld")
    return g


@pytest.fixture(scope="module")
def shapes_graph():
    g = Graph()
    g.parse(str(SHAPES_FILE), format="json-ld")
    return g


@pytest.fixture(scope="module")
def views_graph():
    g = Graph()
    g.parse(str(VIEWS_FILE), format="json-ld")
    return g


@pytest.fixture(scope="module")
def rules_graph():
    g = Graph()
    g.parse(str(RULES_FILE), format="turtle")
    return g


@pytest.fixture(scope="module")
def manifest():
    with open(MANIFEST_FILE) as f:
        return yaml.safe_load(f)


# ── Ontology: New Classes ───────────────────────────────────────────

class TestOntologyClasses:
    """Verify PillarScore and GuidingPrinciples exist as owl:Class."""

    def test_pillarscore_class_exists(self, ontology_graph):
        assert (PPV.PillarScore, RDF.type, OWL.Class) in ontology_graph

    def test_guidingprinciples_class_exists(self, ontology_graph):
        assert (PPV.GuidingPrinciples, RDF.type, OWL.Class) in ontology_graph

    def test_pillarscore_has_label(self, ontology_graph):
        labels = list(ontology_graph.objects(PPV.PillarScore, RDFS.label))
        assert len(labels) >= 1
        assert "Pillar Score" in [str(l) for l in labels]

    def test_guidingprinciples_has_label(self, ontology_graph):
        labels = list(ontology_graph.objects(PPV.GuidingPrinciples, RDFS.label))
        assert len(labels) >= 1
        assert "Guiding Principles" in [str(l) for l in labels]


# ── Ontology: New Properties ────────────────────────────────────────

NEW_PROPERTIES = [
    "score",
    "weeklyReview",
    "values",
    "purpose",
    "meaning",
    "manifestation",
    "foundationalStatement",
    "guidingWord",
    "wentWell",
    "needsAttention",
    "wins",
    "challenges",
    "supportingPriorities",
    "biggestWins",
    "biggestChallenges",
    "focusAreas",
    "habitsToAdjust",
    "accomplishments",
    "disappointments",
    "whatWorked",
    "whatDidntWork",
    "howToImprove",
    "annualVisionNotes",
    "intentionWord",
    "yearTheme",
]


class TestOntologyProperties:
    """Verify all new properties exist in the ontology."""

    @pytest.mark.parametrize("prop_name", NEW_PROPERTIES)
    def test_property_exists(self, ontology_graph, prop_name):
        prop_iri = PPV[prop_name]
        # Property should have at least one triple as subject
        triples = list(ontology_graph.triples((prop_iri, None, None)))
        assert len(triples) > 0, f"Property ppv:{prop_name} not found in ontology"

    @pytest.mark.parametrize("prop_name", NEW_PROPERTIES)
    def test_property_has_type(self, ontology_graph, prop_name):
        prop_iri = PPV[prop_name]
        types = list(ontology_graph.objects(prop_iri, RDF.type))
        assert len(types) >= 1, f"Property ppv:{prop_name} has no rdf:type"


# ── Shapes: New NodeShapes ──────────────────────────────────────────

class TestShapesNodeShapes:
    """Verify PillarScoreShape and GuidingPrinciplesShape exist with correct targets."""

    def test_pillarscore_shape_exists(self, shapes_graph):
        assert (PPV.PillarScoreShape, RDF.type, SH.NodeShape) in shapes_graph

    def test_pillarscore_shape_targets_class(self, shapes_graph):
        targets = list(shapes_graph.objects(PPV.PillarScoreShape, SH.targetClass))
        assert PPV.PillarScore in targets

    def test_guidingprinciples_shape_exists(self, shapes_graph):
        assert (PPV.GuidingPrinciplesShape, RDF.type, SH.NodeShape) in shapes_graph

    def test_guidingprinciples_shape_targets_class(self, shapes_graph):
        targets = list(shapes_graph.objects(PPV.GuidingPrinciplesShape, SH.targetClass))
        assert PPV.GuidingPrinciples in targets


# ── Shapes: Score Constraints ───────────────────────────────────────

class TestScoreConstraints:
    """Verify PillarScoreShape has score property with min/max 1-10."""

    def test_score_min_inclusive(self, shapes_graph):
        """Find the property shape for ppv:score and check sh:minInclusive = 1."""
        found = False
        for prop_shape in shapes_graph.objects(PPV.PillarScoreShape, SH.property):
            paths = list(shapes_graph.objects(prop_shape, SH.path))
            if PPV.score in paths:
                min_vals = list(shapes_graph.objects(prop_shape, SH.minInclusive))
                assert len(min_vals) >= 1, "ppv:score has no sh:minInclusive"
                assert any(int(v) == 1 for v in min_vals), \
                    f"ppv:score sh:minInclusive should be 1, got {min_vals}"
                found = True
                break
        assert found, "No property shape for ppv:score found in PillarScoreShape"

    def test_score_max_inclusive(self, shapes_graph):
        """Find the property shape for ppv:score and check sh:maxInclusive = 10."""
        found = False
        for prop_shape in shapes_graph.objects(PPV.PillarScoreShape, SH.property):
            paths = list(shapes_graph.objects(prop_shape, SH.path))
            if PPV.score in paths:
                max_vals = list(shapes_graph.objects(prop_shape, SH.maxInclusive))
                assert len(max_vals) >= 1, "ppv:score has no sh:maxInclusive"
                assert any(int(v) == 10 for v in max_vals), \
                    f"ppv:score sh:maxInclusive should be 10, got {max_vals}"
                found = True
                break
        assert found, "No property shape for ppv:score found in PillarScoreShape"


# ── Shapes: PropertyGroups ──────────────────────────────────────────

EXPECTED_GROUPS = [
    "WeeklyReviewReflectionGroup",
    "QuarterlyReviewReflectionGroup",
    "YearlyReviewReflectionGroup",
]


class TestPropertyGroups:
    """Verify new reflection PropertyGroups exist."""

    @pytest.mark.parametrize("group_name", EXPECTED_GROUPS)
    def test_group_exists(self, shapes_graph, group_name):
        group_iri = PPV[group_name]
        assert (group_iri, RDF.type, SH.PropertyGroup) in shapes_graph, \
            f"PropertyGroup ppv:{group_name} not found"

    @pytest.mark.parametrize("group_name", EXPECTED_GROUPS)
    def test_group_has_label(self, shapes_graph, group_name):
        group_iri = PPV[group_name]
        labels = list(shapes_graph.objects(group_iri, RDFS.label))
        assert len(labels) >= 1, f"PropertyGroup ppv:{group_name} has no label"


# ── Views: New ViewSpecs ────────────────────────────────────────────

NEW_VIEWSPECS = [
    ("ppv:view-pillarscore-table", "Pillar Scores", "table"),
    ("ppv:view-action-kanban", "Action Kanban", "kanban"),
    ("ppv:view-project-kanban", "Project Kanban", "kanban"),
    ("ppv:view-action-by-context", "Actions by Context", "table"),
]


class TestViewSpecs:
    """Verify 4 new ViewSpecs exist with correct properties."""

    @pytest.mark.parametrize("view_id,label,renderer", NEW_VIEWSPECS)
    def test_viewspec_exists(self, views_graph, view_id, label, renderer):
        view_iri = URIRef(view_id.replace("ppv:", "urn:sempkm:model:ppv:"))
        assert (view_iri, RDF.type, SEMPKM.ViewSpec) in views_graph, \
            f"ViewSpec {view_id} not found"

    @pytest.mark.parametrize("view_id,label,renderer", NEW_VIEWSPECS)
    def test_viewspec_label(self, views_graph, view_id, label, renderer):
        view_iri = URIRef(view_id.replace("ppv:", "urn:sempkm:model:ppv:"))
        labels = [str(l) for l in views_graph.objects(view_iri, RDFS.label)]
        assert label in labels, f"ViewSpec {view_id} label should be '{label}', got {labels}"

    @pytest.mark.parametrize("view_id,label,renderer", NEW_VIEWSPECS)
    def test_viewspec_renderer(self, views_graph, view_id, label, renderer):
        view_iri = URIRef(view_id.replace("ppv:", "urn:sempkm:model:ppv:"))
        renderers = [str(r) for r in views_graph.objects(view_iri, SEMPKM.rendererType)]
        assert renderer in renderers, \
            f"ViewSpec {view_id} renderer should be '{renderer}', got {renderers}"

    @pytest.mark.parametrize("view_id,label,renderer", NEW_VIEWSPECS)
    def test_viewspec_has_sparql(self, views_graph, view_id, label, renderer):
        view_iri = URIRef(view_id.replace("ppv:", "urn:sempkm:model:ppv:"))
        queries = list(views_graph.objects(view_iri, SEMPKM.sparqlQuery))
        assert len(queries) >= 1, f"ViewSpec {view_id} has no sparqlQuery"

    def test_total_viewspec_count(self, views_graph):
        """Should now have 23 ViewSpecs total (19 original + 4 new)."""
        count = len(list(views_graph.triples((None, RDF.type, SEMPKM.ViewSpec))))
        assert count >= 23, f"Expected at least 23 ViewSpecs, got {count}"

    def test_pillarscore_table_has_columns(self, views_graph):
        view_iri = PPV["view-pillarscore-table"]
        columns = list(views_graph.objects(view_iri, SEMPKM.columns))
        assert len(columns) >= 1, "Pillar Scores table should have columns"

    def test_action_by_context_has_columns(self, views_graph):
        view_iri = PPV["view-action-by-context"]
        columns = list(views_graph.objects(view_iri, SEMPKM.columns))
        assert len(columns) >= 1, "Actions by Context table should have columns"


# ── Rules: PillarScoreDateDenormRule ────────────────────────────────

class TestRules:
    """Verify PillarScoreDateDenormRule and schema prefix in PrefixDeclarations."""

    def test_denorm_rule_exists(self, rules_graph):
        assert (PPV.PillarScoreDateDenormRule, RDF.type, SH.NodeShape) in rules_graph

    def test_denorm_rule_targets_pillarscore(self, rules_graph):
        targets = list(rules_graph.objects(PPV.PillarScoreDateDenormRule, SH.targetClass))
        assert PPV.PillarScore in targets

    def test_denorm_rule_has_sparql_rule(self, rules_graph):
        rules = list(rules_graph.objects(PPV.PillarScoreDateDenormRule, SH.rule))
        assert len(rules) >= 1, "PillarScoreDateDenormRule has no sh:rule"
        # Verify it's a SPARQLRule
        rule_node = rules[0]
        types = list(rules_graph.objects(rule_node, RDF.type))
        assert SH.SPARQLRule in types

    def test_denorm_rule_has_construct(self, rules_graph):
        rules = list(rules_graph.objects(PPV.PillarScoreDateDenormRule, SH.rule))
        assert len(rules) >= 1
        rule_node = rules[0]
        constructs = list(rules_graph.objects(rule_node, SH.construct))
        assert len(constructs) >= 1, "SPARQLRule has no sh:construct"
        construct_text = str(constructs[0])
        assert "schema:startDate" in construct_text
        assert "weeklyReview" in construct_text

    def test_schema_prefix_in_declarations(self, rules_graph):
        """The PrefixDeclarations should include a schema prefix."""
        decls = list(rules_graph.objects(PPV.PrefixDeclarations, SH.declare))
        schema_found = False
        for decl in decls:
            prefix = list(rules_graph.objects(decl, SH.prefix))
            ns = list(rules_graph.objects(decl, SH.namespace))
            if prefix and str(prefix[0]) == "schema":
                assert ns and "schema.org" in str(ns[0])
                schema_found = True
        assert schema_found, "schema prefix not found in PrefixDeclarations"

    def test_rules_triple_count(self, rules_graph):
        """Should have more triples than the original 46 (pre-expansion)."""
        assert len(rules_graph) > 50, f"Expected >50 triples, got {len(rules_graph)}"


# ── Manifest ────────────────────────────────────────────────────────

class TestManifest:
    """Verify manifest.yaml contains icon entries for new types."""

    def test_manifest_parses(self, manifest):
        assert manifest is not None

    def test_manifest_has_icons(self, manifest):
        assert "icons" in manifest

    def test_pillarscore_icon(self, manifest):
        icons = manifest["icons"]
        type_ids = [icon["type"] for icon in icons]
        assert "ppv:PillarScore" in type_ids, \
            f"ppv:PillarScore not in manifest icons: {type_ids}"

    def test_guidingprinciples_icon(self, manifest):
        icons = manifest["icons"]
        type_ids = [icon["type"] for icon in icons]
        assert "ppv:GuidingPrinciples" in type_ids, \
            f"ppv:GuidingPrinciples not in manifest icons: {type_ids}"


# ── Combined Graph Parse ────────────────────────────────────────────

class TestCombinedParse:
    """Load all model files into a single graph to verify no cross-file parse errors."""

    def test_combined_graph_loads(self):
        combined = Graph()
        combined.parse(str(ONTOLOGY_FILE), format="json-ld")
        combined.parse(str(SHAPES_FILE), format="json-ld")
        combined.parse(str(VIEWS_FILE), format="json-ld")
        combined.parse(str(RULES_FILE), format="turtle")
        # Should have substantial triples from all files
        assert len(combined) > 1000, \
            f"Combined graph unexpectedly small: {len(combined)} triples"

    def test_cross_reference_pillarscore_class_to_shape(self):
        """Shape's sh:targetClass should match the ontology's owl:Class."""
        onto = Graph()
        onto.parse(str(ONTOLOGY_FILE), format="json-ld")
        shapes = Graph()
        shapes.parse(str(SHAPES_FILE), format="json-ld")

        # Ontology declares the class
        assert (PPV.PillarScore, RDF.type, OWL.Class) in onto
        # Shape targets the same class
        targets = list(shapes.objects(PPV.PillarScoreShape, SH.targetClass))
        assert PPV.PillarScore in targets

    def test_cross_reference_guidingprinciples_class_to_shape(self):
        onto = Graph()
        onto.parse(str(ONTOLOGY_FILE), format="json-ld")
        shapes = Graph()
        shapes.parse(str(SHAPES_FILE), format="json-ld")

        assert (PPV.GuidingPrinciples, RDF.type, OWL.Class) in onto
        targets = list(shapes.objects(PPV.GuidingPrinciplesShape, SH.targetClass))
        assert PPV.GuidingPrinciples in targets

    def test_viewspec_targets_match_ontology_classes(self):
        """All ViewSpec targetClass values should be defined as owl:Class in the ontology."""
        onto = Graph()
        onto.parse(str(ONTOLOGY_FILE), format="json-ld")
        views = Graph()
        views.parse(str(VIEWS_FILE), format="json-ld")

        classes = set(onto.subjects(RDF.type, OWL.Class))
        for view in views.subjects(RDF.type, SEMPKM.ViewSpec):
            for target in views.objects(view, SEMPKM.targetClass):
                assert target in classes, \
                    f"ViewSpec {view} targets {target} which is not an owl:Class"
