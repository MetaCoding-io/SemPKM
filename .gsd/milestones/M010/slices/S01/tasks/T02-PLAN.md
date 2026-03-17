---
estimated_steps: 6
estimated_files: 5
---

# T02: Create rss-feeds Mental Model with Article and FeedSubscription types

**Slice:** S01 — Platform fix + Mental Model + App data pipeline
**Milestone:** M010

## Description

Creates the `rss-feeds` Mental Model following the exact patterns of `models/basic-pkm/`. This model defines two core RDF types — `rss:Article` and `rss:FeedSubscription` — with OWL ontology, SHACL shapes for form generation, and ViewSpecs for browsing. The model is installable independently of the RSS Reader app (per RSS-07).

Reference the existing `models/basic-pkm/` directory for all file formats and conventions. The model namespace is `urn:sempkm:model:rss-feeds:` with prefix `rss`.

## Steps

1. Create `models/rss-feeds/manifest.yaml`:
   ```yaml
   modelId: rss-feeds
   version: "1.0.0"
   name: "RSS Feeds"
   description: "RSS/Atom feed articles and subscriptions. Provides Article and FeedSubscription types for feed reader applications."
   namespace: "urn:sempkm:model:rss-feeds:"
   prefixes:
     rss: "urn:sempkm:model:rss-feeds:"
   entrypoints:
     ontology: "ontology/rss-feeds.jsonld"
     shapes: "shapes/rss-feeds.jsonld"
     views: "views/rss-feeds.jsonld"
     seed: null
   icons:
     - type: "rss:Article"
       icon: "newspaper"
       color: "#f59e0b"
       tree: { icon: "newspaper", color: "#f59e0b", size: 16 }
       tab: { icon: "newspaper", color: "#f59e0b", size: 14 }
       graph: { icon: "newspaper", color: "#f59e0b" }
     - type: "rss:FeedSubscription"
       icon: "rss"
       color: "#3b82f6"
       tree: { icon: "rss", color: "#3b82f6", size: 16 }
       tab: { icon: "rss", color: "#3b82f6", size: 14 }
       graph: { icon: "rss", color: "#3b82f6" }
       browserVisible: false
   ```
   Note: FeedSubscription has `browserVisible: false` — managed by the app, not cluttering the object browser.

2. Create `models/rss-feeds/ontology/rss-feeds.jsonld` — OWL ontology with:
   - `rss:Article` class (subClassOf `gist:FormattedContent`) with properties:
     - `dcterms:title` (string, required) — article title
     - `rss:link` (anyURI) — original article URL
     - `rss:author` (string) — author name
     - `dcterms:created` (dateTime) — publication date
     - `dcterms:description` (string) — article summary
     - `rss:feedSource` (object property → rss:FeedSubscription) — which feed it came from
     - `rss:isRead` (boolean, default false) — read/unread state
     - `rss:isStarred` (boolean, default false) — starred state
     - `rss:articleId` (string) — unique article identifier (feed entry ID / GUID)
   - `rss:FeedSubscription` class with properties:
     - `dcterms:title` (string) — feed title
     - `rss:feedUrl` (anyURI, required) — RSS/Atom feed URL
     - `rss:siteUrl` (anyURI) — website URL
     - `rss:lastPolled` (dateTime) — last poll timestamp
     - `rss:errorCount` (integer) — consecutive error count
     - `rss:lastError` (string) — last error message
     - `rss:etag` (string) — HTTP ETag for conditional GET
     - `rss:lastModifiedHeader` (string) — HTTP Last-Modified for conditional GET
   - Use `@context` with prefixes matching `basic-pkm` pattern (owl, rdf, rdfs, xsd, dcterms, schema, gist)

3. Create `models/rss-feeds/shapes/rss-feeds.jsonld` — SHACL shapes:
   - `rss:ArticleShape` targeting `rss:Article` with PropertyGroups:
     - "Basic Info" (title, link, author, published, summary) — sh:order 1
     - "Feed" (feedSource) — sh:order 2
     - "Status" (isRead, isStarred) — sh:order 3
   - `rss:FeedSubscriptionShape` targeting `rss:FeedSubscription` with PropertyGroups:
     - "Feed Info" (title, feedUrl, siteUrl) — sh:order 1
     - "Polling" (lastPolled, errorCount, lastError) — sh:order 2
   - Follow the `basic-pkm` shapes pattern exactly: `sh:NodeShape`, `sh:PropertyGroup`, `sh:property` arrays with `sh:path`, `sh:name`, `sh:datatype`/`sh:class`, `sh:minCount`, `sh:maxCount`, `sh:order`, `sh:group`, `sh:description`

