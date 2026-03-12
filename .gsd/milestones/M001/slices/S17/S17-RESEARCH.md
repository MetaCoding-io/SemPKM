# Phase 17: LLM Connection Configuration - Research

**Researched:** 2026-02-24
**Domain:** API key encryption, OpenAI-compatible LLM proxy, FastAPI SSE streaming, nginx SSE configuration
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LLM-01 | Admin can configure a generic OpenAI-compatible LLM connection (API base URL, API key, default model) via the Settings page under an LLM Connection category | Settings system (Phase 15) is wired; adding `llm.api_base_url`, `llm.api_key`, and `llm.default_model` as new `SettingDefinition` entries in `SettingsService.SYSTEM_SETTINGS` under a new `"LLM Connection"` category. API key field uses a custom `"masked-text"` input type in the settings template to display a masked placeholder after save instead of the raw value. |
| LLM-02 | API keys are stored server-side only (encrypted in database), never exposed to the browser; the settings UI shows a masked key after save | The `user_settings` table already stores values server-side. Encryption via `cryptography.fernet.Fernet` applied at the `SettingsService.set_override()` layer for keys matching `llm.api_key`. The settings page template never renders the actual key value — it renders a masked placeholder string (`"••••••••"`) if the key is set. The GET `/browser/settings/data` JSON endpoint strips `llm.api_key` from the response entirely. |
| LLM-03 | A "Test Connection" button validates the configured endpoint and displays connection status | New FastAPI endpoint `POST /browser/llm/test` — reads the stored (decrypted) API key and base URL from `InstanceConfig` (not `user_settings`, since LLM config is instance-wide), makes an HTTP GET to `{base_url}/v1/models` using `httpx.AsyncClient`, and returns an HTML fragment with a status badge (success/failure). |
| LLM-04 | A "Fetch Models" button retrieves and populates available models from the provider | New FastAPI endpoint `POST /browser/llm/models` — similar to test, calls `{base_url}/v1/models`, parses the `data[].id` list, returns an HTML partial that populates a `<select>` element for the default model setting. |
| LLM-05 | Backend provides a streaming proxy endpoint (SSE) for LLM chat completions with proper nginx configuration (proxy_buffering off, increased read timeout) | New FastAPI endpoint `POST /browser/llm/chat/stream` — receives messages array, fetches encrypted API key from `InstanceConfig`, uses `httpx.AsyncClient` with `stream=True` to proxy the SSE chunks from `{base_url}/v1/chat/completions?stream=true`, yields them via `StreamingResponse(media_type="text/event-stream")`. `nginx.conf` gets a new `/browser/llm/chat/stream` location block with `proxy_buffering off`, `proxy_read_timeout 300s`, and `X-Accel-Buffering: no` header. |
</phase_requirements>

---

## Summary

Phase 17 builds on the Phase 15 settings system to add an LLM connection configuration category. It has three distinct implementation concerns: (1) secure API key storage using Fernet symmetric encryption on top of the existing `InstanceConfig` SQL table, (2) validation and model-fetch UI using standard `httpx.AsyncClient` HTTP calls to an OpenAI-compatible `/v1/models` endpoint, and (3) a streaming proxy endpoint using `FastAPI.StreamingResponse` with `httpx` streaming to forward SSE chunks from the LLM provider to the browser, with nginx configured to not buffer the response.

The key architectural decision is **where to store LLM config**: it is instance-wide (shared by all users), so it belongs in `InstanceConfig` (the existing key-value table) rather than `user_settings` (which is per-user). Only the owner role should be able to configure it (matching other admin actions). The API key encryption uses `cryptography.Fernet` with the Fernet key derived from the existing `settings.secret_key` via PBKDF2. This avoids adding a new secret to manage — the same application secret that protects session tokens also protects the LLM API key.

The Settings page UI already exists and has the infrastructure for custom input types. The LLM config section needs a custom `"masked-text"` display for the API key input (show `"••••••••"` after save, allow re-entry), plus two action buttons ("Test Connection" and "Fetch Models") that are outside the standard settings row pattern and need inline htmx calls. The streaming proxy endpoint (LLM-05) is primarily a foundation for the future AI Copilot feature (v2.1) but must work correctly with nginx's proxy buffering disabled.

**Primary recommendation:** Store LLM config in `InstanceConfig` (instance-wide, owner-only), encrypt the API key with Fernet derived from `secret_key`, add a `"LLM Connection"` category to `SettingsService`, and use `httpx.AsyncClient` for both the test/fetch endpoints and the streaming proxy.

---

## Standard Stack

