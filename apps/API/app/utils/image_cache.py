"""
In-memory cache for original image bytes and metadata per job.

This cache stores:
- Original image bytes (keyed by job_id)
- Image metadata (dimensions, content_type, size_bytes)
"""
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger("media_promo_localizer")


class ImageCache:
    """In-memory cache for job images and metadata."""

    def __init__(self):
        """Initialize image cache."""
        self._images: Dict[str, bytes] = {}  # job_id -> image_bytes
        self._metadata: Dict[str, Dict] = {}  # job_id -> {width, height, content_type, size_bytes}

    def store_image(
        self,
        job_id: str,
        image_bytes: bytes,
        width: int,
        height: int,
        content_type: Optional[str] = None,
    ) -> None:
        """
        Store image bytes and metadata for a job.

        Args:
            job_id: Job identifier
            image_bytes: Original image bytes
            width: Image width in pixels
            height: Image height in pixels
            content_type: MIME type (optional)
        """
        self._images[job_id] = image_bytes
        self._metadata[job_id] = {
            "width": width,
            "height": height,
            "content_type": content_type,
            "size_bytes": len(image_bytes),
        }
        logger.debug(f"ImageCache stored image for job={job_id} size_bytes={len(image_bytes)} dims={width}x{height}")

    def get_image(self, job_id: str) -> Optional[bytes]:
        """
        Get original image bytes for a job.

        Args:
            job_id: Job identifier

        Returns:
            Image bytes if found, None otherwise
        """
        return self._images.get(job_id)

    def get_metadata(self, job_id: str) -> Optional[Dict]:
        """
        Get image metadata for a job.

        Args:
            job_id: Job identifier

        Returns:
            Metadata dict if found, None otherwise
        """
        return self._metadata.get(job_id)

    def remove(self, job_id: str) -> None:
        """
        Remove image and metadata for a job.

        Args:
            job_id: Job identifier
        """
        self._images.pop(job_id, None)
        self._metadata.pop(job_id, None)
        logger.debug(f"ImageCache removed image for job={job_id}")


# Global singleton instance
_image_cache: Optional[ImageCache] = None


def get_image_cache() -> ImageCache:
    """Get the global image cache instance."""
    global _image_cache
    if _image_cache is None:
        _image_cache = ImageCache()
    return _image_cache
