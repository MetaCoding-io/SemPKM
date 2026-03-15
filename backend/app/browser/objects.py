"""Object CRUD, relations, edges, and lint sub-router.

Handles object viewing/editing, body saving, relations panel,
edge provenance/deletion, bulk deletion, lint panel, type picker,
and create/save object flows.
"""

import logging
from datetime import datetime, timezone
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from rdflib import URIRef

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> gsd/M003/S05
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.db.session import get_db_session
<<<<<<< HEAD
=======
from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
>>>>>>> gsd/M002/S04
=======
>>>>>>> gsd/M003/S05
from app.dependencies import (
    get_event_store,
    get_label_service,
    get_lint_service,
    get_prefix_registry,
    get_shapes_service,
    get_triplestore_client,
    get_validation_queue,
)
<<<<<<< HEAD
<<<<<<< HEAD
from app.favorites.models import UserFavorite
=======
>>>>>>> gsd/M002/S04
=======
from app.favorites.models import UserFavorite
>>>>>>> gsd/M003/S05
from app.events.store import EventStore, Operation
from app.lint.service import LintService
from app.services.icons import IconService
from app.services.labels import LabelService
from app.services.prefixes import PrefixRegistry
from app.services.shapes import ShapesService
from app.triplestore.client import TriplestoreClient
from app.validation.queue import AsyncValidationQueue

from ._helpers import (
    _format_date,
    _validate_iri,
    get_icon_service,
)

logger = logging.getLogger(__name__)

objects_router = APIRouter(tags=["objects"])


