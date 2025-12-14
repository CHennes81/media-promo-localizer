"""
Credits block detection and semantic grouping.

Implements two-pass detection:
- Pass 1: Detect and preserve discrete overlay elements (logos, badges, URLs)
- Pass 2: Cluster residual regions into dense credits blocks
- Pass 3: Extract crop and run specialized OCR + grouping
"""
import logging
import math
import statistics
from io import BytesIO
from typing import List, Optional, Tuple

from PIL import Image

from app.models.jobs import DetectedText
from app.models.credits import (
    CreditGroup,
    CreditGroupType,
    CreditLine,
    CreditsBandDetection,
    CreditsBlock,
    CreditsOverlayElement,
    CreditsOverlayType,
    PointNorm,
    QuadNorm,
    RegionGeometry,
)
from app.utils.credits_config import (
    BOTTOM_BAND_Y_MAX,
    BOTTOM_BAND_Y_MIN,
    CREDITS_ANGLE_STD_MAX,
    CREDITS_FONT_HEIGHT_MAX,
    CREDITS_LINE_COUNT_MIN,
    CREDITS_ROLE_ANCHORS,
    OVERLAY_AREA_SMALL,
    OVERLAY_ASPECT_WIDE,
    OVERLAY_HEIGHT_TINY,
    OVER_UNDER_MAX_GAP_Y,
    OVER_UNDER_MIN_X_OVERLAP,
    TOP_LITE_BAND_Y_MAX,
    TOP_LITE_BAND_Y_MIN,
)
from app.utils.credits_geometry import (
    aspect_ratio_from_bbox,
    area_from_bbox,
    font_height_from_geometry,
    geometry_from_detected_text,
    height_from_bbox,
)

logger = logging.getLogger("media_promo_localizer")


def detect_credits_band(
    line_regions: List[DetectedText],
    original_image_bytes: bytes,
    image_width: int,
    image_height: int,
    job_id: Optional[str] = None,
) -> Optional[CreditsBandDetection]:
    """
    Detect credits block in bottom or top band using two-pass approach.

    Args:
        line_regions: List of detected text regions from OCR
        original_image_bytes: Full-resolution original image bytes
        image_width: Image width in pixels
        image_height: Image height in pixels
        job_id: Optional job ID for logging

    Returns:
        CreditsBandDetection or None if no credits block detected
    """
    correlation = f"job={job_id}" if job_id else ""

    # Step A: Select candidate band (bottom first, then top-lite)
    band_name, band_bbox_norm, band_regions = _select_candidate_band(line_regions)

    if not band_regions:
        logger.info(f"CreditsBandSelection {correlation} band={band_name} regions=0 result=no_candidates")
        return None

    logger.info(
        f"CreditsBandSelection {correlation} band={band_name} "
        f"bbox_norm={band_bbox_norm} regions={len(band_regions)}"
    )

    # Step B: Pass 1 - Detect overlays
    logger.info(f"CreditsPass1Start {correlation} band={band_name}")
    overlays, residual_regions = _detect_credits_overlays(
        band_regions, band_bbox_norm, image_width, image_height, job_id
    )

    # Step C: Pass 2 - Cluster and score
    credits_block = None
    if residual_regions:
        logger.info(f"CreditsPass2Start {correlation} residual_regions={len(residual_regions)}")
        credits_block = _detect_credits_block(
            residual_regions, overlays, band_bbox_norm, image_width, image_height, job_id
        )

    # Compute overall confidence
    confidence = credits_block.confidence if credits_block else 0.0

    detection = CreditsBandDetection(
        band_name=band_name,
        band_bbox_norm=band_bbox_norm,
        overlays=overlays,
        credits_block=credits_block,
        confidence=confidence,
        debug={},
    )

    if credits_block:
        logger.info(
            f"CreditsDetectionComplete {correlation} band={band_name} "
            f"overlays={len(overlays)} credits_block_confidence={confidence:.3f}"
        )
    else:
        logger.info(
            f"CreditsDetectionComplete {correlation} band={band_name} "
            f"overlays={len(overlays)} credits_block=None"
        )

    return detection


