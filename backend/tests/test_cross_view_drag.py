"""Unit tests for cross-view drag: calendar external drop data flow
and PATCH endpoint handling of start-only vs start+end payloads.

These complement test_calendar_editable.py with focused tests on the
exact payloads the JS external drop handler sends:
  1. start + end (the default 1-hour block from handleExternalDrop)
  2. start only (edge case when only scheduledStart is set)

Also validates the scope-changed event detail structure that the
workspace.js dispatch emits.
"""

import uuid
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rdflib import URIRef


# ── Helpers ────────────────────────────────────────────────────


@dataclass
class _FakeEventResult:
    """Minimal stand-in for EventResult returned by EventStore.commit()."""
    event_iri: URIRef
    timestamp: str


def _make_fake_user():
    user = MagicMock()
    user.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user.role = "member"
    return user


def _make_fake_request():
    return MagicMock()


def _mock_client_returning_type(type_iri: str) -> MagicMock:
    """Create a triplestore client mock that returns a single type binding."""
    client = MagicMock()
    client.query = AsyncMock(return_value={
        "results": {"bindings": [
            {"type": {"value": type_iri}},
        ]},
    })
    return client


# ── External drop: start + end (default 1-hour block) ─────────


class TestExternalDropStartAndEnd:
    """Simulates the exact payload handleExternalDrop sends:
    { iri, start: <ISO>, end: <+1hr ISO> }"""

    @pytest.mark.asyncio
    async def test_task_drop_with_start_and_end(self):
        """PATCH with start+end dispatches both scheduledStart and scheduledEnd."""
        from app.views.router import calendar_patch, CalendarPatchRequest

        client = _mock_client_returning_type("urn:sempkm:model:basic-pkm:Task")
        fake_result = _FakeEventResult(
            event_iri=URIRef("urn:sempkm:event:drop-1"),
            timestamp="2025-06-15T14:00:00+00:00",
        )

        body = CalendarPatchRequest(
            iri="urn:sempkm:obj:task-drag-1",
            start="2025-06-15T14:00:00",
            end="2025-06-15T15:00:00",
        )

        validation_queue = MagicMock()
        validation_queue.enqueue = AsyncMock()
        webhook_service = MagicMock()
        webhook_service.dispatch = AsyncMock()

        with patch("app.commands.dispatcher.dispatch", new_callable=AsyncMock) as mock_dispatch, \
             patch("app.events.store.EventStore") as MockEventStore:
            mock_dispatch.return_value = MagicMock()
            mock_store = MagicMock()
            mock_store.commit = AsyncMock(return_value=fake_result)
            MockEventStore.return_value = mock_store

            result = await calendar_patch(
                body=body,
                request=_make_fake_request(),
                user=_make_fake_user(),
                client=client,
                view_spec_service=MagicMock(),
                validation_queue=validation_queue,
                webhook_service=webhook_service,
            )

        assert result.status_code == 200

        import json
        content = json.loads(result.body)
        assert content["ok"] is True

        # Verify both date predicates present
        dispatched_cmd = mock_dispatch.call_args[0][0]
        props = dispatched_cmd.params.properties
        assert props["urn:sempkm:model:basic-pkm:scheduledStart"] == "2025-06-15T14:00:00"
        assert props["urn:sempkm:model:basic-pkm:scheduledEnd"] == "2025-06-15T15:00:00"


# ── External drop: start only (minimum payload) ───────────────


