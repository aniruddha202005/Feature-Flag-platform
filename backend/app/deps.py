from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.cache import FlagCache
from app.config import settings
from app.db import get_db
from app.repositories.flag_repository import FlagRepository
from app.services.evaluation_service import EvaluationService
from app.services.flag_service import FlagService


@lru_cache
def get_cache() -> FlagCache:
    return FlagCache.from_url(
        settings.redis_url,
        socket_timeout=settings.redis_socket_timeout_seconds,
        flag_ttl=settings.flag_cache_ttl_seconds,
        eval_ttl=settings.eval_cache_ttl_seconds,
        negative_ttl=settings.negative_cache_ttl_seconds,
        cooldown_seconds=settings.redis_cooldown_seconds,
    )


def get_repository(db: Session = Depends(get_db)) -> FlagRepository:
    return FlagRepository(db)


def get_flag_service(
    repo: FlagRepository = Depends(get_repository),
    cache: FlagCache = Depends(get_cache),
) -> FlagService:
    return FlagService(repo, cache)


def get_evaluation_service(
    repo: FlagRepository = Depends(get_repository),
    cache: FlagCache = Depends(get_cache),
) -> EvaluationService:
    return EvaluationService(repo, cache)
