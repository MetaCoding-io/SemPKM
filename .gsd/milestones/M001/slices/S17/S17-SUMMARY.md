---
id: S17
parent: M001
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
# S17: Llm Connection Configuration

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

# Phase 17 Plan 02: SSE Streaming Proxy Endpoint Summary

**One-liner:** SSE streaming proxy endpoint POST /browser/llm/chat/stream using httpx aiter_lines passthrough, plus nginx location block with proxy_buffering off for real-time LLM response delivery.

## What Was Built

### SSE Streaming Endpoint (`backend/app/browser/router.py`)

New endpoint `POST /browser/llm/chat/stream` added to the LLM Connection Configuration section:

- Accepts JSON body `{"messages": [...], "model": "optional-override"}`
- Retrieves encrypted API key via `LLMConfigService.get_decrypted_api_key()`
- Uses `httpx.AsyncClient(timeout=300.0)` with `client.stream()` + `aiter_lines()` for upstream SSE passthrough
- Returns `StreamingResponse(media_type="text/event-stream")` with `X-Accel-Buffering: no` and `Cache-Control: no-cache` headers
- Graceful error path: when LLM is not configured, yields `data: {"error": "LLM not configured"}\n\n` + `data: [DONE]\n\n`
- Exception handler yields SSE-formatted error event so the client always receives a clean termination
- Accessible to any authenticated user via `get_current_user` (not owner-only)

The `if line:` guard skips empty keep-alive lines that some providers send, and the 300s timeout accommodates long-form LLM responses.

### nginx SSE Location Block (`frontend/nginx.conf`)

New dedicated location block added before the catch-all `location /`:

```nginx
location /browser/llm/chat/stream {
    proxy_pass http://api:8000/browser/llm/chat/stream;
    proxy_buffering off;
    proxy_http_version 1.1;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
    proxy_set_header Cache-Control "no-cache";
    proxy_set_header Connection "keep-alive";
    add_header X-Accel-Buffering "no";
    # + standard proxy headers (Host, X-Real-IP, Cookie, etc.)
}
```

Block ordering in nginx.conf:
1. `location /css/`
2. `location /js/`
3. `location = /setup.html`
4. `location = /login.html`
5. `location = /invite.html`
6. `location /api/`
7. **NEW: `location /browser/llm/chat/stream`** (line 49)
8. `location /` catch-all (line 69)

## Decisions Made

1. **aiter_lines() over aiter_bytes()** — `aiter_lines()` buffers across HTTP chunk boundaries, ensuring complete SSE lines are yielded; `aiter_bytes()` can split lines mid-chunk breaking SSE framing
2. **300s timeout** — Long LLM completions (multi-turn, large context) can take minutes; 10s would abort legitimate requests
3. **X-Accel-Buffering: no on response** — Defense-in-depth: tells nginx not to buffer even if the location block is missed or a future nginx reconfig drops it
4. **get_current_user (not require_role)** — The streaming endpoint is for end users (future AI Copilot), not admin config; owner sets config, all authenticated users consume it
5. **nginx location before catch-all** — Explicit placement is conventional best practice; avoids ambiguity even though nginx longest-prefix matching would select it anyway

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `backend/app/browser/router.py` contains `@router.post("/llm/chat/stream")`
- [x] `StreamingResponse` with `media_type="text/event-stream"` present
- [x] `aiter_lines()` used for upstream SSE passthrough
- [x] `X-Accel-Buffering: no` header on StreamingResponse
- [x] `frontend/nginx.conf` has `location /browser/llm/chat/stream` block
- [x] `proxy_buffering off` directive present in SSE location block
- [x] `proxy_read_timeout 300s` present
- [x] `proxy_http_version 1.1` present
- [x] nginx SSE block at line 49, before catch-all `location /` at line 69

## Self-Check: PASSED
