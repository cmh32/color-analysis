import numpy as np

from color_analysis.cv.types import RegionFeatures, RegionMasks

_REGION_CLEANUP_LIMITS: dict[str, tuple[float, float, float]] = {
    "cheek_left": (3.0, 2.5, 2.5),
    "cheek_right": (3.0, 2.5, 2.5),
    "forehead": (3.0, 2.5, 2.5),
    "hair": (3.0, 2.5, 2.5),
    "iris_left": (2.5, 2.5, 2.5),
    "iris_right": (2.5, 2.5, 2.5),
    "sclera": (2.5, 2.0, 2.0),
}


def _rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    rgb_f = rgb.astype(np.float32) / 255.0
    rgb_f = np.where(rgb_f <= 0.04045, rgb_f / 12.92, ((rgb_f + 0.055) / 1.055) ** 2.4)

    mat = np.array(
        [
            [0.4124, 0.3576, 0.1805],
            [0.2126, 0.7152, 0.0722],
            [0.0193, 0.1192, 0.9505],
        ],
        dtype=np.float32,
    )
    xyz = np.tensordot(rgb_f, mat.T, axes=1)

    x = xyz[..., 0] / 0.95047
    y = xyz[..., 1] / 1.0
    z = xyz[..., 2] / 1.08883

    epsilon = 216 / 24389
    kappa = 24389 / 27

    def f(t: np.ndarray) -> np.ndarray:
        return np.where(t > epsilon, np.cbrt(t), (kappa * t + 16) / 116)

    fx = f(x)
    fy = f(y)
    fz = f(z)

    l_star = 116 * fy - 16
    a_star = 500 * (fx - fy)
    b_star = 200 * (fy - fz)

    return np.stack([l_star, a_star, b_star], axis=-1)


def _clean_region_pixels(region: str, pixels: np.ndarray) -> np.ndarray:
    if pixels.shape[0] < 8:
        return pixels

    limits = _REGION_CLEANUP_LIMITS[region]
    median = np.median(pixels, axis=0)
    mad = np.median(np.abs(pixels - median), axis=0)
    mad = np.where(mad > 1e-6, mad, 1e-6)

    keep = np.ones(pixels.shape[0], dtype=bool)
    for idx, limit in enumerate(limits):
        keep &= np.abs(pixels[:, idx] - median[idx]) <= (mad[idx] * limit)

    cleaned = pixels[keep]
    minimum_cleaned = max(8, int(np.ceil(pixels.shape[0] * 0.3)))
    return cleaned if cleaned.shape[0] >= minimum_cleaned else pixels


def _region_feature(photo_id: str, region: str, lab: np.ndarray, mask: np.ndarray) -> RegionFeatures:
    pixels = lab[mask]
    if pixels.size == 0:
        pixels = np.zeros((1, 3), dtype=np.float32)
    else:
        pixels = _clean_region_pixels(region, pixels)

    l_star = float(np.median(pixels[:, 0]))
    a_star = float(np.median(pixels[:, 1]))
    b_star = float(np.median(pixels[:, 2]))
    c_star = float(np.sqrt(a_star**2 + b_star**2))
    h_deg = float(np.degrees(np.arctan2(b_star, a_star)))
    ita_deg = float(np.degrees(np.arctan2(l_star - 50.0, b_star if abs(b_star) > 1e-6 else 1e-6)))

    return RegionFeatures(
        photo_id=photo_id,
        region=region,
        l_star=l_star,
        a_star=a_star,
        b_star=b_star,
        c_star=c_star,
        h_deg=h_deg,
        ita_deg=ita_deg,
    )


def extract_features(photo_id: str, rgb: np.ndarray, masks: RegionMasks) -> list[RegionFeatures]:
    lab = _rgb_to_lab(rgb)

    mapping = {
        "cheek_left": masks.cheek_left,
        "cheek_right": masks.cheek_right,
        "forehead": masks.forehead,
        "iris_left": masks.iris_left,
        "iris_right": masks.iris_right,
        "sclera": masks.sclera,
        "hair": masks.hair,
    }

    return [_region_feature(photo_id, region, lab, mask) for region, mask in mapping.items()]
