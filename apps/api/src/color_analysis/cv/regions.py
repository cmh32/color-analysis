import numpy as np

from color_analysis.cv.types import Landmarks, RegionMasks


def _empty_mask(shape: tuple[int, int]) -> np.ndarray:
    return np.zeros(shape, dtype=bool)


def _rect(mask: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> np.ndarray:
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(mask.shape[1], x1)
    y1 = min(mask.shape[0], y1)
    mask[y0:y1, x0:x1] = True
    return mask


def build_region_masks(rgb_shape: tuple[int, int, int], landmarks: Landmarks) -> RegionMasks:
    height, width, _ = rgb_shape
    x0, y0, x1, y1 = landmarks.face_bbox

    cheek_left = _rect(_empty_mask((height, width)), x0 + 10, y0 + 120, x0 + 130, y0 + 240)
    cheek_right = _rect(_empty_mask((height, width)), x1 - 130, y0 + 120, x1 - 10, y0 + 240)
    forehead = _rect(_empty_mask((height, width)), x0 + 90, y0 + 10, x1 - 90, y0 + 100)

    iris_left = _rect(
        _empty_mask((height, width)),
        landmarks.left_eye_center[0] - 12,
        landmarks.left_eye_center[1] - 12,
        landmarks.left_eye_center[0] + 12,
        landmarks.left_eye_center[1] + 12,
    )
    iris_right = _rect(
        _empty_mask((height, width)),
        landmarks.right_eye_center[0] - 12,
        landmarks.right_eye_center[1] - 12,
        landmarks.right_eye_center[0] + 12,
        landmarks.right_eye_center[1] + 12,
    )

    sclera_left = _rect(
        _empty_mask((height, width)),
        landmarks.left_eye_center[0] - 30,
        landmarks.left_eye_center[1] - 10,
        landmarks.left_eye_center[0] + 30,
        landmarks.left_eye_center[1] + 10,
    )
    sclera_right = _rect(
        _empty_mask((height, width)),
        landmarks.right_eye_center[0] - 30,
        landmarks.right_eye_center[1] - 10,
        landmarks.right_eye_center[0] + 30,
        landmarks.right_eye_center[1] + 10,
    )
    sclera = (sclera_left | sclera_right) & ~(iris_left | iris_right)

    hair = _rect(_empty_mask((height, width)), x0 + 40, max(0, y0 - 80), x1 - 40, y0 + 20)

    return RegionMasks(
        photo_id=landmarks.photo_id,
        cheek_left=cheek_left,
        cheek_right=cheek_right,
        forehead=forehead,
        iris_left=iris_left,
        iris_right=iris_right,
        sclera=sclera,
        hair=hair,
    )
