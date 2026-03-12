# S17: Llm Connection Configuration

**Goal:** Implement LLM connection configuration: secure API key storage via Fernet encryption in InstanceConfig, owner-only settings UI with masked key field, and backend endpoints for saving config, testing the connection, and fetching available models.
**Demo:** Implement LLM connection configuration: secure API key storage via Fernet encryption in InstanceConfig, owner-only settings UI with masked key field, and backend endpoints for saving config, testing the connection, and fetching available models.

## Must-Haves


## Tasks

- [x] **T01: 17-llm-connection-configuration 01**
  - Implement LLM connection configuration: secure API key storage via Fernet encryption in InstanceConfig, owner-only settings UI with masked key field, and backend endpoints for saving config, testing the connection, and fetching available models.

Purpose: Lays the foundation for AI Copilot (v2.1) by letting admins wire up any OpenAI-compatible LLM endpoint securely. The API key is encrypted at rest and never exposed to the browser.
Output: LLMConfigService, three new browser endpoints, LLM Connection category in Settings page, and HTML fragment templates for Test/Fetch results.
- [x] **T02: 17-llm-connection-configuration 02**
  - Implement the SSE streaming proxy endpoint for LLM chat completions and configure nginx to not buffer it. This is the foundation for the AI Copilot (v2.1) — it proxies streaming responses from any OpenAI-compatible provider to the browser without accumulating the full response server-side.

Purpose: Without this endpoint, streaming LLM responses cannot be delivered to the browser in real-time. Without the nginx configuration, responses are silently buffered and arrive all at once at the end.
Output: POST /browser/llm/chat/stream FastAPI endpoint + nginx SSE location block.

## Files Likely Touched

- `backend/pyproject.toml`
- `backend/app/services/llm.py`
- `backend/app/browser/router.py`
- `backend/app/templates/browser/settings_page.html`
- `backend/app/templates/browser/_llm_settings.html`
- `backend/app/templates/browser/llm/test_result.html`
- `backend/app/templates/browser/llm/models_select.html`
- `backend/app/browser/router.py`
- `frontend/nginx.conf`
