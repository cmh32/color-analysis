import numpy as np
import pytest

from color_analysis.cv.regions import _expand_upper_band, build_region_masks

from .helpers import synthetic_landmarks


def _is_axis_aligned_rectangle(mask: np.ndarray) -> bool:
    ys, xs = np.nonzero(mask)
    if ys.size == 0:
        return False
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    return bool(mask[y0:y1, x0:x1].all() and int(mask.sum()) == (y1 - y0) * (x1 - x0))


def test_region_masks_are_polygonal_and_nonempty() -> None:
    landmarks = synthetic_landmarks()

    masks = build_region_masks((480, 640, 3), landmarks)

    assert masks.cheek_left.any()
    assert masks.cheek_right.any()
    assert masks.forehead.any()
    assert masks.iris_left.any()
    assert masks.iris_right.any()
    assert masks.sclera.any()
    assert not _is_axis_aligned_rectangle(masks.cheek_left)
    assert not _is_axis_aligned_rectangle(masks.cheek_right)
    assert not _is_axis_aligned_rectangle(masks.forehead)
    assert not _is_axis_aligned_rectangle(masks.iris_left)


def test_sclera_excludes_iris_pixels() -> None:
    landmarks = synthetic_landmarks()

    masks = build_region_masks((480, 640, 3), landmarks)

    assert not np.any(masks.sclera & masks.iris_left)
    assert not np.any(masks.sclera & masks.iris_right)


def test_region_masks_require_landmarks() -> None:
    with pytest.raises(ValueError, match="landmarks are required"):
        build_region_masks((800, 640, 3), None)


def test_hair_mask_stays_above_forehead_boundary() -> None:
    landmarks = synthetic_landmarks()

    masks = build_region_masks((480, 640, 3), landmarks)

    forehead_ys, _ = np.nonzero(masks.forehead)
    hair_ys, _ = np.nonzero(masks.hair)

    assert hair_ys.size > 0
    assert forehead_ys.size > 0
    assert int(hair_ys.max()) < int(np.quantile(forehead_ys, 0.12))


def test_hair_upper_band_has_a_domed_center() -> None:
    landmarks = synthetic_landmarks()
    forehead_upper = [landmarks.mesh_points[index] for index in (54, 103, 67, 109, 10, 338, 297, 332, 284)]

    expanded = _expand_upper_band(forehead_upper, (480, 640, 3), landmarks.face_bbox)

    midpoint = len(expanded) // 2
    center_y = expanded[midpoint][1]
    edge_y = max(expanded[0][1], expanded[-1][1])

    assert center_y < edge_y
