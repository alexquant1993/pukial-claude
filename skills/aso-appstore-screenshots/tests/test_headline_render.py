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
    # Pixel where verb should be — top third of canvas, center band.
    # Scan a ±60px column band around center; font glyphs land slightly off the
    # exact midpoint depending on the typeface's advance widths.
    found = False
    for y in range(200, 400):
        for x in range(600, 720):
            px = out.getpixel((x, y))[:3]
            if px == (188, 0, 75):
                found = True
                break
        if found:
            break
    assert found, "expected to find text-color pixel in verb region"
    # Headline band should be returned and non-empty.
    assert headline_band[2] > 0 and headline_band[3] > 0
