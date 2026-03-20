---
estimated_steps: 5
estimated_files: 2
---

# T02: Build from-notion.html and fresh-start.html, verify all three pages

**Slice:** S02 — Persona landing path pages
**Milestone:** M026

## Description

This task creates the remaining two persona landing pages (`docs/from-notion.html` and `docs/fresh-start.html`) following the template pattern established by `docs/from-obsidian.html` in T01. Then it verifies all three persona pages at desktop and mobile viewports and runs the full verification script.

The Notion page targets Tier 2 users who love databases and views but hate vendor lock-in. The Fresh Start page targets newcomers with no existing PKM system. Both use the shared CSS from `docs/styles.css` including the new step/pain components added in T01.

**Critical constraint:** The from-notion page must NOT promise a Notion import wizard — NOTION-01 is deferred. Frame it as "start fresh with SemPKM and get what Notion gives you, but better."

**Relevant skill:** `frontend-design` — load this skill for guidance on creating distinctive, production-grade HTML/CSS.

## Steps

1. **Create `docs/from-notion.html`** following the exact same structural pattern as `from-obsidian.html`:

   **`<head>`** — persona-specific:
   - `<title>SemPKM — Coming from Notion</title>`
   - `<meta name="description" content="Everything you love about Notion databases — but enforceable, portable, and future-proof. Self-hosted, no vendor lock-in, no performance cliffs.">` 
   - OG tags matching pattern

   **Content sections:**

   a. **Hero**: "Everything you love about Notion databases —<br><span class='gradient'>but yours to keep</span>"
      - Subtitle: about getting the structure of Notion with full ownership and enforced schemas
      - CTAs: Try Demo + Self-Host

   b. **Pain points** (section-alt, `.pain-grid`):
      - Vendor lock-in (your data lives on Notion's servers)
      - Performance cliffs at scale (thousands of pages = sluggish)
      - Flat relations (no typed links between databases)
      - Optional properties (nothing stops incomplete records)

   c. **SemPKM answers** (`.features-grid`):
      - Table and card views (same paradigm as Notion database views)
      - Dashboards (CSS Grid layouts with cross-view filtering — like Notion dashboards)
      - Create types like databases (in-app type creation = "create a database")
      - Forms with real validation (SHACL-driven — properties are enforced, not optional)
      - Self-hosted (your data on your machine, export anytime)
      - Full history (every change tracked, unlike Notion)

   d. **Mini comparison table** — Notion vs SemPKM:
      - Data ownership, Structure enforcement, Typed relationships, Performance at scale, Full history, Offline access

   e. **Getting started steps** (`.steps-grid`):
      - DO NOT mention "import from Notion" — NOTION-01 is deferred
      - Steps: Install with Docker → Pick a domain kit → Create your first type → Build views and dashboards

   f. **CTA section**, **Footer**, **JS** — same pattern as from-obsidian.html

2. **Create `docs/fresh-start.html`**:

   **`<head>`** — persona-specific:
   - `<title>SemPKM — Start Fresh</title>`
   - `<meta name="description" content="No existing notes? Perfect. Pick a domain kit and start building structured knowledge in under 3 minutes. Self-hosted, open source.">` 
   - OG tags matching pattern

   **Content sections:**

   a. **Hero**: "Pick a workflow,<br><span class='gradient'>start building</span>"
      - Subtitle: about no blank-page syndrome, domain kits give you instant structure
      - CTAs: Try Demo + Self-Host

   b. **No-baggage intro section** (section-alt):
      - Title: "No migration needed — just start"
      - Brief explanation that SemPKM comes with domain kits that give you types, forms, views, and validation instantly

   c. **Domain kit showcase** — reuse `.kits-grid` / `.kit-card` from homepage but with MORE detail per kit:
      - Basic PKM (5 types — what each does, who it's for)
      - Personal CRM (4 types — relationship tracking use case)
      - Zettelkasten+ (5 types — note progression workflow)
      - Research Workflow (4 types — academic research use case)
      - Each card slightly more descriptive than the homepage version

   d. **Onboarding path** (section-alt, `.steps-grid`):
      - Steps: Pick a domain kit → Take the 3-minute guided tour → Create your first object → Explore views and graph

   e. **What you get section** (`.features-grid`):
      - Auto-generated forms with validation
      - Table, card, and graph views
      - Full history and undo
      - Spatial canvas for visual thinking
      - WebDAV access for Markdown editing
      - Self-hosted, open source

   f. **CTA section**, **Footer**, **JS** — same pattern

3. **Browser verification at two viewports** — Open all three persona pages in the browser:
   - Desktop (1280px): all sections visible, comparison tables render, CTAs clickable, nav dropdown works
   - Mobile (375px): single column, no horizontal overflow, buttons full-width, nav hamburger works
   - Fix any CSS or layout issues found

4. **Run full verification script** from the slice plan (all 10 checks must pass):
   ```bash
   # All files exist
   test -f docs/from-obsidian.html && test -f docs/from-notion.html && test -f docs/fresh-start.html
   # styles.css linked, SEO tags, nav, demo CTA, no tech jargon, no bare anchors, HTML well-formed, no conflict markers, no Notion import promise
   ```

5. If any verification check fails, fix the issue and re-run.

## Must-Haves

- [ ] `docs/from-notion.html` created with all content sections
- [ ] `docs/fresh-start.html` created with all content sections
- [ ] from-notion does NOT promise Notion import wizard
- [ ] Both pages have corrected nav anchor links (index.html# prefix)
- [ ] Both pages have SEO meta tags
- [ ] Both pages have demo CTA linking to demo.sempkm.app
- [ ] Both pages have opaque section backgrounds (no canvas bleed-through)
- [ ] All 10 slice verification checks pass
- [ ] All three pages render correctly at 1280px and 375px viewports

## Verification

Run the complete verification script from the slice plan:

```bash
# 1. All three files exist
test -f docs/from-obsidian.html && test -f docs/from-notion.html && test -f docs/fresh-start.html && echo "PASS: all files exist"

# 2. All link to shared styles.css
for f in docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html; do
  grep -q 'styles.css' "$f" || { echo "FAIL: $f missing styles.css link"; exit 1; }
done && echo "PASS: all link to styles.css"

# 3. No RDF/SHACL/SPARQL above the fold
python3 -c "
import re
for f in ['docs/from-obsidian.html', 'docs/from-notion.html', 'docs/fresh-start.html']:
    content = open(f).read()
    hero_end = content.index('</section>') if '</section>' in content else 2000
    hero = content[:hero_end]
    for term in ['RDF', 'SHACL', 'SPARQL']:
        assert term not in hero, f'{term} found above fold in {f}'
print('PASS: no tech jargon above the fold')
"

# 4. SEO meta tags
for f in docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html; do
  grep -q 'meta name="description"' "$f" && grep -q 'og:title' "$f" && echo "$f: SEO OK"
done

# 5. Nav with persona dropdown
for f in docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html; do
  grep -q 'nav-dropdown' "$f" && echo "$f: nav OK"
done

# 6. Demo CTA present
for f in docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html; do
  grep -q 'demo.sempkm.app' "$f" || { echo "FAIL: $f missing demo CTA"; exit 1; }
done && echo "PASS: all have demo CTA"

# 7. No Notion import promise
! grep -qi 'import.*wizard\|import.*notion.*workspace\|upload.*notion' docs/from-notion.html && echo "PASS: no Notion import promise"

# 8. HTML well-formedness
python3 -c "
from html.parser import HTMLParser
for f in ['docs/from-obsidian.html', 'docs/from-notion.html', 'docs/fresh-start.html']:
    HTMLParser().feed(open(f).read())
print('PASS: all 3 pages HTML well-formed')
"

# 9. No conflict markers
grep -rn '<<<<<<< ' docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html || echo "PASS: no conflict markers"

# 10. No bare anchor links
python3 -c "
import re
for f in ['docs/from-obsidian.html', 'docs/from-notion.html', 'docs/fresh-start.html']:
    content = open(f).read()
    bare = re.findall(r'href=\"#(why|features|personas|kits)\"', content)
    assert len(bare) == 0, f'{f} has bare anchor links: {bare}'
print('PASS: no bare anchor links to homepage sections')
"
```

Additionally, browser verification at 1280px and 375px for all three pages.

## Observability Impact

- **New signals:** Two new HTML pages become servable; browser console errors and network 404s are the primary failure signals. Canvas animation JS errors are decorative-only — page content renders without JS.
- **Inspection:** Open any page via `python3 -m http.server -d docs` → DevTools Console (JS errors), Network tab (404s for missing assets). `grep -c 'section' docs/from-notion.html docs/fresh-start.html` confirms section count.
- **Failure state:** Missing styles.css link → unstyled page (visible immediately). Broken nav anchors → 404 on click (Network tab). Missing demo CTA → no conversion path (detectable via `grep 'demo.sempkm.app'`).
- **Graceful degradation:** All `<section>` content is plain HTML; canvas animation and fade-in JS are progressive enhancement. Page remains fully readable with JS disabled.

## Inputs

- `docs/from-obsidian.html` — T01's output, used as the structural template for the other two pages
- `docs/styles.css` — shared CSS design system including new step/pain components from T01
- `docs/index.html` — nav/footer/JS reference (same as T01 input)
- `.gsd/design/USER-CONVERSION-STRATEGY.md` — content source for Notion and Fresh Start messaging

Key content from USER-CONVERSION-STRATEGY.md for Notion persona:
- **Hero:** "Everything you love about Notion databases — but enforceable, portable, and future-proof"
- **Pain points:** Cloud lock-in, performance cliffs, flat relations, optional properties
- **Answers:** Table/card views, dashboards, type creation, SHACL forms, self-hosted
- **CRITICAL:** Do NOT promise Notion import (NOTION-01 deferred). Frame as "start fresh and get what Notion gives you, but better"

Key content for Fresh Start persona:
- **Hero:** "Pick a workflow, start building"
- **Path:** Pick kit → guided tour → create first object → explore views
- **Key message:** No blank-page syndrome. Domain kits give instant types/forms/views.

## Expected Output

- `docs/from-notion.html` — complete persona landing page (~500-600 lines)
- `docs/fresh-start.html` — complete persona landing page (~400-500 lines)
- All 10 slice verification checks passing
- Browser verification at 1280px and 375px confirming correct rendering
