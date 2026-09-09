"""compose_qa.py - every test reads pixels back from the composed PNG."""

import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compose_qa.py"
sys.path.insert(0, str(ROOT / "scripts"))

import compose_qa  # noqa: E402

COLOURS = {1: (200, 30, 30), 2: (30, 200, 30), 3: (30, 30, 200)}


@pytest.fixture
def png_dir(tmp_path):
    d = tmp_path / "png"
    d.mkdir()
    for n, rgb in COLOURS.items():
        img = Image.new("RGB", (160, 90), (255, 255, 255))
        for x in range(50, 160):          # a solid block in the bottom strip, unique per slide
            for y in range(80, 90):
                img.putpixel((x, y), rgb)
        img.save(d / ("s%02d.png" % n))
    return d


def test_find_slides_orders_by_number_and_names_a_missing_one(png_dir):
    assert [n for n, _ in compose_qa.find_slides(png_dir)] == [1, 2, 3]
    assert [n for n, _ in compose_qa.find_slides(png_dir, slides=[3, 1])] == [1, 3]
    with pytest.raises(FileNotFoundError, match="s07.png"):
        compose_qa.find_slides(png_dir, slides=[1, 7])


def test_band_stacks_every_slide_in_order_with_a_gutter(png_dir, tmp_path):
    out = compose_qa.band(png_dir, (50, 80, 160, 90), tmp_path / "band.png", expect=3)
    img = Image.open(out).convert("RGB")
    assert img.size == (200 + 110, 10 * 3)
    for k, n in enumerate((1, 2, 3)):
        assert img.getpixel((200 + 5, k * 10 + 5)) == COLOURS[n], "row %d holds the wrong slide" % k
        assert img.getpixel((5, k * 10 + 1)) != COLOURS[n], "the gutter is not a gutter"


def test_band_fails_on_a_count_that_does_not_match(png_dir, tmp_path):
    with pytest.raises(ValueError, match="expected 4 slide"):
        compose_qa.band(png_dir, (50, 80, 160, 90), tmp_path / "band.png", expect=4)
    assert not (tmp_path / "band.png").exists(), "a failed composition wrote a file"


def test_band_refuses_a_box_outside_the_image(png_dir, tmp_path):
    """Pillow pads an out-of-range crop with black and raises nothing; a
    strip composed of padding would pass every visual check by being
    uniformly wrong."""
    with pytest.raises(ValueError, match="outside"):
        compose_qa.band(png_dir, (500, 800, 1600, 900), tmp_path / "band.png", expect=3)


def test_zoom_scales_the_rectangle_and_labels_each_row(png_dir, tmp_path):
    out = compose_qa.zoom(png_dir, (50, 80, 100, 90), tmp_path / "zoom.png", slides=[3, 1],
                          scale=2, expect=2)
    img = Image.open(out).convert("RGB")
    assert img.size == (130 + 100, 20 * 2)
    assert img.getpixel((130 + 10, 10)) == COLOURS[1]
    assert img.getpixel((130 + 10, 30)) == COLOURS[3]


def test_ink_separates_a_row_with_content_from_a_uniform_one(png_dir, tmp_path):
    """Row 1 crops x 0..160, so its scanlines start white and turn coloured at
    x=50: inked. A crop of the block alone (x 50..160) is uniform per
    scanline: blank. This is the assertion the gate uses to prove the band
    shows the footer region and not a blank strip of some size."""
    inked = compose_qa.band(png_dir, (0, 80, 160, 90), tmp_path / "inked.png", expect=3)
    got = compose_qa.ink(inked, rows=3, gutter=200, inked=[1, 2, 3], blank=[])
    assert got == {1: 110 * 10, 2: 110 * 10, 3: 110 * 10}
    blank = compose_qa.band(png_dir, (50, 80, 160, 90), tmp_path / "blank.png", expect=3)
    assert compose_qa.ink(blank, rows=3, gutter=200, inked=[], blank=[1, 2, 3]) == {1: 0, 2: 0, 3: 0}
    with pytest.raises(ValueError, match="row 2 .* no ink"):
        compose_qa.ink(blank, rows=3, gutter=200, inked=[2], blank=[])
    with pytest.raises(ValueError, match="row 1 .* ink"):
        compose_qa.ink(inked, rows=3, gutter=200, inked=[], blank=[1])


def test_ink_refuses_a_row_number_that_does_not_exist(png_dir, tmp_path):
    blank = compose_qa.band(png_dir, (50, 80, 160, 90), tmp_path / "blank.png", expect=3)
    with pytest.raises(ValueError, match="outside 1..3"):
        compose_qa.ink(blank, rows=3, gutter=200, inked=[], blank=[4])
    with pytest.raises(ValueError, match="outside 1..3"):
        compose_qa.ink(blank, rows=3, gutter=200, inked=[0], blank=[])


def test_the_cli_composes_and_refuses_to_write_over_an_input(png_dir, tmp_path):
    cmd = [sys.executable, str(SCRIPT), "band", "--png-dir", str(png_dir),
           "--box", "50,80,160,90", "--expect", "3"]
    ok = subprocess.run(cmd + ["--out", str(tmp_path / "cli.png")],
                        capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert "composed 3 slide(s)" in ok.stdout
    bad = subprocess.run(cmd + ["--out", str(png_dir / "s01.png")],
                         capture_output=True, text=True)
    assert bad.returncode == 1
    assert "FAIL" in bad.stdout + bad.stderr
