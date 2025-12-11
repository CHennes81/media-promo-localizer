"""
Pytest configuration and fixtures.
"""
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def sample_image_jpeg():
    """Create a sample JPEG image for testing."""
    # Create a minimal valid JPEG (1x1 pixel)
    # JPEG header + minimal data
    jpeg_data = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n"
        b"\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d"
        b"\x1a\x1c\x1c $.\' ", b"#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01"
        b"\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14"
        b"\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xaa\xff\xd9"
    )
    return io.BytesIO(b"".join(jpeg_data))


@pytest.fixture
def sample_image_png():
    """Create a sample PNG image for testing."""
    # Create a minimal valid PNG (1x1 pixel, red)
    png_data = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00"
        b"\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return io.BytesIO(png_data)


@pytest.fixture(autouse=True)
def cleanup_uploads():
    """Clean up uploaded files after each test."""
    yield
    # Cleanup happens after test
    uploads_dir = Path("apps/api/tmp/uploads")
    if uploads_dir.exists():
        import shutil

        for job_dir in uploads_dir.iterdir():
            if job_dir.is_dir():
                shutil.rmtree(job_dir, ignore_errors=True)


