# Chapter 40: AI Features

SemPKM's browser extension can analyze web pages using AI to detect claims, match them against your existing knowledge graph, suggest new relationships, and generate personalized summaries that highlight what's new versus what you already know. These features appear in the **AI Insights** section of the extension sidebar when visiting any web page.

By the end of this chapter you will understand how claim detection works, how detected claims are matched against your knowledge, how relationship suggestions are generated, and how personalized summaries incorporate your existing graph context.

---

## Prerequisites

Before using AI features, make sure you have:

1. **LLM configuration.** Navigate to **Admin > Settings > LLM Configuration** and provide:
   - `api_base_url` — the base URL of your OpenAI-compatible LLM provider (e.g., `https://api.openai.com/v1`)
   - `api_key` — your API key for the provider
   - `default_model` — the model identifier to use (e.g., `gpt-4o`)

   Without LLM configuration, the AI Insights section will display a message: *"AI features require LLM configuration."*

2. **Research Workflow model (recommended).** Graph matching works with any Mental Model, but installing the Research Workflow model enables richer results — particularly claim-to-claim matching with confidence-based contradiction detection and research question gap analysis. Install it via **Admin > Mental Models**. See [Chapter 10: Managing Mental Models](10-managing-mental-models.md).

3. **Browser extension installed and connected.** The AI features are accessed through the extension sidebar. See [Chapter 32: Browser Extension](32-browser-extension.md) for installation and connection instructions.

---

## Claim Detection

Claim detection extracts testable assertions from the text content of the web page you are currently viewing. The LLM analyzes the page and returns structured claims — specific statements that could be verified, challenged, or built upon.

### How it works

1. The extension extracts the visible text content from the current page (up to 8,000 characters)
2. The text is sent to your configured LLM via the `POST /api/ai/detect-claims` endpoint
3. The LLM returns a list of claims, each with a confidence level and type classification
4. Claims appear in the **Claims** section of the AI Insights panel

### Confidence levels

Each claim is assigned a confidence level indicating how well-established the assertion is:

| Level | Description | Badge color |
|-------|-------------|-------------|
| **Established** | Widely accepted, well-supported by evidence | Green |
| **Likely** | Supported by evidence but not universally accepted | Blue |
| **Possible** | Plausible but lacking strong evidence | Amber |
| **Speculative** | Preliminary or hypothetical, needs investigation | Gray |

### Claim types

Each claim is also classified by type:

| Type | Description |
|------|-------------|
| **Factual** | A statement of fact that can be directly verified |
| **Statistical** | A claim involving numbers, percentages, or quantitative data |
| **Analytical** | An interpretation or analysis of underlying data |
| **Predictive** | A forward-looking statement about expected outcomes |
| **Causal** | A claim asserting a cause-and-effect relationship |

### Accessing AI Insights

Open the browser extension sidebar by pressing **Alt+K** (or clicking the extension icon), then scroll to the **AI Insights** section. Claims begin loading automatically when the sidebar opens on a page with extractable text content.

---

## Graph Matching

After claims are detected, each claim is automatically matched against existing objects in your knowledge graph using full-text search. This helps you see how new information on the page relates to what you already know.

### Match indicators

Each match includes an indicator describing the relationship between the detected claim and your existing knowledge:

| Indicator | Meaning | Badge color |
|-----------|---------|-------------|
| **Corroborates** | Your existing object agrees with the detected claim | Green |
| **Contradicts** | Your existing object disagrees with the detected claim, based on confidence comparison | Red |
| **Contested** | Mixed evidence — some supporting, some refuting | Amber |
| **Related** | Same topic area, but no directional agreement or disagreement | Gray |

Contradiction detection is bidirectional: if an established existing claim is matched against a speculative page claim, or vice versa, both cases register as a contradiction.

### Match limits

Each claim returns up to **5 matches**, sorted by full-text search relevance score. This cap keeps the results focused on the most relevant connections.

### Research question gap detection

If you have the Research Workflow model installed, graph matching also detects **open research questions** related to the page's topics that lack linked evidence. These appear as highlighted gap cards, helping you identify where the page content might address questions you've been investigating.

Research gap detection requires at least 2 meaningful keyword overlaps between the page content and an open research question (common stop words are filtered out).

---

## Relationship Suggestions

Relationship suggestions help you connect the current page to objects in your knowledge graph. Unlike graph matching (which compares detected claims), suggestions are generated using URL matching and keyword overlap — no LLM is required for this step.

