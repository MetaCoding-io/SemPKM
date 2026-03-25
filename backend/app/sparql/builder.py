"""Centralized SPARQL building utilities with safe IRI/literal serialization.

This module is the **single authoritative** place for SPARQL value escaping
in SemPKM.  It replaces the nine scattered ``_sparql_escape`` / ``_escape_sparql``
/ ``_sparql_escape_str`` / ``_escape_sparql_string`` functions that existed
across browser, vfs, api, federation, task_templates, and webhooks modules.

All SPARQL string construction MUST go through one of these helpers:

* :func:`safe_iri` — validate + serialize an IRI in ``<…>`` N3 form
* :func:`safe_literal` — serialize a typed/tagged literal via rdflib
* :func:`sparql_escape_string` — escape a raw string for interpolation
  inside an *already-quoted* SPARQL literal (``"…"``)
* :func:`values_clause` — build a ``VALUES`` binding block
* :func:`triple_pattern` — build one safe ``s p o .`` pattern

Security rationale
------------------
Hand-rolled f-string interpolation into SPARQL is equivalent to SQL injection.
rdflib's ``URIRef.n3()`` raises on malformed IRIs that contain ``>``, ``"``,
whitespace, etc., so using it as the serialization layer blocks breakout
attacks at the lowest possible level.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from rdflib import Literal, URIRef, XSD  # noqa: F401 — XSD reexport for callers

__all__ = [
    "safe_iri",
    "safe_literal",
    "sparql_escape_string",
    "values_clause",
    "triple_pattern",
]

# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

# Characters that MUST NOT appear in an IRI destined for SPARQL <…> quoting.
# This is a defence-in-depth check *before* handing to rdflib, so we reject
# obviously malicious payloads with a clear ValueError rather than relying
# solely on rdflib's internal "does not look like a valid URI" message.
_FORBIDDEN_IRI_CHARS = re.compile(r'[<>"\\{}\s]')

# Recognised URI schemes.  urn: is used for model/seed IRIs.
_ALLOWED_SCHEMES = frozenset({"http", "https", "urn"})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def safe_iri(value: str) -> str:
    """Validate *value* as an absolute IRI and return its N3 ``<…>`` form.

    Uses :class:`rdflib.URIRef` internally — which raises on structurally
    invalid IRIs — but adds pre-validation for SPARQL-specific injection
    characters that rdflib alone may not catch.

    Parameters
    ----------
    value:
        A raw IRI string, e.g. ``"http://example.org/Thing"``.

    Returns
    -------
    str
        The angle-bracket-wrapped N3 form, e.g. ``"<http://example.org/Thing>"``.

    Raises
    ------
    ValueError
        If *value* is empty, uses an unsupported scheme, contains forbidden
        characters, or fails rdflib's own validation.

    Examples
    --------
    >>> safe_iri("http://example.org/test")
    '<http://example.org/test>'
    >>> safe_iri("urn:sempkm:model:basic-pkm:Note")
    '<urn:sempkm:model:basic-pkm:Note>'
    """
    if not value:
        raise ValueError("IRI must not be empty")

    # ---- Structural pre-checks (fast, before touching rdflib) ----
    if _FORBIDDEN_IRI_CHARS.search(value):
        raise ValueError(
            f"IRI contains forbidden characters: {value!r}"
        )

    parsed = urlparse(value)
    if not parsed.scheme:
        raise ValueError(f"IRI has no scheme: {value!r}")
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"IRI scheme {parsed.scheme!r} is not allowed (expected one of "
            f"{sorted(_ALLOWED_SCHEMES)}): {value!r}"
        )
    if parsed.scheme in ("http", "https") and not parsed.netloc:
        raise ValueError(f"HTTP(S) IRI must have a host: {value!r}")
    if parsed.scheme == "urn" and not parsed.path:
        raise ValueError(f"URN IRI must have a path: {value!r}")

    # ---- rdflib serialization (catches anything we missed) ----
    ref = URIRef(value)
    return ref.n3()


def safe_literal(
    value: str,
    datatype: str | None = None,
    lang: str | None = None,
) -> str:
    """Serialize *value* as a SPARQL literal using rdflib's N3 serializer.

    Handles quoting, escaping of special characters, and optional datatype /
    language tag attachment.

    Parameters
    ----------
    value:
        The raw Python string to serialize.
    datatype:
        Optional XSD datatype IRI (e.g. ``"http://www.w3.org/2001/XMLSchema#dateTime"``).
    lang:
        Optional BCP-47 language tag (e.g. ``"en"``).

    Returns
    -------
    str
        The full N3 literal, e.g. ``'"hello"'``, ``'"42"^^<xsd:integer>'``,
        ``'"hello"@en'``.

    Examples
    --------
    >>> safe_literal("hello")
    '"hello"'
    >>> safe_literal("42", datatype=str(XSD.integer))
    '"42"^^<http://www.w3.org/2001/XMLSchema#integer>'
    """
    if value is None:
        raise ValueError("Literal value must not be None")

    kwargs: dict = {}
    if datatype is not None:
        kwargs["datatype"] = URIRef(datatype)
    if lang is not None:
        kwargs["lang"] = lang

    lit = Literal(value, **kwargs)
    return lit.n3()


def sparql_escape_string(value: str) -> str:
    r"""Escape *value* for safe embedding inside a SPARQL ``"…"`` literal.

    This is the **authoritative** replacement for every scattered
    ``_sparql_escape`` / ``_escape_sparql`` helper in the codebase.
    Callers typically use this in an f-string like::

        f'"{ sparql_escape_string(user_input) }"'

    The function escapes backslash, double-quote, single-quote,
    newline, carriage return, and tab — covering the full set of
    characters that can break SPARQL string literal syntax.

    Parameters
    ----------
    value:
        A raw Python string to escape.

    Returns
    -------
    str
        The escaped string (*without* surrounding quotes).

    Raises
    ------
    ValueError
        If *value* is ``None``.
    """
    if value is None:
        raise ValueError("Cannot escape None value")
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
    """Build a SPARQL ``VALUES`` binding clause from a list of IRIs.

    Parameters
    ----------
    var_name:
        The SPARQL variable name **without** the leading ``?``,
        e.g. ``"type"`` produces ``VALUES (?type) { … }``.
    iris:
        A list of IRI strings.  Each is validated and serialized via
        :func:`safe_iri`.

    Returns
    -------
    str
        A ``VALUES`` clause, e.g.
        ``VALUES (?type) { (<http://a.org/A>) (<http://a.org/B>) }``.

    Raises
    ------
    ValueError
        If *iris* is empty or any IRI is invalid.
    """
    if not iris:
        raise ValueError("VALUES clause requires at least one IRI")
    if not var_name:
        raise ValueError("Variable name must not be empty")
    entries = " ".join(f"({safe_iri(iri)})" for iri in iris)
    return f"VALUES (?{var_name}) {{ {entries} }}"


def triple_pattern(s: str, p: str, o: str) -> str:
    """Build a single SPARQL triple pattern from subject, predicate, object.

    Each position may be:

    * A SPARQL variable (starts with ``?`` or ``$``) — passed through as-is.
    * An IRI string — validated and serialized via :func:`safe_iri`.

    Object-position literals are **not** supported by this helper; use
    :func:`safe_literal` or :func:`sparql_escape_string` directly for those.

    Parameters
    ----------
    s, p, o:
        Subject, predicate, and object terms.

    Returns
    -------
    str
        A triple pattern like ``<http://a.org/s> <http://a.org/p> ?obj .``

    Examples
    --------
    >>> triple_pattern("http://a.org/s", "http://a.org/p", "?obj")
    '<http://a.org/s> <http://a.org/p> ?obj .'
    """
    parts: list[str] = []
    for term in (s, p, o):
        if not term:
            raise ValueError("Triple pattern terms must not be empty")
        if term.startswith("?") or term.startswith("$"):
            parts.append(term)
        else:
            parts.append(safe_iri(term))
    return f"{parts[0]} {parts[1]} {parts[2]} ."
