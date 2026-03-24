"""Rules service — CRUD and evaluation logic for schedule rules.

Rules are stored as a JSON array under StateClient key ``schedule_rules``.
Each rule has:
- ``id`` (uuid str) — unique identifier
- ``name`` (str) — human-readable label
- ``priority`` (int) — higher wins; ties broken by array position
- ``enabled`` (bool) — disabled rules are skipped during evaluation
- ``conditions`` (dict) — keys: location_zone, activity, time_period, time_range
  - null/missing values act as wildcards (always match)
  - time_range is ``{"start": "HH:MM", "end": "HH:MM"}``
- ``action`` (dict) — ``{"type": "source_type"|"source_iri"|"category", "value": "..."}``

Evaluation uses AND-matching: all non-null conditions must match the context
for the rule to fire. Rules are sorted by priority descending; ties broken
by original array position (stable sort).

Pure functions (no SDK dependency):
- ``validate_rule(rule_dict)`` — validates required fields, generates UUID if missing
- ``evaluate_rules(rules, context)`` — filters + AND-matches + sorts by priority
- ``_matches_condition(conditions, context)`` — internal AND-match logic

I/O boundary functions (require a state_client):
- ``load_rules(state_client)`` — deserialize from JSON state
- ``save_rules(state_client, rules)`` — serialize to JSON state
- ``add_rule(state_client, rule_dict)`` — validate + append + save
- ``update_rule(state_client, rule_id, updates)`` — find + merge + save
- ``delete_rule(state_client, rule_id)`` — remove + save
- ``toggle_rule(state_client, rule_id)`` — flip enabled + save

Constants:
- ``RULES_STATE_KEY`` — StateClient key for the rules JSON array
- ``DEFAULT_DURATIONS`` — media-type default durations in seconds
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# ── Constants ──

RULES_STATE_KEY = "schedule_rules"

DEFAULT_DURATIONS: dict[str, int] = {
    "podcast": 1800,   # 30 minutes
    "video": 900,      # 15 minutes
    "track": 240,      # 4 minutes
    "youtube": 900,    # 15 minutes
    "spotify": 240,    # 4 minutes
}


# ── Validation ──


def validate_rule(rule_dict: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalise a rule dict, filling defaults for missing fields.

    Args:
        rule_dict: Raw rule dict from user input.

    Returns:
        Validated rule dict with all required keys present.

    Raises:
        ValueError: If required fields are missing or have invalid types.
    """
    if not isinstance(rule_dict, dict):
        raise ValueError("Rule must be a dict")

    name = rule_dict.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        raise ValueError("Rule must have a non-empty 'name' string")

    rule: dict[str, Any] = {
        "id": rule_dict.get("id") or str(uuid.uuid4()),
        "name": name.strip(),
        "priority": rule_dict.get("priority", 0),
        "enabled": rule_dict.get("enabled", True),
        "conditions": rule_dict.get("conditions") or {},
        "action": rule_dict.get("action") or {},
    }

    # Coerce priority to int
    try:
        rule["priority"] = int(rule["priority"])
    except (TypeError, ValueError):
        raise ValueError(f"Rule priority must be an integer, got: {rule['priority']!r}")

    # Ensure enabled is bool
    if not isinstance(rule["enabled"], bool):
        rule["enabled"] = bool(rule["enabled"])

    return rule


# ── State I/O ──


async def load_rules(state_client: Any) -> list[dict]:
    """Load the rules array from StateClient.

    Args:
        state_client: SDK StateClient instance with ``get(key)`` method.

    Returns:
        List of rule dicts, or empty list if no rules stored.
    """
    raw = await state_client.get(RULES_STATE_KEY)
    if raw is None:
        return []
    try:
        rules = json.loads(raw)
        if not isinstance(rules, list):
            logger.warning("schedule_rules state is not a list, resetting to []")
            return []
        return rules
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("Failed to parse schedule_rules: %s", exc)
        return []


async def save_rules(state_client: Any, rules: list[dict]) -> None:
    """Persist the rules array to StateClient.

    Args:
        state_client: SDK StateClient instance with ``set(key, value)`` method.
        rules: List of validated rule dicts.
    """
    await state_client.set(RULES_STATE_KEY, json.dumps(rules))


# ── CRUD ──


async def add_rule(state_client: Any, rule_dict: dict[str, Any]) -> dict:
    """Validate a new rule, append to the list, and persist.

    Args:
        state_client: SDK StateClient instance.
        rule_dict: Raw rule dict from user input.

    Returns:
        The validated rule dict with generated ID.

    Raises:
        ValueError: If validation fails.
    """
    rule = validate_rule(rule_dict)
    rules = await load_rules(state_client)
    rules.append(rule)
    await save_rules(state_client, rules)
    logger.info("Added rule %s: %s (priority=%d)", rule["id"], rule["name"], rule["priority"])
    return rule


