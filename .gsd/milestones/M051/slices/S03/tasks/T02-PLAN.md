---
estimated_steps: 48
estimated_files: 1
skills_used: []
---

# T02: Fix admin graph popover viewport-relative positioning

## Description

The admin model ontology diagram popover (`.graph-popover`) has `position: fixed` in CSS but the positioning JS in `model_ontology_diagram.html` computes panel-relative coordinates by subtracting `panelRect`. This causes the popover to appear offset from the hovered node.

## Steps

1. Read `backend/app/templates/admin/model_ontology_diagram.html` lines 215-235 (the `showPopover` function's positioning block).

2. Fix the initial position calculation. Change:
   ```javascript
   var left = (containerRect.left - panelRect.left) + pos.x + 16;
   var top = (containerRect.top - panelRect.top) + pos.y - 12;
   ```
   To:
   ```javascript
   var left = containerRect.left + pos.x + 16;
   var top = containerRect.top + pos.y - 12;
   ```

3. Fix the right-edge overflow check. Change:
   ```javascript
   popover.style.left = ((containerRect.left - panelRect.left) + pos.x - pRect.width - 12) + 'px';
   ```
   To:
   ```javascript
   popover.style.left = (containerRect.left + pos.x - pRect.width - 12) + 'px';
   ```

4. Fix the bottom-edge overflow check. Change:
   ```javascript
   popover.style.top = ((containerRect.top - panelRect.top) + pos.y - pRect.height + 12) + 'px';
   ```
   To:
   ```javascript
   popover.style.top = (containerRect.top + pos.y - pRect.height + 12) + 'px';
   ```

5. Update the overflow boundary checks from panel bounds to viewport bounds. Change:
   ```javascript
   if (pRect.right > panelRect.right - 8) {
   ```
   To:
   ```javascript
   if (pRect.right > window.innerWidth - 8) {
   ```
   And change:
   ```javascript
   if (pRect.bottom > panelRect.bottom - 8) {
   ```
   To:
   ```javascript
   if (pRect.bottom > window.innerHeight - 8) {
   ```

6. The `panelRect` variable is no longer needed in the positioning block. It can be removed or left — the `panel` variable is still used for `panel.appendChild(popover)` earlier in the function.

7. Verify: `grep -c 'panelRect.left\|panelRect.right\|panelRect.top\|panelRect.bottom' backend/app/templates/admin/model_ontology_diagram.html` returns 0. `grep -c 'containerRect.left + pos' backend/app/templates/admin/model_ontology_diagram.html` returns at least 1.

## Inputs

- ``backend/app/templates/admin/model_ontology_diagram.html` — existing popover positioning JS`
- ``frontend/static/css/views.css` — .graph-popover has position:fixed (read-only reference, no changes needed)`

## Expected Output

- ``backend/app/templates/admin/model_ontology_diagram.html` — popover uses viewport-relative coordinates matching position:fixed CSS`

## Verification

grep -c 'panelRect\.left\|panelRect\.right\|panelRect\.top\|panelRect\.bottom' backend/app/templates/admin/model_ontology_diagram.html | grep -q '^0$' && grep -q 'containerRect.left + pos' backend/app/templates/admin/model_ontology_diagram.html && grep -q 'window.innerWidth' backend/app/templates/admin/model_ontology_diagram.html && echo 'PASS'
