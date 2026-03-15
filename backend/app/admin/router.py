"""Admin portal routes for model management and webhook configuration.

Serves Jinja2 templates with htmx partial rendering for in-place updates.
Uses ModelService and WebhookService via FastAPI dependency injection.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.db.session import get_db_session
from app.dependencies import (
    get_label_service,
    get_model_service,
    get_ontology_service,
    get_ops_log_service,
    get_triplestore_client,
    get_webhook_service,
)
from app.ontology.service import OntologyService
from app.inference.entailments import ENTAILMENT_TYPES, MANIFEST_KEY_TO_TYPE, TYPE_TO_MANIFEST_KEY
from app.services.labels import LabelService
from app.services.models import ModelService
from app.services.ops_log import OperationsLogService
from app.services.settings import SettingsService
from app.services.webhooks import WebhookService
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")

# Available webhook event types
WEBHOOK_EVENT_TYPES = ["object.changed", "edge.changed", "validation.completed"]


def _is_htmx_request(request: Request) -> bool:
    """Check if the request is an htmx partial request."""
    return request.headers.get("HX-Request") == "true"


@router.get("/")
async def admin_index(request: Request, user: User = Depends(require_role("owner"))):
    """Render the admin portal landing page with links to Models and Webhooks."""
    templates = request.app.state.templates
    context = {"active_page": "admin", "user": user}
    if _is_htmx_request(request):
        return templates.TemplateResponse(
            request, "admin/index.html", context, block_name="content"
        )
    return templates.TemplateResponse(request, "admin/index.html", context)


# ---- Known activity types for filter dropdown ----
OPS_LOG_ACTIVITY_TYPES = [
    ("model.install", "Model Install"),
    ("model.remove", "Model Remove"),
    ("model.refresh", "Model Refresh"),
    ("inference.run", "Inference Run"),
    ("validation.run", "Validation Run"),
]


@router.get("/ops-log")
async def admin_ops_log(
    request: Request,
    user: User = Depends(require_role("owner")),
    ops_log: OperationsLogService = Depends(get_ops_log_service),
    activity_type: str | None = None,
    cursor: str | None = None,
):
    """Render the operations log page with filterable, paginated activity table.

    Supports htmx partial rendering: when HX-Request is present with a cursor,
    returns only the table rows block for append-based "Load more" pagination.
    When HX-Request is present without a cursor (filter change), returns the
    full table block for replacement.
    """
    page_size = 50
    activities, next_cursor = await ops_log.list_activities(
        activity_type=activity_type or None,
        cursor=cursor,
        limit=page_size,
    )

    # Compute duration for each activity
    for a in activities:
        a["duration"] = _compute_duration(a.get("started_at"), a.get("ended_at"))
        a["relative_time"] = _relative_time(a.get("started_at"))
        # Extract short actor name from IRI
        actor_iri = a.get("actor", "")
        if actor_iri.startswith("urn:sempkm:user:"):
            a["actor_short"] = "user:" + actor_iri.split(":")[-1]
        elif actor_iri == "urn:sempkm:system":
            a["actor_short"] = "system"
        else:
            a["actor_short"] = actor_iri.split("/")[-1] if "/" in actor_iri else actor_iri

    context = {
        "request": request,
        "activities": activities,
        "next_cursor": next_cursor,
        "activity_type": activity_type or "",
        "activity_types": OPS_LOG_ACTIVITY_TYPES,
        "user": user,
    }

    is_htmx = _is_htmx_request(request)

    if is_htmx:
        hx_target = request.headers.get("HX-Target", "")
        if hx_target == "app-content":
            # Sidebar navigation — return full content block
            return templates_response(
                request, "admin/ops_log.html", context, block_name="content"
            )
        else:
            # Filter change or pagination — return just the table block
            return templates_response(
                request, "admin/ops_log.html", context, block_name="table_rows"
            )
    return templates_response(request, "admin/ops_log.html", context)


def _compute_duration(started_at: str | None, ended_at: str | None) -> str:
    """Compute human-readable duration between two ISO timestamps."""
    if not started_at or not ended_at:
        return "—"
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
        diff = (end - start).total_seconds()
        if diff < 0:
            return "—"
        if diff < 1:
            return f"{int(diff * 1000)}ms"
        if diff < 60:
            return f"{diff:.1f}s"
        minutes = int(diff // 60)
        secs = int(diff % 60)
        return f"{minutes}m {secs}s"
    except (ValueError, TypeError):
        return "—"


def _relative_time(iso_str: str | None) -> str:
    """Convert an ISO timestamp to a relative time string like '2 minutes ago'."""
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = (now - dt).total_seconds()
        if diff < 0:
            return "just now"
        if diff < 60:
            return "just now"
        if diff < 3600:
            minutes = int(diff // 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        if diff < 86400:
            hours = int(diff // 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        days = int(diff // 86400)
        if days == 1:
            return "yesterday"
        if days < 30:
            return f"{days} days ago"
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return "—"


@router.get("/models")
async def admin_models(
    request: Request,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
    ontology_service: OntologyService = Depends(get_ontology_service),
):
    """Render model management page with table of installed models."""
    models = await model_service.list_models()
    try:
        gist_summary = await ontology_service.get_gist_summary()
    except Exception:
        logger.warning("Failed to load gist summary for admin page", exc_info=True)
        gist_summary = None
    try:
        custom_types = await ontology_service.list_user_types()
    except Exception:
        logger.warning("Failed to load custom types for admin page", exc_info=True)
        custom_types = {"classes": [], "object_properties": [], "datatype_properties": []}
    context = {
        "request": request,
        "models": models,
        "user": user,
        "gist": gist_summary,
        "custom_types": custom_types,
    }
    if _is_htmx_request(request):
        return templates_response(request, "admin/models.html", context, block_name="content")
    return templates_response(request, "admin/models.html", context)


@router.get("/models/{model_id}")
async def admin_model_detail(
    request: Request,
    model_id: str,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
):
    """Render read-only detail dashboard for an installed Mental Model."""
    detail = await model_service.get_model_detail(model_id)
    if detail is None:
        models = await model_service.list_models()
        context = {"request": request, "models": models, "error": f"Model '{model_id}' not found.", "user": user}
        return templates_response(request, "admin/models.html", context)

    # Get icon data from IconService
    from app.services.icons import IconService
    icon_svc = IconService(models_dir="/app/models")
    icon_map = icon_svc.get_icon_map("tree")

    # Attach icon/color to each type
    for t in detail["types"]:
        icon_info = icon_map.get(t["iri"], {"icon": "circle", "color": "#999"})
        t["icon"] = icon_info["icon"]
        t["color"] = icon_info["color"]

    # Build type-centric detail: merge shapes, views, relationships per type
    type_map = {}
    for t in detail["types"]:
        type_map[t["local_name"]] = {
            **t,
            "fields": [],
            "field_count": 0,
            "views": [],
            "relationships": [],
        }

    for shape in detail["shapes"]:
        tc = shape["target_class"]
        if tc in type_map:
            type_map[tc]["fields"] = shape["properties"]
            type_map[tc]["field_count"] = shape["property_count"]

    for v in detail["views"]:
        tc = v["target_class"]
        if tc in type_map:
            type_map[tc]["views"].append(v)

    for p in detail["properties"]:
        if p["prop_type"] == "Object":
            domain = p["domain"]
            if domain in type_map:
                type_map[domain]["relationships"].append(p)

    # Fetch live analytics (instance counts, top nodes)
    type_iris = [t["iri"] for t in detail["types"]]
    analytics = await model_service.get_type_analytics(type_iris)
    for td in type_map.values():
        a = analytics.get(td["iri"], {"count": 0, "top_nodes": [], "avg_connections": 0.0, "last_modified": None, "growth_trend": [], "link_distribution": []})
        td["instance_count"] = a["count"]
        td["top_nodes"] = a["top_nodes"]
        td["avg_connections"] = a["avg_connections"]
        td["total_links"] = int(round(a["avg_connections"] * a["count"]))
        td["last_modified"] = a["last_modified"]
        td["growth_trend"] = a["growth_trend"]
        td["link_distribution"] = a["link_distribution"]

    detail["type_details"] = list(type_map.values())

    # Stats
    detail["stats"] = {
        "types": len(detail["types"]),
        "properties": len(detail["properties"]),
        "views": len(detail["views"]),
        "shapes": len(detail["shapes"]),
    }

    context = {"request": request, "detail": detail, "user": user}
    if _is_htmx_request(request):
        return templates_response(request, "admin/model_detail.html", context, block_name="content")
    return templates_response(request, "admin/model_detail.html", context)


@router.get("/models/{model_id}/ontology-diagram")
async def admin_model_ontology_diagram(
    request: Request,
    model_id: str,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
):
    """Render Cytoscape.js ontology relationship diagram for a model.

    Shows type-to-type relationships derived from OWL ObjectProperties.
    Returns an htmx partial with Cytoscape container and inline JS initialization.
    """
    detail = await model_service.get_model_detail(model_id)
    if detail is None:
        return HTMLResponse(
            '<div class="diagram-empty"><p>Model not found.</p></div>',
            status_code=404,
        )

    # Get icon data from IconService for type colors
    from app.services.icons import IconService
    icon_svc = IconService(models_dir="/app/models")
    icon_map = icon_svc.get_icon_map("tree")

    # Build nodes list: one dict per type
    nodes = []
    for t in detail["types"]:
        icon_data = icon_map.get(t["iri"], {"icon": "circle", "color": "#999"})
        nodes.append({
            "id": t["local_name"],
            "label": t["label"],
            "color": icon_data["color"],
        })

    # Build edges list: one dict per ObjectProperty
    edges = []
    for idx, p in enumerate(detail["properties"]):
        if p["prop_type"] == "Object" and p["domain"] and p["range"]:
            edges.append({
                "id": f"edge-{idx}-{p['domain']}-{p['range']}",
                "source": p["domain"],
                "target": p["range"],
                "label": p["label"],
            })

    # Build SHACL property lookup from shapes
    shape_props: dict[str, list] = {}
    for shape in detail["shapes"]:
        tc = shape["target_class"]
        shape_props[tc] = shape["properties"]

    # Fetch instance counts
    type_iris = [t["iri"] for t in detail["types"]]
    analytics = await model_service.get_type_analytics(type_iris)

    # Build node_data dict for hover popovers
    node_data = {}
    for t in detail["types"]:
        local_name = t["local_name"]
        icon_data = icon_map.get(t["iri"], {"icon": "circle", "color": "#999"})
        props = shape_props.get(local_name, [])[:6]
        count = analytics.get(t["iri"], {}).get("count", 0)
        node_data[local_name] = {
            "label": t["label"],
            "color": icon_data["color"],
            "instance_count": count,
            "properties": [{"name": p["name"], "type": p.get("type", "any")} for p in props],
        }

    context = {
        "request": request,
        "model_id": model_id,
        "nodes": nodes,
        "edges": edges,
        "node_data": node_data,
        "has_edges": len(edges) > 0,
    }
    return templates_response(request, "admin/model_ontology_diagram.html", context)


@router.post("/models/install")
async def admin_models_install(
    request: Request,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
    ops_log: OperationsLogService = Depends(get_ops_log_service),
    path: str = Form(...),
):
    """Install a Mental Model from a filesystem path.

    Returns the updated model table partial for htmx swap.
    """
    result = await model_service.install(Path(path))
    models = await model_service.list_models()
    context = {"request": request, "models": models}

    if not result.success:
        error_msg = "; ".join(result.errors)
        context["error"] = error_msg
        logger.warning("Model install failed: %s", error_msg)
        # Log failed install to ops log (fire-and-forget)
        try:
            await ops_log.log_activity(
                activity_type="model.install",
                label=f"Install model from {path}",
                actor=f"urn:sempkm:user:{user.id}",
                used_iris=[path],
                status="failed",
                error_message=error_msg,
            )
        except Exception:
            logger.warning("Failed to write ops log for model install failure", exc_info=True)
    else:
        # Invalidate ViewSpec cache after successful model install
        request.app.state.view_spec_service.invalidate_cache()
        context["success"] = f"Model '{result.model_id}' installed successfully."
        if result.warnings:
            context["success"] += " Warnings: " + "; ".join(result.warnings)
        # Log successful install to ops log (fire-and-forget)
        try:
            model_iri = f"urn:sempkm:model:{result.model_id}"
            await ops_log.log_activity(
                activity_type="model.install",
                label=f"Installed model '{result.model_id}'",
                actor=f"urn:sempkm:user:{user.id}",
                used_iris=[model_iri],
                status="success",
            )
        except Exception:
            logger.warning("Failed to write ops log for model install", exc_info=True)

    return templates_response(request, "admin/models.html", context, block_name="model_table")


@router.delete("/models/{model_id}")
async def admin_models_remove(
    request: Request,
    model_id: str,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
    client: TriplestoreClient = Depends(get_triplestore_client),
    ops_log: OperationsLogService = Depends(get_ops_log_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Remove an installed Mental Model.

    Returns the updated model table partial for htmx swap.
    Handles 404 (not installed) and 409 (user data exists) errors.
    Also cleans up inference artifacts: inferred graph, triple state, settings.
    """
    result = await model_service.remove(model_id)
    models = await model_service.list_models()
    context = {"request": request, "models": models}

    if not result.success:
        error_msg = "; ".join(result.errors)
        context["error"] = error_msg
        logger.warning("Model remove failed for '%s': %s", model_id, error_msg)
        # Log failed removal to ops log (fire-and-forget)
        try:
            model_iri = f"urn:sempkm:model:{model_id}"
            await ops_log.log_activity(
                activity_type="model.remove",
                label=f"Remove model '{model_id}'",
                actor=f"urn:sempkm:user:{user.id}",
                used_iris=[model_iri],
                status="failed",
                error_message=error_msg,
            )
        except Exception:
            logger.warning("Failed to write ops log for model remove failure", exc_info=True)
    else:
        # Invalidate ViewSpec cache after successful model removal
        request.app.state.view_spec_service.invalidate_cache()

        # Clean up inference artifacts
        await _cleanup_inference_on_uninstall(client, db, user.id, model_id)

        context["success"] = f"Model '{model_id}' removed."
        # Log successful removal to ops log (fire-and-forget)
        try:
            model_iri = f"urn:sempkm:model:{model_id}"
            await ops_log.log_activity(
                activity_type="model.remove",
                label=f"Removed model '{model_id}'",
                actor=f"urn:sempkm:user:{user.id}",
                used_iris=[model_iri],
                status="success",
            )
        except Exception:
            logger.warning("Failed to write ops log for model remove", exc_info=True)

    return templates_response(request, "admin/models.html", context, block_name="model_table")


