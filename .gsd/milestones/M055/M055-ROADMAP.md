# M055: Browser History & Tab Recovery

## Vision
Make the workspace URL reflect the active tab, enable browser back/forward navigation between tabs, support bookmarkable/shareable URLs, and add closed-tab recovery via Ctrl+Shift+T and command palette.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | URL Sync & History Navigation | medium | — | ⬜ | Open object A → URL shows ?tab=A → open B → URL shows ?tab=B → back → A focused → URL shows A. Paste bookmarked URL → correct object opens. |
| S02 | Closed Tab Recovery | low | — | ⬜ | Close a tab → Ctrl+Shift+T → tab reopens with same content. F1 → 'Reopen Closed Tab' → same result. |
