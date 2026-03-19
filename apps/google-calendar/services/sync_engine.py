"""Pull sync engine — fetches Google Calendar events and creates/updates bpkm:Event objects.

Orchestrates GCalClient, field mapper, person matcher, and the bulk
command API into a complete pull sync pipeline.  Commands bypass the
SDK's ``CommandClient`` (which enforces IRI prefix checks) by posting
directly to ``/api/commands/bulk`` via the shared httpx client.

Two-phase bulk for new events:
  Phase 1: ``object.create`` commands (no IRI needed — platform assigns it)
  Phase 2: SPARQL-discover minted IRIs, then submit ``body.set`` / ``edge.create``

For existing events, all commands (patch, body, edge) go in one batch
because the IRI is already known from the SPARQL lookup.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

try:
    from services.field_mapper import (
        build_event_properties,
        compute_event_slug,
        extract_body,
        BPKM,
    )
    from services.person_matcher import PersonMatcher
    from services.auth import get_connection_status, refresh_if_expired
    from services.gcal_client import GCalClient, GCalAPIError
except ImportError:
    from field_mapper import (
        build_event_properties,
        compute_event_slug,
        extract_body,
        BPKM,
    )
    from person_matcher import PersonMatcher
    from auth import get_connection_status, refresh_if_expired
    from gcal_client import GCalClient, GCalAPIError

logger = logging.getLogger("google_calendar.sync")

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
        f'  ?event <{BPKM}externalProvider> "google-calendar" .\n'
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
# Main pull sync
# ---------------------------------------------------------------------------


async def pull_sync(ctx) -> dict:
    """Run the full Google Calendar → bpkm:Event pull sync pipeline.

    Steps:
      1. Check auth status
      2. Read selected calendars from state
      3. Refresh access token if needed
      4. For each calendar: fetch events, classify, build commands
      5. Phase 1: submit object.create commands
      6. Phase 2: discover IRIs of new events, submit body.set / edge.create
      7. Submit update commands
      8. Store sync tokens and result

    Returns a result dict with ``status``, ``created``, ``updated``,
    ``unchanged``, and ``errors`` fields.
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
    gcal_client = GCalClient(
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
        # Read per-calendar sync token
        sync_token_key = f"sync_token:{calendar_id}"
        sync_token = await ctx.state.get(sync_token_key)

        # Fetch events (with 410 retry)
        try:
            events, next_sync_token = await gcal_client.get_events(
                calendar_id, sync_token=sync_token
            )
        except GCalAPIError as e:
            if e.status_code == 410:
                logger.info(
                    "SyncToken expired for calendar %s — performing full sync",
                    calendar_id,
                )
                await ctx.state.set(sync_token_key, "")
                events, next_sync_token = await gcal_client.get_events(
                    calendar_id, sync_token=None
                )
            else:
                raise

        logger.info(
            "Fetched %d events from calendar %s (sync_token=%s)",
            len(events),
            calendar_id,
            "incremental" if sync_token else "full",
        )

        # Get calendar name for field mapping
        calendar_name = calendar_id  # default to ID

        # Process each event
        for event in events:
            try:
                event_id = event.get("id", "")
                slug = compute_event_slug(calendar_id, event_id)
                existing = await _find_existing_event(ctx.graph, slug)

                properties = build_event_properties(
                    event, calendar_name, sync_time=sync_timestamp
                )
                description = extract_body(event)

                # Process attendees (non-self)
                attendee_iris: list[str] = []
                for attendee in event.get("attendees", []):
                    if attendee.get("self"):
                        continue
                    att_email = attendee.get("email")
                    att_name = attendee.get("displayName")
                    att_iri = await person_matcher.match_or_create(
                        att_email, att_name
                    )
                    if att_iri:
                        attendee_iris.append(att_iri)

                # Process organizer
                organizer_iri: str | None = None
                organizer = event.get("organizer")
                if organizer and not organizer.get("self"):
                    org_email = organizer.get("email")
                    org_name = organizer.get("displayName")
                    organizer_iri = await person_matcher.match_or_create(
                        org_email, org_name
                    )

                if existing:
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

        # Store per-calendar sync token
        if next_sync_token:
            await ctx.state.set(sync_token_key, next_sync_token)

    # 5. Phase 1: submit create commands
    if create_commands:
        await _submit_commands_batched(
            http_client,
            create_commands,
            f"Google Calendar sync: created {len(create_commands)} events",
            "google-calendar",
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
            f"Google Calendar sync: updated {updated_count} events, "
            f"{len(phase2_commands)} follow-ups",
            "google-calendar",
        )

    # 8. Store sync state
    await ctx.state.set("last_sync_at", sync_timestamp)

    result = {
        "status": "ok",
        "created": created_count,
        "updated": updated_count,
        "unchanged": unchanged_count,
        "errors": errors,
    }
    logger.info("Pull sync complete: %s", result)
    await ctx.state.set("last_pull_result", json.dumps(result))
    return result
