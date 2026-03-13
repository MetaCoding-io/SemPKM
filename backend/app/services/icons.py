"""IconService: loads icon/color maps from installed model manifests.

Reads the `icons` field from each installed model's manifest.yaml and
builds a flat dict keyed by full type IRI (with prefix expansion).
Provides per-context (tree, graph, tab) icon and color lookups.

Also supports user-type icons loaded from the triplestore via SPARQL
(urn:sempkm:user-types graph, sempkm:typeIcon / sempkm:typeColor predicates).
"""

import logging
import os
from dataclasses import dataclass
from typing import Any

import yaml

from ..models.manifest import ManifestSchema

logger = logging.getLogger(__name__)

FALLBACK_ICON = "circle"
FALLBACK_COLOR = "var(--color-text-faint)"


@dataclass
class IconContextDef:
    icon: str
    color: str
    size: int | None = None


@dataclass
class TypeIconMap:
    """Resolved icon definitions for a single type, per context."""

    tree: IconContextDef
    graph: IconContextDef
    tab: IconContextDef


FALLBACK_CONTEXT = IconContextDef(icon=FALLBACK_ICON, color=FALLBACK_COLOR)


class IconService:
    def __init__(self, models_dir: str | None = None):
        self._models_dir = models_dir
        self._cache: dict[str, TypeIconMap] | None = None

    def _expand_prefix(self, type_ref: str, prefixes: dict[str, str]) -> str:
        """Expand 'prefix:LocalName' to full IRI using manifest prefixes dict."""
        if ":" not in type_ref or type_ref.startswith("http") or type_ref.startswith("urn"):
            return type_ref
        prefix, local = type_ref.split(":", 1)
        base = prefixes.get(prefix, "")
        return base + local if base else type_ref

    def _build_cache(self) -> dict[str, TypeIconMap]:
        result: dict[str, TypeIconMap] = {}
        if not self._models_dir:
            return result
        try:
            model_ids = os.listdir(self._models_dir)
        except OSError:
            return result

        for model_id in model_ids:
            manifest_path = os.path.join(self._models_dir, model_id, "manifest.yaml")
            if not os.path.exists(manifest_path):
                continue
            try:
                with open(manifest_path) as f:
                    raw = yaml.safe_load(f)
                manifest = ManifestSchema.model_validate(raw)
                prefixes = dict(manifest.prefixes or {})
                for icon_def in manifest.icons or []:
                    full_iri = self._expand_prefix(icon_def.type, prefixes)

                    def resolve_ctx(
                        ctx_def: Any,
                        top_icon: str | None,
                        top_color: str | None,
                        default_size: int | None,
                    ) -> IconContextDef:
                        if ctx_def is not None:
                            return IconContextDef(
                                icon=ctx_def.icon or top_icon or FALLBACK_ICON,
                                color=ctx_def.color or top_color or FALLBACK_COLOR,
                                size=ctx_def.size or default_size,
                            )
                        if top_icon:
                            return IconContextDef(
                                icon=top_icon,
                                color=top_color or FALLBACK_COLOR,
                                size=default_size,
                            )
                        return IconContextDef(
                            icon=FALLBACK_ICON,
                            color=FALLBACK_COLOR,
                            size=default_size,
                        )

                    result[full_iri] = TypeIconMap(
                        tree=resolve_ctx(icon_def.tree, icon_def.icon, icon_def.color, 16),
                        graph=resolve_ctx(icon_def.graph, icon_def.icon, icon_def.color, None),
                        tab=resolve_ctx(icon_def.tab, icon_def.icon, icon_def.color, 14),
                    )
            except Exception:
                continue
        return result

    def _get_cache(self) -> dict[str, TypeIconMap]:
        if self._cache is None:
            self._cache = self._build_cache()
        return self._cache

    def invalidate(self) -> None:
        """Call when a model is installed or uninstalled."""
        self._cache = None

    def get_icon_map(self, context: str = "tree") -> dict[str, dict]:
        """Return {type_iri: {icon, color, size}} for the given context.

        Merges manifest-based icons with user-type icon overrides.
        User-type icons are added with size=None (no per-context sizes).
        """
        cache = self._get_cache()
        result: dict[str, dict] = {}
        for type_iri, type_map in cache.items():
            ctx = getattr(type_map, context, FALLBACK_CONTEXT)
            result[type_iri] = {
                "icon": ctx.icon,
                "color": ctx.color,
                "size": ctx.size,
            }

        # Merge user-type icons (lower priority — don't override manifest icons)
        user_icons = getattr(self, "_user_type_icons", None)
        if user_icons:
            for type_iri, entry in user_icons.items():
                if type_iri not in result:
                    result[type_iri] = {
                        "icon": entry.get("icon", FALLBACK_ICON),
                        "color": entry.get("color", FALLBACK_COLOR),
                        "size": None,
                    }

        return result

    def set_user_type_icons(self, icons: dict[str, dict]) -> None:
        """Set user-type icon overrides from an external source.

        Args:
            icons: Dict mapping class IRI to {"icon": str, "color": str}.
                   Typically populated from app.state.user_type_icons by the
                   caller (router or dependency).
        """
        self._user_type_icons = icons

    def get_type_icon(self, type_iri: str, context: str = "tree") -> dict:
        """Return icon dict for a single type IRI, or fallback if not found.

        Checks manifest-based cache first, then user-type icon overrides.
        """
        m = self._get_cache().get(type_iri)
        if m:
            ctx = getattr(m, context, FALLBACK_CONTEXT)
            return {"icon": ctx.icon, "color": ctx.color, "size": ctx.size}

        # Check user-type icons (from triplestore, set via set_user_type_icons)
        user_icons = getattr(self, "_user_type_icons", None)
        if user_icons and type_iri in user_icons:
            entry = user_icons[type_iri]
            return {
                "icon": entry.get("icon", FALLBACK_ICON),
                "color": entry.get("color", FALLBACK_COLOR),
                "size": None,
            }

        return {"icon": FALLBACK_ICON, "color": FALLBACK_COLOR, "size": None}


