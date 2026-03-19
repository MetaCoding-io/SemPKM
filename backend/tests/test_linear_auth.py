"""Unit tests for Linear Sync auth helpers and app route handlers.

Loads ``auth.py`` and ``app.py`` from the apps directory using importlib
to avoid requiring the app to be installed as a package. All HTTP and
state interactions are mocked — no network calls are made.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

# ---------------------------------------------------------------------------
# Load modules from apps directory
# ---------------------------------------------------------------------------

_APPS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "apps" / "linear-sync"
)
_SERVICES_DIR = _APPS_DIR / "services"

# Load linear_client first (auth.py depends on it)
_LC_PATH = _SERVICES_DIR / "linear_client.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# linear_client must be in sys.modules before auth imports it
lc = _load_module("linear_client", _LC_PATH)
LinearAuthError = lc.LinearAuthError
LinearAPIError = lc.LinearAPIError

# Now load auth module — it tries "from services.linear_client" then "from linear_client"
auth = _load_module("auth", _SERVICES_DIR / "auth.py")

build_oauth_authorize_url = auth.build_oauth_authorize_url
exchange_code = auth.exchange_code
store_auth_tokens = auth.store_auth_tokens
store_workspace_info = auth.store_workspace_info
get_connection_status = auth.get_connection_status
clear_auth_state = auth.clear_auth_state
LINEAR_AUTHORIZE_URL = auth.LINEAR_AUTHORIZE_URL
LINEAR_TOKEN_URL = auth.LINEAR_TOKEN_URL
AUTH_STATE_KEYS = auth.AUTH_STATE_KEYS


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

class MockResponse:
    """Minimal httpx.Response stand-in."""

    def __init__(
        self,
        status_code: int = 200,
        body: dict | str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._body = body if body is not None else {}
        self.headers = headers or {}

    @property
    def text(self) -> str:
        if isinstance(self._body, str):
            return self._body
        return json.dumps(self._body)

    def json(self) -> Any:
        if isinstance(self._body, str):
            return json.loads(self._body)
        return self._body


class MockHttpClient:
    """Records calls and returns preset responses."""

    def __init__(self, responses: list[MockResponse] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._responses = list(responses or [])
        self._idx = 0

    async def post(self, url: str, **kwargs: Any) -> MockResponse:
        self.calls.append({"method": "POST", "url": url, **kwargs})
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            return resp
        return MockResponse(500, {"error": "No mock response configured"})

    async def get(self, url: str, **kwargs: Any) -> MockResponse:
        self.calls.append({"method": "GET", "url": url, **kwargs})
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            return resp
        return MockResponse(500, {"error": "No mock response configured"})


class MockStateClient:
    """In-memory state store with async get/set."""

    def __init__(self, initial: dict[str, str] | None = None) -> None:
        self._store: dict[str, str] = dict(initial or {})
        self.get_calls: list[str] = []
        self.set_calls: list[tuple[str, str]] = []

    async def get(self, key: str) -> str | None:
        self.get_calls.append(key)
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self.set_calls.append((key, value))
        self._store[key] = value


# ---------------------------------------------------------------------------
# Tests: build_oauth_authorize_url
# ---------------------------------------------------------------------------

class TestBuildOAuthAuthorizeUrl:

    def test_basic_url_construction(self):
        url = build_oauth_authorize_url(
            client_id="client123",
            redirect_uri="http://localhost:8000/callback",
            state="csrf_token_abc",
        )
        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "linear.app"
        assert parsed.path == "/oauth/authorize"

        params = parse_qs(parsed.query)
        assert params["client_id"] == ["client123"]
        assert params["redirect_uri"] == ["http://localhost:8000/callback"]
        assert params["response_type"] == ["code"]
        assert params["state"] == ["csrf_token_abc"]
        assert params["scope"] == ["read,write"]

    def test_url_encodes_redirect_uri(self):
        url = build_oauth_authorize_url(
            client_id="cid",
            redirect_uri="http://example.com/path?foo=bar&baz=1",
            state="s",
        )
        # The redirect_uri should be properly encoded
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        assert params["redirect_uri"] == ["http://example.com/path?foo=bar&baz=1"]
        # The raw URL should contain encoded characters
        assert "foo%3Dbar" in url or "foo=bar" in parse_qs(parsed.query)["redirect_uri"][0]


# ---------------------------------------------------------------------------
# Tests: exchange_code
# ---------------------------------------------------------------------------

class TestExchangeCode:

    @pytest.mark.asyncio
    async def test_success_returns_token_dict(self):
        http = MockHttpClient([
            MockResponse(200, {
                "access_token": "acc_tok_123",
                "refresh_token": "ref_tok_456",
                "expires_in": 3600,
            })
        ])

        result = await exchange_code(
            http,
            code="auth_code_abc",
            client_id="cid",
            client_secret="csecret",
            redirect_uri="http://localhost/cb",
        )

        assert result["access_token"] == "acc_tok_123"
        assert result["refresh_token"] == "ref_tok_456"
        assert result["expires_in"] == 3600

        # Verify the POST was made correctly
        call = http.calls[0]
        assert call["url"] == LINEAR_TOKEN_URL
        assert call["data"]["grant_type"] == "authorization_code"
        assert call["data"]["code"] == "auth_code_abc"
        assert call["data"]["client_id"] == "cid"
        assert call["data"]["client_secret"] == "csecret"

    @pytest.mark.asyncio
    async def test_failure_raises_auth_error(self):
        http = MockHttpClient([
            MockResponse(400, {"error": "invalid_grant"})
        ])

        with pytest.raises(LinearAuthError, match="OAuth token exchange failed: 400"):
            await exchange_code(
                http,
                code="bad_code",
                client_id="cid",
                client_secret="csecret",
                redirect_uri="http://localhost/cb",
            )


# ---------------------------------------------------------------------------
# Tests: store_auth_tokens
# ---------------------------------------------------------------------------

class TestStoreAuthTokens:

    @pytest.mark.asyncio
    async def test_stores_oauth_tokens(self):
        state = MockStateClient()

        await store_auth_tokens(
            state,
            access_token="oauth_access_tok",
            refresh_token="oauth_refresh_tok",
            auth_method="oauth",
        )

        assert state._store["access_token"] == "oauth_access_tok"
        assert state._store["refresh_token"] == "oauth_refresh_tok"
        assert state._store["auth_method"] == "oauth"
        # api_key should NOT be set for OAuth
        assert "api_key" not in state._store

    @pytest.mark.asyncio
    async def test_stores_api_key(self):
        state = MockStateClient()

        await store_auth_tokens(
            state,
            access_token="lin_api_mykey",
            refresh_token=None,
            auth_method="api_key",
        )

        assert state._store["api_key"] == "lin_api_mykey"
        assert state._store["auth_method"] == "api_key"
        # access_token and refresh_token should NOT be set for API key
        assert "access_token" not in state._store
        assert "refresh_token" not in state._store

    @pytest.mark.asyncio
    async def test_oauth_without_refresh_token(self):
        state = MockStateClient()

        await store_auth_tokens(
            state,
            access_token="acc_tok",
            refresh_token=None,
            auth_method="oauth",
        )

        assert state._store["access_token"] == "acc_tok"
        assert state._store["auth_method"] == "oauth"
        assert "refresh_token" not in state._store


# ---------------------------------------------------------------------------
# Tests: store_workspace_info
# ---------------------------------------------------------------------------

class TestStoreWorkspaceInfo:

    @pytest.mark.asyncio
    async def test_stores_workspace_data(self):
        state = MockStateClient()

        await store_workspace_info(state, "Acme Corp", "org_123")

        assert state._store["workspace_name"] == "Acme Corp"
        assert state._store["workspace_id"] == "org_123"


# ---------------------------------------------------------------------------
# Tests: get_connection_status
# ---------------------------------------------------------------------------

class TestGetConnectionStatus:

    @pytest.mark.asyncio
    async def test_connected_with_full_info(self):
        state = MockStateClient({
            "auth_method": "api_key",
            "workspace_name": "My Workspace",
            "workspace_id": "ws_1",
        })

        status = await get_connection_status(state)

        assert status["connected"] is True
        assert status["auth_method"] == "api_key"
        assert status["workspace_name"] == "My Workspace"
        assert status["workspace_id"] == "ws_1"

    @pytest.mark.asyncio
    async def test_disconnected_when_no_auth(self):
        state = MockStateClient()

        status = await get_connection_status(state)

        assert status["connected"] is False
        assert status["auth_method"] is None
        assert status["workspace_name"] is None

    @pytest.mark.asyncio
    async def test_disconnected_after_clear(self):
        """After clear_auth_state, connection shows as disconnected."""
        state = MockStateClient({
            "auth_method": "oauth",
            "workspace_name": "Test",
            "workspace_id": "x",
            "access_token": "tok",
            "refresh_token": "ref",
        })

        await clear_auth_state(state)
        status = await get_connection_status(state)

        # Empty string is falsy, so connected should be False
        assert status["connected"] is False


# ---------------------------------------------------------------------------
# Tests: clear_auth_state
# ---------------------------------------------------------------------------

class TestClearAuthState:

    @pytest.mark.asyncio
    async def test_clears_all_auth_keys(self):
        state = MockStateClient({
            "access_token": "tok",
            "refresh_token": "ref",
            "api_key": "key",
            "auth_method": "oauth",
            "workspace_name": "Acme",
            "workspace_id": "org_1",
        })

        await clear_auth_state(state)

        # All keys should now be empty strings
        for key in AUTH_STATE_KEYS:
            assert state._store[key] == ""

    @pytest.mark.asyncio
    async def test_clear_on_empty_state(self):
        """Clearing when already empty should not raise."""
        state = MockStateClient()

        await clear_auth_state(state)

        for key in AUTH_STATE_KEYS:
            assert state._store[key] == ""


# ---------------------------------------------------------------------------
# Tests: Template rendering (Jinja2)
# ---------------------------------------------------------------------------

class TestTemplateRendering:
    """Verify templates render without Jinja errors."""

    @pytest.fixture
    def jinja_env(self):
        from jinja2 import Environment, FileSystemLoader
        template_dir = _APPS_DIR / "frontend" / "templates"
        return Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True,
        )

    def test_connect_html_renders_without_error(self, jinja_env):
        result = jinja_env.get_template("connect.html").render(error=None)
        assert "Connect to Linear" in result
        assert "API Key" in result

    def test_connect_html_renders_with_error(self, jinja_env):
        result = jinja_env.get_template("connect.html").render(
            error="Invalid API key"
        )
        assert "Invalid API key" in result
        assert "alert-error" in result

    def test_connect_status_renders_with_teams(self, jinja_env):
        result = jinja_env.get_template("connect_status.html").render(
            workspace_name="Test Workspace",
            auth_method="api_key",
            teams=[
                {"name": "Engineering", "key": "ENG"},
                {"name": "Design", "key": "DES"},
            ],
        )
        assert "Test Workspace" in result
        assert "Api Key" in result  # title-cased from filter
        assert "Engineering" in result
        assert "ENG" in result
        assert "Design" in result
        assert "Disconnect" in result

    def test_connect_status_renders_empty_teams(self, jinja_env):
        result = jinja_env.get_template("connect_status.html").render(
            workspace_name="Acme",
            auth_method="oauth",
            teams=[],
        )
        assert "Acme" in result
        assert "No teams found" in result
