"""Tests for app.template_helpers — asset URL resolution in dev and production modes."""

import json
import logging

import pytest

import app.template_helpers as th


@pytest.fixture(autouse=True)
def _reset_module_state():
    """Reset module-level state before each test."""
    th._manifest = None
    th._manifest_loaded = False
    yield
    th._manifest = None
    th._manifest_loaded = False


# ---------------------------------------------------------------------------
# asset_url — production mode (manifest loaded)
# ---------------------------------------------------------------------------


class TestAssetUrlWithManifest:
    def test_resolves_js_via_manifest(self):
        th._manifest = {"workspace.js": "workspace-abc123.min.js"}
        th._manifest_loaded = True
        assert th.asset_url("workspace.js") == "/assets/workspace-abc123.min.js"

    def test_resolves_css_via_manifest(self):
        th._manifest = {"workspace.css": "workspace-def456.min.css"}
        th._manifest_loaded = True
        assert th.asset_url("workspace.css") == "/assets/workspace-def456.min.css"

    def test_missing_key_falls_back_to_dev_js(self):
        th._manifest = {"other.js": "other-111.min.js"}
        th._manifest_loaded = True
        assert th.asset_url("workspace.js") == "/js/workspace.js"

    def test_missing_key_falls_back_to_dev_css(self):
        th._manifest = {"other.css": "other-222.min.css"}
        th._manifest_loaded = True
        assert th.asset_url("workspace.css") == "/css/workspace.css"


# ---------------------------------------------------------------------------
# asset_url — dev mode (no manifest)
# ---------------------------------------------------------------------------


class TestAssetUrlWithoutManifest:
    def test_js_returns_dev_path(self):
        assert th.asset_url("workspace.js") == "/js/workspace.js"

    def test_css_returns_dev_path(self):
        assert th.asset_url("workspace.css") == "/css/workspace.css"

    def test_other_extension_returns_root_path(self):
        assert th.asset_url("favicon.ico") == "/favicon.ico"


# ---------------------------------------------------------------------------
# asset_url — edge cases
# ---------------------------------------------------------------------------


class TestAssetUrlEdgeCases:
    def test_empty_string_returns_empty(self):
        assert th.asset_url("") == ""

    def test_none_returns_empty(self):
        # Filter receives None if template variable is undefined
        assert th.asset_url(None) == ""

    def test_no_extension_returns_root_path(self):
        assert th.asset_url("README") == "/README"

    def test_dotfile_returns_root_path(self):
        # ".htaccess" ends with no common extension
        assert th.asset_url(".htaccess") == "/.htaccess"

    def test_nested_name_in_manifest(self):
        th._manifest = {"hljs-github.css": "hljs-github-abc.css"}
        th._manifest_loaded = True
        assert th.asset_url("hljs-github.css") == "/assets/hljs-github-abc.css"


# ---------------------------------------------------------------------------
# is_asset_manifest_available
# ---------------------------------------------------------------------------


class TestIsAssetManifestAvailable:
    def test_true_when_manifest_loaded(self):
        th._manifest = {"a.js": "a-111.min.js"}
        th._manifest_loaded = True
        assert th.is_asset_manifest_available() is True

    def test_false_when_no_manifest(self):
        th._manifest = None
        th._manifest_loaded = True
        assert th.is_asset_manifest_available() is False

    def test_false_before_load(self):
        assert th.is_asset_manifest_available() is False


# ---------------------------------------------------------------------------
# _load_manifest — filesystem interactions
# ---------------------------------------------------------------------------


