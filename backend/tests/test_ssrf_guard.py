"""Tests for the SSRF guard utility (app.security.ssrf).

Validates that validate_outbound_url() blocks dangerous URLs (loopback,
private, link-local, reserved, multicast, non-http schemes) and passes
safe public URLs. DNS resolution is mocked for deterministic results.
"""

from unittest.mock import patch

import pytest

from app.security.ssrf import validate_outbound_url


# ---------------------------------------------------------------------------
# Helper: mock getaddrinfo returning a single IPv4 address
# ---------------------------------------------------------------------------


def _mock_getaddrinfo_factory(ip: str):
    """Return a mock getaddrinfo that resolves any hostname to the given IP."""
    def _mock_getaddrinfo(hostname, port, **kwargs):
        return [
            (2, 1, 6, "", (ip, port or 443)),  # AF_INET, SOCK_STREAM, TCP
        ]
    return _mock_getaddrinfo


def _mock_getaddrinfo_ipv6_factory(ip: str):
    """Return a mock getaddrinfo that resolves to an IPv6 address."""
    def _mock_getaddrinfo(hostname, port, **kwargs):
        return [
            (10, 1, 6, "", (ip, port or 443, 0, 0)),  # AF_INET6
        ]
    return _mock_getaddrinfo


# ---------------------------------------------------------------------------
# Tests: blocked URLs
# ---------------------------------------------------------------------------


class TestSSRFBlocked:
    """URLs that must be rejected by the SSRF guard."""

    def test_loopback_127(self):
        """http://127.0.0.1 resolves to loopback — blocked."""
        with patch(
            "app.security.ssrf.socket.getaddrinfo",
            _mock_getaddrinfo_factory("127.0.0.1"),
        ):
            with pytest.raises(ValueError, match="loopback"):
                validate_outbound_url("http://127.0.0.1/api")

    def test_localhost(self):
        """http://localhost is in the blocked hostnames list."""
        with pytest.raises(ValueError, match="blocked address"):
            validate_outbound_url("http://localhost/path")

    def test_ipv6_loopback(self):
        """http://[::1] — hostname resolves to ::1 which is blocked."""
        with pytest.raises(ValueError, match="blocked address"):
            validate_outbound_url("http://[::1]/path")

    def test_ipv6_loopback_resolved(self):
        """IPv6 loopback via DNS resolution."""
        with patch(
            "app.security.ssrf.socket.getaddrinfo",
            _mock_getaddrinfo_ipv6_factory("::1"),
        ):
            with pytest.raises(ValueError, match="loopback"):
                validate_outbound_url("http://some-host-resolving-to-loopback/api")

    def test_private_10(self):
        """http://10.0.0.1 — RFC 1918 private range."""
        with patch(
            "app.security.ssrf.socket.getaddrinfo",
            _mock_getaddrinfo_factory("10.0.0.1"),
        ):
            with pytest.raises(ValueError, match="private"):
                validate_outbound_url("http://10.0.0.1/internal")

    def test_private_172_16(self):
        """http://172.16.0.1 — RFC 1918 private range."""
        with patch(
            "app.security.ssrf.socket.getaddrinfo",
            _mock_getaddrinfo_factory("172.16.0.1"),
        ):
            with pytest.raises(ValueError, match="private"):
                validate_outbound_url("http://172.16.0.1/admin")

    def test_private_192_168(self):
        """http://192.168.1.1 — RFC 1918 private range."""
        with patch(
            "app.security.ssrf.socket.getaddrinfo",
            _mock_getaddrinfo_factory("192.168.1.1"),
        ):
            with pytest.raises(ValueError, match="private"):
                validate_outbound_url("http://192.168.1.1/router")

    def test_aws_metadata(self):
        """http://169.254.169.254 — AWS/cloud metadata endpoint (link-local)."""
        with patch(
            "app.security.ssrf.socket.getaddrinfo",
            _mock_getaddrinfo_factory("169.254.169.254"),
        ):
            with pytest.raises(ValueError, match="link-local|private"):
                validate_outbound_url("http://169.254.169.254/latest/meta-data/")

    def test_ftp_scheme(self):
        """ftp://example.com — non-http scheme blocked."""
        with pytest.raises(ValueError, match="scheme.*not allowed"):
            validate_outbound_url("ftp://example.com/file.txt")

    def test_file_scheme(self):
        """file:///etc/passwd — non-http scheme blocked."""
        with pytest.raises(ValueError, match="scheme.*not allowed"):
            validate_outbound_url("file:///etc/passwd")

    def test_zero_address(self):
        """http://0.0.0.0 is in the blocked hostnames list."""
        with pytest.raises(ValueError, match="blocked address"):
            validate_outbound_url("http://0.0.0.0/path")

    def test_empty_url(self):
        """Empty string is rejected."""
        with pytest.raises(ValueError, match="empty"):
            validate_outbound_url("")

    def test_none_url(self):
        """None is rejected."""
        with pytest.raises(ValueError, match="empty"):
            validate_outbound_url(None)

    def test_multicast(self):
        """Multicast addresses (224.0.0.0/4) are blocked."""
        with patch(
            "app.security.ssrf.socket.getaddrinfo",
            _mock_getaddrinfo_factory("224.0.0.1"),
        ):
            with pytest.raises(ValueError, match="multicast"):
                validate_outbound_url("http://multicast.example.com/feed")


