from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Operator = Literal["equals", "not_equals", "in", "not_in", "gt", "lt"]
AttributeValue = str | int | float | bool

FLAG_KEY_PATTERN = r"^[a-z0-9][a-z0-9_-]{1,99}$"


class Rule(BaseModel):
    attribute: str = Field(min_length=1, max_length=100)
    operator: Operator
    values: list[str] = Field(min_length=1)


class FlagBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    enabled: bool = False
    rollout_percentage: int = Field(default=0, ge=0, le=100)
    targeted_users: list[str] = Field(default_factory=list)
    rules: list[Rule] = Field(default_factory=list)

    @field_validator("targeted_users")
    @classmethod
    def dedupe_users(cls, users: list[str]) -> list[str]:
        cleaned = [u.strip() for u in users if u and u.strip()]
        return list(dict.fromkeys(cleaned))


class FlagCreate(FlagBase):
    key: str = Field(pattern=FLAG_KEY_PATTERN)


class FlagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    enabled: bool | None = None
    rollout_percentage: int | None = Field(default=None, ge=0, le=100)
    targeted_users: list[str] | None = None
    rules: list[Rule] | None = None

    @field_validator("targeted_users")
    @classmethod
    def dedupe_users(cls, users: list[str] | None) -> list[str] | None:
        if users is None:
            return None
        cleaned = [u.strip() for u in users if u and u.strip()]
        return list(dict.fromkeys(cleaned))


class FlagOut(FlagBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    version: int
    created_at: datetime
    updated_at: datetime


class EvaluateRequest(BaseModel):
    flag_key: str = Field(min_length=1)
    user_id: str = Field(min_length=1, max_length=200)
    attributes: dict[str, AttributeValue] = Field(default_factory=dict)


class BatchEvaluateRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)
    flag_keys: list[str] = Field(min_length=1, max_length=100)
    attributes: dict[str, AttributeValue] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    flag_key: str
    user_id: str
    enabled: bool
    reason: Literal["FLAG_DISABLED", "TARGETED_USER", "RULE_MATCH", "ROLLOUT_INCLUDED", "ROLLOUT_EXCLUDED"]
    bucket: int | None = None
    flag_version: int
    cached: bool = False


class BatchEvaluationResult(BaseModel):
    user_id: str
    results: list[EvaluationResult]
    missing: list[str]


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    flag_key: str
    action: str
    details: dict
    created_at: datetime


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    database: bool
    redis: bool
