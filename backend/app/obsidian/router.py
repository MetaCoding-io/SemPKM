"""Obsidian vault import router.

Provides endpoints for uploading, scanning, streaming progress,
and discarding Obsidian vault ZIP imports.
"""

import asyncio
import json
import logging
import shutil
import zipfile
from pathlib import Path
from time import time

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from fastapi import Form

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.dependencies import get_shapes_service
from app.services.shapes import ShapesService

from .broadcast import ScanBroadcast, stream_sse
from .executor import ImportExecutor
from .models import ImportResult, MappingConfig, TypeMapping, PropertyMapping, VaultScanResult
from .scanner import VaultScanner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/browser/import", tags=["import"])

# Active broadcast instances keyed by import_id
_broadcasts: dict[str, ScanBroadcast] = {}

# Base directory for imports
IMPORTS_DIR = Path("/app/data/imports")


def _user_imports_dir(user: User) -> Path:
    """Return the imports directory for a user."""
    return IMPORTS_DIR / str(user.id)


def _find_existing_import(user: User) -> tuple[str, Path] | None:
    """Find an existing in-progress import for the user.

    Returns (import_id, import_path) or None.
    """
    user_dir = _user_imports_dir(user)
    if not user_dir.is_dir():
        return None
    for child in user_dir.iterdir():
        if child.is_dir():
            import_id = f"{user.id}_{child.name}"
            return import_id, child
    return None


