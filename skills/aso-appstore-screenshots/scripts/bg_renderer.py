"""Deterministic Pillow background renderer for ASO scaffolds.

Each render() call returns an RGB Pillow image at the requested size,
painted in one of eight styles. All styles are pure Pillow — no external
deps beyond PIL.
"""
import math

from PIL import Image


BLOB_POSITIONS = {
    "upper-left": (0.25, 0.25),
    "upper-right": (0.75, 0.25),
    "lower-left": (0.25, 0.75),
    "lower-right": (0.75, 0.75),
    "center": (0.5, 0.5),
}

MESH_POSITIONS = [
    (0.25, 0.30),
    (0.75, 0.30),
    (0.50, 0.75),
]


def hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _gaussian_falloff(d: float, sigma: float) -> float:
    """Returns weight in [0,1] for distance d with Gaussian sigma."""
    return math.exp(-(d * d) / (2 * sigma * sigma))


def render(style: str, size: tuple, colors: list, **kwargs) -> Image.Image:
    """Render a background image.

    Args:
        style: one of 'plain', 'linear-vertical', 'linear-diagonal',
            'radial', 'vignette', 'blob', 'dual-blob', 'mesh-gradient'
        size: (width, height) in pixels
        colors: list of hex strings — length depends on style
        kwargs: style-specific extras (blob_position, blob_positions)

    Returns:
        RGB Image at the requested size.
    """
    if style == "plain":
        return _plain(size, colors[0])
    if style == "linear-vertical":
        return _linear_vertical(size, colors[0], colors[1])
    if style == "linear-diagonal":
        return _linear_diagonal(size, colors[0], colors[1])
    if style == "radial":
        return _radial(size, colors[0], colors[1])
    if style == "vignette":
        return _vignette(size, colors[0], colors[1])
    if style == "blob":
        return _blob(size, colors[0], colors[1], kwargs.get("blob_position", "center"))
    if style == "dual-blob":
        return _dual_blob(
            size, colors[0], colors[1], colors[2],
            kwargs.get("blob_positions", "upper-left,lower-right"),
        )
    if style == "mesh-gradient":
        return _mesh_gradient(size, colors[0], colors[1], colors[2], colors[3])
    raise ValueError(f"Unknown background style: {style}")


def _plain(size: tuple, color_hex: str) -> Image.Image:
    return Image.new("RGB", size, hex_to_rgb(color_hex))


def _linear_vertical(size: tuple, top_hex: str, bottom_hex: str) -> Image.Image:
    w, h = size
    top = hex_to_rgb(top_hex)
    bottom = hex_to_rgb(bottom_hex)
    img = Image.new("RGB", size)
    pixels = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(round(top[0] * (1 - t) + bottom[0] * t))
        g = int(round(top[1] * (1 - t) + bottom[1] * t))
        b = int(round(top[2] * (1 - t) + bottom[2] * t))
        for x in range(w):
            pixels[x, y] = (r, g, b)
    return img


def _radial(size: tuple, center_hex: str, edge_hex: str) -> Image.Image:
    w, h = size
    cx, cy = w / 2, h / 2
    max_r = math.hypot(cx, cy)
    center = hex_to_rgb(center_hex)
    edge = hex_to_rgb(edge_hex)
    img = Image.new("RGB", size)
    pixels = img.load()
    for y in range(h):
        for x in range(w):
            d = math.hypot(x - cx, y - cy)
            t = min(d / max_r, 1.0)
            r = int(round(center[0] * (1 - t) + edge[0] * t))
            g = int(round(center[1] * (1 - t) + edge[1] * t))
            b = int(round(center[2] * (1 - t) + edge[2] * t))
            pixels[x, y] = (r, g, b)
    return img


def _vignette(size: tuple, center_hex: str, edge_hex: str) -> Image.Image:
    w, h = size
    cx, cy = w / 2, h / 2
    max_r = math.hypot(cx, cy)
    center = hex_to_rgb(center_hex)
    edge = hex_to_rgb(edge_hex)
    img = Image.new("RGB", size)
    pixels = img.load()
    for y in range(h):
        for x in range(w):
            d = math.hypot(x - cx, y - cy)
            t = min(d / max_r, 1.0) ** 2  # steeper falloff than _radial
            r = int(round(center[0] * (1 - t) + edge[0] * t))
            g = int(round(center[1] * (1 - t) + edge[1] * t))
            b = int(round(center[2] * (1 - t) + edge[2] * t))
            pixels[x, y] = (r, g, b)
    return img