def _select_candidate_band(
    line_regions: List[DetectedText],
) -> Tuple[str, List[float], List[DetectedText]]:
    """
    Select candidate band (bottom or top-lite) and filter regions.

    Returns:
        Tuple of (band_name, band_bbox_norm, filtered_regions)
    """
    # Try bottom band first
    bottom_regions = [
        r
        for r in line_regions
        if hasattr(r, "boundingBox")
        and len(r.boundingBox) >= 4
        and BOTTOM_BAND_Y_MIN <= r.boundingBox[1] <= BOTTOM_BAND_Y_MAX
    ]

    if bottom_regions:
        return (
            "BOTTOM_BAND",
            [0.0, BOTTOM_BAND_Y_MIN, 1.0, BOTTOM_BAND_Y_MAX],
            bottom_regions,
        )

    # Try top-lite band
    top_regions = [
        r
        for r in line_regions
        if hasattr(r, "boundingBox")
        and len(r.boundingBox) >= 4
        and TOP_LITE_BAND_Y_MIN <= r.boundingBox[1] <= TOP_LITE_BAND_Y_MAX
    ]

    if top_regions:
        return (
            "TOP_LITE_BAND",
            [0.0, TOP_LITE_BAND_Y_MIN, 1.0, TOP_LITE_BAND_Y_MAX],
            top_regions,
        )

    # No candidates
    return ("BOTTOM_BAND", [0.0, BOTTOM_BAND_Y_MIN, 1.0, BOTTOM_BAND_Y_MAX], [])


def _detect_credits_overlays(
    band_regions: List[DetectedText],
    band_bbox_norm: List[float],
    image_width: int,
    image_height: int,
    job_id: Optional[str] = None,
) -> Tuple[List[CreditsOverlayElement], List[DetectedText]]:
    """
    Pass 1: Detect discrete overlay elements (logos, badges, URLs, social handles).

    Args:
        band_regions: Regions in the candidate band
        band_bbox_norm: Band bounding box [x1, y1, x2, y2]
        image_width: Image width in pixels
        image_height: Image height in pixels
        job_id: Optional job ID for logging

    Returns:
        Tuple of (overlays, residual_regions)
    """
    correlation = f"job={job_id}" if job_id else ""
    overlays: List[CreditsOverlayElement] = []
    residual_regions: List[DetectedText] = []

    for region in band_regions:
        geometry = geometry_from_detected_text(region, image_width, image_height)
        if not geometry:
            # Skip regions without geometry
            residual_regions.append(region)
            continue

        overlay_type: Optional[CreditsOverlayType] = None

        # B1: URL/social signature
        text = region.text if hasattr(region, "text") else ""
        text_upper = text.upper()

        if "@" in text:
            overlay_type = "SOCIAL_HANDLE"
        elif any(
            token in text_upper
            for token in [".COM", ".NET", ".ORG", ".IO", "HTTP://", "HTTPS://", "WWW."]
        ):
            overlay_type = "URL"

        # B2: Badge/logo geometry
        if not overlay_type and geometry.bbox_norm:
            area_norm = area_from_bbox(geometry.bbox_norm)
            height_norm = height_from_bbox(geometry.bbox_norm)
            aspect = aspect_ratio_from_bbox(geometry.bbox_norm)

            if area_norm < OVERLAY_AREA_SMALL:
                overlay_type = "LOGO"
            elif height_norm < OVERLAY_HEIGHT_TINY and aspect > OVERLAY_ASPECT_WIDE:
                overlay_type = "UNKNOWN"  # Could be logo or badge

            # Optional: rating badge patterns
            if not overlay_type and any(
                pattern in text_upper for pattern in ["RATED", "PG", "G", "R", "NC-17", "MPAA"]
            ):
                overlay_type = "RATING_BADGE"

        if overlay_type:
            overlays.append(
                CreditsOverlayElement(
                    element_type=overlay_type,
                    text=text if text else None,
                    geometry=geometry,
                    locked=True,
                )
            )
        else:
            residual_regions.append(region)

    # Log overlay detection
    counts_by_type = {}
    for overlay in overlays:
        counts_by_type[overlay.element_type] = counts_by_type.get(overlay.element_type, 0) + 1

    logger.info(
        f"CreditsOverlaysDetected {correlation} counts_by_type={counts_by_type} "
        f"total={len(overlays)} residual={len(residual_regions)}"
    )

    return overlays, residual_regions


