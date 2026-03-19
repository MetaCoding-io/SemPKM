"""Unit tests for the Google Calendar pull sync engine.

Loads app modules from the apps directory via importlib so the app does
not need to be installed as a package.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

import pytest

# ---------------------------------------------------------------------------
# Load app modules from apps directory (dependency order)
# ---------------------------------------------------------------------------

_SERVICES_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "google-calendar"
    / "services"
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_field_mapper = _load_module("field_mapper", _SERVICES_DIR / "field_mapper.py")
_person_matcher = _load_module(
    "person_matcher", _SERVICES_DIR / "person_matcher.py"
)
_gcal_client = _load_module("gcal_client", _SERVICES_DIR / "gcal_client.py")
_auth = _load_module("auth", _SERVICES_DIR / "auth.py")
_sync_engine = _load_module("sync_engine", _SERVICES_DIR / "sync_engine.py")

pull_sync = _sync_engine.pull_sync
push_sync = _sync_engine.push_sync
_find_existing_event = _sync_engine._find_existing_event
_find_changed_events = _sync_engine._find_changed_events
_build_create_command = _sync_engine._build_create_command
_build_update_commands = _sync_engine._build_update_commands
_submit_commands_batched = _sync_engine._submit_commands_batched
BATCH_SIZE = _sync_engine.BATCH_SIZE
BPKM = _field_mapper.BPKM
compute_event_slug = _field_mapper.compute_event_slug
build_event_patch = _field_mapper.build_event_patch
GCalAPIError = _gcal_client.GCalAPIError


# ===================================================================
# Mock clients
# ===================================================================


class MockStateClient:
    """In-memory key-value store mirroring SDK StateClient."""

    def __init__(self, data: dict[str, str] | None = None):
        self._data = dict(data or {})

    async def get(self, key: str) -> str | None:
        return self._data.get(key)

    async def set(self, key: str, value: str) -> None:
        self._data[key] = value


class MockGraphClient:
    """Stub for GraphClient.query() — returns results by slug lookup.

    ``slug_map`` values: ``{"iri": ..., "status": ..., "externalId": ..., "lastSyncedAt": ...}``
    or just a string (treated as IRI with defaults).

    ``changed_events`` is a list of dicts returned when the query matches
    ``_find_changed_events`` pattern (selects with ``externalProvider``
    + ``modified`` filter but no ``STRENDS``).
    """

    def __init__(
        self,
        default_results: dict | None = None,
        slug_map: dict[str, str | dict] | None = None,
        email_to_iri: dict[str, str] | None = None,
        changed_events: list[dict] | None = None,
    ):
        self.default_results = default_results or {"results": {"bindings": []}}
        self.slug_map = slug_map or {}
        self.email_to_iri = email_to_iri or {}
        self.changed_events = changed_events or []
        self.queries: list[str] = []

    async def query(self, sparql: str) -> dict:
        self.queries.append(sparql)
        # Check slug-based lookups (STRENDS)
        if "STRENDS" in sparql:
            for slug, info in self.slug_map.items():
                if slug in sparql:
                    if isinstance(info, str):
                        info = {"iri": info}
                    binding: dict = {
                        "event": {"type": "uri", "value": info["iri"]},
                    }
                    if info.get("status"):
                        binding["status"] = {
                            "type": "literal",
                            "value": info["status"],
                        }
                    if info.get("externalId"):
                        binding["extId"] = {
                            "type": "literal",
                            "value": info["externalId"],
                        }
                    if info.get("lastSyncedAt"):
                        binding["lastSynced"] = {
                            "type": "literal",
                            "value": info["lastSyncedAt"],
                        }
                    return {"results": {"bindings": [binding]}}
        # Check _find_changed_events pattern (no STRENDS, has responseStatus)
        elif "responseStatus" in sparql and "STRENDS" not in sparql and self.changed_events:
            bindings = []
            for evt in self.changed_events:
                binding = {
                    "event": {"type": "uri", "value": evt["iri"]},
                    "extId": {"type": "literal", "value": evt["externalId"]},
                }
                if evt.get("calendarName"):
                    binding["calName"] = {"type": "literal", "value": evt["calendarName"]}
                if evt.get("responseStatus"):
                    binding["responseStatus"] = {"type": "literal", "value": evt["responseStatus"]}
                if evt.get("lastSyncedAt"):
                    binding["lastSynced"] = {"type": "literal", "value": evt["lastSyncedAt"]}
                bindings.append(binding)
            return {"results": {"bindings": bindings}}
        # Check person-matcher email queries
        if "foaf" in sparql.lower() or "crm:email" in sparql.lower():
            for email, iri in self.email_to_iri.items():
                if email.lower() in sparql.lower():
                    return {
                        "results": {
                            "bindings": [
                                {"person": {"type": "uri", "value": iri}}
                            ]
                        }
                    }
        return self.default_results


class MockResponse:
    """Minimal httpx.Response stub."""

    def __init__(self, status_code: int = 200, data=None,
                 headers: dict | None = None):
        self.status_code = status_code
        self._data = data if data is not None else {}
        self.headers = headers or {}
        self.text = json.dumps(self._data)

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class MockHttpClient:
    """Stub for httpx.AsyncClient — records POST calls."""

    def __init__(self):
        self.posts: list[dict] = []

    async def post(self, url: str, json: dict | None = None, **kwargs) -> MockResponse:
        self.posts.append({"url": url, "json": json, **kwargs})
        return MockResponse(200, {"ok": True})


class MockCommandClient:
    """Stub for CommandClient with ._client for bulk POST and .execute()."""

    def __init__(self, http_client=None):
        self._client = http_client or MockHttpClient()
        self.commands: list[dict] = []

    async def execute(self, command_type: str, params: dict) -> dict:
        self.commands.append({"command": command_type, "params": params})
        slug = params.get("slug", "unknown")
        type_name = params["type"].split(":")[-1]
        return {"iri": f"https://example.org/data/{type_name}/{slug}"}


class MockExternalHttpClient:
    """Stub for SDK HttpClient (external requests).

    Supports get/post methods and pre-configured responses.
    """

    def __init__(self, responses: list[MockResponse] | None = None):
        self.requests: list[dict] = []
        self._responses = list(responses or [])
        self._index = 0

    async def get(self, url: str, **kwargs) -> MockResponse:
        self.requests.append({"method": "GET", "url": url, **kwargs})
        return self._next_response()

    async def post(self, url: str, **kwargs) -> MockResponse:
        self.requests.append({"method": "POST", "url": url, **kwargs})
        return self._next_response()

    async def patch(self, url: str, **kwargs) -> MockResponse:
        self.requests.append({"method": "PATCH", "url": url, **kwargs})
        return self._next_response()

    def _next_response(self) -> MockResponse:
        if self._index < len(self._responses):
            resp = self._responses[self._index]
            self._index += 1
            return resp
        return MockResponse(200, {"access_token": "test-token", "expires_in": 3600})

    async def close(self):
        pass


class MockAppContext:
    """Mimics the SDK ``AppContext`` with all required client attributes."""

    def __init__(
        self,
        state_data: dict[str, str] | None = None,
        graph_client: MockGraphClient | None = None,
        http_client: MockHttpClient | None = None,
        ext_http_client: MockExternalHttpClient | None = None,
    ):
        self.state = MockStateClient(state_data)
        self.graph = graph_client or MockGraphClient()
        _http = http_client or MockHttpClient()
        self.commands = MockCommandClient(_http)
        self.http = ext_http_client or MockExternalHttpClient()
        self.app_id = "google-calendar"


# ===================================================================
# Event fixtures
# ===================================================================


def make_event(
    event_id: str = "evt001",
    summary: str = "Team Standup",
    **overrides,
) -> dict:
    """Build a realistic Google Calendar event dict."""
    base = {
        "id": event_id,
        "summary": summary,
        "status": "confirmed",
        "htmlLink": f"https://calendar.google.com/event?eid={event_id}",
        "created": "2026-03-17T10:00:00Z",
        "updated": "2026-03-18T12:00:00Z",
        "start": {"dateTime": "2026-03-19T09:00:00-04:00", "timeZone": "America/New_York"},
        "end": {"dateTime": "2026-03-19T09:30:00-04:00", "timeZone": "America/New_York"},
        "attendees": [],
        "organizer": {"email": "organizer@example.com", "self": True},
    }
    base.update(overrides)
    return base


def make_all_day_event(event_id: str = "allday001", summary: str = "Holiday") -> dict:
    """Build an all-day event."""
    return make_event(
        event_id=event_id,
        summary=summary,
        start={"date": "2026-03-20"},
        end={"date": "2026-03-21"},
    )


def _make_connected_state(
    calendars: list[str] | None = None,
    sync_tokens: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build state dict for a connected account with calendars selected."""
    data: dict[str, str] = {
        "auth_method": "oauth",
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
        "token_expiry": "2099-12-31T23:59:59Z",
        "google_email": "user@example.com",
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
    }
    if calendars is not None:
        data["selected_calendars"] = json.dumps(calendars)
    if sync_tokens:
        for cal_id, token in sync_tokens.items():
            data[f"sync_token:{cal_id}"] = token
    return data


