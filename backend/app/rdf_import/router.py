"""RDF data import router — wizard flow for paste/upload, preview, and import.

Provides endpoints for the 3-step RDF import wizard:
1. Paste/upload RDF data → parse and preview subjects with SHACL validation
2. Select subjects → execute import with SSE progress
3. View import summary

Uses module-level caches keyed by user ID to pass parse results between
the parse and execute steps without re-parsing.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.obsidian.broadcast import ScanBroadcast, SSEEvent, stream_sse
from app.rdf_import.executor import check_collisions, execute_import, validate_shacl
from app.rdf_import.models import RdfImportResult, RdfParseResult
from app.rdf_import.parser import detect_format, parse_rdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/browser/rdf-import", tags=["rdf-import"])

# Module-level caches keyed by user ID (string)
_parse_cache: dict[str, RdfParseResult] = {}
_import_results: dict[str, RdfImportResult] = {}
_broadcasts: dict[str, ScanBroadcast] = {}


# ---------------------------------------------------------------------------
# GET / — Import wizard page
# ---------------------------------------------------------------------------

@router.get("")
async def import_page(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Serve the RDF import wizard page (full page or htmx partial)."""
    templates = request.app.state.templates

    is_htmx = request.headers.get("HX-Request") == "true"
    block_name = "content" if is_htmx else None

    return templates.TemplateResponse(
        request,
        "rdf_import/import.html",
        {"request": request, "user": user},
        block_name=block_name,
    )


# ---------------------------------------------------------------------------
# POST /parse — Parse RDF content and return preview
# ---------------------------------------------------------------------------

@router.post("/parse")
async def parse_rdf_content(
    request: Request,
    user: User = Depends(get_current_user),
    content: str | None = Form(None),
    file: UploadFile | None = None,
    format_override: str | None = Form(None),
):
    """Parse pasted or uploaded RDF content and return a preview partial.

    On success, runs SHACL validation and collision detection, caches the
    parse result, and renders the preview table with subjects, types,
    validation status, and collision warnings.

    On failure, renders an error message partial.
    """
    templates = request.app.state.templates
    triplestore_client = request.app.state.triplestore_client

    # Read content from file upload or form field
    raw_content: str | None = None
    filename: str | None = None

    if file and file.filename:
        raw_bytes = await file.read()
        raw_content = raw_bytes.decode("utf-8", errors="replace")
        filename = file.filename
    elif content:
        raw_content = content

    if not raw_content or not raw_content.strip():
        return templates.TemplateResponse(
            request,
            "rdf_import/partials/error.html",
            {"request": request, "error": "No RDF content provided. Paste or upload RDF data."},
        )

    # Parse the RDF content
    fmt = detect_format(raw_content, filename=filename, format_override=format_override)
    parse_result = parse_rdf(raw_content, format=fmt)

    if parse_result.errors:
        error_msg = "; ".join(parse_result.errors)
        return templates.TemplateResponse(
            request,
            "rdf_import/partials/error.html",
            {"request": request, "error": f"Parse error ({fmt}): {error_msg}"},
        )

    if not parse_result.subjects:
        return templates.TemplateResponse(
            request,
            "rdf_import/partials/error.html",
            {"request": request, "error": "No subjects found in the RDF data."},
        )

    # Run SHACL validation and collision detection in parallel
    subject_iris = [si.iri for si in parse_result.subjects if not si.is_blank_node]
    shacl_results, collisions = await asyncio.gather(
        validate_shacl(parse_result.raw_graph, triplestore_client),
        check_collisions(subject_iris, triplestore_client),
    )

    # Cache the parse result for the execute step
    user_key = str(user.id)
    _parse_cache[user_key] = parse_result

    return templates.TemplateResponse(
        request,
        "rdf_import/partials/preview.html",
        {
            "request": request,
            "subjects": parse_result.subjects,
            "shacl_results": shacl_results,
            "collisions": collisions,
            "format_used": parse_result.format_used,
            "total_triples": parse_result.total_triples,
        },
    )


# ---------------------------------------------------------------------------
# POST /execute — Start import execution
# ---------------------------------------------------------------------------

@router.post("/execute")
async def execute_rdf_import(
    request: Request,
    user: User = Depends(get_current_user),
    selected: list[str] = Form(...),
):
    """Start importing selected subjects and return progress partial.

    Retrieves the cached parse result, creates a background task for
    the import, and returns the progress UI partial which connects to
    the SSE stream.
    """
    templates = request.app.state.templates
    user_key = str(user.id)

    cached = _parse_cache.get(user_key)
    if not cached:
        return templates.TemplateResponse(
            request,
            "rdf_import/partials/error.html",
            {"request": request, "error": "No parsed data found. Please parse RDF content first."},
        )

    event_store = request.app.state.event_store
    triplestore_client = request.app.state.triplestore_client

    # Create broadcast for SSE progress
    broadcast = ScanBroadcast()
    _broadcasts[user_key] = broadcast

    async def _run_import():
        try:
            result = await execute_import(
                parse_result=cached,
                selected_iris=selected,
                user=user,
                event_store=event_store,
                triplestore_client=triplestore_client,
                broadcast=broadcast,
            )
            _import_results[user_key] = result
        finally:
            # Clean up parse cache — import is done
            _parse_cache.pop(user_key, None)
            # Broadcast is cleaned up after SSE clients disconnect
            # but remove after a short delay if no clients connect
            await asyncio.sleep(30)
            _broadcasts.pop(user_key, None)

    asyncio.create_task(_run_import())

    return templates.TemplateResponse(
        request,
        "rdf_import/partials/progress.html",
        {"request": request},
    )


# ---------------------------------------------------------------------------
# GET /execute/stream — SSE stream for import progress
# ---------------------------------------------------------------------------

@router.get("/execute/stream")
async def import_stream(
    request: Request,
    user: User = Depends(get_current_user),
):
    """SSE stream for real-time import progress events.

    Clients subscribe to the user's broadcast queue and receive
    ``import_progress``, ``import_complete``, or ``import_error`` events.
    """
    user_key = str(user.id)
    broadcast = _broadcasts.get(user_key)

    if not broadcast:
        # Import may have already completed before SSE connected
        cached_result = _import_results.get(user_key)
        if cached_result:
            async def completed():
                yield SSEEvent(
                    event="import_complete",
                    data=cached_result.to_dict(),
                ).format()
            return StreamingResponse(completed(), media_type="text/event-stream")

        async def no_import():
            yield SSEEvent(
                event="import_error",
                data={"message": "No active import"},
            ).format()
        return StreamingResponse(no_import(), media_type="text/event-stream")

    queue = broadcast.subscribe()
    try:
        return StreamingResponse(
            stream_sse(
                queue,
                terminal_events={"import_complete", "import_error"},
                shutdown_event=request.app.state.shutdown_event,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception:
        broadcast.unsubscribe(queue)
        raise


# ---------------------------------------------------------------------------
# GET /summary — Import result summary
# ---------------------------------------------------------------------------

@router.get("/summary")
async def import_summary(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Render the import summary partial with stats (created/skipped/errors)."""
    templates = request.app.state.templates
    user_key = str(user.id)

    result = _import_results.pop(user_key, None)
    if not result:
        result = RdfImportResult()

    return templates.TemplateResponse(
        request,
        "rdf_import/partials/summary.html",
        {
            "request": request,
            "result": result,
        },
    )
