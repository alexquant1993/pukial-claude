"""Visual QA by composition: the same crop from many slides, stacked and labelled.

An agent that cannot look at a deck can still do pixel work by comparing
one region across every slide: a footer five pixels low on one slide is
invisible slide by slide and obvious in the stack.

    band: the same strip from every slide, stacked with a labelled gutter
    zoom: the same rectangle from chosen slides, scaled up, stacked

Input PNGs are `sNN.png` as scripts/export_png.ps1 writes them.

Run: uv run --offline --no-project --with python-pptx --with pillow python scripts/compose_qa.py band --png-dir out/png_walk --box 0,836,1600,900 --expect 2 --out out/qa/band.png
"""

import argparse
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from deck_kit.merge import refuse_in_place  # noqa: E402

GUTTER_FILL = (240, 240, 240)
RULE_FILL = (200, 0, 0)
NAME = re.compile(r"^s(\d+)\.png$")


def find_slides(png_dir, slides="all"):
    """Sorted (number, path) pairs. Names a missing number instead of skipping it."""
    png_dir = Path(png_dir)
    found = {}
    for p in png_dir.iterdir():
        m = NAME.match(p.name)
        if m:
            found[int(m.group(1))] = p
    wanted = sorted(found) if slides == "all" else sorted(set(int(s) for s in slides))
    out = []
    for n in wanted:
        if n not in found:
            raise FileNotFoundError("%s has no s%02d.png" % (png_dir, n))
        out.append((n, found[n]))
    return out


def _check_expect(pairs, expect):
    if expect is not None and len(pairs) != expect:
        raise ValueError("expected %d slide PNG(s), found %d" % (expect, len(pairs)))
    if not pairs:
        raise ValueError("no slide PNGs to compose")


def _crop(path, box):
    img = Image.open(path).convert("RGB")
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= img.width and 0 <= y0 < y1 <= img.height):
        raise ValueError("box %s lies outside %s (%dx%d)" % (box, path.name, img.width, img.height))
    return img.crop(box)


def _stack(crops, out, gutter, label):
    """crops: list of (number, image), all the same size."""
    w, h = crops[0][1].size
    canvas = Image.new("RGB", (gutter + w, h * len(crops)), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    for k, (n, crop) in enumerate(crops):
        top = k * h
        canvas.paste(crop, (gutter, top))
        draw.rectangle([0, top, gutter - 1, top + h - 1], fill=GUTTER_FILL)
        draw.text((10, top + max(0, h // 2 - 6)), label % n, fill=(0, 0, 0))
        # the row separator lives in the gutter only: a rule drawn across the
        # crop would overwrite its bottom pixel row, which for a footer band
        # is the row that matters
        draw.line([0, top + h - 1, gutter - 1, top + h - 1], fill=RULE_FILL)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    return out, canvas.size


def band(png_dir, box, out, *, slides="all", expect=None, gutter=200, label="slide %d"):
    """The same strip from every slide, stacked. Returns the output path."""
    pairs = find_slides(png_dir, slides)
    _check_expect(pairs, expect)
    refuse_in_place(out, [p for _, p in pairs])
    crops = [(n, _crop(p, box)) for n, p in pairs]
    path, size = _stack(crops, out, gutter, label)
    print("composed %d slide(s) -> %s (%dx%d)" % (len(crops), path, size[0], size[1]))
    return path


def zoom(png_dir, box, out, *, slides, scale=2, expect=None, gutter=130, label="s%d"):
    """The same rectangle from chosen slides at `scale`, stacked."""
    pairs = find_slides(png_dir, slides)
    _check_expect(pairs, expect)
    refuse_in_place(out, [p for _, p in pairs])
    x0, y0, x1, y1 = box
    target = ((x1 - x0) * scale, (y1 - y0) * scale)
    crops = [(n, _crop(p, box).resize(target, Image.NEAREST)) for n, p in pairs]
    path, size = _stack(crops, out, gutter, label)
    print("composed %d slide(s) -> %s (%dx%d)" % (len(crops), path, size[0], size[1]))
    return path


def ink(image, *, rows, gutter, inked, blank):
    """{row: pixels differing from their scanline's first pixel}, right of the gutter.

    Raises if a row named in `inked` has none or a row named in `blank` has any.
    Rows are 1-based, top to bottom, each `height // rows` tall.
    """
    img = Image.open(image).convert("RGB")
    if img.height % rows:
        raise ValueError("%s is %d px tall, not divisible into %d rows" % (image, img.height, rows))
    bad = sorted(r for r in set(inked) | set(blank) if not 1 <= r <= rows)
    if bad:
        raise ValueError("row(s) %s outside 1..%d" % (bad, rows))
    h = img.height // rows
    px = img.load()
    counts = {}
    for r in range(1, rows + 1):
        n = 0
        for y in range((r - 1) * h, r * h):
            first = px[gutter, y]
            n += sum(1 for x in range(gutter, img.width) if px[x, y] != first)
        counts[r] = n
    print("ink " + "  ".join("row %d: %d" % kv for kv in sorted(counts.items())))
    for r in inked:
        if counts.get(r, 0) == 0:
            raise ValueError("row %d has no ink; expected content there" % r)
    for r in blank:
        if counts.get(r, 0):
            raise ValueError("row %d has ink (%d px); expected a blank row" % (r, counts[r]))
    return counts


def _rows(text):
    return [int(v) for v in text.split(",")] if text else []


def _box(text):
    parts = [int(v) for v in text.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("box is x0,y0,x1,y1")
    return tuple(parts)


def _slides(text):
    return "all" if text == "all" else [int(v) for v in text.split(",")]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("band", "zoom"):
        p = sub.add_parser(name)
        p.add_argument("--png-dir", type=Path, required=True)
        p.add_argument("--box", type=_box, required=True, help="x0,y0,x1,y1 in PNG pixels")
        p.add_argument("--out", type=Path, required=True)
        p.add_argument("--expect", type=int, default=None, help="exact number of PNGs expected")
        p.add_argument("--slides", type=_slides, default="all" if name == "band" else None,
                       required=(name == "zoom"), help="all, or 1,2,3")
        if name == "zoom":
            p.add_argument("--scale", type=int, default=2)
    k = sub.add_parser("ink")
    k.add_argument("--image", type=Path, required=True)
    k.add_argument("--rows", type=int, required=True)
    k.add_argument("--gutter", type=int, required=True)
    k.add_argument("--inked", type=_rows, default=[], help="rows that must contain something, e.g. 2")
    k.add_argument("--blank", type=_rows, default=[], help="rows that must be uniform, e.g. 1")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "band":
            band(args.png_dir, args.box, args.out, slides=args.slides, expect=args.expect)
        elif args.cmd == "zoom":
            zoom(args.png_dir, args.box, args.out, slides=args.slides, scale=args.scale,
                 expect=args.expect)
        else:
            ink(args.image, rows=args.rows, gutter=args.gutter, inked=args.inked, blank=args.blank)
    except (ValueError, FileNotFoundError) as e:
        print("FAIL: %s" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
