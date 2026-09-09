"""Visual inspection helper: overlay a source_rect on a source screenshot.

Usage:
    python3 preview_crop.py SOURCE_PNG x,y,w,h OUTPUT_PNG [LABEL]

Draws a translucent magenta rectangle with a solid border + label at the rect
coords on a copy of the source image. Useful to verify a literal-mode
source_rect captures the intended UI element BEFORE running compose.py.
"""
import sys
from PIL import Image, ImageDraw, ImageFont


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    src_path = sys.argv[1]
    x, y, w, h = (int(v) for v in sys.argv[2].split(","))
    out_path = sys.argv[3]
    label = sys.argv[4] if len(sys.argv) > 4 else f"crop ({x},{y},{w},{h})"

    img = Image.open(src_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    d.rectangle([x, y, x + w, y + h], fill=(255, 0, 100, 90), outline=(255, 0, 100, 255), width=8)
    try:
        font = ImageFont.truetype(
            "/Users/andersonarroyo/Documents/01_projects/waki/screenshots/fonts/Nunito-Bold.ttf",
            48,
        )
    except OSError:
        font = ImageFont.load_default()
    d.rectangle([x, max(y - 80, 0), x + 600, max(y - 10, 60)], fill=(255, 0, 100, 230))
    d.text((x + 16, max(y - 70, 10)), label, fill=(255, 255, 255, 255), font=font)
    out = Image.alpha_composite(img, overlay)
    out.convert("RGB").save(out_path)
    print(f"wrote {out_path} ({img.size[0]}x{img.size[1]} source, rect={x},{y},{w},{h})")


if __name__ == "__main__":
    main()
