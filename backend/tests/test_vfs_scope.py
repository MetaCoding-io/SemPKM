"""Tests for VFS scope filter resolution (M006/S02).

Verifies that build_scope_filter correctly handles scope_query
resolution and _extract_where_body parsing.
"""

from unittest.mock import MagicMock

from app.vfs.cache import listing_cache, _cache_lock
from app.vfs.strategies import _extract_where_body, build_scope_filter
from app.vfs.mount_service import MountDefinition


class TestExtractWhereBody:
    """Test SPARQL WHERE clause extraction."""

    def test_simple_select(self):
        query = "SELECT ?s WHERE { ?s a <http://example.org/Type> }"
        body = _extract_where_body(query)
        # ?s should be renamed to ?iri
        assert "?iri" in body
        assert "<http://example.org/Type>" in body

    def test_select_with_iri_var(self):
        query = "SELECT ?iri WHERE { ?iri a <http://example.org/Type> . ?iri <http://example.org/active> true }"
        body = _extract_where_body(query)
        assert "?iri" in body
        assert "a <http://example.org/Type>" in body

    def test_multiline_query(self):
        query = """
        PREFIX bpkm: <http://example.org/bpkm/>
        SELECT ?s WHERE {
          ?s a bpkm:Note .
          ?s bpkm:tags "project" .
        }
        """
        body = _extract_where_body(query)
        assert "?iri" in body  # ?s renamed
        assert 'bpkm:Note' in body

    def test_no_where_clause(self):
        """Fallback: return raw text if WHERE not found."""
        query = "ASK { ?s ?p ?o }"
        body = _extract_where_body(query)
        assert body == query


class TestBuildScopeFilter:
    """Test scope filter construction."""

    def _make_mount(self, sparql_scope="all", scope_query=None):
        return MountDefinition(
            id="test-id",
            name="test",
            path="test",
            strategy="flat",
            sparql_scope=sparql_scope,
            scope_query=scope_query,
        )

    def test_scope_all_returns_empty(self):
        mount = self._make_mount(sparql_scope="all")
        assert build_scope_filter(mount) == ""

    def test_scope_none_returns_empty(self):
        mount = self._make_mount(sparql_scope=None)
        assert build_scope_filter(mount) == ""

    def test_custom_sparql_scope(self):
        mount = self._make_mount(sparql_scope="?iri a <http://example.org/Note>")
        result = build_scope_filter(mount)
        assert "?iri a <http://example.org/Note>" in result
        assert "SELECT ?iri WHERE" in result

    def test_resolved_query_takes_precedence(self):
        mount = self._make_mount(sparql_scope="?iri a <http://example.org/OldType>")
        query_text = "SELECT ?s WHERE { ?s a <http://example.org/NewType> }"
        result = build_scope_filter(mount, resolved_query_text=query_text)
        assert "<http://example.org/NewType>" in result
        assert "<http://example.org/OldType>" not in result

    def test_resolved_query_renames_variables(self):
        mount = self._make_mount()
        query_text = "SELECT ?s WHERE { ?s a <http://example.org/Note> }"
        result = build_scope_filter(mount, resolved_query_text=query_text)
        assert "?iri" in result

    def test_no_resolved_query_falls_back(self):
        mount = self._make_mount(sparql_scope="?iri a <http://example.org/Note>")
        result = build_scope_filter(mount, resolved_query_text=None)
        assert "<http://example.org/Note>" in result


