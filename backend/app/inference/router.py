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
from app.dependencies import get_event_store, get_ops_log_service, get_triplestore_client, get_validation_queue
from app.events.store import EventStore
from app.inference.entailments import ENTAILMENT_TYPES, MANIFEST_KEY_TO_TYPE, TYPE_TO_MANIFEST_KEY
from app.inference.service import InferenceService
from app.services.ops_log import OperationsLogService
from app.triplestore.client import TriplestoreClient
from app.validation.queue import AsyncValidationQueue

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
    ops_log: OperationsLogService = Depends(get_ops_log_service),
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

    # Get entailment config (manifest defaults + user overrides)
    config = await service.get_entailment_config(user_id=current_user.id)

    # Run inference
    result = await service.run_inference(config)

    # Log inference run to ops log (fire-and-forget)
    try:
        label = (
            f"Inference run: {result.total_inferred} inferred, "
            f"{result.new_count} new"
        )
        await ops_log.log_activity(
            activity_type="inference.run",
            label=label,
            actor=f"urn:sempkm:user:{current_user.id}",
            status="success",
        )
    except Exception:
        logger.warning("Failed to write ops log for inference run", exc_info=True)

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
    object_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    group_by: str | None = None,
    client: TriplestoreClient = Depends(get_triplestore_client),
    db: AsyncSession = Depends(get_db_session),
    event_store: EventStore = Depends(get_event_store),
    current_user: User = Depends(get_current_user),
):
    """List all inferred triples with their status.

    Query params:
        entailment_type: Filter by entailment type (e.g., "owl:inverseOf").
        triple_status: Filter by status ("active", "dismissed").
        object_type: Filter by object type slug (e.g., "person", "project").
        date_from: Filter by inferred_at >= date (ISO date string).
        date_to: Filter by inferred_at <= date (ISO date string).
        group_by: Group results by "time", "object_type", or "property_type".

    Returns list of inferred triple dicts, or HTML fragment for htmx.
    """
    service = _get_inference_service(client, db, event_store)

    filters = {}
    if entailment_type:
        filters["entailment_type"] = entailment_type
    if triple_status:
        filters["status"] = triple_status
    if object_type:
        filters["object_type"] = object_type
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to

    triples = await service.get_inferred_triples(filters if filters else None)

    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        if group_by:
            return _render_grouped_triples_html(triples, group_by)
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
    validation_queue: AsyncValidationQueue = Depends(get_validation_queue),
    current_user: User = Depends(get_current_user),
):
    """Promote an inferred triple to user data.

    Copies the triple to urn:sempkm:current via EventStore.commit(),
    marks it as promoted, and removes it from urn:sempkm:inferred.
    Enqueues re-validation after successful promotion.

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

    # Enqueue validation after promotion commits to EventStore
    from datetime import datetime, timezone

    await validation_queue.enqueue(
        event_iri=f"urn:sempkm:inference:promote:{triple_hash}",
        timestamp=datetime.now(timezone.utc).isoformat(),
        trigger_source="inference_promote",
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
    config = await service.get_entailment_config(user_id=current_user.id)
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

    # Persist via SettingsService
    from app.services.settings import SettingsService

    settings_svc = SettingsService()
    for key, value in body.items():
        # Normalize key: accept both manifest keys and entailment type labels
        manifest_key = key if key in MANIFEST_KEY_TO_TYPE else TYPE_TO_MANIFEST_KEY.get(key)
        if manifest_key:
            settings_key = f"inference.{model_id}.{manifest_key}"
            await settings_svc.set_override(
                current_user.id, settings_key, str(bool(value)).lower(), db
            )

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

    cards = _render_triple_cards(triples)

    # OOB swap for last-run timestamp (updates #inference-last-run outside #inference-results)
    timestamp_display = result.run_timestamp[:19].replace("T", " ")
    oob_timestamp = (
        f'<span id="inference-last-run" class="inference-last-run" '
        f'hx-swap-oob="true">Last run: {timestamp_display}</span>'
    )

    html = f"""{summary}
