---
phase: 34-merge-inferred-properties-into-relations
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/templates/browser/object_read.html
  - backend/app/browser/router.py
  - frontend/static/css/workspace.css
autonomous: true
requirements: [QUICK-34]

must_haves:
  truths:
    - "Inferred properties appear inline in the main property table alongside user-created properties"
    - "Each inferred property row displays an 'inferred' badge to distinguish it from user-created properties"
    - "The separate inferred column is completely removed from the object read view"
    - "Inferred IRI values are still rendered as clickable ref-pills with openTab()"
  artifacts:
    - path: "backend/app/templates/browser/object_read.html"
      provides: "Merged property table with inferred items inline"
      contains: "inferred-badge"
    - path: "backend/app/browser/router.py"
      provides: "Merged values dict with source tracking"
    - path: "frontend/static/css/workspace.css"
      provides: "Cleaned up CSS without inferred-column rules"
  key_links:
    - from: "backend/app/browser/router.py"
      to: "backend/app/templates/browser/object_read.html"
      via: "values dict entries now carry source='inferred' flag"
      pattern: "source.*inferred"
---

<objective>
Merge inferred properties into the main property table in the object read view, removing the separate inferred column. Inferred properties should appear alongside user-created properties in the same table, distinguished by the existing "inferred" badge/pill.

Purpose: Simplify the object read view by eliminating the two-column layout and showing all properties in one unified table. The user already likes the "inferred" badge in the relations panel -- apply the same pattern to the property table.

Output: Single-column property table with inferred items inline, no separate inferred panel.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@backend/app/browser/router.py (lines 575-725: object_read endpoint, inferred_values loading)
@backend/app/templates/browser/object_read.html (current two-column layout)
@backend/app/templates/browser/properties.html (reference: how relations panel uses inferred-badge)
@frontend/static/css/workspace.css (lines 1258-1337: inferred-column CSS to remove)

Key existing behavior:
- Router queries `urn:sempkm:inferred` graph for inferred triples per object
- `inferred_values` dict maps predicate IRI -> list of object values
- `inferred_labels` dict maps IRIs -> human-readable labels
- Relations panel (properties.html) already uses `obj.source == "inferred"` + `.inferred-badge`
- The `.inferred-badge` CSS class is shared and must be preserved (used by relations panel too)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Merge inferred properties into main values dict in router</name>
  <files>backend/app/browser/router.py</files>
  <action>
In the `load_object` endpoint (around line 600-725), change how inferred properties are prepared for the template:

1. After the existing `inferred_values` dict is built (line 609-624), merge inferred entries into the main `values` dict with source tracking. Instead of passing `inferred_values` as a separate dict, create a unified structure where each value carries its source.

2. Change the `values` dict structure: currently `values[pred] = [val1, val2, ...]` (plain strings). Change to `values[pred] = [{"value": val1, "source": "user"}, ...]`. Wrap existing user values with `{"value": v, "source": "user"}` and append inferred values with `{"value": v, "source": "inferred"}`.

3. After wrapping user values, merge `inferred_values` entries into `values`:
   - For each pred in `inferred_values`, append `{"value": v, "source": "inferred"}` to `values[pred]`
   - For inferred preds not already in `values`, create a new entry

4. Merge `inferred_labels` into `ref_labels` so the template can resolve all IRI labels from one dict. The inferred_labels dict already maps predicate IRIs and object IRIs to labels -- merge these into `ref_labels`.

5. Update the template context: remove `inferred_values` and `inferred_labels` from the context dict (lines 712-713). The template will now use `values` (with source tracking) and `ref_labels` (merged).

6. IMPORTANT: The edit form also uses `values` -- check `object_edit.html` or the edit mode. The edit form reads `values.get(prop.path, [])` and iterates plain strings. The simplest approach: keep `inferred_values` and `inferred_labels` in the context but ALSO add a new `merged_values` dict that the read template uses. Or, create a separate `read_values` dict that has the merged+tagged structure, keeping the original `values` dict untouched for the edit form.

   Recommended approach: Create `read_values` dict alongside the existing `values` dict:
   ```python
   # Build read_values: same keys as values but with source tracking + inferred merged in
   read_values: dict[str, list[dict]] = {}
   for pred, vals in values.items():
       read_values[pred] = [{"value": v, "source": "user"} for v in vals]
   for pred, vals in inferred_values.items():
       if pred not in read_values:
           read_values[pred] = []
       for v in vals:
           read_values[pred].append({"value": v, "source": "inferred"})
   ```
   Add `read_values` to the template context. Keep `values` unchanged for edit form compatibility.

7. Merge `inferred_labels` into `ref_labels` so the template has a single label lookup:
   ```python
   ref_labels.update(inferred_labels)
   ```
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM && python -c "import ast; ast.parse(open('backend/app/browser/router.py').read()); print('syntax OK')"</automated>
  </verify>
  <done>Router passes `read_values` (merged user+inferred with source tags) to template context. Original `values` dict unchanged for edit form. `ref_labels` includes inferred labels.</done>
</task>

<task type="auto">
  <name>Task 2: Update object_read template and remove inferred column CSS</name>
  <files>backend/app/templates/browser/object_read.html, frontend/static/css/workspace.css</files>
  <action>
**Template changes (object_read.html):**

1. Remove the entire two-column grid layout. Replace `object-read-columns` with a single-column container. Remove the `{% if has_inferred %}` conditional column and `inferred-column` div entirely (lines 142-170).

