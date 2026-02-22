"""Extensible renderer registry for view spec rendering.

Provides a module-level registry of renderer types (table, card, graph)
with support for Mental Model custom renderer registration. Models declare
custom renderers in their views JSONLD using sempkm:customRenderer entries
and register them at installation time via register_renderer().

The ViewSpecService consults this registry when resolving which renderer
template to use for a given view spec. The view toolbar dynamically lists
whatever types are registered.
"""

import logging

logger = logging.getLogger(__name__)

# Built-in renderer types. Each entry maps a renderer type string to a dict
# containing at minimum 'type' and 'template' (Jinja2 template path).
RENDERER_REGISTRY: dict[str, dict] = {
    "table": {
        "type": "table",
        "template": "browser/table_view.html",
    },
    "card": {
        "type": "card",
        "template": "browser/card_view.html",
    },
    "graph": {
        "type": "graph",
        "template": "browser/graph_view.html",
    },
}


def register_renderer(type_str: str, handler: dict) -> None:
    """Register a custom renderer type in the registry.

    Called by ModelService during model installation for any custom
    renderers the model declares (e.g., timeline, kanban, calendar).

    Args:
        type_str: The renderer type identifier (e.g., 'timeline').
        handler: Dict with at minimum 'type' (str) and 'template' (str,
                 the Jinja2 template path for rendering).
    """
    if "type" not in handler or "template" not in handler:
        raise ValueError(
            f"Renderer handler must contain 'type' and 'template' keys, got: {handler}"
        )
    RENDERER_REGISTRY[type_str] = handler
    logger.info("Registered custom renderer: %s -> %s", type_str, handler["template"])


def get_registered_renderers() -> dict[str, dict]:
    """Return the current registry contents (built-in + model-contributed).

    Returns:
        Dict mapping renderer type strings to handler dicts.
    """
    return dict(RENDERER_REGISTRY)