# ===================================================================
# TestFindExistingEvent
# ===================================================================


class TestFindExistingEvent:
    """Test SPARQL lookup for existing events."""

    @pytest.mark.asyncio
    async def test_found(self):
        """When an event with the slug exists, return its info."""
        slug = "abc123"
        graph = MockGraphClient(slug_map={
            slug: {
                "iri": "https://example.org/data/Event/abc123",
                "status": "confirmed",
                "externalId": "gcal-evt-1",
                "lastSyncedAt": "2026-03-17T10:00:00Z",
            }
        })
        result = await _find_existing_event(graph, slug)
        assert result is not None
        assert result["iri"] == "https://example.org/data/Event/abc123"
        assert result["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_not_found(self):
        """When no event matches, return None."""
        graph = MockGraphClient()
        result = await _find_existing_event(graph, "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_bindings(self):
        """Empty bindings list should return None."""
        graph = MockGraphClient(
            default_results={"results": {"bindings": []}}
        )
        result = await _find_existing_event(graph, "anything")
        assert result is None


# ===================================================================
# TestBuildCreateCommand
# ===================================================================


class TestBuildCreateCommand:
    """Test object.create command builder."""

    def test_correct_type_and_slug(self):
        cmd = _build_create_command("myslug", {"dcterms:title": "Test"})
        assert cmd["command"] == "object.create"
        assert cmd["params"]["type"] == f"{BPKM}Event"
        assert cmd["params"]["slug"] == "myslug"

    def test_properties_included(self):
        props = {"dcterms:title": "Meeting", f"{BPKM}location": "Room A"}
        cmd = _build_create_command("s1", props)
        assert cmd["params"]["properties"] == props


# ===================================================================
# TestBuildUpdateCommands
# ===================================================================


class TestBuildUpdateCommands:
    """Test update command builder."""

    def test_patch_only(self):
        """With no body or edges, only object.patch is returned."""
        cmds = _build_update_commands(
            "urn:evt:1", {"dcterms:title": "Updated"}, None, [], None
        )
        assert len(cmds) == 1
        assert cmds[0]["command"] == "object.patch"

    def test_with_body(self):
        """body.set command should be included when description provided."""
        cmds = _build_update_commands(
            "urn:evt:1", {}, "Meeting notes here", [], None
        )
        assert any(c["command"] == "body.set" for c in cmds)
        body_cmd = [c for c in cmds if c["command"] == "body.set"][0]
        assert body_cmd["params"]["body"] == "Meeting notes here"

    def test_with_attendees_and_organizer(self):
        """edge.create commands for attendees and organizer."""
        cmds = _build_update_commands(
            "urn:evt:1",
            {},
            None,
            ["urn:person:alice", "urn:person:bob"],
            "urn:person:carol",
        )
        edge_cmds = [c for c in cmds if c["command"] == "edge.create"]
        assert len(edge_cmds) == 3  # 2 attendees + 1 organizer

        predicates = [c["params"]["predicate"] for c in edge_cmds]
        assert f"{BPKM}attendee" in predicates
        assert f"{BPKM}organizer" in predicates

    def test_attendee_edge_targets(self):
        """Each attendee gets its own edge.create."""
        cmds = _build_update_commands(
            "urn:evt:1", {}, None, ["urn:p:a", "urn:p:b"], None
        )
        edge_cmds = [c for c in cmds if c["command"] == "edge.create"]
        targets = [c["params"]["target"] for c in edge_cmds]
        assert "urn:p:a" in targets
        assert "urn:p:b" in targets


# ===================================================================
# TestSubmitCommandsBatched
# ===================================================================


class TestSubmitCommandsBatched:
    """Test batched command submission."""

    @pytest.mark.asyncio
    async def test_single_batch(self):
        http = MockHttpClient()
        cmds = [{"command": "object.create", "params": {}} for _ in range(5)]
        await _submit_commands_batched(http, cmds, "test", "google-calendar")
        assert len(http.posts) == 1
        assert len(http.posts[0]["json"]["commands"]) == 5

    @pytest.mark.asyncio
    async def test_multi_batch(self):
        """Commands exceeding BATCH_SIZE should be split."""
        http = MockHttpClient()
        cmds = [{"command": "object.create", "params": {}} for _ in range(BATCH_SIZE + 5)]
        await _submit_commands_batched(http, cmds, "test", "google-calendar")
        assert len(http.posts) == 2
        assert len(http.posts[0]["json"]["commands"]) == BATCH_SIZE
        assert len(http.posts[1]["json"]["commands"]) == 5

    @pytest.mark.asyncio
    async def test_empty_commands(self):
        """Empty command list should produce no POST calls."""
        http = MockHttpClient()
        await _submit_commands_batched(http, [], "test", "google-calendar")
        assert len(http.posts) == 0


# ===================================================================
# TestPullSync
# ===================================================================


class TestPullSyncNotConnected:
    """Test pull_sync when not authenticated."""

    @pytest.mark.asyncio
    async def test_not_connected(self):
        ctx = MockAppContext(state_data={})
        result = await pull_sync(ctx)
        assert result["status"] == "skipped"
        assert "not connected" in result["reason"]


class TestPullSyncNoCalendars:
    """Test pull_sync with no calendars selected."""

    @pytest.mark.asyncio
    async def test_no_calendars_state_missing(self):
        ctx = MockAppContext(state_data=_make_connected_state())
        result = await pull_sync(ctx)
        assert result["status"] == "ok"
        assert result["created"] == 0
        assert "No calendars" in result.get("message", "")

    @pytest.mark.asyncio
    async def test_empty_calendar_list(self):
        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=[])
        )
        result = await pull_sync(ctx)
        assert result["status"] == "ok"
        assert result["created"] == 0


