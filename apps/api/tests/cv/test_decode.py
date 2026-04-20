from pathlib import Path

from color_analysis.cv.decode import decode_photo
from color_analysis.cv.types import PhotoInput


def test_decode_resizes_and_hashes() -> None:
    fixture = Path(__file__).resolve().parents[1] / "fixtures/happy_path/photo_1.jpg"
    decoded = decode_photo(PhotoInput(id="1", filename=fixture.name, payload=fixture.read_bytes()))

    assert decoded.rgb.shape[1] <= 2048
    assert len(decoded.sha256) == 64
