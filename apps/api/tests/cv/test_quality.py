from pathlib import Path

from color_analysis.cv.decode import decode_photo
from color_analysis.cv.quality import evaluate_quality
from color_analysis.cv.types import PhotoInput


def test_quality_report_fields_present() -> None:
    fixture = Path(__file__).resolve().parents[1] / "fixtures/happy_path/photo_2.jpg"
    decoded = decode_photo(PhotoInput(id="2", filename=fixture.name, payload=fixture.read_bytes()))
    report = evaluate_quality(decoded)

    assert report.blur_score >= 0
    assert 0 <= report.exposure_score <= 1
