"""Notion workspace import executor.

Two-pass import engine: Pass 1 creates RDF objects from CSV rows with
mapped properties and optional Markdown bodies.  Pass 2 resolves
cross-database relations as edges via title matching.  Broadcasts SSE
progress events throughout execution.
"""

import csv
import json
import logging
import time
from pathlib import Path
from typing import Any

from rdflib import URIRef

from app.auth.models import User
from app.commands.handlers.body_set import handle_body_set
from app.commands.handlers.edge_create import handle_edge_create
from app.commands.handlers.object_create import handle_object_create
from app.commands.schemas import (
    BodySetParams,
    EdgeCreateParams,
    ObjectCreateParams,
)
from app.config import settings
from app.events.store import EventStore
from app.triplestore.client import TriplestoreClient

from .broadcast import ScanBroadcast, SSEEvent
from .models import ImportResult, MappingConfig, NotionScanResult
from .scanner import _strip_notion_id

logger = logging.getLogger(__name__)


class NotionImportExecutor:
    """Two-pass Notion import executor.

    Pass 1: Creates RDF objects from CSV rows with mapped properties
            and optional Markdown body files.
    Pass 2: Resolves cross-database relations as edges by title matching.
    """

    def __init__(
        self,
        scan_result: NotionScanResult,
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
            # title_index: db_name -> {title_lower -> object_iri}
            title_index: dict[str, dict[str, str]] = {}

            # Count total items for progress reporting
            total = 0
            for db in self.scan_result.databases:
                if self.mapping_config.type_mappings.get(db.name) is not None:
                    total += db.row_count
            if self.mapping_config.standalone_page_type_iri:
                total += len(self.scan_result.standalone_pages)

            current = 0

            # ── Pass 1: Create Objects ────────────────────────────
            for db in self.scan_result.databases:
                type_mapping = self.mapping_config.type_mappings.get(db.name)
                if type_mapping is None:
                    continue

                type_iri = type_mapping.target_type_iri
                prop_mappings = self.mapping_config.property_mappings.get(
                    type_iri, {}
                )

                # Read CSV
                csv_path = Path(self.scan_result.extract_path) / db.csv_path
                if not csv_path.exists():
                    logger.warning("CSV not found: %s", csv_path)
                    continue

                # Build body file lookup: stripped_title.lower() -> md Path
                body_lookup: dict[str, Path] = {}
                folder_path = Path(self.scan_result.extract_path) / db.folder_path
                if folder_path.is_dir():
                    for md_file in folder_path.glob("*.md"):
                        stripped = _strip_notion_id(md_file.stem).lower()
                        body_lookup[stripped] = md_file

                title_index[db.name] = {}

                with open(csv_path, encoding="utf-8-sig", newline="") as f:
                    reader = csv.DictReader(f)
                    if not reader.fieldnames:
                        continue
                    title_column = reader.fieldnames[0]

                    for row in reader:
                        current += 1
                        title = row.get(title_column, "").strip()
                        if not title:
                            result.skipped += 1
                            self._broadcast_progress(
                                "objects", current, total, current_file=db.csv_path
                            )
                            continue

                        try:
                            # Build properties from mapped columns
                            properties: dict[str, Any] = {}
                            for col_name, pm in prop_mappings.items():
                                if pm is None:
                                    continue
                                val = row.get(col_name, "").strip()
                                if val:
                                    properties[pm.target_property_iri] = val

                            # Always include import source and title
                            properties["sempkm:importSource"] = db.csv_path
                            properties["dcterms:title"] = title

                            # Create object
                            create_op = await handle_object_create(
                                ObjectCreateParams(
                                    type=type_iri,
                                    slug=None,
                                    properties=properties,
                                ),
                                self._base_namespace,
                            )
                            object_iri = create_op.affected_iris[0]

                            operations = [create_op]

                            # Look up and set body
                            body_file = body_lookup.get(title.lower())
                            if body_file and body_file.exists():
                                body_text = body_file.read_text(encoding="utf-8")
                                if body_text.strip():
                                    body_op = await handle_body_set(
                                        BodySetParams(
                                            iri=object_iri, body=body_text
                                        ),
                                        self._base_namespace,
                                    )
                                    operations.append(body_op)

                            # Commit
                            await self.event_store.commit(
                                operations,
                                performed_by=self._user_iri,
                                performed_by_role=self.user.role,
                            )

                            result.created += 1
                            title_index[db.name][title.lower()] = object_iri

                        except Exception as exc:
                            logger.warning(
                                "Import error for row '%s' in %s: %s",
                                title,
                                db.csv_path,
                                exc,
                                exc_info=True,
                            )
                            result.errors.append((db.csv_path, str(exc)))

                        self._broadcast_progress(
                            "objects", current, total, current_file=db.csv_path
                        )

            # Standalone pages
            if self.mapping_config.standalone_page_type_iri:
                standalone_type_iri = self.mapping_config.standalone_page_type_iri
                title_index["_standalone"] = {}

                for page in self.scan_result.standalone_pages:
                    current += 1
                    try:
                        properties: dict[str, Any] = {
                            "sempkm:importSource": page.file_path,
                            "dcterms:title": page.title,
                        }
                        create_op = await handle_object_create(
                            ObjectCreateParams(
                                type=standalone_type_iri,
                                slug=None,
                                properties=properties,
                            ),
                            self._base_namespace,
                        )
                        object_iri = create_op.affected_iris[0]
                        operations = [create_op]

                        # Read body if file exists
                        page_path = (
                            Path(self.scan_result.extract_path) / page.file_path
                        )
                        if page_path.exists():
                            body_text = page_path.read_text(encoding="utf-8")
                            if body_text.strip():
                                body_op = await handle_body_set(
                                    BodySetParams(
                                        iri=object_iri, body=body_text
                                    ),
                                    self._base_namespace,
                                )
                                operations.append(body_op)

                        await self.event_store.commit(
                            operations,
                            performed_by=self._user_iri,
                            performed_by_role=self.user.role,
                        )
                        result.created += 1
                        title_index["_standalone"][page.title.lower()] = object_iri

                    except Exception as exc:
                        logger.warning(
                            "Import error for standalone page '%s': %s",
                            page.title,
                            exc,
                            exc_info=True,
                        )
                        result.errors.append((page.file_path, str(exc)))

                    self._broadcast_progress(
                        "objects", current, total, current_file=page.file_path
                    )

            # ── Pass 2: Resolve Relations ─────────────────────────
            edge_batch: list[Any] = []
            edge_total = 0
            edge_current = 0

            for db in self.scan_result.databases:
                type_mapping = self.mapping_config.type_mappings.get(db.name)
                if type_mapping is None:
                    continue

                # Gather relation columns for this DB
                db_relations = [
                    r
                    for r in self.scan_result.detected_relations
                    if r.source_db_name == db.name
                ]
                # Filter to only mapped relations
                mapped_relations = []
                for rel in db_relations:
                    relation_key = f"{db.name}|{rel.source_column}"
                    rm = self.mapping_config.relation_mappings.get(relation_key)
                    if rm is not None:
                        mapped_relations.append((rel, rm, relation_key))

                if not mapped_relations:
                    continue

                # Re-read CSV for relation resolution
                csv_path = Path(self.scan_result.extract_path) / db.csv_path
                if not csv_path.exists():
                    continue

                with open(csv_path, encoding="utf-8-sig", newline="") as f:
                    reader = csv.DictReader(f)
                    if not reader.fieldnames:
                        continue
                    title_column = reader.fieldnames[0]

                    for row in reader:
                        title = row.get(title_column, "").strip()
                        if not title:
                            continue

                        source_iri = title_index.get(db.name, {}).get(
                            title.lower()
                        )
                        if source_iri is None:
                            continue

                        for rel, rm, relation_key in mapped_relations:
                            cell_value = row.get(rel.source_column, "").strip()
                            if not cell_value:
                                continue

                            # Split on comma for multi-value relations
                            target_titles = [
                                t.strip() for t in cell_value.split(",") if t.strip()
                            ]

                            for target_title in target_titles:
                                target_iri = title_index.get(
                                    rel.target_db_name, {}
                                ).get(target_title.lower())

                                if target_iri is None:
                                    result.unresolved_relations.append(
                                        (source_iri, relation_key, target_title)
                                    )
                                    continue

                                try:
                                    edge_op = await handle_edge_create(
                                        EdgeCreateParams(
                                            source=source_iri,
                                            target=target_iri,
                                            predicate=rm.target_predicate_iri,
                                            properties={},
                                        ),
                                        self._base_namespace,
                                    )
                                    edge_batch.append(edge_op)
                                    edge_current += 1

                                    # Batch commit every 10 edges
                                    if len(edge_batch) >= 10:
                                        await self.event_store.commit(
                                            edge_batch,
                                            performed_by=self._user_iri,
                                            performed_by_role=self.user.role,
                                        )
                                        result.edges_created += len(edge_batch)
                                        edge_batch = []

                                    self._broadcast_progress(
                                        "edges",
                                        edge_current,
                                        edge_current,  # total not known upfront
                                        current_link=target_title,
                                    )

                                except Exception as exc:
                                    logger.warning(
                                        "Edge creation error %s -> %s: %s",
                                        source_iri,
                                        target_title,
                                        exc,
                                    )

            # Commit remaining edge batch
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

            # ── Persist result and broadcast completion ────────────
            result.duration_seconds = round(time.monotonic() - start, 2)

            result_path = self.import_dir / "import_result.json"
            result_path.write_text(json.dumps(result.to_dict(), indent=2))

            self.broadcast.publish(
                SSEEvent(event="import_complete", data=result.to_dict())
            )

        except Exception as exc:
            logger.error("Import failed: %s", exc, exc_info=True)
            result.duration_seconds = round(time.monotonic() - start, 2)
            self.broadcast.publish(
                SSEEvent(event="import_error", data={"message": str(exc)})
            )

        return result

    # ── Helpers ────────────────────────────────────────────────────

    def _broadcast_progress(
        self,
        phase: str,
        current: int,
        total: int,
        current_file: str | None = None,
        current_link: str | None = None,
    ) -> None:
        """Emit an SSE import_progress event."""
        data: dict[str, Any] = {
            "phase": phase,
            "current": current,
            "total": total,
        }
        if current_file is not None:
            data["current_file"] = current_file
        if current_link is not None:
            data["current_link"] = current_link
        self.broadcast.publish(SSEEvent(event="import_progress", data=data))
