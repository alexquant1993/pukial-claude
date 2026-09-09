# ASO skill v3 — Pillow-first pivot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the ASO skill so Pillow renders the entire scaffold deterministically (frame + UI + bg + shadow + headline), and gpt-image-2 is only invoked to paint hero cards on a transparent canvas for slots that need them.

**Architecture:** Two-stage pipeline. Stage 1 (compose.py, always runs): Pillow assembles a finished-looking scaffold per slot. Stage 2 (enhance_card.py, hero slots only): the AI paints a card on a transparent canvas; Pillow composites it onto the scaffold to produce the final. AI never sees the headline, the app UI, the chassis, or the canvas background — so it cannot drift them.

**Tech Stack:** Python 3.9+, Pillow (PIL fork), pytest for testing, OpenAI Python SDK for the `images.generate` call.

**Spec reference:** `~/.claude/skills/aso-appstore-screenshots/docs/specs/2026-05-13-pillow-first-pivot-design.md`

**Note on git:** The skill folder is not a git repo. Replace "Commit" steps with "Verify the test passes" before moving on. Standard `git add` / `git commit` commands in this plan are illustrative only.

---

## Task 1: Move photoreal frame assets into the skill, delete legacy placeholders

**Files:**
- Create: `~/.claude/skills/aso-appstore-screenshots/assets/iphone-6.9-frame.png`
- Create: `~/.claude/skills/aso-appstore-screenshots/assets/android-frame.png`
- Delete: `~/.claude/skills/aso-appstore-screenshots/assets/device_frame.png`
- Delete: `~/.claude/skills/aso-appstore-screenshots/assets/device_frame_android.png`

- [ ] **Step 1: Copy iPhone frame into skill assets**

Run:
```bash
cp "/Users/andersonarroyo/Downloads/Color=Deep Blue.png" \
   "/Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/assets/iphone-6.9-frame.png"
```

- [ ] **Step 2: Copy cleaned Android frame into skill assets**

Run:
```bash
cp "/Users/andersonarroyo/Downloads/main_clean.png" \
   "/Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/assets/android-frame.png"
```

- [ ] **Step 3: Verify both assets land correctly**

Run:
```bash
python3 -c "
from PIL import Image
for name in ['iphone-6.9-frame.png', 'android-frame.png']:
    p = f'/Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/assets/{name}'
    img = Image.open(p)
    cx, cy = img.size[0]//2, img.size[1]//2
    print(f'{name}: {img.size}, mode={img.mode}, center alpha={img.getpixel((cx, cy))[3]}')
"
```
Expected:
- `iphone-6.9-frame.png: (490, 1000), mode=RGBA, center alpha=0`
- `android-frame.png: (486, 1024), mode=RGBA, center alpha=0`

- [ ] **Step 4: Delete the legacy placeholder frame PNGs**

Run:
```bash
rm "/Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/assets/device_frame.png"
rm "/Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/assets/device_frame_android.png"
```

---

## Task 2: Set up test infrastructure

**Files:**
- Create: `~/.claude/skills/aso-appstore-screenshots/tests/__init__.py`
- Create: `~/.claude/skills/aso-appstore-screenshots/tests/conftest.py`
- Create: `~/.claude/skills/aso-appstore-screenshots/tests/fixtures/__init__.py`
- Create: `~/.claude/skills/aso-appstore-screenshots/tests/fixtures/make_sample_ui.py`
- Create: `~/.claude/skills/aso-appstore-screenshots/tests/fixtures/sample_ui.png` (generated)

- [ ] **Step 1: Confirm pytest is available**

Run: `python3 -m pytest --version`
Expected: pytest version printed. If missing: `pip3 install pytest pillow openai`

- [ ] **Step 2: Create the tests folder and an empty `__init__.py`**

Run:
```bash
mkdir -p /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/tests/fixtures
touch /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/tests/__init__.py
touch /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/tests/fixtures/__init__.py
```

- [ ] **Step 3: Create `tests/conftest.py` with shared fixtures**

Write to `~/.claude/skills/aso-appstore-screenshots/tests/conftest.py`:

```python
"""Shared pytest fixtures for ASO skill tests."""
import os
import sys
import pytest

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")

sys.path.insert(0, SCRIPTS_DIR)


@pytest.fixture
def skill_dir():
    return SKILL_DIR


@pytest.fixture
def assets_dir():
    return os.path.join(SKILL_DIR, "assets")


@pytest.fixture
def sample_ui_path():
    return os.path.join(SKILL_DIR, "tests", "fixtures", "sample_ui.png")


@pytest.fixture
def tmp_output(tmp_path):
    """A clean tmp output path for each test."""
    return str(tmp_path / "output.png")
```

- [ ] **Step 4: Create the sample-UI fixture generator**

Write to `~/.claude/skills/aso-appstore-screenshots/tests/fixtures/make_sample_ui.py`:

```python
"""Generate a 256x512 blue PNG used as a fake app UI in compose tests."""
import os
from PIL import Image, ImageDraw

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_ui.png")


def main():
    img = Image.new("RGBA", (256, 512), (45, 90, 200, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 40, 236, 80], fill=(255, 255, 255, 255))
    draw.rectangle([20, 100, 236, 140], fill=(255, 255, 255, 255))
    img.save(OUT_PATH, format="PNG")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Generate the sample UI**

Run:
```bash
python3 /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/tests/fixtures/make_sample_ui.py
```
Expected: `Wrote .../tests/fixtures/sample_ui.png`

- [ ] **Step 6: Sanity-run pytest (no tests yet, should exit 5)**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/ -v
```
Expected: pytest collects 0 tests, exits with `no tests ran in X.XXs`. This confirms collection works.

---

## Task 3: Implement `bg_renderer.plain` style with TDD

**Files:**
- Create: `~/.claude/skills/aso-appstore-screenshots/scripts/bg_renderer.py`
- Create: `~/.claude/skills/aso-appstore-screenshots/tests/test_bg_renderer.py`

- [ ] **Step 1: Write the failing test**

Write to `~/.claude/skills/aso-appstore-screenshots/tests/test_bg_renderer.py`:

```python
"""Tests for the deterministic Pillow background renderer."""
from PIL import Image
import bg_renderer


def test_plain_renders_solid_color():
    img = bg_renderer.render(
        style="plain",
        size=(100, 200),
        colors=["#ff0080"],
    )
    assert img.size == (100, 200)
    assert img.mode == "RGB"
    assert img.getpixel((50, 100)) == (255, 0, 128)
    assert img.getpixel((0, 0)) == (255, 0, 128)
    assert img.getpixel((99, 199)) == (255, 0, 128)
```

- [ ] **Step 2: Run test, verify it fails**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_bg_renderer.py::test_plain_renders_solid_color -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'bg_renderer'`

- [ ] **Step 3: Create `bg_renderer.py` with `plain` support**

Write to `~/.claude/skills/aso-appstore-screenshots/scripts/bg_renderer.py`:

```python
"""Deterministic Pillow background renderer for ASO scaffolds.

Each render() call returns an RGB Pillow image at the requested size,
painted in one of eight styles. All styles are pure Pillow — no external
deps beyond PIL.
"""
from PIL import Image


def hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


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
    raise ValueError(f"Unknown background style: {style}")


def _plain(size: tuple, color_hex: str) -> Image.Image:
    return Image.new("RGB", size, hex_to_rgb(color_hex))
```

- [ ] **Step 4: Run test, verify it passes**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_bg_renderer.py::test_plain_renders_solid_color -v
```
Expected: PASS

---

## Task 4: Implement `linear-vertical` background style

**Files:**
- Modify: `~/.claude/skills/aso-appstore-screenshots/scripts/bg_renderer.py`
- Modify: `~/.claude/skills/aso-appstore-screenshots/tests/test_bg_renderer.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_bg_renderer.py`:

```python
def test_linear_vertical_gradient_top_to_bottom():
    img = bg_renderer.render(
        style="linear-vertical",
        size=(100, 200),
        colors=["#ffffff", "#000000"],
    )
    top = img.getpixel((50, 0))
    bottom = img.getpixel((50, 199))
    middle = img.getpixel((50, 100))
    assert top == (255, 255, 255)
    assert bottom == (0, 0, 0)
    # Middle should be roughly gray
    assert 100 <= middle[0] <= 155
```

- [ ] **Step 2: Run test, verify fail**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_bg_renderer.py::test_linear_vertical_gradient_top_to_bottom -v
```
Expected: FAIL with `ValueError: Unknown background style: linear-vertical`

- [ ] **Step 3: Implement `linear-vertical`**

Modify `bg_renderer.py`:

```python
def render(style: str, size: tuple, colors: list, **kwargs) -> Image.Image:
    if style == "plain":
        return _plain(size, colors[0])
    if style == "linear-vertical":
        return _linear_vertical(size, colors[0], colors[1])
    raise ValueError(f"Unknown background style: {style}")


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
```

- [ ] **Step 4: Run test, verify pass**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_bg_renderer.py::test_linear_vertical_gradient_top_to_bottom -v
```
Expected: PASS

---

## Task 5: Implement `linear-diagonal` background style

**Files:**
- Modify: `scripts/bg_renderer.py`
- Modify: `tests/test_bg_renderer.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_bg_renderer.py`:

```python
def test_linear_diagonal_top_left_to_bottom_right():
    img = bg_renderer.render(
        style="linear-diagonal",
        size=(100, 100),
        colors=["#ffffff", "#000000"],
    )
    top_left = img.getpixel((0, 0))
    bottom_right = img.getpixel((99, 99))
    assert top_left == (255, 255, 255)
    assert bottom_right == (0, 0, 0)
    # Top-right and bottom-left should be roughly mid-gray
    mid_a = img.getpixel((99, 0))
    mid_b = img.getpixel((0, 99))
    assert 100 <= mid_a[0] <= 155
    assert 100 <= mid_b[0] <= 155
```

- [ ] **Step 2: Run, verify fail**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_bg_renderer.py::test_linear_diagonal_top_left_to_bottom_right -v
```
Expected: FAIL with `Unknown background style: linear-diagonal`

- [ ] **Step 3: Implement `linear-diagonal`**

Add to `bg_renderer.py` (and route in `render`):

```python
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
```

Add the route to `render`:
```python
    if style == "linear-diagonal":
        return _linear_diagonal(size, colors[0], colors[1])
```

- [ ] **Step 4: Run, verify pass**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_bg_renderer.py::test_linear_diagonal_top_left_to_bottom_right -v
```
Expected: PASS

---

## Task 6: Implement `radial` background style

**Files:**
- Modify: `scripts/bg_renderer.py`
- Modify: `tests/test_bg_renderer.py`

- [ ] **Step 1: Add failing test**

Append:

```python
def test_radial_center_brighter_than_corners():
    img = bg_renderer.render(
        style="radial",
        size=(100, 100),
        colors=["#ffffff", "#000000"],
    )
    center = img.getpixel((50, 50))
    corner = img.getpixel((0, 0))
    assert center == (255, 255, 255)
    assert corner == (0, 0, 0)
```

- [ ] **Step 2: Run, verify fail**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_bg_renderer.py::test_radial_center_brighter_than_corners -v
```
Expected: FAIL with `Unknown background style: radial`

- [ ] **Step 3: Implement `radial`**

Add to `bg_renderer.py`:

```python
import math


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
```

Route in `render`:
```python
    if style == "radial":
        return _radial(size, colors[0], colors[1])
```

- [ ] **Step 4: Run, verify pass**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_bg_renderer.py::test_radial_center_brighter_than_corners -v
```
Expected: PASS

---

## Task 7: Implement `vignette` background style

**Files:**
- Modify: `scripts/bg_renderer.py`
- Modify: `tests/test_bg_renderer.py`

The `vignette` style is similar to `radial` but the radius default + falloff curve gives a tighter focus.

- [ ] **Step 1: Add failing test**

Append:

```python
def test_vignette_darkens_corners_more_than_radial():
    img = bg_renderer.render(
        style="vignette",
        size=(100, 100),
        colors=["#ffffff", "#202020"],
    )
    center = img.getpixel((50, 50))
    corner = img.getpixel((0, 0))
    assert center == (255, 255, 255)
    # Vignette uses a steeper falloff than linear radial.
    # At the corner, t = 1.0 → color = edge_hex.
    assert corner == (32, 32, 32)
    # Mid-radius point should already be noticeably darker than radial linear.
    quarter = img.getpixel((25, 25))
    assert quarter[0] < 240  # well below 255
```

- [ ] **Step 2: Run, verify fail**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_bg_renderer.py::test_vignette_darkens_corners_more_than_radial -v
```
Expected: FAIL with `Unknown background style: vignette`

- [ ] **Step 3: Implement `vignette`** (radial with `t**2` falloff for steeper curve)

Add to `bg_renderer.py`:

```python
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
```

Route:
```python
    if style == "vignette":
        return _vignette(size, colors[0], colors[1])
```

- [ ] **Step 4: Run, verify pass**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_bg_renderer.py::test_vignette_darkens_corners_more_than_radial -v
```
Expected: PASS

---

## Task 8: Implement `blob` background style

**Files:**
- Modify: `scripts/bg_renderer.py`
- Modify: `tests/test_bg_renderer.py`

A `blob` is a Gaussian-falloff glow at a named position, painted over the base color.

- [ ] **Step 1: Add failing test**

Append:

```python
def test_blob_brightens_named_corner():
    img = bg_renderer.render(
        style="blob",
        size=(200, 200),
        colors=["#000000", "#ffffff"],
        blob_position="upper-left",
    )
    upper_left = img.getpixel((10, 10))
    lower_right = img.getpixel((190, 190))
    # Blob is upper-left, so upper-left should be much brighter than lower-right.
    assert upper_left[0] > 100
    assert lower_right[0] < 50
```

- [ ] **Step 2: Run, verify fail**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_bg_renderer.py::test_blob_brightens_named_corner -v
```
Expected: FAIL with `Unknown background style: blob`

- [ ] **Step 3: Implement `blob`**

Add to `bg_renderer.py`:

```python
BLOB_POSITIONS = {
    "upper-left": (0.25, 0.25),
    "upper-right": (0.75, 0.25),
    "lower-left": (0.25, 0.75),
    "lower-right": (0.75, 0.75),
    "center": (0.5, 0.5),
}


def _gaussian_falloff(d: float, sigma: float) -> float:
    """Returns weight in [0,1] for distance d with Gaussian sigma."""
    return math.exp(-(d * d) / (2 * sigma * sigma))


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
```

Route:
```python
    if style == "blob":
        return _blob(size, colors[0], colors[1], kwargs.get("blob_position", "center"))
```

- [ ] **Step 4: Run, verify pass**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_bg_renderer.py::test_blob_brightens_named_corner -v
```
Expected: PASS

---

## Task 9: Implement `dual-blob` background style

**Files:**
- Modify: `scripts/bg_renderer.py`
- Modify: `tests/test_bg_renderer.py`

- [ ] **Step 1: Add failing test**

Append:

```python
def test_dual_blob_brightens_two_named_corners():
    img = bg_renderer.render(
        style="dual-blob",
        size=(200, 200),
        colors=["#000000", "#ffffff", "#888888"],
        blob_positions="upper-left,lower-right",
    )
    upper_left = img.getpixel((10, 10))
    lower_right = img.getpixel((190, 190))
    upper_right = img.getpixel((190, 10))
    assert upper_left[0] > 100   # white blob
    assert lower_right[0] > 50   # gray blob
    assert upper_right[0] < 80   # away from both
```

- [ ] **Step 2: Run, verify fail**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_bg_renderer.py::test_dual_blob_brightens_two_named_corners -v
```
Expected: FAIL

- [ ] **Step 3: Implement `dual-blob`**

Add to `bg_renderer.py`:

```python
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
```

Route:
```python
    if style == "dual-blob":
        return _dual_blob(
            size, colors[0], colors[1], colors[2],
            kwargs.get("blob_positions", "upper-left,lower-right"),
        )
```

- [ ] **Step 4: Run, verify pass**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_bg_renderer.py::test_dual_blob_brightens_two_named_corners -v
```
Expected: PASS

---

## Task 10: Implement `mesh-gradient` background style

**Files:**
- Modify: `scripts/bg_renderer.py`
- Modify: `tests/test_bg_renderer.py`

Three Gaussian blobs at fixed thirds of the canvas, all blended over a base color.

- [ ] **Step 1: Add failing test**

Append:

```python
def test_mesh_gradient_picks_up_all_three_blob_colors():
    img = bg_renderer.render(
        style="mesh-gradient",
        size=(300, 300),
        colors=["#000000", "#ff0000", "#00ff00", "#0000ff"],
    )
    # Three blobs at thirds: (0.25, 0.30), (0.75, 0.30), (0.50, 0.75).
    near_red = img.getpixel((75, 90))
    near_green = img.getpixel((225, 90))
    near_blue = img.getpixel((150, 225))
    assert near_red[0] > near_red[1] and near_red[0] > near_red[2]
    assert near_green[1] > near_green[0] and near_green[1] > near_green[2]
    assert near_blue[2] > near_blue[0] and near_blue[2] > near_blue[1]
```

- [ ] **Step 2: Run, verify fail**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_bg_renderer.py::test_mesh_gradient_picks_up_all_three_blob_colors -v
```
Expected: FAIL

- [ ] **Step 3: Implement `mesh-gradient`**

Add to `bg_renderer.py`:

```python
MESH_POSITIONS = [
    (0.25, 0.30),
    (0.75, 0.30),
    (0.50, 0.75),
]


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
```

Route:
```python
    if style == "mesh-gradient":
        return _mesh_gradient(size, colors[0], colors[1], colors[2], colors[3])
```

- [ ] **Step 4: Run, verify pass**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_bg_renderer.py -v
```
Expected: ALL 8 bg style tests PASS

---

## Task 11: Implement the photoreal frame compositor with drop shadow

**Files:**
- Create: `~/.claude/skills/aso-appstore-screenshots/scripts/frame_composite.py`
- Create: `~/.claude/skills/aso-appstore-screenshots/tests/test_frame_composite.py`

The compositor: scale the frame PNG to match `device_w`, paste it over an already-laid background+UI canvas, and render a Pillow drop shadow underneath using the frame alpha.

- [ ] **Step 1: Write the failing test**

Write to `~/.claude/skills/aso-appstore-screenshots/tests/test_frame_composite.py`:

```python
"""Tests for the photoreal frame compositor."""
import os
from PIL import Image
import frame_composite


def test_compose_frame_preserves_screen_transparency(assets_dir):
    """A pixel inside the frame's screen area should equal the UI behind it."""
    frame_path = os.path.join(assets_dir, "iphone-6.9-frame.png")
    # 1056x2155 base (matches iPhone 6.9 device_w when frame is scaled).
    bg = Image.new("RGBA", (1056, 2868), (255, 215, 240, 255))
    # Paint a green pixel at the center of where the screen will be.
    bg.putpixel((528, 1700), (0, 255, 0, 255))
    result = frame_composite.composite_frame(
        canvas=bg,
        frame_path=frame_path,
        device_x=0,
        device_y=738,
        device_w=1056,
    )
    # Frame screen-interior is transparent → green pixel should still show.
    assert result.getpixel((528, 1700))[:3] == (0, 255, 0)


def test_drop_shadow_renders_below_phone(assets_dir):
    frame_path = os.path.join(assets_dir, "iphone-6.9-frame.png")
    bg = Image.new("RGBA", (1320, 2868), (255, 215, 240, 255))
    result = frame_composite.composite_frame(
        canvas=bg,
        frame_path=frame_path,
        device_x=132,
        device_y=738,
        device_w=1056,
        with_shadow=True,
    )
    # A pixel just outside the chassis on the right, at mid-height, should
    # be darker than the pure bg because the shadow extends a bit.
    bg_color = (255, 215, 240)
    chassis_right_x = 132 + 1056
    shadow_sample = result.getpixel((chassis_right_x + 20, 1700))[:3]
    assert shadow_sample[0] < bg_color[0]  # darker red component
```

- [ ] **Step 2: Run, verify fail**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_frame_composite.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'frame_composite'`

- [ ] **Step 3: Implement `frame_composite.py`**

Write to `~/.claude/skills/aso-appstore-screenshots/scripts/frame_composite.py`:

```python
"""Photoreal frame compositing + drop shadow for ASO scaffolds."""
from PIL import Image, ImageFilter

SHADOW_OFFSET_Y = 24
SHADOW_BLUR_RADIUS = 60
SHADOW_OPACITY = 46  # ≈ 18% of 255


def composite_frame(
    canvas: Image.Image,
    frame_path: str,
    device_x: int,
    device_y: int,
    device_w: int,
    with_shadow: bool = True,
) -> Image.Image:
    """Composite the photoreal frame PNG onto `canvas` at (device_x, device_y).

    The frame is scaled so its width matches device_w (aspect-preserving).
    If with_shadow=True, a Pillow Gaussian drop shadow from the frame's alpha
    channel is composited UNDER the frame.

    Returns a new RGBA image; the input canvas is not mutated.
    """
    canvas = canvas.convert("RGBA").copy()
    frame = Image.open(frame_path).convert("RGBA")

    # Scale frame width → device_w, keeping aspect ratio.
    if frame.width != device_w:
        new_h = int(round(frame.height * (device_w / frame.width)))
        frame = frame.resize((device_w, new_h), Image.LANCZOS)

    if with_shadow:
        shadow = _build_shadow(frame, canvas.size, device_x, device_y)
        canvas = Image.alpha_composite(canvas, shadow)

    # Paste frame on top (alpha-aware).
    frame_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    frame_layer.paste(frame, (device_x, device_y), frame)
    canvas = Image.alpha_composite(canvas, frame_layer)
    return canvas


def _build_shadow(
    frame: Image.Image,
    canvas_size: tuple,
    device_x: int,
    device_y: int,
) -> Image.Image:
    """Build a soft drop-shadow layer the size of the canvas."""
    # Extract frame alpha as a grayscale mask.
    alpha = frame.split()[-1]
    # Make a black-filled rect with that alpha, on a transparent canvas.
    shadow_silhouette = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    black = Image.new("RGBA", frame.size, (0, 0, 0, SHADOW_OPACITY))
    shadow_silhouette.paste(black, (0, 0), alpha)
    # Blur.
    shadow_silhouette = shadow_silhouette.filter(
        ImageFilter.GaussianBlur(SHADOW_BLUR_RADIUS)
    )
    # Place onto full canvas at device anchor + Y offset.
    out = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    out.paste(
        shadow_silhouette,
        (device_x, device_y + SHADOW_OFFSET_Y),
        shadow_silhouette,
    )
    return out
```

- [ ] **Step 4: Run, verify pass**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_frame_composite.py -v
```
Expected: BOTH tests PASS

---

## Task 12: Implement the headline text renderer

**Files:**
- Create: `~/.claude/skills/aso-appstore-screenshots/scripts/headline_render.py`
- Create: `~/.claude/skills/aso-appstore-screenshots/tests/test_headline_render.py`

Lifted from the existing compose.py's word-wrap + fit-font logic.

- [ ] **Step 1: Write the failing test**

Write to `~/.claude/skills/aso-appstore-screenshots/tests/test_headline_render.py`:

```python
"""Tests for headline text rendering."""
from PIL import Image
import headline_render


def test_renders_verb_and_descriptor_in_text_color():
    canvas = Image.new("RGBA", (1320, 2868), (255, 215, 240, 255))
    out, headline_band = headline_render.draw_headline(
        canvas=canvas,
        verb="TEST",
        desc="THIS IS A DESCRIPTOR",
        text_top=205,
        canvas_w=1320,
        text_color="#BC004B",
    )
    # Pixel where verb should be — top third of canvas, center column.
    # Just check that *some* pixel near the verb is the text color.
    found = False
    for y in range(200, 400):
        px = out.getpixel((660, y))[:3]
        if px == (188, 0, 75):
            found = True
            break
    assert found, "expected to find text-color pixel in verb region"
    # Headline band should be returned and non-empty.
    assert headline_band[2] > 0 and headline_band[3] > 0
```

