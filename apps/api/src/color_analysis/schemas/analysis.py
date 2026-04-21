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


class AnalysisResult(BaseModel):
    session_id: str
    top_2_seasons: tuple[Season, Season]
    scorecard: Scorecard
    reliability: Reliability
    result_state: ResultState
    trace: list[str]
