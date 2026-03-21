"""Mock Microsoft Graph API + OAuth token server for E2E testing.

A lightweight HTTP server returning canned REST responses based on URL
path matching.  Designed to run inside Docker alongside the SemPKM test
stack so the OutlookClient and auth module can be redirected here via
OUTLOOK_API_URL, OUTLOOK_TOKEN_URL, and OUTLOOK_AUTH_URL environment
variables.

Endpoints:
    GET  /health                                              → 200 health check
    POST /common/oauth2/v2.0/token                            → token exchange / refresh
    GET  /v1.0/me                                             → user profile
    GET  /v1.0/me/calendars                                   → calendar list
    GET  /v1.0/me/calendars/{id}/events/delta                 → events delta (initial or incremental)
    PATCH /v1.0/me/calendars/{calId}/events/{eventId}         → event PATCH (RSVP)

Usage:
    python server.py              # Start on port 8080
    python server.py --selftest   # Verify canned responses then exit
"""

from __future__ import annotations

import json
import re
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

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

USER_PROFILE = {
    "displayName": "Test User",
    "mail": "test@example.com",
    "userPrincipalName": "test@example.com",
}

CALENDAR_LIST_RESPONSE = {
    "value": [
        {
            "id": "cal-primary-001",
            "name": "Calendar",
            "isDefaultCalendar": True,
            "color": "auto",
            "canEdit": True,
        },
        {
            "id": "cal-secondary-002",
            "name": "Team Events",
            "isDefaultCalendar": False,
            "color": "lightBlue",
            "canEdit": True,
        },
    ],
}

_TIMED_EVENT = {
    "id": "event-timed-001",
    "subject": "Team Standup",
    "body": {
        "contentType": "html",
        "content": "<p>Daily standup</p>",
    },
    "start": {
        "dateTime": "2026-03-20T09:00:00.0000000",
        "timeZone": "America/New_York",
    },
    "end": {
        "dateTime": "2026-03-20T09:30:00.0000000",
        "timeZone": "America/New_York",
    },
    "attendees": [
        {
            "emailAddress": {"name": "Test User", "address": "test@example.com"},
            "status": {"response": "accepted", "time": "2026-03-18T14:00:00Z"},
        },
        {
            "emailAddress": {"name": "Colleague", "address": "colleague@example.com"},
            "status": {"response": "none", "time": "0001-01-01T00:00:00Z"},
        },
    ],
    "categories": ["Work", "Important"],
    "showAs": "busy",
    "sensitivity": "normal",
    "location": {"displayName": "Conference Room A"},
    "onlineMeeting": {"joinUrl": "https://teams.microsoft.com/meet/123"},
    "isAllDay": False,
    "organizer": {
        "emailAddress": {"name": "Test User", "address": "test@example.com"},
    },
    "createdDateTime": "2026-03-15T10:00:00Z",
    "lastModifiedDateTime": "2026-03-18T14:00:00Z",
}

_ALLDAY_EVENT = {
    "id": "event-allday-002",
    "subject": "Company Holiday",
    "body": {
        "contentType": "text",
        "content": "Office closed.",
    },
    "start": {
        "dateTime": "2026-03-25",
        "timeZone": "UTC",
    },
    "end": {
        "dateTime": "2026-03-26",
        "timeZone": "UTC",
    },
    "isAllDay": True,
    "showAs": "free",
    "sensitivity": "private",
    "categories": [],
    "attendees": [],
    "organizer": {
        "emailAddress": {"name": "Admin", "address": "admin@example.com"},
    },
    "createdDateTime": "2026-03-01T08:00:00Z",
    "lastModifiedDateTime": "2026-03-01T08:00:00Z",
}

