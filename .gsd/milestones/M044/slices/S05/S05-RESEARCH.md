# S05 Research: Template Hygiene & Deduplication

## Summary

Three distinct problems, all well-understood with known patterns. No unfamiliar technology — this is straightforward Jinja2 refactoring and Python view restructuring.

1. **Template computation → Python views**: 10 `.append()` hacks across 8 templates, 7 `namespace()` hacks across 5 templates. Each is a small, isolated change to move list-building/grouping/counting from Jinja2 into the Python view endpoint that serves the template.

2. **Notion/Obsidian importer template deduplication**: 10 shared partials across the two importers (1,254 + 999 = 2,253 lines). ~6 are near-identical (differ only in string labels, URL prefixes, and include paths). ~4 have structural differences (scan_results, preview, property_mapping, type_mapping) where Notion has database/column concepts and Obsidian has note/tag concepts.

3. **Guide page loop-ification**: 55 copy-pasted `<button>` blocks in `guide.html` (578 lines). Replace with a Python-side `GUIDE_CHAPTERS` registry and a Jinja2 `{% for %}` loop (~30 lines of template + ~80 lines of data definition).

## Recommendation

**Split into three tasks:**

- **T01: Move template computation to Python views** — 8 files with `.append()` hacks, 5 with `namespace()` (some overlap). Each is a surgical edit: add 1-5 lines to the Python view function, simplify the template. Low risk, high testability. Verification: `rg -c '\.append\(' backend/app/templates/ -g '*.html'` returns 0; `rg -c 'namespace\(' backend/app/templates/ -g '*.html'` returns only `base_namespace`/`info.namespace` hits.

- **T02: Deduplicate Notion/Obsidian importer templates** — Create shared base templates in `backend/app/templates/importer/partials/`. Each importer passes context variables (`importer_name`, `url_prefix`, `steps`) from its Python view. Near-identical templates (step_bar, upload_form, scan_trigger, import_progress) become shared. Structurally-different templates (scan_results, preview) stay importer-specific but inherit a shared outer skeleton.

- **T03: Guide page data-driven chapter list** — Define `GUIDE_CHAPTERS` list in `backend/app/shell/router.py`, pass to template context, replace 55 hardcoded buttons with a loop. The three-file sync problem (README.md, index.html, guide.html) per KNOWLEDGE.md is reduced — guide.html becomes data-driven, but README.md and index.html remain manual.

## Implementation Landscape

### T01: Template computation → Python views

Each fix site is independent. Here's the full inventory:

| File | Hack | Python view file | Fix |
|------|------|-----------------|-----|
| `browser/saved_queries_explorer.html` | `.append()` to split model/user queries | `views/router.py:saved_queries_explorer()` | Split in Python: `model_queries = [q for q in queries if q.source == 'model']`, pass both |
| `browser/dashboard_builder.html` | `.append()` to group block types by category | `dashboard/router.py:_block_types_for_template()` | Return `categories` dict from `_block_types_for_template()` using `defaultdict(list)` |
| `admin/models.html` | `.append()` to merge object + datatype properties | Admin model detail view | Pass `all_props = custom_types.object_properties + custom_types.datatype_properties` |
| `browser/object_read.html` | `.append()` to build form_paths set | `browser/objects.py:object_detail()` | Pass `form_paths = {prop.path for prop in form.properties}` |
| `browser/object_embed.html` | `.append()` + `namespace()` for same pattern | `browser/objects.py:object_detail()` | Same fix as object_read — add `form_paths` to context |
| `browser/object_tab.html` | `namespace()` counting non-empty properties | `browser/objects.py:object_detail()` | Compute `property_count` in Python, pass in context |
| `browser/_context_rules.html` | `.append()` as boolean flag counter | `browser/settings.py` or wherever context_rules is served | Use `any()` or `selectattr` filter; or pass `has_conditions: bool` |
| `notion/partials/scan_results.html` | `.append()` to group warnings by category | `notion/router.py` scan results endpoint | Group warnings in Python: `warning_categories = defaultdict(list)` |
| `obsidian/partials/scan_results.html` | Same pattern | `obsidian/router.py` | Same fix |
| `forms/object_form.html` | `namespace()` splitting required/optional/grouped props | `browser/objects.py:object_detail()` | Pass `required_props`, `optional_ungrouped`, `grouped_props` from Python |
| `notion/partials/property_mapping.html` | `namespace()` for auto-match IRI | `notion/router.py` property mapping step | Compute auto-match in Python view, pass as dict |
| `browser/object_read.html` | `namespace()` for `any_prop` flag | `browser/objects.py` | Pass `any_prop: bool` from Python |

**Key constraint:** The `object_detail()` function in `browser/objects.py` serves `object_tab.html`, `object_read.html`, and `object_embed.html`. All three templates' computation can be consolidated into a single block of pre-computation at the end of `object_detail()`.

### T02: Importer template deduplication

**Near-identical templates (can become shared):**
- `import.html` — differs only in title ("Notion Workspace" vs "Obsidian Vault") and include paths
- `partials/step_bar.html` — differs in step count (7 vs 6, Notion has "Relations")
- `partials/upload_form.html` — differs in labels, input IDs, URL prefix
- `partials/scan_trigger.html` — differs in labels, URL prefix, one Notion-only script block
- `partials/import_progress.html` — differs only in step number and step_bar include path
- `partials/import_summary.html` — mostly similar structure, differs in Notion's relation_mapping stats

