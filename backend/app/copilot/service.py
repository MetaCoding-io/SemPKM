"""Core CopilotService — schema context building, SPARQL generation,
validation, self-correction loop, and query execution/formatting.

This is a pure service class with no HTTP dependencies. The router (T02)
calls its methods and streams results over SSE.
"""

import logging
import re
from typing import Callable, Awaitable

from app.config import settings
from app.copilot.schemas import QueryExecutionResult, SparqlGenerationResult
from app.services.labels import LabelService
from app.services.prefixes import PrefixRegistry
from app.services.shapes import ShapesService
from app.sparql.client import inject_prefixes, scope_to_current_graph
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

# Per D324: max 2 self-correction retries
MAX_RETRIES = 2

# Per D326: ~4 chars per token, default budget 4000 tokens
DEFAULT_TOKEN_BUDGET = 4000
CHARS_PER_TOKEN = 4

# SPARQL keywords that indicate read-only queries (allowed)
_READ_KEYWORDS = re.compile(
    r"^\s*(SELECT|ASK|CONSTRUCT|DESCRIBE)\b", re.IGNORECASE | re.MULTILINE
)

# SPARQL keywords that indicate mutation queries (rejected)
_MUTATION_KEYWORDS = re.compile(
    r"\b(INSERT|DELETE|DROP|CLEAR|LOAD|CREATE|COPY|MOVE|ADD)\b", re.IGNORECASE
)

# Extract predicate IRIs from triple patterns (simplified: ?s <predIRI> ?o or prefix:local)
_PREDICATE_IRI_RE = re.compile(
    r"""
    (?:^|[\s{;.])          # preceded by whitespace, brace, semicolon, or dot
    (?:
        <([^>]+)>           # group 1: full IRI in angle brackets
        |
        (\w+:\w+)           # group 2: prefixed name like dcterms:title
    )
    \s+                     # followed by whitespace (object position follows)
    """,
    re.VERBOSE | re.MULTILINE,
)