class TestTypeFilter:
    """Test type_filter VALUES clause generation in build_scope_filter."""

    def _make_mount(self, type_filter=None, sparql_scope="all", scope_query=None):
        return MountDefinition(
            id="test-id",
            name="test",
            path="test",
            strategy="flat",
            sparql_scope=sparql_scope,
            scope_query=scope_query,
            type_filter=type_filter,
        )

    def test_type_filter_single_type(self):
        mount = self._make_mount(type_filter=["http://example.org/Note"])
        result = build_scope_filter(mount)
        assert "VALUES ?type { <http://example.org/Note> }" in result
        assert "?iri a ?type ." in result

    def test_type_filter_multiple_types(self):
        iris = [
            "http://example.org/Note",
            "http://example.org/Task",
            "http://example.org/Event",
        ]
        mount = self._make_mount(type_filter=iris)
        result = build_scope_filter(mount)
        assert "VALUES ?type" in result
        for iri in iris:
            assert f"<{iri}>" in result
        assert "?iri a ?type ." in result

    def test_type_filter_empty_list(self):
        mount = self._make_mount(type_filter=[])
        result = build_scope_filter(mount)
        assert "VALUES" not in result

    def test_type_filter_none(self):
        mount = self._make_mount(type_filter=None)
        result = build_scope_filter(mount)
        assert "VALUES" not in result

    def test_type_filter_with_scope_composes(self):
        mount = self._make_mount(
            type_filter=["http://example.org/Note"],
            sparql_scope="?iri a <http://example.org/Active>",
        )
        result = build_scope_filter(mount)
        # Both type VALUES and scope sub-select must appear
        assert "VALUES ?type { <http://example.org/Note> }" in result
        assert "?iri a ?type ." in result
        assert "SELECT ?iri WHERE" in result
        assert "<http://example.org/Active>" in result

    def test_type_filter_with_resolved_query_composes(self):
        mount = self._make_mount(type_filter=["http://example.org/Task"])
        query_text = "SELECT ?s WHERE { ?s a <http://example.org/Resolved> }"
        result = build_scope_filter(mount, resolved_query_text=query_text)
        # Both type VALUES and resolved query sub-select must appear
        assert "VALUES ?type { <http://example.org/Task> }" in result
        assert "?iri a ?type ." in result
        assert "SELECT ?iri WHERE" in result
        assert "<http://example.org/Resolved>" in result


class TestQueryResolution:
    """Test scope_query resolution via sync_client in build_scope_filter."""

    QUERY_IRI = "urn:sempkm:query:abc-123-def"
    QUERY_TEXT = "SELECT ?s WHERE { ?s a <http://example.org/Note> }"

    def _make_mount(self, scope_query=None, sparql_scope="all"):
        return MountDefinition(
            id="test-id",
            name="test",
            path="test",
            strategy="flat",
            sparql_scope=sparql_scope,
            scope_query=scope_query,
        )

    def _make_sync_client(self, query_text=None):
        """Create a mock SyncTriplestoreClient that returns query_text."""
        mock = MagicMock()
        if query_text is not None:
            mock.query.return_value = {
                "results": {
                    "bindings": [{"text": {"value": query_text}}]
                }
            }
        else:
            mock.query.return_value = {"results": {"bindings": []}}
        return mock

    def setup_method(self):
        """Clear cache before each test."""
        with _cache_lock:
            listing_cache.clear()

    def test_scope_query_resolved_via_sync_client(self):
        mount = self._make_mount(scope_query=self.QUERY_IRI)
        mock_client = self._make_sync_client(self.QUERY_TEXT)

        result = build_scope_filter(mount, sync_client=mock_client)

        assert "SELECT ?iri WHERE" in result
        assert "<http://example.org/Note>" in result
        mock_client.query.assert_called_once()

    def test_scope_query_not_found_returns_empty(self):
        mount = self._make_mount(scope_query=self.QUERY_IRI)
        mock_client = self._make_sync_client(query_text=None)  # no results

        result = build_scope_filter(mount, sync_client=mock_client)

        assert result == ""
        mock_client.query.assert_called_once()

    def test_scope_query_without_client_ignored(self):
        mount = self._make_mount(
            scope_query=self.QUERY_IRI,
            sparql_scope="?iri a <http://example.org/Fallback>",
        )

        # No sync_client → falls back to sparql_scope
        result = build_scope_filter(mount)

        assert "<http://example.org/Fallback>" in result
        assert "SELECT ?iri WHERE" in result

    def test_scope_query_cached_on_second_call(self):
        mount = self._make_mount(scope_query=self.QUERY_IRI)
        mock_client = self._make_sync_client(self.QUERY_TEXT)

        # First call: resolves from triplestore
        result1 = build_scope_filter(mount, sync_client=mock_client)
        assert "<http://example.org/Note>" in result1

        # Second call: should use cache, not query again
        result2 = build_scope_filter(mount, sync_client=mock_client)
        assert "<http://example.org/Note>" in result2

        # sync_client.query called only once (cached on second)
        assert mock_client.query.call_count == 1

    def test_resolved_query_text_takes_precedence_over_sync_client(self):
        """When resolved_query_text is explicitly provided, sync_client is not used."""
        mount = self._make_mount(scope_query=self.QUERY_IRI)
        mock_client = self._make_sync_client(self.QUERY_TEXT)
        explicit_text = "SELECT ?s WHERE { ?s a <http://example.org/Explicit> }"

        result = build_scope_filter(mount, resolved_query_text=explicit_text, sync_client=mock_client)

        assert "<http://example.org/Explicit>" in result
        # sync_client should NOT have been called
        mock_client.query.assert_not_called()


