import numpy as np

from color_analysis.cv.types import RegionMasks

_MIN_SCLERA_PIXELS = 64
_MIN_NEUTRAL_SCLERA_PIXELS = 24
_GAIN_LIMITS = (0.85, 1.18)


def _clip_rgb(rgb: np.ndarray) -> np.ndarray:
    return np.clip(rgb, 0, 255).astype(np.uint8)


def _clip_gains(gains: np.ndarray) -> np.ndarray:
    lo, hi = _GAIN_LIMITS
    return np.clip(gains, lo, hi)


def _neutral_sclera_pixels(rgb: np.ndarray, masks: RegionMasks) -> np.ndarray:
    sclera_pixels = rgb[masks.sclera].astype(np.float32)
    if sclera_pixels.shape[0] < _MIN_SCLERA_PIXELS:
        return np.empty((0, 3), dtype=np.float32)

    luminance = np.mean(sclera_pixels, axis=1)
    channel_floor = np.min(sclera_pixels, axis=1)
    bright_cut = np.quantile(luminance, 0.55)
    floor_cut = np.quantile(channel_floor, 0.45)
    neutral = sclera_pixels[(luminance >= bright_cut) & (channel_floor >= floor_cut)]
    minimum_neutral = max(_MIN_NEUTRAL_SCLERA_PIXELS, int(np.ceil(sclera_pixels.shape[0] * 0.15)))
    return neutral if neutral.shape[0] >= minimum_neutral else np.empty((0, 3), dtype=np.float32)


def apply_white_balance(rgb: np.ndarray, masks: RegionMasks) -> tuple[np.ndarray, str, float]:
    sclera_pixels = _neutral_sclera_pixels(rgb, masks)
    if sclera_pixels.shape[0] >= _MIN_NEUTRAL_SCLERA_PIXELS:
        median = np.median(sclera_pixels, axis=0)
        target = float(np.mean(median))
        gains = _clip_gains(np.where(median > 1e-3, target / median, 1.0))
        corrected = _clip_rgb(rgb.astype(np.float32) * gains)
        return corrected, "sclera", 1.0

    return rgb.copy(), "none", 0.35
