---
estimated_steps: 7
estimated_files: 6
---

# T03: Write Chapter 40 user guide and update navigation

**Slice:** S03 — E2E tests and user guide
**Milestone:** M028

## Description

Write the user guide chapter documenting AI features (claim detection, graph matching, relationship suggestions, personalized summaries) and update all three navigation files plus the glossary. This is fully independent of T01/T02 — it's a documentation task with no code dependencies.

Follow the Chapter 39 pattern for structure, navigation footer, and heading hierarchy. Per KNOWLEDGE.md rule "User guide has THREE files that must stay in sync", all three navigation files must be updated together.

## Steps

1. **Create `docs/guide/40-ai-features.md`** with these sections:
   - **Title:** `# Chapter 40: AI Features`
   - **Intro paragraph:** Explain that SemPKM's browser extension can analyze web pages using AI, detect claims, match them against existing knowledge, suggest relationships, and provide personalized summaries.
   - **Prerequisites section:** LLM configuration required (Admin > Settings > LLM Configuration — provide api_base_url, api_key, and default_model). Research Workflow model recommended for claim matching (graph matching works without it but returns fewer results). Browser extension installed and connected (see Chapter 32).
   - **Claim Detection section:** Explain what claim detection does (extracts testable assertions from page text). Describe confidence levels (established, likely, possible, speculative). Describe claim types (factual, statistical, analytical, predictive, causal). Mention the AI Insights section in the sidebar appears when visiting a page with Alt+K.
   - **Graph Matching section:** Explain that detected claims are matched against existing objects in the knowledge graph via full-text search. Describe indicators: `corroborates` (your existing claim agrees), `contradicts` (your existing claim disagrees based on confidence comparison), `contested` (mixed supporting and refuting evidence), `related` (same topic, no directional indicator). Mention the 5-match cap per claim. Mention Research Question gap detection (open questions related to page topics that lack evidence).
   - **Relationship Suggestions section:** Explain that suggestions appear based on URL matching and keyword overlap with existing objects. Describe Accept action (creates an edge linking the object to the current page or between objects). Describe Dismiss action (hides the suggestion for this URL; persisted in browser storage). Mention the 4 suggestion types: link (URL edge), evidence (new Evidence object + edge), supports (supports edge), contradicts (refutes edge).
   - **Personalized Summaries section:** Explain that the LLM generates a summary incorporating the user's existing knowledge graph context — noting what's new vs. already known.
   - **Progressive Loading section:** Briefly explain the loading sequence: claims appear first (fastest), then matches, then suggestions, then summary. Each section renders as its API call completes.
   - **Troubleshooting section** with these subsections:
     - "AI features require LLM configuration" message — need to configure LLM provider in Settings
     - No graph matches appearing — Research Workflow model may not be installed; claim keywords may not overlap with existing objects
     - Slow AI responses — LLM latency depends on provider; first call may be slower due to model loading
     - Claims not relevant — claim extraction quality varies by page content; works best on article-style pages with clear assertions
   - **See Also section:** Link to Chapter 10 (Mental Models), Chapter 32 (Browser Extension), Appendix A (Environment Variables)
   - **Navigation footer:** `**Previous:** [Chapter 39: Notion Import](39-notion-import.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)`

2. **Update `docs/guide/README.md`** — Add entry after line 68 (Notion Import):
   ```
   40. [AI Features](40-ai-features.md)
   ```

3. **Update `docs/guide/index.html`** — Add sidebar entry after the Notion Import `<li>` (which is at the line containing `39-notion-import.md`):
   ```html
   <li><a href="#" data-file="40-ai-features.md">40. AI Features</a></li>
   ```

4. **Update `backend/app/templates/guide.html`** — Add button between Notion Import and Appendix A entries:
   ```html
   <button class="docs-chapter-item"
           hx-get="/guide/40-ai-features.md"
           hx-target="#app-content"
           hx-swap="innerHTML"
           hx-push-url="true">
     <i data-lucide="brain"></i>
     <span>40. AI Features</span>
   </button>
   ```
   Insert this after the Chapter 39 button block and before the first Appendix A button block. Use `brain` as the Lucide icon (fits AI theme).

5. **Update `docs/guide/39-notion-import.md` navigation footer** — Change the last line from:
   ```
   **Previous:** [Chapter 38: Hosted Demo](38-hosted-demo.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
   ```
   to:
   ```
   **Previous:** [Chapter 38: Hosted Demo](38-hosted-demo.md) | **Next:** [Chapter 40: AI Features](40-ai-features.md)
   ```

