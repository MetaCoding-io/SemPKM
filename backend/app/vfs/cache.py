"""TTL cache for WebDAV directory listing results.

Prevents SPARQL query on every PROPFIND. Cache is keyed by path string.
TTL=30s is short enough that edits propagate within one filesystem poll cycle.
maxsize=256 handles typical PKM installs with many type folders.
"""

import threading

from cachetools import TTLCache

# Module-level singleton -- shared across all collection instances.
# Thread-safe for read operations; wsgidav calls from a thread pool.
listing_cache: TTLCache = TTLCache(maxsize=256, ttl=30)

# TTLCache is NOT thread-safe for writes. Protect cache mutations.
_cache_lock = threading.Lock()


def cached_get_member_names(cache_key: str, loader):
    """Check cache for member names; on miss, call loader() and cache the result.

    Args:
        cache_key: Cache key string (e.g. "root:models", "model:basic-pkm:types")
        loader: Callable that returns list[str] of member names (executes SPARQL)

    Returns:
        list[str]: Cached or freshly loaded member names
    """
    # Read outside lock is acceptable -- worst case is a stale miss
    # that triggers a SPARQL query (which we'd do anyway).
    if cache_key in listing_cache:
        return listing_cache[cache_key]

    result = loader()

    with _cache_lock:
        listing_cache[cache_key] = result

    return result
