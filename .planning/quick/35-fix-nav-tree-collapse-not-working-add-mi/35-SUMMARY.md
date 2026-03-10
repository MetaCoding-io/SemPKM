# Quick Task 35: Fix nav tree collapse not working

## Problem
The object browser's left nav tree allowed expanding type nodes but collapsing did not work. Clicking an expanded node toggled the `.expanded` class (rotating the chevron) but children remained visible.

## Root Cause
Missing CSS rules for `.tree-children` visibility based on parent `.tree-node` expanded state. The analogous `.view-group-node` / `.view-group-children` pattern had these rules (lines 135-141) but they were never added for the tree node variant.

## Fix
Added two CSS rules to `workspace.css` after the `.tree-children` block:

```css
.tree-node:not(.expanded) + .tree-children {
    display: none;
}

.tree-node.expanded + .tree-children {
    display: block;
}
```

This mirrors the existing `.view-group-node` pattern and uses the adjacent sibling selector (`+`) which matches the template structure (`nav_tree.html` line 23-24: `.tree-node` immediately followed by `.tree-children`).

## Files Changed
- `frontend/static/css/workspace.css` — added 8 lines (2 CSS rules)

## Commit
- `285ccd2`: fix(35): add missing CSS rules for nav tree collapse
