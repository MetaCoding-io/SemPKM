---
id: T01
parent: S01
milestone: M045
provides: []
requires: []
affects: []
key_files: ["backend/app/security/__init__.py", "backend/app/security/ssrf.py", "backend/app/federation/service.py", "backend/app/federation/router.py", "backend/app/services/webhooks.py", "backend/tests/test_ssrf_guard.py"]
key_decisions: ["Check order is loopback → link-local → multicast → private → reserved so most specific category fires first", "Added bare ::1 to blocked hostnames since urlparse strips brackets from IPv6 addresses"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "Ran pytest tests/test_ssrf_guard.py -v — 23/23 passed. Verified all modified modules import cleanly without errors."
completed_at: 2026-03-28T23:22:25.073Z
blocker_discovered: false
---

# T01: Created validate_outbound_url() SSRF guard and wired it into all 4 outbound HTTP code paths (federation sync, inbox POST, profile discovery, webhook dispatch) with 23 passing tests

> Created validate_outbound_url() SSRF guard and wired it into all 4 outbound HTTP code paths (federation sync, inbox POST, profile discovery, webhook dispatch) with 23 passing tests

## What Happened
---
id: T01
parent: S01
milestone: M045
key_files:
  - backend/app/security/__init__.py
  - backend/app/security/ssrf.py
  - backend/app/federation/service.py
  - backend/app/federation/router.py
  - backend/app/services/webhooks.py
  - backend/tests/test_ssrf_guard.py
key_decisions:
  - Check order is loopback → link-local → multicast → private → reserved so most specific category fires first
  - Added bare ::1 to blocked hostnames since urlparse strips brackets from IPv6 addresses
duration: ""
verification_result: passed
completed_at: 2026-03-28T23:22:25.074Z
blocker_discovered: false
---

# T01: Created validate_outbound_url() SSRF guard and wired it into all 4 outbound HTTP code paths (federation sync, inbox POST, profile discovery, webhook dispatch) with 23 passing tests

**Created validate_outbound_url() SSRF guard and wired it into all 4 outbound HTTP code paths (federation sync, inbox POST, profile discovery, webhook dispatch) with 23 passing tests**

## What Happened

Created backend/app/security/ssrf.py with validate_outbound_url() that parses URLs, rejects non-http(s) schemes, checks hostnames against a blocked list, resolves DNS, and validates all resolved IPs against loopback/link-local/multicast/private/reserved categories. Wired it into FederationService.sync_shared_graph(), _post_to_inbox(), _discover_inbox_from_profile(), and WebhookService.dispatch(). Added HTTP 400 response in federation sync router for SSRF-blocked URLs. Wrote 23 unit tests covering blocked URLs, allowed URLs, error message quality, and DNS failure handling.

## Verification

Ran pytest tests/test_ssrf_guard.py -v — 23/23 passed. Verified all modified modules import cleanly without errors.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_ssrf_guard.py -v` | 0 | ✅ pass | 2200ms |
| 2 | `cd backend && .venv/bin/python -c "from app.security.ssrf import validate_outbound_url"` | 0 | ✅ pass | 300ms |
| 3 | `cd backend && .venv/bin/python -c "from app.federation.service import FederationService"` | 0 | ✅ pass | 300ms |
| 4 | `cd backend && .venv/bin/python -c "from app.services.webhooks import WebhookService"` | 0 | ✅ pass | 300ms |


## Deviations

Added bare ::1 to blocked hostnames (urlparse strips IPv6 brackets). Reordered IP checks so link-local fires before private for more specific error messages. Used globally-routable test IPs instead of RFC 5737 documentation ranges which Python 3.14 classifies as private.

## Known Issues

None.

## Files Created/Modified

- `backend/app/security/__init__.py`
- `backend/app/security/ssrf.py`
- `backend/app/federation/service.py`
- `backend/app/federation/router.py`
- `backend/app/services/webhooks.py`
- `backend/tests/test_ssrf_guard.py`


## Deviations
Added bare ::1 to blocked hostnames (urlparse strips IPv6 brackets). Reordered IP checks so link-local fires before private for more specific error messages. Used globally-routable test IPs instead of RFC 5737 documentation ranges which Python 3.14 classifies as private.

## Known Issues
None.
