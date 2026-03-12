"""Tests for SPARQL utility functions — escape_sparql_regex().

Covers SEC-04 (injection prevention) and TEST-02 (unit test coverage).
"""

import pytest

from app.sparql.utils import escape_sparql_regex


class TestEscapeSparqlRegex:
    """Tests for escape_sparql_regex()."""

    def test_backslash_escaped_first(self):
        """Backslash must be escaped before other chars to avoid double-escaping."""
        assert escape_sparql_regex("a\\b") == "a\\\\b"

    def test_double_quote_escaped(self):
        assert escape_sparql_regex('say "hello"') == 'say \\"hello\\"'

    def test_dot_escaped(self):
        assert escape_sparql_regex("a.b") == "a\\.b"

    def test_star_escaped(self):
        assert escape_sparql_regex("a*b") == "a\\*b"

    def test_plus_escaped(self):
        assert escape_sparql_regex("a+b") == "a\\+b"

    def test_question_mark_escaped(self):
        assert escape_sparql_regex("a?b") == "a\\?b"

    def test_caret_escaped(self):
        assert escape_sparql_regex("a^b") == "a\\^b"

    def test_dollar_escaped(self):
        assert escape_sparql_regex("a$b") == "a\\$b"

    def test_left_brace_escaped(self):
        assert escape_sparql_regex("a{b") == "a\\{b"

    def test_right_brace_escaped(self):
        assert escape_sparql_regex("a}b") == "a\\}b"

    def test_left_paren_escaped(self):
        assert escape_sparql_regex("a(b") == "a\\(b"

    def test_right_paren_escaped(self):
        assert escape_sparql_regex("a)b") == "a\\)b"

    def test_pipe_escaped(self):
        assert escape_sparql_regex("a|b") == "a\\|b"

    def test_left_bracket_escaped(self):
        assert escape_sparql_regex("a[b") == "a\\[b"

    def test_right_bracket_escaped(self):
        assert escape_sparql_regex("a]b") == "a\\]b"

    def test_safe_text_passthrough(self):
        """Alphanumeric, spaces, and underscores pass through unchanged."""
        safe = "Hello World 123_test"
        assert escape_sparql_regex(safe) == safe

    def test_combined_metacharacters(self):
        """Multiple metacharacters in a single input are all escaped."""
        result = escape_sparql_regex('foo.bar*"baz')
        assert result == 'foo\\.bar\\*\\"baz'

    def test_empty_string(self):
        assert escape_sparql_regex("") == ""

    def test_backslash_before_other_escapes(self):
        r"""Backslash in `\.` must not become `\\\\.` — only `\\.`."""
        # Input: literal backslash followed by dot
        # Backslash -> \\, then dot -> \.
        assert escape_sparql_regex("\\.") == "\\\\\\."
