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
