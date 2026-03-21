"""Unit tests for the CalDAV pull sync engine.

Loads app modules from the apps directory via importlib so the app does
not need to be installed as a package.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

import icalendar
import pytest

# ---------------------------------------------------------------------------
# Load app modules from apps directory (dependency order)
# ---------------------------------------------------------------------------

_SERVICES_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "caldav-calendar"
    / "services"
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_caldav_client_mod = _load_module("caldav_client", _SERVICES_DIR / "caldav_client.py")
_auth_mod = _load_module("auth", _SERVICES_DIR / "auth.py")
_field_mapper = _load_module("field_mapper", _SERVICES_DIR / "field_mapper.py")
_person_matcher_mod = _load_module(
    "person_matcher", _SERVICES_DIR / "person_matcher.py"
)
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
modify_vevent_partstat = _field_mapper.modify_vevent_partstat
CalDAVError = _caldav_client_mod.CalDAVError
CalDAVConflictError = _caldav_client_mod.CalDAVConflictError
_extract_sync_token = _caldav_client_mod._extract_sync_token


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

    ``slug_map``: slug → dict with iri/status/externalId/lastSyncedAt.
    ``email_to_iri``: email → Person IRI for person-matcher queries.
    ``changed_events``: list of dicts for _find_changed_events queries.
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
        self.changed_events = changed_events
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
        # Check _find_changed_events pattern (has responseStatus, no STRENDS)
        elif "responseStatus" in sparql and "STRENDS" not in sparql and self.changed_events is not None:
            bindings = []
            for evt in self.changed_events:
                binding = {
                    "event": {"type": "uri", "value": evt["iri"]},
                    "extId": {"type": "literal", "value": evt["externalId"]},
                }
                if evt.get("externalUrl"):
                    binding["extUrl"] = {"type": "literal", "value": evt["externalUrl"]}
                if evt.get("calendarName"):
                    binding["calName"] = {"type": "literal", "value": evt["calendarName"]}
                if evt.get("responseStatus"):
                    binding["responseStatus"] = {"type": "literal", "value": evt["responseStatus"]}
                if evt.get("lastSyncedAt"):
                    binding["lastSynced"] = {"type": "literal", "value": evt["lastSyncedAt"]}
                bindings.append(binding)
            return {"results": {"bindings": bindings}}
        # Check person-matcher email queries
        if "foaf" in sparql.lower() or "crm" in sparql.lower():
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
                 headers: dict | None = None, text: str | None = None):
        self.status_code = status_code
        self._data = data if data is not None else {}
        self.headers = headers or {}
        if text is not None:
            self.text = text
        else:
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


class PhaseAwareGraphClient(MockGraphClient):
    """Graph client that returns empty for the first N slug lookups, then found.

    Simulates the two-phase pattern: event doesn't exist during processing
    (phase 1), but is discoverable after object.create (phase 2).
    """

    def __init__(
        self,
        slug_map: dict[str, str | dict] | None = None,
        email_to_iri: dict[str, str] | None = None,
        phase1_lookups: int = 1,
    ):
        super().__init__(slug_map=slug_map, email_to_iri=email_to_iri)
        self._phase1_lookups = phase1_lookups
        self._slug_lookup_count: dict[str, int] = {}

    async def query(self, sparql: str) -> dict:
        self.queries.append(sparql)
        # For slug-based lookups, track call count per slug
        if "STRENDS" in sparql:
            for slug, info in self.slug_map.items():
                if slug in sparql:
                    self._slug_lookup_count[slug] = self._slug_lookup_count.get(slug, 0) + 1
                    if self._slug_lookup_count[slug] <= self._phase1_lookups:
                        # Phase 1: not found yet
                        return {"results": {"bindings": []}}
                    # Phase 2: found
                    if isinstance(info, str):
                        info = {"iri": info}
                    binding: dict = {
                        "event": {"type": "uri", "value": info["iri"]},
                    }
                    if info.get("status"):
                        binding["status"] = {"type": "literal", "value": info["status"]}
                    if info.get("externalId"):
                        binding["extId"] = {"type": "literal", "value": info["externalId"]}
                    if info.get("lastSyncedAt"):
                        binding["lastSynced"] = {"type": "literal", "value": info["lastSyncedAt"]}
                    return {"results": {"bindings": [binding]}}
        # Person-matcher email queries
        if "foaf" in sparql.lower() or "crm" in sparql.lower():
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


# ===================================================================


class MockCalDAVHttpClient:
    """Stub for SDK HttpClient (external CalDAV requests).

    Supports request() for PROPFIND/REPORT and captures all calls.
    Responses can be pre-configured.
    """

    def __init__(self, responses: list[MockResponse] | None = None):
        self.requests: list[dict] = []
        self._responses = list(responses or [])
        self._index = 0

    async def request(self, method: str, url: str, **kwargs) -> MockResponse:
        self.requests.append({"method": method, "url": url, **kwargs})
        return self._next_response()

    async def get(self, url: str, **kwargs) -> MockResponse:
        self.requests.append({"method": "GET", "url": url, **kwargs})
        return self._next_response()

    async def post(self, url: str, **kwargs) -> MockResponse:
        self.requests.append({"method": "POST", "url": url, **kwargs})
        return self._next_response()

    async def put(self, url: str, **kwargs) -> MockResponse:
        self.requests.append({"method": "PUT", "url": url, **kwargs})
        return self._next_response()

    async def delete(self, url: str, **kwargs) -> MockResponse:
        self.requests.append({"method": "DELETE", "url": url, **kwargs})
        return self._next_response()

    def _next_response(self) -> MockResponse:
        if self._index < len(self._responses):
            resp = self._responses[self._index]
            self._index += 1
            return resp
        return MockResponse(200, {})


class MockAppContext:
    """Mimics the SDK ``AppContext`` with all required client attributes."""

    def __init__(
        self,
        state_data: dict[str, str] | None = None,
        graph_client: MockGraphClient | None = None,
        http_client: MockHttpClient | None = None,
        ext_http_client: MockCalDAVHttpClient | None = None,
    ):
        self.state = MockStateClient(state_data)
        self.graph = graph_client or MockGraphClient()
        _http = http_client or MockHttpClient()
        self.commands = MockCommandClient(_http)
        self.http = ext_http_client or MockCalDAVHttpClient()
        self.app_id = "caldav-calendar"


# ===================================================================
# ICS helpers
# ===================================================================


def _build_ics(
    uid: str = "evt-001@example.com",
    summary: str = "Team Meeting",
    dtstart: str = "20260319T090000Z",
    dtend: str = "20260319T100000Z",
    description: str | None = None,
    last_modified: str | None = "20260318T120000Z",
    attendees: list[dict] | None = None,
    organizer: dict | None = None,
    status: str | None = None,
    location: str | None = None,
) -> str:
    """Build a minimal VCALENDAR/VEVENT iCalendar string for testing."""
    cal = icalendar.Calendar()
    cal.add("prodid", "-//Test//Test//EN")
    cal.add("version", "2.0")

    event = icalendar.Event()
    event.add("uid", uid)
    event.add("summary", summary)
    event.add("dtstart", datetime.strptime(dtstart, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc))
    event.add("dtend", datetime.strptime(dtend, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc))

    if last_modified:
        event.add("last-modified", datetime.strptime(last_modified, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc))

    if description:
        event.add("description", description)

    if status:
        event.add("status", status)

    if location:
        event.add("location", location)

    if attendees:
        for att in attendees:
            attendee = icalendar.vCalAddress(f"mailto:{att['email']}")
            if att.get("name"):
                attendee.params["CN"] = att["name"]
            if att.get("partstat"):
                attendee.params["PARTSTAT"] = att["partstat"]
            event.add("attendee", attendee)

    if organizer:
        org = icalendar.vCalAddress(f"mailto:{organizer['email']}")
        if organizer.get("name"):
            org.params["CN"] = organizer["name"]
        event.add("organizer", org)

    cal.add_component(event)
    return cal.to_ical().decode("utf-8")


def _build_multistatus_xml(
    events: list[dict],
    sync_token: str | None = None,
) -> str:
    """Build a WebDAV multistatus XML response string.

    Each event dict: href, etag, calendar_data, status (optional, for deleted).
    """
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">',
    ]

    if sync_token:
        lines.append(f"  <d:sync-token>{sync_token}</d:sync-token>")

    for evt in events:
        href = evt.get("href", "")
        if evt.get("deleted"):
            lines.append(f"  <d:response>")
            lines.append(f"    <d:href>{href}</d:href>")
            lines.append(f"    <d:status>HTTP/1.1 404 Not Found</d:status>")
            lines.append(f"  </d:response>")
        else:
            etag = evt.get("etag", '"abc123"')
            cal_data = evt.get("calendar_data", "")
            # Escape XML special chars in calendar data
            cal_data_escaped = cal_data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            lines.append(f"  <d:response>")
            lines.append(f"    <d:href>{href}</d:href>")
            lines.append(f"    <d:propstat>")
            lines.append(f"      <d:prop>")
            lines.append(f"        <d:getetag>{etag}</d:getetag>")
            lines.append(f"        <c:calendar-data>{cal_data_escaped}</c:calendar-data>")
            lines.append(f"      </d:prop>")
            lines.append(f"      <d:status>HTTP/1.1 200 OK</d:status>")
            lines.append(f"    </d:propstat>")
            lines.append(f"  </d:response>")

    lines.append("</d:multistatus>")
    return "\n".join(lines)


def _make_connected_state(
    calendars: list | None = None,
    sync_tokens: dict[str, str] | None = None,
    username: str = "user@example.com",
) -> dict[str, str]:
    """Build state dict for a connected CalDAV account with calendars selected."""
    data: dict[str, str] = {
        "auth_method": "basic",
        "server_url": "https://caldav.example.com",
        "username": username,
        "password": "secret",
    }
    if calendars is not None:
        data["selected_calendars"] = json.dumps(calendars)
    if sync_tokens:
        for key, val in sync_tokens.items():
            data[key] = val
    return data


# ===================================================================
# Sync-token extraction tests
# ===================================================================


class TestExtractSyncToken:
    """Test _extract_sync_token() parsing."""

    def test_extracts_sync_token_from_multistatus(self):
        xml = _build_multistatus_xml([], sync_token="https://caldav.example.com/sync/12345")
        token = _extract_sync_token(xml)
        assert token == "https://caldav.example.com/sync/12345"

    def test_returns_none_when_no_sync_token(self):
        xml = _build_multistatus_xml([])
        token = _extract_sync_token(xml)
        assert token is None

    def test_returns_none_for_empty_string(self):
        assert _extract_sync_token("") is None

    def test_returns_none_for_malformed_xml(self):
        assert _extract_sync_token("<not-xml") is None

    def test_returns_none_for_empty_sync_token_element(self):
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<d:multistatus xmlns:d="DAV:">'
            '<d:sync-token></d:sync-token>'
            '</d:multistatus>'
        )
        assert _extract_sync_token(xml) is None

    def test_strips_whitespace_from_sync_token(self):
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<d:multistatus xmlns:d="DAV:">'
            '<d:sync-token>  https://example.com/sync/99  </d:sync-token>'
            '</d:multistatus>'
        )
        token = _extract_sync_token(xml)
        assert token == "https://example.com/sync/99"


# ===================================================================
# pull_sync guard tests
# ===================================================================


class TestPullSyncGuards:
    """Test pull_sync early-return conditions."""

    @pytest.mark.asyncio
    async def test_not_connected_returns_skipped(self):
        """When auth is not configured, pull_sync returns skipped."""
        ctx = MockAppContext(state_data={})
        result = await pull_sync(ctx)

        assert result["status"] == "skipped"
        assert result["reason"] == "not connected"
        assert result["created"] == 0

    @pytest.mark.asyncio
    async def test_no_calendars_selected_returns_ok(self):
        """When connected but no calendars selected, returns ok with 0 counts."""
        ctx = MockAppContext(state_data=_make_connected_state(calendars=[]))
        result = await pull_sync(ctx)

        assert result["status"] == "ok"
        assert result["created"] == 0
        assert result["updated"] == 0

    @pytest.mark.asyncio
    async def test_no_selected_calendars_key_returns_ok(self):
        """When selected_calendars key is missing entirely, returns ok."""
        state = _make_connected_state()
        # Don't set selected_calendars at all
        ctx = MockAppContext(state_data=state)
        result = await pull_sync(ctx)

        assert result["status"] == "ok"
        assert result["created"] == 0


# ===================================================================
# New event creation (two-phase) tests
# ===================================================================


class TestPullSyncNewEvent:
    """Test new event creation via two-phase bulk commands."""

    @pytest.mark.asyncio
    async def test_single_new_event_creates_commands(self):
        """A new event should generate object.create in phase 1."""
        ics_text = _build_ics(
            uid="test-uid-001",
            summary="Sprint Planning",
            description="Weekly sprint planning session",
        )
        multistatus = _build_multistatus_xml([
            {"href": "/cal/event1.ics", "calendar_data": ics_text},
        ], sync_token="https://caldav.example.com/sync/new-token")

        ext_http = MockCalDAVHttpClient(responses=[
            MockResponse(207, text=multistatus),
        ])

        # Phase-aware: not found on first lookup, found on phase 2
        slug = compute_event_slug("/calendars/work/", "test-uid-001")
        graph = PhaseAwareGraphClient(slug_map={
            slug: {"iri": f"https://example.org/data/Event/{slug}"},
        })

        state = _make_connected_state(
            calendars=[{"href": "/calendars/work/", "name": "Work"}],
        )

        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=state,
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["status"] == "ok"
        assert result["created"] == 1
        assert result["updated"] == 0

        # Check that bulk POST was called (phase 1 create + phase 2 body)
        assert len(bulk_http.posts) >= 1
        # Phase 1: object.create
        phase1_payload = bulk_http.posts[0]["json"]
        create_cmds = [c for c in phase1_payload["commands"] if c["command"] == "object.create"]
        assert len(create_cmds) == 1
        assert create_cmds[0]["params"]["properties"]["dcterms:title"] == "Sprint Planning"
        assert create_cmds[0]["params"]["properties"][f"{BPKM}externalProvider"] == "caldav"

    @pytest.mark.asyncio
    async def test_new_event_with_description_gets_body_set_in_phase2(self):
        """Phase 2 should include body.set for events with descriptions."""
        ics_text = _build_ics(
            uid="desc-uid",
            summary="Lunch",
            description="Bring your own food",
        )
        multistatus = _build_multistatus_xml([
            {"href": "/cal/lunch.ics", "calendar_data": ics_text},
        ], sync_token="https://caldav.example.com/sync/t2")

        ext_http = MockCalDAVHttpClient(responses=[
            MockResponse(207, text=multistatus),
        ])

        slug = compute_event_slug("/calendars/personal/", "desc-uid")
        graph = PhaseAwareGraphClient(slug_map={
            slug: {"iri": f"https://example.org/data/Event/{slug}"},
        })

        state = _make_connected_state(
            calendars=[{"href": "/calendars/personal/", "name": "Personal"}],
        )

        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=state,
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["created"] == 1
        # Phase 2 should have body.set
        assert len(bulk_http.posts) >= 2
        phase2_payload = bulk_http.posts[1]["json"]
        body_cmds = [c for c in phase2_payload["commands"] if c["command"] == "body.set"]
        assert len(body_cmds) >= 1
        assert "Bring your own food" in body_cmds[0]["params"]["body"]

    @pytest.mark.asyncio
    async def test_new_event_slug_uses_calendar_href_and_uid(self):
        """Slug should be computed from calendar_href + UID."""
        ics_text = _build_ics(uid="unique-123")
        multistatus = _build_multistatus_xml([
            {"href": "/cal/e.ics", "calendar_data": ics_text},
        ])

        ext_http = MockCalDAVHttpClient(responses=[
            MockResponse(207, text=multistatus),
        ])

        slug = compute_event_slug("/calendars/work/", "unique-123")

        # First query (during event processing) returns empty — it's new.
        # Second query (phase 2 discovery) returns the created event.
        call_count = 0
        original_graph = MockGraphClient()

        class PhaseAwareGraph(MockGraphClient):
            def __init__(self):
                super().__init__()
                self._call_count = 0

            async def query(self, sparql: str) -> dict:
                self.queries.append(sparql)
                self._call_count += 1
                if "STRENDS" in sparql and slug in sparql:
                    if self._call_count > 1:
                        return {"results": {"bindings": [{
                            "event": {"type": "uri", "value": f"https://example.org/data/Event/{slug}"},
                        }]}}
                return {"results": {"bindings": []}}

        graph = PhaseAwareGraph()

        state = _make_connected_state(
            calendars=[{"href": "/calendars/work/", "name": "Work"}],
        )

        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=state,
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)
        assert result["created"] == 1

        # Verify the slug in the create command
        phase1 = bulk_http.posts[0]["json"]
        create_cmd = phase1["commands"][0]
        assert create_cmd["params"]["slug"] == slug


# ===================================================================
# Existing event update tests
# ===================================================================


class TestPullSyncExistingEvent:
    """Test update path for existing events."""

    @pytest.mark.asyncio
    async def test_existing_event_generates_update_commands(self):
        """When event already exists, should produce object.patch + body.set."""
        ics_text = _build_ics(
            uid="existing-uid",
            summary="Updated Meeting",
            description="New agenda",
            last_modified="20260319T120000Z",
        )
        multistatus = _build_multistatus_xml([
            {"href": "/cal/existing.ics", "calendar_data": ics_text},
        ])

        ext_http = MockCalDAVHttpClient(responses=[
            MockResponse(207, text=multistatus),
        ])

        slug = compute_event_slug("/calendars/work/", "existing-uid")
        graph = MockGraphClient(slug_map={
            slug: {
                "iri": f"https://example.org/data/Event/{slug}",
                "lastSyncedAt": "2026-03-18T00:00:00+00:00",
            },
        })

        state = _make_connected_state(
            calendars=[{"href": "/calendars/work/", "name": "Work"}],
        )

        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=state,
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["updated"] == 1
        assert result["created"] == 0

        # Should have update commands with object.patch and body.set
        assert len(bulk_http.posts) >= 1
        update_payload = bulk_http.posts[0]["json"]
        patch_cmds = [c for c in update_payload["commands"] if c["command"] == "object.patch"]
        body_cmds = [c for c in update_payload["commands"] if c["command"] == "body.set"]
        assert len(patch_cmds) >= 1
        assert len(body_cmds) >= 1
        assert "New agenda" in body_cmds[0]["params"]["body"]


# ===================================================================
# Loop prevention tests
# ===================================================================


class TestPullSyncLoopPrevention:
    """Test unchanged detection via lastSyncedAt comparison."""

    @pytest.mark.asyncio
    async def test_event_not_modified_since_last_sync_is_unchanged(self):
        """If lastSyncedAt >= LAST-MODIFIED, event should be counted as unchanged."""
        ics_text = _build_ics(
            uid="unchanged-uid",
            summary="Old Meeting",
            last_modified="20260317T100000Z",  # older than lastSyncedAt
        )
        multistatus = _build_multistatus_xml([
            {"href": "/cal/old.ics", "calendar_data": ics_text},
        ])

        ext_http = MockCalDAVHttpClient(responses=[
            MockResponse(207, text=multistatus),
        ])

        slug = compute_event_slug("/calendars/work/", "unchanged-uid")
        graph = MockGraphClient(slug_map={
            slug: {
                "iri": f"https://example.org/data/Event/{slug}",
                "lastSyncedAt": "2026-03-18T00:00:00+00:00",  # newer than LAST-MODIFIED
            },
        })

        state = _make_connected_state(
            calendars=[{"href": "/calendars/work/", "name": "Work"}],
        )

        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=state,
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["unchanged"] == 1
        assert result["updated"] == 0
        assert result["created"] == 0
        # No bulk commands should be submitted
        assert len(bulk_http.posts) == 0


# ===================================================================
# Per-event error isolation tests
# ===================================================================


class TestPullSyncErrorIsolation:
    """Test that one bad event doesn't abort the sync."""

    @pytest.mark.asyncio
    async def test_malformed_ics_is_captured_as_error(self):
        """Invalid iCalendar data should be captured in errors, not crash sync."""
        good_ics = _build_ics(uid="good-uid", summary="Good Event")
        multistatus = _build_multistatus_xml([
            {"href": "/cal/bad.ics", "calendar_data": "NOT VALID ICS DATA"},
            {"href": "/cal/good.ics", "calendar_data": good_ics},
        ])

        ext_http = MockCalDAVHttpClient(responses=[
            MockResponse(207, text=multistatus),
        ])

        slug = compute_event_slug("/calendars/work/", "good-uid")

        class PhaseAwareGraph(MockGraphClient):
            def __init__(self):
                super().__init__()
                self._phase2 = False

            async def query(self, sparql: str) -> dict:
                self.queries.append(sparql)
                if "STRENDS" in sparql and slug in sparql and self._phase2:
                    return {"results": {"bindings": [{
                        "event": {"type": "uri", "value": f"https://example.org/data/Event/{slug}"},
                    }]}}
                return {"results": {"bindings": []}}

        graph = PhaseAwareGraph()

        state = _make_connected_state(
            calendars=[{"href": "/calendars/work/", "name": "Work"}],
        )

        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=state,
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        # After phase 1, mark graph as phase 2
        result = await pull_sync(ctx)

        # Bad ICS should be in errors, good event should be created
        assert len(result["errors"]) >= 1
        assert result["created"] == 1  # the good event


