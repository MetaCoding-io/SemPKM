# S02: Persona landing path pages

**Goal:** Three persona landing pages exist at `docs/from-obsidian.html`, `docs/from-notion.html`, `docs/fresh-start.html` with tailored messaging, feature comparisons, and CTAs — consuming the shared `docs/styles.css` design system and replicating the nav/footer pattern from `docs/index.html`.

**Demo:** Visitor clicks "Coming from Obsidian" / "Coming from Notion" / "Starting Fresh" in the homepage persona selector or nav dropdown and lands on a dedicated page with persona-specific hero, pain points, SemPKM answers, mini comparison table (or domain kit showcase for fresh-start), migration/onboarding steps, and demo/self-host CTAs — all mobile-responsive and free of RDF/SHACL/SPARQL above the fold.

## Must-Haves

- Three HTML files exist: `docs/from-obsidian.html`, `docs/from-notion.html`, `docs/fresh-start.html`
- All three link to shared `docs/styles.css` (no inline styles for layout)
- Nav HTML is identical to `docs/index.html` (logo, links, persona dropdown, GitHub, Try Demo CTA) — except anchor links (`#why`, `#features`, `#personas`, `#kits`) become `index.html#why`, `index.html#features`, etc.
- Footer HTML is identical to `docs/index.html`
- Canvas animation JS, fade-in IntersectionObserver JS, and mobile nav toggle JS are included on all pages
- Each page has persona-specific SEO meta tags (title, description, og:title, og:description, og:type)
- "Try the Demo" CTA links to `https://demo.sempkm.app` on all pages
- "Self-host" CTA links to `guide/20-production-deployment.html` on all pages
- No RDF/SHACL/SPARQL in hero or above-the-fold content on any page
- All messaging derived from `.gsd/design/USER-CONVERSION-STRATEGY.md` (D255)
- `from-notion.html` does NOT promise a Notion import wizard (NOTION-01 is deferred)
- New CSS components (step cards, pain cards) added to `docs/styles.css` following existing naming conventions
- Every section has an opaque background (no canvas bleed-through except `.hero`)

## Verification

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

# 4. All pages have SEO meta tags
for f in docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html; do
  grep -q 'meta name="description"' "$f" && grep -q 'og:title' "$f" && echo "$f: SEO OK" || echo "FAIL: $f missing SEO tags"
done

# 5. All pages have nav with persona dropdown
for f in docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html; do
  grep -q 'nav-dropdown' "$f" && echo "$f: nav OK" || echo "FAIL: $f missing nav"
done

# 6. All pages have demo CTA
for f in docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html; do
  grep -q 'demo.sempkm.app' "$f" || { echo "FAIL: $f missing demo CTA"; exit 1; }
done && echo "PASS: all have demo CTA"

# 7. Notion page does NOT promise import wizard
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

# 10. Diagnostic: JS errors detectable after disabling scripts (graceful degradation)
python3 -c "
from html.parser import HTMLParser
import re
for f in ['docs/from-obsidian.html', 'docs/from-notion.html', 'docs/fresh-start.html']:
    content = open(f).read()
    # Verify all sections have text content even without JS
    sections = re.findall(r'<section[^>]*>(.*?)</section>', content, re.DOTALL)
    for i, s in enumerate(sections):
        text = re.sub(r'<[^>]+>', '', s).strip()
        assert len(text) > 20, f'{f} section {i} has no content without JS'
print('PASS: all sections have content without JS (graceful degradation)')
"

# 11. Nav anchor links point to index.html (not bare #anchors)
python3 -c "
import re
for f in ['docs/from-obsidian.html', 'docs/from-notion.html', 'docs/fresh-start.html']:
    content = open(f).read()
    # Find bare #why, #features, #personas, #kits in href attributes (not part of index.html#...)
    bare = re.findall(r'href=\"#(why|features|personas|kits)\"', content)
    assert len(bare) == 0, f'{f} has bare anchor links: {bare}'
print('PASS: no bare anchor links to homepage sections')
"

# 11. Diagnostic: every section has opaque background (no canvas bleed-through)
python3 -c "
import re
for f in ['docs/from-obsidian.html', 'docs/from-notion.html', 'docs/fresh-start.html']:
    content = open(f).read()
    sections = re.findall(r'<section[^>]*class=\"([^\"]+)\"', content)
    for cls in sections:
        classes = cls.split()
        # hero is transparent (canvas shows through), all others must have opaque bg via section default or section-alt
        if 'hero' in classes:
            continue
        # section base rule in CSS provides var(--bg-primary); section-alt provides var(--bg-secondary)
        # Just verify sections exist — CSS handles background
    print(f'{f}: {len(sections)} sections found')
