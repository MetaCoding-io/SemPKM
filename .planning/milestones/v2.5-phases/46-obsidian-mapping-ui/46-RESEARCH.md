# Phase 46: Obsidian Mapping UI - Research

**Researched:** 2026-03-08
**Domain:** htmx wizard UI, SHACL shape querying, mapping config persistence
**Confidence:** HIGH

## Summary

Phase 46 adds three wizard steps (Type Map, Property Map, Preview) to the existing Obsidian import page. The existing codebase provides strong foundations: `VaultScanResult` with `NoteTypeGroup` data, `ShapesService` with `get_node_shapes()`/`get_types()` for installed Mental Model types, and htmx partial rendering patterns established in Phase 45.

The primary technical challenge is **per-group frontmatter key tracking**. The current scan result stores frontmatter keys globally (across all notes), but property mapping needs to know which keys appear in notes belonging to each type group. This requires either enhancing the scanner/models to track per-group keys, or computing them at mapping time from persisted data.

**Primary recommendation:** Extend `NoteTypeGroup` to include per-group `frontmatter_keys` summaries during scanning, add wizard step endpoints to the obsidian router, and use htmx `hx-swap="innerHTML"` on `#import-content` for step transitions -- the same pattern already used for upload/scan/results transitions.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Import page uses a linear wizard with steps: Upload -> Scan -> Type Map -> Property Map -> Preview -> Import
- Phase 46 adds steps 3-5 (Type Map, Property Map, Preview)
- Step bar at top with numbered circles and labels, current step highlighted, completed steps show checkmark
- Linear navigation: forward requires completing current step, back is always available
- "Next" button enables when step is valid
- Each step replaces content area via htmx
- Type mapping: dropdown per detected group row listing installed Mental Model types, "Skip" option, many-to-one allowed, expandable sample notes, table columns: Detected Group | Count | Signal | Map To dropdown
- Property mapping: per-type tables, SHACL property dropdown, custom RDF IRI input, inline sample values, skip option, markdown body auto-maps to body.set
- Preview: summary table (type, count, properties mapped), 2-3 sample objects per type as key-value lists, "Back to Mapping" and "Import" buttons
- Mapping saved as mapping_config.json alongside scan_result.json
- Auto-save on each dropdown change via htmx POST
- One-off per scan, cleaned up on discard

### Claude's Discretion
- Exact step bar visual design and CSS
- mapping_config.json schema structure
- How to fetch and display SHACL properties for the type dropdown
- Custom IRI input UX (inline text field, modal, etc.)
- How many sample objects to render per type in preview
- htmx endpoint design for auto-save and step transitions

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| OBSI-03 | User can interactively map Obsidian note categories to Mental Model types | Type mapping wizard step with dropdown per NoteTypeGroup, ShapesService.get_types() populates options |
| OBSI-04 | User can map frontmatter keys to RDF properties for each type | Property mapping wizard step with per-type tables, ShapesService.get_form_for_type() provides SHACL PropertyShape list per target class |
| OBSI-05 | User can preview mapped objects before committing import | Preview wizard step renders sample objects from scan data + mapping config as key-value lists |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | Backend endpoints for wizard steps | Already used for all obsidian routes |
| Jinja2 | existing | Server-side template rendering | htmx partial response pattern |
| htmx | existing | Step transitions, auto-save | Already drives all import page interactions |
| Lucide | existing | Icons in step bar and buttons | Project standard icon library |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ShapesService | existing | Fetch installed types and SHACL properties | Type/property mapping dropdowns |
| VaultScanResult | existing | Read scan data for mapping source | All wizard steps reference this |
| python-frontmatter | existing | Re-parse notes for preview generation | Preview step needs full note content |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Server-rendered wizard steps | Client-side JS wizard | Server-side keeps htmx pattern consistent, simpler state management |
| Re-parsing notes for per-group keys | Pre-computing during scan | Pre-computing is cleaner and avoids re-reading files at mapping time |

## Architecture Patterns

