# Phase 50: User Guide & Documentation - Research

**Researched:** 2026-03-09
**Domain:** Technical documentation (Markdown user guide)
**Confidence:** HIGH

## Summary

Phase 50 is a documentation-only phase: no application code changes. The existing user guide at `docs/guide/` has 24 chapters plus 6 appendices written for v1.0/v2.0 era. Several chapters reference outdated UI patterns (Split.js layout, 3D flip cards) and two thin Part VIII chapters need expansion (Ch 21: 64 lines, Ch 22: 37 lines). Chapter 24 (Obsidian Onboarding, 971 lines) describes a manual Python-script workflow that has been superseded by the in-app Obsidian Import tool (Phases 45-47). Two new chapters are needed for WebID Profiles and IndieAuth (Part IX: Identity & Federation).

The project has established Playwright screenshot infrastructure (`e2e/tests/screenshots/capture.spec.ts`) with a `screenshots` project configuration that captures both light and dark variants at 1440x900 viewport. The existing 20 screenshots live in `e2e/screenshots/` and are referenced from guide chapters. New screenshots for the user guide should follow the same pattern but output to `docs/screenshots/` as specified in CONTEXT.md, using light mode only.

**Primary recommendation:** Organize work into 4 waves: (1) stale chapter updates (Ch 4, 5, 7, 8), (2) thin chapter expansion + new feature sections (Ch 14, 16, 21, 22), (3) Ch 24 rewrite + new Part IX chapters (25, 26), (4) appendix updates + README/outline sync + screenshot capture.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Integrate v2.3/v2.4 features into existing chapters, not new standalone chapters:
  - Dockview panels + named layouts -> Ch 4 (Workspace Interface)
  - Object view redesign + edit form helptext -> Ch 5 (Working with Objects)
  - Carousel views -> Ch 7 (Browsing and Visualizing)
  - Global lint dashboard -> Ch 14 (System Health and Debugging)
  - OWL inference + SHACL-AF rules -> Ch 16 (The Data Model)
- New Part IX: Identity & Federation with two new chapters:
  - Ch 25: WebID Profiles
  - Ch 26: IndieAuth
- Task-oriented style: "how do I do X?" with steps, ~100-200 lines per feature section
- Expand existing thin pages (Ch 21 SPARQL Console: 64 lines, Ch 22 Keyword Search: 37 lines) to match
- Audience: both end-users and technical self-hosters, with clear signposting ("For Advanced Users" callouts)
- All examples use Basic PKM model (Projects, People, Notes, Concepts) -- no hypothetical models
- Rewrite outdated sections in-place (targeted surgery, not full chapter rewrites)
- Key stale areas: Ch 4 (Split.js -> dockview), Ch 5 (flip card -> crossfade, add markdown-first view), Ch 7 (add carousel views)
- Update both README.md (live index) and USER_GUIDE_OUTLINE.md (mark as implemented/update structure)
- Update all appendices: env vars, keyboard shortcuts, glossary, FAQ, troubleshooting
- Rewrite Ch 24 (Obsidian Onboarding, 971 lines) from scratch to match actual Phases 45-47 implementation
- ~15-20 key screenshots via Playwright automation, light mode only, PNG in `docs/screenshots/`, relative paths in markdown
- Exact screenshot framing and viewport sizing at Claude's discretion
- Whether to add ASCII diagrams alongside screenshots at Claude's discretion
- How to structure "For Advanced Users" callout boxes at Claude's discretion
- Ordering of new sections within existing chapters at Claude's discretion

