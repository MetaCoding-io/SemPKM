"""AI router: LLM streaming proxy, status, and AI insight endpoints.

Provides /api/llm/stream (SSE proxy for OpenAI-compatible chat completions),
/api/llm/status (feature-gating endpoint), /api/ai/detect-claims
(structured claim extraction from page text), /api/ai/match-claims
(claim-to-graph matching with contradiction/corroboration indicators),
/api/ai/suggest-relationships (graph-aware relationship suggestions),
and /api/ai/summarize (personalized page summary via LLM).

All endpoints accept dual auth: session cookie + Bearer token via
``get_current_user_or_api``.
"""

import json
import logging
import re
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user_or_api
from app.auth.models import User
from app.db.session import get_db_session
from app.services.llm import LLMConfigService
from app.services.search import SearchService
from app.sparql.builder import sparql_escape_string

logger = logging.getLogger(__name__)

ai_router = APIRouter(prefix="/api", tags=["ai"])


@ai_router.post("/llm/stream")
async def llm_stream(
    request: Request,
    user: User = Depends(get_current_user_or_api),
    db: AsyncSession = Depends(get_db_session),
):
    """SSE streaming proxy for LLM chat completions.

    Receives JSON body: {"messages": [...], "model": "optional-override"}
    Fetches the encrypted API key from InstanceConfig, then proxies the
    streaming /v1/chat/completions response as text/event-stream.

    Accepts both session cookies and Bearer tokens (dual-auth).
    """
    svc = LLMConfigService()
    config = await svc.get_config(db)
    base_url = config["api_base_url"].rstrip("/") if config["api_base_url"] else ""

    if not base_url:
        logger.debug("LLM stream requested but not configured, user=%s", user.email)

        async def error_stream():
            yield 'data: {"error": "LLM not configured"}\n\n'
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    body = await request.json()
    messages = body.get("messages", [])
    model = body.get("model") or config["default_model"]

    logger.debug("LLM stream request: user=%s, model=%s", user.email, model)

    api_key = await svc.get_decrypted_api_key(db)

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {"model": model, "messages": messages, "stream": True}

    async def event_stream():
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            yield f"{line}\n\n"
        except Exception as e:
            logger.warning("LLM proxy error: %s", str(e), exc_info=True)
            yield f'data: {{"error": "{str(e)[:100]}"}}\n\n'
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@ai_router.get("/llm/status")
async def llm_status(
    user: User = Depends(get_current_user_or_api),
    db: AsyncSession = Depends(get_db_session),
):
    """Return LLM availability and provider info for feature gating.

    Returns {"available": bool, "provider": string|null} where provider
    is the hostname extracted from the configured API base URL.
    """
    svc = LLMConfigService()
    config = await svc.get_config(db)
    base_url = config["api_base_url"].strip() if config["api_base_url"] else ""

    if not base_url:
        logger.debug("LLM status check: not configured, user=%s", user.email)
        return JSONResponse({"available": False, "provider": None})

    # Extract provider hostname from base URL (e.g. "api.openai.com")
    try:
        provider = urlparse(base_url).hostname
    except Exception:
        provider = None

    logger.debug("LLM status check: available=True, provider=%s, user=%s", provider, user.email)
    return JSONResponse({"available": True, "provider": provider})


# ---------------------------------------------------------------------------
# Claim detection models
# ---------------------------------------------------------------------------

# Maximum characters of page content included in the LLM prompt.
_MAX_CONTENT_CHARS = 4000

# Valid confidence and type values for detected claims.
_VALID_CONFIDENCES = {"established", "likely", "possible", "speculative"}
_VALID_CLAIM_TYPES = {"factual", "causal", "evaluative", "predictive"}


# ---------------------------------------------------------------------------
# Claim matching models
# ---------------------------------------------------------------------------

# Research model namespace and type IRIs
_RES_NS = "urn:sempkm:model:research:"
_RES_CLAIM = f"{_RES_NS}Claim"
_RES_EVIDENCE = f"{_RES_NS}Evidence"
_RES_RESEARCH_QUESTION = f"{_RES_NS}ResearchQuestion"

