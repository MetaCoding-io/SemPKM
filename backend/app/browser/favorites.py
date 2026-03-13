"""Favorites sub-router — toggle and list endpoints for starred objects."""

import logging

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.db.session import get_db_session
from app.dependencies import get_label_service
from app.favorites.models import UserFavorite
from app.services.icons import IconService
from app.services.labels import LabelService

from ._helpers import get_icon_service

logger = logging.getLogger(__name__)

favorites_router = APIRouter(tags=["favorites"])


@favorites_router.post("/favorites/toggle")
async def toggle_favorite(
    request: Request,
    object_iri: str = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """Toggle a favorite on/off for the current user.

    If the (user, object_iri) pair exists, delete it (unfavorite).
    If it doesn't exist, insert a new row (favorite).
    Returns an updated star button HTML snippet and sets HX-Trigger
    so the FAVORITES section auto-refreshes.
    """
    result = await db.execute(
        select(UserFavorite).where(
            UserFavorite.user_id == user.id,
            UserFavorite.object_iri == object_iri,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        await db.execute(
            delete(UserFavorite).where(UserFavorite.id == existing.id)
        )
        action = "removed"
        is_favorited = False
        logger.debug(
            "Favorite toggled: user_id=%s, object_iri=%s, action=remove",
            user.id,
            object_iri,
        )
    else:
        fav = UserFavorite(user_id=user.id, object_iri=object_iri)
        db.add(fav)
        action = "added"
        is_favorited = True
        logger.debug(
            "Favorite toggled: user_id=%s, object_iri=%s, action=add",
            user.id,
            object_iri,
        )

    # Render star button HTML — filled star if favorited, outline if not
    if is_favorited:
        star_html = (
            '<button class="toolbar-btn favorite-btn is-favorited" '
            f'title="Remove from favorites" '
            f'hx-post="/browser/favorites/toggle" '
            f'hx-vals=\'{{"object_iri": "{object_iri}"}}\' '
            f'hx-swap="outerHTML">'
            '<i data-lucide="star" class="favorite-icon filled"></i>'
            "</button>"
        )
    else:
        star_html = (
            '<button class="toolbar-btn favorite-btn" '
            f'title="Add to favorites" '
            f'hx-post="/browser/favorites/toggle" '
            f'hx-vals=\'{{"object_iri": "{object_iri}"}}\' '
            f'hx-swap="outerHTML">'
            '<i data-lucide="star" class="favorite-icon"></i>'
            "</button>"
        )

    response = HTMLResponse(content=star_html)
    response.headers["HX-Trigger"] = "favoritesRefreshed"
    return response


@favorites_router.get("/favorites/list")
async def list_favorites(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    label_service: LabelService = Depends(get_label_service),
    icon_svc: IconService = Depends(get_icon_service),
) -> HTMLResponse:
    """Return favorited objects as tree-leaf HTML for the FAVORITES section.

    Resolves labels and type icons via LabelService and SPARQL.
    Filters out dangling favorites (deleted objects with no label resolution).
    """
    templates = request.app.state.templates
    client = request.app.state.triplestore_client

    # Fetch all favorites for the user, newest first
    result = await db.execute(
        select(UserFavorite)
        .where(UserFavorite.user_id == user.id)
        .order_by(UserFavorite.created_at.desc())
    )
    favorites = result.scalars().all()

    if not favorites:
        return templates.TemplateResponse(
            request,
            "browser/partials/favorites_list.html",
            {"request": request, "objects": []},
        )

    object_iris = [f.object_iri for f in favorites]

    # Batch-resolve labels
    labels = await label_service.resolve_batch(object_iris)

    # Batch-resolve types via SPARQL
    values_clause = " ".join(f"(<{iri}>)" for iri in object_iris)
    sparql = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?iri ?typeIri
    FROM <urn:sempkm:current>
    WHERE {{
      VALUES (?iri) {{ {values_clause} }}
      ?iri rdf:type ?typeIri .
      FILTER(?typeIri != <http://www.w3.org/2000/01/rdf-schema#Resource>)
    }}
    """
    try:
        sparql_result = await client.query(sparql)
        bindings = sparql_result.get("results", {}).get("bindings", [])
    except Exception:
        logger.warning("Failed to query types for favorites", exc_info=True)
        bindings = []

    # Build IRI → type_iri map (first type wins)
    iri_types: dict[str, str] = {}
    for b in bindings:
        iri = b["iri"]["value"]
        if iri not in iri_types:
            iri_types[iri] = b["typeIri"]["value"]

    # Build objects list, filtering dangling favorites
    objects = []
    dangling_count = 0
    for iri in object_iris:
        label = labels.get(iri)
        # A favorite is dangling if label resolution returned the raw IRI
        # (no triples found) and it has no type — meaning the object
        # likely no longer exists in the triplestore
        if label is None or (label == iri and iri not in iri_types):
            dangling_count += 1
            continue

        type_iri = iri_types.get(iri, "")
        icon = (
            icon_svc.get_type_icon(type_iri, context="tree")
            if type_iri
            else {"icon": "circle", "color": "var(--color-text-faint)", "size": 14}
        )
        objects.append({
            "iri": iri,
            "label": label,
            "icon": icon,
        })

    if dangling_count > 0:
        logger.warning(
            "Filtered %d dangling favorites for user %s", dangling_count, user.id
        )

    return templates.TemplateResponse(
        request,
        "browser/partials/favorites_list.html",
        {"request": request, "objects": objects},
    )
