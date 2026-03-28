"""GraphContextService — 1-hop neighborhood query and token-budgeted serialization.

Queries the triplestore for an IRI's immediate graph neighborhood (types,
literal properties, outbound object edges, inbound edges) and serializes it
as human-readable text suitable for LLM system prompt injection.

Runtime signals:
  - copilot.context.neighborhood (iri, triple_count, estimated_tokens)
  - copilot.context.truncated (iri, budget, actual_chars)
"""

import logging
from typing import Any

from app.services.labels import LabelService
from app.services.prefixes import PrefixRegistry
from app.triplestore.client import TriplestoreClient
from app.rdf.namespaces import CURRENT_GRAPH

logger = logging.getLogger(__name__)

# ~4 chars per token (same constant as service.py D326)
CHARS_PER_TOKEN = 4
DEFAULT_TOKEN_BUDGET = 2000


class GraphContextService:
    """Queries a 1-hop graph neighborhood for any IRI and serializes it
    as human-readable text within a configurable token budget.

    Dependencies follow the same injection pattern as CopilotService.
    """

    def __init__(
        self,
        triplestore_client: TriplestoreClient,
        label_service: LabelService,
        prefix_registry: PrefixRegistry,
    ) -> None:
        self._client = triplestore_client
        self._labels = label_service
        self._prefixes = prefix_registry

    # ------------------------------------------------------------------
    # Neighborhood query
    # ------------------------------------------------------------------

    async def get_neighborhood(self, iri: str) -> dict[str, Any]:
        """Query the 1-hop graph neighborhood of *iri* from urn:sempkm:current.

        Returns a structured dict:
          {
            "iri": str,
            "types": [str, ...],
            "properties": {predicate_iri: [value, ...]},
            "outbound": [(predicate_iri, target_iri), ...],
            "inbound": [(source_iri, predicate_iri), ...],
          }
        """
        sparql = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?p ?o ?inSubject ?inPredicate WHERE {{
          {{
            # Types
            GRAPH <{CURRENT_GRAPH}> {{
              <{iri}> rdf:type ?o .
            }}
            BIND(rdf:type AS ?p)
          }}
          UNION
          {{
            # Literal properties
            GRAPH <{CURRENT_GRAPH}> {{
              <{iri}> ?p ?o .
              FILTER(isLiteral(?o))
              FILTER(?p != rdf:type)
            }}
          }}
          UNION
          {{
            # Outbound object edges
            GRAPH <{CURRENT_GRAPH}> {{
              <{iri}> ?p ?o .
              FILTER(isIRI(?o))
              FILTER(?p != rdf:type)
            }}
          }}
          UNION
          {{
            # Inbound edges
            GRAPH <{CURRENT_GRAPH}> {{
              ?inSubject ?inPredicate <{iri}> .
              FILTER(isIRI(?inSubject))
              FILTER(?inPredicate != rdf:type)
            }}
          }}
        }}
        """

        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])

        types: list[str] = []
        properties: dict[str, list[str]] = {}
        outbound: list[tuple[str, str]] = []
        inbound: list[tuple[str, str]] = []

        for b in bindings:
            # Inbound edges: have inSubject + inPredicate
            if "inSubject" in b and "inPredicate" in b:
                src = b["inSubject"]["value"]
                pred = b["inPredicate"]["value"]
                inbound.append((src, pred))
                continue

            p = b.get("p", {}).get("value", "")
            o_node = b.get("o", {})
            o_val = o_node.get("value", "")

            if p == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type":
                types.append(o_val)
            elif o_node.get("type") == "literal":
                properties.setdefault(p, []).append(o_val)
            elif o_node.get("type") == "uri":
                outbound.append((p, o_val))

        triple_count = len(types) + sum(len(v) for v in properties.values()) + len(outbound) + len(inbound)

        logger.info(
            "copilot.context.neighborhood: iri=%s, triple_count=%d, types=%d, props=%d, outbound=%d, inbound=%d",
            iri,
            triple_count,
            len(types),
            sum(len(v) for v in properties.values()),
            len(outbound),
            len(inbound),
        )

        return {
            "iri": iri,
            "types": types,
            "properties": properties,
            "outbound": outbound,
            "inbound": inbound,
        }

    # ------------------------------------------------------------------
    # Serialization with token budget
    # ------------------------------------------------------------------

    async def serialize_context(
        self, neighborhood: dict[str, Any], token_budget: int = DEFAULT_TOKEN_BUDGET
    ) -> str:
        """Serialize *neighborhood* as human-readable text within *token_budget*.

        Resolves all IRIs to labels and compacts predicates. Truncation
        priority: own literal properties first, then outbound edges, then
        inbound edges.

        Returns an empty string if the neighborhood has no meaningful data.
        """
        iri = neighborhood["iri"]
        types = neighborhood.get("types", [])
        properties = neighborhood.get("properties", {})
        outbound = neighborhood.get("outbound", [])
        inbound = neighborhood.get("inbound", [])

        # Nothing to serialize
        if not types and not properties and not outbound and not inbound:
            logger.info("copilot.context.neighborhood: iri=%s, empty=true", iri)
            return ""

        char_budget = token_budget * CHARS_PER_TOKEN

        # Collect all IRIs that need label resolution
        iris_to_resolve: list[str] = [iri]
        iris_to_resolve.extend(types)
        for pred in properties:
            iris_to_resolve.append(pred)
        for pred, target in outbound:
            iris_to_resolve.extend([pred, target])
        for src, pred in inbound:
            iris_to_resolve.extend([src, pred])

        # Deduplicate while preserving resolution
        unique_iris = list(set(iris_to_resolve))
        labels = await self._labels.resolve_batch(unique_iris) if unique_iris else {}

        def _label(i: str) -> str:
            return labels.get(i, self._prefixes.compact(i))

        def _compact(i: str) -> str:
            return self._prefixes.compact(i)

        # Build sections with priority ordering
        sections: list[str] = []

        # Header (always included — very small)
        type_labels = ", ".join(f"{_label(t)} ({_compact(t)})" for t in types) if types else "Unknown type"
        header = f"## Current Context\nYou are looking at: {_label(iri)} ({type_labels})"
        sections.append(header)

        # Properties section (highest priority for truncation budget)
        if properties:
            prop_lines: list[str] = ["\nProperties:"]
            for pred_iri, values in properties.items():
                pred_name = _label(pred_iri)
                for val in values:
                    prop_lines.append(f"- {pred_name}: {val}")
            sections.append("\n".join(prop_lines))

        # Outbound edges (second priority)
        if outbound:
            out_lines: list[str] = ["\nOutbound relations:"]
            for pred_iri, target_iri in outbound:
                pred_name = _label(pred_iri)
                target_name = _label(target_iri)
                out_lines.append(f"- {pred_name} → {target_name}")
            sections.append("\n".join(out_lines))

        # Inbound edges (lowest priority — truncated first)
        if inbound:
            in_lines: list[str] = ["\nInbound relations:"]
            for src_iri, pred_iri in inbound:
                src_name = _label(src_iri)
                pred_name = _label(pred_iri)
                in_lines.append(f"- {src_name} → {pred_name} → this")
            sections.append("\n".join(in_lines))

        # Assemble with priority truncation: drop from the end (inbound first)
        text = sections[0]  # header always included
        for section in sections[1:]:
            candidate = text + "\n" + section
            if len(candidate) <= char_budget:
                text = candidate
            else:
                # Try to fit partial section
                remaining = char_budget - len(text) - 1  # 1 for newline
                if remaining > 40:
                    # Include what fits from this section
                    lines = section.split("\n")
                    partial = ""
                    for line in lines:
                        if len(partial) + len(line) + 1 <= remaining:
                            partial += ("\n" if partial else "") + line
                        else:
                            break
                    if partial:
                        text = text + "\n" + partial + "\n... (truncated to fit token budget)"
                logger.info(
                    "copilot.context.truncated: iri=%s, budget=%d, actual_chars=%d",
                    iri,
                    char_budget,
                    len(text),
                )
                break

        estimated_tokens = len(text) // CHARS_PER_TOKEN
        logger.info(
            "copilot.context.neighborhood: iri=%s, estimated_tokens=%d",
            iri,
            estimated_tokens,
        )

        return text