# ===================================================================
# Sync-token persistence tests
# ===================================================================


class TestPullSyncTokenPersistence:
    """Test sync-token storage after successful sync."""

    @pytest.mark.asyncio
    async def test_sync_token_stored_after_pull(self):
        """After successful pull, per-calendar sync-token should be stored in state."""
        ics_text = _build_ics(uid="token-test-uid")
        new_token = "https://caldav.example.com/sync/after-pull-token"
        multistatus = _build_multistatus_xml([
            {"href": "/cal/evt.ics", "calendar_data": ics_text},
        ], sync_token=new_token)

        ext_http = MockCalDAVHttpClient(responses=[
            MockResponse(207, text=multistatus),
        ])

        slug = compute_event_slug("/calendars/work/", "token-test-uid")
        graph = MockGraphClient(slug_map={
            slug: {"iri": f"https://example.org/data/Event/{slug}"},
        })

        state = _make_connected_state(
            calendars=[{"href": "/calendars/work/", "name": "Work"}],
        )

        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=state,
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)
        assert result["status"] == "ok"

        # Verify sync-token was stored
        stored_token = await ctx.state.get("sync_token:/calendars/work/")
        assert stored_token == new_token

    @pytest.mark.asyncio
    async def test_last_pull_result_stored_in_state(self):
        """After pull, last_pull_result should be stored as JSON in state."""
        ics_text = _build_ics(uid="result-test-uid")
        multistatus = _build_multistatus_xml([
            {"href": "/cal/evt.ics", "calendar_data": ics_text},
        ])

        ext_http = MockCalDAVHttpClient(responses=[
            MockResponse(207, text=multistatus),
        ])

        slug = compute_event_slug("/calendars/work/", "result-test-uid")
        graph = MockGraphClient(slug_map={
            slug: {"iri": f"https://example.org/data/Event/{slug}"},
        })

        state = _make_connected_state(
            calendars=[{"href": "/calendars/work/", "name": "Work"}],
        )

        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=state,
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        await pull_sync(ctx)

        stored_json = await ctx.state.get("last_pull_result")
        assert stored_json is not None
        stored = json.loads(stored_json)
        assert stored["status"] == "ok"
        assert "created" in stored


