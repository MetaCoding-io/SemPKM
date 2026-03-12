"""HTTP Message Signatures (RFC 9421) sign/verify wrappers for federation.

Provides outbound request signing with the local instance's Ed25519 private key,
inbound request verification by fetching remote WebID public keys, and a FastAPI
dependency for protecting federation endpoints.

Uses the http-message-signatures library with Ed25519 algorithm.
"""

import base64
import hashlib
import logging
from typing import Any

import httpx
import requests as req_lib
from cachetools import TTLCache
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from fastapi import HTTPException, Request
from http_message_signatures import (
    HTTPMessageSigner,
    HTTPMessageVerifier,
    HTTPSignatureKeyResolver,
    InvalidSignature,
    algorithms,
)
from rdflib import Graph

logger = logging.getLogger(__name__)

# Cache for remote WebID public keys: 1-hour TTL, 64 entries per CONTEXT.md
_webid_key_cache: TTLCache = TTLCache(maxsize=64, ttl=3600)


class SemPKMKeyResolver(HTTPSignatureKeyResolver):
    """Key resolver for outbound signing with a local Ed25519 private key."""

    def __init__(self, private_key: Any, key_id: str):
        self._private_key = private_key
        self._key_id = key_id

    def resolve_private_key(self, key_id: str) -> Any:
        return self._private_key

    def resolve_public_key(self, key_id: str) -> Any:
        # Not used for signing, but required by interface
        return self._private_key.public_key()


async def sign_request(
    method: str,
    url: str,
    headers: dict,
    body: bytes | None,
    private_key_pem: str,
    key_id: str,
) -> dict:
    """Sign an outbound HTTP request with RFC 9421 HTTP Message Signatures.

    Args:
        method: HTTP method (GET, POST, etc.)
        url: Full target URL
        headers: Request headers dict
        body: Request body bytes or None
        private_key_pem: PEM-encoded Ed25519 private key
        key_id: Key identifier (typically the sender's WebID URI)

    Returns:
        Updated headers dict with Signature and Signature-Input added.
    """
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    private_key = load_pem_private_key(private_key_pem.encode(), password=None)

    # Add Content-Digest header if body is present
    if body is not None:
        digest = hashlib.sha256(body).digest()
        b64_digest = base64.b64encode(digest).decode()
        headers["Content-Digest"] = f"sha-256=:{b64_digest}:"

    resolver = SemPKMKeyResolver(private_key, key_id)
    signer = HTTPMessageSigner(
        signature_algorithm=algorithms.ED25519,
        key_resolver=resolver,
    )

    # Build covered components based on what's available
    covered = ["@method", "@authority", "@target-uri"]
    if "content-type" in {k.lower() for k in headers}:
        covered.append("content-type")
    if "content-digest" in {k.lower() for k in headers}:
        covered.append("content-digest")

    # Build a requests.Request object for the library
    r = req_lib.Request(method, url, headers=headers, data=body)
    prepared = r.prepare()

    signer.sign(
        prepared,
        key_id=key_id,
        covered_component_ids=tuple(covered),
    )

    return dict(prepared.headers)


async def fetch_webid_public_key(
    webid_uri: str, force_refresh: bool = False
) -> Ed25519PublicKey:
    """Fetch and cache a remote WebID's Ed25519 public key.

    Fetches the WebID profile in Turtle format, extracts the sec:publicKeyPem
    value, and loads it as an Ed25519PublicKey. Results are cached with 1-hour
    TTL. On force_refresh, the cache entry is evicted and refetched.

    Args:
        webid_uri: The WebID URI (e.g., https://example.com/users/alice#me)
        force_refresh: If True, bypass cache and refetch

    Returns:
        Ed25519PublicKey instance

    Raises:
        HTTPException(401): If key cannot be fetched or parsed
    """
    if not force_refresh and webid_uri in _webid_key_cache:
        return _webid_key_cache[webid_uri]

    # Evict stale entry if force-refreshing
    _webid_key_cache.pop(webid_uri, None)

    # Derive profile URL from WebID URI (strip #me fragment)
    profile_url = webid_uri.split("#")[0]

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                profile_url,
                headers={"Accept": "text/turtle"},
            )
            resp.raise_for_status()

        # Parse Turtle response
        g = Graph()
        g.parse(data=resp.text, format="turtle")

        # Extract sec:publicKeyPem value
        SEC = "https://w3id.org/security#"
        pem_values = list(
            g.objects(predicate=__import__("rdflib").URIRef(f"{SEC}publicKeyPem"))
        )
        if not pem_values:
            raise ValueError(f"No sec:publicKeyPem found in WebID profile: {webid_uri}")

        pem_str = str(pem_values[0])
        public_key = load_pem_public_key(pem_str.encode())

        if not isinstance(public_key, Ed25519PublicKey):
            raise ValueError(f"WebID key is not Ed25519: {webid_uri}")

        _webid_key_cache[webid_uri] = public_key
        logger.info("Cached public key for WebID: %s", webid_uri)
        return public_key

    except Exception as e:
        logger.warning("Failed to fetch WebID public key for %s: %s", webid_uri, e)
        raise HTTPException(
            status_code=401,
            detail=f"Cannot verify sender identity: {e}",
        )


