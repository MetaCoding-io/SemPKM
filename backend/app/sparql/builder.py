"""Centralised SPARQL builder utilities — safe IRI/literal serialization.

Every SPARQL query in the codebase MUST construct IRIs and string literals
through these helpers instead of raw f-string interpolation.  The functions
use **rdflib's .n3()** as the serialization layer, with additional
pre-validation to reject payloads that rdflib alone would let through
(schemeless strings, empty values, forbidden URI schemes, control characters).

This module is the authoritative replacement for the nine (!) scattered
``_sparql_escape`` / ``_escape_sparql`` / ``_validate_iri`` helpers that
previously lived in individual router/service modules.

Audit trail: created as part of M043/S01 to close SPARQL injection findings
F-006 through F-010.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from rdflib import Literal, URIRef

# ---------------------------------------------------------------------------
# Allowed URI schemes for SPARQL IRI interpolation
# ---------------------------------------------------------------------------
_ALLOWED_SCHEMES = frozenset({"http", "https", "urn", "mailto"})

# Characters that MUST NOT appear in an IRI destined for SPARQL.
# rdflib catches some of these (angle brackets, spaces, quotes, braces)
# but NOT tabs, carriage returns, or backslashes.
_FORBIDDEN_IRI_CHARS = re.compile(r'[<>"\\{}\n\r\t\x00-\x1f ]')

# SPARQL variable pattern: ?varName or $varName
_SPARQL_VAR_RE = re.compile(r'^[\?\$][a-zA-Z_][a-zA-Z0-9_]*$')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def safe_iri(value: str) -> str:
    """Validate *value* as a safe absolute IRI and return its N3 form ``<…>``.

    Uses :class:`rdflib.URIRef` plus pre-validation:

    * Non-empty string with an allowed scheme (http, https, urn, mailto).
    * No forbidden characters (angle brackets, quotes, backslash, braces,
      whitespace, control characters).
    * ``http``/``https`` IRIs must have a host component.
    * ``urn`` IRIs must have a path component.

    Raises :exc:`ValueError` with a descriptive message on invalid input.
    """
    if not value or not isinstance(value, str):
        raise ValueError("IRI must be a non-empty string")

    # Strip surrounding whitespace that could sneak through URL decoding
    value = value.strip()
    if not value:
        raise ValueError("IRI must be a non-empty string")

    # ── Pre-validation ────────────────────────────────────────────────
    if _FORBIDDEN_IRI_CHARS.search(value):
        raise ValueError(
            f"IRI contains forbidden characters: {value!r}"
        )

    try:
        parsed = urlparse(value)
    except Exception as exc:
        raise ValueError(f"Cannot parse IRI: {value!r}") from exc

    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"IRI scheme {scheme!r} not in allowed set "
            f"{sorted(_ALLOWED_SCHEMES)}: {value!r}"
        )

    if scheme in ("http", "https") and not parsed.netloc:
        raise ValueError(
            f"HTTP(S) IRI must have a host component: {value!r}"
        )

    if scheme == "urn" and not parsed.path:
        raise ValueError(f"URN IRI must have a path component: {value!r}")

    # ── rdflib serialization ──────────────────────────────────────────
    try:
        return URIRef(value).n3()
    except Exception as exc:
        raise ValueError(
            f"rdflib rejected IRI: {value!r}"
        ) from exc


def safe_literal(
    value: str,
    datatype: str | None = None,
    lang: str | None = None,
) -> str:
    """Return the N3 serialization of a SPARQL string literal.

    Constructs an :class:`rdflib.Literal` and calls ``.n3()`` which handles
    escaping of quotes, newlines, backslashes, tabs, and carriage returns.

    Parameters
    ----------
    value:
        The raw string value.
    datatype:
        Optional XSD datatype IRI (e.g. ``"http://www.w3.org/2001/XMLSchema#date"``).
    lang:
        Optional language tag (e.g. ``"en"``).
    """
    if value is None:
        raise ValueError("Literal value must not be None")

    dt = URIRef(datatype) if datatype else None
    lit = Literal(value, datatype=dt, lang=lang)
    return lit.n3()


def sparql_escape_string(value: str) -> str:
    r"""Escape a string for embedding inside a SPARQL ``"…"`` literal.

    This is the **authoritative replacement** for every scattered
    ``_sparql_escape`` / ``_escape_sparql`` / ``_sparql_escape_str`` helper.

    Escapes: ``\``, ``"``, ``'``, newline, carriage return, tab.

    Returns the *inner* string (without surrounding quotes) — callers wrap it
    in ``"…"`` themselves.  If you want the full N3 form with quotes, use
    :func:`safe_literal` instead.
    """
    if value is None:
        raise ValueError("Cannot escape None")
    return (
        value
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def values_clause(var_name: str, iris: list[str]) -> str:
    """Build a SPARQL ``VALUES`` clause from a list of IRIs.

    Example::

        values_clause("type", ["http://a.org/A", "http://b.org/B"])
        # => 'VALUES (?type) { (<http://a.org/A>) (<http://b.org/B>) }'

    Each IRI is validated and serialized through :func:`safe_iri`.

    Raises :exc:`ValueError` if *iris* is empty or any IRI is invalid.
    """
    if not var_name:
        raise ValueError("var_name must be a non-empty string")
    if not iris:
        raise ValueError("iris list must not be empty")

    # Ensure var_name is bare (no leading ?)
    clean_var = var_name.lstrip("?").strip()
    if not clean_var:
        raise ValueError("var_name must be a non-empty string")

    entries = " ".join(f"({safe_iri(iri)})" for iri in iris)
    return f"VALUES (?{clean_var}) {{ {entries} }}"


def triple_pattern(s: str, p: str, o: str) -> str:
    """Build a safe SPARQL triple pattern ``s p o .``

    Each component can be:
    * A SPARQL variable (``?x``, ``$y``) — passed through as-is.
    * An IRI string — validated and serialized via :func:`safe_iri`.

    Raises :exc:`ValueError` if any component is invalid.
    """
    parts: list[str] = []
    for label, component in [("subject", s), ("predicate", p), ("object", o)]:
        if not component or not isinstance(component, str):
            raise ValueError(f"Triple {label} must be a non-empty string")
        component = component.strip()
        if _SPARQL_VAR_RE.match(component):
            parts.append(component)
        else:
            parts.append(safe_iri(component))

    return f"{parts[0]} {parts[1]} {parts[2]} ."


def validate_iri(value: str) -> bool:
    """Check whether *value* is a valid, safe IRI for SPARQL interpolation.

    Convenience wrapper around :func:`safe_iri` that returns a boolean
    instead of raising.  Drop-in replacement for the old
    ``_validate_iri()`` helper.
    """
    try:
        safe_iri(value)
        return True
    except (ValueError, TypeError):
        return False
