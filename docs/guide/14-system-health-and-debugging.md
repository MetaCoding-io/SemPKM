# Chapter 14: System Health and Debugging

SemPKM provides built-in tools for monitoring system health, inspecting your data at the lowest level, and troubleshooting issues. This chapter covers the Health page, the API health endpoint, the SPARQL Console, the Commands page, and the Event Log -- everything you need to verify that the system is working correctly and to diagnose problems when it is not.

## Health Check

### The Health Page

The Health page gives you an at-a-glance overview of your SemPKM instance's operational status. Access it by clicking **Health** in the left sidebar, or navigate directly to `/health/`.

<!-- Screenshot: Health page showing the Service Status card, Data Stores card, and Email (SMTP) card -->

The page is organized into three cards:

#### Service Status

This card queries the API health endpoint on page load and displays:

- **Overall status** -- "HEALTHY" (green) when all services are operational, or "DEGRADED" (amber) when one or more services are down.
- **Service list** -- Each service shows a colored status dot and its current state:
  - **api** -- Always "up" if you can see the page (since the page is served by the API).
  - **triplestore** -- "up" if the RDF4J triplestore responds to health probes, "down" if it cannot be reached.
- **Version** -- The current SemPKM API version (e.g., `0.1.0`).

#### Data Stores

This card shows static configuration information for the two data backends:

**Auth Database:**

| Field | Description |
|---|---|
| Engine | The database engine: SQLite (default for local) or PostgreSQL (for production) |
| Path | The database file path or connection string |
| Sessions | Session expiry duration (default: 30 days) |

**RDF Triplestore:**

| Field | Description |
|---|---|
| URL | The RDF4J server URL (e.g., `http://triplestore:8080/rdf4j-server`) |
| Repository | The repository ID (default: `sempkm`) |
| Namespace | The base namespace for your data (e.g., `https://example.org/data/`) |

> **Tip:** If the triplestore shows "down" but SemPKM loaded the Health page, it means the API is running but cannot reach the triplestore. Check that the RDF4J container is running with `docker compose ps` and review the triplestore container logs for errors.

#### Email (SMTP)

This card shows the SMTP configuration status:

- **Configured** (green badge) -- SMTP environment variables are set. Shows the host, port, user, and from-email address.
- **Not configured** (amber badge) -- SMTP is not set up. The card displays a hint explaining that magic link tokens will be returned directly in the browser, and lists the environment variables needed to enable email delivery (`SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`).

### The API Health Endpoint

The health check is also available as a public JSON API endpoint for use by Docker healthchecks, load balancers, and monitoring systems:

```
GET /api/health
```

This endpoint requires **no authentication** -- it is intentionally public so that infrastructure tools that cannot provide session cookies can still probe the service.

**Example response (healthy):**

```json
{
  "status": "healthy",
  "services": {
    "api": "up",
    "triplestore": "up"
  },
  "version": "0.1.0"
}
```

**Example response (degraded):**

```json
{
  "status": "degraded",
  "services": {
    "api": "up",
    "triplestore": "down"
  },
  "version": "0.1.0"
}
```

The endpoint returns HTTP 200 in both cases. To use this with a Docker healthcheck, test the `status` field in the JSON response:

```yaml
healthcheck:
  test: ["CMD", "curl", "-sf", "http://localhost:8000/api/health"]
  interval: 30s
  timeout: 5s
  retries: 3
```

> **Note:** The health endpoint checks triplestore connectivity by issuing a lightweight probe to the RDF4J server. If the triplestore is starting up slowly (common on first launch when it initializes the repository), the health check may report "degraded" for the first few seconds until the triplestore is ready.

## Debug Tools

SemPKM ships with several debug tools that are useful for advanced users, developers, and anyone troubleshooting unexpected behavior. These tools are available to any authenticated user (owner or member).

### Commands Page

The Commands page lets you execute SemPKM commands directly, bypassing the normal UI forms. This is useful for testing, bulk operations, or understanding how the command system works.

Access it by navigating to `/commands`.

<!-- Screenshot: Commands page showing the Form tab with command type dropdown and fields, and the Raw JSON tab -->

The page has two modes, switchable with tabs at the top:

#### Form Mode

The **Form** tab provides a guided interface:

1. Select a **Command Type** from the dropdown:
   - `object.create` -- Create a new object with type, slug, and properties
   - `object.patch` -- Update properties on an existing object
   - `body.set` -- Set or replace the Markdown body of an object
   - `edge.create` -- Create a relationship edge between two objects
   - `edge.patch` -- Update properties on an existing edge

2. The form fields update dynamically based on the selected command type.

3. Fill in the required fields and click **Execute**.

The result (or error) appears below the form.

#### Raw JSON Mode

The **Raw JSON** tab provides a text area where you can paste a complete command JSON payload and execute it directly. This is useful when you have a command copied from the API documentation or from a script.

**Example raw command:**

```json
{
  "command": "object.create",
  "params": {
    "type": "Person",
    "slug": "alice",
    "properties": {
      "rdfs:label": "Alice Chen"
    }
  }
}
```

Click **Execute** to submit the JSON to the command API.

