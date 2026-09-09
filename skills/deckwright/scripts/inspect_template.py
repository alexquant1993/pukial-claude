"""Report a deck against a brand's template contract, clause by clause.

This is how a corporate master gets adopted: point it here, fix whatever it
fails, and the builders work against it unchanged.

`--variant NAME` checks the deck against the same brand's contract under the
variant master and layout names `make_template.py --variant NAME` writes, so
the second master of the Phase 2 round trip faces the contract verifier the
same way the host's does.

Run: uv run --offline --no-project --with python-pptx --with pillow \
       python scripts/inspect_template.py --brand relay deck.pptx
     uv run --offline --no-project --with python-pptx --with pillow \
       python scripts/inspect_template.py --brand relay --variant donor \
         out/template2.pptx
"""

import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pptx import Presentation

from deck_kit.brand import load_brand
from make_template import variant_spec


UNNAMED_REMEDY = (
    "this deck's slide masters carry no usable names. Name the master in "
    "PowerPoint's Slide Master view (View > Slide Master, rename), or "
    "generate a template with make_template.py --brand %s. Do NOT set "
    "master_name = \"\" in brand.py: BrandSpec refuses it, because an empty "
    "name binds to whichever master comes first, which is an index.")


def _name_remedy(spec, names):
    """The line printed under a failed master clause, or None.

    The contract's one rule is "by name, never by index", and a real
    corporate template usually supplies no names to bind to: the file that
    prompted this had four masters all called '' and a hundred layouts with
    names repeated across and within them. "Fix what it reports" had no
    documented fix for that case, and both obvious moves are wrong - an
    empty `master_name` is an index in disguise (BrandSpec now refuses it),
    and renaming a master inside somebody else's deck is editing their
    artifact. So the report says what to do.
    tests/test_template.py::test_inspect_names_the_remedy_for_an_unnamed_master.
    """
    blank = [n for n in names if not n.strip()]
    if blank:
        return UNNAMED_REMEDY % spec.name
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        return ("this deck names the same master more than once (%s), so a "
                "name does not select one master. Rename them in "
                "PowerPoint's Slide Master view, or generate a template with "
                "make_template.py --brand %s."
                % (", ".join(repr(n) for n in duplicates), spec.name))
    return None


def clauses(spec, path):
    """(name, ok, detail, remedy) per clause; remedy is None unless there is one."""
    prs = Presentation(str(path))
    yield ("slide size", (prs.slide_width, prs.slide_height) == spec.slide_size_emu,
           "%s x %s EMU" % (prs.slide_width, prs.slide_height), None)

    names = [m.name for m in prs.slide_masters]
    ok_master = spec.master_name in names
    yield ("master %r" % spec.master_name, ok_master,
           "found: %s" % ", ".join(repr(n) for n in names),
           None if ok_master else _name_remedy(spec, names))

    if not ok_master:
        yield ("layout %r" % spec.layout_name, False, "master missing", None)
        yield ("background on layout", False, "master missing", None)
    else:
        master = next(m for m in prs.slide_masters if m.name == spec.master_name)
        layouts = [l.name for l in master.slide_layouts]
        ok_layout = spec.layout_name in layouts
        yield ("layout %r" % spec.layout_name, ok_layout,
               "found: %s" % ", ".join(repr(n) for n in layouts),
               None if ok_layout else _name_remedy(spec, layouts))
        if ok_layout:
            layout = next(l for l in master.slide_layouts if l.name == spec.layout_name)
            covering = [sh for sh in layout.shapes
                        if sh.width == prs.slide_width and sh.height == prs.slide_height]
            yield ("background on layout", bool(covering) or spec.background == "drawn",
                   "%d covering shape(s)" % len(covering), None)

    with zipfile.ZipFile(str(path)) as z:
        fonts = [n for n in z.namelist() if n.startswith("ppt/fonts/")]
    # Reported, never asserted: the count is information, not a contract.
    yield ("embedded fonts (reported)", True,
           "%d part(s), brand expects %d" % (len(fonts), spec.expects_embedded_fonts),
           None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--variant", default=None,
                    help="check against the variant master and layout names "
                         "make_template.py --variant NAME writes")
    ap.add_argument("deck", type=Path)
    args = ap.parse_args()
    spec = load_brand(args.brand)
    if args.variant:
        spec = variant_spec(spec, args.variant)

    failures = 0
    for name, ok, detail, remedy in clauses(spec, args.deck):
        print("%-4s %-34s %s" % ("PASS" if ok else "FAIL", name, detail))
        if not ok and remedy:
            print("     remedy: %s" % remedy)
        failures += 0 if ok else 1
    if failures:
        print("%d clause(s) failed" % failures)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
