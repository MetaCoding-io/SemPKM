"""Tests for claim-to-graph matching endpoint and helpers.

Covers:
- _compute_indicator: corroborates, contradicts, contested, non-claim type, no confidence
- POST /api/ai/match-claims: success, caps at 5, empty claims, no FTS results,
  research model not installed, auth required, search service error
- _find_research_gaps: with matches, no overlap
"""

import hashlib
import secrets
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.ai import (
    _RES_CLAIM,
    _RES_EVIDENCE,
    _RES_RESEARCH_QUESTION,
    _compute_indicator,
    _extract_keywords,
    _find_research_gaps,
    ai_router,
    ClaimInput,
    MatchClaimsRequest,
    MatchClaimsResponse,
)
from app.auth.models import ApiToken, User
from app.auth.service import AuthService
from app.db.base import Base
from app.services.search import SearchResult


# ---------------------------------------------------------------------------
# Fixtures (same pattern as test_claim_detection.py)
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


def _build_match_app(db_session_factory, search_service=None, triplestore=None, label_service=None) -> FastAPI:
    """Build a minimal FastAPI app with the AI router, auth, and mocked services."""
    from app.db.session import get_db_session

    app = FastAPI()
    app.state.auth_service = AuthService(db_session_factory)

    # Mock services on app.state
    app.state.search_service = search_service or MagicMock()
    app.state.triplestore_client = triplestore or AsyncMock()
    app.state.label_service = label_service or AsyncMock()

    app.include_router(ai_router)

    async def _test_db_session():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _test_db_session
    return app


# ---------------------------------------------------------------------------
# Helper: mock FTS results
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


def _make_confidence_sparql_response(iri_conf_pairs: list[tuple[str, str]]) -> dict:
    """Build a triplestore SPARQL result for confidence resolution."""
    return {
        "results": {
            "bindings": [
                {"s": {"value": iri}, "confidence": {"value": conf}}
                for iri, conf in iri_conf_pairs
            ]
        }
    }


def _make_rq_sparql_response(rqs: list[dict]) -> dict:
    """Build a triplestore SPARQL result for ResearchQuestion queries."""
    bindings = []
    for rq in rqs:
        binding: dict = {"rq": {"value": rq["iri"]}}
        if "title" in rq:
            binding["title"] = {"value": rq["title"]}
        if "description" in rq:
            binding["description"] = {"value": rq["description"]}
        if "status" in rq:
            binding["status"] = {"value": rq["status"]}
        bindings.append(binding)
    return {"results": {"bindings": bindings}}


def _make_count_response(count: int) -> dict:
    """Build SPARQL COUNT response."""
    return {"results": {"bindings": [{"count": {"value": str(count)}}]}}


# ---------------------------------------------------------------------------
# _compute_indicator unit tests
# ---------------------------------------------------------------------------


class TestComputeIndicatorCorroborates:
    """Both established → 'corroborates'."""

    def test_both_established(self):
        assert _compute_indicator("established", "established", _RES_CLAIM) == "corroborates"

    def test_both_supported(self):
        assert _compute_indicator("supported", "supported", _RES_CLAIM) == "corroborates"

    def test_likely_established(self):
        assert _compute_indicator("likely", "established", _RES_CLAIM) == "corroborates"


class TestComputeIndicatorContradicts:
    """Established vs speculative → 'contradicts'."""

    def test_established_vs_speculative(self):
        assert _compute_indicator("speculative", "established", _RES_CLAIM) == "contradicts"

    def test_established_vs_possible(self):
        assert _compute_indicator("possible", "supported", _RES_CLAIM) == "contradicts"

    def test_speculative_vs_established(self):
        """Reverse direction: low existing vs high detected also contradicts."""
        assert _compute_indicator("established", "speculative", _RES_CLAIM) == "contradicts"


class TestComputeIndicatorContested:
    """Existing contested → 'contested'."""

    def test_contested(self):
        assert _compute_indicator("established", "contested", _RES_CLAIM) == "contested"

    def test_contested_any_detected(self):
        assert _compute_indicator("speculative", "contested", _RES_CLAIM) == "contested"


