# S01: SSRF Guards, Federation Integrity & Audit Extension — UAT

**Milestone:** M045
**Written:** 2026-03-28T23:36:42.776Z

## UAT: S01 — SSRF Guards, Federation Integrity & Audit Extension

### Preconditions
- Backend running with federation and webhook subsystems available
- At least one Mental Model available for install/uninstall
- Database with SecurityAuditLog table (M043 migration applied)

---

### UAT-1: SSRF Guard blocks loopback URLs in federation sync

**Steps:**
1. POST to `/api/federation/sync` with `remote_instance_url: "http://127.0.0.1:8000/api/federation/export"`
2. Observe response

**Expected:** HTTP 400 response with error message indicating the URL was blocked (loopback address)

---

### UAT-2: SSRF Guard blocks private network URLs in federation sync

**Steps:**
1. POST to `/api/federation/sync` with `remote_instance_url: "http://192.168.1.100/api/federation/export"`
2. POST with `remote_instance_url: "http://10.0.0.1/api/federation/export"`
3. POST with `remote_instance_url: "http://172.16.0.1/api/federation/export"`

**Expected:** All three return HTTP 400 with error messages identifying the blocked private IP range

---

### UAT-3: SSRF Guard blocks AWS metadata endpoint

**Steps:**
1. POST to `/api/federation/sync` with `remote_instance_url: "http://169.254.169.254/latest/meta-data/"`

**Expected:** HTTP 400 — link-local address blocked

---

### UAT-4: SSRF Guard blocks non-HTTP schemes

**Steps:**
1. POST to `/api/federation/sync` with `remote_instance_url: "ftp://example.com/export"`
2. POST with `remote_instance_url: "file:///etc/passwd"`

**Expected:** Both return HTTP 400 with error message about disallowed scheme

---

### UAT-5: SSRF Guard allows legitimate federation URLs

**Steps:**
1. POST to `/api/federation/sync` with `remote_instance_url: "https://federation.example.org:8443/api/federation/export"` (will fail at connection, not at validation)

**Expected:** Request passes SSRF validation (may fail with connection error, which is expected — the SSRF guard should not block it)

---

### UAT-6: Federation export includes SHA-256 content hash

**Steps:**
1. GET `/api/federation/export?since=2020-01-01T00:00:00Z`
2. Inspect response JSON

**Expected:** Response includes `content_hash` field containing a 64-character hex string (SHA-256 of `patch_text`)

---

### UAT-7: Federation import verifies hash when present

**Steps:**
1. Construct a sync request to a remote instance that returns `content_hash` matching the patch content
2. Construct a sync request where `content_hash` does not match patch content

**Expected:** 
- Matching hash: sync proceeds normally
- Mismatched hash: sync fails with integrity error in SyncResult, no triples applied

---

### UAT-8: Federation import warns on missing hash

**Steps:**
1. Sync with a remote instance running an older version that does not include `content_hash` in exports
2. Check server logs

**Expected:** WARNING log about missing integrity verification, sync proceeds normally (backward compatible)

---

### UAT-9: Namespace filter rejects system-namespace triples

**Steps:**
1. Attempt federation sync where remote payload includes triples with predicates in `urn:sempkm:` namespace (e.g., `urn:sempkm:internal:secret`)
2. Include triples with `owl:Class` type assertions
3. Include triples with `sh:` (SHACL) predicates

**Expected:** All system-namespace triples rejected (logged at WARNING with count). Only allowed data triples applied.

---

### UAT-10: Namespace filter allows shared graph IRIs

**Steps:**
1. Attempt federation sync where remote payload includes triples with subjects in `urn:sempkm:shared:` namespace

**Expected:** Triples with `urn:sempkm:shared:` subjects pass the filter (this is the federation graph namespace)

---

### UAT-11: Model install audit event

**Steps:**
1. Install a Mental Model via Admin > Models (e.g., basic-pkm)
2. Query SecurityAuditLog table for `event_type = 'model_installed'`

**Expected:** New audit row with event_type='model_installed', detail JSON including model_id and path, source_ip populated, user_id matching the admin user

---

### UAT-12: Model uninstall audit event

**Steps:**
1. Uninstall a Mental Model via Admin > Models
2. Query SecurityAuditLog table for `event_type = 'model_uninstalled'`

**Expected:** New audit row with event_type='model_uninstalled', detail JSON including model_id, source_ip populated

---

### UAT-13: Audit failure does not block model operations

**Steps:**
1. Simulate audit logging failure (e.g., temporarily make SecurityAuditLog table unavailable)
2. Install a Mental Model

**Expected:** Model installs successfully despite audit logging failure. Error logged at ERROR level but operation completes.

---

### UAT-14: Webhook dispatch SSRF guard

**Steps:**
1. Create a webhook configuration with `target_url: "http://127.0.0.1:9999/hook"`
2. Trigger an event that would dispatch to this webhook

**Expected:** Webhook dispatch blocked, WARNING log about SSRF-blocked URL. No HTTP request made to loopback address.

---

### Edge Cases

- **DNS rebinding:** validate_outbound_url() resolves DNS at validation time. A DNS rebinding attack returning safe IP during validation and private IP during connection is a known accepted risk.
- **IPv6 addresses:** `http://[::1]/` blocked. Both bracketed and bare `::1` handled.
- **Empty/None URLs:** Return clear error messages, not unhandled exceptions.
- **Multicast addresses:** Blocked (e.g., `http://224.0.0.1/`).
- **Unresolvable hostnames:** Rejected with DNS resolution failure error.
