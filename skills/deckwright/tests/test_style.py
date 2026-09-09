"""The brand style layer, walked over EVERY brand that ships one.

The type floors are the repository's, not one brand's. The repository ships
one brand today, so the walk covers one - but it is written as a walk, and
`_brands_with_style()` reads the brands directory rather than naming a brand,
so the day a second is added it is held to the same floors without this file
being edited. That is exactly when a floor gets broken, because a new brand's
scale is re-derived from a design system with floors of its own: Relay's own
is "nothing below 24px", which is 12.2 pt here and does not agree with this
repository's 8 to 11.

The module docstring of tests/test_no_source_grep_doctrines.py names this
file as the legitimate case of a test reading a brand module.
"""

import pytest
from pptx import Presentation

from deck_kit.brand import brands_dir, load_brand
from deck_kit.metrics import TextMetrics, WarnRegister


def _brands_with_style():
    """Every brand package that ships a style.py, by name."""
    root = brands_dir()
    return sorted(d.name for d in root.iterdir()
                  if (d / "brand.py").is_file() and (d / "style.py").is_file())


def _brands_with_furniture():
    """Those that also ship the full slide-furniture contract.

    A brand may ship a style.py that is a palette and a type scale and no
    more - the second fixture brand was exactly that - so header() and GEOM
    are checked only where they exist. Asserting them on a brand that does
    not draw slides would only force a fake.
    """
    out = []
    for name in _brands_with_style():
        style = load_brand(name).style()
        if hasattr(style, "header") and hasattr(style, "GEOM"):
            out.append(name)
    return out


WITH_STYLE = _brands_with_style()
WITH_FURNITURE = _brands_with_furniture()


@pytest.fixture(params=WITH_STYLE)
def any_style(request):
    return load_brand(request.param).style()


@pytest.fixture(params=WITH_FURNITURE)
def furnished(request):
    return load_brand(request.param)


@pytest.fixture(scope="module")
def style():
    return load_brand("relay").style()


@pytest.fixture
def slide():
    prs = Presentation()
    return prs.slides.add_slide(prs.slide_layouts[6])


@pytest.fixture
def m():
    return TextMetrics("brands/relay/fonts", "PublicSans-Regular.ttf",
                       "PublicSans-Bold.ttf", 1.11, 1.06)


def test_geometry_columns_sum_within_the_content_band(furnished):
    style = furnished.style()
    assert style.GEOM["col_x"][-1] + style.GEOM["col_w"] <= style.R


def test_type_scale_honours_the_spec_floors(style):
    assert style.T_BODY >= 11.0
    assert style.T_CAPTION >= 9.5
    assert style.T_COL_HEAD >= 12.0
    assert style.T_FOOT >= 8.0


def test_header_writes_kicker_title_and_page(furnished, slide):
    """The same signature in every brand: builders call it positionally, so
    a brand that reordered the arguments would build a whole deck with the
    subtitle in the title's box and nothing would raise."""
    style = furnished.style()
    warn = WarnRegister()
    style.header(slide, furnished.metrics(), warn, "01. Section",
                 "A title that fits", "A subtitle.", 7)
    texts = [sh.text_frame.text for sh in slide.shapes if sh.has_text_frame]
    assert "01. SECTION" in texts
    assert "A title that fits" in texts
    assert "7" in texts
    assert warn.clean


def test_header_warns_when_the_title_would_overflow(furnished, slide):
    style = furnished.style()
    warn = WarnRegister()
    style.header(slide, furnished.metrics(), warn, "01. Section",
                 "A title " * 40, "sub", 7)
    assert not warn.clean
    assert "OVERFLOW" in warn.dump()


def test_header_warns_when_the_sub_would_wrap(furnished, slide):
    """SUB_AVAIL's comment says "one line for every sub in the deck" and
    nothing checked it. A sub that wrapped to two lines pushed into the
    content under it and the build printed "no warnings"; it was caught by
    measuring by hand, which is what the register exists to replace."""
    style = furnished.style()
    warn = WarnRegister()
    style.header(slide, furnished.metrics(), warn, "01. Section",
                 "A title that fits", "A subtitle that goes on. " * 12, 7)
    assert not warn.clean
    assert "OVERFLOW sub:" in warn.dump()


def test_header_takes_the_bare_string_sub_every_builder_passes(furnished, slide):
    """The sub arrives as a plain string, the same argument `textbox` takes
    on the line above; measuring it must accept exactly that."""
    style = furnished.style()
    warn = WarnRegister()
    style.header(slide, furnished.metrics(), warn, "01. Section",
                 "A title that fits", "A short subtitle.", 7)
    assert warn.clean, warn.dump()


def test_the_core_library_holds_no_colour_values():
    """Colours belong to the brand. A palette constant creeping into the
    core is how the engagement ended up with two navies."""
    import pathlib
    import re

    offenders = []
    for path in pathlib.Path("src/deck_kit").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if re.search(r"RGBColor\s*\(", text):
            offenders.append(str(path))
    assert offenders == []


