# Appendix E: Troubleshooting

This appendix covers common issues you may encounter when running SemPKM, with symptoms, causes, and solutions.

---

## Setup and Authentication

### Setup token not showing in logs

**Symptom:** You started SemPKM for the first time but cannot find the setup token in the API logs.

**Cause:** The token is printed once during startup and can scroll past quickly, especially if other services produce log output at the same time.

**Solution:**

1. Search the API logs specifically for the token:
   ```bash
   docker compose logs api | grep -i "setup token"
   ```

2. Alternatively, read the token file directly from the container:
   ```bash
   docker compose exec api cat /app/data/.setup-token
   ```

3. If the file does not exist, the setup has already been completed. If you need to reset, run the reset script:
   ```bash
   ./scripts/reset-instance.sh
   ```

### Magic links not sent (no email received)

**Symptom:** You click "Send Magic Link" but no email arrives. The login form shows no error.

**Cause:** SMTP is not configured. When SMTP variables (`SMTP_HOST`, `SMTP_USER`, etc.) are empty, SemPKM falls back to displaying the magic link token directly in the API response or logs instead of sending an email.

**Solution:**

- For development: check the API logs for the token:
  ```bash
  docker compose logs api | grep -i "magic\|token"
  ```

- For production: configure SMTP environment variables. See [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md) for the complete list.

### Session expired unexpectedly

**Symptom:** You are logged out sooner than expected.

**Cause:** The default session duration is 30 days. If the `SECRET_KEY` changes (e.g., because the auto-generated key was lost during a container rebuild), all sessions are invalidated.

**Solution:**

- Set a persistent `SECRET_KEY` environment variable so it survives container rebuilds. See [Production Deployment](20-production-deployment.md).
- Increase `SESSION_DURATION_DAYS` if needed.

---

## Objects and Data

### Objects not loading in the Explorer tree

**Symptom:** The Explorer tree shows type categories but no objects underneath them, or clicking a type category does not expand.

**Cause:** This typically means the triplestore is not responding, or the current state graph is empty.

**Solution:**

1. Check that the triplestore is running and healthy:
   ```bash
   docker compose ps
   docker compose logs triplestore | tail -20
   ```

2. Verify the API can reach the triplestore:
   ```bash
   docker compose exec api curl -f http://triplestore:8080/rdf4j-server/protocol
   ```

3. If the triplestore is healthy but data is missing, check that Mental Models were installed successfully:
   ```bash
   docker compose logs api | grep -i "model\|install\|ontology"
   ```

### Objects not appearing after creation

**Symptom:** You create a new object via the form or Command API, the response indicates success, but the object does not appear in the Explorer tree.

**Cause:** The Explorer tree may need to be refreshed. Tree expansion is lazy-loaded -- clicking a type node fetches its children from the API.

**Solution:**

- Collapse and re-expand the type node in the Explorer tree.
- If the object still does not appear, check the API logs for errors during the command execution.
- Verify the object exists via the SPARQL console in the bottom panel:
  ```sparql
  SELECT ?s ?p ?o WHERE { ?s ?p ?o . FILTER(?s = <your-object-iri>) }
  ```

### Cannot edit objects (form is read-only)

**Symptom:** Opening an object shows the read view, but clicking **Edit** or pressing `Ctrl+E` does not switch to edit mode.

**Cause:** The edit/read flip container may not have initialized properly, typically due to a JavaScript error or a partial page load.

**Solution:**

1. Check the browser console (F12) for JavaScript errors.
2. Try a hard refresh of the page (`Ctrl+Shift+R`).
3. If the issue persists, check that all frontend static files are being served correctly:
   ```bash
   docker compose logs frontend | tail -20
   ```

---

## Validation

### Validation not running (Lint Panel stays empty)

**Symptom:** You save an object but the Lint Panel in the right pane shows no validation results, even for objects with intentionally invalid data.

**Cause:** Validation runs asynchronously via a background queue. It may take 1--3 seconds after saving for results to appear. If the Lint Panel remains empty indefinitely, the validation queue may have stalled.

**Solution:**

1. Wait a few seconds and click the object again (or press `Ctrl+E` twice to flip back to read mode) to trigger a Lint Panel refresh.

2. Manually trigger validation via the command palette: press `Ctrl+K`, type "Run Validation", and select it.

3. Check the API logs for validation errors:
   ```bash
   docker compose logs api | grep -i "validation\|shacl\|lint"
   ```

