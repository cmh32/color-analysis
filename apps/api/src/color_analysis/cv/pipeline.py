import numpy as np

from color_analysis.cv.aggregate import aggregate_features
from color_analysis.cv.classifier import classify, compute_reliability
from color_analysis.cv.decode import decode_photo
from color_analysis.cv.features import extract_features
from color_analysis.cv.landmarks import detect_landmarks
from color_analysis.cv.quality import evaluate_quality
from color_analysis.cv.regions import build_region_masks
from color_analysis.cv.scorecard import build_scorecard
from color_analysis.cv.types import PipelineResult, PhotoInput
from color_analysis.cv.white_balance import apply_white_balance


def run(inputs: list[PhotoInput]) -> PipelineResult:
    trace: list[str] = []
    decoded = [decode_photo(item) for item in inputs]
    trace.append("decode")

    quality_reports = {photo.id: evaluate_quality(photo) for photo in decoded}
    trace.append("quality")

    accepted = [photo for photo in decoded if quality_reports[photo.id].accepted]
    if len(accepted) < 6:
        dummy_scorecard = build_scorecard({})
        classification = classify(dummy_scorecard)
        reliability = compute_reliability(0.0, 0.0, 0.0)
        return PipelineResult(
            result_state="insufficient_photos",
            scorecard=dummy_scorecard,
            classification=classification,
            reliability=reliability,
            trace=tuple(trace),
        )

    all_features = []
    wb_confidence: dict[str, float] = {}

    for photo in accepted:
        landmarks = detect_landmarks(photo)
        masks = build_region_masks(photo.rgb.shape, landmarks)
        wb_rgb, wb_method, confidence = apply_white_balance(photo.rgb, masks)
        wb_confidence[photo.id] = confidence

        features = extract_features(photo.id, wb_rgb, masks)
        all_features.extend(features)
        trace.append(f"{photo.id}:landmarks+regions+wb={wb_method}+features")

    aggregated = aggregate_features(all_features, quality_reports, wb_confidence)
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
    consistency_score = max(0.0, min(1.0, 1.0 - np.std(list(aggregated.values() or [0.0])) / 50.0))
    reliability = compute_reliability(quality_mean, consistency_score, classification.margin)

    result_state = "ok_low_reliability" if reliability.bucket == "Low" else "ok"
    trace.append("aggregate+scorecard+classify")

    return PipelineResult(
        result_state=result_state,
        scorecard=scorecard,
        classification=classification,
        reliability=reliability,
        trace=tuple(trace),
    )
