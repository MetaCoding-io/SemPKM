"""SSRF (Server-Side Request Forgery) guard for outbound HTTP requests.

Validates URLs before any outbound HTTP call to prevent requests to
internal/private network addresses. Blocks loopback, private, link-local,
reserved, and multicast IP ranges. Restricts schemes to http/https.

Usage:
    from app.security.ssrf import validate_outbound_url

    validate_outbound_url(url)  # raises ValueError if blocked
"""

import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Hostnames that resolve to loopback but might bypass IP checks
_BLOCKED_HOSTNAMES = frozenset({
    "localhost",
    "localhost.",
    "0.0.0.0",
    "::1",
    "[::]",
    "[::1]",
    "[0:0:0:0:0:0:0:0]",
    "[0:0:0:0:0:0:0:1]",
})

_ALLOWED_SCHEMES = frozenset({"http", "https"})


def validate_outbound_url(url: str) -> None:
    """Validate that a URL is safe for outbound HTTP requests.

    Checks:
    - Scheme must be http or https
    - Hostname must not be a known loopback alias
    - All resolved IP addresses must not be loopback, private,
      link-local, reserved, or multicast

    Args:
        url: The URL to validate.

    Raises:
        ValueError: If the URL targets a blocked address or uses
            a disallowed scheme. The message includes the reason.
    """
    if not url or not isinstance(url, str):
        raise ValueError("SSRF blocked: empty or invalid URL")

    parsed = urlparse(url)

    # -- Scheme check --
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"SSRF blocked: scheme '{parsed.scheme}' not allowed "
            f"(must be http or https)"
        )

    # -- Hostname extraction --
    hostname = parsed.hostname  # lowercase, brackets stripped for IPv6
    if not hostname:
        raise ValueError("SSRF blocked: no hostname in URL")

    # -- Known blocked hostnames --
    # Check both the extracted hostname and the raw netloc for bracket forms
    netloc_lower = (parsed.netloc or "").lower().split(":")[0]  # strip port
    if hostname in _BLOCKED_HOSTNAMES or netloc_lower in _BLOCKED_HOSTNAMES:
        raise ValueError(
            f"SSRF blocked: hostname '{hostname}' resolves to a blocked address"
        )

    # -- DNS resolution + IP check --
    try:
        addr_infos = socket.getaddrinfo(
            hostname, parsed.port or 443, proto=socket.IPPROTO_TCP
        )
    except socket.gaierror as exc:
        raise ValueError(
            f"SSRF blocked: cannot resolve hostname '{hostname}': {exc}"
        ) from exc

    if not addr_infos:
        raise ValueError(
            f"SSRF blocked: hostname '{hostname}' resolved to no addresses"
        )

    for family, _type, _proto, _canonname, sockaddr in addr_infos:
        ip_str = sockaddr[0]
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            # If we can't parse the resolved address, block it
            raise ValueError(
                f"SSRF blocked: unparseable resolved address '{ip_str}' "
                f"for hostname '{hostname}'"
            )

        if addr.is_loopback:
            raise ValueError(
                f"SSRF blocked: '{hostname}' resolves to loopback address {addr}"
            )
        if addr.is_link_local:
            raise ValueError(
                f"SSRF blocked: '{hostname}' resolves to link-local address {addr}"
            )
        if addr.is_multicast:
            raise ValueError(
                f"SSRF blocked: '{hostname}' resolves to multicast address {addr}"
            )
        if addr.is_private:
            raise ValueError(
                f"SSRF blocked: '{hostname}' resolves to private address {addr}"
            )
        if addr.is_reserved:
            raise ValueError(
                f"SSRF blocked: '{hostname}' resolves to reserved address {addr}"
            )

    logger.debug("SSRF check passed for %s", url)