async def update_rule(
    state_client: Any, rule_id: str, updates: dict[str, Any]
) -> dict | None:
    """Find a rule by ID, merge updates, and persist.

    Args:
        state_client: SDK StateClient instance.
        rule_id: UUID string of the rule to update.
        updates: Dict of fields to merge into the existing rule.

    Returns:
        The updated rule dict, or None if not found.
    """
    rules = await load_rules(state_client)
    for rule in rules:
        if rule.get("id") == rule_id:
            rule.update(updates)
            # Re-validate after merge to catch bad updates
            validated = validate_rule(rule)
            # Replace in-place
            rule.clear()
            rule.update(validated)
            await save_rules(state_client, rules)
            logger.info("Updated rule %s", rule_id)
            return rule
    return None


async def delete_rule(state_client: Any, rule_id: str) -> bool:
    """Remove a rule by ID and persist.

    Args:
        state_client: SDK StateClient instance.
        rule_id: UUID string of the rule to delete.

    Returns:
        True if the rule was found and deleted, False otherwise.
    """
    rules = await load_rules(state_client)
    original_len = len(rules)
    rules = [r for r in rules if r.get("id") != rule_id]
    if len(rules) == original_len:
        return False
    await save_rules(state_client, rules)
    logger.info("Deleted rule %s", rule_id)
    return True


async def toggle_rule(state_client: Any, rule_id: str) -> dict | None:
    """Flip the enabled flag on a rule and persist.

    Args:
        state_client: SDK StateClient instance.
        rule_id: UUID string of the rule to toggle.

    Returns:
        The updated rule dict, or None if not found.
    """
    rules = await load_rules(state_client)
    for rule in rules:
        if rule.get("id") == rule_id:
            rule["enabled"] = not rule.get("enabled", True)
            await save_rules(state_client, rules)
            logger.info("Toggled rule %s → enabled=%s", rule_id, rule["enabled"])
            return rule
    return None


# ── Evaluation ──


def _matches_condition(conditions: dict[str, Any], context: dict[str, Any]) -> bool:
    """Check if all non-null conditions match the context (AND logic).

    Condition keys: location_zone, activity, time_period, time_range.
    - ``None`` or missing key = wildcard (always matches)
    - String values must match exactly (case-sensitive)
    - ``time_range`` is a dict ``{"start": "HH:MM", "end": "HH:MM"}`` checked
      against ``context["current_time"]`` (string comparison, supports wrapping
      midnight when start > end)

    Args:
        conditions: The rule's conditions dict.
        context: The current context dict.

    Returns:
        True if all non-null conditions match, False otherwise.
    """
    # Simple string-match conditions
    for key in ("location_zone", "activity", "time_period"):
        condition_value = conditions.get(key)
        if condition_value is None:
            continue  # wildcard
        context_value = context.get(key)
        if condition_value != context_value:
            return False

    # Time range condition
    time_range = conditions.get("time_range")
    if time_range is not None and isinstance(time_range, dict):
        start = time_range.get("start", "")
        end = time_range.get("end", "")
        current_time = context.get("current_time", "")

        if start and end:
            if not current_time:
                # Can't verify time_range without current_time → no match
                return False
            if start <= end:
                # Normal range: e.g. 08:00 to 17:00
                if not (start <= current_time <= end):
                    return False
            else:
                # Wrapping midnight: e.g. 22:00 to 06:00
                if not (current_time >= start or current_time <= end):
                    return False

    return True


def evaluate_rules(rules: list[dict], context: dict[str, Any]) -> list[dict]:
    """Evaluate rules against context and return matched rules sorted by priority.

    Filters to enabled rules, then AND-matches each rule's conditions against
    the context dict. Results are sorted by priority descending (higher wins).
    Ties are broken by original array position (stable sort preserves insertion order).

    Args:
        rules: List of rule dicts (all rules, including disabled).
        context: Current context dict with keys like location_zone, activity,
            time_period, current_time.

    Returns:
        List of matched rule dicts, sorted by priority descending.
    """
    matched: list[dict] = []

    for rule in rules:
        # Skip disabled rules
        if not rule.get("enabled", True):
            continue

        conditions = rule.get("conditions") or {}
        if _matches_condition(conditions, context):
            matched.append(rule)

    # Sort by priority descending; stable sort preserves array-position ties
    matched.sort(key=lambda r: r.get("priority", 0), reverse=True)

    return matched