@router.post("/models/{model_id}/refresh-artifacts")
async def admin_models_refresh_artifacts(
    request: Request,
    model_id: str,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
    ops_log: OperationsLogService = Depends(get_ops_log_service),
):
    """Refresh a model's artifact graphs (ontology, shapes, views, rules) from disk.

    Reloads artifact files without touching user data or requiring uninstall/reinstall.
    Returns model table partial (list page) or model detail content (detail page)
    depending on the htmx target.
    """
    result = await model_service.refresh_artifacts(model_id)
    model_iri = f"urn:sempkm:model:{model_id}"

    if not result.success:
        error_msg = "; ".join(result.errors)
        logger.warning("Model artifact refresh failed for '%s': %s", model_id, error_msg)
        # Log failed refresh to ops log (fire-and-forget)
        try:
            await ops_log.log_activity(
                activity_type="model.refresh",
                label=f"Refresh artifacts for model '{model_id}'",
                actor=f"urn:sempkm:user:{user.id}",
                used_iris=[model_iri],
                status="failed",
                error_message=error_msg,
            )
        except Exception:
            logger.warning("Failed to write ops log for model refresh failure", exc_info=True)

        # Return appropriate partial based on htmx target
        hx_target = request.headers.get("HX-Target", "")
        if hx_target == "app-content":
            # Detail page — re-render full detail view with error
            return await _refresh_detail_response(request, model_id, model_service, user, error=error_msg)
        else:
            # List page — return model table partial
            models = await model_service.list_models()
            context = {"request": request, "models": models, "error": error_msg}
            return templates_response(request, "admin/models.html", context, block_name="model_table")
    else:
        # Invalidate ViewSpec cache after successful artifact refresh
        request.app.state.view_spec_service.invalidate_cache()
        graphs_str = ", ".join(result.graphs_refreshed)
        success_msg = f"Model '{model_id}' artifacts refreshed ({graphs_str})."
        # Log successful refresh to ops log (fire-and-forget)
        try:
            await ops_log.log_activity(
                activity_type="model.refresh",
                label=f"Refreshed artifacts for model '{model_id}'",
                actor=f"urn:sempkm:user:{user.id}",
                used_iris=[model_iri],
                status="success",
            )
        except Exception:
            logger.warning("Failed to write ops log for model refresh", exc_info=True)

        # Return appropriate partial based on htmx target
        hx_target = request.headers.get("HX-Target", "")
        if hx_target == "app-content":
            # Detail page — re-render full detail view with success
            return await _refresh_detail_response(request, model_id, model_service, user, success=success_msg)
        else:
            # List page — return model table partial
            models = await model_service.list_models()
            context = {"request": request, "models": models, "success": success_msg}
            return templates_response(request, "admin/models.html", context, block_name="model_table")


