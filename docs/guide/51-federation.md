# Chapter 51: Federation and Shared Graphs

Federation lets separate SemPKM instances collaborate. You can create a **shared graph**, invite a user on another instance to join it, copy objects into it, and keep both copies in sync — all while each person keeps full ownership of their own self-hosted instance. Identity is anchored in your [WebID profile](25-webid-profiles.md), discovery uses WebFinger, and instances talk to each other with signed Linked Data Notifications (LDN).

By the end of this chapter you will understand what shared graphs are, how to create one and invite a remote collaborator, how invitations arrive in your Inbox, how sync pulls changes between instances, and what security guarantees protect your knowledge base from remote data.

> **Note:** "Federation" appears in two places in SemPKM. This chapter covers **instance-to-instance federation** (shared graphs and notifications). The **Admin > Federation Endpoints** page is a different feature — an allowlist of external SPARQL endpoints (e.g., Wikidata, DBpedia) that may be used in `SERVICE` clauses; see the note at the end of this chapter.

---

## How Federation Works

Four building blocks make up SemPKM federation:

1. **Shared graphs.** A shared graph is a named graph (`urn:sempkm:shared:{uuid}`) that exists on every member's instance. Objects copied into it are visible to all members, appear in the **SHARED** section of the Explorer, and are included when the workspace queries your data.

2. **WebID + WebFinger identity.** Each participant is identified by their WebID URI (e.g., `https://your-instance/users/alice#me`). Remote users can be addressed by handle (`alice@instance-a.example`), which SemPKM resolves through the standard `/.well-known/webfinger` endpoint to find their WebID profile and LDN inbox.

3. **Linked Data Notifications.** Instances exchange JSON-LD notifications (invitations, sync alerts, recommendations, messages) by POSTing ActivityStreams payloads to each other's `/api/inbox`. Inbound notifications must carry a valid HTTP Message Signature (RFC 9421) that verifies against the Ed25519 public key published in the sender's WebID profile.

4. **RDF Patch sync.** Sync is **pull-based**: your instance fetches the changes made to a shared graph on a remote instance since your last sync, as an RDF Patch derived from the remote event log, and applies them locally through the event store. Every synced change is an attributed event in your [Event Log](15-event-log.md), like any other write.

### Prerequisites

Before federating, on **both** instances:

1. **Claim a username and publish your WebID.** Navigate to **Settings > WebID Profile**, claim a username, and publish your profile. Invitation delivery, signature verification, and remote-instance discovery all depend on a published, HTTP-reachable WebID. See [Chapter 25: WebID Profiles](25-webid-profiles.md).
2. **Deploy with a public base URL over HTTPS.** WebFinger discovery contacts `https://{domain}/.well-known/webfinger`, and remote instances must be able to fetch your profile document and reach your inbox. A locally-bound dev instance cannot receive invitations from the outside. See [Chapter 20: Production Deployment](20-production-deployment.md).

---

## The Federation UI

Federation lives in three places in the workspace:

- **COLLABORATION panel** (right pane) — your shared graphs and contacts. Each shared graph card shows its name, a sync status dot, the member count, the last sync time, a pending-changes badge, and **Sync Now** / **Invite** buttons.
- **INBOX panel** (right pane) — notifications received from remote instances, with a badge showing the unread count. The badge and the list refresh automatically about once a minute.
- **SHARED section** (Explorer sidebar) — the contents of your shared graphs, grouped by type. Clicking an object opens it in a workspace tab.

The sync status dot on each shared graph card is color-coded:

| Dot | Meaning |
|-----|---------|
| 🟢 Green | Synced within the last 24 hours |
| 🟡 Yellow | Synced, but more than 24 hours ago |
| ⚪ Gray | Never synced |

A **pending** badge counts local events targeting the shared graph that originated on this instance (i.e., changes your collaborators have not necessarily pulled yet).

---

## Creating a Shared Graph

1. Expand the **COLLABORATION** panel in the right pane.
2. Click the **+** button next to **Shared Graphs**.
3. Enter a name (required) and an optional description.
4. Click **Create**.

The graph is created with you as its first member and appears as a card in the panel. Behind the scenes this calls:

```
POST /api/federation/shared-graphs
{"name": "Research Exchange", "description": "Shared reading notes"}
```

The API also accepts an optional `required_model` field naming a Mental Model ID that participants should have installed, so that shared objects render with proper forms and views on every instance.

## Inviting a Collaborator

1. On the shared graph's card, click **Invite**.
2. Enter the recipient as either a **handle** (`bob@instance-b.example`) or a full **WebID URL** (`https://instance-b.example/users/bob#me`).
3. Click **Send**.

