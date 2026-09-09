"""Build a font donor: write .fntdata parts straight from a brand's TTF files.

The engagement only ever produced embedded fonts through PowerPoint itself
(scripts/embed_fonts.ps1 here). This route is portable and needs no installed
font, but only the doubled COM check can say whether PowerPoint accepts it -
see docs/decisions.md.

Run: PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx \
       --with pillow python scripts/embed_fonts.py --brand relay \
       --deck out/template.pptx --out out/fontdonor.pptx
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from deck_kit.brand import load_brand
from deck_kit.fonts import embed


def write_specimen(deck, out, brand, faces):
    """A deck with one text box per face, and no font parts.

    `embed_fonts.ps1` embeds the faces a deck's text actually uses, so the
    donor needs text in each face before COM has anything to embed.
    """
    from deck_kit.deck import add_slide, open_deck
    from deck_kit.primitives import textbox

    prs = open_deck(deck, brand)
    style = brand.style()
    slide = add_slide(prs, brand)
    for i, (typeface, _regular, _bold) in enumerate(faces):
        textbox(slide, 80, 80 + i * 60, 900, 40,
                [("%s regular " % typeface, False), ("and bold", True)],
                20, style.INK, typeface)
    prs.save(str(out))
    return len(faces)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--deck", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--text-only", action="store_true",
                    help="write no font parts; add one text box per face so "
                         "PowerPoint has something to embed when "
                         "embed_fonts.ps1 runs over the result")
    args = ap.parse_args()
    brand = load_brand(args.brand)
    faces = [(brand.sans,
              brand.font_dir / brand.font_regular,
              brand.font_dir / brand.font_bold)]
    if args.text_only:
        n = write_specimen(args.deck, args.out, brand, faces)
        print("wrote a %d-face specimen -> %s (now run embed_fonts.ps1 on it)"
              % (n, args.out))
        return
    n = embed(args.deck, args.out, faces)
    print("embedded %d font part(s) -> %s" % (n, args.out))


if __name__ == "__main__":
    main()