**Structurally different (keep separate, but extract shared skeleton):**
- `partials/scan_results.html` — Notion: databases/columns/relations stats. Obsidian: notes/tags/wikilinks stats. Shared: stats card grid, type-group accordion pattern, warnings section.
- `partials/preview.html` — Different object preview structure (Notion has CSV rows, Obsidian has markdown frontmatter)
- `partials/type_mapping.html` — Different source data structure (Notion databases vs Obsidian type groups)
- `partials/property_mapping.html` — Different column concepts

**Deduplication strategy:**
1. Create `backend/app/templates/importer/partials/` with shared templates
2. Each shared template uses variables: `{{ importer_name }}`, `{{ url_prefix }}`, `{{ steps }}` (list of tuples)
3. Python views pass these via template context: `{"importer_name": "Notion", "url_prefix": "/browser/notion", "steps": [(1, "Upload"), ...]}`
4. For the step_bar: parametric via `steps` list variable (7 steps for Notion, 6 for Obsidian)
5. For scan_results and other divergent templates: extract shared sections (stats cards, warnings) into macros or includes, keep importer-specific sections in `notion/partials/` and `obsidian/partials/`
6. Update `{% include %}` paths in templates and keep Notion's `relation_mapping.html` as Notion-only (Obsidian doesn't have it)

**URL routing:** Notion uses `/browser/notion/`, Obsidian uses `/browser/import/`. Both routers' view functions already pass `import_id` — they just need to add `url_prefix` and `importer_name` to template context.

**Lines saved estimate:** ~600 lines eliminated from ~2,253 total across both importers.

### T03: Guide page data-driven chapter list

Define in `backend/app/shell/router.py`:
```python
GUIDE_CHAPTERS = [
    {"section": "Interactive Tutorials", "items": [
        {"filename": None, "title": "Welcome to SemPKM", "icon": "play-circle", "url": "/browser/?tour=welcome", "type": "tour"},
        {"filename": None, "title": "Creating Your First Object", "icon": "plus-circle", "url": "/browser/?tour=create-object", "type": "tour"},
    ]},
    {"section": "User Guide", "items": [
        {"filename": "01-what-is-sempkm.md", "title": "1. What is SemPKM?", "icon": "info"},
        {"filename": "02-core-concepts.md", "title": "2. Core Concepts", "icon": "layers"},
        # ... ~50 entries
    ]},
    # External References section (different rendering)
]
```

Template becomes:
```jinja2
{% for section in guide_sections %}
<section class="docs-section">
    <h3 class="docs-section-title">{{ section.title }}</h3>
    <div class="docs-chapter-list">
    {% for ch in section.chapters %}
        <button class="docs-chapter-item{{ ' docs-chapter-appendix' if ch.appendix else '' }}"
                hx-get="/guide/{{ ch.filename }}" hx-target="#app-content" hx-swap="innerHTML" hx-push-url="true">
            <i data-lucide="{{ ch.icon }}"></i>
            <span>{{ ch.title }}</span>
        </button>
    {% endfor %}
    </div>
</section>
{% endfor %}
```

**Result:** guide.html drops from 578 lines to ~50 lines of template. The `GUIDE_CHAPTERS` data structure (~100 lines) is Python — testable, diffable, single source of truth for the in-app guide page. README.md and index.html remain separate (per KNOWLEDGE.md three-file-sync rule).

## Constraints

1. **No functional changes** — all three tasks are pure refactoring. Every template must render identical HTML before/after.
2. **Notion's `relation_mapping.html` stays Notion-only** — Obsidian has no equivalent step.
3. **htmx URL paths differ** between importers (`/browser/notion/` vs `/browser/import/`) — shared templates must use a variable, not hardcoded paths.
4. **`_context_rules.html`** `.append()` is used as a bool counter — the simplest fix is Jinja2's `selectattr` filter or passing `has_conditions` from Python. Check which view serves this partial.
5. **`object_form.html` namespace()** for required/optional splitting is borderline — it's presentation-layer partitioning. Consider moving to Python OR replacing with `selectattr`/`rejectattr` Jinja2 filters (cleaner, no namespace needed, no Python view change).

## Verification Strategy

- **T01:** `rg '\.append\(' backend/app/templates/ -g '*.html'` → 0 results. `rg 'namespace\(' backend/app/templates/ -g '*.html'` → only `base_namespace`/`info.namespace` (non-hack references). Run existing test suite (`cd backend && python -m pytest tests/ -x -q`) to catch any import/runtime errors.
- **T02:** `diff` old vs new rendered HTML for a sample import flow (start Docker, hit the Notion/Obsidian import pages, compare output). `wc -l` on templates directory shows reduction. E2E import tests pass.
- **T03:** `grep -c 'docs-chapter-item' backend/app/templates/guide.html` returns 0 (no more hardcoded buttons). `wc -l backend/app/templates/guide.html` < 80. Navigate to `/guide` in browser and verify all chapters render.
- **Cross-cutting:** Full E2E suite in S07 provides regression safety net.

## Task Ordering

T01 → T02 → T03 (but all are independent — no hard dependencies between them). T01 is listed first because it touches the most files and the scan_results `.append()` fix in Notion/Obsidian templates should happen before T02 deduplicates those templates (otherwise T02 would need to deduplicate the hack and then T01 would remove it from the shared template — cleaner to fix first).