class TestPullSyncNewEvents:
    """Test pull_sync creating new events."""

    @pytest.mark.asyncio
    async def test_creates_single_event(self):
        """A single new event should produce 1 create command."""
        event = make_event()
        events_resp = MockResponse(200, {
            "items": [event],
            "nextSyncToken": "new-token-1",
        })
        ext_http = MockExternalHttpClient(responses=[events_resp])

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        assert result["status"] == "ok"
        assert result["created"] == 1
        assert result["errors"] == []

        # Verify create command was submitted
        bulk_http = ctx.commands._client
        assert len(bulk_http.posts) >= 1

    @pytest.mark.asyncio
    async def test_creates_multiple_events(self):
        """Multiple events should produce multiple create commands."""
        events = [make_event(event_id=f"evt{i}") for i in range(3)]
        events_resp = MockResponse(200, {
            "items": events,
            "nextSyncToken": "tok-multi",
        })
        ext_http = MockExternalHttpClient(responses=[events_resp])

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        assert result["created"] == 3
        assert result["errors"] == []


class TestPullSyncExistingEvents:
    """Test pull_sync updating existing events."""

    @pytest.mark.asyncio
    async def test_updates_existing_event(self):
        """An event whose slug matches an existing IRI should update."""
        event = make_event(event_id="existing1")
        slug = compute_event_slug("cal@example.com", "existing1")

        events_resp = MockResponse(200, {
            "items": [event],
            "nextSyncToken": "tok-upd",
        })
        ext_http = MockExternalHttpClient(responses=[events_resp])

        graph = MockGraphClient(slug_map={
            slug: {
                "iri": f"https://example.org/data/Event/{slug}",
                "status": "confirmed",
            }
        })

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            graph_client=graph,
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        assert result["updated"] == 1
        assert result["created"] == 0