### Recommended Project Structure
```
backend/app/obsidian/
    router.py           # Add wizard step endpoints
    models.py           # Add MappingConfig model, extend NoteTypeGroup
    scanner.py          # Enhance to track per-group frontmatter keys
backend/app/templates/obsidian/
    import.html          # Add step bar to base layout
    partials/
        step_bar.html        # Wizard step indicator (reusable)
        type_mapping.html    # Step 3: type mapping table
        property_mapping.html # Step 4: property mapping tables
        preview.html         # Step 5: preview with sample objects
frontend/static/css/
    import.css           # Extend with wizard step bar + mapping table styles
```

### Pattern 1: Wizard Step Transitions via htmx

**What:** Each wizard step is a separate endpoint returning HTML that replaces `#import-content`. Step bar is included in each partial to show current position.
**When to use:** All step navigation (Next, Back buttons).
**Example:**
```python
# Router endpoint for type mapping step
@router.get("/{import_id}/step/type-mapping")
async def type_mapping_step(request, import_id, user=Depends(get_current_user)):
    scan_result = _load_scan_result(user, import_id)
    mapping_config = _load_or_create_mapping(user, import_id)
    types = await shapes_service.get_types()
    return templates.TemplateResponse(request, "obsidian/partials/type_mapping.html", {
        "scan_result": scan_result,
        "mapping_config": mapping_config,
        "available_types": types,
        "import_id": import_id,
        "current_step": 3,
    })
```

```html
<!-- Step transition button -->
<button hx-get="/browser/import/{{ import_id }}/step/property-mapping"
        hx-target="#import-content"
        hx-swap="innerHTML"
        class="btn btn-primary"
        id="next-btn">
    Next: Property Mapping
</button>
```

### Pattern 2: Auto-Save via htmx POST on Change

**What:** Each dropdown change triggers an htmx POST that saves the mapping and returns minimal confirmation (or the same dropdown with updated state).
**When to use:** Type mapping dropdowns, property mapping dropdowns.
**Example:**
```html
<!-- Type mapping dropdown with auto-save -->
<select name="type_mapping"
        hx-post="/browser/import/{{ import_id }}/mapping/type"
        hx-vals='{"group_key": "{{ group.type_name }}|{{ group.signal_source }}", "target_type": ""}'
        hx-swap="none"
        hx-trigger="change">
    <option value="">-- Skip --</option>
    {% for t in available_types %}
    <option value="{{ t.iri }}" {% if mapping.get(group_key) == t.iri %}selected{% endif %}>
        {{ t.label }}
    </option>
    {% endfor %}
</select>
```

**Note:** Use `hx-include="this"` or `hx-vals` to send the selected value. `hx-swap="none"` avoids DOM replacement on auto-save. Alternatively, swap a small status indicator to confirm save.

### Pattern 3: mapping_config.json Schema

**What:** Persisted mapping configuration structure.
**Recommended schema:**
```json
{
    "version": 1,
    "type_mappings": {
        "Projects|folder:Projects": {
            "target_type_iri": "urn:sempkm:basic-pkm:Project",
            "target_type_label": "Project"
        },
        "Uncategorized|none": null
    },
    "property_mappings": {
        "urn:sempkm:basic-pkm:Project": {
            "status": {
                "target_property_iri": "http://purl.org/dc/terms/subject",
                "target_property_label": "Subject",
                "source": "shacl"
            },
            "due_date": {
                "target_property_iri": "http://purl.org/dc/terms/date",
                "target_property_label": "Date",
                "source": "shacl"
            },
            "custom_field": null
        }
    }
}
```

**Key design choices:**
- Group key is `type_name|signal_source` (matches NoteTypeGroup identity)
- `null` value means "skip this group/property"
- Property mappings are keyed by target type IRI, not group key (since many groups can map to one type)
- `source` field distinguishes SHACL-derived vs custom IRI mappings

### Pattern 4: Per-Group Frontmatter Keys

**What:** Track which frontmatter keys appear in notes of each type group.
**Why needed:** Property mapping shows different key tables per type, and keys vary by group.
**Implementation:** Extend `NoteTypeGroup` with `frontmatter_keys: list[FrontmatterKeySummary]` and populate during scanning.

```python
# In scanner.py, during note processing:
group_fm_keys: dict[tuple[str, str], dict[str, dict]] = {}
# ... when classifying a note into a type group:
bucket_key = (type_name, signal_source)
for key, value in meta.items():
    if bucket_key not in group_fm_keys:
        group_fm_keys[bucket_key] = {}
    if key not in group_fm_keys[bucket_key]:
        group_fm_keys[bucket_key][key] = {"count": 0, "samples": set()}
    group_fm_keys[bucket_key][key]["count"] += 1
    if len(group_fm_keys[bucket_key][key]["samples"]) < 5:
        group_fm_keys[bucket_key][key]["samples"].add(str(value)[:100])
```

