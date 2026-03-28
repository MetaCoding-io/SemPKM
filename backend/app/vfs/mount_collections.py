"""WebDAV collection classes for custom mount directories.

Mount directories appear alongside model directories at the WebDAV root.
Each mount uses a strategy (flat, by-type, by-date, by-tag, by-property)
to organize objects into a folder hierarchy driven by SPARQL queries.

Hierarchy:
  /mount-prefix/                       -> MountRootCollection
  /mount-prefix/folder/                -> StrategyFolderCollection
  /mount-prefix/folder/file.md         -> MountedResourceFile
  /mount-prefix/year/month/file.md     -> MountedResourceFile (by-date)
"""

from __future__ import annotations

import hashlib
import logging
import re

from wsgidav.dav_provider import DAVCollection
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN

from app.triplestore.sync_client import SyncTriplestoreClient
from app.vfs.cache import cached_get_member_names
from app.vfs.mount_service import MountDefinition
from app.vfs.strategies import (
    DirectoryStrategy,
    build_chain_narrowing_filter,
    build_scope_filter,
    query_date_month_folders,
    query_date_year_folders,
    query_flat_objects,
    query_has_uncategorized,
    query_objects_by_date,
    query_objects_by_property,
    query_objects_by_tag,
    query_objects_by_type,
    query_property_folders,
    query_tag_folders,
    query_type_folders,
    query_uncategorized_objects,
)
from app.rdf.namespaces import CURRENT_GRAPH

logger = logging.getLogger(__name__)

_UNCATEGORIZED = "_uncategorized"

# Month name lookup for by-date folder labels
_MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")
    return slug or "untitled"


def _build_file_map_from_bindings(
    bindings: list[dict],
    filename_template: str | None = None,
    type_labels: dict[str, str] | None = None,
) -> dict[str, dict]:
    """Build filename -> {iri, label, type_iri} map from SPARQL bindings.

    If filename_template is provided, template variables are expanded before
    slugification. Supported variables: {title}, {date}, {type}, {id}.
    Handles slug deduplication by appending IRI hash suffix.
    """
    entries = []
    slug_counts: dict[str, int] = {}
    for b in bindings:
        iri = b["iri"]["value"]
        label = b["label"]["value"]
        type_iri = b.get("typeIri", {}).get("value", "")

        if filename_template:
            expanded = filename_template
            expanded = expanded.replace("{title}", label)
            expanded = expanded.replace("{id}", hashlib.sha256(iri.encode()).hexdigest()[:8])
            if "{date}" in expanded:
                date_val = b.get("created", {}).get("value", "")
                date_str = date_val[:10] if date_val else "undated"
                expanded = expanded.replace("{date}", date_str)
            if "{type}" in expanded:
                type_label = ""
                if type_labels and type_iri:
                    type_label = type_labels.get(type_iri, "")
                if not type_label and type_iri:
                    type_label = type_iri.rsplit("/", 1)[-1].rsplit("#", 1)[-1].rsplit(":", 1)[-1]
                expanded = expanded.replace("{type}", type_label or "unknown")
            slug = _slugify(expanded)
            logger.debug(
                "filename_template expanded: template=%r iri=%s slug=%s",
                filename_template, iri, slug,
            )
        else:
            slug = _slugify(label)

        slug_counts[slug] = slug_counts.get(slug, 0) + 1
        entries.append({"iri": iri, "label": label, "slug": slug, "type_iri": type_iri})

    file_map: dict[str, dict] = {}
    for entry in entries:
        slug = entry["slug"]
        if slug_counts[slug] > 1:
            iri_hash = hashlib.sha256(entry["iri"].encode()).hexdigest()[:6]
            filename = f"{slug}--{iri_hash}.md"
        else:
            filename = f"{slug}.md"
        file_map[filename] = {
            "iri": entry["iri"],
            "label": entry["label"],
            "type_iri": entry["type_iri"],
        }
    return file_map


