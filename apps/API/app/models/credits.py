"""
Pydantic models for credits block detection and semantic grouping.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class PointNorm(BaseModel):
    """Normalized point (x, y in range 0.0-1.0)."""

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)


class QuadNorm(BaseModel):
    """Normalized quadrilateral (TL, TR, BR, BL vertices)."""

    vertices: List[PointNorm] = Field(min_length=4, max_length=4)


class RegionGeometry(BaseModel):
    """Rotation-aware geometry for a text region."""

    quad_norm: QuadNorm
    center_norm: PointNorm
    angle_deg: float
    # Optional derived axis-aligned bbox for convenience
    bbox_norm: Optional[List[float]] = None  # [x1, y1, x2, y2]


CreditsOverlayType = Literal["LOGO", "RATING_BADGE", "URL", "SOCIAL_HANDLE", "UNKNOWN"]


class CreditsOverlayElement(BaseModel):
    """Discrete overlay element in credits band (logo, badge, URL, etc.)."""

    element_type: CreditsOverlayType
    text: Optional[str] = None
    geometry: RegionGeometry
    locked: bool = True  # always true


CreditGroupType = Literal["TITLE", "PROPER_NAME", "CERTIFICATION", "LOGO_IGNORED", "UNKNOWN"]


class CreditLine(BaseModel):
    """Single line of text within a credit group."""

    text: str
    geometry: RegionGeometry
    font_height_norm: float  # proxy from quad height
    hints: List[str] = Field(default_factory=list)  # e.g., matched anchors


class CreditGroup(BaseModel):
    """Semantically grouped credit lines (e.g., "Directed by" + name)."""

    group_type: CreditGroupType
    lines: List[CreditLine]
    geometry: RegionGeometry  # union or representative
    localizable: bool  # True for TITLE, False otherwise
    confidence: float = Field(ge=0.0, le=1.0)


class CreditsBlock(BaseModel):
    """Detected dense credits block with grouped lines."""

    geometry: RegionGeometry  # oriented quad covering the whole credits block
    dominant_angle_deg: float
    source_line_region_ids: List[str] = Field(default_factory=list)  # stable IDs if available
    credit_groups: List[CreditGroup] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class CreditsBandDetection(BaseModel):
    """Complete credits band detection result."""

    band_name: Literal["BOTTOM_BAND", "TOP_LITE_BAND"]
    band_bbox_norm: List[float]  # [x1, y1, x2, y2] normalized
    overlays: List[CreditsOverlayElement] = Field(default_factory=list)
    credits_block: Optional[CreditsBlock] = None
    confidence: float = Field(ge=0.0, le=1.0)
    debug: dict = Field(default_factory=dict)  # cluster scores, counts, etc.
