"""Mock CalDAV server for E2E testing.

A lightweight HTTP server returning canned WebDAV XML (multistatus)
responses and raw iCalendar event data.  Handles CalDAV's custom HTTP
methods (PROPFIND, REPORT) alongside standard GET/PUT/DELETE.

Designed to run inside Docker alongside the SemPKM test stack so the
CalDAV app's ``CalDAVClient`` can be pointed here via the credential
form's server-URL field (``http://mock-caldav:8080/``).

Endpoints:
    GET     /health                                → 200 health check (JSON)
    PROPFIND /                       (Depth:0)     → 207 current-user-principal
    PROPFIND /principals/user/       (Depth:0)     → 207 calendar-home-set
    PROPFIND /calendars/user/        (Depth:1)     → 207 calendar list (Work + Personal)
    REPORT  /calendars/user/work/                  → 207 sync-collection (initial or incremental)
    GET     /calendars/user/work/{uid}.ics         → 200 iCalendar event
    PUT     /calendars/user/work/{uid}.ics         → 204 (ETag concurrency via If-Match)
    DELETE  /calendars/user/work/{uid}.ics         → 204

Usage:
    python server.py              # Start on port 8080
    python server.py --selftest   # Verify canned responses then exit
"""

from __future__ import annotations

import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from xml.etree import ElementTree as ET

PORT = 8080

# ---------------------------------------------------------------------------
# XML namespace constants (must match CalDAVClient expectations)
# ---------------------------------------------------------------------------

DAV_NS = "DAV:"
CALDAV_NS = "urn:ietf:params:xml:ns:caldav"
CS_NS = "http://calendarserver.org/ns/"

# ---------------------------------------------------------------------------
# Canned iCalendar event data
# ---------------------------------------------------------------------------

EVENT_TIMED = """\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//SemPKM//MockCalDAV//EN
BEGIN:VEVENT
UID:team-standup-001
SUMMARY:Team Standup
DTSTART;TZID=America/New_York:20260320T090000
DTEND;TZID=America/New_York:20260320T093000
LOCATION:Conference Room B
ORGANIZER;CN=Test User:mailto:test@example.com
ATTENDEE;CN=Test User;PARTSTAT=ACCEPTED:mailto:test@example.com
ATTENDEE;CN=Colleague;PARTSTAT=NEEDS-ACTION:mailto:colleague@example.com
CATEGORIES:work,standup
DESCRIPTION:Daily standup meeting
BEGIN:VALARM
TRIGGER:-PT15M
ACTION:DISPLAY
DESCRIPTION:Reminder
END:VALARM
END:VEVENT
END:VCALENDAR"""

EVENT_ALLDAY = """\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//SemPKM//MockCalDAV//EN
BEGIN:VEVENT
UID:company-holiday-002
SUMMARY:Company Holiday
DTSTART;VALUE=DATE:20260325
CLASS:PRIVATE
ORGANIZER;CN=Admin:mailto:admin@example.com
DESCRIPTION:Office closed
END:VEVENT
END:VCALENDAR"""

EVENT_RECURRING = """\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//SemPKM//MockCalDAV//EN
BEGIN:VEVENT
UID:weekly-review-003
SUMMARY:Weekly Review
DTSTART;TZID=America/New_York:20260320T160000
DTEND;TZID=America/New_York:20260320T170000
RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR;UNTIL=20261231T000000Z
DESCRIPTION:End-of-week review
END:VEVENT
END:VCALENDAR"""

# Map UID → iCalendar text
EVENTS = {
    "team-standup-001": EVENT_TIMED,
    "company-holiday-002": EVENT_ALLDAY,
    "weekly-review-003": EVENT_RECURRING,
}

# Mutable ETag store for concurrency simulation
ETAGS: dict[str, str] = {
    "team-standup-001": '"etag-team-standup-001-v1"',
    "company-holiday-002": '"etag-company-holiday-002-v1"',
    "weekly-review-003": '"etag-weekly-review-003-v1"',
}

# Mutable version counter for generating new ETags on PUT
_ETAG_VERSIONS: dict[str, int] = {
    "team-standup-001": 1,
    "company-holiday-002": 1,
    "weekly-review-003": 1,
}

# ---------------------------------------------------------------------------
# XML response builders
# ---------------------------------------------------------------------------


