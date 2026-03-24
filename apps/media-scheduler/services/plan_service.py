"""Plan generation service — daily media plan creation from schedule rules.

Orchestration flow:
1. Fetch current context from platform API
2. Load + evaluate schedule rules against context
3. For each matched rule, build SPARQL to select queued MediaItems
4. Collect items (dedup by IRI), allocate time slots
5. Patch existing plan entries to "replaced" if regenerating
6. Bulk-create DailyMediaPlan + PlanEntry objects via CommandClient

Pure functions (no SDK dependency):
- ``mint_plan_iri(date_str)`` — deterministic plan IRI
- ``mint_entry_iri(date_str, order)`` — deterministic entry IRI
- ``build_item_query(action, limit)`` — SPARQL SELECT for queued items
- ``allocate_slots(items, start_hour)`` — time-slot assignment

I/O boundary functions (require SDK clients):
- ``fetch_context(http_client)`` — GET /api/context/current
- ``get_existing_plan_entries(graph_client, plan_iri)`` — SPARQL for existing entries
- ``generate_plan(ctx, date_str, context_override)`` — full orchestration

Constants:
- ``DEFAULT_DURATIONS`` — media-type default durations in seconds
- ``PLAN_START_HOUR`` — default plan start hour (08:00)
- ``MAX_ITEMS_PER_RULE`` — cap on items selected per matched rule
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ── Import rules_service (same importlib fallback as app.py) ──

try:
    from services.rules_service import evaluate_rules, load_rules
except ModuleNotFoundError:
    import importlib.util as _ilu
    import pathlib as _pl

    _rsvc = _pl.Path(__file__).resolve().parent / "rules_service.py"
    _rsp = _ilu.spec_from_file_location("_rules_service_fallback", _rsvc)
    _rfm = _ilu.module_from_spec(_rsp)
    _rsp.loader.exec_module(_rfm)
    evaluate_rules = _rfm.evaluate_rules
    load_rules = _rfm.load_rules

# ── Import constants from podcast_service ──

try:
    from services.podcast_service import MEDIA_ITEM_TYPE, MS_NS
except ModuleNotFoundError:
    import importlib.util as _ilu2
    import pathlib as _pl2

    _psvc = _pl2.Path(__file__).resolve().parent / "podcast_service.py"
    _psp = _ilu2.spec_from_file_location("_podcast_service_fallback", _psvc)
    _pfm = _ilu2.module_from_spec(_psp)
    _psp.loader.exec_module(_pfm)
    MEDIA_ITEM_TYPE = _pfm.MEDIA_ITEM_TYPE
    MS_NS = _pfm.MS_NS


# ── Constants ──

DEFAULT_DURATIONS: dict[str, int] = {
    "podcast": 1800,   # 30 minutes
    "youtube": 900,    # 15 minutes
    "spotify": 240,    # 4 minutes
}

PLAN_START_HOUR: int = 8
MAX_ITEMS_PER_RULE: int = 5

PLAN_IRI_TEMPLATE = "urn:sempkm:app:media-scheduler:plan-{date_str}"
ENTRY_IRI_TEMPLATE = "urn:sempkm:app:media-scheduler:entry-{date_str}-{order:03d}"

DAILY_MEDIA_PLAN_TYPE = f"{MS_NS}DailyMediaPlan"
PLAN_ENTRY_TYPE = f"{MS_NS}PlanEntry"


# ── IRI minting ──


def mint_plan_iri(date_str: str) -> str:
    """Mint a deterministic DailyMediaPlan IRI from a date string.

    Args:
        date_str: Date in YYYY-MM-DD format.

    Returns:
        IRI like ``urn:sempkm:app:media-scheduler:plan-2026-03-23``.
    """
    return PLAN_IRI_TEMPLATE.format(date_str=date_str)


def mint_entry_iri(date_str: str, order: int) -> str:
    """Mint a deterministic PlanEntry IRI from a date string and order.

    Args:
        date_str: Date in YYYY-MM-DD format.
        order: Zero-based ordinal position within the plan.

    Returns:
        IRI like ``urn:sempkm:app:media-scheduler:entry-2026-03-23-001``.
    """
    return ENTRY_IRI_TEMPLATE.format(date_str=date_str, order=order)


# ── SPARQL query building ──


def build_item_query(action: dict[str, str], limit: int = MAX_ITEMS_PER_RULE) -> str:
    """Build a SPARQL SELECT for queued MediaItems matching a rule's action.

    Action types:
    - ``source_type``: filter by source's sourceType (e.g. "podcast")
    - ``source_iri``: filter by specific source IRI
    - ``category``: filter by source's category IRI

    Always filters for ``ms:status = "queued"`` and orders by
    ``dcterms:created DESC``.

    Args:
        action: Rule action dict with ``type`` and ``value`` keys.
        limit: Maximum items to return (default: MAX_ITEMS_PER_RULE).

    Returns:
        SPARQL SELECT query string.

    Raises:
        ValueError: If action type is unknown or action is empty.
    """
    action_type = action.get("type", "")
    action_value = action.get("value", "")

    if not action_type or not action_value:
        raise ValueError(f"Action must have 'type' and 'value', got: {action!r}")

    # Base pattern: select queued items with title, source, duration, sourceType
    base = f"""SELECT ?item ?title ?sourceType ?duration WHERE {{
    ?item a <{MEDIA_ITEM_TYPE}> .
    ?item <{MS_NS}status> "queued" .
    ?item <{MS_NS}mediaSource> ?source .
    ?source <{MS_NS}sourceType> ?sourceType .
    OPTIONAL {{ ?item <http://purl.org/dc/terms/title> ?title }}
    OPTIONAL {{ ?item <{MS_NS}duration> ?duration }}"""

    if action_type == "source_type":
        filter_clause = f'    FILTER(?sourceType = "{action_value}")'
    elif action_type == "source_iri":
        filter_clause = f"    FILTER(?source = <{action_value}>)"
    elif action_type == "category":
        # Category is on the source, not the item
        filter_clause = (
            f"    ?source <{MS_NS}category> ?category .\n"
            f"    FILTER(?category = <{action_value}>)"
        )
    else:
        raise ValueError(f"Unknown action type: {action_type!r}")

    return f"""{base}
{filter_clause}
}} ORDER BY DESC(?title) LIMIT {limit}"""


# ── Slot allocation ──


def allocate_slots(
    items: list[dict[str, Any]],
    start_hour: int = PLAN_START_HOUR,
) -> list[dict[str, Any]]:
    """Assign time slots to a list of items sequentially.

    Each item gets a start/end time. The first item starts at
    ``start_hour:00``. Each subsequent item starts where the previous
    one ended. Duration comes from the item's ``duration`` field or
    falls back to DEFAULT_DURATIONS based on ``source_type``.

    Args:
        items: List of dicts with keys: ``item_iri``, ``title``,
            ``source_type``, ``duration`` (optional, seconds),
            ``rule_id`` (optional).
        start_hour: Hour (0-23) at which the plan starts.

    Returns:
        List of slot dicts with: ``item_iri``, ``title``, ``source_type``,
        ``duration``, ``slot_start`` (HH:MM), ``slot_end`` (HH:MM),
        ``slot_order``, ``rule_id``.
    """
    slots: list[dict[str, Any]] = []
    current_seconds = start_hour * 3600  # seconds since midnight

    for i, item in enumerate(items):
        # Determine duration: item's own or default by source type
        duration = item.get("duration")
        if duration is None or duration <= 0:
            source_type = item.get("source_type", "")
            duration = DEFAULT_DURATIONS.get(source_type, 1800)  # fallback 30min

        slot_start_h = current_seconds // 3600
        slot_start_m = (current_seconds % 3600) // 60
        slot_start = f"{slot_start_h:02d}:{slot_start_m:02d}"

        end_seconds = current_seconds + duration
        slot_end_h = end_seconds // 3600
        slot_end_m = (end_seconds % 3600) // 60
        slot_end = f"{slot_end_h:02d}:{slot_end_m:02d}"

        slots.append({
            "item_iri": item.get("item_iri", ""),
            "title": item.get("title", ""),
            "source_type": item.get("source_type", ""),
            "duration": duration,
            "slot_start": slot_start,
            "slot_end": slot_end,
            "slot_order": i,
            "rule_id": item.get("rule_id", ""),
        })

        current_seconds = end_seconds

    return slots


# ── Context fetching ──


async def fetch_context(http_client: Any) -> dict[str, Any]:
    """Fetch current context from the platform API.

    Calls ``GET /api/context/current`` via the app's HTTP client.
    Returns an empty dict on any failure (logged as warning, not raised).

    Args:
        http_client: SDK HttpClient (ctx.http) with platform base URL.

    Returns:
        Context dict or empty dict on failure.
    """
    try:
        response = await http_client.get("/api/context/current")
        if hasattr(response, "status_code") and response.status_code >= 400:
            logger.warning(
                "Context fetch failed: HTTP %d", response.status_code
            )
            return {}
        # httpx-style response: .json() method
        if hasattr(response, "json"):
            data = response.json()
            if callable(data):
                data = data()
            if isinstance(data, dict):
                return data
        return {}
    except Exception as exc:
        logger.warning("Context fetch error: %s", exc)
        return {}


# ── Existing plan query ──


async def get_existing_plan_entries(
    graph_client: Any, plan_iri: str
) -> list[str]:
    """Query the triplestore for existing PlanEntry IRIs belonging to a plan.

    Args:
        graph_client: SDK GraphClient with SPARQL read access.
        plan_iri: IRI of the DailyMediaPlan.

    Returns:
        List of PlanEntry IRI strings.
    """
    sparql = f"""
    SELECT ?entry WHERE {{
        ?entry a <{PLAN_ENTRY_TYPE}> .
        ?entry <{MS_NS}plan> <{plan_iri}> .
    }}
    """
    try:
        result = await graph_client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        return [
            b.get("entry", {}).get("value", "")
            for b in bindings
            if b.get("entry", {}).get("value")
        ]
    except Exception as exc:
        logger.warning("Failed to query existing plan entries: %s", exc)
        return []


# ── Plan generation orchestration ──


async def generate_plan(
    ctx: Any,
    date_str: str | None = None,
    context_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a daily media plan: rules → items → slots → RDF objects.

    Full orchestration:
    1. Determine date (default: today YYYY-MM-DD)
    2. Fetch context (or use context_override)
    3. Load + evaluate rules via rules_service
    4. For each matched rule, query items via graph_client
    5. Collect items (dedup by IRI), allocate time slots
    6. Patch existing entries to "replaced" if plan already exists
    7. Bulk-create DailyMediaPlan + PlanEntry objects
    8. Return summary dict

    Args:
        ctx: SDK AppContext with ``http``, ``graph``, ``commands``, ``state``.
        date_str: Date in YYYY-MM-DD format. Defaults to today.
        context_override: Optional context dict (skips fetch_context).

    Returns:
        Summary dict: ``{plan_iri, date, rules_matched, entries_created}``.
    """
    # 1. Date
    if date_str is None:
        date_str = date.today().isoformat()

    plan_iri = mint_plan_iri(date_str)

    # 2. Context
    if context_override is not None:
        context = context_override
    else:
        context = await fetch_context(ctx.http)

    if not context:
        logger.warning(
            "Empty context for plan generation on %s — returning empty plan",
            date_str,
        )
        return {
            "plan_iri": plan_iri,
            "date": date_str,
            "rules_matched": 0,
            "entries_created": 0,
        }

    # 3. Load + evaluate rules
    rules = await load_rules(ctx.state)
    matched_rules = evaluate_rules(rules, context)

    logger.info(
        "Plan generation %s: %d rules matched out of %d total",
        date_str,
        len(matched_rules),
        len(rules),
    )

    if not matched_rules:
        return {
            "plan_iri": plan_iri,
            "date": date_str,
            "rules_matched": 0,
            "entries_created": 0,
        }

    # 4. Query items for each matched rule
    all_items: list[dict[str, Any]] = []
    seen_iris: set[str] = set()

    for rule in matched_rules:
        action = rule.get("action") or {}
        if not action.get("type") or not action.get("value"):
            logger.warning(
                "Rule %s has no valid action, skipping", rule.get("id")
            )
            continue

        try:
            sparql = build_item_query(action, limit=MAX_ITEMS_PER_RULE)
            result = await ctx.graph.query(sparql)
            bindings = result.get("results", {}).get("bindings", [])

            for b in bindings:
                item_iri = b.get("item", {}).get("value", "")
                if not item_iri or item_iri in seen_iris:
                    continue
                seen_iris.add(item_iri)

                title = b.get("title", {}).get("value", "")
                source_type = b.get("sourceType", {}).get("value", "")
                duration_raw = b.get("duration", {}).get("value")
                duration = None
                if duration_raw:
                    try:
                        duration = int(duration_raw)
                    except (ValueError, TypeError):
                        duration = None

                all_items.append({
                    "item_iri": item_iri,
                    "title": title,
                    "source_type": source_type,
                    "duration": duration,
                    "rule_id": rule.get("id", ""),
                })

        except Exception as exc:
            logger.warning(
                "Item query failed for rule %s: %s", rule.get("id"), exc
            )
            continue

    if not all_items:
        logger.info("No items found for matched rules on %s", date_str)
        return {
            "plan_iri": plan_iri,
            "date": date_str,
            "rules_matched": len(matched_rules),
            "entries_created": 0,
        }

    # 5. Allocate time slots
    slots = allocate_slots(all_items, start_hour=PLAN_START_HOUR)

    # 6. Patch existing entries to "replaced"
    existing_entries = await get_existing_plan_entries(ctx.graph, plan_iri)
    for entry_iri in existing_entries:
        try:
            await ctx.commands.execute(
                "object.patch",
                {
                    "iri": entry_iri,
                    "properties": {f"{MS_NS}entryStatus": "replaced"},
                },
            )
        except Exception as exc:
            logger.warning("Failed to patch old entry %s: %s", entry_iri, exc)

    # 7. Bulk-create plan + entries
    plan_properties = {
        "dcterms:title": f"Media Plan for {date_str}",
        f"{MS_NS}planStatus": "active",
        "dcterms:created": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Create the plan object
        await ctx.commands.execute(
            "object.create",
            {
                "iri": plan_iri,
                "type": DAILY_MEDIA_PLAN_TYPE,
                "properties": plan_properties,
            },
        )

        # Create each entry
        for slot in slots:
            entry_iri = mint_entry_iri(date_str, slot["slot_order"])
            entry_properties = {
                f"{MS_NS}plan": plan_iri,
                f"{MS_NS}mediaItem": slot["item_iri"],
                f"{MS_NS}slotStart": slot["slot_start"],
                f"{MS_NS}slotEnd": slot["slot_end"],
                f"{MS_NS}slotOrder": slot["slot_order"],
                f"{MS_NS}entryStatus": "pending",
                f"{MS_NS}ruleId": slot["rule_id"],
                "dcterms:title": slot["title"],
            }
            await ctx.commands.execute(
                "object.create",
                {
                    "iri": entry_iri,
                    "type": PLAN_ENTRY_TYPE,
                    "properties": entry_properties,
                },
            )
    except Exception as exc:
        logger.error("Plan creation failed for %s: %s", date_str, exc)
        return {
            "plan_iri": plan_iri,
            "date": date_str,
            "rules_matched": len(matched_rules),
            "entries_created": 0,
            "error": str(exc),
        }

    entries_created = len(slots)
    logger.info(
        "Plan generated for %s: %d rules matched, %d entries created, plan=%s",
        date_str,
        len(matched_rules),
        entries_created,
        plan_iri,
    )

    return {
        "plan_iri": plan_iri,
        "date": date_str,
        "rules_matched": len(matched_rules),
        "entries_created": entries_created,
    }
