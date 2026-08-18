# FraudWatch Validation Record

## Local deterministic demonstration

The FastAPI analyst API and React workspace were run without Kafka, Redis, or PostgreSQL connections, exercising the explicit deterministic test mode rather than implying a live financial integration.

| Check | Result |
|---|---|
| API health | `200 OK` with `mode: synthetic-demo` |
| Synthetic batch | 5 idempotent, safe transaction-shaped events processed |
| Decisions | 3 `allow`, 1 `review`, and 1 `block` |
| Investigation cases | 2 open analyst-review cases created with reason codes |
| Risk explanation | The dashboard rendered score, matched controls, velocity count, and processor latency for the blocked event |
| Observability | Prometheus endpoint exposed latency histogram samples for all processed events |

The dashboard’s event injection uses deterministic synthetic data only. It does not submit payment transactions, access an external payment system, or execute any financial action.

## Automated quality gate

| Layer | Result |
|---|---|
| Python lint | `ruff check .` passed |
| Risk-engine and API tests | 4 tests passed |
| Frontend lint | ESLint passed |
| Frontend tests | 2 tests passed |
| Frontend production build | TypeScript and Vite build passed |

## Container topology

The Docker Compose topology includes Kafka, Kafka initialization, Kafka worker, synthetic Kafka producer, PostgreSQL, Redis, FastAPI, React/nginx, Prometheus, and Grafana.

Docker is not installed in this sandbox, so the Compose services could not be started or validated here. The local deterministic mode and all application quality checks were run successfully. Before using the full topology elsewhere, run `docker compose config --quiet` and `docker compose up --build` on a machine with Docker installed.