# ===================================================================
# 410 recovery tests
# ===================================================================


class TestPullSync410Recovery:
    """Test sync-token expiry (410 Gone) recovery flow."""

    @pytest.mark.asyncio
    async def test_410_clears_token_and_retries(self):
        """CalDAVError with status_code=410 should trigger full sync retry."""
        ics_text = _build_ics(uid="recovery-uid", summary="Recovered Event")
        full_sync_multistatus = _build_multistatus_xml([
            {"href": "/cal/recovered.ics", "calendar_data": ics_text},
        ], sync_token="https://caldav.example.com/sync/fresh-token")

        # First request: 410 error (expired sync-token)
        # Second request: full sync success
        call_count = 0

        class RecoveryHttpClient(MockCalDAVHttpClient):
            def __init__(self):
                super().__init__()
                self._call_count = 0

            async def request(self, method: str, url: str, **kwargs) -> MockResponse:
                self.requests.append({"method": method, "url": url, **kwargs})
                self._call_count += 1
                if self._call_count == 1:
                    # Return 410 for the first REPORT (sync-token expired)
                    return MockResponse(410, text="<error>sync-token expired</error>")
                # Return success for the second REPORT (full sync)
                return MockResponse(207, text=full_sync_multistatus)

        ext_http = RecoveryHttpClient()

        slug = compute_event_slug("/calendars/work/", "recovery-uid")
        graph = PhaseAwareGraphClient(slug_map={
            slug: {"iri": f"https://example.org/data/Event/{slug}"},
        })

        state = _make_connected_state(
            calendars=[{"href": "/calendars/work/", "name": "Work"}],
            sync_tokens={"sync_token:/calendars/work/": "https://caldav.example.com/sync/old-expired"},
        )

        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=state,
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["status"] == "ok"
        assert result["created"] == 1
        # Verify the expired sync-token was cleared
        cleared_token = await ctx.state.get("sync_token:/calendars/work/")
        # Should be either empty or the new token
        assert cleared_token in ("", "https://caldav.example.com/sync/fresh-token")
        # Two REPORT requests should have been made
        report_requests = [r for r in ext_http.requests if r["method"] == "REPORT"]
        assert len(report_requests) == 2


