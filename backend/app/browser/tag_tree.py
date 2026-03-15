"""Pure function for building hierarchical tag tree nodes from flat tag data.

No I/O, no async, no imports beyond stdlib. Designed for easy unit testing
without Docker/triplestore dependencies.
"""

from __future__ import annotations


def build_tag_tree(
    tag_values: list[dict], prefix: str = ""
) -> list[dict]:
    """Group flat tag values into tree nodes at the specified prefix level.

    Args:
        tag_values: List of ``{"value": "garden/cultivate/roses", "count": N}``.
            Each dict must have ``"value"`` (str) and ``"count"`` (int) keys.
        prefix: Parent prefix path. Empty string for root-level nodes,
            ``"garden"`` for first-level children under *garden*, etc.

    Returns:
        Sorted list of node dicts, each containing:

        - **segment** – the folder/leaf label at this level (e.g. ``"garden"``)
        - **prefix** – full prefix path (e.g. ``"garden"`` at root,
          ``"garden/cultivate"`` at level 2)
        - **direct_count** – objects tagged exactly with this node's prefix
          value (0 if only a grouping folder)
        - **total_count** – ``direct_count`` plus counts of all descendants
        - **has_children** – whether deeper ``/``-separated segments exist
          beyond this level
    """
    if not tag_values:
        return []

    # Bucket: segment -> {"direct_count": int, "descendant_count": int,
    #                      "has_children": bool}
    buckets: dict[str, dict] = {}

    prefix_slash = f"{prefix}/" if prefix else ""

    for entry in tag_values:
        value: str = entry["value"]
        count: int = entry["count"]

        if prefix:
            # Non-root: only consider tags that start with "prefix/"
            if not value.startswith(prefix_slash):
                # Also check for exact match (tag equals the prefix itself).
                # This contributes to the parent node, not to children at
                # this level, so skip.
                continue
            remainder = value[len(prefix_slash):]
        else:
            # Root level: the full value is the remainder
            remainder = value

        if not remainder:
            # Tag value is exactly the prefix (e.g. prefix="garden",
            # value="garden"). This was already counted as direct_count
            # at the parent level — skip for children listing.
            continue

        # Extract the next segment (before the next `/`)
        slash_pos = remainder.find("/")
        if slash_pos == -1:
            segment = remainder
            is_exact = True  # This tag's value ends at this segment
            deeper = False
        else:
            segment = remainder[:slash_pos]
            is_exact = False
            deeper = True

        # Filter out empty segments (e.g. from "//" in tags)
        if not segment:
            continue

        if segment not in buckets:
            buckets[segment] = {
                "direct_count": 0,
                "descendant_count": 0,
                "has_children": False,
            }

        bucket = buckets[segment]

        if is_exact:
            # Tag value ends exactly at this segment
            bucket["direct_count"] += count
        else:
            # Tag value continues deeper
            bucket["descendant_count"] += count
            bucket["has_children"] = True

        if deeper:
            bucket["has_children"] = True

    # Also scan for exact prefix matches to set direct_count on the
    # parent level. When prefix="" and a tag value has no "/" at all,
    # it's already handled above (is_exact=True). When prefix="garden"
    # and tag value is exactly "garden", that's the direct_count for
    # the "garden" node — but that node lives at the *parent* level,
    # not at this level. So we don't need to do anything extra here.

    # Build result nodes
    result: list[dict] = []
    for segment, bucket in buckets.items():
        node_prefix = f"{prefix}/{segment}" if prefix else segment
        result.append({
            "segment": segment,
            "prefix": node_prefix,
            "direct_count": bucket["direct_count"],
            "total_count": bucket["direct_count"] + bucket["descendant_count"],
            "has_children": bucket["has_children"],
        })

    # Sort alphabetically by segment
    result.sort(key=lambda n: n["segment"])

    return result