### Pattern 5: Preview Generation

**What:** Build sample objects from scan data + mapping config for preview display.
**How:** For each mapped type, take 2-3 sample notes from the group's `sample_notes` paths, re-read their frontmatter, apply property mappings, and render as key-value pairs.
**Why re-read:** The scan result only stores paths and key summaries, not per-note frontmatter values. The vault files are still extracted on disk at this point.

```python
async def _generate_preview(scan_result, mapping_config, vault_root, shapes_service):
    previews = []
    for group in scan_result.type_groups:
        group_key = f"{group.type_name}|{group.signal_source}"
        type_mapping = mapping_config.type_mappings.get(group_key)
        if not type_mapping:
            continue  # skipped group

        sample_objects = []
        for note_path in group.sample_notes[:3]:
            full_path = vault_root / note_path
            post = frontmatter.load(str(full_path))
            mapped_props = {}
            for fm_key, fm_val in post.metadata.items():
                prop_mapping = mapping_config.property_mappings.get(
                    type_mapping.target_type_iri, {}
                ).get(fm_key)
                if prop_mapping:
                    mapped_props[prop_mapping.target_property_label] = str(fm_val)
            sample_objects.append({
                "title": note_path,
                "type_label": type_mapping.target_type_label,
                "properties": mapped_props,
                "has_body": bool(post.content.strip()),
            })
        previews.append({
            "type_label": type_mapping.target_type_label,
            "type_iri": type_mapping.target_type_iri,
            "total_count": group.count,
            "mapped_properties": len(mapping_config.property_mappings.get(type_mapping.target_type_iri, {})),
            "samples": sample_objects,
        })
    return previews
```

### Anti-Patterns to Avoid
- **Client-side state management:** Do not store mapping state in JS variables or localStorage. Use server-side mapping_config.json as single source of truth.
- **Full page reload on step change:** Use htmx partial swap, not page reload. The import page URL stays the same; only `#import-content` changes.
- **Inline styles on Lucide icons:** Per CLAUDE.md, always use CSS classes for Lucide icon sizing with `flex-shrink: 0`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Type list for dropdowns | Custom SPARQL query | `ShapesService.get_types()` | Already returns `[{iri, label}]` list |
| Property list per type | Custom shape parsing | `ShapesService.get_form_for_type(type_iri)` | Returns `NodeShapeForm` with full `PropertyShape` list |
| Frontmatter parsing | Custom YAML parser | `python-frontmatter` library | Already a dependency, handles edge cases |
| JSON serialization | Manual dict building | Dataclass `to_dict()`/`from_dict()` pattern | Matches existing `VaultScanResult` pattern |
| Icon rendering | Inline SVG | Lucide `data-lucide` attributes | Project standard, auto-replaced by `lucide.createIcons()` |

**Key insight:** ShapesService already provides everything needed for the type and property dropdowns. The main new code is the mapping config model, the wizard step endpoints, and the Jinja2 templates.

## Common Pitfalls

### Pitfall 1: Lucide Icons in Flex Containers
**What goes wrong:** Icons become invisible (0px width) inside flex buttons/rows.
**Why it happens:** SVG elements are flex items; without `flex-shrink: 0` they compress to nothing.
**How to avoid:** Per CLAUDE.md, always add `flex-shrink: 0` in CSS for SVGs inside flex containers.
**Warning signs:** Buttons appear to have no icon but spacing suggests one exists.

### Pitfall 2: htmx Swap Losing Lucide Icons
**What goes wrong:** After htmx swaps new content, Lucide icons show as raw `<i>` tags.
**Why it happens:** `lucide.createIcons()` only runs on page load; swapped content has unprocessed `<i data-lucide>` elements.
**How to avoid:** Call `lucide.createIcons()` in a `<script>` block at the end of each partial, or use htmx `afterSwap` event.
**Warning signs:** Icons missing after step transitions.