def _xml_preamble() -> str:
    return '<?xml version="1.0" encoding="utf-8"?>\n'


def _multistatus_principal() -> str:
    """PROPFIND / (Depth:0) → current-user-principal."""
    return (
        _xml_preamble()
        + '<d:multistatus xmlns:d="DAV:">\n'
        "  <d:response>\n"
        "    <d:href>/</d:href>\n"
        "    <d:propstat>\n"
        "      <d:prop>\n"
        "        <d:current-user-principal>\n"
        "          <d:href>/principals/user/</d:href>\n"
        "        </d:current-user-principal>\n"
        "      </d:prop>\n"
        "      <d:status>HTTP/1.1 200 OK</d:status>\n"
        "    </d:propstat>\n"
        "  </d:response>\n"
        "</d:multistatus>"
    )


def _multistatus_calendar_home() -> str:
    """PROPFIND /principals/user/ (Depth:0) → calendar-home-set."""
    return (
        _xml_preamble()
        + '<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">\n'
        "  <d:response>\n"
        "    <d:href>/principals/user/</d:href>\n"
        "    <d:propstat>\n"
        "      <d:prop>\n"
        "        <c:calendar-home-set>\n"
        "          <d:href>/calendars/user/</d:href>\n"
        "        </c:calendar-home-set>\n"
        "      </d:prop>\n"
        "      <d:status>HTTP/1.1 200 OK</d:status>\n"
        "    </d:propstat>\n"
        "  </d:response>\n"
        "</d:multistatus>"
    )


def _multistatus_calendar_list() -> str:
    """PROPFIND /calendars/user/ (Depth:1) → calendar list with home entry."""
    return (
        _xml_preamble()
        + '<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav"\n'
        '               xmlns:cs="http://calendarserver.org/ns/">\n'
        # Home collection entry (client filters this out)
        "  <d:response>\n"
        "    <d:href>/calendars/user/</d:href>\n"
        "    <d:propstat>\n"
        "      <d:prop>\n"
        "        <d:displayname>Calendar Home</d:displayname>\n"
        "      </d:prop>\n"
        "      <d:status>HTTP/1.1 200 OK</d:status>\n"
        "    </d:propstat>\n"
        "  </d:response>\n"
        # Work calendar
        "  <d:response>\n"
        "    <d:href>/calendars/user/work/</d:href>\n"
        "    <d:propstat>\n"
        "      <d:prop>\n"
        "        <d:displayname>Work</d:displayname>\n"
        "        <cs:getctag>ctag-work-001</cs:getctag>\n"
        "        <c:supported-calendar-component-set>\n"
        '          <c:comp name="VEVENT"/>\n'
        "        </c:supported-calendar-component-set>\n"
        "      </d:prop>\n"
        "      <d:status>HTTP/1.1 200 OK</d:status>\n"
        "    </d:propstat>\n"
        "  </d:response>\n"
        # Personal calendar
        "  <d:response>\n"
        "    <d:href>/calendars/user/personal/</d:href>\n"
        "    <d:propstat>\n"
        "      <d:prop>\n"
        "        <d:displayname>Personal</d:displayname>\n"
        "        <cs:getctag>ctag-personal-001</cs:getctag>\n"
        "        <c:supported-calendar-component-set>\n"
        '          <c:comp name="VEVENT"/>\n'
        "        </c:supported-calendar-component-set>\n"
        "      </d:prop>\n"
        "      <d:status>HTTP/1.1 200 OK</d:status>\n"
        "    </d:propstat>\n"
        "  </d:response>\n"
        "</d:multistatus>"
    )


def _multistatus_sync_initial() -> str:
    """REPORT sync-collection (initial) → 3 events + sync-token."""
    parts = [
        _xml_preamble(),
        '<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">\n',
    ]

    for uid, ics_data in EVENTS.items():
        etag = ETAGS.get(uid, f'"etag-{uid}-v1"')
        parts.append(
            f"  <d:response>\n"
            f"    <d:href>/calendars/user/work/{uid}.ics</d:href>\n"
            f"    <d:propstat>\n"
            f"      <d:prop>\n"
            f"        <d:getetag>{etag}</d:getetag>\n"
            f"        <c:calendar-data>{ics_data}</c:calendar-data>\n"
            f"      </d:prop>\n"
            f"      <d:status>HTTP/1.1 200 OK</d:status>\n"
            f"    </d:propstat>\n"
            f"  </d:response>\n"
        )

    parts.append(
        "  <d:sync-token>sync-token-initial-001</d:sync-token>\n"
        "</d:multistatus>"
    )
    return "".join(parts)


