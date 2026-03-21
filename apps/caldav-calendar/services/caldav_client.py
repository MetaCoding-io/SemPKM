"""CalDAVClient — WebDAV/CalDAV client for calendar operations.

Speaks the CalDAV protocol (XML-over-HTTP) via PROPFIND, REPORT, PUT,
and DELETE methods. Handles the full discovery chain (server → principal
→ calendar-home → calendar-list) and event CRUD with ETag-based
optimistic concurrency.

Uses stdlib xml.etree.ElementTree for XML generation and parsing,
and the SDK HttpClient for HTTP requests.

Decision D224: hand-crafted XML with stdlib ET + httpx via SDK HttpClient.
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

logger = logging.getLogger("caldav.client")

# ---------------------------------------------------------------------------
# XML namespace constants
# ---------------------------------------------------------------------------

DAV_NS = "DAV:"
CALDAV_NS = "urn:ietf:params:xml:ns:caldav"
CS_NS = "http://calendarserver.org/ns/"

_NS_MAP = {
    "d": DAV_NS,
    "c": CALDAV_NS,
    "cs": CS_NS,
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CalDAVError(Exception):
    """Base exception for CalDAV protocol errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body


class CalDAVAuthError(CalDAVError):
    """Authentication/authorization error (401/403 or missing credentials)."""


class CalDAVNotFoundError(CalDAVError):
    """Resource not found (404)."""


class CalDAVConflictError(CalDAVError):
    """ETag conflict (409/412) — resource was modified concurrently."""


# ---------------------------------------------------------------------------
# XML builder helpers
# ---------------------------------------------------------------------------


def _build_propfind_xml(properties: list[tuple[str, str]]) -> str:
    """Build a PROPFIND XML body requesting the given properties.

    Args:
        properties: List of (namespace, local_name) tuples.
            Example: [("DAV:", "current-user-principal")]

    Returns:
        XML string for the PROPFIND request body.
    """
    # Register namespaces for clean output
    for prefix, uri in _NS_MAP.items():
        ET.register_namespace(prefix, uri)

    propfind = ET.Element(f"{{{DAV_NS}}}propfind")
    prop = ET.SubElement(propfind, f"{{{DAV_NS}}}prop")

    for ns, name in properties:
        ET.SubElement(prop, f"{{{ns}}}{name}")

    return ET.tostring(propfind, encoding="unicode", xml_declaration=True)


def _build_sync_collection_xml(
    sync_token: str | None,
    props: list[tuple[str, str]] | None = None,
) -> str:
    """Build a sync-collection REPORT XML body.

    Args:
        sync_token: Previous sync token, or None/empty for full sync.
        props: Properties to request. Defaults to getetag + calendar-data.

    Returns:
        XML string for the REPORT request body.
    """
    if props is None:
        props = [(DAV_NS, "getetag"), (CALDAV_NS, "calendar-data")]

    for prefix, uri in _NS_MAP.items():
        ET.register_namespace(prefix, uri)

    root = ET.Element(f"{{{DAV_NS}}}sync-collection")

    token_el = ET.SubElement(root, f"{{{DAV_NS}}}sync-token")
    token_el.text = sync_token or ""

    level_el = ET.SubElement(root, f"{{{DAV_NS}}}sync-level")
    level_el.text = "1"

    prop = ET.SubElement(root, f"{{{DAV_NS}}}prop")
    for ns, name in props:
        ET.SubElement(prop, f"{{{ns}}}{name}")

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def _build_calendar_query_xml() -> str:
    """Build a calendar-query REPORT XML body requesting all VEVENTs.

    Returns:
        XML string for the REPORT request body.
    """
    for prefix, uri in _NS_MAP.items():
        ET.register_namespace(prefix, uri)

    root = ET.Element(f"{{{CALDAV_NS}}}calendar-query")

    prop = ET.SubElement(root, f"{{{DAV_NS}}}prop")
    ET.SubElement(prop, f"{{{DAV_NS}}}getetag")
    ET.SubElement(prop, f"{{{CALDAV_NS}}}calendar-data")

    # Filter to only VEVENT components
    filter_el = ET.SubElement(root, f"{{{CALDAV_NS}}}filter")
    comp_filter = ET.SubElement(
        filter_el, f"{{{CALDAV_NS}}}comp-filter", attrib={"name": "VCALENDAR"}
    )
    ET.SubElement(
        comp_filter, f"{{{CALDAV_NS}}}comp-filter", attrib={"name": "VEVENT"}
    )

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


