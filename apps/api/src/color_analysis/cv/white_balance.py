import numpy as np

from color_analysis.cv.types import RegionMasks


def _clip_rgb(rgb: np.ndarray) -> np.ndarray:
    return np.clip(rgb, 0, 255).astype(np.uint8)


def apply_white_balance(rgb: np.ndarray, masks: RegionMasks) -> tuple[np.ndarray, str, float]:
    sclera_pixels = rgb[masks.sclera]
    if sclera_pixels.size >= 600:
        median = np.median(sclera_pixels.astype(np.float32), axis=0)
        target = float(np.mean(median))
        gains = np.where(median > 1e-3, target / median, 1.0)
        corrected = _clip_rgb(rgb.astype(np.float32) * gains)
        return corrected, "sclera", 1.0

    gray = np.mean(rgb.astype(np.float32), axis=(0, 1))
    target = float(np.mean(gray))
    gains = np.where(gray > 1e-3, target / gray, 1.0)
    corrected = _clip_rgb(rgb.astype(np.float32) * gains)
    return corrected, "gray_world", 0.6
