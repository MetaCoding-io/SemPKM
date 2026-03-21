"""Tests for claim detection endpoint and helpers.

Covers:
- _parse_claims_response: valid JSON, markdown code block, malformed, missing fields, empty text
- _build_claim_extraction_prompt: content truncation, metadata inclusion
- POST /api/ai/detect-claims: success, LLM not configured, empty content, auth, LLM error
"""

import hashlib
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.ai import (
    _MAX_CONTENT_CHARS,
    _build_claim_extraction_prompt,
    _parse_claims_response,
    ai_router,
)
from app.auth.models import ApiToken, User, UserSession
from app.auth.service import AuthService
from app.db.base import Base


# ---------------------------------------------------------------------------
# Fixtures (same pattern as test_llm_proxy.py)
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


def _build_ai_app(db_session_factory) -> FastAPI:
    """Build a minimal FastAPI app with the AI router and auth service."""
    from app.db.session import get_db_session

    app = FastAPI()
    app.state.auth_service = AuthService(db_session_factory)
    app.include_router(ai_router)

    async def _test_db_session():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _test_db_session
    return app


# ---------------------------------------------------------------------------
# Helper: mock LLM config (configured)
# ---------------------------------------------------------------------------

_MOCK_CONFIG_AVAILABLE = {
    "api_base_url": "https://api.openai.com",
    "api_key_set": True,
    "default_model": "gpt-4o",
}

_MOCK_CONFIG_UNAVAILABLE = {
    "api_base_url": "",
    "api_key_set": False,
    "default_model": "",
}


# ---------------------------------------------------------------------------
# _parse_claims_response tests
# ---------------------------------------------------------------------------


class TestParseClaimsValidJson:
    """Direct JSON string parses correctly."""

    def test_parse_claims_valid_json(self):
        raw = json.dumps({
            "claims": [
                {"text": "The Earth is round", "confidence": "established", "type": "factual"},
                {"text": "Coffee causes cancer", "confidence": "speculative", "type": "causal"},
            ]
        })
        claims, error = _parse_claims_response(raw)
        assert error is None
        assert len(claims) == 2
        assert claims[0]["text"] == "The Earth is round"
        assert claims[0]["confidence"] == "established"
        assert claims[0]["type"] == "factual"
        assert claims[1]["confidence"] == "speculative"
        assert claims[1]["type"] == "causal"


class TestParseClaimsMarkdownCodeBlock:
    """JSON in markdown ```json...``` code block parses correctly."""

    def test_parse_claims_markdown_code_block(self):
        raw = (
            "Here are the claims I found:\n\n"
            "```json\n"
            '{"claims": [{"text": "Water boils at 100C", "confidence": "established", "type": "factual"}]}\n'
            "```\n"
            "\nThose are the results."
        )
        claims, error = _parse_claims_response(raw)
        assert error is None
        assert len(claims) == 1
        assert claims[0]["text"] == "Water boils at 100C"


class TestParseClaimsMalformedJson:
    """Garbage text returns empty list + parse_error."""

    def test_parse_claims_malformed_json(self):
        raw = "This is not JSON at all, just random text."
        claims, error = _parse_claims_response(raw)
        assert claims == []
        assert error is not None
        assert "parse" in error.lower() or "Failed" in error


class TestParseClaimsMissingFields:
    """Claims without required fields are filtered out."""

    def test_parse_claims_missing_fields(self):
        raw = json.dumps({
            "claims": [
                {"text": "Valid claim", "confidence": "likely", "type": "factual"},
                {"confidence": "likely", "type": "factual"},  # missing text
                {"text": "Another", "type": "factual"},  # missing confidence
                {"text": "Third"},  # missing confidence and type
            ]
        })
        claims, error = _parse_claims_response(raw)
        assert error is None
        assert len(claims) == 1
        assert claims[0]["text"] == "Valid claim"


class TestParseClaimsEmptyTextFiltered:
    """Claims with empty text are removed."""

    def test_parse_claims_empty_text_filtered(self):
        raw = json.dumps({
            "claims": [
                {"text": "", "confidence": "likely", "type": "factual"},
                {"text": "  ", "confidence": "likely", "type": "factual"},
                {"text": "Real claim", "confidence": "established", "type": "factual"},
            ]
        })
        claims, error = _parse_claims_response(raw)
        assert error is None
        assert len(claims) == 1
        assert claims[0]["text"] == "Real claim"


# ---------------------------------------------------------------------------
# _build_claim_extraction_prompt tests
# ---------------------------------------------------------------------------


class TestBuildPromptTruncatesLongContent:
    """Content exceeding _MAX_CONTENT_CHARS is truncated in the prompt."""

    def test_build_prompt_truncates_long_content(self):
        long_content = "x" * (_MAX_CONTENT_CHARS + 500)
        messages = _build_claim_extraction_prompt(long_content, "Test", "https://example.com")
        user_msg = messages[1]["content"]
        # Should contain truncation marker
        assert "[...content truncated...]" in user_msg
        # Content in user message should not contain the full input
        assert len(user_msg) < len(long_content)


