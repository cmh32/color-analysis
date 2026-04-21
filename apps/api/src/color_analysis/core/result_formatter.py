import math

from color_analysis.cv.features import _lab_to_rgb_hex
from color_analysis.db.models.aggregated_feature import AggregatedFeature
from color_analysis.db.models.classification import Classification
from color_analysis.schemas.analysis import (
    AnalysisResult,
    AxisExplanation,
    MeasurementDetail,
    MeasurementExplanation,
    MeasurementPhoto,
    MeasurementReading,
    Reliability,
    Scorecard,
)

_HAIR_MIN_CHROMA = 6.0
_DISPLAY_PREFIX = "display."


def _feature_lookup(features: list[AggregatedFeature]) -> dict[str, float]:
    return {f.feature_name: f.feature_value for f in features}


def _avg_lab(lookup: dict[str, float], prefixes: list[str], *, prefix: str = "") -> tuple[float, float, float] | None:
    ls, as_, bs = [], [], []
    for p in prefixes:
        base = f"{prefix}{p}"
        if all(f"{base}.{c}" in lookup for c in ("l_star", "a_star", "b_star")):
            ls.append(lookup[f"{base}.l_star"])
            as_.append(lookup[f"{base}.a_star"])
            bs.append(lookup[f"{base}.b_star"])
    return (sum(ls) / len(ls), sum(as_) / len(as_), sum(bs) / len(bs)) if ls else None


def _measurement_lab(
    lookup: dict[str, float],
    prefixes: list[str],
) -> tuple[tuple[float, float, float] | None, tuple[float, float, float] | None]:
    display = _avg_lab(lookup, prefixes, prefix=_DISPLAY_PREFIX)
    analysis = _avg_lab(lookup, prefixes)
    return display or analysis, analysis or display


def _format_num(value: float, suffix: str = "") -> str:
    return f"{value:.1f}{suffix}"


def _skin_summary(l_star: float, a_star: float, b_star: float) -> str:
    if l_star >= 78:
        depth = "very fair"
    elif l_star >= 68:
        depth = "fair"
    elif l_star >= 58:
        depth = "light"
    elif l_star >= 48:
        depth = "medium"
    else:
        depth = "deeper"

    if b_star >= 14 and a_star >= 4:
        undertone = "a peachy warmth"
    elif b_star >= 10:
        undertone = "a soft golden warmth"
    elif a_star >= 6:
        undertone = "a gentle pink cast"
    else:
        undertone = "a fairly neutral balance"
    return f"We read your skin as {depth} with {undertone}."


def _hair_summary(l_star: float, a_star: float, b_star: float, chroma: float) -> str:
    if chroma < _HAIR_MIN_CHROMA:
        return "We could not read your hair color clearly enough for it to be a strong signal."

    if l_star >= 62:
        depth = "light"
    elif l_star >= 48:
        depth = "medium"
    else:
        depth = "deeper"

    if a_star >= 10 and b_star >= 18:
        color = "coppery"
    elif b_star >= 16:
        color = "golden"
    elif a_star <= 2 and b_star <= 8:
        color = "ashy"
    else:
        color = "soft warm"

    if l_star >= 58:
        family = "blonde"
    elif l_star >= 42:
        family = "brown"
    else:
        family = "brown"
    return f"We read your hair as {depth} {color} {family}."


def _eyes_summary(l_star: float, a_star: float, b_star: float, chroma: float) -> str:
    if chroma < 8:
        family = "soft gray"
    elif b_star <= -10 and a_star <= 1:
        family = "blue-gray"
    elif a_star <= -6 and b_star >= 4:
        family = "green"
    elif a_star >= 6 and b_star >= 12:
        family = "hazel"
    else:
        family = "muted gray-blue"

    if l_star >= 55:
        depth = "lighter"
    elif l_star >= 40:
        depth = "medium"
    else:
        depth = "deeper"
    return f"We read your eyes as {depth} {family}. They matter most when we judge softness versus clarity."


def _technical_details(lab: tuple[float, float, float] | None) -> list[MeasurementDetail]:
    if lab is None:
        return []
    l_star, a_star, b_star = lab
    chroma = math.sqrt(a_star**2 + b_star**2)
    hue = (math.degrees(math.atan2(b_star, a_star)) + 360.0) % 360.0
    return [
        MeasurementDetail(label="Measured lightness", value=_format_num(l_star)),
        MeasurementDetail(label="Color strength", value=_format_num(chroma)),
        MeasurementDetail(label="Hue angle", value=_format_num(hue, "°")),
    ]


