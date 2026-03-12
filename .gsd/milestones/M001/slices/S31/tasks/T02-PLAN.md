# T02: 31-object-view-redesign 02

**Slice:** S31 — **Milestone:** M001

## Description

Human verification of the object view redesign. Confirm body-first layout, properties toggle, localStorage persistence, empty-body behavior, edit mode layout, and 3D flip animation all work correctly in the browser.

Purpose: Visual and functional verification that cannot be done through automated testing alone — CSS transitions, layout correctness, animation integrity.
Output: Verified phase completion or bug list for gap closure.

## Must-Haves

- [ ] "Opening any object tab shows the rendered Markdown body immediately without properties visible"
- [ ] "User clicks a 'N properties' toggle badge and the full property list expands inline without a page reload"
- [ ] "User collapses properties, reloads the page, and reopens the same object — properties remain collapsed"
- [ ] "The existing CSS 3D flip to edit mode is unaffected and still reachable from the view header"
