"""Unit tests for views explorer app contributions and command palette API.

Validates:
- GET /apps/views/explorer — returns app view entries for running apps
- GET /apps/{app_id}/view/{view_id} — renders app view tab content
- GET /api/apps/commands — returns command palette entries from running apps
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jinja2_fragments.fastapi import Jinja2Blocks

from app.apps.manifest import (
    AppBackend,
    AppCommandPaletteEntry,
    AppContributions,
    AppDependencies,
    AppFrontend,
    AppManifestSchema,
    AppPage,
    AppUI,
    AppViewContribution,
)
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.db.session import get_db_session
from app.apps.registry import AppRegistry
from app.browser.apps import app_commands_router, apps_router


# ── Helpers ──

# Fake user for auth dependency override
_FAKE_USER = User(id="00000000-0000-0000-0000-000000000001", email="test@example.com", role="owner")


def _override_auth():
    """Override get_current_user to return a fake user."""
    return _FAKE_USER


def _make_view(
    id: str = "my-view",
    label: str = "My View",
    icon: str = "layout-grid",
    fragment: str = "my-view",
) -> AppViewContribution:
    return AppViewContribution(id=id, label=label, icon=icon, fragment=fragment)


def _make_command(
    id: str = "my-cmd",
    label: str = "Do Something",
    action_type: str = "dialog",
    fragment: str | None = "my-dialog",
    endpoint: str | None = None,
    path: str | None = None,
    keywords: list[str] | None = None,
) -> AppCommandPaletteEntry:
    return AppCommandPaletteEntry(
        id=id,
        label=label,
        actionType=action_type,
        fragment=fragment,
        endpoint=endpoint,
        path=path,
        keywords=keywords or [],
    )


def _make_manifest(
    app_id: str = "test-app",
    name: str = "Test App",
    contributions: AppContributions | None = None,
) -> AppManifestSchema:
    return AppManifestSchema(
        appId=app_id,
        version="1.0.0",
        name=name,
        description="Test",
        backend=AppBackend(entrypoint="backend.app:TestApp"),
        dependencies=AppDependencies(platform=">=0.1.0"),
        frontend=AppFrontend(),
        ui=AppUI(contributions=contributions or AppContributions()),
    )


def _create_app(
    registry: AppRegistry | None = None,
    running_apps: set[str] | None = None,
) -> FastAPI:
    """Create a FastAPI test app with both routers and mocked state."""
    test_app = FastAPI()
    test_app.include_router(apps_router)
    test_app.include_router(app_commands_router)

    # Override auth dependency to return fake user
    test_app.dependency_overrides[get_current_user] = _override_auth

    # Templates
    templates_dir = Path(__file__).parent.parent / "app" / "templates"
    templates = Jinja2Blocks(directory=templates_dir)
    test_app.state.templates = templates

    # Registry
    test_app.state.app_registry = registry or AppRegistry()

    # Mock manager — return running for specified apps, stopped otherwise
    running = running_apps or set()

    async def _get_status(app_id: str) -> dict:
        if app_id in running:
            return {"status": "running"}
        return {"status": "stopped"}

    manager = AsyncMock()
    manager.get_status = _get_status
    manager.registry = registry or AppRegistry()
    test_app.state.app_manager = manager

    return test_app


# ── Views Explorer Tests ──


class TestViewsExplorerApps:
    """Tests for GET /apps/views/explorer."""

    def test_running_app_with_views_returns_entries(self):
        """Running app with views shows view entries in HTML."""
        view = _make_view(id="kanban", label="Kanban Board", icon="columns")
        manifest = _make_manifest(
            app_id="proj-app",
            name="Project App",
            contributions=AppContributions(views=[view]),
        )
        registry = AppRegistry()
        registry.register("proj-app", manifest)

        app = _create_app(registry=registry, running_apps={"proj-app"})
        client = TestClient(app)
        resp = client.get("/apps/views/explorer")
        assert resp.status_code == 200
        html = resp.text
        assert "Kanban Board" in html
        assert "openAppViewTab" in html
        assert "proj-app" in html
        assert "kanban" in html

    def test_no_apps_returns_empty(self):
        """With no apps registered, response is empty (no group heading)."""
        app = _create_app()
        client = TestClient(app)
        resp = client.get("/apps/views/explorer")
        assert resp.status_code == 200
        html = resp.text.strip()
        # No App Views group when there are no views
        assert "App Views" not in html

    def test_stopped_app_excluded(self):
        """Stopped app views do not appear in the explorer."""
        view = _make_view(id="timeline", label="Timeline")
        manifest = _make_manifest(
            app_id="stopped-app",
            name="Stopped App",
            contributions=AppContributions(views=[view]),
        )
        registry = AppRegistry()
        registry.register("stopped-app", manifest)

        # stopped-app is NOT in running_apps
        app = _create_app(registry=registry, running_apps=set())
        client = TestClient(app)
        resp = client.get("/apps/views/explorer")
        assert resp.status_code == 200
        assert "Timeline" not in resp.text

    def test_multiple_views_from_multiple_apps(self):
        """Views from multiple running apps all appear."""
        v1 = _make_view(id="kanban", label="Kanban")
        v2 = _make_view(id="calendar", label="Calendar")
        m1 = _make_manifest(
            app_id="app-a", name="App A",
            contributions=AppContributions(views=[v1]),
        )
        m2 = _make_manifest(
            app_id="app-b", name="App B",
            contributions=AppContributions(views=[v2]),
        )
        registry = AppRegistry()
        registry.register("app-a", m1)
        registry.register("app-b", m2)

        app = _create_app(registry=registry, running_apps={"app-a", "app-b"})
        client = TestClient(app)
        resp = client.get("/apps/views/explorer")
        assert resp.status_code == 200
        assert "Kanban" in resp.text
        assert "Calendar" in resp.text


# ── App View Tab Tests ──


class TestAppViewTab:
    """Tests for GET /apps/{app_id}/view/{view_id}."""

    def test_returns_view_tab_with_fragment(self):
        """Valid app/view returns tab content with htmx fragment URL."""
        view = _make_view(id="kanban", label="Kanban Board", fragment="kanban-view")
        manifest = _make_manifest(
            app_id="proj-app",
            name="Project App",
            contributions=AppContributions(views=[view]),
        )
        registry = AppRegistry()
        registry.register("proj-app", manifest)

        app = _create_app(registry=registry)
        client = TestClient(app)
        resp = client.get("/apps/proj-app/view/kanban")
        assert resp.status_code == 200
        html = resp.text
        assert "/app/proj-app/_fragments/kanban-view" in html
        assert "Kanban Board" in html

    def test_unknown_app_returns_404(self):
        """Unknown app_id returns 404."""
        app = _create_app()
        client = TestClient(app)
        resp = client.get("/apps/unknown-app/view/some-view")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_unknown_view_returns_404(self):
        """Known app but unknown view_id returns 404."""
        manifest = _make_manifest(app_id="proj-app", name="Project App")
        registry = AppRegistry()
        registry.register("proj-app", manifest)

        app = _create_app(registry=registry)
        client = TestClient(app)
        resp = client.get("/apps/proj-app/view/nonexistent")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_includes_css_and_js(self):
        """App with frontend assets includes CSS and JS in tab content."""
        view = _make_view(id="board", label="Board", fragment="board-frag")
        manifest = AppManifestSchema(
            appId="styled-app",
            version="1.0.0",
            name="Styled App",
            description="Test",
            backend=AppBackend(entrypoint="backend.app:StyledApp"),
            dependencies=AppDependencies(platform=">=0.1.0"),
            frontend=AppFrontend(css=["style.css"], js=["app.js"]),
            ui=AppUI(contributions=AppContributions(views=[view])),
        )
        registry = AppRegistry()
        registry.register("styled-app", manifest)

        app = _create_app(registry=registry)
        client = TestClient(app)
        resp = client.get("/apps/styled-app/view/board")
        assert resp.status_code == 200
        assert "/app-static/styled-app/style.css" in resp.text
        assert "/app-static/styled-app/app.js" in resp.text


# ── Command Palette API Tests ──


class TestCommandPaletteAPI:
    """Tests for GET /api/apps/commands."""

    def test_running_app_with_commands_returns_entries(self):
        """Running app with command palette entries returns correct JSON."""
        cmd = _make_command(
            id="open-crm",
            label="Open CRM Dashboard",
            action_type="dialog",
            fragment="crm-dialog",
        )
        manifest = _make_manifest(
            app_id="crm-app",
            name="CRM App",
            contributions=AppContributions(commandPalette=[cmd]),
        )
        registry = AppRegistry()
        registry.register("crm-app", manifest)

        app = _create_app(registry=registry, running_apps={"crm-app"})
        client = TestClient(app)
        resp = client.get("/api/apps/commands")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        entry = data[0]
        assert entry["id"] == "appcmd:crm-app:open-crm"
        assert entry["title"] == "Open CRM Dashboard"
        assert entry["section"] == "CRM App"
        assert entry["actionType"] == "dialog"
        assert entry["actionUrl"] == "/app/crm-app/_fragments/crm-dialog"

    def test_no_apps_returns_empty_array(self):
        """With no apps registered, returns empty JSON array."""
        app = _create_app()
        client = TestClient(app)
        resp = client.get("/api/apps/commands")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_stopped_app_excluded(self):
        """Stopped apps do not contribute command palette entries."""
        cmd = _make_command(id="stopped-cmd", label="Stopped Command")
        manifest = _make_manifest(
            app_id="stopped-app",
            name="Stopped App",
            contributions=AppContributions(commandPalette=[cmd]),
        )
        registry = AppRegistry()
        registry.register("stopped-app", manifest)

        app = _create_app(registry=registry, running_apps=set())
        client = TestClient(app)
        resp = client.get("/api/apps/commands")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_post_action_type_url(self):
        """Post action type uses endpoint for actionUrl."""
        cmd = _make_command(
            id="run-sync",
            label="Run Sync",
            action_type="post",
            fragment=None,
            endpoint="api/sync",
        )
        manifest = _make_manifest(
            app_id="sync-app",
            name="Sync App",
            contributions=AppContributions(commandPalette=[cmd]),
        )
        registry = AppRegistry()
        registry.register("sync-app", manifest)

        app = _create_app(registry=registry, running_apps={"sync-app"})
        client = TestClient(app)
        resp = client.get("/api/apps/commands")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["actionType"] == "post"
        assert data[0]["actionUrl"] == "/app/sync-app/api/sync"

    def test_navigate_action_type_url(self):
        """Navigate action type uses path as-is for actionUrl."""
        cmd = _make_command(
            id="go-settings",
            label="Open Settings",
            action_type="navigate",
            fragment=None,
            path="/browser/settings",
        )
        manifest = _make_manifest(
            app_id="nav-app",
            name="Nav App",
            contributions=AppContributions(commandPalette=[cmd]),
        )
        registry = AppRegistry()
        registry.register("nav-app", manifest)

        app = _create_app(registry=registry, running_apps={"nav-app"})
        client = TestClient(app)
        resp = client.get("/api/apps/commands")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["actionType"] == "navigate"
        assert data[0]["actionUrl"] == "/browser/settings"

    def test_multiple_apps_multiple_commands(self):
        """Multiple running apps with commands all contribute entries."""
        cmd1 = _make_command(id="cmd-a", label="Command A")
        cmd2 = _make_command(id="cmd-b", label="Command B")
        m1 = _make_manifest(
            app_id="app-a", name="App A",
            contributions=AppContributions(commandPalette=[cmd1]),
        )
        m2 = _make_manifest(
            app_id="app-b", name="App B",
            contributions=AppContributions(commandPalette=[cmd2]),
        )
        registry = AppRegistry()
        registry.register("app-a", m1)
        registry.register("app-b", m2)

        app = _create_app(registry=registry, running_apps={"app-a", "app-b"})
        client = TestClient(app)
        resp = client.get("/api/apps/commands")
        data = resp.json()
        assert len(data) == 2
        ids = [d["id"] for d in data]
        assert "appcmd:app-a:cmd-a" in ids
        assert "appcmd:app-b:cmd-b" in ids

    def test_keywords_included_in_response(self):
        """Keywords from manifest are passed through in JSON response."""
        cmd = _make_command(
            id="search-crm",
            label="Search CRM",
            keywords=["crm", "contacts", "deals"],
        )
        manifest = _make_manifest(
            app_id="crm-app",
            name="CRM",
            contributions=AppContributions(commandPalette=[cmd]),
        )
        registry = AppRegistry()
        registry.register("crm-app", manifest)

        app = _create_app(registry=registry, running_apps={"crm-app"})
        client = TestClient(app)
        resp = client.get("/api/apps/commands")
        data = resp.json()
        assert data[0]["keywords"] == ["crm", "contacts", "deals"]

    def test_navigate_matching_app_page_includes_appid_pageid(self):
        """Navigate command whose path matches an app page includes appId/pageId."""
        page = AppPage(
            id="reader",
            path="/reader",
            label="Reader",
            icon="rss",
            fragment="reader-main",
        )
        cmd = _make_command(
            id="open-reader",
            label="Open Reader",
            action_type="navigate",
            fragment=None,
            path="/reader",
        )
        manifest = AppManifestSchema(
            appId="rss-reader",
            version="1.0.0",
            name="RSS Reader",
            description="Test",
            backend=AppBackend(entrypoint="backend.app:RssApp"),
            dependencies=AppDependencies(platform=">=0.1.0"),
            frontend=AppFrontend(),
            ui=AppUI(
                pages=[page],
                contributions=AppContributions(commandPalette=[cmd]),
            ),
        )
        registry = AppRegistry()
        registry.register("rss-reader", manifest)

        app = _create_app(registry=registry, running_apps={"rss-reader"})
        client = TestClient(app)
        resp = client.get("/api/apps/commands")
        data = resp.json()
        assert len(data) == 1
        entry = data[0]
        assert entry["actionType"] == "navigate"
        assert entry["actionUrl"] == "/reader"
        assert entry["appId"] == "rss-reader"
        assert entry["pageId"] == "reader"

    def test_navigate_non_matching_path_omits_appid_pageid(self):
        """Navigate command whose path does NOT match any app page omits appId/pageId."""
        page = AppPage(
            id="reader",
            path="/reader",
            label="Reader",
            icon="rss",
            fragment="reader-main",
        )
        cmd = _make_command(
            id="go-settings",
            label="Open Settings",
            action_type="navigate",
            fragment=None,
            path="/browser/settings",
        )
        manifest = AppManifestSchema(
            appId="rss-reader",
            version="1.0.0",
            name="RSS Reader",
            description="Test",
            backend=AppBackend(entrypoint="backend.app:RssApp"),
            dependencies=AppDependencies(platform=">=0.1.0"),
            frontend=AppFrontend(),
            ui=AppUI(
                pages=[page],
                contributions=AppContributions(commandPalette=[cmd]),
            ),
        )
        registry = AppRegistry()
        registry.register("rss-reader", manifest)

        app = _create_app(registry=registry, running_apps={"rss-reader"})
        client = TestClient(app)
        resp = client.get("/api/apps/commands")
        data = resp.json()
        assert len(data) == 1
        entry = data[0]
        assert entry["actionType"] == "navigate"
        assert entry["actionUrl"] == "/browser/settings"
        assert "appId" not in entry
        assert "pageId" not in entry


# ── Unauthenticated 401 Tests ──


class TestUnauthenticatedEndpoints:
    """Verify all app endpoints return 401 without authentication."""

    def _create_app_no_auth(self) -> FastAPI:
        """Create a FastAPI test app WITHOUT auth override — endpoints require login.

        Overrides get_db_session with a dummy so the dependency chain
        resolves without a real DB engine. get_current_user still raises
        401 because no session cookie is present.
        """
        test_app = FastAPI()
        test_app.include_router(apps_router)
        test_app.include_router(app_commands_router)

        # Provide a dummy DB session so get_current_user's Depends(get_db_session)
        # resolves — the function body raises 401 before using the session.
        async def _dummy_db():
            yield None
        test_app.dependency_overrides[get_db_session] = _dummy_db

        return test_app

    def test_apps_explorer_requires_auth(self):
        app = self._create_app_no_auth()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/apps/explorer")
        assert resp.status_code == 401

    def test_app_page_requires_auth(self):
        app = self._create_app_no_auth()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/apps/test-app/page/main")
        assert resp.status_code == 401

    def test_right_pane_sections_requires_auth(self):
        app = self._create_app_no_auth()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/apps/right-pane-sections?iri=urn:test:1")
        assert resp.status_code == 401

    def test_views_explorer_requires_auth(self):
        app = self._create_app_no_auth()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/apps/views/explorer")
        assert resp.status_code == 401

    def test_app_view_tab_requires_auth(self):
        app = self._create_app_no_auth()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/apps/test-app/view/my-view")
        assert resp.status_code == 401

    def test_commands_list_requires_auth(self):
        app = self._create_app_no_auth()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/apps/commands")
        assert resp.status_code == 401
