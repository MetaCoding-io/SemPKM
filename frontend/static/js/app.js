/**
 * SemPKM Dev Console - Vanilla JS
 *
 * Provides: SPARQL prefix injection, query execution with table rendering,
 * command form handling with dynamic fields, and error display.
 */

/* ── SPARQL Prefixes ── */

const COMMON_PREFIXES = [
  "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>",
  "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>",
  "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>",
  "PREFIX sempkm: <urn:sempkm:>",
  "PREFIX schema: <https://schema.org/>",
  "PREFIX dcterms: <http://purl.org/dc/terms/>",
  "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>",
];

/**
 * Inject common SPARQL prefixes into a textarea, skipping already-declared ones.
 */
function injectPrefixes(textareaId) {
  const textarea = document.getElementById(textareaId);
  if (!textarea) return;

  const current = textarea.value;
  const upper = current.toUpperCase();

  const missing = COMMON_PREFIXES.filter((prefix) => {
    const name = prefix.split(":")[0].replace("PREFIX ", "").trim();
    return !upper.includes("PREFIX " + name.toUpperCase() + ":");
  });

  if (missing.length > 0) {
    textarea.value = missing.join("\n") + "\n" + current;
  }
}

/* ── SPARQL Query Execution ── */

/**
 * Execute the SPARQL query from the textarea, render results as a table.
 */
async function runSparqlQuery() {
  const textarea = document.getElementById("sparql-query");
  const resultsDiv = document.getElementById("sparql-results");
  const errorDiv = document.getElementById("sparql-error");

  if (!textarea || !resultsDiv) return;

  const query = textarea.value.trim();
  if (!query) {
    showError(errorDiv, "Please enter a SPARQL query.");
    return;
  }

  // Clear previous results/errors
  resultsDiv.innerHTML = '<p class="loading">Running query...</p>';
  if (errorDiv) errorDiv.innerHTML = "";

  try {
    const resp = await fetch("/api/sparql", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query }),
    });

    const data = await resp.json();

    if (!resp.ok) {
      resultsDiv.innerHTML = "";
      showError(errorDiv, data.error || "Query failed with status " + resp.status);
      return;
    }

    renderSparqlResults(resultsDiv, data);
  } catch (err) {
    resultsDiv.innerHTML = "";
    showError(errorDiv, "Network error: " + err.message);
  }
}

/**
 * Render SPARQL JSON results as an HTML table.
 * Expected format: { head: { vars: [...] }, results: { bindings: [...] } }
 */
function renderSparqlResults(container, data) {
  const vars = data.head && data.head.vars ? data.head.vars : [];
  const bindings = data.results && data.results.bindings ? data.results.bindings : [];

  if (vars.length === 0) {
    container.innerHTML = '<p class="result-count">No variables in result.</p>';
    return;
  }

  let html = '<div class="results-container">';
  html += '<table class="sparql-results"><thead><tr>';

  for (const v of vars) {
    html += "<th>?" + escapeHtml(v) + "</th>";
  }
  html += "</tr></thead><tbody>";

  if (bindings.length === 0) {
    html += '<tr><td colspan="' + vars.length + '" style="text-align:center;color:#999;">No results</td></tr>';
  } else {
    for (const row of bindings) {
      html += "<tr>";
      for (const v of vars) {
        const cell = row[v];
        const value = cell ? formatRdfValue(cell) : "";
        html += "<td>" + value + "</td>";
      }
      html += "</tr>";
    }
  }

  html += "</tbody></table></div>";
  html += '<p class="result-count">' + bindings.length + " result(s)</p>";

  container.innerHTML = html;
}

/**
 * Format an RDF value from SPARQL JSON results for display.
 */
function formatRdfValue(cell) {
  const value = escapeHtml(cell.value);
  if (cell.type === "uri") {
    // Shorten common prefixes for readability
    const shortened = shortenIri(cell.value);
    return '<span title="' + value + '">' + escapeHtml(shortened) + "</span>";
  }
  if (cell.type === "literal" && cell.datatype) {
    return value + ' <span style="color:#999;font-size:0.8em">(' + escapeHtml(shortenIri(cell.datatype)) + ")</span>";
  }
  return value;
}

/**
 * Shorten well-known IRIs to prefixed form for display.
 */
function shortenIri(iri) {
  const prefixes = {
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf:",
    "http://www.w3.org/2000/01/rdf-schema#": "rdfs:",
    "http://www.w3.org/2001/XMLSchema#": "xsd:",
    "urn:sempkm:": "sempkm:",
    "https://schema.org/": "schema:",
    "http://purl.org/dc/terms/": "dcterms:",
    "http://www.w3.org/2004/02/skos/core#": "skos:",
  };

  for (const [ns, prefix] of Object.entries(prefixes)) {
    if (iri.startsWith(ns)) {
      return prefix + iri.substring(ns.length);
    }
  }
  return iri;
}

