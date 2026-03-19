"""Regression tests for SDK AppContext network permission parsing.

The AppContext.http property must correctly parse both:
- dict-style: ``{"domains": ["*.example.com"]}`` → extract domains list
- list-style: ``["api.linear.app", "api.google.com"]`` → use directly

Prior to the fix, list-style permissions (the format real manifests use)
resulted in ``allowed_domains=[]``, blocking all external HTTP.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestNetworkPermissionParsing:
    """Verify that AppContext.http gets the correct allowed_domains."""

    def _make_context(self, permissions: dict) -> object:
        """Create an AppContext with the given permissions."""
        from sempkm_app_sdk.context import AppContext

        return AppContext(
            app_id="test-app",
            app_dir=Path("/tmp/test-app"),
            platform_url="http://localhost:8000",
            app_token="test-token",
            permissions=permissions,
        )

    def test_list_network_permissions(self):
        """List-style network perms (real manifest format) populate allowed_domains."""
        ctx = self._make_context({
            "network": ["api.linear.app", "api.google.com"],
        })

        http = ctx.http
        assert http._allowed_domains == ["api.linear.app", "api.google.com"]

    def test_dict_network_permissions(self):
        """Dict-style network perms still work (backward compatible)."""
        ctx = self._make_context({
            "network": {"domains": ["*.example.com", "api.github.com"]},
        })

        http = ctx.http
        assert http._allowed_domains == ["*.example.com", "api.github.com"]

    def test_dict_network_no_domains_key(self):
        """Dict-style with missing 'domains' key defaults to empty list."""
        ctx = self._make_context({
            "network": {"rate_limit": 100},
        })

        http = ctx.http
        assert http._allowed_domains == []

    def test_no_network_permission(self):
        """No network key at all → empty allowed_domains (all blocked)."""
        ctx = self._make_context({
            "commands": ["object.create"],
        })

        http = ctx.http
        assert http._allowed_domains == []

    def test_empty_list_network(self):
        """Explicit empty list → empty allowed_domains."""
        ctx = self._make_context({
            "network": [],
        })

        http = ctx.http
        assert http._allowed_domains == []

    def test_wildcard_in_list(self):
        """Wildcard pattern in list-style perms is preserved."""
        ctx = self._make_context({
            "network": ["*"],
        })

        http = ctx.http
        assert http._allowed_domains == ["*"]

    def test_http_client_enforces_list_domains(self):
        """End-to-end: HttpClient domain check works with list-parsed domains."""
        ctx = self._make_context({
            "network": ["api.google.com", "oauth2.googleapis.com"],
        })

        http = ctx.http

        # Allowed domain should not raise
        http._check_domain("https://api.google.com/calendar/v3/calendars")

        # Blocked domain should raise
        with pytest.raises(PermissionError, match="not permitted"):
            http._check_domain("https://evil.example.com/steal")
