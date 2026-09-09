from pathlib import Path

import pytest

from deck_kit import brand as brand_mod
from deck_kit.brand import BrandSpec, load_brand


def test_brand_spec_derives_slide_size_from_the_canvas():
    spec = load_brand("relay")
    assert spec.slide_size_emu == (spec.canvas_w * 9525, spec.canvas_h * 9525)


def test_brand_selects_its_layout_by_name_not_index():
    spec = load_brand("relay")
    assert isinstance(spec.master_name, str) and spec.master_name
    assert isinstance(spec.layout_name, str) and spec.layout_name


def test_brand_supplies_the_measurement_factors():
    """The body role's pair, calibrated for Public Sans against an export -
    brands/relay/brand.py's docstring carries the method and the numbers."""
    spec = load_brand("relay")
    assert spec.width_factor == 1.11
    assert spec.wrap_factor == 1.06


def test_brand_paths_resolve_to_files_that_exist():
    spec = load_brand("relay")
    for path in (spec.font_dir, spec.logo_primary, spec.logo_secondary):
        assert path.exists(), path


def test_unknown_brand_raises_a_clear_error():
    with pytest.raises(ValueError, match="no such brand"):
        load_brand("does-not-exist")


def test_brand_spec_rejects_an_index_shaped_layout_selector():
    with pytest.raises(TypeError, match="by name"):
        BrandSpec(name="x", master_name=3, layout_name="Content")


def test_brand_spec_rejects_an_empty_name():
    """A real corporate master often arrives with every slide master called
    ''. Writing that into brand.py used to pass __post_init__ and then pass
    inspect_template.py's `master_name in names` clause, while deck._layout
    bound to whichever unnamed master came first - an index in disguise, and
    the disguise fooled the contract verifier."""
    for empty in ("", "   ", "\t"):
        with pytest.raises(ValueError, match="by name"):
            BrandSpec(name="x", master_name=empty, layout_name="Content")
        with pytest.raises(ValueError, match="by name"):
            BrandSpec(name="x", master_name="Master", layout_name=empty)
    with pytest.raises(ValueError, match="make_template.py"):
        BrandSpec(name="x", master_name="", layout_name="Content")


def test_replacing_a_name_on_a_loaded_brand_still_refuses_an_index():
    """`dataclasses.replace` is how the Phase 2 donor gets its variant master
    and layout names (`scripts/make_template.py`'s `variant_spec`), now that
    the second master is a variant of this brand rather than a second brand
    package. replace() re-runs `__post_init__`, so the by-name-never-by-index
    rule is enforced on the copy as well as on the original - a variant that
    could take an index would put the rule back exactly where it came out."""
    from dataclasses import replace

    spec = load_brand("relay")
    renamed = replace(spec, master_name=spec.master_name + " (donor)",
                      layout_name=spec.layout_name + " (donor)")
    assert renamed.master_name == "Relay Master (donor)"
    assert renamed.layout_name == "Relay Content (donor)"
    # The original is untouched: a loaded brand is a module-level singleton,
    # and renaming it in place would rename it for every other caller.
    assert spec.master_name == "Relay Master"
    with pytest.raises(TypeError, match="by name"):
        replace(spec, layout_name=0)


def _write_brand(root, name):
    """A minimal brand package on disk, enough for load_brand to import."""
    d = root / name
    d.mkdir(parents=True)
    (d / "__init__.py").write_text("")
    (d / "brand.py").write_text(
        "from deck_kit.brand import BrandSpec\n"
        "BRAND = BrandSpec(name=%r, master_name='M', layout_name='L')\n" % name)
    return d


def test_brand_root_comes_from_the_environment_when_it_is_set(tmp_path, monkeypatch):
    _write_brand(tmp_path, "elsewhere")
    monkeypatch.setenv("DECKWRIGHT_BRANDS", str(tmp_path))
    assert brand_mod.brands_dir() == tmp_path
    assert brand_mod.load_brand("elsewhere").name == "elsewhere"


def test_brand_root_can_be_passed_explicitly_overriding_the_environment(tmp_path, monkeypatch):
    other = tmp_path / "other"
    _write_brand(other, "explicit")
    monkeypatch.setenv("DECKWRIGHT_BRANDS", str(tmp_path / "ignored"))
    assert brand_mod.load_brand("explicit", brands_dir=other).name == "explicit"


def test_brand_root_falls_back_to_the_repository_when_nothing_is_set(monkeypatch):
    monkeypatch.delenv("DECKWRIGHT_BRANDS", raising=False)
    assert (brand_mod.brands_dir() / "relay" / "brand.py").exists()


def test_the_module_exposes_no_frozen_brands_dir_constant():
    """A module-level constant is evaluated at import and cannot be overridden
    by the time a caller knows where the brands are."""
    assert not hasattr(brand_mod, "BRANDS_DIR")


def _every_brand():
    from deck_kit.brand import brands_dir
    return sorted(d.name for d in brands_dir().iterdir() if (d / "brand.py").is_file())