/* ── Command Execution ── */

/**
 * Command type -> field definitions for the dynamic form.
 */
const COMMAND_FIELDS = {
  "object.create": [
    { name: "type", label: "Type", type: "text", placeholder: "e.g. Person, Note, Project", required: true },
    { name: "slug", label: "Slug (optional)", type: "text", placeholder: "e.g. alice (leave blank for UUID)" },
    { name: "properties", label: "Properties (JSON)", type: "json", placeholder: '{"rdfs:label": "Alice", "schema:name": "Alice Smith"}' },
  ],
  "object.patch": [
    { name: "iri", label: "Object IRI", type: "text", placeholder: "https://example.org/data/Person/alice", required: true },
    { name: "properties", label: "Properties (JSON)", type: "json", placeholder: '{"schema:name": "Alice Jones"}' },
  ],
  "body.set": [
    { name: "iri", label: "Object IRI", type: "text", placeholder: "https://example.org/data/Note/my-note", required: true },
    { name: "body", label: "Body (Markdown)", type: "markdown", placeholder: "# My Note\n\nNote content here..." },
  ],
  "edge.create": [
    { name: "source", label: "Source IRI", type: "text", placeholder: "https://example.org/data/Person/alice", required: true },
    { name: "target", label: "Target IRI", type: "text", placeholder: "https://example.org/data/Person/bob", required: true },
    { name: "predicate", label: "Predicate", type: "text", placeholder: "e.g. schema:knows, sempkm:relatedTo", required: true },
    { name: "properties", label: "Properties (JSON)", type: "json", placeholder: '{"rdfs:label": "knows"}' },
  ],
  "edge.patch": [
    { name: "iri", label: "Edge IRI", type: "text", placeholder: "https://example.org/data/Edge/...", required: true },
    { name: "properties", label: "Properties (JSON)", type: "json", placeholder: '{"rdfs:label": "updated label"}' },
  ],
};

/**
 * Switch the command form fields based on the selected command type.
 */
function switchCommandForm(commandType) {
  const container = document.getElementById("command-fields");
  if (!container) return;

  const fields = COMMAND_FIELDS[commandType];
  if (!fields) {
    container.innerHTML = "<p>Unknown command type.</p>";
    return;
  }

  let html = "";
  for (const field of fields) {
    html += '<div class="form-group">';
    html += '<label for="cmd-' + field.name + '">' + escapeHtml(field.label) + "</label>";

    if (field.type === "json") {
      html += '<textarea id="cmd-' + field.name + '" class="json-box" placeholder="' + escapeHtml(field.placeholder || "") + '"></textarea>';
    } else if (field.type === "markdown") {
      html += '<textarea id="cmd-' + field.name + '" class="json-box" placeholder="' + escapeHtml(field.placeholder || "") + '"></textarea>';
    } else {
      html += '<input type="text" id="cmd-' + field.name + '" placeholder="' + escapeHtml(field.placeholder || "") + '"';
      if (field.required) html += " required";
      html += ">";
    }

    html += "</div>";
  }

  container.innerHTML = html;
}

/**
 * Build a command JSON payload from the current form state.
 */
function buildCommandPayload() {
  const commandType = document.getElementById("command-type").value;
  const fields = COMMAND_FIELDS[commandType];
  if (!fields) return null;

  const params = {};

  for (const field of fields) {
    const el = document.getElementById("cmd-" + field.name);
    if (!el) continue;

    let value = el.value.trim();
    if (!value && field.required) {
      throw new Error(field.label + " is required.");
    }
    if (!value) continue;

    if (field.type === "json") {
      try {
        params[field.name] = JSON.parse(value);
      } catch {
        throw new Error(field.label + " must be valid JSON.");
      }
    } else {
      params[field.name] = value;
    }
  }

  return { command: commandType, params: params };
}

/**
 * Execute a command via the form, posting to /api/commands.
 */
