"""Inference API router for OWL 2 RL inference management.

Provides endpoints for triggering inference runs, listing inferred triples,
dismissing/promoting individual triples, and managing entailment configuration.
All endpoints require authentication.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.db.session import get_db_session
from app.dependencies import get_event_store, get_triplestore_client
from app.events.store import EventStore
from app.inference.entailments import ENTAILMENT_TYPES, MANIFEST_KEY_TO_TYPE
from app.inference.service import InferenceService
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/inference")


def _get_inference_service(
    client: TriplestoreClient,
    db: AsyncSession,
    event_store: EventStore,
) -> InferenceService:
    """Create an InferenceService instance with injected dependencies."""
    return InferenceService(client=client, db_session=db, event_store=event_store)


@router.post("/run")
async def run_inference(
    request: Request,
    client: TriplestoreClient = Depends(get_triplestore_client),
    db: AsyncSession = Depends(get_db_session),
    event_store: EventStore = Depends(get_event_store),
    current_user: User = Depends(get_current_user),
):
    """Trigger a full inference run.

    Runs OWL 2 RL forward-chaining closure expansion on current data
    merged with ontology graphs. Materializes inferred triples into
    urn:sempkm:inferred and logs the run as an event.

    Returns InferenceResult as JSON, or an HTML fragment if HX-Request
    header is present (for htmx integration).
    """
    service = _get_inference_service(client, db, event_store)

    # Get entailment config (defaults for now)
    config = await service.get_entailment_config()

    # Run inference
    result = await service.run_inference(config)

    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        # Return HTML fragment for the inference panel
        triples = await service.get_inferred_triples()
        return _render_inference_panel_html(result, triples)

    return {
        "total_inferred": result.total_inferred,
        "by_entailment_type": result.by_entailment_type,
        "new_count": result.new_count,
        "preserved_dismissed": result.preserved_dismissed,
        "preserved_promoted": result.preserved_promoted,
        "run_timestamp": result.run_timestamp,
    }


@router.get("/triples")
async def get_inferred_triples(
    request: Request,
    entailment_type: str | None = None,
    triple_status: str | None = None,
    client: TriplestoreClient = Depends(get_triplestore_client),
    db: AsyncSession = Depends(get_db_session),
    event_store: EventStore = Depends(get_event_store),
    current_user: User = Depends(get_current_user),
):
    """List all inferred triples with their status.

    Query params:
        entailment_type: Filter by entailment type (e.g., "owl:inverseOf").
        triple_status: Filter by status ("active", "dismissed").

    Returns list of inferred triple dicts, or HTML fragment for htmx.
    """
    service = _get_inference_service(client, db, event_store)

    filters = {}
    if entailment_type:
        filters["entailment_type"] = entailment_type
    if triple_status:
        filters["status"] = triple_status

    triples = await service.get_inferred_triples(filters if filters else None)

    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        return _render_triples_list_html(triples)

    return triples


@router.post("/triples/{triple_hash}/dismiss")
async def dismiss_triple(
    triple_hash: str,
    request: Request,
    client: TriplestoreClient = Depends(get_triplestore_client),
    db: AsyncSession = Depends(get_db_session),
    event_store: EventStore = Depends(get_event_store),
    current_user: User = Depends(get_current_user),
):
    """Dismiss an inferred triple.

    Marks the triple as dismissed and removes it from the inferred graph.
    The triple will not reappear on future inference runs.

    Args:
        triple_hash: SHA-256 hash identifying the triple.
    """
    service = _get_inference_service(client, db, event_store)
    result = await service.dismiss_triple(triple_hash)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Triple not found: {triple_hash}",
        )

    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        return _render_triple_row_html(result)

    return result


@router.post("/triples/{triple_hash}/promote")
async def promote_triple(
    triple_hash: str,
    request: Request,
    client: TriplestoreClient = Depends(get_triplestore_client),
    db: AsyncSession = Depends(get_db_session),
    event_store: EventStore = Depends(get_event_store),
    current_user: User = Depends(get_current_user),
):
    """Promote an inferred triple to user data.

    Copies the triple to urn:sempkm:current via EventStore.commit(),
    marks it as promoted, and removes it from urn:sempkm:inferred.

    Args:
        triple_hash: SHA-256 hash identifying the triple.
    """
    service = _get_inference_service(client, db, event_store)
    result = await service.promote_triple(triple_hash)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Triple not found: {triple_hash}",
        )

    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        return _render_triple_row_html(result)

    return result


@router.get("/config")
async def get_inference_config(
    client: TriplestoreClient = Depends(get_triplestore_client),
    db: AsyncSession = Depends(get_db_session),
    event_store: EventStore = Depends(get_event_store),
    current_user: User = Depends(get_current_user),
):
    """Get current entailment configuration.

    Returns the enabled/disabled state for each entailment type,
    using manifest defaults as the baseline.
    """
    service = _get_inference_service(client, db, event_store)
    config = await service.get_entailment_config()
    return {
        "entailment_types": ENTAILMENT_TYPES,
        "config": config,
        "manifest_key_map": MANIFEST_KEY_TO_TYPE,
    }


@router.put("/config/{model_id}")
async def update_inference_config(
    model_id: str,
    request: Request,
    client: TriplestoreClient = Depends(get_triplestore_client),
    db: AsyncSession = Depends(get_db_session),
    event_store: EventStore = Depends(get_event_store),
    current_user: User = Depends(get_current_user),
):
    """Update entailment toggles for a specific model.

    Accepts JSON body with entailment type keys and boolean values.
    Saves to settings service for persistence across sessions.

    Args:
        model_id: The model identifier to update config for.
    """
    body = await request.json()

    # Validate: only known entailment types allowed
    for key in body:
        if key not in MANIFEST_KEY_TO_TYPE and key not in ENTAILMENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown entailment type: {key}",
            )

    # For now, return the submitted config (persistence via settings service
    # will be wired in a later plan when admin UI is built)
    return {
        "model_id": model_id,
        "config": body,
        "status": "updated",
    }


# --- HTML rendering helpers for htmx responses ---

def _compact_iri(iri: str) -> str:
    """Shorten an IRI for display."""
    for prefix, ns in [
        ("bpkm:", "urn:sempkm:model:basic-pkm:"),
        ("dcterms:", "http://purl.org/dc/terms/"),
        ("foaf:", "http://xmlns.com/foaf/0.1/"),
        ("skos:", "http://www.w3.org/2004/02/skos/core#"),
        ("schema:", "https://schema.org/"),
        ("rdf:", "http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
        ("rdfs:", "http://www.w3.org/2000/01/rdf-schema#"),
        ("owl:", "http://www.w3.org/2002/07/owl#"),
    ]:
        if iri.startswith(ns):
            return prefix + iri[len(ns):]
    # Fallback: last segment
    for sep in ("#", "/", ":"):
        idx = iri.rfind(sep)
        if 0 <= idx < len(iri) - 1:
            return iri[idx + 1:]
    return iri


def _render_inference_panel_html(result, triples):
    """Render the full inference panel HTML fragment."""
    from fastapi.responses import HTMLResponse

    summary = (
        f'<div class="inference-summary">'
        f"<strong>{result.total_inferred}</strong> inferred triples"
    )
    if result.by_entailment_type:
        parts = [f"{v} {k}" for k, v in result.by_entailment_type.items()]
        summary += f' ({", ".join(parts)})'
    summary += f" | {result.new_count} new"
    if result.preserved_dismissed:
        summary += f" | {result.preserved_dismissed} dismissed"
    summary += "</div>"

    rows = _render_triple_rows(triples)
    html = f"""{summary}
