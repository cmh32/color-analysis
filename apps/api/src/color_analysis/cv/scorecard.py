import math

from color_analysis.cv.types import Scorecard


def _clip_unit(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _z_to_unit(value: float, mu: float, sd: float) -> float:
    if sd <= 1e-6:
        return 0.0
    return _clip_unit((value - mu) / (2.0 * sd))


def build_scorecard(aggregated: dict[str, float]) -> Scorecard:
    skin_hue = (aggregated.get("cheek_left.h_deg", 0.0) + aggregated.get("cheek_right.h_deg", 0.0)) / 2.0
    skin_ita = (aggregated.get("cheek_left.ita_deg", 0.0) + aggregated.get("cheek_right.ita_deg", 0.0)) / 2.0
    iris_c = (aggregated.get("iris_left.c_star", 0.0) + aggregated.get("iris_right.c_star", 0.0)) / 2.0

    warmth_raw = 0.7 * math.cos(math.radians(skin_hue - 70.0)) + 0.3 * _z_to_unit(skin_ita, 10.0, 20.0)
    value_raw = 0.6 * _z_to_unit(aggregated.get("cheek_left.l_star", 50.0), 55.0, 12.0) + 0.4 * _z_to_unit(
        aggregated.get("hair.l_star", 35.0), 45.0, 14.0
    )
    chroma_raw = _z_to_unit(max(iris_c, aggregated.get("cheek_left.c_star", 0.0)), 25.0, 12.0)
    contrast_raw = _z_to_unit(
        abs(aggregated.get("cheek_left.l_star", 50.0) - aggregated.get("hair.l_star", 45.0)), 20.0, 12.0
    )

    return Scorecard(
        warmth=_clip_unit(warmth_raw),
        value=_clip_unit(value_raw),
        chroma=_clip_unit(chroma_raw),
        contrast=_clip_unit(contrast_raw),
    )