### Core (already in project — no new installs except `cryptography`)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `cryptography` | latest (pypi) | `Fernet` symmetric encryption for API key at rest | The `pyca/cryptography` library is the Python standard for field-level encryption; Fernet provides authenticated symmetric encryption with one-function API |
| `httpx` | current (already in project) | Async HTTP client for test/fetch/proxy calls to LLM provider | Already used in `triplestore/client.py` and `main.py`; supports `async with client.stream(...)` for SSE proxy |
| `FastAPI StreamingResponse` | current (already in project) | SSE streaming endpoint | Already in `fastapi` package; `StreamingResponse(generator, media_type="text/event-stream")` |
| `InstanceConfig` ORM model | current (already in project) | Instance-wide key-value store for LLM config | Already the pattern for instance-level config; LLM config is instance-wide, not per-user |
| `SettingsService` | current (already in project) | Expose LLM config fields in Settings page UI | Extend `SYSTEM_SETTINGS` dict with LLM category settings |
| `settings.secret_key` | current (already in project) | Fernet key derivation via PBKDF2 | Already loaded via `pydantic_settings`; avoid adding a second secret |

### Supporting (no install needed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `base64`, `os`, `hashlib` | stdlib | PBKDF2 for Fernet key derivation | When deriving Fernet key from `secret_key` string |
| `cryptography.hazmat.primitives.kdf.pbkdf2.PBKDF2HMAC` | part of `cryptography` | Key derivation from string secret | Used once at startup to derive the Fernet key |
| `fastapi.responses.StreamingResponse` | part of fastapi | SSE streaming response | LLM-05 streaming proxy endpoint |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `cryptography.Fernet` | AES-GCM via `cryptography.hazmat` | Fernet is simpler and includes authentication; hazmat gives more control but requires manual MAC |
| `cryptography.Fernet` | Store plaintext in `InstanceConfig` | Plaintext is simpler but violates LLM-02 (never exposed to browser is not enough — at-rest encryption is also required per the requirement wording) |
| Fernet key from `secret_key` PBKDF2 | Separate `LLM_ENCRYPTION_KEY` env var | PBKDF2 avoids adding a new secret; the tradeoff is that rotating `secret_key` also invalidates the stored API key |
| `InstanceConfig` | `user_settings` with a fixed user | `InstanceConfig` is the correct table for instance-wide config; `user_settings` is per-user by design |
| `httpx.AsyncClient` streaming | `openai` Python SDK | The OpenAI SDK adds a dependency and is OpenAI-specific; `httpx` is already in the project and works with any OpenAI-compatible base URL |

**Installation:**
```bash
# In backend/pyproject.toml, add:
"cryptography>=43.0",
# Then run:
uv add cryptography
```

---

## Architecture Patterns

### Recommended Project Structure additions

```
backend/app/
├── services/
│   └── llm.py              # NEW: LLMConfigService (encrypt/decrypt, test, fetch models)
├── auth/
│   └── models.py           # UNCHANGED: InstanceConfig already has key/value/updated_at
├── browser/
│   └── router.py           # EXTEND: /browser/llm/* endpoints (test, models, stream)
├── templates/browser/
│   └── settings_page.html  # EXTEND: LLM Connection category with masked key + action buttons
│   └── _setting_input.html # EXTEND: new "masked-text" input type for API key
├── templates/browser/llm/
│   └── test_result.html    # NEW: inline status badge fragment for Test Connection result
│   └── models_select.html  # NEW: <select> fragment for Fetch Models result
└── migrations/versions/
    └── 003_llm_config.py   # NEW (optional): if InstanceConfig needs index additions
                            #   (likely NOT needed — InstanceConfig already exists)

config/
└── nginx.conf              # EXTEND: add SSE location block for /browser/llm/chat/stream
```

**Important:** No new migration is needed unless the `InstanceConfig` table needs changes. The existing table schema (`key`, `value`, `updated_at`) is sufficient. The `003_llm_config.py` migration is only needed if a new table is added — which it is NOT in this phase. So: **no migration needed**.

### Pattern 1: LLM Config Storage in InstanceConfig

LLM configuration is instance-wide (shared across all users), owned by the instance admin. Use `InstanceConfig` keys:

```python
# LLM config keys in InstanceConfig
LLM_API_BASE_URL_KEY = "llm.api_base_url"
LLM_API_KEY_KEY      = "llm.api_key"         # stored as Fernet-encrypted ciphertext
LLM_DEFAULT_MODEL_KEY = "llm.default_model"
```

Never use `user_settings` for these — they are not per-user overrides but instance-wide system configuration.

### Pattern 2: Fernet Encryption via PBKDF2 from secret_key

```python
# backend/app/services/llm.py
import base64
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# Fixed salt for LLM key derivation (not secret, but stable)
# Using a fixed salt means the same secret_key always produces the same Fernet key.
# This is acceptable because we're deriving from an already-secret application key.
_LLM_KDF_SALT = b"sempkm-llm-config-v1"

def _get_fernet(secret_key: str) -> Fernet:
    """Derive a Fernet key from the application secret key."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_LLM_KDF_SALT,
        iterations=100_000,   # lower than password KDF; secret_key is already high entropy
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
    return Fernet(key)


def encrypt_api_key(api_key: str, secret_key: str) -> str:
    """Encrypt an API key string, returning a base64 Fernet token string."""
    f = _get_fernet(secret_key)
    return f.encrypt(api_key.encode()).decode()


def decrypt_api_key(ciphertext: str, secret_key: str) -> str | None:
    """Decrypt a Fernet token. Returns None on failure (wrong key, corrupted data)."""
    f = _get_fernet(secret_key)
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        return None
```