def _detect_credits_block(
    residual_regions: List[DetectedText],
    overlays: List[CreditsOverlayElement],
    band_bbox_norm: List[float],
    image_width: int,
    image_height: int,
    job_id: Optional[str] = None,
) -> Optional[CreditsBlock]:
    """
    Pass 2: Cluster residual regions and score as credits candidates.

    Args:
        residual_regions: Regions not tagged as overlays
        overlays: Detected overlay elements
        band_bbox_norm: Band bounding box
        image_width: Image width in pixels
        image_height: Image height in pixels
        job_id: Optional job ID for logging

    Returns:
        CreditsBlock or None if no viable cluster found
    """
    correlation = f"job={job_id}" if job_id else ""

    if not residual_regions:
        return None

    # Cluster residual regions
    clusters = _cluster_regions(residual_regions, image_width, image_height)

    if not clusters:
        logger.info(f"CreditsPass2ClustersScored {correlation} clusters=0")
        return None

    # Score clusters
    scored_clusters = []
    for cluster in clusters:
        score, stats = _score_cluster(cluster, band_bbox_norm, image_width, image_height)
        scored_clusters.append((score, stats, cluster))

    # Sort by score (highest first)
    scored_clusters.sort(key=lambda x: x[0], reverse=True)

    # Log top clusters
    top_k = scored_clusters[:3]
    top_k_log = []
    for score, stats, cluster in top_k:
        top_k_log.append(
            {
                "score": round(score, 2),
                "line_count": stats["line_count"],
                "median_font_height": round(stats["median_font_height"], 4),
                "angle_std": round(stats["angle_std"], 1),
                "lex_boost": round(stats["lex_boost"], 2),
                "bbox_norm": stats["bbox_norm"],
            }
        )

    logger.info(f"CreditsPass2ClustersScored {correlation} top_k={top_k_log}")

    # Select best cluster if score is above threshold
    if not scored_clusters:
        return None

    best_score, best_stats, best_cluster = scored_clusters[0]
    min_acceptance_threshold = 2.0  # Tune as needed

    if best_score < min_acceptance_threshold:
        logger.info(
            f"CreditsBlockSelected {correlation} score={best_score:.2f} "
            f"threshold={min_acceptance_threshold} result=rejected"
        )
        return None

    # Compute oriented bbox for winning cluster
    dominant_angle = best_stats["angle_mean"]
    quad_norm, bbox_norm = _compute_oriented_bbox_for_cluster(
        best_cluster, dominant_angle, image_width, image_height
    )

    # Create CreditsBlock (credit_groups will be populated in later step)
    credits_block = CreditsBlock(
        geometry=RegionGeometry(
            quad_norm=quad_norm,
            center_norm=PointNorm(
                x=(bbox_norm[0] + bbox_norm[2]) / 2, y=(bbox_norm[1] + bbox_norm[3]) / 2
            ),
            angle_deg=dominant_angle,
            bbox_norm=bbox_norm,
        ),
        dominant_angle_deg=dominant_angle,
        source_line_region_ids=[],  # Will be populated if stable IDs available
        credit_groups=[],  # Will be populated in grouping step
        confidence=min(1.0, best_score / 5.0),  # Normalize to 0-1
    )

    logger.info(
        f"CreditsBlockSelected {correlation} score={best_score:.2f} confidence={credits_block.confidence:.3f} "
        f"bbox_norm={bbox_norm} angle={dominant_angle:.1f}"
    )

    return credits_block


