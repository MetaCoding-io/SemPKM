# Secrets Manifest

**Milestone:** M035
**Generated:** 2026-03-22

### OPENAI_API_KEY

**Service:** OpenAI
**Dashboard:** https://platform.openai.com/api-keys
**Format hint:** `sk-...` (51+ characters)
**Status:** pending
**Destination:** dotenv

1. Navigate to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Name it "SemPKM-M035-test" (or similar)
4. Copy the key immediately — it won't be shown again
5. Key is used only for Tier 3 cloud LLM tests (optional — tests skip gracefully without it)

### ANTHROPIC_API_KEY

**Service:** Anthropic
**Dashboard:** https://console.anthropic.com/settings/keys
**Format hint:** `sk-ant-...` (108 characters)
**Status:** pending
**Destination:** dotenv

1. Navigate to https://console.anthropic.com/settings/keys
2. Click "Create Key"
3. Name it "SemPKM-M035-test"
4. Copy the key immediately
5. Optional alternative to OPENAI_API_KEY for Tier 3 cloud tests — either works, both not required
