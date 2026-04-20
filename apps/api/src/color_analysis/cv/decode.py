import hashlib
import io

import numpy as np
from PIL import Image, ImageOps

from color_analysis.cv.types import DecodedPhoto, PhotoInput


def decode_photo(photo: PhotoInput, max_edge: int = 2048) -> DecodedPhoto:
    image = Image.open(io.BytesIO(photo.payload))
    image = ImageOps.exif_transpose(image).convert("RGB")

    width, height = image.size
    scale = min(1.0, max_edge / max(width, height))
    if scale < 1.0:
        image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)

    rgb = np.asarray(image, dtype=np.uint8)
    digest = hashlib.sha256(photo.payload).hexdigest()
    return DecodedPhoto(id=photo.id, filename=photo.filename, rgb=rgb, sha256=digest)
