"""Object browser router serving the IDE-style workspace.

Provides the workspace layout, navigation tree endpoints, object
loading, body saving, related objects, lint panel, type picker,
create/edit object flows, and reference search endpoints for the
three-column IDE workspace. Uses htmx partial rendering for dynamic
content updates.
"""

import logging
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from app.dependencies import (
    get_label_service,
    get_shapes_service,
    get_triplestore_client,
    get_validation_queue,
)
from app.services.labels import LabelService
from app.services.shapes import ShapesService
from app.triplestore.client import TriplestoreClient
from app.validation.queue import AsyncValidationQueue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/browser", tags=["browser"])


def _is_htmx_request(request: Request) -> bool:
    """Check if the request is an htmx partial request."""
    return request.headers.get("HX-Request") == "true"


@router.get("/")
async def workspace(
    request: Request,
    shapes_service: ShapesService = Depends(get_shapes_service),
):
    """Render the IDE-style workspace with three-column layout.

    Queries available object types from ShapesService for the navigation
    tree. Full page for direct navigation, content block only for htmx.
    """
    templates = request.app.state.templates
    types = await shapes_service.get_types()
    context = {"request": request, "types": types}

    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request, "browser/workspace.html", context, block_name="content"
        )
    return templates.TemplateResponse(request, "browser/workspace.html", context)


@router.get("/tree/{type_iri:path}")
async def tree_children(
    request: Request,
    type_iri: str,
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
    shapes_service: ShapesService = Depends(get_shapes_service),
    label_service: LabelService = Depends(get_label_service),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Render an object in the editor area with properties form and body editor.

    Queries the object's current property values and body text from the
    triplestore, resolves its type, fetches SHACL form metadata, and
    renders the object_tab.html split view.
    """
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
        logger.warning("Failed to query object %s", decoded_iri, exc_info=True)
        bindings = []

    values: dict[str, str] = {}
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
            values[pred] = obj_val

    form = None
    if type_iris:
        for type_iri in type_iris:
            form = await shapes_service.get_form_for_type(type_iri)
            if form:
                break

    labels = await label_service.resolve_batch([decoded_iri])
    object_label = labels.get(decoded_iri, decoded_iri)

    context = {
        "request": request,
        "form": form,
        "values": values,
        "object_iri": decoded_iri,
        "object_label": object_label,
        "body_text": body_text,
        "mode": "edit",
    }

    return templates.TemplateResponse(
        request, "browser/object_tab.html", context
    )


@router.post("/objects/{object_iri:path}/body")
async def save_body(
    request: Request,
    object_iri: str,
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

    params = BodySetParams(iri=decoded_iri, body=body_content)
    operation = await handle_body_set(params, settings.base_namespace)
    event_store = EventStore(client)
    event_result = await event_store.commit([operation])

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