class RemoteKeyResolver(HTTPSignatureKeyResolver):
    """Key resolver that fetches public keys from remote WebID profiles.

    Used for verifying inbound HTTP Signatures. The key_id in the signature
    is expected to be the sender's WebID URI.
    """

    def __init__(self, cache: TTLCache):
        self._cache = cache
        self._resolved_key: Ed25519PublicKey | None = None

    def resolve_public_key(self, key_id: str) -> Ed25519PublicKey:
        """Resolve a public key by key_id (WebID URI).

        This is called synchronously by the library, so we check the cache.
        The actual async fetch happens in verify_request before calling verify.
        """
        if key_id in self._cache:
            return self._cache[key_id]
        if self._resolved_key is not None:
            return self._resolved_key
        raise InvalidSignature(f"No cached key for {key_id}")

    def resolve_private_key(self, key_id: str) -> Any:
        raise NotImplementedError("RemoteKeyResolver is for verification only")

    def set_resolved_key(self, key: Ed25519PublicKey) -> None:
        """Set a pre-fetched key for synchronous resolution."""
        self._resolved_key = key


async def verify_request(
    method: str,
    url: str,
    headers: dict,
    body: bytes | None,
) -> str:
    """Verify an inbound HTTP Signature and return the sender's WebID URI.

    Extracts the key_id from the signature, fetches the remote WebID's
    public key, and verifies. On failure, force-refreshes the key cache
    and retries once (handles key rotation).

    Args:
        method: HTTP method
        url: Full request URL
        headers: Request headers
        body: Request body bytes or None

    Returns:
        The sender's WebID URI (key_id from signature)

    Raises:
        HTTPException(401): If signature is invalid or key cannot be fetched
    """
    # Build a requests.PreparedRequest for the library
    r = req_lib.Request(method, url, headers=headers, data=body)
    prepared = r.prepare()

    # Extract key_id from Signature-Input header to pre-fetch the key
    sig_input = headers.get("Signature-Input", headers.get("signature-input", ""))
    key_id = _extract_key_id(sig_input)
    if not key_id:
        raise HTTPException(status_code=401, detail="Missing or invalid HTTP Signature")

    # Pre-fetch the key asynchronously
    try:
        public_key = await fetch_webid_public_key(key_id)
    except HTTPException:
        raise

    resolver = RemoteKeyResolver(_webid_key_cache)
    resolver.set_resolved_key(public_key)

    verifier = HTTPMessageVerifier(
        signature_algorithm=algorithms.ED25519,
        key_resolver=resolver,
    )

    try:
        results = verifier.verify(prepared)
        if not results:
            raise InvalidSignature("No valid signatures found")
        return key_id
    except (InvalidSignature, Exception) as e:
        # Force-refresh key and retry once (handles key rotation)
        logger.info("Signature verification failed for %s, retrying with fresh key", key_id)
        try:
            public_key = await fetch_webid_public_key(key_id, force_refresh=True)
            resolver.set_resolved_key(public_key)
            results = verifier.verify(prepared)
            if not results:
                raise InvalidSignature("No valid signatures found after key refresh")
            return key_id
        except (InvalidSignature, Exception) as retry_err:
            logger.warning("Signature verification failed after retry for %s: %s", key_id, retry_err)
            raise HTTPException(
                status_code=401,
                detail="HTTP Signature verification failed",
            )


def _extract_key_id(sig_input: str) -> str | None:
    """Extract key_id from Signature-Input header value.

    Signature-Input format: label=("@method" ...);keyid="webid-uri";...
    """
    if not sig_input:
        return None

    import re

    match = re.search(r'keyid="([^"]+)"', sig_input)
    if match:
        return match.group(1)
    return None


class VerifyHTTPSignature:
    """FastAPI dependency that verifies HTTP Signatures on incoming requests.

    Usage:
        @router.post("/api/inbox")
        async def receive(sender_webid: str = Depends(VerifyHTTPSignature())):
            ...
    """

    async def __call__(self, request: Request) -> str:
        """Extract request details and verify the HTTP Signature.

        Returns:
            The sender's WebID URI string.
        """
        # Read body early and cache it (request.body() caches internally)
        body = await request.body()

        # Build full URL from request
        url = str(request.url)
        method = request.method
        headers = dict(request.headers)

        return await verify_request(method, url, headers, body if body else None)
