import math

import numpy as np

from color_analysis.cv.types import QualityReport, RegionFeatures


def _weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    sorted_weights = weights[order]
    cumulative = np.cumsum(sorted_weights)
    cutoff = sorted_weights.sum() / 2.0
    index = int(np.searchsorted(cumulative, cutoff, side="left"))
    return float(sorted_values[min(index, sorted_values.size - 1)])


def _circular_distance_degrees(a: float, b: float) -> float:
    return abs(((a - b + 180.0) % 360.0) - 180.0)


def _weighted_circular_median(values: np.ndarray, weights: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    normalized = np.mod(values, 360.0)
    best_value = float(normalized[0])
    best_cost = math.inf
    for candidate in normalized:
        cost = float(np.sum([weight * _circular_distance_degrees(candidate, value) for value, weight in zip(normalized, weights)]))
        if cost < best_cost - 1e-9:
            best_cost = cost
            best_value = float(candidate)
        elif abs(cost - best_cost) <= 1e-9 and candidate < best_value:
            best_value = float(candidate)
    return best_value


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
        if key.endswith(".h_deg"):
            aggregated[key] = _weighted_circular_median(arr, weights)
        else:
            aggregated[key] = _weighted_median(arr, weights)

    return aggregated
