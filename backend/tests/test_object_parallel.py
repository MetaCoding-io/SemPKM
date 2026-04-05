"""Tests for get_object asyncio.gather parallelization and timing log.

Verifies that the property UNION query and favorites check run concurrently,
and that the handler emits a timing log at INFO level.
"""

import asyncio
import logging
import time

import pytest
from unittest.mock import AsyncMock, MagicMock

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
TEST_IRI = "http://example.org/obj/parallel-test"
TEST_TYPE = "http://example.org/ontology/Note"


def _make_bindings():
    """Minimal UNION query result with one type triple."""
    return {
        "results": {
            "bindings": [
                {
                    "p": {"type": "uri", "value": RDF_TYPE},
                    "o": {"type": "uri", "value": TEST_TYPE},
                    "source": {"type": "literal", "value": "user"},
                },
            ]
        }
    }


class _CallTracker:
    """Async callable that tracks invocation count and introduces a delay."""

    def __init__(self, delay, return_value):
        self.delay = delay
        self.return_value = return_value
        self.call_count = 0

    async def __call__(self, *args, **kwargs):
        self.call_count += 1
        await asyncio.sleep(self.delay)
        return self.return_value


@pytest.fixture
def mock_deps():
    """Build all mock dependencies for get_object."""
    # Triplestore client with 0.15s delay to simulate network round-trip
    client = MagicMock()
    client.query = _CallTracker(0.15, _make_bindings())

    # DB session (favorites) with 0.15s delay to simulate SQLite I/O
    fav_result = MagicMock()
    fav_result.scalar_one_or_none = MagicMock(return_value=None)

    db = MagicMock()
    db.execute = _CallTracker(0.15, fav_result)

    # Label service — instant
    label_svc = AsyncMock()
    label_svc.resolve_batch = AsyncMock(
        side_effect=lambda iris: {iri: iri.split("/")[-1] for iri in iris}
    )

    # Shapes service — instant, no form
    shapes_svc = AsyncMock()
    shapes_svc.get_form_for_type = AsyncMock(return_value=None)

    # Icon service
    icon_svc = MagicMock()
    icon_svc.get_type_icon = MagicMock(return_value=None)

    # Request with templates
    request = MagicMock()
    templates = MagicMock()
    env = MagicMock()
    env.filters = {}
    templates.env = env

    def _capture_template(req, name, ctx):
        resp = MagicMock()
        resp.headers = {}
        return resp

    templates.TemplateResponse = _capture_template
    request.app.state.templates = templates

    user = MagicMock()
    user.id = 42

    return {
        "request": request,
        "client": client,
        "db": db,
        "label_service": label_svc,
        "shapes_service": shapes_svc,
        "icon_svc": icon_svc,
        "user": user,
    }


class TestAsyncGatherParallelization:
    """Verify that property query and favorites check run concurrently."""

    async def test_parallel_faster_than_sequential(self, mock_deps):
        """Total wall-clock time should be less than the sum of individual delays.

        Each mock sleeps 0.15s. Sequential = ~0.30s minimum.
        Parallel = ~0.15s (overlap). We assert < 0.25s to allow slack.
        """
        from app.browser.objects import get_object

        start = time.perf_counter()
        await get_object(
            request=mock_deps["request"],
            object_iri=TEST_IRI,
            mode="read",
            embed=0,
            user=mock_deps["user"],
            shapes_service=mock_deps["shapes_service"],
            label_service=mock_deps["label_service"],
            client=mock_deps["client"],
            icon_svc=mock_deps["icon_svc"],
            db=mock_deps["db"],
        )
        elapsed = time.perf_counter() - start

        # Sequential would take >= 0.30s (0.15 + 0.15).
        # Parallel should complete in ~0.15s. Allow generous headroom.
        assert elapsed < 0.25, (
            f"Expected parallel execution under 0.25s, got {elapsed:.3f}s "
            "(suggests sequential, not parallel)"
        )

    async def test_both_operations_called(self, mock_deps):
        """Both triplestore query and db.execute (favorites) should be called."""
        from app.browser.objects import get_object

        await get_object(
            request=mock_deps["request"],
            object_iri=TEST_IRI,
            mode="read",
            embed=0,
            user=mock_deps["user"],
            shapes_service=mock_deps["shapes_service"],
            label_service=mock_deps["label_service"],
            client=mock_deps["client"],
            icon_svc=mock_deps["icon_svc"],
            db=mock_deps["db"],
        )

        assert mock_deps["client"].query.call_count == 1, "SPARQL query not called"
        assert mock_deps["db"].execute.call_count == 1, "Favorites check not called"


class TestTimingLog:
    """Verify that the handler logs wall-clock time at INFO level."""

    async def test_timing_log_emitted(self, mock_deps, caplog):
        """Handler should log 'get_object ... completed in X.XXXs' at INFO."""
        from app.browser.objects import get_object

        with caplog.at_level(logging.INFO, logger="app.browser.objects"):
            await get_object(
                request=mock_deps["request"],
                object_iri=TEST_IRI,
                mode="read",
                embed=0,
                user=mock_deps["user"],
                shapes_service=mock_deps["shapes_service"],
                label_service=mock_deps["label_service"],
                client=mock_deps["client"],
                icon_svc=mock_deps["icon_svc"],
                db=mock_deps["db"],
            )

        timing_msgs = [
            r.message for r in caplog.records
            if "get_object" in r.message and "completed in" in r.message
        ]
        assert len(timing_msgs) >= 1, (
            f"Expected timing log message, got: {[r.message for r in caplog.records]}"
        )
        # Verify the IRI is in the message
        assert TEST_IRI in timing_msgs[0], "Timing log should include the object IRI"
        # Verify it contains a time value like "0.123s"
        assert "s" in timing_msgs[0], "Timing log should include seconds"

    async def test_timing_log_includes_elapsed(self, mock_deps, caplog):
        """The logged time should be a reasonable positive number."""
        from app.browser.objects import get_object

        with caplog.at_level(logging.INFO, logger="app.browser.objects"):
            await get_object(
                request=mock_deps["request"],
                object_iri=TEST_IRI,
                mode="read",
                embed=0,
                user=mock_deps["user"],
                shapes_service=mock_deps["shapes_service"],
                label_service=mock_deps["label_service"],
                client=mock_deps["client"],
                icon_svc=mock_deps["icon_svc"],
                db=mock_deps["db"],
            )

        timing_msgs = [
            r.message for r in caplog.records
            if "completed in" in r.message
        ]
        assert timing_msgs, "No timing log found"
        # Extract the numeric value — format is "get_object <IRI> completed in X.XXXs"
        import re
        match = re.search(r"(\d+\.\d+)s", timing_msgs[0])
        assert match, f"Could not parse elapsed time from: {timing_msgs[0]}"
        elapsed = float(match.group(1))
        assert elapsed > 0, "Elapsed time should be positive"
        assert elapsed < 10, "Elapsed time should be reasonable (< 10s)"