def _cluster_regions(
    regions: List[DetectedText], image_width: int, image_height: int
) -> List[List[DetectedText]]:
    """
    Cluster regions into dense blobs using greedy approach.

    Args:
        regions: List of regions to cluster
        image_width: Image width in pixels
        image_height: Image height in pixels

    Returns:
        List of clusters (each cluster is a list of regions)
    """
    if not regions:
        return []

    # Sort by y, then x
    regions_sorted = sorted(
        regions,
        key=lambda r: (
            r.boundingBox[1] if hasattr(r, "boundingBox") and len(r.boundingBox) >= 4 else 1.0,
            r.boundingBox[0] if hasattr(r, "boundingBox") and len(r.boundingBox) >= 4 else 0.0,
        ),
    )

    clusters: List[List[DetectedText]] = []
    dy_threshold = 0.02  # Tune: 2% of image height

    for region in regions_sorted:
        if not hasattr(region, "boundingBox") or len(region.boundingBox) < 4:
            continue

        region_y = region.boundingBox[1]  # y1
        region_x1 = region.boundingBox[0]
        region_x2 = region.boundingBox[2]

        matched = False
        for cluster in clusters:
            if not cluster:
                continue

            # Check if region is close in y and overlaps in x
            cluster_y_centers = []
            cluster_x_ranges = []
            for cluster_region in cluster:
                if hasattr(cluster_region, "boundingBox") and len(cluster_region.boundingBox) >= 4:
                    cluster_y_centers.append(cluster_region.boundingBox[1])
                    cluster_x_ranges.append(
                        (cluster_region.boundingBox[0], cluster_region.boundingBox[2])
                    )

            if not cluster_y_centers:
                continue

            avg_cluster_y = sum(cluster_y_centers) / len(cluster_y_centers)

            # Check y adjacency
            if abs(region_y - avg_cluster_y) > dy_threshold:
                continue

            # Check x overlap
            cluster_x_min = min(x1 for x1, _ in cluster_x_ranges)
            cluster_x_max = max(x2 for _, x2 in cluster_x_ranges)
            overlap_ratio = max(
                0.0,
                (min(region_x2, cluster_x_max) - max(region_x1, cluster_x_min))
                / max(region_x2 - region_x1, cluster_x_max - cluster_x_min, 0.001),
            )

            if overlap_ratio > 0.2:  # Tune: 20% overlap
                cluster.append(region)
                matched = True
                break

        if not matched:
            clusters.append([region])

    return clusters


