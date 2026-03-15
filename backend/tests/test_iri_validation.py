"""Tests for _validate_iri() from browser/router.py.

This function is the primary defense against SPARQL injection from
user-controlled URL path segments. Tests cover valid schemes (http,
https, urn), all forbidden injection characters, missing components,
structural invalidity, and injection payloads.
"""

import pytest

<<<<<<< HEAD
from app.browser._helpers import _validate_iri
=======
from app.browser.router import _validate_iri
>>>>>>> gsd/M002/S03


# ── Valid IRIs (acceptance) ──────────────────────────────────────────


class TestValidIRIs:
    """IRIs that must be accepted."""

    def test_https_object_iri(self):
        assert _validate_iri("https://example.org/data/obj1") is True

    def test_http_object_iri(self):
        assert _validate_iri("http://example.org/item") is True

    def test_urn_sempkm_model(self):
        assert _validate_iri("urn:sempkm:model:basic-pkm:Note") is True

    def test_urn_isbn(self):
        assert _validate_iri("urn:isbn:0451450523") is True

    def test_https_with_path_and_fragment(self):
        assert _validate_iri("https://example.org/data/obj1#section") is True

    def test_https_with_query(self):
        assert _validate_iri("https://example.org/resource?type=note") is True

    def test_urn_sempkm_seed(self):
        assert _validate_iri("urn:sempkm:model:basic-pkm:seed-note-arch") is True


# ── Invalid — empty/missing ──────────────────────────────────────────


class TestEmptyAndMissing:
    """Empty strings and IRIs with missing required components."""

    def test_empty_string(self):
        assert _validate_iri("") is False

    def test_missing_scheme(self):
        assert _validate_iri("example.org/data") is False

    def test_scheme_only_http(self):
        assert _validate_iri("http://") is False


# ── Invalid — forbidden characters (each tested individually) ────────


class TestForbiddenCharacters:
    """Each of the 10 forbidden characters must be independently rejected.

    Tests embed a single forbidden character in an otherwise-valid IRI
    to prove each character is individually detected.
    """

    @pytest.mark.parametrize(
        "char, label",
        [
            ("<", "less-than"),
            (">", "greater-than"),
            ('"', "double-quote"),
            ("\\", "backslash"),
            ("{", "left-brace"),
            ("}", "right-brace"),
            ("\n", "newline"),
            ("\r", "carriage-return"),
            ("\t", "tab"),
            (" ", "space"),
        ],
        ids=lambda x: x if len(x) > 1 else repr(x),
    )
    def test_forbidden_char_rejected(self, char, label):
        iri = f"https://example.org/data/obj{char}1"
        assert _validate_iri(iri) is False, (
            f"Forbidden character {label!r} ({char!r}) was not rejected"
        )


# ── Invalid — structural ────────────────────────────────────────────


class TestStructuralInvalidity:
    """IRIs with structural problems beyond missing characters."""

    def test_http_without_netloc(self):
        assert _validate_iri("http:///path") is False

    def test_urn_without_path(self):
        assert _validate_iri("urn:") is False

    def test_unknown_scheme_ftp(self):
        assert _validate_iri("ftp://example.org") is False

    def test_javascript_scheme(self):
        assert _validate_iri("javascript:alert(1)") is False

    def test_data_scheme(self):
        assert _validate_iri("data:text/html,<h1>hi</h1>") is False

    def test_file_scheme(self):
        assert _validate_iri("file:///etc/passwd") is False


# ── Invalid — injection payloads ────────────────────────────────────


class TestInjectionPayloads:
    """Real-world SPARQL injection attempts that must be blocked."""

    def test_sparql_injection_angle_bracket_drop(self):
        assert _validate_iri("https://example.org/data/obj1> ; DROP") is False

    def test_sparql_injection_script_tag(self):
        assert _validate_iri("https://example.org/data/<script>") is False

    def test_sparql_injection_comment(self):
        assert _validate_iri("https://example.org/data/obj1\n# injected") is False

    def test_sparql_injection_curly_brace_block(self):
        assert _validate_iri("https://example.org/data/obj1} ; {SELECT") is False

    def test_sparql_injection_backslash_escape(self):
        assert _validate_iri("https://example.org/data/obj1\\x00") is False
