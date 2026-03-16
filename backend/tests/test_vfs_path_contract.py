"""Tests for the VFS path contract: slug generation and collision dedup.

The path contract defines how RDF IRIs and labels map to filesystem paths:
  Forward: IRI + label → slugified filename (.md)
  Reverse: filename → IRI via file_map lookup (built per-request)

Key functions under test:
  _slugify(text) — label → filesystem-safe slug
  _build_file_map_from_bindings(bindings) — SPARQL bindings → {filename: {iri, label, type_iri}}
"""

import hashlib

import pytest

from app.vfs.mount_collections import _build_file_map_from_bindings, _slugify


# ---------------------------------------------------------------------------
# _slugify
# ---------------------------------------------------------------------------

class TestSlugify:
    """Slug generation edge cases."""

    def test_normal_label(self):
        assert _slugify("My Research Note") == "my-research-note"

    def test_lowercase(self):
        assert _slugify("ALLCAPS") == "allcaps"

    def test_mixed_case(self):
        assert _slugify("CamelCase Title") == "camelcase-title"

    def test_unicode_stripped(self):
        """Non-ASCII characters are replaced by hyphens (regex [^a-z0-9]+)."""
        result = _slugify("Über Données")
        # 'Ü' and 'é' are not in [a-z0-9], so replaced with hyphens
        assert result == "ber-donn-es"

    def test_special_characters(self):
        result = _slugify("Hello/World: A <Test>")
        assert result == "hello-world-a-test"

    def test_empty_string(self):
        assert _slugify("") == "untitled"

    def test_only_special_chars(self):
        """All characters replaced → empty after strip → falls back to 'untitled'."""
        assert _slugify("!!!@@@###") == "untitled"

    def test_only_whitespace(self):
        assert _slugify("   ") == "untitled"

    def test_leading_trailing_hyphens_stripped(self):
        assert _slugify("-hello-world-") == "hello-world"

    def test_multiple_consecutive_hyphens_collapsed(self):
        assert _slugify("a   b---c") == "a-b-c"

    def test_already_slugified(self):
        """Idempotent for already-clean input."""
        assert _slugify("my-note") == "my-note"

    def test_numbers_preserved(self):
        assert _slugify("Chapter 42 Notes") == "chapter-42-notes"

    def test_long_label_not_truncated(self):
        """Current implementation does not truncate. Document this behavior."""
        long_label = "a" * 300
        result = _slugify(long_label)
        assert result == "a" * 300

    def test_single_character(self):
        assert _slugify("x") == "x"

    def test_numeric_only(self):
        assert _slugify("12345") == "12345"


# ---------------------------------------------------------------------------
# _build_file_map_from_bindings — helpers
# ---------------------------------------------------------------------------

def _make_binding(iri: str, label: str, type_iri: str = "urn:test:Type") -> dict:
    """Create a SPARQL binding dict matching the expected shape."""
    return {
        "iri": {"value": iri},
        "label": {"value": label},
        "typeIri": {"value": type_iri},
    }


def _iri_hash_prefix(iri: str) -> str:
    """Return the 6-char hex prefix used for dedup suffixes."""
    return hashlib.sha256(iri.encode()).hexdigest()[:6]


# ---------------------------------------------------------------------------
# _build_file_map_from_bindings
# ---------------------------------------------------------------------------

