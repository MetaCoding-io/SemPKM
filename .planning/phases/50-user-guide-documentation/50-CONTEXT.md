# Phase 50: User Guide & Documentation - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Catch up the user guide (`docs/guide/`) for all features shipped since v2.0. Cover v2.2-v2.5 features with dedicated sections, update stale content in existing chapters, and capture screenshots. This is documentation-only — no application code changes.

</domain>

<decisions>
## Implementation Decisions

### Doc structure
- Integrate v2.3/v2.4 features into existing chapters, not new standalone chapters:
  - Dockview panels + named layouts → Ch 4 (Workspace Interface)
  - Object view redesign + edit form helptext → Ch 5 (Working with Objects)
  - Carousel views → Ch 7 (Browsing and Visualizing)
  - Global lint dashboard → Ch 14 (System Health and Debugging)
  - OWL inference + SHACL-AF rules → Ch 16 (The Data Model)
- New Part IX: Identity & Federation with two new chapters:
  - Ch 25: WebID Profiles
  - Ch 26: IndieAuth

### Content depth
- Task-oriented style: "how do I do X?" with steps, ~100-200 lines per feature section
- Expand existing thin pages (Ch 21 SPARQL Console: 64 lines, Ch 22 Keyword Search: 37 lines) to match
- Audience: both end-users and technical self-hosters, with clear signposting ("For Advanced Users" callouts)
- All examples use Basic PKM model (Projects, People, Notes, Concepts) — no hypothetical models

### Stale content strategy
- Rewrite outdated sections in-place (targeted surgery, not full chapter rewrites)
- Key stale areas: Ch 4 (Split.js → dockview), Ch 5 (flip card → crossfade, add markdown-first view), Ch 7 (add carousel views)
- Update both README.md (live index) and USER_GUIDE_OUTLINE.md (mark as implemented/update structure)
- Update all appendices: env vars, keyboard shortcuts, glossary, FAQ, troubleshooting
- Rewrite Ch 24 (Obsidian Onboarding, 971 lines) from scratch to match actual Phases 45-47 implementation

### Visual aids
- Include ~15-20 key screenshots across the guide
- Capture via Playwright automation (existing `e2e/` screenshots project infrastructure)
- Light mode only (default theme, prints better)
- Store as PNG in `docs/screenshots/` with descriptive names (e.g., workspace-layout.png, lint-dashboard.png)
- Reference in markdown as relative paths

### Claude's Discretion
- Exact screenshot framing and viewport sizing
- Whether to add ASCII diagrams alongside screenshots for architecture concepts
- How to structure "For Advanced Users" callout boxes (markdown blockquotes, HTML details/summary, or other)
- Ordering of new sections within existing chapters

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches within the task-oriented style.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/guide/` — 24 chapters + 6 appendices already written for v1.0/v2.0 era
- `docs/USER_GUIDE_OUTLINE.md` — detailed outline with section descriptions (490 lines)
- `docs/guide/README.md` — live table of contents with Part I-VIII + Appendices structure
- `e2e/` — Playwright test infrastructure with `screenshots` project for automated captures
- `docs/screenshots/` — existing screenshot directory (used by CNAME/index.html)

### Established Patterns
- Document conventions defined in USER_GUIDE_OUTLINE.md: `Ctrl+K` for shortcuts, **bold** for UI elements, `inline code` for paths/IRIs, Basic PKM examples throughout
- Chapter numbering: sequential, filename pattern `XX-slug.md`
- Navigation footer: `**Previous:** [link] | **Next:** [link]`
- Part grouping in README.md with numbered entries

### Integration Points
- README.md must be updated with new Part IX and any chapter additions
- Appendices cross-reference main chapters (glossary terms link back, FAQ references chapters)
- Ch 14 already mentions SPARQL Console briefly — lint dashboard docs should follow same style
- Ch 16 (Data Model) has sections on named graphs and SHACL — inference/rules extend naturally

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 50-user-guide-documentation*
*Context gathered: 2026-03-08*