# Confidence levels considered "high" vs "low" for contradiction detection
_HIGH_CONFIDENCE = {"established", "supported", "likely"}
_LOW_CONFIDENCE = {"speculative", "possible"}

# Minimum shared meaningful words for research gap keyword overlap
_MIN_KEYWORD_OVERLAP = 2

# Stop words filtered out during keyword overlap computation
_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "out",
    "off", "over", "under", "again", "further", "then", "once", "and",
    "but", "or", "nor", "not", "so", "yet", "both", "either", "neither",
    "each", "every", "all", "any", "few", "more", "most", "other",
    "some", "such", "no", "only", "own", "same", "than", "too", "very",
    "that", "this", "these", "those", "it", "its", "he", "she", "they",
    "we", "you", "i", "me", "my", "your", "his", "her", "our", "their",
    "what", "which", "who", "whom", "how", "when", "where", "why",
    "if", "about", "up", "there", "here",
})


class ClaimInput(BaseModel):
    """A single claim to match against the knowledge graph."""
    text: str
    confidence: str = "possible"
    type: str = "factual"


class MatchClaimsRequest(BaseModel):
    """Request body for POST /api/ai/match-claims."""
    claims: list[ClaimInput]


class MatchedObject(BaseModel):
    """A knowledge graph object matched to a detected claim."""
    iri: str
    label: str
    type_iri: str | None = None
    type_label: str | None = None
    match_type: str  # "fts" | "url" | "exact"
    indicator: str | None = None  # "contradicts" | "corroborates" | "contested" | "related"
    confidence: str | None = None  # existing object's confidence level
    fts_score: float | None = None


class ClaimMatch(BaseModel):
    """Matches for a single detected claim."""
    claim_text: str
    matched_objects: list[MatchedObject] = []


class ResearchGap(BaseModel):
    """An open research question related to claims but lacking evidence."""
    iri: str
    label: str
    question_text: str | None = None
    status: str | None = None


class MatchClaimsResponse(BaseModel):
    """Response body for POST /api/ai/match-claims."""
    matches: list[ClaimMatch] = []
    research_gaps: list[ResearchGap] = []


# ---------------------------------------------------------------------------
# Indicator computation
# ---------------------------------------------------------------------------

def _compute_indicator(
    detected_confidence: str,
    existing_confidence: str | None,
    existing_type_iri: str | None,
) -> str:
    """Compute contradiction/corroboration indicator between a detected claim
    and an existing knowledge graph object.

    Returns one of: "contradicts", "corroborates", "contested", "related".
    """
    # Only Claims get typed indicators; everything else is "related"
    if existing_type_iri != _RES_CLAIM:
        return "related"

    if not existing_confidence:
        return "related"

    # Contested existing claim → always "contested"
    if existing_confidence == "contested":
        return "contested"

    # High-confidence existing vs low-confidence detected → contradicts
    if existing_confidence in _HIGH_CONFIDENCE and detected_confidence in _LOW_CONFIDENCE:
        return "contradicts"

    # Low-confidence existing vs high-confidence detected → also contradicts
    if existing_confidence in _LOW_CONFIDENCE and detected_confidence in _HIGH_CONFIDENCE:
        return "contradicts"

    # Both high-confidence → corroborates
    if existing_confidence in _HIGH_CONFIDENCE and detected_confidence in _HIGH_CONFIDENCE:
        return "corroborates"

    return "related"


# ---------------------------------------------------------------------------
# Research gap detection
# ---------------------------------------------------------------------------