async def _refresh_detail_response(
    request: Request,
    model_id: str,
    model_service: ModelService,
    user: User,
    error: str | None = None,
    success: str | None = None,
):
    """Build the model detail response for a refresh triggered from the detail page.

    Re-uses the same logic as admin_model_detail() but adds success/error messages.
    """
    detail = await model_service.get_model_detail(model_id)
    if detail is None:
        models = await model_service.list_models()
        context = {"request": request, "models": models, "error": f"Model '{model_id}' not found.", "user": user}
        return templates_response(request, "admin/models.html", context, block_name="content")

    # Get icon data from IconService
    from app.services.icons import IconService
    icon_svc = IconService(models_dir="/app/models")
    icon_map = icon_svc.get_icon_map("tree")

    # Attach icon/color to each type
    for t in detail["types"]:
        icon_info = icon_map.get(t["iri"], {"icon": "circle", "color": "#999"})
        t["icon"] = icon_info["icon"]
        t["color"] = icon_info["color"]

    # Build type-centric detail
    type_map = {}
    for t in detail["types"]:
        type_map[t["local_name"]] = {
            **t,
            "fields": [],
            "field_count": 0,
            "views": [],
            "relationships": [],
        }

    for shape in detail["shapes"]:
        tc = shape["target_class"]
        if tc in type_map:
            type_map[tc]["fields"] = shape["properties"]
            type_map[tc]["field_count"] = shape["property_count"]

    for v in detail["views"]:
        tc = v["target_class"]
        if tc in type_map:
            type_map[tc]["views"].append(v)

    for p in detail["properties"]:
        if p["prop_type"] == "Object":
            domain = p["domain"]
            if domain in type_map:
                type_map[domain]["relationships"].append(p)

    # Fetch live analytics
    type_iris = [t["iri"] for t in detail["types"]]
    analytics = await model_service.get_type_analytics(type_iris)
    for td in type_map.values():
        a = analytics.get(td["iri"], {"count": 0, "top_nodes": [], "avg_connections": 0.0, "last_modified": None, "growth_trend": [], "link_distribution": []})
        td["instance_count"] = a["count"]
        td["top_nodes"] = a["top_nodes"]
        td["avg_connections"] = a["avg_connections"]
        td["total_links"] = int(round(a["avg_connections"] * a["count"]))
        td["last_modified"] = a["last_modified"]
        td["growth_trend"] = a["growth_trend"]
        td["link_distribution"] = a["link_distribution"]

    detail["type_details"] = list(type_map.values())
    detail["stats"] = {
        "types": len(detail["types"]),
        "properties": len(detail["properties"]),
        "views": len(detail["views"]),
        "shapes": len(detail["shapes"]),
    }

    context = {"request": request, "detail": detail, "user": user}
    if error:
        context["error"] = error
    if success:
        context["success"] = success

    return templates_response(request, "admin/model_detail.html", context, block_name="content")


