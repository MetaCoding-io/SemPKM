"""Notion workspace import router.

Provides endpoints for uploading, scanning, streaming progress,
viewing results, mapping wizard steps, auto-save, and discarding
Notion workspace ZIP imports.
Follows the same htmx-driven wizard pattern as the Obsidian importer.
"""

import asyncio
import json
import logging
import shutil
import zipfile
from pathlib import Path
from time import time

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.dependencies import get_shapes_service
from app.services.shapes import ShapesService

from .broadcast import ScanBroadcast, stream_sse
from .models import MappingConfig, NotionScanResult, PropertyMapping, RelationMapping, TypeMapping
from .scanner import NotionScanner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/browser/notion", tags=["notion-import"])

# Shared importer context variables used by shared templates in importer/partials/
_IMPORTER_CTX = {
    "steps": [
        (1, "Upload"),
        (2, "Scan"),
        (3, "Types"),
        (4, "Properties"),
        (5, "Relations"),
        (6, "Preview"),
        (7, "Import"),
    ],
    "url_prefix": "/browser/notion",
    "file_input_id": "notion-zip",
    "upload_title": "Upload your Notion workspace as a ZIP file",
    "upload_hint": "Export from Notion: Settings \u2192 Export all workspace content \u2192 Markdown &amp; CSV format",
    "importer_label": "Notion",
    "importer_name": "Notion workspace",
    "progress_step": 7,
    "summary_step": 7,
    "edge_label": "relations",
    "import_page_url": "/browser/notion/import",
    "discard_button_text": "Files",
    "discard_confirm_text": "workspace files",
}

# Active broadcast instances keyed by import_id
_broadcasts: dict[str, ScanBroadcast] = {}

# Base directory for Notion imports
IMPORTS_DIR = Path("/app/data/imports/notion")


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


def _get_import_dir(user: User, import_id: str) -> Path:
    """Validate import_id ownership and return import directory path."""
    parts = import_id.split("_", 1)
    if len(parts) != 2 or parts[0] != str(user.id):
        raise HTTPException(403, "Access denied")
    return _user_imports_dir(user) / parts[1]


def _load_scan_result(import_dir: Path) -> NotionScanResult:
    """Load scan_result.json from import directory."""
    result_path = import_dir / "scan_result.json"
    if not result_path.exists():
        raise HTTPException(404, "Scan results not found")
    return NotionScanResult.from_dict(json.loads(result_path.read_text()))


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


