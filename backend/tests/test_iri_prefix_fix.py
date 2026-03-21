"""Tests for the IRI prefix whitelist fix (D171).

Validates that ``CommandClient._check_iri_prefix()`` correctly scopes
enforcement to only ``urn:sempkm:app:*`` and ``urn:sempkm:data:*``
namespaces, while allowing model IRIs, standard vocabularies, user-types,
and the app's own namespace.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

import httpx

from sempkm_app_sdk.clients.commands import CommandClient


APP_ID = "test-app"
IRI_PREFIX = f"urn:sempkm:app:{APP_ID}:"
ALLOWED_COMMANDS = {"object.create", "object.patch", "edge.create", "body.set"}


def _make_client() -> CommandClient:
    """Create a CommandClient configured for ``test-app``."""
    http = AsyncMock(spec=httpx.AsyncClient)
    return CommandClient(
        client=http,
        allowed_commands=ALLOWED_COMMANDS,
        iri_prefix=IRI_PREFIX,
    )


class TestIRIPrefixWhitelist:
    """Tests for the namespace-scoped IRI prefix policy."""

    def test_model_type_iri_passes(self) -> None:
        """Model namespace IRIs (``urn:sempkm:model:*``) are always allowed."""
        client = _make_client()
        # Should not raise — model type IRI
        client._check_permissions(
            "object.patch",
            {"iri": "urn:sempkm:model:rss-feeds:Article"},
        )

    def test_standard_http_vocab_passes(self) -> None:
        """HTTP standard vocabulary IRIs pass unchecked."""
        client = _make_client()
        client._check_permissions(
            "edge.create",
            {"source": "urn:sempkm:app:test-app:x", "target": "http://purl.org/dc/terms/title"},
        )

    def test_standard_https_vocab_passes(self) -> None:
        """HTTPS standard vocabulary IRIs pass unchecked."""
        client = _make_client()
        client._check_permissions(
            "edge.create",
            {"source": "urn:sempkm:app:test-app:x", "target": "https://schema.org/name"},
        )

    def test_user_types_iri_passes(self) -> None:
        """User-types namespace (``urn:sempkm:user-types:*``) passes unchecked."""
        client = _make_client()
        client._check_permissions(
            "object.patch",
            {"iri": "urn:sempkm:user-types:CustomClass"},
        )

    def test_own_app_iri_passes(self) -> None:
        """App's own namespace IRI is allowed."""
        client = _make_client()
        client._check_permissions(
            "object.patch",
            {"iri": "urn:sempkm:app:test-app:item1"},
        )

    def test_foreign_app_iri_blocked(self) -> None:
        """A foreign app's namespace IRI raises PermissionError."""
        client = _make_client()
        with pytest.raises(PermissionError, match=r"urn:sempkm:app:other-app:thing"):
            client._check_permissions(
                "object.patch",
                {"iri": "urn:sempkm:app:other-app:thing"},
            )

    def test_data_namespace_iri_blocked(self) -> None:
        """The ``urn:sempkm:data:*`` namespace raises PermissionError."""
        client = _make_client()
        with pytest.raises(PermissionError, match=r"urn:sempkm:data:other:thing"):
            client._check_permissions(
                "body.set",
                {"iri": "urn:sempkm:data:other:thing"},
            )

    def test_non_iri_strings_ignored(self) -> None:
        """Plain text values in IRI fields are not subject to prefix checks."""
        client = _make_client()
        # _check_iri_prefix returns True for non-IRI strings (no namespace match)
        assert client._check_iri_prefix("just-a-plain-string") is True
        assert client._check_iri_prefix("My Article Title") is True
        assert client._check_iri_prefix("") is True

    def test_other_urn_namespaces_pass(self) -> None:
        """Non-sempkm URNs like ``urn:uuid:*`` are allowed."""
        client = _make_client()
        client._check_permissions(
            "object.patch",
            {"iri": "urn:uuid:550e8400-e29b-41d4-a716-446655440000"},
        )

    def test_rdf_type_reference_pattern(self) -> None:
        """Typical ``object.create`` with model type IRI and own-app IRI passes.

        This is the real-world pattern: type references the model, the object
        IRI belongs to the app.
        """
        client = _make_client()
        # object.create has no IRI fields in _IRI_PARAMS, so the type value
        # isn't validated — but edge.create checks source + target:
        client._check_permissions(
            "edge.create",
            {
                "source": "urn:sempkm:app:test-app:article-123",
                "target": "urn:sempkm:model:rss-feeds:Article",
            },
        )

    def test_mixed_valid_and_invalid_iri_fails(self) -> None:
        """When one IRI field is valid and another is invalid, reject."""
        client = _make_client()
        with pytest.raises(PermissionError, match=r"urn:sempkm:app:other-app:stolen"):
            client._check_permissions(
                "edge.create",
                {
                    "source": "urn:sempkm:app:test-app:mine",  # valid
                    "target": "urn:sempkm:app:other-app:stolen",  # foreign
                },
            )

    def test_error_message_includes_offending_iri_and_prefix(self) -> None:
        """PermissionError message includes both the offending IRI and the required prefix."""
        client = _make_client()
        with pytest.raises(PermissionError) as exc_info:
            client._check_permissions(
                "object.patch",
                {"iri": "urn:sempkm:app:evil-app:data"},
            )
        msg = str(exc_info.value)
        assert "urn:sempkm:app:evil-app:data" in msg
        assert IRI_PREFIX in msg

    def test_check_iri_prefix_direct(self) -> None:
        """Direct unit tests on ``_check_iri_prefix`` for each branch."""
        client = _make_client()
        # Whitelisted
        assert client._check_iri_prefix("urn:sempkm:model:basic:Thing") is True
        assert client._check_iri_prefix("urn:sempkm:user-types:Foo") is True
        assert client._check_iri_prefix("http://example.org/vocab#x") is True
        assert client._check_iri_prefix("https://schema.org/name") is True
        # Own app
        assert client._check_iri_prefix("urn:sempkm:app:test-app:obj1") is True
        # Blocked
        assert client._check_iri_prefix("urn:sempkm:app:foreign:obj") is False
        assert client._check_iri_prefix("urn:sempkm:data:bucket:key") is False
        # Other URNs
        assert client._check_iri_prefix("urn:isbn:0451450523") is True
