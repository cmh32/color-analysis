import numpy as np

from color_analysis.cv.landmarks import detect_landmarks
from color_analysis.cv.types import DecodedPhoto

from .helpers import normalized_mesh_points, rotation_matrix


class _FakeResult:
    def __init__(self) -> None:
        self.face_landmarks = [normalized_mesh_points()]
        self.facial_transformation_matrixes = [rotation_matrix(yaw=12.0, pitch=-6.0, roll=4.0)]


class _FakeLandmarker:
    def detect(self, image: object) -> _FakeResult:
        del image
        return _FakeResult()


def test_detect_landmarks_returns_full_mesh_and_pose(monkeypatch) -> None:
    monkeypatch.setattr("color_analysis.cv.landmarks._get_face_landmarker", lambda: _FakeLandmarker())
    photo = DecodedPhoto(
        id="photo",
        filename="photo.jpg",
        rgb=np.zeros((480, 640, 3), dtype=np.uint8),
        sha256="deadbeef",
    )

    detection = detect_landmarks(photo)

    assert detection.available is True
    assert detection.face_count == 1
    assert detection.landmarks is not None
    assert len(detection.landmarks.mesh_points) == 478
    assert detection.landmarks.left_eye_center == detection.landmarks.mesh_points[468]
    assert detection.landmarks.right_eye_center == detection.landmarks.mesh_points[473]
    assert round(detection.landmarks.pose_yaw_degrees, 1) == 12.0
    assert round(detection.landmarks.pose_pitch_degrees, 1) == -6.0
    assert round(detection.landmarks.pose_roll_degrees, 1) == 4.0
