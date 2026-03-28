---
estimated_steps: 7
estimated_files: 6
skills_used: []
---

# T01: SSRF guard utility and application to all outbound HTTP callers

Create a shared SSRF validation utility at `backend/app/security/ssrf.py` that resolves hostnames and rejects loopback, private, link-local, and reserved IPs. Restrict schemes to http/https. Apply it to all outbound HTTP code paths: federation sync (`FederationService.sync_shared_graph`), federation outbound notifications (`FederationService._post_to_inbox`, `FederationService._discover_inbox_from_profile`, `FederationService.notify_remote_members_of_change` inbox discovery calls), and webhook dispatch (`WebhookService.dispatch`). Add input validation to the federation sync router endpoint to reject obviously invalid URLs before they reach the service layer. Write comprehensive unit tests proving the guard blocks dangerous URLs and passes safe ones.

Steps:
1. Create `backend/app/security/__init__.py` and `backend/app/security/ssrf.py` with `validate_outbound_url(url: str) -> None` that raises `ValueError` on blocked URLs. Implementation: parse with `urllib.parse.urlparse`, reject non-http(s) schemes, resolve hostname via `socket.getaddrinfo`, check each resolved IP against `ipaddress.ip_address(addr).is_loopback`, `.is_private`, `.is_link_local`, `.is_reserved`, `.is_multicast`. Also reject hostnames like `localhost`, `0.0.0.0`, `[::]`.
2. In `backend/app/federation/service.py`, add `from app.security.ssrf import validate_outbound_url`. Call `validate_outbound_url(remote_instance_url)` at the top of `sync_shared_graph()` before any HTTP request. Call `validate_outbound_url(inbox_url)` in `_post_to_inbox()`. Call `validate_outbound_url(profile_url)` in `_discover_inbox_from_profile()`.
3. In `backend/app/federation/router.py`, add URL validation in `sync_shared_graph()` router handler — catch ValueError from the service and return HTTP 400.
4. In `backend/app/services/webhooks.py`, add `from app.security.ssrf import validate_outbound_url`. Call `validate_outbound_url(config.target_url)` at the top of `dispatch()` before the httpx POST. Log blocked URLs at WARNING.
5. Write `backend/tests/test_ssrf_guard.py` with tests: blocks `http://127.0.0.1`, `http://localhost`, `http://[::1]`, `http://10.0.0.1`, `http://172.16.0.1`, `http://192.168.1.1`, `http://169.254.169.254` (AWS metadata), `ftp://example.com` (wrong scheme), `http://0.0.0.0`; passes `https://example.com`, `https://federation.example.org:8443/api`. Test that ValueError message includes the reason.

## Inputs

- ``backend/app/federation/service.py` — existing outbound HTTP calls to guard`
- ``backend/app/federation/router.py` — sync endpoint accepting remote_instance_url`
- ``backend/app/services/webhooks.py` — webhook dispatch with target_url`

## Expected Output

- ``backend/app/security/__init__.py` — empty init for new security package`
- ``backend/app/security/ssrf.py` — validate_outbound_url() utility`
- ``backend/app/federation/service.py` — SSRF validation calls added`
- ``backend/app/federation/router.py` — HTTP 400 on SSRF-blocked URLs`
- ``backend/app/services/webhooks.py` — SSRF validation in dispatch()`
- ``backend/tests/test_ssrf_guard.py` — unit tests for SSRF guard`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_ssrf_guard.py -v
