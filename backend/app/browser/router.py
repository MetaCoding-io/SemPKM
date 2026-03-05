"""Object browser router serving the IDE-style workspace.

Provides the workspace layout, navigation tree endpoints, object
loading, body saving, related objects, lint panel, type picker,
create/edit object flows, and reference search endpoints for the
three-column IDE workspace. Uses htmx partial rendering for dynamic
content updates.
"""

import logging
from datetime import datetime, timezone
from urllib.parse import unquote, urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from rdflib import URIRef
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.db.session import get_db_session
from app.dependencies import (
    get_event_store,
    get_label_service,
    get_lint_service,
    get_shapes_service,
    get_triplestore_client,
    get_validation_queue,
)
from app.lint.service import LintService
from app.events.store import EventStore
from app.services.icons import IconService
from app.services.labels import LabelService
from app.services.settings import SettingsService
from app.services.shapes import ShapesService
from app.triplestore.client import TriplestoreClient
from app.validation.queue import AsyncValidationQueue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/browser", tags=["browser"])


def _validate_iri(iri: str) -> bool:
    """Validate that a decoded IRI is an absolute URI before SPARQL interpolation.

    Accepts both https://... object IRIs and urn:sempkm:... model/seed IRIs.
    The Basic PKM model uses urn: scheme for all object and type IRIs
    (e.g. urn:sempkm:model:basic-pkm:Note, urn:sempkm:model:basic-pkm:seed-note-arch).

    Blocks SPARQL injection characters (>, <, ", whitespace) that would break
    the SPARQL template interpolation <{decoded_iri}>.
    """
    if not iri:
        return False
    try:
        result = urlparse(iri)
        if not result.scheme:
            return False
        # Reject characters that would break SPARQL angle-bracket quoting
        forbidden = set('<>"\\{}\n\r\t ')
        if any(c in forbidden for c in iri):
            return False
        # https/http IRIs must have a netloc (host)
        if result.scheme in ("http", "https"):
            return bool(result.netloc)
        # urn: IRIs are opaque (no netloc) but valid semantic web IRIs
        if result.scheme == "urn":
            return bool(result.path)
        # Reject unknown schemes
        return False
    except Exception:
        return False


# Models directory path -- mirrors the Docker mount used in main.py
_MODELS_DIR = "/app/models"


def get_settings_service() -> SettingsService:
    """FastAPI dependency that returns a SettingsService with the models directory."""
    return SettingsService(installed_models_dir=_MODELS_DIR)


def get_icon_service() -> IconService:
    """FastAPI dependency that returns an IconService with the models directory."""
    return IconService(models_dir=_MODELS_DIR)


