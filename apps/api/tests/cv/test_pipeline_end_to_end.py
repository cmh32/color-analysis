from pathlib import Path

from color_analysis.cv.pipeline import run
from color_analysis.cv.types import PhotoInput


def test_pipeline_happy_path() -> None:
    fixture_dir = Path(__file__).resolve().parents[1] / "fixtures/happy_path"
    photos = [
        PhotoInput(id=str(i), filename=path.name, payload=path.read_bytes())
        for i, path in enumerate(sorted(fixture_dir.glob("*.jpg")))
    ]

    result = run(photos)

    assert result.classification.top_2[0] in {"Spring", "Summer", "Autumn", "Winter"}
    assert result.reliability.bucket in {"High", "Medium", "Low"}
    assert len(result.trace) >= 2


def test_pipeline_handles_corrupt_image_without_crashing() -> None:
    fixture_dir = Path(__file__).resolve().parents[1] / "fixtures/happy_path"
    photos = [
        PhotoInput(id=str(i), filename=path.name, payload=path.read_bytes())
        for i, path in enumerate(sorted(fixture_dir.glob("*.jpg")))
    ]
    photos[0] = PhotoInput(id="bad", filename="corrupt.jpg", payload=b"not-a-real-image")

    result = run(photos)

    assert result.result_state == "insufficient_photos"
    assert "bad" in result.quality_reports
    assert result.quality_reports["bad"].accepted is False
    assert "decode_failed" in result.quality_reports["bad"].reasons