# ── Chain Strategy Tests (S03/T02) ───────────────────────────────────

class TestChainStrategyParsing:
    """Test strategy_chain and is_chain properties on MountDefinition."""

    def _make_mount(self, strategy: str) -> MountDefinition:
        return MountDefinition(
            id="test-id",
            name="test",
            path="test",
            strategy=strategy,
        )

    def test_single_strategy_chain(self):
        mount = self._make_mount("by-tag")
        assert mount.strategy_chain == ["by-tag"]

    def test_two_level_chain(self):
        mount = self._make_mount("by-tag|by-date")
        assert mount.strategy_chain == ["by-tag", "by-date"]

    def test_three_level_chain(self):
        mount = self._make_mount("by-type|by-tag|by-date")
        assert mount.strategy_chain == ["by-type", "by-tag", "by-date"]

    def test_single_is_not_chain(self):
        mount = self._make_mount("flat")
        assert mount.is_chain is False

    def test_pipe_delimited_is_chain(self):
        mount = self._make_mount("by-tag|by-date")
        assert mount.is_chain is True

    def test_to_dict_single_no_strategy_chain_key(self):
        mount = self._make_mount("by-type")
        d = mount.to_dict()
        assert "strategy_chain" not in d
        assert d["strategy"] == "by-type"

    def test_to_dict_chain_includes_strategy_chain_key(self):
        mount = self._make_mount("by-tag|by-date")
        d = mount.to_dict()
        assert d["strategy"] == "by-tag|by-date"
        assert d["strategy_chain"] == ["by-tag", "by-date"]


class TestChainValidation:
    """Test chain validation in _validate_strategy_chain."""

    def test_single_valid_strategy(self):
        from app.vfs.mount_service import _validate_strategy_chain
        # Should not raise
        _validate_strategy_chain("flat")
        _validate_strategy_chain("by-type")
        _validate_strategy_chain("by-date")
        _validate_strategy_chain("by-tag")
        _validate_strategy_chain("by-property")

    def test_two_level_chain_valid(self):
        from app.vfs.mount_service import _validate_strategy_chain
        _validate_strategy_chain("by-tag|by-date")

    def test_three_level_chain_valid(self):
        from app.vfs.mount_service import _validate_strategy_chain
        _validate_strategy_chain("by-type|by-tag|by-date")

    def test_four_level_chain_raises(self):
        from app.vfs.mount_service import _validate_strategy_chain
        import pytest
        with pytest.raises(ValueError, match="too long.*4 levels"):
            _validate_strategy_chain("by-type|by-tag|by-date|flat")

    def test_five_level_chain_raises(self):
        from app.vfs.mount_service import _validate_strategy_chain
        import pytest
        with pytest.raises(ValueError, match="too long.*5 levels"):
            _validate_strategy_chain("by-type|by-tag|by-date|flat|by-property")

    def test_invalid_strategy_in_chain(self):
        from app.vfs.mount_service import _validate_strategy_chain
        import pytest
        with pytest.raises(ValueError, match="Invalid strategy 'invalid'"):
            _validate_strategy_chain("by-tag|invalid")

    def test_empty_segment_in_chain(self):
        from app.vfs.mount_service import _validate_strategy_chain
        import pytest
        with pytest.raises(ValueError, match="Empty strategy segment"):
            _validate_strategy_chain("by-tag||by-date")

    def test_invalid_single_strategy(self):
        from app.vfs.mount_service import _validate_strategy_chain
        import pytest
        with pytest.raises(ValueError, match="Invalid strategy 'bogus'"):
            _validate_strategy_chain("bogus")


