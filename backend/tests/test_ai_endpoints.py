"""Integration tests for all AI endpoints.

Covers:
- Auth (401) on all 6 endpoints
- Graceful degradation when LLM not configured
- suggest-relationships: success, empty input, URL match, deduplication
- summarize: success, empty content, graph context in prompt
- well-known discovery includes AI capabilities
"""

import hashlib
import json
import secrets
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.ai import ai_router
from app.api.router import well_known_router
from app.auth.models import ApiToken, User
from app.auth.service import AuthService
from app.db.base import Base
from app.services.search import SearchResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_engine():
    """Create an in-memory SQLite engine with all tables."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest.fixture
async def db_session(db_session_factory):
    async with db_session_factory() as session:
        yield session


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(id=uuid.uuid4(), email="test@example.com", role="owner")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def valid_api_token(db_session: AsyncSession, test_user: User) -> str:
    plaintext = secrets.token_hex(32)
    token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    api_token = ApiToken(user_id=test_user.id, name="test-token", token_hash=token_hash)
    db_session.add(api_token)
    await db_session.commit()
    return plaintext


# ---------------------------------------------------------------------------
# App builders
# ---------------------------------------------------------------------------


def _build_ai_app(db_session_factory, search_service=None, triplestore=None, label_service=None) -> FastAPI:
    """Build a minimal FastAPI app with the AI router, auth, and mocked services."""
    from app.db.session import get_db_session

    app = FastAPI()
    app.state.auth_service = AuthService(db_session_factory)

    app.state.search_service = search_service or MagicMock()
    app.state.triplestore_client = triplestore or AsyncMock()
    app.state.label_service = label_service or AsyncMock()

    app.include_router(ai_router)

    async def _test_db_session():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _test_db_session
    return app


def _build_well_known_app(db_session_factory) -> FastAPI:
    """Build a minimal FastAPI app with the well-known router."""
    from app.db.session import get_db_session

    app = FastAPI()
    app.state.auth_service = AuthService(db_session_factory)
    app.include_router(well_known_router)

    async def _test_db_session():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _test_db_session
    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_search_results(count: int, prefix: str = "urn:test:") -> list[SearchResult]:
    """Generate ``count`` SearchResult objects for testing."""
    return [
        SearchResult(
            iri=f"{prefix}obj-{i}",
            type=None,
            label=f"Object {i}",
            snippet=f"Snippet for object {i}",
            score=1.0 - (i * 0.04),
        )
        for i in range(count)
    ]


def _make_type_sparql_response(iri_type_pairs: list[tuple[str, str]]) -> dict:
    """Build a triplestore SPARQL result for type resolution."""
    return {
        "results": {
            "bindings": [
                {"s": {"value": iri}, "type": {"value": type_iri}}
                for iri, type_iri in iri_type_pairs
            ]
        }
    }


def _make_url_sparql_response(iris: list[str]) -> dict:
    """Build a triplestore SPARQL result for URL matching."""
    return {
        "results": {
            "bindings": [{"s": {"value": iri}} for iri in iris]
        }
    }


def _mock_llm_response(content: str) -> dict:
    """Build a mock OpenAI-compatible chat completions response."""
    return {
        "choices": [
            {
                "message": {
                    "content": content,
                },
                "index": 0,
                "finish_reason": "stop",
            }
        ],
        "model": "gpt-4o",
    }


# ---------------------------------------------------------------------------
# Auth tests — all 6 endpoints must return 401 without auth
# ---------------------------------------------------------------------------


class TestAuthRequired:
    """All AI endpoints require authentication."""

    async def test_llm_stream_requires_auth(self, db_session_factory):
        app = _build_ai_app(db_session_factory)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/llm/stream", json={"messages": []})
        assert resp.status_code == 401

    async def test_llm_status_requires_auth(self, db_session_factory):
        app = _build_ai_app(db_session_factory)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/llm/status")
        assert resp.status_code == 401

    async def test_detect_claims_requires_auth(self, db_session_factory):
        app = _build_ai_app(db_session_factory)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ai/detect-claims",
                json={"content": "test"},
            )
        assert resp.status_code == 401

    async def test_match_claims_requires_auth(self, db_session_factory):
        app = _build_ai_app(db_session_factory)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ai/match-claims",
                json={"claims": [{"text": "test"}]},
            )
        assert resp.status_code == 401

    async def test_suggest_relationships_requires_auth(self, db_session_factory):
        app = _build_ai_app(db_session_factory)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ai/suggest-relationships",
                json={"url": "http://example.com"},
            )
        assert resp.status_code == 401

    async def test_summarize_requires_auth(self, db_session_factory):
        app = _build_ai_app(db_session_factory)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ai/summarize",
                json={"content": "test"},
            )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Degradation tests — LLM not configured
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """Endpoints degrade gracefully when LLM is not configured."""

    @patch(
        "app.api.ai.LLMConfigService.get_config",
        new_callable=AsyncMock,
        return_value={"api_base_url": "", "default_model": ""},
    )
    async def test_detect_claims_llm_not_configured(
        self, mock_get_config, db_session_factory, test_user, valid_api_token
    ):
        app = _build_ai_app(db_session_factory)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ai/detect-claims",
                json={"content": "Some page text to analyze"},
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )
        assert resp.status_code == 503
        assert "not configured" in resp.json()["error"].lower()

    @patch(
        "app.api.ai.LLMConfigService.get_config",
        new_callable=AsyncMock,
        return_value={"api_base_url": "", "default_model": ""},
    )
    async def test_summarize_llm_not_configured(
        self, mock_get_config, db_session_factory, test_user, valid_api_token
    ):
        app = _build_ai_app(db_session_factory)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ai/summarize",
                json={"content": "Some page text to summarize"},
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )
        assert resp.status_code == 503
        assert "not configured" in resp.json()["error"].lower()

    async def test_match_claims_works_without_llm(
        self, db_session_factory, test_user, valid_api_token
    ):
        """match-claims doesn't need LLM — should work regardless."""
        mock_search = AsyncMock()
        mock_search.search.return_value = _make_search_results(2)

        mock_triplestore = AsyncMock()
        mock_triplestore.query.return_value = {"results": {"bindings": []}}

        mock_label_service = AsyncMock()
        mock_label_service.resolve_batch.return_value = {}

        app = _build_ai_app(
            db_session_factory,
            search_service=mock_search,
            triplestore=mock_triplestore,
            label_service=mock_label_service,
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ai/match-claims",
                json={"claims": [{"text": "Any claim text"}]},
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["matches"]) == 1
        assert len(data["matches"][0]["matched_objects"]) == 2


