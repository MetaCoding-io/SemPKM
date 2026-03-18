"""AppRegistry — in-memory manifest cache for installed apps.

Keyed by ``app_id``, this registry is the single source of truth
for which apps are loaded and what their manifests contain.  It is
populated during startup (from DB rows + on-disk manifests) and
updated on install/uninstall.
"""

from __future__ import annotations

import logging

from app.apps.manifest import AppManifestSchema

logger = logging.getLogger(__name__)


class AppRegistry:
    """In-memory cache of validated app manifests, keyed by ``app_id``."""

    def __init__(self) -> None:
        self._apps: dict[str, AppManifestSchema] = {}

    # ── Mutation ──

    def register(self, app_id: str, manifest: AppManifestSchema) -> None:
        """Register (or replace) a manifest for *app_id*."""
        self._apps[app_id] = manifest
        logger.info("Registered app %s (v%s)", app_id, manifest.version)

    def unregister(self, app_id: str) -> None:
        """Remove *app_id* from the registry.  No-op if not present."""
        removed = self._apps.pop(app_id, None)
        if removed:
            logger.info("Unregistered app %s", app_id)

    # ── Queries ──

    def get_manifest(self, app_id: str) -> AppManifestSchema | None:
        """Return the full manifest for *app_id*, or ``None``."""
        return self._apps.get(app_id)

    def list_apps(self) -> list[str]:
        """Return a sorted list of registered ``app_id`` values."""
        return sorted(self._apps.keys())

    def get_app(self, app_id: str) -> dict | None:
        """Return a summary dict ``{id, name, version}`` or ``None``."""
        m = self._apps.get(app_id)
        if m is None:
            return None
        return {"id": app_id, "name": m.name, "version": m.version}

    def get_renderer(self, type_iri: str) -> dict | None:
        """Return renderer info for *type_iri*, or ``None``.

        Iterates all registered app manifests and checks
        ``ui.objectRenderers`` for an entry whose ``type`` matches
        *type_iri* (exact full-IRI comparison).

        Returns ``{app_id, app_name, read_fragment, edit_fragment, label}``
        for the first match found, or ``None``.
        """
        for app_id, manifest in self._apps.items():
            for renderer in manifest.ui.objectRenderers:
                if renderer.type == type_iri:
                    return {
                        "app_id": app_id,
                        "app_name": manifest.name,
                        "read_fragment": renderer.modes.read,
                        "edit_fragment": renderer.modes.edit,
                        "label": manifest.name,
                    }
        return None

    def get_right_pane_contributions(
        self, type_iris: list[str]
    ) -> list[dict]:
        """Return right-pane section descriptors for the given object types.

        Iterates all registered app manifests and collects
        ``ui.contributions.rightPane`` entries whose ``targetTypes``
        match *type_iris* (or use the wildcard ``"*"``).

        Returns a list of dicts sorted by ``priority`` (ascending):
        ``{app_id, app_name, label, icon, fragment, priority}``.
        """
        sections: list[dict] = []
        type_set = set(type_iris)

        for app_id, manifest in self._apps.items():
            for contrib in manifest.ui.contributions.rightPane:
                # Wildcard or explicit type match
                if "*" in contrib.targetTypes or type_set & set(contrib.targetTypes):
                    sections.append({
                        "app_id": app_id,
                        "app_name": manifest.name,
                        "label": contrib.label,
                        "icon": contrib.icon,
                        "fragment": contrib.fragment,
                        "priority": contrib.priority,
                    })

        sections.sort(key=lambda s: s["priority"])
        return sections
