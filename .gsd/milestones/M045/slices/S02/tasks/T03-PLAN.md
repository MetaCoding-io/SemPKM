---
estimated_steps: 31
estimated_files: 5
skills_used: []
---

# T03: SECRET_KEY startup rejection and per-app JWT key isolation

Reject known weak SECRET_KEY values at startup when not in demo/test mode, and derive per-app HMAC signing keys instead of using the platform-wide key directly.

## Steps

1. Edit `backend/app/main.py` in the `# --- Security Startup Warnings ---` section (around line 497):
   - Define `_WEAK_KEYS = {"changeme", "secret", "password", "admin"}`
   - After the existing localhost checks, add: if `settings.secret_key` is in `_WEAK_KEYS` and `settings.demo_mode` is `False`, log `logger.error("SECRET_KEY is a known weak value ('%s'). ...", settings.secret_key)` and `raise SystemExit(1)`
   - The demo key (`demo-secret-key-not-for-production`) and E2E test key (`e2e-test-secret-key-do-not-use-in-production`) are NOT in the weak list — they're intentional and clearly labeled
   - An empty `secret_key` is fine because `_get_secret_key()` auto-generates a secure random key

2. Edit `backend/app/apps/tokens.py`:
   - Add `import hmac` and `import hashlib`
   - Add function `get_app_secret(app_id: str) -> str` that calls `get_secret()` for the platform key, then returns `hmac.new(platform_key.encode(), app_id.encode(), hashlib.sha256).hexdigest()`
   - Keep `get_secret()` as-is for backward compat (other callers may still use it)

3. Edit `backend/app/apps/manager.py` line 193:
   - Change `generate_app_token(app_id, {}, get_secret())` to `generate_app_token(app_id, {}, get_app_secret(app_id))`
   - Update import to include `get_app_secret`

4. Edit `backend/app/apps/router.py` lines 79-80:
   - Change `secret = get_secret()` to `secret = get_app_secret(app_id)` — `app_id` is already available as a route parameter
   - Update import to include `get_app_secret`
   - Also update the `generate_app_token` call on the renewal path to use `get_app_secret(app_id)`

5. Create `backend/tests/test_app_token_isolation.py`:
   - Test: `get_app_secret('app-a')` != `get_app_secret('app-b')` (different apps get different keys)
   - Test: `get_app_secret('app-a')` called twice returns same value (deterministic)
   - Test: token signed with `get_app_secret('app-a')` validates with same key
   - Test: token signed with `get_app_secret('app-a')` does NOT validate with `get_app_secret('app-b')`
   - Test: startup rejection of weak key (mock settings, capture SystemExit)
   - Test: startup allows demo key when demo_mode=True

## Must-Haves

- [ ] Startup exits with error on weak SECRET_KEY when demo_mode=False
- [ ] Demo key passes when demo_mode=True
- [ ] `get_app_secret(app_id)` derives per-app key via HMAC-SHA256
- [ ] manager.py and router.py use `get_app_secret(app_id)` instead of `get_secret()`
- [ ] Unit tests prove key isolation and startup rejection

## Inputs

- ``backend/app/main.py` — Security Startup Warnings section at line 497`
- ``backend/app/apps/tokens.py` — get_secret() returns platform-wide key`
- ``backend/app/apps/manager.py` — line 193 calls generate_app_token with get_secret()`
- ``backend/app/apps/router.py` — line 79 calls get_secret() for token renewal`

## Expected Output

- ``backend/app/main.py` — weak key rejection at startup`
- ``backend/app/apps/tokens.py` — new get_app_secret(app_id) function using HMAC-SHA256`
- ``backend/app/apps/manager.py` — uses get_app_secret(app_id)`
- ``backend/app/apps/router.py` — uses get_app_secret(app_id)`
- ``backend/tests/test_app_token_isolation.py` — unit tests for key isolation and startup check`

## Verification

cd backend && python -m pytest tests/test_app_token_isolation.py -v
