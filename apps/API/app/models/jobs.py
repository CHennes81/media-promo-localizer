"""
Pydantic models for API request/response schemas and internal job representation.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional, TYPE_CHECKING, Dict

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from typing import ForwardRef


class JobStatus(str, Enum):
    """Job status enumeration."""

    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"  # Reserved for future use


class ProgressStage(str, Enum):
    """Pipeline stage enumeration."""

    OCR = "ocr"
    TRANSLATION = "translation"
    INPAINT = "inpaint"
    PACKAGING = "packaging"


class PipelinePlan(BaseModel):
    """Pipeline execution plan with stage enablement flags."""

    enableTranslation: bool = True
    enableInpaint: bool = True
    enablePackaging: bool = True


class Progress(BaseModel):
    """Job progress information."""

    stage: ProgressStage
    percent: int = Field(ge=0, le=100)
    stageTimingsMs: dict[str, int] = Field(default_factory=dict)


class DetectedText(BaseModel):
    """Detected text region with normalized bounding box."""

    text: str
    boundingBox: List[float] = Field(
        description="Normalized coordinates [x1, y1, x2, y2] in range 0.0-1.0"
    )
    role: str = Field(
        description="Text role: title, tagline, credits, rating, other, etc."
    )


class DebugTextRegion(BaseModel):
    """Debug text region with full metadata for line-level OCR output."""

    id: str = Field(description="Unique identifier for this region")
    role: str = Field(description="Text role: title, tagline, credits, legal, other, etc.")
    bbox_norm: List[float] = Field(
        description="Normalized bounding box [x, y, width, height] in range 0.0-1.0"
    )
    original_text: str = Field(description="Original text from OCR")
    translated_text: Optional[str] = Field(
        default=None, description="Translated text (if available)"
    )
    is_localizable: bool = Field(description="Whether this region is localizable")
    geometry: Optional[Dict] = Field(
        default=None,
        description="Rotation-aware geometry: quad_norm (4 vertices), center_norm (x,y), angle_deg (degrees)"
    )


class ProcessingTimeMs(BaseModel):
    """Processing time breakdown per stage."""

    ocr: int = 0
    translation: int = 0
    inpaint: int = 0
    packaging: int = 0
    total: int = 0


class DebugInfo(BaseModel):
    """Debug information for job result."""

    regions: List["DebugTextRegion"] = Field(
        default_factory=list, description="Line-level text regions with debug metadata"
    )
    timings: ProcessingTimeMs = Field(description="Processing timings per stage")


# Update forward references after all models are defined
DebugInfo.model_rebuild()


class JobResult(BaseModel):
    """Result payload for a completed localization job."""

    imageUrl: str
    thumbnailUrl: Optional[str] = None
    processingTimeMs: ProcessingTimeMs
    language: str
    sourceLanguage: Optional[str] = None
    detectedText: Optional[List[DetectedText]] = None
    debug: Optional[DebugInfo] = Field(
        default=None, description="Debug information with line-level regions"
    )


class ErrorInfo(BaseModel):
    """Error information for failed jobs."""

    code: str
    message: str
    retryable: bool = False
    details: Optional[dict] = None


class CreateJobResponse(BaseModel):
    """Response for POST /v1/localization-jobs (202 Accepted)."""

    jobId: str
    status: JobStatus
    createdAt: datetime
    estimatedSeconds: Optional[int] = None


class GetJobResponse(BaseModel):
    """Response for GET /v1/localization-jobs/{jobId}."""

    jobId: str
    status: JobStatus
    createdAt: datetime
    updatedAt: datetime
    progress: Optional[Progress] = None
    result: Optional[JobResult] = None
    error: Optional[ErrorInfo] = None


# Internal job model (not exposed directly in API)
class LocalizationJob(BaseModel):
    """Internal representation of a localization job."""

    jobId: str
    status: JobStatus
    createdAt: datetime
    updatedAt: datetime
    targetLanguage: str
    sourceLanguage: Optional[str] = None
    progress: Optional[Progress] = None
    result: Optional[JobResult] = None
    error: Optional[ErrorInfo] = None
    # Internal fields
    filePath: Optional[str] = None  # Path to uploaded file
    fileName: Optional[str] = None
    fileSize: Optional[int] = None
    jobMetadata: Optional[dict] = None
    # Credits detection result (optional, populated during OCR stage)
    credits_detection: Optional[Dict] = None

    def to_get_response(self) -> GetJobResponse:
        """Convert internal job to API response format."""
        return GetJobResponse(
            jobId=self.jobId,
            status=self.status,
            createdAt=self.createdAt,
            updatedAt=self.updatedAt,
            progress=self.progress,
            result=self.result,
            error=self.error,
        )