- [ ] **Step 2: Run, verify fail**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_headline_render.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'headline_render'`

- [ ] **Step 3: Implement `headline_render.py`**

Write to `~/.claude/skills/aso-appstore-screenshots/scripts/headline_render.py`:

```python
"""Headline text rendering for ASO scaffolds (Pillow-deterministic)."""
import os
from PIL import Image, ImageDraw, ImageFont

TEXT_W_RATIO = 0.92
VERB_SIZE_MAX_RATIO = 0.198
VERB_SIZE_MIN_RATIO = 0.116
DESC_SIZE_RATIO = 0.096
VERB_DESC_GAP = 20
DESC_LINE_GAP = 24


def _resolve_default_font() -> str:
    for p in (
        "/Library/Fonts/SF-Pro-Display-Black.otf",
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/Arial Black.ttf",
    ):
        if os.path.exists(p):
            return p
    raise RuntimeError("No suitable heavy/black font found.")


def _word_wrap(draw, text, font, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit_font(text, font_path, max_w, size_max, size_min):
    dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    for size in range(size_max, size_min - 1, -4):
        font = ImageFont.truetype(font_path, size)
        bbox = dummy.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= max_w:
            return font
    return ImageFont.truetype(font_path, size_min)


def _draw_centered(draw, y, text, font, canvas_w, max_w, fill):
    lines = _word_wrap(draw, text, font, max_w) if max_w else [text]
    max_line_w = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        h = bbox[3] - bbox[1]
        line_w = bbox[2] - bbox[0]
        max_line_w = max(max_line_w, line_w)
        draw.text((canvas_w // 2, y - bbox[1]), line, fill=fill, font=font, anchor="mt")
        y += h + DESC_LINE_GAP
    return y, max_line_w


def draw_headline(
    canvas: Image.Image,
    verb: str,
    desc: str,
    text_top: int,
    canvas_w: int,
    text_color: str,
    font_path: str = None,
    desc_font_path: str = None,
) -> tuple:
    """Draw the headline onto `canvas` in place. Returns (canvas, headline_band).

    headline_band is (x, y, w, h) in canvas coords — a tight rect around the
    rendered text with ~30px padding on each side, used downstream by the
    sidecar so future masking / overlay tools can identify the headline area.
    """
    font_path = font_path or _resolve_default_font()
    desc_font_path = desc_font_path or font_path
    max_text_w = int(canvas_w * TEXT_W_RATIO)
    verb_size_max = int(canvas_w * VERB_SIZE_MAX_RATIO)
    verb_size_min = int(canvas_w * VERB_SIZE_MIN_RATIO)
    desc_size = int(canvas_w * DESC_SIZE_RATIO)

    draw = ImageDraw.Draw(canvas)
    verb_font = _fit_font(verb.upper(), font_path, max_text_w, verb_size_max, verb_size_min)
    desc_font = ImageFont.truetype(desc_font_path, desc_size)

    y = text_top
    y, verb_max_w = _draw_centered(draw, y, verb.upper(), verb_font, canvas_w, None, text_color)
    y += VERB_DESC_GAP
    y, desc_max_w = _draw_centered(
        draw, y, desc.upper(), desc_font, canvas_w, max_text_w, text_color
    )
    text_bottom = y - DESC_LINE_GAP  # strip the trailing gap

    max_line_w = max(verb_max_w, desc_max_w)
    pad = 30
    band_x = max(0, (canvas_w - max_line_w) // 2 - pad)
    band_y = max(0, text_top - pad)
    band_w = min(canvas_w - band_x, max_line_w + 2 * pad)
    band_h = (text_bottom - text_top) + 2 * pad
    return canvas, (band_x, band_y, band_w, band_h)
```

- [ ] **Step 4: Run, verify pass**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_headline_render.py -v
```
Expected: PASS

---

## Task 13: Implement the `literal` mode lifted-panel renderer

**Files:**
- Create: `~/.claude/skills/aso-appstore-screenshots/scripts/lifted_panel.py`
- Create: `~/.claude/skills/aso-appstore-screenshots/tests/test_lifted_panel.py`

Lifted from the existing compose.py's `render_lifted_panel` logic.

- [ ] **Step 1: Write the failing test**

Write to `~/.claude/skills/aso-appstore-screenshots/tests/test_lifted_panel.py`:

```python
"""Tests for the literal-mode lifted UI panel renderer."""
from PIL import Image
import lifted_panel


def test_lifts_a_source_rect_onto_canvas():
    canvas = Image.new("RGBA", (1320, 2868), (255, 215, 240, 255))
    # Source UI: a 100x100 yellow square inside a larger white canvas.
    src = Image.new("RGBA", (500, 1000), (255, 255, 255, 255))
    from PIL import ImageDraw
    ImageDraw.Draw(src).rectangle([100, 100, 200, 200], fill=(255, 255, 0, 255))

    out, panel_bbox = lifted_panel.render(
        canvas=canvas,
        shot=src,
        rect=(100, 100, 100, 100),   # the yellow square in source coords
        screen_x=147,
        screen_y=753,
        screen_scale=1056 / 500,     # screen width 1056 / source width 500
        device_x=132,
        device_w=1056,
        anchor="left",
        scale_factor=1.5,
        overflow=100,
    )
    px, py, pw, ph = panel_bbox
    # Sample inside the panel — should be yellow-ish (with rounded corners
    # so the corners might be the bg; sample middle).
    mid = out.getpixel((px + pw // 2, py + ph // 2))[:3]
    assert mid == (255, 255, 0)
```

- [ ] **Step 2: Run, verify fail**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_lifted_panel.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'lifted_panel'`

- [ ] **Step 3: Implement `lifted_panel.py`**

Write to `~/.claude/skills/aso-appstore-screenshots/scripts/lifted_panel.py`:

```python
"""Pillow rendering of the `literal` mode lifted UI panel."""
from PIL import Image, ImageDraw, ImageFilter

PANEL_CORNER_R = 24
PANEL_SHADOW_OFFSET = (8, 14)
PANEL_SHADOW_BLUR = 24
PANEL_SHADOW_ALPHA = 110
PANEL_SHADOW_PAD = 60


def render(
    canvas: Image.Image,
    shot: Image.Image,
    rect: tuple,
    screen_x: int,
    screen_y: int,
    screen_scale: float,
    device_x: int,
    device_w: int,
    anchor: str,
    scale_factor: float,
    overflow: int,
) -> tuple:
    """Paint a lifted UI panel. Returns (canvas, panel_bbox)."""
    rect_x, rect_y, rect_w, rect_h = rect
    panel_src = shot.crop(
        (rect_x, rect_y, rect_x + rect_w, rect_y + rect_h)
    ).convert("RGBA")

    final_w = int(rect_w * screen_scale * scale_factor)
    final_h = int(rect_h * screen_scale * scale_factor)
    if final_w <= 0 or final_h <= 0:
        raise ValueError(f"Invalid panel size: {final_w}x{final_h}")
    panel_src = panel_src.resize((final_w, final_h), Image.LANCZOS)

    panel = Image.new("RGBA", (final_w, final_h), (0, 0, 0, 0))
    corner_mask = Image.new("L", (final_w, final_h), 0)
    ImageDraw.Draw(corner_mask).rounded_rectangle(
        [0, 0, final_w, final_h], radius=PANEL_CORNER_R, fill=255,
    )
    panel.paste(panel_src, (0, 0), corner_mask)

    src_center_y_on_canvas = screen_y + (rect_y + rect_h / 2) * screen_scale
    panel_y = int(src_center_y_on_canvas - final_h / 2)
    if anchor == "left":
        panel_x = device_x - overflow
    elif anchor == "right":
        panel_x = device_x + device_w + overflow - final_w
    else:
        raise ValueError(f"anchor must be 'left' or 'right', got {anchor!r}")

    sw = final_w + 2 * PANEL_SHADOW_PAD
    sh = final_h + 2 * PANEL_SHADOW_PAD
    shadow_layer = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    ImageDraw.Draw(shadow_layer).rounded_rectangle(
        [PANEL_SHADOW_PAD, PANEL_SHADOW_PAD,
         PANEL_SHADOW_PAD + final_w, PANEL_SHADOW_PAD + final_h],
        radius=PANEL_CORNER_R, fill=(0, 0, 0, PANEL_SHADOW_ALPHA),
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(PANEL_SHADOW_BLUR))

    shadow_full = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_full.alpha_composite(
        shadow_layer,
        (panel_x - PANEL_SHADOW_PAD + PANEL_SHADOW_OFFSET[0],
         panel_y - PANEL_SHADOW_PAD + PANEL_SHADOW_OFFSET[1]),
    )
    canvas = Image.alpha_composite(canvas, shadow_full)

    panel_full = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    panel_full.alpha_composite(panel, (panel_x, panel_y))
    canvas = Image.alpha_composite(canvas, panel_full)

    return canvas, (panel_x, panel_y, final_w, final_h)
```

- [ ] **Step 4: Run, verify pass**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_lifted_panel.py -v
```
Expected: PASS

---

## Task 14: Rewrite `compose.py` to orchestrate the new pipeline

**Files:**
- Modify: `~/.claude/skills/aso-appstore-screenshots/scripts/compose.py` (full rewrite)
- Create: `~/.claude/skills/aso-appstore-screenshots/tests/test_compose.py`

The rewritten `compose.py` is glue: bg → app UI → frame+shadow → headline → optional panel → sidecar. The individual renderers from Tasks 3-13 do the work.

- [ ] **Step 1: Write the failing end-to-end test**

Write to `~/.claude/skills/aso-appstore-screenshots/tests/test_compose.py`:

```python
"""End-to-end tests for compose.py orchestration."""
import json
import os
from PIL import Image
import compose


def test_compose_clean_slot_writes_scaffold_and_sidecar(
    sample_ui_path, tmp_output, assets_dir
):
    sidecar = tmp_output.replace(".png", ".meta.json")
    compose.compose(
        device="iphone-6.9",
        bg_style="plain",
        bg_colors=["#FFD7F0"],
        verb="TEST",
        desc="DESCRIPTOR LINE",
        text_color="#BC004B",
        screenshot_path=sample_ui_path,
        frame_path=os.path.join(assets_dir, "iphone-6.9-frame.png"),
        output_path=tmp_output,
    )
    out = Image.open(tmp_output)
    assert out.size == (1320, 2868)
    meta = json.load(open(sidecar))
    assert meta["device"] == "iphone-6.9"
    assert meta["canvas"] == [1320, 2868]
    assert meta["panel_mode"] == "clean"
    assert meta["background"] == {"style": "plain", "colors": ["#FFD7F0"]}
    assert meta["screen_rect"][2] > 0   # screen width > 0
    assert meta["breakout_zone"] is None


def test_compose_hero_slot_records_breakout_zone(
    sample_ui_path, tmp_output, assets_dir
):
    sidecar = tmp_output.replace(".png", ".meta.json")
    compose.compose(
        device="iphone-6.9",
        bg_style="plain",
        bg_colors=["#FFD7F0"],
        verb="GIVE",
        desc="ITEMS",
        text_color="#BC004B",
        screenshot_path=sample_ui_path,
        frame_path=os.path.join(assets_dir, "iphone-6.9-frame.png"),
        output_path=tmp_output,
        breakout_zone=(60, 950, 760, 820),
    )
    meta = json.load(open(sidecar))
    assert meta["panel_mode"] == "hero"
    assert meta["breakout_zone"] == [60, 950, 760, 820]
```

- [ ] **Step 2: Run, verify fail**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_compose.py -v
```
Expected: FAIL — old `compose.py` doesn't have this signature.

- [ ] **Step 3: Rewrite `scripts/compose.py`**

Write to `~/.claude/skills/aso-appstore-screenshots/scripts/compose.py` (full replacement):

```python
#!/usr/bin/env python3
"""ASO scaffold composer — Pillow-only.

Pipeline per slot:
  1. Render background per chosen style (one of 8) — bg_renderer.render
  2. Composite the source app UI into the screen area
  3. Composite the photoreal phone frame (+ Pillow drop shadow underneath)
  4. Draw the headline above the phone
  5. Optionally render a literal lifted UI panel beside the phone
  6. Write scaffold.png + scaffold.meta.json

The AI is NOT involved at this stage. The output is a finished-looking
screenshot that the user can ship as-is for clean / literal slots, or as
a base for the optional hero card (Phase 7 → enhance_card.py).
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)

import bg_renderer
import frame_composite
import headline_render
import lifted_panel

# ── Device profiles ─────────────────────────────────────────────────
DEVICE_PROFILES = {
    "iphone-6.7": {
        "canvas": (1290, 2796),
        "device_w": 1030,
        "bezel": 15,
        "screen_corner_r": 62,
        "device_y": 720,
        "text_top": 200,
        "frame_file": "iphone-6.9-frame.png",
    },
    "iphone-6.5": {
        "canvas": (1242, 2688),
        "device_w": 994,
        "bezel": 15,
        "screen_corner_r": 60,
        "device_y": 692,
        "text_top": 192,
        "frame_file": "iphone-6.9-frame.png",
    },
    "iphone-6.9": {
        "canvas": (1320, 2868),
        "device_w": 1056,
        "bezel": 15,
        "screen_corner_r": 64,
        "device_y": 738,
        "text_top": 205,
        "frame_file": "iphone-6.9-frame.png",
    },
    "android": {
        "canvas": (1080, 2400),
        "device_w": 864,
        "bezel": 8,
        "screen_corner_r": 44,
        "device_y": 625,
        "text_top": 163,
        "frame_file": "android-frame.png",
    },
}

BOTTOM_BLEED_PX = 500


def _default_frame_path(device: str, project_override_dir: str = None) -> str:
    """Resolve the frame asset path. Project override takes precedence."""
    profile = DEVICE_PROFILES[device]
    if project_override_dir:
        override = os.path.join(project_override_dir, profile["frame_file"])
        if os.path.exists(override):
            return override
    return os.path.join(SKILL_DIR, "assets", profile["frame_file"])


def compose(
    device: str,
    bg_style: str,
    bg_colors: list,
    verb: str,
    desc: str,
    text_color: str,
    screenshot_path: str,
    output_path: str,
    frame_path: str = None,
    font_path: str = None,
    desc_font_path: str = None,
    bg_blob_position: str = "center",
    bg_blob_positions: str = "upper-left,lower-right",
    breakout_zone: tuple = None,
    breakout_rect: tuple = None,
    breakout_anchor: str = None,
    breakout_scale: float = 1.5,
    breakout_overflow: int = 100,
) -> None:
    if bg_style is None:
        bg_style = "plain"
    profile = DEVICE_PROFILES[device]
    canvas_w, canvas_h = profile["canvas"]
    device_w = profile["device_w"]
    bezel = profile["bezel"]
    screen_w = device_w - 2 * bezel
    device_y = profile["device_y"]
    text_top = profile["text_top"]
    device_x = (canvas_w - device_w) // 2
    screen_x = device_x + bezel
    screen_y = device_y + bezel

    # 1. Background.
    bg = bg_renderer.render(
        style=bg_style,
        size=(canvas_w, canvas_h),
        colors=bg_colors,
        blob_position=bg_blob_position,
        blob_positions=bg_blob_positions,
    ).convert("RGBA")

    # 2. App UI into the screen area, fit-to-width, bleeds below.
    shot = Image.open(screenshot_path).convert("RGBA")
    screen_scale = screen_w / shot.width
    sc_w = int(shot.width * screen_scale)
    sc_h = int(shot.height * screen_scale)
    shot_scaled = shot.resize((sc_w, sc_h), Image.LANCZOS)

    screen_h = canvas_h - screen_y + BOTTOM_BLEED_PX
    scr_mask = Image.new("L", bg.size, 0)
    ImageDraw.Draw(scr_mask).rounded_rectangle(
        [screen_x, screen_y, screen_x + screen_w, screen_y + screen_h],
        radius=profile["screen_corner_r"], fill=255,
    )
    scr_layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    scr_layer.paste(shot_scaled, (screen_x, screen_y))
    scr_layer.putalpha(scr_mask)
    canvas = Image.alpha_composite(bg, scr_layer)

    # 3. Photoreal frame + drop shadow.
    frame_path = frame_path or _default_frame_path(device)
    canvas = frame_composite.composite_frame(
        canvas=canvas,
        frame_path=frame_path,
        device_x=device_x,
        device_y=device_y,
        device_w=device_w,
        with_shadow=True,
    )

    # 4. Headline.
    canvas, headline_band = headline_render.draw_headline(
        canvas=canvas,
        verb=verb,
        desc=desc,
        text_top=text_top,
        canvas_w=canvas_w,
        text_color=text_color,
        font_path=font_path,
        desc_font_path=desc_font_path,
    )

    # 5. Optional literal lifted panel (literal mode).
    panel_bbox = None
    panel_mode = "clean"
    derived_zone = None
    if breakout_rect is not None:
        if breakout_anchor not in ("left", "right"):
            raise ValueError("breakout_anchor required for literal mode")
        canvas, panel_bbox = lifted_panel.render(
            canvas=canvas, shot=shot, rect=breakout_rect,
            screen_x=screen_x, screen_y=screen_y, screen_scale=screen_scale,
            device_x=device_x, device_w=device_w,
            anchor=breakout_anchor, scale_factor=breakout_scale,
            overflow=breakout_overflow,
        )
        panel_mode = "literal"
        derived_zone = list(panel_bbox)
    elif breakout_zone is not None:
        panel_mode = "hero"
        derived_zone = list(breakout_zone)

    # 6. Save image + sidecar.
    canvas.convert("RGB").save(output_path, "PNG")
    print(f"✓ {output_path} ({canvas_w}×{canvas_h}) [{device}, mode={panel_mode}]")

    meta = {
        "device": device,
        "canvas": [canvas_w, canvas_h],
        "device_y": device_y,
        "screen_rect": [screen_x, screen_y, screen_w, canvas_h - screen_y],
        "panel_mode": panel_mode,
        "breakout_zone": derived_zone,
        "preserve_panel": list(panel_bbox) if panel_bbox else None,
        "headline_band": list(headline_band),
        "background": {"style": bg_style, "colors": bg_colors},
    }
    meta_path = os.path.splitext(output_path)[0] + ".meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)


def _parse_rect(s):
    parts = [int(p.strip()) for p in s.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(f"Rect must be 'x,y,w,h', got {s!r}")
    return tuple(parts)


def main():
    p = argparse.ArgumentParser(description="Compose store screenshot (Pillow-only).")
    p.add_argument("--device", choices=list(DEVICE_PROFILES.keys()), default="iphone-6.9")
    p.add_argument("--bg-style", default="plain", choices=[
        "plain", "linear-vertical", "linear-diagonal", "radial",
        "vignette", "blob", "dual-blob", "mesh-gradient",
    ])
    p.add_argument("--bg-color", required=True, help="Primary hex color")
    p.add_argument("--bg-color-2", default=None, help="Secondary hex (styles 2-8)")
    p.add_argument("--bg-color-3", default=None, help="Tertiary hex (dual-blob, mesh-gradient)")
    p.add_argument("--bg-color-4", default=None, help="Quaternary hex (mesh-gradient only)")
    p.add_argument("--bg-blob-position", default="center",
                   choices=list(bg_renderer.BLOB_POSITIONS.keys()))
    p.add_argument("--bg-blob-positions", default="upper-left,lower-right",
                   help="Comma-separated positions for dual-blob")
    p.add_argument("--verb", required=True)
    p.add_argument("--desc", required=True)
    p.add_argument("--text-color", default="white")
    p.add_argument("--screenshot", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--frame-path", default=None,
                   help="Override frame asset path (default: skill-bundled).")
    p.add_argument("--font-path", default=None)
    p.add_argument("--desc-font-path", default=None)
    p.add_argument("--breakout-rect", type=_parse_rect, default=None,
                   help="Literal mode source rect")
    p.add_argument("--breakout-zone", type=_parse_rect, default=None,
                   help="Hero mode canvas zone")
    p.add_argument("--breakout-anchor", choices=["left", "right"], default=None)
    p.add_argument("--breakout-scale", type=float, default=1.5)
    p.add_argument("--breakout-overflow", type=int, default=100)
    args = p.parse_args()

    if args.breakout_rect is not None and args.breakout_zone is not None:
        p.error("--breakout-rect and --breakout-zone are mutually exclusive.")

    bg_colors = [args.bg_color]
    for extra in (args.bg_color_2, args.bg_color_3, args.bg_color_4):
        if extra is not None:
            bg_colors.append(extra)

    compose(
        device=args.device,
        bg_style=args.bg_style,
        bg_colors=bg_colors,
        verb=args.verb, desc=args.desc, text_color=args.text_color,
        screenshot_path=args.screenshot, output_path=args.output,
        frame_path=args.frame_path,
        font_path=args.font_path, desc_font_path=args.desc_font_path,
        bg_blob_position=args.bg_blob_position,
        bg_blob_positions=args.bg_blob_positions,
        breakout_zone=args.breakout_zone,
        breakout_rect=args.breakout_rect,
        breakout_anchor=args.breakout_anchor,
        breakout_scale=args.breakout_scale,
        breakout_overflow=args.breakout_overflow,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests, verify pass**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/ -v
```
Expected: all bg, frame, headline, lifted_panel, and compose tests PASS

---

## Task 15: Update `overlay_zone.py` for the new sidecar shape

**Files:**
- Modify: `~/.claude/skills/aso-appstore-screenshots/scripts/overlay_zone.py`

The new sidecar adds `background` and changes some defaults; `overlay_zone.py` only reads `screen_rect`, `breakout_zone`, and `preserve_panel` which all still exist. Verify it still works and tidy any comments.

- [ ] **Step 1: Read the current file**

Run:
```bash
cat /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/scripts/overlay_zone.py | head -80
```

- [ ] **Step 2: If the file references removed fields (`headline_band` defaults, mask fields), update; otherwise leave as-is**

If `overlay_zone.py` references `mask_screen` or `mask_headline`, remove those lines. Keep all `screen_rect`, `breakout_zone`, `preserve_panel` reads.

- [ ] **Step 3: Run a quick smoke test**

Generate a scaffold first, then run overlay_zone on it:

```bash
mkdir -p /tmp/aso_smoke
python3 /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/scripts/compose.py \
  --device iphone-6.9 --bg-style plain --bg-color "#FFD7F0" \
  --verb TEST --desc "OVERLAY ZONE CHECK" --text-color "#BC004B" \
  --screenshot /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/tests/fixtures/sample_ui.png \
  --breakout-zone "60,950,760,820" \
  --output /tmp/aso_smoke/scaffold.png

python3 /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/scripts/overlay_zone.py /tmp/aso_smoke/
ls /tmp/aso_smoke/
```
Expected: `scaffold.png`, `scaffold.meta.json`, and `scaffold_with_zone.png` all present.

---

## Task 16: Implement `enhance_card.py` — prompt builder

**Files:**
- Create: `~/.claude/skills/aso-appstore-screenshots/scripts/enhance_card.py`
- Create: `~/.claude/skills/aso-appstore-screenshots/tests/test_enhance_card.py`

- [ ] **Step 1: Write the failing test**

Write to `~/.claude/skills/aso-appstore-screenshots/tests/test_enhance_card.py`:

```python
"""Tests for enhance_card.py — hero card prompt + composite."""
import enhance_card


def test_build_prompt_includes_creative_direction():
    prompt = enhance_card.build_prompt(
        creative_direction="A polished red sofa card on a white background.",
    )
    assert "polished red sofa card" in prompt
    assert "TRANSPARENT BACKGROUND" in prompt
    assert "DO NOT" in prompt


def test_build_prompt_short_enough():
    prompt = enhance_card.build_prompt(
        creative_direction="Some creative direction string here.",
    )
    # Wrapper alone should be ~50 words. Total under 200.
    assert len(prompt.split()) < 200
```

- [ ] **Step 2: Run, verify fail**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_enhance_card.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'enhance_card'`

- [ ] **Step 3: Create `enhance_card.py` with `build_prompt`**

Write to `~/.claude/skills/aso-appstore-screenshots/scripts/enhance_card.py`:

```python
#!/usr/bin/env python3
"""Hero card generator for ASO scaffolds.

Phase 7 (hero slots only). Calls /v1/images/generations with a transparent
background. The model paints ONE card with its own drop shadow onto an
empty canvas; Pillow composites the result onto the scaffold to produce
`final.png`.

The AI never sees the scaffold, the headline, or the app UI.
"""
PROMPT_WRAPPER = """TRANSPARENT BACKGROUND. Paint ONE polished card filling the canvas edge-to-edge.

CARD CONTENT:
{creative_direction}

SHADOW: soft drop shadow beneath the card, blurred, falling down and slightly outward.

DO NOT: paint anything outside the card itself. No extra cards, no surrounding text or labels, no decorative borders, no fake UI badges. The card is the only thing on the canvas."""


def build_prompt(creative_direction: str) -> str:
    """Assemble the hero card prompt with the creative_direction interpolated."""
    if not creative_direction or not creative_direction.strip():
        raise ValueError("creative_direction must be non-empty for hero slots")
    return PROMPT_WRAPPER.replace("{creative_direction}", creative_direction.strip())
```

- [ ] **Step 4: Run, verify pass**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_enhance_card.py -v
```
Expected: PASS

---

## Task 17: `enhance_card.py` — canvas sizing helper + composite math

**Files:**
- Modify: `~/.claude/skills/aso-appstore-screenshots/scripts/enhance_card.py`
- Modify: `~/.claude/skills/aso-appstore-screenshots/tests/test_enhance_card.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_enhance_card.py`:

```python
def test_canvas_size_padded_to_mult16():
    # breakout 760x820 + 60px shadow padding both sides = 880x940 → mult16 → 880x944
    w, h = enhance_card.canvas_size_for_zone((60, 950, 760, 820), shadow_pad=60)
    assert w % 16 == 0 and h % 16 == 0
    assert w >= 880 and h >= 940


def test_composite_card_at_breakout_position(assets_dir, tmp_path):
    from PIL import Image
    scaffold = Image.new("RGBA", (1320, 2868), (255, 215, 240, 255))
    # A small red card with full alpha, simulating an AI output.
    card_w, card_h = 880, 944
    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    # Paint a red rect inside, leaving 60px padding all around as transparent shadow margin.
    from PIL import ImageDraw
    ImageDraw.Draw(card).rectangle(
        [60, 60, card_w - 60, card_h - 60], fill=(255, 0, 0, 255)
    )
    scaffold_path = str(tmp_path / "scaffold.png")
    card_path = str(tmp_path / "card.png")
    final_path = str(tmp_path / "final.png")
    scaffold.convert("RGB").save(scaffold_path)
    card.save(card_path)

    enhance_card.composite_onto_scaffold(
        scaffold_path=scaffold_path,
        card_path=card_path,
        breakout_zone=(60, 950, 760, 820),
        shadow_pad=60,
        output_path=final_path,
    )
    final = Image.open(final_path)
    # Card paints over canvas at (zx - pad, zy - pad) = (0, 890). Card red
    # interior starts at zx, zy = (60, 950). Sample inside the red region.
    px = final.getpixel((60 + 100, 950 + 100))
    assert px[:3] == (255, 0, 0)
```

- [ ] **Step 2: Run, verify fail**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_enhance_card.py -v
```
Expected: FAILs on the new tests (missing functions).

- [ ] **Step 3: Add `canvas_size_for_zone` and `composite_onto_scaffold`**

Append to `enhance_card.py`:

```python
from PIL import Image


def _round_up_to_mult(n: int, mult: int = 16) -> int:
    return ((n + mult - 1) // mult) * mult


def canvas_size_for_zone(breakout_zone: tuple, shadow_pad: int = 60) -> tuple:
    """Compute the (w, h) of the AI canvas, padded for shadow + mult-16."""
    _, _, zw, zh = breakout_zone
    w = _round_up_to_mult(zw + 2 * shadow_pad)
    h = _round_up_to_mult(zh + 2 * shadow_pad)
    return w, h


def composite_onto_scaffold(
    scaffold_path: str,
    card_path: str,
    breakout_zone: tuple,
    shadow_pad: int,
    output_path: str,
) -> None:
    """Alpha-composite the AI-painted card onto the scaffold at the zone."""
    scaffold = Image.open(scaffold_path).convert("RGBA")
    card = Image.open(card_path).convert("RGBA")
    zx, zy, _, _ = breakout_zone
    scaffold.alpha_composite(card, (zx - shadow_pad, zy - shadow_pad))
    scaffold.convert("RGB").save(output_path, "PNG")
```

- [ ] **Step 4: Run, verify pass**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_enhance_card.py -v
```
Expected: PASS

---

## Task 18: `enhance_card.py` — main entry + OpenAI API call

**Files:**
- Modify: `~/.claude/skills/aso-appstore-screenshots/scripts/enhance_card.py`
- Modify: `~/.claude/skills/aso-appstore-screenshots/tests/test_enhance_card.py`

Wire the API call. Test by mocking the OpenAI client so we don't burn money.

- [ ] **Step 1: Add a mocked API-call test**

Append to `tests/test_enhance_card.py`:

```python
def test_enhance_calls_generate_with_transparent_background(monkeypatch, tmp_path):
    import base64, io, json
    from PIL import Image
    import enhance_card

    # Build a tiny card image as the mocked API response.
    fake_card = Image.new("RGBA", (880, 944), (0, 0, 0, 0))
    from PIL import ImageDraw
    ImageDraw.Draw(fake_card).rectangle(
        [60, 60, 820, 884], fill=(255, 0, 0, 255)
    )
    buf = io.BytesIO()
    fake_card.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    captured = {}

    class FakeImages:
        def generate(self, **kwargs):
            captured.update(kwargs)
            class R:
                data = [type("D", (), {"b64_json": b64})()]
            return R()

    class FakeClient:
        def __init__(self, **kwargs):
            self.images = FakeImages()

    monkeypatch.setattr(enhance_card, "OpenAI", FakeClient)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    # Set up a scaffold + sidecar.
    scaffold = Image.new("RGBA", (1320, 2868), (255, 215, 240, 255))
    scaffold_path = str(tmp_path / "scaffold.png")
    sidecar_path = str(tmp_path / "scaffold.meta.json")
    scaffold.convert("RGB").save(scaffold_path)
    json.dump(
        {
            "device": "iphone-6.9",
            "canvas": [1320, 2868],
            "panel_mode": "hero",
            "breakout_zone": [60, 950, 760, 820],
            "screen_rect": [147, 753, 1026, 2115],
            "background": {"style": "plain", "colors": ["#FFD7F0"]},
        },
        open(sidecar_path, "w"),
    )

    enhance_card.enhance(
        scaffold_path=scaffold_path,
        creative_direction="A polished red card.",
        output_card=str(tmp_path / "card.png"),
        output_final=str(tmp_path / "final.png"),
    )
    assert captured["model"] == "gpt-image-2"
    assert captured["background"] == "transparent"
    assert captured["size"] == "880x944"
    assert "polished red card" in captured["prompt"]
```

- [ ] **Step 2: Run, verify fail**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_enhance_card.py::test_enhance_calls_generate_with_transparent_background -v
```
Expected: FAIL (missing `enhance_card.enhance` and `OpenAI` symbol).

- [ ] **Step 3: Add the API-call entry point**

Append to `enhance_card.py`:

```python
import argparse
import base64
import io
import json
import os
import sys

from openai import OpenAI

SHADOW_PAD = 60


def _load_meta(scaffold_path: str) -> dict:
    meta_path = os.path.splitext(scaffold_path)[0] + ".meta.json"
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f"Sidecar not found: {meta_path}")
    with open(meta_path) as f:
        return json.load(f)


def enhance(
    scaffold_path: str,
    creative_direction: str,
    output_card: str,
    output_final: str,
    model: str = "gpt-image-2",
    quality: str = "high",
) -> None:
    """Generate the hero card via gpt-image-2 and composite onto scaffold."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY env var not set. "
            "Get a key at https://platform.openai.com/api-keys "
            "and export: export OPENAI_API_KEY=sk-..."
        )
    meta = _load_meta(scaffold_path)
    if meta.get("panel_mode") != "hero" or not meta.get("breakout_zone"):
        raise ValueError(
            "enhance_card requires a hero-mode scaffold with breakout_zone"
        )
    breakout_zone = tuple(meta["breakout_zone"])
    canvas_w, canvas_h = canvas_size_for_zone(breakout_zone, SHADOW_PAD)

    prompt = build_prompt(creative_direction)
    client = OpenAI(api_key=api_key)
    response = client.images.generate(
        model=model,
        prompt=prompt,
        size=f"{canvas_w}x{canvas_h}",
        background="transparent",
        quality=quality,
        n=1,
    )
    b64 = response.data[0].b64_json
    out_bytes = base64.b64decode(b64)
    Image.open(io.BytesIO(out_bytes)).save(output_card, format="PNG")

    composite_onto_scaffold(
        scaffold_path=scaffold_path,
        card_path=output_card,
        breakout_zone=breakout_zone,
        shadow_pad=SHADOW_PAD,
        output_path=output_final,
    )


def main():
    p = argparse.ArgumentParser(description="Generate a hero card and composite onto a scaffold.")
    p.add_argument("--scaffold", required=True)
    p.add_argument("--creative-direction", required=True,
                   help="Verbatim creative direction from aso_enhancements.md")
    p.add_argument("--output-card", required=True)
    p.add_argument("--output-final", required=True)
    p.add_argument("--model", default="gpt-image-2")
    p.add_argument("--quality", default="high", choices=["low", "medium", "high"])
    args = p.parse_args()
    enhance(
        scaffold_path=args.scaffold,
        creative_direction=args.creative_direction,
        output_card=args.output_card,
        output_final=args.output_final,
        model=args.model,
        quality=args.quality,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run, verify pass**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/test_enhance_card.py -v
```
Expected: all enhance_card tests PASS

---

## Task 19: Delete `enhance_openai.py`

**Files:**
- Delete: `~/.claude/skills/aso-appstore-screenshots/scripts/enhance_openai.py`

- [ ] **Step 1: Confirm no other code imports it**

Run:
```bash
grep -r "enhance_openai" /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/ --exclude-dir=docs
```
Expected: no live references (results only in docs we're about to rewrite).

- [ ] **Step 2: Delete the file**

Run:
```bash
rm /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/scripts/enhance_openai.py
```

- [ ] **Step 3: Re-run the full test suite to confirm nothing breaks**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/ -v
```
Expected: all tests PASS.

---

## Task 20: Rewrite `references/prompt-templates.md`

**Files:**
- Modify: `~/.claude/skills/aso-appstore-screenshots/references/prompt-templates.md` (full rewrite)

The new template is tiny — just the hero card wrapper and the assembly rule.

- [ ] **Step 1: Rewrite the file**

Write to `~/.claude/skills/aso-appstore-screenshots/references/prompt-templates.md`:

```markdown
# Hero card prompt template

Phase 7 (hero-mode slots only). The AI receives the prompt below + a
transparent canvas at the size of the breakout zone (plus shadow margin),
rounded to a multiple of 16. It returns a PNG of the card with its own
drop shadow on a transparent background. Pillow composites that PNG
onto the scaffold at the breakout-zone position to produce `final.png`.

## The prompt

```
TRANSPARENT BACKGROUND. Paint ONE polished card filling the canvas edge-to-edge.

CARD CONTENT:
{creative_direction}

SHADOW: soft drop shadow beneath the card, blurred, falling down and slightly outward.

DO NOT: paint anything outside the card itself. No extra cards, no surrounding text or labels, no decorative borders, no fake UI badges. The card is the only thing on the canvas.
```

## How it's assembled

`enhance_card.build_prompt(creative_direction)` substitutes the per-slot
`creative_direction` string from `aso_enhancements.md` into the
`{creative_direction}` placeholder.

Wrapper alone: ~50 words. Total with a typical `creative_direction`
(60–100 words): ~110–150 words. Far shorter than v2's 600+.

## What the AI never sees

- The headline text (rendered by Pillow on the scaffold)
- The phone chassis (rendered by Pillow from the photoreal frame PNG)
- The app UI inside the screen (composited by Pillow)
- The canvas background (rendered by Pillow from one of 8 styles)

The AI cannot drift anything outside the card because nothing else is
inside its prompt or canvas.

## API call

`enhance_card.py` calls `/v1/images/generations` (not `/edits`):

```python
response = client.images.generate(
    model="gpt-image-2",
    prompt=prompt,
    size=f"{w}x{h}",          # zone + 60px shadow padding both sides, mult-16
    background="transparent", # critical — the card needs alpha
    quality="high",
    n=1,
)
```

No mask, no input image, no `input_fidelity` flag (gpt-image-2 rejects it
anyway). The transparent canvas is implicit from `background="transparent"`.
```

---

## Task 21: Rewrite `references/phase-6-scaffold.md`

**Files:**
- Modify: `~/.claude/skills/aso-appstore-screenshots/references/phase-6-scaffold.md` (full rewrite)

- [ ] **Step 1: Rewrite the file**

Write to `~/.claude/skills/aso-appstore-screenshots/references/phase-6-scaffold.md`:

```markdown
# Phase 6 — Scaffold Production

**Goal:** Render the Pillow-deterministic scaffold for each slot. For clean
and literal slots, this is the final deliverable. For hero slots, it is the
base over which Phase 7 will paint the AI card.

**Inputs:**
- `aso_visual_direction.md` — device, background style + colors, frame asset, fonts, text color
- `aso_enhancements.md` — per-slot `panel_mode` + `breakout_zone` (hero) or `source_rect` (literal)
- `aso_benefits.md` — headlines (verb + descriptor)
- Source captures at `screenshots/source/<platform>/<locale>/img0N.png`

## Procedure

Per slot, derive the `compose.py` flags from `aso_enhancements.md` and run:

```bash
SKILL="$HOME/.claude/skills/aso-appstore-screenshots"

python3 "$SKILL/scripts/compose.py" \
  --device iphone-6.9 \
  --bg-style plain --bg-color "#FFD7F0" \
  --verb "REGALA" --desc "LO QUE YA NO USAS" --text-color "#BC004B" \
  --font-path "$PROJECT/screenshots/fonts/Nunito-Black.ttf" \
  --desc-font-path "$PROJECT/screenshots/fonts/Nunito-Bold.ttf" \
  --screenshot "$PROJECT/screenshots/source/ios/es/img01.png" \
  --breakout-zone "60,950,760,820" \
  --output "$PROJECT/screenshots/es-ios/01-regala/scaffold.png"
```

Per-mode flag mapping:

| `panel_mode` | Flags to add |
|---|---|
| `clean` | (none — base flags only) |
| `hero` | `--breakout-zone "x,y,w,h"` (canvas coords) |
| `literal` | `--breakout-rect "x,y,w,h" --breakout-anchor [left\|right] --breakout-scale 1.5 --breakout-overflow 100` |

Per-style background flag mapping:

| `bg-style` | Required flags |
|---|---|
| `plain` | `--bg-color "#X"` |
| `linear-vertical` | `--bg-color "#TOP" --bg-color-2 "#BOTTOM"` |
| `linear-diagonal` | `--bg-color "#A" --bg-color-2 "#B"` |
| `radial` | `--bg-color "#CENTER" --bg-color-2 "#EDGE"` |
| `vignette` | `--bg-color "#BASE" --bg-color-2 "#EDGE-DARK"` |
| `blob` | `--bg-color "#BASE" --bg-color-2 "#BLOB" --bg-blob-position [enum]` |
| `dual-blob` | `--bg-color "#BASE" --bg-color-2 "#GLOW-A" --bg-color-3 "#GLOW-B" --bg-blob-positions "upper-left,lower-right"` |
| `mesh-gradient` | `--bg-color "#BASE" --bg-color-2 "#A" --bg-color-3 "#B" --bg-color-4 "#C"` |

## Sidecar JSON shape

`compose.py` writes `scaffold.meta.json` next to each scaffold:

```json
{
  "device": "iphone-6.9",
  "canvas": [1320, 2868],
  "panel_mode": "hero | literal | clean",
  "breakout_zone": [x, y, w, h] | null,
  "preserve_panel": [x, y, w, h] | null,
  "screen_rect": [x, y, w, h],
  "headline_band": [x, y, w, h],
  "background": {"style": "plain", "colors": ["#FFD7F0"]}
}
```

The sidecar is used by Phase 7 (`enhance_card.py` reads `breakout_zone`) and
by `overlay_zone.py` for QA debug overlays.

## Sanity check (this is the gate)

Render scaffolds for all slots, then show every PNG to the user via `Read`.
Cheapest place to catch typos, wrong color, wrong rect, wrong breakout
position. Pillow is local and deterministic — regen costs nothing.

For `hero` slots, also generate the zone overlay to confirm placement:

```bash
python3 "$SKILL/scripts/overlay_zone.py" $PROJECT/screenshots/es-ios/01-regala/
```

Look at `scaffold_with_zone.png` — cyan rect = phone screen, magenta rect =
breakout zone. Confirm the zone Y aligns with where the AI card should sit.

## AskUserQuestion gate (per slot)

After rendering each scaffold and showing it to the user, use the
`AskUserQuestion` tool to lock the decision:

```python
AskUserQuestion(
    questions=[{
        "question": "Slot N ({verb} / {desc}): lock this scaffold, regenerate with tweaks, or change something upstream?",
        "header": "Slot N scaffold",
        "multiSelect": False,
        "options": [
            {
                "label": "Lock — proceed",
                "description": "Scaffold is ready. For clean/literal, it is the final. For hero, proceed to Phase 7."
            },
            {
                "label": "Regenerate with tweaks",
                "description": "Change a specific param (color, font size, breakout zone) and re-run compose.py."
            },
            {
                "label": "Go back to Phase 4 (visual direction)",
                "description": "Frame, background, or fonts need changing for the whole deck."
            }
        ]
    }]
)
```

Iterate until the scaffold is locked, then move to the next slot.

## Output

Per slot:
- `scaffold.png` — Pillow-rendered finished-looking image
- `scaffold.meta.json` — sidecar
- `scaffold_with_zone.png` — debug overlay (hero + literal modes only)

## Gate

User locks every scaffold via AskUserQuestion before proceeding to Phase 7
(if any hero slots) or Phase 8 (replication) / Phase 9 (showcase).
```

---

## Task 22: Rewrite `references/phase-7-enhancement.md`

**Files:**
- Modify: `~/.claude/skills/aso-appstore-screenshots/references/phase-7-enhancement.md` (full rewrite)

- [ ] **Step 1: Rewrite the file**

Write to `~/.claude/skills/aso-appstore-screenshots/references/phase-7-enhancement.md`:

```markdown
# Phase 7 — Hero card (AI, hero slots only)

**Goal:** For each `hero` slot, generate a polished card with `gpt-image-2`
on a transparent canvas, then composite it onto the scaffold to produce
`final.png`. `clean` and `literal` slots skip this phase entirely — their
`scaffold.png` is already the final.

**Inputs:**
- `scaffold.png` + `scaffold.meta.json` (from Phase 6) — sidecar's `breakout_zone` tells `enhance_card.py` what size to request from the API
- `creative_direction` string from `aso_enhancements.md` (verbatim, per-slot)
- `OPENAI_API_KEY` env var

See [prompt-templates.md](./prompt-templates.md) for the full prompt shape.

## Procedure

ONE variant at a time (per `feedback_aso_thorough_on_drift` memory):

```bash
SKILL="$HOME/.claude/skills/aso-appstore-screenshots"
SLOT="$PROJECT/screenshots/es-ios/01-regala"

python3 "$SKILL/scripts/enhance_card.py" \
  --scaffold "$SLOT/scaffold.png" \
  --creative-direction "$(cat $SLOT/creative_direction.txt)" \
  --output-card "$SLOT/card.png" \
  --output-final "$SLOT/final.png"
```

Or programmatically (when `creative_direction` is short enough to inline):

```bash
python3 "$SKILL/scripts/enhance_card.py" \
  --scaffold "$SLOT/scaffold.png" \
  --creative-direction "A polished editorial photo card with rounded corners (~24px radius)..." \
  --output-card "$SLOT/card.png" \
  --output-final "$SLOT/final.png"
```

## How it works

1. `enhance_card.py` reads the sidecar to get `breakout_zone`.
2. Computes the canvas size: `(zw + 120) × (zh + 120)`, rounded to mult-16.
   The 60 px padding on each side gives the AI room to paint the card's
   drop shadow without it being clipped.
3. Builds the prompt using `build_prompt(creative_direction)` — see
   [prompt-templates.md](./prompt-templates.md).
4. Calls `/v1/images/generations` with `background="transparent"`,
   `quality="high"`, `model="gpt-image-2"`.
5. Saves the AI output as `card.png`.
6. Alpha-composites `card.png` onto `scaffold.png` at the breakout-zone
   position (offset by `-shadow_pad` so the shadow margin aligns) →
   saves as `final.png`.

## Outputs

- `card.png` — AI output, transparent canvas, card + its own shadow (savable standalone)
- `final.png` — scaffold + card composited

## AskUserQuestion gate (per card)

After each fire, show the user `card.png` and `final.png` via `Read`. Then:

```python
AskUserQuestion(
    questions=[{
        "question": "Slot N hero card: lock as winner, refire with adjusted prompt, or change the breakout zone?",
        "header": "Slot N card",
        "multiSelect": False,
        "options": [
            {
                "label": "Lock — proceed",
                "description": "card.png is good; final.png is the slot's deliverable."
            },
            {
                "label": "Refire with adjusted prompt",
                "description": "Tweak creative_direction in aso_enhancements.md and re-run enhance_card.py for this slot."
            },
            {
                "label": "Change the breakout zone",
                "description": "Update breakout_zone in aso_enhancements.md, regen the scaffold (Phase 6), refire Phase 7."
            }
        ]
    }]
)
```

## Iterate

If the user wants changes, identify the smallest delta:

- **Wrong creative direction** → tweak `creative_direction` in `aso_enhancements.md`, refire that slot.
- **Hero zone wrong size / position** → update `breakout_zone` in `aso_enhancements.md`, regen scaffold (Phase 6), refire Phase 7.
- **Card content too literal / too abstract** → adjust phrasing in `creative_direction` (e.g., add "stylized" or "photorealistic", be specific about props).

ONE variant per refire, not three. Per the feedback memory: single variants during iteration.

## Save winner

Already saved automatically — `card.png` + `final.png` overwrite previous attempts.

Update `aso_generated_screenshots.md` per Phase 7 schema (see
[memory-schema.md](./memory-schema.md)) once user locks the slot.

## Output per slot

- `card.png`
- `final.png`

## Gate

User locks every hero card via AskUserQuestion. After all hero slots
approved, proceed to Phase 8 (replication) if multi-locale/platform;
otherwise Phase 9 (showcase).
```

---

## Task 23: Rewrite `references/phase-4-visual-direction.md`

**Files:**
- Modify: `~/.claude/skills/aso-appstore-screenshots/references/phase-4-visual-direction.md` (full rewrite)

- [ ] **Step 1: Rewrite the file**

Write to `~/.claude/skills/aso-appstore-screenshots/references/phase-4-visual-direction.md`:

```markdown
# Phase 4 — Visual Direction

**Goal:** Lock the visual cues that stay constant across the entire deck:
device profile, frame asset, background style + colors, fonts, text color.
Persist to `aso_visual_direction.md`.

**Inputs:** `aso_app_context.md` (brand cues, vibe), `aso_benefits.md` (the
headlines whose typography we're choosing).

## Procedure — driven by sequential `AskUserQuestion` calls

The skill walks the user through binding decisions one at a time. Each
decision is an `AskUserQuestion` call. Free-text input is reserved for hex
colors and asset paths.

### Decision 1 — Device profile

```python
AskUserQuestion(questions=[{
    "question": "Which device size profile? (Determines canvas dimensions and which frame asset is used.)",
    "header": "Device",
    "multiSelect": False,
    "options": [
        {"label": "iphone-6.9 (Recommended)", "description": "1320×2868, Apple's primary required size for App Store Connect."},
        {"label": "iphone-6.7", "description": "1290×2796."},
        {"label": "iphone-6.5", "description": "1242×2688."},
        {"label": "android", "description": "1080×2400, Google Play Store."},
    ],
}])
```

### Decision 2 — Frame asset source

```python
AskUserQuestion(questions=[{
    "question": "Use the skill's bundled photoreal frame, or a project-local override?",
    "header": "Frame source",
    "multiSelect": False,
    "options": [
        {"label": "Bundled default (Recommended)", "description": "iPhone 17 Pro Max Deep Blue (Apple Design Resources) for iOS; Pixel-style silver for Android."},
        {"label": "Project override", "description": "Drop a custom frame PNG at screenshots/assets/{frame_file}; compose.py picks it up automatically."},
    ],
}])
```

### Decision 3 — Background style

```python
AskUserQuestion(questions=[{
    "question": "Which background style? (Same style applied to every slot in the deck.)",
    "header": "BG style",
    "multiSelect": False,
    "options": [
        {"label": "plain", "description": "One flat color edge-to-edge."},
        {"label": "linear-vertical", "description": "Vertical gradient, top color → bottom color."},
        {"label": "linear-diagonal", "description": "45° gradient, top-left → bottom-right."},
        {"label": "radial", "description": "Center color glow fades to edge color."},
        {"label": "vignette", "description": "Bright center, darker edges — focus on the phone."},
        {"label": "blob", "description": "One large soft glow at a named position over a base color."},
        {"label": "dual-blob", "description": "Two glows of different colors at named positions."},
        {"label": "mesh-gradient", "description": "Three soft glows blending (Stripe / Apple Music aesthetic)."},
    ],
}])
```

### Decision 4 — Colors (free-text per style)

Ask the user for the hex colors required by the chosen style. Style → colors
needed (per [phase-6-scaffold.md](./phase-6-scaffold.md) flag mapping):

| Style | Colors |
|---|---|
| `plain` | 1 hex |
| `linear-vertical`, `linear-diagonal`, `radial`, `vignette` | 2 hex |
| `blob` | 2 hex + blob_position enum |
| `dual-blob` | 3 hex + blob_positions enum-pair |
| `mesh-gradient` | 4 hex |

When the user is undecided between colors, render Slot 1's scaffold with
the user's top 2-3 choices (Pillow is cheap) and show all variants — pick
the winner via another `AskUserQuestion`.

### Decision 5 — Fonts

```python
AskUserQuestion(questions=[{
    "question": "Verb font (line 1) — must be a heavy/black weight for ASO impact",
    "header": "Verb font",
    "multiSelect": False,
    "options": [
        {"label": "Bundled default (Nunito Black)", "description": "Strong sans-serif, premium feel. Recommended for most decks."},
        {"label": "Project-supplied font", "description": "Provide path to a .ttf or .otf file at screenshots/fonts/."},
        {"label": "System default", "description": "Falls back to SF Pro Display Black or Arial Black."},
    ],
}])
```

Then similarly for descriptor font (typically Bold, not Black).

### Decision 6 — Text color

Free-text hex (e.g., `#BC004B`). Confirm with `AskUserQuestion`:

```python
AskUserQuestion(questions=[{
    "question": "Lock text color {color} for all headlines in the deck?",
    "header": "Text color",
    "multiSelect": False,
    "options": [
        {"label": "Lock", "description": "Use this color across all slots."},
        {"label": "Try a different hex", "description": "Free-text another hex value."},
    ],
}])
```

## Persistence — `aso_visual_direction.md`

Once all decisions are locked, write to memory:

```yaml
---
name: Visual direction
description: Locked visual cues for the deck
type: project
---
device: iphone-6.9
frame_asset: bundled-default          # or: project-override:screenshots/assets/iphone-6.9-frame.png
background:
  style: plain
  color: "#FFD7F0"
  color_2: null
  color_3: null
  color_4: null
  blob_position: null
  blob_positions: null
fonts:
  verb: "screenshots/fonts/Nunito-Black.ttf"
  desc: "screenshots/fonts/Nunito-Bold.ttf"
text_color: "#BC004B"
```

## Gate

All decisions locked via AskUserQuestion. Phase 4 memory file written.
Proceed to Phase 5 (Enhancement Analysis).
```

---

## Task 24: Update `references/memory-schema.md` for new visual-direction format

**Files:**
- Modify: `~/.claude/skills/aso-appstore-screenshots/references/memory-schema.md`

- [ ] **Step 1: Read the current file**

Run:
```bash
cat /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/references/memory-schema.md
```

- [ ] **Step 2: Update the `aso_visual_direction.md` section**

Locate the section that documents `aso_visual_direction.md` and replace its schema with:

```yaml
---
name: Visual direction
description: Locked visual cues for the deck (device, frame, background, fonts, colors)
type: project
---
device: iphone-6.9 | iphone-6.7 | iphone-6.5 | android
frame_asset: bundled-default | project-override:<relative-path-from-project>
background:
  style: plain | linear-vertical | linear-diagonal | radial | vignette | blob | dual-blob | mesh-gradient
  color: "#XXXXXX"
  color_2: "#XXXXXX" | null
  color_3: "#XXXXXX" | null
  color_4: "#XXXXXX" | null
  blob_position: upper-left | upper-right | lower-left | lower-right | center | null
  blob_positions: "<pos>,<pos>" | null
fonts:
  verb: <path-to-ttf-or-otf>
  desc: <path-to-ttf-or-otf>
text_color: "#XXXXXX"
```

Remove any reference to `provider:` / `provider_model:` (those are gone —
gpt-image-2 is the only model; Nano Banana is dropped from v3).

---

## Task 25: Light AskUserQuestion gate updates for phases 1, 2, 3

**Files:**
- Modify: `~/.claude/skills/aso-appstore-screenshots/references/phase-1-app-discovery.md`
- Modify: `~/.claude/skills/aso-appstore-screenshots/references/phase-2-headlines.md`
- Modify: `~/.claude/skills/aso-appstore-screenshots/references/phase-3-source-captures.md`

- [ ] **Step 1: Append AskUserQuestion gate template to phase-1**

Append to `references/phase-1-app-discovery.md`:

```markdown
## AskUserQuestion gate

Once the app summary is drafted, present it to the user and lock with:

\`\`\`python
AskUserQuestion(questions=[{
    "question": "Lock this app context summary, revise, or restart Phase 1?",
    "header": "App context",
    "multiSelect": False,
    "options": [
        {"label": "Lock", "description": "Write aso_app_context.md and proceed to Phase 2."},
        {"label": "Revise", "description": "Adjust specific lines without restarting."},
        {"label": "Restart Phase 1", "description": "The summary missed important context; gather more before drafting again."}
    ]
}])
\`\`\`
```

- [ ] **Step 2: Append AskUserQuestion gate template to phase-2**

Append to `references/phase-2-headlines.md`:

```markdown
## AskUserQuestion gate (per slot)

For each of the 5 slots' verb + descriptor pairs:

\`\`\`python
AskUserQuestion(questions=[{
    "question": "Slot N headline '{verb} / {desc}': approve, revise wording, or pick a different framework slot?",
    "header": "Slot N headline",
    "multiSelect": False,
    "options": [
        {"label": "Approve", "description": "Lock this verb + descriptor."},
        {"label": "Revise wording", "description": "Tweak verb or descriptor; keep the framework slot."},
        {"label": "Different framework slot", "description": "Try a different role in the Solt framework (Pain → Shift → Proof → Feature×2)."}
    ]
}])
\`\`\`
```

- [ ] **Step 3: Append AskUserQuestion gate template to phase-3**

Append to `references/phase-3-source-captures.md`:

```markdown
## AskUserQuestion gate (per slot pairing)

For each of the 5 slots' paired source capture:

\`\`\`python
AskUserQuestion(questions=[{
    "question": "Slot N source img0N.png: right fit for this headline, swap to a different file, or re-shoot?",
    "header": "Slot N source",
    "multiSelect": False,
    "options": [
        {"label": "Right fit", "description": "This capture conveys the slot's benefit visually. Lock the pairing."},
        {"label": "Swap to different file", "description": "Try a different existing capture (img0M.png or alt)."},
        {"label": "Re-shoot", "description": "No existing capture works; take a new one before locking."}
    ]
}])
\`\`\`
```

---

## Task 26: Light AskUserQuestion gate updates for phases 5, 8, 9

**Files:**
- Modify: `~/.claude/skills/aso-appstore-screenshots/references/phase-5-enhancements.md`
- Modify: `~/.claude/skills/aso-appstore-screenshots/references/phase-8-replication.md`
- Modify: `~/.claude/skills/aso-appstore-screenshots/references/phase-9-showcase.md`

- [ ] **Step 1: Append AskUserQuestion gate template to phase-5**

Append to `references/phase-5-enhancements.md`:

```markdown
## AskUserQuestion gates (per slot)

### Step 1 — panel_mode per slot

\`\`\`python
AskUserQuestion(questions=[{
    "question": "Slot N panel_mode: hero (AI paints a card), literal (Pillow lifts a UI panel), or clean (no breakout)?",
    "header": "Slot N mode",
    "multiSelect": False,
    "options": [
        {"label": "hero", "description": "AI paints a creative card per creative_direction. Use for editorial / hero moments."},
        {"label": "literal", "description": "Pillow lifts a literal UI element from the screen. Use when the proof is on-screen (numbers, badges)."},
        {"label": "clean", "description": "No breakout — the screen IS the message. Use for map / hero captures."}
    ]
}])
\`\`\`

### Step 2 — confirm creative_direction (hero slots only)

After the user authors the free-text `creative_direction` string:

\`\`\`python
AskUserQuestion(questions=[{
    "question": "Lock creative_direction for slot N: '{text}' ?",
    "header": "Creative direction",
    "multiSelect": False,
    "options": [
        {"label": "Lock", "description": "Use this verbatim in the Phase 7 prompt."},
        {"label": "Revise", "description": "Edit the text — try again."}
    ]
}])
\`\`\`
```

- [ ] **Step 2: Append AskUserQuestion gate template to phase-8**

Append to `references/phase-8-replication.md`:

```markdown
## AskUserQuestion gate

Once the primary deck (e.g., es-iOS) is locked, ask which decks to replicate:

\`\`\`python
AskUserQuestion(questions=[{
    "question": "Which decks should we replicate now? Pick all that apply.",
    "header": "Replicate decks",
    "multiSelect": True,
    "options": [
        {"label": "en-iOS", "description": "English headlines, iOS source captures."},
        {"label": "es-Android", "description": "Spanish headlines, Android source captures."},
        {"label": "en-Android", "description": "English headlines, Android source captures."}
    ]
}])
\`\`\`

Then per replicated slot, the Phase 6/7 gate templates from those phase
docs apply.
```

- [ ] **Step 3: Append AskUserQuestion gate template to phase-9**

Append to `references/phase-9-showcase.md`:

```markdown
## AskUserQuestion gate

After rendering the showcase composite:

\`\`\`python
AskUserQuestion(questions=[{
    "question": "Showcase composite: ship it, regenerate with different ordering, or revise an underlying slot?",
    "header": "Showcase",
    "multiSelect": False,
    "options": [
        {"label": "Ship it", "description": "Save as final showcase.png; deck is done."},
        {"label": "Regenerate with different ordering", "description": "Swap slot order; re-composite."},
        {"label": "Revise an underlying slot", "description": "Go back to Phase 6 or 7 for the offending slot."}
    ]
}])
\`\`\`
```

---

## Task 27: Update `references/setup-openai.md`; delete `references/setup-nano-banana.md`

**Files:**
- Modify: `~/.claude/skills/aso-appstore-screenshots/references/setup-openai.md`
- Delete: `~/.claude/skills/aso-appstore-screenshots/references/setup-nano-banana.md`

- [ ] **Step 1: Read the current setup-openai.md**

Run:
```bash
cat /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/references/setup-openai.md
```

- [ ] **Step 2: Rewrite setup-openai.md (full replacement)**

Write to `~/.claude/skills/aso-appstore-screenshots/references/setup-openai.md`:

```markdown
# Setting up OpenAI gpt-image-2

The skill calls `/v1/images/generations` (NOT `/edits`) to generate hero
cards on transparent canvases. The model is always `gpt-image-2`.

## Prerequisites

1. OpenAI account with billing enabled (gpt-image-2 is a paid model).
2. API key from https://platform.openai.com/api-keys.
3. Python SDK: `pip3 install openai pillow`.

## Auth

Export the key in your shell before running Phase 7:

```bash
export OPENAI_API_KEY=sk-...
```

The skill never writes this key to disk.

## API parameters used

```python
client.images.generate(
    model="gpt-image-2",
    prompt=<built-by-enhance_card.build_prompt>,
    size=f"{w}x{h}",          # mult-16, max 3840 edge, max 8.3 Mpx
    background="transparent", # critical
    quality="high",
    n=1,
)
```

**Not used:** `input_fidelity` (rejected by gpt-image-2 — returns
`400 invalid_input_fidelity_model`).

## Cost

Approximate per-call cost at the hero-card canvas size (~880×940):
~$0.04 per fire. A 5-slot deck with 3 hero slots costs ~$0.12 to generate
all cards. Refire cost is the same per attempt.

## Failure modes

| Failure | Cause | Fix |
|---|---|---|
| `400 invalid_input_fidelity_model` | The flag was passed | Remove the flag (gpt-image-2 rejects it) |
| `400 invalid_request_error: size` | Width or height not multiple of 16 | `canvas_size_for_zone()` should have rounded; check sidecar |
| Card extends past canvas / clipped shadow | Shadow margin too small | Increase `SHADOW_PAD` constant in `enhance_card.py` |
| AI paints multiple cards / text outside card | Prompt drift | Tighten `creative_direction`; ensure the DO NOT block is intact |
| OPENAI_API_KEY not set | Env var missing | Export the key |
```

- [ ] **Step 3: Delete setup-nano-banana.md**

Run:
```bash
rm /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/references/setup-nano-banana.md
```

- [ ] **Step 4: Search for and remove any remaining Nano Banana references**

Run:
```bash
grep -rn "nano-banana\|Nano Banana\|nano_banana" /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/references/ /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/SKILL.md
```
Expected: no results. If results found, edit those files to remove the references.

---

## Task 28: Update `SKILL.md` with the new pipeline summary

**Files:**
- Modify: `~/.claude/skills/aso-appstore-screenshots/SKILL.md`

- [ ] **Step 1: Read the current SKILL.md**

Run:
```bash
cat /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots/SKILL.md | head -80
```

- [ ] **Step 2: Update the "Scripts" section**

Find the section listing executables (currently mentions `compose.py`,
`enhance_openai.py`, `showcase.py`). Replace with:

```markdown
## Scripts

All executables live in `scripts/`:

- `scripts/compose.py` — Pillow-only scaffold renderer. Required flags: `--bg-style`, `--bg-color`, `--verb`, `--desc`, `--screenshot`, `--output`. Renders background (1 of 8 styles) → app UI → photoreal frame + Pillow drop shadow → headline → optional literal lifted panel. Writes `scaffold.png` + `scaffold.meta.json`. Per-mode flags:
  - `clean` mode: no extra flags
  - `hero` mode: `--breakout-zone "x,y,w,h"`
  - `literal` mode: `--breakout-rect "x,y,w,h" --breakout-anchor [left|right] --breakout-scale 1.5 --breakout-overflow 100`
- `scripts/enhance_card.py` — Hero card generator. Required flags: `--scaffold`, `--creative-direction`, `--output-card`, `--output-final`. Calls `/v1/images/generations` on `gpt-image-2` with `background="transparent"`. Returns the card PNG; Pillow composites onto the scaffold to produce `final.png`. Used in Phase 7 only.
- `scripts/overlay_zone.py` — QA debug overlay. Reads `scaffold.meta.json` and writes `scaffold_with_zone.png` with cyan = screen_rect, magenta = breakout_zone or preserve_panel.
- `scripts/showcase.py` — Side-by-side composite of finals (Phase 9). Reads `final.png` if present, else `scaffold.png` per slot.
```

- [ ] **Step 3: Update the "Key Principles" section to mention AskUserQuestion**

Add a bullet:

```markdown
- **Every binding decision is captured via `AskUserQuestion`**: the skill never relies on inferring user intent from free text for choice-between-options gates. Each phase doc includes a concrete `AskUserQuestion(...)` template at its gate step.
```

- [ ] **Step 4: Update the "Style consistency" section to mention frame + background**

Replace with:

```markdown
## Style consistency

- Same font, size, weight on every screenshot in a deck
- Same background style and color palette on every screenshot in a deck (locked in Phase 4)
- Same photoreal device frame on every screenshot in a deck (one frame asset per device profile, locked in Phase 4)
- Captures should be the same theme (light or dark mode) across the deck
```

- [ ] **Step 5: Run the full test suite to confirm everything still passes**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/ -v
```
Expected: all tests PASS.

---

## Task 29: Run an end-to-end smoke test (no API call)

**Files:**
- None — this is a verification step

- [ ] **Step 1: Render a clean-mode scaffold using the sample UI**

Run:
```bash
SKILL="/Users/andersonarroyo/.claude/skills/aso-appstore-screenshots"
mkdir -p /tmp/aso_smoke_clean
python3 "$SKILL/scripts/compose.py" \
  --device iphone-6.9 \
  --bg-style plain --bg-color "#FFD7F0" \
  --verb "SMOKE" --desc "TEST CLEAN MODE" --text-color "#BC004B" \
  --screenshot "$SKILL/tests/fixtures/sample_ui.png" \
  --output /tmp/aso_smoke_clean/scaffold.png
ls /tmp/aso_smoke_clean/
```
Expected: `scaffold.png` and `scaffold.meta.json` both present.

- [ ] **Step 2: Render a hero-mode scaffold and confirm the sidecar records the zone**

Run:
```bash
mkdir -p /tmp/aso_smoke_hero
python3 "$SKILL/scripts/compose.py" \
  --device iphone-6.9 \
  --bg-style mesh-gradient \
  --bg-color "#FFD7F0" --bg-color-2 "#FFE8F4" --bg-color-3 "#FFC4E8" --bg-color-4 "#FFB8DC" \
  --verb "HERO" --desc "MESH GRADIENT BG" --text-color "#BC004B" \
  --screenshot "$SKILL/tests/fixtures/sample_ui.png" \
  --breakout-zone "60,950,760,820" \
  --output /tmp/aso_smoke_hero/scaffold.png
cat /tmp/aso_smoke_hero/scaffold.meta.json
```
Expected: `panel_mode: hero`, `breakout_zone: [60, 950, 760, 820]`, `background: {style: mesh-gradient, colors: [...]}`.

- [ ] **Step 3: Generate the zone overlay**

Run:
```bash
python3 "$SKILL/scripts/overlay_zone.py" /tmp/aso_smoke_hero/
ls /tmp/aso_smoke_hero/
```
Expected: `scaffold_with_zone.png` present.

- [ ] **Step 4: Visually inspect each smoke output**

Use the `Read` tool (in a Claude Code session) to open `/tmp/aso_smoke_clean/scaffold.png` and `/tmp/aso_smoke_hero/scaffold.png` and `/tmp/aso_smoke_hero/scaffold_with_zone.png`. Confirm:
- Frame is photoreal Deep Blue iPhone with transparent screen showing the blue sample UI
- Headline is rendered above the phone in deep rose
- Drop shadow visible under the phone
- For mesh-gradient: 3 soft glows blending into background pink

---

## Task 30: Run an end-to-end test WITH an API call (single hero slot)

**Files:**
- None — verification, requires OPENAI_API_KEY

This is the final integration check. Costs ~$0.04.

- [ ] **Step 1: Ensure `OPENAI_API_KEY` is set**

Run:
```bash
echo "${OPENAI_API_KEY:-NOT SET}" | sed 's/sk-.*/sk-***/'
```
Expected: `sk-***` (not "NOT SET"). If unset: `export OPENAI_API_KEY=sk-...`

- [ ] **Step 2: Generate a hero card on the smoke scaffold**

Run:
```bash
python3 "$SKILL/scripts/enhance_card.py" \
  --scaffold /tmp/aso_smoke_hero/scaffold.png \
  --creative-direction "A polished editorial photo card with rounded corners (~24px radius), clean white card surface, showing a stylized vintage record player on a wooden table with warm afternoon light." \
  --output-card /tmp/aso_smoke_hero/card.png \
  --output-final /tmp/aso_smoke_hero/final.png
ls /tmp/aso_smoke_hero/
```
Expected: `card.png` (transparent PNG, ~880×944) and `final.png` (scaffold + card composited) both present.

- [ ] **Step 3: Visually inspect both outputs**

Use the `Read` tool to inspect `/tmp/aso_smoke_hero/card.png` and `/tmp/aso_smoke_hero/final.png`. Confirm:
- `card.png` shows the card on a transparent background with its own drop shadow
- `final.png` shows the scaffold (frame + headline + UI) with the card composited at the breakout zone position
- Headline letters are pixel-identical to the scaffold (the AI never saw them — they can't drift)
- Phone chassis matches the photoreal Apple frame (the AI never rendered it — it can't drift)

- [ ] **Step 4: Final test run**

Run:
```bash
cd /Users/andersonarroyo/.claude/skills/aso-appstore-screenshots && python3 -m pytest tests/ -v
```
Expected: ALL tests PASS — the v3 pipeline is live.

---

## Self-Review Notes

**Spec coverage checklist:**
- Pillow-first scaffold pipeline → Tasks 3-14 (bg renderer, frame composite, headline, lifted panel, compose orchestration)
- Photoreal frame asset, app-agnostic with override → Task 1 (assets) + Task 14 (`_default_frame_path` with override hook) + Task 23 (Phase 4 records `frame_asset`)
- 8 background styles → Tasks 3-10
- Phase 6/7 contract + file outputs → Tasks 14, 21, 22
- Hero card AI call via /v1/images/generations → Tasks 16-18
- AskUserQuestion universal gate → Tasks 23, 25, 26 + templates baked into 21, 22
- Migration plan execution → Tasks 1, 19, 27 (delete legacy) + Task 28 (SKILL.md update)
- Out of scope: Nano Banana → Task 27 (delete + grep)
- Smoke tests → Tasks 29, 30

**Type consistency:** `panel_mode` values (`clean | literal | hero`) consistent across compose.py, sidecar JSON, phase-6/7 docs. `breakout_zone` is always a 4-tuple `(x, y, w, h)`. `background` block consistent in sidecar and `aso_visual_direction.md`.

**No placeholders found:** every step has explicit code or commands. No "TBD" / "implement appropriately" / "similar to above" without showing the code.