class MountRootCollection(DAVCollection):
    """Top-level directory for a mount (e.g., /my-notes/).

    Dispatches to strategy-specific sub-collections or flat file listing.
    """

    def __init__(
        self,
        path: str,
        environ: dict,
        client: SyncTriplestoreClient,
        mount: MountDefinition,
        event_store=None,
    ) -> None:
        super().__init__(path, environ)
        self._client = client
        self._mount = mount
        self._event_store = event_store
        self._strategy = DirectoryStrategy(mount.strategy)
        self._scope_filter = build_scope_filter(mount, sync_client=client)
        # Cached file map for flat strategy
        self._flat_file_map: dict[str, dict] | None = None

    def get_member_names(self) -> list[str]:
        """Return folder names (or file names for flat strategy)."""
        cache_key = f"mount:{self._mount.id}:folders"

        def _load():
            strategy = self._strategy
            if strategy == DirectoryStrategy.FLAT:
                return list(self._get_flat_file_map().keys())
            elif strategy == DirectoryStrategy.BY_TYPE:
                return self._load_type_folders()
            elif strategy == DirectoryStrategy.BY_DATE:
                return self._load_date_year_folders()
            elif strategy == DirectoryStrategy.BY_TAG:
                return self._load_tag_folders()
            elif strategy == DirectoryStrategy.BY_PROPERTY:
                return self._load_property_folders()
            return []

        return cached_get_member_names(cache_key, _load)

    def get_member(self, name: str):
        """Return child collection or resource for the given name."""
        member_path = f"{self.path.rstrip('/')}/{name}"

        strategy = self._strategy
        if strategy == DirectoryStrategy.FLAT:
            # Flat: children are .md files
            obj = self._get_flat_file_map().get(name)
            if obj is None:
                return None
            from app.vfs.mount_resource import MountedResourceFile
            return MountedResourceFile(
                member_path,
                self.environ,
                self._client,
                object_iri=obj["iri"],
                object_label=obj["label"],
                type_iri=obj["type_iri"],
                event_store=self._event_store,
            )
        else:
            # Other strategies: children are folders
            return StrategyFolderCollection(
                member_path,
                self.environ,
                self._client,
                self._mount,
                folder_value=name,
                event_store=self._event_store,
            )

    # ── Strategy-specific folder loaders ──────────────────────────────

    def _get_flat_file_map(self) -> dict[str, dict]:
        """Lazily build flat file map."""
        if self._flat_file_map is None:
            sparql = query_flat_objects(self._scope_filter)
            result = self._client.query(sparql)
            self._flat_file_map = _build_file_map_from_bindings(
                result["results"]["bindings"],
                filename_template=self._mount.filename_template,
            )
        return self._flat_file_map

    def _load_type_folders(self) -> list[str]:
        sparql = query_type_folders(self._scope_filter)
        result = self._client.query(sparql)
        return [
            b["typeLabel"]["value"]
            for b in result["results"]["bindings"]
            if b.get("typeLabel", {}).get("value")
        ]

    def _load_date_year_folders(self) -> list[str]:
        if not self._mount.date_property:
            return []
        sparql = query_date_year_folders(self._mount.date_property, self._scope_filter)
        result = self._client.query(sparql)
        return [
            b["year"]["value"]
            for b in result["results"]["bindings"]
            if b.get("year", {}).get("value")
        ]

    def _load_tag_folders(self) -> list[str]:
        if not self._mount.group_by_property:
            return []
        sparql = query_tag_folders(self._mount.group_by_property, self._scope_filter)
        result = self._client.query(sparql)
        folders = [
            b["tagValue"]["value"]
            for b in result["results"]["bindings"]
            if b.get("tagValue", {}).get("value")
        ]
        # Check for uncategorized objects
        if self._has_uncategorized():
            folders.append(_UNCATEGORIZED)
        return folders

    def _load_property_folders(self) -> list[str]:
        if not self._mount.group_by_property:
            return []
        sparql = query_property_folders(
            self._mount.group_by_property, self._scope_filter
        )
        result = self._client.query(sparql)
        folders = [
            b["groupLabel"]["value"]
            for b in result["results"]["bindings"]
            if b.get("groupLabel", {}).get("value")
        ]
        # Check for uncategorized objects
        if self._has_uncategorized():
            folders.append(_UNCATEGORIZED)
        return folders

    def _has_uncategorized(self) -> bool:
        """Check if any objects are missing the grouping property."""
        if not self._mount.group_by_property:
            return False
        sparql = query_has_uncategorized(
            self._mount.group_by_property, self._scope_filter
        )
        result = self._client.query(sparql)
        return result.get("boolean", False)

    # Read-only enforcement
    def create_empty_resource(self, name: str):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def create_collection(self, name: str):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def handle_delete(self):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def handle_move(self, dest_path):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def handle_copy(self, dest_path, *, depth_infinity=None):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")


