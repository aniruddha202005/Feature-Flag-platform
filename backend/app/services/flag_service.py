from sqlalchemy.exc import IntegrityError

from app.cache import FlagCache
from app.exceptions import FlagAlreadyExistsError, FlagNotFoundError
from app.models import AuditEvent, Flag
from app.repositories.flag_repository import FlagRepository
from app.schemas import FlagCreate, FlagUpdate


class FlagService:
    """Admin operations. Every write bumps the flag version, commits, then
    invalidates the cache so the hot path never serves a stale definition."""

    def __init__(self, repo: FlagRepository, cache: FlagCache) -> None:
        self.repo = repo
        self.cache = cache

    def list_flags(self) -> list[Flag]:
        return self.repo.list_all()

    def get_flag(self, key: str) -> Flag:
        flag = self.repo.get_by_key(key)
        if flag is None:
            raise FlagNotFoundError(key)
        return flag

    def create_flag(self, data: FlagCreate) -> Flag:
        if self.repo.get_by_key(data.key) is not None:
            raise FlagAlreadyExistsError(data.key)
        flag = Flag(
            key=data.key,
            name=data.name,
            description=data.description,
            enabled=data.enabled,
            rollout_percentage=data.rollout_percentage,
            targeted_users=data.targeted_users,
            rules=[r.model_dump() for r in data.rules],
            version=1,
        )
        try:
            self.repo.add(flag)
            self.repo.add_audit(flag.key, "created", flag.snapshot())
            self.repo.commit()
        except IntegrityError as exc:
            self.repo.rollback()
            raise FlagAlreadyExistsError(data.key) from exc
        self.cache.invalidate(flag.key, flag.version)
        return flag

    def update_flag(self, key: str, data: FlagUpdate) -> Flag:
        flag = self.get_flag(key)
        changes = data.model_dump(exclude_unset=True)
        if "rules" in changes and data.rules is not None:
            changes["rules"] = [r.model_dump() for r in data.rules]

        diff = {}
        for field, new_value in changes.items():
            if new_value is None:
                continue
            old_value = getattr(flag, field)
            if old_value != new_value:
                diff[field] = {"from": old_value, "to": new_value}
                setattr(flag, field, new_value)

        if not diff:
            return flag

        flag.version += 1
        self.repo.add_audit(flag.key, "updated", {"changes": diff, "version": flag.version})
        self.repo.commit()
        self.cache.invalidate(flag.key, flag.version)
        return flag

    def toggle_flag(self, key: str) -> Flag:
        flag = self.get_flag(key)
        flag.enabled = not flag.enabled
        flag.version += 1
        self.repo.add_audit(flag.key, "toggled", {"enabled": flag.enabled, "version": flag.version})
        self.repo.commit()
        self.cache.invalidate(flag.key, flag.version)
        return flag

    def delete_flag(self, key: str) -> None:
        flag = self.get_flag(key)
        self.repo.delete(flag)
        self.repo.add_audit(key, "deleted", {"version": flag.version})
        self.repo.commit()
        self.cache.invalidate(key, None)

    def list_audit(self, flag_key: str | None, limit: int) -> list[AuditEvent]:
        return self.repo.list_audit(flag_key, limit)
