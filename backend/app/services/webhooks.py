"""Webhook configuration storage and event dispatch service.

Stores webhook configurations as RDF triples in a dedicated named graph
(urn:sempkm:webhooks). Provides CRUD operations for webhook configs and
fire-and-forget HTTP POST dispatch to registered webhook URLs for matching
event types.

Uses httpx.AsyncClient for non-blocking outbound HTTP delivery. Webhook
dispatch failures are logged as warnings but never propagate exceptions
(fire-and-forget semantics per research anti-pattern guidance).
"""

import logging
import uuid
from dataclasses import dataclass, field

import httpx
from rdflib.namespace import XSD

from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

# Dedicated named graph for webhook configuration storage
WEBHOOKS_GRAPH = "urn:sempkm:webhooks"

# SemPKM vocabulary namespace for webhook terms
SEMPKM_NS = "urn:sempkm:"


@dataclass
class WebhookConfig:
    """A webhook configuration entry."""

    id: str
    target_url: str
    events: list[str] = field(default_factory=list)
    filters: list[str] = field(default_factory=list)
    enabled: bool = True


class WebhookService:
    """Manages webhook configurations and dispatches event notifications.

    Webhook configs are stored as RDF triples in urn:sempkm:webhooks.
    Each config is identified by a UUID-based IRI:

        <urn:sempkm:webhook:{uuid}> a sempkm:Webhook ;
            sempkm:targetUrl "https://example.com/hook" ;
            sempkm:event "object.changed" ;
            sempkm:event "edge.changed" ;
            sempkm:filter "bpkm:Person" ;
            sempkm:enabled "true"^^xsd:boolean .
    """

    def __init__(self, client: TriplestoreClient) -> None:
        self._client = client

    async def create_config(
        self,
        target_url: str,
        events: list[str],
        filters: list[str] | None = None,
    ) -> WebhookConfig:
        """Create a new webhook configuration.

        Generates a UUID, stores the config as RDF triples in the
        webhooks graph, and returns the created WebhookConfig.

        Args:
            target_url: The URL to POST webhook payloads to.
            events: List of event types to subscribe to.
            filters: Optional type/namespace filters.

        Returns:
            The created WebhookConfig with generated ID.
        """
        webhook_id = str(uuid.uuid4())
        webhook_iri = f"urn:sempkm:webhook:{webhook_id}"
        actual_filters = filters or []

        # Build triples
        triple_lines = [
            f'    <{webhook_iri}> a <{SEMPKM_NS}Webhook> .',
            f'    <{webhook_iri}> <{SEMPKM_NS}targetUrl> "{_escape_sparql(target_url)}" .',
            f'    <{webhook_iri}> <{SEMPKM_NS}enabled> "true"^^<{XSD.boolean}> .',
        ]

        for event in events:
            triple_lines.append(
                f'    <{webhook_iri}> <{SEMPKM_NS}event> "{_escape_sparql(event)}" .'
            )

        for f in actual_filters:
            triple_lines.append(
                f'    <{webhook_iri}> <{SEMPKM_NS}filter> "{_escape_sparql(f)}" .'
            )

        triples_str = "\n".join(triple_lines)
        sparql = f"""INSERT DATA {{
  GRAPH <{WEBHOOKS_GRAPH}> {{
{triples_str}
  }}
}}"""
        await self._client.update(sparql)

        logger.info("Created webhook %s -> %s for events %s", webhook_id, target_url, events)
        return WebhookConfig(
            id=webhook_id,
            target_url=target_url,
            events=events,
            filters=actual_filters,
            enabled=True,
        )

    async def list_configs(self) -> list[WebhookConfig]:
        """Query all webhook configurations from the webhooks graph.

        Returns:
            List of WebhookConfig dataclasses.
        """
        sparql = f"""SELECT ?webhook ?targetUrl ?enabled WHERE {{
  GRAPH <{WEBHOOKS_GRAPH}> {{
    ?webhook a <{SEMPKM_NS}Webhook> ;
             <{SEMPKM_NS}targetUrl> ?targetUrl ;
             <{SEMPKM_NS}enabled> ?enabled .
  }}
}}"""
        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])

        configs: list[WebhookConfig] = []
        for b in bindings:
            webhook_iri = b["webhook"]["value"]
            webhook_id = webhook_iri.replace("urn:sempkm:webhook:", "")
            target_url = b["targetUrl"]["value"]
            enabled = b["enabled"]["value"].lower() == "true"

            # Fetch events and filters for this webhook
            events = await self._get_webhook_values(webhook_iri, "event")
            filters = await self._get_webhook_values(webhook_iri, "filter")

            configs.append(
                WebhookConfig(
                    id=webhook_id,
                    target_url=target_url,
                    events=events,
                    filters=filters,
                    enabled=enabled,
                )
            )

        return configs

    async def get_config(self, webhook_id: str) -> WebhookConfig | None:
        """Get a specific webhook configuration by ID.

        Args:
            webhook_id: The webhook UUID.

        Returns:
            WebhookConfig if found, None otherwise.
        """
        webhook_iri = f"urn:sempkm:webhook:{webhook_id}"
        sparql = f"""SELECT ?targetUrl ?enabled WHERE {{
  GRAPH <{WEBHOOKS_GRAPH}> {{
    <{webhook_iri}> a <{SEMPKM_NS}Webhook> ;
                    <{SEMPKM_NS}targetUrl> ?targetUrl ;
                    <{SEMPKM_NS}enabled> ?enabled .
  }}
}}"""
        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        if not bindings:
            return None

        b = bindings[0]
        target_url = b["targetUrl"]["value"]
        enabled = b["enabled"]["value"].lower() == "true"

        events = await self._get_webhook_values(webhook_iri, "event")
        filters = await self._get_webhook_values(webhook_iri, "filter")

        return WebhookConfig(
            id=webhook_id,
            target_url=target_url,
            events=events,
            filters=filters,
            enabled=enabled,
        )

    async def update_config(
        self,
        webhook_id: str,
        target_url: str | None = None,
        events: list[str] | None = None,
        filters: list[str] | None = None,
        enabled: bool | None = None,
    ) -> WebhookConfig:
        """Update specific fields of a webhook configuration.

        Uses DELETE/INSERT pattern for atomic update. Only specified
        (non-None) fields are updated.

        Args:
            webhook_id: The webhook UUID.
            target_url: New target URL (or None to keep existing).
            events: New events list (or None to keep existing).
            filters: New filters list (or None to keep existing).
            enabled: New enabled state (or None to keep existing).

        Returns:
            The updated WebhookConfig.

        Raises:
            ValueError: If the webhook is not found.
        """
        webhook_iri = f"urn:sempkm:webhook:{webhook_id}"

        # Get current config
        current = await self.get_config(webhook_id)
        if current is None:
            raise ValueError(f"Webhook '{webhook_id}' not found")

        # Apply updates
        new_target_url = target_url if target_url is not None else current.target_url
        new_events = events if events is not None else current.events
        new_filters = filters if filters is not None else current.filters
        new_enabled = enabled if enabled is not None else current.enabled

        # Delete all triples for this webhook and re-insert
        delete_sparql = f"""DELETE WHERE {{
  GRAPH <{WEBHOOKS_GRAPH}> {{
    <{webhook_iri}> ?p ?o .
  }}
}}"""
        await self._client.update(delete_sparql)

        # Re-insert with updated values
        enabled_str = "true" if new_enabled else "false"
        triple_lines = [
            f'    <{webhook_iri}> a <{SEMPKM_NS}Webhook> .',
            f'    <{webhook_iri}> <{SEMPKM_NS}targetUrl> "{_escape_sparql(new_target_url)}" .',
            f'    <{webhook_iri}> <{SEMPKM_NS}enabled> "{enabled_str}"^^<{XSD.boolean}> .',
        ]

        for event in new_events:
            triple_lines.append(
                f'    <{webhook_iri}> <{SEMPKM_NS}event> "{_escape_sparql(event)}" .'
            )

        for f in new_filters:
            triple_lines.append(
                f'    <{webhook_iri}> <{SEMPKM_NS}filter> "{_escape_sparql(f)}" .'
            )

        triples_str = "\n".join(triple_lines)
        insert_sparql = f"""INSERT DATA {{
  GRAPH <{WEBHOOKS_GRAPH}> {{
{triples_str}
  }}
}}"""
        await self._client.update(insert_sparql)

        logger.info("Updated webhook %s", webhook_id)
        return WebhookConfig(
            id=webhook_id,
            target_url=new_target_url,
            events=new_events,
            filters=new_filters,
            enabled=new_enabled,
        )

    async def delete_config(self, webhook_id: str) -> bool:
        """Remove a webhook configuration from the graph.

        Args:
            webhook_id: The webhook UUID to delete.

        Returns:
            True if the webhook existed and was deleted, False if not found.
        """
        webhook_iri = f"urn:sempkm:webhook:{webhook_id}"

        # Check if it exists first
        existing = await self.get_config(webhook_id)
        if existing is None:
            return False

        sparql = f"""DELETE WHERE {{
  GRAPH <{WEBHOOKS_GRAPH}> {{
    <{webhook_iri}> ?p ?o .
  }}
}}"""
        await self._client.update(sparql)
        logger.info("Deleted webhook %s", webhook_id)
        return True

    async def dispatch(self, event_type: str, payload: dict) -> None:
        """Fire outbound webhooks for matching event subscriptions.

        Queries all enabled webhook configs, filters by event_type match,
        and sends HTTP POST to each matching webhook's target URL.

        Uses httpx.AsyncClient with a 5-second timeout. Failures are
        logged as warnings (fire-and-forget, never raises).

        Args:
            event_type: The event type (e.g., "object.changed").
            payload: The JSON payload to send.
        """
        try:
            configs = await self.list_configs()
        except Exception:
            logger.warning("Failed to fetch webhook configs for dispatch", exc_info=True)
            return

        matching = [
            c for c in configs
            if c.enabled and event_type in c.events
        ]

        if not matching:
            return

        async with httpx.AsyncClient(timeout=5.0) as http_client:
            for config in matching:
                try:
                    resp = await http_client.post(
                        config.target_url,
                        json={
                            "event_type": event_type,
                            **payload,
                        },
                    )
                    logger.debug(
                        "Webhook %s dispatched to %s: status %d",
                        config.id,
                        config.target_url,
                        resp.status_code,
                    )
                except Exception:
                    logger.warning(
                        "Webhook dispatch failed for %s -> %s",
                        config.id,
                        config.target_url,
                        exc_info=True,
                    )

    async def _get_webhook_values(
        self, webhook_iri: str, predicate: str
    ) -> list[str]:
        """Query multi-valued predicates for a webhook config.

        Used to fetch the list of events and filters for a webhook.

        Args:
            webhook_iri: The webhook IRI.
            predicate: The predicate local name (e.g., "event", "filter").

        Returns:
            List of string values.
        """
        sparql = f"""SELECT ?value WHERE {{
  GRAPH <{WEBHOOKS_GRAPH}> {{
    <{webhook_iri}> <{SEMPKM_NS}{predicate}> ?value .
  }}
}}"""
        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        return [b["value"]["value"] for b in bindings]


def _escape_sparql(value: str) -> str:
    """Escape a string for use in a SPARQL literal."""
    return (
        value
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