# ------------------------------------------------------------------
# Async loader for user-type icons from triplestore
# ------------------------------------------------------------------

USER_TYPES_GRAPH = "urn:sempkm:user-types"
SEMPKM_NS = "urn:sempkm:"


async def load_user_type_icons(client: Any) -> dict[str, dict]:
    """Load user-type icon metadata from the triplestore.

    Queries the urn:sempkm:user-types graph for classes that have
    sempkm:typeIcon and/or sempkm:typeColor predicates.

    Args:
        client: TriplestoreClient (async) with a .query() method.

    Returns:
        Dict mapping class IRI to {"icon": str, "color": str}.
    """
    sparql = f"""SELECT ?class ?icon ?color WHERE {{
  GRAPH <{USER_TYPES_GRAPH}> {{
    ?class a <http://www.w3.org/2002/07/owl#Class> .
    OPTIONAL {{ ?class <{SEMPKM_NS}typeIcon> ?icon . }}
    OPTIONAL {{ ?class <{SEMPKM_NS}typeColor> ?color . }}
  }}
  FILTER(BOUND(?icon) || BOUND(?color))
}}"""

    try:
        result = await client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception:
        logger.warning("Failed to load user-type icons from triplestore", exc_info=True)
        return {}

    icons: dict[str, dict] = {}
    for b in bindings:
        class_iri = b["class"]["value"]
        icon_name = b.get("icon", {}).get("value", FALLBACK_ICON)
        icon_color = b.get("color", {}).get("value", FALLBACK_COLOR)
        icons[class_iri] = {"icon": icon_name, "color": icon_color}

    logger.info("Loaded %d user-type icons from triplestore", len(icons))
    return icons
