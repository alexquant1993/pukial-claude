"""The synthetic 'generated deck': slides built by a builder, to be
transplanted into the host.

Two slides, carrying the things a transplant has to bring with it or drop:
  - slide 1 has a picture, so a media part and its relationship travel;
  - slide 1 has a speaker note, so the notesSlide has to be dropped;
  - slide 2 gets a modern-comment anchor <p:ext> injected after the save, so
    the anchor strip has something to strip.

Built on the DONOR VARIANT of brands/relay - the second master
`scripts/make_template.py --brand relay --variant donor` writes - and not on
the host's own master. A donor whose master is a genuinely different part
exercises the master transplant (catalogue item 5, the reason merge.py
exists); a donor built on the host's template merges a template with itself,
where the copied master is byte-identical to the destination's and the
p:sldLayoutId re-mint is a no-op. `make_template.variant_spec` says exactly
what differs and what stays the same, and
tests/test_template.py::test_a_variant_template_is_a_second_master_of_the_same_brand
asserts it against the two generated files.

This used to be a second brand package, `brands/example2`. The repository now
carries one brand, so the second master is a variant of its own contract
rather than a second identity - which also makes the two masters visibly
different (white against Relay's PANEL) where the two fixture palettes were
not.

Run: PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx \
       --with pillow python examples/integration/build_donor.py \
       --template out/template2.pptx --out out/donor.pptx
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from deck_kit import merge
from deck_kit.brand import load_brand
from deck_kit.deck import add_slide, open_deck
from deck_kit.primitives import textbox

from make_template import variant_spec  # noqa: E402

COMMENT_EXT_URI = "{6950BFC3-D8DA-4A85-94F7-54DA5524770B}"
VARIANT = "donor"


def build(template, out):
    # The variant names, not the brand's own: open_deck resolves the layout by
    # name, and this template carries "Relay Content (donor)". Loading plain
    # brands/relay here would raise on a layout the donor template does not
    # have - which is the failure mode a by-index selector would have hidden.
    brand = variant_spec(load_brand("relay"), VARIANT)
    s = brand.style()

    prs = open_deck(template, brand)

    # 1: a picture (its media part and relationship must travel) and a
    #    speaker note (which must NOT travel - the notesSlide is dropped).
    slide = add_slide(prs, brand)
    textbox(slide, 80, 80, 900, 40, "Donor slide one", 20, s.INK, brand.sans)
    # Through the brand's own helper, so the mark keeps its aspect: placed at
    # a fixed 120x90 the wordmark was visibly stretched in the export. One
    # picture either way, which is what --min-pictures 1 / --max-pictures 1
    # on the final deck counts.
    s.wordmark(slide, 300, 300, 40)
    slide.notes_slide.notes_text_frame.text = "donor speaker note"

    # 2: plain content. The modern-comment anchor is injected below, after
    #    the save, because it is not something a builder writes through
    #    python-pptx - it is what a human's comment leaves behind.
    slide = add_slide(prs, brand)
    textbox(slide, 80, 80, 900, 40, "Donor slide two", 20, s.INK, brand.sans)

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))

    parts = merge.read_package(out)
    order = merge.slide_order(parts)
    xml = parts[order[1]].decode("utf-8")
    anchor = ('<p:extLst><p:ext uri="%s">'
              '<p188:commentRel xmlns:p188="http://example.invalid/p188" r:id="rId99"/>'
              "</p:ext></p:extLst>" % COMMENT_EXT_URI)
    parts[order[1]] = xml.replace("</p:sld>", anchor + "</p:sld>").encode("utf-8")
    merge.write_package(out, parts)

    print("wrote", out, "slides:", len(order))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    build(args.template, args.out)


if __name__ == "__main__":
    main()
