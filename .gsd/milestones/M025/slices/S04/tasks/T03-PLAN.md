---
estimated_steps: 7
estimated_files: 7
---

# T03: User guide Chapter 38 and documentation updates

**Slice:** S04 — Cloud deployment config + E2E + docs
**Milestone:** M025

## Description

Write the user guide chapter for the hosted demo deployment and update all supporting documentation files. This covers the "docs" portion of S04, documenting DEMO_MODE, docker-compose.demo.yml, seed script usage, Caddy SSL termination, periodic reset, and CTA customization.

Per KNOWLEDGE.md rule: three files must stay in sync when adding a guide chapter — `docs/guide/README.md`, `docs/guide/index.html`, and `backend/app/templates/guide.html`. The navigation chain must be updated: Ch 37 currently points to Appendix A as "Next"; after this task, Ch 37 → Ch 38 → Appendix A.

## Steps

1. Create `docs/guide/38-hosted-demo.md` with these sections:
   - **Title:** `# Chapter 38: Hosted Demo Instance`
   - **Overview:** What the hosted demo is — a pre-populated, read-only SemPKM instance for prospective users to explore without installing Docker
   - **Prerequisites:** Docker, a VPS (for cloud deployment), a domain (for SSL)
   - **DEMO_MODE Configuration:** `DEMO_MODE=true` env var, what it does (anonymous access, synthetic guest user, setup wizard bypass). Reference `docker-compose.demo.yml`.
   - **Read-Only Enforcement:** How nginx blocks all write methods with 403 JSON. Mention `frontend/nginx.demo.conf`.
   - **Sample Data:** `scripts/seed-demo-data.py` usage — what it creates (4 models, 74 objects, cross-model edges, markdown bodies). Running via `docker compose exec`. The `--verify-only` flag.
   - **Demo Tour:** The 7-step Driver.js tour, auto-start behavior, manual restart button, localStorage keys (`sempkm_demo_tour_done`, `sempkm_demo_cta_dismissed`).
   - **Demo Dashboard:** Pre-built dashboard with cross-view context filtering. UUID `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee`.
   - **CTA Banner:** "Try SemPKM" banner after tour completion, dismiss behavior, customizing the link target.
   - **SSL with Caddy:** Installing Caddy, configuring the Caddyfile, domain setup. Reference `Caddyfile` at repo root.
   - **Periodic Reset:** `scripts/reset-demo.sh` usage, cron setup example (`0 */6 * * *`).
   - **Health Monitoring:** `curl http://localhost:3902/api/health` for uptime checks.
   - **Quick Start:** Concise steps: clone → `bash scripts/deploy-demo.sh` → visit URL
   - **Troubleshooting:** Common issues (port conflicts, seed script failures, stale data)
   - **See Also:** Links to Appendix A (env vars), Chapter 29 (App Platform), Chapter 10 (Mental Models)
   - **Navigation footer:** `**Previous:** [Chapter 37: Monday.com Sync](37-monday-sync.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)`

2. Update `docs/guide/37-monday-sync.md` navigation footer — change the "Next" link from Appendix A to Chapter 38:
   - Old: `**Previous:** [Chapter 36: Jira Sync](36-jira-sync.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)`
   - New: `**Previous:** [Chapter 36: Jira Sync](36-jira-sync.md) | **Next:** [Chapter 38: Hosted Demo](38-hosted-demo.md)`

3. Update `docs/guide/README.md` — add Chapter 38 entry after Chapter 37 in the Part VIII section:
   - Add `38. [Hosted Demo](38-hosted-demo.md)` after the Monday.com Sync line

4. Update `docs/guide/index.html` — add sidebar `<li>` for Chapter 38 after the Monday.com entry:
   - Pattern: `<li><a href="#" data-file="38-hosted-demo.md">38. Hosted Demo</a></li>`
   - Insert after the line containing `37-monday-sync.md`

5. Update `backend/app/templates/guide.html` — add `<button>` for Chapter 38 between the Monday.com button and the first appendix button:
   - Follow the existing button pattern with `hx-get="/guide/38-hosted-demo.md"`, `hx-target="#app-content"`, `hx-swap="innerHTML"`, `hx-push-url="true"`
   - Use Lucide icon `globe` (appropriate for hosted/cloud) or `play-circle` (appropriate for demo)
   - `<span>38. Hosted Demo</span>`

6. Update `docs/guide/appendix-a-environment-variables.md` — add `DEMO_MODE` to the main "Complete Variable Reference" table:
   - `| \`DEMO_MODE\` | Enable demo mode for the hosted demo instance. Makes all auth dependencies return a synthetic read-only guest user, bypasses the setup wizard, and exposes demo-specific UI (tour auto-start, CTA banner). Combine with \`nginx.demo.conf\` for write-blocking. | \`false\` | No |`
   - Insert it in alphabetical order (after `DATABASE_URL`, before `DEBUG`)