**Why fixed salt is acceptable here:** `secret_key` is a high-entropy randomly generated application secret (already derived via `load_or_create_setup_token` logic). Using a fixed salt for key derivation from a high-entropy secret is standard practice — it provides deterministic key recovery without needing to store/manage an additional random salt.

### Pattern 3: LLMConfigService

```python
# backend/app/services/llm.py

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.models import InstanceConfig
from app.config import settings as app_settings

LLM_API_BASE_URL_KEY = "llm.api_base_url"
LLM_API_KEY_KEY = "llm.api_key"
LLM_DEFAULT_MODEL_KEY = "llm.default_model"


class LLMConfigService:
    """Manages LLM connection configuration stored in InstanceConfig.

    API keys are stored encrypted using Fernet symmetric encryption
    derived from the application secret_key.
    """

    async def get_config(self, db: AsyncSession) -> dict[str, str]:
        """Return LLM config with api_key as masked string (for UI display)."""
        result = await db.execute(
            select(InstanceConfig).where(
                InstanceConfig.key.in_([
                    LLM_API_BASE_URL_KEY,
                    LLM_API_KEY_KEY,
                    LLM_DEFAULT_MODEL_KEY,
                ])
            )
        )
        rows = {row.key: row.value for row in result.scalars()}
        return {
            "api_base_url": rows.get(LLM_API_BASE_URL_KEY, ""),
            "api_key_set": bool(rows.get(LLM_API_KEY_KEY)),  # boolean, not the value
            "default_model": rows.get(LLM_DEFAULT_MODEL_KEY, ""),
        }

    async def save_config(
        self,
        db: AsyncSession,
        api_base_url: str | None = None,
        api_key: str | None = None,   # plaintext; will be encrypted before storage
        default_model: str | None = None,
    ) -> None:
        """Upsert LLM config values. Pass None to skip updating a field."""
        updates: list[tuple[str, str]] = []
        if api_base_url is not None:
            updates.append((LLM_API_BASE_URL_KEY, api_base_url))
        if api_key is not None:
            encrypted = encrypt_api_key(api_key, app_settings.secret_key)
            updates.append((LLM_API_KEY_KEY, encrypted))
        if default_model is not None:
            updates.append((LLM_DEFAULT_MODEL_KEY, default_model))

        for key, value in updates:
            existing = await db.execute(
                select(InstanceConfig).where(InstanceConfig.key == key)
            )
            row = existing.scalar_one_or_none()
            if row:
                row.value = value
            else:
                db.add(InstanceConfig(key=key, value=value))
        await db.commit()

    async def get_decrypted_api_key(self, db: AsyncSession) -> str | None:
        """Return the decrypted API key. Returns None if not set or decryption fails."""
        result = await db.execute(
            select(InstanceConfig).where(InstanceConfig.key == LLM_API_KEY_KEY)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return decrypt_api_key(row.value, app_settings.secret_key)
```

### Pattern 4: SettingsService Extension for LLM Category

The `LLM Connection` category settings are added to `SettingsService.SYSTEM_SETTINGS`. However, these settings need special UI handling:
- `llm.api_base_url` and `llm.default_model` use the standard text and select input types
- `llm.api_key` uses `input_type="masked-text"` (a new type) — renders a password-style input that masks the current value with `"••••••••"` placeholder when set

The LLM settings values **are NOT stored in `user_settings`**. They are stored in `InstanceConfig` via `LLMConfigService`. This means:
- `SettingsService.resolve()` still includes `llm.*` keys in its output, but with special handling: `llm.api_key` never appears in the resolved dict (the JSON API never exposes it)
- The settings page template renders the `LLM Connection` category differently, using a special template partial `_llm_settings.html` rather than the standard `_setting_input.html` loop

**Design choice:** Render the LLM Connection section as a dedicated partial within `settings_page.html`, passing the `llm_config_set` dict from the route handler (which contains `api_key_set: bool`, `api_base_url: str`, `default_model: str`). This avoids forcing the encrypted API key through the normal settings machinery.

### Pattern 5: Settings Page UI for LLM Connection

The LLM Connection category needs non-standard UI elements:
1. **API Base URL** — standard text input, stored in `InstanceConfig`
2. **API Key** — password-style input, shows `"••••••••"` when set; htmx `PUT /browser/llm/config` to save
3. **Default Model** — text input OR dynamically populated `<select>` after "Fetch Models"
4. **Test Connection** button — `hx-post="/browser/llm/test"` → replaces `#llm-test-status` with a status badge
5. **Fetch Models** button — `hx-post="/browser/llm/models"` → replaces `#llm-model-select` with a `<select>` populated from the API