# ---- Inference cleanup on model uninstall ----


async def _cleanup_inference_on_uninstall(
    client: TriplestoreClient,
    db: AsyncSession,
    user_id,
    model_id: str,
) -> None:
    """Clean up all inference artifacts when a model is uninstalled.

    1. Drop urn:sempkm:inferred graph (inferred triples may cross-reference
       multiple models' ontology axioms; full recompute is the correct approach)
    2. Delete all inference_triple_state SQLite records
    3. Remove entailment settings for this model from user settings

    Args:
        client: Triplestore client for SPARQL graph cleanup.
        db: Database session for SQLite cleanup.
        user_id: User ID for settings cleanup.
        model_id: The model being uninstalled.
    """
    from app.models.registry import clear_inferred_graph
    from app.inference.models import InferenceTripleState
    from sqlalchemy import delete

    # 1. Drop inferred graph
    try:
        await clear_inferred_graph(client)
        logger.info("Cleared urn:sempkm:inferred graph during model uninstall")
    except Exception as e:
        logger.warning("Failed to clear inferred graph: %s", e)

    # 2. Delete all inference_triple_state records
    try:
        await db.execute(delete(InferenceTripleState))
        logger.info("Cleared inference_triple_state table during model uninstall")
    except Exception as e:
        logger.warning("Failed to clear inference_triple_state: %s", e)

    # 3. Remove entailment settings for this model
    try:
        settings_svc = SettingsService()
        for manifest_key in MANIFEST_KEY_TO_TYPE:
            settings_key = f"inference.{model_id}.{manifest_key}"
            await settings_svc.reset_override(user_id, settings_key, db)
        logger.info("Removed entailment settings for model '%s'", model_id)
    except Exception as e:
        logger.warning("Failed to remove entailment settings: %s", e)


