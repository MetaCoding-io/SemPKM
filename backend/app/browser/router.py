"""Object browser router serving the IDE-style workspace.

Provides the workspace layout, navigation tree endpoints, and object
loading for the three-column IDE workspace. Uses htmx partial rendering
for dynamic content updates.
"""

import logging
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Request

from app.dependencies import get_label_service, get_shapes_service
from app.services.labels import LabelService
from app.services.shapes import ShapesService

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

    # Query objects of this type from the current graph
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

    # Resolve labels for all objects
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
