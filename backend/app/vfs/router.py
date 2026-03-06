"""VFS file-browser router.

Serves the VFS file-browser page and API endpoints for the tree and
file content.  Uses the async TriplestoreClient (not the sync WebDAV one)
so everything runs on the main event loop.

Endpoints:
  GET /browser/vfs           -> full page (or htmx content block)
  GET /api/vfs/tree          -> JSON tree [{model, types: [{type, files: [...]}]}]
  GET /api/vfs/file          -> JSON {content, path} for a single .md file
  PUT /api/vfs/file          -> save file content back via event store
"""

import hashlib
import logging
import re
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

import frontmatter

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.dependencies import get_event_store, get_triplestore_client
from app.events.store import EventStore
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

router = APIRouter(tags=["vfs-browser"])

# ── helpers ──────────────────────────────────────────────────────────

_PREDICATE_LABELS: dict[str, str] = {
    "http://purl.org/dc/terms/title": "title",
    "http://www.w3.org/2000/01/rdf-schema#label": "rdfs_label",
    "http://www.w3.org/2004/02/skos/core#prefLabel": "pref_label",
    "http://xmlns.com/foaf/0.1/name": "name",
    "http://purl.org/dc/terms/description": "description",
    "https://schema.org/description": "schema_description",
    "http://purl.org/dc/terms/created": "created",
    "http://purl.org/dc/terms/modified": "modified",
    "https://schema.org/jobTitle": "job_title",
    "https://schema.org/worksFor": "works_for",
    "http://xmlns.com/foaf/0.1/mbox": "email",
}

_SKIP_PREDICATES = {
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
}


def _slugify(text: str) -> str:
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")
    return slug or "untitled"


# ── page route ───────────────────────────────────────────────────────

