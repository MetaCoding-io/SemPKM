"""Mock Google Calendar API + OAuth token server for E2E testing.

A lightweight HTTP server returning canned REST responses based on URL
path matching.  Designed to run inside Docker alongside the SemPKM test
stack so the GCalClient and auth module can be redirected here via
GCAL_API_URL and GOOGLE_TOKEN_URL environment variables.

Endpoints:
    GET  /health                                          → 200 health check
    POST /oauth/token                                     → token exchange / refresh
    GET  /calendar/v3/users/me/calendarList               → calendar list
    GET  /calendar/v3/calendars/{id}/events               → events list (syncToken)
    PATCH /calendar/v3/calendars/{id}/events/{eventId}    → event PATCH (RSVP)

Usage:
    python server.py              # Start on port 8080
    python server.py --selftest   # Verify canned responses then exit
"""

from __future__ import annotations

import io
import json
import re
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

PORT = 8080

# ---------------------------------------------------------------------------
# Canned response data
# ---------------------------------------------------------------------------

TOKEN_RESPONSE = {
    "access_token": "mock-access-token",
    "refresh_token": "mock-refresh-token",
    "expires_in": 3600,
    "token_type": "Bearer",
}

CALENDAR_LIST_RESPONSE = {
    "kind": "calendar#calendarList",
    "items": [
        {
            "kind": "calendar#calendarListEntry",
            "id": "test@example.com",
            "summary": "Test User",
            "primary": True,
            "accessRole": "owner",
            "timeZone": "America/New_York",
            "selected": True,
        },
        {
            "kind": "calendar#calendarListEntry",
            "id": "team-calendar-id",
            "summary": "Team Calendar",
            "primary": False,
            "accessRole": "writer",
            "timeZone": "America/New_York",
            "selected": True,
        },
    ],
}

_TIMED_EVENT = {
    "kind": "calendar#event",
    "id": "event-timed-001",
    "status": "confirmed",
    "htmlLink": "https://calendar.google.com/event?eid=event-timed-001",
    "summary": "Team Standup",
    "description": "Daily team standup meeting to discuss progress and blockers.",
    "location": "Conference Room A",
    "creator": {"email": "test@example.com", "self": True},
    "organizer": {"email": "test@example.com", "self": True},
    "start": {
        "dateTime": "2026-03-20T09:00:00-04:00",
        "timeZone": "America/New_York",
    },
    "end": {
        "dateTime": "2026-03-20T09:30:00-04:00",
        "timeZone": "America/New_York",
    },
    "attendees": [
        {
            "email": "test@example.com",
            "self": True,
            "responseStatus": "accepted",
        },
        {
            "email": "colleague@example.com",
            "responseStatus": "needsAction",
        },
    ],
    "conferenceData": {
        "entryPoints": [
            {
                "entryPointType": "video",
                "uri": "https://meet.google.com/abc-defg-hij",
                "label": "meet.google.com/abc-defg-hij",
            },
        ],
        "conferenceSolution": {
            "key": {"type": "hangoutsMeet"},
            "name": "Google Meet",
        },
        "conferenceId": "abc-defg-hij",
    },
    "iCalUID": "event-timed-001@google.com",
    "created": "2026-03-15T10:00:00.000Z",
    "updated": "2026-03-18T14:00:00.000Z",
}

_ALLDAY_EVENT = {
    "kind": "calendar#event",
    "id": "event-allday-001",
    "status": "confirmed",
    "htmlLink": "https://calendar.google.com/event?eid=event-allday-001",
    "summary": "Company Holiday",
    "description": "Office closed for company holiday.",
    "creator": {"email": "admin@example.com"},
    "organizer": {"email": "admin@example.com"},
    "start": {"date": "2026-03-25"},
    "end": {"date": "2026-03-26"},
    "transparency": "transparent",
    "iCalUID": "event-allday-001@google.com",
    "created": "2026-03-01T08:00:00.000Z",
    "updated": "2026-03-01T08:00:00.000Z",
}

_RECURRING_EVENT = {
    "kind": "calendar#event",
    "id": "event-recurring-001",
    "status": "confirmed",
    "htmlLink": "https://calendar.google.com/event?eid=event-recurring-001",
    "summary": "Weekly Review",
    "description": "End-of-week review and retrospective.",
    "creator": {"email": "test@example.com", "self": True},
    "organizer": {"email": "test@example.com", "self": True},
    "start": {
        "dateTime": "2026-03-20T16:00:00-04:00",
        "timeZone": "America/New_York",
    },
    "end": {
        "dateTime": "2026-03-20T17:00:00-04:00",
        "timeZone": "America/New_York",
    },
    "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=FR"],
    "iCalUID": "event-recurring-001@google.com",
    "created": "2026-01-10T12:00:00.000Z",
    "updated": "2026-03-18T14:00:00.000Z",
}