# ---------------------------------------------------------------------------
# Tests: allowed URLs
# ---------------------------------------------------------------------------


class TestSSRFAllowed:
    """URLs that must pass the SSRF guard."""

    def test_public_https(self):
        """https://example.com with public IP passes."""
        with patch(
            "app.security.ssrf.socket.getaddrinfo",
            _mock_getaddrinfo_factory("93.184.216.34"),
        ):
            # Should not raise
            validate_outbound_url("https://example.com")

    def test_public_https_with_port(self):
        """https://federation.example.org:8443/api passes."""
        with patch(
            "app.security.ssrf.socket.getaddrinfo",
            _mock_getaddrinfo_factory("93.184.216.34"),
        ):
            validate_outbound_url("https://federation.example.org:8443/api")

    def test_public_http(self):
        """http:// with public IP passes."""
        with patch(
            "app.security.ssrf.socket.getaddrinfo",
            _mock_getaddrinfo_factory("8.8.8.8"),
        ):
            validate_outbound_url("http://open-data.example.org/feed")

    def test_public_ipv6(self):
        """Public IPv6 address passes."""
        with patch(
            "app.security.ssrf.socket.getaddrinfo",
            _mock_getaddrinfo_ipv6_factory("2606:2800:220:1:248:1893:25c8:1946"),
        ):
            validate_outbound_url("https://ipv6.example.com/api")


# ---------------------------------------------------------------------------
# Tests: error messages include reason
# ---------------------------------------------------------------------------


class TestSSRFErrorMessages:
    """Verify that ValueError messages contain actionable information."""

    def test_scheme_error_includes_scheme(self):
        with pytest.raises(ValueError) as exc_info:
            validate_outbound_url("ftp://example.com")
        assert "ftp" in str(exc_info.value)
        assert "scheme" in str(exc_info.value).lower()

    def test_private_error_includes_ip(self):
        with patch(
            "app.security.ssrf.socket.getaddrinfo",
            _mock_getaddrinfo_factory("10.0.0.1"),
        ):
            with pytest.raises(ValueError) as exc_info:
                validate_outbound_url("http://10.0.0.1/api")
            assert "10.0.0.1" in str(exc_info.value)
            assert "private" in str(exc_info.value).lower()

    def test_loopback_error_includes_hostname(self):
        with pytest.raises(ValueError) as exc_info:
            validate_outbound_url("http://localhost/secret")
        msg = str(exc_info.value)
        assert "localhost" in msg

    def test_metadata_error_includes_link_local(self):
        with patch(
            "app.security.ssrf.socket.getaddrinfo",
            _mock_getaddrinfo_factory("169.254.169.254"),
        ):
            with pytest.raises(ValueError) as exc_info:
                validate_outbound_url("http://169.254.169.254/latest/")
            msg = str(exc_info.value).lower()
            assert "link-local" in msg or "private" in msg


# ---------------------------------------------------------------------------
# Tests: DNS resolution failure
# ---------------------------------------------------------------------------


class TestSSRFDNSFailure:
    """Verify behaviour when hostname cannot be resolved."""

    def test_unresolvable_hostname(self):
        """Unresolvable hostname raises ValueError."""
        import socket

        with patch(
            "app.security.ssrf.socket.getaddrinfo",
            side_effect=socket.gaierror("Name or service not known"),
        ):
            with pytest.raises(ValueError, match="cannot resolve"):
                validate_outbound_url("https://nonexistent.invalid/api")