### Claude's Discretion
- Exact screenshot framing and viewport sizing
- Whether to add ASCII diagrams alongside screenshots for architecture concepts
- How to structure "For Advanced Users" callout boxes (markdown blockquotes, HTML details/summary, or other)
- Ordering of new sections within existing chapters

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DOCS-01 | User guide in `docs/` covers all features shipped since v2.0 (SPARQL console, FTS, VFS, dockview, inference, lint dashboard, helptext, Obsidian import, WebID, IndieAuth) | Chapters 4, 5, 7, 14, 16, 21, 22, 23, 24, 25, 26 identified for updates/creation |
| DOCS-02 | Each major feature has a dedicated user guide page with usage instructions | Ch 21 (SPARQL), Ch 22 (FTS), Ch 23 (VFS), Ch 24 (Obsidian Import rewrite), Ch 25 (WebID), Ch 26 (IndieAuth) -- each gets ~100-200 line dedicated coverage |
| DOCS-03 | Existing user guide pages updated to reflect current UI state (no stale references) | Ch 4 Split.js->dockview, Ch 5 flip->crossfade, Ch 7 add carousel, appendices updated |
</phase_requirements>

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Markdown | CommonMark | Documentation format | Already used throughout docs/guide/ |
| Playwright | (project version) | Screenshot automation | Existing `screenshots` project in e2e/ with proven patterns |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `e2e/fixtures/auth` | Authenticated page context for screenshots | All screenshot captures requiring login |
| `e2e/helpers/wait-for` | Wait for workspace/idle states | Screenshot captures of dynamic content |
| `e2e/fixtures/seed-data` | Seed data labels and constants | Opening specific objects for screenshots |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Playwright screenshots | Manual screenshots | Manual is faster for one-off but non-reproducible and inconsistent across themes |
| Markdown callout syntax | HTML `<details>` | Markdown blockquotes (`> **For Advanced Users:**`) are simpler and match existing doc style |

## Architecture Patterns

### Existing Documentation Structure
```
docs/
├── guide/
│   ├── README.md              # Live table of contents (Parts I-VIII + Appendices)
│   ├── 01-what-is-sempkm.md   # Chapter files (01-24 existing)
│   ├── 25-webid-profiles.md   # NEW
│   ├── 26-indieauth.md        # NEW
│   ├── appendix-a-*.md        # 6 appendices (a-f)
│   └── images/                # Chapter-specific diagrams (currently unused)
├── screenshots/               # Playwright-captured PNGs (light mode for guide)
├── USER_GUIDE_OUTLINE.md      # Master outline (490 lines, needs update)
└── README.md                  # Docs-level readme (distinct from guide/README.md)
```

### Pattern: Chapter Update (Targeted Surgery)
**What:** Update specific sections within existing chapters to reflect current UI state
**When to use:** Ch 4 (dockview), Ch 5 (crossfade + helptext), Ch 7 (carousel), Ch 14 (lint dashboard), Ch 16 (inference)
**Approach:**
1. Read current chapter content in full
2. Identify stale paragraphs referencing old patterns
3. Replace only the stale content, preserving surrounding structure
4. Add new sections for new features at appropriate positions
5. Update any screenshot references to point to new captures
6. Verify navigation footer links remain correct

### Pattern: Chapter Expansion (Thin -> Full)
**What:** Expand short placeholder chapters to full ~150-200 line coverage
**When to use:** Ch 21 (64 lines -> ~150), Ch 22 (37 lines -> ~150)
**Approach:**
1. Keep existing content as foundation
2. Add task-oriented sections: "How to...", "Example workflows"
3. Add "For Advanced Users" callouts where appropriate
4. Add screenshots showing the feature in action

### Pattern: Chapter Rewrite (Scratch)
**What:** Delete and rewrite a chapter that describes a superseded workflow
**When to use:** Ch 24 (manual Python scripts -> in-app wizard)
**Approach:**
1. Read old chapter to understand intended scope
2. Examine actual implementation (templates, routes, UI flow)
3. Write new chapter matching the implemented step-by-step wizard
4. Include screenshots of each wizard step

### Pattern: New Chapter Creation
**What:** Create new chapters for entirely new features
**When to use:** Ch 25 (WebID Profiles), Ch 26 (IndieAuth)
**Approach:**
1. Research the actual implementation (backend routes, templates, config)
2. Follow document conventions: `Ctrl+K` for shortcuts, **bold** for UI elements, `inline code` for paths
3. Include "what it is", "how to use it", "configuration", "For Advanced Users"
4. Add navigation footer: Previous/Next links
5. Register in README.md under new Part IX

### Pattern: Screenshot Capture
**What:** Automated screenshot creation via Playwright
**When to use:** All new screenshots for the guide (~15-20 total)
**Approach:**
1. Create new test file: `e2e/tests/screenshots/guide-capture.spec.ts`
2. Follow existing `capture.spec.ts` patterns (serial mode, helper functions)
3. Light mode only (per CONTEXT.md decision, unlike marketing screenshots which capture both)
4. Output to `docs/screenshots/` with descriptive names
5. Viewport: 1440x900 (consistent with existing)
6. Reference in markdown as `../screenshots/filename.png` or `screenshots/filename.png`

