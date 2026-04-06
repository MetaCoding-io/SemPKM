# S02: Marketplace Registry + Install-from-Cloud — UAT

**Milestone:** M053
**Written:** 2026-04-06T03:35:33.590Z

## Preconditions

- SemPKM running with Docker stack (`docker compose up -d`)
- Logged in as owner role
- At least one Mental Model already installed (e.g., basic-pkm)
- `MARKETPLACE_REGISTRY_URL` configured pointing to a valid registry.json, OR left empty to test disabled state

---

## Test Case 1: Marketplace Section Loads on Admin Page

**Steps:**
1. Navigate to Admin → Mental Models (`/admin/models`)
2. Observe page layout

**Expected:**
- Page shows existing "Available Models" section (from S01)
- Below it, a "Browse Marketplace" section appears
- If registry URL is configured: marketplace cards load via htmx lazy-load after brief "Loading marketplace…" text
- If registry URL is empty: section shows "Marketplace is not configured" or similar informational message

---

## Test Case 2: Marketplace Cards Display Correctly

**Precondition:** `MARKETPLACE_REGISTRY_URL` points to a valid registry.json with at least 2 models

**Steps:**
1. Navigate to Admin → Mental Models
2. Wait for marketplace section to load
3. Inspect card content

**Expected:**
- Each card shows: model name, version badge, description text, size badge (human-readable KB/MB), tag pills
- Cards use same visual style as "Available Models" cards (consistent `.available-model-card` grid)
- Already-installed models show "Installed" badge instead of Install button
- Non-installed models show "Install" button

---

## Test Case 3: Install Model from Marketplace

**Precondition:** Registry contains a model that is NOT currently installed

**Steps:**
1. Navigate to Admin → Mental Models
2. Find a non-installed marketplace model card
3. Click "Install" button
4. Observe loading state

**Expected:**
- Install button shows loading spinner/indicator during download
- After successful install: model appears in Installed Models table, card shows "Installed" badge
- Model types appear in workspace explorer under the new model
- Refreshing the page confirms model persists

---

## Test Case 4: SHA-256 Hash Mismatch Rejection

**Precondition:** Registry contains a model entry with an incorrect sha256 hash (e.g., manually modified registry.json)

**Steps:**
1. Attempt to install the model with mismatched hash

**Expected:**
- Installation fails with an error message mentioning hash verification
- No model files extracted to `/app/data/models/`
- Temporary download files cleaned up (no orphaned tempdirs)

---

## Test Case 5: Duplicate Install Prevention

**Precondition:** A marketplace model is already installed

**Steps:**
1. Navigate to Admin → Mental Models
2. Observe the already-installed marketplace model card

**Expected:**
- Card shows "Installed" badge, no Install button available
- If the install endpoint is called directly (e.g., via curl), it returns an error indicating the model is already installed

---

## Test Case 6: Registry Unreachable (Graceful Degradation)

**Precondition:** `MARKETPLACE_REGISTRY_URL` points to an unreachable URL (e.g., invalid domain)

**Steps:**
1. Navigate to Admin → Mental Models
2. Wait for marketplace section to load

**Expected:**
- Marketplace section shows informative error: "Marketplace unavailable" or similar
- Rest of admin page functions normally — Available Models cards and Installed Models table unaffected
- No server crash, no 500 error on the page
- Page remains interactive

---

## Test Case 7: Tar Archive Security (Path Traversal)

**Verified by unit tests — manual verification optional**

**Steps:**
1. Run `cd backend && .venv/bin/python -m pytest tests/test_tar_validator.py -v`

**Expected:**
- 33 tests pass
- Path traversal (`../../etc/passwd`) rejected with ValueError
- Absolute paths (`/etc/passwd`) rejected
- Symlinks and hardlinks rejected
- Oversized archives rejected
- Archives exceeding file count limit rejected

---

## Test Case 8: Model Path Resolution After Marketplace Install

**Precondition:** A model installed from marketplace (lives in `/app/data/models/`)

**Steps:**
1. Navigate to workspace, select a type from the marketplace model
2. Create an object of that type
3. Admin → Mental Models → click Refresh Artifacts on the marketplace model
4. Check that model icons appear in workspace explorer

**Expected:**
- Object creation works (forms render from SHACL shapes)
- Refresh artifacts succeeds (finds model dir via resolve_model_dir in /app/data/models/)
- Icons load correctly (IconService scans both /app/models/ and /app/data/models/)
- Entailment defaults load for the model (admin detail page shows correct toggles)

---

## Edge Cases

- **Empty registry:** registry.json with `{"models": []}` → Marketplace section loads but shows no cards (or "No models available" message)
- **Very large archive:** Archive exceeding 2048 MB uncompressed → rejected by tar_validator before extraction
- **Slow registry:** Registry taking >5s to respond → timeout, empty catalog returned, informative error shown
- **Concurrent installs:** Two users clicking Install on different models simultaneously → each gets its own tempdir, no interference