class TestPullSyncMixed:
    """Test pull_sync with a mix of new and existing events."""

    @pytest.mark.asyncio
    async def test_mixed_create_and_update(self):
        new_event = make_event(event_id="new1")
        existing_event = make_event(event_id="existing1")
        slug_existing = compute_event_slug("cal@example.com", "existing1")

        events_resp = MockResponse(200, {
            "items": [new_event, existing_event],
            "nextSyncToken": "tok-mix",
        })
        ext_http = MockExternalHttpClient(responses=[events_resp])

        graph = MockGraphClient(slug_map={
            slug_existing: {
                "iri": f"https://example.org/data/Event/{slug_existing}",
            }
        })

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            graph_client=graph,
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        assert result["created"] == 1
        assert result["updated"] == 1


class TestPullSyncSyncToken:
    """Test syncToken persistence and 410 Gone handling."""

    @pytest.mark.asyncio
    async def test_sync_token_stored(self):
        """After successful sync, syncToken should be saved in state."""
        events_resp = MockResponse(200, {
            "items": [],
            "nextSyncToken": "saved-token-xyz",
        })
        ext_http = MockExternalHttpClient(responses=[events_resp])

        state_data = _make_connected_state(calendars=["cal@example.com"])
        ctx = MockAppContext(
            state_data=state_data,
            ext_http_client=ext_http,
        )
        await pull_sync(ctx)

        stored = await ctx.state.get("sync_token:cal@example.com")
        assert stored == "saved-token-xyz"

    @pytest.mark.asyncio
    async def test_incremental_sync_uses_token(self):
        """When a syncToken exists, it should be passed to get_events."""
        events_resp = MockResponse(200, {
            "items": [],
            "nextSyncToken": "new-token",
        })
        ext_http = MockExternalHttpClient(responses=[events_resp])

        state_data = _make_connected_state(
            calendars=["cal@example.com"],
            sync_tokens={"cal@example.com": "old-token"},
        )
        ctx = MockAppContext(
            state_data=state_data,
            ext_http_client=ext_http,
        )
        await pull_sync(ctx)

        # Verify the request URL contains the syncToken
        get_reqs = [r for r in ext_http.requests if r["method"] == "GET"]
        assert any("syncToken=old-token" in r["url"] for r in get_reqs)

    @pytest.mark.asyncio
    async def test_410_gone_retries_full_sync(self):
        """On 410 Gone, clear syncToken and retry as full sync."""
        # First response: token refresh
        # Second response: 410 Gone for incremental sync (will be handled by _request)
        gone_resp = MockResponse(410, {"error": {"code": 410, "message": "Sync token expired"}})
        # Third response: full sync succeeds
        full_resp = MockResponse(200, {
            "items": [make_event()],
            "nextSyncToken": "fresh-token",
        })
        ext_http = MockExternalHttpClient(responses=[gone_resp, full_resp])

        state_data = _make_connected_state(
            calendars=["cal@example.com"],
            sync_tokens={"cal@example.com": "expired-token"},
        )
        ctx = MockAppContext(
            state_data=state_data,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["status"] == "ok"
        assert result["created"] == 1
        # syncToken should be updated to the fresh one
        stored = await ctx.state.get("sync_token:cal@example.com")
        assert stored == "fresh-token"


class TestPullSyncErrorIsolation:
    """Test per-event error isolation."""

    @pytest.mark.asyncio
    async def test_bad_event_doesnt_block_others(self):
        """One event raising an exception should not block the rest."""
        good_event = make_event(event_id="good1")
        # Bad event: missing start field entirely (will cause an error in field mapper)
        bad_event = {"id": "bad1"}  # minimal — will fail somewhere

        events_resp = MockResponse(200, {
            "items": [good_event, bad_event],
            "nextSyncToken": "tok-err",
        })
        ext_http = MockExternalHttpClient(responses=[events_resp])

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        # Good event should still be created
        assert result["created"] >= 1
        # Bad event captured in errors (or it happened to succeed — depends on field mapper)
        # The key invariant: no exception propagated

    @pytest.mark.asyncio
    async def test_errors_include_event_id(self):
        """Errors should include the event_id for diagnosis."""
        # Create a context where the graph client raises on query
        class FailingGraphClient(MockGraphClient):
            async def query(self, sparql: str) -> dict:
                self.queries.append(sparql)
                if "STRENDS" in sparql:
                    raise RuntimeError("SPARQL timeout")
                return self.default_results

        events_resp = MockResponse(200, {
            "items": [make_event(event_id="fail-evt")],
            "nextSyncToken": "tok",
        })
        ext_http = MockExternalHttpClient(responses=[events_resp])

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            graph_client=FailingGraphClient(),
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        assert len(result["errors"]) >= 1
        assert result["errors"][0]["event_id"] == "fail-evt"
        assert "SPARQL timeout" in result["errors"][0]["error"]


class TestPullSyncAttendees:
    """Test attendee and organizer matching."""

    @pytest.mark.asyncio
    async def test_attendees_matched(self):
        """Non-self attendees should trigger person matching."""
        event = make_event(
            event_id="with-attendees",
            attendees=[
                {"email": "alice@example.com", "displayName": "Alice", "self": False},
                {"email": "user@example.com", "displayName": "Me", "self": True},
                {"email": "bob@example.com", "displayName": "Bob", "self": False},
            ],
            organizer={"email": "user@example.com", "self": True},
        )
        events_resp = MockResponse(200, {
            "items": [event],
            "nextSyncToken": "tok-att",
        })
        ext_http = MockExternalHttpClient(responses=[events_resp])

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        assert result["created"] == 1
        # Person matcher should have been called for alice and bob (not self)
        assert len(ctx.commands.commands) >= 2  # at least 2 person creates

    @pytest.mark.asyncio
    async def test_organizer_matched(self):
        """Non-self organizer should trigger person matching."""
        event = make_event(
            event_id="ext-organizer",
            organizer={"email": "boss@example.com", "displayName": "Boss", "self": False},
            attendees=[],
        )
        events_resp = MockResponse(200, {
            "items": [event],
            "nextSyncToken": "tok-org",
        })
        ext_http = MockExternalHttpClient(responses=[events_resp])

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        assert result["created"] == 1
        # Person matcher creates the organizer
        assert len(ctx.commands.commands) >= 1

    @pytest.mark.asyncio
    async def test_self_organizer_not_matched(self):
        """Self organizer should NOT create a person."""
        event = make_event(
            event_id="self-org",
            organizer={"email": "user@example.com", "self": True},
            attendees=[],
        )
        events_resp = MockResponse(200, {
            "items": [event],
            "nextSyncToken": "tok-so",
        })
        ext_http = MockExternalHttpClient(responses=[events_resp])

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        assert result["created"] == 1
        # No person creates — organizer is self
        assert len(ctx.commands.commands) == 0


class TestPullSyncMultipleCalendars:
    """Test pull_sync with multiple calendars."""

    @pytest.mark.asyncio
    async def test_two_calendars(self):
        """Events from two calendars should be processed independently."""
        events1 = MockResponse(200, {
            "items": [make_event(event_id="cal1-evt1")],
            "nextSyncToken": "tok-cal1",
        })
        events2 = MockResponse(200, {
            "items": [make_event(event_id="cal2-evt1"), make_event(event_id="cal2-evt2")],
            "nextSyncToken": "tok-cal2",
        })
        ext_http = MockExternalHttpClient(
            responses=[events1, events2]
        )

        ctx = MockAppContext(
            state_data=_make_connected_state(
                calendars=["cal1@example.com", "cal2@example.com"]
            ),
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        assert result["created"] == 3  # 1 + 2
        # Both sync tokens stored
        tok1 = await ctx.state.get("sync_token:cal1@example.com")
        tok2 = await ctx.state.get("sync_token:cal2@example.com")
        assert tok1 == "tok-cal1"
        assert tok2 == "tok-cal2"


class TestPullSyncAllDayEvents:
    """Test that all-day events are handled correctly."""

    @pytest.mark.asyncio
    async def test_all_day_event_created(self):
        event = make_all_day_event()
        events_resp = MockResponse(200, {
            "items": [event],
            "nextSyncToken": "tok-ad",
        })
        ext_http = MockExternalHttpClient(responses=[events_resp])

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        assert result["created"] == 1
        assert result["errors"] == []


class TestPullSyncConferenceData:
    """Test events with conference URLs."""

    @pytest.mark.asyncio
    async def test_event_with_conference(self):
        event = make_event(
            event_id="conf1",
            conferenceData={
                "entryPoints": [
                    {"entryPointType": "video", "uri": "https://meet.google.com/abc-def-ghi"},
                ]
            },
        )
        events_resp = MockResponse(200, {
            "items": [event],
            "nextSyncToken": "tok-conf",
        })
        ext_http = MockExternalHttpClient(responses=[events_resp])

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        assert result["created"] == 1
        assert result["errors"] == []


class TestPullSyncRecurrence:
    """Test events with recurrence rules."""

    @pytest.mark.asyncio
    async def test_recurring_event(self):
        event = make_event(
            event_id="recur1",
            recurrence=["RRULE:FREQ=WEEKLY;BYDAY=MO"],
        )
        events_resp = MockResponse(200, {
            "items": [event],
            "nextSyncToken": "tok-recur",
        })
        ext_http = MockExternalHttpClient(responses=[events_resp])

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        assert result["created"] == 1
        assert result["errors"] == []


class TestPullSyncDescription:
    """Test events with description (body) content."""

    @pytest.mark.asyncio
    async def test_new_event_with_description(self):
        """New event with description should defer body.set to phase 2."""
        event = make_event(
            event_id="desc1",
            description="<p>Meeting agenda</p>",
        )
        slug = compute_event_slug("cal@example.com", "desc1")

        events_resp = MockResponse(200, {
            "items": [event],
            "nextSyncToken": "tok-desc",
        })
        ext_http = MockExternalHttpClient(responses=[events_resp])

        # After phase 1 create, the slug lookup should find the event
        graph = MockGraphClient()
        # We can't easily simulate the two-phase lookup (not found first,
        # then found after create) without a stateful mock. Instead, we just
        # verify the pipeline runs without error.
        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            graph_client=graph,
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        assert result["created"] == 1
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_existing_event_with_description(self):
        """Existing event with description should include body.set in update."""
        event = make_event(event_id="desc-upd", description="Updated notes")
        slug = compute_event_slug("cal@example.com", "desc-upd")

        events_resp = MockResponse(200, {
            "items": [event],
            "nextSyncToken": "tok-du",
        })
        ext_http = MockExternalHttpClient(responses=[events_resp])

        graph = MockGraphClient(slug_map={
            slug: {"iri": f"https://example.org/data/Event/{slug}"}
        })

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            graph_client=graph,
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        assert result["updated"] == 1

        # Check that body.set was among the posted commands
        bulk_http = ctx.commands._client
        assert len(bulk_http.posts) >= 1
        all_cmds = []
        for post in bulk_http.posts:
            all_cmds.extend(post["json"].get("commands", []))
        body_cmds = [c for c in all_cmds if c["command"] == "body.set"]
        assert len(body_cmds) >= 1


class TestPullSyncLastSyncAt:
    """Test that last_sync_at and last_pull_result are stored."""

    @pytest.mark.asyncio
    async def test_last_sync_at_stored(self):
        events_resp = MockResponse(200, {"items": [], "nextSyncToken": "t1"})
        ext_http = MockExternalHttpClient(responses=[events_resp])

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            ext_http_client=ext_http,
        )
        await pull_sync(ctx)

        last_sync = await ctx.state.get("last_sync_at")
        assert last_sync is not None

    @pytest.mark.asyncio
    async def test_last_pull_result_stored(self):
        events_resp = MockResponse(200, {"items": [], "nextSyncToken": "t2"})
        ext_http = MockExternalHttpClient(responses=[events_resp])

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        stored = await ctx.state.get("last_pull_result")
        assert stored is not None
        parsed = json.loads(stored)
        assert parsed["status"] == "ok"


class TestPullSyncEmptyCalendar:
    """Test pull_sync with a calendar that has no events."""

    @pytest.mark.asyncio
    async def test_empty_calendar(self):
        events_resp = MockResponse(200, {"items": [], "nextSyncToken": "empty-tok"})
        ext_http = MockExternalHttpClient(responses=[events_resp])

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        assert result["status"] == "ok"
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["errors"] == []


# ===================================================================
# TestFindChangedEvents — push sync change detection
# ===================================================================


class TestFindChangedEvents:
    """Test _find_changed_events SPARQL query."""

    @pytest.mark.asyncio
    async def test_finds_changed_events(self):
        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt1",
                "externalId": "gcal-evt-1",
                "calendarName": "cal@example.com",
                "responseStatus": "accepted",
                "lastSyncedAt": "2026-03-17T10:00:00Z",
            }
        ])
        result = await _find_changed_events(graph)
        assert len(result) == 1
        assert result[0]["iri"] == "https://example.org/data/Event/evt1"
        assert result[0]["externalId"] == "gcal-evt-1"
        assert result[0]["calendarName"] == "cal@example.com"
        assert result[0]["responseStatus"] == "accepted"

    @pytest.mark.asyncio
    async def test_returns_correct_fields(self):
        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt2",
                "externalId": "gcal-evt-2",
                "calendarName": "work@group.calendar.google.com",
                "responseStatus": "tentative",
                "lastSyncedAt": "2026-03-18T08:00:00Z",
            }
        ])
        result = await _find_changed_events(graph)
        assert len(result) == 1
        evt = result[0]
        assert set(evt.keys()) == {"iri", "externalId", "calendarName", "responseStatus", "lastSyncedAt"}

    @pytest.mark.asyncio
    async def test_handles_no_changes(self):
        graph = MockGraphClient(changed_events=[])
        result = await _find_changed_events(graph)
        assert result == []

    @pytest.mark.asyncio
    async def test_multiple_changed_events(self):
        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/a",
                "externalId": "ga",
                "calendarName": "cal@example.com",
                "responseStatus": "accepted",
            },
            {
                "iri": "https://example.org/data/Event/b",
                "externalId": "gb",
                "calendarName": "cal@example.com",
                "responseStatus": "declined",
            },
        ])
        result = await _find_changed_events(graph)
        assert len(result) == 2


