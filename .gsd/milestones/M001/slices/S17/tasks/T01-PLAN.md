# T01: 17-llm-connection-configuration 01

**Slice:** S17 — **Milestone:** M001

## Description

Implement LLM connection configuration: secure API key storage via Fernet encryption in InstanceConfig, owner-only settings UI with masked key field, and backend endpoints for saving config, testing the connection, and fetching available models.

Purpose: Lays the foundation for AI Copilot (v2.1) by letting admins wire up any OpenAI-compatible LLM endpoint securely. The API key is encrypted at rest and never exposed to the browser.
Output: LLMConfigService, three new browser endpoints, LLM Connection category in Settings page, and HTML fragment templates for Test/Fetch results.

## Must-Haves

- [ ] "Admin can navigate to the Settings page and see an 'LLM Connection' category in the sidebar"
- [ ] "Admin can enter an API base URL and it is saved to InstanceConfig on input (debounced 600ms)"
- [ ] "Admin can enter an API key; after save the field shows a bullet placeholder (not the key value) and a 'Set' badge"
- [ ] "The /browser/settings/data JSON endpoint never includes llm.api_key in its response"
- [ ] "Test Connection button posts to /browser/llm/test and replaces #llm-test-status with a success or error badge"
- [ ] "Fetch Models button posts to /browser/llm/models and replaces #llm-model-select with a populated <select> or error message"

## Files

- `backend/pyproject.toml`
- `backend/app/services/llm.py`
- `backend/app/browser/router.py`
- `backend/app/templates/browser/settings_page.html`
- `backend/app/templates/browser/_llm_settings.html`
- `backend/app/templates/browser/llm/test_result.html`
- `backend/app/templates/browser/llm/models_select.html`
