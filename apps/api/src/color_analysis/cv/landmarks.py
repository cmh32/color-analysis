from color_analysis.cv.types import DecodedPhoto, Landmarks


def detect_landmarks(photo: DecodedPhoto) -> Landmarks:
    height, width, _ = photo.rgb.shape

    # Conservative geometric fallback to preserve deterministic behavior
    x0 = int(width * 0.2)
    x1 = int(width * 0.8)
    y0 = int(height * 0.15)
    y1 = int(height * 0.85)

    left_eye = (int(width * 0.38), int(height * 0.4))
    right_eye = (int(width * 0.62), int(height * 0.4))

    return Landmarks(
        photo_id=photo.id,
        face_bbox=(x0, y0, x1, y1),
        left_eye_center=left_eye,
        right_eye_center=right_eye,
    )