class TestComputeIndicatorNonClaimType:
    """Evidence type → 'related'."""

    def test_evidence_type(self):
        assert _compute_indicator("established", "established", _RES_EVIDENCE) == "related"

    def test_unknown_type(self):
        assert _compute_indicator("established", "established", "urn:other:Type") == "related"

    def test_none_type(self):
        assert _compute_indicator("established", "established", None) == "related"


class TestComputeIndicatorNoConfidence:
    """Missing confidence → 'related'."""

    def test_no_confidence(self):
        assert _compute_indicator("established", None, _RES_CLAIM) == "related"

    def test_empty_confidence(self):
        assert _compute_indicator("established", "", _RES_CLAIM) == "related"


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


class TestMatchClaimsSuccess:
    """Mock search service + triplestore returning matches → correct response."""

    async def test_match_claims_success(
        self, db_session_factory, test_user, valid_api_token
    ):
        mock_search = AsyncMock()
        mock_search.search.return_value = _make_search_results(3)

        mock_triplestore = AsyncMock()
        # First call: type resolution → obj-0 is a Claim, obj-1 is Evidence
        # Second call: confidence resolution → obj-0 has "established"
        # Third+ calls: research gap queries → no results
        mock_triplestore.query.side_effect = [
            _make_type_sparql_response([
                ("urn:test:obj-0", _RES_CLAIM),
                ("urn:test:obj-1", _RES_EVIDENCE),
            ]),
            _make_confidence_sparql_response([
                ("urn:test:obj-0", "established"),
            ]),
            # Research gap RQ query → empty
            {"results": {"bindings": []}},
        ]

        mock_label_service = AsyncMock()
        mock_label_service.resolve_batch.return_value = {
            "urn:test:obj-0": "First Claim",
            "urn:test:obj-1": "Some Evidence",
            "urn:test:obj-2": "Other Object",
            _RES_CLAIM: "Claim",
            _RES_EVIDENCE: "Evidence",
        }

        app = _build_match_app(
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
                json={"claims": [{"text": "Earth is round", "confidence": "established", "type": "factual"}]},
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["matches"]) == 1
        match = data["matches"][0]
        assert match["claim_text"] == "Earth is round"
        assert len(match["matched_objects"]) == 3
        # First object is a Claim with corroborates indicator (both established)
        obj0 = match["matched_objects"][0]
        assert obj0["iri"] == "urn:test:obj-0"
        assert obj0["indicator"] == "corroborates"
        assert obj0["confidence"] == "established"
        assert obj0["match_type"] == "fts"
        # Second is Evidence → related
        assert match["matched_objects"][1]["indicator"] == "related"


class TestMatchClaimsCapsAtFive:
    """20 FTS results → only 5 per claim in response."""

    async def test_match_claims_caps_at_five(
        self, db_session_factory, test_user, valid_api_token
    ):
        mock_search = AsyncMock()
        mock_search.search.return_value = _make_search_results(20)

        mock_triplestore = AsyncMock()
        mock_triplestore.query.return_value = {"results": {"bindings": []}}

        mock_label_service = AsyncMock()
        mock_label_service.resolve_batch.return_value = {}

        app = _build_match_app(
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
                json={"claims": [{"text": "Some claim text"}]},
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["matches"][0]["matched_objects"]) == 5


class TestMatchClaimsEmptyClaims:
    """Empty claims list → 400."""

    async def test_match_claims_empty_claims(
        self, db_session_factory, test_user, valid_api_token
    ):
        app = _build_match_app(db_session_factory)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ai/match-claims",
                json={"claims": []},
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )

        assert resp.status_code == 400
        assert "required" in resp.json()["error"].lower() or "Claims" in resp.json()["error"]


class TestMatchClaimsNoFTSResults:
    """Search returns empty → empty matches."""

    async def test_match_claims_no_fts_results(
        self, db_session_factory, test_user, valid_api_token
    ):
        mock_search = AsyncMock()
        mock_search.search.return_value = []

        mock_triplestore = AsyncMock()
        mock_triplestore.query.return_value = {"results": {"bindings": []}}

        app = _build_match_app(
            db_session_factory,
            search_service=mock_search,
            triplestore=mock_triplestore,
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ai/match-claims",
                json={"claims": [{"text": "Unknown topic"}]},
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["matches"]) == 1
        assert data["matches"][0]["matched_objects"] == []


