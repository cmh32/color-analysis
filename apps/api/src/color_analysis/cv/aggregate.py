import numpy as np

from color_analysis.cv.types import QualityReport, RegionFeatures


def aggregate_features(
    features: list[RegionFeatures],
    quality_reports: dict[str, QualityReport],
    wb_confidence: dict[str, float],
) -> dict[str, float]:
    values: dict[str, list[tuple[float, float]]] = {}

    for feature in features:
        quality = quality_reports[feature.photo_id]
        weight = max(0.01, (1.0 if quality.accepted else 0.3) * wb_confidence[feature.photo_id])
        for name in ("l_star", "a_star", "b_star", "c_star", "h_deg", "ita_deg"):
            key = f"{feature.region}.{name}"
            values.setdefault(key, []).append((getattr(feature, name), weight))

    aggregated: dict[str, float] = {}
    for key, points in values.items():
        arr = np.array([value for value, _ in points], dtype=np.float64)
        weights = np.array([weight for _, weight in points], dtype=np.float64)
        aggregated[key] = float(np.average(arr, weights=weights))

    return aggregated
