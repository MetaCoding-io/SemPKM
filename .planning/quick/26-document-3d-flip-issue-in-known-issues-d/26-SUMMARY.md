# Quick Task 26: Summary

**Task:** Document 3D flip issue in known-issues doc
**Date:** 2026-03-07

## What was done

Created `.planning/KNOWN-ISSUES.md` with KI-001 documenting:
- The 3D card flip (`backface-visibility: hidden`) works in the cards grid view but fails inside dockview panels
- Root cause hypothesis: dockview's `.dv-groupview` sets `overflow: hidden`, which per CSS spec flattens `transform-style: preserve-3d`
- Current workaround: 250ms opacity crossfade
- Investigation leads for future revisiting
- Note that user reports it was working previously, so the hypothesis may be incomplete