# ---- Entailment Config endpoints ----

# Display names and SPARQL queries for each entailment type
ENTAILMENT_DISPLAY = {
    "owl:inverseOf": {
        "display_name": "Inverse Properties",
        "description": "When A relates to B, the inverse relation from B to A is inferred.",
    },
    "rdfs:subClassOf": {
        "display_name": "Class Hierarchy",
        "description": "Instances of a subclass are also inferred to be instances of the superclass.",
    },
    "rdfs:subPropertyOf": {
        "display_name": "Property Hierarchy",
        "description": "When a sub-property relates two things, the super-property relation is also inferred.",
    },
    "owl:TransitiveProperty": {
        "display_name": "Transitive Properties",
        "description": "If A relates to B and B relates to C via a transitive property, A relates to C is inferred.",
    },
    "rdfs:domain/rdfs:range": {
        "display_name": "Domain/Range Type Inference",
        "description": "Types are inferred from property domain and range declarations.",
    },
    "sh:rule": {
        "display_name": "SHACL Rules",
        "description": "SHACL Advanced Features (SHACL-AF) rules declared in the model's rules file. These can express arbitrary derivations beyond OWL 2 RL axioms.",
    },
}


async def _query_entailment_examples(
    client: TriplestoreClient,
    model_id: str,
    label_service: LabelService,
) -> dict[str, list[dict]]:
    """Query the model's ontology graph for concrete examples of each entailment type.

    Returns a dict mapping entailment type labels to lists of example dicts.
    """
    ontology_graph = f"urn:sempkm:model:{model_id}:ontology"
    examples: dict[str, list[dict]] = {}

    # owl:inverseOf examples
    sparql = f"""SELECT ?p ?q WHERE {{
  GRAPH <{ontology_graph}> {{
    ?p <http://www.w3.org/2002/07/owl#inverseOf> ?q .
  }}
}}"""
    try:
        result = await client.query(sparql)
        iris_to_resolve = []
        pairs = []
        for b in result.get("results", {}).get("bindings", []):
            p_iri = b["p"]["value"]
            q_iri = b["q"]["value"]
            iris_to_resolve.extend([p_iri, q_iri])
            pairs.append((p_iri, q_iri))

        if pairs:
            labels = await label_service.resolve_batch(iris_to_resolve)
            examples["owl:inverseOf"] = [
                {"label_a": labels.get(p, p), "label_b": labels.get(q, q)}
                for p, q in pairs
            ]
    except Exception:
        pass

    # rdfs:subClassOf examples
    sparql = f"""SELECT ?sub ?super WHERE {{
  GRAPH <{ontology_graph}> {{
    ?sub <http://www.w3.org/2000/01/rdf-schema#subClassOf> ?super .
    FILTER(!isBlank(?sub)) FILTER(!isBlank(?super))
  }}
}}"""
    try:
        result = await client.query(sparql)
        iris_to_resolve = []
        pairs = []
        for b in result.get("results", {}).get("bindings", []):
            sub_iri = b["sub"]["value"]
            super_iri = b["super"]["value"]
            iris_to_resolve.extend([sub_iri, super_iri])
            pairs.append((sub_iri, super_iri))

        if pairs:
            labels = await label_service.resolve_batch(iris_to_resolve)
            examples["rdfs:subClassOf"] = [
                {"label_a": labels.get(s, s), "label_b": labels.get(sp, sp)}
                for s, sp in pairs
            ]
    except Exception:
        pass

    # rdfs:subPropertyOf examples
    sparql = f"""SELECT ?sub ?super WHERE {{
  GRAPH <{ontology_graph}> {{
    ?sub <http://www.w3.org/2000/01/rdf-schema#subPropertyOf> ?super .
    FILTER(!isBlank(?sub)) FILTER(!isBlank(?super))
  }}
}}"""
    try:
        result = await client.query(sparql)
        iris_to_resolve = []
        pairs = []
        for b in result.get("results", {}).get("bindings", []):
            sub_iri = b["sub"]["value"]
            super_iri = b["super"]["value"]
            iris_to_resolve.extend([sub_iri, super_iri])
            pairs.append((sub_iri, super_iri))

        if pairs:
            labels = await label_service.resolve_batch(iris_to_resolve)
            examples["rdfs:subPropertyOf"] = [
                {"label_a": labels.get(s, s), "label_b": labels.get(sp, sp)}
                for s, sp in pairs
            ]
    except Exception:
        pass

    # owl:TransitiveProperty examples
    sparql = f"""SELECT ?p WHERE {{
  GRAPH <{ontology_graph}> {{
    ?p a <http://www.w3.org/2002/07/owl#TransitiveProperty> .
  }}
}}"""
    try:
        result = await client.query(sparql)
        iris_to_resolve = []
        for b in result.get("results", {}).get("bindings", []):
            iris_to_resolve.append(b["p"]["value"])

        if iris_to_resolve:
            labels = await label_service.resolve_batch(iris_to_resolve)
            examples["owl:TransitiveProperty"] = [
                {"label_a": labels.get(p, p), "label_b": "transitive"}
                for p in iris_to_resolve
            ]
    except Exception:
        pass

    # rdfs:domain/rdfs:range examples
    sparql = f"""SELECT ?p ?domain ?range WHERE {{
  GRAPH <{ontology_graph}> {{
    OPTIONAL {{ ?p <http://www.w3.org/2000/01/rdf-schema#domain> ?domain }}
    OPTIONAL {{ ?p <http://www.w3.org/2000/01/rdf-schema#range> ?range }}
    FILTER(BOUND(?domain) || BOUND(?range))
  }}
}} LIMIT 10"""
    try:
        result = await client.query(sparql)
        iris_to_resolve = []
        triples = []
        for b in result.get("results", {}).get("bindings", []):
            p_iri = b["p"]["value"]
            d_iri = b.get("domain", {}).get("value", "")
            r_iri = b.get("range", {}).get("value", "")
            iris_to_resolve.append(p_iri)
            if d_iri:
                iris_to_resolve.append(d_iri)
            if r_iri:
                iris_to_resolve.append(r_iri)
            triples.append((p_iri, d_iri, r_iri))

        if triples:
            labels = await label_service.resolve_batch(iris_to_resolve)
            dr_examples = []
            for p, d, r in triples:
                p_label = labels.get(p, p)
                parts = []
                if d:
                    parts.append(f"domain: {labels.get(d, d)}")
                if r:
                    parts.append(f"range: {labels.get(r, r)}")
                if parts:
                    dr_examples.append({"label_a": p_label, "label_b": ", ".join(parts)})
            examples["rdfs:domain/rdfs:range"] = dr_examples
    except Exception:
        pass

    # sh:rule examples (SHACL-AF rules with rdfs:label)
    rules_graph = f"urn:sempkm:model:{model_id}:rules"
    sparql = f"""SELECT ?label WHERE {{
  GRAPH <{rules_graph}> {{
    ?shape <http://www.w3.org/ns/shacl#rule> ?ruleNode .
    ?ruleNode <http://www.w3.org/2000/01/rdf-schema#label> ?label .
  }}
}}"""
    try:
        result = await client.query(sparql)
        rule_examples = []
        for b in result.get("results", {}).get("bindings", []):
            rule_examples.append({"label_a": b["label"]["value"], "label_b": ""})
        if rule_examples:
            examples["sh:rule"] = rule_examples
    except Exception:
        pass

    return examples


