"""WebDAV provider routing requests to collection and resource instances.

SemPKMDAVProvider dispatches path segments to the appropriate DAV resource:
  /                          -> RootCollection  (lists installed models)
  /{model-id}/               -> ModelCollection (lists type labels)
  /{model-id}/{type-label}/  -> TypeCollection  (lists .md files per object)
  /{model-id}/{type-label}/{filename}.md -> ResourceFile (rendered object)
"""

from wsgidav.dav_provider import DAVProvider

from app.triplestore.sync_client import SyncTriplestoreClient


class SemPKMDAVProvider(DAVProvider):
    """Routes WebDAV path requests to collection/resource instances."""

    def __init__(self, sync_client: SyncTriplestoreClient) -> None:
        super().__init__()
        self._client = sync_client

    def get_resource_inst(self, path: str, environ: dict):
        """Dispatch path to appropriate DAV resource.

        Path structure:
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
        elif len(parts) == 1:
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
            )
        return None