class StrategyFolderCollection(DAVCollection):
    """A subfolder within a mount (e.g., /my-notes/machine-learning/).

    folder_value holds the raw value that defines this folder:
      - by-type: type local name (e.g., "Note")
      - by-date at year level: year string (e.g., "2024")
      - by-date at month level: "MM-MonthName" (e.g., "01-January")
      - by-tag: tag literal value
      - by-property: property value label
    """

    def __init__(
        self,
        path: str,
        environ: dict,
        client: SyncTriplestoreClient,
        mount: MountDefinition,
        folder_value: str,
        parent_folder_value: str | None = None,
        chain: list[str] | None = None,
        chain_depth: int = 0,
        chain_folder_values: list[str] | None = None,
        event_store=None,
    ) -> None:
        super().__init__(path, environ)
        self._client = client
        self._mount = mount
        self._folder_value = folder_value
        self._parent_folder_value = parent_folder_value
        self._event_store = event_store
        self._chain = chain
        self._chain_depth = chain_depth
        self._chain_folder_values = chain_folder_values or []

        # Compute effective strategy: chain-aware or single
        if chain is not None:
            self._strategy = DirectoryStrategy(chain[chain_depth])
        else:
            self._strategy = DirectoryStrategy(mount.strategy)

        # Compute terminal status
        if chain is not None:
            self._is_terminal = chain_depth >= len(chain) - 1
        else:
            # Non-chain: terminal unless it's by-date at year level (existing behavior)
            self._is_terminal = not (
                self._strategy == DirectoryStrategy.BY_DATE
                and self._parent_folder_value is None
            )

        # Build scope filter with cumulative chain narrowing
        self._scope_filter = self._build_cumulative_scope_filter()
        self._file_map: dict[str, dict] | None = None

    def _build_cumulative_scope_filter(self) -> str:
        """Build scope filter combining base scope + all parent chain narrowing filters."""
        base_filter = build_scope_filter(self._mount, sync_client=self._client)
        if self._chain is None:
            return base_filter

        parts = [base_filter] if base_filter else []
        # Add narrowing from each parent chain level
        for depth, folder_val in enumerate(self._chain_folder_values):
            strategy_at_depth = self._chain[depth]
            # For by-date, determine if this is year or month level
            parent_val = None
            if strategy_at_depth == "by-date" and depth > 0:
                # Check if previous level in chain_folder_values provides year context
                # This is a simplification — by-date in a chain uses the folder value as year
                pass
            narrowing = build_chain_narrowing_filter(
                strategy_at_depth, folder_val, self._mount,
                parent_folder_value=parent_val,
            )
            if narrowing:
                parts.append(narrowing)
                logger.debug(
                    "Chain narrowing at depth %d (strategy=%s, value=%s): %s",
                    depth, strategy_at_depth, folder_val, narrowing,
                )

        return "\n  ".join(parts)

    def get_member_names(self) -> list[str]:
        """Return file names or sub-folder names."""
        strategy = self._strategy

        # ── Chain-aware dispatch ──
        if self._chain is not None:
            if self._is_terminal:
                # Terminal chain depth: return files
                cache_key = f"mount:{self._mount.id}:chain:{self._chain_depth}:{self._folder_value}:files"

                def _load():
                    return list(self._ensure_file_map().keys())

                return cached_get_member_names(cache_key, _load)
            else:
                # Non-terminal: return sub-folder names using NEXT strategy's folder query
                next_strategy = DirectoryStrategy(self._chain[self._chain_depth + 1])
                cache_key = f"mount:{self._mount.id}:chain:{self._chain_depth}:{self._folder_value}:subfolders"

                def _load_subfolders():
                    return self._load_chain_subfolders(next_strategy)

                return cached_get_member_names(cache_key, _load_subfolders)

        # ── Non-chain: existing behavior ──
        cache_key = f"mount:{self._mount.id}:{self._folder_value}:files"

        # by-date year level: return month folders, not files
        if strategy == DirectoryStrategy.BY_DATE and self._parent_folder_value is None:
            cache_key = f"mount:{self._mount.id}:{self._folder_value}:months"

            def _load_months():
                return self._load_month_folders()

            return cached_get_member_names(cache_key, _load_months)

        def _load():
            return list(self._ensure_file_map().keys())

        return cached_get_member_names(cache_key, _load)

    def get_member(self, name: str):
        """Return child resource or sub-collection."""
        member_path = f"{self.path.rstrip('/')}/{name}"

        strategy = self._strategy

        # ── Chain-aware dispatch ──
        if self._chain is not None:
            if self._is_terminal:
                # Terminal: children are .md files
                obj = self._ensure_file_map().get(name)
                if obj is None:
                    return None
                from app.vfs.mount_resource import MountedResourceFile
                return MountedResourceFile(
                    member_path,
                    self.environ,
                    self._client,
                    object_iri=obj["iri"],
                    object_label=obj["label"],
                    type_iri=obj["type_iri"],
                    event_store=self._event_store,
                )
            else:
                # Non-terminal: children are sub-folders at next chain depth
                new_folder_values = self._chain_folder_values + [self._folder_value]
                return StrategyFolderCollection(
                    member_path,
                    self.environ,
                    self._client,
                    self._mount,
                    folder_value=name,
                    chain=self._chain,
                    chain_depth=self._chain_depth + 1,
                    chain_folder_values=new_folder_values,
                    event_store=self._event_store,
                )

        # ── Non-chain: existing behavior ──

        # by-date year level: children are month folders
        if strategy == DirectoryStrategy.BY_DATE and self._parent_folder_value is None:
            return StrategyFolderCollection(
                member_path,
                self.environ,
                self._client,
                self._mount,
                folder_value=name,
                parent_folder_value=self._folder_value,  # year
                event_store=self._event_store,
            )

        # All other cases: children are .md files
        obj = self._ensure_file_map().get(name)
        if obj is None:
            return None
        from app.vfs.mount_resource import MountedResourceFile
        return MountedResourceFile(
            member_path,
            self.environ,
            self._client,
            object_iri=obj["iri"],
            object_label=obj["label"],
            type_iri=obj["type_iri"],
            event_store=self._event_store,
        )

    def get_object_by_filename(self, filename: str) -> dict | None:
        """Return object info for a filename."""
        return self._ensure_file_map().get(filename)

    # ── File map builders ─────────────────────────────────────────────

    def _ensure_file_map(self) -> dict[str, dict]:
        """Lazily build and cache the file map."""
        if self._file_map is None:
            self._file_map = self._build_file_map()
        return self._file_map

    def _build_file_map(self) -> dict[str, dict]:
        """Build filename -> object info map for this folder's strategy.

        For chain mounts, scope narrowing from parent levels is already
        included in self._scope_filter (cumulative). Additionally, the
        current folder's own constraint is added.
        """
        strategy = self._strategy
        sf = self._scope_filter

        # Add current folder's own narrowing to the scope filter
        if self._chain is not None:
            current_narrowing = build_chain_narrowing_filter(
                self._chain[self._chain_depth],
                self._folder_value,
                self._mount,
                parent_folder_value=self._parent_folder_value,
            )
            if current_narrowing:
                sf = f"{sf}\n  {current_narrowing}" if sf else current_narrowing

        if strategy == DirectoryStrategy.BY_TYPE:
            sparql = self._build_by_type_query(sf)
        elif strategy == DirectoryStrategy.BY_DATE:
            sparql = self._build_by_date_query(sf)
        elif strategy == DirectoryStrategy.BY_TAG:
            sparql = self._build_by_tag_query(sf)
        elif strategy == DirectoryStrategy.BY_PROPERTY:
            sparql = self._build_by_property_query(sf)
        else:
            return {}

        result = self._client.query(sparql)
        return _build_file_map_from_bindings(
            result["results"]["bindings"],
            filename_template=self._mount.filename_template,
        )

    def _load_chain_subfolders(self, next_strategy: DirectoryStrategy) -> list[str]:
        """Load sub-folder names for a non-terminal chain level.

        Uses the NEXT strategy's folder query builder with the current
        cumulative scope filter + this folder's own narrowing.
        """
        sf = self._scope_filter

        # Add current folder's own narrowing
        current_narrowing = build_chain_narrowing_filter(
            self._chain[self._chain_depth],
            self._folder_value,
            self._mount,
            parent_folder_value=self._parent_folder_value,
        )
        if current_narrowing:
            sf = f"{sf}\n  {current_narrowing}" if sf else current_narrowing

        if next_strategy == DirectoryStrategy.BY_TYPE:
            sparql = query_type_folders(sf)
            result = self._client.query(sparql)
            return [
                b["typeLabel"]["value"]
                for b in result["results"]["bindings"]
                if b.get("typeLabel", {}).get("value")
            ]

        elif next_strategy == DirectoryStrategy.BY_DATE:
            if not self._mount.date_property:
                return []
            sparql = query_date_year_folders(self._mount.date_property, sf)
            result = self._client.query(sparql)
            return [
                b["year"]["value"]
                for b in result["results"]["bindings"]
                if b.get("year", {}).get("value")
            ]

        elif next_strategy == DirectoryStrategy.BY_TAG:
            if not self._mount.group_by_property:
                return []
            sparql = query_tag_folders(self._mount.group_by_property, sf)
            result = self._client.query(sparql)
            return [
                b["tagValue"]["value"]
                for b in result["results"]["bindings"]
                if b.get("tagValue", {}).get("value")
            ]

        elif next_strategy == DirectoryStrategy.BY_PROPERTY:
            if not self._mount.group_by_property:
                return []
            sparql = query_property_folders(self._mount.group_by_property, sf)
            result = self._client.query(sparql)
            return [
                b["groupLabel"]["value"]
                for b in result["results"]["bindings"]
                if b.get("groupLabel", {}).get("value")
            ]

        elif next_strategy == DirectoryStrategy.FLAT:
            # Flat at a sub-level: return files directly
            sparql = query_flat_objects(sf)
            result = self._client.query(sparql)
            fm = _build_file_map_from_bindings(
                result["results"]["bindings"],
                filename_template=self._mount.filename_template,
            )
            return list(fm.keys())

        return []

    def _build_by_type_query(self, scope_filter: str | None = None) -> str:
        """Query objects of the type matching this folder's label."""
        sf = scope_filter if scope_filter is not None else self._scope_filter
        # Resolve the type IRI from the type label
        type_iri = self._resolve_type_iri_from_label(self._folder_value)
        if type_iri:
            return query_objects_by_type(type_iri, sf)
        # Fallback: no objects
        return f"SELECT ?iri ?label ?typeIri FROM <{CURRENT_GRAPH}> WHERE {{ FILTER(false) }}"

    def _build_by_date_query(self, scope_filter: str | None = None) -> str:
        """Query objects for a specific year+month."""
        sf = scope_filter if scope_filter is not None else self._scope_filter
        if not self._mount.date_property or not self._parent_folder_value:
            return f"SELECT ?iri ?label ?typeIri FROM <{CURRENT_GRAPH}> WHERE {{ FILTER(false) }}"

        year = self._parent_folder_value
        # Parse month from "MM-MonthName" format
        month = self._parse_month_number(self._folder_value)
        if month is None:
            return f"SELECT ?iri ?label ?typeIri FROM <{CURRENT_GRAPH}> WHERE {{ FILTER(false) }}"

        return query_objects_by_date(
            self._mount.date_property, year, month, sf
        )

    def _build_by_tag_query(self, scope_filter: str | None = None) -> str:
        """Query objects with a specific tag value."""
        sf = scope_filter if scope_filter is not None else self._scope_filter
        if not self._mount.group_by_property:
            return f"SELECT ?iri ?label ?typeIri FROM <{CURRENT_GRAPH}> WHERE {{ FILTER(false) }}"

        if self._folder_value == _UNCATEGORIZED:
            return query_uncategorized_objects(
                self._mount.group_by_property, sf
            )
        return query_objects_by_tag(
            self._mount.group_by_property, self._folder_value, sf
        )

    def _build_by_property_query(self, scope_filter: str | None = None) -> str:
        """Query objects with a specific property value."""
        sf = scope_filter if scope_filter is not None else self._scope_filter
        if not self._mount.group_by_property:
            return f"SELECT ?iri ?label ?typeIri FROM <{CURRENT_GRAPH}> WHERE {{ FILTER(false) }}"

        if self._folder_value == _UNCATEGORIZED:
            return query_uncategorized_objects(
                self._mount.group_by_property, sf
            )

        # Try to resolve folder label back to IRI or literal value
        group_value, is_iri = self._resolve_group_value(self._folder_value)
        return query_objects_by_property(
            self._mount.group_by_property, group_value, is_iri, sf
        )

    # ── Helpers ───────────────────────────────────────────────────────

    def _resolve_type_iri_from_label(self, type_label: str) -> str | None:
        """Resolve type IRI from its local name label via shapes graphs."""
        result = self._client.query(
            f"""
            PREFIX sh: <http://www.w3.org/ns/shacl#>
            SELECT ?class WHERE {{
              GRAPH ?g {{
                ?shape sh:targetClass ?class .
                FILTER(STRSTARTS(STR(?g), "urn:sempkm:model:") && STRENDS(STR(?g), ":shapes"))
              }}
              FILTER(REPLACE(STR(?class), ".*[/:#]", "") = "{type_label}")
            }}
            LIMIT 1
            """
        )
        bindings = result["results"]["bindings"]
        return bindings[0]["class"]["value"] if bindings else None

    def _resolve_group_value(self, folder_label: str) -> tuple[str, bool]:
        """Resolve a folder label back to its original property value.

        Returns (value_string, is_iri). For IRI values where the label was
        derived from the IRI local name, we need to find the original IRI.
        For literal values, the label IS the value.
        """
        if not self._mount.group_by_property:
            return folder_label, False

        # Try to find an IRI value whose resolved label matches
        sparql = f"""
SELECT ?groupValue
FROM <{CURRENT_GRAPH}>
WHERE {{
  ?iri <{self._mount.group_by_property}> ?groupValue .
  FILTER(isIRI(?groupValue))
  OPTIONAL {{ ?groupValue <http://purl.org/dc/terms/title> ?gt }}
  OPTIONAL {{ ?groupValue <http://www.w3.org/2000/01/rdf-schema#label> ?gr }}
  BIND(COALESCE(?gt, ?gr, REPLACE(STR(?groupValue), ".*[/:#]", "")) AS ?resolvedLabel)
  FILTER(STR(?resolvedLabel) = "{folder_label}")
}}
LIMIT 1
"""
        result = self._client.query(sparql)
        bindings = result["results"]["bindings"]
        if bindings:
            return bindings[0]["groupValue"]["value"], True

        # Fall back to literal match
        return folder_label, False

    def _load_month_folders(self) -> list[str]:
        """Load month folders for a by-date year folder."""
        if not self._mount.date_property:
            return []
        sparql = query_date_month_folders(
            self._mount.date_property, self._folder_value, self._scope_filter
        )
        result = self._client.query(sparql)
        folders = []
        for b in result["results"]["bindings"]:
            month_num_str = b.get("monthNum", {}).get("value", "")
            try:
                month_num = int(float(month_num_str))
                month_name = _MONTH_NAMES.get(month_num, "Unknown")
                folders.append(f"{month_num:02d}-{month_name}")
            except (ValueError, TypeError):
                continue
        return folders

    @staticmethod
    def _parse_month_number(month_folder: str) -> int | None:
        """Parse month number from 'MM-MonthName' folder format."""
        if "-" in month_folder:
            try:
                return int(month_folder.split("-")[0])
            except ValueError:
                return None
        return None

    # Read-only enforcement
    def create_empty_resource(self, name: str):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def create_collection(self, name: str):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def handle_delete(self):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def handle_move(self, dest_path):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def handle_copy(self, dest_path, *, depth_infinity=None):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")
