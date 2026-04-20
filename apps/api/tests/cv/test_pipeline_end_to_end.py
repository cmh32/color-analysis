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