class TestBuildFileMap:
    """File map construction and collision dedup."""

    def test_single_object(self):
        bindings = [_make_binding("urn:test:1", "My Note")]
        result = _build_file_map_from_bindings(bindings)
        assert "my-note.md" in result
        assert result["my-note.md"]["iri"] == "urn:test:1"
        assert result["my-note.md"]["label"] == "My Note"

    def test_no_collision_no_suffix(self):
        bindings = [
            _make_binding("urn:test:1", "Alpha"),
            _make_binding("urn:test:2", "Beta"),
        ]
        result = _build_file_map_from_bindings(bindings)
        assert "alpha.md" in result
        assert "beta.md" in result

    def test_two_way_collision_gets_hash_suffix(self):
        """Two objects with the same label both get IRI hash suffixes."""
        bindings = [
            _make_binding("urn:test:aaa", "Same Label"),
            _make_binding("urn:test:bbb", "Same Label"),
        ]
        result = _build_file_map_from_bindings(bindings)

        hash_a = _iri_hash_prefix("urn:test:aaa")
        hash_b = _iri_hash_prefix("urn:test:bbb")
        expected_a = f"same-label--{hash_a}.md"
        expected_b = f"same-label--{hash_b}.md"

        assert expected_a in result
        assert expected_b in result
        assert result[expected_a]["iri"] == "urn:test:aaa"
        assert result[expected_b]["iri"] == "urn:test:bbb"

    def test_three_way_collision(self):
        """Three objects with the same label all get unique hash suffixes."""
        bindings = [
            _make_binding("urn:test:x1", "Collision"),
            _make_binding("urn:test:x2", "Collision"),
            _make_binding("urn:test:x3", "Collision"),
        ]
        result = _build_file_map_from_bindings(bindings)

        assert len(result) == 3
        for b in bindings:
            iri = b["iri"]["value"]
            h = _iri_hash_prefix(iri)
            filename = f"collision--{h}.md"
            assert filename in result, f"Expected {filename} in file map"
            assert result[filename]["iri"] == iri

    def test_collision_only_affects_colliding_slugs(self):
        """Non-colliding slugs are unaffected by collisions elsewhere."""
        bindings = [
            _make_binding("urn:test:1", "Duplicate"),
            _make_binding("urn:test:2", "Duplicate"),
            _make_binding("urn:test:3", "Unique Entry"),
        ]
        result = _build_file_map_from_bindings(bindings)

        # Unique entry has no hash suffix
        assert "unique-entry.md" in result
        # Colliding entries have hash suffixes
        assert any("duplicate--" in k for k in result)

    def test_type_iri_preserved(self):
        bindings = [_make_binding("urn:test:1", "Typed", "urn:type:Note")]
        result = _build_file_map_from_bindings(bindings)
        assert result["typed.md"]["type_iri"] == "urn:type:Note"

    def test_missing_type_iri_defaults_empty(self):
        """typeIri is optional in SPARQL bindings."""
        bindings = [{"iri": {"value": "urn:test:1"}, "label": {"value": "No Type"}}]
        result = _build_file_map_from_bindings(bindings)
        assert result["no-type.md"]["type_iri"] == ""

    def test_empty_bindings(self):
        result = _build_file_map_from_bindings([])
        assert result == {}

    def test_extension_always_md(self):
        """All generated filenames end with .md."""
        bindings = [
            _make_binding("urn:test:1", "Note Alpha"),
            _make_binding("urn:test:2", "Note Beta"),
            _make_binding("urn:test:3", "Note Beta"),  # collision
        ]
        result = _build_file_map_from_bindings(bindings)
        for filename in result:
            assert filename.endswith(".md"), f"{filename} should end with .md"

    def test_reverse_lookup_by_filename(self):
        """file_map supports reverse mapping: filename → IRI."""
        bindings = [_make_binding("urn:test:abc123", "My Document")]
        result = _build_file_map_from_bindings(bindings)
        # Reverse: given a filename, retrieve the IRI
        assert result["my-document.md"]["iri"] == "urn:test:abc123"

    def test_label_with_unicode_in_file_map(self):
        """Unicode labels slugify but original label is preserved in map."""
        bindings = [_make_binding("urn:test:1", "Café Résumé")]
        result = _build_file_map_from_bindings(bindings)
        filename = "caf-r-sum.md"
        assert filename in result
        assert result[filename]["label"] == "Café Résumé"


# ---------------------------------------------------------------------------
# _build_file_map_from_bindings — filename templates
# ---------------------------------------------------------------------------

def _make_template_binding(
    iri: str, label: str, type_iri: str = "", created: str = ""
) -> dict:
    """Create a SPARQL binding dict with optional created date for template tests."""
    b: dict = {
        "iri": {"value": iri},
        "label": {"value": label},
        "typeIri": {"value": type_iri},
    }
    if created:
        b["created"] = {"value": created}
    return b


