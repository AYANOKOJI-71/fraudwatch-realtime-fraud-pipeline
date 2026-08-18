from fastapi.testclient import TestClient

from apps.api.main import app


def event(event_id: str = "event-test-001", **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "event_id": event_id,
        "account_token": "acct-test",
        "amount_usd": 65,
        "merchant_category": "groceries",
        "country": "US",
        "home_country": "US",
    }
    payload.update(overrides)
    return payload


def test_low_risk_event_is_allowed() -> None:
    with TestClient(app) as client:
        response = client.post("/api/events", json=event())
        assert response.status_code == 201
        assert response.json()["action"] == "allow"


def test_high_risk_event_opens_case() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/events",
            json=event("event-block-001", amount_usd=2_000, country="BR", new_device=True),
        )
        assert response.json()["action"] == "block"
        cases = client.get("/api/cases").json()
        assert cases[0]["priority"] == "critical"


def test_event_id_is_idempotent() -> None:
    with TestClient(app) as client:
        first = client.post("/api/events", json=event("event-dup-001"))
        replay = client.post("/api/events", json=event("event-dup-001", amount_usd=4_000))
        assert first.json()["score"] == replay.json()["score"]
        assert replay.headers["X-Idempotent-Replay"] == "true"
        assert client.get("/api/overview").json()["duplicate_events"] == 1


def test_velocity_rule_escalates_third_event() -> None:
    with TestClient(app) as client:
        client.post("/api/events", json=event("event-v1", account_token="acct-velocity"))
        client.post("/api/events", json=event("event-v2", account_token="acct-velocity"))
        decision = client.post("/api/events", json=event("event-v3", account_token="acct-velocity"))
        assert decision.json()["action"] == "review"
        assert "velocity_5m" in decision.json()["rules"]