def test_every_type_size_honours_the_floors(any_style):
    """Naming four constants by hand let every violator through. This walks
    all of them, in every brand, so neither a new size nor a new brand can
    quietly slip under the floor - and a second brand is where it would
    happen, because its scale comes from a design system with floors of its
    own. Relay's is "nothing on a slide goes below 24px", which is 12.2 pt
    at this canvas and does not agree with this repository's 8 to 11."""
    micro = set(getattr(any_style, "ALL_CAPS_MICRO", ()))
    offenders = []
    for name in dir(any_style):
        if not name.startswith("T_"):
            continue
        size = getattr(any_style, name)
        if name in micro:
            continue
        if size < 9.0:
            offenders.append((name, size))
    assert offenders == [], (
        "sizes below 9 pt must be all-caps micro-labels listed in "
        "ALL_CAPS_MICRO; these are not: %s" % offenders)


def test_the_all_caps_exemption_list_names_only_real_constants(any_style):
    for name in getattr(any_style, "ALL_CAPS_MICRO", ()):
        assert hasattr(any_style, name), name


def test_every_all_caps_micro_size_stays_above_the_micro_floor(any_style):
    """The exemption licenses 8 pt, not any size at all."""
    for name in getattr(any_style, "ALL_CAPS_MICRO", ()):
        assert getattr(any_style, name) >= 8.0, name


def test_body_and_caption_floors_hold_specifically(furnished):
    style = furnished.style()
    assert style.T_BODY >= 11.0
    assert style.T_CAPTION >= 9.5
    assert style.T_PILL_SUB >= 9.5
    assert style.T_COL_HEAD >= 12.0
    assert style.T_META >= 9.0


def test_every_furnished_brand_ships_the_page_marker_and_the_band(furnished):
    """pagenums.MarkerStyle takes geometry, size, colour and font from the
    brand, so a brand missing one of them fails at renumber() time - after
    the whole deck has been built."""
    style = furnished.style()
    for name in ("PAGE_X", "PAGE_Y", "PAGE_W", "PAGE_H", "PAGE_SIZE",
                 "PAGE_COLOR", "SANS", "COPYRIGHT", "L", "R", "W"):
        assert hasattr(style, name), name


def test_the_repository_ships_exactly_one_brand_and_it_is_furnished():
    """One brand, and it draws slides.

    This replaces an assertion that the repository shipped at least TWO
    brands with a style - which was true only while `brands/example` and
    `brands/example2` existed as fixtures, and which was there to prove the
    walk above was worth something. The coverage that assertion really stood
    for - that two DIFFERENT masters exist and the Phase 2 transplant crosses
    them - moved to tests/test_template.py::
    test_a_variant_template_is_a_second_master_of_the_same_brand, where it is
    asserted against the generated files rather than inferred from a package
    count.
    """
    assert WITH_STYLE == ["relay"], WITH_STYLE
    assert WITH_FURNITURE == ["relay"], WITH_FURNITURE


def test_every_brand_names_its_icon_colour_key(furnished):
    """`deck_kit.components.matrix_frame` builds an icon filename as
    `ic_<name>_<ICON_KEY>.png`. The kit used to hardcode "blue" - one brand's
    value living in src/ - and a brand whose icons are cropped in another key
    got a missing-file raise mid-deck."""
    style = furnished.style()
    key = getattr(style, "ICON_KEY", None)
    assert isinstance(key, str) and key, furnished.name
    icons = sorted(furnished.icon_dir.glob("ic_*_%s.png" % key))
    assert icons, "%s declares ICON_KEY %r and ships no icon in it" % (
        furnished.name, key)


def test_header_measures_the_title_against_the_display_face(furnished, slide):
    """`header`'s optional `display` argument is the display role's metrics.
    A brand whose title face is not its body face measures the title with
    the wrong factors without it, and the factors are per face - which is a
    silent overflow, the one thing the register exists to stop."""
    style = furnished.style()
    warn = WarnRegister()
    style.header(slide, furnished.metrics(), warn, "01. Section", "A title that fits",
                 "A subtitle.", 7, display=furnished.metrics("display"))
    assert warn.clean
    long_warn = WarnRegister()
    style.header(slide, furnished.metrics(), long_warn, "01. Section", "A title " * 40,
                 "sub", 7, display=furnished.metrics("display"))
    assert "OVERFLOW" in long_warn.dump()


def test_every_face_a_brand_names_in_style_is_the_face_brand_py_declares(furnished):
    """style.py writes a family name onto a run and brand.py points the
    measurement at a file. Two spellings of one family is a deck measured
    against a face it is not set in, and nothing raises."""
    style = furnished.style()
    for attr, role in (("SANS", "sans"), ("DISPLAY", "display"), ("MONO", "mono")):
        if hasattr(style, attr):
            assert getattr(style, attr) == furnished.family(role), attr


def test_the_page_marker_font_is_a_family_the_brand_declares(furnished):
    style = furnished.style()
    declared = {furnished.family(r) for r in ("sans", "display", "mono")}
    assert getattr(style, "PAGE_FONT", style.SANS) in declared