def _score_cluster(
    cluster: List[DetectedText],
    band_bbox_norm: List[float],
    image_width: int,
    image_height: int,
) -> Tuple[float, dict]:
    """
    Score a cluster as a credits candidate.

    Returns:
        Tuple of (score, stats_dict)
    """
    if not cluster:
        return 0.0, {}

    # Collect stats
    line_count = len(cluster)
    font_heights = []
    angles = []
    text_lines = []

    for region in cluster:
        geometry = geometry_from_detected_text(region, image_width, image_height)
        if geometry:
            font_heights.append(font_height_from_geometry(geometry))
            angles.append(geometry.angle_deg)
        if hasattr(region, "text"):
            text_lines.append(region.text)

    median_font_height = statistics.median(font_heights) if font_heights else 0.1
    angle_mean = statistics.mean(angles) if angles else 0.0
    angle_std = statistics.stdev(angles) if len(angles) > 1 else 0.0

    # Compute cluster bbox
    all_x = []
    all_y = []
    for region in cluster:
        if hasattr(region, "boundingBox") and len(region.boundingBox) >= 4:
            all_x.extend([region.boundingBox[0], region.boundingBox[2]])
            all_y.extend([region.boundingBox[1], region.boundingBox[3]])

    if not all_x or not all_y:
        return 0.0, {}

    cluster_bbox = [min(all_x), min(all_y), max(all_x), max(all_y)]
    cluster_height = cluster_bbox[3] - cluster_bbox[1]
    density = line_count / max(cluster_height, 0.001)

    # Lexical boost
    lex_boost = 0.0
    if text_lines:
        matching_lines = 0
        for line in text_lines:
            line_lower = line.lower()
            if any(anchor in line_lower for anchor in CREDITS_ROLE_ANCHORS):
                matching_lines += 1
        lex_boost = matching_lines / len(text_lines)

    # Scoring components
    score = 0.0
    if line_count >= CREDITS_LINE_COUNT_MIN:
        score += 1.0
    if median_font_height <= CREDITS_FONT_HEIGHT_MAX:
        score += 1.0
    if density > 10.0:  # Tune: lines per normalized height unit
        score += 1.0

    # Bottom quartile boost
    band_center_y = (band_bbox_norm[1] + band_bbox_norm[3]) / 2
    cluster_center_y = (cluster_bbox[1] + cluster_bbox[3]) / 2
    if cluster_center_y > band_center_y:
        score += 0.5

    if angle_std <= CREDITS_ANGLE_STD_MAX:
        score += 0.5

    score += lex_boost  # 0.0-1.0 boost

    stats = {
        "line_count": line_count,
        "median_font_height": median_font_height,
        "angle_mean": angle_mean,
        "angle_std": angle_std,
        "density": density,
        "lex_boost": lex_boost,
        "bbox_norm": cluster_bbox,
    }

    return score, stats


def _compute_oriented_bbox_for_cluster(
    cluster: List[DetectedText],
    dominant_angle_deg: float,
    image_width: int,
    image_height: int,
) -> Tuple[QuadNorm, List[float]]:
    """
    Compute oriented bounding box for cluster.

    For now, returns axis-aligned bbox (per spec note that oriented crop can be approximated).

    Returns:
        Tuple of (QuadNorm, bbox_norm)
    """
    all_x = []
    all_y = []

    for region in cluster:
        geometry = geometry_from_detected_text(region, image_width, image_height)
        if geometry:
            for v in geometry.quad_norm.vertices:
                all_x.append(v.x)
                all_y.append(v.y)

    if not all_x or not all_y:
        # Default
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

    x1, y1 = min(all_x), min(all_y)
    x2, y2 = max(all_x), max(all_y)

    # Axis-aligned quad (will be logged as such)
    quad_norm = QuadNorm(
        vertices=[
            PointNorm(x=x1, y=y1),
            PointNorm(x=x2, y=y1),
            PointNorm(x=x2, y=y2),
            PointNorm(x=x1, y=y2),
        ]
    )

    return quad_norm, [x1, y1, x2, y2]