def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful lowercase keywords from text, filtering stop words."""
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return {w for w in words if w not in _STOP_WORDS}


async def _find_research_gaps(
    triplestore,
    label_service,
    claim_texts: list[str],
) -> list[ResearchGap]:
    """Find open/partially-answered research questions that overlap with
    detected claim keywords but lack linked evidence.

    Returns up to 5 research gap objects.
    """
    # Query for all open/partially-answered ResearchQuestion objects
    rq_sparql = f"""
    PREFIX res: <{_RES_NS}>
    PREFIX dcterms: <http://purl.org/dc/terms/>

    SELECT ?rq ?title ?description ?status WHERE {{
      GRAPH <urn:sempkm:current> {{
        ?rq a res:ResearchQuestion .
        ?rq res:status ?status .
        FILTER(?status IN ("open", "partially-answered"))
        OPTIONAL {{ ?rq dcterms:title ?title }}
        OPTIONAL {{ ?rq res:description ?description }}
      }}
    }}
    LIMIT 50
    """

    try:
        result = await triplestore.query(rq_sparql)
    except Exception:
        logger.warning("Research gap SPARQL query failed", exc_info=True)
        return []

    bindings = result.get("results", {}).get("bindings", [])
    if not bindings:
        return []

    # Build keyword set from all claim texts combined
    claim_keywords: set[str] = set()
    for text in claim_texts:
        claim_keywords.update(_extract_keywords(text))

    if not claim_keywords:
        return []

    gaps: list[ResearchGap] = []

    for row in bindings:
        rq_iri = row.get("rq", {}).get("value", "")
        title = row.get("title", {}).get("value", "")
        description = row.get("description", {}).get("value", "")
        status = row.get("status", {}).get("value", "")

        if not rq_iri:
            continue

        # Check keyword overlap between claim texts and RQ title+description
        rq_text = f"{title} {description}"
        rq_keywords = _extract_keywords(rq_text)
        overlap = claim_keywords & rq_keywords

        if len(overlap) < _MIN_KEYWORD_OVERLAP:
            continue

        # Check if this RQ has any linked evidence
        evidence_sparql = f"""
        PREFIX res: <{_RES_NS}>
        SELECT (COUNT(?ev) AS ?count) WHERE {{
          GRAPH <urn:sempkm:current> {{
            ?ev a res:Evidence .
            ?ev res:addresses <{rq_iri}> .
          }}
        }}
        """
        try:
            ev_result = await triplestore.query(evidence_sparql)
            ev_bindings = ev_result.get("results", {}).get("bindings", [])
            ev_count = int(ev_bindings[0].get("count", {}).get("value", "0")) if ev_bindings else 0
        except Exception:
            logger.warning("Evidence count query failed for RQ=%s", rq_iri, exc_info=True)
            ev_count = 0

        # If no evidence → it's a gap
        if ev_count == 0:
            # Resolve label
            try:
                labels = await label_service.resolve_batch([rq_iri])
                label = labels.get(rq_iri, rq_iri)
            except Exception:
                label = title or rq_iri

            gaps.append(ResearchGap(
                iri=rq_iri,
                label=label,
                question_text=title or None,
                status=status or None,
            ))

        if len(gaps) >= 5:
            break

    return gaps


# ---------------------------------------------------------------------------
# Claim detection models
# ---------------------------------------------------------------------------

class DetectClaimsRequest(BaseModel):
    """Request body for POST /api/ai/detect-claims."""
    content: str  # page text content
    url: str = ""
    title: str = ""


class DetectedClaim(BaseModel):
    """A single claim extracted from page text."""
    text: str
    confidence: str  # established|likely|possible|speculative
    type: str  # factual|causal|evaluative|predictive


class DetectClaimsResponse(BaseModel):
    """Response body for POST /api/ai/detect-claims."""
    claims: list[DetectedClaim] = []
    parse_error: str | None = None


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_claim_extraction_prompt(content: str, title: str, url: str) -> list[dict]:
    """Build the messages array for the claim extraction LLM call.

    The system message instructs the LLM to extract specific, testable claims
    and return valid JSON. The user message contains the page metadata and
    content (truncated to ~4000 chars).
    """
    system_message = (
        "You are a claim extraction engine. Your task is to identify specific, "
        "testable claims from the provided text.\n\n"
        "Return ONLY valid JSON with no additional text, explanation, or markdown "
        "formatting. The JSON must have this exact structure:\n"
        '{"claims": [{"text": "...", "confidence": "...", "type": "..."}]}\n\n'
        "Confidence levels (choose one per claim):\n"
        "- established: widely accepted fact, strong consensus\n"
        "- likely: well-supported by evidence, broadly accepted\n"
        "- possible: some supporting evidence, not yet conclusive\n"
        "- speculative: hypothesis, conjecture, or early-stage idea\n\n"
        "Claim types (choose one per claim):\n"
        "- factual: verifiable statement of fact\n"
        "- causal: cause-and-effect relationship\n"
        "- evaluative: judgment or assessment\n"
        "- predictive: forecast or projection\n\n"
        "Rules:\n"
        "- Extract at most 10 of the most significant claims\n"
        "- Each claim text should be a self-contained statement\n"
        "- Skip opinions presented as opinions (e.g. 'I think...')\n"
        "- Focus on claims that could be verified or contradicted\n"
        "- Return an empty claims array if no claims are found\n"
    )

    # Truncate content to stay within context limits
    truncated = content[:_MAX_CONTENT_CHARS]
    if len(content) > _MAX_CONTENT_CHARS:
        truncated += "\n[...content truncated...]"

    user_parts = []
    if title:
        user_parts.append(f"Title: {title}")
    if url:
        user_parts.append(f"URL: {url}")
    user_parts.append(f"\nContent:\n{truncated}")

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": "\n".join(user_parts)},
    ]


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------

def _parse_claims_response(content: str) -> tuple[list[dict], str | None]:
    """Parse LLM response into a list of claim dicts with fallback strategies.

    Tries three approaches in order:
    1. Direct json.loads() on the full content
    2. Extract JSON from a markdown ```json ... ``` code block
    3. Find outermost { ... } boundaries and parse

    Returns (claims_list, error_or_none). Each claim dict has text, confidence,
    and type keys. Claims with empty text are filtered out.
    """
    parsed = None

    # Strategy 1: direct JSON parse
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        pass

    # Strategy 2: extract from markdown code block
    if parsed is None:
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", content, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1))
            except (json.JSONDecodeError, TypeError):
                pass

    # Strategy 3: find outermost { ... } boundaries
    if parsed is None:
        first_brace = content.find("{")
        last_brace = content.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            try:
                parsed = json.loads(content[first_brace:last_brace + 1])
            except (json.JSONDecodeError, TypeError):
                pass

    # All strategies failed
    if parsed is None:
        return [], "Failed to parse LLM response"

    # Validate structure: must have a "claims" key with a list
    if not isinstance(parsed, dict) or "claims" not in parsed:
        return [], "LLM response missing 'claims' key"

    raw_claims = parsed["claims"]
    if not isinstance(raw_claims, list):
        return [], "LLM response 'claims' is not a list"

    # Validate and filter individual claims
    valid_claims: list[dict] = []
    for claim in raw_claims:
        if not isinstance(claim, dict):
            continue
        # Must have text, confidence, type
        if not all(k in claim for k in ("text", "confidence", "type")):
            continue
        # Filter out empty text
        if not claim["text"] or not claim["text"].strip():
            continue
        valid_claims.append({
            "text": claim["text"].strip(),
            "confidence": claim["confidence"] if claim["confidence"] in _VALID_CONFIDENCES else "possible",
            "type": claim["type"] if claim["type"] in _VALID_CLAIM_TYPES else "factual",
        })

    return valid_claims, None


# ---------------------------------------------------------------------------
# Claim detection endpoint
# ---------------------------------------------------------------------------

@ai_router.post("/ai/detect-claims")
async def detect_claims(
    body: DetectClaimsRequest,
    user: User = Depends(get_current_user_or_api),
    db: AsyncSession = Depends(get_db_session),
):
    """Extract structured claims from page text via LLM.

    Accepts ``{content, url, title}`` and returns
    ``{claims: [{text, confidence, type}], parse_error}``.
    Returns 503 when LLM is not configured, 400 when content is empty.
    """
    # Validate content is not empty
    if not body.content or not body.content.strip():
        return JSONResponse({"error": "Content is required"}, status_code=400)

    # Check LLM availability
    svc = LLMConfigService()
    config = await svc.get_config(db)
    base_url = config["api_base_url"].rstrip("/") if config["api_base_url"] else ""

    if not base_url:
        logger.debug("Claim detection requested but LLM not configured, user=%s", user.email)
        return JSONResponse({"error": "LLM not configured"}, status_code=503)

    # Build prompt
    messages = _build_claim_extraction_prompt(body.content, body.title, body.url)
    model = config["default_model"] or "gpt-4o"

    # Get API key
    api_key = await svc.get_decrypted_api_key(db)

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "temperature": 0.2,  # low temperature for consistent structured output
    }

    # Make non-streaming LLM call
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        # Extract the assistant's message content
        llm_content = data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning("LLM call failed for claim detection: %s", str(e), exc_info=True)
        return DetectClaimsResponse(claims=[], parse_error=f"LLM call failed: {str(e)[:200]}")

    # Parse claims from LLM response
    claims_data, parse_error = _parse_claims_response(llm_content)

    claims = [DetectedClaim(**c) for c in claims_data]

    logger.debug(
        "Claim detection: user=%s, content_len=%d, claims_found=%d, parse_error=%s",
        user.email,
        len(body.content),
        len(claims),
        parse_error,
    )

    return DetectClaimsResponse(claims=claims, parse_error=parse_error)


# ---------------------------------------------------------------------------
# Claim-to-graph matching endpoint
# ---------------------------------------------------------------------------

@ai_router.post("/ai/match-claims")
async def match_claims(
    body: MatchClaimsRequest,
    request: Request,
    user: User = Depends(get_current_user_or_api),
):
    """Match detected claims against the knowledge graph.

    For each claim, runs FTS search via SearchService, resolves types and
    confidence levels via SPARQL, computes contradiction/corroboration
    indicators, and detects research question gaps.

    Returns ``MatchClaimsResponse`` with matches capped at 5 per claim
    (sorted by FTS score) and up to 5 research gaps.
    """
    if not body.claims:
        return JSONResponse({"error": "Claims list is required"}, status_code=400)

    triplestore = request.app.state.triplestore_client
    label_service = request.app.state.label_service
    search_service: SearchService = request.app.state.search_service

    matches: list[ClaimMatch] = []

    for claim in body.claims:
        if not claim.text or not claim.text.strip():
            matches.append(ClaimMatch(claim_text=claim.text, matched_objects=[]))
            continue

        # FTS search for this claim
        try:
            fts_results = await search_service.search(claim.text, limit=20)
        except Exception:
            logger.warning(
                "SearchService error for claim=%r", claim.text[:80], exc_info=True
            )
            matches.append(ClaimMatch(claim_text=claim.text, matched_objects=[]))
            continue

        if not fts_results:
            matches.append(ClaimMatch(claim_text=claim.text, matched_objects=[]))
            continue

        # Collect all matched IRIs for batch resolution
        matched_iris = [sr.iri for sr in fts_results]

        # Resolve types via SPARQL
        type_map: dict[str, str] = {}  # iri → type_iri
        if matched_iris:
            values_clause = " ".join(f"(<{iri}>)" for iri in matched_iris)
            type_sparql = (
                "SELECT ?s ?type WHERE { "
                "GRAPH <urn:sempkm:current> { "
                f"VALUES (?s) {{ {values_clause} }} "
                "?s a ?type "
                "} }"
            )
            try:
                type_result = await triplestore.query(type_sparql)
                for row in type_result.get("results", {}).get("bindings", []):
                    iri = row.get("s", {}).get("value", "")
                    type_iri = row.get("type", {}).get("value", "")
                    if iri and type_iri and iri not in type_map:
                        type_map[iri] = type_iri
            except Exception:
                logger.warning("Type resolution SPARQL failed for claim matching", exc_info=True)

        # For res:Claim objects, fetch their confidence via SPARQL
        confidence_map: dict[str, str] = {}  # iri → confidence
        claim_iris = [iri for iri, t in type_map.items() if t == _RES_CLAIM]
        if claim_iris:
            values_clause = " ".join(f"(<{iri}>)" for iri in claim_iris)
            conf_sparql = (
                f"PREFIX res: <{_RES_NS}> "
                "SELECT ?s ?confidence WHERE { "
                "GRAPH <urn:sempkm:current> { "
                f"VALUES (?s) {{ {values_clause} }} "
                "?s res:confidence ?confidence "
                "} }"
            )
            try:
                conf_result = await triplestore.query(conf_sparql)
                for row in conf_result.get("results", {}).get("bindings", []):
                    iri = row.get("s", {}).get("value", "")
                    conf = row.get("confidence", {}).get("value", "")
                    if iri and conf:
                        confidence_map[iri] = conf
            except Exception:
                logger.warning("Confidence resolution SPARQL failed", exc_info=True)

        # Resolve labels for matched objects + their types
        labels: dict[str, str] = {}
        type_labels: dict[str, str] = {}
        try:
            labels = await label_service.resolve_batch(matched_iris)
        except Exception:
            logger.warning("Label resolution failed for claim matching", exc_info=True)

        unique_type_iris = list(set(type_map.values()))
        if unique_type_iris:
            try:
                type_labels = await label_service.resolve_batch(unique_type_iris)
            except Exception:
                logger.warning("Type label resolution failed for claim matching", exc_info=True)

        # Build matched objects, sorted by FTS score descending, capped at 5
        matched_objects: list[MatchedObject] = []
        for sr in fts_results:
            type_iri = type_map.get(sr.iri)
            existing_confidence = confidence_map.get(sr.iri)
            indicator = _compute_indicator(
                claim.confidence, existing_confidence, type_iri
            )

            matched_objects.append(MatchedObject(
                iri=sr.iri,
                label=labels.get(sr.iri, sr.label or sr.iri),
                type_iri=type_iri,
                type_label=type_labels.get(type_iri) if type_iri else None,
                match_type="fts",
                indicator=indicator,
                confidence=existing_confidence,
                fts_score=sr.score,
            ))

        # FTS results are already sorted by score descending; cap at 5
        matched_objects = matched_objects[:5]
        matches.append(ClaimMatch(claim_text=claim.text, matched_objects=matched_objects))

    # Detect research question gaps across all claim texts
    claim_texts = [c.text for c in body.claims if c.text and c.text.strip()]
    research_gaps: list[ResearchGap] = []
    try:
        research_gaps = await _find_research_gaps(triplestore, label_service, claim_texts)
    except Exception:
        logger.warning("Research gap detection failed", exc_info=True)

    logger.debug(
        "Claim matching: user=%s, claims=%d, total_matches=%d, research_gaps=%d",
        user.email,
        len(body.claims),
        sum(len(m.matched_objects) for m in matches),
        len(research_gaps),
    )

    return MatchClaimsResponse(matches=matches, research_gaps=research_gaps)


# ---------------------------------------------------------------------------
# Relationship suggestion models
# ---------------------------------------------------------------------------


class SuggestRelationshipsRequest(BaseModel):
    """Request body for POST /api/ai/suggest-relationships."""
    url: str = ""
    title: str = ""
    claims: list[ClaimInput] = []


class RelationshipSuggestion(BaseModel):
    """A single suggested relationship between the page and a graph object."""
    type: str  # "link" | "evidence" | "supports" | "contradicts"
    label: str  # human-readable suggestion text
    target_iri: str
    target_label: str
    reason: str  # why this suggestion was made


class SuggestRelationshipsResponse(BaseModel):
    """Response body for POST /api/ai/suggest-relationships."""
    suggestions: list[RelationshipSuggestion] = []


# ---------------------------------------------------------------------------
# Suggest-relationships endpoint
# ---------------------------------------------------------------------------

# Maximum suggestions returned
_MAX_SUGGESTIONS = 10


@ai_router.post("/ai/suggest-relationships")
async def suggest_relationships(
    body: SuggestRelationshipsRequest,
    request: Request,
    user: User = Depends(get_current_user_or_api),
):
    """Suggest relationships between a page and existing graph objects.

    Given a page's URL, title, and detected claims, finds existing objects
    that share references or topics, and suggests creating edges.

    Phase 1 — URL matching: find objects with matching URL string value.
    Phase 2 — Keyword matching: combine title + claim texts into search
    keywords and run FTS.

    Returns ``SuggestRelationshipsResponse`` capped at 10 suggestions.
    Returns 400 when no url/title/claims are provided.
    """
    # Validate at least one input is provided
    has_url = bool(body.url and body.url.strip())
    has_title = bool(body.title and body.title.strip())
    has_claims = bool(body.claims and any(c.text.strip() for c in body.claims if c.text))

    if not has_url and not has_title and not has_claims:
        return JSONResponse(
            {"error": "At least one of url, title, or claims is required"},
            status_code=400,
        )

    triplestore = request.app.state.triplestore_client
    label_service = request.app.state.label_service
    search_service: SearchService = request.app.state.search_service

    suggestions: list[RelationshipSuggestion] = []
    seen_iris: set[str] = set()

    # Phase 1 — URL matching via SPARQL
    if has_url:
        escaped_url = sparql_escape_string(body.url.strip())
        url_sparql = (
            "SELECT DISTINCT ?s WHERE { "
            "GRAPH <urn:sempkm:current> { "
            f'?s ?p ?val . FILTER(STR(?val) = "{escaped_url}") '
            "} } LIMIT 20"
        )
        try:
            url_result = await triplestore.query(url_sparql)
            bindings = url_result.get("results", {}).get("bindings", [])
            url_iris = [
                row.get("s", {}).get("value", "")
                for row in bindings
                if row.get("s", {}).get("value", "")
            ]

            if url_iris:
                # Resolve labels for URL-matched objects
                try:
                    url_labels = await label_service.resolve_batch(url_iris)
                except Exception:
                    url_labels = {}

                for iri in url_iris:
                    if iri in seen_iris or len(suggestions) >= _MAX_SUGGESTIONS:
                        break
                    seen_iris.add(iri)
                    suggestions.append(RelationshipSuggestion(
                        type="link",
                        label=f"Links to {url_labels.get(iri, iri)}",
                        target_iri=iri,
                        target_label=url_labels.get(iri, iri),
                        reason="cites same URL",
                    ))
        except Exception:
            logger.warning(
                "Suggest-relationships URL matching failed for url=%s",
                body.url,
                exc_info=True,
            )

    # Phase 2 — Keyword matching via FTS
    search_parts: list[str] = []
    if has_title:
        search_parts.append(body.title.strip())
    for claim in body.claims:
        if claim.text and claim.text.strip():
            search_parts.append(claim.text.strip())
    search_text = " ".join(search_parts).strip()

    if search_text and len(suggestions) < _MAX_SUGGESTIONS:
        try:
            fts_results = await search_service.search(search_text, limit=20)
        except Exception:
            logger.warning(
                "Suggest-relationships FTS failed for text=%r",
                search_text[:80],
                exc_info=True,
            )
            fts_results = []

        # Resolve types for FTS results
        fts_iris = [sr.iri for sr in fts_results if sr.iri not in seen_iris]
        type_map: dict[str, str] = {}
        if fts_iris:
            values_clause = " ".join(f"(<{iri}>)" for iri in fts_iris)
            type_sparql = (
                "SELECT ?s ?type WHERE { "
                "GRAPH <urn:sempkm:current> { "
                f"VALUES (?s) {{ {values_clause} }} "
                "?s a ?type "
                "} }"
            )
            try:
                type_result = await triplestore.query(type_sparql)
                for row in type_result.get("results", {}).get("bindings", []):
                    iri = row.get("s", {}).get("value", "")
                    type_iri = row.get("type", {}).get("value", "")
                    if iri and type_iri and iri not in type_map:
                        type_map[iri] = type_iri
            except Exception:
                logger.warning("Suggest-relationships type resolution failed", exc_info=True)

        # Resolve labels for FTS results
        fts_labels: dict[str, str] = {}
        if fts_iris:
            try:
                fts_labels = await label_service.resolve_batch(fts_iris)
            except Exception:
                logger.warning("Suggest-relationships label resolution failed", exc_info=True)

        for sr in fts_results:
            if sr.iri in seen_iris or len(suggestions) >= _MAX_SUGGESTIONS:
                continue
            seen_iris.add(sr.iri)

            type_iri = type_map.get(sr.iri, "")
            label = fts_labels.get(sr.iri, sr.label or sr.iri)

            # Determine suggestion type based on object type
            if type_iri == _RES_CLAIM:
                # Check claim confidence to suggest supports vs contradicts
                suggestion_type = "supports"
                reason = "discusses similar claim"
            elif type_iri == _RES_EVIDENCE:
                suggestion_type = "evidence"
                reason = "may provide evidence"
            else:
                suggestion_type = "link"
                reason = "discusses similar topic"

            suggestions.append(RelationshipSuggestion(
                type=suggestion_type,
                label=f"{suggestion_type.title()}s {label}" if suggestion_type != "link" else f"Related to {label}",
                target_iri=sr.iri,
                target_label=label,
                reason=reason,
            ))

    logger.debug(
        "Suggest relationships: user=%s, url=%s, title=%s, claims=%d, suggestions=%d",
        user.email,
        body.url[:50] if body.url else "",
        body.title[:50] if body.title else "",
        len(body.claims),
        len(suggestions),
    )

    return SuggestRelationshipsResponse(suggestions=suggestions)


# ---------------------------------------------------------------------------
# Summarize models
# ---------------------------------------------------------------------------


class GraphContextItem(BaseModel):
    """An existing knowledge graph object provided as context for summarization."""
    iri: str
    label: str
    type: str = ""
    snippet: str = ""


class SummarizeRequest(BaseModel):
    """Request body for POST /api/ai/summarize."""
    content: str
    graph_context: list[GraphContextItem] = []


class SummarizeResponse(BaseModel):
    """Response body for POST /api/ai/summarize."""
    summary: str


# ---------------------------------------------------------------------------
# Summarize endpoint
# ---------------------------------------------------------------------------


def _build_summarize_prompt(
    content: str,
    graph_context: list[GraphContextItem],
) -> list[dict]:
    """Build the messages array for the summarization LLM call.

    The system message instructs the LLM to summarize the page content
    in the context of the user's existing knowledge graph.
    """
    context_lines: list[str] = []
    for item in graph_context:
        parts = [f"- {item.label}"]
        if item.type:
            parts.append(f"(type: {item.type})")
        if item.snippet:
            parts.append(f"— {item.snippet[:200]}")
        context_lines.append(" ".join(parts))

    if context_lines:
        context_block = (
            "The user has existing knowledge about these topics:\n"
            + "\n".join(context_lines)
            + "\n\nIncorporate references to the user's existing knowledge where relevant."
        )
    else:
        context_block = "The user has no prior context for this page."

    system_message = (
        "Summarize the following page content. "
        + context_block
        + " Be concise (2-3 paragraphs)."
    )

    # Truncate content to stay within context limits
    truncated = content[:_MAX_CONTENT_CHARS]
    if len(content) > _MAX_CONTENT_CHARS:
        truncated += "\n[...content truncated...]"

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": truncated},
    ]


@ai_router.post("/ai/summarize")
async def summarize(
    body: SummarizeRequest,
    user: User = Depends(get_current_user_or_api),
    db: AsyncSession = Depends(get_db_session),
):
    """Generate a personalized summary of page content.

    Takes page content and optional graph context objects (from match-claims
    results), sends to LLM with a prompt that incorporates the user's existing
    knowledge, and returns the summary string.

    Returns 400 when content is empty, 503 when LLM is not configured.
    """
    # Validate content is not empty
    if not body.content or not body.content.strip():
        return JSONResponse({"error": "Content is required"}, status_code=400)

    # Check LLM availability
    svc = LLMConfigService()
    config = await svc.get_config(db)
    base_url = config["api_base_url"].rstrip("/") if config["api_base_url"] else ""

    if not base_url:
        logger.debug("Summarize requested but LLM not configured, user=%s", user.email)
        return JSONResponse({"error": "LLM not configured"}, status_code=503)

    # Build prompt
    messages = _build_summarize_prompt(body.content, body.graph_context)
    model = config["default_model"] or "gpt-4o"

    # Get API key
    api_key = await svc.get_decrypted_api_key(db)

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "temperature": 0.5,
    }

    # Make non-streaming LLM call
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        # Extract the assistant's message content
        summary_text = data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning("LLM call failed for summarize: %s", str(e), exc_info=True)
        return SummarizeResponse(summary="Unable to generate summary. Please try again.")

    logger.debug(
        "Summarize: user=%s, content_len=%d, context_items=%d, summary_len=%d",
        user.email,
        len(body.content),
        len(body.graph_context),
        len(summary_text),
    )

    return SummarizeResponse(summary=summary_text)