7. Update `docs/guide/appendix-d-glossary.md` — add two entries:
   - **Demo Mode**: A configuration flag (`DEMO_MODE=true`) that makes SemPKM accessible without login for prospective users. Enables anonymous access via a synthetic guest user, bypasses the setup wizard, auto-starts the demo tour on first visit, and shows a CTA banner after tour completion. Combine with read-only nginx config to prevent data modification. See [Chapter 38: Hosted Demo](38-hosted-demo.md).
   - **Hosted Demo**: A pre-populated, read-only SemPKM instance deployed for prospective users to explore. Includes 4 Mental Models with 74 sample objects, a guided Driver.js tour, and a pre-built dashboard demonstrating cross-view context filtering. See [Chapter 38: Hosted Demo](38-hosted-demo.md).
   - Insert in alphabetical order within the glossary

## Must-Haves

- [ ] `docs/guide/38-hosted-demo.md` exists with deployment documentation
- [ ] `docs/guide/README.md` has Chapter 38 entry
- [ ] `docs/guide/index.html` has Chapter 38 sidebar entry
- [ ] `backend/app/templates/guide.html` has Chapter 38 button
- [ ] `DEMO_MODE` added to `docs/guide/appendix-a-environment-variables.md`
- [ ] "Demo Mode" and "Hosted Demo" entries in `docs/guide/appendix-d-glossary.md`
- [ ] Navigation chain: Ch 37 → Ch 38 → Appendix A (both forward and back links)

## Verification

- `test -f docs/guide/38-hosted-demo.md` — chapter file exists
- `grep "38.*Hosted Demo" docs/guide/README.md` — TOC entry present
- `grep "38-hosted-demo" docs/guide/index.html` — sidebar entry present
- `grep "38-hosted-demo" backend/app/templates/guide.html` — in-app button present
- `grep "DEMO_MODE" docs/guide/appendix-a-environment-variables.md` — env var documented
- `grep -i "demo mode" docs/guide/appendix-d-glossary.md` — glossary entry present
- `grep -i "hosted demo" docs/guide/appendix-d-glossary.md` — glossary entry present
- `grep "Chapter 38" docs/guide/37-monday-sync.md` — Ch 37 links forward to Ch 38
- `grep "Appendix A" docs/guide/38-hosted-demo.md` — Ch 38 links forward to Appendix A
- `grep "Chapter 37" docs/guide/38-hosted-demo.md` — Ch 38 links back to Ch 37

## Observability Impact

This task is documentation-only — no runtime behavior changes. Observability signals:

- **Documentation completeness:** `grep -c "38-hosted-demo" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html` — all three navigation files must contain the chapter reference (the KNOWLEDGE.md three-file sync rule)
- **Navigation chain integrity:** Forward/back link verification via `grep "Chapter 38" docs/guide/37-monday-sync.md` and `grep "Chapter 37\|Appendix A" docs/guide/38-hosted-demo.md`
- **Environment variable documentation:** `grep "DEMO_MODE" docs/guide/appendix-a-environment-variables.md` confirms the env var is documented for operators deploying the demo
- **Glossary discoverability:** `grep -i "demo mode\|hosted demo" docs/guide/appendix-d-glossary.md` confirms terms are findable

No new endpoints, logs, or failure modes are introduced. The failure state is a broken navigation chain (missing links) or undocumented configuration, both detectable by the grep checks above.

## Inputs

- `docs/guide/37-monday-sync.md` — current "last chapter" before appendices; its navigation footer must be updated
- `docs/guide/README.md` — table of contents; Ch 37 is the last entry in Part VIII
- `docs/guide/index.html` — sidebar HTML; `37-monday-sync.md` is the last chapter `<li>` before Part IX
- `backend/app/templates/guide.html` — in-app guide; Monday.com button is the last chapter button before appendix buttons
- `docs/guide/appendix-a-environment-variables.md` — env var table; needs `DEMO_MODE` row
- `docs/guide/appendix-d-glossary.md` — glossary; needs "Demo Mode" and "Hosted Demo" entries
- S01-S03 summaries for content: DEMO_MODE behavior, nginx config, seed script, tour details, dashboard UUID, CTA banner

## Expected Output

- `docs/guide/38-hosted-demo.md` — new: ~200-300 lines documenting the hosted demo deployment
- `docs/guide/README.md` — modified: one line added (Ch 38 TOC entry)
- `docs/guide/index.html` — modified: one `<li>` added (Ch 38 sidebar)
- `backend/app/templates/guide.html` — modified: one `<button>` block added (Ch 38)
- `docs/guide/appendix-a-environment-variables.md` — modified: one table row added (DEMO_MODE)
- `docs/guide/appendix-d-glossary.md` — modified: two entries added (Demo Mode, Hosted Demo)
- `docs/guide/37-monday-sync.md` — modified: navigation footer "Next" changed from Appendix A to Ch 38