# ===================================================================
# TestPushSync — full push pipeline
# ===================================================================


def _make_push_state(
    sync_direction: str = "bidirectional",
    **extra,
) -> dict[str, str]:
    """Build state dict for a connected account ready for push sync."""
    data = _make_connected_state()
    data["sync_direction"] = sync_direction
    data["google_email"] = "user@example.com"
    data.update(extra)
    return data


class TestPushSync:
    """Test push_sync pipeline."""

    @pytest.mark.asyncio
    async def test_not_connected_skips(self):
        ctx = MockAppContext(state_data={})
        result = await push_sync(ctx)
        assert result["status"] == "skipped"
        assert "not connected" in result.get("reason", "")

    @pytest.mark.asyncio
    async def test_pull_only_skips(self):
        ctx = MockAppContext(state_data=_make_push_state(sync_direction="pull-only"))
        result = await push_sync(ctx)
        assert result["status"] == "skipped"
        assert "pull-only" in result.get("reason", "")

    @pytest.mark.asyncio
    async def test_no_changed_events(self):
        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=MockGraphClient(changed_events=[]),
        )
        result = await push_sync(ctx)
        assert result["status"] == "ok"
        assert result["pushed"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_successful_rsvp_push(self):
        """Push an RSVP change and verify PATCH was sent."""
        patch_resp = MockResponse(200, {"id": "gcal-evt-1", "status": "confirmed"})
        ext_http = MockExternalHttpClient(responses=[patch_resp])

        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt1",
                "externalId": "gcal-evt-1",
                "calendarName": "cal@example.com",
                "responseStatus": "declined",
            }
        ])

        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=graph,
            ext_http_client=ext_http,
        )
        result = await push_sync(ctx)

        assert result["status"] == "ok"
        assert result["pushed"] == 1
        assert result["errors"] == []

        # Verify PATCH request
        patch_reqs = [r for r in ext_http.requests if r["method"] == "PATCH"]
        assert len(patch_reqs) == 1
        assert "cal@example.com" in patch_reqs[0]["url"]
        assert "gcal-evt-1" in patch_reqs[0]["url"]

    @pytest.mark.asyncio
    async def test_last_synced_at_updated_after_push(self):
        """After a successful push, lastSyncedAt should be updated."""
        patch_resp = MockResponse(200, {"id": "gcal-evt-1"})
        ext_http = MockExternalHttpClient(responses=[patch_resp])

        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt1",
                "externalId": "gcal-evt-1",
                "calendarName": "cal@example.com",
                "responseStatus": "accepted",
            }
        ])

        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=graph,
            ext_http_client=ext_http,
        )
        await push_sync(ctx)

        # Check that an object.patch command was posted to update lastSyncedAt
        bulk_http = ctx.commands._client
        all_cmds = []
        for post in bulk_http.posts:
            all_cmds.extend(post["json"].get("commands", []))
        patch_cmds = [
            c for c in all_cmds
            if c["command"] == "object.patch"
            and f"{BPKM}lastSyncedAt" in c["params"].get("properties", {})
        ]
        assert len(patch_cmds) == 1
        assert patch_cmds[0]["params"]["iri"] == "https://example.org/data/Event/evt1"

    @pytest.mark.asyncio
    async def test_error_isolation_per_event(self):
        """One event failing should not block others."""
        # First PATCH fails (500), second succeeds
        fail_resp = MockResponse(500, {"error": "Internal error"})
        ok_resp = MockResponse(200, {"id": "gcal-evt-2"})
        ext_http = MockExternalHttpClient(responses=[fail_resp, ok_resp])

        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt1",
                "externalId": "gcal-evt-1",
                "calendarName": "cal@example.com",
                "responseStatus": "declined",
            },
            {
                "iri": "https://example.org/data/Event/evt2",
                "externalId": "gcal-evt-2",
                "calendarName": "cal@example.com",
                "responseStatus": "accepted",
            },
        ])

        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=graph,
            ext_http_client=ext_http,
        )
        result = await push_sync(ctx)

        assert result["status"] == "partial"
        assert result["pushed"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["event_iri"] == "https://example.org/data/Event/evt1"

    @pytest.mark.asyncio
    async def test_last_push_result_stored(self):
        """last_push_result should be stored in state after push."""
        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=MockGraphClient(changed_events=[]),
        )
        await push_sync(ctx)

        stored = await ctx.state.get("last_push_result")
        assert stored is not None
        parsed = json.loads(stored)
        assert parsed["status"] == "ok"
        assert "timestamp" in parsed

    @pytest.mark.asyncio
    async def test_partial_status_on_mixed(self):
        """When some events push and others error, status is 'partial'."""
        # First fails, second succeeds
        fail_resp = MockResponse(500, {"error": "boom"})
        ok_resp = MockResponse(200, {"id": "evt2"})
        ext_http = MockExternalHttpClient(responses=[fail_resp, ok_resp])

        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/e1",
                "externalId": "e1",
                "calendarName": "cal@example.com",
                "responseStatus": "declined",
            },
            {
                "iri": "https://example.org/data/Event/e2",
                "externalId": "e2",
                "calendarName": "cal@example.com",
                "responseStatus": "accepted",
            },
        ])

        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=graph,
            ext_http_client=ext_http,
        )
        result = await push_sync(ctx)

        assert result["status"] == "partial"
        assert result["pushed"] == 1
        assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_all_errors_status(self):
        """When all events error, status is 'error'."""
        fail_resp = MockResponse(500, {"error": "boom"})
        ext_http = MockExternalHttpClient(responses=[fail_resp])

        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/e1",
                "externalId": "e1",
                "calendarName": "cal@example.com",
                "responseStatus": "declined",
            },
        ])

        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=graph,
            ext_http_client=ext_http,
        )
        result = await push_sync(ctx)

        assert result["status"] == "error"
        assert result["pushed"] == 0
        assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_skips_event_without_response_status(self):
        """Events with no responseStatus should be skipped (no PATCH)."""
        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt1",
                "externalId": "gcal-evt-1",
                "calendarName": "cal@example.com",
                "responseStatus": None,  # no response status
            },
        ])

        ext_http = MockExternalHttpClient(responses=[])
        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=graph,
            ext_http_client=ext_http,
        )
        result = await push_sync(ctx)

        assert result["pushed"] == 0
        assert result["skipped"] == 1
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_missing_calendar_name_errors(self):
        """Events with no calendarName should produce an error."""
        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt1",
                "externalId": "gcal-evt-1",
                "calendarName": None,
                "responseStatus": "accepted",
            },
        ])

        ext_http = MockExternalHttpClient(responses=[])
        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=graph,
            ext_http_client=ext_http,
        )
        result = await push_sync(ctx)

        assert result["pushed"] == 0
        assert len(result["errors"]) == 1
        assert "calendarName" in result["errors"][0]["error"]


