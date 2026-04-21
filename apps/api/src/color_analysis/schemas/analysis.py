from typing import Literal

from pydantic import BaseModel, Field

Season = Literal["Spring", "Summer", "Autumn", "Winter"]
QualityIssueCode = Literal["blurry", "bad_exposure", "no_face_detected", "multiple_subjects", "decode_failed"]
ResultState = Literal[
    "ok",
    "ok_low_reliability",
    "insufficient_photos",
    "no_face_detected",
    "multiple_subjects",
    "filter_suspected",
    "failed",
]


class AnalyzeRequest(BaseModel):
    force_recompute: bool = False


class AnalyzeResponse(BaseModel):
    accepted: bool


class RejectionSummaryItem(BaseModel):
    code: QualityIssueCode
    count: int = Field(ge=1)


class RejectedPhotoReview(BaseModel):
    photo_id: str
    filename: str
    reasons: list[QualityIssueCode]
    preview_url: str


class SessionReviewResponse(BaseModel):
    rejected_photos: list[RejectedPhotoReview]


class StatusResponse(BaseModel):
    status: Literal["pending", "running", "complete", "failed", "deleted"]
    result_state: ResultState | None = None
    rejection_summary: list[RejectionSummaryItem] | None = None


class Scorecard(BaseModel):
    warmth: float = Field(ge=-1.0, le=1.0)
    value: float = Field(ge=-1.0, le=1.0)
    chroma: float = Field(ge=-1.0, le=1.0)
    contrast: float = Field(ge=-1.0, le=1.0)


class Reliability(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    bucket: Literal["High", "Medium", "Low"]
    reasons: list[str]


class MeasurementPoint(BaseModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)


class MeasurementOverlay(BaseModel):
    id: Literal["skin", "hair", "left_eye", "right_eye"]
    group: Literal["skin", "hair", "eyes"]
    label: str
    anchor_x: float = Field(ge=0.0, le=1.0)
    anchor_y: float = Field(ge=0.0, le=1.0)
    polygons: list[list[MeasurementPoint]]


class MeasurementPhoto(BaseModel):
    photo_id: str
    filename: str
    preview_url: str
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    is_default: bool = False
    overlays: list[MeasurementOverlay]


class MeasurementDetail(BaseModel):
    label: str
    value: str


class MeasurementReading(BaseModel):
    key: Literal["skin", "hair", "eyes"]
    label: str
    summary: str
    swatch: str | None = None
    technical_details: list[MeasurementDetail] = Field(default_factory=list)


class AxisExplanation(BaseModel):
    key: Literal["warmth", "value", "chroma", "contrast"]
    label: str
    summary: str


class MeasurementExplanation(BaseModel):
    note: str
    photos: list[MeasurementPhoto]
    readings: list[MeasurementReading]
    axis_explanations: list[AxisExplanation]


class AnalysisResult(BaseModel):
    session_id: str
    top_2_seasons: tuple[Season, Season]
    scorecard: Scorecard
    reliability: Reliability
    result_state: ResultState
    trace: list[str]
    color_swatches: dict[str, str] | None = None
    measurement_explanation: MeasurementExplanation | None = None