@router.get("/browser/vfs")
async def vfs_page(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Render the VFS file-browser page."""
    templates = request.app.state.templates
    context = {
        "request": request,
        "user": user,
        "active_page": "vfs",
    }
    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(
            request, "browser/vfs_browser.html", context, block_name="content"
        )
    return templates.TemplateResponse(request, "browser/vfs_browser.html", context)


# ── tree API ─────────────────────────────────────────────────────────

@router.get("/api/vfs/tree")
async def vfs_tree(
    request: Request,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Return the full VFS tree as JSON.

    Structure: [{id, label, children: [{id, label, children: [{id, label, path}]}]}]
    """
    # 1. Get models
    models_result = await client.query("""
        SELECT DISTINCT ?modelId FROM <urn:sempkm:models>
        WHERE {
          ?model a <urn:sempkm:MentalModel> ;
                 <urn:sempkm:modelId> ?modelId .
        }
    """)
    models = [b["modelId"]["value"] for b in models_result["results"]["bindings"]]

    tree = []
    for model_id in sorted(models):
        # 2. Get types for this model
        types_result = await client.query(f"""
            PREFIX sh: <http://www.w3.org/ns/shacl#>
            SELECT DISTINCT ?typeLabel ?class
            FROM <urn:sempkm:model:{model_id}:shapes>
            WHERE {{
              ?shape sh:targetClass ?class .
              BIND(REPLACE(STR(?class), ".*[/:#]", "") AS ?typeLabel)
            }}
        """)
        type_entries = []
        for tb in types_result["results"]["bindings"]:
            type_label = tb["typeLabel"]["value"]
            type_iri = tb["class"]["value"]

            # 3. Get objects for this type
            objs_result = await client.query(f"""
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX dcterms: <http://purl.org/dc/terms/>
                PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
                PREFIX foaf: <http://xmlns.com/foaf/0.1/>
                SELECT ?iri ?label FROM <urn:sempkm:current>
                WHERE {{
                  ?iri a <{type_iri}> .
                  OPTIONAL {{ ?iri dcterms:title ?t }}
                  OPTIONAL {{ ?iri rdfs:label ?r }}
                  OPTIONAL {{ ?iri skos:prefLabel ?s }}
                  OPTIONAL {{ ?iri foaf:name ?f }}
                  BIND(COALESCE(?t, ?r, ?s, ?f, REPLACE(STR(?iri), ".*[/:#]", "")) AS ?label)
                }}
                ORDER BY ?label
            """)

            # Build file list with slugified names
            entries = []
            slug_counts: dict[str, int] = {}
            for ob in objs_result["results"]["bindings"]:
                iri = ob["iri"]["value"]
                label = ob["label"]["value"]
                slug = _slugify(label)
                slug_counts[slug] = slug_counts.get(slug, 0) + 1
                entries.append({"iri": iri, "label": label, "slug": slug})

            files = []
            for entry in entries:
                slug = entry["slug"]
                if slug_counts[slug] > 1:
                    iri_hash = hashlib.sha256(entry["iri"].encode()).hexdigest()[:6]
                    filename = f"{slug}--{iri_hash}.md"
                else:
                    filename = f"{slug}.md"
                files.append({
                    "id": f"{model_id}/{type_label}/{filename}",
                    "label": entry["label"],
                    "filename": filename,
                    "iri": entry["iri"],
                })

            type_entries.append({
                "id": f"{model_id}/{type_label}",
                "label": type_label,
                "children": files,
            })

        type_entries.sort(key=lambda t: t["label"])
        tree.append({
            "id": model_id,
            "label": model_id,
            "children": type_entries,
        })

    return JSONResponse(tree)


# ── file content API ─────────────────────────────────────────────────

@router.get("/api/vfs/file")
async def vfs_file_content(
    request: Request,
    path: str = Query(..., description="VFS path like model-id/TypeLabel/slug.md"),
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Return rendered file content (markdown+frontmatter) as JSON."""
    parts = [p for p in path.strip("/").split("/") if p]
    if len(parts) != 3 or not parts[2].endswith(".md"):
        raise HTTPException(400, "Invalid path — expected model/type/file.md")

    model_id, type_label, filename = parts

    # Resolve type IRI
    type_result = await client.query(f"""
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        SELECT ?class FROM <urn:sempkm:model:{model_id}:shapes>
        WHERE {{
          ?shape sh:targetClass ?class .
          FILTER(REPLACE(STR(?class), ".*[/:#]", "") = "{type_label}")
        }}
        LIMIT 1
    """)
    type_bindings = type_result["results"]["bindings"]
    if not type_bindings:
        raise HTTPException(404, f"Type {type_label} not found in model {model_id}")
    type_iri = type_bindings[0]["class"]["value"]

    # Get objects for type, build file map to resolve filename -> IRI
    objs_result = await client.query(f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        SELECT ?iri ?label FROM <urn:sempkm:current>
        WHERE {{
          ?iri a <{type_iri}> .
          OPTIONAL {{ ?iri dcterms:title ?t }}
          OPTIONAL {{ ?iri rdfs:label ?r }}
          OPTIONAL {{ ?iri skos:prefLabel ?s }}
          OPTIONAL {{ ?iri foaf:name ?f }}
          BIND(COALESCE(?t, ?r, ?s, ?f, REPLACE(STR(?iri), ".*[/:#]", "")) AS ?label)
        }}
        ORDER BY ?label
    """)

    entries = []
    slug_counts: dict[str, int] = {}
    for ob in objs_result["results"]["bindings"]:
        iri = ob["iri"]["value"]
        label = ob["label"]["value"]
        slug = _slugify(label)
        slug_counts[slug] = slug_counts.get(slug, 0) + 1
        entries.append({"iri": iri, "label": label, "slug": slug})

    object_iri = None
    object_label = None
    for entry in entries:
        slug = entry["slug"]
        if slug_counts[slug] > 1:
            iri_hash = hashlib.sha256(entry["iri"].encode()).hexdigest()[:6]
            fn = f"{slug}--{iri_hash}.md"
        else:
            fn = f"{slug}.md"
        if fn == filename:
            object_iri = entry["iri"]
            object_label = entry["label"]
            break

    if object_iri is None:
        raise HTTPException(404, f"File {filename} not found")

    # Fetch all properties
    props_result = await client.query(f"""
        SELECT ?predicate ?object FROM <urn:sempkm:current>
        WHERE {{ <{object_iri}> ?predicate ?object . }}
    """)

    fm: dict = {
        "type_iri": type_iri,
        "object_iri": object_iri,
        "label": object_label,
    }
    body_text = ""

    for b in props_result["results"]["bindings"]:
        pred = b["predicate"]["value"]
        obj_val = b["object"]["value"]
        if pred in _SKIP_PREDICATES:
            continue
        pred_local = pred.rsplit("/", 1)[-1].rsplit(":", 1)[-1]
        if pred_local == "body":
            body_text = obj_val
            continue
        if pred in _PREDICATE_LABELS:
            fm[_PREDICATE_LABELS[pred]] = obj_val

    post = frontmatter.Post(content=body_text, **fm)
    content = frontmatter.dumps(post)

    return JSONResponse({
        "content": content,
        "path": path,
        "iri": object_iri,
        "label": object_label,
    })


# ── file save API ────────────────────────────────────────────────────

@router.put("/api/vfs/file")
async def vfs_file_save(
    request: Request,
    path: str = Query(..., description="VFS path like model-id/TypeLabel/slug.md"),
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
    event_store: EventStore = Depends(get_event_store),
):
    """Save file content back. Strips frontmatter and commits body.set."""
    parts = [p for p in path.strip("/").split("/") if p]
    if len(parts) != 3 or not parts[2].endswith(".md"):
        raise HTTPException(400, "Invalid path")

    body_json = await request.json()
    raw_content = body_json.get("content", "")

    # Parse frontmatter to extract just the body
    try:
        post = frontmatter.loads(raw_content)
        body = post.content
        object_iri = post.metadata.get("object_iri")
    except Exception:
        body = raw_content
        object_iri = None

    if not object_iri:
        raise HTTPException(400, "Missing object_iri in frontmatter")

    user_iri = f"urn:sempkm:user:{user.id}" if user else None
    user_role = "member"

    from app.vfs.write import write_body_via_event_store
    write_body_via_event_store(
        object_iri=object_iri,
        body=body,
        event_store=event_store,
        user_iri=user_iri,
        user_role=user_role,
    )

    return JSONResponse({"ok": True, "iri": object_iri})