# Keyed by event ID for PATCH merging
_EVENTS_BY_ID = {
    "event-timed-001": _TIMED_EVENT,
    "event-allday-001": _ALLDAY_EVENT,
    "event-recurring-001": _RECURRING_EVENT,
}

EVENTS_RESPONSE = {
    "kind": "calendar#events",
    "summary": "Test User",
    "updated": "2026-03-18T14:00:00.000Z",
    "timeZone": "America/New_York",
    "accessRole": "owner",
    "nextSyncToken": "mock-sync-token-1",
    "items": [_TIMED_EVENT, _ALLDAY_EVENT, _RECURRING_EVENT],
}

INCREMENTAL_EVENTS_RESPONSE = {
    "kind": "calendar#events",
    "summary": "Test User",
    "updated": "2026-03-19T10:00:00.000Z",
    "timeZone": "America/New_York",
    "accessRole": "owner",
    "nextSyncToken": "mock-sync-token-2",
    "items": [],
}

# Route patterns
_EVENTS_LIST_RE = re.compile(r"^/calendar/v3/calendars/([^/]+)/events$")
_EVENT_PATCH_RE = re.compile(r"^/calendar/v3/calendars/([^/]+)/events/([^/]+)$")


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class MockGCalHandler(BaseHTTPRequestHandler):
    """Handles GET, POST, and PATCH requests mimicking Google Calendar API."""

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = parse_qs(parsed.query)

        if path == "/health":
            self._json_response(200, {"status": "ok"})

        elif path == "/calendar/v3/users/me/calendarList":
            self._json_response(200, CALENDAR_LIST_RESPONSE)

        elif _EVENTS_LIST_RE.match(path):
            self._handle_events_list(qs)

        else:
            self._json_response(404, {"error": {"code": 404, "message": "Not Found"}})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/oauth/token":
            self._handle_token()
        else:
            self._json_response(404, {"error": {"code": 404, "message": "Not Found"}})

    def do_PATCH(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        m = _EVENT_PATCH_RE.match(path)
        if m:
            self._handle_event_patch(m.group(1), m.group(2))
        else:
            self._json_response(404, {"error": {"code": 404, "message": "Not Found"}})

    # -- endpoint handlers --

    def _handle_token(self) -> None:
        """Handle POST /oauth/token — code exchange or refresh."""
        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length)

        # Parse form-encoded body
        body_qs = parse_qs(raw.decode("utf-8", errors="replace"))
        grant_type = body_qs.get("grant_type", [None])[0]

        if grant_type not in ("authorization_code", "refresh_token"):
            self._json_response(400, {
                "error": "unsupported_grant_type",
                "error_description": f"Invalid grant_type: {grant_type}",
            })
            return

        self._json_response(200, TOKEN_RESPONSE)

    def _handle_events_list(self, qs: dict) -> None:
        """Handle GET /calendar/v3/calendars/{id}/events with syncToken logic."""
        sync_token_values = qs.get("syncToken", [])
        sync_token = sync_token_values[0] if sync_token_values else None

        if sync_token is None:
            # Full sync — return all events
            self._json_response(200, EVENTS_RESPONSE)
        elif sync_token == "mock-sync-token-1":
            # Incremental sync — nothing changed
            self._json_response(200, INCREMENTAL_EVENTS_RESPONSE)
        else:
            # Unknown sync token → 410 Gone (client should do full resync)
            self._json_response(410, {
                "error": {
                    "code": 410,
                    "message": "Sync token is no longer valid, a full sync is required.",
                    "errors": [{
                        "domain": "calendar",
                        "reason": "fullSyncRequired",
                        "message": "Sync token is no longer valid, a full sync is required.",
                    }],
                },
            })

    def _handle_event_patch(self, calendar_id: str, event_id: str) -> None:
        """Handle PATCH — merge JSON body with canned event, return result."""
        base = _EVENTS_BY_ID.get(event_id)
        if base is None:
            self._json_response(404, {
                "error": {"code": 404, "message": f"Event not found: {event_id}"},
            })
            return

        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length)
        try:
            patch_data = json.loads(raw) if raw else {}
        except (json.JSONDecodeError, ValueError):
            self._json_response(400, {
                "error": {"code": 400, "message": "Invalid JSON body"},
            })
            return

        # Merge: shallow copy of base, overwrite with patch fields
        result = dict(base)
        result.update(patch_data)
        result["updated"] = "2026-03-19T12:00:00.000Z"
        self._json_response(200, result)

    # -- helpers --

    def _json_response(self, status: int, body: dict | list) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
        self._log_request(self.command, self.path, status)

    def _log_request(self, method: str, path: str, status: int) -> None:
        print(f"[mock-gcal] {method} {path} → {status}", file=sys.stderr, flush=True)

    def log_message(self, fmt: str, *args) -> None:  # type: ignore[override]
        """Override to prefix all access logs for easy filtering."""
        print(f"[mock-gcal] {fmt % args}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Self-test mode
# ---------------------------------------------------------------------------

def selftest() -> None:
    """Start mock server in background thread, exercise all endpoints, exit."""
    import threading
    import urllib.request
    import urllib.error

    print("[selftest] Starting mock Google Calendar API self-test...")

    server = HTTPServer(("127.0.0.1", PORT), MockGCalHandler)
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
        content_type: str | None = None,
        expect_status: int = 200,
        expect_check=None,
    ):
        nonlocal passed, failed
        req = urllib.request.Request(url, method=method)
        if data is not None:
            req.data = data
        if content_type:
            req.add_header("Content-Type", content_type)

        try:
            resp = urllib.request.urlopen(req)
            status = resp.getcode()
            body = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            status = e.code
            try:
                body = json.loads(e.read())
            except Exception:
                body = {}

        if status != expect_status:
            print(f"  ✗ {name}: expected status {expect_status}, got {status}")
            failed += 1
            return

        if expect_check and not expect_check(body):
            print(f"  ✗ {name}: response body check failed")
            failed += 1
            return

        print(f"  ✓ {name}")
        passed += 1

    # -- 1. Health --
    check("GET /health", f"{base}/health",
          expect_check=lambda b: b.get("status") == "ok")

    # -- 2. Token exchange (authorization_code) --
    check("POST /oauth/token (authorization_code)",
          f"{base}/oauth/token",
          method="POST",
          data=b"grant_type=authorization_code&code=mock-auth-code&client_id=cid&client_secret=csec&redirect_uri=http://localhost",
          content_type="application/x-www-form-urlencoded",
          expect_check=lambda b: b.get("access_token") == "mock-access-token" and b.get("refresh_token") == "mock-refresh-token")

    # -- 3. Token refresh (refresh_token) --
    check("POST /oauth/token (refresh_token)",
          f"{base}/oauth/token",
          method="POST",
          data=b"grant_type=refresh_token&refresh_token=mock-refresh-token&client_id=cid&client_secret=csec",
          content_type="application/x-www-form-urlencoded",
          expect_check=lambda b: b.get("access_token") == "mock-access-token")

    # -- 4. Token endpoint with bad grant_type --
    check("POST /oauth/token (bad grant_type → 400)",
          f"{base}/oauth/token",
          method="POST",
          data=b"grant_type=invalid_type",
          content_type="application/x-www-form-urlencoded",
          expect_status=400,
          expect_check=lambda b: b.get("error") == "unsupported_grant_type")

    # -- 5. Calendar list --
    check("GET /calendar/v3/users/me/calendarList",
          f"{base}/calendar/v3/users/me/calendarList",
          expect_check=lambda b: b.get("kind") == "calendar#calendarList" and len(b.get("items", [])) == 2)

    # -- 6. Events list (full sync — no syncToken) --
    check("GET events (full sync)",
          f"{base}/calendar/v3/calendars/test%40example.com/events",
          expect_check=lambda b: (
              len(b.get("items", [])) == 3
              and b.get("nextSyncToken") == "mock-sync-token-1"
          ))

    # -- 7. Events list (incremental — valid syncToken) --
    check("GET events (incremental sync)",
          f"{base}/calendar/v3/calendars/test%40example.com/events?syncToken=mock-sync-token-1",
          expect_check=lambda b: (
              len(b.get("items", [])) == 0
              and b.get("nextSyncToken") == "mock-sync-token-2"
          ))

    # -- 8. Events list (invalid syncToken → 410) --
    check("GET events (invalid syncToken → 410)",
          f"{base}/calendar/v3/calendars/test%40example.com/events?syncToken=stale-token",
          expect_status=410,
          expect_check=lambda b: b.get("error", {}).get("code") == 410)

    # -- 9. Event PATCH (RSVP echo-back) --
    rsvp_body = json.dumps({
        "attendees": [
            {"email": "test@example.com", "self": True, "responseStatus": "declined"},
        ],
        "attendeesOmitted": True,
    }).encode()
    check("PATCH event (RSVP)",
          f"{base}/calendar/v3/calendars/test%40example.com/events/event-timed-001",
          method="PATCH",
          data=rsvp_body,
          content_type="application/json",
          expect_check=lambda b: (
              b.get("id") == "event-timed-001"
              and b.get("attendeesOmitted") is True
              and any(a.get("responseStatus") == "declined" for a in b.get("attendees", []))
          ))

    # -- 10. PATCH unknown event → 404 --
    check("PATCH unknown event → 404",
          f"{base}/calendar/v3/calendars/test%40example.com/events/nonexistent",
          method="PATCH",
          data=b"{}",
          content_type="application/json",
          expect_status=404)

    # -- 11. Unknown path → 404 --
    check("GET unknown path → 404",
          f"{base}/unknown/endpoint",
          expect_status=404)

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

    print(f"[mock-gcal] Starting on port {PORT}...", file=sys.stderr, flush=True)
    server = HTTPServer(("0.0.0.0", PORT), MockGCalHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[mock-gcal] Shutting down.", file=sys.stderr, flush=True)
        server.shutdown()
