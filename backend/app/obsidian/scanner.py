"""Obsidian vault scanner with multi-signal type detection.

Scans an extracted Obsidian vault directory, parsing markdown files
for frontmatter, wiki-links, tags, and applying heuristic type
detection to group notes by likely type.
"""

import asyncio
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import frontmatter

from .broadcast import ScanBroadcast, SSEEvent
from .models import (
    FrontmatterKeySummary,
    NoteTypeGroup,
    ScanWarning,
    TagSummary,
    VaultScanResult,
)

logger = logging.getLogger(__name__)

# Regex patterns
# Wiki-links: [[target]] or [[target|alias]] or [[target#heading]]
# Excludes ![[embeds]] (image/file embeds)
WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]\|#]+)(?:#[^\]\|]*)?\s*(?:\|[^\]]*)?\]\]")

# Tags: #tag preceded by whitespace or line start
TAG_RE = re.compile(r"(?:^|\s)#([a-zA-Z][a-zA-Z0-9_/-]*)", re.MULTILINE)

# Fenced code blocks to strip before extracting links/tags
CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)

# Attachment extensions
ATTACHMENT_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp",
    ".pdf", ".mp3", ".mp4", ".wav", ".ogg", ".webm",
    ".zip", ".tar", ".gz", ".rar",
}

# Folders to skip for folder-based type detection
SKIP_FOLDERS = {
    "attachments", "assets", "images", "templates",
    "archive", "daily", "inbox", ".obsidian", ".trash",
}

# Frontmatter keys that indicate note type (case-insensitive)
TYPE_KEYS = {"type", "category", "class", "kind", "note_type", "notetype"}

# Known Obsidian-specific keys (not type indicators)
OBSIDIAN_KEYS = {"cssclass", "cssclasses", "aliases", "alias"}