@router.get("/import")
async def import_page(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Serve the Notion import page (full page or htmx partial)."""
    templates = request.app.state.templates

    existing = _find_existing_import(user)
    context: dict = {"request": request, "user": user, **_IMPORTER_CTX}

    if existing:
        import_id, import_path = existing
        scan_result_path = import_path / "scan_result.json"
        if scan_result_path.exists():
            result = NotionScanResult.from_dict(
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
        "notion/import.html",
        context,
        block_name=block_name,
    )


@router.post("/upload")
async def upload_notion(
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

    zip_path = import_dir / "workspace.zip"
    extract_path = import_dir / "workspace"
    extract_path.mkdir(exist_ok=True)

    def _write_and_extract():
        with open(zip_path, "wb") as f:
            while True:
                chunk = file.file.read(8192)
                if not chunk:
                    break
                f.write(chunk)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_path)

        # Remove ZIP after extraction to save disk space
        zip_path.unlink(missing_ok=True)

    try:
        await asyncio.to_thread(_write_and_extract)
    except zipfile.BadZipFile:
        zip_path.unlink(missing_ok=True)
        shutil.rmtree(extract_path, ignore_errors=True)
        error_html = (
            '<div class="import-upload-wrapper">'
            '<div class="import-existing-notice">'
            '<p style="color: var(--color-danger, #e74c3c); font-weight: 600;">'
            'The uploaded file is not a valid ZIP archive.</p>'
            '<p style="margin-top: 0.5rem; color: var(--color-text-muted, #888);">'
            'Please select a valid .zip file exported from Notion and try again.</p>'
            '<div class="import-existing-actions">'
            '<button onclick="location.reload()" class="btn btn-primary">Try Again</button>'
            '</div></div></div>'
        )
        return HTMLResponse(content=error_html, status_code=400)

    logger.info("Notion workspace uploaded and extracted: %s (%s)", import_id, file.filename)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "importer/partials/scan_trigger.html",
        {"request": request, "import_id": import_id, **_IMPORTER_CTX},
    )


@router.post("/scan/{import_id}")
async def trigger_scan(
    request: Request,
    import_id: str,
    user: User = Depends(get_current_user),
):
    """Trigger Notion workspace scan and return results partial."""
    parts = import_id.split("_", 1)
    if len(parts) != 2 or parts[0] != str(user.id):
        raise HTTPException(403, "Access denied")

    timestamp = parts[1]
    import_dir = _user_imports_dir(user) / timestamp
    extract_path = import_dir / "workspace"

    if not extract_path.is_dir():
        raise HTTPException(404, "Import not found or already discarded")

    # Create broadcast for this scan
    broadcast = ScanBroadcast()
    _broadcasts[import_id] = broadcast

    try:
        scanner = NotionScanner(extract_path, import_id, broadcast)
        result = await scanner.scan()

        # Persist result as JSON
        result_path = import_dir / "scan_result.json"
        result_path.write_text(json.dumps(result.to_dict(), indent=2))

        logger.info(
            "Notion scan complete: %s — %d databases, %d standalone pages, %d relations, %d warnings",
            import_id,
            len(result.databases),
            len(result.standalone_pages),
            len(result.detected_relations),
            len(result.warnings),
        )

        templates = request.app.state.templates
        # Pre-group warnings by category for the template
        warning_categories: dict[str, list] = {}
        for w in result.warnings:
            warning_categories.setdefault(w.category, []).append(w)
        return templates.TemplateResponse(
            request,
            "notion/partials/scan_results.html",
            {"request": request, "scan_result": result, "import_id": import_id, "warning_categories": warning_categories, **_IMPORTER_CTX},
        )
    finally:
        _broadcasts.pop(import_id, None)


@router.get("/scan/{import_id}/stream")
async def scan_stream(
    request: Request,
    import_id: str,
    user: User = Depends(get_current_user),
):
    """SSE stream for scan progress events."""
    parts = import_id.split("_", 1)
    if len(parts) != 2 or parts[0] != str(user.id):
        raise HTTPException(403, "Access denied")

    broadcast = _broadcasts.get(import_id)
    if not broadcast:
        async def empty():
            yield "event: scan_error\ndata: {\"message\": \"No active scan\"}\n\n"
        return StreamingResponse(empty(), media_type="text/event-stream")

    queue = broadcast.subscribe()
    try:
        return StreamingResponse(
            stream_sse(queue, shutdown_event=request.app.state.shutdown_event),
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
        logger.info("Notion import discarded: %s", import_id)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "importer/partials/upload_form.html",
        {"request": request, **_IMPORTER_CTX},
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

    result = NotionScanResult.from_dict(json.loads(result_path.read_text()))

    templates = request.app.state.templates
    # Pre-group warnings by category for the template
    warning_categories: dict[str, list] = {}
    for w in result.warnings:
        warning_categories.setdefault(w.category, []).append(w)
    return templates.TemplateResponse(
        request,
        "notion/partials/scan_results.html",
        {"request": request, "scan_result": result, "import_id": import_id, "warning_categories": warning_categories, **_IMPORTER_CTX},
    )


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
    """Serve the type-mapping wizard step (step 3)."""
    import_dir = _get_import_dir(user, import_id)
    scan_result = _load_scan_result(import_dir)
    mapping_config = _load_mapping(import_dir)
    available_types = await shapes_service.get_types()

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "notion/partials/type_mapping.html",
        {
            "request": request,
            "scan_result": scan_result,
            "mapping_config": mapping_config,
            "available_types": available_types,
            "import_id": import_id,
            "current_step": 3,
            **_IMPORTER_CTX,
        },
    )


@router.get("/{import_id}/step/property-mapping")
async def property_mapping_step(
    request: Request,
    import_id: str,
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
):
    """Serve the property-mapping wizard step (step 4).

    Merges columns from all databases mapped to the same type and
    excludes columns with inferred_type == 'relation' (those go to
    the relation mapping step instead).
    """
    import_dir = _get_import_dir(user, import_id)
    scan_result = _load_scan_result(import_dir)
    mapping_config = _load_mapping(import_dir)

    # Build per-type column data: merge databases mapped to the same type.
    # type_sections[type_iri] = {label, properties (from SHACL), columns (merged)}
    type_sections: dict[str, dict] = {}

    for db_name, tm in mapping_config.type_mappings.items():
        if tm is None:
            continue
        type_iri = tm.target_type_iri

        if type_iri not in type_sections:
            form = await shapes_service.get_form_for_type(type_iri)
            type_sections[type_iri] = {
                "label": tm.target_type_label,
                "properties": form.properties if form else [],
                "columns": {},  # col_name -> {non_empty_count, sample_values}
            }

        # Find the database in scan_result
        for db in scan_result.databases:
            if db.name == db_name:
                for col in db.columns:
                    # Exclude relation columns — they go to relation mapping
                    if col.inferred_type == "relation":
                        continue
                    existing = type_sections[type_iri]["columns"]
                    if col.name in existing:
                        # Keep the higher non_empty_count
                        if col.non_empty_count > existing[col.name]["non_empty_count"]:
                            existing[col.name]["non_empty_count"] = col.non_empty_count
                        # Merge sample values
                        combined = existing[col.name]["sample_values"]
                        for sv in col.sample_values:
                            if sv not in combined and len(combined) < 5:
                                combined.append(sv)
                    else:
                        existing[col.name] = {
                            "non_empty_count": col.non_empty_count,
                            "sample_values": list(col.sample_values),
                        }
                break

    # Convert columns dict to list for template iteration
    for type_iri, section in type_sections.items():
        col_dict = section["columns"]
        section["columns"] = [
            {
                "name": name,
                "non_empty_count": info["non_empty_count"],
                "sample_values": info["sample_values"],
            }
            for name, info in col_dict.items()
        ]

    # Pre-compute auto-matches: for each type+column pair, find the SHACL property
    # whose label matches the column name (case-insensitive). Eliminates namespace() in template.
    auto_matches: dict[str, dict[str, str]] = {}
    for type_iri, section in type_sections.items():
        prop_mappings = mapping_config.property_mappings.get(type_iri, {})
        type_matches: dict[str, str] = {}
        for col in section["columns"]:
            if col["name"] not in prop_mappings:
                for prop in section.get("properties", []):
                    if prop.name.lower() == col["name"].lower():
                        type_matches[col["name"]] = prop.path
                        break
        auto_matches[type_iri] = type_matches

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "notion/partials/property_mapping.html",
        {
            "request": request,
            "type_sections": type_sections,
            "mapping_config": mapping_config,
            "import_id": import_id,
            "current_step": 4,
            "auto_matches": auto_matches,
            **_IMPORTER_CTX,
        },
    )


@router.get("/{import_id}/step/relation-mapping")
async def relation_mapping_step(
    request: Request,
    import_id: str,
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
):
    """Serve the relation-mapping wizard step (step 5).

    For each detected relation, looks up the target database's mapped
    type to find available edge predicates from its SHACL shape.
    """
    import_dir = _get_import_dir(user, import_id)
    scan_result = _load_scan_result(import_dir)
    mapping_config = _load_mapping(import_dir)

    relation_entries = []
    for rel in scan_result.detected_relations:
        relation_key = f"{rel.source_db_name}|{rel.source_column}"

        # Check if target DB is mapped to a type
        target_tm = mapping_config.type_mappings.get(rel.target_db_name)
        available_predicates = []
        warning = False

        if target_tm is not None:
            form = await shapes_service.get_form_for_type(target_tm.target_type_iri)
            if form:
                # Object properties (those with target_class) are edge predicates
                available_predicates = [
                    {
                        "iri": prop.path,
                        "label": prop.name,
                        "target_class": prop.target_class,
                    }
                    for prop in form.properties
                    if prop.target_class is not None
                ]
        else:
            warning = True

        # Also check the source DB's mapped type for outgoing predicates
        source_tm = mapping_config.type_mappings.get(rel.source_db_name)
        if source_tm is not None:
            source_form = await shapes_service.get_form_for_type(
                source_tm.target_type_iri
            )
            if source_form:
                for prop in source_form.properties:
                    if prop.target_class is not None:
                        # Avoid duplicates
                        existing_iris = {p["iri"] for p in available_predicates}
                        if prop.path not in existing_iris:
                            available_predicates.append(
                                {
                                    "iri": prop.path,
                                    "label": prop.name,
                                    "target_class": prop.target_class,
                                }
                            )

        current_mapping = mapping_config.relation_mappings.get(relation_key)

        relation_entries.append(
            {
                "key": relation_key,
                "source_db_name": rel.source_db_name,
                "source_column": rel.source_column,
                "target_db_name": rel.target_db_name,
                "match_ratio": rel.match_ratio,
                "available_predicates": available_predicates,
                "warning": warning,
                "current_mapping": current_mapping,
            }
        )

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "notion/partials/relation_mapping.html",
        {
            "request": request,
            "relation_entries": relation_entries,
            "mapping_config": mapping_config,
            "import_id": import_id,
            "current_step": 5,
            **_IMPORTER_CTX,
        },
    )


@router.get("/{import_id}/step/preview")
async def preview_step(
    request: Request,
    import_id: str,
    user: User = Depends(get_current_user),
):
    """Serve the preview wizard step (step 6).

    Builds sample preview cards showing how scan data will map to
    RDF objects with properties and edges applied.
    """
    import_dir = _get_import_dir(user, import_id)
    scan_result = _load_scan_result(import_dir)
    mapping_config = _load_mapping(import_dir)

    previews = []

    for db in scan_result.databases:
        tm = mapping_config.type_mappings.get(db.name)
        if tm is None:
            continue

        type_iri = tm.target_type_iri
        prop_map = mapping_config.property_mappings.get(type_iri, {})

        sample_objects = []
        for row in db.sample_rows[:3]:
            mapped_properties = []
            mapped_relations = []

            for col_name, value in row.items():
                if not value:
                    continue

                # Check property mapping
                pm = prop_map.get(col_name)
                if pm is not None:
                    mapped_properties.append(
                        {
                            "label": pm.target_property_label,
                            "value": value,
                            "source": pm.source,
                        }
                    )
                    continue

                # Check relation mapping
                rel_key = f"{db.name}|{col_name}"
                rm = mapping_config.relation_mappings.get(rel_key)
                if rm is not None:
                    mapped_relations.append(
                        {
                            "predicate_label": rm.target_predicate_label,
                            "target_type_label": rm.target_type_label,
                            "value": value,
                        }
                    )

            # Use first column value as title if available
            title = list(row.values())[0] if row else "(untitled)"
            sample_objects.append(
                {
                    "title": title,
                    "properties": mapped_properties,
                    "relations": mapped_relations,
                }
            )

        previews.append(
            {
                "db_name": db.name,
                "type_label": tm.target_type_label,
                "type_iri": type_iri,
                "sample_objects": sample_objects,
                "total_rows": db.row_count,
            }
        )

    # Standalone pages preview
    standalone_preview = None
    if (
        mapping_config.standalone_page_type_iri
        and scan_result.standalone_pages
    ):
        standalone_preview = {
            "type_label": mapping_config.standalone_page_type_label
            or "Standalone Page",
            "type_iri": mapping_config.standalone_page_type_iri,
            "pages": [
                {"title": p.title, "has_body": p.has_body}
                for p in scan_result.standalone_pages[:5]
            ],
            "total_count": len(scan_result.standalone_pages),
        }

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "notion/partials/preview.html",
        {
            "request": request,
            "previews": previews,
            "standalone_preview": standalone_preview,
            "import_id": import_id,
            "current_step": 6,
            **_IMPORTER_CTX,
        },
    )


# ---------------------------------------------------------------------------
# Auto-save endpoints (POST, persist individual mapping entries)
# ---------------------------------------------------------------------------


@router.post("/{import_id}/mapping/type")
async def save_type_mapping(
    request: Request,
    import_id: str,
    db_name: str = Form(...),
    target_type: str = Form(""),
    target_label: str = Form(""),
    user: User = Depends(get_current_user),
):
    """Auto-save a single database → type mapping."""
    import_dir = _get_import_dir(user, import_id)
    config = _load_mapping(import_dir)

    if target_type:
        config.type_mappings[db_name] = TypeMapping(
            target_type_iri=target_type,
            target_type_label=target_label,
        )
    else:
        config.type_mappings[db_name] = None

    _save_mapping(import_dir, config)
    logger.debug("Saved type mapping: %s → %s", db_name, target_type or "(skip)")
    return HTMLResponse("")


@router.post("/{import_id}/mapping/property")
async def save_property_mapping(
    request: Request,
    import_id: str,
    type_iri: str = Form(...),
    column_name: str = Form(...),
    target_property: str = Form(""),
    property_label: str = Form(""),
    source: str = Form("shacl"),
    custom_iri: str = Form(""),
    user: User = Depends(get_current_user),
):
    """Auto-save a single column → property mapping."""
    import_dir = _get_import_dir(user, import_id)
    config = _load_mapping(import_dir)

    if type_iri not in config.property_mappings:
        config.property_mappings[type_iri] = {}

    if target_property == "__custom__" and custom_iri:
        config.property_mappings[type_iri][column_name] = PropertyMapping(
            target_property_iri=custom_iri,
            target_property_label=property_label,
            source="custom",
        )
    elif target_property and target_property != "__custom__":
        config.property_mappings[type_iri][column_name] = PropertyMapping(
            target_property_iri=target_property,
            target_property_label=property_label,
            source=source,
        )
    else:
        config.property_mappings[type_iri][column_name] = None

    _save_mapping(import_dir, config)
    logger.debug(
        "Saved property mapping: %s.%s → %s",
        type_iri,
        column_name,
        target_property or "(skip)",
    )
    return HTMLResponse("")


@router.post("/{import_id}/mapping/relation")
async def save_relation_mapping(
    request: Request,
    import_id: str,
    relation_key: str = Form(...),
    target_predicate: str = Form(""),
    predicate_label: str = Form(""),
    target_type_iri: str = Form(""),
    target_type_label: str = Form(""),
    user: User = Depends(get_current_user),
):
    """Auto-save a single relation → edge predicate mapping."""
    import_dir = _get_import_dir(user, import_id)
    config = _load_mapping(import_dir)

    if target_predicate:
        config.relation_mappings[relation_key] = RelationMapping(
            target_predicate_iri=target_predicate,
            target_predicate_label=predicate_label,
            target_type_iri=target_type_iri,
            target_type_label=target_type_label,
        )
    else:
        config.relation_mappings[relation_key] = None

    _save_mapping(import_dir, config)
    logger.debug(
        "Saved relation mapping: %s → %s",
        relation_key,
        target_predicate or "(skip)",
    )
    return HTMLResponse("")


@router.post("/{import_id}/mapping/standalone-type")
async def save_standalone_type_mapping(
    request: Request,
    import_id: str,
    target_type: str = Form(""),
    target_label: str = Form(""),
    user: User = Depends(get_current_user),
):
    """Auto-save the standalone pages type mapping."""
    import_dir = _get_import_dir(user, import_id)
    config = _load_mapping(import_dir)

    config.standalone_page_type_iri = target_type or None
    config.standalone_page_type_label = target_label or None

    _save_mapping(import_dir, config)
    logger.debug("Saved standalone type mapping: %s", target_type or "(cleared)")
    return HTMLResponse("")
