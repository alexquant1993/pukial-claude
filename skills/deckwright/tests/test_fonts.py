"""Font tests open the package. The count of .fntdata parts, the position of
the embeddedFontLst inside presentation.xml and the byte size of a font part
are all invisible to any check that reads Python source."""

import re

import pytest

from deck_kit import fonts, merge
from deck_kit.brand import load_brand
from deck_kit.deck import add_slide, open_deck
from deck_kit.primitives import textbox

# TEMPLATE arrives from the session-scoped `template` fixture in conftest.py.
# Never a module constant pointing at out/: the gate runs the unit tests BEFORE
# it builds the template, and out/ is gitignored, so a hardcoded path fails on
# a clean checkout and, worse, silently uses a stale template on a dirty one.


@pytest.fixture(scope="module")
def brand():
    return load_brand("relay")


@pytest.fixture(scope="module")
def faces(brand):
    return [(brand.sans,
             brand.font_dir / brand.font_regular,
             brand.font_dir / brand.font_bold)]


@pytest.fixture(scope="module")
def plain(tmp_path_factory, template, brand):
    prs = open_deck(template, brand)
    slide = add_slide(prs, brand)
    textbox(slide, 80, 80, 600, 40, "PLAIN", 20, brand.style().INK, brand.sans)
    out = tmp_path_factory.mktemp("f") / "plain.pptx"
    prs.save(str(out))
    return out


@pytest.fixture(scope="module")
def donor(tmp_path_factory, plain, faces):
    out = tmp_path_factory.mktemp("f") / "donor.pptx"
    fonts.embed(plain, out, faces)
    return out


def test_a_plain_deck_has_no_embedded_fonts(plain):
    assert fonts.font_parts(merge.read_package(plain)) == []


def test_embed_writes_one_part_per_face_variant(donor):
    assert len(fonts.font_parts(merge.read_package(donor))) == 2  # regular, bold


def test_embed_writes_each_face_as_its_own_part(donor, faces):
    """NOT catalogue item 4, despite the obvious temptation.

    `embed` is a byte copy, so comparing part size to file size asserts that a
    copy is a copy. It cannot detect subsetting, because nothing in this module
    can produce a subset. Item 4 - embed ALL characters, not just the used
    subset - is a property of the COM donor route, pinned by
    `scripts/embed_fonts.ps1` setting SaveSubsetFonts = $false and by the
    `--expect-fonts` count on the final deck. `references/06` records item 4 as
    pinned there, not here.
    """
    parts = merge.read_package(donor)
    sizes = sorted(len(parts[n]) for n in fonts.font_parts(parts))
    expected = sorted((faces[0][1].stat().st_size, faces[0][2].stat().st_size))
    assert sizes == expected


def test_transplant_adds_exactly_the_donors_font_parts(tmp_path, plain, donor):
    """Catalogue item 1: PowerPoint strips embedded fonts when a human saves.
    The check is the count of .fntdata parts in the package."""
    out = tmp_path / "embedded.pptx"
    assert fonts.transplant(plain, donor, out, expect_parts=2) == 2
    assert len(fonts.font_parts(merge.read_package(out))) == 2


def test_transplant_refuses_a_count_that_does_not_match(tmp_path, plain, donor):
    """Exact values, never a floor. A donor that lost a face must stop the
    build, not quietly produce a deck missing its bold."""
    with pytest.raises(AssertionError):
        fonts.transplant(plain, donor, tmp_path / "x.pptx", expect_parts=21)


def test_transplant_refuses_a_destination_that_already_has_fonts(tmp_path, plain, donor):
    first = tmp_path / "once.pptx"
    fonts.transplant(plain, donor, first, expect_parts=2)
    with pytest.raises(AssertionError):
        fonts.transplant(first, donor, tmp_path / "twice.pptx", expect_parts=2)


def test_transplant_refuses_to_write_over_its_dest_or_src(tmp_path, plain, donor):
    with pytest.raises(ValueError, match="overwrite"):
        fonts.transplant(plain, donor, plain, expect_parts=2)
    with pytest.raises(ValueError, match="overwrite"):
        fonts.transplant(plain, donor, donor, expect_parts=2)


def test_embed_refuses_to_write_over_its_dest(tmp_path, plain, faces):
    with pytest.raises(ValueError, match="overwrite"):
        fonts.embed(plain, plain, faces)


def test_embedded_font_list_lands_after_notesSz_with_reminted_rids(tmp_path, plain, donor):
    """Catalogue item 2: the transplant is not a file copy. The block goes
    after <p:notesSz/>, its rIds are re-minted against the destination's rels,
    and [Content_Types].xml gets a Default for the fntdata extension."""
    out = tmp_path / "embedded.pptx"
    fonts.transplant(plain, donor, out, expect_parts=2)
    parts = merge.read_package(out)

    pres = parts["ppt/presentation.xml"].decode("utf-8")
    notes_end = re.search(r"<p:notesSz[^>]*/>", pres).end()
    lst = re.search(r"<p:embeddedFontLst>.*?</p:embeddedFontLst>", pres, re.S)
    assert lst.start() == notes_end, "embeddedFontLst must immediately follow notesSz"

    rels = parts["ppt/_rels/presentation.xml.rels"].decode("utf-8")
    known = re.findall(r'Id="(rId\d+)"', rels)
    assert len(known) == len(set(known)), "duplicate rId minted"
    used = set(re.findall(r'r:id="(rId\d+)"', lst.group(0)))
    assert used and used <= set(known)

    assert 'Extension="fntdata"' in parts["[Content_Types].xml"].decode("utf-8")
    assert merge.dangling_refs(parts) == []
