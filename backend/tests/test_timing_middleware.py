"""Tests for TimingMiddleware: Server-Timing header, slow request logging,
per-path stats accumulation, p95 computation, max samples cap, admin
timing report endpoint, and stats reset.
"""

import time

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.responses import JSONResponse

from app.middleware.timing import (
    TimingMiddleware,
    _MAX_SAMPLES_PER_PATH,
    _record_timing,
    _timing_stats,
    get_timing_report,
    reset_timing_stats,
    timing_router,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_stats():
    """Reset timing stats before and after every test."""
    reset_timing_stats()
    yield
    reset_timing_stats()


def _make_app() -> FastAPI:
    """Build a minimal FastAPI app with TimingMiddleware attached."""
    app = FastAPI()
    app.add_middleware(TimingMiddleware)

    @app.get("/fast")
    async def fast():
        return {"ok": True}

    @app.get("/slow")
    async def slow():
        # Simulate a slow endpoint (>100ms)
        import asyncio
        await asyncio.sleep(0.12)
        return {"ok": True}

    return app


def _make_app_with_admin_router() -> FastAPI:
    """Build a FastAPI app with TimingMiddleware AND the admin timing router.

    Auth is bypassed by overriding get_current_user to return a fake owner,
    keeping tests self-contained without a real DB.
    """
    from app.auth.dependencies import get_current_user
    from app.auth.models import User
    import uuid

    app = FastAPI()
    app.add_middleware(TimingMiddleware)

    # Override the auth dependency so require_role("owner") succeeds
    fake_user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        email="test@example.com",
        role="owner",
    )

    async def _fake_current_user():
        return fake_user

    app.dependency_overrides[get_current_user] = _fake_current_user

    app.include_router(timing_router)

    @app.get("/test-endpoint")
    async def test_endpoint():
        return {"hello": "world"}

    return app


# ---------------------------------------------------------------------------
# Server-Timing header tests
# ---------------------------------------------------------------------------


class TestServerTimingHeader:
    @pytest.mark.anyio
    async def test_header_present(self):
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/fast")
            assert resp.status_code == 200
            assert "server-timing" in resp.headers

    @pytest.mark.anyio
    async def test_header_format(self):
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/fast")
            header = resp.headers["server-timing"]
            assert header.startswith("total;dur=")
            dur_str = header.split("=")[1]
            dur_val = float(dur_str)
            assert dur_val >= 0.0


# ---------------------------------------------------------------------------
# Stats accumulation tests
# ---------------------------------------------------------------------------


class TestStatsAccumulation:
    @pytest.mark.anyio
    async def test_stats_recorded_after_request(self):
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.get("/fast")
            await client.get("/fast")
        assert "/fast" in _timing_stats
        assert len(_timing_stats["/fast"]) == 2

    @pytest.mark.anyio
    async def test_multiple_paths_recorded(self):
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.get("/fast")
            await client.get("/slow")
        assert "/fast" in _timing_stats
        assert "/slow" in _timing_stats


# ---------------------------------------------------------------------------
# get_timing_report tests
# ---------------------------------------------------------------------------


class TestTimingReport:
    def test_empty_report(self):
        report = get_timing_report()
        assert report == []

    def test_report_structure(self):
        _record_timing("/api/test", 50.0)
        _record_timing("/api/test", 150.0)
        _record_timing("/api/test", 100.0)
        report = get_timing_report()
        assert len(report) == 1
        entry = report[0]
        assert entry["path"] == "/api/test"
        assert entry["count"] == 3
        assert entry["avg_ms"] == 100.0
        assert entry["max_ms"] == 150.0
        assert entry["min_ms"] == 50.0
        assert "p95_ms" in entry
        assert "total_ms" in entry

    def test_report_sorted_by_avg_desc(self):
        _record_timing("/slow", 200.0)
        _record_timing("/fast", 10.0)
        _record_timing("/medium", 100.0)
        report = get_timing_report(top_n=10)
        paths = [e["path"] for e in report]
        assert paths == ["/slow", "/medium", "/fast"]

    def test_top_n_limit(self):
        for i in range(10):
            _record_timing(f"/path/{i}", float(i * 10))
        report = get_timing_report(top_n=3)
        assert len(report) == 3

    def test_p95_computation(self):
        """p95 of 100 values [1..100] should be 95 or 96 depending on index."""
        for i in range(1, 101):
            _record_timing("/p95test", float(i))
        report = get_timing_report()
        entry = [e for e in report if e["path"] == "/p95test"][0]
        # int(100 * 0.95) = 95, sorted[95] = 96 (1-indexed values, 0-indexed list)
        assert entry["p95_ms"] == 96.0

    def test_avg_computation(self):
        _record_timing("/avg", 10.0)
        _record_timing("/avg", 20.0)
        _record_timing("/avg", 30.0)
        report = get_timing_report()
        entry = [e for e in report if e["path"] == "/avg"][0]
        assert entry["avg_ms"] == 20.0

    def test_total_ms(self):
        _record_timing("/total", 10.0)
        _record_timing("/total", 20.0)
        report = get_timing_report()
        entry = [e for e in report if e["path"] == "/total"][0]
        assert entry["total_ms"] == 30.0