### How suggestions are generated

1. **URL matching:** If objects in your graph reference the current page's URL (via `schema:url` properties), they appear as suggestions
2. **Keyword matching:** The page title and key terms are matched against existing objects using full-text search
3. Results are deduplicated by IRI and capped at 10 suggestions

### Suggestion types

Each suggestion includes a recommended relationship type:

| Type | Action when accepted |
|------|---------------------|
| **Link** | Creates a `schema:url` edge linking the existing object to the current page URL |
| **Evidence** | Creates a new Evidence object from the page content, then creates an edge connecting it to the existing object |
| **Supports** | Creates a `res:supports` edge between the objects |
| **Contradicts** | Creates a `res:refutes` edge between the objects |

### Accept and Dismiss

- **Accept:** Click the **Accept** button to create the suggested relationship. This immediately creates the edge (and any intermediate objects) in your knowledge graph. The button is replaced with a "✓ Accepted" badge on success.

- **Dismiss:** Click the **Dismiss** button to hide the suggestion for this URL. Dismissed suggestions are persisted in browser storage (`chrome.storage.local`) and filtered out on subsequent visits to the same page. Dismissals are per-URL, not global.

---

## Personalized Summaries

The LLM generates a summary of the current page that incorporates context from your existing knowledge graph. Rather than a generic summary, this personalized version highlights:

- What information on the page is **new** relative to your existing knowledge
- What information **overlaps** with objects you already have
- How the page content **connects** to your existing research or notes

The summary appears in the **Summary** section at the bottom of the AI Insights panel after all other sections have loaded.

---

## Progressive Loading

The AI Insights panel uses a progressive loading pattern — each section renders independently as its API call completes, rather than waiting for all results before showing anything.

The loading sequence is:

1. **Claims** appear first (single LLM call, typically fastest)
2. **Matches** appear next (graph search against detected claims)
3. **Suggestions** appear next (URL + keyword matching, no LLM needed)
4. **Summary** appears last (LLM call with full graph context, typically slowest)

Each section shows a loading indicator until its data arrives. If any individual step fails, the remaining steps still attempt to load — you may see partial results (e.g., claims without matches if the graph search encounters an error).

---

## Troubleshooting

### "AI features require LLM configuration"

This message appears in the AI Insights section when no LLM provider is configured. To resolve:

1. Navigate to **Admin > Settings > LLM Configuration**
2. Enter your LLM provider's `api_base_url`, `api_key`, and `default_model`
3. Save the configuration
4. Reload the page in your browser — the AI Insights section should now show a loading state instead of the configuration message

### No graph matches appearing

If claims are detected but no matches appear:

- **Research Workflow model not installed:** Without this model, claim-type objects won't exist in your graph for matching. Install it via **Admin > Mental Models**.
- **No overlapping content:** Graph matching uses full-text search — if the detected claim keywords don't overlap with any existing object content, no matches will be found. Try adding more objects to your knowledge graph on the claim's topic area.
- **Empty knowledge graph:** Matches require existing objects to compare against. A newly created instance with no objects will return zero matches.

### Slow AI responses

AI feature latency depends on several factors:

- **LLM provider speed:** Cloud providers vary in response time; local models may be slower but more private
- **First call latency:** Some providers take longer on the first request while loading the model into memory
- **Page content length:** Longer pages produce more text for the LLM to analyze, increasing processing time
- **Graph size:** Larger knowledge graphs take longer for full-text search matching

The progressive loading pattern ensures you see early results (claims) while slower operations (summary) are still processing.

### Claims not relevant

Claim extraction quality varies by page content:

- **Best results:** Article-style pages with clear assertions, research papers, blog posts with specific claims
- **Weaker results:** Navigation-heavy pages, image galleries, pages with minimal text content, heavily formatted marketing copy
- **No results:** Pages with very little extractable text, or content that consists entirely of questions or instructions rather than assertions

The LLM assigns confidence levels and types as best it can, but these are AI-generated assessments and should be treated as starting points for your own evaluation.

---

## See Also

- [Chapter 10: Managing Mental Models](10-managing-mental-models.md) — install the Research Workflow model for richer graph matching
- [Chapter 32: Browser Extension](32-browser-extension.md) — extension installation and connection setup
- [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md) — LLM configuration environment variables

---

**Previous:** [Chapter 39: Notion Import](39-notion-import.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
