# FraudWatch — Real-Time Fraud Detection Pipeline

FraudWatch is a **synthetic-data streaming lab** that demonstrates the engineering patterns behind low-latency financial-risk decisions without processing cardholder data, personal data, or real transactions.

> **Safety boundary:** this is a portfolio project, not a production fraud model. Every event is generated locally and every decision is an explainable, reviewable rule outcome. No payment is accepted, declined, or altered.

## What it demonstrates

| Area | Implementation |
|---|---|
| Event streaming | Kafka topics for immutable transaction and decision events, consumer-group processing, and manual commit after persistence. |
| Low-latency decisioning | Python stateful risk engine with explicit rule scores, Prometheus latency histograms, and decision-action counters. |
| Stateful features | Redis sorted sets retain a five-minute synthetic-event velocity window per opaque account token. |
| Reliable outcomes | Event-ID idempotency check, PostgreSQL decision records, investigation cases, and audit events. |
| Analyst workflow | React dashboard with decision distribution, risk explanations, investigation queue, and safe event seeding in local demo mode. |
| Monitoring | Prometheus scrape configuration and an automatically provisioned Grafana dashboard. |

## Architecture

```text
Synthetic producer → Kafka fraud.transactions.v1 → Python risk worker
                                                ├→ Redis velocity feature
                                                ├→ PostgreSQL decisions / cases / audit records
                                                ├→ Kafka fraud.decisions.v1
                                                └→ Prometheus metrics → Grafana

React analyst workspace → FastAPI read API → PostgreSQL / metrics
```

The detailed design, rules, data boundaries, and failure handling are in [docs/architecture.md](docs/architecture.md).

## Local demonstration

### Deterministic test mode — no containers required

```bash
pip install -e ".[dev]"
uvicorn apps.api.main:app --port 4200

# separate terminal
cd apps/web && npm install && npm run dev -- --port 5176
```

The dashboard’s **Seed safe event batch** control executes only against the local in-memory risk engine. It is explicitly separate from Kafka mode.

### Full Kafka topology

```bash
docker compose up --build
```

| Endpoint | Purpose |
|---|---|
| `http://localhost:5176` | React analyst workspace |
| `http://localhost:4200/docs` | FastAPI API documentation |
| `http://localhost:9090` | Prometheus targets and query interface |
| `http://localhost:3001` | Grafana (`analyst` / `analyst-demo-only`) |

Use demo credentials only on an isolated local machine. Production configuration must use secret management, TLS/SASL for Kafka, managed database identities, encryption at rest, authenticated dashboards, and a validated model-governance process.

## Decision model

FraudWatch deliberately uses deterministic, inspectable rules:

| Signal | Example | Effect |
|---|---|---|
| High amount | Synthetic amount ≥ $1,500 | Raises score |
| Country deviation | Transaction country differs from opaque account home-country field | Raises score |
| New device | Synthetic device novelty flag | Raises score |
| Five-minute velocity | Repeated events for the same opaque account token | Raises score and may create a review case |

`allow`, `review`, and `block` are **lab outcomes**, not real payment decisions. Every non-allow outcome creates a case record with the contributing rule codes.

## Quality checks

```bash
ruff check .
pytest -q
cd apps/web && npm run lint && npm test -- --run && npm run build
```

GitHub Actions repeats these checks on pull requests and pushes to `main`.