@router.get("/settings")
async def settings_page(
    request: Request,
    user: User = Depends(get_current_user),
    settings_svc: SettingsService = Depends(get_settings_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Render the Settings page as an htmx partial."""
    from collections import defaultdict
    from app.services.llm import LLMConfigService

    templates = request.app.state.templates
    all_settings = await settings_svc.get_all_settings()
    user_overrides = await settings_svc.get_user_overrides(user.id, db)
    resolved = await settings_svc.resolve(user.id, db)

    categories = defaultdict(list)
    for s in all_settings:
        categories[s.category].append(s)

    llm_config = None
    if user.role == "owner":
        llm_svc = LLMConfigService()
        llm_config = await llm_svc.get_config(db)

    auth_service = request.app.state.auth_service
    api_tokens = await auth_service.list_api_tokens(user.id)
    webdav_endpoint = str(request.base_url).rstrip("/") + "/dav/"

    return templates.TemplateResponse(request, "browser/settings_page.html", {
        "request": request,
        "categories": dict(categories),
        "user_overrides": user_overrides,
        "resolved": resolved,
        "all_settings": all_settings,
        "llm_config": llm_config,
        "user": user,
        "api_tokens": api_tokens,
        "webdav_endpoint": webdav_endpoint,
    })


@router.get("/docs")
async def docs_page(
    request: Request,
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Docs & Tutorials hub page rendered as a workspace tab fragment."""
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "browser/docs_page.html", {
        "user": user,
    })


@router.get("/docs/guide/{filename:path}")
async def docs_guide_viewer(
    filename: str,
    request: Request,
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Render a single guide markdown file as a workspace tab fragment."""
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "browser/docs_viewer.html", {
        "user": user,
        "filename": filename,
    })


@router.get("/lint-dashboard")
async def lint_dashboard(
    request: Request,
    page: int = 1,
    severity: str | None = None,
    object_type: str | None = None,
    search: str | None = None,
    sort: str = "severity",
    user: User = Depends(get_current_user),
    lint_service: LintService = Depends(get_lint_service),
    shapes_service: ShapesService = Depends(get_shapes_service),
):
    """Render the global lint dashboard as an htmx partial for the bottom panel."""
    results = await lint_service.get_results(
        page=page, per_page=50, severity=severity,
        object_type=object_type, search=search, sort=sort,
    )
    status = await lint_service.get_status()
    types = await shapes_service.get_types()

    templates = request.app.state.templates
    return templates.TemplateResponse(request, "browser/lint_dashboard.html", {
        "results": results,
        "status": status,
        "types": types,
        "current_severity": severity or "",
        "current_type": object_type or "",
        "current_search": search or "",
        "current_sort": sort,
        "current_page": page,
    })


@router.get("/settings/data")
async def settings_data(
    user: User = Depends(get_current_user),
    settings_svc: SettingsService = Depends(get_settings_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Return resolved settings as JSON for the client-side cache."""
    resolved = await settings_svc.resolve(user.id, db)
    # Never expose the encrypted API key to the browser
    resolved.pop("llm.api_key", None)
    return JSONResponse(content=resolved)


@router.put("/settings/{key:path}")
async def update_setting(
    key: str,
    request: Request,
    user: User = Depends(get_current_user),
    settings_svc: SettingsService = Depends(get_settings_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Upsert a user override. Body: {\"value\": \"...\"}"""
    body = await request.json()
    value = str(body.get("value", ""))
    await settings_svc.set_override(user.id, key, value, db)
    return JSONResponse(content={"key": key, "value": value})


@router.delete("/settings/{key:path}")
async def reset_setting(
    key: str,
    user: User = Depends(get_current_user),
    settings_svc: SettingsService = Depends(get_settings_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a user override, reverting to default."""
    await settings_svc.reset_override(user.id, key, db)
    resolved = await settings_svc.resolve(user.id, db)
    return JSONResponse(content={"key": key, "default_value": resolved.get(key)})


# ── LLM Connection Configuration ─────────────────────────────────────────────

@router.put("/llm/config")
async def save_llm_config(
    request: Request,
    user: User = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db_session),
):
    """Save a single LLM config field. Owner-only — instance-wide setting.
    Body: {"field": "api_base_url"|"api_key"|"default_model", "value": "..."}
    """
    from app.services.llm import LLMConfigService
    body = await request.json()
    field = body.get("field", "")
    value = str(body.get("value", ""))
    allowed = {"api_base_url", "api_key", "default_model"}
    if field in allowed:
        svc = LLMConfigService()
        kwargs: dict = {field: value}
        await svc.save_config(db, **kwargs)
    return JSONResponse(content={"ok": True})


@router.post("/llm/test")
async def test_llm_connection(
    request: Request,
    user: User = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db_session),
):
    """Test the configured LLM connection by calling GET {base_url}/v1/models.
    Returns an HTML fragment for #llm-test-status.
    """
    import httpx
    from app.services.llm import LLMConfigService
    templates = request.app.state.templates
    svc = LLMConfigService()
    config = await svc.get_config(db)
    api_key = await svc.get_decrypted_api_key(db)
    base_url = config["api_base_url"].rstrip("/") if config["api_base_url"] else ""

    if not base_url:
        return templates.TemplateResponse(request, "browser/llm/test_result.html",
            {"request": request, "status": "error", "message": "No API base URL configured."})

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base_url}/v1/models", headers=headers)
        if resp.status_code == 200:
            return templates.TemplateResponse(request, "browser/llm/test_result.html",
                {"request": request, "status": "ok", "message": "Connection successful"})
        else:
            return templates.TemplateResponse(request, "browser/llm/test_result.html",
                {"request": request, "status": "error",
                 "message": f"HTTP {resp.status_code}: {resp.text[:200]}"})
    except httpx.TimeoutException:
        return templates.TemplateResponse(request, "browser/llm/test_result.html",
            {"request": request, "status": "error", "message": "Connection timed out after 10s"})
    except Exception as e:
        return templates.TemplateResponse(request, "browser/llm/test_result.html",
            {"request": request, "status": "error", "message": str(e)[:200]})


@router.post("/llm/models")
async def fetch_llm_models(
    request: Request,
    user: User = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db_session),
):
    """Fetch available models from the configured LLM provider.
    Returns an HTML fragment that replaces #llm-model-select.
    """
    import httpx
    from app.services.llm import LLMConfigService
    templates = request.app.state.templates
    svc = LLMConfigService()
    config = await svc.get_config(db)
    api_key = await svc.get_decrypted_api_key(db)
    base_url = config["api_base_url"].rstrip("/") if config["api_base_url"] else ""
    current_model = config["default_model"]

    models: list[str] = []
    error: str | None = None

    if not base_url:
        error = "No API base URL configured."
    else:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{base_url}/v1/models", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                models = sorted([m["id"] for m in data.get("data", [])])
            else:
                error = f"HTTP {resp.status_code}"
        except Exception as e:
            error = str(e)[:200]

    return templates.TemplateResponse(request, "browser/llm/models_select.html", {
        "request": request,
        "models": models,
        "current_model": current_model,
        "error": error,
    })


@router.post("/llm/chat/stream")
async def llm_chat_stream(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """SSE streaming proxy for LLM chat completions.

    Receives JSON body: {"messages": [...], "model": "optional-override"}
    Fetches the encrypted API key from InstanceConfig, then proxies the
    streaming /v1/chat/completions response to the browser as text/event-stream.

    Accessible to any authenticated user (owner sets config; all users stream).
    """
    import httpx
    from fastapi.responses import StreamingResponse
    from app.services.llm import LLMConfigService

    svc = LLMConfigService()
    config = await svc.get_config(db)
    api_key = await svc.get_decrypted_api_key(db)
    base_url = config["api_base_url"].rstrip("/") if config["api_base_url"] else ""

    if not base_url:
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


@router.get("/icons")
async def icons_data(
    request: Request,
    user: User = Depends(get_current_user),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Return icon map for all contexts as JSON for client-side caching."""
    return JSONResponse(content={
        "tree": icon_svc.get_icon_map("tree"),
        "tab": icon_svc.get_icon_map("tab"),
        "graph": icon_svc.get_icon_map("graph"),
    })


def _format_date(value: str) -> str:
    """Format ISO date string to human-readable: 'Feb 23, 2026'."""
    try:
        dt = datetime.fromisoformat(str(value))
        return dt.strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return str(value)


def _is_htmx_request(request: Request) -> bool:
    """Check if the request is an htmx partial request."""
    return request.headers.get("HX-Request") == "true"


@router.get("/")
async def workspace(
    request: Request,
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Render the IDE-style workspace with three-column layout.

    Queries available object types from ShapesService for the navigation
    tree. Full page for direct navigation, content block only for htmx.
    """
    templates = request.app.state.templates
    types = await shapes_service.get_types()
    type_icons = icon_svc.get_icon_map(context="tree")
    from app.config import settings

    context = {
        "request": request,
        "types": types,
        "type_icons": type_icons,
        "active_page": "browser",
        "user": user,
        "base_namespace": settings.base_namespace,
    }

    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request, "browser/workspace.html", context, block_name="content"
        )
    return templates.TemplateResponse(request, "browser/workspace.html", context)


@router.get("/tree/{type_iri:path}")
async def tree_children(
    request: Request,
    type_iri: str,
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
    label_service: LabelService = Depends(get_label_service),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Load objects of a given type for the navigation tree.

    Queries the current graph for instances of the specified type,
    resolves labels via LabelService, and returns tree leaf nodes
    as an htmx partial.
    """
    templates = request.app.state.templates
    client = request.app.state.triplestore_client
    decoded_iri = unquote(type_iri)
    if not _validate_iri(decoded_iri):
        raise HTTPException(status_code=400, detail="Invalid IRI")

    sparql = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?obj WHERE {{
      GRAPH <urn:sempkm:current> {{
        ?obj rdf:type <{decoded_iri}> .
      }}
    }}
    """

    try:
        result = await client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception:
        logger.warning("Failed to query objects for type %s", decoded_iri, exc_info=True)
        bindings = []

    obj_iris = [b["obj"]["value"] for b in bindings]
    labels = await label_service.resolve_batch(obj_iris) if obj_iris else {}

    objects = [
        {"iri": iri, "label": labels.get(iri, iri)}
        for iri in obj_iris
    ]

    type_icon = icon_svc.get_type_icon(decoded_iri, context="tree")

    # Resolve type label for nav tree tooltip (phase 19-02)
    type_labels = await label_service.resolve_batch([decoded_iri])
    type_label = type_labels.get(decoded_iri, "")

    context = {"request": request, "objects": objects, "type_icon": type_icon, "type_label": type_label}
    return templates.TemplateResponse(
        request, "browser/tree_children.html", context
    )


@router.get("/object/{object_iri:path}")
async def get_object(
    request: Request,
    object_iri: str,
    mode: str = Query(default="read"),
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
    label_service: LabelService = Depends(get_label_service),
    client: TriplestoreClient = Depends(get_triplestore_client),
    icon_svc: IconService = Depends(get_icon_service),
):
    """Render an object in the editor area with read-only view or edit form.

    Queries the object's current property values and body text from the
    triplestore, resolves its type, fetches SHACL form metadata, resolves
    reference labels and tooltips, and renders the object_tab.html with
    flip container for read/edit mode switching.
    """
    templates = request.app.state.templates
    # Register the format_date filter if not already present
    templates.env.filters.setdefault("format_date", _format_date)

    decoded_iri = unquote(object_iri)
    if not _validate_iri(decoded_iri):
        raise HTTPException(status_code=400, detail="Invalid IRI")

    # Query user-created properties from current graph
    props_sparql = f"""
    SELECT ?p ?o WHERE {{
      GRAPH <urn:sempkm:current> {{
        <{decoded_iri}> ?p ?o .
      }}
    }}
    """

    try:
        result = await client.query(props_sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception:
        logger.warning("Failed to query object %s", decoded_iri, exc_info=True)
        bindings = []

    values: dict[str, list[str]] = {}
    type_iris: list[str] = []
    body_text = ""
    rdf_type = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    sempkm_body = "urn:sempkm:body"

    for b in bindings:
        pred = b["p"]["value"]
        obj_val = b["o"]["value"]

        if pred == rdf_type:
            type_iris.append(obj_val)
        elif pred == sempkm_body:
            body_text = obj_val
        else:
            if pred not in values:
                values[pred] = []
            values[pred].append(obj_val)

    # Query inferred properties from the inferred graph (for right column)
    inferred_props_sparql = f"""
    SELECT ?p ?o WHERE {{
      GRAPH <urn:sempkm:inferred> {{
        <{decoded_iri}> ?p ?o .
      }}
    }}
    """

    inferred_values: dict[str, list[str]] = {}
    try:
        inf_result = await client.query(inferred_props_sparql)
        inf_bindings = inf_result.get("results", {}).get("bindings", [])
        for b in inf_bindings:
            pred = b["p"]["value"]
            obj_val = b["o"]["value"]
            # Skip rdf:type and body -- only show object/data properties
            if pred == rdf_type or pred == sempkm_body:
                continue
            # Deduplicate: skip if same triple exists in user-created data
            if pred in values and obj_val in values[pred]:
                continue
            if pred not in inferred_values:
                inferred_values[pred] = []
            inferred_values[pred].append(obj_val)
    except Exception:
        logger.warning(
            "Failed to query inferred properties for %s",
            decoded_iri, exc_info=True,
        )

    form = None
    if type_iris:
        for type_iri in type_iris:
            form = await shapes_service.get_form_for_type(type_iri)
            if form:
                break

    # Detect SHACL "Body" property: if the form defines a body-like property,
    # use its value as the markdown body and exclude it from the property table.
    # This unifies model-specific body predicates (e.g. urn:sempkm:model:basic-pkm:body)
    # with the canonical urn:sempkm:body used by the body editor.
    body_predicate = sempkm_body  # default save target
    body_property_path = ""  # SHACL body property path to exclude from edit form
    if form:
        for prop in form.properties:
            if prop.name and prop.name.lower() == "body":
                # Found SHACL body property — use its value if available
                shacl_body_vals = values.get(prop.path, [])
                if shacl_body_vals:
                    body_text = shacl_body_vals[0]
                    del values[prop.path]
                body_predicate = prop.path
                body_property_path = prop.path
                break

    # Resolve reference labels and tooltips for read-only view
    ref_iris: set[str] = set()
    type_class_iris: set[str] = set()
    ref_type_map: dict[str, str] = {}  # ref IRI -> target_class IRI
    if form:
        for prop in form.properties:
            if prop.target_class and prop.path in values:
                type_class_iris.add(prop.target_class)
                for v in values[prop.path]:
                    if v.startswith("http") or v.startswith("urn:"):
                        ref_iris.add(v)
                        ref_type_map[v] = prop.target_class

    ref_labels = await label_service.resolve_batch(list(ref_iris)) if ref_iris else {}
    type_labels = await label_service.resolve_batch(list(type_class_iris)) if type_class_iris else {}

    # Build tooltip: "TypeLabel: ObjectLabel"
    ref_tooltips: dict[str, str] = {}
    ref_types: dict[str, str] = {}
    for iri in ref_iris:
        obj_label = ref_labels.get(iri, iri)
        type_iri = ref_type_map.get(iri, "")
        type_label = type_labels.get(type_iri, "")
        if type_label:
            ref_tooltips[iri] = f"{type_label}: {obj_label}"
            ref_types[iri] = type_label
        else:
            ref_tooltips[iri] = obj_label

    # Resolve object label and type label
    iris_to_resolve = [decoded_iri] + type_iris
    labels = await label_service.resolve_batch(iris_to_resolve)
    object_label = labels.get(decoded_iri, decoded_iri)
    object_type_label = labels.get(type_iris[0], "") if type_iris else ""

    # Resolve type icon for the tab bar
    object_type_iri = type_iris[0] if type_iris else ""
    type_icon = icon_svc.get_type_icon(object_type_iri, context="tab") if object_type_iri else None

    # Resolve labels for inferred property IRIs (predicates and IRI objects)
    inferred_iris_to_resolve: set[str] = set()
    for pred, vals in inferred_values.items():
        inferred_iris_to_resolve.add(pred)
        for v in vals:
            if v.startswith("http") or v.startswith("urn:"):
                inferred_iris_to_resolve.add(v)
    inferred_labels = (
        await label_service.resolve_batch(list(inferred_iris_to_resolve))
        if inferred_iris_to_resolve
        else {}
    )

    context = {
        "request": request,
        "form": form,
        "values": values,
        "inferred_values": inferred_values,
        "inferred_labels": inferred_labels,
        "ref_labels": ref_labels,
        "ref_tooltips": ref_tooltips,
        "ref_types": ref_types,
        "object_iri": decoded_iri,
        "object_label": object_label,
        "object_type_label": object_type_label,
        "body_text": body_text,
        "body_predicate": body_predicate,
        "body_property_path": body_property_path,
        "mode": mode,
        "type_icon": type_icon,
    }

    return templates.TemplateResponse(
        request, "browser/object_tab.html", context
    )


@router.get("/tooltip/{object_iri:path}")
async def get_tooltip(
    request: Request,
    object_iri: str,
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
    label_service: LabelService = Depends(get_label_service),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Return a lightweight HTML popover for a referenced object."""
    templates = request.app.state.templates
    decoded_iri = unquote(object_iri)
    if not _validate_iri(decoded_iri):
        raise HTTPException(status_code=400, detail="Invalid IRI")

    props_sparql = f"""
    SELECT ?p ?o WHERE {{
      GRAPH <urn:sempkm:current> {{
        <{decoded_iri}> ?p ?o .
      }}
    }}
    """

    try:
        result = await client.query(props_sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception:
        bindings = []

    rdf_type = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    sempkm_body = "urn:sempkm:body"
    type_iris: list[str] = []
    props: dict[str, str] = {}

    for b in bindings:
        pred = b["p"]["value"]
        val = b["o"]["value"]
        if pred == rdf_type:
            type_iris.append(val)
        elif pred == sempkm_body:
            continue  # skip body in tooltip
        else:
            props[pred] = val

    # Resolve labels for the object, its type, and property predicates
    all_iris = [decoded_iri] + type_iris + list(props.keys())
    labels = await label_service.resolve_batch(all_iris) if all_iris else {}

    object_label = labels.get(decoded_iri, decoded_iri)
    type_label = labels.get(type_iris[0], "") if type_iris else ""

    # Build property display (resolved predicate labels -> values, max 5)
    display_props: list[dict[str, str]] = []
    for pred_iri, val in list(props.items())[:5]:
        pred_label = labels.get(pred_iri, pred_iri.rsplit("/", 1)[-1].rsplit("#", 1)[-1])
        display_val = val if len(val) <= 120 else val[:120] + "..."
        display_props.append({"name": pred_label, "value": display_val})

    context = {
        "request": request,
        "object_label": object_label,
        "type_label": type_label,
        "properties": display_props,
        "object_iri": decoded_iri,
    }

    return templates.TemplateResponse(
        request, "browser/ref_tooltip.html", context
    )


@router.post("/objects/{object_iri:path}/body")
async def save_body(
    request: Request,
    object_iri: str,
    predicate: str = Query(default=""),
    user: User = Depends(require_role("owner", "member")),
    client: TriplestoreClient = Depends(get_triplestore_client),
    validation_queue: AsyncValidationQueue = Depends(get_validation_queue),
    event_store: EventStore = Depends(get_event_store),
    label_service: LabelService = Depends(get_label_service),
):
    """Save the Markdown body of an object.

    Accepts body content as text/plain. Dispatches a body.set operation
    through the EventStore to atomically update the body in the current
    state graph and create an immutable event record.
    """
    from app.commands.handlers.body_set import handle_body_set
    from app.commands.schemas import BodySetParams
    from app.config import settings

    decoded_iri = unquote(object_iri)
    if not _validate_iri(decoded_iri):
        raise HTTPException(status_code=400, detail="Invalid IRI")
    body_content = (await request.body()).decode("utf-8")

    params = BodySetParams(
        iri=decoded_iri,
        body=body_content,
        predicate=predicate if predicate else None,
    )
    operation = await handle_body_set(params, settings.base_namespace)

    # Also update dcterms:modified timestamp
    from rdflib import Literal, Variable
    from rdflib.namespace import XSD
    dcterms_modified_uri = URIRef("http://purl.org/dc/terms/modified")
    now_literal = Literal(datetime.now(timezone.utc).isoformat(), datatype=XSD.dateTime)
    subject = URIRef(decoded_iri)
    operation.materialize_deletes.append(
        (subject, dcterms_modified_uri, Variable("old_modified"))
    )
    operation.materialize_inserts.append(
        (subject, dcterms_modified_uri, now_literal)
    )

    user_iri = URIRef(f"urn:sempkm:user:{user.id}")
    event_result = await event_store.commit([operation], performed_by=user_iri, performed_by_role=user.role)
    label_service.invalidate(event_result.affected_iris)

    await validation_queue.enqueue(
        event_iri=str(event_result.event_iri),
        timestamp=event_result.timestamp,
    )

    return HTMLResponse(
        content='<span class="save-ok">Saved</span>',
        status_code=200,
    )


@router.get("/relations/{object_iri:path}")
async def get_relations(
    request: Request,
    object_iri: str,
    user: User = Depends(get_current_user),
    label_service: LabelService = Depends(get_label_service),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Query and render related objects for the right pane.

    Queries outbound edges (this object as subject) and inbound edges
    (this object as object) from the current graph. Groups by predicate
    and resolves all IRIs to labels.
    """
    templates = request.app.state.templates
    decoded_iri = unquote(object_iri)
    if not _validate_iri(decoded_iri):
        raise HTTPException(status_code=400, detail="Invalid IRI")

    # Use UNION pattern to query both current and inferred graphs,
    # annotating each result with its source graph (Pitfall 5: do NOT
    # mix FROM and GRAPH patterns in the same query).
    outbound_sparql = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?predicate ?object ?source WHERE {{
      {{
        GRAPH <urn:sempkm:current> {{
          <{decoded_iri}> ?predicate ?object .
          FILTER(isIRI(?object))
          FILTER(?predicate != rdf:type)
        }}
        BIND("user" AS ?source)
      }} UNION {{
        GRAPH <urn:sempkm:inferred> {{
          <{decoded_iri}> ?predicate ?object .
          FILTER(isIRI(?object))
          FILTER(?predicate != rdf:type)
        }}
        BIND("inferred" AS ?source)
      }}
    }}
    """

    inbound_sparql = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?subject ?predicate ?source WHERE {{
      {{
        GRAPH <urn:sempkm:current> {{
          ?subject ?predicate <{decoded_iri}> .
          FILTER(isIRI(?subject))
          FILTER(?predicate != rdf:type)
        }}
        BIND("user" AS ?source)
      }} UNION {{
        GRAPH <urn:sempkm:inferred> {{
          ?subject ?predicate <{decoded_iri}> .
          FILTER(isIRI(?subject))
          FILTER(?predicate != rdf:type)
        }}
        BIND("inferred" AS ?source)
      }}
    }}
    """

    outbound_edges: list[dict] = []
    inbound_edges: list[dict] = []

    try:
        out_result = await client.query(outbound_sparql)
        for b in out_result.get("results", {}).get("bindings", []):
            outbound_edges.append({
                "predicate": b["predicate"]["value"],
                "target": b["object"]["value"],
                "source": b.get("source", {}).get("value", "user"),
            })
    except Exception:
        logger.warning("Failed to query outbound edges for %s", decoded_iri, exc_info=True)

    try:
        in_result = await client.query(inbound_sparql)
        for b in in_result.get("results", {}).get("bindings", []):
            inbound_edges.append({
                "predicate": b["predicate"]["value"],
                "source_iri": b["subject"]["value"],
                "source": b.get("source", {}).get("value", "user"),
            })
    except Exception:
        logger.warning("Failed to query inbound edges for %s", decoded_iri, exc_info=True)

    # Deduplicate: if a triple exists in both current and inferred,
    # keep only the user version (user-created takes precedence).
    seen_outbound: set[tuple[str, str]] = set()
    deduped_outbound: list[dict] = []
    for e in outbound_edges:
        key = (e["predicate"], e["target"])
        if key in seen_outbound:
            continue
        seen_outbound.add(key)
        deduped_outbound.append(e)
    outbound_edges = deduped_outbound

    seen_inbound: set[tuple[str, str]] = set()
    deduped_inbound: list[dict] = []
    for e in inbound_edges:
        key = (e["predicate"], e["source_iri"])
        if key in seen_inbound:
            continue
        seen_inbound.add(key)
        deduped_inbound.append(e)
    inbound_edges = deduped_inbound

    all_iris: set[str] = set()
    for e in outbound_edges:
        all_iris.add(e["predicate"])
        all_iris.add(e["target"])
    for e in inbound_edges:
        all_iris.add(e["predicate"])
        all_iris.add(e["source_iri"])

    labels = await label_service.resolve_batch(list(all_iris)) if all_iris else {}

    outbound_grouped: dict[str, list[dict]] = {}
    for e in outbound_edges:
        pred_label = labels.get(e["predicate"], e["predicate"])
        if pred_label not in outbound_grouped:
            outbound_grouped[pred_label] = []
        outbound_grouped[pred_label].append({
            "iri": e["target"],
            "label": labels.get(e["target"], e["target"]),
            "source": e["source"],
        })

    inbound_grouped: dict[str, list[dict]] = {}
    for e in inbound_edges:
        pred_label = labels.get(e["predicate"], e["predicate"])
        if pred_label not in inbound_grouped:
            inbound_grouped[pred_label] = []
        inbound_grouped[pred_label].append({
            "iri": e["source_iri"],
            "label": labels.get(e["source_iri"], e["source_iri"]),
            "source": e["source"],
        })

    context = {
        "request": request,
        "object_iri": decoded_iri,
        "outbound_grouped": outbound_grouped,
        "inbound_grouped": inbound_grouped,
    }

    return templates.TemplateResponse(
        request, "browser/properties.html", context
    )


@router.get("/lint/{object_iri:path}")
async def get_lint(
    request: Request,
    object_iri: str,
    user: User = Depends(get_current_user),
    lint_service: LintService = Depends(get_lint_service),
):
    """Get SHACL validation results for a specific object.

    Queries structured lint result triples from the latest run filtered
    to this object's focus node. Renders the lint_panel.html partial.
    """
    templates = request.app.state.templates
    decoded_iri = unquote(object_iri)
    if not _validate_iri(decoded_iri):
        raise HTTPException(status_code=400, detail="Invalid IRI")

    results = await lint_service.get_results_for_object(decoded_iri)

    violations: list[dict] = []
    warnings: list[dict] = []
    infos: list[dict] = []

    for entry in results:
        severity = entry["severity"]
        item = {
            "message": entry["message"],
            "path": entry["path"],
            "source_shape": entry["source_shape"],
        }
        if severity.endswith("Violation"):
            violations.append(item)
        elif severity.endswith("Warning"):
            warnings.append(item)
        else:
            infos.append(item)

    conforms = len(violations) == 0

    context = {
        "request": request,
        "object_iri": decoded_iri,
        "violations": violations,
        "warnings": warnings,
        "infos": infos,
        "conforms": conforms,
        "violation_count": len(violations),
        "warning_count": len(warnings),
    }

    return templates.TemplateResponse(
        request, "browser/lint_panel.html", context
    )


@router.get("/types")
async def type_picker(
    request: Request,
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
):
    """Render the type picker dialog listing all available object types.

    Lists all SHACL NodeShapes with their target classes from installed
    Mental Models. Each type card links to the create form via htmx GET.
    """
    templates = request.app.state.templates
    types = await shapes_service.get_types()
    context = {"request": request, "types": types}
    return templates.TemplateResponse(
        request, "browser/type_picker.html", context
    )


@router.get("/objects/new")
async def create_form(
    request: Request,
    type: str,
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
):
    """Render the SHACL-driven create form for a given object type.

    Fetches form metadata from ShapesService for the specified type IRI
    and renders the object_form.html template in create mode with empty
    values. Returned as an htmx partial for the editor area.
    """
    templates = request.app.state.templates
    form = await shapes_service.get_form_for_type(type)

    if not form:
        return HTMLResponse(
            content='<div class="form-empty"><p>No form schema available for this type.</p></div>',
            status_code=200,
        )

    context = {
        "request": request,
        "form": form,
        "values": {},
        "mode": "create",
        "object_iri": None,
        "success_message": None,
        "error_message": None,
    }

    return templates.TemplateResponse(
        request, "forms/object_form.html", context
    )


@router.post("/objects")
async def create_object(
    request: Request,
    user: User = Depends(require_role("owner", "member")),
    shapes_service: ShapesService = Depends(get_shapes_service),
    label_service: LabelService = Depends(get_label_service),
    client: TriplestoreClient = Depends(get_triplestore_client),
    validation_queue: AsyncValidationQueue = Depends(get_validation_queue),
    event_store: EventStore = Depends(get_event_store),
):
    """Process create form submission and create a new object.

    Parses form data to extract the type IRI and property values,
    dispatches an object.create command through the EventStore, and
    re-renders the form in edit mode with the newly created object.
    """
    from app.commands.handlers.object_create import handle_object_create
    from app.commands.schemas import ObjectCreateParams
    from app.config import settings

    templates = request.app.state.templates
    form_data = await request.form()

    type_iri = form_data.get("type_iri", "")
    if not type_iri:
        return HTMLResponse(
            content='<div class="form-error">Missing type information.</div>',
            status_code=400,
        )

    # Extract the type local name from the full IRI for the command handler
    # Build properties dict from form data, excluding hidden/meta fields
    properties: dict[str, str | list[str]] = {}
    skip_fields = {"type_iri", "object_iri", "q"}

    for key in form_data.keys():
        if key in skip_fields or key.startswith("_search_"):
            continue
        raw_values = form_data.getlist(key)
        # Filter out empty values
        values = [v for v in raw_values if v and v.strip()]
        if not values:
            continue
        # Strip array suffix if present
        clean_key = key.rstrip("[]")
        if len(values) == 1:
            properties[clean_key] = values[0]
        else:
            # Multi-valued: store first value (command API uses single values per property)
            # For multiple values of the same property, we'd need multiple commands
            # For now, join or use first value
            properties[clean_key] = values[0]

    try:
        params = ObjectCreateParams(
            type=type_iri,  # pass full IRI; handler resolves local name for object IRI minting
            properties=properties,
        )
        operation = await handle_object_create(params, settings.base_namespace)
        user_iri = URIRef(f"urn:sempkm:user:{user.id}")
        event_result = await event_store.commit([operation], performed_by=user_iri, performed_by_role=user.role)
        label_service.invalidate(event_result.affected_iris)

        # Trigger async validation
        await validation_queue.enqueue(
            event_iri=str(event_result.event_iri),
            timestamp=event_result.timestamp,
        )

        # Get the created object IRI
        created_iri = operation.affected_iris[0] if operation.affected_iris else ""

        # Resolve label for the new object
        labels = await label_service.resolve_batch([created_iri])
        object_label = labels.get(created_iri, created_iri)

        # Re-render as edit form with success message
        form = await shapes_service.get_form_for_type(type_iri)
        context = {
            "request": request,
            "form": form,
            "values": properties,
            "mode": "edit",
            "object_iri": created_iri,
            "success_message": f"Created {type_iri.rsplit('/', 1)[-1].rsplit(':', 1)[-1]} successfully",
            "error_message": None,
        }

        response = templates.TemplateResponse(
            request, "forms/object_form.html", context
        )
        # Set HX-Trigger header to update the tab with the new object
        response.headers["HX-Trigger"] = (
            f'{{"objectCreated": {{"iri": "{created_iri}", "label": "{object_label}"}}}}'
        )
        return response

    except Exception as e:
        logger.exception("Failed to create object")
        form = await shapes_service.get_form_for_type(type_iri)
        context = {
            "request": request,
            "form": form,
            "values": properties,
            "mode": "create",
            "object_iri": None,
            "success_message": None,
            "error_message": f"Failed to create object: {str(e)}",
        }
        return templates.TemplateResponse(
            request, "forms/object_form.html", context
        )


@router.post("/objects/{object_iri:path}/save")
async def save_object(
    request: Request,
    object_iri: str,
    user: User = Depends(require_role("owner", "member")),
    shapes_service: ShapesService = Depends(get_shapes_service),
    label_service: LabelService = Depends(get_label_service),
    client: TriplestoreClient = Depends(get_triplestore_client),
    validation_queue: AsyncValidationQueue = Depends(get_validation_queue),
    event_store: EventStore = Depends(get_event_store),
):
    """Process edit form submission and patch an existing object.

    Parses form data to detect changed properties, dispatches
    object.patch commands for modifications, and re-renders the
    form with updated values and a success message.
    """
    from app.commands.handlers.object_patch import handle_object_patch
    from app.commands.schemas import ObjectPatchParams
    from app.config import settings

    templates = request.app.state.templates
    decoded_iri = unquote(object_iri)
    form_data = await request.form()

    type_iri = form_data.get("type_iri", "")

    # Build properties dict from form data (all values per key, not just the first)
    properties: dict[str, list[str]] = {}
    skip_fields = {"type_iri", "object_iri", "q"}
    dcterms_modified = "http://purl.org/dc/terms/modified"

    for key in form_data.keys():
        if key in skip_fields or key.startswith("_search_"):
            continue
        raw_values = form_data.getlist(key)
        values = [v for v in raw_values if v and v.strip()]
        if not values:
            continue
        clean_key = key.rstrip("[]")
        properties[clean_key] = values

    # Auto-set dcterms:modified to current UTC timestamp
    properties[dcterms_modified] = [datetime.now(timezone.utc).isoformat()]

    try:
        if properties:
            params = ObjectPatchParams(
                iri=decoded_iri,
                properties=properties,
            )
            operation = await handle_object_patch(params, settings.base_namespace)
            user_iri = URIRef(f"urn:sempkm:user:{user.id}")
            event_result = await event_store.commit([operation], performed_by=user_iri, performed_by_role=user.role)
            label_service.invalidate(event_result.affected_iris)

            await validation_queue.enqueue(
                event_iri=str(event_result.event_iri),
                timestamp=event_result.timestamp,
            )

        # Re-render the form with current values
        form = await shapes_service.get_form_for_type(type_iri)

        # Resolve labels for reference values so search inputs show names not IRIs
        ref_iris = {
            v.strip()
            for key in form_data.keys()
            if key not in skip_fields and not key.startswith("_search_")
            for v in form_data.getlist(key)
            if v.strip() and (v.strip().startswith("http") or v.strip().startswith("urn:"))
        }
        save_ref_labels = await label_service.resolve_batch(list(ref_iris)) if ref_iris else {}

        context = {
            "request": request,
            "form": form,
            "values": properties,
            "ref_labels": save_ref_labels,
            "mode": "edit",
            "object_iri": decoded_iri,
            "success_message": "Changes saved successfully",
            "error_message": None,
        }

        response = templates.TemplateResponse(
            request, "forms/object_form.html", context
        )
        # Trigger markClean + label update on the tab
        _label_predicates = [
            "http://purl.org/dc/terms/title",
            "http://www.w3.org/2000/01/rdf-schema#label",
            "http://www.w3.org/2004/02/skos/core#prefLabel",
            "http://schema.org/name",
            "http://xmlns.com/foaf/0.1/name",
        ]
        import json as _json
        new_label = next((properties[p][0] for p in _label_predicates if p in properties and properties[p]), None)
        trigger_payload = {"iri": decoded_iri}
        if new_label:
            trigger_payload["label"] = new_label
        response.headers["HX-Trigger"] = _json.dumps({"objectSaved": trigger_payload})
        return response

    except Exception as e:
        logger.exception("Failed to save object %s", decoded_iri)
        form = await shapes_service.get_form_for_type(type_iri)
        context = {
            "request": request,
            "form": form,
            "values": properties,
            "mode": "edit",
            "object_iri": decoded_iri,
            "success_message": None,
            "error_message": f"Failed to save changes: {str(e)}",
        }
        return templates.TemplateResponse(
            request, "forms/object_form.html", context
        )


@router.get("/events")
async def event_log(
    request: Request,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
    label_service: LabelService = Depends(get_label_service),
    db: AsyncSession = Depends(get_db_session),
    cursor: str | None = Query(default=None),
    op: str | None = Query(default=None),
    user_filter: str | None = Query(default=None, alias="user"),
    obj: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
):
    """Render the event log timeline as an htmx partial for the bottom panel."""
    import re

    from app.events.query import EventQueryService

    templates = request.app.state.templates
    query_svc = EventQueryService(client)
    events, next_cursor = await query_svc.list_events(
        cursor_timestamp=cursor,
        op_type=op,
        user_iri=user_filter,
        object_iri=obj,
        date_from=date_from,
        date_to=date_to,
    )

    # Resolve labels for all affected IRIs
    all_iris = [iri for e in events for iri in e.affected_iris if iri]
    labels = await label_service.resolve_batch(all_iris) if all_iris else {}

    # Resolve user display names via SQL lookup (user IRIs are urn:sempkm:user:{uuid})
    user_iris = list({e.performed_by for e in events if e.performed_by})
    user_names: dict[str, str] = {}
    if user_iris:
        import uuid as _uuid
        from app.auth.models import User as UserModel
        from sqlalchemy import select as sa_select

        for uiri in user_iris:
            m = re.match(r"urn:sempkm:user:(.+)$", uiri)
            if m:
                try:
                    uuid_obj = _uuid.UUID(m.group(1))
                    result = await db.execute(
                        sa_select(UserModel).where(UserModel.id == uuid_obj)
                    )
                    db_user = result.scalar_one_or_none()
                    if db_user:
                        user_names[uiri] = db_user.display_name or db_user.email
                except Exception:
                    logger.warning("Failed to resolve user IRI %s", uiri, exc_info=True)

    # Build active filters list for chip rendering
    active_filters = []
    if op:
        active_filters.append({"param": "op", "value": op, "label": f"op: {op}"})
    if obj:
        obj_label = labels.get(obj, obj[:30] + "..." if len(obj) > 30 else obj)
        active_filters.append({"param": "obj", "value": obj, "label": f"object: {obj_label}"})
    if user_filter:
        active_filters.append({"param": "user", "value": user_filter, "label": f"user: {user_names.get(user_filter, user_filter)}"})
    if date_from:
        active_filters.append({"param": "date_from", "value": date_from, "label": f"from: {date_from}"})
    if date_to:
        active_filters.append({"param": "date_to", "value": date_to, "label": f"to: {date_to}"})

    return templates.TemplateResponse(request, "browser/event_log.html", {
        "request": request,
        "events": events,
        "labels": labels,
        "user_names": user_names,
        "next_cursor": next_cursor,
        "active_filters": active_filters,
        "current_params": dict(request.query_params),
    })


@router.get("/events/{event_iri:path}/detail")
async def event_detail(
    request: Request,
    event_iri: str,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Render an inline diff partial for a single event.

    Returns an HTML fragment (no base template) suitable for insertion
    into a .event-diff-container via htmx.
    """
    from app.events.query import EventQueryService
    from urllib.parse import unquote as _unquote

    templates = request.app.state.templates
    decoded_iri = _unquote(event_iri)
    query_svc = EventQueryService(client)
    detail = await query_svc.get_event_detail(decoded_iri)
    if not detail:
        return HTMLResponse("<div class='event-diff-error'>Event not found.</div>")
    return templates.TemplateResponse(request, "browser/event_detail.html", {
        "request": request,
        "detail": detail,
    })


@router.post("/events/{event_iri:path}/undo")
async def undo_event(
    request: Request,
    event_iri: str,
    user: User = Depends(require_role("owner", "member")),
    client: TriplestoreClient = Depends(get_triplestore_client),
    event_store: EventStore = Depends(get_event_store),
    label_service: LabelService = Depends(get_label_service),
):
    """Create a compensating event that reverses the specified event.

    Builds a compensation Operation via EventQueryService.build_compensation()
    and commits it via EventStore. The original event is not modified.
    """
    from app.events.query import EventQueryService
    from urllib.parse import unquote as _unquote

    decoded_iri = _unquote(event_iri)
    query_svc = EventQueryService(client)
    detail = await query_svc.get_event_detail(decoded_iri)
    if not detail:
        return JSONResponse(status_code=404, content={"error": "Event not found"})
    compensation = await query_svc.build_compensation(decoded_iri, detail)
    if not compensation:
        return JSONResponse(status_code=400, content={"error": "This event cannot be undone"})
    user_iri = URIRef(f"urn:sempkm:user:{user.id}")
    event_result = await event_store.commit([compensation], performed_by=user_iri, performed_by_role=user.role)
    label_service.invalidate(event_result.affected_iris)
    return JSONResponse(content={"status": "ok", "message": "Undo applied successfully"})


@router.get("/search")
async def search_references(
    request: Request,
    type: str = "",
    q: str = "",
    field_id: str = "",
    index: str | None = None,
    user: User = Depends(get_current_user),
    label_service: LabelService = Depends(get_label_service),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Search for instances of a type for sh:class reference fields.

    Queries the current state graph for objects matching the given rdf:type
    and filtering by label regex. Returns HTML suggestion items for the
    search-as-you-type dropdown.
    """
    templates = request.app.state.templates

    if not type:
        return HTMLResponse(content="", status_code=200)

    if not _validate_iri(type):
        raise HTTPException(status_code=400, detail="Invalid IRI")

    # Build SPARQL query to find instances of the type
    sparql = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT DISTINCT ?obj WHERE {{
      GRAPH <urn:sempkm:current> {{
        ?obj rdf:type <{type}> .
      }}
    }}
    LIMIT 20
    """

    try:
        result = await client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception:
        logger.warning("Reference search failed for type %s", type, exc_info=True)
        bindings = []

    obj_iris = [b["obj"]["value"] for b in bindings]
    labels = await label_service.resolve_batch(obj_iris) if obj_iris else {}

    # Filter by query string if provided
    results = []
    query_lower = q.lower() if q else ""
    for iri in obj_iris:
        label = labels.get(iri, iri)
        if not query_lower or query_lower in label.lower() or query_lower in iri.lower():
            results.append({"iri": iri, "label": label})

    # Resolve type label for the "Create new..." option
    type_labels = await label_service.resolve_batch([type])
    type_label = type_labels.get(type, type.rsplit("/", 1)[-1] if "/" in type else type)

    context = {
        "request": request,
        "results": results,
        "type_iri": type,
        "type_label": type_label,
        "field_id": field_id,
        "index": int(index) if index is not None and index.isdigit() else None,
    }

    return templates.TemplateResponse(
        request, "browser/search_suggestions.html", context
    )
