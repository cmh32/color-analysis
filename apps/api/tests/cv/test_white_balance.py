import numpy as np

from color_analysis.cv.types import RegionMasks
from color_analysis.cv.white_balance import apply_white_balance


def _masks(shape: tuple[int, int], sclera: np.ndarray) -> RegionMasks:
    empty = np.zeros(shape, dtype=bool)
    return RegionMasks(
        photo_id="p",
        cheek_left=empty.copy(),
        cheek_right=empty.copy(),
        forehead=empty.copy(),
        iris_left=empty.copy(),
        iris_right=empty.copy(),
        sclera=sclera,
        hair=empty.copy(),
    )


def test_white_balance_uses_bright_neutral_sclera_subset() -> None:
    rgb = np.full((20, 20, 3), 150, dtype=np.uint8)
    sclera = np.zeros((20, 20), dtype=bool)
    sclera[6:14, 6:14] = True

    rgb[6:11, 6:14] = np.array([240, 220, 200], dtype=np.uint8)
    rgb[11:14, 6:14] = np.array([120, 90, 80], dtype=np.uint8)

    corrected, method, confidence = apply_white_balance(rgb, _masks((20, 20), sclera))

    assert method == "sclera"
    assert confidence == 1.0
    corrected_sample = corrected[7, 7]
    assert int(corrected_sample[0]) < 240
    assert int(corrected_sample[2]) > 200
    assert max(map(int, corrected_sample)) - min(map(int, corrected_sample)) < 40


def test_white_balance_skips_global_gray_world_when_no_good_reference_exists() -> None:
    rgb = np.full((12, 12, 3), [210, 170, 150], dtype=np.uint8)
    sclera = np.zeros((12, 12), dtype=bool)
    sclera[0:3, 0:4] = True

    corrected, method, confidence = apply_white_balance(rgb, _masks((12, 12), sclera))

    assert method == "none"
    assert confidence == 0.35
    assert np.array_equal(corrected, rgb)
