from typing import Any

from app.cache import MISSING, FlagCache
from app.exceptions import FlagNotFoundError
from app.repositories.flag_repository import FlagRepository
from app.schemas import BatchEvaluationResult, EvaluationResult
from app.services.engine import evaluate_flag


class EvaluationService:
    """The hot path. Lookup order:

    1. per-user evaluation cache  (hit -> return immediately)
    2. flag-definition cache      (hit -> skip PostgreSQL)
    3. PostgreSQL                 (on double miss, repopulate the cache)
    4. compute MD5 rollout bucket and cache the result for next time
    """

    def __init__(self, repo: FlagRepository, cache: FlagCache) -> None:
        self.repo = repo
        self.cache = cache

    def _load_snapshot(self, flag_key: str) -> dict:
        cached = self.cache.get_flag(flag_key)
        if cached is MISSING:
            raise FlagNotFoundError(flag_key)
        if cached is not None:
            return cached

        flag = self.repo.get_by_key(flag_key)
        if flag is None:
            self.cache.set_missing(flag_key)
            raise FlagNotFoundError(flag_key)

        snapshot = flag.snapshot()
        self.cache.set_flag(snapshot)
        return snapshot

    def evaluate(
        self, flag_key: str, user_id: str, attributes: dict[str, Any] | None = None
    ) -> EvaluationResult:
        attributes = attributes or {}
        attr_hash = self.cache.attributes_hash(attributes)

        version = self.cache.get_version(flag_key)
        if version is not None:
            hit = self.cache.get_eval(flag_key, version, user_id, attr_hash)
            if hit is not None:
                return EvaluationResult(**hit, cached=True)

        snapshot = self._load_snapshot(flag_key)
        result = evaluate_flag(snapshot, user_id, attributes)
        self.cache.set_eval(flag_key, snapshot["version"], user_id, attr_hash, result)
        return EvaluationResult(**result, cached=False)

    def evaluate_many(
        self, flag_keys: list[str], user_id: str, attributes: dict[str, Any] | None = None
    ) -> BatchEvaluationResult:
        results, missing = [], []
        for key in dict.fromkeys(flag_keys):
            try:
                results.append(self.evaluate(key, user_id, attributes))
            except FlagNotFoundError:
                missing.append(key)
        return BatchEvaluationResult(user_id=user_id, results=results, missing=missing)
