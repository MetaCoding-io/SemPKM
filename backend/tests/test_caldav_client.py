"""Unit tests for the CalDAV client.

Loads ``caldav_client.py`` from the apps directory using importlib to avoid
requiring the app to be installed as a package. All HTTP and state interactions
are mocked — no network calls are made.

Canned XML responses cover Fastmail-style (absolute hrefs) and
Nextcloud-style (relative hrefs) server variants.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import pytest

# ---------------------------------------------------------------------------
# Load modules from apps directory
# ---------------------------------------------------------------------------

_APPS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "apps" / "caldav-calendar"
)
_SERVICES_DIR = _APPS_DIR / "services"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Load caldav_client first, then auth (for get_auth_headers)
cc = _load_module("caldav_client", _SERVICES_DIR / "caldav_client.py")
auth_mod = _load_module("auth", _SERVICES_DIR / "auth.py")

CalDAVClient = cc.CalDAVClient
CalDAVError = cc.CalDAVError
CalDAVAuthError = cc.CalDAVAuthError
CalDAVNotFoundError = cc.CalDAVNotFoundError
CalDAVConflictError = cc.CalDAVConflictError

_build_propfind_xml = cc._build_propfind_xml
_build_sync_collection_xml = cc._build_sync_collection_xml
_build_calendar_query_xml = cc._build_calendar_query_xml
_parse_multistatus = cc._parse_multistatus

DAV_NS = cc.DAV_NS
CALDAV_NS = cc.CALDAV_NS
CS_NS = cc.CS_NS


# ---------------------------------------------------------------------------
# Canned XML responses
# ---------------------------------------------------------------------------

PRINCIPAL_RESPONSE_ABSOLUTE = """<?xml version="1.0" encoding="utf-8"?>
<d:multistatus xmlns:d="DAV:">
  <d:response>
    <d:href>https://caldav.fastmail.com/dav/</d:href>
    <d:propstat>
      <d:prop>
        <d:current-user-principal>
          <d:href>https://caldav.fastmail.com/dav/principals/user/alice@fastmail.com/</d:href>
        </d:current-user-principal>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
</d:multistatus>"""

PRINCIPAL_RESPONSE_RELATIVE = """<?xml version="1.0" encoding="utf-8"?>
<d:multistatus xmlns:d="DAV:">
  <d:response>
    <d:href>/remote.php/dav/</d:href>
    <d:propstat>
      <d:prop>
        <d:current-user-principal>
          <d:href>/remote.php/dav/principals/users/alice/</d:href>
        </d:current-user-principal>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
</d:multistatus>"""

CALENDAR_HOME_ABSOLUTE = """<?xml version="1.0" encoding="utf-8"?>
<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:response>
    <d:href>https://caldav.fastmail.com/dav/principals/user/alice@fastmail.com/</d:href>
    <d:propstat>
      <d:prop>
        <c:calendar-home-set>
          <d:href>https://caldav.fastmail.com/dav/calendars/user/alice@fastmail.com/</d:href>
        </c:calendar-home-set>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
</d:multistatus>"""

CALENDAR_HOME_RELATIVE = """<?xml version="1.0" encoding="utf-8"?>
<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:response>
    <d:href>/remote.php/dav/principals/users/alice/</d:href>
    <d:propstat>
      <d:prop>
        <c:calendar-home-set>
          <d:href>/remote.php/dav/calendars/alice/</d:href>
        </c:calendar-home-set>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