### Document Conventions (Established)
- **Keyboard shortcuts:** `Ctrl+K` inline code
- **UI element names:** **bold** on first mention per section
- **File paths and IRIs:** `inline code`
- **Examples:** Basic PKM model only (Projects, People, Notes, Concepts)
- **Navigation footer:** `**Previous:** [link] | **Next:** [link]`
- **Admonitions:** `> **Tip:**`, `> **Note:**`, `> **Warning:**` blockquote style

### Anti-Patterns to Avoid
- **Full chapter rewrites when surgery suffices:** Only Ch 24 warrants a full rewrite. Other chapters need targeted paragraph replacements.
- **Generic/hypothetical examples:** All examples must use Basic PKM model types and seed data.
- **Stale cross-references:** After adding Part IX and updating chapter structure, all Previous/Next links and README.md entries must be verified.
- **Dark mode screenshots in guide:** CONTEXT.md specifies light mode only for the guide (prints better). Marketing screenshots in e2e/screenshots/ have both modes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Screenshot capture | Manual screenshots | Playwright `screenshots` project | Reproducible, consistent viewport, automated |
| Markdown rendering preview | Custom tooling | Read rendered docs in-app via `/guide/` route | App already has `guide.html` + `guide_article.html` templates |
| Table of contents | Manual index | Update existing `README.md` structure | Established pattern with Part numbering |

## Common Pitfalls

### Pitfall 1: Stale Navigation Footers
**What goes wrong:** Adding/reordering chapters breaks Previous/Next links in footers
**Why it happens:** Footer links are hardcoded in each .md file, not generated
**How to avoid:** After all chapter changes, verify every footer link by reading first and last lines of each chapter file
**Warning signs:** 404 or wrong chapter when clicking Previous/Next

### Pitfall 2: Screenshot Path Confusion
**What goes wrong:** Screenshots referenced from wrong directory or with wrong relative path
**Why it happens:** Two screenshot directories exist: `e2e/screenshots/` (marketing) and `docs/screenshots/` (guide)
**How to avoid:** Guide chapters reference `../screenshots/filename.png` from `docs/guide/` or use consistent relative paths. Verify paths resolve correctly.
**Warning signs:** Broken image links in rendered markdown

### Pitfall 3: Ch 24 Rewrite Scope Creep
**What goes wrong:** Ch 24 rewrite balloons because the old chapter was 971 lines of manual Python workflow
**Why it happens:** Temptation to preserve old content alongside new
**How to avoid:** Complete scratch rewrite. The new in-app wizard (upload -> scan -> type mapping -> property mapping -> preview -> import) is the only workflow to document. Target ~200-300 lines.
**Warning signs:** Chapter exceeding 400 lines, references to Python scripts

### Pitfall 4: Missing Glossary/Appendix Updates
**What goes wrong:** New terms (WebID, IndieAuth, PKCE, carousel view, lint dashboard) introduced in chapters but not added to Glossary
**Why it happens:** Glossary updates are easy to forget
**How to avoid:** After all chapter work, scan for new technical terms and add to Appendix D
**Warning signs:** Terms used in chapters but not defined in glossary

### Pitfall 5: Outline Drift
**What goes wrong:** USER_GUIDE_OUTLINE.md and README.md get out of sync with actual chapters
**Why it happens:** Updates to chapters without corresponding updates to the outline and index
**How to avoid:** Include outline/README sync as explicit final task in last wave
**Warning signs:** Outline describes sections that don't exist or misses sections that do

## Code Examples

### Screenshot Capture Pattern (Light Mode Only)
```typescript
// Source: adapted from e2e/tests/screenshots/capture.spec.ts
import { test } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';
import path from 'path';

const GUIDE_SCREENSHOTS = path.resolve(__dirname, '../../../docs/screenshots');
const VIEWPORT = { width: 1440, height: 900 };

async function setupPage(page) {
  await page.setViewportSize(VIEWPORT);
  // Ensure light mode
  await page.evaluate(() => {
    document.documentElement.setAttribute('data-theme', 'light');
    localStorage.setItem('sempkm_theme', 'light');
  });
}

test('lint-dashboard', async ({ ownerPage: page }) => {
  await setupPage(page);
  await page.goto('/browser/lint-dashboard');
  await waitForIdle(page);
  await page.waitForTimeout(1000);
  await page.screenshot({
    path: path.join(GUIDE_SCREENSHOTS, 'lint-dashboard.png'),
    fullPage: false,
  });
});
```

