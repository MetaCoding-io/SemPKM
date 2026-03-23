# M036 Research: Business Planning Mental Models & Custom Renderers

**Researched:** 2026-03-22
**Status:** Complete

Key findings:
- `register_renderer()` is dead code — all 7 renderers are hardcoded elif branches in 1486-line view router
- Model archive pattern is well-proven (6-file structure), business-planning model would be ~2× PPV size
- Quadrant renderer can be generic and parameterized (reused by 6+ frameworks)
- BMC 9-box layout is CSS Grid with drag-between-sections (kanban variant)
- Computed fields (OKR progress, Decision Matrix scores) best done server-side for MVP
- Cross-model edges work today with no platform changes
- Recommended: single model, registry-based renderer dispatch refactoring, 6 slices