> **Tip:** The Commands page is a convenient way to test integrations or reproduce issues. If an object is not behaving as expected, try recreating the operation on the Commands page to see the raw API response, which often includes more detail than the UI shows.

### SPARQL Console

The SPARQL Console gives you direct read access to the RDF triplestore, letting you run arbitrary SPARQL queries against all your data. This is the most powerful exploration tool in SemPKM.

Access it by navigating to `/sparql`.

<!-- Screenshot: SPARQL Console showing the query text area with a sample SELECT query, the Run Query and Add Prefixes buttons, and a results table below -->

#### Running a Query

1. The text area starts with a default query:

```sparql
SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 20
```

2. Edit the query to match what you want to explore.

3. Click **Run Query** to execute.

4. Results appear in a table below the query box, with one column per SPARQL variable.

#### Adding Prefixes

Click **Add Prefixes** to inject common namespace prefixes (from your installed Mental Models) into the query text area. This saves you from having to remember or look up prefix declarations. For example, after clicking Add Prefixes, your query might gain:

```sparql
PREFIX bpkm: <https://example.org/models/basic-pkm/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX sempkm: <urn:sempkm:>
```

#### Common Exploration Queries

**List all object types and their counts:**

```sparql
SELECT ?type (COUNT(?s) AS ?count)
WHERE { ?s a ?type }
GROUP BY ?type
ORDER BY DESC(?count)
```

**Find all properties of a specific object:**

```sparql
SELECT ?p ?o
WHERE { <https://example.org/data/person/alice> ?p ?o }
```

**List all relationships (edges) for a Person:**

```sparql
PREFIX bpkm: <https://example.org/models/basic-pkm/>
SELECT ?predicate ?target ?targetLabel
WHERE {
  <https://example.org/data/person/alice> ?predicate ?target .
  OPTIONAL { ?target rdfs:label ?targetLabel }
  FILTER(isIRI(?target))
}
```

**Browse the Event Log via SPARQL:**

```sparql
PREFIX sempkm: <urn:sempkm:>
SELECT ?event ?timestamp ?opType
WHERE {
  GRAPH ?event {
    ?event a sempkm:Event ;
           sempkm:timestamp ?timestamp ;
           sempkm:operationType ?opType .
  }
  FILTER(STRSTARTS(STR(?event), "urn:sempkm:event:"))
}
ORDER BY DESC(?timestamp)
LIMIT 20
```

**Inspect webhook configurations:**

```sparql
SELECT ?webhook ?targetUrl ?event ?enabled
WHERE {
  GRAPH <urn:sempkm:webhooks> {
    ?webhook a <urn:sempkm:Webhook> ;
             <urn:sempkm:targetUrl> ?targetUrl ;
             <urn:sempkm:enabled> ?enabled .
    ?webhook <urn:sempkm:event> ?event .
  }
}
```

> **Warning:** The SPARQL Console executes read-only SELECT queries against the triplestore. Do not attempt UPDATE or DELETE operations through this console -- data modifications should go through the command API to ensure proper event logging, validation, and webhook dispatch.

### API Documentation

SemPKM is built on FastAPI, which automatically generates interactive API documentation. Access it at:

- **Swagger UI:** `/docs` -- An interactive interface where you can explore all API endpoints, see request/response schemas, and execute test requests directly from the browser.
- **ReDoc:** `/redoc` -- A read-only alternative view of the same API documentation, formatted for easier reading.

<!-- Screenshot: Swagger UI showing the list of API endpoint groups: auth, commands, health, models, sparql, validation -->

The API docs are especially useful for:

- Understanding the exact request format for each endpoint
- Testing API calls without writing code
- Discovering endpoints you might not have known about
- Verifying response schemas when building integrations

### Event Log

The Event Log is a built-in panel in the workspace that shows a chronological record of every data change in your SemPKM instance. While it is covered in depth in [Understanding the Event Log](15-event-log.md), it is also a critical debugging tool.

Access the Event Log from the workspace by opening the **Event Log** panel.

<!-- Screenshot: Event Log panel showing a timeline of events with operation badges, affected objects, users, and timestamps -->

#### What the Event Log Shows

Each event row displays:

- **Operation badge** -- Color-coded label showing the operation type (`object.create`, `object.patch`, `body.set`, `edge.create`, `edge.patch`)
- **Affected object** -- A clickable link to the object that was changed, with a count if multiple objects were affected
- **User** -- Who performed the operation (clickable to filter by user)
- **Timestamp** -- When the event occurred

#### Filtering Events

The Event Log provides three filters at the top:

- **Operation type** -- Dropdown to show only events of a specific type (e.g., only `object.patch` events)
- **Date range** -- Two date pickers (From and To) to narrow the timeline
- **Object filter** -- Click an object link in the event list to show only events affecting that object
- **User filter** -- Click a username to show only events by that user

Active filters appear as **chips** at the top of the panel. Click the "x" on any chip to remove that filter.

#### Diff and Undo

For patch and set operations, each event row includes:

