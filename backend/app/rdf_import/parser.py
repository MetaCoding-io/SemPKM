"""RDF parser — format detection, parsing, subject extraction, and blank node skolemization."""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from uuid import uuid4

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, FOAF, RDF, RDFS, SKOS
from rdflib.util import guess_format

from app.rdf_import.models import RdfParseResult, SubjectInfo

logger = logging.getLogger(__name__)

SCHEMA = Namespace("http://schema.org/")

# Label resolution precedence — first match wins.
_LABEL_PREDICATES: list[URIRef] = [
    DCTERMS.title,
    RDFS.label,
    SKOS.prefLabel,
    SCHEMA.name,
    FOAF.name,
]

# Prefixes that mark an IRI as "vocabulary" — these are never user subjects.
_VOCAB_PREFIXES: tuple[str, ...] = (
    "http://www.w3.org/",
    "http://purl.org/dc/",
    "http://xmlns.com/foaf/",
    "http://schema.org/",
    "http://www.w3.org/2002/07/owl#",
)

# N-Triples first-line pattern: <IRI> <IRI> at minimum.
_NT_PATTERN = re.compile(r"^<[^>]+>\s+<[^>]+>")


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def detect_format(
    content: str,
    filename: str | None = None,
    format_override: str | None = None,
) -> str:
    """Detect the RDF serialization format of *content*.

    Resolution order:
    1. ``format_override`` — caller knows best.
    2. ``filename`` extension via ``rdflib.util.guess_format``.
    3. Content heuristic (JSON-LD, Turtle, N-Triples).
    4. Fallback to ``turtle``.
    """
    if format_override:
        return format_override

    if filename:
        guessed = guess_format(filename)
        if guessed:
            return guessed

    stripped = content.lstrip()

    # JSON-LD: starts with { or [
    if stripped.startswith("{") or stripped.startswith("["):
        return "json-ld"

    # Turtle: @prefix or @base directives
    stripped_lower = stripped.lower()
    if stripped_lower.startswith("@prefix") or stripped_lower.startswith("@base"):
        return "turtle"

    # Turtle: PREFIX (SPARQL-style Turtle shorthand)
    if stripped_lower.startswith("prefix "):
        return "turtle"

    # N-Triples: <IRI> <IRI> on the first non-blank line
    first_line = stripped.split("\n", 1)[0]
    if _NT_PATTERN.match(first_line):
        return "nt"

    # Fallback
    return "turtle"


# ---------------------------------------------------------------------------
# RDF parsing
# ---------------------------------------------------------------------------

def parse_rdf(
    content: str,
    format: str | None = None,
    filename: str | None = None,
    format_override: str | None = None,
) -> RdfParseResult:
    """Parse *content* as RDF, returning structured subjects and any errors.

    If *format* is ``None``, :func:`detect_format` is called automatically.
    Parse failures are captured — never raised — and returned in
    ``RdfParseResult.errors``.
    """
    fmt = format or detect_format(content, filename=filename, format_override=format_override)

    try:
        g = Graph()
        g.parse(data=content, format=fmt)
    except Exception as exc:
        logger.warning("RDF parse error (format=%s): %s", fmt, exc)
        return RdfParseResult(
            subjects=[],
            total_triples=0,
            format_used=fmt,
            errors=[str(exc)],
            raw_graph=None,
        )

    total = len(g)
    subjects = extract_subjects(g)

    logger.info(
        "Parsed RDF (%s): %d triples, %d subjects",
        fmt,
        total,
        len(subjects),
    )

    return RdfParseResult(
        subjects=subjects,
        total_triples=total,
        format_used=fmt,
        errors=[],
        raw_graph=g,
    )


# ---------------------------------------------------------------------------
# Subject extraction
# ---------------------------------------------------------------------------

def _resolve_label(graph: Graph, subject: URIRef | BNode) -> str | None:
    """Resolve a human-readable label for *subject* using the precedence chain."""
    for pred in _LABEL_PREDICATES:
        for obj in graph.objects(subject, pred):
            val = str(obj)
            if val:
                return val
    # QName fallback for URIRefs
    if isinstance(subject, URIRef):
        s = str(subject)
        for sep in ("#", "/"):
            if sep in s:
                local = s.rsplit(sep, 1)[-1]
                if local:
                    return local
    return None


def _is_vocab_iri(iri: str) -> bool:
    """Return True if *iri* belongs to a well-known vocabulary namespace."""
    return any(iri.startswith(prefix) for prefix in _VOCAB_PREFIXES)


def extract_subjects(graph: Graph) -> list[SubjectInfo]:
    """Extract per-subject metadata from *graph*.

    Groups all triples by subject, computes types, labels, and property
    counts.  Applies a top-level subject heuristic: subjects that appear
    only in the subject position (never as an object) are considered
    top-level.  If the heuristic yields nothing, all subjects are returned.
    """
    # Group triples by subject
    by_subject: dict[URIRef | BNode, list[tuple]] = defaultdict(list)
    for s, p, o in graph:
        by_subject[s].append((s, p, o))

    # Collect all IRIs that appear in the object position
    # (excluding rdf:type targets and vocab IRIs — those aren't "parent" subjects).
    object_iris: set[str] = set()
    for _s, p, o in graph:
        if p == RDF.type:
            continue
        if isinstance(o, (URIRef, BNode)):
            o_str = str(o)
            if not _is_vocab_iri(o_str):
                object_iris.add(o_str)

    infos: list[SubjectInfo] = []
    for subj, triples in by_subject.items():
        types = [str(o) for _, p, o in triples if p == RDF.type]
        label = _resolve_label(graph, subj)
        # Property count = distinct predicates (excluding rdf:type which is metadata)
        predicates = {str(p) for _, p, _ in triples}
        prop_count = len(predicates)
        is_bnode = isinstance(subj, BNode)

        infos.append(
            SubjectInfo(
                iri=str(subj),
                types=types,
                label=label,
                property_count=prop_count,
                is_blank_node=is_bnode,
                triples=triples,
            )
        )

    # Top-level heuristic: subjects NOT referenced as objects.
    top_level = [si for si in infos if si.iri not in object_iris]
    if top_level:
        return top_level
    # Heuristic produced nothing — return all.
    return infos


# ---------------------------------------------------------------------------
# Blank node skolemization
# ---------------------------------------------------------------------------

def skolemize_bnodes(
    graph: Graph,
) -> tuple[Graph, dict[BNode, URIRef]]:
    """Replace all blank nodes in *graph* with deterministic ``urn:sempkm:import:*`` URIs.

    Returns the new graph and the BNode→URIRef mapping used.  The mapping
    is consistent: the same BNode appearing as both subject and object maps
    to the same URI.  Namespace bindings are preserved.
    """
    bnode_map: dict[BNode, URIRef] = {}

    def _resolve(term: URIRef | BNode | Literal) -> URIRef | BNode | Literal:
        if isinstance(term, BNode):
            if term not in bnode_map:
                bnode_map[term] = URIRef(f"urn:sempkm:import:{uuid4()}")
            return bnode_map[term]
        return term

    new_graph = Graph()

    # Preserve namespace bindings
    for prefix, ns in graph.namespaces():
        new_graph.bind(prefix, ns)

    for s, p, o in graph:
        new_graph.add((_resolve(s), p, _resolve(o)))

    logger.info(
        "Skolemized %d blank nodes in %d triples",
        len(bnode_map),
        len(new_graph),
    )

    return new_graph, bnode_map