@pytest.mark.parametrize("name", _every_brand())
def test_every_brand_declares_paths_that_exist(name):
    """A brand that names a font, a logo or an icon directory it does not
    have fails at the first build, after the template is already written -
    and `primitives.icon` raises rather than returning silently, so the
    failure lands mid-deck rather than at load."""
    spec = load_brand(name)
    for field in ("logo_primary", "logo_secondary", "icon_dir"):
        path = getattr(spec, field)
        if path is not None:
            assert path.exists(), "%s: %s -> %s" % (name, field, path)
    # font_dir and the face are checked separately: a brand may point
    # font_dir at a directory it does not own and reach the real faces
    # through ".." inside font_regular, so that BrandSpec.style_path keeps
    # resolving to its own palette. What must exist is the face.
    if spec.font_dir is not None and spec.font_regular is not None:
        for face in (spec.font_regular, spec.font_bold):
            assert (spec.font_dir / face).exists(), "%s: %s" % (name, face)


@pytest.mark.parametrize("name", _every_brand())
def test_every_brand_selects_master_and_layout_by_name(name):
    spec = load_brand(name)
    assert isinstance(spec.master_name, str) and spec.master_name
    assert isinstance(spec.layout_name, str) and spec.layout_name


def test_no_two_brands_share_a_master_or_layout_name():
    """`deck._layout` resolves by name across every master in the file, so
    two brands with the same master name cannot both be present in one
    transplanted deck without one silently winning.

    The repository ships one brand, so this walk is currently vacuous over
    brands - but the deck the Phase 2 round trip builds carries TWO masters,
    the brand's own and the donor variant of it, and that pair is the case
    that matters now. `make_template.variant_spec` is what keeps them
    distinct, and tests/test_template.py::
    test_a_variant_template_is_a_second_master_of_the_same_brand asserts it
    against the generated files. This walk stays so that a second brand
    package cannot be added without meeting the same rule.
    """
    masters, layouts = [], []
    for name in _every_brand():
        spec = load_brand(name)
        masters.append(spec.master_name)
        layouts.append(spec.layout_name)
    assert len(set(masters)) == len(masters), masters
    assert len(set(layouts)) == len(layouts), layouts


# --- type roles -------------------------------------------------------------

def test_a_one_family_brand_answers_every_role():
    """A brand naming one family sets its display and mono lines in that
    family, so a style helper written for three roles must keep working
    against it and `metrics("display")` must hand back the sans metrics
    rather than raising.

    Built here rather than loaded. The repository's one brand declares all
    three roles; the one-family brand this used to load, `brands/example`,
    was deleted when the repository dropped to a single brand. A BrandSpec is
    the whole contract, so constructing one proves the fallback without a
    package on disk - and this is the only thing that still walks it.
    """
    spec = BrandSpec(name="one-family", master_name="M", layout_name="L",
                     sans="Public Sans", font_dir=Path("brands/relay/fonts"),
                     font_regular="PublicSans-Regular.ttf",
                     font_bold="PublicSans-Bold.ttf",
                     width_factor=1.11, wrap_factor=1.06)
    assert not spec.declares("display") and not spec.declares("mono")
    for role in ("sans", "display", "mono"):
        assert spec.family(role) == spec.sans
        assert spec.metrics(role) is spec.metrics()


def test_a_three_family_brand_answers_each_role_with_its_own_face():
    spec = load_brand("relay")
    assert spec.family("sans") == "Public Sans"
    assert spec.family("display") == "Space Grotesk"
    assert spec.family("mono") == "JetBrains Mono"
    three = [spec.metrics(r) for r in ("sans", "display", "mono")]
    assert len({id(m) for m in three}) == 3
    assert [m.files[False] for m in three] == [
        "PublicSans-Regular.ttf", "SpaceGrotesk-Regular.ttf",
        "JetBrainsMono-Regular.ttf"]


def test_each_role_carries_its_own_measurement_factors():
    """The factors calibrate a face, not a repository. Sharing one pair
    across three families measures two of them against the third."""
    spec = load_brand("relay")
    assert spec.metrics("mono").width_factor == spec.mono_width_factor
    assert spec.metrics("display").width_factor == spec.display_width_factor
    assert spec.metrics("mono").width_factor != spec.metrics("sans").width_factor


def test_metrics_are_built_once_per_role():
    """TextMetrics caches loaded faces by size; a fresh one per call would
    reload the TTF for every measurement a builder takes."""
    spec = load_brand("relay")
    assert spec.metrics("display") is spec.metrics("display")


def test_an_unknown_role_raises_rather_than_falling_back():
    spec = load_brand("relay")
    with pytest.raises(ValueError, match="no such type role"):
        spec.metrics("handwriting")
    with pytest.raises(ValueError, match="no such type role"):
        spec.family("serif")


def test_a_role_declared_without_its_files_fails_loudly():
    spec = BrandSpec(name="x", master_name="M", layout_name="L",
                     font_dir=Path("."), display="Some Face")
    with pytest.raises(ValueError, match="display_regular"):
        spec.metrics("display")


@pytest.mark.parametrize("name", _every_brand())
def test_every_declared_face_is_on_disk(name):
    """faces() walks the roles the brand declares, so a face added to a
    brand is covered here without this test being edited."""
    spec = load_brand(name)
    for role, family, regular, bold in spec.faces():
        assert isinstance(family, str) and family, (name, role)
        for filename in (regular, bold):
            assert (spec.font_dir / filename).exists(), "%s %s: %s" % (name, role, filename)
