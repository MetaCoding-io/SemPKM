"""Obsidian vault import executor.

Two-pass import engine: Pass 1 creates RDF objects with properties,
bodies, and tags. Pass 2 resolves wiki-links to dcterms:references edges.
Broadcasts SSE progress events throughout execution.
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

import frontmatter as fm_lib
from rdflib import Literal, URIRef

from app.auth.models import User
from app.commands.handlers.body_set import handle_body_set
from app.commands.handlers.edge_create import handle_edge_create
from app.commands.handlers.object_create import (
    _resolve_predicate,
    handle_object_create,
)
from app.commands.schemas import (
    BodySetParams,
    EdgeCreateParams,
    ObjectCreateParams,
)
from app.config import settings
from app.events.store import EventStore
from app.triplestore.client import TriplestoreClient

from .broadcast import ScanBroadcast, SSEEvent
from .models import ImportResult, MappingConfig, VaultScanResult
from .scanner import CODE_BLOCK_RE, TAG_RE, SKIP_FOLDERS, TYPE_KEYS

logger = logging.getLogger(__name__)

# Enhanced wiki-link regex that captures alias
WIKILINK_FULL_RE = re.compile(
    r"(?<!!)\[\[([^\]\|#]+)(?:#[^\]\|]*)?\s*(?:\|([^\]]*))?\]\]"
)


class ImportExecutor:
    """Two-pass Obsidian vault import executor.

    Pass 1: Creates RDF objects with type, properties, body, and tags.
    Pass 2: Resolves wiki-links between imported notes to edges.
    """

    def __init__(
        self,
        scan_result: VaultScanResult,
        mapping_config: MappingConfig,
        extract_path: Path,
        event_store: EventStore,
        triplestore_client: TriplestoreClient,
        user: User,
        broadcast: ScanBroadcast,
        import_dir: Path,
    ) -> None:
        self.scan_result = scan_result
        self.mapping_config = mapping_config
        self.extract_path = extract_path
        self.event_store = event_store
        self.triplestore_client = triplestore_client
        self.user = user
        self.broadcast = broadcast
        self.import_dir = import_dir
        self._user_iri = URIRef(f"urn:sempkm:user:{user.id}")
        self._base_namespace = settings.base_namespace

    async def execute(self) -> ImportResult:
        """Run the two-pass import and return results."""
        start = time.monotonic()
        result = ImportResult()

        try:
            # Detect vault root (same logic as scanner)
            vault_root = self._detect_vault_root()

            # Query existing imports for deduplication
            existing_sources = await self._get_existing_import_sources()

            # Collect all markdown files
            md_files = sorted(vault_root.rglob("*.md"))
            # Filter out hidden directories
            md_files = [
                f for f in md_files
                if not any(part.startswith(".") for part in f.relative_to(vault_root).parts)
            ]

            total_notes = len(md_files)

            # Pass 1: Create objects
            filename_to_iri: dict[str, str] = {}  # stem.lower() -> object_iri
            note_links: list[tuple[str, list[tuple[str, str | None]]]] = []
            # (source_iri, [(target_name, alias)])

            for i, md_file in enumerate(md_files):
                rel_path = str(md_file.relative_to(vault_root))

                # Broadcast progress
                self.broadcast.publish(SSEEvent(
                    event="import_progress",
                    data={
                        "phase": "objects",
                        "current": i + 1,
                        "total": total_notes,
                        "current_file": rel_path,
                    },
                ))

                # Check deduplication
                if rel_path in existing_sources:
                    result.skipped_existing += 1
                    continue

                try:
                    # Parse note
                    post = fm_lib.load(str(md_file))
                    meta = post.metadata or {}
                    body = post.content or ""

                    # Detect type group
                    group_key = self._detect_group_key(
                        rel_path, meta, body, md_file, vault_root
                    )
                    if group_key is None:
                        result.skipped_errors += 1
                        continue

                    # Look up type mapping
                    type_mapping = self.mapping_config.type_mappings.get(group_key)
                    if type_mapping is None:
                        # No mapping or explicitly skipped
                        result.skipped_existing += 1
                        continue

                    # Build properties from frontmatter mappings
                    properties: dict[str, Any] = {}
                    type_iri = type_mapping.target_type_iri
                    prop_mappings = self.mapping_config.property_mappings.get(
                        type_iri, {}
                    )
                    for fm_key, pm in prop_mappings.items():
                        if pm is not None and fm_key in meta:
                            value = meta[fm_key]
                            if isinstance(value, list):
                                # Use first value for single-valued properties
                                value = ", ".join(str(v) for v in value)
                            properties[pm.target_property_iri] = str(value)

                    # Add import source and title
                    properties["sempkm:importSource"] = rel_path
                    stem_name = md_file.stem
                    properties["dcterms:title"] = stem_name

                    # Create object
                    create_params = ObjectCreateParams(
                        type=type_iri,
                        slug=None,
                        properties=properties,
                    )
                    create_op = await handle_object_create(
                        create_params, self._base_namespace
                    )
                    object_iri = create_op.affected_iris[0]

                    # Add tags as multi-valued schema:keywords
                    clean_body = CODE_BLOCK_RE.sub("", body)
                    tags = set()
                    for match in TAG_RE.finditer(clean_body):
                        tags.add(match.group(1))
                    # Also extract frontmatter tags
                    fm_tags = meta.get("tags") or meta.get("tag")
                    if fm_tags:
                        if isinstance(fm_tags, str):
                            fm_tags = [
                                t.strip() for t in fm_tags.split(",") if t.strip()
                            ]
                        if isinstance(fm_tags, list):
                            for tag in fm_tags:
                                tag_str = str(tag).strip().lstrip("#")
                                if tag_str:
                                    tags.add(tag_str)

                    if tags:
                        subject = URIRef(object_iri)
                        keywords_pred = _resolve_predicate("schema:keywords")
                        for tag in sorted(tags):
                            tag_triple = (subject, keywords_pred, Literal(tag))
                            create_op.data_triples.append(tag_triple)
                            create_op.materialize_inserts.append(tag_triple)

                    # Build operations list
                    operations = [create_op]

                    # Set body if non-empty
                    if body.strip():
                        body_params = BodySetParams(iri=object_iri, body=body)
                        body_op = await handle_body_set(
                            body_params, self._base_namespace
                        )
                        operations.append(body_op)

                    # Commit object + body atomically
                    await self.event_store.commit(
                        operations,
                        performed_by=self._user_iri,
                        performed_by_role=self.user.role,
                    )

                    result.created += 1
                    filename_to_iri[stem_name.lower()] = object_iri

                    # Extract wiki-links for Pass 2
                    links = []
                    for match in WIKILINK_FULL_RE.finditer(clean_body):
                        target_name = match.group(1).strip()
                        alias = match.group(2)
                        if alias:
                            alias = alias.strip()
                        if target_name:
                            links.append((target_name, alias))
                    if links:
                        note_links.append((object_iri, links))

                except Exception as exc:
                    logger.warning(
                        "Import error for %s: %s", rel_path, exc, exc_info=True
                    )
                    result.skipped_errors += 1
                    result.errors.append((rel_path, str(exc)))

            # Pass 2: Create edges from wiki-links
            edge_batch: list[Any] = []
            total_links = sum(len(links) for _, links in note_links)
            link_idx = 0

            for source_iri, links in note_links:
                for target_name, alias in links:
                    link_idx += 1

                    # Broadcast progress
                    if link_idx % 5 == 0 or link_idx == total_links:
                        self.broadcast.publish(SSEEvent(
                            event="import_progress",
                            data={
                                "phase": "edges",
                                "current": link_idx,
                                "total": total_links,
                                "current_link": target_name,
                            },
                        ))

                    target_iri = filename_to_iri.get(target_name.lower())
                    if target_iri is None:
                        result.unresolved_links.append(
                            (source_iri, target_name)
                        )
                        continue

                    try:
                        edge_props: dict[str, Any] = {}
                        if alias:
                            edge_props["rdfs:label"] = alias

                        edge_params = EdgeCreateParams(
                            source=source_iri,
                            target=target_iri,
                            predicate="dcterms:references",
                            properties=edge_props,
                        )
                        edge_op = await handle_edge_create(
                            edge_params, self._base_namespace
                        )
                        edge_batch.append(edge_op)

                        # Batch commit every 10 edges
                        if len(edge_batch) >= 10:
                            await self.event_store.commit(
                                edge_batch,
                                performed_by=self._user_iri,
                                performed_by_role=self.user.role,
                            )
                            result.edges_created += len(edge_batch)
                            edge_batch = []

                    except Exception as exc:
                        logger.warning(
                            "Edge creation error %s -> %s: %s",
                            source_iri,
                            target_name,
                            exc,
                        )

            # Commit remaining edges
            if edge_batch:
                try:
                    await self.event_store.commit(
                        edge_batch,
                        performed_by=self._user_iri,
                        performed_by_role=self.user.role,
                    )
                    result.edges_created += len(edge_batch)
                except Exception as exc:
                    logger.warning("Final edge batch commit error: %s", exc)

            result.duration_seconds = round(time.monotonic() - start, 2)

            # Persist result
            result_path = self.import_dir / "import_result.json"
            result_path.write_text(json.dumps(result.to_dict(), indent=2))

            # Broadcast completion
            self.broadcast.publish(SSEEvent(
                event="import_complete",
                data=result.to_dict(),
            ))

        except Exception as exc:
            logger.error("Import failed: %s", exc, exc_info=True)
            result.duration_seconds = round(time.monotonic() - start, 2)
            self.broadcast.publish(SSEEvent(
                event="import_error",
                data={"message": str(exc)},
            ))

        return result

    async def _get_existing_import_sources(self) -> set[str]:
        """Query triplestore for existing sempkm:importSource values."""
        sparql = """
        SELECT ?source WHERE {
            GRAPH <urn:sempkm:current> {
                ?s <urn:sempkm:importSource> ?source .
            }
        }
        """
        try:
            resp = await self.triplestore_client.query(sparql)
            sources = set()
            for binding in resp.get("results", {}).get("bindings", []):
                val = binding.get("source", {}).get("value", "")
                if val:
                    sources.add(val)
            return sources
        except Exception as exc:
            logger.warning("Failed to query import sources: %s", exc)
            return set()

    def _detect_group_key(
        self,
        rel_path: str,
        meta: dict,
        body: str,
        md_file: Path,
        vault_root: Path,
    ) -> str | None:
        """Detect the type group key for a note, mirroring scanner logic.

        Returns a group key like "type_name|signal_source" or None.
        """
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
            if (
                parent
                and parent not in SKIP_FOLDERS
                and md_file.parent != vault_root
            ):
                type_name = md_file.parent.name  # preserve original case
                signal_source = f"folder:{type_name}"

        # Signal 3: first tag
        if not type_name:
            fm_tags = meta.get("tags") or meta.get("tag")
            first_tag = None
            if fm_tags:
                tag_list = (
                    fm_tags
                    if isinstance(fm_tags, list)
                    else [t.strip() for t in fm_tags.split(",")]
                )
                if tag_list:
                    first_tag = str(tag_list[0]).strip().lstrip("#")
            if not first_tag:
                clean_body = CODE_BLOCK_RE.sub("", body)
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

        return f"{type_name}|{signal_source}"

    def _detect_vault_root(self) -> Path:
        """Auto-detect vault root directory (same logic as scanner)."""
        entries = list(self.extract_path.iterdir())
        visible = [e for e in entries if not e.name.startswith(".")]

        if len(visible) == 1 and visible[0].is_dir():
            candidate = visible[0]
            if (candidate / ".obsidian").is_dir():
                return candidate
            return candidate

        return self.extract_path