# ---------------------------------------------------------------------------
# Suggest-relationships tests
# ---------------------------------------------------------------------------


class TestSuggestRelationships:
    """POST /api/ai/suggest-relationships endpoint tests."""

    async def test_suggest_relationships_success(
        self, db_session_factory, test_user, valid_api_token
    ):
        """Mock search + triplestore → suggestions returned."""
        mock_search = AsyncMock()
        mock_search.search.return_value = _make_search_results(3)

        mock_triplestore = AsyncMock()
        # Type resolution → no special types (all generic)
        mock_triplestore.query.return_value = {"results": {"bindings": []}}

        mock_label_service = AsyncMock()
        mock_label_service.resolve_batch.return_value = {
            "urn:test:obj-0": "First Object",
            "urn:test:obj-1": "Second Object",
            "urn:test:obj-2": "Third Object",
        }

        app = _build_ai_app(
            db_session_factory,
            search_service=mock_search,
            triplestore=mock_triplestore,
            label_service=mock_label_service,
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ai/suggest-relationships",
                json={
                    "title": "Machine Learning in Healthcare",
                    "claims": [{"text": "ML can detect cancer early"}],
                },
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["suggestions"]) == 3
        # All should be "link" type since no special types resolved
        for s in data["suggestions"]:
            assert s["type"] == "link"
            assert s["target_iri"].startswith("urn:test:")
            assert s["reason"] == "discusses similar topic"

    async def test_suggest_relationships_empty_input(
        self, db_session_factory, test_user, valid_api_token
    ):
        """No url/title/claims → 400."""
        app = _build_ai_app(db_session_factory)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ai/suggest-relationships",
                json={"url": "", "title": "", "claims": []},
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )
        assert resp.status_code == 400
        assert "required" in resp.json()["error"].lower()

    async def test_suggest_relationships_url_match(
        self, db_session_factory, test_user, valid_api_token
    ):
        """Mock URL match → link suggestion with 'cites same URL' reason."""
        mock_search = AsyncMock()
        mock_search.search.return_value = []  # No FTS results

        mock_triplestore = AsyncMock()
        # URL SPARQL query returns one match
        mock_triplestore.query.return_value = _make_url_sparql_response(
            ["urn:test:page-ref"]
        )

        mock_label_service = AsyncMock()
        mock_label_service.resolve_batch.return_value = {
            "urn:test:page-ref": "Referenced Page",
        }

        app = _build_ai_app(
            db_session_factory,
            search_service=mock_search,
            triplestore=mock_triplestore,
            label_service=mock_label_service,
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ai/suggest-relationships",
                json={"url": "https://example.com/article"},
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["suggestions"]) >= 1
        url_suggestion = data["suggestions"][0]
        assert url_suggestion["type"] == "link"
        assert url_suggestion["target_iri"] == "urn:test:page-ref"
        assert url_suggestion["reason"] == "cites same URL"

    async def test_suggest_relationships_deduplicates(
        self, db_session_factory, test_user, valid_api_token
    ):
        """Same IRI from URL + FTS → single suggestion (first wins)."""
        shared_iri = "urn:test:shared-obj"

        mock_search = AsyncMock()
        mock_search.search.return_value = [
            SearchResult(
                iri=shared_iri,
                type=None,
                label="Shared Object",
                snippet="Found via FTS",
                score=0.9,
            ),
            SearchResult(
                iri="urn:test:fts-only",
                type=None,
                label="FTS Only Object",
                snippet="Only from FTS",
                score=0.8,
            ),
        ]

        mock_triplestore = AsyncMock()
        # First call: URL SPARQL → returns the shared IRI
        # Second call: type resolution for FTS results → empty
        mock_triplestore.query.side_effect = [
            _make_url_sparql_response([shared_iri]),
            {"results": {"bindings": []}},
        ]

        mock_label_service = AsyncMock()
        mock_label_service.resolve_batch.return_value = {
            shared_iri: "Shared Object",
            "urn:test:fts-only": "FTS Only Object",
        }

        app = _build_ai_app(
            db_session_factory,
            search_service=mock_search,
            triplestore=mock_triplestore,
            label_service=mock_label_service,
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ai/suggest-relationships",
                json={
                    "url": "https://example.com/page",
                    "title": "Some topic",
                },
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        suggestions = data["suggestions"]
        # Should have exactly 2: shared (from URL, first) + fts-only (from FTS)
        target_iris = [s["target_iri"] for s in suggestions]
        assert target_iris.count(shared_iri) == 1, "shared IRI should appear exactly once"
        assert "urn:test:fts-only" in target_iris
        # The shared one should be "link" with "cites same URL" (URL match wins)
        shared_suggestion = next(s for s in suggestions if s["target_iri"] == shared_iri)
        assert shared_suggestion["reason"] == "cites same URL"


# ---------------------------------------------------------------------------
# Summarize tests
# ---------------------------------------------------------------------------


class TestSummarize:
    """POST /api/ai/summarize endpoint tests."""

    @patch(
        "app.api.ai.LLMConfigService.get_decrypted_api_key",
        new_callable=AsyncMock,
        return_value="sk-test-key",
    )
    @patch(
        "app.api.ai.LLMConfigService.get_config",
        new_callable=AsyncMock,
        return_value={"api_base_url": "http://llm:8080", "default_model": "gpt-4o"},
    )
    @patch("app.api.ai.httpx.AsyncClient")
    async def test_summarize_success(
        self, mock_httpx_class, mock_get_config, mock_get_key,
        db_session_factory, test_user, valid_api_token,
    ):
        """Mock LLM → summary returned."""
        expected_summary = "This page discusses machine learning in healthcare."
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = _mock_llm_response(expected_summary)

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx_class.return_value = mock_client

        app = _build_ai_app(db_session_factory)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ai/summarize",
                json={"content": "Machine learning is transforming healthcare diagnostics."},
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"] == expected_summary

    @patch("app.api.ai.LLMConfigService")
    async def test_summarize_empty_content(
        self, mock_svc_class, db_session_factory, test_user, valid_api_token
    ):
        """Empty content → 400."""
        app = _build_ai_app(db_session_factory)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ai/summarize",
                json={"content": ""},
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )
        assert resp.status_code == 400
        assert "required" in resp.json()["error"].lower()

    @patch(
        "app.api.ai.LLMConfigService.get_decrypted_api_key",
        new_callable=AsyncMock,
        return_value="sk-test-key",
    )
    @patch(
        "app.api.ai.LLMConfigService.get_config",
        new_callable=AsyncMock,
        return_value={"api_base_url": "http://llm:8080", "default_model": "gpt-4o"},
    )
    @patch("app.api.ai.httpx.AsyncClient")
    async def test_summarize_includes_graph_context(
        self, mock_httpx_class, mock_get_config, mock_get_key,
        db_session_factory, test_user, valid_api_token,
    ):
        """Verify that graph context items appear in the prompt sent to LLM."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = _mock_llm_response("A context-aware summary.")

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx_class.return_value = mock_client

        app = _build_ai_app(db_session_factory)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ai/summarize",
                json={
                    "content": "Page about neural networks.",
                    "graph_context": [
                        {
                            "iri": "urn:test:nn-claim",
                            "label": "Neural Networks for Classification",
                            "type": "Claim",
                            "snippet": "Deep learning approaches",
                        },
                        {
                            "iri": "urn:test:ml-note",
                            "label": "ML Fundamentals",
                            "type": "Note",
                        },
                    ],
                },
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )

        assert resp.status_code == 200

        # Verify the request sent to the LLM included graph context
        call_args = mock_client.post.call_args
        sent_payload = call_args.kwargs.get("json") or call_args[1].get("json")
        system_msg = sent_payload["messages"][0]["content"]

        # Graph context items should appear in the system prompt
        assert "Neural Networks for Classification" in system_msg
        assert "ML Fundamentals" in system_msg
        assert "Claim" in system_msg
        assert "Deep learning approaches" in system_msg


# ---------------------------------------------------------------------------
# Well-known integration test
# ---------------------------------------------------------------------------


class TestWellKnownAICapabilities:
    """GET /.well-known/sempkm includes AI capabilities and endpoints."""

    async def test_well_known_includes_ai_capabilities(
        self, db_session_factory, test_user, valid_api_token
    ):
        app = _build_well_known_app(db_session_factory)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/.well-known/sempkm",
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )

        assert resp.status_code == 200
        data = resp.json()

        # Check capabilities include AI
        assert "ai-insights" in data["capabilities"]

        # Check all 6 AI endpoint paths
        endpoints = data["endpoints"]
        assert endpoints["llm_stream"] == "/api/llm/stream"
        assert endpoints["llm_status"] == "/api/llm/status"
        assert endpoints["detect_claims"] == "/api/ai/detect-claims"
        assert endpoints["match_claims"] == "/api/ai/match-claims"
        assert endpoints["suggest_relationships"] == "/api/ai/suggest-relationships"
        assert endpoints["summarize"] == "/api/ai/summarize"