# ===================================================================
# Deleted resources tests
# ===================================================================


class TestPullSyncDeletedResources:
    """Test handling of sync-collection deleted entries."""

    @pytest.mark.asyncio
    async def test_deleted_resource_is_skipped(self):
        """Sync-collection entry with 404 status should be skipped."""
        good_ics = _build_ics(uid="alive-uid", summary="Living Event")
        multistatus = _build_multistatus_xml([
            {"href": "/cal/deleted.ics", "deleted": True},
            {"href": "/cal/alive.ics", "calendar_data": good_ics},
        ])

        ext_http = MockCalDAVHttpClient(responses=[
            MockResponse(207, text=multistatus),
        ])

        slug = compute_event_slug("/calendars/work/", "alive-uid")
        graph = PhaseAwareGraphClient(slug_map={
            slug: {"iri": f"https://example.org/data/Event/{slug}"},
        })

        state = _make_connected_state(
            calendars=[{"href": "/calendars/work/", "name": "Work"}],
        )

        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=state,
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        # Only the alive event should be processed
        assert result["created"] == 1
        assert len(result["errors"]) == 0


# ===================================================================
# Push sync helpers
# ===================================================================


def _make_push_state(
    sync_direction: str = "bidirectional",
    username: str = "user@example.com",
) -> dict[str, str]:
    """Build state dict for a connected CalDAV account ready for push sync."""
    return {
        "auth_method": "basic",
        "server_url": "https://cal.example.com",
        "username": username,
        "password": "secret",
        "sync_direction": sync_direction,
    }