```html
<!-- _llm_settings.html partial -->
<div class="settings-row" data-key="llm.api_base_url" data-search="llm base url endpoint">
  <div class="settings-row-info">
    <span class="settings-label">API Base URL</span>
    <span class="settings-description">Base URL for OpenAI-compatible provider (e.g. https://api.openai.com or http://localhost:11434)</span>
  </div>
  <div class="settings-row-control">
    <input type="text" class="settings-text-input" id="llm-api-base-url"
           value="{{ llm_config.api_base_url }}"
           placeholder="https://api.openai.com"
           oninput="llmSettingChanged('api_base_url', this.value)">
  </div>
</div>

<div class="settings-row" data-key="llm.api_key" data-search="llm api key secret">
  <div class="settings-row-info">
    <span class="settings-label">API Key</span>
    <span class="settings-description">Stored encrypted server-side. Never sent to the browser after save.</span>
  </div>
  <div class="settings-row-control">
    <input type="password" class="settings-text-input" id="llm-api-key"
           placeholder="{{ '••••••••' if llm_config.api_key_set else 'Enter API key' }}"
           autocomplete="new-password"
           oninput="llmSettingChanged('api_key', this.value)">
    {% if llm_config.api_key_set %}
    <span class="settings-modified-badge">Set</span>
    {% endif %}
  </div>
</div>

<div class="settings-row" data-key="llm.default_model" data-search="llm model default">
  <div class="settings-row-info">
    <span class="settings-label">Default Model</span>
    <span class="settings-description">Model identifier to use for LLM requests.</span>
  </div>
  <div class="settings-row-control">
    <div id="llm-model-select">
      <input type="text" class="settings-text-input" id="llm-default-model"
             value="{{ llm_config.default_model }}"
             placeholder="e.g. gpt-4o or llama3"
             oninput="llmSettingChanged('default_model', this.value)">
    </div>
    <button class="settings-action-btn"
            hx-post="/browser/llm/models"
            hx-target="#llm-model-select"
            hx-swap="innerHTML">
      <i data-lucide="refresh-cw" style="width:14px;height:14px;"></i>
      Fetch Models
    </button>
  </div>
</div>

<!-- Action row: Test Connection -->
<div class="settings-action-row">
  <button class="settings-action-btn settings-action-btn--primary"
          hx-post="/browser/llm/test"
          hx-target="#llm-test-status"
          hx-swap="innerHTML"
          hx-indicator="#llm-test-spinner">
    <i data-lucide="plug" style="width:14px;height:14px;"></i>
    Test Connection
  </button>
  <span class="htmx-indicator" id="llm-test-spinner">
    <i data-lucide="loader-2" style="width:14px;height:14px;" class="spin"></i>
    Testing...
  </span>
  <span id="llm-test-status"></span>
</div>

<script>
(function () {
  // Debounced save for LLM config fields
  var _pending = {};
  window.llmSettingChanged = function (field, value) {
    clearTimeout(_pending[field]);
    _pending[field] = setTimeout(function () {
      fetch('/browser/llm/config', {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field: field, value: value })
      });
    }, 600);  // 600ms debounce -- avoids hitting the API on every keystroke
  };
})();
</script>
```

**VS Code pattern note:** VS Code uses masked key field with inline status. The `input type="password"` with a placeholder of `"••••••••"` when already set mimics VS Code's approach — user knows a value is present, can type a new one to replace it.

### Pattern 6: FastAPI LLM Endpoints

