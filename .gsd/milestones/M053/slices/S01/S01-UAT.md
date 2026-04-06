# S01: Auto-Discover Bundled Models — UAT

**Milestone:** M053
**Written:** 2026-04-06T03:10:52.875Z

# S01 UAT: Auto-Discover Bundled Models

## Preconditions
- SemPKM running with Docker stack (`docker compose up -d`)
- At least one Mental Model NOT installed (e.g., fresh instance or after uninstalling a model)
- Logged in as admin user

## Test 1: Available Models Display
1. Navigate to Admin → Mental Models (`/admin/models`)
2. **Expected:** An "Available Models" section appears showing cards for each bundled model not yet installed
3. Each card shows: model name (bold), version badge (e.g., "v2.2.0"), description (truncated if long), type count, icon count
4. Cards are in a responsive grid — resize browser to verify 1→2→3 column layout

## Test 2: One-Click Install
1. On the Mental Models page, locate a model card (e.g., "Zettelkasten+")
2. Click the "Install" button on the card
3. **Expected:** The page updates (htmx swap) — the installed model appears in the installed models table AND the card disappears from the Available Models section
4. Navigate to the workspace explorer — the model's types should appear

## Test 3: Uninstall Restores Availability
1. In the installed models table, click Remove on a previously installed model
2. **Expected:** The model reappears as a card in the Available Models section after the htmx swap

## Test 4: All Models Installed State
1. Install all available bundled models
2. **Expected:** The Available Models section shows "All bundled models are installed." empty state message

## Test 5: Advanced Install Fallback
1. On the Mental Models page, look for "Install from path…" collapsed section below the available models
2. Click to expand it
3. **Expected:** The original text-input form appears with a path field and Install button
4. This form accepts arbitrary filesystem paths for models not in /app/models/

## Test 6: Malformed Model Directory Tolerance
1. (Requires filesystem access) Create a directory in /app/models/ with no manifest.yaml
2. Reload Admin → Mental Models
3. **Expected:** The page loads normally — the invalid directory is silently skipped, other models display correctly

## Edge Cases
- **No bundled models directory:** If /app/models/ doesn't exist, the Available Models section shows empty state (no crash)
- **Concurrent install:** Two browser tabs installing the same model — second install should show an error or the model already installed