6. **Add glossary entries to `docs/guide/appendix-d-glossary.md`** — Insert these entries in alphabetical order:
   - **AI Insights** — The browser extension feature that analyzes web pages using AI to detect claims, match them against the knowledge graph, suggest relationships, and generate personalized summaries. Accessed via the sidebar's AI Insights section. See [Chapter 40](40-ai-features.md).
   - **Claim Detection** — The process of extracting testable assertions from web page text using an LLM. Each claim has a confidence level (established, likely, possible, speculative) and a type (factual, statistical, analytical, predictive, causal). See [Chapter 40](40-ai-features.md).
   - **Graph Matching** — The process of comparing detected claims against existing objects in the knowledge graph via full-text search. Returns matches with indicators: corroborates, contradicts, contested, or related. See [Chapter 40](40-ai-features.md).

7. **Verify all navigation updates** by running the grep checks from the slice verification section.

## Must-Haves

- [ ] `docs/guide/40-ai-features.md` exists with sections for claim detection, graph matching, suggestions, summaries, troubleshooting
- [ ] `docs/guide/README.md` has entry for Chapter 40
- [ ] `docs/guide/index.html` has sidebar entry for Chapter 40
- [ ] `backend/app/templates/guide.html` has button for Chapter 40
- [ ] `docs/guide/39-notion-import.md` navigation footer points Next to Chapter 40
- [ ] `docs/guide/40-ai-features.md` navigation footer points Previous to Chapter 39, Next to Appendix A
- [ ] `docs/guide/appendix-d-glossary.md` has 3 new entries (AI Insights, Claim Detection, Graph Matching)

## Verification

- `test -f docs/guide/40-ai-features.md && echo "Chapter exists"` — prints "Chapter exists"
- `grep "40-ai-features" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html | wc -l` — returns ≥3
- `tail -3 docs/guide/39-notion-import.md | grep "Chapter 40"` — finds Chapter 40 reference
- `tail -3 docs/guide/40-ai-features.md | grep "Appendix A"` — finds Appendix A reference
- `grep -c "AI Insights\|Claim Detection\|Graph Matching" docs/guide/appendix-d-glossary.md` — returns ≥3
- `grep "Claim Detection\|Graph Matching\|Relationship Suggestions\|Personalized Summar\|Troubleshooting" docs/guide/40-ai-features.md | wc -l` — returns ≥5 (major sections present)

## Inputs

- `docs/guide/39-notion-import.md` — most recent chapter, reference for heading structure and navigation footer pattern
- `docs/guide/README.md` — current TOC (Chapter 39 is last entry before appendices)
- `docs/guide/index.html` — current sidebar HTML (Chapter 39 is last entry)
- `backend/app/templates/guide.html` — current in-app page (Chapter 39 is last entry before appendices)
- `docs/guide/appendix-d-glossary.md` — existing glossary entries (alphabetical)
- S01 Summary — documents all 6 AI endpoints, confidence levels, indicator logic, research gap detection
- S02 Summary — documents sidebar rendering functions, accept/dismiss behavior, progressive loading, graceful degradation
- M028 Roadmap — success criteria describe the user-facing behaviors to document

## Observability Impact

This task is pure documentation — it adds no runtime behavior, API endpoints, or logs. Signals to verify:

- **Navigation sync:** `grep "40-ai-features" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html` confirms all three nav files reference Chapter 40.
- **Chapter structure:** Section headings in `40-ai-features.md` enumerate the documented feature surface; `grep -c` on heading keywords confirms coverage.
- **Glossary consistency:** `grep -c "AI Insights\|Claim Detection\|Graph Matching" docs/guide/appendix-d-glossary.md` confirms term definitions were added.
- **Navigation chain:** `tail -3 docs/guide/39-notion-import.md` and `tail -3 docs/guide/40-ai-features.md` confirm bidirectional Previous/Next links.

No failure state beyond file-missing or link-broken scenarios, both caught by the grep checks above.

## Expected Output

- `docs/guide/40-ai-features.md` — new file (~250-350 lines): Chapter 40 with all sections
- `docs/guide/README.md` — modified: TOC entry added
- `docs/guide/index.html` — modified: sidebar entry added
- `backend/app/templates/guide.html` — modified: button added
- `docs/guide/39-notion-import.md` — modified: navigation footer updated
- `docs/guide/appendix-d-glossary.md` — modified: 3 entries added