```python
# In browser/router.py (new section)

@router.put("/llm/config")
async def save_llm_config(
    request: Request,
    user: User = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db_session),
):
    """Save LLM configuration. Owner only — instance-wide setting."""
    from app.services.llm import LLMConfigService
    body = await request.json()
    field = body.get("field")
    value = str(body.get("value", ""))
    svc = LLMConfigService()
    kwargs = {field: value} if field in ("api_base_url", "api_key", "default_model") else {}
    if kwargs:
        await svc.save_config(db, **kwargs)
    return JSONResponse(content={"ok": True})


@router.post("/llm/test")
async def test_llm_connection(
    request: Request,
    user: User = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db_session),
):
    """Test the configured LLM connection by calling /v1/models."""
    import httpx
    from app.services.llm import LLMConfigService
    templates = request.app.state.templates
    svc = LLMConfigService()
    config = await svc.get_config(db)
    api_key = await svc.get_decrypted_api_key(db)
    base_url = config["api_base_url"].rstrip("/")

    if not base_url:
        return templates.TemplateResponse(request, "browser/llm/test_result.html",
            {"status": "error", "message": "No API base URL configured."})

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base_url}/v1/models", headers=headers)
        if resp.status_code == 200:
            return templates.TemplateResponse(request, "browser/llm/test_result.html",
                {"request": request, "status": "ok", "message": "Connection successful"})
        else:
            return templates.TemplateResponse(request, "browser/llm/test_result.html",
                {"request": request, "status": "error",
                 "message": f"HTTP {resp.status_code}: {resp.text[:200]}"})
    except httpx.TimeoutException:
        return templates.TemplateResponse(request, "browser/llm/test_result.html",
            {"request": request, "status": "error", "message": "Connection timed out"})
    except Exception as e:
        return templates.TemplateResponse(request, "browser/llm/test_result.html",
            {"request": request, "status": "error", "message": str(e)[:200]})


@router.post("/llm/models")
async def fetch_llm_models(
    request: Request,
    user: User = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db_session),
):
    """Fetch available models from the configured LLM provider."""
    import httpx
    from app.services.llm import LLMConfigService
    templates = request.app.state.templates
    svc = LLMConfigService()
    config = await svc.get_config(db)
    api_key = await svc.get_decrypted_api_key(db)
    base_url = config["api_base_url"].rstrip("/")
    current_model = config["default_model"]

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    models: list[str] = []
    error: str | None = None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base_url}/v1/models", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            models = sorted([m["id"] for m in data.get("data", [])])
        else:
            error = f"HTTP {resp.status_code}"
    except Exception as e:
        error = str(e)[:200]

    return templates.TemplateResponse(request, "browser/llm/models_select.html", {
        "request": request, "models": models, "current_model": current_model, "error": error,
    })


@router.post("/llm/chat/stream")
async def llm_chat_stream(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Streaming proxy for LLM chat completions (SSE).

    Receives a JSON body: {"messages": [...], "model": "..."}
    Proxies to the configured LLM provider with streaming enabled.
    Returns a text/event-stream response.
    """
    import httpx
    from fastapi.responses import StreamingResponse
    from app.services.llm import LLMConfigService

    svc = LLMConfigService()
    config = await svc.get_config(db)
    api_key = await svc.get_decrypted_api_key(db)
    base_url = config["api_base_url"].rstrip("/")

    body = await request.json()
    messages = body.get("messages", [])
    model = body.get("model") or config["default_model"]

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    headers["Content-Type"] = "application/json"

    payload = {"model": model, "messages": messages, "stream": True}

    async def event_stream():
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            yield f"{line}\n\n"
        except Exception as e:
            yield f"data: {{\"error\": \"{str(e)[:100]}\"}}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

### Pattern 7: nginx SSE Configuration

Add a dedicated location block for the streaming endpoint in `frontend/nginx.conf`:

```nginx
# LLM Streaming Proxy - disable buffering for SSE
location /browser/llm/chat/stream {
    proxy_pass http://api:8000/browser/llm/chat/stream;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Cookie $http_cookie;
    proxy_pass_header Set-Cookie;

    # SSE-specific: disable buffering and increase timeout
    proxy_buffering off;
    proxy_http_version 1.1;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
    proxy_set_header Cache-Control "no-cache";
    proxy_set_header Connection "keep-alive";
    add_header X-Accel-Buffering "no";
}
```

This location must be placed **before** the catch-all `location /` block in nginx.conf (nginx uses first-match for location blocks).

### Pattern 8: Settings Page Route Handler Extension

The `settings_page` route in `browser/router.py` must be extended to pass `llm_config` context:

```python
@router.get("/settings")
async def settings_page(
    request: Request,
    user: User = Depends(require_role("owner")),  # NOTE: restrict to owner for LLM config
    # ... existing deps ...
    db: AsyncSession = Depends(get_db_session),
):
    # ... existing settings resolution ...
    from app.services.llm import LLMConfigService
    llm_svc = LLMConfigService()
    llm_config = await llm_svc.get_config(db)

    return templates.TemplateResponse(request, "browser/settings_page.html", {
        # ... existing context ...
        "llm_config": llm_config,
        "user": user,
    })
```

**Important:** The current `settings_page` route uses `get_current_user` (any authenticated user). Since LLM config is owner-only, consider: (a) restricting the whole settings page to owners, or (b) rendering the LLM Connection category conditionally based on `user.role`. Option (b) is better UX — non-owners can still access their personal settings but cannot see/edit LLM config.

### Pattern 9: `settings.js` Extension for LLM

The `/browser/settings/data` JSON endpoint must NOT return `llm.api_key` in its response — the key must never be exposed to the browser. Modify `settings_data` endpoint to strip LLM key fields:

```python
@router.get("/settings/data")
async def settings_data(
    user: User = Depends(get_current_user),
    settings_svc: SettingsService = Depends(get_settings_service),
    db: AsyncSession = Depends(get_db_session),
):
    resolved = await settings_svc.resolve(user.id, db)
    # Never expose the encrypted API key to the browser
    resolved.pop("llm.api_key", None)
    return JSONResponse(content=resolved)