class TestFilenameTemplates:
    """Filename template expansion in _build_file_map_from_bindings."""

    def test_title_only(self):
        """Template with just {title} — same as no template."""
        bindings = [_make_template_binding("urn:x:1", "My Note")]
        result = _build_file_map_from_bindings(bindings, filename_template="{title}")
        assert "my-note.md" in result

    def test_date_title(self):
        """Template {date}-{title} produces date-prefixed slug."""
        bindings = [_make_template_binding("urn:x:1", "My Note", created="2024-01-15T10:00:00Z")]
        result = _build_file_map_from_bindings(bindings, filename_template="{date}-{title}")
        assert "2024-01-15-my-note.md" in result

    def test_type_title(self):
        """Template {type}-{title} uses type IRI local name."""
        bindings = [_make_template_binding("urn:x:1", "My Note", type_iri="http://example.org/Note")]
        result = _build_file_map_from_bindings(bindings, filename_template="{type}-{title}")
        assert "note-my-note.md" in result

    def test_type_with_label_map(self):
        """Template {type}-{title} uses type_labels dict when provided."""
        bindings = [_make_template_binding("urn:x:1", "My Note", type_iri="http://example.org/Note")]
        result = _build_file_map_from_bindings(
            bindings,
            filename_template="{type}-{title}",
            type_labels={"http://example.org/Note": "Notebook"},
        )
        assert "notebook-my-note.md" in result

    def test_id_suffix(self):
        """Template {title}-{id} appends IRI hash."""
        bindings = [_make_template_binding("urn:x:1", "My Note")]
        result = _build_file_map_from_bindings(bindings, filename_template="{title}-{id}")
        keys = list(result.keys())
        assert len(keys) == 1
        # Should have hash suffix in the slug
        assert keys[0].startswith("my-note-")
        assert keys[0].endswith(".md")
        # The id part should be 8 hex chars
        slug_part = keys[0].replace(".md", "")
        id_part = slug_part.split("my-note-")[1]
        assert len(id_part) == 8

    def test_missing_date_uses_undated(self):
        """Missing created date falls back to 'undated'."""
        bindings = [_make_template_binding("urn:x:1", "My Note")]
        result = _build_file_map_from_bindings(bindings, filename_template="{date}-{title}")
        assert "undated-my-note.md" in result

    def test_missing_type_uses_unknown(self):
        """Missing type IRI falls back to 'unknown'."""
        bindings = [_make_template_binding("urn:x:1", "My Note", type_iri="")]
        result = _build_file_map_from_bindings(bindings, filename_template="{type}-{title}")
        assert "unknown-my-note.md" in result

    def test_no_template_unchanged(self):
        """No template = existing behavior (slug from label only)."""
        bindings = [_make_template_binding("urn:x:1", "My Note")]
        result = _build_file_map_from_bindings(bindings)
        assert "my-note.md" in result

    def test_dedup_with_template(self):
        """Dedup still works when templates produce same slug."""
        bindings = [
            _make_template_binding("urn:x:1", "Note A", created="2024-01-15T00:00:00Z"),
            _make_template_binding("urn:x:2", "Note A", created="2024-01-15T00:00:00Z"),
        ]
        result = _build_file_map_from_bindings(bindings, filename_template="{date}-{title}")
        assert len(result) == 2
        # Both files should exist with hash suffixes
        for fname in result:
            assert fname.endswith(".md")
            assert "2024-01-15-note-a--" in fname

    def test_bogus_variable_passthrough(self):
        """Unknown template variables like {bogus} pass through as literal text."""
        bindings = [_make_template_binding("urn:x:1", "My Note")]
        result = _build_file_map_from_bindings(bindings, filename_template="{bogus}-{title}")
        keys = list(result.keys())
        assert len(keys) == 1
        # {bogus} gets slugified as literal — curly braces become hyphens
        assert "my-note" in keys[0]
        assert keys[0].endswith(".md")

    def test_type_iri_with_hash_fragment(self):
        """Type IRI with # fragment extracts local name correctly."""
        bindings = [_make_template_binding("urn:x:1", "My Note", type_iri="http://example.org/onto#Article")]
        result = _build_file_map_from_bindings(bindings, filename_template="{type}-{title}")
        assert "article-my-note.md" in result

    def test_type_iri_with_colon(self):
        """Type IRI with : separator extracts local name correctly."""
        bindings = [_make_template_binding("urn:x:1", "My Note", type_iri="urn:test:Concept")]
        result = _build_file_map_from_bindings(bindings, filename_template="{type}-{title}")
        assert "concept-my-note.md" in result