### Advanced Users Callout Pattern
```markdown
> **For Advanced Users:** The SPARQL Console accepts any valid SPARQL 1.1
> SELECT query. If you are familiar with RDF, you can query across named
> graphs by specifying `GRAPH ?g { ... }` patterns. See
> [The Data Model](16-data-model.md) for the full named graph layout.
```

### New Chapter Template
```markdown
# Chapter NN: Feature Name

[2-3 paragraph introduction explaining what the feature is and why it matters]

---

## Getting Started

[Task-oriented "how to" steps]

## Configuration

[Any settings or environment variables]

## Usage

### Common Task 1
[Steps with screenshots]

### Common Task 2
[Steps with screenshots]

> **For Advanced Users:** [Technical details]

## Troubleshooting

[Common issues and solutions]

---

**Previous:** [Chapter NN-1: Title](NN-1-slug.md) | **Next:** [Chapter NN+1: Title](NN+1-slug.md)
```

## State of the Art

| Old State (docs) | Current State (app) | Impact on Docs |
|-------------------|---------------------|----------------|
| Split.js 3-column layout | Dockview panel system with named layouts | Ch 4: rewrite layout description |
| CSS 3D flip card for read/edit | Opacity crossfade toggle | Ch 5: update read/edit switching section |
| No carousel views | Carousel tab bar for multi-view browsing | Ch 7: add new section |
| No lint dashboard | Global lint dashboard page | Ch 14: add new section |
| No OWL inference UI | Entailment config + inference panel | Ch 16: add inference section |
| No edit form helptext | SHACL-driven helptext on form fields | Ch 5: add helptext section |
| Manual Python Obsidian workflow | In-app wizard: upload->scan->map->preview->import | Ch 24: complete rewrite |
| No WebID | WebID profiles with content negotiation | Ch 25: new chapter |
| No IndieAuth | IndieAuth authorization + token endpoints | Ch 26: new chapter |
| 64-line SPARQL Console doc | Full SPARQL Console with multi-tab, CodeMirror | Ch 21: expand |
| 37-line Keyword Search doc | FTS with type icons and snippets | Ch 22: expand |
| Env vars: 13 listed | New: APP_BASE_URL, CORS_ORIGINS, COOKIE_SECURE, POSTHOG_* | Appendix A: add new vars |

## Inventory of Changes Needed

### Chapters Requiring Updates (Targeted Surgery)
| Chapter | Lines | Stale Content | New Content to Add |
|---------|-------|---------------|-------------------|
| Ch 4 | 266 | Split.js references, old layout description | Dockview panels, named layouts, group management |
| Ch 5 | 260 | "flip card" references, no helptext | Crossfade toggle, markdown-first read view, SHACL helptext |
| Ch 7 | 210 | No carousel | Carousel view section |
| Ch 8 | 159 | May be missing new shortcuts | Verify all current shortcuts listed |
| Ch 14 | 337 | No lint dashboard | Global lint dashboard section |
| Ch 16 | 279 | No inference/entailment | OWL inference + SHACL-AF rules section |

### Chapters Requiring Expansion
| Chapter | Current Lines | Target Lines | Content to Add |
|---------|--------------|-------------|----------------|
| Ch 21 | 64 | ~150 | Multi-tab queries, CodeMirror features, more examples, advanced patterns |
| Ch 22 | 37 | ~150 | Search behavior details, result ranking, scope, integration with workspace |

### Chapters Requiring Rewrite
| Chapter | Current Lines | Target Lines | Reason |
|---------|--------------|-------------|--------|
| Ch 24 | 971 | ~250 | Manual Python workflow replaced by in-app wizard |

### New Chapters
| Chapter | Target Lines | Content |
|---------|-------------|---------|
| Ch 25 | ~150 | WebID Profiles: what, how to view, content negotiation, rel=me, key management |
| Ch 26 | ~150 | IndieAuth: what, consent screen, token management, developer integration |

### Appendices Requiring Updates
| Appendix | Lines | Updates Needed |
|----------|-------|---------------|
| A (Env Vars) | 76 | Add APP_BASE_URL, CORS_ORIGINS, COOKIE_SECURE, POSTHOG_* |
| B (Shortcuts) | 86 | Verify completeness against current app |
| D (Glossary) | 80 | Add: WebID, IndieAuth, PKCE, Carousel, Lint Dashboard, Entailment, Inference |
| E (Troubleshooting) | 279 | Add Obsidian import issues, WebID issues |
| F (FAQ) | 195 | Update Obsidian answer (now in-app import), add WebID/IndieAuth FAQ |