class TestBuildPromptIncludesMetadata:
    """Title and URL appear in the user message."""

    def test_build_prompt_includes_metadata(self):
        messages = _build_claim_extraction_prompt(
            "Some content", "My Page Title", "https://example.com/page"
        )
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        user_msg = messages[1]["content"]
        assert "My Page Title" in user_msg
        assert "https://example.com/page" in user_msg
        assert "Some content" in user_msg

        # System message should mention JSON format
        sys_msg = messages[0]["content"]
        assert "claims" in sys_msg
        assert "JSON" in sys_msg


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


class TestDetectClaimsEndpointSuccess:
    """Mock LLM returning valid JSON → claims returned."""

    async def test_detect_claims_endpoint_success(
        self, db_session_factory, test_user, valid_api_token
    ):
        app = _build_ai_app(db_session_factory)
        llm_response_body = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "claims": [
                                {
                                    "text": "Python is popular",
                                    "confidence": "established",
                                    "type": "factual",
                                },
                                {
                                    "text": "AI will replace jobs",
                                    "confidence": "speculative",
                                    "type": "predictive",
                                },
                            ]
                        })
                    }
                }
            ]
        }

        mock_http_response = AsyncMock()
        mock_http_response.status_code = 200
        mock_http_response.raise_for_status = lambda: None
        # httpx Response.json() is synchronous — use a regular Mock for it
        from unittest.mock import Mock
        mock_http_response.json = Mock(return_value=llm_response_body)

        with (
            patch(
                "app.api.ai.LLMConfigService.get_config",
                new_callable=AsyncMock,
                return_value=_MOCK_CONFIG_AVAILABLE,
            ),
            patch(
                "app.api.ai.LLMConfigService.get_decrypted_api_key",
                new_callable=AsyncMock,
                return_value="sk-test-key",
            ),
            patch("app.api.ai.httpx.AsyncClient") as MockClient,
        ):
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_http_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/ai/detect-claims",
                    json={"content": "Python is a popular programming language."},
                    headers={"Authorization": f"Bearer {valid_api_token}"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["parse_error"] is None
        assert len(data["claims"]) == 2
        assert data["claims"][0]["text"] == "Python is popular"
        assert data["claims"][0]["confidence"] == "established"
        assert data["claims"][1]["type"] == "predictive"


class TestDetectClaimsEndpointLLMNotConfigured:
    """No LLM config → 503."""

    async def test_detect_claims_endpoint_llm_not_configured(
        self, db_session_factory, test_user, valid_api_token
    ):
        app = _build_ai_app(db_session_factory)

        with patch(
            "app.api.ai.LLMConfigService.get_config",
            new_callable=AsyncMock,
            return_value=_MOCK_CONFIG_UNAVAILABLE,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/ai/detect-claims",
                    json={"content": "Some text"},
                    headers={"Authorization": f"Bearer {valid_api_token}"},
                )

        assert resp.status_code == 503
        assert resp.json()["error"] == "LLM not configured"


class TestDetectClaimsEndpointEmptyContent:
    """Empty content → 400."""

    async def test_detect_claims_endpoint_empty_content(
        self, db_session_factory, test_user, valid_api_token
    ):
        app = _build_ai_app(db_session_factory)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ai/detect-claims",
                json={"content": ""},
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )

        assert resp.status_code == 400
        assert "required" in resp.json()["error"].lower() or "Content" in resp.json()["error"]


class TestDetectClaimsEndpointRequiresAuth:
    """No auth → 401."""

    async def test_detect_claims_endpoint_requires_auth(self, db_session_factory):
        app = _build_ai_app(db_session_factory)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ai/detect-claims",
                json={"content": "Some text"},
            )

        assert resp.status_code == 401


class TestDetectClaimsEndpointLLMError:
    """httpx error → empty claims with parse_error."""

    async def test_detect_claims_endpoint_llm_error(
        self, db_session_factory, test_user, valid_api_token
    ):
        app = _build_ai_app(db_session_factory)

        with (
            patch(
                "app.api.ai.LLMConfigService.get_config",
                new_callable=AsyncMock,
                return_value=_MOCK_CONFIG_AVAILABLE,
            ),
            patch(
                "app.api.ai.LLMConfigService.get_decrypted_api_key",
                new_callable=AsyncMock,
                return_value="sk-test-key",
            ),
            patch("app.api.ai.httpx.AsyncClient") as MockClient,
        ):
            mock_client_instance = AsyncMock()
            mock_client_instance.post.side_effect = httpx.ConnectError("Connection refused")
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/ai/detect-claims",
                    json={"content": "Some text to analyze"},
                    headers={"Authorization": f"Bearer {valid_api_token}"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["claims"] == []
        assert data["parse_error"] is not None
        assert "LLM call failed" in data["parse_error"]