2. Remove the `object-read-columns--single` modifier class logic (line 61).

3. Remove the `has_inferred` variable check (line 52) and the conditional grid class (line 61). The layout should always be single-column now.

4. Remove `object-read-user-column` wrapper div -- just use `object-read-view` directly.

5. Update the property table to use `read_values` instead of `values`. For each form property, get values from `read_values.get(prop.path, [])`. Each entry is now a dict with `value` and `source` keys:

   ```jinja2
   {% for prop in form.properties %}
     {% set vals = read_values.get(prop.path, []) %}
     {% if vals %}
     <div class="property-row">
       <div class="property-label">{{ prop.name }}</div>
       <div class="property-value">
         {% if prop.target_class %}
           {% for item in vals %}
           <span class="ref-pill" data-ref-iri="{{ item.value }}"
                 onclick="openTab('{{ item.value }}', '{{ ref_labels.get(item.value, item.value) }}')">
             <span class="ref-pill-dot"></span>
             {{ ref_labels.get(item.value, item.value) }}
             {% if item.source == "inferred" %}
             <span class="inferred-badge" title="Inferred by OWL 2 RL reasoning">inferred</span>
             {% endif %}
           </span>
           {% endfor %}
         {% elif ... (keep existing datatype handlers but adapt to item.value) %}
           ...
         {% endif %}
       </div>
     </div>
     {% endif %}
   {% endfor %}
   ```

6. After the form-defined properties loop, add a section for inferred properties whose predicates are NOT in the form (i.e., inferred triples with predicates that have no SHACL property definition). These are properties that only exist because of inference. Iterate `read_values` keys that are NOT in the form property paths:

   ```jinja2
   {# Inferred-only properties (predicates not in SHACL form) #}
   {% set form_paths = [] %}
   {% if form %}
     {% for prop in form.properties %}
       {% set _ = form_paths.append(prop.path) %}
     {% endfor %}
   {% endif %}
   {% for pred, items in read_values.items() %}
     {% if pred not in form_paths %}
       {% set inferred_items = items | selectattr("source", "equalto", "inferred") | list %}
       {% if inferred_items %}
       <div class="property-row">
         <div class="property-label">{{ ref_labels.get(pred, pred) }}</div>
         <div class="property-value">
           {% for item in inferred_items %}
             {% if item.value.startswith('http') or item.value.startswith('urn:') %}
             <span class="ref-pill" data-ref-iri="{{ item.value }}"
                   onclick="openTab('{{ item.value }}', '{{ ref_labels.get(item.value, item.value) }}')">
               <span class="ref-pill-dot"></span>
               {{ ref_labels.get(item.value, item.value) }}
               <span class="inferred-badge" title="Inferred by OWL 2 RL reasoning">inferred</span>
             </span>
             {% else %}
             <span>{{ item.value }} <span class="inferred-badge" title="Inferred by OWL 2 RL reasoning">inferred</span></span>
             {% endif %}
           {% endfor %}
         </div>
       </div>
       {% endif %}
     {% endif %}
   {% endfor %}
   ```

7. Keep the `ns_check.has_values` logic but also check `read_values` for any inferred-only properties when deciding whether to show the "no content" empty state. Update the empty check: `{% set has_inferred = read_values is defined and read_values|length > (values|length if values else 0) %}` or simply check if read_values has any entries.

**CSS changes (workspace.css):**

1. Remove the entire "Object Read View: Two-Column Layout" section (lines 1258-1337):
   - `.object-read-columns` grid
   - `.object-read-columns--single`
   - `.object-read-user-column`
   - `.inferred-column` and all its children (`.inferred-column-header`, `.inferred-column-title`, nested `.property-table`, `.property-label`, `.property-value`, `.ref-pill`)
   - The `@media (max-width: 640px)` responsive rule for these classes

2. Keep the `.inferred-badge` CSS (lines 1218-1233) -- it is shared with the relations panel.

3. Keep the `.relation-item .inferred-badge` rule (lines 1235-1238) -- relations panel needs it.

4. Keep the `.inferred-stale` rules (lines 1240-1256) -- used by inference panel.
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM && python -c "
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('backend/app/templates'))
t = env.get_template('browser/object_read.html')
print('template parses OK')
" && rg -c 'inferred-column' frontend/static/css/workspace.css; echo "expect 0 matches"</automated>
  </verify>
  <done>Object read view shows all properties (user + inferred) in a single-column property table. Inferred properties have "inferred" badges. No separate inferred column exists. CSS for two-column layout removed. Shared `.inferred-badge` CSS preserved.</done>
</task>

</tasks>

<verification>
1. Open an object that has inferred properties -- verify they appear inline in the property table with "inferred" badges
2. Open an object with NO inferred properties -- verify the read view looks unchanged (single column, no empty inferred section)
3. Verify the relations panel still shows "inferred" badges on inferred relations (no regression)
4. Verify the edit form still works correctly (values dict unchanged)
5. Check the bottom panel INFERENCE tab still functions (separate system, should be unaffected)
</verification>

<success_criteria>
- Inferred properties appear in the main property table with "inferred" badges
- No separate inferred column or two-column layout in the object read view
- Relations panel inferred badges still work
- Edit form still functions correctly
- No CSS classes for `.inferred-column` remain
</success_criteria>

<output>
After completion, create `.planning/quick/34-merge-inferred-properties-into-relations/34-SUMMARY.md`
</output>
