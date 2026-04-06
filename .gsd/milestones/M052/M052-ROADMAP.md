# M052: UI Design System & Polish Pass

## Vision
Establish consistent visual identity across the entire Object Browser — type-colored accents, property table polish, enriched kanban cards, improved tab distinction, and writing-surface body editor. Transform the functional-but-bland workspace into a distinctively styled product.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | Kanban Enrichment & Column Colors | medium | — | ✅ | Kanban view shows cards with priority badge, due date, and type icon. Columns have color-coded left border accents. Types without enrichment fields still render correctly. |
| S02 | Property Table & Popover Polish | low | — | ✅ | Object read view has zebra-striped property rows with hover highlight, stronger label/value distinction, and tooltips. Graph popover properties have borders and alternating backgrounds. |
| S03 | Type Badge, Tabs & Navigation Chrome | low | — | ✅ | Type badge shows Lucide icon with type color accent. Active tab is clearly distinguishable from inactive. View explorer uses Lucide icons with per-renderer colors. Body editor feels like a writing surface. |
| S04 | Forms, Timeline & Final Polish | low | S01, S02, S03 | ✅ | Form sections have prominent headers with accent bars and tighter help text. Timeline bars have status colors. Right panel shows helpful empty state. View name underline inconsistency resolved. |