@router.get("")
async def import_page(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Serve the import page (full page or htmx partial)."""
    templates = request.app.state.templates

    existing = _find_existing_import(user)
    context = {"request": request, "user": user}

    if existing:
        import_id, import_path = existing
        scan_result_path = import_path / "scan_result.json"
        if scan_result_path.exists():
            result = VaultScanResult.from_dict(
                json.loads(scan_result_path.read_text())
            )
            context["scan_result"] = result
            context["import_id"] = import_id
        else:
            context["import_id"] = import_id
            context["has_extract"] = True

    is_htmx = request.headers.get("HX-Request") == "true"
    block_name = "content" if is_htmx else None

    return templates.TemplateResponse(
        request,
        "obsidian/import.html",
        context,
        block_name=block_name,
    )


@router.post("/upload")
async def upload_vault(
    request: Request,
    file: UploadFile,
    user: User = Depends(get_current_user),
):
    """Accept a ZIP file upload, extract it, and return scan trigger partial."""
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(400, "Only ZIP files are accepted")

    timestamp = str(int(time()))
    import_id = f"{user.id}_{timestamp}"
    import_dir = _user_imports_dir(user) / timestamp
    import_dir.mkdir(parents=True, exist_ok=True)

    zip_path = import_dir / "vault.zip"
    extract_path = import_dir / "vault"
    extract_path.mkdir(exist_ok=True)

    # Write uploaded file in chunks (no aiofiles dependency)
    def _write_and_extract():
        with open(zip_path, "wb") as f:
            while True:
                chunk = file.file.read(8192)
                if not chunk:
                    break
                f.write(chunk)

        # Extract ZIP
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_path)

        # Remove ZIP after extraction
        zip_path.unlink(missing_ok=True)

    try:
        await asyncio.to_thread(_write_and_extract)
    except zipfile.BadZipFile:
        zip_path.unlink(missing_ok=True)
        shutil.rmtree(extract_path, ignore_errors=True)
        # Return styled HTML error that fits in #import-content target
        error_html = (
            '<div class="import-upload-wrapper">'
            '<div class="import-existing-notice">'
            '<p style="color: var(--color-danger, #e74c3c); font-weight: 600;">'
            'The uploaded file is not a valid ZIP archive.</p>'
            '<p style="margin-top: 0.5rem; color: var(--color-text-muted, #888);">'
            'Please select a valid .zip file and try again.</p>'
            '<div class="import-existing-actions">'
            '<button onclick="location.reload()" class="btn btn-primary">Try Again</button>'
            '</div></div></div>'
        )
        return HTMLResponse(content=error_html, status_code=400)

    logger.info("Vault uploaded and extracted: %s (%s)", import_id, file.filename)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "obsidian/partials/scan_trigger.html",
        {"request": request, "import_id": import_id},
    )


@router.post("/scan/{import_id}")
async def trigger_scan(
    request: Request,
    import_id: str,
    user: User = Depends(get_current_user),
):
    """Trigger vault scan and return results partial."""
    parts = import_id.split("_", 1)
    if len(parts) != 2 or parts[0] != str(user.id):
        raise HTTPException(403, "Access denied")

    timestamp = parts[1]
    import_dir = _user_imports_dir(user) / timestamp
    extract_path = import_dir / "vault"

    if not extract_path.is_dir():
        raise HTTPException(404, "Import not found or already discarded")

    # Delete stale mapping config on re-scan
    mapping_path = import_dir / "mapping_config.json"
    if mapping_path.exists():
        mapping_path.unlink()

    # Create broadcast for this scan
    broadcast = ScanBroadcast()
    _broadcasts[import_id] = broadcast

    try:
        scanner = VaultScanner(extract_path, import_id, broadcast)
        result = await scanner.scan()

        # Persist result as JSON
        result_path = import_dir / "scan_result.json"
        result_path.write_text(json.dumps(result.to_dict(), indent=2))

        logger.info(
            "Vault scan complete: %s — %d markdown, %d attachments, %d types",
            import_id,
            result.markdown_files,
            result.attachment_files,
            len(result.type_groups),
        )

        templates = request.app.state.templates
        return templates.TemplateResponse(
            request,
            "obsidian/partials/scan_results.html",
            {"request": request, "scan_result": result, "import_id": import_id},
        )
    finally:
        _broadcasts.pop(import_id, None)


@router.get("/scan/{import_id}/stream")
async def scan_stream(
    import_id: str,
    user: User = Depends(get_current_user),
):
    """SSE stream for scan progress events."""
    parts = import_id.split("_", 1)
    if len(parts) != 2 or parts[0] != str(user.id):
        raise HTTPException(403, "Access denied")

    broadcast = _broadcasts.get(import_id)
    if not broadcast:
        # No active scan — return empty stream
        async def empty():
            yield "event: scan_error\ndata: {\"message\": \"No active scan\"}\n\n"
        return StreamingResponse(empty(), media_type="text/event-stream")

    queue = broadcast.subscribe()
    try:
        return StreamingResponse(
            stream_sse(queue),
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


@router.post("/{import_id}/discard")
async def discard_import(
    request: Request,
    import_id: str,
    user: User = Depends(get_current_user),
):
    """Remove entire import directory and return upload form."""
    parts = import_id.split("_", 1)
    if len(parts) != 2 or parts[0] != str(user.id):
        raise HTTPException(403, "Access denied")

    timestamp = parts[1]
    import_dir = _user_imports_dir(user) / timestamp

    if import_dir.is_dir():
        await asyncio.to_thread(shutil.rmtree, import_dir)
        logger.info("Import discarded: %s", import_id)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "obsidian/partials/upload_form.html",
        {"request": request},
    )


@router.get("/{import_id}/results")
async def get_results(
    request: Request,
    import_id: str,
    user: User = Depends(get_current_user),
):
    """Return persisted scan results (for re-rendering after page refresh)."""
    parts = import_id.split("_", 1)
    if len(parts) != 2 or parts[0] != str(user.id):
        raise HTTPException(403, "Access denied")

    timestamp = parts[1]
    import_dir = _user_imports_dir(user) / timestamp
    result_path = import_dir / "scan_result.json"

    if not result_path.exists():
        raise HTTPException(404, "Scan results not found")

    result = VaultScanResult.from_dict(json.loads(result_path.read_text()))

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "obsidian/partials/scan_results.html",
        {"request": request, "scan_result": result, "import_id": import_id},
    )


# ---------------------------------------------------------------------------
# Helper functions for mapping wizard
# ---------------------------------------------------------------------------


def _get_import_dir(user: User, import_id: str) -> Path:
    """Validate import_id ownership and return import directory path."""
    parts = import_id.split("_", 1)
    if len(parts) != 2 or parts[0] != str(user.id):
        raise HTTPException(403, "Access denied")
    return _user_imports_dir(user) / parts[1]


def _load_scan_result(import_dir: Path) -> VaultScanResult:
    """Load scan_result.json from import directory."""
    result_path = import_dir / "scan_result.json"
    if not result_path.exists():
        raise HTTPException(404, "Scan results not found")
    return VaultScanResult.from_dict(json.loads(result_path.read_text()))


def _load_mapping(import_dir: Path) -> MappingConfig:
    """Load mapping_config.json, returning empty MappingConfig if missing."""
    mapping_path = import_dir / "mapping_config.json"
    if mapping_path.exists():
        return MappingConfig.from_dict(json.loads(mapping_path.read_text()))
    return MappingConfig()


def _save_mapping(import_dir: Path, config: MappingConfig) -> None:
    """Write mapping_config.json to import directory."""
    mapping_path = import_dir / "mapping_config.json"
    mapping_path.write_text(json.dumps(config.to_dict(), indent=2))


# ---------------------------------------------------------------------------
# Wizard step endpoints (GET, return HTML partials)
# ---------------------------------------------------------------------------


@router.get("/{import_id}/step/type-mapping")
async def type_mapping_step(
    request: Request,
    import_id: str,
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
):
    """Serve the type-mapping wizard step."""
    import_dir = _get_import_dir(user, import_id)
    scan_result = _load_scan_result(import_dir)
    mapping_config = _load_mapping(import_dir)
    available_types = await shapes_service.get_types()

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "obsidian/partials/type_mapping.html",
        {
            "request": request,
            "scan_result": scan_result,
            "mapping_config": mapping_config,
            "available_types": available_types,
            "import_id": import_id,
            "current_step": 3,
        },
    )


@router.get("/{import_id}/step/property-mapping")
async def property_mapping_step(
    request: Request,
    import_id: str,
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
):
    """Serve the property-mapping wizard step."""
    import_dir = _get_import_dir(user, import_id)
    scan_result = _load_scan_result(import_dir)
    mapping_config = _load_mapping(import_dir)

    # Build per-type property data: merge groups mapped to same type
    # Template expects: type_sections[type_iri] = {label, properties, frontmatter_keys}
    # where frontmatter_keys is a list of objects with .key, .count, .sample_values
    type_sections: dict[str, dict] = {}
    for group_key, tm in mapping_config.type_mappings.items():
        if tm is None:
            continue
        type_iri = tm.target_type_iri
        if type_iri not in type_sections:
            form = await shapes_service.get_form_for_type(type_iri)
            type_sections[type_iri] = {
                "label": tm.target_type_label,
                "properties": form.properties if form else [],
                "frontmatter_keys": {},  # key -> {count, sample_values} (dict for merging)
            }
        # Find the group in scan_result to get its frontmatter_keys
        parts = group_key.split("|", 1)
        if len(parts) == 2:
            type_name, signal = parts
            for g in scan_result.type_groups:
                if g.type_name == type_name and g.signal_source == signal:
                    for fk in g.frontmatter_keys:
                        existing = type_sections[type_iri]["frontmatter_keys"]
                        if fk.key in existing:
                            existing[fk.key]["count"] += fk.count
                            combined = existing[fk.key]["sample_values"]
                            for sv in fk.sample_values:
                                if sv not in combined and len(combined) < 5:
                                    combined.append(sv)
                        else:
                            existing[fk.key] = {
                                "count": fk.count,
                                "sample_values": list(fk.sample_values),
                            }
                    break

    # Convert frontmatter_keys from dict to list of objects for template iteration
    for type_iri, section in type_sections.items():
        fk_dict = section["frontmatter_keys"]
        section["frontmatter_keys"] = [
            {"key": k, "count": v["count"], "sample_values": v["sample_values"]}
            for k, v in fk_dict.items()
        ]

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "obsidian/partials/property_mapping.html",
        {
            "request": request,
            "type_sections": type_sections,
            "mapping_config": mapping_config,
            "import_id": import_id,
            "current_step": 4,
        },
    )


@router.get("/{import_id}/step/preview")
async def preview_step(
    request: Request,
    import_id: str,
    user: User = Depends(get_current_user),
):
    """Serve the preview wizard step with sample note transformations."""
    import_dir = _get_import_dir(user, import_id)
    scan_result = _load_scan_result(import_dir)
    mapping_config = _load_mapping(import_dir)

    import frontmatter as fm_lib

    previews = []  # [{type_label, notes: [{path, properties: [{key, value}], has_body}]}]
    extract_path = Path(scan_result.extract_path)

    for group_key, tm in mapping_config.type_mappings.items():
        if tm is None:
            continue
        type_iri = tm.target_type_iri
        prop_map = mapping_config.property_mappings.get(type_iri, {})

        # Find sample notes from matching group
        parts = group_key.split("|", 1)
        sample_notes = []
        if len(parts) == 2:
            type_name, signal = parts
            for g in scan_result.type_groups:
                if g.type_name == type_name and g.signal_source == signal:
                    sample_notes = g.sample_notes[:3]
                    break

        notes = []
        for note_path in sample_notes:
            full_path = extract_path / note_path
            if not full_path.exists():
                # Try with vault subdirectory
                for child in extract_path.iterdir():
                    candidate = child / note_path
                    if candidate.exists():
                        full_path = candidate
                        break
            try:
                post = fm_lib.load(str(full_path))
                meta = post.metadata or {}
                body = post.content or ""
            except Exception:
                meta = {}
                body = ""

            properties = []
            for fm_key, pm in prop_map.items():
                if pm is not None and fm_key in meta:
                    properties.append({
                        "key": pm.target_property_label,
                        "value": str(meta[fm_key])[:200],
                    })

            notes.append({
                "path": note_path,
                "properties": properties,
                "has_body": bool(body.strip()),
            })

        if notes:
            previews.append({
                "type_label": tm.target_type_label,
                "type_iri": type_iri,
                "notes": notes,
            })

    templates = request.app.state.templates
    block_name = "content" if request.headers.get("HX-Request") == "true" else None
    return templates.TemplateResponse(
        request,
        "obsidian/partials/preview.html",
        {
            "request": request,
            "previews": previews,
            "import_id": import_id,
            "current_step": 5,
        },
        block_name=block_name,
    )


# ---------------------------------------------------------------------------
# Import execution endpoints
# ---------------------------------------------------------------------------


@router.post("/{import_id}/execute")
async def import_execute(
    request: Request,
    import_id: str,
    user: User = Depends(get_current_user),
):
    """Trigger import execution and return progress UI partial."""
    import_dir = _get_import_dir(user, import_id)
    scan_result = _load_scan_result(import_dir)
    mapping_config = _load_mapping(import_dir)
    extract_path = Path(scan_result.extract_path)

    # Get dependencies from app state
    event_store = request.app.state.event_store
    triplestore_client = request.app.state.triplestore_client

    # Create broadcast for this import (distinct key from scan)
    broadcast = ScanBroadcast()
    broadcast_key = f"{import_id}_import"
    _broadcasts[broadcast_key] = broadcast

    executor = ImportExecutor(
        scan_result=scan_result,
        mapping_config=mapping_config,
        extract_path=extract_path,
        event_store=event_store,
        triplestore_client=triplestore_client,
        user=user,
        broadcast=broadcast,
        import_dir=import_dir,
    )

    async def _run_import():
        try:
            await executor.execute()
        finally:
            _broadcasts.pop(broadcast_key, None)

    asyncio.create_task(_run_import())

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "obsidian/partials/import_progress.html",
        {"request": request, "import_id": import_id, "current_step": 6},
    )


@router.get("/{import_id}/execute/stream")
async def import_stream(
    import_id: str,
    user: User = Depends(get_current_user),
):
    """SSE stream for import progress events."""
    parts = import_id.split("_", 1)
    if len(parts) != 2 or parts[0] != str(user.id):
        raise HTTPException(403, "Access denied")

    broadcast_key = f"{import_id}_import"
    broadcast = _broadcasts.get(broadcast_key)
    if not broadcast:
        # Import may have already completed before SSE connected (race condition)
        import_dir = _get_import_dir(user, import_id)
        result_path = import_dir / "import_result.json"
        if result_path.exists():
            result_data = json.loads(result_path.read_text())
            async def completed():
                yield f'event: import_complete\ndata: {json.dumps(result_data)}\n\n'
            return StreamingResponse(completed(), media_type="text/event-stream")
        async def empty():
            yield 'event: import_error\ndata: {"message": "No active import"}\n\n'
        return StreamingResponse(empty(), media_type="text/event-stream")

    queue = broadcast.subscribe()
    try:
        return StreamingResponse(
            stream_sse(
                queue,
                terminal_events={"import_complete", "import_error"},
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


@router.get("/{import_id}/summary")
async def import_summary(
    request: Request,
    import_id: str,
    user: User = Depends(get_current_user),
):
    """Return post-import summary with nav refresh trigger."""
    import_dir = _get_import_dir(user, import_id)
    result_path = import_dir / "import_result.json"

    if not result_path.exists():
        raise HTTPException(404, "Import results not found")

    result_data = json.loads(result_path.read_text())
    scan_result = _load_scan_result(import_dir)

    templates = request.app.state.templates
    response = templates.TemplateResponse(
        request,
        "obsidian/partials/import_summary.html",
        {
            "request": request,
            "import_result": result_data,
            "scan_result": scan_result,
            "import_id": import_id,
        },
    )
    response.headers["HX-Trigger"] = "sempkm:nav-refresh"
    return response


# ---------------------------------------------------------------------------
# Auto-save endpoints (POST)
# ---------------------------------------------------------------------------


@router.post("/{import_id}/mapping/type")
async def save_type_mapping(
    request: Request,
    import_id: str,
    group_key: str = Form(...),
    target_type: str = Form(""),
    target_label: str = Form(""),
    user: User = Depends(get_current_user),
):
    """Auto-save a single type mapping."""
    import_dir = _get_import_dir(user, import_id)
    config = _load_mapping(import_dir)

    if target_type:
        config.type_mappings[group_key] = TypeMapping(
            target_type_iri=target_type,
            target_type_label=target_label or target_type,
        )
    else:
        config.type_mappings[group_key] = None

    _save_mapping(import_dir, config)
    return HTMLResponse("")


@router.post("/{import_id}/mapping/property")
async def save_property_mapping(
    request: Request,
    import_id: str,
    type_iri: str = Form(...),
    fm_key: str = Form(...),
    target_property: str = Form(""),
    property_label: str = Form(""),
    source: str = Form("shacl"),
    user: User = Depends(get_current_user),
):
    """Auto-save a single property mapping."""
    import_dir = _get_import_dir(user, import_id)
    config = _load_mapping(import_dir)

    if type_iri not in config.property_mappings:
        config.property_mappings[type_iri] = {}

    if target_property:
        config.property_mappings[type_iri][fm_key] = PropertyMapping(
            target_property_iri=target_property,
            target_property_label=property_label or target_property,
            source=source,
        )
    else:
        config.property_mappings[type_iri][fm_key] = None

    _save_mapping(import_dir, config)
    return HTMLResponse("")