@objects_router.get("/object/{object_iri:path}")
async def get_object(
    request: Request,
    object_iri: str,
    mode: str = Query(default="read"),
    user: User = Depends(get_current_user),
    shapes_service: ShapesService = Depends(get_shapes_service),
    label_service: LabelService = Depends(get_label_service),
    client: TriplestoreClient = Depends(get_triplestore_client),
    icon_svc: IconService = Depends(get_icon_service),
<<<<<<< HEAD
<<<<<<< HEAD
    db: AsyncSession = Depends(get_db_session),
=======
>>>>>>> gsd/M002/S04
=======
    db: AsyncSession = Depends(get_db_session),
>>>>>>> gsd/M003/S05
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

    # Build read_values: user values + inferred values merged, each tagged with source.
    # Keeps original `values` dict untouched for the edit form.
    read_values: dict[str, list[dict]] = {}
    for pred, vals in values.items():
        read_values[pred] = [{"value": v, "source": "user"} for v in vals]
    for pred, vals in inferred_values.items():
        if pred not in read_values:
            read_values[pred] = []
        for v in vals:
            read_values[pred].append({"value": v, "source": "inferred"})

    # Merge inferred labels into ref_labels so the template has a single label lookup
    ref_labels.update(inferred_labels)

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> gsd/M003/S05
    # Check if the current user has favorited this object
    fav_result = await db.execute(
        select(UserFavorite.id).where(
            UserFavorite.user_id == user.id,
            UserFavorite.object_iri == decoded_iri,
        ).limit(1)
    )
    is_favorite = fav_result.scalar_one_or_none() is not None

<<<<<<< HEAD
=======
>>>>>>> gsd/M002/S04
=======
>>>>>>> gsd/M003/S05
    context = {
        "request": request,
        "form": form,
        "values": values,
        "read_values": read_values,
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
<<<<<<< HEAD
<<<<<<< HEAD
        "is_favorite": is_favorite,
=======
>>>>>>> gsd/M002/S04
=======
        "is_favorite": is_favorite,
>>>>>>> gsd/M003/S05
    }

    return templates.TemplateResponse(
        request, "browser/object_tab.html", context
    )


@objects_router.get("/tooltip/{object_iri:path}")
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


@objects_router.post("/objects/{object_iri:path}/body")
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


@objects_router.get("/relations/{object_iri:path}")
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
            "predicate_iri": e["predicate"],
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
            "predicate_iri": e["predicate"],
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


@objects_router.get("/edge-provenance")
async def get_edge_provenance(
    request: Request,
    subject: str = Query(...),
    predicate: str = Query(...),
    target: str = Query(...),
    source: str = Query("user"),
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
    prefix_registry: PrefixRegistry = Depends(get_prefix_registry),
):
    """Return edge provenance metadata as JSON.

    Queries event named graphs to find when a specific edge triple was
    created. For inferred edges, returns inference metadata without
    event lookup. Returns predicate QName, timestamp, author, source,
    and event IRI.
    """
    if not _validate_iri(subject) or not _validate_iri(predicate) or not _validate_iri(target):
        raise HTTPException(status_code=400, detail="Invalid IRI")

    predicate_qname = prefix_registry.compact(predicate)

    if source == "inferred":
        return JSONResponse({
            "predicate_qname": predicate_qname,
            "source": "inferred",
            "description": "Inferred by OWL 2 RL reasoning",
            "event_iri": None,
            "timestamp": None,
            "performed_by": None,
        })

    # Try edge resource query first (edges created via edge.create command)
    edge_resource_sparql = f"""
    SELECT ?event ?timestamp ?performedBy WHERE {{
      GRAPH ?event {{
        ?event <urn:sempkm:timestamp> ?timestamp .
        OPTIONAL {{ ?event <urn:sempkm:performedBy> ?performedBy }}
        ?edge a <urn:sempkm:Edge> ;
              <urn:sempkm:source> <{subject}> ;
              <urn:sempkm:predicate> <{predicate}> ;
              <urn:sempkm:target> <{target}> .
      }}
      FILTER(STRSTARTS(STR(?event), "urn:sempkm:event:"))
    }}
    ORDER BY DESC(?timestamp)
    LIMIT 1
    """

    # Fallback: direct triple query (properties set during object.create/patch)
    direct_triple_sparql = f"""
    SELECT ?event ?timestamp ?performedBy WHERE {{
      GRAPH ?event {{
        ?event <urn:sempkm:timestamp> ?timestamp .
        OPTIONAL {{ ?event <urn:sempkm:performedBy> ?performedBy }}
        <{subject}> <{predicate}> <{target}> .
      }}
      FILTER(STRSTARTS(STR(?event), "urn:sempkm:event:"))
    }}
    ORDER BY DESC(?timestamp)
    LIMIT 1
    """

    event_iri = None
    timestamp = None
    performed_by = None

    try:
        result = await client.query(edge_resource_sparql)
        bindings = result.get("results", {}).get("bindings", [])
        if not bindings:
            result = await client.query(direct_triple_sparql)
            bindings = result.get("results", {}).get("bindings", [])

        if bindings:
            b = bindings[0]
            event_iri = b["event"]["value"]
            timestamp = b["timestamp"]["value"]
            if "performedBy" in b:
                performed_by = b["performedBy"]["value"]
    except Exception:
        logger.warning(
            "Failed to query edge provenance for %s %s %s",
            subject, predicate, target, exc_info=True,
        )

    # Resolve performer label if we have an IRI
    performed_by_label = None
    if performed_by:
        if performed_by.startswith("urn:sempkm:user:"):
            user_id = performed_by.rsplit(":", 1)[-1]
            from sqlalchemy import text
            try:
                db_factory = request.app.state.async_session_factory
                async with db_factory() as session:
                    row = await session.execute(
                        text("SELECT username FROM users WHERE id = :uid"),
                        {"uid": int(user_id)},
                    )
                    username = row.scalar()
                    performed_by_label = username or f"User {user_id}"
            except Exception:
                performed_by_label = f"User {user_id}"
        else:
            performed_by_label = performed_by

    return JSONResponse({
        "predicate_qname": predicate_qname,
        "source": "user",
        "event_iri": event_iri,
        "timestamp": timestamp,
        "performed_by": performed_by_label,
    })


@objects_router.post("/edge/delete")
async def delete_edge(
    request: Request,
    user: User = Depends(require_role("owner", "member")),
    client: TriplestoreClient = Depends(get_triplestore_client),
    event_store: EventStore = Depends(get_event_store),
    label_service: LabelService = Depends(get_label_service),
):
    """Delete a user-asserted edge by removing its materialized triple.

    Accepts subject, predicate, target IRIs. Creates a deletion event
    with materialize_deletes to remove the triple from the current graph.
    Also removes the edge resource if one exists.
    """
    body = await request.json()
    subject_iri = body.get("subject")
    predicate_iri = body.get("predicate")
    target_iri = body.get("target")

    if not subject_iri or not predicate_iri or not target_iri:
        raise HTTPException(status_code=400, detail="Missing subject, predicate, or target")

    if not _validate_iri(subject_iri) or not _validate_iri(predicate_iri) or not _validate_iri(target_iri):
        raise HTTPException(status_code=400, detail="Invalid IRI")

    subject = URIRef(subject_iri)
    predicate = URIRef(predicate_iri)
    target = URIRef(target_iri)

    # Delete the direct triple from current graph
    materialize_deletes = [(subject, predicate, target)]

    # Also find and delete any edge resource for this triple
    edge_query = f"""
    SELECT ?edge WHERE {{
      GRAPH <urn:sempkm:current> {{
        ?edge a <urn:sempkm:Edge> ;
              <urn:sempkm:source> <{subject_iri}> ;
              <urn:sempkm:predicate> <{predicate_iri}> ;
              <urn:sempkm:target> <{target_iri}> .
      }}
    }}
    """
    try:
        result = await client.query(edge_query)
        bindings = result.get("results", {}).get("bindings", [])
        for b in bindings:
            edge_iri = URIRef(b["edge"]["value"])
            from rdflib import Variable
            # Delete all triples where the edge resource is subject
            materialize_deletes.append((edge_iri, Variable("p"), Variable("o")))
    except Exception:
        logger.warning("Failed to query edge resource for deletion", exc_info=True)

    operation = Operation(
        operation_type="edge.delete",
        affected_iris=[subject_iri, target_iri],
        description=f"Deleted edge: {subject_iri} -> {target_iri}",
        data_triples=[],
        materialize_inserts=[],
        materialize_deletes=materialize_deletes,
    )

    user_iri = URIRef(f"urn:sempkm:user:{user.id}")
    event_result = await event_store.commit(
        [operation], performed_by=user_iri, performed_by_role=user.role
    )
    label_service.invalidate(event_result.affected_iris)

    return JSONResponse({"event_iri": str(event_result.event_iri)})


@objects_router.post("/objects/delete")
async def bulk_delete_objects(
    request: Request,
    user: User = Depends(require_role("owner", "member")),
    client: TriplestoreClient = Depends(get_triplestore_client),
    event_store: EventStore = Depends(get_event_store),
    label_service: LabelService = Depends(get_label_service),
):
    """Bulk delete objects by removing all their triples from the current graph.

    Accepts a JSON body with {"iris": ["iri1", "iri2", ...]}. For each IRI,
    queries all triples where that IRI is the subject in urn:sempkm:current,
    then creates an Operation with materialize_deletes to remove them via
    the event store (maintaining immutable audit trail).
    """
    body = await request.json()
    iris = body.get("iris", [])

    if not iris or not isinstance(iris, list):
        raise HTTPException(status_code=400, detail="Missing or invalid 'iris' array")

    # Validate all IRIs first
    for iri in iris:
        if not _validate_iri(iri):
            raise HTTPException(status_code=400, detail=f"Invalid IRI: {iri}")

    from rdflib import Variable

    operations = []
    all_affected = []

    for iri in iris:
        # Query all triples where this IRI is the subject in the current graph
        sparql = f"""
        SELECT ?p ?o WHERE {{
          GRAPH <urn:sempkm:current> {{
            <{iri}> ?p ?o .
          }}
        }}
        """
        try:
            result = await client.query(sparql)
            bindings = result.get("results", {}).get("bindings", [])
        except Exception:
            logger.warning("Failed to query triples for %s during bulk delete", iri, exc_info=True)
            bindings = []

        if not bindings:
            continue

        materialize_deletes = []
        subject = URIRef(iri)
        for b in bindings:
            pred_val = b["p"]["value"]
            obj_binding = b["o"]
            pred = URIRef(pred_val)

            if obj_binding["type"] == "uri":
                obj = URIRef(obj_binding["value"])
            elif obj_binding["type"] == "bnode":
                from rdflib import BNode
                obj = BNode(obj_binding["value"])
            else:
                from rdflib import Literal
                datatype = obj_binding.get("datatype")
                lang = obj_binding.get("xml:lang")
                if datatype:
                    obj = Literal(obj_binding["value"], datatype=URIRef(datatype))
                elif lang:
                    obj = Literal(obj_binding["value"], lang=lang)
                else:
                    obj = Literal(obj_binding["value"])

            materialize_deletes.append((subject, pred, obj))

        operation = Operation(
            operation_type="object.delete",
            affected_iris=[iri],
            description=f"Deleted object: {iri}",
            data_triples=[],
            materialize_inserts=[],
            materialize_deletes=materialize_deletes,
        )
        operations.append(operation)
        all_affected.append(iri)

    if not operations:
        return JSONResponse({"event_iri": None, "deleted_count": 0})

    user_iri = URIRef(f"urn:sempkm:user:{user.id}")
    event_result = await event_store.commit(
        operations, performed_by=user_iri, performed_by_role=user.role
    )
    label_service.invalidate(event_result.affected_iris)

    return JSONResponse({
        "event_iri": str(event_result.event_iri),
        "deleted_count": len(operations),
    })


@objects_router.get("/lint/{object_iri:path}")
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


@objects_router.get("/types")
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


@objects_router.get("/objects/new")
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


@objects_router.post("/objects")
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


@objects_router.post("/objects/{object_iri:path}/save")
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
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> gsd/M003/S04
    from app.commands.handlers.object_patch import (
        handle_object_patch,
        is_tag_property,
        split_tag_values,
    )
<<<<<<< HEAD
=======
    from app.commands.handlers.object_patch import handle_object_patch
>>>>>>> gsd/M002/S04
=======
>>>>>>> gsd/M003/S04
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

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> gsd/M003/S04
    # Split comma-separated tag values into individual entries
    for prop_key in list(properties.keys()):
        if is_tag_property(prop_key):
            split_values = []
            for v in properties[prop_key]:
                split_values.extend(split_tag_values(v))
            properties[prop_key] = split_values

<<<<<<< HEAD
=======
>>>>>>> gsd/M002/S04
=======
>>>>>>> gsd/M003/S04
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