4. Ensure SHACL shapes were loaded correctly. A model with invalid shapes will silently produce no validation results.

### False validation errors after model update

**Symptom:** After updating a Mental Model's shapes file, objects show validation errors that seem incorrect.

**Cause:** The triplestore may be serving cached or stale shape data from a previous version.

**Solution:**

1. Restart the API to reload models:
   ```bash
   docker compose restart api
   ```

2. If stale data persists, the old shapes may still be in the triplestore. Check the model-specific named graph and verify the shapes are current.

---

## Container and Startup Issues

### Triplestore fails to start

**Symptom:** `docker compose up` shows the triplestore container restarting or exiting with an error.

**Cause:** Common causes include insufficient memory for the JVM or corrupted data files.

**Solution:**

1. Check triplestore logs:
   ```bash
   docker compose logs triplestore
   ```

2. If you see `OutOfMemoryError`, increase the heap allocation:
   ```yaml
   environment:
     JAVA_OPTS: "-Xmx2g"
   ```
   Also ensure your Docker host has enough memory allocated (Docker Desktop users: check Settings > Resources).

3. If data files are corrupted, you may need to remove and recreate the volume:
   ```bash
   docker compose down
   docker volume rm sempkm_rdf4j_data
   docker compose up -d
   ```
   > **Warning:** Removing the volume deletes all triplestore data. Ensure you have a backup before proceeding.

### API container keeps restarting

**Symptom:** The API container enters a restart loop. `docker compose ps` shows it as "restarting".

**Cause:** The API depends on the triplestore being healthy. If the triplestore is not ready, or if there is a configuration error (invalid `DATABASE_URL`, missing dependencies), the API will fail to start.

**Solution:**

1. Check API logs for the specific error:
   ```bash
   docker compose logs api
   ```

2. Common causes:
   - **Triplestore not healthy:** Wait for the triplestore to pass its healthcheck before starting the API.
   - **Invalid DATABASE_URL:** Ensure the connection string format is correct (`sqlite+aiosqlite:///` or `postgresql+asyncpg://`).
   - **Port conflict:** If port 8001 is already in use, change the port mapping in `docker-compose.yml`.

### Frontend returns 502 or blank page

**Symptom:** The browser shows a 502 Bad Gateway error or a completely blank page at `http://localhost:3000`.

**Cause:** The frontend Nginx container depends on the API being healthy. If the API is not running, the Nginx reverse proxy returns a 502 for API-proxied requests.

**Solution:**

1. Ensure all three services are running:
   ```bash
   docker compose ps
   ```

2. If the API is not healthy, troubleshoot it first (see above).

3. If Nginx is running but serving a blank page, check that the static files volume is mounted correctly:
   ```bash
   docker compose exec frontend ls /usr/share/nginx/html/
   ```

---

## Triplestore Memory

### Slow queries or high memory usage

**Symptom:** SPARQL queries in the bottom panel take a long time, or the triplestore container uses excessive memory.

**Cause:** As your knowledge base grows, complex queries (especially graph views with many relationships) may require more memory.

**Solution:**

1. Increase the JVM heap size:
   ```yaml
   environment:
     JAVA_OPTS: "-Xmx2g"
   ```

2. Optimize your view queries. Avoid `SELECT *` patterns; explicitly list the variables you need. Use `LIMIT` for exploratory queries.

3. Check how many triples are in the triplestore:
   ```sparql
   SELECT (COUNT(*) AS ?count) WHERE { GRAPH ?g { ?s ?p ?o } }
   ```

4. If the triplestore has accumulated many event graphs over time and you do not need the full history, consider exporting current state and resetting (advanced operation -- back up first).

---

## Obsidian Import Issues

### Zip file upload fails or is rejected

**Symptom:** Uploading an Obsidian vault `.zip` file produces an error, or the file is silently rejected.

**Cause:** The file may exceed the maximum upload size, may not be a valid zip archive, or may not contain recognizable Markdown files.

**Solution:**

1. Ensure the file is a standard `.zip` archive (not `.rar`, `.7z`, or `.tar.gz`).
2. Check that the zip contains `.md` files. The importer scans for Markdown files and ignores everything else.
3. For very large vaults, split the zip into smaller batches and import in multiple passes.
4. Check the API logs for specific error messages:
   ```bash
   docker compose logs api | grep -i "import\|upload\|zip"
   ```

