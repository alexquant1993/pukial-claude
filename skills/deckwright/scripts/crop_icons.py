"""Slice an icon-sheet screenshot into ic_<name>_<key>.png.

Cell size is derived from the screenshot's own dimensions, which makes this
device-pixel-ratio agnostic: capture at 1x or 2x and the crop is the same.

One entry in SHEETS per icon sheet. `--sheet NAME` picks one and is
REQUIRED: the filenames this writes end in the sheet's colour key, so a
default would let a screenshot of one sheet be cropped under another sheet's
names, and the only symptom would be a missing-file raise mid-deck weeks
later.

Run: uv run --offline --no-project --with pillow \
       python scripts/crop_icons.py out/relay/iconsheet.png brands/relay/icons \
       --sheet relay
"""

import argparse
from pathlib import Path

from PIL import Image

# Each LIST order MUST match the LIST in the sheet it is named for. These
# comments are the only contract between the two files, which is why every
# sheet names its cropper entry and every entry names its sheet.
#
# templates/iconsheet.html - the skeleton a new brand copies. It is not any
# brand's sheet: nothing in the repository is cropped from it, and its entry
# exists so the skeleton is runnable end to end before the brand has icons.
TEMPLATE = [("activity", "blue"), ("network", "blue"), ("zap", "blue"),
            ("search", "blue")]
# brands/relay/iconsheet.html - the worked sheet, and the one the committed
# icons came from.
RELAY = [("terminal", "ink"), ("activity", "ink"), ("users", "ink"),
         ("zap", "ink"), ("arrowup", "ink"), ("arrowdown", "ink")]

SHEETS = {
    "template": (TEMPLATE, 4, 1),
    "relay": (RELAY, 6, 1),
}


def crop(sheet_path, out_dir, name):
    """Slice `sheet_path` into `out_dir`, returning the paths written."""
    if name not in SHEETS:
        raise SystemExit("no such sheet %r; known: %s"
                         % (name, ", ".join(sorted(SHEETS))))
    icons, cols, rows = SHEETS[name]
    img = Image.open(str(sheet_path)).convert("RGBA")
    cw, ch = img.width / float(cols), img.height / float(rows)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for i, (icon, key) in enumerate(icons):
        x, y = (i % cols) * cw, (i // cols) * ch
        cell = img.crop((int(round(x)), int(round(y)),
                         int(round(x + cw)), int(round(y + ch))))
        path = out_dir / ("ic_%s_%s.png" % (icon, key))
        cell.save(path)
        print("wrote %s (%dx%d)" % (path, cell.width, cell.height))
        written.append(path)
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--sheet-name", "--sheet", dest="name", required=True,
                    choices=sorted(SHEETS),
                    help="which sheet the screenshot came from; no default, "
                         "because the wrong one writes plausible filenames")
    args = ap.parse_args()
    crop(args.sheet, args.out_dir, args.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
