---
estimated_steps: 4
estimated_files: 2
---

# T02: Record QUIC/HTTP/3 decision and register PERF-02 through PERF-10 requirements

**Slice:** S05 — Lighthouse Verification & QUIC/HTTP/3 Decision
**Milestone:** M029

## Description

Record the QUIC/HTTP/3 deferral decision via `gsd_save_decision` and register all 9 new PERF requirements (PERF-02 through PERF-10) in REQUIREMENTS.md. This is the documentation/traceability task that ensures the milestone's deliverables are tracked in the project's requirements and decisions registers.

The QUIC/HTTP/3 decision was already documented during M029 planning (referenced as D274 in the roadmap) but needs to be formally recorded via the GSD tooling. The rationale is fully established: nginx:stable-alpine lacks HTTP/3 support, self-hosted single-user tool gets minimal benefit from QUIC multiplexing, Caddy already exists for the demo instance (D246).

The PERF requirements have been referenced throughout S01–S04 summaries but were never registered in REQUIREMENTS.md. Each needs the correct status and validation proof based on prior slice work + T01 Lighthouse results.

## Steps

1. **Record QUIC/HTTP/3 decision** via `gsd_save_decision`:
   - scope: `tech`
   - decision: `QUIC/HTTP/3 for self-hosted Docker deployment`
   - choice: `Defer — nginx:stable-alpine lacks HTTP/3 support. Document rationale, revisit when nginx stable adds HTTP/3 or Caddy migration is separately motivated.`
   - rationale: `nginx:stable-alpine does NOT include HTTP/3 module (requires --with-http_v3_module + BoringSSL). nginx:mainline-alpine has experimental HTTP/3 but not stable. Self-hosted single-user tool over localhost gets minimal benefit from QUIC multiplexing and 0-RTT. HTTP/2 over h2c (cleartext) has limited browser support. Caddy supports HTTP/3 out of the box and is already used for the demo instance (D246), but switching the main Docker stack is a separate decision with its own trade-offs. Cost of implementing exceeds benefit for the current deployment model.`
   - revisable: `Yes — revisit when nginx:stable-alpine adds HTTP/3 or Caddy migration is separately motivated`

2. **Read T01's lighthouse-results.md** to get the actual measured Lighthouse scores for PERF-07 validation proof.

3. **Register PERF-02 through PERF-10 requirements** in REQUIREMENTS.md. For each, provide id, description, status, primary_owner, and validation proof. The requirements and their validation sources:

   | ID | Description | Status | Primary Owner | Validation Proof |
   |----|-------------|--------|---------------|-----------------|
   | PERF-02 | All 18 CDN dependencies replaced with locally served files | validated | M029/S01 | S01: 18 deps in package.json, vendor bundle produced, 37 manifest entries, all templates use conditional local/CDN blocks |
   | PERF-03 | Build pipeline produces minified, content-hashed assets automatically via docker compose build | validated | M029/S01 | S01: esbuild build.js, manifest.json with 37 entries, multi-stage Dockerfile, 0.8s build time |
   | PERF-04 | nginx serves gzip-compressed responses for CSS/JS/HTML/JSON/SVG | validated | M029/S02 | S02: gzip_static on for pre-compressed .gz siblings, gzip_proxied any for dynamic HTML, curl confirms Content-Encoding: gzip |
   | PERF-05 | HTTP caching with immutable headers on hashed assets, no-cache with ETag on auth pages | validated | M029/S02 | S02: Cache-Control: public, max-age=31536000, immutable on /assets/; no-cache + ETag + 304 on auth pages; curl verified all 8 checks |
   | PERF-06 | CSS code-splitting by route — admin pages load only shared CSS | validated | M029/S03 | S03: 19 templates override page_css block, curl confirms 0 workspace CSS links on admin pages, 5 on workspace pages |
   | PERF-07 | Lighthouse Performance score on workspace page (desktop preset) | validated | M029/S05 | S05/T01: [insert actual score from T01 results] desktop preset, up from estimated ~40-60 pre-M029 |
   | PERF-08 | Backend response timing middleware with top-5 slowest endpoint report | validated | M029/S04 | S04: TimingMiddleware + /api/admin/timing-report endpoint, Server-Timing header, 20 unit tests pass |
   | PERF-09 | Backend HTTP cache headers — ETag, conditional GET returning 304 | validated | M029/S04 | S04: ConditionalGetMiddleware, weak ETags on JSON API GET responses, 304 Not Modified, 16 unit tests pass |
   | PERF-10 | QUIC/HTTP/3 decision documented with rationale | validated | M029/S05 | S05/T02: Decision recorded — defer, nginx:stable-alpine lacks HTTP/3, minimal benefit for self-hosted single-user |

4. **Verify** both DECISIONS.md and REQUIREMENTS.md contain the new entries:
   ```bash
   grep 'QUIC' .gsd/DECISIONS.md
   grep -c 'PERF-' .gsd/REQUIREMENTS.md  # should be ≥10
   ```

## Must-Haves

- [ ] QUIC/HTTP/3 decision recorded via `gsd_save_decision` — appears in DECISIONS.md
- [ ] PERF-02 through PERF-10 (9 requirements) registered in REQUIREMENTS.md
- [ ] Each requirement has status=validated and a specific validation proof referencing slice evidence
- [ ] PERF-07 validation proof includes the actual measured Lighthouse score from T01

## Verification

- `grep 'QUIC' .gsd/DECISIONS.md` — shows the decision entry
- `grep -c 'PERF-' .gsd/REQUIREMENTS.md` — returns ≥10 (PERF-01 existed + 9 new)
- `grep 'PERF-07' .gsd/REQUIREMENTS.md` — shows the Lighthouse score in validation proof
- `grep 'PERF-10' .gsd/REQUIREMENTS.md` — shows QUIC/HTTP/3 decision reference

## Inputs

- `.gsd/milestones/M029/slices/S05/lighthouse-results.md` — T01's Lighthouse measurement results (needed for PERF-07 validation proof)
- `.gsd/milestones/M029/slices/S01/S01-SUMMARY.md` — S01 validation evidence (PERF-02, PERF-03)
- `.gsd/milestones/M029/slices/S02/S02-SUMMARY.md` — S02 validation evidence (PERF-04, PERF-05)
- `.gsd/milestones/M029/slices/S03/S03-SUMMARY.md` — S03 validation evidence (PERF-06)
- `.gsd/milestones/M029/slices/S04/S04-SUMMARY.md` — S04 validation evidence (PERF-08, PERF-09)
- M029-ROADMAP.md — QUIC/HTTP/3 rationale and D274 planning reference

## Expected Output

- `.gsd/DECISIONS.md` — new row with QUIC/HTTP/3 deferral decision
- `.gsd/REQUIREMENTS.md` — 9 new PERF requirement entries (PERF-02 through PERF-10) with validated status and proofs

## Observability Impact

- **DECISIONS.md**: New decision row for QUIC/HTTP/3 deferral. Inspect with `grep 'QUIC' .gsd/DECISIONS.md`.
- **REQUIREMENTS.md**: 9 new PERF-02 through PERF-10 entries. Verify count with `grep -c 'PERF-' .gsd/REQUIREMENTS.md` (should be ≥10 including pre-existing PERF-01). Verify individual entries with `grep 'PERF-07' .gsd/REQUIREMENTS.md` to confirm Lighthouse score is embedded.
- **Failure visibility**: If `gsd_save_decision` or `gsd_update_requirement` fails, the respective `.gsd/*.md` file will not contain the expected entries. The grep-based verification checks will catch this immediately.
