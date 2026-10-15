import redis

from app.cache import FlagCache
from app.deps import get_cache
from app.main import app
from app.services.engine import rollout_bucket


def evaluate(client, flag_key="new-checkout", user_id="user_42", **attributes):
    response = client.post(
        "/api/v1/evaluate",
        json={"flag_key": flag_key, "user_id": user_id, "attributes": attributes},
    )
    return response


def test_get_endpoint(client, make_flag):
    make_flag(rollout_percentage=100)
    response = client.get("/api/v1/evaluate", params={"flag_key": "new-checkout", "user_id": "u1"})
    assert response.status_code == 200
    assert response.json()["enabled"] is True


def test_reasons(client, make_flag):
    make_flag(
        targeted_users=["vip"],
        rules=[{"attribute": "country", "operator": "equals", "values": ["IN"]}],
    )
    assert evaluate(client, user_id="vip").json()["reason"] == "TARGETED_USER"
    assert evaluate(client, user_id="x", country="IN").json()["reason"] == "RULE_MATCH"
    assert evaluate(client, user_id="x", country="US").json()["reason"] == "ROLLOUT_EXCLUDED"


def test_second_call_is_served_from_cache(client, make_flag):
    make_flag(rollout_percentage=50)
    first = evaluate(client).json()
    second = evaluate(client).json()
    assert first["cached"] is False
    assert second["cached"] is True
    assert first["enabled"] == second["enabled"]
    assert second["bucket"] == rollout_bucket("new-checkout", "user_42")


def test_attributes_are_part_of_the_cache_key(client, make_flag):
    make_flag(rules=[{"attribute": "country", "operator": "equals", "values": ["IN"]}])
    assert evaluate(client, country="IN").json()["enabled"] is True
    assert evaluate(client, country="US").json()["enabled"] is False


def test_toggle_invalidates_cached_evaluations(client, make_flag):
    make_flag(rollout_percentage=100)
    evaluate(client)
    assert evaluate(client).json()["cached"] is True

    client.post("/api/v1/flags/new-checkout/toggle")
    after = evaluate(client).json()
    assert after["enabled"] is False
    assert after["reason"] == "FLAG_DISABLED"
    assert after["cached"] is False
    assert after["flag_version"] == 2


def test_rollout_change_invalidates_cache(client, make_flag):
    make_flag(rollout_percentage=0)
    assert evaluate(client).json()["enabled"] is False
    client.patch("/api/v1/flags/new-checkout", json={"rollout_percentage": 100})
    assert evaluate(client).json()["enabled"] is True


def test_unknown_flag_returns_404(client):
    assert evaluate(client, flag_key="ghost").status_code == 404
    assert evaluate(client, flag_key="ghost").status_code == 404


def test_flag_created_after_negative_cache_is_visible_immediately(client, make_flag):
    assert evaluate(client).status_code == 404
    make_flag(rollout_percentage=100)
    response = evaluate(client)
    assert response.status_code == 200
    assert response.json()["enabled"] is True


def test_deleted_flag_stops_evaluating(client, make_flag):
    make_flag(rollout_percentage=100)
    evaluate(client)
    client.delete("/api/v1/flags/new-checkout")
    assert evaluate(client).status_code == 404


def test_batch_evaluation(client, make_flag):
    make_flag(key="flag-on", name="on", rollout_percentage=100)
    make_flag(key="flag-off", name="off", enabled=False)
    response = client.post(
        "/api/v1/evaluate/batch",
        json={"user_id": "u1", "flag_keys": ["flag-on", "flag-off", "ghost", "flag-on"]},
    )
    body = response.json()
    assert response.status_code == 200
    assert {r["flag_key"]: r["enabled"] for r in body["results"]} == {"flag-on": True, "flag-off": False}
    assert body["missing"] == ["ghost"]


def test_redis_outage_falls_back_to_postgres(client, make_flag):
    make_flag(rollout_percentage=100)
    broken = FlagCache(
        redis.Redis(host="127.0.0.1", port=1, socket_timeout=0.05, socket_connect_timeout=0.05),
        cooldown_seconds=30,
    )
    app.dependency_overrides[get_cache] = lambda: broken

    first = evaluate(client)
    second = evaluate(client)
    assert first.status_code == 200 and first.json()["enabled"] is True
    assert second.status_code == 200 and second.json()["cached"] is False

    toggled = client.post("/api/v1/flags/new-checkout/toggle")
    assert toggled.status_code == 200

    health = client.get("/health").json()
    assert health["status"] == "degraded" and health["redis"] is False
