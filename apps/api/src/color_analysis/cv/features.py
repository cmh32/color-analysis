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


def _lab_to_rgb_hex(l_star: float, a_star: float, b_star: float) -> str:
    fy = (l_star + 16.0) / 116.0
    fx = a_star / 500.0 + fy
    fz = fy - b_star / 200.0

    epsilon = 216 / 24389
    kappa = 24389 / 27

    def finv(t: float) -> float:
        return t**3 if t**3 > epsilon else (116 * t - 16) / kappa

    x = finv(fx) * 0.95047
    y = finv(fy) * 1.00000
    z = finv(fz) * 1.08883

    r_lin = 3.2406 * x - 1.5372 * y - 0.4986 * z
    g_lin = -0.9689 * x + 1.8758 * y + 0.0415 * z
    b_lin = 0.0557 * x - 0.2040 * y + 1.0570 * z

    def compand(c: float) -> int:
        c = max(0.0, min(1.0, c))
        c = 1.055 * c ** (1 / 2.4) - 0.055 if c > 0.0031308 else 12.92 * c
        return round(c * 255)

    return f"#{compand(r_lin):02x}{compand(g_lin):02x}{compand(b_lin):02x}"


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


def _focus_region_pixels(region: str, pixels: np.ndarray, ys: np.ndarray, xs: np.ndarray) -> np.ndarray:
    if pixels.shape[0] < 8:
        return pixels

    keep = np.ones(pixels.shape[0], dtype=bool)
    if region in {"cheek_left", "cheek_right"}:
        keep &= ys <= np.quantile(ys, 0.6)
        x_lo, x_hi = np.quantile(xs, [0.15, 0.85])
        keep &= (xs >= x_lo) & (xs <= x_hi)
    elif region == "hair":
        keep &= ys >= np.quantile(ys, 0.45)
        x_lo, x_hi = np.quantile(xs, [0.1, 0.9])
        keep &= (xs >= x_lo) & (xs <= x_hi)

    focused = pixels[keep]
    minimum_focused = max(8, int(np.ceil(pixels.shape[0] * 0.25)))
    return focused if focused.shape[0] >= minimum_focused else pixels


def _refine_iris_pixels(pixels: np.ndarray) -> np.ndarray:
    if pixels.shape[0] < 8:
        return pixels

    lightness = pixels[:, 0]
    lo, hi = np.quantile(lightness, [0.2, 0.8])
    refined = pixels[(lightness >= lo) & (lightness <= hi)]
    minimum_refined = max(8, int(np.ceil(pixels.shape[0] * 0.35)))
    return refined if refined.shape[0] >= minimum_refined else pixels


def _region_feature(photo_id: str, region: str, lab: np.ndarray, mask: np.ndarray) -> RegionFeatures:
    ys, xs = np.nonzero(mask)
    pixels = lab[mask]
    if pixels.size == 0:
        pixels = np.zeros((1, 3), dtype=np.float32)
    else:
        pixels = _focus_region_pixels(region, pixels, ys, xs)
        if region == "hair":
            # Exclude near-white and achromatic pixels (highlights, background, scalp).
            # Actual hair — even platinum blonde — has C* >> 6; near-zero chroma means
            # background or specular regardless of lightness.
            chroma = np.sqrt(pixels[:, 1] ** 2 + pixels[:, 2] ** 2)
            has_color = (pixels[:, 0] <= 88.0) & (chroma >= 6.0)
            if np.count_nonzero(has_color) >= 8:
                pixels = pixels[has_color]
        elif region in {"iris_left", "iris_right"}:
            pixels = _refine_iris_pixels(pixels)
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
