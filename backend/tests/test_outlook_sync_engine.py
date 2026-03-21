"""Unit tests for the Outlook Calendar pull sync engine.

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
    / "outlook-calendar"
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
_outlook_client = _load_module(
    "outlook_client", _SERVICES_DIR / "outlook_client.py"
)
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
OutlookAPIError = _outlook_client.OutlookAPIError


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


class MockOutlookClient:
    """Stub for OutlookClient — returns pre-configured delta responses.

    ``delta_responses`` is a list of ``(events, delta_link)`` tuples returned
    in order by get_events_delta. If exhausted, returns ``([], None)``.

    If ``raise_on_delta`` is set to an exception, the first get_events_delta
    call will raise it (simulating expired delta, 410, etc.).
    """

    def __init__(
        self,
        delta_responses: list[tuple[list[dict], str | None]] | None = None,
        raise_on_delta: Exception | None = None,
        patch_responses: list[dict] | None = None,
    ):
        self._delta_responses = list(delta_responses or [])
        self._delta_index = 0
        self._raise_on_delta = raise_on_delta
        self._raised = False
        self._patch_responses = list(patch_responses or [])
        self._patch_index = 0
        self.delta_calls: list[dict] = []
        self.patch_calls: list[dict] = []

    async def get_events_delta(
        self, calendar_id: str, delta_link: str | None = None
    ) -> tuple[list[dict], str | None]:
        self.delta_calls.append({"calendar_id": calendar_id, "delta_link": delta_link})
        if self._raise_on_delta and not self._raised:
            self._raised = True
            raise self._raise_on_delta
        if self._delta_index < len(self._delta_responses):
            resp = self._delta_responses[self._delta_index]
            self._delta_index += 1
            return resp
        return ([], None)

    async def patch_event(
        self, calendar_id: str, event_id: str, data: dict
    ) -> dict:
        self.patch_calls.append({
            "calendar_id": calendar_id,
            "event_id": event_id,
            "data": data,
        })
        if self._patch_index < len(self._patch_responses):
            resp = self._patch_responses[self._patch_index]
            self._patch_index += 1
            return resp
        return {"id": event_id}


class MockExternalHttpClient:
    """Stub for SDK HttpClient (external requests).

    Supports get/post/patch methods and pre-configured responses.
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
    """Mimics the SDK ``AppContext`` with all required client attributes.

    When ``outlook_client`` is provided, the sync engine's internal
    ``OutlookClient(...)`` construction is monkey-patched out so our mock
    is used instead. This works because pull_sync builds the client
    locally — we patch the module's OutlookClient class.
    """

    def __init__(
        self,
        state_data: dict[str, str] | None = None,
        graph_client: MockGraphClient | None = None,
        http_client: MockHttpClient | None = None,
        ext_http_client: MockExternalHttpClient | None = None,
        outlook_client: MockOutlookClient | None = None,
    ):
        self.state = MockStateClient(state_data)
        self.graph = graph_client or MockGraphClient()
        _http = http_client or MockHttpClient()
        self.commands = MockCommandClient(_http)
        self.http = ext_http_client or MockExternalHttpClient()
        self.app_id = "outlook-calendar"
        self._outlook_client = outlook_client


# ===================================================================
# Monkey-patch helper
# ===================================================================

import contextlib


@contextlib.contextmanager
def _patch_outlook_client(ctx: MockAppContext):
    """Replace OutlookClient construction in sync_engine with ctx's mock."""
    if ctx._outlook_client is None:
        yield
        return

    original = _sync_engine.OutlookClient

    class _PatchedClient:
        def __init__(self, **kwargs):
            pass

        def __getattr__(self, name):
            return getattr(ctx._outlook_client, name)

    _sync_engine.OutlookClient = _PatchedClient
    try:
        yield
    finally:
        _sync_engine.OutlookClient = original


# ===================================================================
# Event fixtures
# ===================================================================


def make_event(
    event_id: str = "evt001",
    subject: str = "Team Standup",
    **overrides,
) -> dict:
    """Build a realistic Outlook Calendar event dict."""
    base = {
        "id": event_id,
        "subject": subject,
        "showAs": "busy",
        "webLink": f"https://outlook.live.com/owa/?itemid={event_id}",
        "createdDateTime": "2026-03-17T10:00:00Z",
        "lastModifiedDateTime": "2026-03-18T12:00:00Z",
        "start": {"dateTime": "2026-03-19T09:00:00.0000000", "timeZone": "America/New_York"},
        "end": {"dateTime": "2026-03-19T09:30:00.0000000", "timeZone": "America/New_York"},
        "attendees": [],
        "organizer": {
            "emailAddress": {
                "address": "user@example.com",
                "name": "Test User",
            }
        },
        "body": {"contentType": "html", "content": ""},
        "sensitivity": "normal",
        "importance": "normal",
        "isAllDay": False,
        "isCancelled": False,
    }
    base.update(overrides)
    return base


def make_all_day_event(event_id: str = "allday001", subject: str = "Holiday") -> dict:
    """Build an all-day event."""
    return make_event(
        event_id=event_id,
        subject=subject,
        isAllDay=True,
        start={"dateTime": "2026-03-20T00:00:00.0000000", "timeZone": "UTC"},
        end={"dateTime": "2026-03-21T00:00:00.0000000", "timeZone": "UTC"},
    )


def make_removed_event(event_id: str = "removed001") -> dict:
    """Build a delta-deleted event with @removed key."""
    return {
        "id": event_id,
        "@removed": {"reason": "deleted"},
    }