# ---------------------------------------------------------------------------
# XML response parser
# ---------------------------------------------------------------------------


def _parse_multistatus(xml_text: str) -> list[dict]:
    """Parse a WebDAV multistatus XML response.

    Handles two response shapes:
    1. Normal: <response><href/><propstat><prop>...</prop><status/></propstat></response>
    2. Deleted (sync-collection): <response><href/><status>HTTP/1.1 404 ...</status></response>

    Args:
        xml_text: Raw XML string from server.

    Returns:
        List of dicts with keys: href, status, properties.
        Properties dict has simplified keys like "getetag", "displayname", etc.
    """
    if not xml_text or not xml_text.strip():
        return []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        logger.warning("Failed to parse multistatus XML")
        return []

    results = []

    for response in root.findall(f"{{{DAV_NS}}}response"):
        href_el = response.find(f"{{{DAV_NS}}}href")
        href = href_el.text.strip() if href_el is not None and href_el.text else ""

        # Check for direct status (deleted resources in sync-collection)
        direct_status_el = response.find(f"{{{DAV_NS}}}status")
        propstat_els = response.findall(f"{{{DAV_NS}}}propstat")

        if not propstat_els and direct_status_el is not None:
            # Deleted resource — status without propstat
            results.append({
                "href": href,
                "status": direct_status_el.text.strip() if direct_status_el.text else "",
                "properties": {},
            })
            continue

        # Normal response with propstat(s)
        for propstat in propstat_els:
            status_el = propstat.find(f"{{{DAV_NS}}}status")
            status = status_el.text.strip() if status_el is not None and status_el.text else ""

            properties: dict[str, str] = {}
            prop_el = propstat.find(f"{{{DAV_NS}}}prop")
            if prop_el is not None:
                for child in prop_el:
                    # Strip namespace, use local name as key
                    local_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag

                    # Some properties contain nested elements (e.g., href inside
                    # current-user-principal or calendar-home-set)
                    nested_href = child.find(f"{{{DAV_NS}}}href")
                    if nested_href is not None and nested_href.text:
                        properties[local_name] = nested_href.text.strip()
                    elif child.text and child.text.strip():
                        properties[local_name] = child.text.strip()
                    else:
                        # Check for supported-calendar-component-set
                        if local_name == "supported-calendar-component-set":
                            comps = []
                            for comp in child.findall(f"{{{CALDAV_NS}}}comp"):
                                name = comp.get("name", "")
                                if name:
                                    comps.append(name)
                            properties[local_name] = ",".join(comps)
                        else:
                            # Element exists but has no text/children
                            properties[local_name] = ""

            results.append({
                "href": href,
                "status": status,
                "properties": properties,
            })

    return results


# ---------------------------------------------------------------------------
# CalDAVClient
# ---------------------------------------------------------------------------


def _extract_sync_token(xml_text: str) -> str | None:
    """Extract root-level ``<d:sync-token>`` from a multistatus XML response.

    CalDAV sync-collection REPORT responses include the next sync-token
    as a direct child of ``<d:multistatus>``.  The normal entry parser
    does not capture this because it only walks ``<d:response>`` children.

    Returns the token string, or ``None`` if absent.
    """
    if not xml_text or not xml_text.strip():
        return None
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None
    token_el = root.find(f"{{{DAV_NS}}}sync-token")
    if token_el is not None and token_el.text and token_el.text.strip():
        return token_el.text.strip()
    return None


