"""The HTML half of a design system mirrors its PPTX half.

These tests read CSS, HTML and markdown on purpose: the artifacts under
test ARE those files. They establish no doctrine about any .py file beyond
reading the brand's T_* names, and are not listed in
test_no_source_grep_doctrines.py's covered lists.

`brands/relay` is the repository's only design system and the one every draft
is written against. The mirror rule - every `T_*` has a `--t-*`, every token
the shared vocabulary uses is defined - is a rule about brands rather than
about one brand, so MIRRORED and BRAND_TOKENS below are lists read by
parametrize rather than a pair of constants: a second brand that ships both
halves is walked without this file being edited. A brand that breaks the rule
renders its drafts with browser defaults and no error anywhere.

There used to be a second brand here, `brands/example`, kept specifically so
that two brands proved the rule. It was deleted with the rest of the fixture
brands; what its `tokens.css` proved about `templates/components.css` -
that the shared vocabulary resolves against a brand's tokens - is proved
against Relay's by the same parametrized tests.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ROOT / "templates" / "components.css"
SLIDE_CSS = ROOT / "templates" / "slide.css"
REFERENCE = ROOT / "references" / "02-html-stage.md"

RELAY_TOKENS = ROOT / "brands" / "relay" / "tokens.css"
RELAY_SLIDE_CSS = ROOT / "brands" / "relay" / "slide.css"
RELAY_STYLE_PY = ROOT / "brands" / "relay" / "style.py"

# The repository's drafts: ten slides, written against brands/relay.
DRAFTS = sorted((ROOT / "examples" / "ai-horizon" / "drafts").glob("*.html"))

# (tokens.css, style.py) for every brand that ships both halves.
MIRRORED = [(RELAY_TOKENS, RELAY_STYLE_PY)]
# Every brand whose tokens.css must satisfy the shared vocabulary in
# templates/. slide.css imports the default brand's tokens, but any brand a
# draft is written against has to resolve the same names.
BRAND_TOKENS = [RELAY_TOKENS]

DECLARED = re.compile(r"(--[a-z][a-z0-9-]*)\s*:")
REFERENCED = re.compile(r"var\(\s*(--[a-z][a-z0-9-]*)")
T_CONST = re.compile(r"^(T_[A-Z0-9_]+)\s*=", re.M)


def _text(path):
    return path.read_text(encoding="utf-8")


def _declared(path):
    return set(DECLARED.findall(_text(path)))


@pytest.mark.parametrize("tokens_css", BRAND_TOKENS, ids=lambda p: p.parent.name)
def test_every_token_the_vocabulary_uses_is_defined_in_tokens_css(tokens_css):
    """A component reaching for a token the brand does not define renders
    with the browser default and no error - the same silent failure as the
    serving-root trap, one level down. Walked over every brand, because
    templates/slide.css names one brand's tokens and any brand may be the
    one a draft imports."""
    referenced = set(REFERENCED.findall(_text(COMPONENTS)))
    referenced |= set(REFERENCED.findall(_text(SLIDE_CSS)))
    # Knobs a component declares for itself (--band-alpha, --cols, --row-h,
    # --gap) are parameters, not brand tokens; they must be declared locally.
    local = _declared(COMPONENTS)
    missing = sorted(referenced - local - _declared(tokens_css))
    assert missing == [], "%s does not define: %s" % (tokens_css.parent.name, missing)


@pytest.mark.parametrize("tokens_css,style_py", MIRRORED,
                         ids=lambda p: p.parent.name)
def test_every_type_size_in_style_py_has_a_css_token(tokens_css, style_py):
    """T_CAPTION is --t-caption, ALL_CAPS_MICRO ones included: the two
    halves of the design system name the same scale, so a draft and its
    builder cannot disagree about which size a caption is."""
    consts = T_CONST.findall(_text(style_py))
    assert len(consts) >= 15, consts
    tokens = _declared(tokens_css)
    missing = [c for c in consts if "--" + c.lower().replace("_", "-") not in tokens]
    assert missing == [], "%s lacks a --t-* for: %s" % (tokens_css.name, missing)


@pytest.mark.parametrize("tokens_css,style_py", MIRRORED,
                         ids=lambda p: p.parent.name)
def test_every_css_type_token_has_a_size_in_style_py(tokens_css, style_py):
    """The mirror runs both ways. A --t-* nothing in style.py names is a
    size a draft can reach for and a builder cannot, which is exactly how a
    draft ends up unportable."""
    consts = set(T_CONST.findall(_text(style_py)))
    names = {"--" + c.lower().replace("_", "-") for c in consts}
    extra = sorted(t for t in _declared(tokens_css)
                   if t.startswith("--t-") and t not in names)
    assert extra == [], "%s declares --t-* with no T_* in style.py: %s" % (
        tokens_css.name, extra)


def _vocabulary_table_classes():
    """Every `.class` named in the first column of the reference's
    vocabulary table."""
    text = _text(REFERENCE)
    section = text.split("## The component vocabulary in CSS")[1].split("\n## ")[0]
    classes = []
    for line in section.splitlines():
        if not line.startswith("| `."):
            continue
        first = line.strip().strip("|").split("|")[0]
        classes += re.findall(r"`(\.[a-z][a-z0-9_-]*)(?:[ ,`]|$)", first + " ")
    return classes


def test_every_class_in_the_reference_vocabulary_table_exists_in_components_css():
    classes = _vocabulary_table_classes()
    assert len(classes) >= 30, classes
    css = _text(COMPONENTS)
    missing = [c for c in classes if not re.search(re.escape(c) + r"(?![a-z0-9_-])", css)]
    assert missing == [], "reference names classes components.css lacks: %s" % missing


def test_slide_css_imports_the_default_brands_tokens_then_components():
    """The skeleton points at the default design system. Change the default
    and this line changes with it, or every draft written from the template
    silently resolves against the wrong palette."""
    text = _text(SLIDE_CSS)
    imports = re.findall(r'@import url\("([^"]+)"\)', text)
    assert imports == ["../brands/relay/tokens.css", "components.css"], imports


# --- the Relay brand: a real design system, adopted rather than authored ---

def test_the_relay_brand_ships_both_halves():
    for path in (RELAY_TOKENS, RELAY_SLIDE_CSS, RELAY_STYLE_PY):
        assert path.is_file(), path


def test_relay_tokens_carry_the_shared_role_names_and_its_own():
    """The shared names are what makes templates/components.css resolve
    against Relay's tokens; the Relay names are what a Relay draft reaches
    for. Both have to be there.

    This is also the whole of what the deleted fixture brand's
    `test_the_palette_and_grid_mirror_style_py` asserted - the same shared
    role names, the same grid tokens, the same "tokens.css is the root of the
    import chain" rule - against the brand that is actually drafted against.
    """
    tokens = _declared(RELAY_TOKENS)
    for name in ("--blue", "--blue-dark", "--navy", "--title", "--grey", "--muted",
                 "--white", "--line", "--cell-bd", "--red-bg", "--red", "--amb-bg",
                 "--amb", "--amb-txt", "--amb-leg", "--bg-top", "--bg-bottom",
                 "--ink", "--panel",
                 "--ls-label", "--ls-title", "--ls-card", "--ls-body",
                 "--left", "--right", "--width", "--row-label-w", "--col-gap",
                 "--page-x", "--page-y", "--page-w", "--page-h"):
        assert name in tokens, name
    for name in ("--ink-1000", "--paper", "--signal-500", "--volt-500",
                 "--state-positive", "--rad-surface", "--rad-control",
                 "--hair", "--rule-heavy", "--track-display", "--track-mono",
                 "--grid-hair", "--dark"):
        assert name in tokens, name
    text = _text(RELAY_TOKENS)
    # The 2/3 scale from Relay's own 1920x1080 kit: 120 px padding -> 80.
    assert "--left: 80px" in text and "--right: 1200px" in text
    assert "--width: 1120px" in text and "--col-gap: 16px" in text
    assert "@import url(" not in text, "tokens.css is the root of the import chain"


def test_relay_declares_a_face_per_type_role():
    """Three families, one per role, and an @font-face for each weight of
    each. The draft has to wrap where the builder measures, and it cannot
    if the browser is setting Arial where the builder set Space Grotesk."""
    text = _text(RELAY_TOKENS)
    tokens = _declared(RELAY_TOKENS)
    for name in ("--sans", "--display", "--mono"):
        assert name in tokens, name
    faces = re.findall(r'font-family:\s*"([^"]+)";\s*\n\s*font-weight:\s*(\d+);\s*\n'
                       r'\s*src:\s*url\("fonts/([^"]+)"\)', text)
    assert sorted(faces) == sorted([
        ("JetBrains Mono", "400", "JetBrainsMono-Regular.ttf"),
        ("JetBrains Mono", "700", "JetBrainsMono-Bold.ttf"),
        ("Public Sans", "400", "PublicSans-Regular.ttf"),
        ("Public Sans", "700", "PublicSans-Bold.ttf"),
        ("Space Grotesk", "400", "SpaceGrotesk-Regular.ttf"),
        ("Space Grotesk", "700", "SpaceGrotesk-Bold.ttf"),
    ]), faces
    for family, _, filename in faces:
        assert (RELAY_TOKENS.parent / "fonts" / filename).is_file(), filename


def test_relay_slide_css_imports_its_own_tokens_then_the_shared_components():
    imports = re.findall(r'@import url\("([^"]+)"\)', _text(RELAY_SLIDE_CSS))
    assert imports == ["tokens.css", "../../templates/components.css"], imports


def test_every_token_the_relay_stylesheet_uses_is_defined():
    """Same silent failure as the serving-root trap, one level down: a
    component reaching for a token the brand does not define renders with
    the browser default and no error."""
    referenced = set(REFERENCED.findall(_text(RELAY_SLIDE_CSS)))
    referenced |= set(REFERENCED.findall(_text(COMPONENTS)))
    local = _declared(RELAY_SLIDE_CSS) | _declared(COMPONENTS)
    missing = sorted(referenced - local - _declared(RELAY_TOKENS))
    assert missing == [], "the Relay stylesheets use undefined tokens: %s" % missing


def test_relay_tokens_hold_no_literal_colour_outside_the_palette_block():
    """Every colour is a token or an alias of one. A hex dropped into a
    component rule is how a rebrand stops being one file."""
    body = _text(RELAY_SLIDE_CSS)
    assert not re.search(r"#[0-9A-Fa-f]{3,8}\b", body), \
        "brands/relay/slide.css carries a literal colour; use a token"


# --- the drafts ------------------------------------------------------------

def test_the_ai_horizon_drafts_exist_one_per_slide():
    names = [p.name for p in DRAFTS]
    assert names == ["s01-cover.html", "s02-how-to-read.html",
                     "s03-horizon-map.html", "s04-next-years.html",
                     "s05-next-decade.html", "s06-toward-2050.html",
                     "s07-beyond-2050.html", "s08-matrix.html",
                     "s09-readiness.html", "s10-signposts.html"], names


@pytest.mark.parametrize("draft", DRAFTS, ids=lambda p: p.name)
def test_each_draft_links_the_brand_stylesheet_and_says_it_is_disposable(draft):
    text = _text(draft)
    assert '<link rel="stylesheet" href="../../../brands/relay/slide.css">' in text
    assert "<style" not in text, \
        "a draft carries no CSS of its own; the vocabulary is the stylesheet"
    low = text.lower()
    assert "disposable" in low and "source of truth" in low, \
        "%s does not say the draft is disposable and the builder the source of truth" % draft.name


@pytest.mark.parametrize("draft", DRAFTS, ids=lambda p: p.name)
def test_no_draft_contains_a_script(draft):
    assert "<script" not in _text(draft).lower(), draft.name


@pytest.mark.parametrize("draft", DRAFTS, ids=lambda p: p.name)
def test_each_draft_uses_only_classes_the_stylesheets_define(draft):
    """A class the stylesheet does not know renders as nothing, silently;
    this is how a draft quietly drifts back to hand-rolled CSS."""
    known = set(re.findall(r"\.([a-z][a-z0-9_-]*)",
                           _text(COMPONENTS) + _text(RELAY_SLIDE_CSS)))
    used = set()
    for attr in re.findall(r'class="([^"]+)"', _text(draft)):
        used |= set(attr.split())
    unknown = sorted(used - known)
    assert unknown == [], "%s uses classes no stylesheet defines: %s" % (draft.name, unknown)


@pytest.mark.parametrize("draft", DRAFTS, ids=lambda p: p.name)
def test_each_draft_points_at_committed_brand_assets(draft):
    """`primitives.icon` raises on a missing file and the draft's <img> just
    renders nothing, so the draft is the half that fails silently."""
    for src in re.findall(r'src="([^"]+)"', _text(draft)):
        assert src.startswith("../../../brands/relay/"), src
        assert (draft.parent / src).resolve().is_file(), src
