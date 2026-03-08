"""WebID profile service: key generation, encryption, and RDF profile construction.

Handles Ed25519 key pair lifecycle, Fernet-based private key encryption,
and building RDF profile graphs conforming to FOAF + W3C Security Vocabulary.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import Request
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import FOAF, RDF, RDFS

# W3C Security Vocabulary namespace
SEC = Namespace("https://w3id.org/security#")

# Fixed salt for Fernet key derivation (different from LLM salt)
_WEBID_KDF_SALT = b"sempkm-webid-keys-v1"


def _get_webid_fernet(secret_key: str) -> Fernet:
    """Derive a Fernet key from the application secret_key via PBKDF2."""
    if not secret_key:
        raise ValueError("secret_key is not set -- cannot derive Fernet key for WebID keys")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_WEBID_KDF_SALT,
        iterations=100_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
    return Fernet(key)


def encrypt_private_key(private_pem: str, secret_key: str) -> str:
    """Encrypt a PEM-encoded private key, returning a Fernet token string."""
    return _get_webid_fernet(secret_key).encrypt(private_pem.encode()).decode()


def decrypt_private_key(ciphertext: str, secret_key: str) -> str | None:
    """Decrypt a Fernet token back to PEM. Returns None on failure."""
    try:
        return _get_webid_fernet(secret_key).decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        return None


def generate_ed25519_keypair() -> tuple[str, str]:
    """Generate an Ed25519 key pair.

    Returns:
        (public_pem, private_pem) -- PEM-encoded strings.
        Public key uses SubjectPublicKeyInfo format.
        Private key uses PKCS8 format (no encryption at PEM level).
    """
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    return public_pem, private_pem


def key_fingerprint(public_key_pem: str) -> str:
    """Compute SHA-256 fingerprint of a PEM public key's DER bytes.

    Returns colon-separated hex string, e.g. 'ab:cd:ef:...'
    """
    # Extract DER bytes from PEM
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    pub_key = load_pem_public_key(public_key_pem.encode())
    der_bytes = pub_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    digest = hashlib.sha256(der_bytes).hexdigest()
    return ":".join(digest[i : i + 2] for i in range(0, len(digest), 2))


def build_webid_uri(username: str, base_url: str) -> str:
    """Construct a WebID URI: {base_url}/users/{username}#me"""
    return f"{base_url.rstrip('/')}/users/{username}#me"


def build_profile_url(username: str, base_url: str) -> str:
    """Construct the profile document URL: {base_url}/users/{username}"""
    return f"{base_url.rstrip('/')}/users/{username}"


def build_profile_graph(
    profile_url: str,
    webid_uri: str,
    display_name: str | None,
    public_key_pem: str,
    rel_me_links: list[str] | None = None,
) -> Graph:
    """Build an RDF graph for a WebID profile document.

    Constructs a FOAF PersonalProfileDocument with:
    - foaf:Person (the WebID)
    - sec:Ed25519VerificationKey2020 (public key)
    - foaf:account for each rel="me" link
    """
    g = Graph()
    g.bind("foaf", FOAF)
    g.bind("sec", SEC)

    doc = URIRef(profile_url)
    me = URIRef(webid_uri)
    key_node = URIRef(f"{webid_uri}-key")

    # Profile document
    g.add((doc, RDF.type, FOAF.PersonalProfileDocument))
    g.add((doc, FOAF.primaryTopic, me))

    # Person
    g.add((me, RDF.type, FOAF.Person))
    if display_name:
        g.add((me, FOAF.name, Literal(display_name)))

    # Public key
    g.add((key_node, RDF.type, SEC.Ed25519VerificationKey2020))
    g.add((key_node, SEC.publicKeyPem, Literal(public_key_pem)))
    g.add((key_node, SEC.controller, me))
    g.add((me, SEC.hasKey, key_node))

    # rel="me" links as foaf:account
    if rel_me_links:
        for link in rel_me_links:
            g.add((me, FOAF.account, URIRef(link)))

    return g


def get_base_url(request: Request) -> str:
    """Return the application base URL.

    Uses settings.app_base_url if set, otherwise constructs from request.
    """
    from app.config import settings

    if settings.app_base_url:
        return settings.app_base_url.rstrip("/")
    # Construct from request
    base = str(request.base_url).rstrip("/")
    return base
