# M054: Explorer Composable Filter/Group/Sort

## Vision
Replace the flat OBJECTS dropdown with a composable explorer where filtering, grouping, and sorting are independent stackable layers — giving users the power to define how objects are organized in the explorer tree.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | Composable Explorer with Config Builder | high | — | ✅ | User opens explorer → clicks Configure → selects type filter (Tasks), group-by (Status), sort (Due Date) → tree renders tasks grouped by status with sorted items within each group |
| S02 | Config Persistence, Multi-Panel & Presets | medium | S01 | ⬜ | User saves a named config → reloads browser → config appears in selector → clicks Duplicate → second OBJECTS section with different config appears → selects By Type preset in the original → both render independently |
