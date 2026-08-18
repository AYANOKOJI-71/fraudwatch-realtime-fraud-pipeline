"""FastAPI analyst service for synthetic fraud decisions and review queues."""

from __future__ import annotations

from contextlib import asynccontextmanager
from os import getenv

import redis
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from apps.worker.models import Decision, Overview, TransactionEvent
from apps.worker.processor import FraudProcessor
from apps.worker.repository import FraudRepository, InMemoryFraudRepository, PostgresFraudRepository
from apps.worker.velocity import InMemoryVelocityStore, RedisVelocityStore


def create_services() -> tuple[FraudRepository, FraudProcessor]:
    database_url = getenv("FRAUDWATCH_DATABASE_URL")
    redis_url = getenv("FRAUDWATCH_REDIS_URL")
    repository: FraudRepository = PostgresFraudRepository(database_url) if database_url else InMemoryFraudRepository()
    velocity_store = RedisVelocityStore(redis.from_url(redis_url)) if redis_url else InMemoryVelocityStore()
    return repository, FraudProcessor(repository, velocity_store)


@asynccontextmanager
async def lifespan(app: FastAPI):
    repository, processor = create_services()
    app.state.repository = repository
    app.state.processor = processor
    yield


app = FastAPI(title="FraudWatch API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[getenv("FRAUDWATCH_ALLOW_ORIGIN", "http://localhost:5176")],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "streaming-lab" if getenv("FRAUDWATCH_DATABASE_URL") else "synthetic-demo"}


@app.get("/api/overview", response_model=Overview)
def overview() -> Overview:
    return app.state.repository.overview()


@app.get("/api/cases")
def cases() -> list[dict]:
    return [case.model_dump(mode="json") for case in app.state.repository.list_cases()]


@app.get("/api/audit")
def audit() -> list[dict]:
    return [record.model_dump(mode="json") for record in app.state.repository.list_audit()]


@app.post("/api/events", response_model=Decision, status_code=201)
def submit_event(event: TransactionEvent, response: Response) -> Decision:
    decision, duplicate = app.state.processor.process(event)
    response.headers["X-Idempotent-Replay"] = str(duplicate).lower()
    return decision


@app.post("/api/demo/seed", response_model=list[Decision])
def seed_demo() -> list[Decision]:
    samples = [
        {
            "event_id": "demo-allow-001",
            "account_token": "acct-alpha",
            "amount_usd": 42.0,
            "merchant_category": "groceries",
            "country": "US",
            "home_country": "US",
        },
        {
            "event_id": "demo-review-001",
            "account_token": "acct-bravo",
            "amount_usd": 680.0,
            "merchant_category": "electronics",
            "country": "CA",
            "home_country": "US",
            "new_device": True,
        },
        {
            "event_id": "demo-velocity-001",
            "account_token": "acct-charlie",
            "amount_usd": 25.0,
            "merchant_category": "fuel",
            "country": "US",
            "home_country": "US",
        },
        {
            "event_id": "demo-velocity-002",
            "account_token": "acct-charlie",
            "amount_usd": 25.0,
            "merchant_category": "fuel",
            "country": "US",
            "home_country": "US",
        },
        {
            "event_id": "demo-block-001",
            "account_token": "acct-charlie",
            "amount_usd": 1_450.0,
            "merchant_category": "electronics",
            "country": "BR",
            "home_country": "US",
            "new_device": True,
        },
    ]
    results = [app.state.processor.process(TransactionEvent.model_validate(sample))[0] for sample in samples]
    return results


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