class TestMatchClaimsResearchModelNotInstalled:
    """No RQ type in graph → empty research_gaps, no error."""

    async def test_research_model_not_installed(
        self, db_session_factory, test_user, valid_api_token
    ):
        mock_search = AsyncMock()
        mock_search.search.return_value = _make_search_results(2)

        mock_triplestore = AsyncMock()
        # All SPARQL queries return empty bindings (no research types)
        mock_triplestore.query.return_value = {"results": {"bindings": []}}

        mock_label_service = AsyncMock()
        mock_label_service.resolve_batch.return_value = {}

        app = _build_match_app(
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
                json={"claims": [{"text": "Some scientific claim"}]},
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        # Matches should still exist (from FTS)
        assert len(data["matches"]) == 1
        assert len(data["matches"][0]["matched_objects"]) == 2
        # No research gaps since no RQ types found
        assert data["research_gaps"] == []


class TestMatchClaimsRequiresAuth:
    """No auth → 401."""

    async def test_match_claims_requires_auth(self, db_session_factory):
        app = _build_match_app(db_session_factory)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/ai/match-claims",
                json={"claims": [{"text": "Some text"}]},
            )

        assert resp.status_code == 401


class TestMatchClaimsSearchServiceError:
    """Search throws → graceful degradation, partial results."""

    async def test_search_service_error(
        self, db_session_factory, test_user, valid_api_token
    ):
        mock_search = AsyncMock()
        # First claim search succeeds, second throws
        mock_search.search.side_effect = [
            _make_search_results(2),
            Exception("Connection refused"),
        ]

        mock_triplestore = AsyncMock()
        mock_triplestore.query.return_value = {"results": {"bindings": []}}

        mock_label_service = AsyncMock()
        mock_label_service.resolve_batch.return_value = {}

        app = _build_match_app(
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
                json={
                    "claims": [
                        {"text": "First claim"},
                        {"text": "Second claim"},
                    ]
                },
                headers={"Authorization": f"Bearer {valid_api_token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        # Two matches returned — first has objects, second is empty (error degraded)
        assert len(data["matches"]) == 2
        assert len(data["matches"][0]["matched_objects"]) == 2
        assert data["matches"][1]["matched_objects"] == []


# ---------------------------------------------------------------------------
# _find_research_gaps tests
# ---------------------------------------------------------------------------


class TestFindResearchGapsWithMatches:
    """Mock RQ objects + claim overlap → gaps returned."""

    async def test_find_research_gaps_with_matches(self):
        mock_triplestore = AsyncMock()
        # First call: RQ query returns one open question about "machine learning algorithms"
        # Second call: evidence count for that RQ → 0 (gap!)
        mock_triplestore.query.side_effect = [
            _make_rq_sparql_response([{
                "iri": "urn:test:rq-1",
                "title": "How do machine learning algorithms handle bias?",
                "description": "Investigating bias in machine learning training data",
                "status": "open",
            }]),
            _make_count_response(0),  # no evidence → it's a gap
        ]

        mock_label_service = AsyncMock()
        mock_label_service.resolve_batch.return_value = {
            "urn:test:rq-1": "ML Bias Question",
        }

        # Claim texts with keyword overlap: "machine" and "learning" overlap
        claim_texts = ["Machine learning models exhibit significant bias in predictions"]

        gaps = await _find_research_gaps(mock_triplestore, mock_label_service, claim_texts)

        assert len(gaps) == 1
        assert gaps[0].iri == "urn:test:rq-1"
        assert gaps[0].label == "ML Bias Question"
        assert gaps[0].status == "open"


class TestFindResearchGapsNoOverlap:
    """No keyword overlap → empty gaps."""

    async def test_find_research_gaps_no_overlap(self):
        mock_triplestore = AsyncMock()
        # RQ query returns a question about quantum physics
        mock_triplestore.query.return_value = _make_rq_sparql_response([{
            "iri": "urn:test:rq-2",
            "title": "What are the implications of quantum entanglement?",
            "description": "Exploring quantum physics phenomena",
            "status": "open",
        }])

        mock_label_service = AsyncMock()

        # Claim texts about cooking — no overlap with quantum physics
        claim_texts = ["Adding salt improves the flavor of pasta dishes"]

        gaps = await _find_research_gaps(mock_triplestore, mock_label_service, claim_texts)

        assert gaps == []