class TestChainNarrowingFilter:
    """Test build_chain_narrowing_filter for each strategy type."""

    def _make_mount(self, **kwargs) -> MountDefinition:
        defaults = dict(
            id="test-id",
            name="test",
            path="test",
            strategy="flat",
        )
        defaults.update(kwargs)
        return MountDefinition(**defaults)

    def test_by_type_narrowing(self):
        from app.vfs.strategies import build_chain_narrowing_filter
        mount = self._make_mount()
        result = build_chain_narrowing_filter("by-type", "Note", mount)
        assert "?iri a ?_chainType" in result
        assert 'REPLACE(STR(?_chainType), ".*[/:#]", "")' in result
        assert '"Note"' in result

    def test_by_tag_narrowing(self):
        from app.vfs.strategies import build_chain_narrowing_filter
        mount = self._make_mount(group_by_property="http://example.org/tags")
        result = build_chain_narrowing_filter("by-tag", "python", mount)
        assert "<http://example.org/tags>" in result
        assert '"python"' in result

    def test_by_tag_no_property_returns_empty(self):
        from app.vfs.strategies import build_chain_narrowing_filter
        mount = self._make_mount()
        result = build_chain_narrowing_filter("by-tag", "python", mount)
        assert result == ""

    def test_by_property_narrowing(self):
        from app.vfs.strategies import build_chain_narrowing_filter
        mount = self._make_mount(group_by_property="http://example.org/status")
        result = build_chain_narrowing_filter("by-property", "Active", mount)
        assert "<http://example.org/status>" in result
        assert '"Active"' in result

    def test_by_date_year_narrowing(self):
        from app.vfs.strategies import build_chain_narrowing_filter
        mount = self._make_mount(date_property="http://purl.org/dc/terms/created")
        result = build_chain_narrowing_filter("by-date", "2024", mount)
        assert "<http://purl.org/dc/terms/created>" in result
        assert '"2024"' in result

    def test_by_date_month_narrowing(self):
        from app.vfs.strategies import build_chain_narrowing_filter
        mount = self._make_mount(date_property="http://purl.org/dc/terms/created")
        result = build_chain_narrowing_filter(
            "by-date", "03-March", mount, parent_folder_value="2024"
        )
        assert "<http://purl.org/dc/terms/created>" in result
        assert '"2024"' in result
        assert "MONTH(?_chainDate) = 3" in result

    def test_by_date_no_property_returns_empty(self):
        from app.vfs.strategies import build_chain_narrowing_filter
        mount = self._make_mount()
        result = build_chain_narrowing_filter("by-date", "2024", mount)
        assert result == ""

    def test_flat_returns_empty(self):
        from app.vfs.strategies import build_chain_narrowing_filter
        mount = self._make_mount()
        result = build_chain_narrowing_filter("flat", "anything", mount)
        assert result == ""

    def test_special_chars_escaped(self):
        from app.vfs.strategies import build_chain_narrowing_filter
        mount = self._make_mount(group_by_property="http://example.org/tags")
        result = build_chain_narrowing_filter("by-tag", 'tag"with"quotes', mount)
        assert r'tag\"with\"quotes' in result


