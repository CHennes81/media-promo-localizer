"""
Tests for request logging middleware.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_request_middleware_adds_request_id(client):
    """Test that middleware adds X-Request-Id header to response."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-Id" in response.headers
    assert response.headers["X-Request-Id"] is not None
    assert len(response.headers["X-Request-Id"]) > 0


def test_request_middleware_preserves_existing_request_id(client):
    """Test that middleware preserves existing X-Request-Id header."""
    custom_request_id = "custom-request-123"
    response = client.get("/health", headers={"X-Request-Id": custom_request_id})
    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == custom_request_id


def test_request_middleware_logs_request(client, caplog):
    """Test that middleware logs request start and end."""
    import logging

    with caplog.at_level(logging.INFO):
        response = client.get("/health")
        assert response.status_code == 200

        # Check that request logs were emitted
        log_messages = [record.message for record in caplog.records]
        request_start_logs = [msg for msg in log_messages if "RequestStart" in msg]
        request_end_logs = [msg for msg in log_messages if "RequestEnd" in msg]

        assert len(request_start_logs) > 0
        assert len(request_end_logs) > 0

        # Verify log format includes required fields
        start_log = request_start_logs[0]
        assert "method=" in start_log
        assert "path=" in start_log
        assert "request=" in start_log

        end_log = request_end_logs[0]
        assert "status=" in end_log
        assert "durationMs=" in end_log


def test_request_middleware_logs_error(client, caplog):
    """Test that middleware logs errors correctly."""
    import logging

    with caplog.at_level(logging.ERROR):
        # Make a request that will fail (invalid endpoint)
        response = client.get("/nonexistent")
        assert response.status_code == 404

        # Check that error was logged
        log_messages = [record.message for record in caplog.records]
        error_logs = [msg for msg in log_messages if "RequestError" in msg or "RequestEnd" in msg]

        # Should have RequestEnd log even for errors
        assert len([msg for msg in error_logs if "RequestEnd" in msg]) > 0
