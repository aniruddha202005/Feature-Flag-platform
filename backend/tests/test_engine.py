import pytest

from app.services.engine import evaluate_flag, rollout_bucket, rule_matches


def make_snapshot(**overrides):
    snapshot = {
        "key": "new-checkout",
        "enabled": True,
        "rollout_percentage": 0,
        "targeted_users": [],
        "rules": [],
        "version": 1,
    }
    snapshot.update(overrides)
    return snapshot


def test_bucket_is_deterministic_and_in_range():
    first = rollout_bucket("new-checkout", "user_42")
    assert first == rollout_bucket("new-checkout", "user_42")
    assert 0 <= first <= 99


def test_bucket_differs_across_flags():
    users = [f"user_{i}" for i in range(200)]
    same = sum(rollout_bucket("flag-a", u) == rollout_bucket("flag-b", u) for u in users)
    assert same < 20


@pytest.mark.parametrize("percentage", [10, 25, 50, 90])
def test_rollout_distribution_is_close_to_target(percentage):
    users = [f"user_{i}" for i in range(20_000)]
    included = sum(rollout_bucket("dist-test", u) < percentage for u in users)
    observed = included / len(users) * 100
    assert abs(observed - percentage) < 1.5


def test_rollout_is_monotonic_when_percentage_increases():
    users = [f"user_{i}" for i in range(2_000)]
    at_20 = {u for u in users if evaluate_flag(make_snapshot(rollout_percentage=20), u, {})["enabled"]}
    at_50 = {u for u in users if evaluate_flag(make_snapshot(rollout_percentage=50), u, {})["enabled"]}
    assert at_20 <= at_50


def test_boundary_bucket_equal_to_cutoff_is_excluded():
    user = "user_42"
    bucket = rollout_bucket("new-checkout", user)
    assert evaluate_flag(make_snapshot(rollout_percentage=bucket), user, {})["enabled"] is False
    assert evaluate_flag(make_snapshot(rollout_percentage=bucket + 1), user, {})["enabled"] is True


def test_zero_and_hundred_percent():
    assert evaluate_flag(make_snapshot(rollout_percentage=0), "u", {})["enabled"] is False
    assert evaluate_flag(make_snapshot(rollout_percentage=100), "u", {})["enabled"] is True


def test_disabled_flag_overrides_everything():
    snapshot = make_snapshot(enabled=False, rollout_percentage=100, targeted_users=["u"])
    result = evaluate_flag(snapshot, "u", {})
    assert result == {
        "flag_key": "new-checkout",
        "user_id": "u",
        "flag_version": 1,
        "enabled": False,
        "reason": "FLAG_DISABLED",
        "bucket": None,
    }


def test_targeted_user_beats_rollout():
    result = evaluate_flag(make_snapshot(targeted_users=["vip"]), "vip", {})
    assert result["enabled"] is True
    assert result["reason"] == "TARGETED_USER"


@pytest.mark.parametrize(
    "rule, attributes, expected",
    [
        ({"attribute": "country", "operator": "equals", "values": ["IN"]}, {"country": "IN"}, True),
        ({"attribute": "country", "operator": "equals", "values": ["IN"]}, {"country": "US"}, False),
        ({"attribute": "country", "operator": "not_equals", "values": ["IN"]}, {"country": "US"}, True),
        ({"attribute": "plan", "operator": "in", "values": ["pro", "team"]}, {"plan": "team"}, True),
        ({"attribute": "plan", "operator": "not_in", "values": ["free"]}, {"plan": "pro"}, True),
        ({"attribute": "age", "operator": "gt", "values": ["18"]}, {"age": 21}, True),
        ({"attribute": "age", "operator": "lt", "values": ["18"]}, {"age": 21}, False),
        ({"attribute": "beta", "operator": "equals", "values": ["true"]}, {"beta": True}, True),
        ({"attribute": "age", "operator": "gt", "values": ["18"]}, {"age": "abc"}, False),
        ({"attribute": "age", "operator": "gt", "values": ["abc"]}, {"age": 30}, False),
        ({"attribute": "plan", "operator": "not_in", "values": ["free"]}, {}, False),
    ],
)
def test_rule_operators(rule, attributes, expected):
    assert rule_matches(rule, attributes) is expected


def test_rule_match_reason():
    snapshot = make_snapshot(rules=[{"attribute": "country", "operator": "in", "values": ["IN"]}])
    result = evaluate_flag(snapshot, "someone", {"country": "IN"})
    assert result["reason"] == "RULE_MATCH"
