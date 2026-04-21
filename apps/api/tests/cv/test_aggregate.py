from color_analysis.cv.aggregate import aggregate_features
from color_analysis.cv.classifier import compute_reliability
from color_analysis.cv.types import QualityReport, RegionFeatures


def _quality(photo_id: str) -> QualityReport:
    return QualityReport(
        photo_id=photo_id,
        accepted=True,
        blur_score=80.0,
        exposure_score=0.9,
        face_count=1,
        yaw_degrees=0.0,
        pitch_degrees=0.0,
        reasons=(),
    )


def _feature(photo_id: str, region: str, l_star: float, h_deg: float) -> RegionFeatures:
    return RegionFeatures(
        photo_id=photo_id,
        region=region,
        l_star=l_star,
        a_star=10.0,
        b_star=5.0,
        c_star=11.2,
        h_deg=h_deg,
        ita_deg=35.0,
    )


def test_aggregate_features_uses_weighted_median_for_outliers() -> None:
    features = [
        _feature("p1", "cheek_left", 42.0, 20.0),
        _feature("p2", "cheek_left", 43.0, 21.0),
        _feature("p3", "cheek_left", 95.0, 22.0),
    ]
    quality_reports = {photo_id: _quality(photo_id) for photo_id in ("p1", "p2", "p3")}
    wb_confidence = {"p1": 1.0, "p2": 1.0, "p3": 0.2}

    aggregated = aggregate_features(features, quality_reports, wb_confidence)

    assert aggregated["cheek_left.l_star"] == 43.0


def test_aggregate_features_uses_circular_hue_median() -> None:
    features = [
        _feature("p1", "iris_left", 50.0, 359.0),
        _feature("p2", "iris_left", 52.0, 1.0),
        _feature("p3", "iris_left", 55.0, 20.0),
    ]
    quality_reports = {photo_id: _quality(photo_id) for photo_id in ("p1", "p2", "p3")}
    wb_confidence = {"p1": 1.0, "p2": 1.0, "p3": 0.2}

    aggregated = aggregate_features(features, quality_reports, wb_confidence)

    assert aggregated["iris_left.h_deg"] in {359.0, 1.0}


def test_reliability_caps_single_photo_to_low() -> None:
    reliability = compute_reliability(0.95, 0.95, 0.8, photo_count=1)

    assert reliability.score == 0.45
    assert reliability.bucket == "Low"
    assert "photo_count=1" in reliability.reasons
    assert "photo_count_cap=0.45" in reliability.reasons


def test_reliability_caps_two_photos_below_high() -> None:
    reliability = compute_reliability(0.95, 0.95, 0.8, photo_count=2)

    assert reliability.score == 0.69
    assert reliability.bucket == "Medium"
    assert "photo_count=2" in reliability.reasons
    assert "photo_count_cap=0.69" in reliability.reasons


def test_reliability_allows_high_confidence_at_three_photos() -> None:
    reliability = compute_reliability(0.95, 0.95, 0.8, photo_count=3)

    assert reliability.score > 0.75
    assert reliability.bucket == "High"
    assert "photo_count=3" in reliability.reasons
    assert not any(reason.startswith("photo_count_cap=") for reason in reliability.reasons)
