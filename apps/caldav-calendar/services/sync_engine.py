"""Pull sync engine — fetches CalDAV events and creates/updates bpkm:Event objects.

Orchestrates CalDAVClient, field mapper, person matcher, and the bulk
command API into a complete pull sync pipeline.  Commands bypass the
SDK's ``CommandClient`` (which enforces IRI prefix checks) by posting
directly to ``/api/commands/bulk`` via the shared httpx client (D204).

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

import icalendar

try:
    from services.field_mapper import (
        build_event_properties,
        build_event_patch,
        compute_event_slug,
        extract_body,
        extract_attendees,
        extract_organizer,
        modify_vevent_partstat,
        BPKM,
    )
    from services.person_matcher import PersonMatcher
    from services.auth import get_connection_status
    from services.caldav_client import CalDAVClient, CalDAVError, CalDAVConflictError
except ImportError:
    from field_mapper import (
        build_event_properties,
        build_event_patch,
        compute_event_slug,
        extract_body,
        extract_attendees,
        extract_organizer,
        modify_vevent_partstat,
        BPKM,
    )
    from person_matcher import PersonMatcher
    from auth import get_connection_status
    from caldav_client import CalDAVClient, CalDAVError, CalDAVConflictError

logger = logging.getLogger("caldav.sync.engine")

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
        f'  ?event <{BPKM}externalProvider> "caldav" .\n'
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


async def _find_changed_events(graph_client) -> list[dict]:
    """Find CalDAV events that have local modifications needing push-back.

    An event is considered changed when:
    - It has ``externalProvider = "caldav"`` and ``externalId``
    - Its ``dcterms:modified`` > ``bpkm:lastSyncedAt``, or it has no
      ``lastSyncedAt`` (treat as changed)

    Returns a list of dicts with keys:
    ``iri``, ``externalId``, ``externalUrl``, ``calendarName``,
    ``responseStatus``, ``lastSyncedAt``.
    """
    sparql = (
        "SELECT ?event ?extId ?extUrl ?calName ?responseStatus ?lastSynced ?modified WHERE {\n"
        f"  ?event a <{BPKM}Event> .\n"
        f'  ?event <{BPKM}externalProvider> "caldav" .\n'
        f"  ?event <{BPKM}externalId> ?extId .\n"
        f"  OPTIONAL {{ ?event <{BPKM}externalUrl> ?extUrl }}\n"
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
            "externalUrl": row.get("extUrl", {}).get("value"),
            "calendarName": row.get("calName", {}).get("value"),
            "responseStatus": row.get("responseStatus", {}).get("value"),
            "lastSyncedAt": row.get("lastSynced", {}).get("value"),
        })
    return events


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
    bypassing the SDK's IRI prefix checks (D204).
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
# Push sync — write local RSVP changes back to CalDAV server
# ---------------------------------------------------------------------------


async def push_sync(ctx) -> dict:
    """Push local RSVP changes back to the CalDAV server.

    Detects locally modified events via SPARQL, fetches the current
    .ics from the CalDAV server, modifies the ATTENDEE PARTSTAT,
    PUTs the full VCALENDAR back with ETag concurrency control, and
    updates lastSyncedAt.

    Steps:
      1. Check auth status
      2. Read sync_direction — skip if "pull-only"
      3. Read user_email from state ("username")
      4. Build CalDAVClient
      5. Find changed events via SPARQL
      6. For each event: reverse-map → GET → modify PARTSTAT → PUT with ETag
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

    # 3. Read user email (CalDAV account username)
    user_email = await ctx.state.get("username") or ""

    # 4. Build CalDAV client
    client = CalDAVClient(http_client=ctx.http, state_client=ctx.state)

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

            # Reverse map to iCalendar PARTSTAT
            patch_data = build_event_patch(event_props, user_email)
            if not patch_data:
                skipped_count += 1
                continue

            # CalDAV requires the event URL for GET/PUT
            external_url = event.get("externalUrl")
            if not external_url:
                errors.append({
                    "event_iri": event["iri"],
                    "error": "Missing externalUrl — cannot push to CalDAV server",
                })
                logger.warning(
                    "push_sync: missing externalUrl for %s", event["iri"],
                )
                continue

            # Fetch current .ics with ETag
            event_resource = await client.get_event(external_url)
            current_etag = event_resource["etag"]
            current_ics = event_resource["calendar_data"]

            # Modify the ATTENDEE PARTSTAT in the .ics
            modified_ics = modify_vevent_partstat(
                current_ics, user_email, patch_data["responseStatus"]
            )

            # PUT the modified .ics back with If-Match ETag
            try:
                await client.put_event(external_url, modified_ics, current_etag)
            except CalDAVConflictError:
                errors.append({
                    "event_iri": event["iri"],
                    "error": f"ETag conflict (412) — event was modified concurrently",
                })
                logger.warning(
                    "push_sync: ETag conflict pushing event %s",
                    event["iri"],
                )
                continue

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
                "CalDAV push: update lastSyncedAt",
                "caldav-calendar",
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
    """Run the full CalDAV → bpkm:Event pull sync pipeline.

    Steps:
      1. Check auth status
      2. Read selected calendars from state
      3. For each calendar: fetch events with sync-token, classify, build commands
      4. Phase 1: submit object.create commands
      5. Phase 2: discover IRIs of new events, submit body.set / edge.create
      6. Submit update commands
      7. Store sync tokens and result

    Returns a result dict with ``status``, ``created``, ``updated``,
    ``unchanged``, ``errors``, and ``timestamp`` fields.
    """
    sync_timestamp = datetime.now(timezone.utc).isoformat()

    # 1. Auth check
    status = await get_connection_status(ctx.state)
    if not status["connected"]:
        result = {
            "status": "skipped",
            "reason": "not connected",
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "errors": [],
            "timestamp": sync_timestamp,
        }
        await ctx.state.set("last_pull_result", json.dumps(result))
        return result

    # 2. Read selected calendars (JSON list of dicts with href/name)
    selected_json = await ctx.state.get("selected_calendars")
    if not selected_json:
        result = {
            "status": "ok",
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "errors": [],
            "timestamp": sync_timestamp,
        }
        await ctx.state.set("last_pull_result", json.dumps(result))
        return result

    selected_calendars = json.loads(selected_json)
    if not selected_calendars:
        result = {
            "status": "ok",
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "errors": [],
            "timestamp": sync_timestamp,
        }
        await ctx.state.set("last_pull_result", json.dumps(result))
        return result

    # 3. Build clients
    client = CalDAVClient(http_client=ctx.http, state_client=ctx.state)
    person_matcher = PersonMatcher(ctx.graph, ctx.commands)
    http_client = ctx.commands._client  # bypass SDK for bulk commands

    # Read user email for self-attendee filtering
    user_email = await ctx.state.get("username") or ""

    create_commands: list[dict] = []
    update_commands: list[dict] = []
    created_count = 0
    updated_count = 0
    unchanged_count = 0
    errors: list[dict] = []

    # Phase 2 deferred data (for newly created events)
    new_event_descriptions: dict[str, str] = {}    # slug → description
    new_event_attendee_iris: dict[str, list[str]] = {}  # slug → [Person IRI]
    new_event_organizer_iris: dict[str, str] = {}   # slug → Person IRI

    # selected_calendars can be:
    #   - list of strings (plain hrefs from S01's calendar checkbox form)
    #   - list of dicts with href/name (richer format)
    # Normalize to list of (href, name) tuples.
    cal_list: list[tuple[str, str]] = []
    for entry in selected_calendars:
        if isinstance(entry, dict):
            cal_list.append((entry.get("href", ""), entry.get("name", entry.get("href", ""))))
        else:
            cal_list.append((str(entry), str(entry)))

    for calendar_href, calendar_name in cal_list:
        # Read per-calendar sync token
        sync_token_key = f"sync_token:{calendar_href}"
        sync_token = await ctx.state.get(sync_token_key)

        # Fetch events (with 410 retry)
        try:
            events, next_sync_token = await client.get_events(
                calendar_href, sync_token=sync_token
            )
        except CalDAVError as e:
            if e.status_code == 410:
                logger.info(
                    "Sync-token expired for calendar %s — performing full sync",
                    calendar_href,
                )
                await ctx.state.set(sync_token_key, "")
                events, next_sync_token = await client.get_events(
                    calendar_href, sync_token=None
                )
            else:
                errors.append({"calendar": calendar_href, "error": str(e)})
                logger.warning(
                    "Error fetching events from %s: %s", calendar_href, e
                )
                continue

        logger.info(
            "Fetched %d entries from calendar %s (sync_token=%s)",
            len(events),
            calendar_href,
            "incremental" if sync_token else "full",
        )

        # Process each event entry
        for event_entry in events:
            # Skip deleted resources (sync-collection returns status with "404")
            entry_status = event_entry.get("status", "")
            if "404" in entry_status:
                logger.debug(
                    "Skipping deleted resource %s", event_entry.get("href", "")
                )
                continue

            # Skip entries without calendar data
            ics_text = event_entry.get("calendar_data", "")
            if not ics_text:
                continue

            # Parse iCalendar data
            try:
                cal = icalendar.Calendar.from_ical(ics_text)
            except Exception as exc:
                errors.append({
                    "href": event_entry.get("href", ""),
                    "error": f"iCalendar parse error: {exc}",
                })
                logger.warning(
                    "Failed to parse iCalendar from %s: %s",
                    event_entry.get("href", ""), exc,
                )
                continue

            # Walk VEVENT components
            for component in cal.walk():
                if component.name != "VEVENT":
                    continue

                try:
                    # Extract UID for slug computation
                    uid_prop = component.get("UID")
                    if not uid_prop:
                        continue
                    uid = str(uid_prop)
                    slug = compute_event_slug(calendar_href, uid)

                    # Build properties from field mapper
                    properties = build_event_properties(
                        component, calendar_name,
                        sync_time=sync_timestamp,
                        user_email=user_email,
                    )

                    # Remove attendees/organizer dicts from properties —
                    # those are handled separately via person matcher + edges
                    attendee_dicts = properties.pop(f"{BPKM}attendees", [])
                    organizer_dict = properties.pop(f"{BPKM}organizer", None)

                    # Remove body from flat properties — handled via body.set
                    body_text = properties.pop(f"{BPKM}body", None)
                    # Also extract via the dedicated function for completeness
                    if body_text is None:
                        body_text = extract_body(component)

                    description = body_text

                    # Check for existing event
                    existing = await _find_existing_event(ctx.graph, slug)

                    if existing:
                        # Loop prevention: skip if lastSyncedAt >= event modified date
                        last_synced = existing.get("lastSyncedAt")
                        modified_prop = component.get("LAST-MODIFIED")
                        if last_synced and modified_prop:
                            event_modified = modified_prop.dt.isoformat()
                            if event_modified <= last_synced:
                                unchanged_count += 1
                                continue

                        # Process attendees via PersonMatcher
                        attendee_iris: list[str] = []
                        for att in attendee_dicts:
                            att_email = att.get("email", "")
                            # Exclude self by email match
                            if user_email and att_email.lower() == user_email.lower():
                                continue
                            att_name = att.get("name")
                            att_iri = await person_matcher.match_or_create(
                                att_email, att_name
                            )
                            if att_iri:
                                attendee_iris.append(att_iri)

                        # Process organizer
                        organizer_iri: str | None = None
                        if organizer_dict:
                            org_email = organizer_dict.get("email", "")
                            if not (user_email and org_email.lower() == user_email.lower()):
                                org_name = organizer_dict.get("name")
                                organizer_iri = await person_matcher.match_or_create(
                                    org_email, org_name
                                )

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

                        # Process attendees for phase 2
                        attendee_iris_new: list[str] = []
                        for att in attendee_dicts:
                            att_email = att.get("email", "")
                            if user_email and att_email.lower() == user_email.lower():
                                continue
                            att_name = att.get("name")
                            att_iri = await person_matcher.match_or_create(
                                att_email, att_name
                            )
                            if att_iri:
                                attendee_iris_new.append(att_iri)

                        organizer_iri_new: str | None = None
                        if organizer_dict:
                            org_email = organizer_dict.get("email", "")
                            if not (user_email and org_email.lower() == user_email.lower()):
                                org_name = organizer_dict.get("name")
                                organizer_iri_new = await person_matcher.match_or_create(
                                    org_email, org_name
                                )

                        create_commands.append(
                            _build_create_command(slug, properties)
                        )
                        if description:
                            new_event_descriptions[slug] = description
                        if attendee_iris_new:
                            new_event_attendee_iris[slug] = attendee_iris_new
                        if organizer_iri_new:
                            new_event_organizer_iris[slug] = organizer_iri_new
                        created_count += 1

                except Exception as exc:
                    href = event_entry.get("href", "unknown")
                    errors.append({"href": href, "error": str(exc)})
                    logger.warning(
                        "Error processing event from %s: %s", href, exc,
                    )

        # Store per-calendar sync token
        if next_sync_token:
            await ctx.state.set(sync_token_key, next_sync_token)

    # 4. Phase 1: submit create commands
    if create_commands:
        await _submit_commands_batched(
            http_client,
            create_commands,
            f"CalDAV sync: created {len(create_commands)} events",
            "caldav-calendar",
        )

    # 5. Phase 2: discover IRIs of new events, submit body.set / edge.create
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

    # 6. Submit update + phase 2 commands
    all_follow_up = update_commands + phase2_commands
    if all_follow_up:
        await _submit_commands_batched(
            http_client,
            all_follow_up,
            f"CalDAV sync: updated {updated_count} events, "
            f"{len(phase2_commands)} follow-ups",
            "caldav-calendar",
        )

    # 7. Store sync state
    await ctx.state.set("last_sync_at", sync_timestamp)

    result = {
        "status": "ok",
        "created": created_count,
        "updated": updated_count,
        "unchanged": unchanged_count,
        "errors": errors,
        "timestamp": sync_timestamp,
    }
    logger.info("Pull sync complete: %s", result)
    await ctx.state.set("last_pull_result", json.dumps(result))
    return result
