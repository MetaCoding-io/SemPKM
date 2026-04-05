# M050: View System Rework

## Vision
Fix the view toolbar UX — replace the 37-pill type bar with a smart dropdown filtered by renderer compatibility, remove the confusing View Variants concept, fix calendar dark mode nav icons, add timeline popover dismiss, and repair the save/restore view flow.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | Smart Type Dropdown | high | — | ✅ | Open Kanban View → type dropdown shows only types with status fields. Open Table View → shows all types. No more 37-pill bar. |
| S02 | Toolbar Cleanup + View Polish | low | S01 | ✅ | View toolbar is clean — no View Variants dropdown. Calendar dark mode shows visible nav buttons. Timeline popover dismisses on Escape/click-outside. |
| S03 | Save/Restore Flow + E2E Tests | medium | S01, S02 | ⬜ | Save a view with type filter and scope query → find it in Saved Views sidebar → click to open → same type filter and scope are restored. E2E tests pass. |
