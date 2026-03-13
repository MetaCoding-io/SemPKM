"""Ontology sub-router — TBox, ABox, RBox endpoints for ontology browsing.

Provides htmx endpoints for:
- TBox Explorer: collapsible class hierarchy tree across gist + all model
  ontology graphs + user-types
- ABox Browser: instance counts per type with drill-down to instance lists
- RBox Legend: property reference table with domain/range columns
- Main ontology page: three-tab layout hosting TBox/ABox/RBox
"""

import logging
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from app.auth.dependencies import get_current_user
from app.auth.models import User

logger = logging.getLogger(__name__)

ontology_router = APIRouter(tags=["ontology"])


# ------------------------------------------------------------------
# Main ontology viewer page
# ------------------------------------------------------------------


@ontology_router.get("/ontology")
async def ontology_page(
    request: Request,
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Render the main ontology viewer with three-tab layout.

    This is the entry point fetched by the special-panel component
    when specialType='ontology'. TBox loads immediately; ABox and
    RBox load lazily on tab click.
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "browser/ontology/ontology_page.html",
        {},
    )


# ------------------------------------------------------------------
# TBox Explorer
# ------------------------------------------------------------------


@ontology_router.get("/ontology/tbox")
async def tbox_tree(
    request: Request,
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Render the TBox Explorer root class hierarchy tree.

    Queries all ontology graphs for root classes (no rdfs:subClassOf parent
    or only owl:Thing parent) and renders them as expandable tree nodes.
    """
    ontology_service = request.app.state.ontology_service
    try:
        classes = await ontology_service.get_root_classes()
    except Exception:
        logger.error("Failed to load TBox root classes", exc_info=True)
        classes = []

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "browser/ontology/tbox_tree.html",
        {"classes": classes, "error": not classes},
    )


@ontology_router.get("/ontology/tbox/children")
async def tbox_children(
    request: Request,
    parent: str,
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Render subclasses of a parent class for lazy htmx expansion.

    Args:
        parent: URL-encoded IRI of the parent class.
    """
    parent_iri = unquote(parent)
    ontology_service = request.app.state.ontology_service
    try:
        classes = await ontology_service.get_subclasses(parent_iri)
    except Exception:
        logger.error(
            "Failed to load TBox children of %s", parent_iri, exc_info=True
        )
        classes = []

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "browser/ontology/tbox_children.html",
        {"classes": classes},
    )


# ------------------------------------------------------------------
# ABox Browser
# ------------------------------------------------------------------


@ontology_router.get("/ontology/abox")
async def abox_browser(
    request: Request,
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Render the ABox Browser showing types with instance counts.

    Lists all ontology classes that have at least one instance in the
    current or inferred graphs. Each type is clickable to drill down
    to its instance list.
    """
    ontology_service = request.app.state.ontology_service
    try:
        types = await ontology_service.get_type_counts()
        error = False
    except Exception:
        logger.error("Failed to load ABox type counts", exc_info=True)
        types = []
        error = True

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "browser/ontology/abox_browser.html",
        {"types": types, "error": error},
    )


@ontology_router.get("/ontology/abox/instances")
async def abox_instances(
    request: Request,
    class_iri: str = Query(..., alias="class"),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Render instances of a specific class for ABox drill-down.

    Args:
        class_iri: IRI of the class to list instances for.
    """
    iri = unquote(class_iri)
    ontology_service = request.app.state.ontology_service
    try:
        instances = await ontology_service.get_instances(iri)
        error = False
    except Exception:
        logger.error(
            "Failed to load ABox instances for %s", iri, exc_info=True
        )
        instances = []
        error = True

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "browser/ontology/abox_instances.html",
        {"instances": instances, "class_iri": iri, "error": error},
    )


# ------------------------------------------------------------------
# RBox Legend
# ------------------------------------------------------------------


@ontology_router.get("/ontology/rbox")
async def rbox_legend(
    request: Request,
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Render the RBox Legend property reference table.

    Shows object properties and datatype properties with domain and
    range columns, sourced from all ontology graphs.
    """
    ontology_service = request.app.state.ontology_service
    try:
        props = await ontology_service.get_properties()
        error = False
    except Exception:
        logger.error("Failed to load RBox properties", exc_info=True)
        props = {"object_properties": [], "datatype_properties": []}
        error = True

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "browser/ontology/rbox_legend.html",
        {
            "object_properties": props["object_properties"],
            "datatype_properties": props["datatype_properties"],
            "error": error,
        },
    )
