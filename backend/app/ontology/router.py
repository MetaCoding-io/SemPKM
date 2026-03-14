"""Ontology sub-router — TBox, ABox, RBox endpoints for ontology browsing.

Provides htmx endpoints for:
- TBox Explorer: collapsible class hierarchy tree across gist + all model
  ontology graphs + user-types
- ABox Browser: instance counts per type with drill-down to instance lists
- RBox Legend: property reference table with domain/range columns
- Main ontology page: three-tab layout hosting TBox/ABox/RBox
- Class creation/deletion: user-defined types in urn:sempkm:user-types
"""

import json
import logging
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.ontology.service import USER_TYPES_GRAPH

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
    hide_gist: str | None = None,
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Render the TBox Explorer root class hierarchy tree.

    Queries all ontology graphs for root classes (no rdfs:subClassOf parent
    or only owl:Thing parent) and renders them as expandable tree nodes.

    When *hide_gist=1*, returns only non-gist classes plus any gist
    classes that are direct parents of model/user classes (shown as
    hierarchy context with their children pre-expanded).
    """
    ontology_service = request.app.state.ontology_service
    try:
        if hide_gist == "1":
            classes = await ontology_service.get_model_classes_with_parents()
        else:
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
# TBox Class Detail
# ------------------------------------------------------------------


@ontology_router.get("/ontology/tbox/detail")
async def tbox_detail(
    request: Request,
    iri: str = Query(...),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Render detail panel for a selected TBox class.

    Shows rdfs:comment, parent classes, sibling classes, subclass count,
    instance count, and properties with this class as domain.
    """
    ontology_service = request.app.state.ontology_service
    try:
        cls = await ontology_service.get_class_detail(iri)
        error = None
    except Exception:
        logger.error("Failed to load class detail for %s", iri, exc_info=True)
        cls = None
        error = "Failed to load class details."

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "browser/ontology/tbox_detail.html",
        {"cls": cls, "error": error},
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


# ------------------------------------------------------------------
# TBox class search (for parent class picker)
# ------------------------------------------------------------------