</d:multistatus>"""

CALENDAR_LIST_FASTMAIL = """<?xml version="1.0" encoding="utf-8"?>
<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav"
               xmlns:cs="http://calendarserver.org/ns/">
  <d:response>
    <d:href>https://caldav.fastmail.com/dav/calendars/user/alice@fastmail.com/</d:href>
    <d:propstat>
      <d:prop>
        <d:displayname>Calendar Home</d:displayname>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
  <d:response>
    <d:href>https://caldav.fastmail.com/dav/calendars/user/alice@fastmail.com/default/</d:href>
    <d:propstat>
      <d:prop>
        <d:displayname>Personal</d:displayname>
        <cs:getctag>ctag-abc123</cs:getctag>
        <c:supported-calendar-component-set>
          <c:comp name="VEVENT"/>
          <c:comp name="VTODO"/>
        </c:supported-calendar-component-set>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
  <d:response>
    <d:href>https://caldav.fastmail.com/dav/calendars/user/alice@fastmail.com/work/</d:href>
    <d:propstat>
      <d:prop>
        <d:displayname>Work</d:displayname>
        <cs:getctag>ctag-def456</cs:getctag>
        <c:supported-calendar-component-set>
          <c:comp name="VEVENT"/>
        </c:supported-calendar-component-set>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
</d:multistatus>"""

CALENDAR_LIST_NEXTCLOUD = """<?xml version="1.0" encoding="utf-8"?>
<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav"
               xmlns:cs="http://calendarserver.org/ns/">
  <d:response>
    <d:href>/remote.php/dav/calendars/alice/</d:href>
    <d:propstat>
      <d:prop>
        <d:displayname/>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
  <d:response>
    <d:href>/remote.php/dav/calendars/alice/personal/</d:href>
    <d:propstat>
      <d:prop>
        <d:displayname>Personal</d:displayname>
        <cs:getctag>http://sabre.io/ns/sync/42</cs:getctag>
        <c:supported-calendar-component-set>
          <c:comp name="VEVENT"/>
        </c:supported-calendar-component-set>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
  <d:response>
    <d:href>/remote.php/dav/calendars/alice/tasks/</d:href>
    <d:propstat>
      <d:prop>
        <d:displayname>Tasks</d:displayname>
        <cs:getctag>http://sabre.io/ns/sync/10</cs:getctag>
        <c:supported-calendar-component-set>
          <c:comp name="VTODO"/>
        </c:supported-calendar-component-set>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
</d:multistatus>"""

SYNC_COLLECTION_RESPONSE = """<?xml version="1.0" encoding="utf-8"?>
<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:response>
    <d:href>/calendars/alice/default/event1.ics</d:href>
    <d:propstat>
      <d:prop>
        <d:getetag>"etag-event1-v2"</d:getetag>
        <c:calendar-data>BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:event1@example.com
SUMMARY:Updated Meeting
DTSTART:20260320T100000Z
DTEND:20260320T110000Z
END:VEVENT
END:VCALENDAR</c:calendar-data>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
  <d:response>
    <d:href>/calendars/alice/default/event2.ics</d:href>
    <d:propstat>
      <d:prop>
        <d:getetag>"etag-event2-v1"</d:getetag>
        <c:calendar-data>BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:event2@example.com
SUMMARY:New Event
DTSTART:20260321T140000Z
DTEND:20260321T150000Z
END:VEVENT
END:VCALENDAR</c:calendar-data>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
  <d:response>
    <d:href>/calendars/alice/default/event3.ics</d:href>
    <d:status>HTTP/1.1 404 Not Found</d:status>
  </d:response>
</d:multistatus>"""

SIMPLE_PROPSTAT_RESPONSE = """<?xml version="1.0" encoding="utf-8"?>
<d:multistatus xmlns:d="DAV:">
  <d:response>
    <d:href>/dav/</d:href>
    <d:propstat>
      <d:prop>
        <d:displayname>My WebDAV Server</d:displayname>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
