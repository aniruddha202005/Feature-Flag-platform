"""Measure /evaluate latency on a running server.

Usage: python scripts/benchmark.py [base_url] [requests]

Reports three paths:
  postgres  - Redis flushed before every request, so each call reads PostgreSQL
  def-cache - flag definition cached, per-user result not cached yet
  eval-cache- repeat users, served straight from the per-user cache
"""

import statistics
import sys
import time

import httpx
import redis

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
REDIS_URL = "redis://localhost:6379/0"
FLAG = "bench-flag"


def timed(client: httpx.Client, user: str) -> float:
    start = time.perf_counter()
    response = client.get("/api/v1/evaluate", params={"flag_key": FLAG, "user_id": user})
    elapsed = (time.perf_counter() - start) * 1000
    response.raise_for_status()
    return elapsed


def report(name: str, samples: list[float]) -> None:
    samples.sort()
    p = lambda q: samples[min(len(samples) - 1, int(q * len(samples)))]  # noqa: E731
    print(
        f"{name:<11} n={len(samples):<5} p50={p(0.50):6.2f}ms  p95={p(0.95):6.2f}ms  "
        f"p99={p(0.99):6.2f}ms  mean={statistics.mean(samples):6.2f}ms"
    )


def main() -> None:
    r = redis.Redis.from_url(REDIS_URL)
    with httpx.Client(base_url=BASE_URL, timeout=5) as client:
        client.delete(f"/api/v1/flags/{FLAG}")
        client.post(
            "/api/v1/flags",
            json={"key": FLAG, "name": "Benchmark", "enabled": True, "rollout_percentage": 50},
        ).raise_for_status()

        for i in range(50):
            timed(client, f"warmup_{i}")

        postgres = []
        for i in range(min(N, 300)):
            r.flushdb()
            postgres.append(timed(client, f"pg_{i}"))

        def_cache = [timed(client, f"user_{i}") for i in range(N)]
        eval_cache = [timed(client, f"user_{i}") for i in range(N)]

        client.delete(f"/api/v1/flags/{FLAG}")

    print(f"GET /api/v1/evaluate against {BASE_URL}")
    report("postgres", postgres)
    report("def-cache", def_cache)
    report("eval-cache", eval_cache)


if __name__ == "__main__":
    main()
