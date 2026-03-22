"""Tests for render_block output of data-driven widgets (M032/S02/T01).

Verifies the HTML structure, data attributes, and escaping for:
- stat-card (new)
- chart (new)
- heading (new)
- markdown (fixed — now uses script type="text/plain" + data-md-block)
- sparql-result (fixed — now uses data-sparql-query + data-sparql-table)
"""

import json
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth.models import User
from app.dashboard.service import DashboardService
from app.db.base import Base


@pytest_asyncio.fixture
async def async_session_factory():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def test_user(async_session_factory):
    user = User(
        id=uuid.uuid4(),
        username="widget_tester",
        email="widget@example.com",
        display_name="Widget Tester",
    )
    async with async_session_factory() as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def dashboard_service(async_session_factory):
    return DashboardService(async_session_factory)


@pytest_asyncio.fixture
async def test_app(async_session_factory, dashboard_service, test_user):
    from pathlib import Path
    from fastapi import FastAPI
    from jinja2_fragments.fastapi import Jinja2Blocks
    from app.dashboard.router import browser_router
    from app.auth.dependencies import get_current_user

    app = FastAPI()
    templates_dir = Path(__file__).parent.parent / "app" / "templates"
    templates = Jinja2Blocks(directory=templates_dir)
    templates.env.filters.setdefault("tojson", json.dumps)
    app.state.templates = templates
    app.state.dashboard_service = dashboard_service

    async def override_user():
        return test_user

    app.dependency_overrides[get_current_user] = override_user
    app.include_router(browser_router)
    yield app


@pytest_asyncio.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _create_dashboard_with_block(service, user_id, block_type, config):
    """Helper: create a dashboard containing exactly one block."""
    dashboard = await service.create(
        user_id=user_id,
        name=f"Test {block_type}",
        layout="gridstack",
        blocks=[{
            "type": block_type,
            "config": config,
            "x": 0, "y": 0, "w": 6, "h": 4,
        }],
    )
    return dashboard


# ---------------------------------------------------------------------------
# stat-card
# ---------------------------------------------------------------------------


