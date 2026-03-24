"""Stats service — aggregate statistics from completed plan entries.

Provides three query functions for the Stats dashboard:
- ``get_hours_by_source_type(ctx)`` — total hours by source type
- ``get_top_sources(ctx, limit)`` — most-played sources by count
- ``get_weekly_trends(ctx, days)`` — completions per day

All queries filter on ``entryStatus = "completed"`` only.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# ── Import constants from podcast_service ──

try:
    from services.podcast_service import MEDIA_ITEM_TYPE, MS_NS
except ModuleNotFoundError:
    import importlib.util as _ilu
    import pathlib as _pl

    _psvc = _pl.Path(__file__).resolve().parent / "podcast_service.py"
    _psp = _ilu.spec_from_file_location("_podcast_service_fallback", _psvc)
    _pfm = _ilu.module_from_spec(_psp)
    _psp.loader.exec_module(_pfm)
    MEDIA_ITEM_TYPE = _pfm.MEDIA_ITEM_TYPE
    MS_NS = _pfm.MS_NS

try:
    from services.plan_service import DAILY_MEDIA_PLAN_TYPE, PLAN_ENTRY_TYPE
except ModuleNotFoundError:
    import importlib.util as _ilu2
    import pathlib as _pl2

    _plansvc = _pl2.Path(__file__).resolve().parent / "plan_service.py"
    _plansp = _ilu2.spec_from_file_location("_plan_service_fallback", _plansvc)
    _planfm = _ilu2.module_from_spec(_plansp)
    _plansp.loader.exec_module(_planfm)
    DAILY_MEDIA_PLAN_TYPE = _planfm.DAILY_MEDIA_PLAN_TYPE
    PLAN_ENTRY_TYPE = _planfm.PLAN_ENTRY_TYPE


# ── SPARQL templates ──

HOURS_BY_SOURCE_TYPE_SPARQL = f"""
SELECT ?sourceType (SUM(?dur) AS ?totalSeconds) WHERE {{
    ?entry a <{PLAN_ENTRY_TYPE}> .
    ?entry <{MS_NS}entryStatus> "completed" .
    ?entry <{MS_NS}mediaItem> ?item .
    ?item <{MS_NS}mediaSource> ?source .
    ?source <{MS_NS}sourceType> ?sourceType .
    ?item <{MS_NS}duration> ?dur .
}}
GROUP BY ?sourceType
ORDER BY DESC(?totalSeconds)
"""

TOP_SOURCES_SPARQL = f"""
SELECT ?sourceTitle (COUNT(?entry) AS ?completionCount) WHERE {{
    ?entry a <{PLAN_ENTRY_TYPE}> .
    ?entry <{MS_NS}entryStatus> "completed" .
    ?entry <{MS_NS}mediaItem> ?item .
    ?item <{MS_NS}mediaSource> ?source .
    ?source <http://purl.org/dc/terms/title> ?sourceTitle .
}}
GROUP BY ?sourceTitle
ORDER BY DESC(?completionCount)
LIMIT {{limit}}
"""

WEEKLY_TRENDS_SPARQL = f"""
SELECT ?planDate (COUNT(?entry) AS ?completionCount) WHERE {{
    ?entry a <{PLAN_ENTRY_TYPE}> .
    ?entry <{MS_NS}entryStatus> "completed" .
    ?entry <{MS_NS}plan> ?plan .
    ?plan a <{DAILY_MEDIA_PLAN_TYPE}> .
    ?plan <http://purl.org/dc/terms/title> ?planTitle .
    BIND(SUBSTR(?planTitle, STRLEN(?planTitle) - 9) AS ?planDate)
    FILTER(?planDate >= "{{start_date}}")
}}
GROUP BY ?planDate
ORDER BY ?planDate
"""


# ── Query functions ──


async def get_hours_by_source_type(ctx: Any) -> list[dict[str, Any]]:
    """Aggregate completed entry durations by source type.

    Returns list of ``{"source_type": str, "hours": float}`` sorted by
    hours descending. Returns empty list on query failure.
    """
    try:
        result = await ctx.graph.query(HOURS_BY_SOURCE_TYPE_SPARQL)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception as exc:
        logger.warning("stats.hours_by_source_type query failed: %s", exc)
        return []

    stats = []
    for b in bindings:
        source_type = b.get("sourceType", {}).get("value", "unknown")
        total_seconds_raw = b.get("totalSeconds", {}).get("value", "0")
        try:
            total_seconds = float(total_seconds_raw)
        except (ValueError, TypeError):
            total_seconds = 0.0
        hours = round(total_seconds / 3600, 1)
        stats.append({"source_type": source_type, "hours": hours})

    return stats


async def get_top_sources(ctx: Any, limit: int = 10) -> list[dict[str, Any]]:
    """Count completed entries per source, top N.

    Returns list of ``{"source_title": str, "count": int}`` sorted by
    count descending. Returns empty list on query failure.
    """
    sparql = TOP_SOURCES_SPARQL.replace("{limit}", str(limit))

    try:
        result = await ctx.graph.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception as exc:
        logger.warning("stats.top_sources query failed: %s", exc)
        return []

    stats = []
    for b in bindings:
        source_title = b.get("sourceTitle", {}).get("value", "Unknown")
        count_raw = b.get("completionCount", {}).get("value", "0")
        try:
            count = int(count_raw)
        except (ValueError, TypeError):
            count = 0
        stats.append({"source_title": source_title, "count": count})

    return stats


async def get_weekly_trends(ctx: Any, days: int = 7) -> list[dict[str, Any]]:
    """Count completed entries per day for the last N days.

    Returns list of ``{"date": str, "count": int}`` ordered
    chronologically. Fills in zero-count days to ensure the chart has
    continuous data. Returns empty list on query failure.
    """
    today = date.today()
    start_date = (today - timedelta(days=days - 1)).isoformat()

    sparql = WEEKLY_TRENDS_SPARQL.replace("{start_date}", start_date)

    try:
        result = await ctx.graph.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception as exc:
        logger.warning("stats.weekly_trends query failed: %s", exc)
        return []

    # Build lookup from query results
    counts: dict[str, int] = {}
    for b in bindings:
        plan_date = b.get("planDate", {}).get("value", "")
        count_raw = b.get("completionCount", {}).get("value", "0")
        try:
            count = int(count_raw)
        except (ValueError, TypeError):
            count = 0
        if plan_date:
            counts[plan_date] = count

    # Fill in all days in range (ensures continuous chart data)
    stats = []
    for i in range(days):
        d = (today - timedelta(days=days - 1 - i)).isoformat()
        stats.append({"date": d, "count": counts.get(d, 0)})

    return stats