def _load_entailment_defaults(model_id: str) -> dict[str, bool]:
    """Load entailment defaults from a model's manifest.yaml.

    Returns a dict mapping manifest keys (e.g., 'owl_inverseOf') to booleans.
    Falls back to all-disabled if manifest cannot be read.
    """
    import os
    manifest_path = os.path.join("/app/models", model_id, "manifest.yaml")
    defaults = {key: False for key in MANIFEST_KEY_TO_TYPE}

    try:
        with open(manifest_path) as f:
            raw = yaml.safe_load(f)
        if raw and "entailment_defaults" in raw:
            for key, val in raw["entailment_defaults"].items():
                if key in MANIFEST_KEY_TO_TYPE:
                    defaults[key] = bool(val)
    except Exception:
        pass

    return defaults


async def _get_entailment_config_for_model(
    model_id: str, user_id, db: AsyncSession
) -> dict[str, bool]:
    """Resolve entailment config: manifest defaults + user overrides.

    Returns dict mapping manifest keys to enabled booleans.
    """
    defaults = _load_entailment_defaults(model_id)

    # Check for user overrides via SettingsService
    settings_svc = SettingsService()
    overrides = await settings_svc.get_user_overrides(user_id, db)

    for manifest_key in MANIFEST_KEY_TO_TYPE:
        settings_key = f"inference.{model_id}.{manifest_key}"
        if settings_key in overrides:
            defaults[manifest_key] = overrides[settings_key] == "true"

    return defaults