</d:multistatus>"""


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class MockResponse:
    """Minimal httpx.Response stand-in."""

    def __init__(
        self,
        status_code: int = 200,
        body: str | dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._body = body if body is not None else ""
        self.headers = headers or {}

    @property
    def text(self) -> str:
        if isinstance(self._body, dict):
            return json.dumps(self._body)
        return self._body


class MockHttpClient:
    """Records calls and returns preset responses.

    Supports multiple HTTP methods (request, get, put, delete).
    """

    def __init__(self, responses: list[MockResponse] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._responses = list(responses or [])
        self._idx = 0

    def _next_response(self) -> MockResponse:
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            return resp
        return MockResponse(500, "No mock response configured")

    async def request(self, method: str, url: str, **kwargs: Any) -> MockResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        return self._next_response()

    async def get(self, url: str, **kwargs: Any) -> MockResponse:
        self.calls.append({"method": "GET", "url": url, **kwargs})
        return self._next_response()

    async def put(self, url: str, **kwargs: Any) -> MockResponse:
        self.calls.append({"method": "PUT", "url": url, **kwargs})
        return self._next_response()

    async def delete(self, url: str, **kwargs: Any) -> MockResponse:
        self.calls.append({"method": "DELETE", "url": url, **kwargs})
        return self._next_response()


class MockStateClient:
    """In-memory state store."""

    def __init__(self, initial: dict[str, str] | None = None) -> None:
        self._store: dict[str, str] = dict(initial or {})

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self._store[key] = value


# ---------------------------------------------------------------------------
# Helper: build a client with canned state
# ---------------------------------------------------------------------------


def _make_client(
    responses: list[MockResponse],
    username: str = "alice",
    password: str = "secret",
) -> tuple[CalDAVClient, MockHttpClient]:
    http = MockHttpClient(responses)
    state = MockStateClient({
        "username": username,
        "password": password,
        "server_url": "https://caldav.example.com",
        "auth_method": "basic",
    })
    return CalDAVClient(http, state), http


# ---------------------------------------------------------------------------
# Tests: XML builder — _build_propfind_xml
# ---------------------------------------------------------------------------


class TestBuildPropfindXml:

    def test_single_property(self):
        xml_str = _build_propfind_xml([(DAV_NS, "current-user-principal")])
        root = ET.fromstring(xml_str)
        assert root.tag == f"{{{DAV_NS}}}propfind"
        prop = root.find(f"{{{DAV_NS}}}prop")
        assert prop is not None
        children = list(prop)
        assert len(children) == 1
        assert children[0].tag == f"{{{DAV_NS}}}current-user-principal"

    def test_multi_properties(self):
        xml_str = _build_propfind_xml([
            (DAV_NS, "displayname"),
            (CALDAV_NS, "calendar-home-set"),
            (CS_NS, "getctag"),
        ])
        root = ET.fromstring(xml_str)
        prop = root.find(f"{{{DAV_NS}}}prop")
        children = list(prop)
        assert len(children) == 3
        tags = {c.tag for c in children}
        assert f"{{{DAV_NS}}}displayname" in tags
        assert f"{{{CALDAV_NS}}}calendar-home-set" in tags
        assert f"{{{CS_NS}}}getctag" in tags

    def test_output_is_valid_xml(self):
        """Generated XML can be parsed without errors."""
        xml_str = _build_propfind_xml([(DAV_NS, "resourcetype")])
        root = ET.fromstring(xml_str)
        assert root is not None


# ---------------------------------------------------------------------------
# Tests: XML builder — _build_sync_collection_xml
# ---------------------------------------------------------------------------


class TestBuildSyncCollectionXml:

    def test_with_sync_token(self):
        xml_str = _build_sync_collection_xml("http://example.com/sync/token-123")
        root = ET.fromstring(xml_str)
        assert root.tag == f"{{{DAV_NS}}}sync-collection"

        token = root.find(f"{{{DAV_NS}}}sync-token")
        assert token is not None
        assert token.text == "http://example.com/sync/token-123"

        level = root.find(f"{{{DAV_NS}}}sync-level")
        assert level.text == "1"

    def test_no_sync_token(self):
        xml_str = _build_sync_collection_xml(None)
        root = ET.fromstring(xml_str)
        token = root.find(f"{{{DAV_NS}}}sync-token")
        assert token is not None
        # ET serializes empty text as None on re-parse
        assert token.text is None or token.text == ""

    def test_default_props(self):
        xml_str = _build_sync_collection_xml("token")
        root = ET.fromstring(xml_str)
        prop = root.find(f"{{{DAV_NS}}}prop")
        tags = {c.tag for c in prop}
        assert f"{{{DAV_NS}}}getetag" in tags
        assert f"{{{CALDAV_NS}}}calendar-data" in tags

    def test_custom_props(self):
        xml_str = _build_sync_collection_xml(
            "token",
            props=[(DAV_NS, "getetag")],
        )
        root = ET.fromstring(xml_str)
        prop = root.find(f"{{{DAV_NS}}}prop")
        children = list(prop)
        assert len(children) == 1


# ---------------------------------------------------------------------------
# Tests: XML builder — _build_calendar_query_xml
# ---------------------------------------------------------------------------


class TestBuildCalendarQueryXml:

    def test_vevent_comp_filter_present(self):
        xml_str = _build_calendar_query_xml()
        root = ET.fromstring(xml_str)
        assert root.tag == f"{{{CALDAV_NS}}}calendar-query"

        # Find the VEVENT comp-filter
        filter_el = root.find(f"{{{CALDAV_NS}}}filter")
        assert filter_el is not None

        vcalendar_filter = filter_el.find(f"{{{CALDAV_NS}}}comp-filter")
        assert vcalendar_filter is not None
        assert vcalendar_filter.get("name") == "VCALENDAR"

        vevent_filter = vcalendar_filter.find(f"{{{CALDAV_NS}}}comp-filter")
        assert vevent_filter is not None
        assert vevent_filter.get("name") == "VEVENT"

    def test_requests_getetag_and_calendar_data(self):
        xml_str = _build_calendar_query_xml()
        root = ET.fromstring(xml_str)
        prop = root.find(f"{{{DAV_NS}}}prop")
        tags = {c.tag for c in prop}
        assert f"{{{DAV_NS}}}getetag" in tags
        assert f"{{{CALDAV_NS}}}calendar-data" in tags


# ---------------------------------------------------------------------------
# Tests: XML parser — _parse_multistatus
# ---------------------------------------------------------------------------


class TestParseMultistatus:

    def test_single_response(self):
        results = _parse_multistatus(SIMPLE_PROPSTAT_RESPONSE)
        assert len(results) == 1
        assert results[0]["href"] == "/dav/"
        assert results[0]["properties"]["displayname"] == "My WebDAV Server"
        assert "200 OK" in results[0]["status"]

    def test_multiple_responses(self):
        results = _parse_multistatus(CALENDAR_LIST_FASTMAIL)
        assert len(results) == 3
        hrefs = [r["href"] for r in results]
        assert any("default" in h for h in hrefs)
        assert any("work" in h for h in hrefs)

    def test_extracts_calendar_data(self):
        results = _parse_multistatus(SYNC_COLLECTION_RESPONSE)
        event1 = [r for r in results if "event1" in r["href"]][0]
        assert "BEGIN:VCALENDAR" in event1["properties"]["calendar-data"]
        assert "Updated Meeting" in event1["properties"]["calendar-data"]

    def test_deleted_resource_without_propstat(self):
        results = _parse_multistatus(SYNC_COLLECTION_RESPONSE)
        deleted = [r for r in results if "event3" in r["href"]][0]
        assert "404" in deleted["status"]
        assert deleted["properties"] == {}

    def test_nested_href_extraction(self):
        """Extracts href from nested element like current-user-principal."""
        results = _parse_multistatus(PRINCIPAL_RESPONSE_ABSOLUTE)
        assert len(results) == 1
        props = results[0]["properties"]
        assert "current-user-principal" in props
        assert "alice@fastmail.com" in props["current-user-principal"]

    def test_empty_body(self):
        results = _parse_multistatus("")
        assert results == []

    def test_malformed_xml(self):
        results = _parse_multistatus("<not-valid-xml")
        assert results == []

    def test_supported_component_set_parsing(self):
        results = _parse_multistatus(CALENDAR_LIST_FASTMAIL)
        personal = [r for r in results if "default" in r["href"]][0]
        comp_str = personal["properties"]["supported-calendar-component-set"]
        assert "VEVENT" in comp_str
        assert "VTODO" in comp_str


# ---------------------------------------------------------------------------
# Tests: Discovery chain
# ---------------------------------------------------------------------------


class TestDiscoverPrincipal:

    @pytest.mark.asyncio
    async def test_absolute_url(self):
        client, http = _make_client([
            MockResponse(207, PRINCIPAL_RESPONSE_ABSOLUTE),
        ])

        url = await client.discover_principal("https://caldav.fastmail.com/dav/")

        assert url == "https://caldav.fastmail.com/dav/principals/user/alice@fastmail.com/"
        assert http.calls[0]["method"] == "PROPFIND"

    @pytest.mark.asyncio
    async def test_relative_url(self):
        client, http = _make_client([
            MockResponse(207, PRINCIPAL_RESPONSE_RELATIVE),
        ])

        url = await client.discover_principal("https://nextcloud.example.com/remote.php/dav/")

        assert url == "https://nextcloud.example.com/remote.php/dav/principals/users/alice/"


class TestDiscoverCalendarHome:

    @pytest.mark.asyncio
    async def test_absolute_home(self):
        client, _ = _make_client([
            MockResponse(207, CALENDAR_HOME_ABSOLUTE),
        ])

        url = await client.discover_calendar_home(
            "https://caldav.fastmail.com/dav/principals/user/alice@fastmail.com/"
        )

        assert url == "https://caldav.fastmail.com/dav/calendars/user/alice@fastmail.com/"

    @pytest.mark.asyncio
    async def test_relative_home(self):
        client, _ = _make_client([
            MockResponse(207, CALENDAR_HOME_RELATIVE),
        ])

        url = await client.discover_calendar_home(
            "https://nextcloud.example.com/remote.php/dav/principals/users/alice/"
        )

        assert url == "https://nextcloud.example.com/remote.php/dav/calendars/alice/"


class TestDiscoverCalendars:

    @pytest.mark.asyncio
    async def test_full_chain(self):
        """Calls principal → home → list, returns calendar dicts."""
        client, http = _make_client([
            MockResponse(207, PRINCIPAL_RESPONSE_ABSOLUTE),
            MockResponse(207, CALENDAR_HOME_ABSOLUTE),
            MockResponse(207, CALENDAR_LIST_FASTMAIL),
        ])

        calendars = await client.discover_calendars("https://caldav.fastmail.com/dav/")

        assert len(http.calls) == 3  # 3 PROPFIND requests
        # Should have 2 VEVENT calendars (Personal + Work), not the home itself
        assert len(calendars) >= 2
        names = [c["displayname"] for c in calendars]
        assert "Personal" in names
        assert "Work" in names

    @pytest.mark.asyncio
    async def test_filters_vevent_only(self):
        """Skips calendars without VEVENT support (e.g., VTODO-only)."""
        client, _ = _make_client([
            MockResponse(207, PRINCIPAL_RESPONSE_RELATIVE),
            MockResponse(207, CALENDAR_HOME_RELATIVE),
            MockResponse(207, CALENDAR_LIST_NEXTCLOUD),
        ])

        calendars = await client.discover_calendars(
            "https://nextcloud.example.com/remote.php/dav/"
        )

        # Nextcloud list has Personal (VEVENT) and Tasks (VTODO-only)
        assert len(calendars) == 1
        assert calendars[0]["displayname"] == "Personal"

    @pytest.mark.asyncio
    async def test_fastmail_variant(self):
        """Canned Fastmail response returns correct structure."""
        client, _ = _make_client([
            MockResponse(207, PRINCIPAL_RESPONSE_ABSOLUTE),
            MockResponse(207, CALENDAR_HOME_ABSOLUTE),
            MockResponse(207, CALENDAR_LIST_FASTMAIL),
        ])

        calendars = await client.discover_calendars("https://caldav.fastmail.com/dav/")

        for cal in calendars:
            assert "href" in cal
            assert "displayname" in cal
            assert "ctag" in cal
            assert "supported_components" in cal

    @pytest.mark.asyncio
    async def test_nextcloud_variant(self):
        """Canned Nextcloud response returns correct structure."""
        client, _ = _make_client([
            MockResponse(207, PRINCIPAL_RESPONSE_RELATIVE),
            MockResponse(207, CALENDAR_HOME_RELATIVE),
            MockResponse(207, CALENDAR_LIST_NEXTCLOUD),
        ])

        calendars = await client.discover_calendars(
            "https://nextcloud.example.com/remote.php/dav/"
        )

        assert len(calendars) == 1
        cal = calendars[0]
        assert cal["displayname"] == "Personal"
        assert cal["ctag"] is not None
        assert "VEVENT" in cal["supported_components"]


# ---------------------------------------------------------------------------
# Tests: Event operations
# ---------------------------------------------------------------------------


class TestGetEvents:

    @pytest.mark.asyncio
    async def test_with_sync_token(self):
        """Sends sync-collection REPORT when sync_token is provided."""
        client, http = _make_client([
            MockResponse(207, SYNC_COLLECTION_RESPONSE),
        ])

        events, token = await client.get_events(
            "https://caldav.example.com/calendars/alice/default/",
            sync_token="http://example.com/sync/42",
        )

        assert len(events) == 3
        call = http.calls[0]
        assert call["method"] == "REPORT"
        assert "sync-collection" in call["content"]
        assert "http://example.com/sync/42" in call["content"]

    @pytest.mark.asyncio
    async def test_no_sync_token(self):
        """Sends calendar-query REPORT for full sync."""
        client, http = _make_client([
            MockResponse(207, SYNC_COLLECTION_RESPONSE),
        ])

        events, token = await client.get_events(
            "https://caldav.example.com/calendars/alice/default/",
        )

        call = http.calls[0]
        assert call["method"] == "REPORT"
        assert "calendar-query" in call["content"]

    @pytest.mark.asyncio
    async def test_includes_deleted(self):
        """Deleted events have status 404 and no calendar_data."""
        client, _ = _make_client([
            MockResponse(207, SYNC_COLLECTION_RESPONSE),
        ])

        events, _ = await client.get_events(
            "https://caldav.example.com/calendars/alice/default/",
            sync_token="token",
        )

        deleted = [e for e in events if "404" in e["status"]]
        assert len(deleted) == 1
        assert "event3" in deleted[0]["href"]
        assert deleted[0]["calendar_data"] == ""

    @pytest.mark.asyncio
    async def test_extracts_etag_and_data(self):
        """Normal events have etag and calendar_data."""
        client, _ = _make_client([
            MockResponse(207, SYNC_COLLECTION_RESPONSE),
        ])

        events, _ = await client.get_events(
            "https://caldav.example.com/calendars/alice/default/",
            sync_token="token",
        )

        event1 = [e for e in events if "event1" in e["href"]][0]
        assert event1["etag"] == '"etag-event1-v2"'
        assert "Updated Meeting" in event1["calendar_data"]


class TestGetEvent:

    @pytest.mark.asyncio
    async def test_single_event(self):
        ics = "BEGIN:VCALENDAR\nBEGIN:VEVENT\nSUMMARY:Test\nEND:VEVENT\nEND:VCALENDAR"
        client, http = _make_client([
            MockResponse(200, ics, headers={"ETag": '"etag-abc"'}),
        ])

        result = await client.get_event(
            "https://caldav.example.com/calendars/alice/default/event1.ics"
        )

        assert result["etag"] == '"etag-abc"'
        assert "BEGIN:VCALENDAR" in result["calendar_data"]
        assert http.calls[0]["method"] == "GET"


class TestPutEvent:

    @pytest.mark.asyncio
    async def test_create_sends_if_none_match(self):
        client, http = _make_client([
            MockResponse(201, "", headers={"ETag": '"new-etag"'}),
        ])

        ics = "BEGIN:VCALENDAR\nBEGIN:VEVENT\nSUMMARY:New\nEND:VEVENT\nEND:VCALENDAR"
        new_etag = await client.put_event(
            "https://caldav.example.com/calendars/alice/default/new-event.ics",
            ics,
            etag=None,
        )

        assert new_etag == '"new-etag"'
        headers = http.calls[0]["headers"]
        assert headers["If-None-Match"] == "*"
        assert "If-Match" not in headers

    @pytest.mark.asyncio
    async def test_update_sends_if_match(self):
        client, http = _make_client([
            MockResponse(204, "", headers={"ETag": '"updated-etag"'}),
        ])

        ics = "BEGIN:VCALENDAR\nBEGIN:VEVENT\nSUMMARY:Updated\nEND:VEVENT\nEND:VCALENDAR"
        new_etag = await client.put_event(
            "https://caldav.example.com/calendars/alice/default/event1.ics",
            ics,
            etag='"old-etag"',
        )

        assert new_etag == '"updated-etag"'
        headers = http.calls[0]["headers"]
        assert headers["If-Match"] == '"old-etag"'
        assert "If-None-Match" not in headers

    @pytest.mark.asyncio
    async def test_conflict_raises(self):
        client, _ = _make_client([
            MockResponse(412, "Precondition Failed"),
        ])

        with pytest.raises(CalDAVConflictError) as exc_info:
            await client.put_event(
                "https://caldav.example.com/calendars/alice/default/event1.ics",
                "VCALENDAR...",
                etag='"stale-etag"',
            )

        assert exc_info.value.status_code == 412


class TestDeleteEvent:

    @pytest.mark.asyncio
    async def test_with_etag(self):
        client, http = _make_client([
            MockResponse(204, ""),
        ])

        await client.delete_event(
            "https://caldav.example.com/calendars/alice/default/event1.ics",
            etag='"etag-abc"',
        )

        headers = http.calls[0]["headers"]
        assert headers["If-Match"] == '"etag-abc"'

    @pytest.mark.asyncio
    async def test_conflict_raises(self):
        client, _ = _make_client([
            MockResponse(412, "Precondition Failed"),
        ])

        with pytest.raises(CalDAVConflictError) as exc_info:
            await client.delete_event(
                "https://caldav.example.com/calendars/alice/default/event1.ics",
                etag='"stale-etag"',
            )

        assert exc_info.value.status_code == 412

    @pytest.mark.asyncio
    async def test_404_not_error(self):
        """Deleting an already-gone resource should not raise."""
        client, _ = _make_client([
            MockResponse(404, "Not Found"),
        ])

        # Should not raise
        await client.delete_event(
            "https://caldav.example.com/calendars/alice/default/gone.ics",
        )


# ---------------------------------------------------------------------------
# Tests: Error handling
# ---------------------------------------------------------------------------


class TestPropfindErrors:

    @pytest.mark.asyncio
    async def test_401_raises_auth_error(self):
        client, _ = _make_client([
            MockResponse(401, "Unauthorized"),
        ])

        with pytest.raises(CalDAVAuthError) as exc_info:
            await client.discover_principal("https://caldav.example.com/")

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_403_raises_auth_error(self):
        client, _ = _make_client([
            MockResponse(403, "Forbidden"),
        ])

        with pytest.raises(CalDAVAuthError) as exc_info:
            await client.discover_principal("https://caldav.example.com/")

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_404_raises_not_found(self):
        client, _ = _make_client([
            MockResponse(404, "Not Found"),
        ])

        with pytest.raises(CalDAVNotFoundError) as exc_info:
            await client.discover_principal("https://caldav.example.com/bad-path")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_500_raises_error(self):
        client, _ = _make_client([
            MockResponse(500, "Internal Server Error"),
        ])

        with pytest.raises(CalDAVError) as exc_info:
            await client.discover_principal("https://caldav.example.com/")

        assert exc_info.value.status_code == 500


class TestReportErrors:

    @pytest.mark.asyncio
    async def test_401_raises_auth_error(self):
        client, _ = _make_client([
            MockResponse(401, "Unauthorized"),
        ])

        with pytest.raises(CalDAVAuthError):
            await client.get_events("https://caldav.example.com/cal/")


class TestAuthNotConfigured:

    @pytest.mark.asyncio
    async def test_no_credentials_raises(self):
        """CalDAVAuthError when no credentials are configured."""
        http = MockHttpClient()
        state = MockStateClient()  # Empty — no credentials
        client = CalDAVClient(http, state)

        with pytest.raises(CalDAVAuthError, match="not configured"):
            await client.discover_principal("https://caldav.example.com/")
