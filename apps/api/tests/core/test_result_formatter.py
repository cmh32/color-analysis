import uuid

from color_analysis.core.result_formatter import format_result
from color_analysis.db.models.aggregated_feature import AggregatedFeature
from color_analysis.db.models.classification import Classification


def _classification() -> Classification:
    return Classification(
        session_id=uuid.uuid4(),
        primary_season="Summer",
        secondary_season="Winter",
        scorecard={"warmth": 0.1, "value": 0.2, "chroma": 0.3, "contrast": 0.4},
        probabilities={"Spring": 0.1, "Summer": 0.5, "Autumn": 0.1, "Winter": 0.3},
        reliability=0.82,
        reliability_bucket="High",
        result_state="ok",
    )


def _feature(session_id: uuid.UUID, feature_name: str, value: float) -> AggregatedFeature:
    return AggregatedFeature(session_id=session_id, feature_name=feature_name, feature_value=value, spread=0.0)


def test_format_result_prefers_display_prefixed_swatches() -> None:
    classification = _classification()
    session_id = classification.session_id
    features = [
        _feature(session_id, "cheek_left.l_star", 68.0),
        _feature(session_id, "cheek_left.a_star", 2.0),
        _feature(session_id, "cheek_left.b_star", 8.0),
        _feature(session_id, "cheek_right.l_star", 68.0),
        _feature(session_id, "cheek_right.a_star", 2.0),
        _feature(session_id, "cheek_right.b_star", 8.0),
        _feature(session_id, "display.cheek_left.l_star", 68.0),
        _feature(session_id, "display.cheek_left.a_star", 8.0),
        _feature(session_id, "display.cheek_left.b_star", 16.0),
        _feature(session_id, "display.cheek_right.l_star", 68.0),
        _feature(session_id, "display.cheek_right.a_star", 8.0),
        _feature(session_id, "display.cheek_right.b_star", 16.0),
    ]

    result = format_result(classification, features)

    assert result.color_swatches is not None
    assert result.color_swatches["skin"] == "#bfa089"


def test_format_result_falls_back_to_classifier_features_when_display_values_are_missing() -> None:
    classification = _classification()
    session_id = classification.session_id
    features = [
        _feature(session_id, "iris_left.l_star", 45.0),
        _feature(session_id, "iris_left.a_star", -4.0),
        _feature(session_id, "iris_left.b_star", -12.0),
        _feature(session_id, "iris_right.l_star", 45.0),
        _feature(session_id, "iris_right.a_star", -4.0),
        _feature(session_id, "iris_right.b_star", -12.0),
    ]

    result = format_result(classification, features)

    assert result.color_swatches is not None
    assert result.color_swatches["iris"] == "#576d7e"
