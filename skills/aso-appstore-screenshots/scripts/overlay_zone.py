"""Visual inspection helper: overlay the breakout_zone (and screen_rect) on a
rendered scaffold so the analyst can confirm Y-alignment with the on-screen
element it's lifting.

Reads `scaffold.meta.json` next to the scaffold and overlays:
- the screen_rect as a thin cyan outline (for reference)
- the breakout_zone as a translucent magenta fill + solid border

Usage:
    python3 overlay_zone.py SCAFFOLD_DIR

Where SCAFFOLD_DIR contains scaffold.png and scaffold.meta.json. Writes
scaffold_with_zone.png alongside.

Useful for hero mode (where the zone is invisible at scaffold time) or any time
you want to verify literal panel placement without rendering the AI fill.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    sc_dir = Path(sys.argv[1])
    sc_path = sc_dir / "scaffold.png"
    meta_path = sc_dir / "scaffold.meta.json"
    if not sc_path.exists() or not meta_path.exists():
        print(f"ERROR: missing {sc_path} or {meta_path}")
        sys.exit(2)

    meta = json.loads(meta_path.read_text())
    zone = meta.get("breakout_zone")
    screen = meta.get("screen_rect")
    img = Image.open(sc_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    if screen:
        sx, sy, sw, sh = screen
        d.rectangle([sx, sy, sx + sw, sy + sh], outline=(0, 200, 255, 200), width=4)

    if zone:
        x, y, w, h = zone
        d.rectangle([x, y, x + w, y + h], fill=(255, 0, 100, 90), outline=(255, 0, 100, 255), width=8)
    else:
        print(f"NOTE: panel_mode={meta.get('panel_mode')} has no breakout_zone — only screen_rect drawn")

    out = Image.alpha_composite(img, overlay)
    out_path = sc_dir / "scaffold_with_zone.png"
    out.convert("RGB").save(out_path)
    print(f"wrote {out_path} | zone={zone} screen={screen} mode={meta.get('panel_mode')}")


if __name__ == "__main__":
    main()
