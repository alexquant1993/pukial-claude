"""Draw the placeholder wordmark `brands/relay` carries.

Run once; the output is committed. It is a placeholder set from the brand's
own wordmark guideline - never commit a real organisation's mark here.

`wordmark()` is for a brand whose guideline says the mark IS the word, set in
the display face. Relay is that case: its `guidelines/brand-wordmark.html`
sets "Relay" in Space Grotesk 500 at -0.045em and says, in the file,
PLACEHOLDER - REPLACE WITH THE REAL MARK WHEN SUPPLIED.

There used to be a second shape here, `mark()`, which drew the synthetic
lockup marks the fixture brand `brands/example` carried: a glyph and a word
on a transparent ground. That brand was deleted when the repository dropped
to one, and with it the deferred minor that this script rewrote all four
marks on every run whichever brand you wanted.

Two marks, not two designs: the same word in the two inks Relay allows a mark
to carry. The cover and the section slides sit on #0A0A0A, and an ink wordmark
on an ink ground is an invisible footer that no shape count would notice.

Run: uv run --offline --no-project --with pillow python scripts/make_placeholder_logos.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RELAY = ROOT / "brands" / "relay"
SS = 8  # supersample, then downscale for clean edges


def wordmark(path, text, fg, font_path, size=26, track_em=-0.045, pad=2):
    """A word set in the brand's face, tracked, cropped to its own ink.

    Drawn glyph by glyph because PIL has no letter-spacing: the advance of
    each character is taken from the face and the tracking added to it, the
    same arithmetic `deck_kit.metrics.width` does for a measurement. Cropped
    to the ink's bounding box so the caller can place the mark by height and
    get its true aspect back - a mark padded with transparent ascender space
    lands smaller than asked for and looks like a rendering bug.
    """
    face = ImageFont.truetype(str(font_path), size * SS)
    spacing = size * SS * track_em
    width = sum(face.getlength(ch) + spacing for ch in text)
    img = Image.new("RGBA", (int(width) + 8 * SS, int(size * 2 * SS)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 4 * SS
    for ch in text:
        d.text((x, size * SS * 0.4), ch, fill=fg, font=face)
        x += face.getlength(ch) + spacing
    img = img.crop(img.getbbox())
    scale = 1.0 / SS
    img = img.resize((max(1, int(round(img.width * scale + pad))),
                      max(1, int(round(img.height * scale + pad)))), Image.LANCZOS)
    img.save(path)
    print("wrote %s (%dx%d)" % (path, img.width, img.height))


if __name__ == "__main__":
    # Relay: ink #0A0A0A, never #000 (its readme, "Colors"). Set in the
    # display face itself, which scripts/fetch_fonts.py puts on disk. Relay's
    # guideline says Space Grotesk 500; this brand declares two weights per
    # family, so the mark is drawn in Bold - the nearer of the two to a 500,
    # and the weight a wordmark is set in anyway.
    wordmark(RELAY / "logo_primary.png", "Relay", (10, 10, 10, 255),
             RELAY / "fonts" / "SpaceGrotesk-Bold.ttf")
    wordmark(RELAY / "logo_inverse.png", "Relay", (255, 255, 255, 255),
             RELAY / "fonts" / "SpaceGrotesk-Bold.ttf")
