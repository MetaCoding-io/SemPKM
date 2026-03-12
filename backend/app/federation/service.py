"""Federation service: shared graph management, sync, notifications.

Orchestrates all federation logic including shared graph CRUD, invitation
flow, sync pull/apply with syncSource loop prevention, notification sending,
contact management, and outbound sync-alert notifications.

Shared graph metadata is stored as RDF triples in the urn:sempkm:federation
metadata graph. All writes go through EventStore to maintain the event
sourcing invariant.
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from rdflib import Literal, URIRef
from rdflib.namespace import RDF, XSD

from app.events.store import EventStore, Operation
from app.federation.patch import deserialize_patch
from app.federation.schemas import (
    ContactInfo,
    SharedGraphResponse,
    SyncResult,
)
from app.federation.signatures import sign_request
from app.federation.webfinger import discover_webid
from app.rdf.namespaces import AS, DCTERMS, SEMPKM
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

# Federation metadata graph for shared graph membership, contacts, etc.
FEDERATION_GRAPH = "urn:sempkm:federation"


class FederationService:
    """Orchestrates federation operations for shared graphs and notifications.

    Initialized with a TriplestoreClient for SPARQL queries and an EventStore
    for writes that must go through the event sourcing pipeline.
    """

    def __init__(self, client: TriplestoreClient, event_store: EventStore) -> None:
        self._client = client
        self._event_store = event_store

    # ------------------------------------------------------------------
    # Shared graph management
    # ------------------------------------------------------------------

    async def create_shared_graph(
        self,
        name: str,
        description: str,
        required_model: str,
        creator_webid: str,
    ) -> str:
        """Create a new shared graph and store its metadata.

        Args:
            name: Human-readable name for the shared graph.
            description: Optional description.
            required_model: Model ID required for participation.
            creator_webid: WebID of the creating user (added as first member).

        Returns:
            The minted shared graph IRI (urn:sempkm:shared:{uuid}).
        """
        graph_iri = f"urn:sempkm:shared:{uuid4()}"
        now = datetime.now(timezone.utc).isoformat()

        graph_ref = URIRef(graph_iri)
        fed_graph = URIRef(FEDERATION_GRAPH)

        # Build metadata triples for the federation graph
        triples = [
            (graph_ref, RDF.type, SEMPKM.SharedGraph),
            (graph_ref, DCTERMS.title, Literal(name)),
            (graph_ref, DCTERMS.description, Literal(description)),
            (graph_ref, SEMPKM.requiredModel, Literal(required_model)),
            (graph_ref, DCTERMS.created, Literal(now, datatype=XSD.dateTime)),
            (graph_ref, SEMPKM.member, URIRef(creator_webid)),
        ]

        # Store metadata directly in the federation graph via SPARQL INSERT
        triple_lines = []
        for s, p, o in triples:
            triple_lines.append(
                f"  <{s}> <{p}> {_sparql_term(o)} ."
            )

        sparql = f"""
        INSERT DATA {{
          GRAPH <{FEDERATION_GRAPH}> {{
            {chr(10).join(triple_lines)}
          }}
        }}
        """
        await self._client.update(sparql)

        logger.info("Created shared graph %s by %s", graph_iri, creator_webid)
        return graph_iri

    async def list_shared_graphs(self, user_webid: str) -> list[SharedGraphResponse]:
        """List shared graphs where the user is a member.

        Args:
            user_webid: The user's WebID URI.

        Returns:
            List of SharedGraphResponse with metadata and pending counts.
        """
        sparql = f"""
        SELECT ?graph ?title ?description ?created
               (GROUP_CONCAT(DISTINCT STR(?member); separator=",") AS ?members)
        WHERE {{
          GRAPH <{FEDERATION_GRAPH}> {{
            ?graph a <{SEMPKM.SharedGraph}> ;
                   <{DCTERMS.title}> ?title ;
                   <{DCTERMS.created}> ?created ;
                   <{SEMPKM.member}> <{user_webid}> .
            OPTIONAL {{ ?graph <{DCTERMS.description}> ?description }}
            ?graph <{SEMPKM.member}> ?member .
          }}
        }}
        GROUP BY ?graph ?title ?description ?created
        """

        results = await self._client.query(sparql)
        bindings = results.get("results", {}).get("bindings", [])

        graphs = []
        for row in bindings:
            graph_iri = row.get("graph", {}).get("value", "")
            members_str = row.get("members", {}).get("value", "")
            members = [m for m in members_str.split(",") if m] if members_str else []

            # Get last sync time
            last_sync = await self._get_last_sync(graph_iri)

            # Get pending event count (events targeting this graph not yet synced)
            pending = await self._get_pending_count(graph_iri)

            graphs.append(SharedGraphResponse(
                graph_iri=graph_iri,
                name=row.get("title", {}).get("value", ""),
                description=row.get("description", {}).get("value", ""),
                created=row.get("created", {}).get("value", ""),
                members=members,
                last_sync=last_sync,
                pending_count=pending,
            ))

        return graphs

    async def get_shared_graph(self, graph_iri: str) -> SharedGraphResponse | None:
        """Get details for a single shared graph.

        Args:
            graph_iri: The shared graph IRI.

        Returns:
            SharedGraphResponse or None if not found.
        """
        sparql = f"""
        SELECT ?title ?description ?created
               (GROUP_CONCAT(DISTINCT STR(?member); separator=",") AS ?members)
        WHERE {{
          GRAPH <{FEDERATION_GRAPH}> {{
            <{graph_iri}> a <{SEMPKM.SharedGraph}> ;
                          <{DCTERMS.title}> ?title ;
                          <{DCTERMS.created}> ?created .
            OPTIONAL {{ <{graph_iri}> <{DCTERMS.description}> ?description }}
            <{graph_iri}> <{SEMPKM.member}> ?member .
          }}
        }}
        GROUP BY ?title ?description ?created
        """

        results = await self._client.query(sparql)
        bindings = results.get("results", {}).get("bindings", [])

        if not bindings:
            return None

        row = bindings[0]
        members_str = row.get("members", {}).get("value", "")
        members = [m for m in members_str.split(",") if m] if members_str else []

        last_sync = await self._get_last_sync(graph_iri)
        pending = await self._get_pending_count(graph_iri)

        return SharedGraphResponse(
            graph_iri=graph_iri,
            name=row.get("title", {}).get("value", ""),
            description=row.get("description", {}).get("value", ""),
            created=row.get("created", {}).get("value", ""),
            members=members,
            last_sync=last_sync,
            pending_count=pending,
        )

    async def leave_shared_graph(self, graph_iri: str, user_webid: str) -> None:
        """Remove user membership from a shared graph.

        Data stays as a frozen snapshot per CONTEXT.md decision.

        Args:
            graph_iri: The shared graph IRI.
            user_webid: The user's WebID to remove.
        """
        sparql = f"""
        DELETE DATA {{
          GRAPH <{FEDERATION_GRAPH}> {{
            <{graph_iri}> <{SEMPKM.member}> <{user_webid}> .
          }}
        }}
        """
        await self._client.update(sparql)
        logger.info("User %s left shared graph %s", user_webid, graph_iri)

    # ------------------------------------------------------------------
    # Object copying to shared graph
    # ------------------------------------------------------------------

    async def copy_to_shared_graph(
        self,
        object_iri: str,
        shared_graph_iri: str,
        performed_by: URIRef,
        performed_by_role: str,
    ) -> None:
        """Copy an object's triples from current graph into a shared graph.

        Queries all triples for the object from CURRENT_GRAPH, creates an
        Operation with those triples as materialize_inserts, and commits
        via EventStore with target_graph set to the shared graph. After
        commit, sends LDN sync-alert notifications to remote members.

        Args:
            object_iri: The IRI of the object to copy.
            shared_graph_iri: The target shared graph IRI.
            performed_by: User IRI performing the copy.
            performed_by_role: User's role string.
        """
        # Query all triples for the object from current graph
        sparql = f"""
        SELECT ?p ?o WHERE {{
          GRAPH <urn:sempkm:current> {{
            <{object_iri}> ?p ?o .
          }}
        }}
        """
        results = await self._client.query(sparql)
        bindings = results.get("results", {}).get("bindings", [])

        if not bindings:
            logger.warning("No triples found for %s in current graph", object_iri)
            return

        # Build insert triples
        subject = URIRef(object_iri)
        inserts = []
        for row in bindings:
            p = _binding_to_term(row["p"])
            o = _binding_to_term(row["o"])
            inserts.append((subject, p, o))

        op = Operation(
            operation_type="federation.copy",
            affected_iris=[object_iri],
            description=f"Copy {object_iri} to shared graph {shared_graph_iri}",
            data_triples=[],
            materialize_inserts=inserts,
            materialize_deletes=[],
        )

        await self._event_store.commit(
            [op],
            performed_by=performed_by,
            performed_by_role=performed_by_role,
            target_graph=shared_graph_iri,
        )

        # Fire-and-forget: notify remote members of the change
        try:
            await self.notify_remote_members_of_change(
                shared_graph_iri,
                str(performed_by),
                event_count=1,
            )
        except Exception as e:
            logger.warning(
                "Failed to notify remote members after copy to %s: %s",
                shared_graph_iri, e,
            )

    # ------------------------------------------------------------------
    # Outbound sync-alert notifications
    # ------------------------------------------------------------------

    async def notify_remote_members_of_change(
        self,
        shared_graph_iri: str,
        local_webid: str,
        event_count: int = 1,
        private_key_pem: str | None = None,
        key_id: str | None = None,
    ) -> None:
        """Send LDN sync-alert Update notifications to all remote members.

        Queries remote members of the shared graph (excluding local_webid),
        discovers their inbox URLs, and POSTs an ActivityStreams Update
        notification signed with the local instance's key.

        This is fire-and-forget: errors are logged but do not propagate.

        Args:
            shared_graph_iri: The shared graph that was modified.
            local_webid: The local user's WebID (excluded from notifications).
            event_count: Number of events/changes to report.
            private_key_pem: PEM key for signing (optional, skips if absent).
            key_id: Key ID for signing (optional).
        """
        # Get graph name for the notification summary
        graph_name = await self._get_graph_name(shared_graph_iri)

        # Query remote members (exclude local)
        sparql = f"""
        SELECT DISTINCT ?member WHERE {{
          GRAPH <{FEDERATION_GRAPH}> {{
            <{shared_graph_iri}> <{SEMPKM.member}> ?member .
          }}
          FILTER(?member != <{local_webid}>)
        }}
        """
        results = await self._client.query(sparql)
        bindings = results.get("results", {}).get("bindings", [])

        for row in bindings:
            member_webid = row.get("member", {}).get("value", "")
            if not member_webid:
                continue

            try:
                # Discover member's inbox
                discovery = await discover_webid(member_webid)
                inbox_url = discovery.get("inbox")
                if not inbox_url:
                    # Try fetching inbox from WebID profile directly
                    inbox_url = await self._discover_inbox_from_profile(member_webid)

                if not inbox_url:
                    logger.warning(
                        "No inbox found for remote member %s", member_webid
                    )
                    continue

                # Build sync-alert notification
                notification = {
                    "@context": "https://www.w3.org/ns/activitystreams",
                    "type": "Update",
                    "actor": local_webid,
                    "object": {
                        "type": "Collection",
                        "id": shared_graph_iri,
                        "name": graph_name,
                    },
                    "summary": f"{event_count} new change(s) in '{graph_name}'",
                    "sempkm:patchCount": event_count,
                    "sempkm:graphTarget": shared_graph_iri,
                }

                await self._post_to_inbox(
                    inbox_url, notification, private_key_pem, key_id
                )
                logger.info(
                    "Sent sync alert to %s for graph %s",
                    member_webid, shared_graph_iri,
                )

            except Exception as e:
                logger.warning(
                    "Failed to send sync alert to %s: %s", member_webid, e
                )

    # ------------------------------------------------------------------
    # Invitation flow
    # ------------------------------------------------------------------

    async def send_invitation(
        self,
        graph_iri: str,
        recipient_handle: str,
        sender_webid: str,
        sender_private_key: str | None = None,
        sender_key_id: str | None = None,
    ) -> None:
        """Send a shared graph invitation to a remote user.

        Discovers the recipient via WebFinger, builds an ActivityStreams
        Offer notification, signs it, and POSTs to the recipient's inbox.

        Args:
            graph_iri: The shared graph to invite the recipient to.
            recipient_handle: WebID URL or user@domain handle.
            sender_webid: The sender's WebID URI.
            sender_private_key: PEM-encoded private key for signing.
            sender_key_id: Key ID for the signature.
        """
        # Discover recipient
        discovery = await discover_webid(recipient_handle)
        recipient_webid = discovery.get("webid", recipient_handle)
        inbox_url = discovery.get("inbox")

        if not inbox_url:
            inbox_url = await self._discover_inbox_from_profile(recipient_webid)

        if not inbox_url:
            raise ValueError(f"Cannot discover inbox for {recipient_handle}")

        # Get graph metadata
        graph_name = await self._get_graph_name(graph_iri)
        required_model = await self._get_required_model(graph_iri)

        # Build Offer notification per RESEARCH.md pattern
        invitation = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Offer",
            "actor": sender_webid,
            "object": {
                "type": "Collection",
                "id": graph_iri,
                "name": graph_name,
                "sempkm:requiredModel": required_model,
            },
            "target": recipient_webid,
            "summary": f"Invitation to join shared graph '{graph_name}'",
        }

        await self._post_to_inbox(
            inbox_url, invitation, sender_private_key, sender_key_id
        )
        logger.info(
            "Sent invitation for %s to %s", graph_iri, recipient_handle
        )

    async def accept_invitation(
        self,
        notification_graph_iri: str,
        user_webid: str,
    ) -> None:
        """Accept a shared graph invitation.

        Reads the invitation from the notification graph, creates the
        shared graph locally with the same IRI, stores the sender as
        a known contact, and updates notification state to "acted".

        Args:
            notification_graph_iri: The notification named graph IRI.
            user_webid: The accepting user's WebID.
        """
        # Read invitation details from the notification graph
        sparql = f"""
        SELECT ?actor ?objectId ?objectName ?requiredModel WHERE {{
          GRAPH <{notification_graph_iri}> {{
            ?notif a <{AS}Offer> ;
                   <{AS}actor> ?actor .
            OPTIONAL {{ ?notif <{AS}object> ?objectId }}
            OPTIONAL {{
              ?objectId <{AS}name> ?objectName .
            }}
            OPTIONAL {{
              ?objectId <{SEMPKM}requiredModel> ?requiredModel .
            }}
          }}
        }}
        """
        results = await self._client.query(sparql)
        bindings = results.get("results", {}).get("bindings", [])

        if not bindings:
            raise ValueError(
                f"No Offer notification found in {notification_graph_iri}"
            )

        row = bindings[0]
        sender_webid = row.get("actor", {}).get("value", "")
        shared_graph_iri = row.get("objectId", {}).get("value", "")
        graph_name = row.get("objectName", {}).get("value", "Shared Graph")
        required_model = row.get("requiredModel", {}).get("value", "")

        if not shared_graph_iri:
            raise ValueError("Invitation missing shared graph IRI")

        # Create local shared graph with the same IRI
        now = datetime.now(timezone.utc).isoformat()
        graph_ref = URIRef(shared_graph_iri)

        triples_sparql = f"""
        INSERT DATA {{
          GRAPH <{FEDERATION_GRAPH}> {{
            <{shared_graph_iri}> a <{SEMPKM.SharedGraph}> ;
              <{DCTERMS.title}> "{_escape_sparql(graph_name)}" ;
              <{DCTERMS.description}> "" ;
              <{SEMPKM.requiredModel}> "{_escape_sparql(required_model)}" ;
              <{DCTERMS.created}> "{now}"^^<{XSD.dateTime}> ;
              <{SEMPKM.member}> <{user_webid}> ;
              <{SEMPKM.member}> <{sender_webid}> .
          }}
        }}
        """
        await self._client.update(triples_sparql)

        # Store sender as known contact
        await self._store_contact(sender_webid)

        # Update notification state to "acted"
        notif_id = notification_graph_iri.replace("urn:sempkm:inbox:", "")
        state_sparql = f"""
        DELETE {{
          GRAPH <{notification_graph_iri}> {{
            ?notif <{SEMPKM}notificationState> ?oldState .
          }}
        }}
        INSERT {{
          GRAPH <{notification_graph_iri}> {{
            ?notif <{SEMPKM}notificationState> "acted" .
          }}
        }}
        WHERE {{
          GRAPH <{notification_graph_iri}> {{
            ?notif <{SEMPKM}notificationState> ?oldState .
          }}
        }}
        """
        await self._client.update(state_sparql)

        logger.info(
            "Accepted invitation for %s from %s",
            shared_graph_iri, sender_webid,
        )

    # ------------------------------------------------------------------
    # Sync flow
    # ------------------------------------------------------------------

    async def sync_shared_graph(
        self,
        graph_iri: str,
        remote_instance_url: str,
        local_webid: str,
        private_key_pem: str | None = None,
        key_id: str | None = None,
    ) -> SyncResult:
        """Pull and apply patches from a remote instance for a shared graph.

        Fetches patches since the last sync timestamp, deserializes them,
        groups into Operations, and applies via EventStore with syncSource
        tagging to prevent re-export loops.

        Args:
            graph_iri: The shared graph IRI to sync.
            remote_instance_url: Base URL of the remote instance.
            local_webid: Local user's WebID.
            private_key_pem: PEM key for signing the request.
            key_id: Key ID for the signature.

        Returns:
            SyncResult with pulled/applied counts and any errors.
        """
        errors: list[str] = []

        # Determine since timestamp (last sync or epoch for first sync)
        since = await self._get_last_sync(graph_iri)
        if not since:
            since = "1970-01-01T00:00:00+00:00"

        # Extract graph_id from IRI
        graph_id = graph_iri.replace("urn:sempkm:shared:", "")

        # Build fetch URL
        local_instance_url = ""  # Will be empty if not configured
        url = (
            f"{remote_instance_url.rstrip('/')}/api/federation/patches/{graph_id}"
            f"?since={since}&requester={local_instance_url}"
        )

        # Fetch patches from remote
        headers: dict[str, str] = {
            "Accept": "application/json",
        }

        # Sign the request if credentials provided
        if private_key_pem and key_id:
            try:
                headers = await sign_request(
                    "GET", url, headers, None, private_key_pem, key_id
                )
            except Exception as e:
                errors.append(f"Failed to sign request: {e}")
                return SyncResult(pulled=0, applied=0, errors=errors)

        try:
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                resp = await http_client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            errors.append(f"Failed to fetch patches: {e}")
            return SyncResult(pulled=0, applied=0, errors=errors)

        patch_text = data.get("patch_text", "")
        event_count = data.get("event_count", 0)

        if not patch_text or event_count == 0:
            # Update last sync even if nothing to pull
            await self._update_last_sync(graph_iri)
            return SyncResult(pulled=0, applied=0, errors=errors)

        # Deserialize patch
        try:
            quads = deserialize_patch(patch_text)
        except Exception as e:
            errors.append(f"Failed to deserialize patch: {e}")
            return SyncResult(pulled=event_count, applied=0, errors=errors)

        # Group A/D tuples into Operations
        inserts: list[tuple] = []
        deletes: list[tuple] = []
        for action, s, p, o, g in quads:
            if action == "A":
                inserts.append((s, p, o))
            elif action == "D":
                deletes.append((s, p, o))

        op = Operation(
            operation_type="federation.sync",
            affected_iris=[graph_iri],
            description=f"Sync {len(inserts)} inserts, {len(deletes)} deletes from {remote_instance_url}",
            data_triples=[],
            materialize_inserts=inserts,
            materialize_deletes=deletes,
        )

        # Apply via EventStore with syncSource tagging
        try:
            await self._event_store.commit(
                [op],
                target_graph=graph_iri,
                sync_source=remote_instance_url,
            )
        except Exception as e:
            errors.append(f"Failed to apply patches: {e}")
            return SyncResult(pulled=event_count, applied=0, errors=errors)

        # Update last sync timestamp
        await self._update_last_sync(graph_iri)

        # Fire-and-forget: notify remote members of sync status
        try:
            await self.notify_remote_members_of_change(
                graph_iri,
                local_webid,
                event_count=len(inserts) + len(deletes),
                private_key_pem=private_key_pem,
                key_id=key_id,
            )
        except Exception as e:
            logger.warning("Failed to send sync status alert: %s", e)

        applied = len(inserts) + len(deletes)
        return SyncResult(pulled=event_count, applied=applied, errors=errors)

    # ------------------------------------------------------------------
    # Notification sending
    # ------------------------------------------------------------------

    async def send_notification(
        self,
        recipient_handle: str,
        notification_type: str,
        sender_webid: str,
        private_key_pem: str | None = None,
        key_id: str | None = None,
        object_iri: str | None = None,
        content: str | None = None,
    ) -> None:
        """Send a notification to a remote user.

        Discovers the recipient, builds an appropriate ActivityStreams
        notification (Announce for recommendation, Note for message),
        signs and POSTs to their inbox.

        Args:
            recipient_handle: WebID URL or user@domain handle.
            notification_type: "recommendation" or "message".
            sender_webid: The sender's WebID URI.
            private_key_pem: PEM key for signing.
            key_id: Key ID for signing.
            object_iri: IRI of the object to recommend (for recommendations).
            content: Text content (for messages).
        """
        # Discover recipient
        discovery = await discover_webid(recipient_handle)
        recipient_webid = discovery.get("webid", recipient_handle)
        inbox_url = discovery.get("inbox")

        if not inbox_url:
            inbox_url = await self._discover_inbox_from_profile(recipient_webid)

        if not inbox_url:
            raise ValueError(f"Cannot discover inbox for {recipient_handle}")

        # Build notification based on type
        if notification_type == "recommendation":
            notification = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "type": "Announce",
                "actor": sender_webid,
                "object": {
                    "type": "Object",
                    "id": object_iri or "",
                },
                "target": recipient_webid,
                "summary": f"Recommended: {object_iri}",
            }
        elif notification_type == "message":
            notification = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "type": "Note",
                "actor": sender_webid,
                "content": content or "",
                "mediaType": "text/markdown",
                "target": recipient_webid,
            }
        else:
            raise ValueError(f"Unknown notification type: {notification_type}")

        await self._post_to_inbox(
            inbox_url, notification, private_key_pem, key_id
        )
        logger.info(
            "Sent %s notification to %s", notification_type, recipient_handle
        )

    # ------------------------------------------------------------------
    # Contact management
    # ------------------------------------------------------------------

    async def list_contacts(self, user_webid: str) -> list[ContactInfo]:
        """List known remote contacts derived from shared graph memberships.

        Args:
            user_webid: The local user's WebID.

        Returns:
            List of ContactInfo for distinct remote WebIDs.
        """
        sparql = f"""
        SELECT DISTINCT ?member WHERE {{
          GRAPH <{FEDERATION_GRAPH}> {{
            ?graph a <{SEMPKM.SharedGraph}> ;
                   <{SEMPKM.member}> <{user_webid}> ;
                   <{SEMPKM.member}> ?member .
          }}
          FILTER(?member != <{user_webid}>)
        }}
        """
        results = await self._client.query(sparql)
        bindings = results.get("results", {}).get("bindings", [])

        contacts = []
        for row in bindings:
            webid = row.get("member", {}).get("value", "")
            if not webid:
                continue

            # Derive instance URL and label from WebID
            instance_url = webid.split("/users/")[0] if "/users/" in webid else webid.rsplit("/", 1)[0]
            label = webid.rsplit("/", 1)[-1].split("#")[0] if "/" in webid else webid

            contacts.append(ContactInfo(
                webid=webid,
                label=label,
                instance_url=instance_url,
                last_seen=None,
            ))

        return contacts

    # ------------------------------------------------------------------
    # Shared graph access for SPARQL scoping
    # ------------------------------------------------------------------

    async def get_user_shared_graphs(self, user_webid: str) -> list[str]:
        """Return list of shared graph IRIs the user is a member of.

        Used by SPARQL scoping to add FROM clauses for shared graph data.

        Args:
            user_webid: The user's WebID URI.

        Returns:
            List of shared graph IRI strings.
        """
        sparql = f"""
        SELECT DISTINCT ?graph WHERE {{
          GRAPH <{FEDERATION_GRAPH}> {{
            ?graph a <{SEMPKM.SharedGraph}> ;
                   <{SEMPKM.member}> <{user_webid}> .
          }}
        }}
        """
        results = await self._client.query(sparql)
        bindings = results.get("results", {}).get("bindings", [])

        return [
            row.get("graph", {}).get("value", "")
            for row in bindings
            if row.get("graph", {}).get("value", "")
        ]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_last_sync(self, graph_iri: str) -> str | None:
        """Get the last sync timestamp for a shared graph."""
        sparql = f"""
        SELECT ?ts WHERE {{
          GRAPH <{FEDERATION_GRAPH}> {{
            <{graph_iri}> <{SEMPKM.lastSync}> ?ts .
          }}
        }}
        """
        results = await self._client.query(sparql)
        bindings = results.get("results", {}).get("bindings", [])
        if bindings:
            return bindings[0].get("ts", {}).get("value")
        return None

    async def _get_pending_count(self, graph_iri: str) -> int:
        """Count events targeting this graph that haven't been pushed."""
        sparql = f"""
        SELECT (COUNT(DISTINCT ?event) AS ?count) WHERE {{
          GRAPH ?event {{
            ?event a <{SEMPKM.Event}> ;
                   <{SEMPKM.graphTarget}> <{graph_iri}> .
            FILTER NOT EXISTS {{ ?event <{SEMPKM.syncSource}> ?src }}
          }}
        }}
        """
        results = await self._client.query(sparql)
        bindings = results.get("results", {}).get("bindings", [])
        if bindings:
            return int(bindings[0].get("count", {}).get("value", "0"))
        return 0

    async def _get_graph_name(self, graph_iri: str) -> str:
        """Get the name/title of a shared graph."""
        sparql = f"""
        SELECT ?title WHERE {{
          GRAPH <{FEDERATION_GRAPH}> {{
            <{graph_iri}> <{DCTERMS.title}> ?title .
          }}
        }}
        """
        results = await self._client.query(sparql)
        bindings = results.get("results", {}).get("bindings", [])
        if bindings:
            return bindings[0].get("title", {}).get("value", "Shared Graph")
        return "Shared Graph"

    async def _get_required_model(self, graph_iri: str) -> str:
        """Get the required model for a shared graph."""
        sparql = f"""
        SELECT ?model WHERE {{
          GRAPH <{FEDERATION_GRAPH}> {{
            <{graph_iri}> <{SEMPKM.requiredModel}> ?model .
          }}
        }}
        """
        results = await self._client.query(sparql)
        bindings = results.get("results", {}).get("bindings", [])
        if bindings:
            return bindings[0].get("model", {}).get("value", "")
        return ""

    async def _update_last_sync(self, graph_iri: str) -> None:
        """Update the last sync timestamp for a shared graph."""
        now = datetime.now(timezone.utc).isoformat()
        sparql = f"""
        DELETE {{
          GRAPH <{FEDERATION_GRAPH}> {{
            <{graph_iri}> <{SEMPKM.lastSync}> ?old .
          }}
        }}
        INSERT {{
          GRAPH <{FEDERATION_GRAPH}> {{
            <{graph_iri}> <{SEMPKM.lastSync}> "{now}"^^<{XSD.dateTime}> .
          }}
        }}
        WHERE {{
          OPTIONAL {{
            GRAPH <{FEDERATION_GRAPH}> {{
              <{graph_iri}> <{SEMPKM.lastSync}> ?old .
            }}
          }}
        }}
        """
        await self._client.update(sparql)

    async def _store_contact(self, webid: str) -> None:
        """Store a WebID as a known contact in federation metadata."""
        now = datetime.now(timezone.utc).isoformat()
        sparql = f"""
        INSERT DATA {{
          GRAPH <{FEDERATION_GRAPH}> {{
            <{webid}> a <{SEMPKM.Contact}> ;
              <{SEMPKM.discoveredAt}> "{now}"^^<{XSD.dateTime}> .
          }}
        }}
        """
        await self._client.update(sparql)

    async def _discover_inbox_from_profile(self, webid: str) -> str | None:
        """Discover a user's inbox URL from their WebID profile."""
        try:
            profile_url = webid.split("#")[0]
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    profile_url,
                    headers={"Accept": "text/turtle"},
                )
                resp.raise_for_status()

                # Look for ldp:inbox in the response
                from rdflib import Graph
                g = Graph()
                g.parse(data=resp.text, format="turtle")

                from app.rdf.namespaces import LDP
                inbox_values = list(g.objects(predicate=LDP.inbox))
                if inbox_values:
                    return str(inbox_values[0])
        except Exception as e:
            logger.warning("Failed to discover inbox for %s: %s", webid, e)
        return None

    async def _post_to_inbox(
        self,
        inbox_url: str,
        notification: dict,
        private_key_pem: str | None = None,
        key_id: str | None = None,
    ) -> None:
        """POST a JSON-LD notification to a remote inbox.

        Signs the request with HTTP Signatures if credentials are provided.

        Args:
            inbox_url: The target inbox URL.
            notification: The JSON-LD notification dict.
            private_key_pem: PEM key for signing.
            key_id: Key ID for signing.
        """
        import json

        body = json.dumps(notification).encode("utf-8")
        headers: dict[str, str] = {
            "Content-Type": "application/ld+json",
        }

        if private_key_pem and key_id:
            try:
                headers = await sign_request(
                    "POST", inbox_url, headers, body, private_key_pem, key_id
                )
            except Exception as e:
                logger.warning("Failed to sign outbound notification: %s", e)

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                inbox_url,
                content=body,
                headers=headers,
            )
            resp.raise_for_status()


def _sparql_term(term) -> str:
    """Serialize an rdflib term for SPARQL INSERT DATA."""
    if isinstance(term, URIRef):
        return f"<{term}>"
    elif isinstance(term, Literal):
        escaped = _escape_sparql(str(term))
        if term.language:
            return f'"{escaped}"@{term.language}'
        elif term.datatype:
            return f'"{escaped}"^^<{term.datatype}>'
        else:
            return f'"{escaped}"'
    else:
        return f'"{_escape_sparql(str(term))}"'


def _escape_sparql(value: str) -> str:
    """Escape a string for SPARQL string literals."""
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _binding_to_term(binding: dict) -> URIRef | Literal:
    """Convert a SPARQL JSON result binding to an rdflib term."""
    term_type = binding["type"]
    value = binding["value"]

    if term_type == "uri":
        return URIRef(value)
    elif term_type == "literal":
        datatype = binding.get("datatype")
        lang = binding.get("xml:lang")
        if lang:
            return Literal(value, lang=lang)
        elif datatype:
            return Literal(value, datatype=URIRef(datatype))
        else:
            return Literal(value)
    elif term_type == "bnode":
        return URIRef(f"urn:skolem:{value}")
    else:
        return URIRef(value)
