"""Redis cache layer for the evaluation hot path.

Key layout
----------
flag:{key}                         -> JSON snapshot of the flag definition
flagver:{key}                      -> current definition version (int)
eval:{key}:v{ver}:{user}:{attrs}   -> JSON evaluation result
flagmiss:{key}                     -> short-lived negative cache for unknown keys

Every evaluation key embeds the flag version. When a flag changes, we bump
flagver; all old evaluation keys become unreachable instantly and simply age
out via TTL. That avoids SCAN + DEL over millions of per-user keys.

Every method fails open: if Redis is slow or down we log, enter a short
cooldown, and let the caller fall through to PostgreSQL rather than erroring.
"""

import hashlib
import json
import logging
import time
from typing import Any

import redis

logger = logging.getLogger(__name__)

MISSING = object()


class FlagCache:
    def __init__(
        self,
        client: redis.Redis,
        flag_ttl: int = 300,
        eval_ttl: int = 60,
        negative_ttl: int = 10,
        cooldown_seconds: float = 5.0,
    ) -> None:
        self.client = client
        self.flag_ttl = flag_ttl
        self.eval_ttl = eval_ttl
        self.negative_ttl = negative_ttl
        self.cooldown_seconds = cooldown_seconds
        self._down_until = 0.0

    @classmethod
    def from_url(cls, url: str, socket_timeout: float = 0.25, **kwargs: Any) -> "FlagCache":
        client = redis.Redis.from_url(
            url,
            decode_responses=True,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_timeout,
        )
        return cls(client, **kwargs)

    @staticmethod
    def attributes_hash(attributes: dict[str, Any]) -> str:
        if not attributes:
            return "-"
        canonical = json.dumps(attributes, sort_keys=True, separators=(",", ":"))
        return hashlib.md5(canonical.encode(), usedforsecurity=False).hexdigest()[:12]

    @staticmethod
    def _flag_key(key: str) -> str:
        return f"flag:{key}"

    @staticmethod
    def _version_key(key: str) -> str:
        return f"flagver:{key}"

    @staticmethod
    def _miss_key(key: str) -> str:
        return f"flagmiss:{key}"

    @staticmethod
    def _eval_key(key: str, version: int, user_id: str, attr_hash: str) -> str:
        return f"eval:{key}:v{version}:{user_id}:{attr_hash}"

    @property
    def available(self) -> bool:
        return time.monotonic() >= self._down_until

    def _mark_down(self, exc: Exception) -> None:
        logger.warning("Redis unavailable, falling back to PostgreSQL: %s", exc)
        self._down_until = time.monotonic() + self.cooldown_seconds

    def ping(self) -> bool:
        try:
            return bool(self.client.ping())
        except redis.RedisError:
            return False

    def get_version(self, key: str) -> int | None:
        if not self.available:
            return None
        try:
            raw = self.client.get(self._version_key(key))
        except redis.RedisError as exc:
            self._mark_down(exc)
            return None
        return int(raw) if raw is not None else None

    def get_eval(self, key: str, version: int, user_id: str, attr_hash: str) -> dict | None:
        if not self.available:
            return None
        try:
            raw = self.client.get(self._eval_key(key, version, user_id, attr_hash))
        except redis.RedisError as exc:
            self._mark_down(exc)
            return None
        return json.loads(raw) if raw else None

    def set_eval(self, key: str, version: int, user_id: str, attr_hash: str, result: dict) -> None:
        if not self.available:
            return
        try:
            self.client.set(
                self._eval_key(key, version, user_id, attr_hash),
                json.dumps(result),
                ex=self.eval_ttl,
            )
        except redis.RedisError as exc:
            self._mark_down(exc)

    def get_flag(self, key: str) -> dict | object | None:
        """Return the cached snapshot, MISSING for a known-absent key, or None on miss."""
        if not self.available:
            return None
        try:
            pipe = self.client.pipeline(transaction=False)
            pipe.get(self._flag_key(key))
            pipe.exists(self._miss_key(key))
            raw, is_missing = pipe.execute()
        except redis.RedisError as exc:
            self._mark_down(exc)
            return None
        if raw:
            return json.loads(raw)
        if is_missing:
            return MISSING
        return None

    def set_flag(self, snapshot: dict) -> None:
        """Cache a snapshot read from PostgreSQL, unless a newer version already exists.

        Without the version guard, a slow reader holding an old snapshot could
        overwrite the cache right after an admin update and serve stale values
        for the whole TTL.
        """
        if not self.available:
            return
        key = snapshot["key"]
        version_key = self._version_key(key)
        try:
            with self.client.pipeline() as pipe:
                pipe.watch(version_key)
                current = pipe.get(version_key)
                if current is not None and int(current) > snapshot["version"]:
                    return
                pipe.multi()
                pipe.set(self._flag_key(key), json.dumps(snapshot), ex=self.flag_ttl)
                pipe.set(version_key, snapshot["version"])
                pipe.execute()
        except redis.WatchError:
            return
        except redis.RedisError as exc:
            self._mark_down(exc)

    def set_missing(self, key: str) -> None:
        if not self.available:
            return
        try:
            self.client.set(self._miss_key(key), "1", ex=self.negative_ttl)
        except redis.RedisError as exc:
            self._mark_down(exc)

    def invalidate(self, key: str, new_version: int | None) -> None:
        """Called after every write. new_version=None means the flag was deleted."""
        try:
            pipe = self.client.pipeline()
            pipe.delete(self._flag_key(key), self._miss_key(key))
            if new_version is None:
                pipe.delete(self._version_key(key))
            else:
                pipe.set(self._version_key(key), new_version)
            pipe.execute()
        except redis.RedisError as exc:
            self._mark_down(exc)
