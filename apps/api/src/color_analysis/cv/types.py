from dataclasses import dataclass
from typing import Literal

import numpy as np

Season = Literal["Spring", "Summer", "Autumn", "Winter"]


@dataclass(frozen=True)
class PhotoInput:
    id: str
    filename: str
    payload: bytes


@dataclass(frozen=True)
class DecodedPhoto:
    id: str
    filename: str
    rgb: np.ndarray
    sha256: str


@dataclass(frozen=True)
class QualityReport:
    photo_id: str
    accepted: bool
    blur_score: float
    exposure_score: float
    face_count: int
    yaw_degrees: float
    pitch_degrees: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class Landmarks:
    photo_id: str
    face_bbox: tuple[int, int, int, int]
    left_eye_center: tuple[int, int]
    right_eye_center: tuple[int, int]


@dataclass(frozen=True)
class LandmarkDetection:
    face_count: int
    landmarks: Landmarks | None
    available: bool


@dataclass(frozen=True)
class RegionMasks:
    photo_id: str
    cheek_left: np.ndarray
    cheek_right: np.ndarray
    forehead: np.ndarray
    iris_left: np.ndarray
    iris_right: np.ndarray
    sclera: np.ndarray
    hair: np.ndarray


@dataclass(frozen=True)
class RegionFeatures:
    photo_id: str
    region: str
    l_star: float
    a_star: float
    b_star: float
    c_star: float
    h_deg: float
    ita_deg: float


@dataclass(frozen=True)
class Scorecard:
    warmth: float
    value: float
    chroma: float
    contrast: float


@dataclass(frozen=True)
class Classification:
    top_2: tuple[Season, Season]
    probabilities: dict[Season, float]
    margin: float


@dataclass(frozen=True)
class Reliability:
    score: float
    bucket: Literal["High", "Medium", "Low"]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PipelineResult:
    result_state: str
    scorecard: Scorecard
    classification: Classification
    reliability: Reliability
    trace: tuple[str, ...]
    quality_reports: dict[str, "QualityReport"]
    per_photo_features: list["RegionFeatures"]
    aggregated_features: dict[str, float]
