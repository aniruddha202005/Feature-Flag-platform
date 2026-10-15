import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

import fakeredis  # noqa: E402
import pytest  # noqa: E402
import redis  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.cache import FlagCache  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.deps import get_cache  # noqa: E402
from app.main import app  # noqa: E402


def _make_redis_client():
    url = os.getenv("TEST_REDIS_URL")
    if url:
        client = redis.Redis.from_url(url, decode_responses=True)
        client.flushdb()
        return client
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def cache():
    return FlagCache(_make_redis_client(), cooldown_seconds=0)


@pytest.fixture
def client(cache):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_cache] = lambda: cache
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_flag(client):
    def _make(**overrides):
        payload = {
            "key": "new-checkout",
            "name": "New checkout",
            "enabled": True,
            "rollout_percentage": 0,
        }
        payload.update(overrides)
        response = client.post("/api/v1/flags", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _make
