"""Typed synthetic-event and decision contracts for FraudWatch."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class DecisionAction(StrEnum):
    ALLOW = "allow"
    REVIEW = "review"
    BLOCK = "block"


class TransactionEvent(BaseModel):
    """A deliberately synthetic payment-shaped event with no personal or card data."""

    event_id: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    account_token: str = Field(min_length=4, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    amount_usd: float = Field(gt=0, le=100_000)
    merchant_category: str = Field(min_length=2, max_length=48, pattern=r"^[a-z_]+$")
    country: str = Field(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    home_country: str = Field(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    new_device: bool = False
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("occurred_at must include a timezone")
        return value.astimezone(UTC)


class Decision(BaseModel):
    event_id: str
    action: DecisionAction
    score: int = Field(ge=0, le=100)
    rules: list[str]
    velocity_count_5m: int = Field(ge=1)
    latency_ms: float = Field(ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class InvestigationCase(BaseModel):
    case_id: str
    event_id: str
    status: str = "open"
    priority: str
    score: int
    rules: list[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AuditRecord(BaseModel):
    sequence: int
    event_id: str
    action: DecisionAction
    detail: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Overview(BaseModel):
    processed_events: int
    duplicate_events: int
    decisions: dict[str, int]
    open_cases: int
    avg_latency_ms: float
    recent_decisions: list[Decision]
