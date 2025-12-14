"""
Geometry helper functions for credits detection.
"""
import math
from typing import Dict, List, Optional, Tuple

from app.models.credits import PointNorm, QuadNorm, RegionGeometry


def bbox_from_quad(quad_norm: QuadNorm) -> List[float]:
    """
    Compute axis-aligned bounding box from normalized quad.

    Args:
        quad_norm: Normalized quadrilateral

    Returns:
        [x1, y1, x2, y2] normalized coordinates
    """
    x_coords = [v.x for v in quad_norm.vertices]
    y_coords = [v.y for v in quad_norm.vertices]
    return [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]


def area_from_bbox(bbox_norm: List[float]) -> float:
    """
    Compute normalized area from bounding box.

    Args:
        bbox_norm: [x1, y1, x2, y2] normalized coordinates

    Returns:
        Normalized area (0.0-1.0)
    """
    if len(bbox_norm) < 4:
        return 0.0
    width = bbox_norm[2] - bbox_norm[0]
    height = bbox_norm[3] - bbox_norm[1]
    return width * height


def height_from_bbox(bbox_norm: List[float]) -> float:
    """
    Compute normalized height from bounding box.

    Args:
        bbox_norm: [x1, y1, x2, y2] normalized coordinates

    Returns:
        Normalized height (0.0-1.0)
    """
    if len(bbox_norm) < 4:
        return 0.0
    return bbox_norm[3] - bbox_norm[1]


def aspect_ratio_from_bbox(bbox_norm: List[float]) -> float:
    """
    Compute aspect ratio (width/height) from bounding box.

    Args:
        bbox_norm: [x1, y1, x2, y2] normalized coordinates

    Returns:
        Aspect ratio (width/height)
    """
    if len(bbox_norm) < 4:
        return 1.0
    width = bbox_norm[2] - bbox_norm[0]
    height = bbox_norm[3] - bbox_norm[1]
    if height == 0:
        return 1.0
    return width / height


def geometry_from_detected_text(region, image_width: int, image_height: int) -> Optional[RegionGeometry]:
    """
    Convert DetectedText region to RegionGeometry.

    Args:
        region: DetectedText with _geometry attribute or boundingBox
        image_width: Image width in pixels
        image_height: Image height in pixels

    Returns:
        RegionGeometry or None if cannot extract
    """
    # Try to get geometry from _geometry attribute (from OCR client)
    if hasattr(region, "_geometry") and region._geometry:
        geom_dict = region._geometry
        quad_vertices = geom_dict.get("quad_norm", [])
        center = geom_dict.get("center_norm", {})
        angle = geom_dict.get("angle_deg", 0.0)

        if quad_vertices and len(quad_vertices) >= 4:
            # Convert dict vertices to PointNorm
            vertices = []
            for v in quad_vertices[:4]:
                if isinstance(v, dict):
                    vertices.append(PointNorm(x=v.get("x", 0.0), y=v.get("y", 0.0)))
                else:
                    vertices.append(PointNorm(x=v[0], y=v[1]))

            quad_norm = QuadNorm(vertices=vertices)
            center_norm = PointNorm(
                x=center.get("x", 0.0) if isinstance(center, dict) else center[0],
                y=center.get("y", 0.0) if isinstance(center, dict) else center[1],
            )
            bbox = bbox_from_quad(quad_norm)

            return RegionGeometry(
                quad_norm=quad_norm,
                center_norm=center_norm,
                angle_deg=float(angle),
                bbox_norm=bbox,
            )

    # Fallback: construct from boundingBox
    if hasattr(region, "boundingBox") and region.boundingBox:
        bbox = region.boundingBox
        if len(bbox) >= 4:
            x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
            # Create axis-aligned quad
            quad_norm = QuadNorm(
                vertices=[
                    PointNorm(x=x1, y=y1),  # TL
                    PointNorm(x=x2, y=y1),  # TR
                    PointNorm(x=x2, y=y2),  # BR
                    PointNorm(x=x1, y=y2),  # BL
                ]
            )
            center_norm = PointNorm(x=(x1 + x2) / 2, y=(y1 + y2) / 2)
            return RegionGeometry(
                quad_norm=quad_norm,
                center_norm=center_norm,
                angle_deg=0.0,
                bbox_norm=[x1, y1, x2, y2],
            )

    return None


def font_height_from_geometry(geometry: RegionGeometry) -> float:
    """
    Estimate font height from geometry (using quad height as proxy).

    Args:
        geometry: RegionGeometry

    Returns:
        Normalized font height estimate
    """
    if geometry.bbox_norm:
        return height_from_bbox(geometry.bbox_norm)
    # Fallback: compute from quad
    y_coords = [v.y for v in geometry.quad_norm.vertices]
    return max(y_coords) - min(y_coords)


def compute_oriented_bbox(
    regions: List, dominant_angle_deg: float, image_width: int, image_height: int
) -> Tuple[QuadNorm, List[float]]:
    """
    Compute oriented bounding box for a set of regions.

    Args:
        regions: List of regions with geometry
        dominant_angle_deg: Dominant rotation angle in degrees
        image_width: Image width in pixels
        image_height: Image height in pixels

    Returns:
        Tuple of (QuadNorm, bbox_norm [x1, y1, x2, y2])
    """
    if not regions:
        # Default bbox
        return (
            QuadNorm(
                vertices=[
                    PointNorm(x=0.0, y=0.0),
                    PointNorm(x=1.0, y=0.0),
                    PointNorm(x=1.0, y=1.0),
                    PointNorm(x=0.0, y=1.0),
                ]
            ),
            [0.0, 0.0, 1.0, 1.0],
        )

    # Collect all vertices from regions
    all_x = []
    all_y = []
    for region in regions:
        geom = geometry_from_detected_text(region, image_width, image_height)
        if geom:
            for v in geom.quad_norm.vertices:
                all_x.append(v.x)
                all_y.append(v.y)

    if not all_x or not all_y:
        # Fallback
        return (
            QuadNorm(
                vertices=[
                    PointNorm(x=0.0, y=0.0),
                    PointNorm(x=1.0, y=0.0),
                    PointNorm(x=1.0, y=1.0),
                    PointNorm(x=0.0, y=1.0),
                ]
            ),
            [0.0, 0.0, 1.0, 1.0],
        )

    # For now, use axis-aligned bbox (per spec note that oriented crop can be approximated)
    x1, y1 = min(all_x), min(all_y)
    x2, y2 = max(all_x), max(all_y)

    # Create axis-aligned quad (will be logged as axis-aligned per spec)
    quad_norm = QuadNorm(
        vertices=[
            PointNorm(x=x1, y=y1),  # TL
            PointNorm(x=x2, y=y1),  # TR
            PointNorm(x=x2, y=y2),  # BR
            PointNorm(x=x1, y=y2),  # BL
        ]
    )

    return quad_norm, [x1, y1, x2, y2]
