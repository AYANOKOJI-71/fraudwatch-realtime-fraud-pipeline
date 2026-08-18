"""Kafka boundary for the full streaming lab; not required by deterministic test mode."""

from __future__ import annotations

from collections.abc import Callable

from confluent_kafka import Consumer, Producer

from .models import Decision, TransactionEvent

TRANSACTION_TOPIC = "fraud.transactions.v1"
DECISION_TOPIC = "fraud.decisions.v1"


class KafkaFraudWorker:
    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        handler: Callable[[TransactionEvent], tuple[Decision, bool]],
    ) -> None:
        self.consumer = Consumer(
            {
                "bootstrap.servers": bootstrap_servers,
                "group.id": group_id,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        self.producer = Producer({"bootstrap.servers": bootstrap_servers})
        self.handler = handler

    def run_once(self, timeout_seconds: float = 1.0) -> bool:
        self.consumer.subscribe([TRANSACTION_TOPIC])
        message = self.consumer.poll(timeout_seconds)
        if message is None:
            return False
        if message.error():
            raise RuntimeError(message.error().str())
        event = TransactionEvent.model_validate_json(message.value())
        decision, _duplicate = self.handler(event)
        self.producer.produce(DECISION_TOPIC, decision.model_dump_json().encode(), key=event.event_id)
        self.producer.flush()
        self.consumer.commit(message=message, asynchronous=False)
        return True


def publish_transaction(bootstrap_servers: str, event: TransactionEvent) -> None:
    producer = Producer({"bootstrap.servers": bootstrap_servers})
    producer.produce(TRANSACTION_TOPIC, event.model_dump_json().encode(), key=event.event_id)
    producer.flush()
