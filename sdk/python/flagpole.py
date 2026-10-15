"""Minimal, dependency-free Python SDK for the Feature Flag Platform.

    from flagpole import FlagClient

    flags = FlagClient("http://localhost:8000")
    if flags.is_enabled("new-checkout", user_id="user_42", attributes={"country": "IN"}):
        show_new_checkout()

Design choices:
  * fail safe: any network/server error returns the caller's default instead of raising
  * short local TTL cache so a tight loop doesn't hammer the API
"""

import json
import time
import urllib.error
import urllib.request
from typing import Any


class FlagClient:
    def __init__(self, base_url: str, timeout: float = 0.5, local_ttl: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.local_ttl = local_ttl
        self._cache: dict[tuple, tuple[float, bool]] = {}

    def is_enabled(
        self,
        flag_key: str,
        user_id: str,
        attributes: dict[str, Any] | None = None,
        default: bool = False,
    ) -> bool:
        attributes = attributes or {}
        cache_key = (flag_key, user_id, json.dumps(attributes, sort_keys=True))
        cached = self._cache.get(cache_key)
        if cached and cached[0] > time.monotonic():
            return cached[1]

        body = json.dumps({"flag_key": flag_key, "user_id": user_id, "attributes": attributes})
        request = urllib.request.Request(
            f"{self.base_url}/api/v1/evaluate",
            data=body.encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                enabled = bool(json.load(response)["enabled"])
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError):
            return default

        self._cache[cache_key] = (time.monotonic() + self.local_ttl, enabled)
        return enabled


if __name__ == "__main__":
    client = FlagClient("http://localhost:8000")
    for user in ["user_1", "user_2", "user_3", "qa_team_1"]:
        print(user, client.is_enabled("new-checkout", user))
