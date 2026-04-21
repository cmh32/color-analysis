from pathlib import Path

from color_analysis.cv.pipeline import run
from color_analysis.cv.types import LandmarkDetection, Landmarks, PhotoInput


def _fixture_photos() -> list[PhotoInput]:
    fixture_dir = Path(__file__).resolve().parents[1] / "fixtures/happy_path"
    return [
        PhotoInput(id=str(i), filename=path.name, payload=path.read_bytes())
        for i, path in enumerate(sorted(fixture_dir.glob("*.jpg")))
    ]


def _single_face_detection(photo) -> LandmarkDetection:
    height, width, _ = photo.rgb.shape
    return LandmarkDetection(
        face_count=1,
        landmarks=Landmarks(
            photo_id=photo.id,
            face_bbox=(width // 5, height // 7, width * 4 // 5, height * 6 // 7),
            left_eye_center=(width // 3, height // 3),
            right_eye_center=(width * 2 // 3, height // 3),
        ),
        available=True,
    )


def test_pipeline_happy_path(monkeypatch) -> None:
    photos = _fixture_photos()
    monkeypatch.setattr("color_analysis.cv.pipeline.detect_landmarks", _single_face_detection)

    result = run(photos)

    assert result.classification.top_2[0] in {"Spring", "Summer", "Autumn", "Winter"}
    assert result.reliability.bucket in {"High", "Medium", "Low"}
    assert len(result.trace) >= 2


def test_pipeline_handles_corrupt_image_without_crashing() -> None:
    photos = _fixture_photos()
    photos[0] = PhotoInput(id="bad", filename="corrupt.jpg", payload=b"not-a-real-image")

    result = run(photos)

    assert result.result_state == "insufficient_photos"
    assert "bad" in result.quality_reports
    assert result.quality_reports["bad"].accepted is False
    assert "decode_failed" in result.quality_reports["bad"].reasons


def test_pipeline_returns_multiple_subjects_when_no_single_face_photos(monkeypatch) -> None:
    photos = _fixture_photos()

    def fake_detect_landmarks(photo: object) -> LandmarkDetection:
        del photo
        return LandmarkDetection(face_count=2, landmarks=None, available=True)

    monkeypatch.setattr("color_analysis.cv.pipeline.detect_landmarks", fake_detect_landmarks)

    result = run(photos)

    assert result.result_state == "multiple_subjects"
    assert all(report.face_count == 2 for report in result.quality_reports.values())


def test_pipeline_returns_no_face_detected_when_no_faces_found(monkeypatch) -> None:
    photos = _fixture_photos()

    def fake_detect_landmarks(photo: object) -> LandmarkDetection:
        del photo
        return LandmarkDetection(face_count=0, landmarks=None, available=True)

    monkeypatch.setattr("color_analysis.cv.pipeline.detect_landmarks", fake_detect_landmarks)

    result = run(photos)

    assert result.result_state == "no_face_detected"
    assert all(report.face_count == 0 for report in result.quality_reports.values())


def test_pipeline_happy_path_with_single_face_detections(monkeypatch) -> None:
    photos = _fixture_photos()
    monkeypatch.setattr("color_analysis.cv.pipeline.detect_landmarks", _single_face_detection)

    result = run(photos)

    assert result.result_state in {"ok", "ok_low_reliability"}
    assert result.classification.top_2[0] in {"Spring", "Summer", "Autumn", "Winter"}
