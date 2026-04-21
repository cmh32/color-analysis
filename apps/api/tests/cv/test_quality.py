from pathlib import Path

from color_analysis.cv.decode import decode_photo
from color_analysis.cv.quality import evaluate_quality
from color_analysis.cv.types import LandmarkDetection, PhotoInput

from .helpers import synthetic_landmarks


def _decoded_fixture() -> object:
    fixture = Path(__file__).resolve().parents[1] / "fixtures/happy_path/photo_2.jpg"
    return decode_photo(PhotoInput(id="2", filename=fixture.name, payload=fixture.read_bytes()))


def test_quality_report_fields_present() -> None:
    decoded = _decoded_fixture()
    report = evaluate_quality(
        decoded,
        LandmarkDetection(
            face_count=1,
            landmarks=synthetic_landmarks(photo_id=decoded.id, width=decoded.rgb.shape[1], height=decoded.rgb.shape[0]),
            available=True,
        ),
    )

    assert report.blur_score >= 0
    assert 0 <= report.exposure_score <= 1
    assert report.face_count == 1
    assert report.yaw_degrees == 0.0
    assert report.pitch_degrees == 0.0


def test_quality_rejects_multiple_subjects() -> None:
    decoded = _decoded_fixture()

    report = evaluate_quality(decoded, LandmarkDetection(face_count=2, landmarks=None, available=True))

    assert report.accepted is False
    assert report.face_count == 2
    assert "multiple_subjects" in report.reasons


def test_quality_rejects_no_face() -> None:
    decoded = _decoded_fixture()

    report = evaluate_quality(decoded, LandmarkDetection(face_count=0, landmarks=None, available=True))

    assert report.accepted is False
    assert report.face_count == 0
    assert "no_face_detected" in report.reasons


def test_quality_rejects_large_yaw() -> None:
    decoded = _decoded_fixture()
    landmarks = synthetic_landmarks(photo_id=decoded.id, width=decoded.rgb.shape[1], height=decoded.rgb.shape[0], yaw=22.0)

    report = evaluate_quality(decoded, LandmarkDetection(face_count=1, landmarks=landmarks, available=True))

    assert report.accepted is False
    assert report.yaw_degrees == 22.0
    assert "pose_yaw_too_large" in report.reasons


def test_quality_rejects_large_pitch() -> None:
    decoded = _decoded_fixture()
    landmarks = synthetic_landmarks(photo_id=decoded.id, width=decoded.rgb.shape[1], height=decoded.rgb.shape[0], pitch=-18.0)

    report = evaluate_quality(decoded, LandmarkDetection(face_count=1, landmarks=landmarks, available=True))

    assert report.accepted is False
    assert report.pitch_degrees == -18.0
    assert "pose_pitch_too_large" in report.reasons


def test_quality_rejects_tiny_region() -> None:
    decoded = _decoded_fixture()
    collapsed_cheek = {
        234: (120, 180),
        93: (120, 180),
        132: (120, 180),
        123: (120, 180),
        117: (120, 180),
        118: (120, 180),
        101: (120, 180),
        50: (120, 180),
        205: (120, 180),
        203: (120, 180),
        129: (120, 180),
    }
    landmarks = synthetic_landmarks(
        photo_id=decoded.id,
        width=decoded.rgb.shape[1],
        height=decoded.rgb.shape[0],
        overrides=collapsed_cheek,
    )

    report = evaluate_quality(decoded, LandmarkDetection(face_count=1, landmarks=landmarks, available=True))

    assert report.accepted is False
    assert "region_too_small:cheek_left" in report.reasons
