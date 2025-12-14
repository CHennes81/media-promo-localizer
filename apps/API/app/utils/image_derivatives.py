"""
Image derivative utilities for generating downscaled images for pipeline steps.

This module provides functions to:
- Get image dimensions
- Resize images to a target long side
- Generate derivatives only when needed
"""
import logging
from io import BytesIO
from typing import Optional, Tuple

from PIL import Image

logger = logging.getLogger("media_promo_localizer")


def get_image_dimensions(image_bytes: bytes) -> Tuple[int, int]:
    """
    Get image dimensions from image bytes.

    Args:
        image_bytes: Image file bytes

    Returns:
        Tuple of (width, height) in pixels

    Raises:
        ValueError: If image cannot be decoded
    """
    try:
        image = Image.open(BytesIO(image_bytes))
        return image.size  # Returns (width, height)
    except Exception as e:
        raise ValueError(f"Failed to decode image: {e}")


def resize_image_long_side(
    image_bytes: bytes,
    long_side_px: int,
    format: str = "JPEG",
    quality: int = 90,
) -> bytes:
    """
    Resize image to a target long side while preserving aspect ratio.

    Args:
        image_bytes: Source image bytes
        long_side_px: Target long side length in pixels
        format: Output format ("JPEG", "PNG", etc.)
        quality: JPEG quality (1-100, ignored for PNG)

    Returns:
        Resized image bytes

    Raises:
        ValueError: If image cannot be decoded or resized
    """
    try:
        image = Image.open(BytesIO(image_bytes))
        original_width, original_height = image.size
        original_long_side = max(original_width, original_height)

        # If image is already smaller or equal, return original
        if original_long_side <= long_side_px:
            return image_bytes

        # Calculate new dimensions preserving aspect ratio
        if original_width >= original_height:
            new_width = long_side_px
            new_height = int(original_height * (long_side_px / original_width))
        else:
            new_height = long_side_px
            new_width = int(original_width * (long_side_px / original_height))

        # Resize image
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Convert to RGB if needed (for JPEG)
        if format == "JPEG" and resized_image.mode in ("RGBA", "LA", "P"):
            # Create white background for transparency
            rgb_image = Image.new("RGB", resized_image.size, (255, 255, 255))
            if resized_image.mode == "P":
                resized_image = resized_image.convert("RGBA")
            rgb_image.paste(resized_image, mask=resized_image.split()[-1] if resized_image.mode == "RGBA" else None)
            resized_image = rgb_image
        elif format == "JPEG" and resized_image.mode != "RGB":
            resized_image = resized_image.convert("RGB")

        # Save to bytes
        output = BytesIO()
        save_kwargs = {"format": format}
        if format == "JPEG":
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True
        resized_image.save(output, **save_kwargs)
        return output.getvalue()

    except Exception as e:
        raise ValueError(f"Failed to resize image: {e}")


def maybe_make_derivative(
    image_bytes: bytes,
    target_long_side_px: int,
    format: str = "JPEG",
    quality: int = 90,
) -> bytes:
    """
    Generate a derivative image if the source exceeds target long side, otherwise return original.

    Args:
        image_bytes: Source image bytes
        target_long_side_px: Target long side length in pixels
        format: Output format ("JPEG", "PNG", etc.)
        quality: JPEG quality (1-100, ignored for PNG)

    Returns:
        Derivative bytes if resized, or original bytes if no resize needed
    """
    try:
        width, height = get_image_dimensions(image_bytes)
        long_side = max(width, height)

        if long_side <= target_long_side_px:
            return image_bytes

        return resize_image_long_side(image_bytes, target_long_side_px, format, quality)
    except Exception as e:
        logger.warning(f"Failed to check/make derivative, using original: {e}")
        return image_bytes
