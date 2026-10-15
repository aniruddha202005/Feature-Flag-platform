def test_create_and_get_flag(client, make_flag):
    created = make_flag(description="Redesigned checkout", rollout_percentage=25)
    assert created["key"] == "new-checkout"
    assert created["version"] == 1

    response = client.get("/api/v1/flags/new-checkout")
    assert response.status_code == 200
    assert response.json()["rollout_percentage"] == 25


def test_list_flags(client, make_flag):
    make_flag(key="flag-one", name="One")
    make_flag(key="flag-two", name="Two")
    keys = {f["key"] for f in client.get("/api/v1/flags").json()}
    assert keys == {"flag-one", "flag-two"}


def test_duplicate_key_returns_409(client, make_flag):
    make_flag()
    response = client.post("/api/v1/flags", json={"key": "new-checkout", "name": "dup"})
    assert response.status_code == 409


def test_validation_errors(client):
    bad_rollout = client.post("/api/v1/flags", json={"key": "abc", "name": "x", "rollout_percentage": 150})
    assert bad_rollout.status_code == 422

    bad_key = client.post("/api/v1/flags", json={"key": "Bad Key!", "name": "x"})
    assert bad_key.status_code == 422

    bad_rule = client.post(
        "/api/v1/flags",
        json={"key": "abc", "name": "x", "rules": [{"attribute": "a", "operator": "regex", "values": ["x"]}]},
    )
    assert bad_rule.status_code == 422


def test_update_bumps_version_and_dedupes_users(client, make_flag):
    make_flag()
    response = client.patch(
        "/api/v1/flags/new-checkout",
        json={"rollout_percentage": 40, "targeted_users": ["a", "a", " b ", ""]},
    )
    body = response.json()
    assert response.status_code == 200
    assert body["rollout_percentage"] == 40
    assert body["targeted_users"] == ["a", "b"]
    assert body["version"] == 2


def test_noop_update_does_not_bump_version(client, make_flag):
    make_flag(rollout_percentage=10)
    body = client.patch("/api/v1/flags/new-checkout", json={"rollout_percentage": 10}).json()
    assert body["version"] == 1


def test_toggle(client, make_flag):
    make_flag(enabled=False)
    body = client.post("/api/v1/flags/new-checkout/toggle").json()
    assert body["enabled"] is True
    assert body["version"] == 2


def test_delete(client, make_flag):
    make_flag()
    assert client.delete("/api/v1/flags/new-checkout").status_code == 204
    assert client.get("/api/v1/flags/new-checkout").status_code == 404


def test_unknown_flag_404(client):
    assert client.get("/api/v1/flags/nope").status_code == 404
    assert client.patch("/api/v1/flags/nope", json={"enabled": True}).status_code == 404


def test_audit_trail_records_every_change(client, make_flag):
    make_flag()
    client.post("/api/v1/flags/new-checkout/toggle")
    client.patch("/api/v1/flags/new-checkout", json={"rollout_percentage": 50})
    client.delete("/api/v1/flags/new-checkout")

    events = client.get("/api/v1/audit", params={"flag_key": "new-checkout"}).json()
    assert [e["action"] for e in events] == ["deleted", "updated", "toggled", "created"]
    assert events[1]["details"]["changes"]["rollout_percentage"] == {"from": 0, "to": 50}


def test_health(client):
    body = client.get("/health").json()
    assert body == {"status": "ok", "database": True, "redis": True}
