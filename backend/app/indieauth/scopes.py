"""IndieAuth scope registry and validation."""

SCOPE_REGISTRY: dict[str, dict[str, str]] = {
    "profile": {
        "description": "Access your profile information (name, photo, URL)",
        "claims": "name, photo, url",
    },
    "email": {
        "description": "Access your email address",
        "claims": "email",
    },
}


def validate_scopes(requested: str) -> list[str]:
    """Split space-separated scope string and return only known scopes.

    Unknown scopes are silently dropped per IndieAuth spec.
    """
    if not requested or not requested.strip():
        return []
    return [s for s in requested.strip().split() if s in SCOPE_REGISTRY]
