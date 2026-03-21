"""Tests for RSS Reader UI route handlers — reading pane, star/read toggles,
mark-all-read, unsubscribe, and workspace views.

Exercises all 5 new route handlers added in S03/T03 plus the 2 workspace views:
- ``/_fragments/article-reading-pane`` — GET, article display + empty state
- ``/_fragments/toggle-star`` — POST, star flip via object.patch
- ``/_fragments/toggle-read`` — POST, mark-read + toggle mode
- ``/_fragments/mark-all-read`` — POST, batch mark-read
- ``/_fragments/unsubscribe`` — POST, soft-delete via feed_service.unsubscribe

Uses mocked SDK clients (graph, commands) — no running Docker stack required.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

# ── Module import via file path ──

_app_path = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "rss-reader"
    / "app.py"
)
_spec = importlib.util.spec_from_file_location("rss_reader_ui_mod", _app_path)
_rss_mod = importlib.util.module_from_spec(_spec)
sys.modules["rss_reader_ui_mod"] = _rss_mod
_spec.loader.exec_module(_rss_mod)

ARTICLE_TYPE = _rss_mod.ARTICLE_TYPE
RSS_NS = _rss_mod.RSS_NS
SUBSCRIPTION_TYPE = _rss_mod.SUBSCRIPTION_TYPE
FEED_SIDEBAR_SPARQL = _rss_mod.FEED_SIDEBAR_SPARQL
BPKM_TAGS = _rss_mod.BPKM_TAGS
rss_reader_app = _rss_mod.rss_reader_app

# ── Constants ──

ARTICLE_IRI = "urn:sempkm:app:rss-reader:article-abc123"
FEED_IRI = "urn:sempkm:app:rss-reader:sub-feed456"


# ── Helpers ──


def _make_article_bindings(
    title="Test Article",
    link="https://example.com/article/1",
    author="Alice",
    created="2026-03-15T10:30:00+00:00",
    is_starred="false",
    is_read="false",
    body="# Hello World\n\nThis is **markdown** content.",
    feed_title="My Feed",
    description="A short summary",
):
    """Build SPARQL result bindings for a single article query."""
    b = {}
    if title:
        b["title"] = {"value": title}
    if link:
        b["link"] = {"value": link}
    if author:
        b["author"] = {"value": author}
    if created:
        b["created"] = {"value": created}
    if is_starred is not None:
        b["isStarred"] = {"value": is_starred}
    if is_read is not None:
        b["isRead"] = {"value": is_read}
    if body:
        b["body"] = {"value": body}
    if feed_title:
        b["feedTitle"] = {"value": feed_title}
    if description:
        b["description"] = {"value": description}
    return {"results": {"bindings": [b]}}


def _make_sidebar_bindings(feeds=None):
    """Build SPARQL result bindings for feed sidebar."""
    if feeds is None:
        feeds = []
    bindings = []
    for f in feeds:
        bindings.append({
            "sub": {"value": f.get("iri", "")},
            "feedUrl": {"value": f.get("url", "")},
            "title": {"value": f.get("title", "")},
            "errorCount": {"value": str(f.get("error_count", 0))},
            "lastError": {"value": f.get("last_error", "")},
            "unreadCount": {"value": str(f.get("unread_count", 0))},
        })
    return {"results": {"bindings": bindings}}


def _empty_sparql():
    """Empty SPARQL result."""
    return {"results": {"bindings": []}}


# ── Fixtures ──


@pytest.fixture
def mock_ctx():
    """Create a mock AppContext with graph, commands, and render_template."""
    ctx = MagicMock()
    ctx.graph = MagicMock()
    ctx.graph.query = AsyncMock(return_value=_empty_sparql())
    ctx.commands = MagicMock()
    ctx.commands.execute = AsyncMock()

    # Template rendering: return template name + kwargs as HTML for inspection
    def _render(template_name, **kwargs):
        # For article-reading-pane.html, we need a real-ish render.
        # For tests, return the template name and key values as HTML.
        parts = [f'<div data-template="{template_name}"']
        if "article" in kwargs:
            art = kwargs["article"]
            parts.append(f' data-article-iri="{art.get("iri", "")}"')
            parts.append(f' data-starred="{str(art.get("is_starred", False)).lower()}"')
            parts.append(f' data-read="{str(art.get("is_read", False)).lower()}"')
        if "article_iri" in kwargs:
            parts.append(f' data-article-iri="{kwargs["article_iri"]}"')
        if "is_starred" in kwargs:
            parts.append(f' data-starred="{str(kwargs["is_starred"]).lower()}"')
        if "feeds" in kwargs:
            parts.append(f' data-feed-count="{len(kwargs["feeds"])}"')
        parts.append(">")
        if "body" in kwargs and kwargs["body"]:
            parts.append(f'<div class="body">{kwargs["body"][:50]}</div>')
        if "md_id" in kwargs:
            parts.append(f'<div class="md-id">{kwargs["md_id"]}</div>')
        parts.append("</div>")
        return "".join(parts)

    ctx.render_template = _render
    return ctx


@pytest.fixture
def app(mock_ctx):
    """Create a Starlette test app from the rss_reader_app routes."""
    from starlette.applications import Starlette
    from starlette.routing import Route

    routes = []
    for methods, path, handler in rss_reader_app._routes:
        routes.append(Route(
            path,
            endpoint=handler,
            methods=methods,
        ))

    starlette_app = Starlette(routes=routes)
    starlette_app.state.ctx = mock_ctx
    return starlette_app


@pytest.fixture
def client(app):
    """TestClient for making HTTP requests."""
    return TestClient(app)


# ═══════════════════════════════════════════════════
# article-reading-pane tests
# ═══════════════════════════════════════════════════


class TestArticleReadingPane:
    """Tests for /_fragments/article-reading-pane GET handler."""

    def test_empty_state_when_no_article_iri(self, client):
        """No article_iri → empty state placeholder."""
        resp = client.get("/_fragments/article-reading-pane")
        assert resp.status_code == 200
        assert "Select an article to read" in resp.text

    def test_empty_state_with_blank_iri(self, client):
        """Blank article_iri → empty state."""
        resp = client.get("/_fragments/article-reading-pane?article_iri=")
        assert resp.status_code == 200
        assert "Select an article to read" in resp.text

    def test_article_not_found(self, client, mock_ctx):
        """Valid IRI but no SPARQL results → 'Article not found'."""
        mock_ctx.graph.query = AsyncMock(return_value=_empty_sparql())
        resp = client.get(f"/_fragments/article-reading-pane?article_iri={ARTICLE_IRI}")
        assert resp.status_code == 200
        assert "Article not found" in resp.text

    def test_renders_article_with_body(self, client, mock_ctx):
        """Full article with body → renders template with markdown body."""
        mock_ctx.graph.query = AsyncMock(
            return_value=_make_article_bindings(body="# Hello", is_read="false")
        )
        resp = client.get(f"/_fragments/article-reading-pane?article_iri={ARTICLE_IRI}")
        assert resp.status_code == 200
        assert "article-reading-pane.html" in resp.text
        assert "# Hello" in resp.text

    def test_falls_back_to_description(self, client, mock_ctx):
        """No body → falls back to description."""
        mock_ctx.graph.query = AsyncMock(
            return_value=_make_article_bindings(body="", description="Short summary")
        )
        resp = client.get(f"/_fragments/article-reading-pane?article_iri={ARTICLE_IRI}")
        assert resp.status_code == 200
        assert "Short summary" in resp.text

    def test_no_body_no_description(self, client, mock_ctx):
        """No body and no description → body is None in template context."""
        mock_ctx.graph.query = AsyncMock(
            return_value=_make_article_bindings(body="", description="")
        )
        resp = client.get(f"/_fragments/article-reading-pane?article_iri={ARTICLE_IRI}")
        assert resp.status_code == 200
        # Template renders without body div
        assert "article-reading-pane.html" in resp.text

    def test_is_starred_parsed_correctly(self, client, mock_ctx):
        """isStarred='true' → is_starred=True in template."""
        mock_ctx.graph.query = AsyncMock(
            return_value=_make_article_bindings(is_starred="true")
        )
        resp = client.get(f"/_fragments/article-reading-pane?article_iri={ARTICLE_IRI}")
        assert 'data-starred="true"' in resp.text.lower()

    def test_is_read_parsed_correctly(self, client, mock_ctx):
        """isRead='true' → is_read=True in template."""
        mock_ctx.graph.query = AsyncMock(
            return_value=_make_article_bindings(is_read="true")
        )
        resp = client.get(f"/_fragments/article-reading-pane?article_iri={ARTICLE_IRI}")
        assert 'data-read="true"' in resp.text.lower()

    def test_sparql_error_returns_error_fragment(self, client, mock_ctx):
        """SPARQL query failure → rss-error fragment."""
        mock_ctx.graph.query = AsyncMock(side_effect=Exception("connection refused"))
        resp = client.get(f"/_fragments/article-reading-pane?article_iri={ARTICLE_IRI}")
        assert resp.status_code == 200
        assert "rss-error" in resp.text
        assert "Failed to load article" in resp.text

    def test_iri_sanitization(self, client, mock_ctx):
        """Angle brackets and backslashes stripped from IRI."""
        mock_ctx.graph.query = AsyncMock(return_value=_empty_sparql())
        resp = client.get(
            "/_fragments/article-reading-pane?article_iri=<malicious>\\injection"
        )
        # Should not crash — sanitized IRI used
        assert resp.status_code == 200

    def test_md_id_present(self, client, mock_ctx):
        """Template receives md_id for markdown source/target element IDs."""
        mock_ctx.graph.query = AsyncMock(
            return_value=_make_article_bindings()
        )
        resp = client.get(f"/_fragments/article-reading-pane?article_iri={ARTICLE_IRI}")
        assert "md-id" in resp.text  # md_id passed to template


# ═══════════════════════════════════════════════════
# toggle-star tests
# ═══════════════════════════════════════════════════


class TestToggleStar:
    """Tests for /_fragments/toggle-star POST handler."""

    def test_missing_article_iri(self, client):
        """No article_iri → 400 error."""
        resp = client.post("/_fragments/toggle-star", data={})
        assert resp.status_code == 400
        assert "Missing article_iri" in resp.text

    def test_star_unstarred_article(self, client, mock_ctx):
        """Star an article that is currently unstarred."""
        mock_ctx.graph.query = AsyncMock(
            return_value={"results": {"bindings": [{"val": {"value": "false"}}]}}
        )
        resp = client.post(
            "/_fragments/toggle-star", data={"article_iri": ARTICLE_IRI}
        )
        assert resp.status_code == 200
        assert "star-button.html" in resp.text
        assert 'data-starred="true"' in resp.text.lower()
        # Verify object.patch was called with True
        mock_ctx.commands.execute.assert_called_once()
        args = mock_ctx.commands.execute.call_args
        assert args[0][0] == "object.patch"
        assert args[0][1]["properties"][f"{RSS_NS}isStarred"] is True

    def test_unstar_starred_article(self, client, mock_ctx):
        """Unstar an article that is currently starred."""
        mock_ctx.graph.query = AsyncMock(
            return_value={"results": {"bindings": [{"val": {"value": "true"}}]}}
        )
        resp = client.post(
            "/_fragments/toggle-star", data={"article_iri": ARTICLE_IRI}
        )
        assert resp.status_code == 200
        assert 'data-starred="false"' in resp.text.lower()
        args = mock_ctx.commands.execute.call_args
        assert args[0][1]["properties"][f"{RSS_NS}isStarred"] is False

    def test_hx_trigger_header_on_success(self, client, mock_ctx):
        """Successful toggle emits HX-Trigger: articleStateChanged."""
        mock_ctx.graph.query = AsyncMock(
            return_value={"results": {"bindings": [{"val": {"value": "false"}}]}}
        )
        resp = client.post(
            "/_fragments/toggle-star", data={"article_iri": ARTICLE_IRI}
        )
        assert resp.headers.get("HX-Trigger") == "articleStateChanged"

    def test_sparql_error_returns_error_fragment(self, client, mock_ctx):
        """SPARQL failure → error fragment."""
        mock_ctx.graph.query = AsyncMock(side_effect=Exception("timeout"))
        resp = client.post(
            "/_fragments/toggle-star", data={"article_iri": ARTICLE_IRI}
        )
        assert "rss-error" in resp.text
        assert "Failed to toggle star" in resp.text

    def test_patch_error_returns_error_fragment(self, client, mock_ctx):
        """object.patch failure → error fragment."""
        mock_ctx.graph.query = AsyncMock(
            return_value={"results": {"bindings": [{"val": {"value": "false"}}]}}
        )
        mock_ctx.commands.execute = AsyncMock(side_effect=Exception("patch failed"))
        resp = client.post(
            "/_fragments/toggle-star", data={"article_iri": ARTICLE_IRI}
        )
        assert "rss-error" in resp.text
        assert "Failed to update star" in resp.text


# ═══════════════════════════════════════════════════
# toggle-read tests
# ═══════════════════════════════════════════════════


class TestToggleRead:
    """Tests for /_fragments/toggle-read POST handler."""

    def test_missing_article_iri(self, client):
        """No article_iri → 400."""
        resp = client.post("/_fragments/toggle-read", data={})
        assert resp.status_code == 400

    def test_mark_read_on_open(self, client, mock_ctx):
        """Default (no toggle param) → sets isRead=True."""
        resp = client.post(
            "/_fragments/toggle-read", data={"article_iri": ARTICLE_IRI}
        )
        assert resp.status_code == 200
        assert resp.text == ""
        args = mock_ctx.commands.execute.call_args
        assert args[0][1]["properties"][f"{RSS_NS}isRead"] is True

    def test_hx_trigger_on_success(self, client, mock_ctx):
        """Emits HX-Trigger: articleStateChanged."""
        resp = client.post(
            "/_fragments/toggle-read", data={"article_iri": ARTICLE_IRI}
        )
        assert resp.headers.get("HX-Trigger") == "articleStateChanged"

    def test_toggle_mode_flips_read_to_unread(self, client, mock_ctx):
        """toggle=true + currently read → sets isRead=False."""
        mock_ctx.graph.query = AsyncMock(
            return_value={"results": {"bindings": [{"val": {"value": "true"}}]}}
        )
        resp = client.post(
            "/_fragments/toggle-read",
            data={"article_iri": ARTICLE_IRI, "toggle": "true"},
        )
        assert resp.status_code == 200
        args = mock_ctx.commands.execute.call_args
        assert args[0][1]["properties"][f"{RSS_NS}isRead"] is False

    def test_toggle_mode_flips_unread_to_read(self, client, mock_ctx):
        """toggle=true + currently unread → sets isRead=True."""
        mock_ctx.graph.query = AsyncMock(
            return_value={"results": {"bindings": [{"val": {"value": "false"}}]}}
        )
        resp = client.post(
            "/_fragments/toggle-read",
            data={"article_iri": ARTICLE_IRI, "toggle": "true"},
        )
        args = mock_ctx.commands.execute.call_args
        assert args[0][1]["properties"][f"{RSS_NS}isRead"] is True

    def test_patch_error_returns_500(self, client, mock_ctx):
        """object.patch failure → 500 empty body."""
        mock_ctx.commands.execute = AsyncMock(side_effect=Exception("db error"))
        resp = client.post(
            "/_fragments/toggle-read", data={"article_iri": ARTICLE_IRI}
        )
        assert resp.status_code == 500


# ═══════════════════════════════════════════════════
# mark-all-read tests
# ═══════════════════════════════════════════════════


class TestMarkAllRead:
    """Tests for /_fragments/mark-all-read POST handler."""

    def test_no_unread_articles(self, client, mock_ctx):
        """No unread articles found → empty patch, returns sidebar."""
        mock_ctx.graph.query = AsyncMock(
            side_effect=[
                _empty_sparql(),  # unread articles query
                _make_sidebar_bindings([]),  # sidebar refresh
            ]
        )
        resp = client.post("/_fragments/mark-all-read", data={})
        assert resp.status_code == 200
        # No patches called
        mock_ctx.commands.execute.assert_not_called()

    def test_marks_all_unread(self, client, mock_ctx):
        """Finds unread articles and patches each to isRead=True."""
        unread_bindings = {
            "results": {
                "bindings": [
                    {"article": {"value": "urn:art1"}},
                    {"article": {"value": "urn:art2"}},
                    {"article": {"value": "urn:art3"}},
                ]
            }
        }
        mock_ctx.graph.query = AsyncMock(
            side_effect=[unread_bindings, _make_sidebar_bindings([])]
        )
        resp = client.post("/_fragments/mark-all-read", data={})
        assert resp.status_code == 200
        assert mock_ctx.commands.execute.call_count == 3

    def test_scoped_to_feed(self, client, mock_ctx):
        """With feed_iri, SPARQL query includes feed filter."""
        mock_ctx.graph.query = AsyncMock(
            side_effect=[_empty_sparql(), _make_sidebar_bindings([])]
        )
        resp = client.post(
            "/_fragments/mark-all-read", data={"feed_iri": FEED_IRI}
        )
        assert resp.status_code == 200
        # Verify query used feed filter
        query_call = mock_ctx.graph.query.call_args_list[0]
        assert FEED_IRI in query_call[0][0]

    def test_hx_trigger_header(self, client, mock_ctx):
        """Returns HX-Trigger: articleStateChanged."""
        mock_ctx.graph.query = AsyncMock(
            side_effect=[_empty_sparql(), _make_sidebar_bindings([])]
        )
        resp = client.post("/_fragments/mark-all-read", data={})
        assert resp.headers.get("HX-Trigger") == "articleStateChanged"

    def test_sparql_error_returns_error_fragment(self, client, mock_ctx):
        """SPARQL failure → error fragment."""
        mock_ctx.graph.query = AsyncMock(side_effect=Exception("timeout"))
        resp = client.post("/_fragments/mark-all-read", data={})
        assert "rss-error" in resp.text

    def test_partial_patch_failure_continues(self, client, mock_ctx):
        """Individual patch failure → continues best-effort."""
        unread_bindings = {
            "results": {
                "bindings": [
                    {"article": {"value": "urn:art1"}},
                    {"article": {"value": "urn:art2"}},
                ]
            }
        }
        mock_ctx.graph.query = AsyncMock(
            side_effect=[unread_bindings, _make_sidebar_bindings([])]
        )
        # First patch succeeds, second fails
        mock_ctx.commands.execute = AsyncMock(
            side_effect=[None, Exception("patch failed")]
        )
        resp = client.post("/_fragments/mark-all-read", data={})
        assert resp.status_code == 200  # best-effort, still returns sidebar


# ═══════════════════════════════════════════════════
# unsubscribe tests
# ═══════════════════════════════════════════════════


class TestUnsubscribe:
    """Tests for /_fragments/unsubscribe POST handler."""

    def test_missing_feed_iri(self, client):
        """No feed_iri → 400 error."""
        resp = client.post("/_fragments/unsubscribe", data={})
        assert resp.status_code == 400
        assert "Missing feed_iri" in resp.text

    def test_successful_unsubscribe(self, client, mock_ctx):
        """Calls unsubscribe and returns updated sidebar."""
        mock_ctx.graph.query = AsyncMock(return_value=_make_sidebar_bindings([]))

        with patch("rss_reader_ui_mod.unsubscribe", new_callable=AsyncMock) as mock_unsub:
            mock_unsub.return_value = {"status": "unsubscribed", "iri": FEED_IRI}
            resp = client.post(
                "/_fragments/unsubscribe", data={"feed_iri": FEED_IRI}
            )
            assert resp.status_code == 200
            mock_unsub.assert_called_once_with(mock_ctx, FEED_IRI)

    def test_hx_trigger_feedsChanged(self, client, mock_ctx):
        """Returns HX-Trigger: feedsChanged header."""
        mock_ctx.graph.query = AsyncMock(return_value=_make_sidebar_bindings([]))

        with patch("rss_reader_ui_mod.unsubscribe", new_callable=AsyncMock) as mock_unsub:
            mock_unsub.return_value = {"status": "unsubscribed", "iri": FEED_IRI}
            resp = client.post(
                "/_fragments/unsubscribe", data={"feed_iri": FEED_IRI}
            )
            assert resp.headers.get("HX-Trigger") == "feedsChanged"

    def test_unsubscribe_error(self, client, mock_ctx):
        """unsubscribe() raises → error fragment."""
        with patch("rss_reader_ui_mod.unsubscribe", new_callable=AsyncMock) as mock_unsub:
            mock_unsub.side_effect = Exception("not found")
            resp = client.post(
                "/_fragments/unsubscribe", data={"feed_iri": FEED_IRI}
            )
            assert "rss-error" in resp.text
            assert "Failed to unsubscribe" in resp.text


# ═══════════════════════════════════════════════════
# Workspace views (template content verification)
# ═══════════════════════════════════════════════════


class TestWorkspaceViews:
    """Verify unread-view.html and starred-view.html use correct filters."""

    def test_unread_view_contains_filter(self):
        """unread-view.html loads articles with filter=unread."""
        template = Path(_app_path).parent / "frontend" / "templates" / "unread-view.html"
        content = template.read_text()
        assert "filter=unread" in content
        assert "hx-get" in content
        assert "rss-unread-view" in content

    def test_starred_view_contains_filter(self):
        """starred-view.html loads articles with filter=starred."""
        template = Path(_app_path).parent / "frontend" / "templates" / "starred-view.html"
        content = template.read_text()
        assert "filter=starred" in content
        assert "hx-get" in content
        assert "rss-starred-view" in content

    def test_star_button_template_exists(self):
        """star-button.html template exists with inline SVG."""
        template = Path(_app_path).parent / "frontend" / "templates" / "star-button.html"
        content = template.read_text()
        assert "rss-star-btn" in content
        assert "svg" in content.lower()
        assert "toggle-star" in content

    def test_reading_pane_template_exists(self):
        """article-reading-pane.html exists with expected structure."""
        template = Path(_app_path).parent / "frontend" / "templates" / "article-reading-pane.html"
        content = template.read_text()
        assert "md-source-" in content
        assert "md-target-" in content
        assert "toggle-read" in content
        assert "star-button.html" in content


# ═══════════════════════════════════════════════════
# Related articles (right pane) tests — S04
# ═══════════════════════════════════════════════════


def _make_related_article_bindings(articles=None):
    """Build SPARQL result bindings for related-articles query."""
    if articles is None:
        articles = []
    bindings = []
    for a in articles:
        b = {}
        b["article"] = {"value": a.get("iri", "")}
        if "title" in a:
            b["title"] = {"value": a["title"]}
        if "created" in a:
            b["created"] = {"value": a["created"]}
        if "feed_title" in a:
            b["feedTitle"] = {"value": a["feed_title"]}
        bindings.append(b)
    return {"results": {"bindings": bindings}}


class TestRelatedArticles:
    """Tests for /_fragments/related-articles GET handler."""

    def test_empty_iri_returns_empty_state(self, client):
        """No iri param → empty-state HTML."""
        resp = client.get("/_fragments/related-articles")
        assert resp.status_code == 200
        assert "rss-empty-state" in resp.text
        assert "No related articles" in resp.text

    def test_blank_iri_returns_empty_state(self, client):
        """Blank iri param → empty-state HTML."""
        resp = client.get("/_fragments/related-articles?iri=")
        assert resp.status_code == 200
        assert "rss-empty-state" in resp.text

    def test_queries_by_iri_with_union_pattern(self, client, mock_ctx):
        """SPARQL query uses UNION for same feedSource OR shared tags."""
        mock_ctx.graph.query = AsyncMock(return_value=_empty_sparql())
        resp = client.get(f"/_fragments/related-articles?iri={ARTICLE_IRI}")
        assert resp.status_code == 200

        # Inspect the SPARQL query
        query = mock_ctx.graph.query.call_args[0][0]
        assert "UNION" in query
        assert f"{RSS_NS}feedSource" in query
        assert BPKM_TAGS in query
        assert ARTICLE_IRI in query

    def test_excludes_self_from_results(self, client, mock_ctx):
        """SPARQL query contains FILTER to exclude the focused IRI."""
        mock_ctx.graph.query = AsyncMock(return_value=_empty_sparql())
        resp = client.get(f"/_fragments/related-articles?iri={ARTICLE_IRI}")
        assert resp.status_code == 200

        query = mock_ctx.graph.query.call_args[0][0]
        assert f"FILTER(?article != <{ARTICLE_IRI}>)" in query

    def test_passes_articles_to_template(self, client, mock_ctx):
        """Articles from bindings are passed to related-articles.html template."""
        related = [
            {"iri": "urn:art:1", "title": "Related Article 1", "created": "2026-03-15T10:00:00+00:00", "feed_title": "Tech Feed"},
            {"iri": "urn:art:2", "title": "Related Article 2"},
        ]
        mock_ctx.graph.query = AsyncMock(
            return_value=_make_related_article_bindings(related)
        )
        resp = client.get(f"/_fragments/related-articles?iri={ARTICLE_IRI}")
        assert resp.status_code == 200
        assert "related-articles.html" in resp.text

    def test_no_results_template_receives_empty_list(self, client, mock_ctx):
        """Empty SPARQL results → template receives empty articles list."""
        mock_ctx.graph.query = AsyncMock(return_value=_empty_sparql())
        resp = client.get(f"/_fragments/related-articles?iri={ARTICLE_IRI}")
        assert resp.status_code == 200
        assert "related-articles.html" in resp.text

    def test_sparql_error_returns_error_fragment(self, client, mock_ctx):
        """SPARQL failure → rss-error fragment."""
        mock_ctx.graph.query = AsyncMock(side_effect=Exception("timeout"))
        resp = client.get(f"/_fragments/related-articles?iri={ARTICLE_IRI}")
        assert resp.status_code == 200
        assert "rss-error" in resp.text
        assert "Failed to load related articles" in resp.text


# ═══════════════════════════════════════════════════
# Article read renderer (object browser) tests — S04
# ═══════════════════════════════════════════════════


class TestArticleReadRenderer:
    """Tests for /_fragments/article-read-renderer GET handler."""

    def test_no_iri_returns_empty_state(self, client):
        """Missing iri param → empty-state placeholder."""
        resp = client.get("/_fragments/article-read-renderer")
        assert resp.status_code == 200
        assert "rss-reading-pane-empty" in resp.text
        assert "No article specified" in resp.text

    def test_blank_iri_returns_empty_state(self, client):
        """Blank iri param → empty-state placeholder."""
        resp = client.get("/_fragments/article-read-renderer?iri=")
        assert resp.status_code == 200
        assert "rss-reading-pane-empty" in resp.text

    def test_queries_article_by_iri(self, client, mock_ctx):
        """SPARQL query fetches article properties for the given IRI."""
        mock_ctx.graph.query = AsyncMock(return_value=_empty_sparql())
        resp = client.get(f"/_fragments/article-read-renderer?iri={ARTICLE_IRI}")
        assert resp.status_code == 200

        query = mock_ctx.graph.query.call_args[0][0]
        assert ARTICLE_IRI in query
        assert ARTICLE_TYPE in query

    def test_article_not_found(self, client, mock_ctx):
        """Empty SPARQL bindings → 'Article not found' message."""
        mock_ctx.graph.query = AsyncMock(return_value=_empty_sparql())
        resp = client.get(f"/_fragments/article-read-renderer?iri={ARTICLE_IRI}")
        assert resp.status_code == 200
        assert "Article not found" in resp.text

    def test_renders_article_with_correct_template(self, client, mock_ctx):
        """Renders article-read-renderer.html with article data."""
        mock_ctx.graph.query = AsyncMock(
            return_value=_make_article_bindings(body="# Test Body", is_starred="true")
        )
        resp = client.get(f"/_fragments/article-read-renderer?iri={ARTICLE_IRI}")
        assert resp.status_code == 200
        assert "article-read-renderer.html" in resp.text

    def test_passes_article_body_and_md_id_to_template(self, client, mock_ctx):
        """Template args include article dict, body content, and md_id."""
        mock_ctx.graph.query = AsyncMock(
            return_value=_make_article_bindings(body="# Hello World")
        )
        resp = client.get(f"/_fragments/article-read-renderer?iri={ARTICLE_IRI}")
        assert resp.status_code == 200
        assert "# Hello World" in resp.text
        assert "md-id" in resp.text

    def test_includes_star_state(self, client, mock_ctx):
        """Article dict contains is_starred field (True when isStarred='true')."""
        mock_ctx.graph.query = AsyncMock(
            return_value=_make_article_bindings(is_starred="true")
        )
        resp = client.get(f"/_fragments/article-read-renderer?iri={ARTICLE_IRI}")
        assert resp.status_code == 200
        assert 'data-starred="true"' in resp.text.lower()

    def test_sparql_error_returns_error_fragment(self, client, mock_ctx):
        """SPARQL failure → rss-error fragment."""
        mock_ctx.graph.query = AsyncMock(side_effect=Exception("db unreachable"))
        resp = client.get(f"/_fragments/article-read-renderer?iri={ARTICLE_IRI}")
        assert resp.status_code == 200
        assert "rss-error" in resp.text
        assert "Failed to load article" in resp.text

    def test_falls_back_to_description_when_no_body(self, client, mock_ctx):
        """No body → falls back to description field."""
        mock_ctx.graph.query = AsyncMock(
            return_value=_make_article_bindings(body="", description="A short desc")
        )
        resp = client.get(f"/_fragments/article-read-renderer?iri={ARTICLE_IRI}")
        assert resp.status_code == 200
        assert "A short desc" in resp.text


# ═══════════════════════════════════════════════════
# Mark-all-read context detection tests — S04
# ═══════════════════════════════════════════════════


class TestMarkAllReadContext:
    """Tests for mark-all-read command palette vs reader UI context branching."""

    def test_command_palette_context_returns_success_message(self, client, mock_ctx):
        """HX-Target: #modal-container → success message, not sidebar HTML."""
        unread = {
            "results": {
                "bindings": [
                    {"article": {"value": "urn:art1"}},
                    {"article": {"value": "urn:art2"}},
                ]
            }
        }
        mock_ctx.graph.query = AsyncMock(return_value=unread)
        resp = client.post(
            "/_fragments/mark-all-read",
            data={},
            headers={"HX-Target": "#modal-container"},
        )
        assert resp.status_code == 200
        assert "rss-success" in resp.text
        assert "Marked 2 articles as read" in resp.text
        # Should NOT contain sidebar template
        assert "feed-sidebar.html" not in resp.text

    def test_command_palette_context_triggers_both_events(self, client, mock_ctx):
        """Command palette response has HX-Trigger with both articleStateChanged and feedsChanged."""
        mock_ctx.graph.query = AsyncMock(return_value=_empty_sparql())
        resp = client.post(
            "/_fragments/mark-all-read",
            data={},
            headers={"HX-Target": "#modal-container"},
        )
        assert resp.status_code == 200
        trigger = resp.headers.get("HX-Trigger", "")
        assert "articleStateChanged" in trigger
        assert "feedsChanged" in trigger

    def test_reader_context_returns_sidebar(self, client, mock_ctx):
        """No HX-Target → returns feed sidebar HTML (not success message)."""
        mock_ctx.graph.query = AsyncMock(
            side_effect=[_empty_sparql(), _make_sidebar_bindings([])]
        )
        resp = client.post("/_fragments/mark-all-read", data={})
        assert resp.status_code == 200
        # Reader context returns sidebar template, not rss-success
        assert "rss-success" not in resp.text
        trigger = resp.headers.get("HX-Trigger", "")
        assert "articleStateChanged" in trigger
        # Reader context does NOT emit feedsChanged
        assert "feedsChanged" not in trigger