class TestLoadManifest:
    def test_valid_json_via_env_override(self, tmp_path, monkeypatch):
        manifest = {"app.js": "app-aaa.min.js", "app.css": "app-bbb.min.css"}
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(manifest))

        monkeypatch.setattr(th, "_MANIFEST_PATH_OVERRIDE", str(p))
        monkeypatch.setattr(th, "_MANIFEST_SEARCH_PATHS", [])
        result = th._load_manifest()

        assert result == manifest
        assert th._manifest == manifest
        assert th._manifest_loaded is True

    def test_valid_json_via_search_path(self, tmp_path, monkeypatch):
        manifest = {"app.js": "app-aaa.min.js"}
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(manifest))

        monkeypatch.setattr(th, "_MANIFEST_PATH_OVERRIDE", None)
        monkeypatch.setattr(th, "_MANIFEST_SEARCH_PATHS", [str(p)])
        result = th._load_manifest()

        assert result == manifest

    def test_first_valid_search_path_wins(self, tmp_path, monkeypatch):
        """When multiple search paths exist, the first valid manifest is used."""
        m1 = {"first.js": "first-111.min.js"}
        m2 = {"second.js": "second-222.min.js"}
        p1 = tmp_path / "m1" / "manifest.json"
        p2 = tmp_path / "m2" / "manifest.json"
        p1.parent.mkdir()
        p2.parent.mkdir()
        p1.write_text(json.dumps(m1))
        p2.write_text(json.dumps(m2))

        monkeypatch.setattr(th, "_MANIFEST_PATH_OVERRIDE", None)
        monkeypatch.setattr(th, "_MANIFEST_SEARCH_PATHS", [str(p1), str(p2)])
        result = th._load_manifest()

        assert result == m1

    def test_skips_missing_then_finds_next(self, tmp_path, monkeypatch):
        """Missing paths are skipped; search continues to the next candidate."""
        manifest = {"found.js": "found-aaa.min.js"}
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(manifest))

        monkeypatch.setattr(th, "_MANIFEST_PATH_OVERRIDE", None)
        monkeypatch.setattr(
            th, "_MANIFEST_SEARCH_PATHS", ["/nonexistent/nope.json", str(p)]
        )
        result = th._load_manifest()

        assert result == manifest

    def test_all_paths_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(th, "_MANIFEST_PATH_OVERRIDE", None)
        monkeypatch.setattr(
            th, "_MANIFEST_SEARCH_PATHS", ["/no/a.json", "/no/b.json"]
        )
        result = th._load_manifest()

        assert result is None
        assert th._manifest is None
        assert th._manifest_loaded is True

    def test_invalid_json(self, tmp_path, monkeypatch, caplog):
        p = tmp_path / "bad.json"
        p.write_text("not json {{{")

        monkeypatch.setattr(th, "_MANIFEST_PATH_OVERRIDE", str(p))
        monkeypatch.setattr(th, "_MANIFEST_SEARCH_PATHS", [])
        with caplog.at_level(logging.WARNING):
            result = th._load_manifest()

        assert result is None
        assert th._manifest is None
        assert "Invalid JSON" in caplog.text

    def test_non_dict_json(self, tmp_path, monkeypatch, caplog):
        p = tmp_path / "array.json"
        p.write_text('["not", "a", "dict"]')

        monkeypatch.setattr(th, "_MANIFEST_PATH_OVERRIDE", str(p))
        monkeypatch.setattr(th, "_MANIFEST_SEARCH_PATHS", [])
        with caplog.at_level(logging.WARNING):
            result = th._load_manifest()

        assert result is None
        assert "not a JSON object" in caplog.text

    def test_caches_after_first_load(self, tmp_path, monkeypatch):
        manifest = {"x.js": "x-111.min.js"}
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(manifest))

        monkeypatch.setattr(th, "_MANIFEST_PATH_OVERRIDE", str(p))
        monkeypatch.setattr(th, "_MANIFEST_SEARCH_PATHS", [])
        th._load_manifest()

        # Change file on disk — should not re-read
        p.write_text(json.dumps({"y.js": "y-222.min.js"}))
        result = th._load_manifest()

        assert result == manifest  # still the first load

    def test_env_override_takes_priority_over_search(self, tmp_path, monkeypatch):
        """ASSET_MANIFEST_PATH env override is checked before search paths."""
        m_env = {"env.js": "env-111.min.js"}
        m_search = {"search.js": "search-222.min.js"}
        p_env = tmp_path / "env_manifest.json"
        p_search = tmp_path / "search_manifest.json"
        p_env.write_text(json.dumps(m_env))
        p_search.write_text(json.dumps(m_search))

        monkeypatch.setattr(th, "_MANIFEST_PATH_OVERRIDE", str(p_env))
        monkeypatch.setattr(th, "_MANIFEST_SEARCH_PATHS", [str(p_search)])
        result = th._load_manifest()

        assert result == m_env


# ---------------------------------------------------------------------------
# init_template_helpers
# ---------------------------------------------------------------------------


class TestInitTemplateHelpers:
    def test_registers_filter_and_global(self, tmp_path, monkeypatch):
        manifest = {"app.js": "app-aaa.min.js"}
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(manifest))
        monkeypatch.setattr(th, "_MANIFEST_PATH_OVERRIDE", str(p))
        monkeypatch.setattr(th, "_MANIFEST_SEARCH_PATHS", [])

        # Minimal app mock with Jinja2-like env
        class FakeEnv:
            def __init__(self):
                self.filters = {}
                self.globals = {}

        class FakeTemplates:
            env = FakeEnv()

        class FakeState:
            templates = FakeTemplates()

        class FakeApp:
            state = FakeState()

        app = FakeApp()
        th.init_template_helpers(app)

        assert "asset_url" in app.state.templates.env.filters
        assert app.state.templates.env.filters["asset_url"] is th.asset_url
        assert app.state.templates.env.globals["asset_manifest_available"] is True

    def test_dev_mode_when_no_manifest(self, monkeypatch):
        monkeypatch.setattr(th, "_MANIFEST_PATH_OVERRIDE", None)
        monkeypatch.setattr(th, "_MANIFEST_SEARCH_PATHS", ["/nonexistent/m.json"])

        class FakeEnv:
            def __init__(self):
                self.filters = {}
                self.globals = {}

        class FakeTemplates:
            env = FakeEnv()

        class FakeState:
            templates = FakeTemplates()

        class FakeApp:
            state = FakeState()

        app = FakeApp()
        th.init_template_helpers(app)

        assert "asset_url" in app.state.templates.env.filters
        assert app.state.templates.env.globals["asset_manifest_available"] is False