- **Diff** button -- Click to expand a diff panel showing what changed. For property changes, it shows the before and after values. For body changes, it shows a unified diff with added lines highlighted in green and removed lines in red.
- **Undo** button -- Click to generate and execute a compensation command that reverses the change. This works for `object.patch`, `body.set`, `edge.create`, and `edge.patch` operations. The undo itself creates a new event in the log (it does not delete the original event).

> **Note:** The Event Log uses cursor-based pagination, loading 50 events at a time. Click **Load more** at the bottom to fetch the next page.

### Global Lint Dashboard

The Lint Dashboard gives you a bird's-eye view of every SHACL validation issue across your entire knowledge base. While the per-object Lint panel (see [Chapter 16: The Data Model](16-data-model.md)) shows violations for a single object, the Global Lint Dashboard aggregates all violations, warnings, and informational messages into one filterable table.

#### Accessing the Lint Dashboard

Open the bottom panel with **Alt+J**, then click the **Lint** tab. The dashboard loads the latest validation report automatically.

<!-- Screenshot: Lint Dashboard showing the filter toolbar, summary counts, and a table of violations -->

#### What the Dashboard Shows

The dashboard displays a table of all validation results from the most recent SHACL validation run. Each row includes:

- **Severity** -- Color-coded badge: red for **Violation**, amber for **Warning**, blue for **Info**
- **Object** -- The offending object, shown as a clickable link that opens it in the workspace
- **Object type** -- The RDF type of the object (e.g., Note, Person, Project)
- **Property** -- The specific property that triggered the validation result (e.g., `dcterms:title`, `foaf:name`)
- **Message** -- A human-readable description of what went wrong (e.g., "Less than 1 values" for a required property that is missing)

#### Filtering Results

The toolbar at the top of the dashboard provides four filters that work in combination:

- **Severity** dropdown -- Show only Violations, Warnings, or Info messages
- **Object type** dropdown -- Filter by type (e.g., show only Note violations). The dropdown is populated from your installed Mental Model shapes.
- **Search** text field -- Free-text search across violation messages. Useful for finding all instances of a specific constraint (e.g., search "minCount" to find all missing required properties).
- **Sort** -- Order results by severity, object, or message

Filters apply immediately via htmx -- no page reload needed.

#### Understanding Violations

SHACL violations come from the constraints defined in your Mental Model shapes. Each shape describes the expected structure for an object type. Common violations include:

| Violation | Meaning | How to Fix |
|-----------|---------|------------|
| "Less than 1 values" | A required property is missing | Open the object and fill in the property |
| "More than 1 values" | A property that allows only one value has multiple | Remove the extra values |
| "Value does not have datatype" | A property value has the wrong type (e.g., text instead of date) | Edit the property and enter a value of the correct type |
| "Value does not have class" | A relationship points to an object of the wrong type | Update the relationship to point to an object of the expected type |

#### Using the Dashboard for Data Cleanup

The Lint Dashboard is most useful as a data cleanup tool. A typical workflow:

1. Open the Lint Dashboard and filter to **Violations** only
2. Sort by **Object type** to work through one type at a time
3. Click an object link to open it in the workspace
4. Fix the issue in the edit form
5. Save -- the object's lint status updates on the next validation run
6. Return to the Lint Dashboard to continue with the next violation

> **For Advanced Users:** The SHACL shapes that drive lint validation are defined in your Mental Model's shapes file. You can add custom SHACL constraints to produce custom lint rules. For example, adding a `sh:pattern` constraint to a property shape will flag objects whose property values do not match the regex pattern. Custom shapes are installed alongside the model -- see [Chapter 16: The Data Model](16-data-model.md) for details on how shapes work.

## Troubleshooting Common Issues

### Triplestore Shows "Down"

1. Check that the RDF4J container is running: `docker compose ps`
2. Check triplestore logs: `docker compose logs triplestore`
3. Verify the `TRIPLESTORE_URL` environment variable points to the correct host and port.
4. On first launch, the triplestore may take 10-30 seconds to initialize the repository. Wait and refresh the Health page.

### Session Expired Unexpectedly

Sessions expire after 30 days of inactivity (configurable via `SESSION_DURATION_DAYS`). If you are actively using SemPKM and still getting logged out:

1. Check the Health page to confirm the Auth Database is accessible.
2. Verify that your browser is not blocking or clearing cookies (especially `sempkm_session`).
3. Check if another admin has revoked your sessions.

### Webhooks Not Firing

1. Verify the webhook is **Enabled** on the Admin > Webhooks page.
2. Confirm the target URL is reachable from the SemPKM container (remember, `localhost` inside Docker does not reach the host machine).
3. Check the server logs for webhook dispatch warnings.
4. Verify you have selected the correct event types for the changes you are making.

### SPARQL Queries Return Empty Results

1. Verify that objects exist by checking the navigation tree in the workspace.
2. Ensure your query uses correct prefix declarations (use the **Add Prefixes** button).
3. Check for typos in IRIs -- they are case-sensitive.
4. If querying event graphs, ensure the graph filter matches: `STRSTARTS(STR(?event), "urn:sempkm:event:")`.

---

**Previous:** [Chapter 13: Settings](13-settings.md) | **Next:** [Chapter 15: Understanding the Event Log](15-event-log.md)
