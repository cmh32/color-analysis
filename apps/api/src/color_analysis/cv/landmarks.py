import logging
import math
import os
import urllib.request
from pathlib import Path

import mediapipe as mp
import numpy as np

from color_analysis.cv.types import DecodedPhoto, LandmarkDetection, Landmarks

logger = logging.getLogger(__name__)

_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
)
_MODEL_CACHE = Path(os.environ.get("MEDIAPIPE_MODEL_DIR", Path.home() / ".cache" / "color_analysis"))
_MODEL_PATH = _MODEL_CACHE / "face_landmarker.task"

_face_landmarker: mp.tasks.vision.FaceLandmarker | None = None
_landmarker_unavailable = False


def _get_face_landmarker() -> mp.tasks.vision.FaceLandmarker | None:
    global _face_landmarker, _landmarker_unavailable
    if _face_landmarker is not None:
        return _face_landmarker
    if _landmarker_unavailable:
        return None

    try:
        if not _MODEL_PATH.exists():
            _MODEL_CACHE.mkdir(parents=True, exist_ok=True)
            logger.info("Downloading MediaPipe face landmarker model to %s", _MODEL_PATH)
            try:
                import certifi

                ssl_ctx: object = __import__("ssl").create_default_context(cafile=certifi.where())
            except ModuleNotFoundError:
                ssl_ctx = None
            if ssl_ctx is not None:
                with urllib.request.urlopen(urllib.request.Request(_MODEL_URL), context=ssl_ctx) as resp:  # type: ignore[arg-type]
                    _MODEL_PATH.write_bytes(resp.read())
            else:
                urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)

        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(_MODEL_PATH)),
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_faces=4,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=True,
        )
        _face_landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
    except Exception:
        _landmarker_unavailable = True
        logger.exception("MediaPipe face landmarker is unavailable")
        return None
    return _face_landmarker


def _clamp_pixel(value: float, limit: int) -> int:
    if limit <= 0:
        return 0
    return max(0, min(limit - 1, int(round(value))))


def _normalized_to_pixel_points(
    raw_points: list[object],
    width: int,
    height: int,
) -> tuple[tuple[int, int], ...]:
    return tuple(
        (
            _clamp_pixel(getattr(point, "x", 0.0) * (width - 1), width),
            _clamp_pixel(getattr(point, "y", 0.0) * (height - 1), height),
        )
        for point in raw_points
    )


def _extract_pose_degrees(matrix: np.ndarray | None) -> tuple[float, float, float]:
    if matrix is None:
        return 0.0, 0.0, 0.0

    arr = np.asarray(matrix, dtype=np.float64)
    if arr.shape not in {(4, 4), (3, 4), (3, 3)}:
        return 0.0, 0.0, 0.0

    rot_scale = arr[:3, :3]
    try:
        u, _, vt = np.linalg.svd(rot_scale)
    except np.linalg.LinAlgError:
        return 0.0, 0.0, 0.0

    rotation = u @ vt
    if np.linalg.det(rotation) < 0:
        vt[-1, :] *= -1.0
        rotation = u @ vt

    sin_yaw = float(np.clip(-rotation[2, 0], -1.0, 1.0))
    yaw = math.degrees(math.asin(sin_yaw))
    pitch = math.degrees(math.atan2(rotation[2, 1], rotation[2, 2]))
    roll = math.degrees(math.atan2(rotation[1, 0], rotation[0, 0]))
    return yaw, pitch, roll


def detect_landmarks(photo: DecodedPhoto) -> LandmarkDetection:
    height, width, _ = photo.rgb.shape
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=photo.rgb)
    landmarker = _get_face_landmarker()
    if landmarker is None:
        return LandmarkDetection(face_count=0, landmarks=None, available=False)
    result = landmarker.detect(mp_image)

    face_count = len(result.face_landmarks)
    if face_count != 1:
        return LandmarkDetection(face_count=face_count, landmarks=None, available=True)

    mesh_points = _normalized_to_pixel_points(result.face_landmarks[0], width, height)
    face_points = mesh_points[:468]
    xs = [point[0] for point in face_points]
    ys = [point[1] for point in face_points]
    x0 = max(0, min(xs))
    y0 = max(0, min(ys))
    x1 = min(width, max(xs) + 1)
    y1 = min(height, max(ys) + 1)

    left_eye = mesh_points[468]
    right_eye = mesh_points[473]

    matrix = result.facial_transformation_matrixes[0] if result.facial_transformation_matrixes else None
    yaw, pitch, roll = _extract_pose_degrees(matrix)

    return LandmarkDetection(
        face_count=1,
        landmarks=Landmarks(
            photo_id=photo.id,
            face_bbox=(x0, y0, x1, y1),
            left_eye_center=left_eye,
            right_eye_center=right_eye,
            mesh_points=mesh_points,
            pose_yaw_degrees=yaw,
            pose_pitch_degrees=pitch,
            pose_roll_degrees=roll,
        ),
        available=True,
    )
