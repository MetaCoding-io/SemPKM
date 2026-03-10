"""WebDAV provider routing requests to collection and resource instances.

SemPKMDAVProvider dispatches path segments to the appropriate DAV resource:
  /                          -> RootCollection  (lists installed models)
  /{model-id}/               -> ModelCollection (lists type labels)
  /{model-id}/{type-label}/  -> TypeCollection  (lists .md files per object)
  /{model-id}/{type-label}/{filename}.md -> ResourceFile (rendered object)

Mount paths are checked first and dispatched to mount collections:
  /mount-prefix/              -> MountRootCollection
  /mount-prefix/folder/       -> StrategyFolderCollection
  /mount-prefix/folder/f.md   -> MountedResourceFile
  /mount-prefix/yr/mo/f.md    -> MountedResourceFile (by-date)

Write path:
  event_store is injected at startup via set_event_store() and passed to each
  ResourceFile so that begin_write/end_write can commit body.set events.
"""

import logging

from wsgidav.dav_provider import DAVProvider

from app.triplestore.sync_client import SyncTriplestoreClient

logger = logging.getLogger(__name__)


class SemPKMDAVProvider(DAVProvider):
    """Routes WebDAV path requests to collection/resource instances."""

    def __init__(self, sync_client: SyncTriplestoreClient) -> None:
        super().__init__()
        self._client = sync_client
        self._event_store = None  # Injected after startup via set_event_store()

    def set_event_store(self, event_store) -> None:
        """Inject the async EventStore instance after app startup.

        Called from the FastAPI lifespan after the event store is created,
        since the DAV provider is constructed at module load time before
        the lifespan runs.
        """
        self._event_store = event_store

    def get_resource_inst(self, path: str, environ: dict):
        """Dispatch path to appropriate DAV resource.

        Mount paths are checked first. If the first path segment matches
        a mount prefix, dispatch to mount collections. Otherwise fall
        through to the existing model/type hierarchy.

        Path structure (mounts):
          /mount-prefix/                   -> MountRootCollection
          /mount-prefix/folder/            -> StrategyFolderCollection
          /mount-prefix/folder/file.md     -> MountedResourceFile
          /mount-prefix/year/month/file.md -> MountedResourceFile (by-date)

        Path structure (models):
          /                          -> RootCollection
          /{model-id}/               -> ModelCollection
          /{model-id}/{type-label}/  -> TypeCollection
          /{model-id}/{type-label}/{filename}.md -> ResourceFile
        """
        from app.vfs.collections import ModelCollection, RootCollection, TypeCollection
        from app.vfs.resources import ResourceFile

        parts = [p for p in path.strip("/").split("/") if p]

        if len(parts) == 0:
            return RootCollection("/", environ, self._client)

        # Check if first segment is a mount prefix
        mount_resource = self._resolve_mount_path(path, parts, environ)
        if mount_resource is not None:
            return mount_resource

        # Fall through to existing model/type hierarchy
        if len(parts) == 1:
            return ModelCollection(path, environ, self._client, model_id=parts[0])
        elif len(parts) == 2:
            return TypeCollection(
                path, environ, self._client, model_id=parts[0], type_label=parts[1]
            )
        elif len(parts) == 3 and parts[2].endswith(".md"):
            return ResourceFile(
                path,
                environ,
                self._client,
                model_id=parts[0],
                type_label=parts[1],
                filename=parts[2],
                event_store=self._event_store,
            )
        return None

    def _resolve_mount_path(self, path: str, parts: list[str], environ: dict):
        """Check if path matches a mount prefix and resolve to DAV resource.

        Returns a DAV resource instance or None if not a mount path.
        """
        from app.vfs.mount_service import SyncMountService
        from app.vfs.mount_collections import (
            MountRootCollection,
            StrategyFolderCollection,
        )

        mount = SyncMountService(self._client).get_mount_by_prefix(parts[0])
        if mount is None:
            return None

        # /mount-prefix/ -> MountRootCollection
        if len(parts) == 1:
            return MountRootCollection(
                path, environ, self._client, mount,
                event_store=self._event_store,
            )

        # /mount-prefix/folder/ -> StrategyFolderCollection
        if len(parts) == 2:
            if parts[1].endswith(".md"):
                # Flat strategy: /mount-prefix/file.md
                root = MountRootCollection(
                    f"/{parts[0]}", environ, self._client, mount,
                    event_store=self._event_store,
                )
                return root.get_member(parts[1])
            return StrategyFolderCollection(
                path, environ, self._client, mount,
                folder_value=parts[1],
                event_store=self._event_store,
            )

        # /mount-prefix/folder/file.md -> MountedResourceFile
        if len(parts) == 3:
            if parts[2].endswith(".md"):
                folder = StrategyFolderCollection(
                    f"/{parts[0]}/{parts[1]}", environ, self._client, mount,
                    folder_value=parts[1],
                    event_store=self._event_store,
                )
                return folder.get_member(parts[2])
            # /mount-prefix/year/month/ -> by-date month folder
            return StrategyFolderCollection(
                path, environ, self._client, mount,
                folder_value=parts[2],
                parent_folder_value=parts[1],
                event_store=self._event_store,
            )

        # /mount-prefix/year/month/file.md -> by-date file
        if len(parts) == 4 and parts[3].endswith(".md"):
            folder = StrategyFolderCollection(
                f"/{parts[0]}/{parts[1]}/{parts[2]}", environ, self._client, mount,
                folder_value=parts[2],
                parent_folder_value=parts[1],
                event_store=self._event_store,
            )
            return folder.get_member(parts[3])

        return None