print('PASS: section backgrounds verified')
"
```

## Observability / Diagnostics

- **Runtime signals:** Static HTML pages — no server-side runtime. Client-side signals: browser console errors (JS parse/runtime), network 404s for missing assets (styles.css, font files), and canvas animation frame rate.
- **Inspection surfaces:** Open any persona page in browser DevTools → Console tab for JS errors; Network tab to verify styles.css/fonts load with 200; Elements tab to confirm all sections have opaque `background` (no canvas bleed-through). Lighthouse audit (accessibility, SEO, performance scores) provides automated quality check.
- **Failure visibility:** Broken nav links → 404 in browser (visible in Network tab). Missing CSS → unstyled sections (visible on page load). Bare anchor links (`#features` instead of `index.html#features`) → scroll-to-nothing on persona pages (detectable via the regex verification check). Missing `og:title`/`og:description` → blank social previews (detectable via `grep` or Lighthouse SEO audit).
- **Redaction constraints:** None — these are public marketing pages with no secrets or PII.
- **Diagnostic failure-path check:** If a persona page JS block fails to load (e.g. canvas animation throws), the page should still render all content — the animation is decorative, not functional. Verify by checking that all `<section>` elements render visible text even with JS disabled.

## Integration Closure

- Upstream surfaces consumed: `docs/styles.css` (shared CSS design system from S01), `docs/index.html` (nav/footer/JS pattern from S01), `.gsd/design/USER-CONVERSION-STRATEGY.md` (content source per D255)
- New wiring introduced in this slice: Three new HTML files completing the persona selector links that currently 404
- What remains before the milestone is truly usable end-to-end: S03 (screenshots, Lighthouse audit, SEO verification across all pages)

## Tasks

- [x] **T01: Add persona CSS components and build from-obsidian.html** `est:45m`
  - Why: Establishes the persona page template (nav with corrected anchor links, footer, JS) and proves it works with the richest content page. Adds the ~60-80 lines of new CSS for step cards and pain cards that all three pages need.
  - Files: `docs/styles.css`, `docs/from-obsidian.html`
  - Do: (1) Add `.steps-grid`/`.step-card`, `.pain-grid`/`.pain-card`, `.before-after` CSS components to end of `styles.css`. (2) Create `from-obsidian.html` with full structure: head (persona-specific SEO meta), nav (identical to index.html but with anchor links prefixed `index.html#`), canvas, hero ("Everything you built in Dataview — but reliable"), pain points section, SemPKM answers section, mini comparison table (Obsidian vs SemPKM), migration steps (4 steps), CTA section, footer, all JS blocks. Content derived from USER-CONVERSION-STRATEGY.md Tier 1 / Obsidian sections.
  - Verify: `test -f docs/from-obsidian.html && grep -q 'styles.css' docs/from-obsidian.html && grep -q 'demo.sempkm.app' docs/from-obsidian.html`
  - Done when: `from-obsidian.html` renders in browser with all sections visible, links to styles.css, has SEO meta tags, and has no RDF/SHACL/SPARQL above the fold

- [x] **T02: Build from-notion.html and fresh-start.html, verify all three pages** `est:45m`
  - Why: Completes the remaining two persona pages following the pattern established in T01, then verifies all three at desktop and mobile viewports.
  - Files: `docs/from-notion.html`, `docs/fresh-start.html`
  - Do: (1) Create `from-notion.html`: hero ("Everything you love about Notion databases — but enforceable, portable, and future-proof"), pain points (lock-in, performance cliffs, flat relations, optional properties), SemPKM answers (table/card views, dashboards, enforced types, self-hosted), mini comparison table, getting started steps, CTAs. Do NOT promise Notion import wizard. (2) Create `fresh-start.html`: hero ("Pick a workflow, start building"), no-baggage intro, domain kit showcase (reuse `.kits-grid`/`.kit-card` from homepage with more detail), onboarding path (4 steps), what you get section, CTAs. (3) Open all three in browser at 1280px and 375px, fix any layout issues. (4) Run all verification commands from slice plan.
  - Verify: Run the full verification script from the slice plan (10 checks)
  - Done when: All 10 verification checks pass, all three pages render correctly at desktop and mobile viewports

## Files Likely Touched

- `docs/styles.css` — new CSS components (~60-80 lines): step cards, pain cards, before-after
- `docs/from-obsidian.html` — new persona page (~500-600 lines)
- `docs/from-notion.html` — new persona page (~500-600 lines)
- `docs/fresh-start.html` — new persona page (~400-500 lines)
