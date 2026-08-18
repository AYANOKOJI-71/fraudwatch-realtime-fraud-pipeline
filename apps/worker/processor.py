"""Idempotent stateful processor used by Kafka and deterministic local modes."""

from __future__ import annotations

from time import perf_counter
from typing import Protocol

from prometheus_client import Counter, Histogram

from .models import Decision, DecisionAction, InvestigationCase, TransactionEvent
from .repository import FraudRepository
from .scoring import evaluate


class VelocityStore(Protocol):
    def record_and_count(self, account_token: str, occurred_at) -> int: ...

DECISIONS_TOTAL = Counter("fraudwatch_decisions_total", "Synthetic fraud decisions", ["action"])
PROCESSING_LATENCY = Histogram("fraudwatch_processing_latency_seconds", "Risk processor decision latency")
DUPLICATES_TOTAL = Counter("fraudwatch_duplicate_events_total", "Duplicate synthetic event messages")


class FraudProcessor:
    def __init__(self, repository: FraudRepository, velocity_store: VelocityStore) -> None:
        self.repository = repository
        self.velocity_store = velocity_store

    def process(self, event: TransactionEvent) -> tuple[Decision, bool]:
        existing = self.repository.decision_for(event.event_id)
        if existing:
            self.repository.mark_duplicate()
            DUPLICATES_TOTAL.inc()
            return existing, True

        started = perf_counter()
        velocity_count = self.velocity_store.record_and_count(event.account_token, event.occurred_at)
        action, score, rules = evaluate(event, velocity_count)
        latency_seconds = perf_counter() - started
        decision = Decision(
            event_id=event.event_id,
            action=action,
            score=score,
            rules=rules,
            velocity_count_5m=velocity_count,
            latency_ms=round(latency_seconds * 1000, 3),
        )
        self.repository.save_event(event)
        self.repository.save_decision(decision)
        if action in {DecisionAction.REVIEW, DecisionAction.BLOCK}:
            priority = "critical" if action == DecisionAction.BLOCK else "high"
            self.repository.save_case(
                InvestigationCase(
                    case_id=f"case-{event.event_id}",
                    event_id=event.event_id,
                    priority=priority,
                    score=score,
                    rules=rules,
                )
            )
        DECISIONS_TOTAL.labels(action=action.value).inc()
        PROCESSING_LATENCY.observe(latency_seconds)
        return decision, False