def _linear_diagonal(size: tuple, a_hex: str, b_hex: str) -> Image.Image:
    w, h = size
    a = hex_to_rgb(a_hex)
    b = hex_to_rgb(b_hex)
    img = Image.new("RGB", size)
    pixels = img.load()
    max_d = (w - 1) + (h - 1)
    for y in range(h):
        for x in range(w):
            t = (x + y) / max(max_d, 1)
            r = int(round(a[0] * (1 - t) + b[0] * t))
            g = int(round(a[1] * (1 - t) + b[1] * t))
            bl = int(round(a[2] * (1 - t) + b[2] * t))
            pixels[x, y] = (r, g, bl)
    return img


def _dual_blob(
    size: tuple,
    base_hex: str,
    blob_a_hex: str,
    blob_b_hex: str,
    blob_positions: str,
) -> Image.Image:
    w, h = size
    pos_a, pos_b = blob_positions.split(",")
    pos_a, pos_b = pos_a.strip(), pos_b.strip()
    for p in (pos_a, pos_b):
        if p not in BLOB_POSITIONS:
            raise ValueError(f"Unknown blob_position: {p}")
    rxa, rya = BLOB_POSITIONS[pos_a]
    rxb, ryb = BLOB_POSITIONS[pos_b]
    cax, cay = rxa * w, rya * h
    cbx, cby = rxb * w, ryb * h
    sigma = h * 0.30
    base = hex_to_rgb(base_hex)
    blob_a = hex_to_rgb(blob_a_hex)
    blob_b = hex_to_rgb(blob_b_hex)
    img = Image.new("RGB", size)
    pixels = img.load()
    for y in range(h):
        for x in range(w):
            ta = _gaussian_falloff(math.hypot(x - cax, y - cay), sigma)
            tb = _gaussian_falloff(math.hypot(x - cbx, y - cby), sigma)
            r = base[0] * (1 - ta - tb) + blob_a[0] * ta + blob_b[0] * tb
            g = base[1] * (1 - ta - tb) + blob_a[1] * ta + blob_b[1] * tb
            b = base[2] * (1 - ta - tb) + blob_a[2] * ta + blob_b[2] * tb
            pixels[x, y] = (
                max(0, min(255, int(round(r)))),
                max(0, min(255, int(round(g)))),
                max(0, min(255, int(round(b)))),
            )
    return img


def _blob(size: tuple, base_hex: str, blob_hex: str, blob_position: str) -> Image.Image:
    w, h = size
    if blob_position not in BLOB_POSITIONS:
        raise ValueError(f"Unknown blob_position: {blob_position}")
    rx, ry = BLOB_POSITIONS[blob_position]
    cx, cy = rx * w, ry * h
    sigma = h * 0.30  # 60% radius / 2 ≈ 30% of height as sigma
    base = hex_to_rgb(base_hex)
    blob = hex_to_rgb(blob_hex)
    img = Image.new("RGB", size)
    pixels = img.load()
    for y in range(h):
        for x in range(w):
            d = math.hypot(x - cx, y - cy)
            t = _gaussian_falloff(d, sigma)
            r = int(round(base[0] * (1 - t) + blob[0] * t))
            g = int(round(base[1] * (1 - t) + blob[1] * t))
            b = int(round(base[2] * (1 - t) + blob[2] * t))
            pixels[x, y] = (r, g, b)
    return img


def _mesh_gradient(
    size: tuple,
    base_hex: str,
    a_hex: str,
    b_hex: str,
    c_hex: str,
) -> Image.Image:
    w, h = size
    sigma = h * 0.28
    base = hex_to_rgb(base_hex)
    blobs = [hex_to_rgb(a_hex), hex_to_rgb(b_hex), hex_to_rgb(c_hex)]
    centers = [(rx * w, ry * h) for rx, ry in MESH_POSITIONS]
    img = Image.new("RGB", size)
    pixels = img.load()
    for y in range(h):
        for x in range(w):
            weights = [
                _gaussian_falloff(math.hypot(x - cx, y - cy), sigma)
                for cx, cy in centers
            ]
            wsum = sum(weights)
            base_w = max(0.0, 1.0 - wsum)
            r = base[0] * base_w
            g = base[1] * base_w
            b = base[2] * base_w
            for blob_color, blob_w in zip(blobs, weights):
                r += blob_color[0] * blob_w
                g += blob_color[1] * blob_w
                b += blob_color[2] * blob_w
            pixels[x, y] = (
                max(0, min(255, int(round(r)))),
                max(0, min(255, int(round(g)))),
                max(0, min(255, int(round(b)))),
            )
    return img