### Pitfall 3: Per-Group Key Aggregation When Many-to-One Mapping
**What goes wrong:** When multiple groups map to the same type, property mapping needs to show the union of all frontmatter keys from all groups.
**Why it happens:** Each group has its own set of frontmatter keys; merging requires intentional aggregation.
**How to avoid:** In the property mapping step, iterate all groups mapped to the same target type and merge their `frontmatter_keys` lists, summing counts and combining samples.
**Warning signs:** Property mapping table shows only one group's keys when multiple groups map to the same type.

### Pitfall 4: Stale mapping_config After Scan Re-run
**What goes wrong:** If user re-scans the vault, old mapping_config references groups that no longer exist.
**Why it happens:** scan_result.json is overwritten on re-scan, but mapping_config.json is not.
**How to avoid:** Delete mapping_config.json when a new scan starts (in the `trigger_scan` endpoint).
**Warning signs:** Dropdown selections reference non-existent groups; UI shows empty rows.

### Pitfall 5: ShapesService Async in Sync Template Context
**What goes wrong:** `ShapesService.get_types()` and `get_form_for_type()` are async methods.
**Why it happens:** They query the triplestore via async HTTP.
**How to avoid:** Await them in the router endpoint before passing results to the template context. Never call async methods from Jinja2 templates.
**Warning signs:** Coroutine objects rendered as strings in HTML.

### Pitfall 6: Select Element `hx-vals` vs `hx-include`
**What goes wrong:** Auto-save POST doesn't include the selected dropdown value.
**Why it happens:** `hx-vals` is static JSON; it doesn't dynamically read the current `<select>` value.
**How to avoid:** Use `hx-include="this"` on the select element, or use `name` attribute and let htmx serialize the form. Alternatively, wrap each row in a small `<form>` element.
**Warning signs:** Server always receives the same value regardless of selection.

## Code Examples

### Wizard Step Bar Template
```html
<!-- partials/step_bar.html -->
<div class="import-step-bar">
    {% set steps = [
        (1, "Upload"),
        (2, "Scan"),
        (3, "Types"),
        (4, "Properties"),
        (5, "Preview"),
        (6, "Import"),
    ] %}
    {% for num, label in steps %}
    <div class="step-item {% if num == current_step %}step-active{% elif num < current_step %}step-complete{% endif %}">
        <div class="step-circle">
            {% if num < current_step %}
                <i data-lucide="check"></i>
            {% else %}
                {{ num }}
            {% endif %}
        </div>
        <span class="step-label">{{ label }}</span>
    </div>
    {% if not loop.last %}
    <div class="step-connector {% if num < current_step %}step-connector-complete{% endif %}"></div>
    {% endfor %}
</div>
```

### Type Mapping Table Row
```html
<tr class="type-mapping-row {% if group.type_name == 'Uncategorized' %}uncategorized{% endif %}">
    <td>
        <details>
            <summary class="type-group-name">{{ group.type_name }}</summary>
            <ul class="type-group-notes">
                {% for note in group.sample_notes[:10] %}
                <li>{{ note }}</li>
                {% endfor %}
            </ul>
        </details>
    </td>
    <td>{{ group.count }}</td>
    <td><span class="import-signal-badge">{{ group.signal_source }}</span></td>
    <td>
        <select name="target_type"
                class="mapping-select"
                hx-post="/browser/import/{{ import_id }}/mapping/type"
                hx-include="this"
                hx-vals='{"group_key": "{{ group.type_name }}|{{ group.signal_source }}"}'
                hx-swap="none">
            <option value="">-- Skip --</option>
            {% for t in available_types %}
            <option value="{{ t.iri }}"
                    {% if current_mapping == t.iri %}selected{% endif %}>
                {{ t.label }}
            </option>
            {% endfor %}
        </select>
    </td>
</tr>
```

### MappingConfig Dataclass
```python
@dataclass
class TypeMapping:
    target_type_iri: str
    target_type_label: str

@dataclass
class PropertyMapping:
    target_property_iri: str
    target_property_label: str
    source: str  # "shacl" or "custom"

@dataclass
class MappingConfig:
    version: int = 1
    type_mappings: dict[str, TypeMapping | None] = field(default_factory=dict)
    # key: "group_type_name|signal_source", value: TypeMapping or None (skip)
    property_mappings: dict[str, dict[str, PropertyMapping | None]] = field(default_factory=dict)
    # key: target_type_iri, value: {frontmatter_key: PropertyMapping or None}

    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, data: dict) -> MappingConfig: ...
```