def _make_connected_state(
    calendars: list[str] | None = None,
    delta_links: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build state dict for a connected account with calendars selected."""
    data: dict[str, str] = {
        "auth_method": "oauth",
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
        "token_expiry": "2099-12-31T23:59:59Z",
        "microsoft_email": "user@example.com",
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
    }
    if calendars is not None:
        data["selected_calendars"] = json.dumps(calendars)
    if delta_links:
        for cal_id, link in delta_links.items():
            data[f"delta_link:{cal_id}"] = link
    return data


# ===================================================================
# Helper to run pull_sync with patched client
# ===================================================================


async def _run_pull_sync(ctx: MockAppContext) -> dict:
    """Run pull_sync with OutlookClient monkey-patched."""
    with _patch_outlook_client(ctx):
        return await pull_sync(ctx)


async def _run_push_sync(ctx: MockAppContext) -> dict:
    """Run push_sync with OutlookClient monkey-patched."""
    with _patch_outlook_client(ctx):
        return await push_sync(ctx)


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
                "externalId": "outlook-evt-1",
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
    async def test_sparql_uses_outlook_provider(self):
        """The SPARQL query must filter by outlook-calendar provider."""
        graph = MockGraphClient()
        await _find_existing_event(graph, "test-slug")
        assert len(graph.queries) == 1
        assert '"outlook-calendar"' in graph.queries[0]


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
        await _submit_commands_batched(http, cmds, "test", "outlook-calendar")
        assert len(http.posts) == 1
        assert len(http.posts[0]["json"]["commands"]) == 5

    @pytest.mark.asyncio
    async def test_multi_batch(self):
        """Commands exceeding BATCH_SIZE should be split."""
        http = MockHttpClient()
        cmds = [{"command": "object.create", "params": {}} for _ in range(BATCH_SIZE + 5)]
        await _submit_commands_batched(http, cmds, "test", "outlook-calendar")
        assert len(http.posts) == 2
        assert len(http.posts[0]["json"]["commands"]) == BATCH_SIZE
        assert len(http.posts[1]["json"]["commands"]) == 5

    @pytest.mark.asyncio
    async def test_empty_commands(self):
        """Empty command list should produce no POST calls."""
        http = MockHttpClient()
        await _submit_commands_batched(http, [], "test", "outlook-calendar")
        assert len(http.posts) == 0


# ===================================================================
# TestPullSync — not connected / no calendars
# ===================================================================


class TestPullSyncNotConnected:
    """Test pull_sync when not authenticated."""

    @pytest.mark.asyncio
    async def test_not_connected(self):
        ctx = MockAppContext(state_data={})
        result = await _run_pull_sync(ctx)
        assert result["status"] == "skipped"
        assert "not connected" in result["reason"]


class TestPullSyncNoCalendars:
    """Test pull_sync with no calendars selected."""

    @pytest.mark.asyncio
    async def test_no_calendars_state_missing(self):
        ctx = MockAppContext(state_data=_make_connected_state())
        result = await _run_pull_sync(ctx)
        assert result["status"] == "ok"
        assert result["created"] == 0
        assert "No calendars" in result.get("message", "")

    @pytest.mark.asyncio
    async def test_empty_calendar_list(self):
        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=[])
        )
        result = await _run_pull_sync(ctx)
        assert result["status"] == "ok"
        assert result["created"] == 0


# ===================================================================
# TestPullSyncNewEvents
# ===================================================================


class TestPullSyncNewEvents:
    """Test pull_sync creating new events."""

    @pytest.mark.asyncio
    async def test_creates_single_event(self):
        """A single new event should produce 1 create command."""
        event = make_event()
        mock_client = MockOutlookClient(
            delta_responses=[([event], "delta-link-1")]
        )
        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

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
        mock_client = MockOutlookClient(
            delta_responses=[(events, "delta-multi")]
        )
        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        assert result["created"] == 3
        assert result["errors"] == []


# ===================================================================
# TestPullSyncExistingEvents
# ===================================================================


class TestPullSyncExistingEvents:
    """Test pull_sync updating existing events."""

    @pytest.mark.asyncio
    async def test_updates_existing_event(self):
        """An event whose slug matches an existing IRI should update."""
        event = make_event(event_id="existing1")
        slug = compute_event_slug("cal-id-1", "existing1")

        mock_client = MockOutlookClient(
            delta_responses=[([event], "delta-upd")]
        )
        graph = MockGraphClient(slug_map={
            slug: {
                "iri": f"https://example.org/data/Event/{slug}",
                "status": "confirmed",
            }
        })

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            graph_client=graph,
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        assert result["updated"] == 1
        assert result["created"] == 0


# ===================================================================
# TestPullSyncMixed
# ===================================================================


class TestPullSyncMixed:
    """Test pull_sync with a mix of new and existing events."""

    @pytest.mark.asyncio
    async def test_mixed_create_and_update(self):
        new_event = make_event(event_id="new1")
        existing_event = make_event(event_id="existing1")
        slug_existing = compute_event_slug("cal-id-1", "existing1")

        mock_client = MockOutlookClient(
            delta_responses=[([new_event, existing_event], "delta-mix")]
        )
        graph = MockGraphClient(slug_map={
            slug_existing: {
                "iri": f"https://example.org/data/Event/{slug_existing}",
            }
        })

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            graph_client=graph,
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        assert result["created"] == 1
        assert result["updated"] == 1


# ===================================================================
# TestPullSyncDeltaLink
# ===================================================================


class TestPullSyncDeltaLink:
    """Test delta link persistence and expired delta (410) handling."""

    @pytest.mark.asyncio
    async def test_delta_link_stored(self):
        """After successful sync, delta link should be saved in state."""
        mock_client = MockOutlookClient(
            delta_responses=[([], "saved-delta-xyz")]
        )
        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            outlook_client=mock_client,
        )
        await _run_pull_sync(ctx)

        stored = await ctx.state.get("delta_link:cal-id-1")
        assert stored == "saved-delta-xyz"

    @pytest.mark.asyncio
    async def test_incremental_sync_uses_delta_link(self):
        """When a delta link exists, it should be passed to get_events_delta."""
        mock_client = MockOutlookClient(
            delta_responses=[([], "new-delta")]
        )
        ctx = MockAppContext(
            state_data=_make_connected_state(
                calendars=["cal-id-1"],
                delta_links={"cal-id-1": "https://graph.microsoft.com/old-delta"},
            ),
            outlook_client=mock_client,
        )
        await _run_pull_sync(ctx)

        assert len(mock_client.delta_calls) == 1
        assert mock_client.delta_calls[0]["delta_link"] == "https://graph.microsoft.com/old-delta"

    @pytest.mark.asyncio
    async def test_expired_delta_410_retries_full_sync(self):
        """On 410 (expired delta), clear link and retry as full sync."""
        mock_client = MockOutlookClient(
            raise_on_delta=OutlookAPIError(
                "Delta link expired", status_code=410
            ),
            delta_responses=[([make_event()], "fresh-delta")],
        )
        ctx = MockAppContext(
            state_data=_make_connected_state(
                calendars=["cal-id-1"],
                delta_links={"cal-id-1": "https://graph.microsoft.com/expired-delta"},
            ),
            outlook_client=mock_client,
        )

        result = await _run_pull_sync(ctx)

        assert result["status"] == "ok"
        assert result["created"] == 1
        # Delta link should be updated to the fresh one
        stored = await ctx.state.get("delta_link:cal-id-1")
        assert stored == "fresh-delta"
        # Two calls: first raised 410, second was full sync
        assert len(mock_client.delta_calls) == 2
        assert mock_client.delta_calls[1]["delta_link"] is None  # full sync

    @pytest.mark.asyncio
    async def test_expired_delta_clears_stored_link(self):
        """On expired delta, the stored link should be cleared before retry."""
        mock_client = MockOutlookClient(
            raise_on_delta=OutlookAPIError(
                "Delta link expired", status_code=410
            ),
            delta_responses=[([], "new-delta-after-clear")],
        )
        ctx = MockAppContext(
            state_data=_make_connected_state(
                calendars=["cal-id-1"],
                delta_links={"cal-id-1": "https://graph.microsoft.com/old"},
            ),
            outlook_client=mock_client,
        )

        await _run_pull_sync(ctx)

        # Verify the stored delta link was updated (not the old one)
        stored = await ctx.state.get("delta_link:cal-id-1")
        assert stored == "new-delta-after-clear"


# ===================================================================
# TestPullSyncRemovedEvents
# ===================================================================


class TestPullSyncRemovedEvents:
    """Test handling of @removed events in delta responses."""

    @pytest.mark.asyncio
    async def test_removed_event_skipped(self):
        """Events with @removed key should not be created."""
        removed = make_removed_event("removed1")
        normal = make_event(event_id="normal1")
        mock_client = MockOutlookClient(
            delta_responses=[([removed, normal], "delta-rm")]
        )

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        # Only the normal event should be created
        assert result["created"] == 1
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_all_removed_events(self):
        """When all events are removed, nothing is created."""
        removed1 = make_removed_event("rm1")
        removed2 = make_removed_event("rm2")
        mock_client = MockOutlookClient(
            delta_responses=[([removed1, removed2], "delta-allrm")]
        )

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_removed_event_not_created_or_updated(self):
        """Removed event should be entirely skipped — no commands generated."""
        removed = make_removed_event("rm-test")
        mock_client = MockOutlookClient(
            delta_responses=[([removed], "delta-rm-only")]
        )

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        # No commands should have been submitted
        bulk_http = ctx.commands._client
        assert len(bulk_http.posts) == 0


# ===================================================================
# TestPullSyncErrorIsolation
# ===================================================================


class TestPullSyncErrorIsolation:
    """Test per-event error isolation."""

    @pytest.mark.asyncio
    async def test_bad_event_doesnt_block_others(self):
        """One event raising an exception should not block the rest."""
        good_event = make_event(event_id="good1")
        # Bad event: missing required fields — will fail somewhere in field mapper
        bad_event = {"id": "bad1"}

        mock_client = MockOutlookClient(
            delta_responses=[([good_event, bad_event], "delta-err")]
        )
        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        # Good event should still be created
        assert result["created"] >= 1
        # The key invariant: no exception propagated

    @pytest.mark.asyncio
    async def test_errors_include_event_id(self):
        """Errors should include the event_id for diagnosis."""

        class FailingGraphClient(MockGraphClient):
            async def query(self, sparql: str) -> dict:
                self.queries.append(sparql)
                if "STRENDS" in sparql:
                    raise RuntimeError("SPARQL timeout")
                return self.default_results

        mock_client = MockOutlookClient(
            delta_responses=[([make_event(event_id="fail-evt")], "delta-fail")]
        )
        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            graph_client=FailingGraphClient(),
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        assert len(result["errors"]) >= 1
        assert result["errors"][0]["event_id"] == "fail-evt"
        assert "SPARQL timeout" in result["errors"][0]["error"]

    @pytest.mark.asyncio
    async def test_last_pull_result_contains_error_detail(self):
        """Diagnostic surface: last_pull_result should contain error details."""

        class FailingGraphClient(MockGraphClient):
            async def query(self, sparql: str) -> dict:
                self.queries.append(sparql)
                if "STRENDS" in sparql:
                    raise RuntimeError("Connection refused")
                return self.default_results

        mock_client = MockOutlookClient(
            delta_responses=[([make_event(event_id="diag-evt")], "delta-d")]
        )
        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            graph_client=FailingGraphClient(),
            outlook_client=mock_client,
        )
        await _run_pull_sync(ctx)

        stored = await ctx.state.get("last_pull_result")
        assert stored is not None
        parsed = json.loads(stored)
        assert len(parsed["errors"]) >= 1
        assert parsed["errors"][0]["event_id"] == "diag-evt"
        assert "Connection refused" in parsed["errors"][0]["error"]


# ===================================================================
# TestPullSyncAttendees
# ===================================================================


class TestPullSyncAttendees:
    """Test attendee and organizer matching (Outlook nested emailAddress structure)."""

    @pytest.mark.asyncio
    async def test_attendees_matched(self):
        """Non-self attendees should trigger person matching."""
        event = make_event(
            event_id="with-attendees",
            attendees=[
                {
                    "emailAddress": {"address": "alice@example.com", "name": "Alice"},
                    "type": "required",
                },
                {
                    "emailAddress": {"address": "bob@example.com", "name": "Bob"},
                    "type": "required",
                },
            ],
            organizer={
                "emailAddress": {"address": "user@example.com", "name": "Test User"}
            },
        )
        mock_client = MockOutlookClient(
            delta_responses=[([event], "delta-att")]
        )

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        assert result["created"] == 1
        # Person matcher should have been called for alice and bob
        assert len(ctx.commands.commands) >= 2

    @pytest.mark.asyncio
    async def test_organizer_matched(self):
        """Non-self organizer should trigger person matching."""
        event = make_event(
            event_id="ext-organizer",
            organizer={
                "emailAddress": {"address": "boss@example.com", "name": "Boss"}
            },
            attendees=[],
        )
        mock_client = MockOutlookClient(
            delta_responses=[([event], "delta-org")]
        )

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        assert result["created"] == 1
        # Person matcher creates the organizer
        assert len(ctx.commands.commands) >= 1

    @pytest.mark.asyncio
    async def test_self_organizer_not_matched(self):
        """Self organizer (same as connected user email) should NOT create a person."""
        event = make_event(
            event_id="self-org",
            organizer={
                "emailAddress": {"address": "user@example.com", "name": "Test User"}
            },
            attendees=[],
        )
        mock_client = MockOutlookClient(
            delta_responses=[([event], "delta-so")]
        )

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        assert result["created"] == 1
        # No person creates — organizer is self
        assert len(ctx.commands.commands) == 0


# ===================================================================
# TestPullSyncMultipleCalendars
# ===================================================================


class TestPullSyncMultipleCalendars:
    """Test pull_sync with multiple calendars."""

    @pytest.mark.asyncio
    async def test_two_calendars(self):
        """Events from two calendars should be processed independently."""
        mock_client = MockOutlookClient(
            delta_responses=[
                ([make_event(event_id="cal1-evt1")], "delta-cal1"),
                ([make_event(event_id="cal2-evt1"), make_event(event_id="cal2-evt2")], "delta-cal2"),
            ]
        )

        ctx = MockAppContext(
            state_data=_make_connected_state(
                calendars=["cal-id-1", "cal-id-2"]
            ),
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        assert result["created"] == 3  # 1 + 2
        # Both delta links stored
        dl1 = await ctx.state.get("delta_link:cal-id-1")
        dl2 = await ctx.state.get("delta_link:cal-id-2")
        assert dl1 == "delta-cal1"
        assert dl2 == "delta-cal2"


# ===================================================================
# TestPullSyncAllDayEvents
# ===================================================================


class TestPullSyncAllDayEvents:
    """Test that all-day events are handled correctly."""

    @pytest.mark.asyncio
    async def test_all_day_event_created(self):
        event = make_all_day_event()
        mock_client = MockOutlookClient(
            delta_responses=[([event], "delta-ad")]
        )

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        assert result["created"] == 1
        assert result["errors"] == []


# ===================================================================
# TestPullSyncDescription
# ===================================================================


class TestPullSyncDescription:
    """Test events with description (body) content."""

    @pytest.mark.asyncio
    async def test_new_event_with_description(self):
        """New event with description should defer body.set to phase 2."""
        event = make_event(
            event_id="desc1",
            body={"contentType": "html", "content": "<p>Meeting agenda</p>"},
        )

        mock_client = MockOutlookClient(
            delta_responses=[([event], "delta-desc")]
        )
        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        assert result["created"] == 1
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_existing_event_with_description(self):
        """Existing event with description should include body.set in update."""
        event = make_event(
            event_id="desc-upd",
            body={"contentType": "html", "content": "<p>Updated notes</p>"},
        )
        slug = compute_event_slug("cal-id-1", "desc-upd")

        mock_client = MockOutlookClient(
            delta_responses=[([event], "delta-du")]
        )
        graph = MockGraphClient(slug_map={
            slug: {"iri": f"https://example.org/data/Event/{slug}"}
        })

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            graph_client=graph,
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        assert result["updated"] == 1

        # Check that body.set was among the posted commands
        bulk_http = ctx.commands._client
        assert len(bulk_http.posts) >= 1
        all_cmds = []
        for post in bulk_http.posts:
            all_cmds.extend(post["json"].get("commands", []))
        body_cmds = [c for c in all_cmds if c["command"] == "body.set"]
        assert len(body_cmds) >= 1


# ===================================================================
# TestPullSyncLastSyncAt
# ===================================================================


class TestPullSyncLastSyncAt:
    """Test that last_sync_at and last_pull_result are stored."""

    @pytest.mark.asyncio
    async def test_last_sync_at_stored(self):
        mock_client = MockOutlookClient(delta_responses=[([], "delta-t")])
        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            outlook_client=mock_client,
        )
        await _run_pull_sync(ctx)

        last_sync = await ctx.state.get("last_sync_at")
        assert last_sync is not None

    @pytest.mark.asyncio
    async def test_last_pull_result_stored(self):
        mock_client = MockOutlookClient(delta_responses=[([], "delta-t2")])
        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        stored = await ctx.state.get("last_pull_result")
        assert stored is not None
        parsed = json.loads(stored)
        assert parsed["status"] == "ok"

    @pytest.mark.asyncio
    async def test_last_pull_result_includes_timestamp(self):
        mock_client = MockOutlookClient(delta_responses=[([], "delta-ts")])
        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            outlook_client=mock_client,
        )
        await _run_pull_sync(ctx)

        stored = await ctx.state.get("last_pull_result")
        parsed = json.loads(stored)
        assert "timestamp" in parsed


# ===================================================================
# TestPullSyncEmptyCalendar
# ===================================================================


class TestPullSyncEmptyCalendar:
    """Test pull_sync with a calendar that has no events."""

    @pytest.mark.asyncio
    async def test_empty_calendar(self):
        mock_client = MockOutlookClient(delta_responses=[([], "empty-delta")])
        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        assert result["status"] == "ok"
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["errors"] == []


# ===================================================================
# TestPullSyncCalendarName
# ===================================================================


class TestPullSyncCalendarName:
    """Test that calendar_id is passed through as calendar name."""

    @pytest.mark.asyncio
    async def test_calendar_name_in_event(self):
        """The calendar ID is used as calendar_name in properties."""
        event = make_event(event_id="calname-evt")
        mock_client = MockOutlookClient(
            delta_responses=[([event], "delta-cn")]
        )
        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["my-work-calendar"]),
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        assert result["created"] == 1
        # The field mapper receives the calendar name — we verify
        # by checking the commands submitted include calendarName property
        bulk_http = ctx.commands._client
        all_cmds = []
        for post in bulk_http.posts:
            all_cmds.extend(post["json"].get("commands", []))
        create_cmds = [c for c in all_cmds if c["command"] == "object.create"]
        assert len(create_cmds) == 1
        props = create_cmds[0]["params"]["properties"]
        assert f"{BPKM}calendarName" in props
        assert props[f"{BPKM}calendarName"] == "my-work-calendar"


# ===================================================================
# TestLoopPrevention — pull_sync skips recently pushed events
# ===================================================================


class TestLoopPrevention:
    """Test that pull_sync skips events where lastModifiedDateTime <= lastSyncedAt."""

    @pytest.mark.asyncio
    async def test_event_with_updated_lte_last_synced_skipped(self):
        """An event whose lastModifiedDateTime <= lastSyncedAt should be skipped."""
        event = make_event(
            event_id="loop1",
            lastModifiedDateTime="2026-03-18T12:00:00Z",  # same as lastSyncedAt
        )
        slug = compute_event_slug("cal-id-1", "loop1")

        mock_client = MockOutlookClient(
            delta_responses=[([event], "delta-loop")]
        )
        graph = MockGraphClient(slug_map={
            slug: {
                "iri": f"https://example.org/data/Event/{slug}",
                "status": "confirmed",
                "lastSyncedAt": "2026-03-18T12:00:00Z",
            }
        })

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            graph_client=graph,
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        assert result["updated"] == 0
        assert result["unchanged"] == 1

    @pytest.mark.asyncio
    async def test_event_with_updated_gt_last_synced_processed(self):
        """An event whose lastModifiedDateTime > lastSyncedAt should be updated."""
        event = make_event(
            event_id="loop2",
            lastModifiedDateTime="2026-03-19T14:00:00Z",
        )
        slug = compute_event_slug("cal-id-1", "loop2")

        mock_client = MockOutlookClient(
            delta_responses=[([event], "delta-loop2")]
        )
        graph = MockGraphClient(slug_map={
            slug: {
                "iri": f"https://example.org/data/Event/{slug}",
                "status": "confirmed",
                "lastSyncedAt": "2026-03-18T10:00:00Z",
            }
        })

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            graph_client=graph,
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        assert result["updated"] == 1
        assert result["unchanged"] == 0

    @pytest.mark.asyncio
    async def test_event_with_no_last_synced_processed(self):
        """An existing event with no lastSyncedAt should be updated."""
        event = make_event(event_id="loop3")
        slug = compute_event_slug("cal-id-1", "loop3")

        mock_client = MockOutlookClient(
            delta_responses=[([event], "delta-loop3")]
        )
        graph = MockGraphClient(slug_map={
            slug: {
                "iri": f"https://example.org/data/Event/{slug}",
                "status": "confirmed",
                # no lastSyncedAt
            }
        })

        ctx = MockAppContext(
            state_data=_make_connected_state(calendars=["cal-id-1"]),
            graph_client=graph,
            outlook_client=mock_client,
        )
        result = await _run_pull_sync(ctx)

        assert result["updated"] == 1


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
                "externalId": "outlook-evt-1",
                "calendarName": "cal-id-1",
                "responseStatus": "accepted",
                "lastSyncedAt": "2026-03-17T10:00:00Z",
            }
        ])
        result = await _find_changed_events(graph)
        assert len(result) == 1
        assert result[0]["iri"] == "https://example.org/data/Event/evt1"
        assert result[0]["externalId"] == "outlook-evt-1"

    @pytest.mark.asyncio
    async def test_sparql_uses_outlook_provider(self):
        """The SPARQL query must filter by outlook-calendar provider."""
        graph = MockGraphClient(changed_events=[])
        await _find_changed_events(graph)
        assert len(graph.queries) == 1
        assert '"outlook-calendar"' in graph.queries[0]

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
                "externalId": "oa",
                "calendarName": "cal-id-1",
                "responseStatus": "accepted",
            },
            {
                "iri": "https://example.org/data/Event/b",
                "externalId": "ob",
                "calendarName": "cal-id-1",
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
    data["microsoft_email"] = "user@example.com"
    data.update(extra)
    return data


class TestPushSync:
    """Test push_sync pipeline."""

    @pytest.mark.asyncio
    async def test_not_connected_skips(self):
        ctx = MockAppContext(state_data={})
        result = await _run_push_sync(ctx)
        assert result["status"] == "skipped"
        assert "not connected" in result.get("reason", "")

    @pytest.mark.asyncio
    async def test_pull_only_skips(self):
        ctx = MockAppContext(state_data=_make_push_state(sync_direction="pull-only"))
        result = await _run_push_sync(ctx)
        assert result["status"] == "skipped"
        assert "pull-only" in result.get("reason", "")

    @pytest.mark.asyncio
    async def test_no_changed_events(self):
        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=MockGraphClient(changed_events=[]),
        )
        result = await _run_push_sync(ctx)
        assert result["status"] == "ok"
        assert result["pushed"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_successful_rsvp_push(self):
        """Push an RSVP change and verify PATCH was sent."""
        mock_client = MockOutlookClient(
            patch_responses=[{"id": "outlook-evt-1", "status": "confirmed"}]
        )
        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt1",
                "externalId": "outlook-evt-1",
                "calendarName": "cal-id-1",
                "responseStatus": "declined",
            }
        ])

        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=graph,
            outlook_client=mock_client,
        )
        result = await _run_push_sync(ctx)

        assert result["status"] == "ok"
        assert result["pushed"] == 1
        assert result["errors"] == []

        # Verify PATCH was sent via mock client
        assert len(mock_client.patch_calls) == 1
        assert mock_client.patch_calls[0]["calendar_id"] == "cal-id-1"
        assert mock_client.patch_calls[0]["event_id"] == "outlook-evt-1"

    @pytest.mark.asyncio
    async def test_last_synced_at_updated_after_push(self):
        """After a successful push, lastSyncedAt should be updated."""
        mock_client = MockOutlookClient(
            patch_responses=[{"id": "outlook-evt-1"}]
        )
        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt1",
                "externalId": "outlook-evt-1",
                "calendarName": "cal-id-1",
                "responseStatus": "accepted",
            }
        ])

        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=graph,
            outlook_client=mock_client,
        )
        await _run_push_sync(ctx)

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
        # First PATCH raises, second succeeds
        class FailThenSucceedClient(MockOutlookClient):
            def __init__(self):
                super().__init__()
                self._call_count = 0

            async def patch_event(self, calendar_id, event_id, data):
                self._call_count += 1
                if self._call_count == 1:
                    raise OutlookAPIError("Server error", status_code=500)
                return {"id": event_id}

        mock_client = FailThenSucceedClient()
        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt1",
                "externalId": "outlook-evt-1",
                "calendarName": "cal-id-1",
                "responseStatus": "declined",
            },
            {
                "iri": "https://example.org/data/Event/evt2",
                "externalId": "outlook-evt-2",
                "calendarName": "cal-id-1",
                "responseStatus": "accepted",
            },
        ])

        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=graph,
            outlook_client=mock_client,
        )
        result = await _run_push_sync(ctx)

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
        await _run_push_sync(ctx)

        stored = await ctx.state.get("last_push_result")
        assert stored is not None
        parsed = json.loads(stored)
        assert parsed["status"] == "ok"
        assert "timestamp" in parsed

    @pytest.mark.asyncio
    async def test_all_errors_status(self):
        """When all events error, status is 'error'."""

        class AlwaysFailClient(MockOutlookClient):
            async def patch_event(self, calendar_id, event_id, data):
                raise OutlookAPIError("Server error", status_code=500)

        mock_client = AlwaysFailClient()
        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/e1",
                "externalId": "e1",
                "calendarName": "cal-id-1",
                "responseStatus": "declined",
            },
        ])

        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=graph,
            outlook_client=mock_client,
        )
        result = await _run_push_sync(ctx)

        assert result["status"] == "error"
        assert result["pushed"] == 0
        assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_skips_event_without_response_status(self):
        """Events with no responseStatus should be skipped (no PATCH)."""
        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt1",
                "externalId": "outlook-evt-1",
                "calendarName": "cal-id-1",
                "responseStatus": None,
            },
        ])

        mock_client = MockOutlookClient()
        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=graph,
            outlook_client=mock_client,
        )
        result = await _run_push_sync(ctx)

        assert result["pushed"] == 0
        assert result["skipped"] == 1
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_missing_calendar_name_errors(self):
        """Events with no calendarName should produce an error."""
        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt1",
                "externalId": "outlook-evt-1",
                "calendarName": None,
                "responseStatus": "accepted",
            },
        ])

        mock_client = MockOutlookClient()
        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=graph,
            outlook_client=mock_client,
        )
        result = await _run_push_sync(ctx)

        assert result["pushed"] == 0
        assert len(result["errors"]) == 1
        assert "calendarName" in result["errors"][0]["error"]


# ===================================================================
# TestPushSyncWiring
# ===================================================================


class TestPushSyncWiring:
    """Test push_sync returns correct structure."""

    def test_push_sync_importable(self):
        """push_sync is importable from the sync_engine module."""
        assert callable(push_sync)

    @pytest.mark.asyncio
    async def test_push_sync_returns_structured_result(self):
        """push_sync signature returns the expected dict shape."""
        ctx = MockAppContext(state_data=_make_push_state())
        result = await _run_push_sync(ctx)
        assert "status" in result
        assert "pushed" in result
        assert "skipped" in result
        assert "errors" in result
        assert "timestamp" in result


# ===================================================================
# Route-handler tests (app.py wiring layer)
# ===================================================================


class _MockRequest:
    """Minimal Starlette Request mock for route handler tests."""

    class _App:
        class _State:
            ctx = None
        state = _State()

    def __init__(self, ctx, form_data: dict | None = None):
        self.app = self._App()
        self.app.state.ctx = ctx
        self._form_data = form_data or {}

    async def form(self):
        return _MockFormData(self._form_data)


class _MockFormData(dict):
    """dict subclass with .getlist() matching Starlette's FormData."""
    def getlist(self, key):
        val = super().get(key)
        if val is None:
            return []
        if isinstance(val, list):
            return val
        return [val]


def _load_app_module():
    """Load outlook-calendar app module via importlib.

    Stubs ``sempkm_app_sdk`` and ``starlette`` so the module loads
    without the full SDK or web framework installed.
    """
    from types import ModuleType

    class _StubApp:
        def __init__(self, name):
            self.name = name

        def route(self, path, methods=None):
            def decorator(fn):
                return fn
            return decorator

        def task(self, name):
            def decorator(fn):
                return fn
            return decorator

        def on_startup(self, fn):
            return fn

        def on_shutdown(self, fn):
            return fn

    # Stub sempkm_app_sdk if not already available
    if "sempkm_app_sdk" not in sys.modules:
        try:
            import sempkm_app_sdk  # noqa: F401
        except ImportError:
            sdk_mock = ModuleType("sempkm_app_sdk")
            sdk_mock.App = _StubApp
            sdk_mock.AppContext = type("AppContext", (), {})
            sys.modules["sempkm_app_sdk"] = sdk_mock

    # Stub starlette modules if not available
    for mod_name in ["starlette", "starlette.requests", "starlette.responses"]:
        if mod_name not in sys.modules:
            sm = ModuleType(mod_name)
            if mod_name == "starlette.requests":
                sm.Request = type("Request", (), {})
            elif mod_name == "starlette.responses":
                class _HTMLResponse:
                    def __init__(self, body, **kw):
                        self.body = body
                        self.headers = {}
                sm.HTMLResponse = _HTMLResponse

                class _RedirectResponse:
                    def __init__(self, url, status_code=302, **kw):
                        self.url = url
                        self.status_code = status_code
                        self.headers = {}
                sm.RedirectResponse = _RedirectResponse
            sys.modules[mod_name] = sm

    # Wire service modules so app.py's `from services.X import ...` resolves
    sys.modules["services.sync_engine"] = _sync_engine
    sys.modules["services.outlook_client"] = _outlook_client
    sys.modules["services.auth"] = _auth

    app_path = (
        Path(__file__).resolve().parent.parent.parent
        / "apps"
        / "outlook-calendar"
        / "app.py"
    )
    spec = importlib.util.spec_from_file_location("outlook_calendar_app_module", app_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Load once at module level
_app_module = _load_app_module()
_render_connect_status = _app_module._render_connect_status


class _RenderableAppContext(MockAppContext):
    """MockAppContext extended with render_template support for route tests."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rendered: list[tuple[str, dict]] = []

    def render_template(self, template_name: str, **kwargs) -> str:
        self._rendered.append((template_name, kwargs))
        return f"<rendered:{template_name}>"


def _make_route_connected_state(**extra) -> dict[str, str]:
    """Build state dict for a connected account suitable for route tests."""
    data = {
        "auth_method": "oauth",
        "microsoft_email": "test@outlook.com",
        "access_token": "eyJ0test",
        "client_id": "test-client-id",
        "client_secret": "test-secret",
    }
    data.update(extra)
    return data


class _MockCalendarClient:
    """Stub returned by monkey-patched _make_client_with_creds."""

    async def get_calendar_list(self):
        return [
            {"id": "cal1", "name": "Calendar", "isDefaultCalendar": True, "canEdit": True},
        ]


@contextlib.contextmanager
def _patch_make_client():
    """Monkey-patch _make_client_with_creds on the app module to return a mock client."""
    original = _app_module._make_client_with_creds

    async def _fake_make_client(ctx):
        return _MockCalendarClient()

    _app_module._make_client_with_creds = _fake_make_client
    try:
        yield
    finally:
        _app_module._make_client_with_creds = original


# ===================================================================
# TestRenderConnectStatus
# ===================================================================


class TestRenderConnectStatus:
    """Verify _render_connect_status reads sync config from ctx.state."""

    @pytest.mark.asyncio
    async def test_passes_sync_direction_to_template(self):
        """sync_direction from state is passed to template kwargs."""
        ctx = _RenderableAppContext(
            state_data={
                **_make_route_connected_state(),
                "sync_direction": "bidirectional",
            },
        )
        with _patch_make_client():
            await _render_connect_status(ctx)
        _, kwargs = ctx._rendered[-1]
        assert kwargs["sync_direction"] == "bidirectional"

    @pytest.mark.asyncio
    async def test_passes_poll_interval_to_template(self):
        """poll_interval from state is passed to template kwargs."""
        ctx = _RenderableAppContext(
            state_data={
                **_make_route_connected_state(),
                "poll_interval": "30m",
            },
        )
        with _patch_make_client():
            await _render_connect_status(ctx)
        _, kwargs = ctx._rendered[-1]
        assert kwargs["poll_interval"] == "30m"

    @pytest.mark.asyncio
    async def test_passes_last_push_result_to_template(self):
        """last_push_result parsed from state JSON is passed to template."""
        push_result = {
            "status": "ok", "pushed": 3, "skipped": 1, "errors": [],
            "timestamp": "2026-03-18T12:00:00Z",
        }
        ctx = _RenderableAppContext(
            state_data={
                **_make_route_connected_state(),
                "last_push_result": json.dumps(push_result),
            },
        )
        with _patch_make_client():
            await _render_connect_status(ctx)
        _, kwargs = ctx._rendered[-1]
        assert kwargs["last_push_result"]["status"] == "ok"
        assert kwargs["last_push_result"]["pushed"] == 3

    @pytest.mark.asyncio
    async def test_defaults_when_no_settings(self):
        """sync_direction defaults to pull-only, poll_interval to 15m, last_push_result to None."""
        ctx = _RenderableAppContext(
            state_data=_make_route_connected_state(),
        )
        with _patch_make_client():
            await _render_connect_status(ctx)
        _, kwargs = ctx._rendered[-1]
        assert kwargs["sync_direction"] == "pull-only"
        assert kwargs["poll_interval"] == "15m"
        assert kwargs["last_push_result"] is None

    @pytest.mark.asyncio
    async def test_passes_existing_pull_result(self):
        """last_pull_result is passed alongside push fields."""
        pull_result = {
            "status": "success", "created": 5, "updated": 2, "skipped": 0,
            "errors": 0, "duration_ms": 100, "timestamp": "2026-03-18T10:00:00Z",
        }
        ctx = _RenderableAppContext(
            state_data={
                **_make_route_connected_state(),
                "last_pull_result": json.dumps(pull_result),
            },
        )
        with _patch_make_client():
            await _render_connect_status(ctx)
        _, kwargs = ctx._rendered[-1]
        assert kwargs["last_pull_result"]["status"] == "success"
        assert kwargs["last_pull_result"]["created"] == 5


# ===================================================================
# TestSyncNowBidirectional
# ===================================================================


class TestSyncNowBidirectional:
    """Verify sync_now calls push_sync when direction is bidirectional."""

    @pytest.mark.asyncio
    async def test_push_called_when_bidirectional(self):
        """push_sync is invoked after pull_sync when sync_direction=bidirectional."""
        from unittest.mock import AsyncMock as AM

        ctx = _RenderableAppContext(
            state_data={
                **_make_route_connected_state(),
                "sync_direction": "bidirectional",
            },
        )
        req = _MockRequest(ctx)

        pull_result = {"status": "success", "created": 1, "updated": 0}
        push_result = {"status": "ok", "pushed": 2, "skipped": 0, "errors": [], "timestamp": "now"}

        original_pull = _sync_engine.pull_sync
        original_push = _sync_engine.push_sync
        _sync_engine.pull_sync = AM(return_value=pull_result)
        _sync_engine.push_sync = AM(return_value=push_result)
        try:
            with _patch_make_client():
                await _app_module.sync_now(req)
            _sync_engine.pull_sync.assert_called_once()
            _sync_engine.push_sync.assert_called_once()
        finally:
            _sync_engine.pull_sync = original_pull
            _sync_engine.push_sync = original_push

        # Verify push result stored in state
        raw = await ctx.state.get("last_push_result")
        assert raw is not None
        stored = json.loads(raw)
        assert stored["status"] == "ok"

    @pytest.mark.asyncio
    async def test_last_sync_at_updated_after_both(self):
        """last_sync_at is set after both pull and push complete."""
        from unittest.mock import AsyncMock as AM

        ctx = _RenderableAppContext(
            state_data={
                **_make_route_connected_state(),
                "sync_direction": "bidirectional",
            },
        )
        req = _MockRequest(ctx)

        original_pull = _sync_engine.pull_sync
        original_push = _sync_engine.push_sync
        _sync_engine.pull_sync = AM(return_value={"status": "success"})
        _sync_engine.push_sync = AM(return_value={"status": "ok"})
        try:
            with _patch_make_client():
                await _app_module.sync_now(req)
        finally:
            _sync_engine.pull_sync = original_pull
            _sync_engine.push_sync = original_push

        last_sync = await ctx.state.get("last_sync_at")
        assert last_sync is not None
        assert "T" in last_sync

    @pytest.mark.asyncio
    async def test_push_error_isolated(self):
        """Push failure doesn't prevent last_sync_at from being set; error is recorded."""
        from unittest.mock import AsyncMock as AM

        ctx = _RenderableAppContext(
            state_data={
                **_make_route_connected_state(),
                "sync_direction": "bidirectional",
            },
        )
        req = _MockRequest(ctx)

        original_pull = _sync_engine.pull_sync
        original_push = _sync_engine.push_sync
        _sync_engine.pull_sync = AM(return_value={"status": "success"})
        _sync_engine.push_sync = AM(side_effect=Exception("push boom"))
        try:
            with _patch_make_client():
                await _app_module.sync_now(req)
        finally:
            _sync_engine.pull_sync = original_pull
            _sync_engine.push_sync = original_push

        # last_sync_at should still be set
        last_sync = await ctx.state.get("last_sync_at")
        assert last_sync is not None
        # Error result should be stored with diagnostic detail
        raw = await ctx.state.get("last_push_result")
        stored = json.loads(raw)
        assert stored["status"] == "error"
        assert "push boom" in stored["message"]


# ===================================================================
# TestSyncNowPullOnly
# ===================================================================


class TestSyncNowPullOnly:
    """Verify sync_now does NOT call push_sync when direction is pull-only."""

    @pytest.mark.asyncio
    async def test_push_not_called_when_pull_only(self):
        """push_sync is not invoked when sync_direction=pull-only."""
        from unittest.mock import AsyncMock as AM

        ctx = _RenderableAppContext(
            state_data={
                **_make_route_connected_state(),
                "sync_direction": "pull-only",
            },
        )
        req = _MockRequest(ctx)

        original_pull = _sync_engine.pull_sync
        original_push = _sync_engine.push_sync
        mock_push = AM()
        _sync_engine.pull_sync = AM(return_value={"status": "success"})
        _sync_engine.push_sync = mock_push
        try:
            with _patch_make_client():
                await _app_module.sync_now(req)
            _sync_engine.pull_sync.assert_called_once()
            mock_push.assert_not_called()
        finally:
            _sync_engine.pull_sync = original_pull
            _sync_engine.push_sync = original_push

    @pytest.mark.asyncio
    async def test_push_not_called_when_no_direction_set(self):
        """push_sync is not invoked when sync_direction is absent (defaults to pull-only)."""
        from unittest.mock import AsyncMock as AM

        ctx = _RenderableAppContext(
            state_data=_make_route_connected_state(),
            # No sync_direction in state
        )
        req = _MockRequest(ctx)

        original_pull = _sync_engine.pull_sync
        original_push = _sync_engine.push_sync
        mock_push = AM()
        _sync_engine.pull_sync = AM(return_value={"status": "success"})
        _sync_engine.push_sync = mock_push
        try:
            with _patch_make_client():
                await _app_module.sync_now(req)
            _sync_engine.pull_sync.assert_called_once()
            mock_push.assert_not_called()
        finally:
            _sync_engine.pull_sync = original_pull
            _sync_engine.push_sync = original_push


# ===================================================================
# TestPushChangesHandler
# ===================================================================


class TestPushChangesHandler:
    """Verify the push-changes task handler calls push_sync."""

    @pytest.mark.asyncio
    async def test_calls_push_sync(self):
        """push_changes task handler invokes push_sync and returns result."""
        from unittest.mock import AsyncMock as AM

        ctx = _RenderableAppContext(
            state_data=_make_route_connected_state(),
        )

        push_result = {"status": "ok", "pushed": 1, "skipped": 0, "errors": [], "timestamp": "now"}
        original_push = _sync_engine.push_sync
        _sync_engine.push_sync = AM(return_value=push_result)
        try:
            result = await _app_module.push_changes(ctx)
        finally:
            _sync_engine.push_sync = original_push
        assert result["status"] == "ok"
        assert result["pushed"] == 1

        # Verify result stored in state
        raw = await ctx.state.get("last_push_result")
        assert raw is not None
        stored = json.loads(raw)
        assert stored["status"] == "ok"

    @pytest.mark.asyncio
    async def test_error_returns_error_dict(self):
        """push_changes returns error dict when push_sync raises."""
        from unittest.mock import AsyncMock as AM

        ctx = _RenderableAppContext(
            state_data=_make_route_connected_state(),
        )

        original_push = _sync_engine.push_sync
        _sync_engine.push_sync = AM(side_effect=Exception("kaboom"))
        try:
            result = await _app_module.push_changes(ctx)
        finally:
            _sync_engine.push_sync = original_push
        assert result["status"] == "error"
        assert "kaboom" in result["message"]

        # Error stored in state for diagnostic visibility
        raw = await ctx.state.get("last_push_result")
        stored = json.loads(raw)
        assert stored["status"] == "error"


# ===================================================================
# TestSyncConfigRoute
# ===================================================================


class TestSyncConfigRoute:
    """Verify sync-config route saves settings to ctx.state."""

    @pytest.mark.asyncio
    async def test_saves_sync_direction(self):
        """sync-config saves sync_direction and poll_interval to state."""
        ctx = _RenderableAppContext(
            state_data=_make_route_connected_state(),
        )
        req = _MockRequest(ctx, form_data={
            "sync_direction": "bidirectional",
            "poll_interval": "30m",
        })

        with _patch_make_client():
            await _app_module.save_sync_config(req)

        assert await ctx.state.get("sync_direction") == "bidirectional"
        assert await ctx.state.get("poll_interval") == "30m"

    @pytest.mark.asyncio
    async def test_defaults_on_missing_form_data(self):
        """sync-config defaults sync_direction to pull-only and poll_interval to 15m."""
        ctx = _RenderableAppContext(
            state_data=_make_route_connected_state(),
        )
        req = _MockRequest(ctx, form_data={})

        with _patch_make_client():
            await _app_module.save_sync_config(req)

        assert await ctx.state.get("sync_direction") == "pull-only"
        assert await ctx.state.get("poll_interval") == "15m"

    @pytest.mark.asyncio
    async def test_returns_html_response(self):
        """sync-config returns an HTMLResponse (re-renders connect_status)."""
        ctx = _RenderableAppContext(
            state_data=_make_route_connected_state(),
        )
        req = _MockRequest(ctx, form_data={
            "sync_direction": "pull-only",
            "poll_interval": "5m",
        })

        with _patch_make_client():
            await _app_module.save_sync_config(req)

        assert len(ctx._rendered) >= 1
        assert ctx._rendered[-1][0] == "connect_status.html"