def extract_credits_crop(
    original_image_bytes: bytes,
    credits_block_geometry: RegionGeometry,
    image_width: int,
    image_height: int,
    job_id: Optional[str] = None,
) -> Tuple[bytes, str]:
    """
    Extract high-resolution crop of credits block from original image.

    Args:
        original_image_bytes: Full-resolution original image bytes
        credits_block_geometry: Geometry of detected credits block
        image_width: Original image width in pixels
        image_height: Original image height in pixels
        job_id: Optional job ID for logging

    Returns:
        Tuple of (crop_bytes, method) where method is "oriented" or "axis_aligned"
    """
    correlation = f"job={job_id}" if job_id else ""

    try:
        image = Image.open(BytesIO(original_image_bytes))
        bbox_norm = credits_block_geometry.bbox_norm

        if not bbox_norm or len(bbox_norm) < 4:
            logger.warning(f"CreditsCropExtracted {correlation} method=invalid bbox_norm={bbox_norm}")
            return original_image_bytes, "axis_aligned"

        # Add small padding (1-2% of bbox size)
        x1, y1, x2, y2 = bbox_norm
        width = x2 - x1
        height = y2 - y1
        padding_x = width * 0.02
        padding_y = height * 0.02

        x1_px = max(0, int((x1 - padding_x) * image_width))
        y1_px = max(0, int((y1 - padding_y) * image_height))
        x2_px = min(image_width, int((x2 + padding_x) * image_width))
        y2_px = min(image_height, int((y2 + padding_y) * image_height))

        # For now, use axis-aligned crop (per spec note)
        crop_box = (x1_px, y1_px, x2_px, y2_px)
        cropped_image = image.crop(crop_box)

        # Save to bytes
        output = BytesIO()
        cropped_image.save(output, format="PNG")
        crop_bytes = output.getvalue()

        crop_w, crop_h = cropped_image.size
        logger.info(
            f"CreditsCropExtracted {correlation} method=axis_aligned "
            f"crop_px_w={crop_w} crop_px_h={crop_h} bbox_norm={bbox_norm}"
        )

        return crop_bytes, "axis_aligned"

    except Exception as e:
        logger.error(f"CreditsCropExtracted {correlation} method=error error={str(e)}", exc_info=True)
        return original_image_bytes, "axis_aligned"


def group_credits_lines(
    line_regions: List[DetectedText],
    image_width: int,
    image_height: int,
    job_id: Optional[str] = None,
) -> List[CreditGroup]:
    """
    Group credit lines into semantic groups (TITLE, PROPER_NAME, CERTIFICATION).

    Args:
        line_regions: List of detected text regions from credits block OCR
        image_width: Crop image width in pixels
        image_height: Crop image height in pixels
        job_id: Optional job ID for logging

    Returns:
        List of CreditGroup objects
    """
    correlation = f"job={job_id}" if job_id else ""

    if not line_regions:
        return []

    # Create preliminary CreditLines
    credit_lines: List[CreditLine] = []
    for region in line_regions:
        geometry = geometry_from_detected_text(region, image_width, image_height)
        if not geometry:
            continue

        font_height = font_height_from_geometry(geometry)
        text = region.text if hasattr(region, "text") else ""

        # Check for matched anchors
        hints = []
        text_lower = text.lower()
        for anchor in CREDITS_ROLE_ANCHORS:
            if anchor in text_lower:
                hints.append(anchor)

        credit_lines.append(
            CreditLine(
                text=text,
                geometry=geometry,
                font_height_norm=font_height,
                hints=hints,
            )
        )

    # Detect over/under structures
    over_under_pairs = []
    for i, line1 in enumerate(credit_lines):
        for j, line2 in enumerate(credit_lines[i + 1 :], start=i + 1):
            # Check if line1 (smaller font) is above line2 (larger font)
            if line1.font_height_norm >= line2.font_height_norm:
                continue

            # Check vertical gap
            gap_y = abs(line2.geometry.center_norm.y - line1.geometry.center_norm.y)
            if gap_y > OVER_UNDER_MAX_GAP_Y:
                continue

            # Check x overlap
            bbox1 = line1.geometry.bbox_norm or [0, 0, 1, 1]
            bbox2 = line2.geometry.bbox_norm or [0, 0, 1, 1]
            x1_min, x1_max = bbox1[0], bbox1[2]
            x2_min, x2_max = bbox2[0], bbox2[2]

            overlap_width = max(0, min(x1_max, x2_max) - max(x1_min, x2_min))
            line1_width = x1_max - x1_min
            line2_width = x2_max - x2_min
            overlap_ratio = overlap_width / max(line1_width, line2_width, 0.001)

            if overlap_ratio >= OVER_UNDER_MIN_X_OVERLAP:
                over_under_pairs.append((i, j))

    if over_under_pairs:
        logger.info(f"CreditsOverUnderDetected {correlation} pairs={len(over_under_pairs)}")

    # Group lines
    groups: List[CreditGroup] = []
    used_indices = set()

    # First, create groups for over/under pairs
    for i, j in over_under_pairs:
        if i in used_indices or j in used_indices:
            continue

        line1 = credit_lines[i]
        line2 = credit_lines[j]

        # Classify the pair
        group_type = _classify_group([line1, line2])
        localizable = group_type == "TITLE"

        # Union geometry
        union_bbox = _union_bbox(
            line1.geometry.bbox_norm or [0, 0, 1, 1],
            line2.geometry.bbox_norm or [0, 0, 1, 1],
        )

        # Create representative geometry
        union_geometry = RegionGeometry(
            quad_norm=line1.geometry.quad_norm,  # Use first line's quad as representative
            center_norm=PointNorm(
                x=(union_bbox[0] + union_bbox[2]) / 2, y=(union_bbox[1] + union_bbox[3]) / 2
            ),
            angle_deg=(line1.geometry.angle_deg + line2.geometry.angle_deg) / 2,
            bbox_norm=union_bbox,
        )

        groups.append(
            CreditGroup(
                group_type=group_type,
                lines=[line1, line2],
                geometry=union_geometry,
                localizable=localizable,
                confidence=0.8,  # High confidence for over/under pairs
            )
        )

        used_indices.add(i)
        used_indices.add(j)

    # Then, create groups for remaining lines
    for i, line in enumerate(credit_lines):
        if i in used_indices:
            continue

        group_type = _classify_group([line])
        localizable = group_type == "TITLE"

        groups.append(
            CreditGroup(
                group_type=group_type,
                lines=[line],
                geometry=line.geometry,
                localizable=localizable,
                confidence=0.6,  # Lower confidence for single lines
            )
        )

    # Log grouping summary
    counts_by_type = {}
    for group in groups:
        counts_by_type[group.group_type] = counts_by_type.get(group.group_type, 0) + 1

    logger.info(
        f"CreditsGroupingSummary {correlation} groups_total={len(groups)} "
        f"by_type={counts_by_type}"
    )

    return groups


