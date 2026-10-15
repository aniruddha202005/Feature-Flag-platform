from app.cache import MISSING


def snapshot(version):
    return {
        "key": "new-checkout",
        "enabled": True,
        "rollout_percentage": 10,
        "targeted_users": [],
        "rules": [],
        "version": version,
    }


def test_stale_snapshot_does_not_overwrite_newer_version(cache):
    cache.invalidate("new-checkout", 3)
    cache.set_flag(snapshot(2))
    assert cache.get_flag("new-checkout") is None
    assert cache.get_version("new-checkout") == 3


def test_current_snapshot_is_cached(cache):
    cache.set_flag(snapshot(1))
    assert cache.get_flag("new-checkout")["version"] == 1
    assert cache.get_version("new-checkout") == 1


def test_eval_keys_are_versioned(cache):
    cache.set_eval("new-checkout", 1, "u", "-", {"enabled": True})
    assert cache.get_eval("new-checkout", 1, "u", "-") == {"enabled": True}
    assert cache.get_eval("new-checkout", 2, "u", "-") is None


def test_negative_cache_cleared_by_invalidate(cache):
    cache.set_missing("new-checkout")
    assert cache.get_flag("new-checkout") is MISSING
    cache.invalidate("new-checkout", 1)
    assert cache.get_flag("new-checkout") is None


def test_attributes_hash_is_order_independent(cache):
    assert cache.attributes_hash({"a": 1, "b": 2}) == cache.attributes_hash({"b": 2, "a": 1})
    assert cache.attributes_hash({}) == "-"
