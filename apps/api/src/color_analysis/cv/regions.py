import math

import numpy as np
from PIL import Image, ImageDraw

from color_analysis.cv.types import Landmarks, RegionMasks

_LEFT_CHEEK_INDICES = (234, 93, 132, 123, 117, 118, 101, 50, 205, 203, 129)
_RIGHT_CHEEK_INDICES = (454, 323, 361, 352, 346, 347, 330, 280, 425, 423, 358)
_FOREHEAD_UPPER_INDICES = (54, 103, 67, 109, 10, 338, 297, 332, 284)
_FOREHEAD_LOWER_INDICES = (300, 293, 334, 296, 336, 107, 66, 105, 63, 70)
_LEFT_EYE_INDICES = (33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246)
_RIGHT_EYE_INDICES = (263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466)
_LEFT_IRIS_INDICES = (468, 469, 470, 471, 472)
_RIGHT_IRIS_INDICES = (473, 474, 475, 476, 477)

_FACE_AREA_THRESHOLDS: dict[str, float] = {
    "cheek_left": 0.008,
    "cheek_right": 0.008,
    "forehead": 0.010,
    "hair": 0.010,
}
_ABSOLUTE_THRESHOLDS: dict[str, int] = {
    "iris_left": 25,
    "iris_right": 25,
    "sclera": 80,
}


def _empty_mask(shape: tuple[int, int]) -> np.ndarray:
    return np.zeros(shape, dtype=bool)


def _points_from_indices(mesh_points: tuple[tuple[int, int], ...], indices: tuple[int, ...]) -> list[tuple[int, int]]:
    max_index = max(indices)
    if len(mesh_points) <= max_index:
        raise ValueError("full 478-point mesh is required to build region masks")
    return [mesh_points[index] for index in indices]


def _polygon_mask(shape: tuple[int, int], points: list[tuple[int, int]]) -> np.ndarray:
    if len(points) < 3:
        return _empty_mask(shape)
    image = Image.new("1", (shape[1], shape[0]), 0)
    draw = ImageDraw.Draw(image)
    draw.polygon(points, outline=1, fill=1)
    return np.array(image, dtype=bool)


def _expand_upper_band(
    points: list[tuple[int, int]],
    rgb_shape: tuple[int, int, int],
    face_bbox: tuple[int, int, int, int],
) -> list[tuple[int, int]]:
    height, width, _ = rgb_shape
    x0, y0, x1, y1 = face_bbox
    face_height = max(1, y1 - y0)
    center_x = (x0 + x1) / 2.0
    expanded: list[tuple[int, int]] = []
    for x, y in points:
        dx = x - center_x
        expanded_x = int(round(x + dx * 0.08))
        expanded_y = int(round(y - face_height * 0.22))
        expanded.append((max(0, min(width - 1, expanded_x)), max(0, min(height - 1, expanded_y))))
    return expanded


def _face_area(face_bbox: tuple[int, int, int, int]) -> int:
    x0, y0, x1, y1 = face_bbox
    return max(1, (x1 - x0) * (y1 - y0))


def minimum_region_pixels(region: str, face_bbox: tuple[int, int, int, int]) -> int:
    if region in _ABSOLUTE_THRESHOLDS:
        return _ABSOLUTE_THRESHOLDS[region]
    ratio = _FACE_AREA_THRESHOLDS[region]
    return max(1, int(math.ceil(_face_area(face_bbox) * ratio)))


def region_pixel_counts(masks: RegionMasks) -> dict[str, int]:
    return {
        "cheek_left": int(np.count_nonzero(masks.cheek_left)),
        "cheek_right": int(np.count_nonzero(masks.cheek_right)),
        "forehead": int(np.count_nonzero(masks.forehead)),
        "iris_left": int(np.count_nonzero(masks.iris_left)),
        "iris_right": int(np.count_nonzero(masks.iris_right)),
        "sclera": int(np.count_nonzero(masks.sclera)),
        "hair": int(np.count_nonzero(masks.hair)),
    }


def find_undersized_regions(masks: RegionMasks, landmarks: Landmarks) -> tuple[str, ...]:
    failures: list[str] = []
    for region, count in region_pixel_counts(masks).items():
        if count < minimum_region_pixels(region, landmarks.face_bbox):
            failures.append(f"region_too_small:{region}")
    return tuple(failures)


def build_region_masks(rgb_shape: tuple[int, int, int], landmarks: Landmarks | None) -> RegionMasks:
    if landmarks is None:
        raise ValueError("landmarks are required to build region masks")

    height, width, _ = rgb_shape
    shape = (height, width)
    mesh_points = landmarks.mesh_points
    if len(mesh_points) < 478:
        raise ValueError("full 478-point mesh is required to build region masks")

    cheek_left = _polygon_mask(shape, _points_from_indices(mesh_points, _LEFT_CHEEK_INDICES))
    cheek_right = _polygon_mask(shape, _points_from_indices(mesh_points, _RIGHT_CHEEK_INDICES))

    forehead_upper = _points_from_indices(mesh_points, _FOREHEAD_UPPER_INDICES)
    forehead_lower = _points_from_indices(mesh_points, _FOREHEAD_LOWER_INDICES)
    forehead = _polygon_mask(shape, forehead_upper + forehead_lower)

    iris_left = _polygon_mask(shape, _points_from_indices(mesh_points, _LEFT_IRIS_INDICES))
    iris_right = _polygon_mask(shape, _points_from_indices(mesh_points, _RIGHT_IRIS_INDICES))

    sclera_left = _polygon_mask(shape, _points_from_indices(mesh_points, _LEFT_EYE_INDICES))
    sclera_right = _polygon_mask(shape, _points_from_indices(mesh_points, _RIGHT_EYE_INDICES))
    sclera = (sclera_left | sclera_right) & ~(iris_left | iris_right)

    hair_upper = _expand_upper_band(forehead_upper, rgb_shape, landmarks.face_bbox)
    hair = _polygon_mask(shape, hair_upper + list(reversed(forehead_upper)))

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