def _classify_group(lines: List[CreditLine]) -> CreditGroupType:
    """
    Classify a group of credit lines by type.

    Args:
        lines: List of CreditLine objects

    Returns:
        CreditGroupType
    """
    if not lines:
        return "UNKNOWN"

    # Check for certification patterns (all caps, periods, short)
    for line in lines:
        text = line.text.strip()
        if len(text) < 10 and text.isupper() and "." in text:
            # Check for common certification patterns
            if any(pattern in text for pattern in ["A.C.E.", "ASC", "A.S.C.", "MPAA"]):
                return "CERTIFICATION"

    # Check for role anchors (TITLE)
    for line in lines:
        text_lower = line.text.lower()
        if any(anchor in text_lower for anchor in CREDITS_ROLE_ANCHORS):
            return "TITLE"

    # Check for proper name patterns (mostly capitalized words, name-like)
    for line in lines:
        text = line.text.strip()
        words = text.split()
        if len(words) >= 2:
            # Check if most words start with capital
            capitalized_count = sum(1 for w in words if w and w[0].isupper())
            if capitalized_count >= len(words) * 0.7:
                return "PROPER_NAME"

    return "UNKNOWN"


def _union_bbox(bbox1: List[float], bbox2: List[float]) -> List[float]:
    """Compute union of two bounding boxes."""
    if len(bbox1) < 4 or len(bbox2) < 4:
        return [0.0, 0.0, 1.0, 1.0]
    return [
        min(bbox1[0], bbox2[0]),
        min(bbox1[1], bbox2[1]),
        max(bbox1[2], bbox2[2]),
        max(bbox1[3], bbox2[3]),
    ]