class CalDAVClient:
    """Authenticated WebDAV/CalDAV client.

    Handles PROPFIND, REPORT, PUT, DELETE requests with proper
    Content-Type, Depth, and auth headers.

    Args:
        http_client: SDK HttpClient instance.
        state_client: SDK StateClient for reading auth credentials.
    """

    def __init__(self, http_client, state_client) -> None:
        self._http = http_client
        self._state = state_client

    async def _get_auth_headers(self) -> dict[str, str]:
        """Read credentials from state and produce Basic auth header.

        Raises:
            CalDAVAuthError: If credentials are not configured.
        """
        # Import here to avoid circular import at module level
        try:
            from services.auth import get_auth_headers
        except ImportError:
            try:
                from auth import get_auth_headers
            except ImportError:
                raise CalDAVAuthError(
                    "Auth module not available",
                    status_code=None,
                    response_body=None,
                )

        username = await self._state.get("username")
        password = await self._state.get("password")

        if not username or not password:
            raise CalDAVAuthError(
                "CalDAV credentials not configured",
                status_code=401,
                response_body=None,
            )

        return get_auth_headers(username, password)

    # ---- low-level WebDAV methods -----------------------------------------

    async def _propfind(
        self,
        url: str,
        body: str,
        depth: str = "0",
    ) -> list[dict]:
        """Send a PROPFIND request and parse the multistatus response.

        Args:
            url: Target URL.
            body: XML request body.
            depth: Depth header value ("0" or "1").

        Returns:
            Parsed multistatus response entries.

        Raises:
            CalDAVAuthError: On 401/403.
            CalDAVNotFoundError: On 404.
            CalDAVError: On other errors.
        """
        auth_headers = await self._get_auth_headers()
        headers = {
            **auth_headers,
            "Content-Type": "application/xml; charset=utf-8",
            "Depth": depth,
        }

        logger.info("PROPFIND %s (Depth: %s)", url, depth)
        resp = await self._http.request("PROPFIND", url, headers=headers, content=body)

        return self._handle_response(resp, url, "PROPFIND")

    async def _report(self, url: str, body: str) -> list[dict]:
        """Send a REPORT request and parse the multistatus response.

        Args:
            url: Target calendar URL.
            body: XML request body (sync-collection or calendar-query).

        Returns:
            Parsed multistatus response entries.

        Raises:
            CalDAVAuthError: On 401/403.
            CalDAVNotFoundError: On 404.
            CalDAVError: On other errors.
        """
        auth_headers = await self._get_auth_headers()
        headers = {
            **auth_headers,
            "Content-Type": "application/xml; charset=utf-8",
            "Depth": "1",
        }

        logger.info("REPORT %s", url)
        resp = await self._http.request("REPORT", url, headers=headers, content=body)

        return self._handle_response(resp, url, "REPORT")

    async def _report_raw(self, url: str, body: str) -> tuple[list[dict], str]:
        """Send a REPORT request and return both parsed entries and raw XML.

        Same as ``_report()`` but also captures ``resp.text`` before parsing,
        so the caller can extract root-level elements (like sync-token) that
        ``_parse_multistatus`` does not return.

        Returns:
            ``(entries, raw_xml)``
        """
        auth_headers = await self._get_auth_headers()
        headers = {
            **auth_headers,
            "Content-Type": "application/xml; charset=utf-8",
            "Depth": "1",
        }

        logger.info("REPORT (raw) %s", url)
        resp = await self._http.request("REPORT", url, headers=headers, content=body)

        raw_xml = resp.text
        entries = self._handle_response(resp, url, "REPORT")
        return (entries, raw_xml)

    def _handle_response(self, resp, url: str, method: str) -> list[dict]:
        """Check response status and parse multistatus body.

        Args:
            resp: HTTP response object.
            url: Request URL (for logging).
            method: HTTP method (for logging).

        Returns:
            Parsed multistatus entries.

        Raises:
            CalDAVAuthError: On 401/403.
            CalDAVNotFoundError: On 404.
            CalDAVError: On 5xx or other errors.
        """
        status = resp.status_code
        logger.info("%s %s → %d", method, url, status)

        if status == 207:
            return _parse_multistatus(resp.text)

        body_text = resp.text

        if status in (401, 403):
            raise CalDAVAuthError(
                f"{method} {url} failed: {status}",
                status_code=status,
                response_body=body_text,
            )
        if status == 404:
            raise CalDAVNotFoundError(
                f"{method} {url}: resource not found",
                status_code=404,
                response_body=body_text,
            )
        if status >= 500:
            raise CalDAVError(
                f"{method} {url} server error: {status}",
                status_code=status,
                response_body=body_text,
            )

        raise CalDAVError(
            f"{method} {url} unexpected status: {status}",
            status_code=status,
            response_body=body_text,
        )

    # ---- discovery chain --------------------------------------------------

    async def discover_principal(self, server_url: str) -> str:
        """Discover the current user's principal URL.

        Sends PROPFIND Depth:0 to server_url requesting
        DAV:current-user-principal.

        Args:
            server_url: CalDAV server base URL.

        Returns:
            Absolute principal URL.
        """
        body = _build_propfind_xml([(DAV_NS, "current-user-principal")])
        entries = await self._propfind(server_url, body, depth="0")

        for entry in entries:
            principal_href = entry["properties"].get("current-user-principal", "")
            if principal_href:
                resolved = urljoin(server_url, principal_href)
                logger.info("Discovered principal: %s", resolved)
                return resolved

        raise CalDAVError(
            "Could not discover user principal from server response",
            status_code=None,
            response_body=None,
        )

    async def discover_calendar_home(self, principal_url: str) -> str:
        """Discover the calendar home set URL.

        Sends PROPFIND Depth:0 to principal_url requesting
        caldav:calendar-home-set.

        Args:
            principal_url: User's principal URL (from discover_principal).

        Returns:
            Absolute calendar home URL.
        """
        body = _build_propfind_xml([(CALDAV_NS, "calendar-home-set")])
        entries = await self._propfind(principal_url, body, depth="0")

        for entry in entries:
            home_href = entry["properties"].get("calendar-home-set", "")
            if home_href:
                resolved = urljoin(principal_url, home_href)
                logger.info("Discovered calendar home: %s", resolved)
                return resolved

        raise CalDAVError(
            "Could not discover calendar home set from principal response",
            status_code=None,
            response_body=None,
        )

    async def discover_calendars(self, server_url: str) -> list[dict]:
        """Full discovery chain: server → principal → home → calendar list.

        Args:
            server_url: CalDAV server base URL.

        Returns:
            List of calendar dicts with keys:
            href, displayname, ctag, supported_components.
            Only calendars that support VEVENT are included.
        """
        principal_url = await self.discover_principal(server_url)
        home_url = await self.discover_calendar_home(principal_url)

        # PROPFIND Depth:1 on calendar home to list calendars
        body = _build_propfind_xml([
            (DAV_NS, "displayname"),
            (CS_NS, "getctag"),
            (CALDAV_NS, "supported-calendar-component-set"),
        ])
        entries = await self._propfind(home_url, body, depth="1")

        calendars = []
        for entry in entries:
            props = entry["properties"]
            # Skip the home collection itself (usually first entry at Depth:1)
            # Resolve relative href against home_url for comparison
            resolved_href = urljoin(home_url, entry["href"])
            if resolved_href.rstrip("/") == home_url.rstrip("/"):
                continue

            # Parse supported components
            comp_str = props.get("supported-calendar-component-set", "")
            supported = [c.strip() for c in comp_str.split(",") if c.strip()] if comp_str else []

            # Filter to VEVENT-supporting calendars only
            # If no supported-calendar-component-set is declared, assume VEVENT support
            if supported and "VEVENT" not in supported:
                logger.debug(
                    "Skipping calendar %s — no VEVENT support (has: %s)",
                    entry["href"],
                    supported,
                )
                continue

            calendars.append({
                "href": resolved_href,
                "displayname": props.get("displayname", ""),
                "ctag": props.get("getctag") or None,
                "supported_components": supported,
            })

        logger.info("Discovered %d VEVENT calendars", len(calendars))
        return calendars

    # ---- event operations -------------------------------------------------

    async def get_events(
        self,
        calendar_url: str,
        sync_token: str | None = None,
    ) -> tuple[list[dict], str | None]:
        """Fetch events from a calendar.

        Uses sync-collection REPORT if sync_token is provided (incremental),
        or calendar-query REPORT for full sync.

        Args:
            calendar_url: URL of the calendar collection.
            sync_token: Previous sync token for incremental sync.

        Returns:
            (events, new_sync_token) where each event is a dict with
            href, etag, calendar_data, status. Deleted resources have
            status containing "404" and no calendar_data.
        """
        if sync_token:
            body = _build_sync_collection_xml(sync_token)
            logger.info("Sync-collection REPORT on %s (incremental)", calendar_url)
        else:
            body = _build_calendar_query_xml()
            logger.info("Calendar-query REPORT on %s (full sync)", calendar_url)

        entries, raw_xml = await self._report_raw(calendar_url, body)

        events = []
        new_sync_token = _extract_sync_token(raw_xml)

        for entry in entries:
            props = entry.get("properties", {})

            event = {
                "href": entry.get("href", ""),
                "etag": props.get("getetag", ""),
                "calendar_data": props.get("calendar-data", ""),
                "status": entry.get("status", ""),
            }
            events.append(event)

        return (events, new_sync_token)

    async def get_event(self, event_url: str) -> dict:
        """Fetch a single event resource.

        Args:
            event_url: Full URL to the .ics resource.

        Returns:
            Dict with etag and calendar_data.

        Raises:
            CalDAVAuthError: On 401/403.
            CalDAVNotFoundError: On 404.
        """
        auth_headers = await self._get_auth_headers()
        headers = {**auth_headers}

        logger.info("GET %s", event_url)
        resp = await self._http.get(event_url, headers=headers)

        if resp.status_code == 200:
            etag = resp.headers.get("ETag", "")
            return {
                "etag": etag,
                "calendar_data": resp.text,
            }

        if resp.status_code in (401, 403):
            raise CalDAVAuthError(
                f"GET {event_url} failed: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )
        if resp.status_code == 404:
            raise CalDAVNotFoundError(
                f"GET {event_url}: not found",
                status_code=404,
                response_body=resp.text,
            )

        raise CalDAVError(
            f"GET {event_url} failed: {resp.status_code}",
            status_code=resp.status_code,
            response_body=resp.text,
        )

    async def put_event(
        self,
        event_url: str,
        ics_data: str,
        etag: str | None = None,
    ) -> str:
        """Create or update an event via PUT.

        Args:
            event_url: Full URL for the .ics resource.
            ics_data: Complete VCALENDAR text.
            etag: For updates, the current ETag (sends If-Match).
                  For creates, None (sends If-None-Match: *).

        Returns:
            New ETag from the response.

        Raises:
            CalDAVConflictError: On 412 (ETag mismatch).
            CalDAVAuthError: On 401/403.
        """
        auth_headers = await self._get_auth_headers()
        headers = {
            **auth_headers,
            "Content-Type": "text/calendar; charset=utf-8",
        }

        if etag is not None:
            # Update — require ETag match
            headers["If-Match"] = etag
        else:
            # Create — require resource doesn't exist
            headers["If-None-Match"] = "*"

        logger.info(
            "PUT %s (etag=%s)",
            event_url,
            etag[:20] + "..." if etag and len(etag) > 20 else etag,
        )
        resp = await self._http.put(event_url, headers=headers, content=ics_data)

        if resp.status_code in (200, 201, 204):
            new_etag = resp.headers.get("ETag", "")
            logger.info("PUT %s → %d (new etag: %s)", event_url, resp.status_code, new_etag)
            return new_etag

        if resp.status_code in (409, 412):
            raise CalDAVConflictError(
                f"PUT {event_url}: ETag conflict ({resp.status_code})",
                status_code=resp.status_code,
                response_body=resp.text,
            )
        if resp.status_code in (401, 403):
            raise CalDAVAuthError(
                f"PUT {event_url} failed: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        raise CalDAVError(
            f"PUT {event_url} failed: {resp.status_code}",
            status_code=resp.status_code,
            response_body=resp.text,
        )

    async def delete_event(
        self,
        event_url: str,
        etag: str | None = None,
    ) -> None:
        """Delete an event resource.

        Args:
            event_url: Full URL to the .ics resource.
            etag: If provided, sends If-Match header for safe delete.

        Raises:
            CalDAVConflictError: On 412 (ETag mismatch).
            CalDAVAuthError: On 401/403.
        """
        auth_headers = await self._get_auth_headers()
        headers = {**auth_headers}

        if etag is not None:
            headers["If-Match"] = etag

        logger.info("DELETE %s (etag=%s)", event_url, etag)
        resp = await self._http.delete(event_url, headers=headers)

        if resp.status_code in (200, 204):
            logger.info("DELETE %s → %d", event_url, resp.status_code)
            return

        if resp.status_code in (409, 412):
            raise CalDAVConflictError(
                f"DELETE {event_url}: ETag conflict ({resp.status_code})",
                status_code=resp.status_code,
                response_body=resp.text,
            )
        if resp.status_code in (401, 403):
            raise CalDAVAuthError(
                f"DELETE {event_url} failed: {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )
        if resp.status_code == 404:
            # Already deleted — not an error for DELETE
            logger.info("DELETE %s → 404 (already gone)", event_url)
            return

        raise CalDAVError(
            f"DELETE {event_url} failed: {resp.status_code}",
            status_code=resp.status_code,
            response_body=resp.text,
        )
