import math

from color_analysis.cv.types import Classification, Reliability, Scorecard

PROTOTYPES: dict[str, tuple[float, float, float, float]] = {
    "Spring": (0.65, 0.55, 0.5, 0.2),
    "Summer": (-0.55, 0.45, -0.35, -0.25),
    "Autumn": (0.55, -0.4, -0.1, 0.1),
    "Winter": (-0.65, -0.2, 0.65, 0.65),
}


def _distance(scorecard: Scorecard, proto: tuple[float, float, float, float]) -> float:
    point = (scorecard.warmth, scorecard.value, scorecard.chroma, scorecard.contrast)
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(point, proto, strict=False)))


def classify(scorecard: Scorecard) -> Classification:
    distances = {season: _distance(scorecard, proto) for season, proto in PROTOTYPES.items()}
    ranked = sorted(distances.items(), key=lambda x: x[1])
    top_1, top_2 = ranked[0][0], ranked[1][0]

    inverted = {season: 1.0 / (distance + 1e-6) for season, distance in distances.items()}
    total = sum(inverted.values())
    probabilities = {season: value / total for season, value in inverted.items()}
    margin = probabilities[top_1] - probabilities[top_2]

    return Classification(top_2=(top_1, top_2), probabilities=probabilities, margin=margin)


def compute_reliability(
    photo_quality_mean: float,
    consistency_score: float,
    margin: float,
    photo_count: int,
) -> Reliability:
    score = max(
        0.0,
        min(1.0, 0.4 * photo_quality_mean + 0.4 * consistency_score + 0.2 * min(1.0, margin / 0.8)),
    )
    cap: float | None = None
    if photo_count <= 0:
        cap = 0.0
    elif photo_count == 1:
        cap = 0.45
    elif photo_count == 2:
        cap = 0.69

    if cap is not None:
        score = min(score, cap)

    if score >= 0.75:
        bucket = "High"
    elif score >= 0.5:
        bucket = "Medium"
    else:
        bucket = "Low"

    reasons = (
        f"quality={photo_quality_mean:.2f}",
        f"consistency={consistency_score:.2f}",
        f"margin={margin:.2f}",
        f"photo_count={photo_count}",
        *(tuple([f"photo_count_cap={cap:.2f}"]) if cap is not None else ()),
    )

    return Reliability(score=score, bucket=bucket, reasons=reasons)
