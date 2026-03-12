---
id: T01
parent: S17
milestone: M001
provides: []
requires: []
affects: []
key_files: []
key_decisions: []
patterns_established: []
observability_surfaces: []
drill_down_paths: []
duration: 
verification_result: passed
completed_at: 
blocker_discovered: false
---
# T01: 17-llm-connection-configuration 01

**# Phase 17 Plan 01: LLM Connection Configuration Summary**

## What Happened

# Phase 17 Plan 01: LLM Connection Configuration Summary

**One-liner:** Fernet-encrypted LLM API key storage with PBKDF2-derived key, owner-only Settings UI with masked key field, and three browser endpoints for config save, connection test, and model fetch.

## What Was Built

### LLMConfigService (`backend/app/services/llm.py`)

Full service for managing LLM connection configuration stored as InstanceConfig key-value rows:

- `encrypt_api_key` / `decrypt_api_key` — Fernet symmetric encryption using a PBKDF2-derived key from the application's `secret_key`
- `LLMConfigService.get_config` — returns `{api_base_url, api_key_set: bool, default_model}` — never the key value
- `LLMConfigService.save_config` — upserts config values, encrypts API key before storage, skips empty strings
- `LLMConfigService.get_decrypted_api_key` — for internal server use only (test/models endpoints)

The PBKDF2 key derivation uses SHA256, 32-byte output, 100K iterations, with a fixed application-level salt `b"sempkm-llm-config-v1"`. The fixed salt is acceptable because the `secret_key` is already high-entropy.

### Three new browser endpoints (`backend/app/browser/router.py`)

- `PUT /browser/llm/config` — owner-only, saves a single field by name (api_base_url, api_key, default_model)
- `POST /browser/llm/test` — owner-only, calls `GET {base_url}/v1/models` via httpx, returns inline HTML badge fragment
- `POST /browser/llm/models` — owner-only, fetches model list from provider and returns select/input HTML fragment

Both modified existing endpoints:
- `GET /browser/settings` — now loads `llm_config` for owners and passes `user` to template
- `GET /browser/settings/data` — now pops `llm.api_key` before returning JSON (security: never expose encrypted key to browser)

### Settings UI templates

- `_llm_settings.html` — owner-only partial with API base URL text input, password field with "Set" badge when key is present, default model row with Fetch Models button, Test Connection button with htmx indicator
- `llm/test_result.html` — inline badge fragment (ok=green check, error=red x) with Lucide icon re-init script
- `llm/models_select.html` — `<select>` populated from provider models, falls back to text input on error/empty

`settings_page.html` updated with conditional `{% if llm_config is not none %}` blocks for sidebar nav button and detail panel.

`settings.css` extended with `.settings-action-row`, `.settings-action-btn`, `.settings-action-btn--primary`, `.llm-status-badge`, `.llm-status-badge--ok`, `.llm-status-badge--error`.

## Decisions Made

1. **PBKDF2 fixed salt** — Using `b"sempkm-llm-config-v1"` as fixed salt because `secret_key` entropy is already high; stability (config survives restarts) matters more than additional salt entropy
2. **Empty api_key skip** — `save_config` ignores empty string `api_key` to prevent accidentally clearing an existing key when the placeholder is displayed
3. **Owner-only guards** — All three LLM write endpoints use `require_role("owner")` since LLM config is instance-wide admin configuration
4. **api_key_set bool** — `get_config` returns `api_key_set: bool` not the key value; `settings/data` strips `llm.api_key` from response as defense-in-depth
5. **Debounced 600ms client saves** — `llmSettingChanged()` uses `setTimeout(600)` matching the plan spec; no form submission, pure `fetch PUT`

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `backend/app/services/llm.py` created
- [x] `backend/app/templates/browser/_llm_settings.html` created
- [x] `backend/app/templates/browser/llm/test_result.html` created
- [x] `backend/app/templates/browser/llm/models_select.html` created
- [x] `backend/pyproject.toml` contains `cryptography>=43.0`
- [x] `browser/router.py` contains PUT /llm/config, POST /llm/test, POST /llm/models
- [x] `settings_data` pops `llm.api_key`
- [x] `settings_page.html` includes LLM Connection category conditional on `llm_config is not none`
- [x] Fernet encrypt/decrypt roundtrip verified in isolation

## Self-Check: PASSED