4. Create `models/rss-feeds/views/rss-feeds.jsonld` — ViewSpecs:
   - `rss:view-article-table` — Articles Table view with columns: title, author, published date, feed source, isRead, isStarred
   - SPARQL query selecting from `rss:Article` type with OPTIONAL clauses
   - Follow the `basic-pkm` views pattern exactly: `sempkm:ViewSpec` type, `sempkm:targetClass`, `sempkm:rendererType`, `sempkm:sparqlQuery`

5. Create `models/rss-feeds/seed/rss-feeds.jsonld` — empty seed (just the JSON-LD context and empty `@graph`). Even though manifest says `seed: null`, having the file prevents errors if the loader checks for it. Actually — since manifest says `seed: null`, skip creating this file. The model loader handles null seed gracefully.

6. Validate the model:
   ```bash
   python -c "
   from backend.app.models.manifest import parse_manifest
   from pathlib import Path
   import json
   m = parse_manifest(Path('models/rss-feeds'))
   print(f'Model: {m.modelId} v{m.version}')
   print(f'Namespace: {m.namespace}')
   print(f'Icons: {len(m.icons)}')
   # Validate JSON files parse
   for name in ['ontology/rss-feeds.jsonld', 'shapes/rss-feeds.jsonld', 'views/rss-feeds.jsonld']:
       with open(f'models/rss-feeds/{name}') as f:
           data = json.load(f)
       print(f'{name}: {len(data.get(\"@graph\", []))} entries')
   "
   ```

## Must-Haves

- [ ] `models/rss-feeds/manifest.yaml` validates against `ManifestSchema`
- [ ] OWL ontology defines `rss:Article` and `rss:FeedSubscription` as `owl:Class`
- [ ] `rss:Article` has ≥8 properties (title, link, author, created, description, feedSource, isRead, isStarred, articleId)
- [ ] `rss:FeedSubscription` has ≥5 properties (title, feedUrl, siteUrl, lastPolled, errorCount)
- [ ] SHACL shapes define `sh:NodeShape` for both types with property groups
- [ ] At least one ViewSpec for articles table
- [ ] All JSON-LD files parse as valid JSON

## Verification

- `python -c "from backend.app.models.manifest import parse_manifest; from pathlib import Path; parse_manifest(Path('models/rss-feeds'))"` — no errors
- `python -c "import json; [json.load(open(f'models/rss-feeds/{p}')) for p in ['ontology/rss-feeds.jsonld', 'shapes/rss-feeds.jsonld', 'views/rss-feeds.jsonld']]"` — all files are valid JSON
- Inspect `@graph` arrays to confirm class and property definitions are present

## Inputs

- `models/basic-pkm/` — reference implementation for all file formats (manifest.yaml, ontology, shapes, views)
- `models/basic-pkm/manifest.yaml` — icon and entrypoint patterns
- `models/basic-pkm/ontology/basic-pkm.jsonld` — OWL class and property patterns
- `models/basic-pkm/shapes/basic-pkm.jsonld` — SHACL shape and PropertyGroup patterns
- `models/basic-pkm/views/basic-pkm.jsonld` — ViewSpec SPARQL query patterns
- `backend/app/models/manifest.py` — `ManifestSchema` validation rules

## Observability Impact

- **Model installation signals:** When `rss-feeds` model is installed via Admin > Models, the model loader logs `Installed model rss-feeds v1.0.0` and loads ontology/shapes/views into the triplestore. Type icons (`newspaper` for Article, `rss` for FeedSubscription) appear in the object browser sidebar.
- **Inspection surfaces:** Admin > Models lists `rss-feeds` with version and namespace. SPARQL console can query `SELECT ?c WHERE { ?c a owl:Class . FILTER(STRSTARTS(STR(?c), "urn:sempkm:model:rss-feeds:")) }` to verify class definitions loaded. ViewSpecs queryable via `SELECT ?v WHERE { ?v a <urn:sempkm:vocab:ViewSpec> . ?v <urn:sempkm:vocab:targetClass> <urn:sempkm:model:rss-feeds:Article> }`.
- **Failure visibility:** If ontology/shapes/views JSON-LD is malformed, the model installer logs parse errors with file path. `parse_manifest()` raises `ValidationError` with field-level details if manifest.yaml is invalid.
- **Agent verification:** `python -c "from backend.app.models.manifest import parse_manifest; from pathlib import Path; m = parse_manifest(Path('models/rss-feeds')); print(m.modelId, m.version)"` — prints `rss-feeds 1.0.0` if manifest is valid.

## Expected Output

- `models/rss-feeds/manifest.yaml` — model manifest defining rss-feeds model
- `models/rss-feeds/ontology/rss-feeds.jsonld` — OWL ontology with Article and FeedSubscription classes
- `models/rss-feeds/shapes/rss-feeds.jsonld` — SHACL shapes for both types
- `models/rss-feeds/views/rss-feeds.jsonld` — ViewSpec for articles table
