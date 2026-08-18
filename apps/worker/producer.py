"""Synthetic Kafka event producer for the full local FraudWatch streaming lab."""

from __future__ import annotations

from datetime import UTC, datetime
from os import getenv
from time import sleep
from uuid import uuid4

from .kafka import publish_transaction
from .models import TransactionEvent


def synthetic_event(sequence: int) -> TransactionEvent:
    """Emit rotating safe scenarios: allow, review, and block without personal data."""
    scenario = sequence % 3
    if scenario == 0:
        amount, country, new_device = 38.75, "US", False
    elif scenario == 1:
        amount, country, new_device = 890.0, "CA", True
    else:
        amount, country, new_device = 2_400.0, "BR", True
    return TransactionEvent(
        event_id=f"synthetic-{uuid4().hex[:20]}",
        account_token=f"demo-account-{sequence % 4}",
        amount_usd=amount,
        merchant_category="online_retail",
        country=country,
        home_country="US",
        new_device=new_device,
        occurred_at=datetime.now(UTC),
    )


def main() -> None:
    bootstrap_servers = getenv("FRAUDWATCH_KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    interval_seconds = float(getenv("FRAUDWATCH_PRODUCER_INTERVAL_SECONDS", "2"))
    sequence = 0
    while True:
        publish_transaction(bootstrap_servers, synthetic_event(sequence))
        sequence += 1
        sleep(interval_seconds)


if __name__ == "__main__":
    main()