### Frontmatter properties not recognized

**Symptom:** After importing, objects are missing properties that were present as YAML frontmatter in the original Obsidian notes.

**Cause:** The property mapping step may not have mapped Obsidian frontmatter keys to SemPKM properties. Only explicitly mapped properties are imported.

**Solution:**

- During the import wizard's property mapping step, review the detected frontmatter keys and map each one to the appropriate SemPKM property.
- Unmapped keys are ignored during import. You can re-import the same vault with updated mappings.
- See [Chapter 24: Obsidian Onboarding](24-obsidian-onboarding.md) for a detailed walkthrough of the mapping step.

### Import appears stuck or does not complete

**Symptom:** The import progress bar stops advancing, or the import summary never appears.

**Cause:** Large vaults with many files can take several minutes. If the SSE (Server-Sent Events) connection drops, the progress UI may freeze while the import continues in the background.

**Solution:**

1. Check the API logs for ongoing import activity:
   ```bash
   docker compose logs api --tail=20
   ```
2. If the import is still running, wait for it to complete. Refreshing the page will show the final summary once the import finishes.
3. If the import has genuinely stalled, restart the API container and re-import:
   ```bash
   docker compose restart api
   ```

---

## WebID and Identity Issues

### WebID profile page returns 404

**Symptom:** Visiting `{APP_BASE_URL}/id/{username}` returns a 404 Not Found error.

**Cause:** The user may not have a WebID profile configured, or `APP_BASE_URL` may not be set correctly.

**Solution:**

1. Verify the username exists in the user management page (Admin > Users).
2. Check that `APP_BASE_URL` is set to the correct public URL of your SemPKM instance:
   ```bash
   docker compose exec api printenv APP_BASE_URL
   ```
3. If `APP_BASE_URL` is empty, the system derives URLs from request headers, which may not work behind a reverse proxy. Set it explicitly in your environment.

### Content negotiation not returning Linked Data

**Symptom:** Requesting a WebID URL with `Accept: application/ld+json` returns HTML instead of JSON-LD.

**Cause:** The reverse proxy (nginx) may be stripping or overriding the `Accept` header before it reaches the API.

**Solution:**

1. Test directly against the API (bypassing nginx):
   ```bash
   curl -H "Accept: application/ld+json" http://localhost:8001/id/{username}
   ```
2. If that works but the nginx-proxied URL does not, check your nginx configuration for `proxy_set_header` directives that may override request headers.
3. You can also use the `?format=jsonld` or `?format=turtle` query parameter as a fallback that bypasses content negotiation.

### IndieAuth login fails at a third-party service

**Symptom:** Attempting to sign into an IndieAuth-compatible service using your SemPKM URL fails during the authorization flow.

**Cause:** Common causes include `APP_BASE_URL` not matching the URL you entered at the third-party service, or the third-party service being unable to reach your SemPKM instance (e.g., running on `localhost`).

**Solution:**

1. Ensure `APP_BASE_URL` exactly matches the URL you use to identify yourself (including `https://`).
2. The third-party service must be able to reach your SemPKM instance over the network. `localhost` URLs will not work with external services.
3. Verify your WebID profile is accessible from the internet if authenticating with an external service.
4. Check the API logs for OAuth-related errors:
   ```bash
   docker compose logs api | grep -i "indieauth\|oauth\|authorize"
   ```

---

## General Tips

- **Always check logs first.** Most issues produce informative error messages in the API or triplestore logs.
  ```bash
  docker compose logs api --tail=50
  docker compose logs triplestore --tail=50
  ```

- **Use the health endpoints.** The API exposes `/api/health` for monitoring. The triplestore healthcheck uses `/rdf4j-server/protocol`.

- **Browser DevTools are your friend.** For frontend issues, open the browser console (F12) to see JavaScript errors, failed network requests, and htmx swap issues.

- **Restart selectively.** If only one service is misbehaving, restart just that service rather than the entire stack:
  ```bash
  docker compose restart api
  ```

## See Also

- [Installation and Setup](03-installation-and-setup.md) -- initial setup walkthrough
- [Production Deployment](20-production-deployment.md) -- production configuration
- [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md) -- all configuration options
- [Appendix F: FAQ](appendix-f-faq.md) -- frequently asked questions

---

**Previous:** [Appendix D: Glossary](appendix-d-glossary.md) | **Next:** [Appendix F: FAQ](appendix-f-faq.md)