SemPKM discovers the recipient via WebFinger, builds an ActivityStreams **Offer** notification describing the shared graph, and POSTs it to the recipient's inbox. If discovery fails (unpublished profile, unreachable domain), the invitation is rejected with an error toast.

## Accepting or Declining an Invitation

On the recipient's instance, the invitation appears in the **INBOX** panel as an **Offer** with **Accept** and **Decline** buttons.

- **Accept** creates the shared graph locally (same IRI as on the sender's instance), records both of you as members, adds the sender to your **Contacts**, and marks the notification as acted.
- **Decline** dismisses the notification. Nothing is created and the sender is not notified.

After accepting, the graph appears in your COLLABORATION panel and its contents populate the SHARED section of the Explorer once you sync.

---

## Adding Objects to a Shared Graph

Copying an object publishes a snapshot of its current triples into the shared graph:

```bash
curl -X POST https://your-instance/api/federation/shared-graphs/{graph-id}/copy \
  -H "Content-Type: application/json" \
  -H "Cookie: sempkm_session=..." \
  -d '{"object_iri": "https://your-instance/objects/abc123"}'
```

`{graph-id}` is the UUID portion of the shared graph IRI (`urn:sempkm:shared:{graph-id}` — visible on the graph card's `data-graph-iri` attribute or in the `GET /api/federation/shared-graphs` response).

> **Note:** Copying is currently API-only — there is no button in the object editor yet. See [Chapter 31: API Surface](31-api-surface.md) for authentication options.

The copy is committed through the event store like any other write, so it is attributed and auditable. After the commit, your instance sends a fire-and-forget **Update** sync alert to every remote member's inbox, telling them there are new changes to pull.

Copies are snapshots: later edits to the original object stay in your private graph until you copy the object again.

## Syncing

Sync is a pull: your instance asks a remote member's instance for everything that changed in the shared graph since your last sync.

Trigger it in either of two ways:

- Click **Sync Now** on the shared graph card in the COLLABORATION panel.
- Click **Sync Now** on an **Update** notification in the INBOX (this also marks the notification as acted).

What happens during a sync:

1. Your instance determines the `since` timestamp (last successful sync, or the epoch for a first sync) and requests `GET /api/federation/patches/{graph-id}?since=...` from the remote instance.
2. The remote instance exports the matching events from its event log as an **RDF Patch** document, together with an event count and a SHA-256 hash of the patch content.
3. Your instance verifies the hash, filters out any system-namespace triples (see Security below), and applies the remaining inserts and deletes through the event store as a single `federation.sync` event.
4. The applied event is tagged with its **sync source** (the remote instance URL). When the remote instance later pulls from you, events tagged with its own URL are excluded from the export — this prevents changes from ping-ponging in an infinite loop between instances.
5. The graph's last-sync timestamp updates, and a sync alert is sent to the other members.

The result appears as a toast: `Synced: N pulled, M applied`. *Pulled* is the number of remote events fetched; *applied* is the number of triples inserted plus deleted locally.

If the shared graph has more than one remote member, auto-discovery picks the first member whose WebID is an HTTP(S) URL and derives their instance URL from it. You can also target a specific instance via the API body: `{"remote_instance_url": "https://instance-b.example"}`.

---

## The Inbox

The INBOX panel receives four kinds of notifications:

| Type | Icon | Sent when | Actions |
|------|------|-----------|---------|
| **Offer** | ✉️ | Someone invites you to a shared graph | Accept / Decline |
| **Update** | 🔄 | A member changed a shared graph you belong to | Sync Now / Dismiss |
| **Announce** | 📣 | Someone recommends an object to you | Import / Open / Dismiss |
| **Note** | 💬 | Someone sends you a direct message (markdown) | Mark Read / Dismiss |

Each notification has a state — `unread`, `read`, `acted`, or `dismissed`. The badge on the INBOX header counts unread notifications and polls about once a minute. Notifications are stored as named graphs (`urn:sempkm:inbox:{uuid}`) in your triplestore, so they survive restarts and are queryable like any other data.

### Sending Recommendations and Messages

Beyond invitations, you can push two other notification types to any discoverable remote user:

```bash
# Recommend an object
curl -X POST https://your-instance/api/federation/notifications/send \
  -H "Content-Type: application/json" -H "Cookie: sempkm_session=..." \
  -d '{"recipient_handle": "bob@instance-b.example",
       "notification_type": "recommendation",
       "object_iri": "https://your-instance/objects/abc123"}'

# Send a message
curl -X POST https://your-instance/api/federation/notifications/send \
  -H "Content-Type: application/json" -H "Cookie: sempkm_session=..." \
  -d '{"recipient_handle": "bob@instance-b.example",
       "notification_type": "message",
       "content": "Take a look at the new zettel structure!"}'
```

## Contacts

The **Contacts** list in the COLLABORATION panel shows the remote WebIDs you share graphs with, along with their instance URLs. Contacts are derived automatically from shared graph memberships (and recorded when you accept an invitation) — there is no manual add/remove.

## Leaving a Shared Graph

`DELETE /api/federation/shared-graphs/{graph-id}` removes your membership. The data you already synced **stays on your instance as a frozen snapshot** — leaving stops future syncs and invitations but never deletes knowledge you have.

---

## Security

Federation accepts data from other machines, so several layers protect your instance:

- **HTTP Message Signatures (RFC 9421).** Inbound inbox POSTs must be signed with Ed25519. Your instance extracts the sender's WebID from the signature's key ID, fetches their profile, and verifies the signature against the `sec:publicKeyPem` key published there. Keys are cached for one hour; a failed verification retries once with a fresh key to tolerate key rotation. The notification's `actor` field must match the verified sender — you cannot forge a notification on someone else's behalf.
- **Namespace filtering.** Incoming sync triples that touch system-managed namespaces are silently rejected: anything under `urn:sempkm:*` (except `urn:sempkm:shared:*` itself), OWL and SHACL vocabulary IRIs, and any `rdf:type` assertion that would instantiate an OWL/SHACL class. A remote instance cannot inject ontology definitions, shapes, or internal metadata into your graph.
- **Integrity hashes.** Patch exports carry a SHA-256 content hash; a mismatch aborts the sync before anything is applied.
- **SSRF guard.** All outbound federation URLs (remote instances, inboxes, profile fetches) are validated against internal/private address ranges before any request is made.
- **Isolation.** Synced data lands only in the shared graph it belongs to, via the event store — never directly in your private `urn:sempkm:current` graph.

---

## Testing Federation Locally

The repository ships a dedicated Compose stack that runs two complete SemPKM instances (A and B) side by side on a shared Docker network:

```bash
docker compose -f docker-compose.federation-test.yml up -d --build
```

Instance A serves on `http://localhost:3911` and instance B on `http://localhost:3912`. The federation E2E suite (`e2e/tests/18-federation/`) exercises the invite → accept → copy → sync flow against this stack. Note that full cross-instance delivery requires HTTPS for WebFinger and valid HTTP Signatures, so the local tests substitute direct delivery for those steps.

## Troubleshooting

- **"Cannot discover inbox for …"** — the recipient's WebID profile is not published, or their instance is not reachable at `https://{domain}`. Ask them to publish their profile (**Settings > WebID Profile**) and check that their instance is served over HTTPS.
- **Invitation sent but never arrives** — the receiving instance rejects unsigned or unverifiable notifications with `401`. Both instances need published WebID profiles (which carry the Ed25519 public keys) reachable from each other.
- **Sync reports `0 pulled`** — there are no new events for that graph since your last sync, or the remote member has not copied anything into the shared graph yet. Syncing still updates the last-sync timestamp.
- **Sync error "Integrity check failed"** — the patch was corrupted in transit; try again. Repeated failures suggest a proxy modifying response bodies.
- **Objects missing after sync** — triples in system namespaces are filtered on import by design. Regular objects and their properties come through; ontology/shape definitions do not. Make sure both instances have the shared graph's required Mental Model installed so the objects render correctly.

---

## See Also

- [Chapter 25: WebID Profiles](25-webid-profiles.md) — publish the identity and Ed25519 keys that federation depends on
- [Chapter 15: Understanding the Event Log](15-event-log.md) — how synced changes are recorded as events
- [Chapter 31: API Surface](31-api-surface.md) — authenticating scripted calls to the federation API
- [Chapter 20: Production Deployment](20-production-deployment.md) — HTTPS deployment, a prerequisite for cross-instance federation
- [Chapter 18: The SPARQL Endpoint](18-sparql-endpoint.md) — querying shared graphs directly

> **Federated SPARQL queries:** the **Admin > Federation Endpoints** page manages an allowlist of external SPARQL endpoints usable in `SERVICE` clauses and from the SPARQL console. It is configured there or via the `FEDERATION_ALLOWED_ENDPOINTS` environment variable (comma-separated URLs; empty means none allowed).

---

**Previous:** [Chapter 26: IndieAuth](26-indieauth.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