<div class="inference-cards">
{cards}
</div>
{oob_timestamp}"""
    return HTMLResponse(content=html)


def _render_triples_list_html(triples):
    """Render just the triples list as HTML."""
    from fastapi.responses import HTMLResponse

    if not triples:
        return HTMLResponse(
            content='<div class="inference-empty">No inferred triples. '
            "Click Refresh to run inference.</div>"
        )

    cards = _render_triple_cards(triples)
    html = f'<div class="inference-cards">\n{cards}\n</div>'
    return HTMLResponse(content=html)


def _extract_type_from_iri(iri: str) -> str:
    """Extract a type-like segment from an IRI for grouping.

    Examples:
        "urn:sempkm:model:basic-pkm:person-1" -> "person"
        "http://xmlns.com/foaf/0.1/Person" -> "Person"
    """
    import re

    parts = iri.rsplit(":", 1)
    if len(parts) == 2:
        segment = parts[1]
        return re.sub(r"-\d+$", "", segment) or segment
    return _compact_iri(iri)


def _render_grouped_triples_html(triples, group_by: str):
    """Render triples grouped by the specified dimension."""
    from collections import defaultdict

    from fastapi.responses import HTMLResponse

    if not triples:
        return HTMLResponse(
            content='<div class="inference-empty">No inferred triples.</div>'
        )

    groups = defaultdict(list)
    for t in triples:
        if group_by == "time":
            key = (t.get("inferred_at") or "")[:10] or "Unknown"
        elif group_by == "object_type":
            subject = t.get("subject", "")
            key = _extract_type_from_iri(subject)
        elif group_by == "property_type":
            key = t.get("entailment_type", "Unknown")
        else:
            key = "All"
        groups[key].append(t)

    html_parts = []
    for group_key in sorted(groups.keys()):
        group_triples = groups[group_key]
        cards = _render_triple_cards(group_triples)
        html_parts.append(
            f'<div class="inference-group">'
            f'<h4 class="inference-group-header">{group_key} ({len(group_triples)})</h4>'
            f'<div class="inference-cards">{cards}</div>'
            f"</div>"
        )

    return HTMLResponse(content="\n".join(html_parts))


def _render_triple_cards(triples):
    """Render card elements for a list of triples."""
    cards = []
    for t in triples:
        cards.append(_build_triple_card(t))
    return "\n".join(cards)


def _build_triple_card(t):
    """Build a single card element for a triple."""
    from html import escape

    h = t["triple_hash"]
    s_iri = t["subject"]
    o_iri = t["object"]
    s_display = _compact_iri(s_iri)
    p_display = _compact_iri(t["predicate"])
    o_display = _compact_iri(o_iri)
    status_class = f"status-{t['status']}"

    # Make subject and object clickable to open in dockview
    s_iri_escaped = escape(s_iri, quote=True)
    o_iri_escaped = escape(o_iri, quote=True)
    s_label_escaped = escape(s_display, quote=True).replace("'", "\\'")
    o_label_escaped = escape(o_display, quote=True).replace("'", "\\'")

    s_link = (
        f'<a href="#" class="inference-card-subject inference-card-link" '
        f"onclick=\"openTab('{s_iri_escaped}', '{s_label_escaped}'); return false;\">"
        f'{s_display}</a>'
    )
    o_link = (
        f'<a href="#" class="inference-card-object inference-card-link" '
        f"onclick=\"openTab('{o_iri_escaped}', '{o_label_escaped}'); return false;\">"
        f'{o_display}</a>'
    )

    actions = ""
    if t["status"] == "active":
        actions = (
            f'<div class="inference-card-actions">'
            f'<button class="btn btn-xs" '
            f'hx-post="/api/inference/triples/{h}/dismiss" '
            f'hx-target="closest .inference-card" hx-swap="outerHTML">Dismiss</button> '
            f'<button class="btn btn-xs btn-primary" '
            f'hx-post="/api/inference/triples/{h}/promote" '
            f'hx-target="closest .inference-card" hx-swap="outerHTML">Promote</button>'
            f"</div>"
        )
    elif t["status"] == "dismissed":
        actions = (
            '<div class="inference-card-actions" style="opacity:1">'
            '<span class="text-muted">Dismissed</span></div>'
        )
    elif t["status"] == "promoted":
        actions = (
            '<div class="inference-card-actions" style="opacity:1">'
            '<span class="text-muted">Promoted</span></div>'
        )

    return (
        f'<div id="triple-{h}" class="inference-card {status_class}">'
        f'<div class="inference-card-triple">'
        f'{s_link}'
        f'<span class="inference-card-predicate">{p_display}</span>'
        f'{o_link}'
        f"</div>"
        f'<div class="inference-card-meta">'
        f'<span class="inference-card-type-badge">{t["entailment_type"]}</span>'
        f"</div>"
        f"{actions}"
        f"</div>"
    )


def _render_triple_row_html(triple):
    """Render a single triple card for htmx swap."""
    from fastapi.responses import HTMLResponse

    return HTMLResponse(content=_build_triple_card(triple))