class VaultScanner:
    """Scans an extracted Obsidian vault and produces a VaultScanResult."""

    def __init__(self, extract_path: Path, import_id: str, broadcast: ScanBroadcast) -> None:
        self.extract_path = extract_path
        self.import_id = import_id
        self.broadcast = broadcast

    async def scan(self) -> VaultScanResult:
        """Run the vault scan in a background thread to avoid blocking."""
        return await asyncio.to_thread(self._do_scan)

    def _do_scan(self) -> VaultScanResult:
        """Synchronous scan logic."""
        start = time.monotonic()

        # Auto-detect vault root
        vault_root = self._detect_vault_root()
        vault_name = vault_root.name

        # Collect all files
        all_files: list[Path] = []
        folders = set()
        for dirpath, dirnames, filenames in os.walk(vault_root):
            dp = Path(dirpath)
            # Skip hidden directories
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            if dp != vault_root:
                folders.add(dp)
            for fn in filenames:
                if not fn.startswith("."):
                    all_files.append(dp / fn)

        total_files = len(all_files)
        md_files: list[Path] = []
        attachment_count = 0
        other_count = 0

        for f in all_files:
            ext = f.suffix.lower()
            if ext == ".md":
                md_files.append(f)
            elif ext in ATTACHMENT_EXTS:
                attachment_count += 1
            else:
                other_count += 1

        # Parse markdown files
        fm_key_counts: dict[str, dict[str, int | set]] = {}  # key -> {count, samples}
        tag_counts: dict[str, int] = {}
        link_counts: dict[str, int] = {}
        type_buckets: dict[tuple[str, str], list[str]] = {}  # (type_name, signal) -> sample paths (max 10)
        type_counts: dict[tuple[str, str], int] = {}  # (type_name, signal) -> total count
        # Per-group frontmatter key tracking
        group_fm_keys: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
        warnings: list[ScanWarning] = []
        md_stems = {f.stem.lower() for f in md_files}

        for i, md_file in enumerate(md_files):
            rel_path = str(md_file.relative_to(vault_root))

            # Broadcast progress every 10 files
            if i % 10 == 0:
                self.broadcast.publish(SSEEvent(
                    event="scan_progress",
                    data={
                        "scanned": i,
                        "total": len(md_files),
                        "current_file": rel_path,
                    },
                ))

            try:
                post = frontmatter.load(str(md_file))
                meta = post.metadata or {}
                body = post.content or ""
            except Exception as exc:
                warnings.append(ScanWarning(
                    severity="warning",
                    category="malformed_frontmatter",
                    message=f"Could not parse frontmatter: {exc}",
                    file_path=rel_path,
                ))
                # Try reading raw content
                try:
                    body = md_file.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    body = ""
                meta = {}

            # Empty note warning
            if not body.strip():
                warnings.append(ScanWarning(
                    severity="warning",
                    category="empty_note",
                    message="Note has no content after frontmatter",
                    file_path=rel_path,
                ))

            # Collect frontmatter keys
            for key, value in meta.items():
                if key not in fm_key_counts:
                    fm_key_counts[key] = {"count": 0, "samples": set()}
                fm_key_counts[key]["count"] += 1
                samples = fm_key_counts[key]["samples"]
                if len(samples) < 5:
                    val_str = str(value)[:100]
                    samples.add(val_str)

            # Strip code blocks before extracting links/tags
            clean_body = CODE_BLOCK_RE.sub("", body)

            # Extract wiki-links
            for match in WIKILINK_RE.finditer(clean_body):
                target = match.group(1).strip()
                if target:
                    link_counts[target] = link_counts.get(target, 0) + 1

            # Extract tags from body
            for match in TAG_RE.finditer(clean_body):
                tag = match.group(1)
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            # Extract tags from frontmatter
            fm_tags = meta.get("tags") or meta.get("tag")
            if fm_tags:
                if isinstance(fm_tags, str):
                    fm_tags = [t.strip() for t in fm_tags.split(",") if t.strip()]
                if isinstance(fm_tags, list):
                    for tag in fm_tags:
                        tag = str(tag).strip().lstrip("#")
                        if tag:
                            tag_counts[tag] = tag_counts.get(tag, 0) + 1

            # Multi-signal type detection
            type_name = None
            signal_source = None

            # Signal 1: frontmatter type fields
            meta_lower = {k.lower(): v for k, v in meta.items()}
            for tk in TYPE_KEYS:
                if tk in meta_lower:
                    val = str(meta_lower[tk]).strip()
                    if val:
                        type_name = val
                        signal_source = f"frontmatter:{tk}"
                        break

            # Signal 2: parent folder
            if not type_name:
                parent = md_file.parent.name.lower()
                if parent and parent not in SKIP_FOLDERS and md_file.parent != vault_root:
                    type_name = md_file.parent.name  # preserve original case
                    signal_source = f"folder:{type_name}"

            # Signal 3: first tag
            if not type_name:
                first_tag = None
                if fm_tags:
                    tag_list = fm_tags if isinstance(fm_tags, list) else [t.strip() for t in fm_tags.split(",")]
                    if tag_list:
                        first_tag = str(tag_list[0]).strip().lstrip("#")
                if not first_tag:
                    tag_match = TAG_RE.search(clean_body)
                    if tag_match:
                        first_tag = tag_match.group(1)
                if first_tag:
                    type_name = first_tag
                    signal_source = f"tag:{first_tag}"

            # Signal 4: uncategorized
            if not type_name:
                type_name = "Uncategorized"
                signal_source = "none"

            bucket_key = (type_name, signal_source)
            type_counts[bucket_key] = type_counts.get(bucket_key, 0) + 1
            if bucket_key not in type_buckets:
                type_buckets[bucket_key] = []
            if len(type_buckets[bucket_key]) < 10:
                type_buckets[bucket_key].append(rel_path)

            # Track per-group frontmatter keys
            if meta:
                if bucket_key not in group_fm_keys:
                    group_fm_keys[bucket_key] = {}
                for key, value in meta.items():
                    if key not in group_fm_keys[bucket_key]:
                        group_fm_keys[bucket_key][key] = {"count": 0, "samples": set()}
                    group_fm_keys[bucket_key][key]["count"] += 1
                    samples = group_fm_keys[bucket_key][key]["samples"]
                    if len(samples) < 5:
                        samples.add(str(value)[:100])

        # Check for broken wiki-links
        for target, count in link_counts.items():
            if target.lower() not in md_stems:
                warnings.append(ScanWarning(
                    severity="warning",
                    category="broken_link",
                    message=f"Wiki-link target not found in vault ({count} references)",
                    file_path=target,
                ))

        duration = time.monotonic() - start

        # Build type groups with actual counts (not capped sample length)
        type_groups = [
            NoteTypeGroup(
                type_name=type_name,
                signal_source=signal_source,
                count=type_counts.get((type_name, signal_source), 0),
                sample_notes=type_buckets.get((type_name, signal_source), []),
                frontmatter_keys=[
                    FrontmatterKeySummary(
                        key=k,
                        count=v["count"],
                        sample_values=list(v["samples"])[:5],
                    )
                    for k, v in sorted(
                        group_fm_keys.get((type_name, signal_source), {}).items(),
                        key=lambda x: x[1]["count"],
                        reverse=True,
                    )
                ],
            )
            for (type_name, signal_source) in sorted(
                type_counts.keys(), key=lambda k: type_counts[k], reverse=True
            )
        ]

        # Build frontmatter key summaries
        fm_summaries = [
            FrontmatterKeySummary(
                key=key,
                count=info["count"],
                sample_values=list(info["samples"])[:5],
            )
            for key, info in sorted(fm_key_counts.items(), key=lambda x: x[1]["count"], reverse=True)
        ]

        # Build tag summaries
        tag_summaries = [
            TagSummary(tag=tag, count=count)
            for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        # Build wikilink targets
        wikilink_list = [
            {"target": target, "count": count}
            for target, count in sorted(link_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        # Final progress
        self.broadcast.publish(SSEEvent(
            event="scan_complete",
            data={"import_id": self.import_id},
        ))

        return VaultScanResult(
            vault_name=vault_name,
            import_id=self.import_id,
            extract_path=str(self.extract_path),
            total_files=total_files,
            markdown_files=len(md_files),
            attachment_files=attachment_count,
            other_files=other_count,
            folders=len(folders),
            type_groups=type_groups,
            frontmatter_keys=fm_summaries,
            tags=tag_summaries,
            wikilink_targets=wikilink_list,
            warnings=warnings,
            scan_duration_seconds=round(duration, 2),
        )

    def _detect_vault_root(self) -> Path:
        """Auto-detect vault root directory.

        If the extracted ZIP has a single top-level directory containing
        .obsidian/, use that as the vault root. Otherwise use extract_path.
        """
        entries = list(self.extract_path.iterdir())
        # Filter out hidden files/dirs at top level
        visible = [e for e in entries if not e.name.startswith(".")]

        if len(visible) == 1 and visible[0].is_dir():
            candidate = visible[0]
            if (candidate / ".obsidian").is_dir():
                return candidate
            # Single dir but no .obsidian — still use it as root
            return candidate

        return self.extract_path
