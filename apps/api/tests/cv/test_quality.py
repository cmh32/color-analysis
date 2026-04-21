from pathlib import Path

from color_analysis.cv.decode import decode_photo
from color_analysis.cv.quality import evaluate_quality
from color_analysis.cv.types import LandmarkDetection, Landmarks, PhotoInput


def test_quality_report_fields_present() -> None:
    fixture = Path(__file__).resolve().parents[1] / "fixtures/happy_path/photo_2.jpg"
    decoded = decode_photo(PhotoInput(id="2", filename=fixture.name, payload=fixture.read_bytes()))
    report = evaluate_quality(
        decoded,
        LandmarkDetection(
            face_count=1,
            landmarks=Landmarks(
                photo_id=decoded.id,
                face_bbox=(0, 0, decoded.rgb.shape[1], decoded.rgb.shape[0]),
                left_eye_center=(decoded.rgb.shape[1] // 3, decoded.rgb.shape[0] // 3),
                right_eye_center=(decoded.rgb.shape[1] * 2 // 3, decoded.rgb.shape[0] // 3),
            ),
            available=True,
        ),
    )

    assert report.blur_score >= 0
    assert 0 <= report.exposure_score <= 1
    assert report.face_count == 1


def test_quality_rejects_multiple_subjects() -> None:
    fixture = Path(__file__).resolve().parents[1] / "fixtures/happy_path/photo_2.jpg"
    decoded = decode_photo(PhotoInput(id="2", filename=fixture.name, payload=fixture.read_bytes()))

    report = evaluate_quality(decoded, LandmarkDetection(face_count=2, landmarks=None, available=True))

    assert report.accepted is False
    assert report.face_count == 2
    assert "multiple_subjects" in report.reasons


def test_quality_rejects_no_face() -> None:
    fixture = Path(__file__).resolve().parents[1] / "fixtures/happy_path/photo_2.jpg"
    decoded = decode_photo(PhotoInput(id="2", filename=fixture.name, payload=fixture.read_bytes()))

    report = evaluate_quality(decoded, LandmarkDetection(face_count=0, landmarks=None, available=True))

    assert report.accepted is False
    assert report.face_count == 0
    assert "no_face_detected" in report.reasons
