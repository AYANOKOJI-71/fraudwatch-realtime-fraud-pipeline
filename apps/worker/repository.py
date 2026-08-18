"""Repository interfaces and deterministic local implementation."""

from __future__ import annotations

from collections import Counter
from typing import Protocol

from psycopg import connect
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .models import AuditRecord, Decision, DecisionAction, InvestigationCase, Overview, TransactionEvent


class FraudRepository(Protocol):
    """Persistence contract shared by deterministic and container streaming modes."""

    def decision_for(self, event_id: str) -> Decision | None: ...
    def save_event(self, event: TransactionEvent) -> None: ...
    def save_decision(self, decision: Decision) -> None: ...
    def save_case(self, case: InvestigationCase) -> None: ...
    def mark_duplicate(self) -> None: ...
    def overview(self) -> Overview: ...
    def list_cases(self) -> list[InvestigationCase]: ...
    def list_audit(self) -> list[AuditRecord]: ...


class InMemoryFraudRepository:
    """Test-mode store that mirrors the intended PostgreSQL persistence contract."""

    def __init__(self) -> None:
        self.events: dict[str, TransactionEvent] = {}
        self.decisions: dict[str, Decision] = {}
        self.cases: dict[str, InvestigationCase] = {}
        self.audit: list[AuditRecord] = []
        self.duplicates = 0

    def decision_for(self, event_id: str) -> Decision | None:
        return self.decisions.get(event_id)

    def save_event(self, event: TransactionEvent) -> None:
        self.events[event.event_id] = event

    def save_decision(self, decision: Decision) -> None:
        self.decisions[decision.event_id] = decision
        self.audit.append(
            AuditRecord(
                sequence=len(self.audit) + 1,
                event_id=decision.event_id,
                action=decision.action,
                detail=f"risk score={decision.score}; rules={','.join(decision.rules) or 'none'}",
            )
        )

    def save_case(self, case: InvestigationCase) -> None:
        self.cases[case.case_id] = case

    def mark_duplicate(self) -> None:
        self.duplicates += 1

    def overview(self) -> Overview:
        distribution = Counter(decision.action.value for decision in self.decisions.values())
        decisions = {action.value: distribution.get(action.value, 0) for action in DecisionAction}
        values = list(self.decisions.values())
        latency = sum(value.latency_ms for value in values) / len(values) if values else 0.0
        recent = sorted(values, key=lambda item: item.created_at, reverse=True)[:12]
        return Overview(
            processed_events=len(self.events),
            duplicate_events=self.duplicates,
            decisions=decisions,
            open_cases=sum(case.status == "open" for case in self.cases.values()),
            avg_latency_ms=round(latency, 3),
            recent_decisions=recent,
        )

    def list_cases(self) -> list[InvestigationCase]:
        return sorted(self.cases.values(), key=lambda item: item.created_at, reverse=True)

    def list_audit(self) -> list[AuditRecord]:
        return self.audit[-30:]


class PostgresFraudRepository:
    """PostgreSQL persistence adapter used by the Kafka and API containers."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.duplicates = 0

    def _connection(self):
        return connect(self.database_url, autocommit=True, row_factory=dict_row)

    def decision_for(self, event_id: str) -> Decision | None:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM fraud_decisions WHERE event_id = %s", (event_id,))
            row = cursor.fetchone()
        if row is None:
            return None
        return Decision(
            event_id=row["event_id"],
            action=row["action"],
            score=row["score"],
            rules=list(row["rule_codes"]),
            velocity_count_5m=row["velocity_count_5m"],
            latency_ms=float(row["latency_ms"]),
            created_at=row["created_at"],
        )

    def save_event(self, event: TransactionEvent) -> None:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO transaction_events
                    (event_id, account_token, amount_usd, merchant_category, country,
                     home_country, new_device, occurred_at)
                VALUES (%(event_id)s, %(account_token)s, %(amount_usd)s, %(merchant_category)s, %(country)s,
                        %(home_country)s, %(new_device)s, %(occurred_at)s)
                ON CONFLICT (event_id) DO NOTHING
                """,
                event.model_dump(),
            )

    def save_decision(self, decision: Decision) -> None:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO fraud_decisions
                    (event_id, action, score, rule_codes, velocity_count_5m, latency_ms, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    decision.event_id,
                    decision.action.value,
                    decision.score,
                    Jsonb(decision.rules),
                    decision.velocity_count_5m,
                    decision.latency_ms,
                    decision.created_at,
                ),
            )
            cursor.execute(
                "INSERT INTO audit_events (event_id, action, detail) VALUES (%s, %s, %s)",
                (
                    decision.event_id,
                    decision.action.value,
                    f"risk score={decision.score}; rules={','.join(decision.rules) or 'none'}",
                ),
            )

    def save_case(self, case: InvestigationCase) -> None:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO investigation_cases (case_id, event_id, status, priority, score, rule_codes, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_id) DO NOTHING
                """,
                (
                    case.case_id,
                    case.event_id,
                    case.status,
                    case.priority,
                    case.score,
                    Jsonb(case.rules),
                    case.created_at,
                ),
            )

    def mark_duplicate(self) -> None:
        self.duplicates += 1

    def overview(self) -> Overview:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM transaction_events")
            processed_events = int(cursor.fetchone()["total"])
            cursor.execute("SELECT action, COUNT(*) AS total FROM fraud_decisions GROUP BY action")
            distribution = {row["action"]: int(row["total"]) for row in cursor.fetchall()}
            cursor.execute("SELECT COUNT(*) AS total FROM investigation_cases WHERE status = 'open'")
            open_cases = int(cursor.fetchone()["total"])
            cursor.execute("SELECT COALESCE(AVG(latency_ms), 0) AS latency FROM fraud_decisions")
            latency = float(cursor.fetchone()["latency"])
            cursor.execute("SELECT * FROM fraud_decisions ORDER BY created_at DESC LIMIT 12")
            recent_rows = cursor.fetchall()
        return Overview(
            processed_events=processed_events,
            duplicate_events=self.duplicates,
            decisions={action.value: distribution.get(action.value, 0) for action in DecisionAction},
            open_cases=open_cases,
            avg_latency_ms=round(latency, 3),
            recent_decisions=[
                Decision(
                    event_id=row["event_id"],
                    action=row["action"],
                    score=row["score"],
                    rules=list(row["rule_codes"]),
                    velocity_count_5m=row["velocity_count_5m"],
                    latency_ms=float(row["latency_ms"]),
                    created_at=row["created_at"],
                )
                for row in recent_rows
            ],
        )

    def list_cases(self) -> list[InvestigationCase]:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM investigation_cases ORDER BY created_at DESC")
            rows = cursor.fetchall()
        return [
            InvestigationCase(
                case_id=row["case_id"], event_id=row["event_id"], status=row["status"], priority=row["priority"],
                score=row["score"], rules=list(row["rule_codes"]), created_at=row["created_at"],
            )
            for row in rows
        ]

    def list_audit(self) -> list[AuditRecord]:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM audit_events ORDER BY sequence DESC LIMIT 30")
            rows = cursor.fetchall()
        return [
            AuditRecord(
                sequence=row["sequence"], event_id=row["event_id"], action=row["action"],
                detail=row["detail"], created_at=row["created_at"],
            )
            for row in rows
        ]