_RECURRING_EVENT = {
    "id": "event-recurring-003",
    "subject": "Weekly Review",
    "body": {
        "contentType": "text",
        "content": "End-of-week review.",
    },
    "start": {
        "dateTime": "2026-03-20T16:00:00.0000000",
        "timeZone": "America/New_York",
    },
    "end": {
        "dateTime": "2026-03-20T17:00:00.0000000",
        "timeZone": "America/New_York",
    },
    "recurrence": {
        "pattern": {
            "type": "weekly",
            "interval": 1,
            "daysOfWeek": ["monday", "wednesday", "friday"],
        },
        "range": {
            "type": "endDate",
            "startDate": "2026-01-01",
            "endDate": "2026-06-30",
        },
    },
    "isAllDay": False,
    "showAs": "busy",
    "sensitivity": "normal",
    "categories": [],
    "attendees": [],
    "organizer": {
        "emailAddress": {"name": "Test User", "address": "test@example.com"},
    },
    "createdDateTime": "2026-01-10T12:00:00Z",
    "lastModifiedDateTime": "2026-03-18T14:00:00Z",
}

# Keyed by event ID for PATCH merging
_EVENTS_BY_ID = {
    "event-timed-001": _TIMED_EVENT,
    "event-allday-002": _ALLDAY_EVENT,
    "event-recurring-003": _RECURRING_EVENT,
}

# Default calendar ID used in deltaLink URLs
_DEFAULT_CAL_ID = "cal-primary-001"

# The @odata.deltaLink must be a full URL (not relative)
_DELTA_LINK_TEMPLATE = (
    "http://localhost:8080/v1.0/me/calendars/{cal_id}"
    "/events/delta?$deltatoken=mock-delta-1"
)

EVENTS_RESPONSE = {
    "value": [_TIMED_EVENT, _ALLDAY_EVENT, _RECURRING_EVENT],
    "@odata.deltaLink": _DELTA_LINK_TEMPLATE.format(cal_id=_DEFAULT_CAL_ID),
}

INCREMENTAL_EVENTS_RESPONSE = {
    "value": [],
    "@odata.deltaLink": _DELTA_LINK_TEMPLATE.format(cal_id=_DEFAULT_CAL_ID).replace(
        "mock-delta-1", "mock-delta-2"
    ),
}