<table class="inference-triples-table">
  <thead>
    <tr>
      <th>Subject</th><th>Predicate</th><th>Object</th>
      <th>Type</th><th>Status</th><th>Actions</th>
    </tr>
  </thead>
  <tbody>
{rows}
  </tbody>
</table>"""
    return HTMLResponse(content=html)


def _render_triples_list_html(triples):
    """Render just the triples list as HTML."""
    from fastapi.responses import HTMLResponse

    if not triples:
        return HTMLResponse(
            content='<div class="inference-empty">No inferred triples. '
            "Click Refresh to run inference.</div>"
        )

    rows = _render_triple_rows(triples)
    html = f"""<table class="inference-triples-table">
  <thead>
    <tr>
      <th>Subject</th><th>Predicate</th><th>Object</th>
      <th>Type</th><th>Status</th><th>Actions</th>
    </tr>
  </thead>
  <tbody>
{rows}
  </tbody>
</table>"""
    return HTMLResponse(content=html)


def _render_triple_rows(triples):
    """Render table rows for a list of triples."""
    rows = []
    for t in triples:
        rows.append(_build_triple_row(t))
    return "\n".join(rows)


def _build_triple_row(t):
    """Build a single table row for a triple."""
    h = t["triple_hash"]
    s_display = _compact_iri(t["subject"])
    p_display = _compact_iri(t["predicate"])
    o_display = _compact_iri(t["object"])
    status_class = f"status-{t['status']}"

    actions = ""
    if t["status"] == "active":
        actions = (
            f'<button class="btn btn-xs" '
            f'hx-post="/api/inference/triples/{h}/dismiss" '
            f'hx-target="closest tr" hx-swap="outerHTML">Dismiss</button> '
            f'<button class="btn btn-xs btn-primary" '
            f'hx-post="/api/inference/triples/{h}/promote" '
            f'hx-target="closest tr" hx-swap="outerHTML">Promote</button>'
        )
    elif t["status"] == "dismissed":
        actions = '<span class="text-muted">Dismissed</span>'
    elif t["status"] == "promoted":
        actions = '<span class="text-muted">Promoted</span>'

    return (
        f'    <tr id="triple-{h}" class="{status_class}">'
        f"<td>{s_display}</td><td>{p_display}</td><td>{o_display}</td>"
        f"<td>{t['entailment_type']}</td><td>{t['status']}</td>"
        f"<td>{actions}</td></tr>"
    )


def _render_triple_row_html(triple):
    """Render a single triple row for htmx swap."""
    from fastapi.responses import HTMLResponse

    return HTMLResponse(content=_build_triple_row(triple))