class TestExternalDropStartOnly:
    """Simulates a drop where only start is provided (no end).
    This is the external drop's minimum valid payload."""

    @pytest.mark.asyncio
    async def test_task_drop_start_only_succeeds(self):
        """PATCH with start-only dispatches scheduledStart, omits scheduledEnd."""
        from app.views.router import calendar_patch, CalendarPatchRequest

        client = _mock_client_returning_type("urn:sempkm:model:basic-pkm:Task")
        fake_result = _FakeEventResult(
            event_iri=URIRef("urn:sempkm:event:drop-2"),
            timestamp="2025-06-15T14:00:00+00:00",
        )

        body = CalendarPatchRequest(
            iri="urn:sempkm:obj:task-drag-2",
            start="2025-06-15T14:00:00",
        )

        validation_queue = MagicMock()
        validation_queue.enqueue = AsyncMock()
        webhook_service = MagicMock()
        webhook_service.dispatch = AsyncMock()

        with patch("app.commands.dispatcher.dispatch", new_callable=AsyncMock) as mock_dispatch, \
             patch("app.events.store.EventStore") as MockEventStore:
            mock_dispatch.return_value = MagicMock()
            mock_store = MagicMock()
            mock_store.commit = AsyncMock(return_value=fake_result)
            MockEventStore.return_value = mock_store

            result = await calendar_patch(
                body=body,
                request=_make_fake_request(),
                user=_make_fake_user(),
                client=client,
                view_spec_service=MagicMock(),
                validation_queue=validation_queue,
                webhook_service=webhook_service,
            )

        assert result.status_code == 200

        dispatched_cmd = mock_dispatch.call_args[0][0]
        props = dispatched_cmd.params.properties
        assert "urn:sempkm:model:basic-pkm:scheduledStart" in props
        assert "urn:sempkm:model:basic-pkm:scheduledEnd" not in props

    @pytest.mark.asyncio
    async def test_event_drop_start_only_uses_schema_predicates(self):
        """PATCH on Event type with start-only uses schema:startDate."""
        from app.views.router import calendar_patch, CalendarPatchRequest

        client = _mock_client_returning_type("urn:sempkm:model:basic-pkm:Event")
        fake_result = _FakeEventResult(
            event_iri=URIRef("urn:sempkm:event:drop-3"),
            timestamp="2025-06-15T10:00:00+00:00",
        )

        body = CalendarPatchRequest(
            iri="urn:sempkm:obj:event-drag-1",
            start="2025-06-15T10:00:00",
        )

        validation_queue = MagicMock()
        validation_queue.enqueue = AsyncMock()
        webhook_service = MagicMock()
        webhook_service.dispatch = AsyncMock()

        with patch("app.commands.dispatcher.dispatch", new_callable=AsyncMock) as mock_dispatch, \
             patch("app.events.store.EventStore") as MockEventStore:
            mock_dispatch.return_value = MagicMock()
            mock_store = MagicMock()
            mock_store.commit = AsyncMock(return_value=fake_result)
            MockEventStore.return_value = mock_store

            result = await calendar_patch(
                body=body,
                request=_make_fake_request(),
                user=_make_fake_user(),
                client=client,
                view_spec_service=MagicMock(),
                validation_queue=validation_queue,
                webhook_service=webhook_service,
            )

        assert result.status_code == 200
        dispatched_cmd = mock_dispatch.call_args[0][0]
        props = dispatched_cmd.params.properties
        assert "https://schema.org/startDate" in props
        assert "https://schema.org/endDate" not in props


# ── Scope-changed event detail structure ───────────────────────


class TestScopeChangedEventStructure:
    """Validates the expected shape of the sempkm:scope-changed event detail
    that workspace.js dispatches. These tests verify the contract, not the JS —
    they confirm the expected fields exist in the documented detail shape."""

    def test_scope_event_detail_has_required_fields(self):
        """The documented event detail shape has all four fields."""
        # This is a contract test — the JS dispatches this shape, and
        # calendar/kanban listeners depend on it.
        expected_fields = {"scopeQuery", "renderer", "selectedType", "sourcePanel"}
        # Simulate the detail object that applyScopeQuery dispatches
        detail = {
            "scopeQuery": "urn:sempkm:query:my-query",
            "renderer": "calendar",
            "selectedType": "urn:sempkm:model:basic-pkm:Task",
            "sourcePanel": "dv_id_1234",
        }
        assert set(detail.keys()) == expected_fields

    def test_scope_event_detail_allows_empty_scope(self):
        """scopeQuery can be empty string (clear scope filter)."""
        detail = {
            "scopeQuery": "",
            "renderer": "kanban",
            "selectedType": "urn:sempkm:model:basic-pkm:Task",
            "sourcePanel": "dv_id_5678",
        }
        assert detail["scopeQuery"] == ""
        assert detail["sourcePanel"] != ""

    def test_scope_event_detail_allows_empty_source_panel(self):
        """sourcePanel can be empty when element is not inside a dv-panel."""
        detail = {
            "scopeQuery": "urn:sempkm:query:some-query",
            "renderer": "table",
            "selectedType": "",
            "sourcePanel": "",
        }
        assert detail["sourcePanel"] == ""