@router.get("/models/{model_id}/entailment")
async def admin_model_entailment(
    request: Request,
    model_id: str,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
    client: TriplestoreClient = Depends(get_triplestore_client),
    label_service: LabelService = Depends(get_label_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Render entailment configuration page for a model.

    Shows toggles for each entailment type with concrete examples
    from the model's ontology.
    """
    # Verify model exists
    models = await model_service.list_models()
    model_info = next((m for m in models if m.model_id == model_id), None)
    if model_info is None:
        return HTMLResponse(
            '<div class="error-box">Model not found.</div>',
            status_code=404,
        )

    # Get current config (manifest defaults + user overrides)
    config = await _get_entailment_config_for_model(model_id, user.id, db)

    # Query ontology for concrete examples
    examples = await _query_entailment_examples(client, model_id, label_service)

    # Build entailment_types list for the template
    entailment_types = []
    for etype in ENTAILMENT_TYPES:
        manifest_key = TYPE_TO_MANIFEST_KEY[etype]
        display = ENTAILMENT_DISPLAY.get(etype, {})
        entailment_types.append({
            "key": manifest_key,
            "type_label": etype,
            "display_name": display.get("display_name", etype),
            "description": display.get("description", ""),
            "enabled": config.get(manifest_key, False),
            "examples": examples.get(etype, []),
        })

    context = {
        "request": request,
        "model": model_info,
        "entailment_types": entailment_types,
        "user": user,
        "success": request.query_params.get("saved"),
    }

    if _is_htmx_request(request):
        return templates_response(
            request, "admin/model_entailment_config.html", context, block_name="content"
        )
    return templates_response(request, "admin/model_entailment_config.html", context)


@router.post("/models/{model_id}/entailment")
async def admin_model_entailment_save(
    request: Request,
    model_id: str,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
    client: TriplestoreClient = Depends(get_triplestore_client),
    label_service: LabelService = Depends(get_label_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Save entailment configuration for a model.

    Reads form checkboxes and persists as user settings overrides.
    """
    # Verify model exists
    models = await model_service.list_models()
    model_info = next((m for m in models if m.model_id == model_id), None)
    if model_info is None:
        return HTMLResponse(
            '<div class="error-box">Model not found.</div>',
            status_code=404,
        )

    form_data = await request.form()
    settings_svc = SettingsService()

    for manifest_key in MANIFEST_KEY_TO_TYPE:
        settings_key = f"inference.{model_id}.{manifest_key}"
        # Checkbox: present in form data = true, absent = false
        enabled = manifest_key in form_data
        await settings_svc.set_override(user.id, settings_key, str(enabled).lower(), db)

    # Re-render the page with success message
    config = await _get_entailment_config_for_model(model_id, user.id, db)
    examples = await _query_entailment_examples(client, model_id, label_service)

    entailment_types = []
    for etype in ENTAILMENT_TYPES:
        mk = TYPE_TO_MANIFEST_KEY[etype]
        display = ENTAILMENT_DISPLAY.get(etype, {})
        entailment_types.append({
            "key": mk,
            "type_label": etype,
            "display_name": display.get("display_name", etype),
            "description": display.get("description", ""),
            "enabled": config.get(mk, False),
            "examples": examples.get(etype, []),
        })

    context = {
        "request": request,
        "model": model_info,
        "entailment_types": entailment_types,
        "user": user,
        "success": "Configuration saved. Changes take effect on the next inference run.",
    }

    if _is_htmx_request(request):
        return templates_response(
            request, "admin/model_entailment_config.html", context, block_name="content"
        )
    return templates_response(request, "admin/model_entailment_config.html", context)


# ---- Webhook endpoints ----


@router.get("/webhooks")
async def admin_webhooks(
    request: Request,
    user: User = Depends(require_role("owner")),
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    """Render webhook configuration page with list of configured webhooks."""
    webhooks = await webhook_service.list_configs()
    context = {
        "request": request,
        "webhooks": webhooks,
        "event_types": WEBHOOK_EVENT_TYPES,
        "user": user,
    }
    if _is_htmx_request(request):
        return templates_response(request, "admin/webhooks.html", context, block_name="content")
    return templates_response(request, "admin/webhooks.html", context)


@router.post("/webhooks")
async def admin_webhooks_create(
    request: Request,
    user: User = Depends(require_role("owner")),
    webhook_service: WebhookService = Depends(get_webhook_service),
    target_url: str = Form(...),
    events: list[str] = Form(default=[]),
    filters: str = Form(default=""),
):
    """Create a new webhook configuration.

    Accepts target URL, event types (multi-select), and optional filters.
    Returns updated webhook list partial for htmx swap.
    """
    # Parse comma-separated filters into list
    filter_list = [f.strip() for f in filters.split(",") if f.strip()] if filters else []

    context: dict = {
        "request": request,
        "event_types": WEBHOOK_EVENT_TYPES,
    }

    if not events:
        webhooks = await webhook_service.list_configs()
        context["webhooks"] = webhooks
        context["error"] = "Please select at least one event type."
        return templates_response(request, "admin/webhooks.html", context, block_name="webhook_list")

    try:
        await webhook_service.create_config(
            target_url=target_url,
            events=events,
            filters=filter_list if filter_list else None,
        )
        context["success"] = f"Webhook created for {target_url}."
    except Exception as e:
        context["error"] = f"Failed to create webhook: {e}"
        logger.warning("Webhook creation failed: %s", e)

    webhooks = await webhook_service.list_configs()
    context["webhooks"] = webhooks
    return templates_response(request, "admin/webhooks.html", context, block_name="webhook_list")


@router.delete("/webhooks/{webhook_id}")
async def admin_webhooks_delete(
    request: Request,
    webhook_id: str,
    user: User = Depends(require_role("owner")),
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    """Delete a webhook configuration.

    Returns updated webhook list partial for htmx swap.
    """
    context: dict = {
        "request": request,
        "event_types": WEBHOOK_EVENT_TYPES,
    }

    deleted = await webhook_service.delete_config(webhook_id)
    if not deleted:
        context["error"] = f"Webhook '{webhook_id}' not found."
    else:
        context["success"] = "Webhook deleted."

    webhooks = await webhook_service.list_configs()
    context["webhooks"] = webhooks
    return templates_response(request, "admin/webhooks.html", context, block_name="webhook_list")


@router.post("/webhooks/{webhook_id}/toggle")
async def admin_webhooks_toggle(
    request: Request,
    webhook_id: str,
    user: User = Depends(require_role("owner")),
    webhook_service: WebhookService = Depends(get_webhook_service),
):
    """Toggle a webhook's enabled/disabled state.

    Returns updated webhook list partial for htmx swap.
    """
    context: dict = {
        "request": request,
        "event_types": WEBHOOK_EVENT_TYPES,
    }

    try:
        current = await webhook_service.get_config(webhook_id)
        if current is None:
            context["error"] = f"Webhook '{webhook_id}' not found."
        else:
            new_enabled = not current.enabled
            await webhook_service.update_config(webhook_id, enabled=new_enabled)
            state = "enabled" if new_enabled else "disabled"
            context["success"] = f"Webhook {state}."
    except Exception as e:
        context["error"] = f"Failed to toggle webhook: {e}"
        logger.warning("Webhook toggle failed for '%s': %s", webhook_id, e)

    webhooks = await webhook_service.list_configs()
    context["webhooks"] = webhooks
    return templates_response(request, "admin/webhooks.html", context, block_name="webhook_list")


@router.get("/sparql")
async def admin_sparql(request: Request, user: User = Depends(require_role("owner", "member"))):
    """Redirect to workspace with SPARQL panel auto-opened.

    Previously rendered the Yasgui SPARQL console; now redirects to the
    integrated SPARQL panel in the workspace bottom panel.
    """
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/browser?panel=sparql", status_code=302)


def templates_response(request: Request, template: str, context: dict, block_name: str | None = None):
    """Render a template with optional block-level rendering."""
    templates = request.app.state.templates
    if block_name:
        return templates.TemplateResponse(request, template, context, block_name=block_name)
    return templates.TemplateResponse(request, template, context)