@ontology_router.get("/ontology/tbox/search")
async def tbox_search(
    request: Request,
    q: str = Query(""),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Search classes by label for the parent class picker dropdown.

    Returns an HTML list of matching classes (label + IRI) for selection.
    """
    if not q.strip():
        return HTMLResponse(content="", status_code=200)

    ontology_service = request.app.state.ontology_service
    try:
        classes = await ontology_service.search_classes(q.strip())
    except Exception:
        logger.error("TBox search failed for q=%s", q, exc_info=True)
        classes = []

    if not classes:
        return HTMLResponse(
            content='<div class="parent-class-empty">No classes found</div>',
            status_code=200,
        )

    # Build HTML list of results
    items = []
    for cls in classes:
        escaped_iri = cls["iri"].replace("&", "&amp;").replace('"', "&quot;")
        escaped_label = cls["label"].replace("&", "&amp;").replace("<", "&lt;")
        items.append(
            f'<div class="parent-class-option" '
            f'onclick="selectParentClass(this, \'{escaped_iri}\', \'{escaped_label}\')" '
            f'data-iri="{escaped_iri}" data-label="{escaped_label}">'
            f'<span class="parent-class-option-label">{escaped_label}</span>'
            f'<span class="parent-class-option-iri">{escaped_iri}</span>'
            f'</div>'
        )

    return HTMLResponse(content="\n".join(items), status_code=200)


# ------------------------------------------------------------------
# Class creation form
# ------------------------------------------------------------------


@ontology_router.get("/ontology/create-class-form")
async def create_class_form(
    request: Request,
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Render the class creation form template."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "browser/ontology/create_class_form.html",
        {},
    )


# ------------------------------------------------------------------
# Class creation and deletion
# ------------------------------------------------------------------


@ontology_router.post("/ontology/create-class")
async def create_class(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    example: str = Form(""),
    icon: str = Form(""),
    icon_color: str = Form(""),
    parent_iri: str = Form(...),
    properties: str = Form("[]"),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Create a user-defined OWL class with SHACL NodeShape.

    Accepts form data with class definition, creates OWL + SHACL triples
    in the urn:sempkm:user-types named graph. Returns an HTML confirmation
    snippet with HX-Trigger header for TBox auto-refresh.

    Returns:
        200 with HTML snippet and HX-Trigger: classCreated on success.
        422 with error message on validation failure.
    """
    # Parse properties JSON
    try:
        props_list = json.loads(properties)
        if not isinstance(props_list, list):
            raise ValueError("properties must be a JSON array")
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("create-class: invalid properties JSON: %s", exc)
        return HTMLResponse(
            content=f'<div class="error-message">Invalid properties format: {exc}</div>',
            status_code=422,
        )

    ontology_service = request.app.state.ontology_service

    try:
        result = await ontology_service.create_class(
            name=name.strip(),
            parent_iri=parent_iri.strip(),
            properties=props_list,
            icon_name=icon.strip() or None,
            icon_color=icon_color.strip() or None,
            description=description.strip() or None,
            example=example.strip() or None,
        )
    except ValueError as exc:
        logger.warning("create-class validation error: %s", exc)
        return HTMLResponse(
            content=f'<div class="error-message">{exc}</div>',
            status_code=422,
        )
    except Exception:
        logger.error("create-class failed", exc_info=True)
        return HTMLResponse(
            content='<div class="error-message">Server error creating class</div>',
            status_code=500,
        )

    # Update user-type icon cache on IconService if available
    _update_icon_cache(request, result["class_iri"], icon.strip(), icon_color.strip())

    response = HTMLResponse(
        content=(
            f'<div class="success-message">'
            f'Created class <strong>{name.strip()}</strong>'
            f'<br><code>{result["class_iri"]}</code>'
            f'</div>'
        ),
        status_code=200,
    )
    response.headers["HX-Trigger"] = "classCreated"
    return response


@ontology_router.delete("/ontology/delete-class")
async def delete_class(
    request: Request,
    class_iri: str = Query(...),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Delete a user-defined class and its SHACL NodeShape.

    Only classes in the urn:sempkm:user-types namespace can be deleted.
    Removes all OWL + SHACL triples for the class from the triplestore.

    Returns:
        200 with HX-Trigger: classDeleted on success.
        403 if the class IRI is not in the user-types namespace.
    """
    if not class_iri.startswith(f"{USER_TYPES_GRAPH}:"):
        logger.warning(
            "delete-class rejected: IRI not in user-types namespace: %s",
            class_iri,
        )
        return HTMLResponse(
            content='<div class="error-message">Only user-created classes can be deleted</div>',
            status_code=403,
        )

    ontology_service = request.app.state.ontology_service

    try:
        result = await ontology_service.delete_class(class_iri)
    except Exception:
        logger.error("delete-class failed for %s", class_iri, exc_info=True)
        return HTMLResponse(
            content='<div class="error-message">Server error deleting class</div>',
            status_code=500,
        )

    # Remove from icon cache
    _remove_from_icon_cache(request, class_iri)

    response = HTMLResponse(
        content=f'<div class="success-message">Deleted class <code>{class_iri}</code></div>',
        status_code=200,
    )
    response.headers["HX-Trigger"] = "classDeleted"
    return response


# ------------------------------------------------------------------
# Delete property
# ------------------------------------------------------------------


@ontology_router.delete("/ontology/delete-property")
async def delete_property(
    request: Request,
    property_iri: str = Query(...),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Delete a user-defined property from the user-types graph.

    Only properties in the urn:sempkm:user-types namespace can be deleted.

    Returns:
        200 with HX-Trigger: propertyDeleted on success.
        403 if the property IRI is not in the user-types namespace.
        500 on SPARQL failure.
    """
    if not property_iri.startswith(f"{USER_TYPES_GRAPH}:"):
        logger.warning(
            "delete-property rejected: IRI not in user-types namespace: %s",
            property_iri,
        )
        return HTMLResponse(
            content='<div class="error-message">Only user-created properties can be deleted</div>',
            status_code=403,
        )

    ontology_service = request.app.state.ontology_service

    try:
        await ontology_service.delete_property(property_iri)
    except Exception:
        logger.error(
            "delete-property failed for %s", property_iri, exc_info=True
        )
        return HTMLResponse(
            content='<div class="error-message">Server error deleting property</div>',
            status_code=500,
        )

    response = HTMLResponse(
        content=f'<div class="success-message">Deleted property <code>{property_iri}</code></div>',
        status_code=200,
    )
    response.headers["HX-Trigger"] = "propertyDeleted"
    return response


# ------------------------------------------------------------------
# Delete class check (pre-delete confirmation info)
# ------------------------------------------------------------------


@ontology_router.get("/ontology/delete-class-check")
async def delete_class_check(
    request: Request,
    class_iri: str = Query(...),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Return a confirmation HTML fragment with instance/subclass counts.

    Used by the UI to show a confirmation modal before class deletion.

    Returns:
        200 with HTML confirmation fragment.
        403 if the class IRI is not in the user-types namespace.
        500 on SPARQL failure.
    """
    if not class_iri.startswith(f"{USER_TYPES_GRAPH}:"):
        logger.warning(
            "delete-class-check rejected: IRI not in user-types namespace: %s",
            class_iri,
        )
        return HTMLResponse(
            content='<div class="error-message">Only user-created classes can be deleted</div>',
            status_code=403,
        )

    ontology_service = request.app.state.ontology_service

    try:
        info = await ontology_service.get_delete_class_info(class_iri)
    except Exception:
        logger.error(
            "delete-class-check failed for %s", class_iri, exc_info=True
        )
        return HTMLResponse(
            content='<div class="error-message">Server error loading class info</div>',
            status_code=500,
        )

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "browser/ontology/delete_class_confirm.html",
        {
            "class_iri": info["class_iri"],
            "label": info["label"],
            "instance_count": info["instance_count"],
            "subclass_count": info["subclass_count"],
        },
    )


# ------------------------------------------------------------------
# Property creation
# ------------------------------------------------------------------


@ontology_router.get("/ontology/create-property-form")
async def create_property_form(
    request: Request,
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Render the property creation form template."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "browser/ontology/create_property_form.html",
        {},
    )


@ontology_router.post("/ontology/create-property")
async def create_property(
    request: Request,
    name: str = Form(...),
    prop_type: str = Form(...),
    domain_iri: str = Form(""),
    range_iri: str = Form(""),
    description: str = Form(""),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Create a user-defined OWL property.

    Returns:
        200 with HX-Trigger: propertyCreated on success.
        422 on validation failure.
    """
    ontology_service = request.app.state.ontology_service

    try:
        result = await ontology_service.create_property(
            name=name.strip(),
            prop_type=prop_type.strip(),
            domain_iri=domain_iri.strip() or None,
            range_iri=range_iri.strip() or None,
            description=description.strip() or None,
        )
    except ValueError as exc:
        logger.warning("create-property validation error: %s", exc)
        return HTMLResponse(
            content=f'<div class="error-message">{exc}</div>',
            status_code=422,
        )
    except Exception:
        logger.error("create-property failed", exc_info=True)
        return HTMLResponse(
            content='<div class="error-message">Server error creating property</div>',
            status_code=500,
        )

    response = HTMLResponse(
        content=(
            f'<div class="success-message">'
            f'Created {prop_type} property <strong>{name.strip()}</strong>'
            f'<br><code>{result["property_iri"]}</code>'
            f'</div>'
        ),
        status_code=200,
    )
    response.headers["HX-Trigger"] = "propertyCreated"
    return response


# ------------------------------------------------------------------
# Class editing
# ------------------------------------------------------------------


@ontology_router.get("/ontology/edit-class-form")
async def edit_class_form(
    request: Request,
    class_iri: str = Query(...),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Render the class edit form pre-populated with current values."""
    ontology_service = request.app.state.ontology_service
    class_data = await ontology_service.get_class_for_edit(
        unquote(class_iri)
    )

    if not class_data:
        return HTMLResponse(
            content='<div class="error-message">Class not found</div>',
            status_code=404,
        )

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "browser/ontology/edit_class_form.html",
        {"cls": class_data},
    )


@ontology_router.post("/ontology/edit-class")
async def edit_class(
    request: Request,
    class_iri: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    example: str = Form(""),
    icon: str = Form(""),
    icon_color: str = Form(""),
    parent_iri: str = Form(...),
    properties: str = Form("[]"),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    """Edit a user-defined class (full replacement).

    Returns:
        200 with HX-Trigger: classEdited on success.
        403 if not a user-types class.
        422 on validation failure.
    """
    if not class_iri.startswith(f"{USER_TYPES_GRAPH}:"):
        return HTMLResponse(
            content='<div class="error-message">Only user-created classes can be edited</div>',
            status_code=403,
        )

    try:
        props_list = json.loads(properties)
        if not isinstance(props_list, list):
            raise ValueError("properties must be a JSON array")
    except (json.JSONDecodeError, ValueError) as exc:
        return HTMLResponse(
            content=f'<div class="error-message">Invalid properties format: {exc}</div>',
            status_code=422,
        )

    ontology_service = request.app.state.ontology_service

    try:
        result = await ontology_service.edit_class(
            class_iri=class_iri.strip(),
            name=name.strip(),
            parent_iri=parent_iri.strip(),
            properties=props_list,
            icon_name=icon.strip() or None,
            icon_color=icon_color.strip() or None,
            description=description.strip() or None,
            example=example.strip() or None,
        )
    except ValueError as exc:
        logger.warning("edit-class validation error: %s", exc)
        return HTMLResponse(
            content=f'<div class="error-message">{exc}</div>',
            status_code=422,
        )
    except Exception:
        logger.error("edit-class failed for %s", class_iri, exc_info=True)
        return HTMLResponse(
            content='<div class="error-message">Server error editing class</div>',
            status_code=500,
        )

    # Update icon cache
    _update_icon_cache(request, class_iri, icon.strip(), icon_color.strip())

    response = HTMLResponse(
        content=(
            f'<div class="success-message">'
            f'Updated class <strong>{name.strip()}</strong>'
            f'</div>'
        ),
        status_code=200,
    )
    response.headers["HX-Trigger"] = "classEdited"
    return response


# ------------------------------------------------------------------
# Icon cache helpers
# ------------------------------------------------------------------


def _update_icon_cache(
    request: Request,
    class_iri: str,
    icon_name: str,
    icon_color: str,
) -> None:
    """Update the app-level user-type icon cache after class creation."""
    icon_cache = getattr(request.app.state, "user_type_icons", None)
    if icon_cache is None:
        request.app.state.user_type_icons = {}
        icon_cache = request.app.state.user_type_icons

    if icon_name:
        icon_cache[class_iri] = {
            "icon": icon_name,
            "color": icon_color or "var(--color-text-faint)",
        }


def _remove_from_icon_cache(request: Request, class_iri: str) -> None:
    """Remove a class from the app-level user-type icon cache."""
    icon_cache = getattr(request.app.state, "user_type_icons", None)
    if icon_cache and class_iri in icon_cache:
        del icon_cache[class_iri]