### ShapesService Usage for Property Dropdown
```python
# In router endpoint for property mapping step
forms = await shapes_service.get_node_shapes()
# Build lookup: target_class_iri -> list of PropertyShape
type_properties = {}
for form in forms:
    type_properties[form.target_class] = [
        {"iri": p.path, "label": p.name}
        for p in form.properties
    ]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| JS-heavy wizard with client state | htmx server-rendered steps | Project convention | Simpler, no client state management |
| Global frontmatter keys only | Per-group frontmatter keys needed | Phase 46 | Scanner/model enhancement needed |

## Open Questions

1. **Per-group frontmatter key tracking**
   - What we know: Current scan stores global keys only; property mapping needs per-group keys
   - What's unclear: Whether to enhance scanner now or compute at mapping time
   - Recommendation: Enhance `NoteTypeGroup` to include `frontmatter_keys` during scan. This is cleaner -- avoids re-parsing at mapping time and the data is naturally available during scan. Requires updating scanner, models (to_dict/from_dict), and scan_result.json schema. Existing scan results without per-group keys would need a re-scan (acceptable since mapping is a new feature).

2. **Custom IRI input UX**
   - What we know: User decided custom RDF property IRI should be possible
   - What's unclear: Exact interaction pattern
   - Recommendation: Add a text input that appears when user selects a "Custom IRI..." option in the property dropdown. Keep it inline (no modal) -- simpler and matches the table layout. Validate as a well-formed IRI on the server side.

3. **Step validation for "Next" button enabling**
   - What we know: Next button should enable when step is valid
   - What's unclear: What constitutes "valid" for each step
   - Recommendation: Type mapping: at least one group is mapped (not all skipped). Property mapping: no validation required (all properties can be skipped). This is simple and avoids blocking the user unnecessarily.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (e2e) |
| Config file | `e2e/playwright.config.ts` |
| Quick run command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium -g "import"` |
| Full suite command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OBSI-03 | Type mapping dropdown renders with Mental Model types, selection persists | manual-only | Manual UAT -- requires vault upload + installed model | No |
| OBSI-04 | Property mapping shows SHACL properties per type, custom IRI input works | manual-only | Manual UAT -- requires vault upload + type mapping | No |
| OBSI-05 | Preview shows sample objects with mapped properties and body indicator | manual-only | Manual UAT -- requires full mapping flow | No |

**Justification for manual-only:** These are multi-step wizard interactions requiring a pre-uploaded vault with scan results and an installed Mental Model. The e2e test infrastructure would need significant setup (vault fixture, model installation) that is better validated through manual UAT for this phase.

### Sampling Rate
- **Per task commit:** Manual browser verification of wizard step
- **Per wave merge:** Full wizard flow walkthrough (upload -> scan -> type map -> property map -> preview)
- **Phase gate:** Complete wizard flow UAT before `/gsd:verify-work`

### Wave 0 Gaps
None -- no automated tests planned for this phase. Manual UAT covers requirements.

## Sources

### Primary (HIGH confidence)
- `backend/app/obsidian/router.py` -- existing endpoint patterns, import_id handling, htmx partial responses
- `backend/app/obsidian/models.py` -- VaultScanResult, NoteTypeGroup, FrontmatterKeySummary dataclasses
- `backend/app/obsidian/scanner.py` -- scan logic, per-group note classification, frontmatter key collection
- `backend/app/services/shapes.py` -- ShapesService with get_node_shapes(), get_form_for_type(), get_types()
- `backend/app/dependencies.py` -- get_shapes_service dependency injection pattern
- `backend/app/templates/obsidian/` -- existing template structure and htmx patterns
- `frontend/static/css/import.css` -- existing import page styles
- `CLAUDE.md` -- Lucide icon rules, htmx conventions

### Secondary (MEDIUM confidence)
- CONTEXT.md decisions -- user-specified wizard flow, mapping persistence, UI layout

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in use, no new dependencies
- Architecture: HIGH - follows established htmx partial rendering pattern from Phase 45
- Pitfalls: HIGH - based on direct codebase analysis and CLAUDE.md documented issues

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable -- no external dependencies changing)
