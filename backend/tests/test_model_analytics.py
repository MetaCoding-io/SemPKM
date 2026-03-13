"""Tests for ModelService.get_type_analytics() SPARQL analytics queries.

Verifies parsing logic for avg_connections, last_modified, growth_trend,
and link_distribution using mock triplestore responses. Also tests graceful
defaults on query exceptions and unchanged count/top_nodes behavior.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.services.models import (
    ModelService,
    _bucket_link_counts,
    _extract_last_modified,
    _iso_week_key,
    _pad_weekly_trend,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bindings(**kwargs: str) -> dict:
    """Build a SPARQL JSON result with a single binding row."""
    row = {k: {"value": v} for k, v in kwargs.items()}
    return {"results": {"bindings": [row]}}


def _make_multi_bindings(rows: list[dict[str, str]]) -> dict:
    """Build a SPARQL JSON result with multiple binding rows."""
    bindings = [{k: {"value": v} for k, v in row.items()} for row in rows]
    return {"results": {"bindings": bindings}}


EMPTY_RESULT = {"results": {"bindings": []}}

TYPE_A = "http://example.org/Type_A"


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------

class TestExtractLastModified:
    def test_extracts_value(self):
        bindings = [{"lastMod": {"value": "2026-03-10T12:00:00"}}]
        assert _extract_last_modified(bindings) == "2026-03-10T12:00:00"

    def test_empty_bindings(self):
        assert _extract_last_modified([]) is None

    def test_empty_value(self):
        bindings = [{"lastMod": {"value": ""}}]
        assert _extract_last_modified(bindings) is None

    def test_missing_key(self):
        bindings = [{"other": {"value": "x"}}]
        assert _extract_last_modified(bindings) is None


class TestIsoWeekKey:
    def test_normal_date(self):
        assert _iso_week_key("2026-03-12T10:00:00") == "2026-W11"

    def test_with_z_suffix(self):
        assert _iso_week_key("2026-03-12T10:00:00Z") == "2026-W11"

    def test_invalid_string(self):
        assert _iso_week_key("not-a-date") is None

    def test_empty_string(self):
        assert _iso_week_key("") is None


class TestPadWeeklyTrend:
    def test_fills_eight_weeks(self):
        now = datetime(2026, 3, 12, tzinfo=timezone.utc)
        result = _pad_weekly_trend({}, now)
        assert len(result) == 8
        assert all(r["count"] == 0 for r in result)
        # Last entry should be the current week
        assert result[-1]["week"] == "2026-W11"

    def test_preserves_counts(self):
        now = datetime(2026, 3, 12, tzinfo=timezone.utc)
        counts = {"2026-W11": 5, "2026-W09": 3}
        result = _pad_weekly_trend(counts, now)
        by_week = {r["week"]: r["count"] for r in result}
        assert by_week["2026-W11"] == 5
        assert by_week["2026-W09"] == 3
        # Weeks not in counts should be 0
        assert by_week.get("2026-W10", 0) == 0

    def test_oldest_first(self):
        now = datetime(2026, 3, 12, tzinfo=timezone.utc)
        result = _pad_weekly_trend({}, now)
        weeks = [r["week"] for r in result]
        assert weeks == sorted(weeks)


class TestBucketLinkCounts:
    def test_all_buckets(self):
        counts = [0, 0, 1, 2, 3, 5, 6, 10, 11, 20]
        result = _bucket_link_counts(counts)
        by_bucket = {r["bucket"]: r["count"] for r in result}
        assert by_bucket["0"] == 2
        assert by_bucket["1-2"] == 2
        assert by_bucket["3-5"] == 2
        assert by_bucket["6-10"] == 2
        assert by_bucket["11+"] == 2

    def test_empty_input(self):
        result = _bucket_link_counts([])
        assert len(result) == 5
        assert all(r["count"] == 0 for r in result)

    def test_bucket_order(self):
        result = _bucket_link_counts([1])
        labels = [r["bucket"] for r in result]
        assert labels == ["0", "1-2", "3-5", "6-10", "11+"]

    def test_single_high_value(self):
        result = _bucket_link_counts([100])
        by_bucket = {r["bucket"]: r["count"] for r in result}
        assert by_bucket["11+"] == 1
        assert sum(r["count"] for r in result) == 1


# ---------------------------------------------------------------------------
# Integration tests with mocked triplestore
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_client():
    """Create a mock TriplestoreClient."""
    client = AsyncMock()
    client.query = AsyncMock(return_value=EMPTY_RESULT)
    return client


@pytest.fixture
def service(mock_client):
    """Create a ModelService with mocked dependencies."""
    with patch("app.services.models.ModelService.__init__", lambda self, *a, **kw: None):
        svc = ModelService.__new__(ModelService)
        svc._client = mock_client
        return svc


class TestAvgConnections:
    @pytest.mark.asyncio
    async def test_avg_connections_basic(self, service, mock_client):
        """Avg connections = totalLinks / instance count."""
        call_count = 0

        async def query_side_effect(sparql):
            nonlocal call_count
            call_count += 1
            # 1st call: batch instance counts
            if "COUNT(DISTINCT ?s) AS ?count" in sparql and "GROUP BY ?type" in sparql:
                return _make_bindings(type=TYPE_A, count="10")
            # top_nodes query
            if "ORDER BY DESC(?linkCount) LIMIT 5" in sparql:
                return EMPTY_RESULT
            # avg_connections query
            if "totalLinks" in sparql:
                return _make_bindings(totalLinks="50")
            # last_modified primary
            if "MAX(?mod) AS ?lastMod" in sparql and "dcterms" not in sparql and "modified" in sparql:
                return EMPTY_RESULT
            return EMPTY_RESULT

        mock_client.query = AsyncMock(side_effect=query_side_effect)
        result = await service.get_type_analytics([TYPE_A])
        assert result[TYPE_A]["avg_connections"] == 5.0

    @pytest.mark.asyncio
    async def test_avg_connections_zero_instances(self, service, mock_client):
        """Types with 0 instances get 0.0 avg_connections."""
        mock_client.query = AsyncMock(return_value=EMPTY_RESULT)
        result = await service.get_type_analytics([TYPE_A])
        assert result[TYPE_A]["avg_connections"] == 0.0

    @pytest.mark.asyncio
    async def test_avg_connections_rounds_to_one_decimal(self, service, mock_client):
        """Avg connections should be rounded to 1 decimal place."""
        async def query_side_effect(sparql):
            if "COUNT(DISTINCT ?s) AS ?count" in sparql and "GROUP BY ?type" in sparql:
                return _make_bindings(type=TYPE_A, count="3")
            if "ORDER BY DESC(?linkCount) LIMIT 5" in sparql:
                return EMPTY_RESULT
            if "totalLinks" in sparql:
                return _make_bindings(totalLinks="10")
            return EMPTY_RESULT

        mock_client.query = AsyncMock(side_effect=query_side_effect)
        result = await service.get_type_analytics([TYPE_A])
        assert result[TYPE_A]["avg_connections"] == 3.3  # 10/3 = 3.333... -> 3.3


class TestLastModified:
    @pytest.mark.asyncio
    async def test_last_modified_from_dcterms(self, service, mock_client):
        """Uses dcterms:modified when available."""
        async def query_side_effect(sparql):
            if "COUNT(DISTINCT ?s) AS ?count" in sparql and "GROUP BY ?type" in sparql:
                return _make_bindings(type=TYPE_A, count="5")
            if "ORDER BY DESC(?linkCount) LIMIT 5" in sparql:
                return EMPTY_RESULT
            if "totalLinks" in sparql:
                return _make_bindings(totalLinks="0")
            # Primary last_modified query
            if "dc/terms/modified" in sparql and "MAX" in sparql:
                return _make_bindings(lastMod="2026-03-10T14:30:00")
            return EMPTY_RESULT

        mock_client.query = AsyncMock(side_effect=query_side_effect)
        result = await service.get_type_analytics([TYPE_A])
        assert result[TYPE_A]["last_modified"] == "2026-03-10T14:30:00"

    @pytest.mark.asyncio
    async def test_last_modified_fallback_to_events(self, service, mock_client):
        """Falls back to event timestamps when dcterms:modified is absent."""
        async def query_side_effect(sparql):
            if "COUNT(DISTINCT ?s) AS ?count" in sparql and "GROUP BY ?type" in sparql:
                return _make_bindings(type=TYPE_A, count="5")
            if "ORDER BY DESC(?linkCount) LIMIT 5" in sparql:
                return EMPTY_RESULT
            if "totalLinks" in sparql:
                return _make_bindings(totalLinks="0")
            # Primary last_modified returns empty
            if "dc/terms/modified" in sparql and "MAX" in sparql:
                return EMPTY_RESULT
            # Fallback event query
            if "operationType" in sparql and "affectedIRI" in sparql and "MAX" in sparql:
                return _make_bindings(lastMod="2026-03-08T10:00:00")
            return EMPTY_RESULT

        mock_client.query = AsyncMock(side_effect=query_side_effect)
        result = await service.get_type_analytics([TYPE_A])
        assert result[TYPE_A]["last_modified"] == "2026-03-08T10:00:00"

    @pytest.mark.asyncio
    async def test_last_modified_none_when_both_empty(self, service, mock_client):
        """Returns None when neither dcterms:modified nor events exist."""
        async def query_side_effect(sparql):
            if "COUNT(DISTINCT ?s) AS ?count" in sparql and "GROUP BY ?type" in sparql:
                return _make_bindings(type=TYPE_A, count="5")
            if "ORDER BY DESC(?linkCount) LIMIT 5" in sparql:
                return EMPTY_RESULT
            if "totalLinks" in sparql:
                return _make_bindings(totalLinks="0")
            return EMPTY_RESULT

        mock_client.query = AsyncMock(side_effect=query_side_effect)
        result = await service.get_type_analytics([TYPE_A])
        assert result[TYPE_A]["last_modified"] is None


class TestGrowthTrend:
    @pytest.mark.asyncio
    async def test_growth_trend_with_events(self, service, mock_client):
        """Growth trend populates weekly counts from event timestamps."""
        now = datetime.now(timezone.utc)
        # Create timestamps in the current and previous weeks
        current_ts = now.strftime("%Y-%m-%dT%H:%M:%S")
        last_week_ts = (now - timedelta(weeks=1)).strftime("%Y-%m-%dT%H:%M:%S")

        async def query_side_effect(sparql):
            if "COUNT(DISTINCT ?s) AS ?count" in sparql and "GROUP BY ?type" in sparql:
                return _make_bindings(type=TYPE_A, count="5")
            if "ORDER BY DESC(?linkCount) LIMIT 5" in sparql:
                return EMPTY_RESULT
            if "totalLinks" in sparql:
                return _make_bindings(totalLinks="0")
            if "dc/terms/modified" in sparql:
                return EMPTY_RESULT
            if "operationType" in sparql and "object.create" in sparql:
                return _make_multi_bindings([
                    {"ts": current_ts},
                    {"ts": current_ts},
                    {"ts": last_week_ts},
                ])
            return EMPTY_RESULT

        mock_client.query = AsyncMock(side_effect=query_side_effect)
        result = await service.get_type_analytics([TYPE_A])
        trend = result[TYPE_A]["growth_trend"]
        assert len(trend) == 8
        # Last entry (current week) should have count 2
        assert trend[-1]["count"] == 2
        # Second to last should have count 1
        assert trend[-2]["count"] == 1

    @pytest.mark.asyncio
    async def test_growth_trend_empty_events(self, service, mock_client):
        """Returns 8 zero-count weeks when no events exist."""
        async def query_side_effect(sparql):
            if "COUNT(DISTINCT ?s) AS ?count" in sparql and "GROUP BY ?type" in sparql:
                return _make_bindings(type=TYPE_A, count="5")
            if "ORDER BY DESC(?linkCount) LIMIT 5" in sparql:
                return EMPTY_RESULT
            if "totalLinks" in sparql:
                return _make_bindings(totalLinks="0")
            return EMPTY_RESULT

        mock_client.query = AsyncMock(side_effect=query_side_effect)
        result = await service.get_type_analytics([TYPE_A])
        trend = result[TYPE_A]["growth_trend"]
        assert len(trend) == 8
        assert all(w["count"] == 0 for w in trend)
        # Check structure
        assert all("week" in w and "count" in w for w in trend)

    @pytest.mark.asyncio
    async def test_growth_trend_zero_instances(self, service, mock_client):
        """Types with 0 instances still get 8 padded weeks."""
        mock_client.query = AsyncMock(return_value=EMPTY_RESULT)
        result = await service.get_type_analytics([TYPE_A])
        trend = result[TYPE_A]["growth_trend"]
        assert len(trend) == 8
        assert all(w["count"] == 0 for w in trend)


class TestLinkDistribution:
    @pytest.mark.asyncio
    async def test_link_distribution_buckets(self, service, mock_client):
        """Link distribution correctly buckets per-instance link counts."""
        async def query_side_effect(sparql):
            if "COUNT(DISTINCT ?s) AS ?count" in sparql and "GROUP BY ?type" in sparql:
                return _make_bindings(type=TYPE_A, count="6")
            if "ORDER BY DESC(?linkCount) LIMIT 5" in sparql:
                return EMPTY_RESULT
            if "totalLinks" in sparql:
                return _make_bindings(totalLinks="0")
            if "dc/terms/modified" in sparql:
                return EMPTY_RESULT
            if "operationType" in sparql and "object.create" in sparql:
                return EMPTY_RESULT
            # Link distribution query
            if "COUNT(?link) AS ?linkCount" in sparql and "GROUP BY ?s" in sparql:
                return _make_multi_bindings([
                    {"s": "http://ex.org/a", "linkCount": "0"},
                    {"s": "http://ex.org/b", "linkCount": "1"},
                    {"s": "http://ex.org/c", "linkCount": "4"},
                    {"s": "http://ex.org/d", "linkCount": "8"},
                    {"s": "http://ex.org/e", "linkCount": "15"},
                ])
            return EMPTY_RESULT

        mock_client.query = AsyncMock(side_effect=query_side_effect)
        result = await service.get_type_analytics([TYPE_A])
        dist = result[TYPE_A]["link_distribution"]
        by_bucket = {d["bucket"]: d["count"] for d in dist}
        # 5 from query + 1 zero-link (count=6, 5 in query results)
        assert by_bucket["0"] == 2  # "0" from query + 1 zero-link instance
        assert by_bucket["1-2"] == 1
        assert by_bucket["3-5"] == 1
        assert by_bucket["6-10"] == 1
        assert by_bucket["11+"] == 1

    @pytest.mark.asyncio
    async def test_link_distribution_empty_for_zero_instances(self, service, mock_client):
        """Types with 0 instances get empty link distribution."""
        mock_client.query = AsyncMock(return_value=EMPTY_RESULT)
        result = await service.get_type_analytics([TYPE_A])
        assert result[TYPE_A]["link_distribution"] == []


class TestGracefulDefaults:
    @pytest.mark.asyncio
    async def test_all_queries_fail_gracefully(self, service, mock_client):
        """All stats default gracefully when SPARQL queries raise exceptions."""
        call_count = 0

        async def query_side_effect(sparql):
            nonlocal call_count
            call_count += 1
            # Let the count query succeed so subsequent per-type queries run
            if call_count == 1:
                return _make_bindings(type=TYPE_A, count="5")
            raise RuntimeError("SPARQL endpoint unavailable")

        mock_client.query = AsyncMock(side_effect=query_side_effect)
        # Should not raise
        result = await service.get_type_analytics([TYPE_A])
        assert result[TYPE_A]["count"] == 5
        assert result[TYPE_A]["top_nodes"] == []
        assert result[TYPE_A]["avg_connections"] == 0.0
        assert result[TYPE_A]["last_modified"] is None
        # growth_trend still gets padded zeros even on error
        assert len(result[TYPE_A]["growth_trend"]) == 8
        assert result[TYPE_A]["link_distribution"] == []

    @pytest.mark.asyncio
    async def test_count_query_fails_gracefully(self, service, mock_client):
        """When even the count query fails, all defaults are returned."""
        mock_client.query = AsyncMock(side_effect=RuntimeError("Connection refused"))
        result = await service.get_type_analytics([TYPE_A])
        assert result[TYPE_A]["count"] == 0
        assert result[TYPE_A]["top_nodes"] == []
        assert result[TYPE_A]["avg_connections"] == 0.0
        assert result[TYPE_A]["last_modified"] is None
        # Zero-instance types still get 8 padded zero-count weeks for consistent rendering
        assert len(result[TYPE_A]["growth_trend"]) == 8
        assert all(w["count"] == 0 for w in result[TYPE_A]["growth_trend"])
        assert result[TYPE_A]["link_distribution"] == []


class TestExistingBehaviorUnchanged:
    @pytest.mark.asyncio
    async def test_count_still_works(self, service, mock_client):
        """Instance count parsing is unchanged."""
        async def query_side_effect(sparql):
            if "COUNT(DISTINCT ?s) AS ?count" in sparql and "GROUP BY ?type" in sparql:
                return _make_bindings(type=TYPE_A, count="42")
            return EMPTY_RESULT

        mock_client.query = AsyncMock(side_effect=query_side_effect)
        result = await service.get_type_analytics([TYPE_A])
        assert result[TYPE_A]["count"] == 42

    @pytest.mark.asyncio
    async def test_top_nodes_still_works(self, service, mock_client):
        """Top nodes parsing is unchanged."""
        async def query_side_effect(sparql):
            if "COUNT(DISTINCT ?s) AS ?count" in sparql and "GROUP BY ?type" in sparql:
                return _make_bindings(type=TYPE_A, count="5")
            if "ORDER BY DESC(?linkCount) LIMIT 5" in sparql:
                return _make_multi_bindings([
                    {"label": "Node A", "linkCount": "10"},
                    {"label": "Node B", "linkCount": "5"},
                ])
            return EMPTY_RESULT

        mock_client.query = AsyncMock(side_effect=query_side_effect)
        result = await service.get_type_analytics([TYPE_A])
        nodes = result[TYPE_A]["top_nodes"]
        assert len(nodes) == 2
        assert nodes[0]["label"] == "Node A"
        assert nodes[0]["link_count"] == 10

    @pytest.mark.asyncio
    async def test_empty_iris_returns_empty(self, service, mock_client):
        """Empty type_iris list returns empty dict."""
        result = await service.get_type_analytics([])
        assert result == {}
        mock_client.query.assert_not_called()

    @pytest.mark.asyncio
    async def test_return_dict_has_all_keys(self, service, mock_client):
        """Every type in result has all 6 expected keys."""
        mock_client.query = AsyncMock(return_value=EMPTY_RESULT)
        result = await service.get_type_analytics([TYPE_A])
        expected_keys = {"count", "top_nodes", "avg_connections", "last_modified", "growth_trend", "link_distribution"}
        assert set(result[TYPE_A].keys()) == expected_keys
