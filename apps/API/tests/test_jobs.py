"""
Tests for localization job endpoints.
"""
import time

import pytest


def test_create_job_success(client, sample_image_jpeg):
    """Test successful job creation."""
    response = client.post(
        "/v1/localization-jobs",
        files={"file": ("poster.jpg", sample_image_jpeg, "image/jpeg")},
        data={"targetLanguage": "es-MX"},
    )

    assert response.status_code == 202
    data = response.json()
    assert "jobId" in data
    assert data["status"] in ["queued", "processing"]
    assert "createdAt" in data
    assert data["jobId"].startswith("loc_")


def test_create_job_missing_target_language(client, sample_image_jpeg):
    """Test job creation fails when targetLanguage is missing."""
    response = client.post(
        "/v1/localization-jobs",
        files={"file": ("poster.jpg", sample_image_jpeg, "image/jpeg")},
    )

    assert response.status_code == 422  # FastAPI validation error


def test_create_job_invalid_mime_type(client):
    """Test job creation fails with unsupported file type."""
    response = client.post(
        "/v1/localization-jobs",
        files={"file": ("document.pdf", b"fake pdf content", "application/pdf")},
        data={"targetLanguage": "es-MX"},
    )

    assert response.status_code == 415
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_create_job_png_success(client, sample_image_png):
    """Test successful job creation with PNG."""
    response = client.post(
        "/v1/localization-jobs",
        files={"file": ("poster.png", sample_image_png, "image/png")},
        data={"targetLanguage": "fr-FR"},
    )

    assert response.status_code == 202
    data = response.json()
    assert "jobId" in data
    assert data["status"] in ["queued", "processing"]


def test_get_job_not_found(client):
    """Test getting a non-existent job returns 404."""
    response = client.get("/v1/localization-jobs/nonexistent_job_id")

    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"


def test_get_job_success_after_creation(client, sample_image_jpeg):
    """Test getting a job after creation."""
    # Create job
    create_response = client.post(
        "/v1/localization-jobs",
        files={"file": ("poster.jpg", sample_image_jpeg, "image/jpeg")},
        data={"targetLanguage": "es-MX"},
    )
    assert create_response.status_code == 202
    create_data = create_response.json()
    job_id = create_data["jobId"]

    # Verify jobId is properly formatted
    assert job_id.startswith("loc_")
    assert len(job_id) > 10

    # Get job immediately (should return 200, not 404)
    get_response = client.get(f"/v1/localization-jobs/{job_id}")
    assert get_response.status_code == 200, f"Expected 200 but got {get_response.status_code}. JobId: {job_id}"
    data = get_response.json()

    # CRITICAL: Verify the jobId from GET matches the one from CREATE
    assert data["jobId"] == job_id, f"JobId mismatch: created={job_id}, retrieved={data['jobId']}"
    assert data["status"] in ["queued", "processing", "succeeded", "failed"]


def test_get_job_completed(client, sample_image_jpeg):
    """Test getting a completed job returns full result."""
    # Create job
    create_response = client.post(
        "/v1/localization-jobs",
        files={"file": ("poster.jpg", sample_image_jpeg, "image/jpeg")},
        data={"targetLanguage": "es-MX"},
    )
    assert create_response.status_code == 202
    job_id = create_response.json()["jobId"]

    # Poll until completed (with timeout)
    max_wait = 30  # seconds
    start_time = time.time()
    while time.time() - start_time < max_wait:
        get_response = client.get(f"/v1/localization-jobs/{job_id}")
        assert get_response.status_code == 200
        data = get_response.json()

        if data["status"] == "succeeded":
            assert "result" in data
            assert data["result"] is not None
            assert "imageUrl" in data["result"]
            assert "processingTimeMs" in data["result"]
            assert "detectedText" in data["result"]
            # Check that detectedText has normalized bounding boxes
            if data["result"]["detectedText"]:
                for text_item in data["result"]["detectedText"]:
                    assert "boundingBox" in text_item
                    bbox = text_item["boundingBox"]
                    assert len(bbox) == 4
                    assert all(0.0 <= coord <= 1.0 for coord in bbox)
            break
        elif data["status"] == "failed":
            pytest.fail(f"Job failed: {data.get('error')}")

        time.sleep(0.5)

    else:
        pytest.fail("Job did not complete within timeout")


def test_create_job_with_optional_fields(client, sample_image_jpeg):
    """Test job creation with optional sourceLanguage and jobMetadata."""
    import json

    metadata = {"campaign": "test", "assetId": "123"}
    response = client.post(
        "/v1/localization-jobs",
        files={"file": ("poster.jpg", sample_image_jpeg, "image/jpeg")},
        data={
            "targetLanguage": "ja-JP",
            "sourceLanguage": "en-US",
            "jobMetadata": json.dumps(metadata),
        },
    )

    assert response.status_code == 202
    data = response.json()
    assert "jobId" in data


def test_create_job_invalid_metadata_json(client, sample_image_jpeg):
    """Test job creation fails with invalid jobMetadata JSON."""
    response = client.post(
        "/v1/localization-jobs",
        files={"file": ("poster.jpg", sample_image_jpeg, "image/jpeg")},
        data={
            "targetLanguage": "es-MX",
            "jobMetadata": "not valid json{",
        },
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_INPUT"


def test_job_get_returns_created_job(client, sample_image_jpeg):
    """Test that GET immediately after creation returns the same job (no 404).

    This test verifies:
    - Job is stored immediately upon creation
    - GET can retrieve it right away
    - JobId correlation is correct
    """
    # Create job
    create_response = client.post(
        "/v1/localization-jobs",
        files={"file": ("poster.jpg", sample_image_jpeg, "image/jpeg")},
        data={"targetLanguage": "fr-FR"},
    )
    assert create_response.status_code == 202

    create_data = create_response.json()
    created_job_id = create_data["jobId"]
    created_status = create_data["status"]

    # Immediately GET the job (should not 404)
    get_response = client.get(f"/v1/localization-jobs/{created_job_id}")
    assert get_response.status_code == 200, (
        f"GET returned {get_response.status_code} for just-created job {created_job_id}. "
        f"This indicates the job was not stored or was immediately evicted."
    )

    get_data = get_response.json()

    # Verify jobId matches exactly
    assert get_data["jobId"] == created_job_id, (
        f"JobId mismatch: created={created_job_id}, retrieved={get_data['jobId']}"
    )

    # Verify status is consistent
    assert get_data["status"] == created_status or get_data["status"] in ["queued", "processing"], (
        f"Status mismatch: created={created_status}, retrieved={get_data['status']}"
    )



