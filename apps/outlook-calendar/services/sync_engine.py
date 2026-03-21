"""Pull sync engine — fetches Outlook Calendar events and creates/updates bpkm:Event objects.

Orchestrates OutlookClient, field mapper, person matcher, and the bulk
command API into a complete pull sync pipeline.  Commands bypass the
SDK's ``CommandClient`` (which enforces IRI prefix checks) by posting
directly to ``/api/commands/bulk`` via the shared httpx client.

Two-phase bulk for new events:
  Phase 1: ``object.create`` commands (no IRI needed — platform assigns it)
  Phase 2: SPARQL-discover minted IRIs, then submit ``body.set`` / ``edge.create``

For existing events, all commands (patch, body, edge) go in one batch
because the IRI is already known from the SPARQL lookup.

Delta queries:
  Outlook uses ``@odata.deltaLink`` (instead of Google's syncToken).
  Deleted events appear with an ``@removed`` key — we skip those.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

try:
    from services.field_mapper import (
        build_event_properties,
        build_event_patch,
        compute_event_slug,
        extract_body,
        BPKM,
    )
    from services.person_matcher import PersonMatcher
    from services.auth import get_connection_status, refresh_if_expired
    from services.outlook_client import OutlookClient, OutlookAPIError
except ImportError:
    from field_mapper import (
        build_event_properties,
        build_event_patch,
        compute_event_slug,
        extract_body,
        BPKM,
    )
    from person_matcher import PersonMatcher
    from auth import get_connection_status, refresh_if_expired
    from outlook_client import OutlookClient, OutlookAPIError

logger = logging.getLogger("outlook.sync")

BATCH_SIZE = 1000  # Max commands per bulk POST


# ---------------------------------------------------------------------------
# SPARQL lookup
# ---------------------------------------------------------------------------


async def _find_existing_event(graph_client, slug: str) -> dict | None:
    """Check whether an Event with the given slug already exists.

    Uses ``STRENDS`` to match the slug suffix of the IRI without
    needing to know the platform's base namespace.

    Returns ``{"iri": ..., "status": ..., "externalId": ..., "lastSyncedAt": ...}``
    or None.
    """
    sparql = (
        "SELECT ?event ?status ?extId ?lastSynced WHERE {\n"
        f"  ?event a <{BPKM}Event> .\n"
        f'  ?event <{BPKM}externalProvider> "outlook-calendar" .\n'
        f'  FILTER(STRENDS(STR(?event), "/Event/{slug}"))\n'
        f"  OPTIONAL {{ ?event <{BPKM}eventStatus> ?status }}\n"
        f"  OPTIONAL {{ ?event <{BPKM}externalId> ?extId }}\n"
        f"  OPTIONAL {{ ?event <{BPKM}lastSyncedAt> ?lastSynced }}\n"
        "} LIMIT 1"
    )
    result = await graph_client.query(sparql)
    bindings = result.get("results", {}).get("bindings", [])
    if not bindings:
        return None
    row = bindings[0]
    return {
        "iri": row["event"]["value"],
        "status": row.get("status", {}).get("value"),
        "externalId": row.get("extId", {}).get("value"),
        "lastSyncedAt": row.get("lastSynced", {}).get("value"),
    }


# ---------------------------------------------------------------------------
# Command builders
# ---------------------------------------------------------------------------


def _build_create_command(slug: str, properties: dict) -> dict:
    """Build an ``object.create`` command for a new event."""
    return {
        "command": "object.create",
        "params": {
            "type": f"{BPKM}Event",
            "slug": slug,
            "properties": properties,
        },
    }


def _build_update_commands(
    existing_iri: str,
    properties: dict,
    description: str | None,
    attendee_iris: list[str],
    organizer_iri: str | None,
) -> list[dict]:
    """Build patch / body.set / edge.create commands for an existing event."""
    cmds: list[dict] = []

    # Always patch with current properties (idempotent)
    cmds.append({
        "command": "object.patch",
        "params": {"iri": existing_iri, "properties": properties},
    })

    if description:
        cmds.append({
            "command": "body.set",
            "params": {"iri": existing_iri, "body": description},
        })

    for attendee_iri in attendee_iris:
        cmds.append({
            "command": "edge.create",
            "params": {
                "source": existing_iri,
                "predicate": f"{BPKM}attendee",
                "target": attendee_iri,
            },
        })

    if organizer_iri:
        cmds.append({
            "command": "edge.create",
            "params": {
                "source": existing_iri,
                "predicate": f"{BPKM}organizer",
                "target": organizer_iri,
            },
        })

    return cmds


# ---------------------------------------------------------------------------
# Bulk submission
# ---------------------------------------------------------------------------


async def _submit_commands_batched(
    http_client,
    commands: list[dict],
    summary: str,
    source: str,
) -> list[dict]:
    """Submit commands in batches of ≤ BATCH_SIZE.

    Posts directly to ``/api/commands/bulk`` via the shared httpx client,
    bypassing the SDK's IRI prefix checks.
    """
    results = []
    for i in range(0, len(commands), BATCH_SIZE):
        batch = commands[i : i + BATCH_SIZE]
        payload = {
            "commands": batch,
            "summary": summary,
            "source": source,
        }
        resp = await http_client.post("/api/commands/bulk", json=payload)
        resp.raise_for_status()
        results.append(resp.json())
    return results


# ---------------------------------------------------------------------------
# Push sync — change detection + RSVP push-back
# ---------------------------------------------------------------------------


async def _find_changed_events(graph_client) -> list[dict]:
    """Find outlook-calendar events that have local modifications.

    An event is considered changed when:
    - It has ``externalProvider = "outlook-calendar"`` and ``externalId``
    - Its ``dcterms:modified`` > ``bpkm:lastSyncedAt``, or it has no
      ``lastSyncedAt`` (treat as changed)

    Returns a list of dicts with keys:
    ``iri``, ``externalId``, ``calendarName``, ``responseStatus``,
    ``lastSyncedAt``.
    """
    sparql = (
        "SELECT ?event ?extId ?calName ?responseStatus ?lastSynced ?modified WHERE {\n"
        f"  ?event a <{BPKM}Event> .\n"
        f'  ?event <{BPKM}externalProvider> "outlook-calendar" .\n'
        f"  ?event <{BPKM}externalId> ?extId .\n"
        f"  OPTIONAL {{ ?event <{BPKM}calendarName> ?calName }}\n"
        f"  OPTIONAL {{ ?event <{BPKM}responseStatus> ?responseStatus }}\n"
        f"  OPTIONAL {{ ?event <{BPKM}lastSyncedAt> ?lastSynced }}\n"
        f"  OPTIONAL {{ ?event <dcterms:modified> ?modified }}\n"
        f"  FILTER(!BOUND(?lastSynced) || !BOUND(?modified) || STR(?modified) > STR(?lastSynced))\n"
        "}"
    )
    result = await graph_client.query(sparql)
    bindings = result.get("results", {}).get("bindings", [])

    events = []
    for row in bindings:
        events.append({
            "iri": row["event"]["value"],
            "externalId": row["extId"]["value"],
            "calendarName": row.get("calName", {}).get("value"),
            "responseStatus": row.get("responseStatus", {}).get("value"),
            "lastSyncedAt": row.get("lastSynced", {}).get("value"),
        })
    return events


async def push_sync(ctx) -> dict:
    """Run the full bpkm:Event → Outlook Calendar RSVP push pipeline.

    Steps:
      1. Check auth status
      2. Read sync_direction from state — skip if "pull-only"
      3. Read microsoft_email from state (needed for PATCH body)
      4. Refresh access token if needed
      5. Find locally changed events via SPARQL
      6. For each changed event: reverse map → PATCH event → update lastSyncedAt
      7. Store last_push_result in state

    Returns a result dict with ``status``, ``pushed``, ``skipped``,
    ``errors``, and ``timestamp`` fields.
    """
    push_timestamp = datetime.now(timezone.utc).isoformat()

    # 1. Auth check
    status = await get_connection_status(ctx.state)
    if not status["connected"]:
        result = {
            "status": "skipped",
            "pushed": 0,
            "skipped": 0,
            "errors": [],
            "timestamp": push_timestamp,
            "reason": "not connected",
        }
        await ctx.state.set("last_push_result", json.dumps(result))
        return result

    # 2. Read sync direction
    sync_direction = await ctx.state.get("sync_direction")
    if sync_direction == "pull-only":
        result = {
            "status": "skipped",
            "pushed": 0,
            "skipped": 0,
            "errors": [],
            "timestamp": push_timestamp,
            "reason": "sync direction is pull-only",
        }
        await ctx.state.set("last_push_result", json.dumps(result))
        return result

    # 3. Read microsoft_email from state
    microsoft_email = await ctx.state.get("microsoft_email") or ""

    # 4. Refresh access token
    client_id = await ctx.state.get("client_id") or ""
    client_secret = await ctx.state.get("client_secret") or ""
    await refresh_if_expired(ctx.http, ctx.state, client_id, client_secret)

    # Build Outlook client
    outlook_client = OutlookClient(
        http_client=ctx.http,
        state_client=ctx.state,
        client_id=client_id,
        client_secret=client_secret,
    )

    # 5. Find changed events
    changed_events = await _find_changed_events(ctx.graph)
    if not changed_events:
        logger.info("push_sync: no changed events found")
        result = {
            "status": "ok",
            "pushed": 0,
            "skipped": 0,
            "errors": [],
            "timestamp": push_timestamp,
        }
        await ctx.state.set("last_push_result", json.dumps(result))
        return result

    logger.info("push_sync: found %d changed events", len(changed_events))

    # 6. Push each changed event
    http_client = ctx.commands._client  # bypass SDK for bulk commands
    pushed_count = 0
    skipped_count = 0
    errors: list[dict] = []

    for event in changed_events:
        try:
            # Build event_props from SPARQL result
            event_props: dict = {}
            if event.get("responseStatus"):
                event_props[f"{BPKM}responseStatus"] = event["responseStatus"]

            # Reverse map to Outlook PATCH body
            patch_data = build_event_patch(event_props, microsoft_email)
            if not patch_data:
                skipped_count += 1
                continue

            calendar_id = event.get("calendarName")
            event_id = event.get("externalId")
            if not calendar_id or not event_id:
                errors.append({
                    "event_iri": event["iri"],
                    "error": "Missing calendarName or externalId",
                })
                logger.warning(
                    "push_sync: missing calendarName/externalId for %s",
                    event["iri"],
                )
                continue

            # PATCH the event on Outlook Calendar
            await outlook_client.patch_event(calendar_id, event_id, patch_data)

            # Update lastSyncedAt on the pushed event
            update_cmds = [{
                "command": "object.patch",
                "params": {
                    "iri": event["iri"],
                    "properties": {f"{BPKM}lastSyncedAt": push_timestamp},
                },
            }]
            await _submit_commands_batched(
                http_client, update_cmds,
                "Outlook Calendar push: update lastSyncedAt",
                "outlook-calendar",
            )

            pushed_count += 1

        except Exception as e:
            errors.append({"event_iri": event["iri"], "error": str(e)})
            logger.warning(
                "push_sync: error pushing event %s: %s", event["iri"], e,
            )

    # Determine overall status
    if not errors:
        overall_status = "ok"
    elif pushed_count > 0:
        overall_status = "partial"
    else:
        overall_status = "error"

    result = {
        "status": overall_status,
        "pushed": pushed_count,
        "skipped": skipped_count,
        "errors": errors,
        "timestamp": push_timestamp,
    }

    await ctx.state.set("last_push_result", json.dumps(result))
    logger.info(
        "Push sync complete: status=%s pushed=%d skipped=%d errors=%d",
        overall_status, pushed_count, skipped_count, len(errors),
    )
    return result


# ---------------------------------------------------------------------------
# Main pull sync
# ---------------------------------------------------------------------------


async def pull_sync(ctx) -> dict:
    """Run the full Outlook Calendar → bpkm:Event pull sync pipeline.

    Steps:
      1. Check auth status
      2. Read selected calendars from state
      3. Refresh access token if needed
      4. For each calendar: fetch events via delta query, classify, build commands
      5. Phase 1: submit object.create commands
      6. Phase 2: discover IRIs of new events, submit body.set / edge.create
      7. Submit update commands
      8. Store delta links and result

    Returns a result dict with ``status``, ``created``, ``updated``,
    ``unchanged``, ``errors``, and ``timestamp`` fields.
    """
    # 1. Auth check
    status = await get_connection_status(ctx.state)
    if not status["connected"]:
        return {"status": "skipped", "reason": "not connected"}

    # 2. Read selected calendars
    selected_json = await ctx.state.get("selected_calendars")
    if not selected_json:
        return {
            "status": "ok",
            "message": "No calendars selected",
            "created": 0,
            "updated": 0,
        }
    selected_calendars = json.loads(selected_json)
    if not selected_calendars:
        return {
            "status": "ok",
            "message": "No calendars selected",
            "created": 0,
            "updated": 0,
        }

    # 3. Refresh access token
    client_id = await ctx.state.get("client_id") or ""
    client_secret = await ctx.state.get("client_secret") or ""
    await refresh_if_expired(ctx.http, ctx.state, client_id, client_secret)

    # 4. Build clients
    outlook_client = OutlookClient(
        http_client=ctx.http,
        state_client=ctx.state,
        client_id=client_id,
        client_secret=client_secret,
    )
    person_matcher = PersonMatcher(ctx.graph, ctx.commands)
    http_client = ctx.commands._client  # bypass SDK for bulk commands

    create_commands: list[dict] = []
    update_commands: list[dict] = []
    created_count = 0
    updated_count = 0
    unchanged_count = 0
    errors: list[dict] = []

    # Phase 2 deferred data (for newly created events)
    new_event_descriptions: dict[str, str] = {}  # slug → description
    new_event_attendee_iris: dict[str, list[str]] = {}  # slug → [Person IRI]
    new_event_organizer_iris: dict[str, str] = {}  # slug → Person IRI

    sync_timestamp = datetime.now(timezone.utc).isoformat()

    for calendar_id in selected_calendars:
        # Read per-calendar delta link
        delta_link_key = f"delta_link:{calendar_id}"
        delta_link = await ctx.state.get(delta_link_key)

        # Fetch events via delta query (with expired delta recovery)
        try:
            events, new_delta_link = await outlook_client.get_events_delta(
                calendar_id, delta_link=delta_link
            )
        except OutlookAPIError as e:
            if e.status_code == 410:
                logger.info(
                    "Delta link expired for calendar %s — performing full sync",
                    calendar_id,
                )
                await ctx.state.set(delta_link_key, "")
                events, new_delta_link = await outlook_client.get_events_delta(
                    calendar_id, delta_link=None
                )
            else:
                raise

        logger.info(
            "Fetched %d events from calendar %s (delta=%s)",
            len(events),
            calendar_id,
            "incremental" if delta_link else "full",
        )

        # Get calendar name for field mapping
        calendar_name = calendar_id  # default to ID

        # Process each event
        for event in events:
            try:
                # Deleted events: @removed key present → skip
                if "@removed" in event:
                    logger.debug(
                        "Skipping removed event %s",
                        event.get("id", "unknown"),
                    )
                    continue

                event_id = event.get("id", "")
                slug = compute_event_slug(calendar_id, event_id)
                existing = await _find_existing_event(ctx.graph, slug)

                properties = build_event_properties(
                    event, calendar_name, sync_time=sync_timestamp
                )
                description = extract_body(event)

                # Process attendees — Outlook uses nested emailAddress structure
                attendee_iris: list[str] = []
                for attendee in event.get("attendees", []):
                    email_addr = attendee.get("emailAddress", {})
                    att_email = email_addr.get("address")
                    att_name = email_addr.get("name")
                    att_iri = await person_matcher.match_or_create(
                        att_email, att_name
                    )
                    if att_iri:
                        attendee_iris.append(att_iri)

                # Process organizer — Outlook uses nested emailAddress structure
                organizer_iri: str | None = None
                organizer = event.get("organizer")
                if organizer:
                    org_email_addr = organizer.get("emailAddress", {})
                    org_email = org_email_addr.get("address")
                    org_name = org_email_addr.get("name")
                    # Skip if organizer is self (same as connected user)
                    microsoft_email = await ctx.state.get("microsoft_email") or ""
                    if org_email and org_email.lower() != microsoft_email.lower():
                        organizer_iri = await person_matcher.match_or_create(
                            org_email, org_name
                        )

                if existing:
                    # Loop prevention: skip events where Outlook's
                    # lastModifiedDateTime is not newer than our lastSyncedAt.
                    last_synced = existing.get("lastSyncedAt")
                    outlook_updated = event.get("lastModifiedDateTime")
                    if last_synced and outlook_updated and outlook_updated <= last_synced:
                        unchanged_count += 1
                        continue

                    # Update existing event
                    update_commands.extend(
                        _build_update_commands(
                            existing["iri"],
                            properties,
                            description,
                            attendee_iris,
                            organizer_iri,
                        )
                    )
                    updated_count += 1
                else:
                    # New event — create in phase 1, defer body/edges to phase 2
                    create_commands.append(
                        _build_create_command(slug, properties)
                    )
                    if description:
                        new_event_descriptions[slug] = description
                    if attendee_iris:
                        new_event_attendee_iris[slug] = attendee_iris
                    if organizer_iri:
                        new_event_organizer_iris[slug] = organizer_iri
                    created_count += 1

            except Exception as e:
                event_id = event.get("id", "unknown")
                errors.append({"event_id": event_id, "error": str(e)})
                logger.warning(
                    "Error processing event %s: %s", event_id, e
                )

        # Store per-calendar delta link
        if new_delta_link:
            await ctx.state.set(delta_link_key, new_delta_link)

    # 5. Phase 1: submit create commands
    if create_commands:
        await _submit_commands_batched(
            http_client,
            create_commands,
            f"Outlook Calendar sync: created {len(create_commands)} events",
            "outlook-calendar",
        )

    # 6. Phase 2: discover IRIs of new events, submit body.set / edge.create
    phase2_commands: list[dict] = []
    for slug, desc in new_event_descriptions.items():
        event_info = await _find_existing_event(ctx.graph, slug)
        if event_info:
            phase2_commands.append({
                "command": "body.set",
                "params": {"iri": event_info["iri"], "body": desc},
            })

    for slug, att_iris in new_event_attendee_iris.items():
        event_info = await _find_existing_event(ctx.graph, slug)
        if event_info:
            for att_iri in att_iris:
                phase2_commands.append({
                    "command": "edge.create",
                    "params": {
                        "source": event_info["iri"],
                        "predicate": f"{BPKM}attendee",
                        "target": att_iri,
                    },
                })

    for slug, org_iri in new_event_organizer_iris.items():
        event_info = await _find_existing_event(ctx.graph, slug)
        if event_info:
            phase2_commands.append({
                "command": "edge.create",
                "params": {
                    "source": event_info["iri"],
                    "predicate": f"{BPKM}organizer",
                    "target": org_iri,
                },
            })

    # 7. Submit update + phase 2 commands
    all_follow_up = update_commands + phase2_commands
    if all_follow_up:
        await _submit_commands_batched(
            http_client,
            all_follow_up,
            f"Outlook Calendar sync: updated {updated_count} events, "
            f"{len(phase2_commands)} follow-ups",
            "outlook-calendar",
        )

    # 8. Store sync state
    await ctx.state.set("last_sync_at", sync_timestamp)

    result = {
        "status": "ok" if not errors else ("partial" if created_count + updated_count > 0 else "error"),
        "created": created_count,
        "updated": updated_count,
        "unchanged": unchanged_count,
        "errors": errors,
        "timestamp": sync_timestamp,
    }
    logger.info("Pull sync complete: %s", result)
    await ctx.state.set("last_pull_result", json.dumps(result))
    return result
