from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, Flag


class FlagRepository:
    """The only layer that talks to PostgreSQL."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_key(self, key: str) -> Flag | None:
        return self.db.scalar(select(Flag).where(Flag.key == key))

    def list_all(self) -> list[Flag]:
        return list(self.db.scalars(select(Flag).order_by(Flag.created_at.desc(), Flag.id.desc())))

    def add(self, flag: Flag) -> Flag:
        self.db.add(flag)
        self.db.flush()
        return flag

    def delete(self, flag: Flag) -> None:
        self.db.delete(flag)
        self.db.flush()

    def add_audit(self, flag_key: str, action: str, details: dict) -> None:
        self.db.add(AuditEvent(flag_key=flag_key, action=action, details=details))

    def list_audit(self, flag_key: str | None = None, limit: int = 50) -> list[AuditEvent]:
        stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        if flag_key:
            stmt = stmt.where(AuditEvent.flag_key == flag_key)
        return list(self.db.scalars(stmt.limit(limit)))

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