# ===================================================================
# _find_changed_events tests
# ===================================================================


class TestFindChangedEvents:
    """Test _find_changed_events SPARQL query."""

    @pytest.mark.asyncio
    async def test_finds_changed_events(self):
        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt1",
                "externalId": "caldav-evt-1",
                "externalUrl": "https://cal.example.com/calendars/work/evt1.ics",
                "calendarName": "Work",
                "responseStatus": "accepted",
                "lastSyncedAt": "2026-03-17T10:00:00Z",
            }
        ])
        result = await _find_changed_events(graph)
        assert len(result) == 1
        assert result[0]["iri"] == "https://example.org/data/Event/evt1"
        assert result[0]["externalId"] == "caldav-evt-1"
        assert result[0]["externalUrl"] == "https://cal.example.com/calendars/work/evt1.ics"
        assert result[0]["calendarName"] == "Work"
        assert result[0]["responseStatus"] == "accepted"

    @pytest.mark.asyncio
    async def test_filters_by_caldav_provider(self):
        """SPARQL query should filter by externalProvider 'caldav'."""
        graph = MockGraphClient(changed_events=[])
        await _find_changed_events(graph)
        assert len(graph.queries) == 1
        assert '"caldav"' in graph.queries[0]

    @pytest.mark.asyncio
    async def test_empty_when_no_changes(self):
        graph = MockGraphClient(changed_events=[])
        result = await _find_changed_events(graph)
        assert result == []

    @pytest.mark.asyncio
    async def test_missing_optional_fields(self):
        """Events with only iri/externalId should return with None for optional fields."""
        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt2",
                "externalId": "caldav-evt-2",
                "externalUrl": None,
                "calendarName": None,
                "responseStatus": None,
                "lastSyncedAt": None,
            }
        ])
        result = await _find_changed_events(graph)
        assert len(result) == 1
        evt = result[0]
        assert evt["iri"] == "https://example.org/data/Event/evt2"
        assert evt["externalId"] == "caldav-evt-2"
        assert evt["externalUrl"] is None
        assert evt["calendarName"] is None
        assert evt["responseStatus"] is None

    @pytest.mark.asyncio
    async def test_returns_all_expected_keys(self):
        """Result dicts should contain the full key set including externalUrl."""
        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt3",
                "externalId": "caldav-evt-3",
                "externalUrl": "https://cal.example.com/e3.ics",
                "calendarName": "Personal",
                "responseStatus": "tentative",
                "lastSyncedAt": "2026-03-18T08:00:00Z",
            }
        ])
        result = await _find_changed_events(graph)
        assert len(result) == 1
        evt = result[0]
        assert set(evt.keys()) == {
            "iri", "externalId", "externalUrl", "calendarName",
            "responseStatus", "lastSyncedAt",
        }


