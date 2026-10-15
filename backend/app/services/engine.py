"""Pure, side-effect-free flag evaluation logic.

Kept separate from I/O so it can be unit-tested exhaustively and reused by any
SDK that wants to evaluate locally.
"""

import hashlib
from typing import Any

BUCKETS = 100


def rollout_bucket(flag_key: str, user_id: str) -> int:
    """Deterministically map (flag_key, user_id) to a bucket in [0, 99].

    The flag key is part of the hash input so the same user lands in different
    buckets for different flags; otherwise the same 10% of users would receive
    every 10% rollout.
    """
    digest = hashlib.md5(f"{flag_key}:{user_id}".encode(), usedforsecurity=False).hexdigest()
    return int(digest, 16) % BUCKETS


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def rule_matches(rule: dict, attributes: dict[str, Any]) -> bool:
    attribute = rule.get("attribute")
    operator = rule.get("operator")
    values = [str(v) for v in rule.get("values", [])]

    if attribute not in attributes:
        return False

    actual = attributes[attribute]
    actual_str = str(actual).lower() if isinstance(actual, bool) else str(actual)

    if operator == "equals":
        return bool(values) and actual_str == values[0]
    if operator == "not_equals":
        return bool(values) and actual_str != values[0]
    if operator == "in":
        return actual_str in values
    if operator == "not_in":
        return actual_str not in values
    if operator in ("gt", "lt"):
        left = _as_number(actual)
        right = _as_number(values[0]) if values else None
        if left is None or right is None:
            return False
        return left > right if operator == "gt" else left < right
    return False


def evaluate_flag(flag: dict, user_id: str, attributes: dict[str, Any]) -> dict:
    """Evaluate a flag snapshot for one user.

    Precedence: kill switch -> explicit user targeting -> attribute rules
    -> percentage rollout.
    """
    base = {"flag_key": flag["key"], "user_id": user_id, "flag_version": flag["version"]}

    if not flag["enabled"]:
        return {**base, "enabled": False, "reason": "FLAG_DISABLED", "bucket": None}

    if user_id in flag.get("targeted_users", []):
        return {**base, "enabled": True, "reason": "TARGETED_USER", "bucket": None}

    for rule in flag.get("rules", []):
        if rule_matches(rule, attributes):
            return {**base, "enabled": True, "reason": "RULE_MATCH", "bucket": None}

    bucket = rollout_bucket(flag["key"], user_id)
    if bucket < flag["rollout_percentage"]:
        return {**base, "enabled": True, "reason": "ROLLOUT_INCLUDED", "bucket": bucket}
    return {**base, "enabled": False, "reason": "ROLLOUT_EXCLUDED", "bucket": bucket}
