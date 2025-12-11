"""
Tests for health check endpoint.
"""
import time


def test_health_check_via_client(client):
    """Test health check endpoint via test client."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "uptimeSeconds" in data
    assert isinstance(data["uptimeSeconds"], int)
    assert data["uptimeSeconds"] >= 0
    assert data["version"] == "0.2.0"


def test_health_check_uptime_increases(client):
    """Test that uptime increases over time."""
    response1 = client.get("/health")
    time.sleep(1)
    response2 = client.get("/health")

    data1 = response1.json()
    data2 = response2.json()

    assert data2["uptimeSeconds"] >= data1["uptimeSeconds"]