# ---------------------------------------------------------------------------
# Stats reset
# ---------------------------------------------------------------------------


class TestStatsReset:
    def test_reset_clears_stats(self):
        _record_timing("/foo", 42.0)
        assert len(_timing_stats) > 0
        reset_timing_stats()
        assert len(_timing_stats) == 0

    def test_report_empty_after_reset(self):
        _record_timing("/foo", 42.0)
        reset_timing_stats()
        assert get_timing_report() == []


# ---------------------------------------------------------------------------
# Max samples cap
# ---------------------------------------------------------------------------


class TestMaxSamplesCap:
    def test_cap_enforced(self):
        for i in range(_MAX_SAMPLES_PER_PATH + 200):
            _record_timing("/capped", float(i))
        assert len(_timing_stats["/capped"]) == _MAX_SAMPLES_PER_PATH

    def test_most_recent_samples_kept(self):
        """After capping, the most recent values should be retained."""
        total = _MAX_SAMPLES_PER_PATH + 100
        for i in range(total):
            _record_timing("/recent", float(i))
        samples = _timing_stats["/recent"]
        # The last sample should be the most recent value
        assert samples[-1] == float(total - 1)
        # The first sample after trimming should be the 100th value
        assert samples[0] == float(100)


# ---------------------------------------------------------------------------
# Admin timing report endpoint
# ---------------------------------------------------------------------------


class TestAdminTimingEndpoint:
    @pytest.mark.anyio
    async def test_endpoint_returns_json(self):
        app = _make_app_with_admin_router()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Generate some timing data
            await client.get("/test-endpoint")
            resp = await client.get("/api/admin/timing-report")
            assert resp.status_code == 200
            data = resp.json()
            assert "top_endpoints" in data
            assert "total_requests" in data
            assert "collection_period_seconds" in data

    @pytest.mark.anyio
    async def test_endpoint_schema(self):
        app = _make_app_with_admin_router()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Make requests to generate data
            for _ in range(3):
                await client.get("/test-endpoint")
            resp = await client.get("/api/admin/timing-report")
            data = resp.json()

            assert isinstance(data["top_endpoints"], list)
            assert isinstance(data["total_requests"], int)
            assert isinstance(data["collection_period_seconds"], float)
            # total_requests should include test-endpoint requests + timing-report request(s)
            assert data["total_requests"] >= 3

    @pytest.mark.anyio
    async def test_endpoint_top_endpoints_structure(self):
        app = _make_app_with_admin_router()
        # Seed some timing data directly
        _record_timing("/seeded", 42.0)
        _record_timing("/seeded", 99.0)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/admin/timing-report")
            data = resp.json()
            # Should have at least the seeded path + the timing-report path itself
            seeded = [e for e in data["top_endpoints"] if e["path"] == "/seeded"]
            assert len(seeded) == 1
            entry = seeded[0]
            for key in ("path", "count", "avg_ms", "max_ms", "min_ms", "p95_ms", "total_ms"):
                assert key in entry


# ---------------------------------------------------------------------------
# Slow request logging (integration with middleware)
# ---------------------------------------------------------------------------


class TestSlowRequestLogging:
    @pytest.mark.anyio
    async def test_slow_request_logged_at_info(self, caplog):
        """Requests over 100ms should emit an INFO log line."""
        import logging
        app = _make_app()
        with caplog.at_level(logging.INFO, logger="app.middleware.timing"):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.get("/slow")
        assert any("Slow request" in rec.message for rec in caplog.records)

    @pytest.mark.anyio
    async def test_fast_request_not_logged_at_info(self, caplog):
        """Fast requests should NOT emit an INFO 'Slow request' line."""
        import logging
        app = _make_app()
        with caplog.at_level(logging.INFO, logger="app.middleware.timing"):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.get("/fast")
        assert not any("Slow request" in rec.message for rec in caplog.records)
