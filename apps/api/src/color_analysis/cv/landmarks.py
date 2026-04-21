import logging
import os
import urllib.request
from pathlib import Path

import mediapipe as mp

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
            output_facial_transformation_matrixes=False,
        )
        _face_landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
    except Exception:
        _landmarker_unavailable = True
        logger.exception("MediaPipe face landmarker is unavailable")
        return None
    return _face_landmarker


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

    lm = result.face_landmarks[0]

    # Bbox from the 468 face mesh points; iris points are indices 468-477
    face_lm = lm[:468]
    xs = [p.x * width for p in face_lm]
    ys = [p.y * height for p in face_lm]
    x0 = max(0, int(min(xs)))
    y0 = max(0, int(min(ys)))
    x1 = min(width, int(max(xs)))
    y1 = min(height, int(max(ys)))

    # Iris centers: index 468 = left iris center, 473 = right iris center
    left_eye = (int(lm[468].x * width), int(lm[468].y * height))
    right_eye = (int(lm[473].x * width), int(lm[473].y * height))

    return LandmarkDetection(
        face_count=1,
        landmarks=Landmarks(
            photo_id=photo.id,
            face_bbox=(x0, y0, x1, y1),
            left_eye_center=left_eye,
            right_eye_center=right_eye,
        ),
        available=True,
    )
