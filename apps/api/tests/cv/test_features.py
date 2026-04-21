import numpy as np

from color_analysis.cv.features import _lab_to_rgb_hex, extract_features
from color_analysis.cv.types import RegionMasks


def _empty_masks(shape: tuple[int, int]) -> dict[str, np.ndarray]:
    return {name: np.zeros(shape, dtype=bool) for name in (
        "cheek_left",
        "cheek_right",
        "forehead",
        "iris_left",
        "iris_right",
        "sclera",
        "hair",
    )}


def _masks(shape: tuple[int, int], **overrides: np.ndarray) -> RegionMasks:
    values = _empty_masks(shape)
    values.update(overrides)
    return RegionMasks(photo_id="p", **values)


def test_extract_features_focuses_upper_cheek_skin_over_lower_beard() -> None:
    rgb = np.zeros((20, 20, 3), dtype=np.uint8)
    cheek = np.zeros((20, 20), dtype=bool)
    cheek[2:18, 2:18] = True
    rgb[2:10, 2:18] = np.array([232, 184, 170], dtype=np.uint8)
    rgb[10:18, 2:18] = np.array([144, 137, 132], dtype=np.uint8)

    feature = next(f for f in extract_features("p", rgb, _masks((20, 20), cheek_left=cheek)) if f.region == "cheek_left")

    assert _lab_to_rgb_hex(feature.l_star, feature.a_star, feature.b_star) == "#e8b8aa"


def test_extract_features_focuses_lower_hair_band_over_background() -> None:
    rgb = np.zeros((24, 24, 3), dtype=np.uint8)
    hair = np.zeros((24, 24), dtype=bool)
    hair[2:22, 3:21] = True
    rgb[2:12, 3:21] = np.array([202, 203, 202], dtype=np.uint8)
    rgb[12:22, 3:21] = np.array([212, 186, 132], dtype=np.uint8)

    feature = next(f for f in extract_features("p", rgb, _masks((24, 24), hair=hair)) if f.region == "hair")

    assert _lab_to_rgb_hex(feature.l_star, feature.a_star, feature.b_star) == "#d4ba84"