```

### Anti-Patterns to Avoid

- **Storing LLM config in `user_settings`:** LLM connection is instance-wide, not per-user. Using `user_settings` would mean the LLM config is per-user and different users could set different LLM providers. Use `InstanceConfig`.
- **Exposing plaintext API key in any response:** The `get_config()` method returns `api_key_set: bool`, never the key value itself. The `/browser/settings/data` endpoint explicitly pops `llm.api_key` before returning JSON.
- **Putting the LLM Connection category in `SYSTEM_SETTINGS` with `user_settings` CRUD:** LLM settings need special save endpoints (`PUT /browser/llm/config`) that go through `LLMConfigService` → `InstanceConfig`, not through the `SettingsService.set_override()` → `user_settings` path.
- **Buffered streaming in nginx:** Without `proxy_buffering off`, nginx will buffer the SSE stream and the browser will see no output until the buffer fills or the connection closes. This breaks streaming entirely.
- **Using `proxy_pass` in the standard location `/` for SSE:** The catch-all location already proxies to FastAPI correctly, but it does NOT disable buffering. The dedicated `/browser/llm/chat/stream` location block must come first.
- **Deriving Fernet key without fixed iteration count:** The `PBKDF2HMAC` derivation must use a fixed iteration count (100_000 is appropriate when deriving from a high-entropy key — not a user password). Do not use `iterations=1_200_000` (appropriate for passwords) — it's unnecessary overhead for a machine secret.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Symmetric encryption | XOR, AES manual | `cryptography.Fernet` | Fernet = AES-128-CBC + HMAC-SHA256 + IV; handles padding, authentication, IV correctly |
| LLM API client | Custom HTTP parsing | `httpx.AsyncClient` | Already in project; supports async streaming via `client.stream()` |
| SSE parsing of upstream | Custom line splitter | `response.aiter_lines()` (httpx) | httpx's `aiter_lines()` correctly handles chunked transfer encoding and line buffering |
| API key masking UI | Custom JS obfuscation | `input type="password"` + `placeholder="••••••••"` | Browser-native password masking; no JS needed |
| OpenAI SDK | — | Don't add it | `httpx` handles the OpenAI-compatible REST API directly; the SDK adds a large dependency for what is essentially just HTTP + JSON |

---

## Common Pitfalls

### Pitfall 1: LLM API Key Appears in Browser Dev Tools
**What goes wrong:** The API key is included in a JSON response (e.g., `/browser/settings/data`) and visible in browser dev tools Network tab.
**Why it happens:** `SettingsService.resolve()` might include `llm.api_key` from `InstanceConfig` if wired carelessly.
**How to avoid:** `LLMConfigService.get_config()` returns `api_key_set: bool` (never the value). The `settings_data` endpoint explicitly pops `llm.api_key`. The settings page template renders a password input with placeholder — it never sets `value=` on the key field.
**Warning signs:** Any `llm.api_key` appearing in a JSON response body.

### Pitfall 2: secret_key is Empty String on First Boot
**What goes wrong:** `settings.secret_key` is `""` (the default) when the app first starts before setup is complete. Fernet key derivation from an empty string produces a weak key.
**Why it happens:** `Settings.secret_key` defaults to `""` and is overwritten after first-run setup.
**How to avoid:** In `LLMConfigService._get_fernet()`, check `if not settings.secret_key: raise ValueError("secret_key not set")`. LLM config save is an owner-only action that only happens after setup is complete, so this should not occur in practice. Add an assertion or guard regardless.
**Warning signs:** Empty `secret_key` in production config.

### Pitfall 3: nginx SSE Location Block Order
**What goes wrong:** The `/browser/llm/chat/stream` location block is placed after `location /` in nginx.conf. nginx uses first-match semantics for standard `location` blocks, so the catch-all matches first and the SSE-specific config is never applied.
**Why it happens:** Location blocks are ordered by specificity rules: exact match (`=`) > prefix string with `^~` modifier > regex > prefix string. The new location is a prefix string match and `location /` is also a prefix string, so the more-specific (longer prefix) wins. However, if the blocks are equal specificity and ordered, the first one wins.
**How to avoid:** Verify that `location /browser/llm/chat/stream` comes before `location /` in nginx.conf. Since `/browser/llm/chat/stream` is more specific (longer prefix match) than `/`, nginx should select it correctly regardless of order — but explicit ordering before the catch-all is best practice and clearer.
**Warning signs:** Streaming endpoint returns but responses are buffered (no data until connection closes).

### Pitfall 4: httpx `aiter_lines()` vs `aiter_bytes()` for SSE Passthrough
**What goes wrong:** Using `aiter_bytes()` to proxy SSE introduces chunk boundary issues — a line like `data: {...}\n\n` may be split across two chunks, yielding malformed events to the browser.
**Why it happens:** HTTP chunked transfer encoding chunks are independent of SSE line boundaries.
**How to avoid:** Use `aiter_lines()` which buffers across chunk boundaries and yields complete lines. Then re-add the `\n\n` SSE delimiter when forwarding: `yield f"{line}\n\n"` for non-empty lines.
**Warning signs:** Client-side EventSource fires partial JSON parse errors.

### Pitfall 5: InstanceConfig `updated_at` onupdate Not Firing on SQLite
**What goes wrong:** `InstanceConfig.updated_at` has `onupdate=func.now()` in the ORM definition, but the model uses `Base.metadata.create_all` (not Alembic) so the schema may already exist without the `onupdate` trigger.
**Why it happens:** `onupdate` in SQLAlchemy is a Python-side hook, not a database-side trigger. It fires when the ORM detects a change via `row.value = new_value` and then commits.
**How to avoid:** Always update `InstanceConfig` rows via ORM (`row.value = new_value`) not raw SQL. The `LLMConfigService.save_config()` pattern shown above uses ORM correctly.
**Warning signs:** `updated_at` not updating when values change.

### Pitfall 6: Fernet Token Length Exceeds InstanceConfig value column (4096 chars)
**What goes wrong:** A long API key (e.g., 512 chars) encrypted with Fernet produces a base64-encoded token that could exceed 4096 chars.
**Why it happens:** Fernet token = IV (16 bytes) + HMAC (32 bytes) + ciphertext (padded to 16-byte blocks) + base64 overhead. A 512-char key produces ~760 chars of ciphertext. This is well within 4096.
**How to avoid:** API keys from providers are typically < 100 chars. 4096 chars is more than sufficient. No action needed, but noted for awareness.
**Warning signs:** SQLAlchemy truncation errors on long API key saves.

---

## Code Examples

Verified patterns from official sources and codebase analysis:

### Fernet Encryption with PBKDF2 (Source: cryptography.io official docs)
```python
import base64
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