async function executeCommand() {
  const resultDiv = document.getElementById("command-result");
  const errorDiv = document.getElementById("command-error");

  if (resultDiv) resultDiv.innerHTML = "";
  if (errorDiv) errorDiv.innerHTML = "";

  let payload;
  try {
    payload = buildCommandPayload();
  } catch (err) {
    showError(errorDiv, err.message);
    return;
  }

  if (!payload) {
    showError(errorDiv, "Could not build command payload.");
    return;
  }

  if (resultDiv) resultDiv.innerHTML = '<p class="loading">Executing command...</p>';

  try {
    const resp = await fetch("/api/commands", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await resp.json();

    if (!resp.ok) {
      if (resultDiv) resultDiv.innerHTML = "";
      showError(errorDiv, data.error || "Command failed with status " + resp.status);
      return;
    }

    if (resultDiv) {
      resultDiv.innerHTML =
        '<div class="success-box">Command executed successfully.</div>' +
        '<pre class="json-output">' +
        escapeHtml(JSON.stringify(data, null, 2)) +
        "</pre>";
    }
    document.dispatchEvent(new CustomEvent('sempkm:command-executed'));
  } catch (err) {
    if (resultDiv) resultDiv.innerHTML = "";
    showError(errorDiv, "Network error: " + err.message);
  }
}

/**
 * Execute a raw JSON command from the textarea.
 */
async function executeRawCommand() {
  const textarea = document.getElementById("raw-json");
  const resultDiv = document.getElementById("command-result");
  const errorDiv = document.getElementById("command-error");

  if (resultDiv) resultDiv.innerHTML = "";
  if (errorDiv) errorDiv.innerHTML = "";

  if (!textarea || !textarea.value.trim()) {
    showError(errorDiv, "Please enter a JSON command.");
    return;
  }

  let payload;
  try {
    payload = JSON.parse(textarea.value.trim());
  } catch {
    showError(errorDiv, "Invalid JSON. Please check your syntax.");
    return;
  }

  if (resultDiv) resultDiv.innerHTML = '<p class="loading">Executing command...</p>';

  try {
    const resp = await fetch("/api/commands", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await resp.json();

    if (!resp.ok) {
      if (resultDiv) resultDiv.innerHTML = "";
      showError(errorDiv, data.error || "Command failed with status " + resp.status);
      return;
    }

    if (resultDiv) {
      resultDiv.innerHTML =
        '<div class="success-box">Command executed successfully.</div>' +
        '<pre class="json-output">' +
        escapeHtml(JSON.stringify(data, null, 2)) +
        "</pre>";
    }
    document.dispatchEvent(new CustomEvent('sempkm:command-executed'));
  } catch (err) {
    if (resultDiv) resultDiv.innerHTML = "";
    showError(errorDiv, "Network error: " + err.message);
  }
}

/* ── Tab Switching ── */

function switchTab(tabName) {
  // Deactivate all tabs and content
  document.querySelectorAll(".tab-bar button").forEach((btn) => {
    btn.classList.remove("active");
  });
  document.querySelectorAll(".tab-content").forEach((content) => {
    content.classList.remove("active");
  });

  // Activate selected
  const btn = document.querySelector('.tab-bar button[data-tab="' + tabName + '"]');
  if (btn) btn.classList.add("active");

  const content = document.getElementById("tab-" + tabName);
  if (content) content.classList.add("active");
}

/* ── Health Display ── */

/**
 * Render health data fetched via htmx into the health container.
 * Called by htmx afterSettle event on the health page.
 */
function renderHealthData(data) {
  const container = document.getElementById("health-data");
  if (!container) return;

  try {
    if (typeof data === "string") {
      data = JSON.parse(data);
    }

    let html = '<ul class="service-list">';

    if (data.services) {
      for (const [name, status] of Object.entries(data.services)) {
        const isUp = status === "up";
        html +=
          "<li>" +
          '<span class="status-dot ' + (isUp ? "up" : "down") + '"></span>' +
          '<span class="service-name">' + escapeHtml(name) + "</span>" +
          '<span class="' + (isUp ? "status-healthy" : "status-down") + '">' +
          escapeHtml(status) +
          "</span>" +
          "</li>";
      }
    }

    html += "</ul>";

    if (data.version) {
      html += '<p class="version-info">API Version: ' + escapeHtml(data.version) + "</p>";
    }

    const statusClass = data.status === "healthy" ? "status-healthy" : "status-degraded";
    html = '<p>Overall: <span class="' + statusClass + '">' + escapeHtml(data.status || "unknown") + "</span></p>" + html;

    container.innerHTML = html;
  } catch {
    container.innerHTML = '<p class="error-box">Failed to parse health data.</p>';
  }
}

/* ── Utilities ── */

function escapeHtml(str) {
  if (typeof str !== "string") return String(str);
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function showError(container, message) {
  if (container) {
    container.innerHTML = '<div class="error-box">' + escapeHtml(message) + "</div>";
  }
}