# Route patterns
_EVENTS_DELTA_RE = re.compile(r"^/v1\.0/me/calendars/([^/]+)/events/delta$")
_EVENT_PATCH_RE = re.compile(r"^/v1\.0/me/calendars/([^/]+)/events/([^/]+)$")


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class MockOutlookHandler(BaseHTTPRequestHandler):
    """Handles GET, POST, and PATCH requests mimicking Microsoft Graph API."""

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = parse_qs(parsed.query)

        if path == "/health":
            self._json_response(200, {"status": "ok"})

        elif path == "/v1.0/me":
            self._json_response(200, USER_PROFILE)

        elif path == "/v1.0/me/calendars":
            self._json_response(200, CALENDAR_LIST_RESPONSE)

        elif _EVENTS_DELTA_RE.match(path):
            self._handle_events_delta(path, qs)

        else:
            self._json_response(404, {
                "error": {"code": "NotFound", "message": "Resource not found"},
            })

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/common/oauth2/v2.0/token":
            self._handle_token()
        else:
            self._json_response(404, {
                "error": {"code": "NotFound", "message": "Resource not found"},
            })

    def do_PATCH(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        m = _EVENT_PATCH_RE.match(path)
        if m:
            self._handle_event_patch(m.group(1), m.group(2))
        else:
            self._json_response(404, {
                "error": {"code": "NotFound", "message": "Resource not found"},
            })

    # -- endpoint handlers --

    def _handle_token(self) -> None:
        """Handle POST /common/oauth2/v2.0/token — code exchange or refresh."""
        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length)

        body_qs = parse_qs(raw.decode("utf-8", errors="replace"))
        grant_type = body_qs.get("grant_type", [None])[0]

        if grant_type not in ("authorization_code", "refresh_token"):
            self._json_response(400, {
                "error": "unsupported_grant_type",
                "error_description": f"AADSTS70000: Invalid grant_type: {grant_type}",
            })
            return

        self._json_response(200, TOKEN_RESPONSE)

    def _handle_events_delta(self, path: str, qs: dict) -> None:
        """Handle GET /v1.0/me/calendars/{id}/events/delta with deltatoken logic."""
        delta_token_values = qs.get("$deltatoken", [])
        delta_token = delta_token_values[0] if delta_token_values else None

        if delta_token is None:
            # Initial sync — return all events with deltaLink
            self._json_response(200, EVENTS_RESPONSE)
        elif delta_token == "mock-delta-1":
            # Incremental sync — nothing changed
            self._json_response(200, INCREMENTAL_EVENTS_RESPONSE)
        else:
            # Unknown delta token → return empty with fresh deltaLink
            # Microsoft Graph returns 200 with empty value (not 410 like Google)
            self._json_response(200, INCREMENTAL_EVENTS_RESPONSE)

    def _handle_event_patch(self, calendar_id: str, event_id: str) -> None:
        """Handle PATCH — merge JSON body with canned event, return result."""
        base = _EVENTS_BY_ID.get(event_id)
        if base is None:
            self._json_response(404, {
                "error": {
                    "code": "ErrorItemNotFound",
                    "message": f"The specified object was not found in the store., The process failed to get the correct properties.",
                },
            })
            return

        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length)
        try:
            patch_data = json.loads(raw) if raw else {}
        except (json.JSONDecodeError, ValueError):
            self._json_response(400, {
                "error": {"code": "BadRequest", "message": "Invalid JSON body"},
            })
            return

        # Shallow merge: base event fields overwritten by patch
        result = dict(base)
        result.update(patch_data)
        result["lastModifiedDateTime"] = "2026-03-19T12:00:00Z"
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
        print(f"[mock-outlook] {method} {path} → {status}", file=sys.stderr, flush=True)

    def log_message(self, fmt: str, *args) -> None:  # type: ignore[override]
        """Override to prefix all access logs for easy filtering."""
        print(f"[mock-outlook] {fmt % args}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Self-test mode
# ---------------------------------------------------------------------------

def selftest() -> None:
    """Start mock server in background thread, exercise all endpoints, exit."""
    import threading
    import urllib.request
    import urllib.error

    print("[selftest] Starting mock Microsoft Graph API self-test...")

    server = HTTPServer(("127.0.0.1", PORT), MockOutlookHandler)
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
            print(f"    body: {json.dumps(body)[:200]}")
            failed += 1
            return

        if expect_check and not expect_check(body):
            print(f"  ✗ {name}: response body check failed")
            print(f"    body: {json.dumps(body)[:200]}")
            failed += 1
            return

        print(f"  ✓ {name}")
        passed += 1

    cal_id = "cal-primary-001"

    # -- 1. Health --
    check("GET /health", f"{base}/health",
          expect_check=lambda b: b.get("status") == "ok")

    # -- 2. Token exchange (authorization_code) --
    check("POST /token (authorization_code)",
          f"{base}/common/oauth2/v2.0/token",
          method="POST",
          data=b"grant_type=authorization_code&code=mock-auth-code&client_id=cid&client_secret=csec&redirect_uri=http://localhost",
          content_type="application/x-www-form-urlencoded",
          expect_check=lambda b: (
              b.get("access_token") == "mock-access-token"
              and b.get("refresh_token") == "mock-refresh-token"
          ))

    # -- 3. Calendar list --
    check("GET /v1.0/me/calendars",
          f"{base}/v1.0/me/calendars",
          expect_check=lambda b: len(b.get("value", [])) == 2)

    # -- 4. Events delta (initial — no deltatoken) --
    check("GET events/delta (initial sync)",
          f"{base}/v1.0/me/calendars/{cal_id}/events/delta",
          expect_check=lambda b: (
              len(b.get("value", [])) == 3
              and "@odata.deltaLink" in b
          ))

    # -- 5. Events delta (incremental — valid deltatoken) --
    check("GET events/delta (incremental sync)",
          f"{base}/v1.0/me/calendars/{cal_id}/events/delta?$deltatoken=mock-delta-1",
          expect_check=lambda b: (
              len(b.get("value", [])) == 0
              and "@odata.deltaLink" in b
          ))

    # -- 6. Timed event has attendees, categories, showAs, onlineMeeting --
    check("Timed event fields",
          f"{base}/v1.0/me/calendars/{cal_id}/events/delta",
          expect_check=lambda b: _check_timed_event(b.get("value", [])))

    # -- 7. All-day event has isAllDay=true --
    check("All-day event isAllDay=true",
          f"{base}/v1.0/me/calendars/{cal_id}/events/delta",
          expect_check=lambda b: _check_allday_event(b.get("value", [])))

    # -- 8. Recurring event has recurrence.pattern.type = "weekly" --
    check("Recurring event recurrence pattern",
          f"{base}/v1.0/me/calendars/{cal_id}/events/delta",
          expect_check=lambda b: _check_recurring_event(b.get("value", [])))

    # -- 9. RSVP PATCH (valid event) --
    rsvp_body = json.dumps({
        "attendees": [
            {
                "emailAddress": {"name": "Test User", "address": "test@example.com"},
                "status": {"response": "declined"},
            },
        ],
    }).encode()
    check("PATCH event (RSVP)",
          f"{base}/v1.0/me/calendars/{cal_id}/events/event-timed-001",
          method="PATCH",
          data=rsvp_body,
          content_type="application/json",
          expect_check=lambda b: (
              b.get("id") == "event-timed-001"
              and any(
                  a.get("status", {}).get("response") == "declined"
                  for a in b.get("attendees", [])
              )
          ))

    # -- 10. PATCH unknown event → 404 (error path) --
    check("PATCH unknown event → 404",
          f"{base}/v1.0/me/calendars/{cal_id}/events/nonexistent-id",
          method="PATCH",
          data=b"{}",
          content_type="application/json",
          expect_status=404,
          expect_check=lambda b: b.get("error", {}).get("code") == "ErrorItemNotFound")

    # -- 11. User profile --
    check("GET /v1.0/me (user profile)",
          f"{base}/v1.0/me",
          expect_check=lambda b: b.get("mail") == "test@example.com")

    # -- 12. @odata.deltaLink is a full URL with $deltatoken --
    check("deltaLink is full URL with $deltatoken",
          f"{base}/v1.0/me/calendars/{cal_id}/events/delta",
          expect_check=lambda b: (
              b.get("@odata.deltaLink", "").startswith("http")
              and "$deltatoken" in b.get("@odata.deltaLink", "")
          ))

    # -- 13. Unknown path → 404 --
    check("GET unknown path → 404",
          f"{base}/unknown/endpoint",
          expect_status=404)

    # -- Summary --
    total = passed + failed
    print(f"\n[selftest] {passed}/{total} passed, {failed} failed")
    server.shutdown()
    sys.exit(0 if failed == 0 else 1)


# -- selftest helpers --

def _check_timed_event(events: list) -> bool:
    """Verify timed event has attendees, categories, showAs, onlineMeeting."""
    for ev in events:
        if ev.get("id") == "event-timed-001":
            return (
                len(ev.get("attendees", [])) >= 2
                and len(ev.get("categories", [])) >= 1
                and ev.get("showAs") == "busy"
                and ev.get("onlineMeeting", {}).get("joinUrl") is not None
            )
    return False


def _check_allday_event(events: list) -> bool:
    """Verify all-day event has isAllDay=true."""
    for ev in events:
        if ev.get("id") == "event-allday-002":
            return ev.get("isAllDay") is True
    return False


def _check_recurring_event(events: list) -> bool:
    """Verify recurring event has recurrence.pattern.type = 'weekly'."""
    for ev in events:
        if ev.get("id") == "event-recurring-003":
            return (
                ev.get("recurrence", {})
                .get("pattern", {})
                .get("type") == "weekly"
            )
    return False


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()

    print(f"[mock-outlook] Starting on port {PORT}...", file=sys.stderr, flush=True)
    server = HTTPServer(("0.0.0.0", PORT), MockOutlookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[mock-outlook] Shutting down.", file=sys.stderr, flush=True)
        server.shutdown()
