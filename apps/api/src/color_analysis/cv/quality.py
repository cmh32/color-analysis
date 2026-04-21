import numpy as np

from color_analysis.cv.landmarks import detect_landmarks
from color_analysis.cv.regions import build_region_masks, find_undersized_regions
from color_analysis.cv.types import DecodedPhoto, LandmarkDetection, QualityReport

try:
    import cv2  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - dependency optional in local bootstrap
    cv2 = None

_MAX_ABS_YAW_DEGREES = 18.0
_MAX_ABS_PITCH_DEGREES = 15.0


def evaluate_quality(photo: DecodedPhoto, detection: LandmarkDetection | None = None) -> QualityReport:
    if detection is None:
        detection = detect_landmarks(photo)

    if cv2 is not None:
        gray = cv2.cvtColor(photo.rgb, cv2.COLOR_RGB2GRAY)
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        histogram = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
    else:
        gray = np.mean(photo.rgb.astype(np.float32), axis=2).astype(np.uint8)
        grad_x = np.diff(gray.astype(np.float32), axis=1)
        grad_y = np.diff(gray.astype(np.float32), axis=0)
        blur_score = float(np.var(grad_x) + np.var(grad_y))
        histogram, _ = np.histogram(gray, bins=256, range=(0, 256))

    total = float(gray.size)
    dark_clip = float(histogram[:3].sum() / total)
    bright_clip = float(histogram[-3:].sum() / total)
    exposure_score = max(0.0, 1.0 - (dark_clip + bright_clip) * 8.0)

    reasons: list[str] = []
    accepted = True
    yaw_degrees = 0.0
    pitch_degrees = 0.0
    if detection.available and detection.face_count == 0:
        accepted = False
        reasons.append("no_face_detected")
    if detection.available and detection.face_count > 1:
        accepted = False
        reasons.append("multiple_subjects")
    if detection.landmarks is not None:
        yaw_degrees = float(detection.landmarks.pose_yaw_degrees)
        pitch_degrees = float(detection.landmarks.pose_pitch_degrees)
        if abs(yaw_degrees) > _MAX_ABS_YAW_DEGREES:
            accepted = False
            reasons.append("pose_yaw_too_large")
        if abs(pitch_degrees) > _MAX_ABS_PITCH_DEGREES:
            accepted = False
            reasons.append("pose_pitch_too_large")
        region_failures = find_undersized_regions(build_region_masks(photo.rgb.shape, detection.landmarks), detection.landmarks)
        if region_failures:
            accepted = False
            reasons.extend(region_failures)
    if blur_score < 35.0:
        accepted = False
        reasons.append("blurry")
    if dark_clip > 0.03 or bright_clip > 0.03:
        accepted = False
        reasons.append("bad_exposure")

    return QualityReport(
        photo_id=photo.id,
        accepted=accepted,
        blur_score=blur_score,
        exposure_score=exposure_score,
        face_count=detection.face_count,
        yaw_degrees=yaw_degrees,
        pitch_degrees=pitch_degrees,
        reasons=tuple(reasons),
    )
