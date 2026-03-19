---
estimated_steps: 5
estimated_files: 2
---

# T02: Build person matcher with unit tests

**Slice:** S02 — Pull Sync — Linear Issues to bpkm:Task
**Milestone:** M016

## Description

Create the person matching module that resolves Linear assignees to SemPKM Person IRIs. When the sync engine encounters an issue with an assignee, it needs to either find an existing Person (by email) or create a new one. This module encapsulates that logic with an in-memory cache to avoid redundant SPARQL queries within a single sync run.

## Steps

1. **Create `apps/linear-sync/services/person_matcher.py`** with a `PersonMatcher` class:

   ```python
   class PersonMatcher:
       """Resolves Linear users to SemPKM Person IRIs.
       
       Queries SPARQL for existing Person objects by email (foaf:mbox or crm:email).
       Creates new Person objects via command API when no match found.
       Caches results per sync run to avoid repeated queries.
       """
       
       def __init__(self, graph_client, command_client):
           self._graph = graph_client
           self._commands = command_client
           self._cache: dict[str, str] = {}  # email → Person IRI
       
       async def match_or_create(self, email: str | None, display_name: str | None) -> str | None:
           """Find or create a Person for the given email.
           
           Returns the Person IRI, or None if email is None/empty.
           """
   ```

2. **Implement the SPARQL lookup** in `match_or_create()`:
   - Return `None` immediately if `email` is None or empty string (use `if not email: return None`)
   - Check `self._cache` first — return cached IRI if present
   - Execute SPARQL query via `self._graph.query()`:
     ```sparql
     SELECT ?person WHERE {
       { ?person <http://xmlns.com/foaf/0.1/mbox> ?email }
       UNION
       { ?person <urn:sempkm:model:crm:email> ?email }
       FILTER(LCASE(STR(?email)) = LCASE("..."))
     } LIMIT 1
     ```
     Use `LCASE()` for case-insensitive matching. Use full IRIs in the query (not prefixed) to avoid prefix declaration issues with the `/api/sparql` endpoint.
   - Parse SPARQL JSON results: `results["results"]["bindings"][0]["person"]["value"]` if bindings exist

3. **Implement Person creation** on SPARQL miss:
   - Use `self._commands.execute("object.create", {...})` — this goes through the SDK's normal `CommandClient` which is fine because `object.create` has no IRI fields to check (per `_IRI_PARAMS`)
   - Params: `{"type": "urn:sempkm:model:basic-pkm:Person", "slug": slugified_name, "properties": {"dcterms:title": display_name, "foaf:mbox": email}}`
   - Slug: slugify the display name (lowercase, replace spaces with hyphens, strip non-alphanumeric) for readable IRIs. If no display name, use the email local part.
   - Extract the created IRI from the response: `response.get("iri")` or fall back to constructing it from the known `{base_namespace}/Person/{slug}` pattern — but prefer the response IRI
   - **Fallback:** If `self._commands` doesn't have an `execute` method available (test environment), the sync engine can handle Person creation at a higher level. Document this in the class docstring.

4. **Cache the result** — store `self._cache[email.lower()] = person_iri` after both lookup hit and creation.

5. **Create `backend/tests/test_person_matcher.py`** with mocked clients:
   
   Use the importlib pattern to load the module. Create mock classes:
   ```python
   class MockGraphClient:
       def __init__(self, results=None):
           self._results = results or {"results": {"bindings": []}}
           self.queries = []
       
       async def query(self, sparql: str) -> dict:
           self.queries.append(sparql)
           return self._results
   
   class MockCommandClient:
       def __init__(self):
           self.commands = []
       
       async def execute(self, command_type: str, params: dict) -> dict:
           self.commands.append({"command": command_type, "params": params})
           slug = params.get("slug", "unknown")
           type_name = params["type"].split(":")[-1]
           return {"iri": f"https://example.org/data/{type_name}/{slug}"}
   ```
   
   Tests (~10):
   - `test_none_email_returns_none` — None email returns None without querying
   - `test_empty_email_returns_none` — Empty string returns None
   - `test_existing_person_found_via_foaf_mbox` — SPARQL returns a binding → returns that IRI, no create
   - `test_existing_person_found_via_crm_email` — Same but with crm:email result
   - `test_new_person_created_on_miss` — SPARQL returns empty → create command issued → IRI returned
   - `test_created_person_has_correct_properties` — Verify command params include dcterms:title and foaf:mbox
   - `test_cache_prevents_duplicate_queries` — Second call with same email hits cache, no SPARQL query
   - `test_cache_is_case_insensitive` — "Alice@example.com" and "alice@example.com" share cache entry
   - `test_slug_from_display_name` — Display name "Alice Smith" → slug "alice-smith"
   - `test_slug_from_email_when_no_name` — No display name → slug from email local part

## Must-Haves

- [ ] `PersonMatcher` class with `match_or_create(email, display_name) -> str | None`
- [ ] SPARQL queries both `foaf:mbox` and `urn:sempkm:model:crm:email` with case-insensitive match
- [ ] Creates `bpkm:Person` via `object.create` command on SPARQL miss
- [ ] In-memory cache prevents duplicate SPARQL queries per sync run
- [ ] Returns None for None/empty email (no exception, no query)
- [ ] ~10 unit tests with mocked GraphClient and CommandClient

## Verification

- `cd backend && python -m pytest tests/test_person_matcher.py -v` — all tests pass
- `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/person_matcher.py').read())"` — syntax valid

## Inputs

- `backend/sdk/sempkm_app_sdk/clients/graph.py` — `GraphClient.query()` returns SPARQL JSON results format: `{"results": {"bindings": [{"person": {"type": "uri", "value": "..."}}]}}`
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — `CommandClient.execute("object.create", params)` returns response dict with `"iri"` key for the created object
- `_IRI_PARAMS` in commands.py: `"object.create": []` — no IRI fields checked, so Person creation works through the normal SDK path

## Expected Output

- `apps/linear-sync/services/person_matcher.py` — ~80 lines, `PersonMatcher` class with cache
- `backend/tests/test_person_matcher.py` — ~10 tests with mocked clients