_LLM_KDF_SALT = b"sempkm-llm-config-v1"

def _get_fernet(secret_key: str) -> Fernet:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_LLM_KDF_SALT,
        iterations=100_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
    return Fernet(key)
```

### FastAPI SSE StreamingResponse (Source: FastAPI docs + OpenAI community patterns)
```python
from fastapi.responses import StreamingResponse

async def event_stream():
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    yield f"{line}\n\n"

return StreamingResponse(
    event_stream(),
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    },
)
```

### nginx SSE Location Block (Source: DigitalOcean community + oneuptime.com December 2025)
```nginx
location /browser/llm/chat/stream {
    proxy_pass http://api:8000/browser/llm/chat/stream;
    proxy_buffering off;
    proxy_http_version 1.1;
    proxy_read_timeout 300s;
    proxy_set_header Connection "keep-alive";
    proxy_set_header Cache-Control "no-cache";
    proxy_set_header Cookie $http_cookie;
    proxy_pass_header Set-Cookie;
    add_header X-Accel-Buffering "no";
}
```

### OpenAI-Compatible /v1/models Test Call (Source: OpenAI API docs + LM Studio docs)
```python
async with httpx.AsyncClient(timeout=10.0) as client:
    resp = await client.get(
        f"{base_url}/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    # Success: resp.status_code == 200
    # Response: {"object": "list", "data": [{"id": "gpt-4o", ...}, ...]}
    models = [m["id"] for m in resp.json().get("data", [])]
```

### InstanceConfig Upsert Pattern (Source: codebase — existing pattern)
```python
# Existing InstanceConfig pattern from admin/auth usage
existing = await db.execute(select(InstanceConfig).where(InstanceConfig.key == key))
row = existing.scalar_one_or_none()
if row:
    row.value = value
else:
    db.add(InstanceConfig(key=key, value=value))
await db.commit()
```

---

## Implementation Sequence for Plans

Based on the ~2 plan estimate:

**Plan 17-01: LLM Config Storage and Settings UI**
- Python: `LLMConfigService` in `backend/app/services/llm.py` (encryption, InstanceConfig CRUD)
- Python: Install `cryptography` package (`uv add cryptography`, update `pyproject.toml`)
- Python: `LLMConfigService.get_config()`, `save_config()`, `get_decrypted_api_key()`
- FastAPI: `PUT /browser/llm/config` endpoint (owner-only, calls `LLMConfigService.save_config()`)
- FastAPI: Extend `settings_page` route to pass `llm_config` context, change to `require_role("owner")` or pass `user.role` for conditional rendering
- Template: Add `LLM Connection` category section to `settings_page.html` using `_llm_settings.html` partial
- Template: `_llm_settings.html` — masked API key field, base URL text input, default model text input
- CSS: `.settings-action-btn`, `.settings-action-row` styles for Test/Fetch buttons
- Test: Save API key → verify it is encrypted in DB → verify it doesn't appear in `/browser/settings/data` response

**Plan 17-02: Test Connection, Fetch Models, and Streaming Proxy**
- FastAPI: `POST /browser/llm/test` → `test_result.html` partial with status badge
- FastAPI: `POST /browser/llm/models` → `models_select.html` partial with `<select>`
- FastAPI: `POST /browser/llm/chat/stream` → `StreamingResponse` SSE proxy
- Template: `browser/llm/test_result.html` — status badge (success/error with icon)
- Template: `browser/llm/models_select.html` — `<select>` + text input fallback on error
- nginx: Add SSE location block to `frontend/nginx.conf` before `location /`
- Test: Test Connection button shows success with a real provider; Fetch Models populates dropdown; streaming endpoint returns SSE chunks

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| openai Python SDK for LLM calls | Direct httpx + OpenAI-compatible REST API | 2023+ | Any `/v1/`-compatible provider (Ollama, LM Studio, Together.ai) works without SDK changes |
| Plaintext API keys in env vars | Fernet-encrypted at rest in SQL | Best practice since 2022 | Keys not visible in DB dumps or logs |
| nginx buffering SSE | `proxy_buffering off` + `X-Accel-Buffering: no` | Always required | Without this, streaming appears to hang until connection closes |
| `localStorage` for settings | Server-side `InstanceConfig`/`user_settings` | Phase 15 | Multi-device sync, encrypted API keys |

**Deprecated/outdated:**
- `openai` Python SDK: Not wrong, but not needed here — direct httpx calls to `/v1/chat/completions` work with any OpenAI-compatible provider and `httpx` is already in the project.

---

## Open Questions

1. **Should non-owner users see the LLM Connection category in settings?**
   - What we know: Other admin features (model management, webhooks) require owner role. The settings page currently uses `get_current_user` (any user).
   - What's unclear: Whether the settings route should be changed to `require_role("owner")` (blocking non-owners from settings entirely) or whether non-owner users still need access to the General category.
   - Recommendation: Keep `get_current_user` for the settings page route; pass `user.role` to the template and conditionally render the LLM Connection category only when `user.role == "owner"`. This preserves access to personal settings for all users.

2. **Where does `secret_key` come from when `LLMConfigService` needs it?**
   - What we know: `app.config.settings.secret_key` is a module-level singleton loaded from env. It is `""` by default and populated from the `SECRET_KEY` env var or auto-generated at first run.
   - What's unclear: The auto-generation logic is in `auth/tokens.py` and loads/saves from `./data/.secret-key` — this runs during lifespan startup. After startup, `settings.secret_key` may still be `""` if the env var wasn't set and the service reads from the module singleton before the file is loaded.
   - Recommendation: Verify how `secret_key` is populated after lifespan startup. If it's file-based (loaded into `settings` object during lifespan), ensure `LLMConfigService` reads from the same populated `settings` object. The existing session signing uses `settings.secret_key`, so if sessions work, the key is present.

3. **Does the `/browser/settings` route need to change from `get_current_user` to `require_role("owner")`?**
   - What we know: Non-owner users can currently access settings (for their personal settings). LLM config should be owner-only.
   - What's unclear: Whether member-role users have any useful settings to configure.
   - Recommendation: Keep the route open to all authenticated users; render the LLM section conditionally based on `user.role`. Add an `is_owner` variable to the template context.

---

## Sources

### Primary (HIGH confidence)
- Codebase: `/home/james/Code/SemPKM/backend/app/auth/models.py` — `InstanceConfig` schema (key/value/updated_at)
- Codebase: `/home/james/Code/SemPKM/backend/app/services/settings.py` — `SettingsService` pattern, `SYSTEM_SETTINGS` dict
- Codebase: `/home/james/Code/SemPKM/backend/app/browser/router.py` — existing settings endpoints, `get_settings_service()`, `require_role` usage
- Codebase: `/home/james/Code/SemPKM/backend/app/templates/browser/settings_page.html` — existing settings page template structure
- Codebase: `/home/james/Code/SemPKM/backend/app/templates/browser/_setting_input.html` — existing input type rendering
- Codebase: `/home/james/Code/SemPKM/backend/app/config.py` — `Settings` model, `secret_key` field
- Codebase: `/home/james/Code/SemPKM/frontend/nginx.conf` — existing nginx config structure
- Codebase: `/home/james/Code/SemPKM/backend/pyproject.toml` — no `cryptography` in deps (must add)
- Official docs: https://cryptography.io/en/latest/fernet/ — Fernet API, PBKDF2HMAC, key generation, encrypt/decrypt
- Official docs: FastAPI `StreamingResponse` with `media_type="text/event-stream"`

### Secondary (MEDIUM confidence)
- WebSearch verified with official source: OpenAI `/v1/models` endpoint format — `{"object": "list", "data": [{"id": ...}]}` (standard across OpenAI-compatible providers including Ollama, LM Studio)
- WebSearch: nginx `proxy_buffering off` + `proxy_read_timeout 300s` for SSE (multiple sources consistent with each other, verified against DigitalOcean community docs)
- WebFetch: https://sevalla.com/blog/real-time-openai-streaming-fastapi/ — `StreamingResponse` + `text/event-stream` + SSE format `data: {text}\n\n`
- WebFetch: https://community.openai.com/t/how-to-forward-openais-stream-response-using-fastapi-in-python/963242 — httpx streaming proxy pattern with `aiter_lines()`

### Tertiary (LOW confidence — verify at implementation)
- The `secret_key` population flow (file load during lifespan vs env var) needs verification at implementation time. This affects whether `LLMConfigService` can safely call `settings.secret_key`.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `cryptography`, `httpx`, `InstanceConfig` all have clear paths; patterns verified against codebase
- Architecture: HIGH — all extension points identified in existing code; two clear plans
- Encryption pattern: HIGH — Fernet documented and verified via official docs
- SSE streaming: HIGH — httpx `aiter_lines()` + `StreamingResponse` is the standard pattern; nginx config verified
- Pitfalls: HIGH — all identified from direct code and infrastructure analysis
- secret_key availability: MEDIUM — verified that sessions use it (so it's populated), but exact loading flow not traced to completion

**Research date:** 2026-02-24
**Valid until:** 2026-03-26 (stable stack)