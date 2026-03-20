---
estimated_steps: 6
estimated_files: 4
---

# T01: Fix broken links and add missing SEO tags

**Slice:** S03 — Screenshots, mobile polish, and SEO verification
**Milestone:** M026

## Description

All 4 docs pages have broken internal links (`guide/20-production-deployment.html` doesn't exist — the guide is an SPA at `guide/index.html`), the homepage og:image uses a relative URL instead of absolute, the 3 persona pages have no og:image at all, and none of the 4 pages have JSON-LD structured data. This task fixes all of these issues through pure HTML editing — no Docker or browser automation needed.

The domain for all absolute URLs is `https://sempkm.metacoding.io` (from `docs/CNAME`).

## Steps

1. **Fix broken guide links** — In all 4 files (`docs/index.html`, `docs/from-obsidian.html`, `docs/from-notion.html`, `docs/fresh-start.html`), find and replace `guide/20-production-deployment.html` with `guide/index.html`. There are 2 occurrences per file (CTA button + footer link), 8 total.

2. **Fix homepage og:image** — In `docs/index.html`, change the existing `<meta property="og:image" content="screenshots/01-workspace-overview-dark.png">` to use the absolute URL: `<meta property="og:image" content="https://sempkm.metacoding.io/screenshots/01-workspace-overview-dark.png">`.

3. **Add og:image to persona pages** — In each of the 3 persona files, add `<meta property="og:image" content="https://sempkm.metacoding.io/screenshots/01-workspace-overview-dark.png">` in the `<head>` section near the other OG tags. Place it after the existing `og:url` meta tag for consistency.

4. **Add JSON-LD structured data to all 4 pages** — Add a `<script type="application/ld+json">` block in the `<head>` of each page containing:
   ```json
   {
     "@context": "https://schema.org",
     "@graph": [
       {
         "@type": "Organization",
         "name": "SemPKM",
         "url": "https://sempkm.metacoding.io",
         "logo": "https://sempkm.metacoding.io/screenshots/01-workspace-overview-dark.png",
         "sameAs": ["https://github.com/metacoding/sempkm"]
       },
       {
         "@type": "WebSite",
         "name": "SemPKM",
         "url": "https://sempkm.metacoding.io"
       }
     ]
   }
   ```
   Place the JSON-LD block after the last `<meta>` tag and before the `<link>` tags in `<head>`.

5. **Run link checker** — Execute the Python link checker from the research doc to verify zero broken internal links across all 4 files:
   ```bash
   cd /home/james/Code/SemPKM && python3 -c "
   from html.parser import HTMLParser
   import os
   class C(HTMLParser):
       def __init__(s): super().__init__(); s.broken=[]
       def handle_starttag(s,t,a):
           if t=='a':
               for k,v in a:
                   if k=='href' and v and not v.startswith(('#','http','mailto','javascript')):
                       base=v.split('#')[0].split('?')[0]
                       if base and not os.path.exists(f'docs/{base}'): s.broken.append(base)
   for f in ['docs/index.html','docs/from-obsidian.html','docs/from-notion.html','docs/fresh-start.html']:
       c=C(); c.feed(open(f).read())
       for b in c.broken: print(f'BROKEN: {f} -> {b}')
   print('Link check complete')
   "
   ```

6. **Validate HTML and SEO tags** — Verify all pages parse cleanly and have the required tags:
   ```bash
   # HTML well-formedness
   python3 -c "
   from html.parser import HTMLParser
   for f in ['docs/index.html','docs/from-obsidian.html','docs/from-notion.html','docs/fresh-start.html']:
       HTMLParser().feed(open(f).read())
       print(f'{f}: OK')
   "
   # SEO tag counts
   grep -l 'og:image.*https://sempkm.metacoding.io' docs/index.html docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html | wc -l
   # Expected: 4
   grep -l 'application/ld+json' docs/index.html docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html | wc -l
   # Expected: 4
   grep -rn 'guide/20-production-deployment.html' docs/index.html docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html
   # Expected: no output
   ```

## Must-Haves

- [ ] Zero occurrences of `guide/20-production-deployment.html` across all 4 files
- [ ] `og:image` with absolute URL `https://sempkm.metacoding.io/screenshots/01-workspace-overview-dark.png` on all 4 pages
- [ ] JSON-LD `<script type="application/ld+json">` block with Organization + WebSite schema on all 4 pages
- [ ] Zero broken internal links reported by link checker
- [ ] All 4 files parse without error via HTMLParser

## Verification

- `grep -rn 'guide/20-production-deployment' docs/index.html docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html` → no output (exit code 1)
- `grep -l 'og:image.*https://sempkm.metacoding.io' docs/index.html docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html | wc -l` → 4
- `grep -l 'application/ld+json' docs/index.html docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html | wc -l` → 4
- Python link checker reports zero broken links
- HTML parser confirms all 4 files are well-formed

## Inputs

- `docs/index.html` — homepage from S01 with partial SEO tags (relative og:image, no JSON-LD)
- `docs/from-obsidian.html` — Obsidian persona page from S02 (has SEO meta tags but no og:image, no JSON-LD)
- `docs/from-notion.html` — Notion persona page from S02 (same gaps)
- `docs/fresh-start.html` — Fresh Start persona page from S02 (same gaps)
- `docs/CNAME` — contains `sempkm.metacoding.io` (domain for absolute URLs)

## Expected Output

- `docs/index.html` — fixed guide links, absolute og:image, JSON-LD added
- `docs/from-obsidian.html` — fixed guide links, og:image added, JSON-LD added
- `docs/from-notion.html` — fixed guide links, og:image added, JSON-LD added
- `docs/fresh-start.html` — fixed guide links, og:image added, JSON-LD added
