"""Object browser router serving the IDE-style workspace.

Provides the workspace layout, navigation tree endpoints, object
loading, body saving, related objects, lint panel, type picker,
create/edit object flows, and reference search endpoints for the
three-column IDE workspace. Uses htmx partial rendering for dynamic
content updates.
"""

import logging
from datetime import datetime
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from rdflib import URIRef
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.db.session import get_db_session
from app.dependencies import (
    get_label_service,
    get_shapes_service,
    get_triplestore_client,
    get_validation_queue,
)
from app.services.labels import LabelService
from app.services.settings import SettingsService
from app.services.shapes import ShapesService
from app.triplestore.client import TriplestoreClient
from app.validation.queue import AsyncValidationQueue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/browser", tags=["browser"])

# Models directory path -- mirrors the Docker mount used in main.py
_MODELS_DIR = "/app/models"


def get_settings_service() -> SettingsService:
    """FastAPI dependency that returns a SettingsService with the models directory."""
    return SettingsService(installed_models_dir=_MODELS_DIR)


@router.get("/settings")
async def settings_page(
    request: Request,
    user: User = Depends(get_current_user),
    settings_svc: SettingsService = Depends(get_settings_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Render the Settings page as an htmx partial."""
    from collections import defaultdict

    templates = request.app.state.templates
    all_settings = await settings_svc.get_all_settings()
    user_overrides = await settings_svc.get_user_overrides(user.id, db)
    resolved = await settings_svc.resolve(user.id, db)

    categories = defaultdict(list)
    for s in all_settings:
        categories[s.category].append(s)

    return templates.TemplateResponse(request, "browser/settings_page.html", {
        "request": request,
        "categories": dict(categories),
        "user_overrides": user_overrides,
        "resolved": resolved,
        "all_settings": all_settings,
    })


@router.get("/settings/data")
async def settings_data(
    user: User = Depends(get_current_user),
    settings_svc: SettingsService = Depends(get_settings_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Return resolved settings as JSON for the client-side cache."""
    resolved = await settings_svc.resolve(user.id, db)
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
):
    """Render the IDE-style workspace with three-column layout.

    Queries available object types from ShapesService for the navigation
    tree. Full page for direct navigation, content block only for htmx.
    """
    templates = request.app.state.templates
    types = await shapes_service.get_types()
    context = {"request": request, "types": types, "active_page": "browser", "user": user}

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
):
    """Load objects of a given type for the navigation tree.

    Queries the current graph for instances of the specified type,
    resolves labels via LabelService, and returns tree leaf nodes
    as an htmx partial.
    """
    templates = request.app.state.templates
    client = request.app.state.triplestore_client
    decoded_iri = unquote(type_iri)

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

    context = {"request": request, "objects": objects}
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

    context = {
        "request": request,
        "form": form,
        "values": values,
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
):
    """Save the Markdown body of an object.

    Accepts body content as text/plain. Dispatches a body.set operation
    through the EventStore to atomically update the body in the current
    state graph and create an immutable event record.
    """
    from app.commands.handlers.body_set import handle_body_set
    from app.commands.schemas import BodySetParams
    from app.config import settings
    from app.events.store import EventStore

    decoded_iri = unquote(object_iri)
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
    now_literal = Literal(datetime.now().isoformat(), datatype=XSD.dateTime)
    subject = URIRef(decoded_iri)
    operation.materialize_deletes.append(
        (subject, dcterms_modified_uri, Variable("old_modified"))
    )
    operation.materialize_inserts.append(
        (subject, dcterms_modified_uri, now_literal)
    )

    event_store = EventStore(client)
    user_iri = URIRef(f"urn:sempkm:user:{user.id}")
    event_result = await event_store.commit([operation], performed_by=user_iri, performed_by_role=user.role)

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

    outbound_sparql = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?predicate ?object WHERE {{
      GRAPH <urn:sempkm:current> {{
        <{decoded_iri}> ?predicate ?object .
        FILTER(isIRI(?object))
        FILTER(?predicate != rdf:type)
      }}
    }}
    """

    inbound_sparql = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?subject ?predicate WHERE {{
      GRAPH <urn:sempkm:current> {{
        ?subject ?predicate <{decoded_iri}> .
        FILTER(isIRI(?subject))
        FILTER(?predicate != rdf:type)
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
            })
    except Exception:
        logger.warning("Failed to query outbound edges for %s", decoded_iri, exc_info=True)

    try:
        in_result = await client.query(inbound_sparql)
        for b in in_result.get("results", {}).get("bindings", []):
            inbound_edges.append({
                "predicate": b["predicate"]["value"],
                "source": b["subject"]["value"],
            })
    except Exception:
        logger.warning("Failed to query inbound edges for %s", decoded_iri, exc_info=True)

    all_iris: set[str] = set()
    for e in outbound_edges:
        all_iris.add(e["predicate"])
        all_iris.add(e["target"])
    for e in inbound_edges:
        all_iris.add(e["predicate"])
        all_iris.add(e["source"])

    labels = await label_service.resolve_batch(list(all_iris)) if all_iris else {}

    outbound_grouped: dict[str, list[dict]] = {}
    for e in outbound_edges:
        pred_label = labels.get(e["predicate"], e["predicate"])
        if pred_label not in outbound_grouped:
            outbound_grouped[pred_label] = []
        outbound_grouped[pred_label].append({
            "iri": e["target"],
            "label": labels.get(e["target"], e["target"]),
        })

    inbound_grouped: dict[str, list[dict]] = {}
    for e in inbound_edges:
        pred_label = labels.get(e["predicate"], e["predicate"])
        if pred_label not in inbound_grouped:
            inbound_grouped[pred_label] = []
        inbound_grouped[pred_label].append({
            "iri": e["source"],
            "label": labels.get(e["source"], e["source"]),
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
    validation_queue: AsyncValidationQueue = Depends(get_validation_queue),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Get SHACL validation results for a specific object.

    Checks the in-memory latest validation report from the queue, then
    queries the triplestore for detailed results filtered to this object's
    focus node. Renders the lint_panel.html partial.
    """
    templates = request.app.state.templates
    decoded_iri = unquote(object_iri)

    latest_report = validation_queue.latest_report

    violations: list[dict] = []
    warnings: list[dict] = []
    infos: list[dict] = []
    conforms = True

    if latest_report and latest_report.report_iri:
        report_sparql = f"""
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        SELECT ?severity ?path ?message ?sourceShape WHERE {{
          GRAPH <{latest_report.report_iri}> {{
            ?result sh:focusNode <{decoded_iri}> ;
                    sh:resultSeverity ?severity .
            OPTIONAL {{ ?result sh:resultPath ?path }}
            OPTIONAL {{ ?result sh:resultMessage ?message }}
            OPTIONAL {{ ?result sh:sourceShape ?sourceShape }}
          }}
        }}
        """

        try:
            result = await client.query(report_sparql)
            for b in result.get("results", {}).get("bindings", []):
                severity = b["severity"]["value"]
                entry = {
                    "message": b.get("message", {}).get("value", "Constraint violated"),
                    "path": b.get("path", {}).get("value", ""),
                    "source_shape": b.get("sourceShape", {}).get("value", ""),
                }

                if severity.endswith("Violation"):
                    violations.append(entry)
                elif severity.endswith("Warning"):
                    warnings.append(entry)
                else:
                    infos.append(entry)

            if violations:
                conforms = False
        except Exception:
            logger.warning(
                "Failed to query validation results for %s", decoded_iri, exc_info=True
            )

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
):
    """Process create form submission and create a new object.

    Parses form data to extract the type IRI and property values,
    dispatches an object.create command through the EventStore, and
    re-renders the form in edit mode with the newly created object.
    """
    from app.commands.handlers.object_create import handle_object_create
    from app.commands.schemas import ObjectCreateParams
    from app.config import settings
    from app.events.store import EventStore

    templates = request.app.state.templates
    form_data = await request.form()

    type_iri = form_data.get("type_iri", "")
    if not type_iri:
        return HTMLResponse(
            content='<div class="form-error">Missing type information.</div>',
            status_code=400,
        )

    # Extract the type local name from the full IRI for the command handler
    type_name = type_iri.rsplit("/", 1)[-1] if "/" in type_iri else type_iri
    if "#" in type_name:
        type_name = type_name.rsplit("#", 1)[-1]

    # Build properties dict from form data, excluding hidden/meta fields
    properties: dict[str, str | list[str]] = {}
    skip_fields = {"type_iri", "object_iri"}

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
            type=type_name,
            properties=properties,
        )
        operation = await handle_object_create(params, settings.base_namespace)
        event_store = EventStore(client)
        user_iri = URIRef(f"urn:sempkm:user:{user.id}")
        event_result = await event_store.commit([operation], performed_by=user_iri, performed_by_role=user.role)

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
            "success_message": f"Created {type_name} successfully",
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
):
    """Process edit form submission and patch an existing object.

    Parses form data to detect changed properties, dispatches
    object.patch commands for modifications, and re-renders the
    form with updated values and a success message.
    """
    from app.commands.handlers.object_patch import handle_object_patch
    from app.commands.schemas import ObjectPatchParams
    from app.config import settings
    from app.events.store import EventStore

    templates = request.app.state.templates
    decoded_iri = unquote(object_iri)
    form_data = await request.form()

    type_iri = form_data.get("type_iri", "")

    # Build properties dict from form data
    properties: dict[str, str] = {}
    skip_fields = {"type_iri", "object_iri"}
    dcterms_modified = "http://purl.org/dc/terms/modified"

    for key in form_data.keys():
        if key in skip_fields or key.startswith("_search_"):
            continue
        raw_values = form_data.getlist(key)
        values = [v for v in raw_values if v and v.strip()]
        if not values:
            continue
        clean_key = key.rstrip("[]")
        properties[clean_key] = values[0]

    # Auto-set dcterms:modified to current timestamp
    properties[dcterms_modified] = datetime.now().isoformat()

    try:
        if properties:
            params = ObjectPatchParams(
                iri=decoded_iri,
                properties=properties,
            )
            operation = await handle_object_patch(params, settings.base_namespace)
            event_store = EventStore(client)
            user_iri = URIRef(f"urn:sempkm:user:{user.id}")
            event_result = await event_store.commit([operation], performed_by=user_iri, performed_by_role=user.role)

            await validation_queue.enqueue(
                event_iri=str(event_result.event_iri),
                timestamp=event_result.timestamp,
            )

        # Re-render the form with current values
        form = await shapes_service.get_form_for_type(type_iri)
        context = {
            "request": request,
            "form": form,
            "values": properties,
            "mode": "edit",
            "object_iri": decoded_iri,
            "success_message": "Changes saved successfully",
            "error_message": None,
        }

        response = templates.TemplateResponse(
            request, "forms/object_form.html", context
        )
        # Trigger markClean on the tab
        response.headers["HX-Trigger"] = (
            f'{{"objectSaved": {{"iri": "{decoded_iri}"}}}}'
        )
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
