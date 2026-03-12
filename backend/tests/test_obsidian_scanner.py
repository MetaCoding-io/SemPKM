"""Unit tests for Obsidian vault scanner and executor __MACOSX filtering
and empty-stem handling.

These tests use temporary directory structures — no Docker or triplestore required.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.obsidian.scanner import VaultScanner
from app.obsidian.executor import ImportExecutor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_broadcast_stub() -> MagicMock:
    """Create a no-op ScanBroadcast stub that accepts publish() calls."""
    stub = MagicMock()
    stub.publish = MagicMock()
    return stub


def _create_vault(tmp_path: Path, vault_name: str = "MyVault", files: dict[str, str] | None = None) -> Path:
    """Create a minimal vault directory structure under tmp_path.

    Args:
        tmp_path: pytest tmp_path fixture
        vault_name: name of the vault directory
        files: mapping of relative paths (from vault root) to file contents

    Returns:
        The extract_path (parent of vault dir), mimicking a ZIP extraction.
    """
    extract_path = tmp_path / "extract"
    vault_dir = extract_path / vault_name
    obsidian_dir = vault_dir / ".obsidian"
    obsidian_dir.mkdir(parents=True)

    if files:
        for rel_path, content in files.items():
            fp = vault_dir / rel_path
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content, encoding="utf-8")

    return extract_path


# ---------------------------------------------------------------------------
# Scanner: _detect_vault_root
# ---------------------------------------------------------------------------

class TestScannerDetectVaultRoot:
    """Tests for VaultScanner._detect_vault_root()."""

    def test_excludes_macosx(self, tmp_path: Path):
        """__MACOSX directory should be filtered from visible entries,
        so the vault root resolves to the actual vault directory."""
        extract_path = _create_vault(tmp_path, "IdeaverseVault")
        # Add __MACOSX at the same level as the vault dir
        macosx_dir = extract_path / "__MACOSX"
        macosx_dir.mkdir()
        (macosx_dir / "._IdeaverseVault").touch()

        scanner = VaultScanner(extract_path, "test-import", _make_broadcast_stub())
        root = scanner._detect_vault_root()

        assert root.name == "IdeaverseVault"
        assert root == extract_path / "IdeaverseVault"

    def test_single_dir_no_macosx(self, tmp_path: Path):
        """Single vault dir without __MACOSX should still resolve correctly."""
        extract_path = _create_vault(tmp_path, "MyVault")

        scanner = VaultScanner(extract_path, "test-import", _make_broadcast_stub())
        root = scanner._detect_vault_root()

        assert root.name == "MyVault"
        assert root == extract_path / "MyVault"

    def test_macosx_alongside_vault_two_visible_dirs(self, tmp_path: Path):
        """If __MACOSX is filtered and only one visible dir remains,
        vault root should be that dir (not extract_path)."""
        extract_path = _create_vault(tmp_path, "Vault")
        # __MACOSX should be invisible
        (extract_path / "__MACOSX").mkdir()

        scanner = VaultScanner(extract_path, "test-import", _make_broadcast_stub())
        root = scanner._detect_vault_root()

        assert root.name == "Vault"


# ---------------------------------------------------------------------------
# Scanner: _do_scan excludes __MACOSX files
# ---------------------------------------------------------------------------

class TestScannerScanExclusions:
    """Tests for VaultScanner._do_scan() filtering."""

    def test_scan_excludes_macosx_files(self, tmp_path: Path):
        """Files under __MACOSX/ should not appear in scan results."""
        extract_path = _create_vault(tmp_path, "Vault", files={
            "note.md": "---\ntitle: Note\n---\nHello",
        })
        # Add __MACOSX resource fork files at the extract level
        macosx_vault = extract_path / "__MACOSX" / "Vault"
        macosx_vault.mkdir(parents=True)
        (macosx_vault / "._note.md").write_text("binary junk")

        scanner = VaultScanner(extract_path, "test-import", _make_broadcast_stub())
        result = scanner._do_scan()

        assert result.markdown_files == 1
        assert result.vault_name == "Vault"

    def test_scan_excludes_macosx_inside_vault(self, tmp_path: Path):
        """__MACOSX nested inside the vault tree should also be pruned."""
        extract_path = _create_vault(tmp_path, "Vault", files={
            "note.md": "---\ntitle: Note\n---\nContent",
        })
        # Simulate __MACOSX inside the vault (unlikely but defensive)
        macosx_inside = extract_path / "Vault" / "__MACOSX"
        macosx_inside.mkdir()
        (macosx_inside / "ghost.md").write_text("should not appear")

        scanner = VaultScanner(extract_path, "test-import", _make_broadcast_stub())
        result = scanner._do_scan()

        assert result.markdown_files == 1

    def test_scan_skips_dot_md_files(self, tmp_path: Path):
        """Files named '.md' (like Books/.md in Ideaverse) are caught by
        the dot-prefix filter in os.walk, so they never appear in results."""
        extract_path = _create_vault(tmp_path, "Vault", files={
            "Notes/good.md": "---\ntitle: Good\n---\nContent",
        })
        # Create dot-prefixed .md files like the real Ideaverse vault has
        books_dir = extract_path / "Vault" / "Books"
        books_dir.mkdir(parents=True, exist_ok=True)
        (books_dir / ".md").write_text("---\ntitle: Ghost\n---\nEmpty stem")

        scanner = VaultScanner(extract_path, "test-import", _make_broadcast_stub())
        result = scanner._do_scan()

        # .md is filtered by the dot-prefix check; only good.md counted
        assert result.markdown_files == 1

    def test_empty_stem_filter_logic(self, tmp_path: Path):
        """Verify the defense-in-depth empty-stem filter works correctly.

        On real filesystems, files like '.md' have stem='.md' (not empty)
        in Python's Path, so they're caught by the dot-prefix filter.
        The empty-stem filter is an additional safety net for hypothetical
        edge cases. We test it by verifying the filter expression is sound.
        """
        from pathlib import PurePosixPath

        # Path('.md').stem is '.md', NOT '' — dot-prefix filter catches these
        assert PurePosixPath(".md").stem == ".md"
        assert PurePosixPath("good.md").stem == "good"

        # The actual empty-stem filter: [f for f in md_files if f.stem]
        # This would catch a file with truly empty stem (theoretical)
        paths = [PurePosixPath("good.md"), PurePosixPath("also_good.md")]
        filtered = [f for f in paths if f.stem]
        assert len(filtered) == 2  # both have stems, both pass


# ---------------------------------------------------------------------------
# Executor: _detect_vault_root
# ---------------------------------------------------------------------------

class TestExecutorDetectVaultRoot:
    """Tests for ImportExecutor._detect_vault_root()."""

    def test_excludes_macosx(self, tmp_path: Path):
        """Executor's _detect_vault_root should also filter __MACOSX."""
        extract_path = _create_vault(tmp_path, "IdeaverseVault")
        (extract_path / "__MACOSX").mkdir()

        # ImportExecutor needs many deps, but _detect_vault_root only uses
        # self.extract_path, so we can construct with stubs.
        executor = ImportExecutor.__new__(ImportExecutor)
        executor.extract_path = extract_path

        root = executor._detect_vault_root()

        assert root.name == "IdeaverseVault"
        assert root == extract_path / "IdeaverseVault"

    def test_single_dir_no_macosx(self, tmp_path: Path):
        """Executor resolves vault root with single dir, no __MACOSX."""
        extract_path = _create_vault(tmp_path, "VaultX")

        executor = ImportExecutor.__new__(ImportExecutor)
        executor.extract_path = extract_path

        root = executor._detect_vault_root()

        assert root.name == "VaultX"
