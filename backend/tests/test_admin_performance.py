"""Tests for /admin/performance dashboard route.

Validates:
- Route requires owner role (returns 200 for owner, 401/403 for unauthenticated)
- Template renders with timing data passed through context
- get_timing_report p50/p99 fields are present
"""

import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from jinja2_fragments.fastapi import Jinja2Blocks

from app.admin.router import router as admin_router
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.middleware.timing import (
    _record_timing,
    get_timing_report,
    reset_timing_stats,
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


def _make_app(authenticated: bool = True) -> FastAPI:
    """Build a minimal FastAPI app with admin router and template engine."""
    app = FastAPI()

    # Set up Jinja2Blocks templates pointing to real template directory
    templates_dir = Path(__file__).parent.parent / "app" / "templates"
    templates = Jinja2Blocks(directory=str(templates_dir))
    app.state.templates = templates

    # Register custom Jinja2 filters used by base.html
    from app.template_helpers import asset_url

    templates.env.filters["asset_url"] = asset_url
    templates.env.filters["dict_without"] = lambda d, *keys: {k: v for k, v in d.items() if k not in keys}
    templates.env.filters["urlencode"] = lambda s: s
    templates.env.filters["compact_iri"] = lambda s: s
    templates.env.globals["asset_manifest_available"] = False

    if authenticated:
        fake_user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            email="test@example.com",
            role="owner",
        )

        async def _fake_current_user():
            return fake_user

        app.dependency_overrides[get_current_user] = _fake_current_user

    app.include_router(admin_router)
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAdminPerformanceRoute:
    @pytest.mark.anyio
    async def test_returns_200_for_owner(self):
        app = _make_app(authenticated=True)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/admin/performance")
            assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_contains_performance_heading(self):
        app = _make_app(authenticated=True)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/admin/performance")
            assert resp.status_code == 200
            assert "Performance Dashboard" in resp.text

    @pytest.mark.anyio
    async def test_renders_chart_js_cdn(self):
        app = _make_app(authenticated=True)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/admin/performance")
            assert "chart.js" in resp.text

    @pytest.mark.anyio
    async def test_renders_timing_data(self):
        """With timing data seeded, the table renders endpoint rows."""
        # Seed some timing data
        for i in range(10):
            _record_timing("/api/test", 50.0 + i * 10)

        app = _make_app(authenticated=True)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/admin/performance")
            assert resp.status_code == 200
            assert "/api/test" in resp.text

    @pytest.mark.anyio
    async def test_renders_empty_state(self):
        """Without timing data, empty message appears."""
        app = _make_app(authenticated=True)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/admin/performance")
            assert resp.status_code == 200
            assert "No timing data collected yet" in resp.text

    @pytest.mark.anyio
    async def test_htmx_partial_rendering(self):
        app = _make_app(authenticated=True)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/admin/performance",
                headers={"HX-Request": "true"},
            )
            assert resp.status_code == 200
            # Partial render should contain the content but not full html wrapper
            assert "Performance Dashboard" in resp.text

    @pytest.mark.anyio
    async def test_unauthenticated_returns_401(self):
        app = _make_app(authenticated=False)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/admin/performance")
            # FastAPI returns 401 when no user provided
            assert resp.status_code in (401, 403)


class TestTimingReportPercentiles:
    def test_p50_present(self):
        for i in range(100):
            _record_timing("/test", float(i))
        report = get_timing_report(top_n=1)
        assert len(report) == 1
        assert "p50_ms" in report[0]

    def test_p99_present(self):
        for i in range(100):
            _record_timing("/test", float(i))
        report = get_timing_report(top_n=1)
        assert len(report) == 1
        assert "p99_ms" in report[0]

    def test_p50_value_reasonable(self):
        # 0..99 → sorted, p50 should be around index 50
        for i in range(100):
            _record_timing("/test", float(i))
        report = get_timing_report(top_n=1)
        assert 45 <= report[0]["p50_ms"] <= 55

    def test_p99_value_reasonable(self):
        for i in range(100):
            _record_timing("/test", float(i))
        report = get_timing_report(top_n=1)
        assert report[0]["p99_ms"] >= 95