### Index Files
| File | Updates Needed |
|------|---------------|
| `docs/guide/README.md` | Add Part IX with Ch 25, 26; update appendix Previous/Next |
| `docs/USER_GUIDE_OUTLINE.md` | Add Part IX sections, mark v2.2-v2.5 features as implemented |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (via existing e2e/ infrastructure) |
| Config file | `e2e/playwright.config.ts` |
| Quick run command | `npx playwright test tests/screenshots/guide-capture.spec.ts --project=screenshots` |
| Full suite command | N/A (docs phase -- validation is content review, not test suite) |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOCS-01 | All v2.0+ features covered in guide | manual-only | N/A -- content completeness review | N/A |
| DOCS-02 | Each major feature has dedicated page | manual-only | N/A -- verify file existence and length | N/A |
| DOCS-03 | No stale references in existing pages | manual-only | `grep -r "Split.js\|flip card\|3D flip" docs/guide/` | N/A |

**Justification for manual-only:** Documentation quality cannot be automatically tested. Validation is content review: checking that chapters exist, reference correct features, contain no stale terminology, and have working navigation links. The DOCS-03 stale reference check can be partially automated with grep.

### Sampling Rate
- **Per task commit:** Verify changed files render correctly (check markdown syntax, image paths)
- **Per wave merge:** Review updated chapters for consistency and cross-references
- **Phase gate:** Full guide walkthrough, grep for stale terms, verify all navigation links

### Wave 0 Gaps
- [ ] `e2e/tests/screenshots/guide-capture.spec.ts` -- new screenshot capture spec for guide images
- [ ] `docs/screenshots/` directory may need new subdirectory or cleanup of old marketing screenshots

## Open Questions

1. **Screenshot directory overlap**
   - What we know: `e2e/screenshots/` has marketing screenshots (light+dark), `docs/screenshots/` currently has 5 old dark-only PNGs
   - What's unclear: Should guide screenshots go alongside the old marketing shots in `docs/screenshots/` or in a new subdirectory?
   - Recommendation: Put guide screenshots directly in `docs/screenshots/` with descriptive names (e.g., `guide-workspace-dockview.png`). The old 5 marketing screenshots can coexist.

2. **Obsidian import flow details**
   - What we know: In-app wizard with upload->scan->type mapping->property mapping->preview->import steps (templates confirm this)
   - What's unclear: Exact UI details of each step (need to examine templates or run the app)
   - Recommendation: Read the Obsidian templates (`obsidian/import.html` + partials) during implementation to describe the actual UI

3. **IndieAuth developer-facing docs**
   - What we know: Authorization endpoint, token endpoint, consent screen implemented
   - What's unclear: How much developer-oriented API documentation belongs in the user guide vs. being left to auto-generated API docs
   - Recommendation: Keep Ch 26 user-focused (what IndieAuth is, consent flow, managing tokens). Reference API docs for developer integration details.

## Sources

### Primary (HIGH confidence)
- Project codebase: `docs/guide/` -- all 24 chapters + 6 appendices read
- Project codebase: `e2e/tests/screenshots/capture.spec.ts` -- existing screenshot infrastructure
- Project codebase: `backend/app/templates/obsidian/` -- import wizard templates
- Project codebase: `backend/app/templates/webid/profile.html` -- WebID profile template
- Project codebase: `backend/app/templates/indieauth/` -- IndieAuth templates
- Project codebase: `backend/app/config.py` -- current env var definitions
- CONTEXT.md: User decisions and constraints
- REQUIREMENTS.md: DOCS-01, DOCS-02, DOCS-03 definitions

### Secondary (MEDIUM confidence)
- MEMORY.md: Architecture notes on crossfade vs flip, dockview behavior

## Metadata

**Confidence breakdown:**
- Documentation structure: HIGH -- based on direct reading of all existing files
- Content changes needed: HIGH -- based on comparing existing docs against implemented features
- Screenshot approach: HIGH -- existing Playwright infrastructure well-documented in codebase
- Feature details (WebID, IndieAuth, Obsidian import): MEDIUM -- templates confirm UI flow but exact behavior needs examination during implementation

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (stable -- documentation of existing features)