class TestStatCardRender:
    async def test_has_data_sparql_query(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "stat-card",
            {"query": "SELECT (COUNT(*) AS ?c) WHERE { ?s a ?o }", "label": "Objects", "icon": "box"},
        )
        resp = await client.get(f"/browser/dashboard/{d.id}/block/0")
        assert resp.status_code == 200
        body = resp.text
        assert 'data-sparql-query="' in body
        assert "SELECT (COUNT(*) AS ?c)" in body

    async def test_has_stat_target(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "stat-card",
            {"query": "SELECT ?c WHERE {}", "label": "Count"},
        )
        resp = await client.get(f"/browser/dashboard/{d.id}/block/0")
        assert "data-stat-target" in resp.text

    async def test_has_label_and_icon(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "stat-card",
            {"query": "SELECT ?c WHERE {}", "label": "Tasks", "icon": "check-square"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert "stat-card-label" in body
        assert "Tasks" in body
        assert 'data-lucide="check-square"' in body

    async def test_color_style(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "stat-card",
            {"query": "SELECT ?c WHERE {}", "label": "X", "color": "#e74c3c"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert "color:#e74c3c" in body

    async def test_no_query_returns_error(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "stat-card",
            {"label": "Empty"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert "dashboard-block-error" in body
        assert "No query configured" in body

    async def test_html_escapes_query(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "stat-card",
            {"query": 'SELECT ?s WHERE { ?s a "test&thing" }', "label": "X"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        # & in query must be escaped to &amp; inside the data attribute
        assert "&amp;" in body


# ---------------------------------------------------------------------------
# chart
# ---------------------------------------------------------------------------


class TestChartRender:
    async def test_has_chart_query_and_type(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "chart",
            {"query": "SELECT ?label ?value WHERE {}", "chart_type": "bar", "label": "Types"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert 'data-chart-query="' in body
        assert 'data-chart-type="bar"' in body

    async def test_has_canvas(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "chart",
            {"query": "SELECT ?label ?value WHERE {}"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert '<canvas class="chart-canvas">' in body

    async def test_default_chart_type(self, client, dashboard_service, test_user):
        """Omitting chart_type defaults to bar."""
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "chart",
            {"query": "SELECT ?label ?value WHERE {}"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert 'data-chart-type="bar"' in body

    async def test_has_label(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "chart",
            {"query": "SELECT ?x WHERE {}", "label": "My Chart"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert "chart-label" in body
        assert "My Chart" in body

    async def test_no_query_returns_error(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "chart", {},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert "dashboard-block-error" in body


# ---------------------------------------------------------------------------
# heading
# ---------------------------------------------------------------------------


class TestHeadingRender:
    async def test_default_h2(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "heading",
            {"text": "Welcome"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert "<h2>Welcome</h2>" in body

    async def test_custom_level_h1(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "heading",
            {"text": "Title", "level": "1"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert "<h1>Title</h1>" in body

    async def test_level_clamped_to_4(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "heading",
            {"text": "Deep", "level": "9"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert "<h4>Deep</h4>" in body

    async def test_subtitle(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "heading",
            {"text": "Section", "subtitle": "Extra info"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert "heading-subtitle" in body
        assert "Extra info" in body

    async def test_alignment(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "heading",
            {"text": "Center", "align": "center"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert "text-align:center" in body

    async def test_html_escapes_text(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "heading",
            {"text": "<script>alert(1)</script>"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert "<script>alert(1)</script>" not in body
        assert "&lt;script&gt;" in body


# ---------------------------------------------------------------------------
# markdown (fixed)
# ---------------------------------------------------------------------------


class TestMarkdownRender:
    async def test_has_md_block_attribute(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "markdown",
            {"content": "# Hello"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert "data-md-block" in body

    async def test_has_script_plain_text(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "markdown",
            {"content": "**bold** and _italic_"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert '<script type="text/plain"' in body
        assert "md-source" in body
        assert "**bold** and _italic_" in body

    async def test_has_rendered_container(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "markdown",
            {"content": "test"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert "md-rendered" in body

    async def test_no_old_paragraph_split(self, client, dashboard_service, test_user):
        """The old handler split on \\n\\n and wrapped in <p> — verify that's gone."""
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "markdown",
            {"content": "line1\n\nline2"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        # Old handler would produce <p>line1</p><p>line2</p>
        assert "<p>line1</p>" not in body


# ---------------------------------------------------------------------------
# sparql-result (fixed)
# ---------------------------------------------------------------------------


class TestSparqlResultRender:
    async def test_has_data_sparql_query(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "sparql-result",
            {"query": "SELECT ?s WHERE { ?s a ?o }", "label": "All"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert 'data-sparql-query="' in body

    async def test_has_data_sparql_table(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "sparql-result",
            {"query": "SELECT ?s WHERE {}", "label": "Res"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert "data-sparql-table" in body

    async def test_no_old_data_query(self, client, dashboard_service, test_user):
        """Old handler used data-query — verify it's gone."""
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "sparql-result",
            {"query": "SELECT ?s WHERE {}", "label": "Test"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        # Should NOT have the old bare data-query attribute
        # (data-sparql-query contains "data-query" as substring, so check specifics)
        assert 'data-query="' not in body.replace('data-sparql-query', '').replace('data-chart-query', '')

    async def test_has_table_container(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "sparql-result",
            {"query": "SELECT ?s WHERE {}", "label": "Res"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert "sparql-table-container" in body

    async def test_has_label(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "sparql-result",
            {"query": "SELECT ?s WHERE {}", "label": "My Result"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert "My Result" in body

    async def test_no_query_returns_error(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "sparql-result",
            {"label": "Empty"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert "dashboard-block-error" in body

    async def test_html_escapes_query(self, client, dashboard_service, test_user):
        d = await _create_dashboard_with_block(
            dashboard_service, test_user.id, "sparql-result",
            {"query": 'SELECT ?s WHERE { ?s a "x&y" }', "label": "T"},
        )
        body = (await client.get(f"/browser/dashboard/{d.id}/block/0")).text
        assert "&amp;" in body