def _multistatus_sync_incremental() -> str:
    """REPORT sync-collection (incremental) → empty + new sync-token."""
    return (
        _xml_preamble()
        + '<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">\n'
        "  <d:sync-token>sync-token-incremental-002</d:sync-token>\n"
        "</d:multistatus>"
    )


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------


class MockCalDAVHandler(BaseHTTPRequestHandler):
    """Handles PROPFIND, REPORT, GET, PUT, DELETE for CalDAV mock."""

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.rstrip("/") or "/"

        if path == "/health":
            self._json_response(200, {"status": "ok", "service": "mock-caldav"})
            return

        # GET /calendars/user/work/{uid}.ics
        if path.startswith("/calendars/user/work/") and path.endswith(".ics"):
            uid = path.rsplit("/", 1)[-1].replace(".ics", "")
            self._handle_get_event(uid)
            return

        self._text_response(404, "Not Found")

    def do_PUT(self) -> None:  # noqa: N802
        path = self.path.rstrip("/")

        if path.startswith("/calendars/user/work/") and path.endswith(".ics"):
            uid = path.rsplit("/", 1)[-1].replace(".ics", "")
            self._handle_put_event(uid)
            return

        self._text_response(404, "Not Found")

    def do_DELETE(self) -> None:  # noqa: N802
        path = self.path.rstrip("/")

        if path.startswith("/calendars/user/work/") and path.endswith(".ics"):
            uid = path.rsplit("/", 1)[-1].replace(".ics", "")
            self._handle_delete_event(uid)
            return

        self._text_response(404, "Not Found")

    def do_PROPFIND(self) -> None:  # noqa: N802
        path = self.path.rstrip("/") or "/"
        depth = self.headers.get("Depth", "0")

        if path == "/":
            self._xml_response(207, _multistatus_principal())
        elif path == "/principals/user":
            self._xml_response(207, _multistatus_calendar_home())
        elif path == "/calendars/user" and depth == "1":
            self._xml_response(207, _multistatus_calendar_list())
        else:
            self._text_response(404, "Not Found")

    def do_REPORT(self) -> None:  # noqa: N802
        path = self.path.rstrip("/")

        if path == "/calendars/user/work":
            self._handle_sync_report()
            return

        self._text_response(404, "Not Found")

    # -- endpoint handlers --

    def _handle_get_event(self, uid: str) -> None:
        ics_data = EVENTS.get(uid)
        if ics_data is None:
            self._text_response(404, f"Event {uid} not found")
            return

        etag = ETAGS.get(uid, f'"etag-{uid}-v1"')
        payload = ics_data.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/calendar; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("ETag", etag)
        self.end_headers()
        self.wfile.write(payload)
        self._log(200)

    def _handle_put_event(self, uid: str) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""

        if_match = self.headers.get("If-Match")
        current_etag = ETAGS.get(uid)

        # ETag concurrency check
        if if_match is not None and current_etag is not None:
            if if_match != current_etag:
                self._text_response(412, "Precondition Failed: ETag mismatch")
                return

        # Bump version
        version = _ETAG_VERSIONS.get(uid, 0) + 1
        _ETAG_VERSIONS[uid] = version
        new_etag = f'"etag-{uid}-v{version}"'
        ETAGS[uid] = new_etag

        # Store updated content if provided
        if body:
            EVENTS[uid] = body.decode("utf-8", errors="replace")

        self.send_response(204)
        self.send_header("ETag", new_etag)
        self.end_headers()
        self._log(204)

    def _handle_delete_event(self, uid: str) -> None:
        # Remove from stores (idempotent — no error if already gone)
        EVENTS.pop(uid, None)
        ETAGS.pop(uid, None)
        _ETAG_VERSIONS.pop(uid, None)

        self.send_response(204)
        self.end_headers()
        self._log(204)

    def _handle_sync_report(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""

        # Determine initial vs incremental by checking for sync-token in request
        has_sync_token = False
        if body:
            try:
                root = ET.fromstring(body)
                token_el = root.find(f"{{{DAV_NS}}}sync-token")
                if token_el is not None and token_el.text and token_el.text.strip():
                    has_sync_token = True
            except ET.ParseError:
                self._text_response(400, "Malformed XML in REPORT body")
                return

        if has_sync_token:
            self._xml_response(207, _multistatus_sync_incremental())
        else:
            self._xml_response(207, _multistatus_sync_initial())

    # -- response helpers --

    def _json_response(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
        self._log(status)

    def _xml_response(self, status: int, xml_body: str) -> None:
        payload = xml_body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
        self._log(status)

    def _text_response(self, status: int, message: str) -> None:
        payload = message.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
        self._log(status)

    def _log(self, status: int) -> None:
        print(
            f"[mock-caldav] {self.command} {self.path} → {status}",
            file=sys.stderr,
            flush=True,
        )

    def log_message(self, fmt: str, *args) -> None:  # type: ignore[override]
        """Override to prefix all access logs for easy filtering."""
        print(f"[mock-caldav] {fmt % args}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Self-test mode
# ---------------------------------------------------------------------------


def selftest() -> None:
    """Start mock server in background thread, exercise all endpoints, exit."""
    import threading
    import urllib.request
    import urllib.error

    print("[selftest] Starting mock CalDAV server self-test...")

    server = HTTPServer(("127.0.0.1", PORT), MockCalDAVHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base = f"http://127.0.0.1:{PORT}"
    passed = 0
    failed = 0

    def check(
        name: str,
        url: str,
        *,
        method: str = "GET",
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
        expect_status: int = 200,
        expect_body_contains: list[str] | None = None,
        expect_body_not_contains: list[str] | None = None,
        expect_header: tuple[str, str] | None = None,
    ):
        nonlocal passed, failed
        req = urllib.request.Request(url, method=method)
        if data is not None:
            req.data = data
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)

        try:
            resp = urllib.request.urlopen(req)
            status = resp.getcode()
            body = resp.read().decode("utf-8", errors="replace")
            resp_headers = resp.headers
        except urllib.error.HTTPError as e:
            status = e.code
            body = e.read().decode("utf-8", errors="replace")
            resp_headers = e.headers

        if status != expect_status:
            print(f"  ✗ {name}: expected status {expect_status}, got {status}")
            print(f"    body: {body[:200]}")
            failed += 1
            return

        if expect_body_contains:
            for text in expect_body_contains:
                if text not in body:
                    print(f"  ✗ {name}: expected body to contain '{text}'")
                    print(f"    body: {body[:300]}")
                    failed += 1
                    return

        if expect_body_not_contains:
            for text in expect_body_not_contains:
                if text in body:
                    print(f"  ✗ {name}: expected body NOT to contain '{text}'")
                    failed += 1
                    return

        if expect_header:
            hdr_name, hdr_substr = expect_header
            hdr_val = resp_headers.get(hdr_name, "")
            if hdr_substr not in hdr_val:
                print(f"  ✗ {name}: expected header {hdr_name} to contain '{hdr_substr}', got '{hdr_val}'")
                failed += 1
                return

        print(f"  ✓ {name}")
        passed += 1

    # -- 1. Health check --
    check(
        "GET /health → 200",
        f"{base}/health",
        expect_body_contains=["ok", "mock-caldav"],
    )

    # -- 2. PROPFIND / (Depth:0) → current-user-principal --
    check(
        "PROPFIND / → 207, current-user-principal",
        f"{base}/",
        method="PROPFIND",
        headers={"Depth": "0", "Content-Type": "application/xml"},
        data=b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:current-user-principal/></d:prop></d:propfind>',
        expect_status=207,
        expect_body_contains=["current-user-principal", "/principals/user/"],
    )

    # -- 3. PROPFIND /principals/user/ (Depth:0) → calendar-home-set --
    check(
        "PROPFIND /principals/user/ → 207, calendar-home-set",
        f"{base}/principals/user/",
        method="PROPFIND",
        headers={"Depth": "0", "Content-Type": "application/xml"},
        data=b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><c:calendar-home-set xmlns:c="urn:ietf:params:xml:ns:caldav"/></d:prop></d:propfind>',
        expect_status=207,
        expect_body_contains=["calendar-home-set", "/calendars/user/"],
    )

    # -- 4. PROPFIND /calendars/user/ (Depth:1) → Work + Personal --
    check(
        "PROPFIND /calendars/user/ → 207, Work + Personal",
        f"{base}/calendars/user/",
        method="PROPFIND",
        headers={"Depth": "1", "Content-Type": "application/xml"},
        data=b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:displayname/></d:prop></d:propfind>',
        expect_status=207,
        expect_body_contains=["Work", "Personal"],
    )

    # -- 5. REPORT initial sync → 3 events + sync-token --
    sync_body_initial = (
        b'<?xml version="1.0"?>'
        b'<d:sync-collection xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
        b'<d:sync-token/><d:sync-level>1</d:sync-level>'
        b'<d:prop><d:getetag/><c:calendar-data/></d:prop>'
        b'</d:sync-collection>'
    )
    check(
        "REPORT initial sync → 207, Team Standup + sync-token",
        f"{base}/calendars/user/work/",
        method="REPORT",
        headers={"Content-Type": "application/xml", "Depth": "1"},
        data=sync_body_initial,
        expect_status=207,
        expect_body_contains=["Team Standup", "sync-token-initial-001", "calendar-data"],
    )

    # -- 6. REPORT incremental sync → new token, no calendar-data --
    sync_body_incremental = (
        b'<?xml version="1.0"?>'
        b'<d:sync-collection xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
        b'<d:sync-token>sync-token-initial-001</d:sync-token><d:sync-level>1</d:sync-level>'
        b'<d:prop><d:getetag/><c:calendar-data/></d:prop>'
        b'</d:sync-collection>'
    )
    check(
        "REPORT incremental sync → 207, new sync-token, no events",
        f"{base}/calendars/user/work/",
        method="REPORT",
        headers={"Content-Type": "application/xml", "Depth": "1"},
        data=sync_body_incremental,
        expect_status=207,
        expect_body_contains=["sync-token-incremental-002"],
        expect_body_not_contains=["calendar-data"],
    )

    # -- 7. GET event .ics → 200, ETag header, VCALENDAR body --
    check(
        "GET team-standup-001.ics → 200, ETag, VCALENDAR",
        f"{base}/calendars/user/work/team-standup-001.ics",
        expect_status=200,
        expect_body_contains=["BEGIN:VCALENDAR", "Team Standup", "VALARM"],
        expect_header=("ETag", "etag-team-standup-001"),
    )

    # -- 8. PUT with matching ETag → 204 --
    current_etag = '"etag-team-standup-001-v1"'
    check(
        "PUT team-standup-001.ics (matching ETag) → 204",
        f"{base}/calendars/user/work/team-standup-001.ics",
        method="PUT",
        headers={
            "Content-Type": "text/calendar; charset=utf-8",
            "If-Match": current_etag,
        },
        data=EVENT_TIMED.encode("utf-8"),
        expect_status=204,
    )

    # -- 9. PUT with wrong ETag → 412 (failure path) --
    check(
        "PUT team-standup-001.ics (wrong ETag) → 412",
        f"{base}/calendars/user/work/team-standup-001.ics",
        method="PUT",
        headers={
            "Content-Type": "text/calendar; charset=utf-8",
            "If-Match": '"stale-etag"',
        },
        data=EVENT_TIMED.encode("utf-8"),
        expect_status=412,
    )

    # -- 10. DELETE event → 204 --
    check(
        "DELETE team-standup-001.ics → 204",
        f"{base}/calendars/user/work/team-standup-001.ics",
        method="DELETE",
        expect_status=204,
    )

    # -- 11. GET deleted event → 404 --
    check(
        "GET deleted event → 404",
        f"{base}/calendars/user/work/team-standup-001.ics",
        expect_status=404,
    )

    # -- 12. GET unknown event → 404 --
    check(
        "GET unknown event → 404",
        f"{base}/calendars/user/work/nonexistent-uid.ics",
        expect_status=404,
    )

    # -- Summary --
    total = passed + failed
    print(f"\n[selftest] {passed}/{total} passed, {failed} failed")
    server.shutdown()
    sys.exit(0 if failed == 0 else 1)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()

    print(f"[mock-caldav] Starting on port {PORT}...", file=sys.stderr, flush=True)
    server = HTTPServer(("0.0.0.0", PORT), MockCalDAVHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[mock-caldav] Shutting down.", file=sys.stderr, flush=True)
        server.shutdown()
