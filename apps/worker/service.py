"""Kafka worker entrypoint for the full FraudWatch streaming lab."""

from __future__ import annotations

from os import getenv

import redis

from .kafka import KafkaFraudWorker
from .processor import FraudProcessor
from .repository import PostgresFraudRepository
from .velocity import RedisVelocityStore


def main() -> None:
    repository = PostgresFraudRepository(
        getenv("FRAUDWATCH_DATABASE_URL", "postgresql://fraudwatch:fraudwatch@postgres:5432/fraudwatch")
    )
    velocity_store = RedisVelocityStore(redis.from_url(getenv("FRAUDWATCH_REDIS_URL", "redis://redis:6379/0")))
    processor = FraudProcessor(repository, velocity_store)
    worker = KafkaFraudWorker(
        bootstrap_servers=getenv("FRAUDWATCH_KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
        group_id=getenv("FRAUDWATCH_KAFKA_GROUP_ID", "fraudwatch-risk-v1"),
        handler=processor.process,
    )
    while True:
        worker.run_once(timeout_seconds=5.0)


if __name__ == "__main__":
    main()
