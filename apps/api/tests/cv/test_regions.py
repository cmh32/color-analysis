from pathlib import Path

from color_analysis.cv.decode import decode_photo
from color_analysis.cv.landmarks import detect_landmarks
from color_analysis.cv.regions import build_region_masks
from color_analysis.cv.types import PhotoInput


def test_region_masks_have_pixels() -> None:
    fixture = Path(__file__).resolve().parents[1] / "fixtures/happy_path/photo_3.jpg"
    decoded = decode_photo(PhotoInput(id="3", filename=fixture.name, payload=fixture.read_bytes()))
    landmarks = detect_landmarks(decoded)
    masks = build_region_masks(decoded.rgb.shape, landmarks)

    assert masks.cheek_left.any()
    assert masks.cheek_right.any()
    assert masks.forehead.any()
