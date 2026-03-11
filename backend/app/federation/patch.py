"""RDF Patch serialization and deserialization.

Converts EventStore Operations to RDF Patch format (A/D lines with quad
graph components) and parses RDF Patch text back into structured tuples.

RDF Patch format (per https://afs.github.io/rdf-patch/):
    H id <urn:uuid:...>        # Header: patch identifier
    TX .                       # Transaction start
    D <s> <p> <o> <g> .       # Delete quad
    A <s> <p> <o> <g> .       # Add quad
    TC .                       # Transaction commit
"""

from uuid import uuid4

from rdflib import URIRef, Literal, BNode

from app.events.store import Operation


def _nt(term) -> str:
    """Serialize an rdflib term to N-Triples format.

    - URIRef -> <uri>
    - Literal -> "value"^^<datatype> or "value"@lang or "value"
    - BNode -> skolemized to <urn:skolem:{bnode_id}>
    """
    if isinstance(term, URIRef):
        return f"<{term}>"
    elif isinstance(term, Literal):
        escaped = (
            str(term)
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )
        if term.language:
            return f'"{escaped}"@{term.language}'
        elif term.datatype:
            return f'"{escaped}"^^<{term.datatype}>'
        else:
            return f'"{escaped}"'
    elif isinstance(term, BNode):
        # Skolemize blank nodes to stable URIs for cross-instance sync
        return f"<urn:skolem:{term}>"
    else:
        raise ValueError(f"Unsupported RDF term type for N-Triples: {type(term)}")


def serialize_patch(operations: list[Operation], graph_iri: str) -> str:
    """Serialize Operations to RDF Patch text format.

    Converts materialize_deletes to D lines and materialize_inserts to A lines,
    each with the graph IRI as the fourth quad component.

    Args:
        operations: List of Operation dataclasses from EventStore.
        graph_iri: The target named graph IRI (e.g. urn:sempkm:shared:abc).

    Returns:
        RDF Patch text with H, TX, D, A, TC lines.
    """
    lines: list[str] = []
    lines.append(f"H id <urn:uuid:{uuid4()}>")
    lines.append("TX .")

    for op in operations:
        for s, p, o in op.materialize_deletes:
            lines.append(f"D {_nt(s)} {_nt(p)} {_nt(o)} <{graph_iri}> .")
        for s, p, o in op.materialize_inserts:
            lines.append(f"A {_nt(s)} {_nt(p)} {_nt(o)} <{graph_iri}> .")

    lines.append("TC .")
    return "\n".join(lines) + "\n"


def deserialize_patch(text: str) -> list[tuple[str, URIRef, URIRef, URIRef | Literal, URIRef]]:
    """Parse RDF Patch text back into structured quad tuples.

    Skips H, TX, TC lines. Parses A and D lines into
    (action, subject, predicate, object, graph) tuples.

    Args:
        text: RDF Patch text string.

    Returns:
        List of (action, s, p, o, g) tuples where action is 'A' or 'D'.
    """
    result: list[tuple[str, URIRef, URIRef, URIRef | Literal, URIRef]] = []

    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("H ") or line.startswith("TX") or line.startswith("TC"):
            continue

        if line.startswith("A ") or line.startswith("D "):
            action = line[0]
            rest = line[2:].rstrip(" .")
            terms = _parse_nquad_terms(rest)
            if len(terms) == 4:
                result.append((action, terms[0], terms[1], terms[2], terms[3]))

    return result


def _parse_nquad_terms(text: str) -> list[URIRef | Literal]:
    """Parse N-Quads terms from a line of space-separated N-Triples values.

    Handles:
        <uri> -> URIRef
        "value"^^<datatype> -> Literal with datatype
        "value"@lang -> Literal with language
        "value" -> plain Literal
    """
    terms: list[URIRef | Literal] = []
    i = 0

    while i < len(text):
        # Skip whitespace
        if text[i] == " ":
            i += 1
            continue

        if text[i] == "<":
            # URI reference
            end = text.index(">", i)
            uri = text[i + 1 : end]
            terms.append(URIRef(uri))
            i = end + 1

        elif text[i] == '"':
            # Literal value
            i += 1  # skip opening quote
            value_chars: list[str] = []
            while i < len(text) and text[i] != '"':
                if text[i] == "\\" and i + 1 < len(text):
                    next_char = text[i + 1]
                    if next_char == "n":
                        value_chars.append("\n")
                    elif next_char == "r":
                        value_chars.append("\r")
                    elif next_char == "t":
                        value_chars.append("\t")
                    elif next_char == "\\":
                        value_chars.append("\\")
                    elif next_char == '"':
                        value_chars.append('"')
                    else:
                        value_chars.append(next_char)
                    i += 2
                else:
                    value_chars.append(text[i])
                    i += 1

            i += 1  # skip closing quote
            value = "".join(value_chars)

            if i < len(text) and text[i] == "^" and i + 1 < len(text) and text[i + 1] == "^":
                # Typed literal: ^^<datatype>
                i += 2  # skip ^^
                if i < len(text) and text[i] == "<":
                    dt_end = text.index(">", i)
                    datatype = URIRef(text[i + 1 : dt_end])
                    terms.append(Literal(value, datatype=datatype))
                    i = dt_end + 1
                else:
                    terms.append(Literal(value))
            elif i < len(text) and text[i] == "@":
                # Language-tagged literal: @lang
                i += 1  # skip @
                lang_start = i
                while i < len(text) and text[i] != " ":
                    i += 1
                lang = text[lang_start:i]
                terms.append(Literal(value, lang=lang))
            else:
                terms.append(Literal(value))
        else:
            i += 1

    return terms