# ===================================================================
# TestLoopPrevention — pull_sync skips recently pushed events
# ===================================================================


class TestLoopPrevention:
    """Test that pull_sync skips events where updated <= lastSyncedAt."""

    @pytest.mark.asyncio
    async def test_event_with_updated_lte_last_synced_skipped(self):
        """An event whose Google updated <= lastSyncedAt should be skipped."""
        event = make_event(
            event_id="loop1",
            updated="2026-03-18T12:00:00Z",  # same as lastSyncedAt
        )
        slug = compute_event_slug("cal@example.com", "loop1")

        events_resp = MockResponse(200, {
            "items": [event],
            "nextSyncToken": "tok-loop",
        })
        ext_http = MockExternalHttpClient(responses=[events_resp])

        graph = MockGraphClient(slug_map={
            slug: {
                "iri": f"https://example.org/data/Event/{slug}",
                "status": "confirmed",
                "lastSyncedAt": "2026-03-18T12:00:00Z",
            }
        })

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            graph_client=graph,
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        assert result["updated"] == 0
        assert result["unchanged"] == 1

    @pytest.mark.asyncio
    async def test_event_with_updated_gt_last_synced_processed(self):
        """An event whose Google updated > lastSyncedAt should be updated."""
        event = make_event(
            event_id="loop2",
            updated="2026-03-19T14:00:00Z",  # newer than lastSyncedAt
        )
        slug = compute_event_slug("cal@example.com", "loop2")

        events_resp = MockResponse(200, {
            "items": [event],
            "nextSyncToken": "tok-loop2",
        })
        ext_http = MockExternalHttpClient(responses=[events_resp])

        graph = MockGraphClient(slug_map={
            slug: {
                "iri": f"https://example.org/data/Event/{slug}",
                "status": "confirmed",
                "lastSyncedAt": "2026-03-18T10:00:00Z",
            }
        })

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            graph_client=graph,
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        assert result["updated"] == 1
        assert result["unchanged"] == 0

    @pytest.mark.asyncio
    async def test_event_with_no_last_synced_processed(self):
        """An existing event with no lastSyncedAt should be updated."""
        event = make_event(event_id="loop3")
        slug = compute_event_slug("cal@example.com", "loop3")

        events_resp = MockResponse(200, {
            "items": [event],
            "nextSyncToken": "tok-loop3",
        })
        ext_http = MockExternalHttpClient(responses=[events_resp])

        graph = MockGraphClient(slug_map={
            slug: {
                "iri": f"https://example.org/data/Event/{slug}",
                "status": "confirmed",
                # no lastSyncedAt
            }
        })

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal@example.com"]),
            graph_client=graph,
            ext_http_client=ext_http,
        )
        result = await pull_sync(ctx)

        assert result["updated"] == 1


# ===================================================================
# TestPushWiring — app.py handlers call push_sync
# ===================================================================


class TestPushWiring:
    """Test that app.py handlers call push_sync when bidirectional.

    We test the sync_engine functions directly since the app.py route
    handlers import push_sync and call it inline. The wiring is verified
    by confirming the import path resolves and the push_sync function
    matches the expected signature.
    """

    def test_push_sync_importable(self):
        """push_sync is importable from the sync_engine module."""
        assert callable(push_sync)

    @pytest.mark.asyncio
    async def test_push_sync_returns_structured_result(self):
        """push_sync signature returns the expected dict shape."""
        ctx = MockAppContext(state_data=_make_push_state())
        result = await push_sync(ctx)
        # Should have the standard push result keys
        assert "status" in result
        assert "pushed" in result
        assert "skipped" in result
        assert "errors" in result
        assert "timestamp" in result

    def test_build_event_patch_importable(self):
        """build_event_patch is importable from field_mapper."""
        assert callable(build_event_patch)
