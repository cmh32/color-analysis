import math

from color_analysis.cv.features import _lab_to_rgb_hex
from color_analysis.db.models.aggregated_feature import AggregatedFeature
from color_analysis.db.models.classification import Classification
from color_analysis.schemas.analysis import AnalysisResult, Reliability, Scorecard

_HAIR_MIN_CHROMA = 6.0
_DISPLAY_PREFIX = "display."


def _build_color_swatches(features: list[AggregatedFeature]) -> dict[str, str] | None:
    lookup = {f.feature_name: f.feature_value for f in features}

    def avg_lab(prefixes: list[str], *, prefix: str = "") -> tuple[float, float, float] | None:
        ls, as_, bs = [], [], []
        for p in prefixes:
            base = f"{prefix}{p}"
            if all(f"{base}.{c}" in lookup for c in ("l_star", "a_star", "b_star")):
                ls.append(lookup[f"{base}.l_star"])
                as_.append(lookup[f"{base}.a_star"])
                bs.append(lookup[f"{base}.b_star"])
        return (sum(ls) / len(ls), sum(as_) / len(as_), sum(bs) / len(bs)) if ls else None

    swatches: dict[str, str] = {}
    for key, prefixes in [
        ("skin", ["cheek_left", "cheek_right"]),
        ("iris", ["iris_left", "iris_right"]),
        ("hair", ["hair"]),
    ]:
        lab = avg_lab(prefixes, prefix=_DISPLAY_PREFIX) or avg_lab(prefixes)
        if lab:
            l, a, b = lab
            if key == "hair" and math.sqrt(a**2 + b**2) < _HAIR_MIN_CHROMA:
                continue
            swatches[key] = _lab_to_rgb_hex(l, a, b)
    return swatches or None


def format_result(
    classification: Classification,
    aggregated_features: list[AggregatedFeature] | None = None,
) -> AnalysisResult:
    scorecard = Scorecard(**classification.scorecard)
    reliability = Reliability(
        score=classification.reliability,
        bucket=classification.reliability_bucket,
        reasons=["Based on photo quality, consistency, and classifier margin"],
    )

    return AnalysisResult(
        session_id=str(classification.session_id),
        top_2_seasons=(classification.primary_season, classification.secondary_season),
        scorecard=scorecard,
        reliability=reliability,
        result_state=classification.result_state,
        trace=[
            "decode -> quality -> landmarks -> regions -> white_balance",
            "features -> aggregate -> scorecard -> classify",
        ],
        color_swatches=_build_color_swatches(aggregated_features) if aggregated_features else None,
    )
