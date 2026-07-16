"""Smoke test confirming the FastAPI app boots and responds.

This is intentionally the first test in the repository: it exists to
verify the M0 foundation (app factory, settings, logging) is wired
correctly before any real feature work begins.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok() -> None:
    """`/health` should report status ok and the current environment."""
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] in {"development", "production", "test"}
