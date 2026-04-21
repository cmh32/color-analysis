"""
Debug overlay: visualize region masks on an actual photo.

Usage (from apps/api with venv active):
    python scripts/debug_hair_mask.py /path/to/photo.jpg [output_dir]

Writes one PNG per region showing: original photo with the mask highlighted in
semi-transparent colour. Also writes a composite showing all regions at once.
"""

import hashlib
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from color_analysis.cv.landmarks import detect_landmarks
from color_analysis.cv.regions import build_region_masks
from color_analysis.cv.types import DecodedPhoto


REGION_COLORS = {
    "cheek_left":  (255, 100, 100),
    "cheek_right": (255, 160, 60),
    "forehead":    (255, 220, 80),
    "hair":        (80, 200, 120),
    "iris_left":   (80, 160, 255),
    "iris_right":  (80, 100, 255),
    "sclera":      (200, 200, 255),
}


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python scripts/debug_hair_mask.py <photo.jpg> [output_dir]")
        sys.exit(1)

    photo_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else photo_path.parent / "mask_debug"
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = photo_path.read_bytes()
    bgr = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if bgr is None:
        print(f"could not load {photo_path}")
        sys.exit(1)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    photo = DecodedPhoto(
        id="debug",
        filename=photo_path.name,
        rgb=rgb,
        sha256=hashlib.sha256(raw).hexdigest(),
    )

    detection = detect_landmarks(photo)
    if detection.landmarks is None:
        print(f"no face detected (face_count={detection.face_count}, available={detection.available})")
        sys.exit(1)

    masks = build_region_masks(rgb.shape, detection.landmarks)

    mask_map = {
        "cheek_left":  masks.cheek_left,
        "cheek_right": masks.cheek_right,
        "forehead":    masks.forehead,
        "hair":        masks.hair,
        "iris_left":   masks.iris_left,
        "iris_right":  masks.iris_right,
        "sclera":      masks.sclera,
    }

    composite = rgb.copy()
    for region, mask in mask_map.items():
        color = REGION_COLORS[region]
        pixel_count = int(np.count_nonzero(mask))

        individual = rgb.copy()
        overlay = np.zeros_like(rgb, dtype=np.uint8)
        overlay[mask] = color
        individual = cv2.addWeighted(individual, 0.6, overlay, 0.4, 0)
        cv2.putText(individual, f"{region}: {pixel_count}px", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        out_path = out_dir / f"{region}.png"
        cv2.imwrite(str(out_path), cv2.cvtColor(individual, cv2.COLOR_RGB2BGR))
        print(f"  {region:12s} {pixel_count:6d} px → {out_path}")

        overlay2 = np.zeros_like(rgb, dtype=np.uint8)
        overlay2[mask] = color
        composite = cv2.addWeighted(composite, 0.75, overlay2, 0.25, 0)

    composite_path = out_dir / "composite.png"
    cv2.imwrite(str(composite_path), cv2.cvtColor(composite, cv2.COLOR_RGB2BGR))
    print(f"\n  composite   → {composite_path}")


if __name__ == "__main__":
    main()