def _build_color_swatches(features: list[AggregatedFeature]) -> dict[str, str] | None:
    lookup = _feature_lookup(features)
    swatches: dict[str, str] = {}
    for key, prefixes in [
        ("skin", ["cheek_left", "cheek_right"]),
        ("iris", ["iris_left", "iris_right"]),
        ("hair", ["hair"]),
    ]:
        lab = _avg_lab(lookup, prefixes, prefix=_DISPLAY_PREFIX) or _avg_lab(lookup, prefixes)
        if lab:
            l_star, a_star, b_star = lab
            if key == "hair" and math.sqrt(a_star**2 + b_star**2) < _HAIR_MIN_CHROMA:
                continue
            swatches[key] = _lab_to_rgb_hex(l_star, a_star, b_star)
    return swatches or None


def _axis_summary(label: str, value: float) -> str:
    if label == "warmth":
        if value >= 0.25:
            return "Your coloring leans warm overall, driven mostly by the undertone we measured in your skin."
        if value <= -0.25:
            return "Your coloring leans cool overall, driven mostly by the undertone we measured in your skin."
        return "Your coloring sits close to neutral, so skin undertone did not pull strongly warm or cool."
    if label == "value":
        if value >= 0.25:
            return "Overall, your features read lighter than deep when we compare your skin and hair."
        if value <= -0.25:
            return "Overall, your features read deeper than light when we compare your skin and hair."
        return "Overall depth sits near the middle when we compare your skin and hair."
    if label == "chroma":
        if value >= 0.25:
            return "Your coloring reads clearer and more vivid than muted, especially through your eyes and skin."
        if value <= -0.25:
            return "Your coloring reads softer and more muted than vivid, especially through your eyes and skin."
        return "Your coloring sits between soft and vivid rather than strongly at either end."
    if value >= 0.25:
        return "There is a noticeable difference between your skin, hair, and eyes, which creates stronger contrast."
    if value <= -0.25:
        return "The difference between your skin, hair, and eyes stays softer, which creates lower contrast."
    return "The contrast between your skin, hair, and eyes sits close to the middle."


def _build_measurement_explanation(
    features: list[AggregatedFeature],
    scorecard: Scorecard,
    measurement_photos: list[MeasurementPhoto],
) -> MeasurementExplanation | None:
    lookup = _feature_lookup(features)

    skin_display, skin_analysis = _measurement_lab(lookup, ["cheek_left", "cheek_right"])
    eye_display, eye_analysis = _measurement_lab(lookup, ["iris_left", "iris_right"])
    hair_display, hair_analysis = _measurement_lab(lookup, ["hair"])

    readings: list[MeasurementReading] = []
    if skin_display is not None:
        readings.append(
            MeasurementReading(
                key="skin",
                label="Skin",
                summary=_skin_summary(*skin_display),
                swatch=_lab_to_rgb_hex(*skin_display),
                technical_details=_technical_details(skin_analysis),
            )
        )
    if hair_display is not None:
        hair_chroma = math.sqrt(hair_display[1] ** 2 + hair_display[2] ** 2)
        readings.append(
            MeasurementReading(
                key="hair",
                label="Hair",
                summary=_hair_summary(*hair_display, hair_chroma),
                swatch=_lab_to_rgb_hex(*hair_display) if hair_chroma >= _HAIR_MIN_CHROMA else None,
                technical_details=_technical_details(hair_analysis),
            )
        )
    if eye_display is not None:
        readings.append(
            MeasurementReading(
                key="eyes",
                label="Eyes",
                summary=_eyes_summary(*eye_display, math.sqrt(eye_display[1] ** 2 + eye_display[2] ** 2)),
                swatch=_lab_to_rgb_hex(*eye_display),
                technical_details=_technical_details(eye_analysis),
            )
        )

    if not measurement_photos and not readings:
        return None

    axis_explanations = [
        AxisExplanation(key="warmth", label="Warmth", summary=_axis_summary("warmth", scorecard.warmth)),
        AxisExplanation(key="value", label="Depth", summary=_axis_summary("value", scorecard.value)),
        AxisExplanation(key="chroma", label="Softness", summary=_axis_summary("chroma", scorecard.chroma)),
        AxisExplanation(key="contrast", label="Contrast", summary=_axis_summary("contrast", scorecard.contrast)),
    ]

    photo_count = len(measurement_photos)
    note = (
        "The final result blends measurements from all of your accepted photos. This viewer shows one photo at a time so you can see where the readings came from."
        if photo_count > 1
        else "This viewer shows the photo we used to illustrate where the readings came from."
    )
    return MeasurementExplanation(
        note=note,
        photos=measurement_photos,
        readings=readings,
        axis_explanations=axis_explanations,
    )


def format_result(
    classification: Classification,
    aggregated_features: list[AggregatedFeature] | None = None,
    measurement_photos: list[MeasurementPhoto] | None = None,
) -> AnalysisResult:
    scorecard = Scorecard(**classification.scorecard)
    reliability = Reliability(
        score=classification.reliability,
        bucket=classification.reliability_bucket,
        reasons=["Based on photo quality, consistency, and classifier margin"],
    )

    explanation = None
    if aggregated_features:
        explanation = _build_measurement_explanation(aggregated_features, scorecard, measurement_photos or [])

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
        measurement_explanation=explanation,
    )