# ── Pydantic Model Chain Validation (S03/T03) ───────────────────────

class TestPydanticStrategyNormalization:
    """Test that Pydantic models accept str | list[str] and normalize to pipe-delimited."""

    def test_create_request_string_strategy(self):
        from app.vfs.mount_router import MountCreateRequest
        req = MountCreateRequest(name="test", path="test", strategy="by-tag")
        assert req.strategy == "by-tag"

    def test_create_request_list_strategy(self):
        from app.vfs.mount_router import MountCreateRequest
        req = MountCreateRequest(name="test", path="test", strategy=["by-tag", "by-date"])
        assert req.strategy == "by-tag|by-date"

    def test_create_request_three_level_chain(self):
        from app.vfs.mount_router import MountCreateRequest
        req = MountCreateRequest(name="test", path="test", strategy=["by-type", "by-tag", "by-date"])
        assert req.strategy == "by-type|by-tag|by-date"

    def test_create_request_rejects_four_levels(self):
        import pytest
        from app.vfs.mount_router import MountCreateRequest
        with pytest.raises(Exception):
            MountCreateRequest(name="test", path="test", strategy=["by-type", "by-tag", "by-date", "flat"])

    def test_create_request_rejects_invalid_strategy(self):
        import pytest
        from app.vfs.mount_router import MountCreateRequest
        with pytest.raises(Exception):
            MountCreateRequest(name="test", path="test", strategy="invalid-strategy")

    def test_create_request_rejects_invalid_in_chain(self):
        import pytest
        from app.vfs.mount_router import MountCreateRequest
        with pytest.raises(Exception):
            MountCreateRequest(name="test", path="test", strategy=["by-tag", "invalid"])

    def test_update_request_string_strategy(self):
        from app.vfs.mount_router import MountUpdateRequest
        req = MountUpdateRequest(strategy="by-type")
        assert req.strategy == "by-type"

    def test_update_request_list_strategy(self):
        from app.vfs.mount_router import MountUpdateRequest
        req = MountUpdateRequest(strategy=["by-tag", "by-date"])
        assert req.strategy == "by-tag|by-date"

    def test_update_request_none_strategy(self):
        from app.vfs.mount_router import MountUpdateRequest
        req = MountUpdateRequest()
        assert req.strategy is None

    def test_preview_request_string_strategy(self):
        from app.vfs.mount_router import MountPreviewRequest
        req = MountPreviewRequest(strategy="flat")
        assert req.strategy == "flat"

    def test_preview_request_list_strategy(self):
        from app.vfs.mount_router import MountPreviewRequest
        req = MountPreviewRequest(strategy=["by-type", "by-tag"])
        assert req.strategy == "by-type|by-tag"

    def test_preview_request_rejects_four_levels(self):
        import pytest
        from app.vfs.mount_router import MountPreviewRequest
        with pytest.raises(Exception):
            MountPreviewRequest(strategy=["by-type", "by-tag", "by-date", "flat"])


class TestMountDefinitionChainDict:
    """Test that MountDefinition.to_dict() correctly exposes chain info for API responses."""

    def test_single_strategy_no_chain_key(self):
        mount = MountDefinition(id="1", name="t", path="t", strategy="by-type")
        d = mount.to_dict()
        assert "strategy_chain" not in d
        assert d["strategy"] == "by-type"

    def test_chain_strategy_includes_chain_key(self):
        mount = MountDefinition(id="1", name="t", path="t", strategy="by-tag|by-date")
        d = mount.to_dict()
        assert d["strategy"] == "by-tag|by-date"
        assert d["strategy_chain"] == ["by-tag", "by-date"]

    def test_three_level_chain_dict(self):
        mount = MountDefinition(id="1", name="t", path="t", strategy="by-type|by-tag|by-date")
        d = mount.to_dict()
        assert d["strategy_chain"] == ["by-type", "by-tag", "by-date"]
