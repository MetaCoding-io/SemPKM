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

        Supports chain strategies with up to 6 path segments:
          /prefix/                         -> MountRootCollection
          /prefix/folder/                  -> StrategyFolderCollection (depth 0)
          /prefix/folder/file.md           -> MountedResourceFile (single or terminal chain)
          /prefix/folder/subfolder/        -> StrategyFolderCollection (depth 1, chain)
          /prefix/folder/subfolder/file.md -> MountedResourceFile (chain terminal)
          /prefix/f1/f2/f3/               -> StrategyFolderCollection (depth 2, chain)
          /prefix/f1/f2/f3/file.md        -> MountedResourceFile (chain terminal)
        """
        from app.vfs.mount_service import SyncMountService
        from app.vfs.mount_collections import (
            MountRootCollection,
            StrategyFolderCollection,
        )

        mount = SyncMountService(self._client).get_mount_by_prefix(parts[0])
        if mount is None:
            return None

        chain = mount.strategy_chain
        is_chain = mount.is_chain

        # /mount-prefix/ -> MountRootCollection
        if len(parts) == 1:
            return MountRootCollection(
                path, environ, self._client, mount,
                event_store=self._event_store,
            )

        remaining = parts[1:]  # strip mount prefix

        # ── Non-chain mounts: preserve existing behavior exactly ──
        if not is_chain:
            if len(remaining) == 1:
                if remaining[0].endswith(".md"):
                    # Flat strategy: /mount-prefix/file.md
                    root = MountRootCollection(
                        f"/{parts[0]}", environ, self._client, mount,
                        event_store=self._event_store,
                    )
                    return root.get_member(remaining[0])
                return StrategyFolderCollection(
                    path, environ, self._client, mount,
                    folder_value=remaining[0],
                    event_store=self._event_store,
                )

            if len(remaining) == 2:
                if remaining[1].endswith(".md"):
                    folder = StrategyFolderCollection(
                        f"/{parts[0]}/{remaining[0]}", environ, self._client, mount,
                        folder_value=remaining[0],
                        event_store=self._event_store,
                    )
                    return folder.get_member(remaining[1])
                # /mount-prefix/year/month/ -> by-date month folder
                return StrategyFolderCollection(
                    path, environ, self._client, mount,
                    folder_value=remaining[1],
                    parent_folder_value=remaining[0],
                    event_store=self._event_store,
                )

            if len(remaining) == 3 and remaining[2].endswith(".md"):
                # /mount-prefix/year/month/file.md -> by-date file
                folder = StrategyFolderCollection(
                    f"/{parts[0]}/{remaining[0]}/{remaining[1]}", environ, self._client, mount,
                    folder_value=remaining[1],
                    parent_folder_value=remaining[0],
                    event_store=self._event_store,
                )
                return folder.get_member(remaining[2])

            return None

        # ── Chain mount dispatch ──
        # Each non-terminal, non-.md segment is a folder at a chain depth.
        # Terminal .md segment is a file at the parent depth.
        logger.debug(
            "Chain dispatch: mount=%s chain=%s remaining=%s",
            mount.path, chain, remaining,
        )

        # Determine if terminal segment is a file
        is_file_request = remaining[-1].endswith(".md")
        folder_segments = remaining[:-1] if is_file_request else remaining
        file_segment = remaining[-1] if is_file_request else None

        # Validate depth doesn't exceed chain length
        max_folder_depth = len(chain)
        if len(folder_segments) > max_folder_depth:
            logger.warning(
                "Chain depth exceeded: %d folders for %d-level chain on mount %s",
                len(folder_segments), len(chain), mount.path,
            )
            return None

        # Build the collection at the appropriate depth
        chain_folder_values = list(folder_segments)
        depth = len(folder_segments)

        if file_segment is not None:
            # File request — build the parent folder collection and get_member
            if depth == 0:
                # File directly under mount root (shouldn't happen for chains, but handle)
                root = MountRootCollection(
                    f"/{parts[0]}", environ, self._client, mount,
                    event_store=self._event_store,
                )
                return root.get_member(file_segment)

            parent_depth = depth - 1
            parent_path = "/" + "/".join(parts[:1] + list(folder_segments))
            logger.debug(
                "Chain file request: depth=%d effective_strategy=%s folder_values=%s",
                parent_depth, chain[parent_depth], chain_folder_values,
            )
            folder = StrategyFolderCollection(
                parent_path, environ, self._client, mount,
                folder_value=folder_segments[-1],
                chain=chain,
                chain_depth=parent_depth,
                chain_folder_values=list(folder_segments[:parent_depth]),
                event_store=self._event_store,
            )
            return folder.get_member(file_segment)
        else:
            # Folder request — return StrategyFolderCollection at this depth
            current_depth = depth - 1  # 0-indexed from the first folder segment
            if current_depth < 0:
                return MountRootCollection(
                    path, environ, self._client, mount,
                    event_store=self._event_store,
                )
            logger.debug(
                "Chain folder request: depth=%d effective_strategy=%s folder_values=%s",
                current_depth, chain[current_depth], chain_folder_values,
            )
            return StrategyFolderCollection(
                path, environ, self._client, mount,
                folder_value=folder_segments[-1],
                chain=chain,
                chain_depth=current_depth,
                chain_folder_values=list(folder_segments[:current_depth]),
                event_store=self._event_store,
            )
