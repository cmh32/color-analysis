from collections.abc import Iterable

import numpy as np

from color_analysis.cv.aggregate import aggregate_features
from color_analysis.cv.classifier import classify, compute_reliability
from color_analysis.cv.decode import decode_photo
from color_analysis.cv.features import extract_features
from color_analysis.cv.landmarks import detect_landmarks
from color_analysis.cv.quality import evaluate_quality
from color_analysis.cv.regions import build_region_masks
from color_analysis.cv.scorecard import build_scorecard
from color_analysis.cv.types import DecodedPhoto, Landmarks, PipelineResult, PhotoInput, QualityReport
from color_analysis.cv.white_balance import apply_white_balance


_FEATURE_RANGES: dict[str, float] = {
    "l_star": 100.0,
    "a_star": 120.0,
    "b_star": 120.0,
    "c_star": 100.0,
    "h_deg": 360.0,
    "ita_deg": 180.0,
}


def _compute_consistency(features: list) -> float:
    """Cross-photo std per feature, normalized to each feature's natural range."""
    if not features:
        return 0.0
    by_key: dict[str, list[float]] = {}
    for feat in features:
        for name, scale in _FEATURE_RANGES.items():
            by_key.setdefault(f"{feat.region}.{name}", []).append(getattr(feat, name) / scale)
    stds = [float(np.std(vals)) for vals in by_key.values() if len(vals) >= 2]
    if not stds:
        return 1.0
    return max(0.0, min(1.0, 1.0 - float(np.mean(stds)) * 2.0))


def _empty_result(
    result_state: str,
    trace: list[str],
    quality_reports: dict[str, QualityReport],
) -> PipelineResult:
    dummy_scorecard = build_scorecard({})
    classification = classify(dummy_scorecard)
    reliability = compute_reliability(0.0, 0.0, 0.0, photo_count=0)
    return PipelineResult(
        result_state=result_state,
        scorecard=dummy_scorecard,
        classification=classification,
        reliability=reliability,
        trace=tuple(trace),
        quality_reports=quality_reports,
        per_photo_features=[],
        aggregated_features={},
    )


def run(inputs: Iterable[PhotoInput]) -> PipelineResult:
    trace: list[str] = []

    quality_reports: dict[str, QualityReport] = {}
    accepted: list[tuple[DecodedPhoto, Landmarks | None]] = []
    for item in inputs:
        try:
            decoded = decode_photo(item)
            detection = detect_landmarks(decoded)
            report = evaluate_quality(decoded, detection)
            quality_reports[decoded.id] = report
            if report.accepted:
                accepted.append((decoded, detection.landmarks))
        except Exception:
            quality_reports[item.id] = QualityReport(
                photo_id=item.id,
                accepted=False,
                blur_score=0.0,
                exposure_score=0.0,
                face_count=0,
                yaw_degrees=0.0,
                pitch_degrees=0.0,
                reasons=("decode_failed",),
            )
            trace.append(f"{item.id}:decode_failed")
    trace.append("decode+quality")

    if len(accepted) < 6:
        if len(accepted) == 0:
            if any("multiple_subjects" in report.reasons for report in quality_reports.values()):
                trace.append("quality:multiple_subjects")
                return _empty_result("multiple_subjects", trace, quality_reports)
            if any("no_face_detected" in report.reasons for report in quality_reports.values()):
                trace.append("quality:no_face_detected")
                return _empty_result("no_face_detected", trace, quality_reports)
        return _empty_result("insufficient_photos", trace, quality_reports)

    all_features = []
    all_display_features = []
    wb_confidence: dict[str, float] = {}
    display_confidence: dict[str, float] = {}
    photos_with_landmarks = 0
    photos_with_processing_errors = 0
    saw_multiple_subjects = False

    for photo, landmarks in accepted:
        if landmarks is None:
            report = quality_reports.get(photo.id)
            if report is not None and report.face_count > 1:
                saw_multiple_subjects = True
                trace.append(f"{photo.id}:multiple_subjects")
            else:
                trace.append(f"{photo.id}:no_face")
            continue
        try:
            photos_with_landmarks += 1
            masks = build_region_masks(photo.rgb.shape, landmarks)
            display_features = extract_features(photo.id, photo.rgb, masks)
            wb_rgb, wb_method, confidence = apply_white_balance(photo.rgb, masks)
            wb_confidence[photo.id] = confidence
            display_confidence[photo.id] = 1.0
            features = extract_features(photo.id, wb_rgb, masks)
            all_features.extend(features)
            all_display_features.extend(display_features)
            trace.append(f"{photo.id}:landmarks+regions+wb={wb_method}+features")
        except Exception:
            photos_with_processing_errors += 1
            trace.append(f"{photo.id}:feature_extraction_failed")
            continue

    if photos_with_landmarks == 0:
        if photos_with_processing_errors > 0:
            trace.append("pipeline:processing_failed")
            return _empty_result("failed", trace, quality_reports)
        if saw_multiple_subjects:
            trace.append("landmarks:multiple_subjects")
            return _empty_result("multiple_subjects", trace, quality_reports)
        trace.append("landmarks:no_face_detected")
        return _empty_result("no_face_detected", trace, quality_reports)

    aggregated = aggregate_features(all_features, quality_reports, wb_confidence)
    display_aggregated = aggregate_features(all_display_features, quality_reports, display_confidence)
    aggregated.update({f"display.{key}": value for key, value in display_aggregated.items()})
    scorecard = build_scorecard(aggregated)
    classification = classify(scorecard)

    quality_mean = float(
        np.mean(
            [
                (min(1.0, report.blur_score / 120.0) * 0.6) + (report.exposure_score * 0.4)
                for report in quality_reports.values()
            ]
        )
    )
    consistency_score = _compute_consistency(all_features)
    reliability = compute_reliability(
        quality_mean,
        consistency_score,
        classification.margin,
        photo_count=len(wb_confidence),
    )

    result_state = "ok_low_reliability" if reliability.bucket == "Low" else "ok"
    trace.append("aggregate+scorecard+classify")

    return PipelineResult(
        result_state=result_state,
        scorecard=scorecard,
        classification=classification,
        reliability=reliability,
        trace=tuple(trace),
        quality_reports=quality_reports,
        per_photo_features=all_features,
        aggregated_features=aggregated,
    )