# ===================================================================
# push_sync tests
# ===================================================================


class TestPushSync:
    """Test push_sync pipeline — CalDAV fetch-modify-PUT with ETag concurrency."""

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
        """Push a DECLINED RSVP → GET .ics, modify PARTSTAT, PUT with ETag."""
        ics_text = _build_ics(
            uid="evt-push-001",
            summary="Team Standup",
            attendees=[
                {"email": "user@example.com", "name": "User", "partstat": "NEEDS-ACTION"},
                {"email": "other@example.com", "name": "Other", "partstat": "ACCEPTED"},
            ],
        )

        # GET returns current .ics with ETag, PUT succeeds with new ETag
        ext_http = MockCalDAVHttpClient(responses=[
            MockResponse(200, text=ics_text, headers={"ETag": '"etag-abc"'}),
            MockResponse(201, headers={"ETag": '"etag-def"'}),
        ])

        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt1",
                "externalId": "caldav-evt-1",
                "externalUrl": "https://cal.example.com/calendars/work/evt1.ics",
                "calendarName": "Work",
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

        # Verify GET request was made to the externalUrl
        get_reqs = [r for r in ext_http.requests if r["method"] == "GET"]
        assert len(get_reqs) == 1
        assert "evt1.ics" in get_reqs[0]["url"]

        # Verify PUT request was made with modified .ics containing new PARTSTAT
        put_reqs = [r for r in ext_http.requests if r["method"] == "PUT"]
        assert len(put_reqs) == 1
        assert "evt1.ics" in put_reqs[0]["url"]
        # PUT should have If-Match header with ETag
        put_headers = put_reqs[0].get("headers", {})
        assert put_headers.get("If-Match") == '"etag-abc"'

    @pytest.mark.asyncio
    async def test_last_synced_at_updated(self):
        """After successful push, lastSyncedAt should be updated via object.patch."""
        ics_text = _build_ics(
            uid="evt-ls-001",
            attendees=[{"email": "user@example.com", "partstat": "NEEDS-ACTION"}],
        )

        ext_http = MockCalDAVHttpClient(responses=[
            MockResponse(200, text=ics_text, headers={"ETag": '"e1"'}),
            MockResponse(201, headers={"ETag": '"e2"'}),
        ])

        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt1",
                "externalId": "caldav-evt-1",
                "externalUrl": "https://cal.example.com/evt1.ics",
                "responseStatus": "accepted",
            }
        ])

        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )
        await push_sync(ctx)

        # Check that an object.patch command was posted with lastSyncedAt
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
    async def test_error_isolation(self):
        """First event fails (GET 500), second succeeds → partial status."""
        ics_text = _build_ics(
            uid="evt-ok",
            attendees=[{"email": "user@example.com", "partstat": "NEEDS-ACTION"}],
        )

        # First GET → 500 error, second GET → 200, then PUT → 201
        ext_http = MockCalDAVHttpClient(responses=[
            MockResponse(500, text="Internal Server Error"),
            MockResponse(200, text=ics_text, headers={"ETag": '"e1"'}),
            MockResponse(201, headers={"ETag": '"e2"'}),
        ])

        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt-fail",
                "externalId": "fail-1",
                "externalUrl": "https://cal.example.com/fail.ics",
                "responseStatus": "declined",
            },
            {
                "iri": "https://example.org/data/Event/evt-ok",
                "externalId": "ok-1",
                "externalUrl": "https://cal.example.com/ok.ics",
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
        assert result["errors"][0]["event_iri"] == "https://example.org/data/Event/evt-fail"

    @pytest.mark.asyncio
    async def test_missing_external_url(self):
        """Event without externalUrl → error recorded, not crash."""
        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt-no-url",
                "externalId": "no-url-1",
                "externalUrl": None,
                "responseStatus": "declined",
            }
        ])

        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=graph,
        )
        result = await push_sync(ctx)

        assert result["pushed"] == 0
        assert len(result["errors"]) == 1
        assert "externalUrl" in result["errors"][0]["error"]

    @pytest.mark.asyncio
    async def test_etag_conflict_412(self):
        """PUT returns 412 (ETag conflict) → CalDAVConflictError caught, recorded."""
        ics_text = _build_ics(
            uid="evt-conflict",
            attendees=[{"email": "user@example.com", "partstat": "NEEDS-ACTION"}],
        )

        # GET succeeds, PUT returns 412
        ext_http = MockCalDAVHttpClient(responses=[
            MockResponse(200, text=ics_text, headers={"ETag": '"stale-etag"'}),
            MockResponse(412, text="Precondition Failed"),
        ])

        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt-conflict",
                "externalId": "conflict-1",
                "externalUrl": "https://cal.example.com/conflict.ics",
                "responseStatus": "declined",
            }
        ])

        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=graph,
            ext_http_client=ext_http,
        )
        result = await push_sync(ctx)

        assert result["pushed"] == 0
        assert len(result["errors"]) == 1
        error_msg = result["errors"][0]["error"].lower()
        assert "conflict" in error_msg or "412" in error_msg

    @pytest.mark.asyncio
    async def test_empty_patch_skipped(self):
        """Event with no responseStatus → build_event_patch returns {} → skipped."""
        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt-no-rs",
                "externalId": "no-rs-1",
                "externalUrl": "https://cal.example.com/no-rs.ics",
                "responseStatus": None,
            }
        ])

        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=graph,
        )
        result = await push_sync(ctx)

        assert result["pushed"] == 0
        assert result["skipped"] == 1
        assert result["errors"] == []

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
        """Some pushed, some errors → status 'partial'."""
        ics_text = _build_ics(
            uid="evt-mix-ok",
            attendees=[{"email": "user@example.com", "partstat": "NEEDS-ACTION"}],
        )

        # First event: GET 500 error. Second event: GET 200 + PUT 201.
        ext_http = MockCalDAVHttpClient(responses=[
            MockResponse(500, text="Server Error"),
            MockResponse(200, text=ics_text, headers={"ETag": '"e1"'}),
            MockResponse(201, headers={"ETag": '"e2"'}),
        ])

        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/e1",
                "externalId": "e1",
                "externalUrl": "https://cal.example.com/e1.ics",
                "responseStatus": "declined",
            },
            {
                "iri": "https://example.org/data/Event/e2",
                "externalId": "e2",
                "externalUrl": "https://cal.example.com/e2.ics",
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
        """All events fail → status 'error'."""
        # GET returns 500 for the only event
        ext_http = MockCalDAVHttpClient(responses=[
            MockResponse(500, text="Server Error"),
        ])

        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/e1",
                "externalId": "e1",
                "externalUrl": "https://cal.example.com/e1.ics",
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
    async def test_skipped_result_stored_not_connected(self):
        """Even when skipped, last_push_result is stored in state."""
        ctx = MockAppContext(state_data={})
        await push_sync(ctx)

        stored = await ctx.state.get("last_push_result")
        assert stored is not None
        parsed = json.loads(stored)
        assert parsed["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_skipped_result_stored_pull_only(self):
        """Pull-only direction stores last_push_result."""
        ctx = MockAppContext(state_data=_make_push_state(sync_direction="pull-only"))
        await push_sync(ctx)

        stored = await ctx.state.get("last_push_result")
        assert stored is not None
        parsed = json.loads(stored)
        assert parsed["status"] == "skipped"
        assert "pull-only" in parsed.get("reason", "")

    @pytest.mark.asyncio
    async def test_multiple_events_all_pushed(self):
        """Multiple events all pushing successfully."""
        ics1 = _build_ics(
            uid="m1", attendees=[{"email": "user@example.com", "partstat": "NEEDS-ACTION"}],
        )
        ics2 = _build_ics(
            uid="m2", attendees=[{"email": "user@example.com", "partstat": "NEEDS-ACTION"}],
        )

        ext_http = MockCalDAVHttpClient(responses=[
            MockResponse(200, text=ics1, headers={"ETag": '"e1"'}),
            MockResponse(201, headers={"ETag": '"e1-new"'}),
            MockResponse(200, text=ics2, headers={"ETag": '"e2"'}),
            MockResponse(201, headers={"ETag": '"e2-new"'}),
        ])

        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt1",
                "externalId": "m1",
                "externalUrl": "https://cal.example.com/m1.ics",
                "responseStatus": "accepted",
            },
            {
                "iri": "https://example.org/data/Event/evt2",
                "externalId": "m2",
                "externalUrl": "https://cal.example.com/m2.ics",
                "responseStatus": "declined",
            },
        ])

        ctx = MockAppContext(
            state_data=_make_push_state(),
            graph_client=graph,
            ext_http_client=ext_http,
        )
        result = await push_sync(ctx)

        assert result["status"] == "ok"
        assert result["pushed"] == 2
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_etag_conflict_does_not_block_next_event(self):
        """ETag conflict on first event should not prevent second from pushing."""
        ics1 = _build_ics(
            uid="conflict-evt",
            attendees=[{"email": "user@example.com", "partstat": "NEEDS-ACTION"}],
        )
        ics2 = _build_ics(
            uid="ok-evt",
            attendees=[{"email": "user@example.com", "partstat": "NEEDS-ACTION"}],
        )

        ext_http = MockCalDAVHttpClient(responses=[
            # Event 1: GET ok, PUT 412 conflict
            MockResponse(200, text=ics1, headers={"ETag": '"stale"'}),
            MockResponse(412, text="Precondition Failed"),
            # Event 2: GET ok, PUT 201 success
            MockResponse(200, text=ics2, headers={"ETag": '"fresh"'}),
            MockResponse(201, headers={"ETag": '"fresh-new"'}),
        ])

        graph = MockGraphClient(changed_events=[
            {
                "iri": "https://example.org/data/Event/evt-conflict",
                "externalId": "conflict-1",
                "externalUrl": "https://cal.example.com/conflict.ics",
                "responseStatus": "declined",
            },
            {
                "iri": "https://example.org/data/Event/evt-ok",
                "externalId": "ok-1",
                "externalUrl": "https://cal.example.com/ok.ics",
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
        assert "conflict" in result["errors"][0]["error"].lower() or "412" in result["errors"][0]["error"]


# ===================================================================
# Command builder tests
# ===================================================================


class TestBuildCreateCommand:
    """Test _build_create_command helper."""

    def test_creates_event_command(self):
        cmd = _build_create_command("caldav-abc123", {"dcterms:title": "Test"})

        assert cmd["command"] == "object.create"
        assert cmd["params"]["type"] == f"{BPKM}Event"
        assert cmd["params"]["slug"] == "caldav-abc123"
        assert cmd["params"]["properties"]["dcterms:title"] == "Test"


class TestBuildUpdateCommands:
    """Test _build_update_commands helper."""

    def test_patch_only(self):
        cmds = _build_update_commands(
            "https://example.org/data/Event/test",
            {"dcterms:title": "Updated"},
            None, [], None,
        )
        assert len(cmds) == 1
        assert cmds[0]["command"] == "object.patch"

    def test_with_description(self):
        cmds = _build_update_commands(
            "https://example.org/data/Event/test",
            {"dcterms:title": "Updated"},
            "Some description", [], None,
        )
        body_cmds = [c for c in cmds if c["command"] == "body.set"]
        assert len(body_cmds) == 1
        assert body_cmds[0]["params"]["body"] == "Some description"

    def test_with_attendees_and_organizer(self):
        cmds = _build_update_commands(
            "https://example.org/data/Event/test",
            {"dcterms:title": "Meeting"},
            None,
            ["https://example.org/data/Person/alice", "https://example.org/data/Person/bob"],
            "https://example.org/data/Person/charlie",
        )
        edge_cmds = [c for c in cmds if c["command"] == "edge.create"]
        # 2 attendees + 1 organizer = 3 edges
        assert len(edge_cmds) == 3
        attendee_edges = [c for c in edge_cmds if "attendee" in c["params"]["predicate"]]
        organizer_edges = [c for c in edge_cmds if "organizer" in c["params"]["predicate"]]
        assert len(attendee_edges) == 2
        assert len(organizer_edges) == 1


# ===================================================================
# Submit batched tests
# ===================================================================


class TestSubmitCommandsBatched:
    """Test _submit_commands_batched."""

    @pytest.mark.asyncio
    async def test_posts_to_bulk_endpoint(self):
        http = MockHttpClient()
        commands = [{"command": "object.create", "params": {"slug": "test"}}]

        await _submit_commands_batched(http, commands, "test summary", "caldav-calendar")

        assert len(http.posts) == 1
        assert http.posts[0]["url"] == "/api/commands/bulk"
        payload = http.posts[0]["json"]
        assert payload["source"] == "caldav-calendar"
        assert len(payload["commands"]) == 1

    @pytest.mark.asyncio
    async def test_empty_commands_no_post(self):
        http = MockHttpClient()
        await _submit_commands_batched(http, [], "empty", "caldav-calendar")
        assert len(http.posts) == 0


# ===================================================================
# SPARQL lookup tests
# ===================================================================


class TestFindExistingEvent:
    """Test _find_existing_event SPARQL lookup."""

    @pytest.mark.asyncio
    async def test_found_returns_dict(self):
        graph = MockGraphClient(slug_map={
            "caldav-abc123": {
                "iri": "https://example.org/data/Event/caldav-abc123",
                "lastSyncedAt": "2026-03-18T00:00:00Z",
            }
        })
        result = await _find_existing_event(graph, "caldav-abc123")

        assert result is not None
        assert result["iri"] == "https://example.org/data/Event/caldav-abc123"
        assert result["lastSyncedAt"] == "2026-03-18T00:00:00Z"

    @pytest.mark.asyncio
    async def test_not_found_returns_none(self):
        graph = MockGraphClient()
        result = await _find_existing_event(graph, "caldav-nonexistent")
        assert result is None


# ===================================================================
# Calendar list format tests
# ===================================================================


class TestCalendarListFormats:
    """Test that pull_sync handles both string and dict calendar formats."""

    @pytest.mark.asyncio
    async def test_string_calendar_list(self):
        """When selected_calendars is a list of strings (href only)."""
        ics_text = _build_ics(uid="fmt-uid")
        multistatus = _build_multistatus_xml([
            {"href": "/cal/e.ics", "calendar_data": ics_text},
        ])

        ext_http = MockCalDAVHttpClient(responses=[
            MockResponse(207, text=multistatus),
        ])

        slug = compute_event_slug("/calendars/work/", "fmt-uid")
        graph = PhaseAwareGraphClient(slug_map={
            slug: {"iri": f"https://example.org/data/Event/{slug}"},
        })

        state = _make_connected_state(
            calendars=["/calendars/work/"],  # plain strings
        )

        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=state,
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)
        assert result["status"] == "ok"
        assert result["created"] == 1

    @pytest.mark.asyncio
    async def test_dict_calendar_list(self):
        """When selected_calendars is a list of dicts with href/name."""
        ics_text = _build_ics(uid="dict-uid")
        multistatus = _build_multistatus_xml([
            {"href": "/cal/e.ics", "calendar_data": ics_text},
        ])

        ext_http = MockCalDAVHttpClient(responses=[
            MockResponse(207, text=multistatus),
        ])

        slug = compute_event_slug("/calendars/personal/", "dict-uid")
        graph = PhaseAwareGraphClient(slug_map={
            slug: {"iri": f"https://example.org/data/Event/{slug}"},
        })

        state = _make_connected_state(
            calendars=[{"href": "/calendars/personal/", "name": "Personal Cal"}],
        )

        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=state,
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)
        assert result["status"] == "ok"
        assert result["created"] == 1

        # Verify calendar name is used in properties
        phase1 = bulk_http.posts[0]["json"]
        create_cmd = phase1["commands"][0]
        assert create_cmd["params"]["properties"][f"{BPKM}calendarName"] == "Personal Cal"


# ===================================================================
# Attendee/organizer person matching tests
# ===================================================================


class TestPullSyncPersonMatching:
    """Test attendee and organizer resolution via PersonMatcher."""

    @pytest.mark.asyncio
    async def test_attendees_resolved_for_existing_event(self):
        """Attendees on an existing event should create edge.create commands."""
        ics_text = _build_ics(
            uid="att-uid",
            summary="Team Sync",
            last_modified="20260319T120000Z",
            attendees=[
                {"email": "alice@example.com", "name": "Alice", "partstat": "ACCEPTED"},
                {"email": "user@example.com", "name": "Self", "partstat": "ACCEPTED"},  # self
            ],
            organizer={"email": "boss@example.com", "name": "Boss"},
        )
        multistatus = _build_multistatus_xml([
            {"href": "/cal/team.ics", "calendar_data": ics_text},
        ])

        ext_http = MockCalDAVHttpClient(responses=[
            MockResponse(207, text=multistatus),
        ])

        slug = compute_event_slug("/calendars/work/", "att-uid")
        graph = MockGraphClient(
            slug_map={
                slug: {
                    "iri": f"https://example.org/data/Event/{slug}",
                    "lastSyncedAt": "2026-03-18T00:00:00+00:00",
                },
            },
            email_to_iri={
                "alice@example.com": "https://example.org/data/Person/alice",
            },
        )

        state = _make_connected_state(
            calendars=[{"href": "/calendars/work/", "name": "Work"}],
            username="user@example.com",
        )

        bulk_http = MockHttpClient()
        ctx = MockAppContext(
            state_data=state,
            graph_client=graph,
            http_client=bulk_http,
            ext_http_client=ext_http,
        )

        result = await pull_sync(ctx)

        assert result["updated"] == 1
        # Check for attendee edge commands (self should be excluded)
        all_cmds = bulk_http.posts[0]["json"]["commands"]
        attendee_edges = [
            c for c in all_cmds
            if c["command"] == "edge.create" and "attendee" in c["params"].get("predicate", "")
        ]
        organizer_edges = [
            c for c in all_cmds
            if c["command"] == "edge.create" and "organizer" in c["params"].get("predicate", "")
        ]
        # alice should be included, self (user@example.com) should be excluded
        assert len(attendee_edges) >= 1
        # organizer (boss@example.com) should be included
        assert len(organizer_edges) >= 1