class CopilotService:
    """Orchestrates natural-language-to-SPARQL for the copilot chat.

    Dependencies are injected at construction time so the service is
    testable without HTTP infrastructure.
    """

    def __init__(
        self,
        triplestore_client: TriplestoreClient,
        shapes_service: ShapesService,
        label_service: LabelService,
        prefix_registry: PrefixRegistry,
    ) -> None:
        self._client = triplestore_client
        self._shapes = shapes_service
        self._labels = label_service
        self._prefixes = prefix_registry

    # ------------------------------------------------------------------
    # Schema context
    # ------------------------------------------------------------------

    async def build_schema_context(
        self, token_budget: int = DEFAULT_TOKEN_BUDGET
    ) -> str:
        """Build a text description of the installed knowledge-graph schema.

        Queries ShapesService for all NodeShapes and serialises them as
        human-readable text suitable for inclusion in an LLM system prompt.
        Includes a prefix table for reference.

        Uses character-based token estimation (~4 chars/token per D326)
        and truncates at *token_budget* tokens.
        """
        char_budget = token_budget * CHARS_PER_TOKEN

        node_shapes = await self._shapes.get_node_shapes()
        all_prefixes = self._prefixes.get_all_prefixes()

        parts: list[str] = []

        # Prefix table
        parts.append("## Prefix Table\n")
        for prefix, ns in sorted(all_prefixes.items()):
            parts.append(f"  {prefix}: <{ns}>")
        parts.append("")

        # Type descriptions
        parts.append("## Knowledge Graph Types\n")
        for shape in node_shapes:
            type_block = f"Type: {shape.label} ({shape.target_class})\n"
            if shape.properties:
                type_block += "  Properties:\n"
                for prop in shape.properties:
                    dt_info = ""
                    if prop.datatype:
                        dt_info = f", datatype: {self._prefixes.compact(prop.datatype)}"
                    elif prop.target_class:
                        dt_info = f", object: {self._prefixes.compact(prop.target_class)}"
                    constraint_info = ""
                    if prop.in_values:
                        constraint_info = f", values: [{', '.join(prop.in_values)}]"
                    type_block += (
                        f"    - {prop.name} ({self._prefixes.compact(prop.path)}"
                        f"{dt_info}{constraint_info})\n"
                    )
            parts.append(type_block)

        text = "\n".join(parts)

        # Truncate at character budget
        if len(text) > char_budget:
            text = text[:char_budget] + "\n... (schema truncated to fit token budget)"

        estimated_tokens = len(text) // CHARS_PER_TOKEN
        logger.info(
            "copilot.schema_context.built: types=%d, estimated_tokens=%d",
            len(node_shapes),
            estimated_tokens,
        )
        return text

    # ------------------------------------------------------------------
    # SPARQL validation
    # ------------------------------------------------------------------

    async def validate_query(self, query: str) -> tuple[bool, str | None]:
        """Validate a generated SPARQL query for safety and correctness.

        Checks:
        1. Must contain a read-only keyword (SELECT, ASK, CONSTRUCT, DESCRIBE).
        2. Must NOT contain mutation keywords (INSERT, DELETE, DROP, etc.).
        3. Warns (non-blocking) on unknown predicates.

        Returns (True, None) if valid, (False, error_message) if invalid.
        A predicate warning is logged but does not reject the query.
        """
        stripped = query.strip()

        # 1. Reject mutation keywords first (specific error message)
        mutation_match = _MUTATION_KEYWORDS.search(stripped)
        if mutation_match:
            keyword = mutation_match.group(1).upper()
            msg = f"Query contains forbidden mutation keyword: {keyword}"
            logger.warning("copilot.sparql.validated: valid=false, error=%s", msg)
            return False, msg

        # 2. Read-only keyword required
        if not _READ_KEYWORDS.search(stripped):
            msg = "Query does not contain a valid read keyword (SELECT, ASK, CONSTRUCT, DESCRIBE)"
            logger.warning("copilot.sparql.validated: valid=false, error=%s", msg)
            return False, msg

        # 3. Check predicates (non-blocking)
        await self._check_predicates(stripped)

        logger.info("copilot.sparql.validated: valid=true")
        return True, None

    async def _check_predicates(self, query: str) -> None:
        """Log warnings for unknown predicates in the query.

        Extracts predicate IRIs from triple patterns and checks them
        against known predicates from the shapes service. Unknown
        predicates are logged but do not block execution.
        """
        predicate_iris: list[str] = []

        for match in _PREDICATE_IRI_RE.finditer(query):
            full_iri = match.group(1)
            prefixed = match.group(2)
            if full_iri:
                # Skip RDF/RDFS/OWL system predicates
                if any(
                    full_iri.startswith(ns)
                    for ns in (
                        "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                        "http://www.w3.org/2000/01/rdf-schema#",
                        "http://www.w3.org/2002/07/owl#",
                    )
                ):
                    continue
                predicate_iris.append(full_iri)
            elif prefixed:
                expanded = self._prefixes.expand(prefixed)
                if expanded:
                    predicate_iris.append(expanded)

        if not predicate_iris:
            return

        known_labels = await self._shapes.get_labels_for_predicates(predicate_iris)
        unknown = [p for p in predicate_iris if p not in known_labels]
        if unknown:
            logger.warning(
                "copilot.sparql.unknown_predicates: %s",
                ", ".join(unknown),
            )

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------

    async def execute_and_format(self, query: str) -> QueryExecutionResult:
        """Execute a validated SPARQL query and format results as prose.

        Pipeline: inject_prefixes → scope_to_current_graph → client.query().
        Extracts bindings, collects object IRIs matching base_namespace,
        resolves labels, and formats as prose with ``[[iri|label]]`` markers.
        """
        prepared = inject_prefixes(query)
        prepared = scope_to_current_graph(prepared)

        result = await self._client.query(prepared)
        bindings = result.get("results", {}).get("bindings", [])

        logger.info(
            "copilot.sparql.executed: bindings=%d",
            len(bindings),
        )

        # Collect object IRIs (those matching the instance base_namespace)
        base_ns = settings.base_namespace
        object_iris: list[str] = []
        seen_iris: set[str] = set()

        for binding in bindings:
            for var_name, val in binding.items():
                if val.get("type") == "uri":
                    iri = val["value"]
                    if iri.startswith(base_ns) and iri not in seen_iris:
                        object_iris.append(iri)
                        seen_iris.add(iri)

        # Resolve labels for found object IRIs
        labels: dict[str, str] = {}
        if object_iris:
            labels = await self._labels.resolve_batch(object_iris)

        # Build prose from bindings
        prose = self._format_bindings_as_prose(bindings, labels, base_ns)

        logger.info(
            "copilot.sparql.formatted: iris=%d",
            len(object_iris),
        )

        return QueryExecutionResult(
            bindings=bindings,
            prose=prose,
            object_iris=object_iris,
        )

    @staticmethod
    def _format_bindings_as_prose(
        bindings: list[dict],
        labels: dict[str, str],
        base_ns: str,
    ) -> str:
        """Format SPARQL bindings as human-readable prose with IRI markers.

        Object IRIs matching base_namespace are rendered as ``[[iri|label]]``
        for the frontend to turn into clickable pill links.
        """
        if not bindings:
            return "The query returned no results."

        var_names = list(bindings[0].keys())

        # Single-value result (e.g., COUNT)
        if len(bindings) == 1 and len(var_names) == 1:
            val = bindings[0][var_names[0]]
            return f"Result: {val.get('value', '')}"

        # Tabular results — format as enumerated list
        lines: list[str] = []
        for i, binding in enumerate(bindings, 1):
            parts: list[str] = []
            for var in var_names:
                if var not in binding:
                    continue
                val = binding[var]
                raw_value = val.get("value", "")
                if val.get("type") == "uri" and raw_value.startswith(base_ns):
                    label = labels.get(raw_value, raw_value.rsplit("/", 1)[-1])
                    parts.append(f"[[{raw_value}|{label}]]")
                else:
                    parts.append(raw_value)
            lines.append(f"{i}. {' — '.join(parts)}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # SPARQL generation with self-correction
    # ------------------------------------------------------------------

    async def generate_sparql(
        self,
        user_message: str,
        schema_context: str,
        llm_call: Callable[[list[dict]], Awaitable[str]],
    ) -> SparqlGenerationResult:
        """Generate SPARQL from a natural-language question.

        Builds a system prompt with schema context, sends to LLM via
        the provided callable, extracts SPARQL from the response,
        validates it, and retries up to MAX_RETRIES times on failure
        with error feedback appended to the conversation.

        Args:
            user_message: The user's natural-language question.
            schema_context: Pre-built schema context text.
            llm_call: Async callable that takes ``[{role, content}, ...]``
                      messages and returns the assistant's response text.
                      This indirection keeps the service testable.

        Returns:
            SparqlGenerationResult with the query, or an error.
        """
        system_prompt = _build_system_prompt(schema_context)
        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        last_error: str | None = None

        for attempt in range(1 + MAX_RETRIES):
            try:
                logger.info(
                    "copilot.sparql.generating: attempt=%d/%d",
                    attempt + 1,
                    1 + MAX_RETRIES,
                )
                response_text = await llm_call(messages)
            except Exception as exc:
                last_error = f"LLM call failed: {exc}"
                logger.error("copilot.sparql.failed: %s", last_error)
                return SparqlGenerationResult(
                    query=None, error=last_error, retries=attempt
                )

            query = _extract_sparql_from_response(response_text)
            if not query:
                last_error = "Could not extract SPARQL query from LLM response"
                logger.warning("copilot.sparql.failed: %s", last_error)
                if attempt < MAX_RETRIES:
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append({
                        "role": "user",
                        "content": (
                            f"Error: {last_error}. "
                            "Please respond with a valid SPARQL query in a ```sparql code block."
                        ),
                    })
                    logger.info(
                        "copilot.sparql.retry: attempt=%d, error=%s",
                        attempt + 1,
                        last_error,
                    )
                    continue
                return SparqlGenerationResult(
                    query=None, error=last_error, retries=attempt
                )

            valid, validation_error = await self.validate_query(query)
            if valid:
                logger.info("copilot.sparql.generated: query_len=%d", len(query))
                return SparqlGenerationResult(
                    query=query, error=None, retries=attempt
                )

            # Validation failed — feed error back for self-correction
            last_error = validation_error
            if attempt < MAX_RETRIES:
                messages.append({"role": "assistant", "content": response_text})
                messages.append({
                    "role": "user",
                    "content": (
                        f"The generated SPARQL query is invalid: {validation_error}. "
                        "Please fix it and respond with a corrected SPARQL query."
                    ),
                })
                logger.info(
                    "copilot.sparql.retry: attempt=%d, error=%s",
                    attempt + 1,
                    last_error,
                )

        return SparqlGenerationResult(
            query=None, error=last_error, retries=MAX_RETRIES
        )


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _extract_sparql_from_response(text: str) -> str | None:
    """Extract a SPARQL query from LLM response text.

    Looks for fenced code blocks (```sparql or ```sql) first,
    falls back to heuristic detection of lines starting with
    SPARQL keywords (PREFIX, SELECT, ASK, CONSTRUCT, DESCRIBE).

    Returns the extracted query string, or None if no SPARQL found.
    """
    # 1. Try fenced code blocks: ```sparql ... ``` or ```sql ... ```
    code_block_re = re.compile(
        r"```(?:sparql|sql)\s*\n(.*?)```", re.DOTALL | re.IGNORECASE
    )
    match = code_block_re.search(text)
    if match:
        query = match.group(1).strip()
        if query:
            return query

    # 2. Try generic code block: ``` ... ```
    generic_block_re = re.compile(r"```\s*\n(.*?)```", re.DOTALL)
    match = generic_block_re.search(text)
    if match:
        candidate = match.group(1).strip()
        if _READ_KEYWORDS.search(candidate):
            return candidate

    # 3. Heuristic: collect consecutive lines starting with SPARQL keywords
    lines = text.strip().splitlines()
    sparql_lines: list[str] = []
    in_query = False

    for line in lines:
        stripped = line.strip()
        if not in_query:
            if re.match(
                r"^(PREFIX|SELECT|ASK|CONSTRUCT|DESCRIBE)\b",
                stripped,
                re.IGNORECASE,
            ):
                in_query = True
                sparql_lines.append(line)
        else:
            # Continue collecting until we hit an empty line or prose
            if stripped == "" and sparql_lines:
                # Allow one empty line inside a query (between PREFIX and SELECT)
                sparql_lines.append(line)
            elif stripped and not re.match(r"^[A-Z][a-z]", stripped):
                # Doesn't look like English prose — keep it
                sparql_lines.append(line)
            else:
                break

    if sparql_lines:
        query = "\n".join(sparql_lines).strip()
        if _READ_KEYWORDS.search(query):
            return query

    return None


def _build_system_prompt(schema_context: str, graph_context: str | None = None) -> str:
    """Build the full LLM system prompt for SPARQL generation.

    Includes the role description, schema context, optional graph context
    for the active object, and instructions for output formatting.
    """
    graph_section = ""
    if graph_context:
        graph_section = f"\n{graph_context}\n"

    return f"""You are a SPARQL assistant for a personal semantic knowledge graph (SemPKM).

Your job is to translate natural-language questions into SPARQL queries that run against the user's knowledge graph.

{schema_context}
{graph_section}
## Instructions

1. Generate ONLY read-only SPARQL queries (SELECT, ASK, CONSTRUCT, DESCRIBE). Never use INSERT, DELETE, DROP, or any mutation keyword.
2. Output the SPARQL query inside a ```sparql code block.
3. Use the prefixes from the Prefix Table above. The data namespace for user objects is <{settings.base_namespace}>.
4. When your answer references specific objects from the knowledge graph, wrap each object reference as [[iri|label]] so the UI can render them as clickable links. For example: [[https://example.org/data/abc123|My Project]].
5. If you're unsure about the exact property path, use the schema above — prefer the documented property paths over guessing.
6. Keep queries simple and efficient. Use COUNT, GROUP BY, ORDER BY, and LIMIT as appropriate.
7. Always query from the current state graph (the system adds FROM clauses automatically — do not add them yourself).
"""
