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

from app.auth.dependencies import get_current_user
from app.auth.models import User

from .broadcast import ScanBroadcast, stream_sse
from .models import VaultScanResult
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
            zf.extractall(extract_path, filter="data")

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
